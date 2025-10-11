#!/usr/bin/env python3
"""
FastAPI integration example for allgreen health checks.

Install dependencies:
    pip install allgreen[fastapi]

Run:
    python examples/fastapi_example.py
    # Visit http://localhost:8000/healthcheck
    # Or try http://localhost:8000/docs for OpenAPI docs
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

from allgreen.integrations.fastapi_integration import create_router, healthcheck_endpoint

# Create FastAPI app
app = FastAPI(
    title="FastAPI + Allgreen Example",
    description="Example showing allgreen health checks with FastAPI",
    version="1.0.0"
)

# Basic route
@app.get("/", response_class=HTMLResponse)
async def index():
    return '''
    <h1>FastAPI + Allgreen Example</h1>
    <p><a href="/healthcheck">View Health Checks</a></p>
    <p><a href="/healthcheck.json">JSON API</a></p>
    <p><a href="/docs">OpenAPI Docs</a></p>
    '''

# Method 1: Mount the health check router
health_router = create_router(
    app_name="FastAPI Example App",
    config_path="examples/allgood.py",
    environment="development"
)
app.include_router(health_router)

# Method 2: Individual endpoint (alternative approach)
@app.get("/health")
async def health_check(request: Request):
    """Alternative health check endpoint using direct function call."""
    return await healthcheck_endpoint(
        request,
        app_name="FastAPI Direct Endpoint",
        config_path="examples/allgood.py",
        environment="development"
    )

if __name__ == '__main__':
    print("🚀 FastAPI + Allgreen Example")
    print("📋 Health checks: http://localhost:8000/healthcheck")
    print("🔧 JSON API: http://localhost:8000/healthcheck.json") 
    print("📚 OpenAPI docs: http://localhost:8000/docs")
    print("💡 Using config: examples/allgood.py")
    print()
    
    # Run with uvicorn
    uvicorn.run(
        "fastapi_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )