# ✅ Allgreen - Python Health Checks Made Simple

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Add quick, simple, and beautiful health checks to your Python application via a `/healthcheck` endpoint.

Perfect for monitoring application health, smoke testing, and ensuring your services are running properly in production.

![Health Check Dashboard](https://via.placeholder.com/800x400/2d3748/e9ecef?text=Beautiful+Dark+Mode+Dashboard)

## Features

- **Simple DSL** - Define health checks in intuitive, readable Python
- **Beautiful Web Dashboard** - Responsive UI with automatic dark mode
- **Fast & Lightweight** - Minimal dependencies, maximum performance  
- **Timeout Protection** - Prevent hanging checks with configurable timeouts
- **Rate Limiting** - Control expensive operations ("2 times per hour")
- **Environment Conditions** - Run checks only in specific environments
- **Result Caching** - Cache expensive operations between rate-limited runs
- **Multiple Output Formats** - HTML dashboard, JSON API, or both
- **Framework Agnostic** - Works with Flask, Django, FastAPI, or standalone

## 📦 Installation

Choose the installation that fits your needs:

```bash
# Core functionality only (no web dependencies)
pip install allgreen

# With Flask integration
pip install allgreen[flask]

# With Django integration  
pip install allgreen[django]

# With FastAPI integration
pip install allgreen[fastapi]
```

**Framework-agnostic design** - use only what you need!

## Quick Start

### 1. Create your health checks

Create an `allgreen_config.py` file in your project root:

> **Note**: Config files should use absolute imports only. Relative imports are not supported to avoid import conflicts.

```python
# allgreen_config.py

@check("Database connection is healthy")
def database_check():
    # Your database connection logic
    make_sure(db.is_connected(), "Database should be accessible")

@check("API response time is acceptable")
def api_performance_check():
    response_time = api.ping()
    expect(response_time).to_be_less_than(200)  # milliseconds

@check("Disk space is sufficient") 
def disk_space_check():
    usage_percent = get_disk_usage()
    expect(usage_percent).to_be_less_than(90)
```

### 2. Add to your application

**Core Only (no web framework):**
```python
from allgreen import get_registry, load_config

load_config()
results = get_registry().run_all()
# Process results as needed
```

**Flask Integration:**
```bash
pip install allgreen[flask]
```
```python
from flask import Flask
from allgreen.integrations.flask_integration import mount_healthcheck

app = Flask(__name__)
mount_healthcheck(app, app_name="My API")
```

**Django Integration:**
```bash
pip install allgreen[django]
```
```python
# urls.py
from django.urls import path
from allgreen.integrations.django_integration import healthcheck_view

urlpatterns = [
    path('healthcheck/', healthcheck_view, name='healthcheck'),
]
```

**FastAPI Integration:**
```bash
pip install allgreen[fastapi]
```
```python
from fastapi import FastAPI
from allgreen.integrations.fastapi_integration import create_router

app = FastAPI()
app.include_router(create_router(app_name="My API"))
```

### 3. View your dashboard

Visit `/healthcheck` in your browser to see a beautiful dashboard, or add `?format=json` for machine-readable output.

## Complete DSL Reference

### Basic Assertions

```python
@check("Basic truthiness check")
def basic_check():
    make_sure(True, "Custom failure message")
    make_sure(user.is_authenticated())
```

### Expectation Methods

```python
@check("Mathematical expectations")
def math_check():
    expect(2 + 2).to_eq(4)
    expect(api.response_time()).to_be_less_than(100)
    expect(database.connection_count()).to_be_greater_than(0)
```

## Advanced Features

### Timeout Protection

```python
@check("Slow external service", timeout=30)  # 30 seconds max
def external_service_check():
    # This check will be terminated if it takes longer than 30 seconds
    response = external_api.health_check()
    make_sure(response.ok)
```

### Rate Limiting for Expensive Operations

```python
@check("Expensive API call", run="2 times per hour", timeout=60)
def expensive_check():
    # This check only runs twice per hour, caching results between runs
    result = paid_api.run_diagnostics()
    expect(result.status).to_eq("healthy")

@check("Daily backup verification", run="1 time per day")
def daily_backup_check():
    # Perfect for expensive operations that should only run occasionally
    backup_status = verify_backup_integrity()
    make_sure(backup_status.valid)
```

**Supported rate limiting patterns:**
- `"1 time per minute"`
- `"5 times per hour"`  
- `"2 times per day"`

### Environment-Specific Checks

```python
@check("Production database performance", only_in="production")
def prod_db_check():
    # Only runs in production environment
    expect(db.query_time()).to_be_less_than(10)

@check("Development tools available", except_in=["production", "staging"])
def dev_tools_check():
    # Skipped in production and staging
    make_sure(debug_tools.available())

@check("Conditional feature check", if_condition=lambda: feature_flag.enabled())
def feature_check():
    # Only runs when condition is true
    expect(new_feature.status()).to_eq("operational")
```

## Web Interface

### HTML Dashboard
Visit `/healthcheck` for a beautiful, responsive dashboard featuring:
- Color-coded check results (pass/fail/skip)
- Automatic dark mode based on system preferences
- ⏱️ Execution timing for each check
- 📊 Summary statistics
- Mobile-responsive design

### JSON API
Access `/healthcheck.json` or `/healthcheck?format=json` for machine-readable output:

```json
{
  "status": "passed",
  "environment": "production", 
  "stats": {
    "total": 8,
    "passed": 6,
    "failed": 1,
    "skipped": 1
  },
  "checks": [
    {
      "description": "Database connection",
      "status": "passed",
      "duration_ms": 23.4
    }
  ]
}
```

### HTTP Status Codes
- **200 OK** - All checks passing
- **503 Service Unavailable** - One or more checks failing

Perfect for integration with monitoring tools like:
- UptimeRobot
- Pingdom  
- Datadog
- Custom monitoring solutions

## Framework Integration

### Flask Application
```python
from flask import Flask
from allgreen.integrations.flask_integration import mount_healthcheck

app = Flask(__name__)

# Mount health checks
mount_healthcheck(
    app, 
    app_name="My Flask API",
    config_path="config/allgreen_config.py",
    environment="production"
)

if __name__ == '__main__':
    app.run()
```

### Django Integration
```python
# urls.py
from django.urls import path
from allgreen.integrations.django_integration import healthcheck_view

urlpatterns = [
    path('healthcheck/', healthcheck_view, name='healthcheck'),
]

# For custom configuration
from allgreen.integrations.django_integration import create_healthcheck_view

custom_view = create_healthcheck_view(
    app_name="My Django App",
    config_path="myapp/health_checks.py",
    environment="production"
)

urlpatterns = [
    path('health/', custom_view, name='healthcheck'),
]
```

### FastAPI Integration
```python
from fastapi import FastAPI
from allgreen.integrations.fastapi_integration import create_router

app = FastAPI()

# Method 1: Mount router
health_router = create_router(
    app_name="My FastAPI",
    config_path="config/allgood.py"
)
app.include_router(health_router)

# Method 2: Individual endpoint
from allgreen.integrations.fastapi_integration import healthcheck_endpoint

@app.get("/healthcheck")
async def health(request: Request):
    return await healthcheck_endpoint(request, app_name="My FastAPI")
```

## Examples

Check out the `examples/` directory for complete working examples:

- **[`examples/allgreen_config.py`](examples/allgreen_config.py)** - Basic health checks configuration
- **[`examples/advanced_allgreen_config.py`](examples/advanced_allgreen_config.py)** - Advanced features (timeouts, rate limiting)
- **[`examples/core_only_example.py`](examples/core_only_example.py)** - Core-only usage (no web dependencies)
- **[`examples/flask_example.py`](examples/flask_example.py)** - Flask integration example
- **[`examples/django_example.py`](examples/django_example.py)** - Django integration example  
- **[`examples/fastapi_example.py`](examples/fastapi_example.py)** - FastAPI integration example

## Configuration File Locations

Allgreen automatically looks for configuration files in these locations:

1. `allgreen_config.py` (project root)
2. `config/allgreen_config.py`  
3. Custom path via `config_path` parameter

## Environment Variables

- `ENVIRONMENT` - Sets the environment for conditional checks (default: "development")

## Best Practices

### Good Health Check Examples

```python
@check("Database queries are fast")
def db_performance():
    start = time.time()
    users = User.objects.all()[:10] 
    duration = (time.time() - start) * 1000
    expect(duration).to_be_less_than(100)  # under 100ms

@check("External API is responsive")  
def api_health():
    response = requests.get("https://api.example.com/health", timeout=5)
    expect(response.status_code).to_eq(200)
    
@check("Cache is working", run="5 times per hour")
def cache_check():
    cache.set('test_key', 'test_value')
    expect(cache.get('test_key')).to_eq('test_value')
```

### What to Avoid

- Don't make checks that modify data
- Avoid checks that depend on external timing
- Don't put business logic in health checks
- Avoid checks that could cause cascading failures

## Security Notes

- Health check endpoints don't require authentication by default
- Consider restricting access in production environments
- Avoid exposing sensitive system information in check descriptions
- Rate limiting helps prevent abuse of expensive operations

## Development

```bash
git clone https://github.com/navinpai/allgreen
cd allgreen
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
python -m pytest

# Run linting  
ruff check .

# Start example server
python test_server.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest`)
6. Run linting (`ruff check .`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the [Allgood Ruby gem](https://github.com/rameerez/allgood)
- Built with ❤️ for the Python community