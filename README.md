# ✅ Allgreen - Python Health Checks Made Simple

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Add quick, simple, and beautiful health checks to your Python application via a `/healthcheck` endpoint.

Perfect for monitoring application health, smoke testing, and ensuring your services are running properly in production.

![Health Check Dashboard](https://via.placeholder.com/800x400/2d3748/e9ecef?text=Beautiful+Dark+Mode+Dashboard)

## 🚀 Features

- **🎯 Simple DSL** - Define health checks in intuitive, readable Python
- **🌐 Beautiful Web Dashboard** - Responsive UI with automatic dark mode
- **⚡ Fast & Lightweight** - Minimal dependencies, maximum performance  
- **⏰ Timeout Protection** - Prevent hanging checks with configurable timeouts
- **🔄 Rate Limiting** - Control expensive operations ("2 times per hour")
- **🌍 Environment Conditions** - Run checks only in specific environments
- **💾 Result Caching** - Cache expensive operations between rate-limited runs
- **📊 Multiple Output Formats** - HTML dashboard, JSON API, or both
- **🔧 Framework Agnostic** - Works with Flask, Django, FastAPI, or standalone

## 📦 Installation

```bash
pip install allgreen
```

## 🎯 Quick Start

### 1. Create your health checks

Create an `allgood.py` file in your project root:

```python
# allgood.py

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

### 2. Add to your web application

**Flask:**
```python
from flask import Flask
from allgreen import mount_healthcheck

app = Flask(__name__)
mount_healthcheck(app, app_name="My API")
```

**Django:** Add to `urls.py`
```python
from allgreen import create_app
from django.urls import path, include

healthcheck_app = create_app(app_name="My Django App")
urlpatterns = [
    path('healthcheck/', include(healthcheck_app)),
]
```

**Standalone:**
```python
from allgreen import run_standalone
run_standalone(app_name="My Service", port=8080)
```

### 3. View your dashboard

Visit `/healthcheck` in your browser to see a beautiful dashboard, or add `?format=json` for machine-readable output.

## 📚 Complete DSL Reference

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

## ⏰ Advanced Features

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
@check("Production database performance", only="production")
def prod_db_check():
    # Only runs in production environment
    expect(db.query_time()).to_be_less_than(10)

@check("Development tools available", except_env=["production", "staging"])
def dev_tools_check():
    # Skipped in production and staging
    make_sure(debug_tools.available())

@check("Conditional feature check", if_condition=lambda: feature_flag.enabled())
def feature_check():
    # Only runs when condition is true
    expect(new_feature.status()).to_eq("operational")
```

## 🌐 Web Interface

### HTML Dashboard
Visit `/healthcheck` for a beautiful, responsive dashboard featuring:
- ✅ Color-coded check results (pass/fail/skip)
- 🌙 Automatic dark mode based on system preferences
- ⏱️ Execution timing for each check
- 📊 Summary statistics
- 📱 Mobile-responsive design

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

## 🔧 Framework Integration

### Flask Application
```python
from flask import Flask
from allgreen import mount_healthcheck

app = Flask(__name__)

# Mount health checks
mount_healthcheck(
    app, 
    app_name="My Flask API",
    config_path="config/allgood.py",
    environment="production"
)

if __name__ == '__main__':
    app.run()
```

### Django Integration
```python
# health/urls.py
from allgreen import create_app

healthcheck_app = create_app(
    app_name="My Django App",
    config_path="myapp/health_checks.py"
)

# main/urls.py  
urlpatterns = [
    path('health/', include('health.urls')),
]
```

### FastAPI Integration
```python
from fastapi import FastAPI
from allgreen import create_app

app = FastAPI()
healthcheck_app = create_app(app_name="My FastAPI")

app.mount("/health", healthcheck_app)
```

### Standalone Server
```python
from allgreen import run_standalone

if __name__ == "__main__":
    run_standalone(
        app_name="Health Check Service",
        config_path="checks/allgood.py", 
        host="0.0.0.0",
        port=8080,
        environment="production"
    )
```

## 📁 Examples

Check out the `examples/` directory for complete working examples:

- **[`examples/allgood.py`](examples/allgood.py)** - Basic health checks
- **[`examples/advanced_allgood.py`](examples/advanced_allgood.py)** - Advanced features (timeouts, rate limiting)

## 🧪 Configuration File Locations

Allgreen automatically looks for configuration files in these locations:

1. `allgood.py` (project root)
2. `config/allgood.py`  
3. Custom path via `config_path` parameter

## 🎛️ Environment Variables

- `ENVIRONMENT` - Sets the environment for conditional checks (default: "development")

## 📊 Best Practices

### ✅ Good Health Check Examples

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

### ❌ What to Avoid

- Don't make checks that modify data
- Avoid checks that depend on external timing
- Don't put business logic in health checks
- Avoid checks that could cause cascading failures

## 🔒 Security Notes

- Health check endpoints don't require authentication by default
- Consider restricting access in production environments
- Avoid exposing sensitive system information in check descriptions
- Rate limiting helps prevent abuse of expensive operations

## 🛠️ Development

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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest`)
6. Run linting (`ruff check .`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the [Allgood Ruby gem](https://github.com/rameerez/allgood)
- Built with ❤️ for the Python community