from .config import ConfigLoader, find_config, load_config
from .core import (
    AllgreenError,
    Check,
    CheckAssertionError,
    CheckRegistry,
    CheckResult,
    CheckStatus,
    CheckTimeoutError,
    check,
    expect,
    get_registry,
    make_sure,
)

__version__ = "0.1.0"

# Core exports (always available)
__all__ = [
    "check",
    "expect",
    "make_sure",
    "get_registry",
    "CheckRegistry",
    "Check",
    "CheckResult",
    "CheckStatus",
    "AllgreenError",
    "CheckAssertionError",
    "CheckTimeoutError",
    "load_config",
    "find_config",
    "ConfigLoader",
]

# Try to import web framework integrations (optional)
try:
    from .integrations.flask_integration import HealthCheckApp, create_app, mount_healthcheck, run_standalone
    __all__.extend([
        "create_app",
        "mount_healthcheck", 
        "run_standalone",
        "HealthCheckApp",
    ])
except ImportError:
    pass

try:
    from .integrations import django_integration
    __all__.append("django_integration")
except ImportError:
    pass

try:
    from .integrations import fastapi_integration
    __all__.append("fastapi_integration")
except ImportError:
    pass
