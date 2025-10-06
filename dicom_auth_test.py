#!/usr/bin/env python3
"""
DICOM Authentication and File Serving Test
Focused test for Study OR2UUPB5 authentication and DICOM file access
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"
TARGET_STUDY_ID = "OR2UUPB5"

class DicomAuthTester:
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
    
    def test_admin_login(self):
        """Test admin login and get JWT token"""
        print("\n=== PRIORITY 1: Testing Admin Authentication ===")
        
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
                    user_info = data["user"]
                    self.log_test("Admin Login", True, 
                                f"Successfully authenticated as {user_info['name']} ({user_info['email']}) with role {user_info['role']}")
                    
                    # Verify token format
                    if len(self.auth_token) > 50:  # JWT tokens are typically long
                        self.log_test("JWT Token Format", True, f"Valid JWT token received (length: {len(self.auth_token)})")
                    else:
                        self.log_test("JWT Token Format", False, f"Token seems too short: {len(self.auth_token)}")
                    
                    return True
                else:
                    self.log_test("Admin Login", False, "Login response missing required fields", 
                                {"response": data})
                    return False
            else:
                self.log_test("Admin Login", False, f"Login failed with status {response.status_code}", 
                            {"response": response.text})
                return False
                
        except Exception as e:
            self.log_test("Admin Login", False, f"Login request failed: {str(e)}")
            return False
    
    def test_study_access(self):
        """Test Study OR2UUPB5 access with proper Authorization header"""
        print(f"\n=== PRIORITY 2: Testing Study {TARGET_STUDY_ID} Access ===")
        
        if not self.auth_token:
            self.log_test("Study Access Test", False, "No authentication token available")
            return None
        
        try:
            # Test study access with authentication
            response = self.session.get(f"{BASE_URL}/studies/{TARGET_STUDY_ID}")
            
            if response.status_code == 200:
                study_data = response.json()
                self.log_test("Study Access", True, 
                            f"Successfully accessed Study {TARGET_STUDY_ID} - Patient: {study_data.get('patient_name', 'Unknown')}")
                
                # Verify study data structure
                required_fields = ['id', 'study_id', 'patient_name', 'file_ids']
                missing_fields = [field for field in required_fields if field not in study_data]
                
                if not missing_fields:
                    file_count = len(study_data.get('file_ids', []))
                    self.log_test("Study Data Structure", True, 
                                f"Study contains all required fields with {file_count} DICOM files")
                    
                    # Log study details
                    print(f"   📋 Study Details:")
                    print(f"      - Study ID: {study_data.get('study_id')}")
                    print(f"      - Patient: {study_data.get('patient_name')}")
                    print(f"      - Age: {study_data.get('patient_age')}")
                    print(f"      - Gender: {study_data.get('patient_gender')}")
                    print(f"      - Modality: {study_data.get('modality')}")
                    print(f"      - Status: {study_data.get('status')}")
                    print(f"      - File Count: {file_count}")
                    
                    return study_data
                else:
                    self.log_test("Study Data Structure", False, f"Missing required fields: {missing_fields}")
                    return study_data
                    
            elif response.status_code == 401:
                self.log_test("Study Access", False, "Authentication failed (401) - JWT token invalid")
                return None
            elif response.status_code == 403:
                self.log_test("Study Access", False, "Access forbidden (403) - insufficient permissions")
                return None
            elif response.status_code == 404:
                self.log_test("Study Access", False, f"Study {TARGET_STUDY_ID} not found (404)")
                return None
            else:
                self.log_test("Study Access", False, f"Unexpected response: {response.status_code}", 
                            {"response": response.text})
                return None
                
        except Exception as e:
            self.log_test("Study Access", False, f"Request failed: {str(e)}")
            return None
    
    def test_dicom_file_download(self, study_data):
        """Test first DICOM file download from Study OR2UUPB5 with auth"""
        print(f"\n=== PRIORITY 3: Testing DICOM File Download ===")
        
        if not study_data or not study_data.get('file_ids'):
            self.log_test("DICOM File Download", False, "No file IDs available in study data")
            return None
        
        file_ids = study_data['file_ids']
        first_file_id = file_ids[0]
        
        try:
            # Test DICOM file download with authentication
            response = self.session.get(f"{BASE_URL}/files/{first_file_id}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                
                self.log_test("DICOM File Download", True, 
                            f"Successfully downloaded file {first_file_id} ({content_length} bytes)")
                
                # Verify content type
                if content_type == 'application/dicom':
                    self.log_test("DICOM Content Type", True, f"Correct content-type: {content_type}")
                else:
                    self.log_test("DICOM Content Type", False, f"Unexpected content-type: {content_type}")
                
                # Log download details
                print(f"   📁 File Details:")
                print(f"      - File ID: {first_file_id}")
                print(f"      - Content-Type: {content_type}")
                print(f"      - Size: {content_length} bytes ({content_length/1024:.1f} KB)")
                
                return response.content
                
            elif response.status_code == 401:
                self.log_test("DICOM File Download", False, "Authentication failed (401) - JWT token invalid")
                return None
            elif response.status_code == 403:
                self.log_test("DICOM File Download", False, "Access forbidden (403) - insufficient permissions")
                return None
            elif response.status_code == 404:
                self.log_test("DICOM File Download", False, f"File {first_file_id} not found (404)")
                return None
            else:
                self.log_test("DICOM File Download", False, f"Unexpected response: {response.status_code}", 
                            {"response": response.text})
                return None
                
        except Exception as e:
            self.log_test("DICOM File Download", False, f"Request failed: {str(e)}")
            return None
    
    def verify_dicom_content(self, file_content):
        """Verify file content - should be valid DICOM with proper headers"""
        print(f"\n=== PRIORITY 4: Verifying DICOM File Content ===")
        
        if not file_content:
            self.log_test("DICOM Content Verification", False, "No file content to verify")
            return False
        
        try:
            # Check DICOM file signature
            if len(file_content) < 132:
                self.log_test("DICOM File Size", False, f"File too small ({len(file_content)} bytes) - not a valid DICOM")
                return False
            
            # DICOM files should have 'DICM' at offset 128
            dicom_signature = file_content[128:132]
            
            if dicom_signature == b'DICM':
                self.log_test("DICOM Signature", True, "Valid DICOM signature found at offset 128")
                
                # Check for additional DICOM markers
                has_dicom_elements = b'\x08\x00' in file_content[:200]  # Group 0008 elements
                if has_dicom_elements:
                    self.log_test("DICOM Elements", True, "DICOM data elements detected in file")
                else:
                    self.log_test("DICOM Elements", False, "No DICOM data elements found")
                
                # File size validation
                if len(file_content) > 1000:  # Reasonable minimum for medical DICOM
                    self.log_test("DICOM File Size", True, f"Reasonable file size: {len(file_content)} bytes")
                else:
                    self.log_test("DICOM File Size", False, f"File seems too small: {len(file_content)} bytes")
                
                # Log content analysis
                print(f"   🔍 Content Analysis:")
                print(f"      - File Size: {len(file_content)} bytes ({len(file_content)/1024:.1f} KB)")
                print(f"      - DICOM Signature: {dicom_signature}")
                print(f"      - First 16 bytes: {file_content[:16].hex()}")
                print(f"      - Bytes 128-144: {file_content[128:144].hex()}")
                
                return True
            else:
                self.log_test("DICOM Signature", False, f"Invalid DICOM signature: {dicom_signature} (expected b'DICM')")
                print(f"   🔍 Found at offset 128: {dicom_signature}")
                print(f"   🔍 First 16 bytes: {file_content[:16].hex()}")
                return False
                
        except Exception as e:
            self.log_test("DICOM Content Verification", False, f"Content verification failed: {str(e)}")
            return False
    
    def test_authentication_edge_cases(self):
        """Test authentication edge cases"""
        print(f"\n=== BONUS: Testing Authentication Edge Cases ===")
        
        # Test access without authentication
        try:
            temp_session = requests.Session()  # No auth headers
            response = temp_session.get(f"{BASE_URL}/studies/{TARGET_STUDY_ID}")
            
            if response.status_code == 401:
                self.log_test("Unauthenticated Access", True, "Correctly denied access without authentication (401)")
            elif response.status_code == 403:
                self.log_test("Unauthenticated Access", True, "Correctly denied access without authentication (403)")
            else:
                self.log_test("Unauthenticated Access", False, f"Unexpected response without auth: {response.status_code}")
                
        except Exception as e:
            self.log_test("Unauthenticated Access", False, f"Request failed: {str(e)}")
        
        # Test access with invalid token
        try:
            temp_session = requests.Session()
            temp_session.headers.update({"Authorization": "Bearer invalid_token_12345"})
            response = temp_session.get(f"{BASE_URL}/studies/{TARGET_STUDY_ID}")
            
            if response.status_code == 401:
                self.log_test("Invalid Token Access", True, "Correctly denied access with invalid token (401)")
            elif response.status_code == 403:
                self.log_test("Invalid Token Access", True, "Correctly denied access with invalid token (403)")
            else:
                self.log_test("Invalid Token Access", False, f"Unexpected response with invalid token: {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid Token Access", False, f"Request failed: {str(e)}")
    
    def run_focused_test(self):
        """Run the focused authentication and DICOM file serving test"""
        print("🎯 Starting Focused DICOM Authentication & File Serving Test")
        print(f"Target: Study {TARGET_STUDY_ID}")
        print(f"Backend: {BASE_URL}")
        print("="*70)
        
        # Step 1: Test admin login and get JWT token
        if not self.test_admin_login():
            print("\n❌ CRITICAL: Authentication failed - cannot proceed with file tests")
            self.print_summary()
            return False
        
        # Step 2: Test Study OR2UUPB5 access with proper Authorization header
        study_data = self.test_study_access()
        if not study_data:
            print(f"\n❌ CRITICAL: Cannot access Study {TARGET_STUDY_ID} - cannot proceed with file tests")
            self.print_summary()
            return False
        
        # Step 3: Test first DICOM file download from Study OR2UUPB5 with auth
        file_content = self.test_dicom_file_download(study_data)
        if not file_content:
            print(f"\n❌ CRITICAL: Cannot download DICOM files from Study {TARGET_STUDY_ID}")
            self.print_summary()
            return False
        
        # Step 4: Verify file content - should be valid DICOM with proper headers
        dicom_valid = self.verify_dicom_content(file_content)
        if not dicom_valid:
            print(f"\n⚠️  WARNING: Downloaded file may not be valid DICOM format")
        
        # Bonus: Test authentication edge cases
        self.test_authentication_edge_cases()
        
        # Print summary
        success = self.print_summary()
        return success
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("🏁 FOCUSED TEST SUMMARY")
        print("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results
        critical_tests = ["Admin Login", "Study Access", "DICOM File Download"]
        critical_failures = [r for r in self.test_results if not r["success"] and r["test"] in critical_tests]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL FAILURES ({len(critical_failures)}):")
            for result in critical_failures:
                print(f"  ❌ {result['test']}: {result['message']}")
        
        if failed_tests > 0 and not critical_failures:
            print(f"\n⚠️  NON-CRITICAL ISSUES ({failed_tests}):")
            for result in self.test_results:
                if not result["success"] and result["test"] not in critical_tests:
                    print(f"  ⚠️  {result['test']}: {result['message']}")
        
        # Final assessment
        if not critical_failures:
            print(f"\n✅ CONCLUSION: Backend authentication and DICOM file serving for Study {TARGET_STUDY_ID} is WORKING")
            print("   The issue with blank images in DICOM viewer is NOT in the backend data pipeline.")
            print("   Focus should be on frontend JavaScript canvas rendering code.")
        else:
            print(f"\n❌ CONCLUSION: Backend has critical issues that need to be resolved")
        
        print("="*70)
        
        return len(critical_failures) == 0

if __name__ == "__main__":
    tester = DicomAuthTester()
    success = tester.run_focused_test()
    sys.exit(0 if success else 1)