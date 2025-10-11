#!/usr/bin/env python3
"""Test Django template discovery."""

import os
import django
from django.conf import settings

# Configure Django
if not settings.configured:
    settings.configure(
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {},
        }],
        INSTALLED_APPS=[
            'allgreen',  # Add allgreen as an app
        ]
    )
    django.setup()

def test_template_discovery():
    """Test that Django can find the allgreen template."""
    try:
        from django.template.loader import render_to_string
        
        context = {
            'results': [],
            'stats': {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0},
            'overall_status': 'passed',
            'app_name': 'Test App',
            'environment': 'test',
            'timestamp': '2024-01-01 12:00:00',
        }
        
        # This should find allgreen/templates/allgreen/healthcheck.html
        html = render_to_string('allgreen/healthcheck.html', context)
        
        if html and '<!DOCTYPE html>' in html:
            print("✅ Django template discovery working!")
            print(f"📄 Template length: {len(html)} characters")
            return True
        else:
            print("❌ Template rendered but seems empty")
            return False
            
    except Exception as e:
        print(f"❌ Django template discovery failed: {e}")
        return False

if __name__ == "__main__":
    success = test_template_discovery()
    exit(0 if success else 1)