#!/usr/bin/env python3
"""
Additional PACS Backend Tests - Testing specific endpoints mentioned in review
"""

import requests
import json

BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

def test_specific_endpoints():
    """Test specific endpoints mentioned in the review request"""
    session = requests.Session()
    
    # Login
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    login_response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print("❌ Failed to login")
        return False
    
    token = login_response.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    print("🔍 Testing Specific Endpoints...")
    
    # Test the specific Stripe endpoints mentioned
    endpoints_to_test = [
        ("/billing/checkout/create", "POST", {"invoice_id": "test"}),
        ("/billing/checkout/status/test_session", "GET", None),
        ("/webhook/stripe", "POST", {"test": "data"}),
        ("/billing/rates", "GET", None),
        ("/billing/invoices", "GET", None),
        ("/billing/transactions", "GET", None),
        ("/dashboard/stats", "GET", None),
        ("/centres", "GET", None),
        ("/users", "GET", None)
    ]
    
    results = []
    
    for endpoint, method, data in endpoints_to_test:
        try:
            if method == "GET":
                response = session.get(f"{BASE_URL}{endpoint}")
            elif method == "POST":
                if endpoint == "/webhook/stripe":
                    # Special headers for webhook
                    response = session.post(f"{BASE_URL}{endpoint}", 
                                          json=data, 
                                          headers={"Stripe-Signature": "test"})
                else:
                    response = session.post(f"{BASE_URL}{endpoint}", json=data)
            
            # Determine if response is expected
            if endpoint == "/billing/checkout/create":
                # Should fail with 404 (invoice not found) or 500 (validation error)
                expected = response.status_code in [404, 500]
                status = "✅ PASS" if expected else "❌ FAIL"
                print(f"{status} {method} {endpoint}: {response.status_code} (expected 404/500)")
            elif endpoint == "/billing/checkout/status/test_session":
                # Should fail with 404 (session not found)
                expected = response.status_code == 404
                status = "✅ PASS" if expected else "❌ FAIL"
                print(f"{status} {method} {endpoint}: {response.status_code} (expected 404)")
            elif endpoint == "/webhook/stripe":
                # Should fail with 400 (bad signature/data)
                expected = response.status_code == 400
                status = "✅ PASS" if expected else "❌ FAIL"
                print(f"{status} {method} {endpoint}: {response.status_code} (expected 400)")
            else:
                # Should succeed with 200
                expected = response.status_code == 200
                status = "✅ PASS" if expected else "❌ FAIL"
                if expected:
                    data_len = len(response.json()) if isinstance(response.json(), list) else "object"
                    print(f"{status} {method} {endpoint}: {response.status_code} (returned {data_len})")
                else:
                    print(f"{status} {method} {endpoint}: {response.status_code} (expected 200)")
            
            results.append(expected)
            
        except Exception as e:
            print(f"❌ FAIL {method} {endpoint}: Exception - {str(e)}")
            results.append(False)
    
    success_rate = (sum(results) / len(results)) * 100
    print(f"\n📊 Additional Tests Summary: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
    
    return all(results)

if __name__ == "__main__":
    success = test_specific_endpoints()
    if success:
        print("✅ All additional endpoint tests passed")
    else:
        print("❌ Some additional endpoint tests failed")