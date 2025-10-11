"""
Django integration for allgreen health checks.

Usage:
    # In views.py
    from allgreen.integrations import django_integration
    
    # Add to urlpatterns
    urlpatterns = [
        path('healthcheck/', django_integration.healthcheck_view, name='healthcheck'),
    ]

    # Or use as class-based view
    urlpatterns = [
        path('healthcheck/', django_integration.HealthCheckView.as_view(), name='healthcheck'),
    ]
"""

import json
from datetime import datetime
from typing import Optional

try:
    from django.http import HttpRequest, HttpResponse, JsonResponse
    from django.template.loader import render_to_string
    from django.views import View
    from django.utils.decorators import method_decorator
    from django.views.decorators.cache import never_cache
except ImportError:
    raise ImportError(
        "Django is required for django_integration. "
        "Install with: pip install allgreen[django]"
    )

from ..config import load_config
from ..core import CheckStatus, get_registry


class HealthCheckView(View):
    """
    Django class-based view for health checks.
    
    Usage:
        urlpatterns = [
            path('healthcheck/', HealthCheckView.as_view(), name='healthcheck'),
        ]
    """
    
    app_name = "Django Application"
    config_path = None
    environment = None
    
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request: HttpRequest) -> HttpResponse:
        return healthcheck_view(
            request,
            app_name=self.app_name,
            config_path=self.config_path,
            environment=self.environment
        )


def healthcheck_view(
    request: HttpRequest,
    app_name: str = "Django Application",
    config_path: Optional[str] = None,
    environment: Optional[str] = None
) -> HttpResponse:
    """
    Django function-based view for health checks.
    
    Returns HTML or JSON based on Accept header or ?format parameter.
    HTTP status codes: 200 OK if all pass, 503 Service Unavailable if any fail.
    
    Args:
        request: Django HTTP request
        app_name: Application name to display
        config_path: Path to allgood.py config file
        environment: Environment name (defaults to 'development')
    """
    
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
    wants_json = (
        'application/json' in request.headers.get('Accept', '') or
        request.GET.get('format') == 'json'
    )
    
    # Determine HTTP status code
    status_code = 200 if overall_status == "passed" else 503
    
    if wants_json:
        # Return JSON response
        return JsonResponse(
            _format_json_response(results, stats, overall_status, app_name, environment),
            status=status_code
        )
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
        return HttpResponse(html_content, status=status_code, content_type='text/html')


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
    """
    Render HTML template. 
    
    First tries to use Django template loader to find 'allgreen/healthcheck.html',
    falls back to inline template if not found.
    """
    try:
        # Try to use Django template
        return render_to_string('allgreen/healthcheck.html', context)
    except:
        # Fall back to inline template (same as Flask version)
        return _get_inline_template().format(**context)


def _get_inline_template():
    """Inline HTML template as fallback."""
    # This would contain the same HTML template as the Flask version
    # For brevity, returning a simple template here
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Health Check - {app_name}</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .skip {{ color: orange; }}
    </style>
</head>
<body>
    <h1>Health Check: {app_name}</h1>
    <p>Status: <strong>{overall_status}</strong></p>
    <p>Environment: {environment}</p>
    <p>Timestamp: {timestamp}</p>
    
    <h2>Results</h2>
    <ul>
    {% for check, result in results %}
        <li class="{result.status.value}">
            {check.description}: {result.status.value}
            {% if result.skip_reason %} - {result.skip_reason}{% endif %}
            {% if result.message and result.status.value != "passed" %} - {result.message}{% endif %}
        </li>
    {% endfor %}
    </ul>
</body>
</html>
"""