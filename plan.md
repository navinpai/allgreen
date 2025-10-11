# Plan for `allgreen` Python Library

## Overview
A Python clone of the Allgood Ruby gem for health checks, providing a simple DSL for defining health checks and a beautiful web interface for displaying results.

## 1. Package Structure
```
allgreen/
├── pyproject.toml          # Modern Python packaging
├── allgreen/
│   ├── __init__.py         # Main exports (check, expect functions)
│   ├── core.py             # Check, Expectation, CheckResult classes
│   ├── config.py           # Configuration loader for allgood.py
│   ├── web.py              # Flask/WSGI app for /healthcheck endpoint
│   ├── conditions.py       # Environment conditions (only, except, if)
│   ├── rate_limiting.py    # Rate limiting for expensive checks
│   └── templates/          # HTML templates for dashboard
│       └── healthcheck.html
├── tests/
├── examples/
│   └── allgood.py          # Sample configuration file
└── README.md
```

## 2. Core Components

### DSL Classes
- **`Check`**: Holds check description, function, conditions, timeout
- **`Expectation`**: Fluent interface for assertions (`expect(x).to_eq(y)`)
- **`CheckResult`**: Success/failure state with messages and timing
- **`CheckRegistry`**: Global registry of defined checks

### Configuration
- Load `allgood.py` or `config/allgood.py` files
- Execute Python code to register checks
- Support hot-reloading in development

### Web Interface
- Flask app serving `/healthcheck` endpoint
- Returns 200 for all passing, 503 for any failures
- Beautiful HTML dashboard with dark mode
- JSON API support for programmatic access

## 3. Key Features to Implement

### DSL Functions
```python
check("Database is accessible") 
make_sure(condition, message=None)
expect(actual).to_eq(expected)
expect(actual).to_be_greater_than(expected)
expect(actual).to_be_less_than(expected)
```

### Conditions
```python
check("...", only="production")
check("...", except="development") 
check("...", if_=lambda: condition)
check("...", timeout=30)
```

### Rate Limiting
```python
check("...", run="2 times per day")
check("...", run="4 times per hour")
```

## 4. Integration Options

### Framework Integration
- **Django**: Middleware or URL pattern
- **Flask**: Blueprint registration  
- **FastAPI**: Router mounting
- **Standalone WSGI app**

### Usage Pattern
```python
# In your app
from allgreen import mount_healthcheck
app = mount_healthcheck(app, config_path="allgood.py")

# Or standalone
from allgreen import create_app
healthcheck_app = create_app("allgood.py")
```

## 5. Implementation Priority

1. **Core DSL** - Basic check definition and execution
2. **Simple web interface** - Basic HTML output  
3. **Configuration loading** - File-based config
4. **Framework integration** - Flask/Django helpers
5. **Advanced features** - Conditions, rate limiting, timeouts
6. **Polish** - Beautiful UI, dark mode, comprehensive tests

## 6. Technical Decisions

### Dependencies
- **Flask** - Lightweight web framework for healthcheck endpoint
- **Jinja2** - Template engine for HTML dashboard
- **No heavy frameworks** - Keep it lightweight and framework-agnostic

### Configuration Format
- Python files (like Ruby's approach) for maximum flexibility
- Support both `allgood.py` and `config/allgood.py` locations
- Allow programmatic configuration for framework integration

### Error Handling
- Graceful degradation when checks fail
- Timeout protection for long-running checks
- Clear error messages and stack traces in development

### Performance
- Lazy loading of checks
- Concurrent execution of independent checks
- Caching of results for rate-limited checks