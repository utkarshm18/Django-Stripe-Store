# How to Get Stripe Test Keys

## Step-by-Step Guide

### 1. Create a Stripe Account (Free)

1. Go to https://stripe.com/
2. Click "Sign up" (top right)
3. Create a free account (no credit card required for test mode)

### 2. Get Your Test API Keys

1. **Log in to Stripe Dashboard:**
   - Go to https://dashboard.stripe.com/login
   - Log in with your account

2. **Switch to Test Mode:**
   - Look at the top right of the dashboard
   - You should see a toggle that says "Test mode" or "Live mode"
   - Make sure it's set to **"Test mode"** (it should be gray/blue, not black)
   - If it says "Live mode", click it to switch to Test mode

3. **Get Your API Keys:**
   - In the left sidebar, click on **"Developers"**
   - Then click on **"API keys"**
   - You'll see two keys:
     - **Publishable key** (starts with `pk_test_...`)
     - **Secret key** (starts with `sk_test_...`)

4. **Copy the Keys:**
   - Click the "Reveal test key" button next to the Secret key to see it
   - Copy both keys

### 3. Set Up Your .env File

1. **Create a `.env` file** in your project root (same folder as `manage.py`)

2. **Copy the content from `.env.example`** and fill in your keys:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Settings
DB_NAME=stripe_db
DB_USER=postgres
DB_PASSWORD=utkarsh18
DB_HOST=localhost
DB_PORT=5432

# Stripe Settings (Test Mode)
STRIPE_PUBLISHABLE_KEY=pk_test_51ABC123...  # Paste your publishable key here
STRIPE_SECRET_KEY=sk_test_51XYZ789...       # Paste your secret key here
STRIPE_WEBHOOK_SECRET=                      # Leave empty for now (optional)
```

3. **Generate a Django Secret Key:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Copy the output and paste it as `SECRET_KEY` in your `.env` file

### 4. Verify Your Setup

1. Make sure your `.env` file is in the project root
2. Make sure the Stripe keys start with:
   - `pk_test_` for publishable key
   - `sk_test_` for secret key
3. Restart your Django server after creating/updating `.env`

## Quick Checklist

- [ ] Created Stripe account
- [ ] Switched to Test mode in Stripe dashboard
- [ ] Copied Publishable key (starts with `pk_test_`)
- [ ] Copied Secret key (starts with `sk_test_`)
- [ ] Created `.env` file in project root
- [ ] Added both keys to `.env` file
- [ ] Generated and added Django SECRET_KEY
- [ ] Restarted Django server

## Troubleshooting

### "Buy Now" button not working?

1. **Check browser console (F12):**
   - Look for JavaScript errors
   - Check if Stripe is loading: `Uncaught ReferenceError: Stripe is not defined`

2. **Check if Stripe keys are loaded:**
   - The publishable key should be visible in the page source
   - Check Network tab for failed requests to `/create-checkout-session/`

3. **Common issues:**
   - Missing `.env` file → Create it
   - Wrong key format → Make sure keys start with `pk_test_` and `sk_test_`
   - Server not restarted → Restart after adding `.env`
   - Keys in wrong mode → Make sure you're using TEST mode keys, not LIVE mode

### Still having issues?

1. Check the terminal where `runserver` is running for error messages
2. Make sure `python-dotenv` is installed: `pip install python-dotenv`
3. Verify your `.env` file is in the correct location (same folder as `manage.py`)

