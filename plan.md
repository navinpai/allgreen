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

## 2025-10-11: Codebase Review and Recommendations

### Strengths
- **Simple DSL**: `@check`, `expect`, `make_sure` are ergonomic and readable.
- **Results model**: `CheckStatus`/`CheckResult` with timing and messages is solid.
- **Timeouts**: Sensible defaults; SIGALRM on main thread, fallback elsewhere.
- **Rate limiting**: Persistent, thread-safe tracker with cached results.
- **Web UI**: Polished template with light/dark mode and clear summaries.
- **Tests**: Good coverage for core, rate limiting, timeout, and Flask endpoints.

### Issues and improvements
- **Py 3.8 typing**: Replace PEP 585 generics like `tuple[...]` with `typing.Tuple[...]` to match declared support.
- **Timeout enforcement**: Threading fallback cannot interrupt blocking work. Consider executing checks in worker threads/processes and enforcing hard timeouts via `join(timeout)` or process boundaries; for FastAPI, avoid blocking the event loop.
- **Cached result semantics**: When rate-limited, returning `SKIPPED` loses original status. Either surface `cached_status`/`cached_result` explicitly or return the last status with a `cached=true` flag.
- **Packaging/templates**: Ensure `allgreen/templates/healthcheck.html` and integration modules are included in distributions (package_data/MANIFEST). Current recorded SOURCES omit them.
- **Version mismatch**: `pyproject.toml` is 0.2.0 while `allgreen.__init__.__version__` is 0.1.0. Unify or derive from package metadata.
- **Global registry concurrency**: `HealthCheckApp` may reload/clear the global registry while being read. Add a lock or snapshot checks per request when auto-reloading.
- **Rate-limit keying**: Cache key is the check description; namespace by `app_name`/`environment` or allow explicit IDs to avoid collisions.
- **Django inline template**: Fallback mixes Jinja-style blocks with Python `.format()` and will render incorrectly. Provide a real Django template `templates/allgreen/healthcheck.html` and remove the broken fallback.
- **Prefixes**: Flask `url_prefix` and FastAPI `prefix` parameters are accepted but unused; either wire them properly (Blueprint/router) or remove to prevent confusion.
- **Caching headers**: Add `Cache-Control: no-store, no-cache, must-revalidate` to Flask/FastAPI responses; decorate Django function view with `@never_cache`.
- **Async checks**: Consider supporting `async def` checks or running sync checks via threadpool in ASGI contexts.
- **Test gaps**: Add tests for Django/FastAPI integrations and for template packaging at runtime.

### Integration-specific notes
- **Flask**: Prefer a Blueprint honoring `url_prefix`; add no-cache headers; ensure templates are discoverable in packaged wheels.
- **Django**: Ship `templates/allgreen/healthcheck.html`; decorate function view with `@never_cache`; remove/better fallback rendering.
- **FastAPI**: Either use `prefix` or rely on `include_router(..., prefix=...)`; avoid blocking by running checks in a threadpool; reuse the shared HTML template for UI parity.

### Prioritized fixes
1. Replace PEP 585 generics for Python 3.8 compatibility.
2. Ship templates and integrations in the package; add MANIFEST/package_data.
3. Resolve version mismatch between `pyproject.toml` and `__init__.__version__`.
4. Make timeout enforcement robust via worker thread/process strategy.
5. Clarify cached-result semantics and rate-limit key namespacing.
6. Apply no-cache headers and wire `url_prefix`/`prefix` or remove.
7. Replace Django fallback with proper template; add decorators.
8. Add tests for Django/FastAPI and packaging of templates.

### Suitability
Overall, the design makes sense as a healthcheck library: approachable DSL, sound execution model, and useful web integrations. Addressing the timeout, packaging, and minor API inconsistencies will make it production-ready.