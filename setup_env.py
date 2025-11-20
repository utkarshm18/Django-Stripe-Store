#!/usr/bin/env python
"""
Helper script to create .env file with Stripe keys.
Run this script and follow the prompts.
"""

import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key

def create_env_file():
    env_path = Path('.env')
    
    if env_path.exists():
        response = input('.env file already exists. Overwrite? (y/n): ')
        if response.lower() != 'y':
            print('Cancelled.')
            return
    
    print('\n=== Django Stripe Store - Environment Setup ===\n')
    print('You need to get your Stripe test keys from: https://dashboard.stripe.com/test/apikeys')
    print('Make sure you are in TEST MODE (toggle in top right of Stripe dashboard)\n')
    
    # Generate secret key
    secret_key = get_random_secret_key()
    print(f'Generated Django SECRET_KEY: {secret_key[:20]}...\n')
    
    # Get Stripe keys
    print('Enter your Stripe keys:')
    stripe_publishable = input('Stripe Publishable Key (pk_test_...): ').strip()
    stripe_secret = input('Stripe Secret Key (sk_test_...): ').strip()
    
    # Validate keys
    if not stripe_publishable.startswith('pk_test_'):
        print('WARNING: Publishable key should start with pk_test_')
    if not stripe_secret.startswith('sk_test_'):
        print('WARNING: Secret key should start with sk_test_')
    
    # Database settings
    print('\nDatabase settings (press Enter for defaults):')
    db_name = input('Database name [stripe_db]: ').strip() or 'stripe_db'
    db_user = input('Database user [postgres]: ').strip() or 'postgres'
    db_password = input('Database password [utkarsh18]: ').strip() or 'utkarsh18'
    db_host = input('Database host [localhost]: ').strip() or 'localhost'
    db_port = input('Database port [5432]: ').strip() or '5432'
    
    # Create .env content
    env_content = f"""# Django Settings
SECRET_KEY={secret_key}
DEBUG=True

# Database Settings
DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_HOST={db_host}
DB_PORT={db_port}

# Stripe Settings (Test Mode)
# Get these from: https://dashboard.stripe.com/test/apikeys
STRIPE_PUBLISHABLE_KEY={stripe_publishable}
STRIPE_SECRET_KEY={stripe_secret}
STRIPE_WEBHOOK_SECRET=
"""
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print('\n✅ .env file created successfully!')
    print('\nNext steps:')
    print('1. Run: python manage.py migrate')
    print('2. Run: python manage.py seed_products')
    print('3. Run: python manage.py runserver')
    print('4. Visit: http://127.0.0.1:8000/')

if __name__ == '__main__':
    try:
        create_env_file()
    except KeyboardInterrupt:
        print('\n\nCancelled.')
    except Exception as e:
        print(f'\nError: {e}')

