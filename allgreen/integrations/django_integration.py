"""
Django integration for allgreen health checks.

Setup:
    1. Add 'allgreen' to INSTALLED_APPS in settings.py:
        INSTALLED_APPS = [
            # ... other apps
            'allgreen',
        ]

    2. Create health checks in allgreen_config.py file in your project root
       Note: Use absolute imports only. Relative imports are not supported.

Usage:
    # In urls.py
    from allgreen.integrations import django_integration

    urlpatterns = [
        path('healthcheck/', django_integration.healthcheck_view, name='healthcheck'),
        path('metrics/', django_integration.metrics_view, name='metrics'),
    ]

    # Or use as class-based view
    urlpatterns = [
        path('healthcheck/', django_integration.HealthCheckView.as_view(), name='healthcheck'),
    ]
"""

from datetime import datetime

try:
    from django.http import HttpRequest, HttpResponse, JsonResponse
    from django.template.loader import render_to_string
    from django.utils.decorators import method_decorator
    from django.views import View
    from django.views.decorators.cache import never_cache
except ImportError:
    raise ImportError(
        "Django is required for django_integration. "
        "Install with: pip install allgreen[django]"
    ) from None

from ..config import load_config
from ..core import get_registry
from ..metrics import PROMETHEUS_CONTENT_TYPE, render_prometheus_metrics
from ..reporting import calculate_stats, format_json_response, get_overall_status


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
            environment=self.environment,
        )


@never_cache
def healthcheck_view(
    request: HttpRequest,
    app_name: str = "Django Application",
    config_path: str | None = None,
    environment: str | None = None,
) -> HttpResponse:
    """
    Django function-based view for health checks.

    Returns HTML or JSON based on Accept header or ?format parameter.
    HTTP status codes: 200 OK if all pass, 503 Service Unavailable if any fail.

    Args:
        request: Django HTTP request
        app_name: Application name to display
        config_path: Path to allgreen_config.py config file
        environment: Environment name (defaults to 'development')
    """

    # Load configuration and run checks
    if environment is None:
        environment = "development"

    load_config(config_path, environment)
    registry = get_registry()
    results = registry.run_all(environment)

    # Calculate statistics and overall status
    stats = calculate_stats(results)
    overall_status = get_overall_status(stats)

    # Determine response format
    wants_json = (
        "application/json" in request.headers.get("Accept", "")
        or request.GET.get("format") == "json"
    )

    # Determine HTTP status code
    status_code = 200 if overall_status == "passed" else 503

    if wants_json:
        # Return JSON response
        response = JsonResponse(
            format_json_response(results, stats, overall_status, app_name, environment),
            status=status_code,
        )
    else:
        # Return HTML response
        # Add formatted duration for template compatibility
        formatted_results = []
        for check, result in results:
            # Create a copy of result with formatted duration
            result_dict = {
                "status": result.status,
                "message": result.message,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "duration_formatted": f"{result.duration_ms:.1f}"
                if result.duration_ms is not None
                else None,
                "skip_reason": result.skip_reason,
            }
            formatted_results.append((check, type("Result", (), result_dict)()))

        context = {
            "results": formatted_results,
            "stats": stats,
            "overall_status": overall_status,
            "app_name": app_name,
            "environment": environment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        html_content = _render_html_template(context)
        response = HttpResponse(
            html_content, status=status_code, content_type="text/html"
        )

    # Add Cache-Control headers to prevent caching
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


def _render_html_template(context):
    """
    Render HTML template using Django's template system.

    Uses the shared template at allgreen/healthcheck.html.
    """
    return render_to_string("allgreen/healthcheck.html", context)


@never_cache
def metrics_view(
    request: HttpRequest,
    config_path: str | None = None,
    environment: str | None = None,
) -> HttpResponse:
    """
    Django view exposing check results as Prometheus metrics.

    Always returns 200 - health is conveyed via the allgreen_up metric.

    Usage:
        urlpatterns = [
            path('metrics/', django_integration.metrics_view, name='metrics'),
        ]
    """
    if environment is None:
        environment = "development"

    load_config(config_path, environment)
    results = get_registry().run_all(environment)

    response = HttpResponse(
        render_prometheus_metrics(results), content_type=PROMETHEUS_CONTENT_TYPE
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response
