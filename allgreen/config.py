import logging
import os
import threading
from typing import Any

from .core import Check, expect, get_registry, make_sure

logger = logging.getLogger(__name__)

# Serializes config execution and guards the loaded-state cache so concurrent
# requests (e.g. Prometheus scrape + uptime ping) can't re-exec the config
# file simultaneously or observe a partially rebuilt registry.
_load_lock = threading.Lock()
_loaded_state: tuple[str, float, str] | None = None  # (path, mtime, environment)


class ConfigLoader:
    def __init__(self, config_path: str | None = None):
        self.config_path = config_path
        self._loaded_path: str | None = None

    def find_config_file(self) -> str | None:
        """Find allgreen_config.py configuration file in standard locations."""
        if self.config_path:
            if os.path.exists(self.config_path):
                return os.path.abspath(self.config_path)
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # Standard locations to check
        possible_paths = [
            "allgreen_config.py",
            "config/allgreen_config.py",
            os.path.join(os.getcwd(), "allgreen_config.py"),
            os.path.join(os.getcwd(), "config", "allgreen_config.py"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        return None

    def load_config(self, environment: str = "development") -> bool:
        """Load configuration file and execute it to register checks.

        The config is only (re-)executed when the file path, its mtime, or the
        environment changes; otherwise this is a cheap no-op. Checks are staged
        into a local list and swapped into the registry atomically, so a load
        error leaves the previously registered checks intact.
        """
        global _loaded_state

        try:
            config_file = self.find_config_file()
            if not config_file:
                return False
        except FileNotFoundError:
            return False

        try:
            mtime = os.path.getmtime(config_file)
        except OSError:
            return False

        with _load_lock:
            if (
                _loaded_state == (config_file, mtime, environment)
                and get_registry().get_checks()
            ):
                self._loaded_path = config_file
                return True

            staged: list[Check] = []

            def staging_check(description: str, *args: Any, **kwargs: Any):
                def decorator(func):
                    staged.append(Check(description, func, *args, **kwargs))
                    return func

                return decorator

            # Create a namespace with our DSL functions
            # Note: Config files should use absolute imports only.
            # Relative imports are not supported to avoid sys.path conflicts.
            namespace: dict[str, Any] = {
                "__file__": config_file,
                "__name__": "__main__",
                "check": staging_check,
                "expect": expect,
                "make_sure": make_sure,
                "ENVIRONMENT": environment,
            }

            try:
                with open(config_file) as f:
                    code = compile(f.read(), config_file, "exec")
                    exec(code, namespace)
            except Exception:
                logger.exception("Error loading config file %s", config_file)
                return False

            get_registry().replace(staged)
            _loaded_state = (config_file, mtime, environment)
            self._loaded_path = config_file
            return True

    @property
    def loaded_path(self) -> str | None:
        """Return the path of the currently loaded config file."""
        return self._loaded_path


def load_config(
    config_path: str | None = None, environment: str = "development"
) -> bool:
    """Convenience function to load configuration."""
    loader = ConfigLoader(config_path)
    return loader.load_config(environment)


def find_config() -> str | None:
    """Convenience function to find config file path."""
    loader = ConfigLoader(config_path=None)
    return loader.find_config_file()
