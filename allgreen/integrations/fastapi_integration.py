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

from datetime import datetime
from typing import Optional

try:
    from fastapi import APIRouter, Request, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
    from jinja2 import Template
except ImportError:
    raise ImportError(
        "FastAPI and Jinja2 are required for fastapi_integration. "
        "Install with: pip install allgreen[fastapi]"
    )

from ..config import load_config
from ..core import CheckStatus, get_registry


def create_router(
    app_name: str = "FastAPI Application",
    config_path: Optional[str] = None,
    environment: Optional[str] = None,
    prefix: str = ""
) -> APIRouter:
    """
    Create a FastAPI router with health check endpoints.
    
    Args:
        app_name: Application name to display
        config_path: Path to allgood.py config file  
        environment: Environment name
        prefix: URL prefix for routes
        
    Returns:
        APIRouter with /healthcheck and /healthcheck.json endpoints
    """
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
    config_path: Optional[str] = None,
    environment: Optional[str] = None
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
    request: Optional[Request],
    app_name: str,
    config_path: Optional[str],
    environment: Optional[str]
):
    """Internal handler for health check logic."""
    
    # Load configuration and run checks
    if environment is None:
        environment = "development"
    
    load_config(config_path, environment)
    registry = get_registry()
    results = registry.run_all(environment)
    
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
    
    if wants_json:
        # Return JSON response
        response_data = _format_json_response(
            results, stats, overall_status, app_name, environment
        )
        return JSONResponse(content=response_data, status_code=status_code)
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
        return HTMLResponse(content=html_content, status_code=status_code)


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
    """Render HTML template using Jinja2."""
    # Use the same template as Flask but render with Jinja2 directly
    template_str = _get_html_template()
    template = Template(template_str)
    return template.render(**context)


def _get_html_template():
    """Get HTML template string."""
    # For brevity, returning a simple template
    # In a real implementation, this would be the full template
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Health Check - {{ app_name }}</title>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        .header { text-align: center; margin-bottom: 2rem; }
        .pass { color: green; }
        .fail { color: red; }
        .skip { color: orange; }
        .summary { display: flex; gap: 2rem; justify-content: center; margin: 2rem 0; }
        .summary-item { text-align: center; padding: 1rem; background: #f5f5f5; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Health Check: {{ app_name }}</h1>
        <p>Status: <strong>{{ overall_status }}</strong></p>
        <p>Environment: {{ environment }} | {{ timestamp }}</p>
    </div>
    
    <div class="summary">
        <div class="summary-item">
            <div style="font-size: 2rem; color: green;">{{ stats.passed }}</div>
            <div>Passed</div>
        </div>
        <div class="summary-item">
            <div style="font-size: 2rem; color: red;">{{ stats.failed }}</div>
            <div>Failed</div>
        </div>
        <div class="summary-item">
            <div style="font-size: 2rem; color: orange;">{{ stats.skipped }}</div>
            <div>Skipped</div>
        </div>
    </div>
    
    <h2>Detailed Results</h2>
    <ul>
    {% for check, result in results %}
        <li class="{{ result.status.value }}">
            <strong>{{ check.description }}</strong>: {{ result.status.value }}
            {% if result.duration_ms %} ({{ "%.1f"|format(result.duration_ms) }}ms){% endif %}
            {% if result.skip_reason %}<br><em>{{ result.skip_reason }}</em>{% endif %}
            {% if result.message and result.status.value != "passed" %}<br><em>{{ result.message }}</em>{% endif %}
        </li>
    {% endfor %}
    </ul>
</body>
</html>
"""