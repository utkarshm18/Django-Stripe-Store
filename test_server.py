#!/usr/bin/env python
"""Test script to verify Django server can start"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stripe_app.settings')
django.setup()

from django.core.management import execute_from_command_line

print("Django configured successfully!")
print("Starting server...")
print("=" * 50)

# Try to run the server check first
try:
    from django.core.management import call_command
    call_command('check')
    print("\n✓ System check passed!")
except Exception as e:
    print(f"\n✗ System check failed: {e}")
    sys.exit(1)

print("\nTo start the server, run:")
print("  python manage.py runserver")
print("\nThen open: http://127.0.0.1:8000/")

