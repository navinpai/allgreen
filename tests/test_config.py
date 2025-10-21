import os
import tempfile

from allgreen import find_config, get_registry, load_config


def test_find_config_file():
    # Test with a temporary config file
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "allgreen_config.py")
        with open(config_path, 'w') as f:
            f.write('# test config')

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            found_path = find_config()
            assert found_path is not None
            assert found_path.endswith("allgreen_config.py")
        finally:
            os.chdir(original_cwd)


def test_load_config_file():
    # Clear registry first
    registry = get_registry()
    registry.clear()

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("Test config check")
def test_check():
    make_sure(True)

@check("Math check from config")
def math_check():
    expect(5).to_be_greater_than(3)
''')
        config_path = f.name

    try:
        # Load the config
        success = load_config(config_path)
        assert success, "Config should load successfully"

        # Check that checks were registered
        checks = registry.get_checks()
        assert len(checks) == 2

        descriptions = [check.description for check in checks]
        assert "Test config check" in descriptions
        assert "Math check from config" in descriptions

        # Run the checks to make sure they work
        results = registry.run_all()
        assert len(results) == 2
        assert all(result.passed for _, result in results)

    finally:
        os.unlink(config_path)


def test_load_nonexistent_config():
    success = load_config("/nonexistent/path/allgreen_config.py")
    assert not success, "Should fail to load nonexistent config"


def test_config_with_environment_conditions():
    registry = get_registry()
    registry.clear()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
@check("Production only", only_in="production")
def prod_check():
    make_sure(True)

@check("Environment aware check")
def env_check():
    make_sure(ENVIRONMENT in ["development", "production"])
''')
        config_path = f.name

    try:
        # Load with development environment
        success = load_config(config_path, environment="development")
        assert success

        checks = registry.get_checks()
        assert len(checks) == 2

        # Run checks
        results = registry.run_all("development")

        # First check should be skipped (production only)
        assert results[0][1].skipped
        # Second check should pass
        assert results[1][1].passed

    finally:
        os.unlink(config_path)
