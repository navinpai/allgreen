"""
FastAPI integration for allgreen health checks.

Usage:
    from fastapi import FastAPI
    from allgreen.integrations import fastapi_integration

    app = FastAPI()

    # Method 1: Mount the router
    app.include_router(
        fastapi_integration.create_router(app_name="My FastAPI App"),
        prefix="/health"
    )

    # Method 2: Add individual route
    @app.get("/healthcheck")
    async def health():
        return await fastapi_integration.healthcheck_endpoint()
"""

import os
from datetime import datetime

try:
    import anyio
    from fastapi import APIRouter, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    raise ImportError(
        "FastAPI, anyio, and jinja2 are required for fastapi_integration. "
        "Install with: pip install allgreen[fastapi]"
    ) from None

import allgreen
from ..config import load_config
from ..core import CheckStatus, get_registry


def create_router(
    app_name: str = "FastAPI Application",
    config_path: str | None = None,
    environment: str | None = None,
    prefix: str | None = None
) -> APIRouter:
    """
    Create a FastAPI router with health check endpoints.

    Args:
        app_name: Application name to display
        config_path: Path to allgood.py config file
        environment: Environment name
        prefix: URL prefix for routes (use with app.include_router(router, prefix="/..."))

    Returns:
        APIRouter with /healthcheck and /healthcheck.json endpoints
        
    Usage:
        router = create_router(app_name="My App")
        app.include_router(router, prefix="/health")  # Routes: /health/healthcheck
    """
    # Create router without prefix - let FastAPI handle it via include_router
    router = APIRouter()

    @router.get("/healthcheck", response_class=HTMLResponse)
    @router.get("/healthcheck.json", response_class=JSONResponse)
    async def healthcheck_endpoint(request: Request):
        return await _healthcheck_handler(
            request, app_name, config_path, environment
        )

    return router


async def healthcheck_endpoint(
    request: Request = None,
    app_name: str = "FastAPI Application",
    config_path: str | None = None,
    environment: str | None = None
):
    """
    Standalone FastAPI health check endpoint.

    Can be used directly as a route handler:
        @app.get("/healthcheck")
        async def health(request: Request):
            return await healthcheck_endpoint(request)
    """
    return await _healthcheck_handler(request, app_name, config_path, environment)


async def _healthcheck_handler(
    request: Request | None,
    app_name: str,
    config_path: str | None,
    environment: str | None
):
    """Internal handler for health check logic."""

    # Load configuration and run checks in thread pool to avoid blocking event loop
    if environment is None:
        environment = "development"

    async def run_checks():
        load_config(config_path, environment)
        registry = get_registry()
        return registry.run_all(environment)

    results = await anyio.to_thread.run_sync(run_checks)

    # Calculate statistics and overall status
    stats = _calculate_stats(results)
    overall_status = _get_overall_status(stats)

    # Determine response format
    wants_json = False
    if request:
        accept_header = request.headers.get("accept", "")
        format_param = request.query_params.get("format")
        wants_json = (
            "application/json" in accept_header or
            format_param == "json" or
            request.url.path.endswith(".json")
        )

    # Determine HTTP status code
    status_code = 200 if overall_status == "passed" else 503

    # Cache-Control headers to prevent caching
    headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

    if wants_json:
        # Return JSON response
        response_data = _format_json_response(
            results, stats, overall_status, app_name, environment
        )
        return JSONResponse(content=response_data, status_code=status_code, headers=headers)
    else:
        # Return HTML response
        context = {
            'results': results,
            'stats': stats,
            'overall_status': overall_status,
            'app_name': app_name,
            'environment': environment,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        html_content = _render_html_template(context)
        return HTMLResponse(content=html_content, status_code=status_code, headers=headers)


def _calculate_stats(results):
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


def _get_overall_status(stats):
    """Determine overall health status."""
    if stats["failed"] > 0:
        return "failed"
    elif stats["total"] == stats["skipped"]:
        return "no_checks"
    elif stats["passed"] > 0:
        return "passed"
    else:
        return "unknown"


def _format_json_response(results, stats, overall_status, app_name, environment):
    """Format results for JSON response."""
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

    return {
        "status": overall_status,
        "stats": stats,
        "environment": environment,
        "app_name": app_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "checks": json_results,
    }


def _render_html_template(context):
    """Render HTML template using the shared template."""
    # Use the shared template from allgreen/templates/
    template_dir = os.path.join(os.path.dirname(allgreen.__file__), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('healthcheck.html')
    return template.render(**context)
