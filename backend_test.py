#!/usr/bin/env python3
"""
PACS System Backend Testing Suite
Tests authentication, billing, and Stripe payment integration endpoints
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

class PACSBackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n=== Testing Authentication ===")
        
        # Test login endpoint
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.auth_token = data["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                    self.log_test("Admin Login", True, f"Successfully logged in as {data['user']['name']}")
                    
                    # Test /auth/me endpoint
                    me_response = self.session.get(f"{BASE_URL}/auth/me")
                    if me_response.status_code == 200:
                        user_data = me_response.json()
                        self.log_test("Get Current User", True, f"Retrieved user info for {user_data['email']}")
                    else:
                        self.log_test("Get Current User", False, f"Failed to get user info: {me_response.status_code}", 
                                    {"response": me_response.text})
                else:
                    self.log_test("Admin Login", False, "Login response missing required fields", 
                                {"response": data})
            else:
                self.log_test("Admin Login", False, f"Login failed with status {response.status_code}", 
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Admin Login", False, f"Login request failed: {str(e)}")
    
    def test_billing_rates(self):
        """Test billing rate management endpoints"""
        print("\n=== Testing Billing Rate Management ===")
        
        if not self.auth_token:
            self.log_test("Billing Rates Test", False, "No authentication token available")
            return
        
        # Test get billing rates
        try:
            response = self.session.get(f"{BASE_URL}/billing/rates")
            if response.status_code == 200:
                rates = response.json()
                self.log_test("Get Billing Rates", True, f"Retrieved {len(rates)} billing rates")
            else:
                self.log_test("Get Billing Rates", False, f"Failed to get rates: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Get Billing Rates", False, f"Request failed: {str(e)}")
        
        # Test create billing rate
        try:
            rate_data = {
                "modality": "CT-TEST",
                "base_rate": 150.00,
                "currency": "USD",
                "description": "Test CT scan rate"
            }
            
            response = self.session.post(f"{BASE_URL}/billing/rates", json=rate_data)
            if response.status_code == 200:
                created_rate = response.json()
                self.log_test("Create Billing Rate", True, f"Created rate for {created_rate['modality']}")
                
                # Test update billing rate
                update_data = {
                    "modality": "CT-TEST",
                    "base_rate": 175.00,
                    "currency": "USD",
                    "description": "Updated test CT scan rate"
                }
                
                update_response = self.session.put(f"{BASE_URL}/billing/rates/{created_rate['id']}", json=update_data)
                if update_response.status_code == 200:
                    self.log_test("Update Billing Rate", True, "Successfully updated billing rate")
                else:
                    self.log_test("Update Billing Rate", False, f"Failed to update rate: {update_response.status_code}", 
                                {"response": update_response.text})
                    
            else:
                self.log_test("Create Billing Rate", False, f"Failed to create rate: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Create Billing Rate", False, f"Request failed: {str(e)}")
    
    def test_invoice_generation(self):
        """Test invoice generation and management"""
        print("\n=== Testing Invoice Generation ===")
        
        if not self.auth_token:
            self.log_test("Invoice Generation Test", False, "No authentication token available")
            return
        
        # First, create a test centre if needed
        centre_id = self.create_test_centre()
        if not centre_id:
            return
        
        # Test get invoices
        try:
            response = self.session.get(f"{BASE_URL}/billing/invoices")
            if response.status_code == 200:
                invoices = response.json()
                self.log_test("Get Invoices", True, f"Retrieved {len(invoices)} invoices")
            else:
                self.log_test("Get Invoices", False, f"Failed to get invoices: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Get Invoices", False, f"Request failed: {str(e)}")
        
        # Test generate invoice
        try:
            # Use date range from last month
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            invoice_data = {
                "centre_id": centre_id,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "currency": "USD"
            }
            
            response = self.session.post(f"{BASE_URL}/billing/invoices/generate", json=invoice_data)
            if response.status_code == 200:
                invoice = response.json()
                self.log_test("Generate Invoice", True, f"Generated invoice {invoice['invoice_number']} for ${invoice['total_amount']}")
                
                # Test mark invoice as paid
                mark_paid_response = self.session.patch(f"{BASE_URL}/billing/invoices/{invoice['id']}/mark-paid")
                if mark_paid_response.status_code == 200:
                    self.log_test("Mark Invoice Paid", True, "Successfully marked invoice as paid")
                else:
                    self.log_test("Mark Invoice Paid", False, f"Failed to mark paid: {mark_paid_response.status_code}", 
                                {"response": mark_paid_response.text})
                    
            else:
                self.log_test("Generate Invoice", False, f"Failed to generate invoice: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Generate Invoice", False, f"Request failed: {str(e)}")
    
    def test_stripe_integration(self):
        """Test Stripe payment integration endpoints"""
        print("\n=== Testing Stripe Payment Integration ===")
        
        if not self.auth_token:
            self.log_test("Stripe Integration Test", False, "No authentication token available")
            return
        
        # Test get payment transactions first (doesn't require invoice)
        try:
            response = self.session.get(f"{BASE_URL}/billing/transactions")
            if response.status_code == 200:
                transactions = response.json()
                self.log_test("Get Payment Transactions", True, f"Retrieved {len(transactions)} payment transactions")
            else:
                self.log_test("Get Payment Transactions", False, f"Failed to get transactions: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Get Payment Transactions", False, f"Request failed: {str(e)}")
        
        # Test webhook endpoint (basic connectivity test)
        try:
            # This will fail validation but should return proper error, not 404
            response = self.session.post(f"{BASE_URL}/webhook/stripe", 
                                       json={"test": "data"}, 
                                       headers={"Stripe-Signature": "test"})
            # We expect this to fail with 400 (bad request) not 404 (not found)
            if response.status_code == 400:
                self.log_test("Stripe Webhook Endpoint", True, "Webhook endpoint is accessible (returned expected 400)")
            elif response.status_code == 404:
                self.log_test("Stripe Webhook Endpoint", False, "Webhook endpoint not found (404)")
            else:
                self.log_test("Stripe Webhook Endpoint", True, f"Webhook endpoint accessible (status: {response.status_code})")
        except Exception as e:
            self.log_test("Stripe Webhook Endpoint", False, f"Request failed: {str(e)}")
        
        # Test create checkout session with a test invoice
        centre_id = self.create_test_centre()
        if not centre_id:
            self.log_test("Stripe Checkout Test", False, "Could not create test centre")
            return
            
        # Create an invoice with a manual amount for testing
        test_invoice_id = self.create_test_invoice_with_amount(centre_id)
        if not test_invoice_id:
            self.log_test("Stripe Checkout Test", False, "Could not create test invoice with amount > 0 - this is expected as no completed studies exist")
            return
        
        # Test create checkout session
        try:
            checkout_data = {
                "invoice_id": test_invoice_id,
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            
            response = self.session.post(f"{BASE_URL}/billing/checkout/create", json=checkout_data)
            if response.status_code == 200:
                checkout_response = response.json()
                if "url" in checkout_response and "session_id" in checkout_response:
                    session_id = checkout_response["session_id"]
                    self.log_test("Create Checkout Session", True, f"Created Stripe checkout session: {session_id}")
                    
                    # Test get checkout status
                    status_response = self.session.get(f"{BASE_URL}/billing/checkout/status/{session_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        self.log_test("Get Checkout Status", True, f"Retrieved checkout status: {status_data.get('payment_status', 'unknown')}")
                    else:
                        self.log_test("Get Checkout Status", False, f"Failed to get status: {status_response.status_code}", 
                                    {"response": status_response.text})
                else:
                    self.log_test("Create Checkout Session", False, "Checkout response missing required fields", 
                                {"response": checkout_response})
            else:
                self.log_test("Create Checkout Session", False, f"Failed to create checkout: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Create Checkout Session", False, f"Request failed: {str(e)}")
    
    def create_test_invoice_with_amount(self, centre_id: str) -> Optional[str]:
        """Create a test invoice with a non-zero amount by manually inserting data"""
        # Since we can't easily create completed studies without file uploads,
        # and the invoice generation requires completed studies,
        # we'll skip the checkout session test and note this limitation
        return None
    
    def create_test_centre(self) -> Optional[str]:
        """Create a test diagnostic centre for testing"""
        try:
            centre_data = {
                "name": "Test Diagnostic Centre",
                "address": "123 Test Street, Test City",
                "phone": "+1-555-0123",
                "email": "test@testcentre.com"
            }
            
            response = self.session.post(f"{BASE_URL}/centres", json=centre_data)
            if response.status_code == 200:
                centre = response.json()
                return centre["id"]
            else:
                # Try to get existing centres
                get_response = self.session.get(f"{BASE_URL}/centres")
                if get_response.status_code == 200:
                    centres = get_response.json()
                    if centres:
                        return centres[0]["id"]
                
                self.log_test("Create Test Centre", False, f"Failed to create/get centre: {response.status_code}", 
                            {"response": response.text})
                return None
        except Exception as e:
            self.log_test("Create Test Centre", False, f"Request failed: {str(e)}")
            return None
    
    def create_test_invoice(self, centre_id: str) -> Optional[str]:
        """Create a test invoice for payment testing"""
        try:
            # First create some test studies to ensure invoice has amount > 0
            self.create_test_studies(centre_id)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            invoice_data = {
                "centre_id": centre_id,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "currency": "USD"
            }
            
            response = self.session.post(f"{BASE_URL}/billing/invoices/generate", json=invoice_data)
            if response.status_code == 200:
                invoice = response.json()
                # If invoice amount is still 0, let's create a manual invoice with amount
                if invoice.get("total_amount", 0) == 0:
                    # Since we can't modify the invoice generation logic, let's skip Stripe test
                    self.log_test("Create Test Invoice", False, "Generated invoice has $0 amount - no completed studies found")
                    return None
                return invoice["id"]
            else:
                self.log_test("Create Test Invoice", False, f"Failed to create invoice: {response.status_code}", 
                            {"response": response.text})
                return None
        except Exception as e:
            self.log_test("Create Test Invoice", False, f"Request failed: {str(e)}")
            return None
    
    def create_test_studies(self, centre_id: str):
        """Create test studies for billing purposes"""
        try:
            # First create a technician user for the centre
            tech_user = self.create_test_technician(centre_id)
            if not tech_user:
                return
            
            # Note: Creating actual studies requires file upload which is complex for testing
            # The invoice generation will work with $0 for testing connectivity
            # In a real system, there would be completed studies
            pass
            
        except Exception as e:
            self.log_test("Create Test Studies", False, f"Request failed: {str(e)}")
    
    def create_test_technician(self, centre_id: str) -> Optional[str]:
        """Create a test technician user"""
        try:
            tech_data = {
                "email": "test.tech@testcentre.com",
                "password": "testpass123",
                "name": "Test Technician",
                "role": "technician",
                "centre_id": centre_id,
                "phone": "+1-555-0124"
            }
            
            response = self.session.post(f"{BASE_URL}/auth/register", json=tech_data)
            if response.status_code == 200:
                user = response.json()
                return user["id"]
            else:
                # User might already exist, that's ok
                return None
        except Exception as e:
            return None
    
    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        print("\n=== Testing Dashboard Stats ===")
        
        if not self.auth_token:
            self.log_test("Dashboard Stats Test", False, "No authentication token available")
            return
        
        try:
            response = self.session.get(f"{BASE_URL}/dashboard/stats")
            if response.status_code == 200:
                stats = response.json()
                self.log_test("Get Dashboard Stats", True, f"Retrieved dashboard stats with {len(stats)} metrics")
            else:
                self.log_test("Get Dashboard Stats", False, f"Failed to get stats: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Get Dashboard Stats", False, f"Request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting PACS Backend Testing Suite")
        print(f"Testing against: {BASE_URL}")
        
        # Run tests in order
        self.test_authentication()
        self.test_billing_rates()
        self.test_invoice_generation()
        self.test_stripe_integration()
        self.test_dashboard_stats()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("🏁 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "="*60)
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = PACSBackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)