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
    from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    raise ImportError(
        "FastAPI, anyio, and jinja2 are required for fastapi_integration. "
        "Install with: pip install allgreen[fastapi]"
    ) from None

import allgreen

from ..config import load_config
from ..core import get_registry
from ..metrics import PROMETHEUS_CONTENT_TYPE, render_prometheus_metrics
from ..reporting import calculate_stats, format_json_response, get_overall_status


def create_router(
    app_name: str = "FastAPI Application",
    config_path: str | None = None,
    environment: str | None = None,
    prefix: str | None = None,
    metrics_path: str | None = "/metrics",
    show_tracebacks: bool | None = None,
) -> APIRouter:
    """
    Create a FastAPI router with health check endpoints.

    Args:
        app_name: Application name to display
        config_path: Path to allgreen_config.py config file
        environment: Environment name
        prefix: URL prefix for routes (use with app.include_router(router, prefix="/..."))
        metrics_path: Route for the Prometheus metrics endpoint.
            Set to None to disable it.
        show_tracebacks: Include full tracebacks for errored checks in
            responses. Defaults to True only in the development environment.

    Returns:
        APIRouter with /healthcheck, /healthcheck.json, and /metrics endpoints

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
            request, app_name, config_path, environment, show_tracebacks
        )

    if metrics_path:

        @router.get(metrics_path, response_class=PlainTextResponse)
        async def metrics_endpoint():
            return await _metrics_handler(config_path, environment)

    return router


async def _metrics_handler(
    config_path: str | None, environment: str | None
) -> PlainTextResponse:
    """Run checks and render Prometheus metrics.

    Always returns 200 - health is conveyed via the allgreen_up metric.
    """
    if environment is None:
        environment = "development"

    await anyio.to_thread.run_sync(load_config, config_path, environment)
    results = await get_registry().run_all_async(environment)

    return PlainTextResponse(
        content=render_prometheus_metrics(results),
        media_type=PROMETHEUS_CONTENT_TYPE,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


async def healthcheck_endpoint(
    request: Request | None = None,
    app_name: str = "FastAPI Application",
    config_path: str | None = None,
    environment: str | None = None,
    show_tracebacks: bool | None = None,
):
    """
    Standalone FastAPI health check endpoint.

    Can be used directly as a route handler:
        @app.get("/healthcheck")
        async def health(request: Request):
            return await healthcheck_endpoint(request)
    """
    return await _healthcheck_handler(
        request, app_name, config_path, environment, show_tracebacks
    )


async def _healthcheck_handler(
    request: Request | None,
    app_name: str,
    config_path: str | None,
    environment: str | None,
    show_tracebacks: bool | None = None,
):
    """Internal handler for health check logic."""

    if environment is None:
        environment = "development"
    if show_tracebacks is None:
        show_tracebacks = environment == "development"

    # Load configuration in a thread pool (file I/O) to avoid blocking the
    # event loop, then run checks natively async: coroutine checks are awaited
    # on the event loop, sync checks run in worker threads.
    await anyio.to_thread.run_sync(load_config, config_path, environment)
    registry = get_registry()
    results = await registry.run_all_async(environment)

    # Calculate statistics and overall status
    stats = calculate_stats(results)
    overall_status = get_overall_status(stats)

    # Determine response format
    wants_json = False
    if request:
        accept_header = request.headers.get("accept", "")
        format_param = request.query_params.get("format")
        wants_json = (
            "application/json" in accept_header
            or format_param == "json"
            or request.url.path.endswith(".json")
        )

    # Determine HTTP status code
    status_code = 200 if overall_status == "passed" else 503

    # Cache-Control headers to prevent caching
    headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

    if wants_json:
        # Return JSON response
        response_data = format_json_response(
            results,
            stats,
            overall_status,
            app_name,
            environment,
            include_tracebacks=show_tracebacks,
        )
        return JSONResponse(
            content=response_data, status_code=status_code, headers=headers
        )
    else:
        # Return HTML response
        context = {
            "results": results,
            "stats": stats,
            "overall_status": overall_status,
            "app_name": app_name,
            "environment": environment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "show_tracebacks": show_tracebacks,
        }

        html_content = _render_html_template(context)
        return HTMLResponse(
            content=html_content, status_code=status_code, headers=headers
        )


def _render_html_template(context):
    """Render HTML template using the shared template."""
    # Use the shared template from allgreen/templates/
    template_dir = os.path.join(os.path.dirname(allgreen.__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("healthcheck.html")
    return template.render(**context)
