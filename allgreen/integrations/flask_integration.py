import os
from datetime import datetime
from typing import Any

from flask import Blueprint, Flask, Response, jsonify, render_template, request

import allgreen

from ..config import load_config
from ..core import Check, CheckResult, CheckStatus, get_registry


class HealthCheckApp:
    def __init__(
        self,
        app_name: str = "Application",
        config_path: str | None = None,
        environment: str | None = None,
        auto_reload_config: bool = True
    ):
        self.app_name = app_name
        self.config_path = config_path
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.auto_reload_config = auto_reload_config
        self._last_config_mtime = None

        # Load initial config
        if auto_reload_config or not get_registry().get_checks():
            self._load_config()

    def _load_config(self) -> bool:
        """Load or reload configuration if needed."""
        if not self.auto_reload_config:
            return load_config(self.config_path, self.environment)

        # Check if we should reload config based on file modification time
        if self.config_path and os.path.exists(self.config_path):
            current_mtime = os.path.getmtime(self.config_path)
            if self._last_config_mtime is None or current_mtime > self._last_config_mtime:
                self._last_config_mtime = current_mtime
                return load_config(self.config_path, self.environment)
        elif not self.config_path:
            # Try to find and load config file
            return load_config(None, self.environment)

        return True

    def _calculate_stats(self, results: list[tuple[Check, CheckResult]]) -> dict[str, int]:
        """Calculate statistics from check results."""
        stats = {
            "total": len(results),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0
        }

        for _, result in results:
            if result.status == CheckStatus.PASSED:
                stats["passed"] += 1
            elif result.status == CheckStatus.FAILED:
                stats["failed"] += 1
            elif result.status == CheckStatus.SKIPPED:
                stats["skipped"] += 1
            elif result.status == CheckStatus.ERROR:
                stats["error"] += 1

        # Combine failed and error for simpler display
        stats["failed"] += stats["error"]

        return stats

    def _get_overall_status(self, stats: dict[str, int]) -> str:
        """Determine overall health status."""
        if stats["failed"] > 0:
            return "failed"
        elif stats["total"] == stats["skipped"]:
            return "no_checks"
        elif stats["passed"] > 0:
            return "passed"
        else:
            return "unknown"

    def run_health_checks(self) -> tuple[list[tuple[Check, CheckResult]], dict[str, Any]]:
        """Run all health checks and return results with metadata."""
        # Reload config if needed
        self._load_config()

        # Get all checks and run them
        registry = get_registry()
        results = registry.run_all(self.environment)

        # Calculate statistics
        stats = self._calculate_stats(results)
        overall_status = self._get_overall_status(stats)

        metadata = {
            "stats": stats,
            "overall_status": overall_status,
            "environment": self.environment,
            "app_name": self.app_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return results, metadata

    def healthcheck_html(self) -> tuple[str, int, dict[str, str]]:
        """Generate HTML health check page."""
        results, metadata = self.run_health_checks()

        # Determine HTTP status code
        status_code = 200 if metadata["overall_status"] == "passed" else 503

        # Render template
        html = render_template(
            "healthcheck.html",
            results=results,
            **metadata
        )

        # Add Cache-Control headers
        headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

        return html, status_code, headers

    def healthcheck_json(self) -> tuple[dict[str, Any], int, dict[str, str]]:
        """Generate JSON health check response."""
        results, metadata = self.run_health_checks()

        # Convert results to JSON-serializable format
        json_results = []
        for check, result in results:
            json_results.append({
                "description": check.description,
                "status": result.status.value,
                "message": result.message,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "skip_reason": result.skip_reason,
            })

        response_data = {
            "status": metadata["overall_status"],
            "stats": metadata["stats"],
            "environment": metadata["environment"],
            "app_name": metadata["app_name"],
            "timestamp": metadata["timestamp"],
            "checks": json_results,
        }

        # Determine HTTP status code
        status_code = 200 if metadata["overall_status"] == "passed" else 503

        # Add Cache-Control headers
        headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

        return response_data, status_code, headers


def create_healthcheck_blueprint(
    app_name: str = "Application",
    config_path: str | None = None,
    environment: str | None = None,
    auto_reload_config: bool = True,
    url_prefix: str | None = None
) -> Blueprint:
    """Create a Blueprint with health check endpoints."""

    # Create blueprint
    blueprint = Blueprint(
        'healthcheck',
        __name__,
        template_folder=os.path.join(os.path.dirname(allgreen.__file__), 'templates'),
        url_prefix=url_prefix
    )

    # Create health check instance
    health_checker = HealthCheckApp(
        app_name=app_name,
        config_path=config_path,
        environment=environment,
        auto_reload_config=auto_reload_config
    )

    @blueprint.route("/healthcheck")
    def healthcheck():
        """Health check endpoint that returns HTML by default, JSON if requested."""
        accept_header = request.headers.get("Accept", "")
        if "application/json" in accept_header or request.args.get("format") == "json":
            data, status_code, headers = health_checker.healthcheck_json()
            response = jsonify(data)
            response.status_code = status_code
            response.headers.update(headers)
            return response
        else:
            html, status_code, headers = health_checker.healthcheck_html()
            response = Response(html, status=status_code, mimetype="text/html")
            response.headers.update(headers)
            return response

    @blueprint.route("/healthcheck.json")
    def healthcheck_json():
        """Explicit JSON health check endpoint."""
        data, status_code, headers = health_checker.healthcheck_json()
        response = jsonify(data)
        response.status_code = status_code
        response.headers.update(headers)
        return response

    return blueprint


def create_app(
    app_name: str = "Application",
    config_path: str | None = None,
    environment: str | None = None,
    auto_reload_config: bool = True,
    flask_app: Flask | None = None
) -> Flask:
    """Create and configure a Flask app with health check endpoints."""

    if flask_app is None:
        flask_app = Flask(__name__, template_folder=os.path.join(os.path.dirname(allgreen.__file__), 'templates'))

    # Create and register blueprint
    blueprint = create_healthcheck_blueprint(
        app_name=app_name,
        config_path=config_path,
        environment=environment,
        auto_reload_config=auto_reload_config
    )
    flask_app.register_blueprint(blueprint)

    return flask_app


def mount_healthcheck(
    app: Flask,
    app_name: str = "Application",
    config_path: str | None = None,
    environment: str | None = None,
    auto_reload_config: bool = True,
    url_prefix: str | None = None
) -> Flask:
    """Mount health check routes on an existing Flask app."""

    # Create and register blueprint
    blueprint = create_healthcheck_blueprint(
        app_name=app_name,
        config_path=config_path,
        environment=environment,
        auto_reload_config=auto_reload_config,
        url_prefix=url_prefix
    )
    app.register_blueprint(blueprint)

    return app


# For standalone usage
def run_standalone(
    host: str = "127.0.0.1",
    port: int = 5000,
    debug: bool = True,
    **kwargs
):
    """Run a standalone health check server."""
    app = create_app(**kwargs)
    app.run(host=host, port=port, debug=debug)
