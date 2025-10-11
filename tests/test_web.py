import os
import tempfile

from allgreen import create_app, get_registry


def test_healthcheck_html_endpoint():
    # Clear registry and add a simple check
    registry = get_registry()
    registry.clear()

    # Create a temp config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("Test passing check")
def test_check():
    make_sure(True)

@check("Test failing check")
def fail_check():
    make_sure(False, "This should fail")
''')
        config_path = f.name

    try:
        # Create Flask app
        app = create_app(
            app_name="Test App",
            config_path=config_path,
            environment="test",
            auto_reload_config=False
        )

        client = app.test_client()

        # Test HTML endpoint
        response = client.get('/healthcheck')
        assert response.status_code == 503  # Should fail due to failing check
        assert b'Test passing check' in response.data
        assert b'Test failing check' in response.data
        assert b'Health Check' in response.data

    finally:
        os.unlink(config_path)


def test_healthcheck_json_endpoint():
    registry = get_registry()
    registry.clear()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("JSON test check")
def json_check():
    expect(2 + 2).to_eq(4)
''')
        config_path = f.name

    try:
        app = create_app(
            app_name="JSON Test App",
            config_path=config_path,
            environment="test"
        )

        client = app.test_client()

        # Test JSON endpoint
        response = client.get('/healthcheck.json')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert data['status'] == 'passed'
        assert data['app_name'] == 'JSON Test App'
        assert data['environment'] == 'test'
        assert len(data['checks']) == 1
        assert data['checks'][0]['description'] == 'JSON test check'
        assert data['checks'][0]['status'] == 'passed'

    finally:
        os.unlink(config_path)


def test_healthcheck_json_via_accept_header():
    registry = get_registry()
    registry.clear()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("Accept header test")
def header_test():
    make_sure(True)
''')
        config_path = f.name

    try:
        app = create_app(config_path=config_path)
        client = app.test_client()

        # Test with Accept: application/json header
        response = client.get(
            '/healthcheck',
            headers={'Accept': 'application/json'}
        )
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert data['status'] == 'passed'

    finally:
        os.unlink(config_path)


def test_healthcheck_format_parameter():
    registry = get_registry()
    registry.clear()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("Format param test")
def format_test():
    make_sure(True)
''')
        config_path = f.name

    try:
        app = create_app(config_path=config_path)
        client = app.test_client()

        # Test with ?format=json parameter
        response = client.get('/healthcheck?format=json')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    finally:
        os.unlink(config_path)


def test_healthcheck_statistics():
    registry = get_registry()
    registry.clear()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("Passing check")
def pass_check():
    make_sure(True)

@check("Failing check")
def fail_check():
    make_sure(False)

@check("Skipped check", only="production")
def skip_check():
    make_sure(True)
''')
        config_path = f.name

    try:
        app = create_app(
            config_path=config_path,
            environment="development"  # Will skip the production-only check
        )
        client = app.test_client()

        response = client.get('/healthcheck.json')
        data = response.get_json()

        assert data['stats']['total'] == 3
        assert data['stats']['passed'] == 1
        assert data['stats']['failed'] == 1
        assert data['stats']['skipped'] == 1
        assert data['status'] == 'failed'  # Overall status should be failed

    finally:
        os.unlink(config_path)
