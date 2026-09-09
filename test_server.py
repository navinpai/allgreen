#!/usr/bin/env python3
"""
Simple test server for allgreen health checks.
"""

from allgreen import run_standalone

if __name__ == "__main__":
    print("🚀 Starting allgreen health check server...")
    print("📋 Config: examples/allgreen_config.py")
    print("🌐 URL: http://127.0.0.1:5000/healthcheck")
    print("🔧 Environment: development")
    print()

    run_standalone(
        app_name="Allgreen Test Server",
        config_path="examples/allgreen_config.py",
        environment="development",
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
