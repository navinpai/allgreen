#!/usr/bin/env python3
"""Standalone demo server for trying the allgreen dashboard locally."""

from pathlib import Path

from allgreen import run_standalone

if __name__ == "__main__":
    config_path = Path(__file__).parent / "allgreen_config.py"

    print("Starting allgreen health check server...")
    print(f"Config: {config_path}")
    print("URL: http://127.0.0.1:5000/healthcheck")
    print()

    run_standalone(
        app_name="Allgreen Demo Server",
        config_path=str(config_path),
        environment="development",
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
