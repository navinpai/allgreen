#!/usr/bin/env python3
"""
Flask integration example for allgreen health checks.

Install dependencies:
    pip install allgreen[flask]

Run:
    python examples/flask_example.py
    # Visit http://localhost:5000/healthcheck
"""

from flask import Flask

from allgreen.integrations.flask_integration import mount_healthcheck

# Create Flask app
app = Flask(__name__)

# Basic route
@app.route('/')
def index():
    return '''
    <h1>Flask + Allgreen Example</h1>
    <p><a href="/healthcheck">View Health Checks</a></p>
    <p><a href="/healthcheck.json">JSON API</a></p>
    '''

# Mount health check routes
mount_healthcheck(
    app,
    app_name="Flask Example App",
    config_path="examples/allgreen.py",
    environment="development"
)

if __name__ == '__main__':
    print("🚀 Flask + Allgreen Example")
    print("📋 Health checks: http://localhost:5000/healthcheck")
    print("🔧 JSON API: http://localhost:5000/healthcheck.json")

    app.run(debug=True, port=5000)
