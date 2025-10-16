import os

from .core import get_registry


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
        """Load configuration file and execute it to register checks."""
        try:
            config_file = self.find_config_file()
            if not config_file:
                return False
        except FileNotFoundError:
            return False

        # Clear existing checks if reloading
        if self._loaded_path != config_file:
            get_registry().clear()

        try:
            # Import DSL functions locally to avoid circular imports
            from .core import check, expect, make_sure

            # Create a namespace with our DSL functions
            # Note: Config files should use absolute imports only.
            # Relative imports are not supported to avoid sys.path conflicts.
            namespace = {
                '__file__': config_file,
                '__name__': '__main__',
                'check': check,
                'expect': expect,
                'make_sure': make_sure,
                'ENVIRONMENT': environment,
            }

            # Execute the config file
            with open(config_file) as f:
                code = compile(f.read(), config_file, 'exec')
                exec(code, namespace)

            self._loaded_path = config_file
            return True

        except Exception as e:
            print(f"Error loading config file {config_file}: {e}")
            return False

    @property
    def loaded_path(self) -> str | None:
        """Return the path of the currently loaded config file."""
        return self._loaded_path


# Import these here to avoid circular imports


def load_config(config_path: str | None = None, environment: str = "development") -> bool:
    """Convenience function to load configuration."""
    loader = ConfigLoader(config_path)
    return loader.load_config(environment)


def find_config() -> str | None:
    """Convenience function to find config file path."""
    loader = ConfigLoader()
    return loader.find_config_file()
