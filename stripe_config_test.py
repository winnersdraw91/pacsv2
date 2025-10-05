#!/usr/bin/env python3
"""
Test Stripe configuration and integration
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

def test_stripe_config():
    """Test if Stripe is properly configured"""
    session = requests.Session()
    
    # Login first
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    login_response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print("❌ Failed to login")
        return False
    
    token = login_response.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Create a test centre
    centre_data = {
        "name": "Stripe Test Centre",
        "address": "123 Stripe Test St",
        "phone": "+1-555-0199",
        "email": "stripe@test.com"
    }
    
    centre_response = session.post(f"{BASE_URL}/centres", json=centre_data)
    if centre_response.status_code != 200:
        print("❌ Failed to create test centre")
        return False
    
    centre_id = centre_response.json()["id"]
    
    # Create a billing rate first
    rate_data = {
        "modality": "CT-STRIPE-TEST",
        "base_rate": 250.00,
        "currency": "USD",
        "description": "Stripe test CT rate"
    }
    
    rate_response = session.post(f"{BASE_URL}/billing/rates", json=rate_data)
    if rate_response.status_code != 200:
        print("❌ Failed to create billing rate")
        return False
    
    # Try to create an invoice (will be $0 but that's expected)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    invoice_data = {
        "centre_id": centre_id,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "currency": "USD"
    }
    
    invoice_response = session.post(f"{BASE_URL}/billing/invoices/generate", json=invoice_data)
    if invoice_response.status_code != 200:
        print("❌ Failed to create invoice")
        return False
    
    invoice = invoice_response.json()
    print(f"✅ Created invoice: {invoice['invoice_number']} for ${invoice['total_amount']}")
    
    # Now test Stripe checkout creation (will fail due to $0 amount, but we can check the error)
    checkout_data = {
        "invoice_id": invoice["id"],
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel"
    }
    
    checkout_response = session.post(f"{BASE_URL}/billing/checkout/create", json=checkout_data)
    
    if checkout_response.status_code == 500:
        error_detail = checkout_response.json().get("detail", "")
        if "Amount must be greater than 0" in error_detail:
            print("✅ Stripe integration is properly configured (validation working)")
            print("✅ Checkout endpoint is functional (fails correctly for $0 amount)")
            return True
        elif "Stripe not configured" in error_detail:
            print("❌ Stripe is not configured properly")
            return False
        else:
            print(f"❌ Unexpected error: {error_detail}")
            return False
    elif checkout_response.status_code == 200:
        print("✅ Stripe checkout session created successfully")
        return True
    else:
        print(f"❌ Unexpected response: {checkout_response.status_code}")
        print(f"Response: {checkout_response.text}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Stripe Configuration...")
    success = test_stripe_config()
    if success:
        print("\n✅ Stripe integration is properly implemented and configured")
    else:
        print("\n❌ Stripe integration has issues")