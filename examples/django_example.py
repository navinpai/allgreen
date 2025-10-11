#!/usr/bin/env python3
"""
Django integration example for allgreen health checks.

This is a minimal Django setup showing how to integrate allgreen.

Install dependencies:
    pip install allgreen[django]

Setup:
    1. Create a Django project: django-admin startproject myproject
    2. Add this code to your urls.py and views.py
    3. Or run this file directly for a minimal example

Run:
    python examples/django_example.py
    # Visit http://localhost:8000/healthcheck
"""

import os
import sys
from pathlib import Path

# Minimal Django setup for this example
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '__main__')

# Django settings (inline for this example)
DEBUG = True
SECRET_KEY = 'django-example-key-not-for-production'
ROOT_URLCONF = '__main__'
USE_TZ = True
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    },
]

if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.http import HttpResponse
    from django.urls import path
    from django.core.management import execute_from_command_line
    
    # Configure Django
    settings.configure(
        DEBUG=DEBUG,
        SECRET_KEY=SECRET_KEY,
        ROOT_URLCONF=ROOT_URLCONF,
        USE_TZ=USE_TZ,
        INSTALLED_APPS=INSTALLED_APPS,
        TEMPLATES=TEMPLATES,
    )
    django.setup()
    
    # Import after Django setup
    from allgreen.integrations.django_integration import healthcheck_view
    
    # Views
    def index(request):
        return HttpResponse('''
        <h1>Django + Allgreen Example</h1>
        <p><a href="/healthcheck/">View Health Checks</a></p>
        <p><a href="/healthcheck/?format=json">JSON API</a></p>
        ''')
    
    # URL patterns
    urlpatterns = [
        path('', index),
        path('healthcheck/', healthcheck_view, name='healthcheck'),
    ]
    
    print("🚀 Django + Allgreen Example")
    print("📋 Health checks: http://localhost:8000/healthcheck/")
    print("🔧 JSON API: http://localhost:8000/healthcheck/?format=json")
    print("💡 Using config: examples/allgood.py")
    print()
    
    # Run Django dev server
    execute_from_command_line(['manage.py', 'runserver', '8000'])