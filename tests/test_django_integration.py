import json
import os
import tempfile

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        ALLOWED_HOSTS=["*"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {},
            }
        ],
        INSTALLED_APPS=["allgreen"],
    )
    django.setup()

from django.test import RequestFactory  # noqa: E402

from allgreen import get_registry  # noqa: E402
from allgreen.integrations.django_integration import (  # noqa: E402
    HealthCheckView,
    healthcheck_view,
)


def _write_config(content: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        return f.name


def test_html_response_with_failure():
    get_registry().clear()
    config_path = _write_config("""
@check("Django passing check")
def pass_check():
    make_sure(True)

@check("Django failing check")
def fail_check():
    make_sure(False, "This should fail")
""")

    try:
        request = RequestFactory().get("/healthcheck/")
        response = healthcheck_view(
            request, app_name="Django Test App", config_path=config_path
        )

        assert response.status_code == 503
        content = response.content.decode()
        assert "Django passing check" in content
        assert "Django failing check" in content
        # @never_cache appends extra directives (e.g. "private"), so check inclusion
        assert "no-store" in response["Cache-Control"]
        assert "no-cache" in response["Cache-Control"]
    finally:
        os.unlink(config_path)


def test_json_response_via_format_param():
    get_registry().clear()
    config_path = _write_config("""
@check("Django JSON check")
def json_check():
    expect(2 + 2).to_eq(4)
""")

    try:
        request = RequestFactory().get("/healthcheck/?format=json")
        response = healthcheck_view(
            request,
            app_name="Django JSON App",
            config_path=config_path,
            environment="test",
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

        data = json.loads(response.content)
        assert data["status"] == "passed"
        assert data["app_name"] == "Django JSON App"
        assert data["environment"] == "test"
        assert len(data["checks"]) == 1
        assert data["checks"][0]["description"] == "Django JSON check"
        assert data["checks"][0]["status"] == "passed"
    finally:
        os.unlink(config_path)


def test_json_response_via_accept_header():
    get_registry().clear()
    config_path = _write_config("""
@check("Accept header check")
def header_check():
    make_sure(True)
""")

    try:
        request = RequestFactory().get("/healthcheck/", HTTP_ACCEPT="application/json")
        response = healthcheck_view(request, config_path=config_path)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "passed"
    finally:
        os.unlink(config_path)


def test_class_based_view():
    get_registry().clear()
    config_path = _write_config("""
@check("CBV check")
def cbv_check():
    make_sure(True)
""")

    try:

        class TestHealthCheckView(HealthCheckView):
            app_name = "CBV App"

        TestHealthCheckView.config_path = config_path

        request = RequestFactory().get("/healthcheck/?format=json")
        response = TestHealthCheckView.as_view()(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["app_name"] == "CBV App"
    finally:
        os.unlink(config_path)


def test_statistics():
    get_registry().clear()
    config_path = _write_config("""
@check("Passing check")
def pass_check():
    make_sure(True)

@check("Failing check")
def fail_check():
    make_sure(False)

@check("Skipped check", only_in="production")
def skip_check():
    make_sure(True)
""")

    try:
        request = RequestFactory().get("/healthcheck/?format=json")
        response = healthcheck_view(
            request, config_path=config_path, environment="development"
        )

        data = json.loads(response.content)
        assert data["stats"]["total"] == 3
        assert data["stats"]["passed"] == 1
        assert data["stats"]["failed"] == 1
        assert data["stats"]["skipped"] == 1
        assert data["status"] == "failed"
    finally:
        os.unlink(config_path)


def test_async_check():
    get_registry().clear()
    config_path = _write_config("""
import asyncio

@check("Async check via Django")
async def async_check():
    await asyncio.sleep(0.01)
    make_sure(True)

@check("Sync check alongside async")
def sync_check():
    make_sure(True)
""")

    try:
        request = RequestFactory().get("/healthcheck/?format=json")
        response = healthcheck_view(request, config_path=config_path)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "passed"
        assert data["stats"]["passed"] == 2
    finally:
        os.unlink(config_path)


def test_template_discovery():
    """Django's app template loader should find allgreen/healthcheck.html."""
    from django.template.loader import render_to_string

    context = {
        "results": [],
        "stats": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        "overall_status": "passed",
        "app_name": "Test App",
        "environment": "test",
        "timestamp": "2024-01-01 12:00:00",
    }

    html = render_to_string("allgreen/healthcheck.html", context)
    assert "<!DOCTYPE html>" in html
