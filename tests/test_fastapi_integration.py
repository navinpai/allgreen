import os
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from allgreen import get_registry
from allgreen.integrations.fastapi_integration import create_router


def _write_config(content: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        return f.name


def _make_client(config_path: str, **router_kwargs) -> TestClient:
    app = FastAPI()
    app.include_router(create_router(config_path=config_path, **router_kwargs))
    return TestClient(app)


def test_html_response_with_failure():
    get_registry().clear()
    config_path = _write_config("""
@check("FastAPI passing check")
def pass_check():
    make_sure(True)

@check("FastAPI failing check")
def fail_check():
    make_sure(False, "This should fail")
""")

    try:
        client = _make_client(config_path, app_name="FastAPI Test App")
        response = client.get("/healthcheck")

        assert response.status_code == 503
        assert "FastAPI passing check" in response.text
        assert "FastAPI failing check" in response.text
        assert (
            response.headers["cache-control"]
            == "no-store, no-cache, must-revalidate, max-age=0"
        )
    finally:
        os.unlink(config_path)


def test_json_endpoint():
    get_registry().clear()
    config_path = _write_config("""
@check("FastAPI JSON check")
def json_check():
    expect(2 + 2).to_eq(4)
""")

    try:
        client = _make_client(
            config_path, app_name="FastAPI JSON App", environment="test"
        )
        response = client.get("/healthcheck.json")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "passed"
        assert data["app_name"] == "FastAPI JSON App"
        assert data["environment"] == "test"
        assert len(data["checks"]) == 1
        assert data["checks"][0]["description"] == "FastAPI JSON check"
        assert data["checks"][0]["status"] == "passed"
    finally:
        os.unlink(config_path)


def test_json_via_format_param():
    get_registry().clear()
    config_path = _write_config("""
@check("Format param check")
def format_check():
    make_sure(True)
""")

    try:
        client = _make_client(config_path)
        response = client.get("/healthcheck?format=json")

        assert response.status_code == 200
        assert response.json()["status"] == "passed"
    finally:
        os.unlink(config_path)


def test_json_via_accept_header():
    get_registry().clear()
    config_path = _write_config("""
@check("Accept header check")
def header_check():
    make_sure(True)
""")

    try:
        client = _make_client(config_path)
        response = client.get("/healthcheck", headers={"Accept": "application/json"})

        assert response.status_code == 200
        assert response.json()["status"] == "passed"
    finally:
        os.unlink(config_path)


def test_router_with_prefix():
    get_registry().clear()
    config_path = _write_config("""
@check("Prefix check")
def prefix_check():
    make_sure(True)
""")

    try:
        app = FastAPI()
        app.include_router(create_router(config_path=config_path), prefix="/health")
        client = TestClient(app)

        response = client.get("/health/healthcheck?format=json")
        assert response.status_code == 200
        assert response.json()["status"] == "passed"
    finally:
        os.unlink(config_path)


def test_async_check():
    get_registry().clear()
    config_path = _write_config("""
import asyncio

@check("Async check via FastAPI")
async def async_check():
    await asyncio.sleep(0.01)
    make_sure(True)

@check("Sync check alongside async")
def sync_check():
    make_sure(True)
""")

    try:
        client = _make_client(config_path)
        response = client.get("/healthcheck.json")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "passed"
        assert data["stats"]["passed"] == 2
    finally:
        os.unlink(config_path)


def test_async_check_failure():
    get_registry().clear()
    config_path = _write_config("""
@check("Failing async check")
async def failing_async_check():
    make_sure(False, "Async check failed")
""")

    try:
        client = _make_client(config_path)
        response = client.get("/healthcheck.json")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "failed"
        assert "Async check failed" in data["checks"][0]["message"]
    finally:
        os.unlink(config_path)


def test_metrics_endpoint():
    get_registry().clear()
    config_path = _write_config("""
@check("Metrics passing check")
def pass_check():
    make_sure(True)

@check("Metrics failing check")
def fail_check():
    make_sure(False)
""")

    try:
        client = _make_client(config_path)
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "allgreen_up 0" in response.text
        assert 'allgreen_check_status{check="Metrics passing check"} 1' in response.text
        assert 'allgreen_check_status{check="Metrics failing check"} 0' in response.text
    finally:
        os.unlink(config_path)


def test_metrics_custom_path():
    get_registry().clear()
    config_path = _write_config("""
@check("Custom path check")
def pass_check():
    make_sure(True)
""")

    try:
        client = _make_client(config_path, metrics_path="/prometheus")

        assert client.get("/metrics").status_code == 404
        response = client.get("/prometheus")
        assert response.status_code == 200
        assert "allgreen_up 1" in response.text
    finally:
        os.unlink(config_path)


def test_metrics_disabled():
    get_registry().clear()
    config_path = _write_config("""
@check("No metrics check")
def pass_check():
    make_sure(True)
""")

    try:
        client = _make_client(config_path, metrics_path=None)
        assert client.get("/metrics").status_code == 404
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
        client = _make_client(config_path, environment="development")
        response = client.get("/healthcheck.json")

        data = response.json()
        assert data["stats"]["total"] == 3
        assert data["stats"]["passed"] == 1
        assert data["stats"]["failed"] == 1
        assert data["stats"]["skipped"] == 1
        assert data["status"] == "failed"
    finally:
        os.unlink(config_path)


def test_tracebacks_hidden_outside_development():
    get_registry().clear()
    config_path = _write_config("""
@check("Erroring check")
def erroring_check():
    raise ValueError("secret internals")
""")

    try:
        client = _make_client(config_path, environment="production")
        data = client.get("/healthcheck.json").json()

        assert data["checks"][0]["error"] == "ValueError: secret internals"
        assert data["checks"][0]["traceback"] is None

        html = client.get("/healthcheck").text
        assert "Traceback (most recent call last)" not in html
    finally:
        os.unlink(config_path)


def test_tracebacks_shown_in_development():
    get_registry().clear()
    config_path = _write_config("""
@check("Erroring check")
def erroring_check():
    raise ValueError("dev details")
""")

    try:
        client = _make_client(config_path, environment="development")
        data = client.get("/healthcheck.json").json()

        assert "Traceback (most recent call last)" in data["checks"][0]["traceback"]
    finally:
        os.unlink(config_path)
