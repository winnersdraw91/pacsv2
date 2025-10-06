#!/usr/bin/env python3
"""
PACS System Study OR2UUPB5 Debug Test
Quick verification of Study OR2UUPB5 access and exact study_id format
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

class StudyOR2UUPB5Tester:
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
        if details:
            print(f"   Details: {json.dumps(details, indent=2, default=str)}")
    
    def authenticate(self):
        """Authenticate as admin user"""
        print("\n=== Authentication ===")
        
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
                    self.log_test("Admin Authentication", True, f"Successfully logged in as {data['user']['name']}")
                    return True
                else:
                    self.log_test("Admin Authentication", False, "Login response missing required fields", 
                                {"response": data})
                    return False
            else:
                self.log_test("Admin Authentication", False, f"Login failed with status {response.status_code}", 
                            {"response": response.text})
                return False
                
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Login request failed: {str(e)}")
            return False
    
    def test_study_or2uupb5_access(self):
        """Test GET /api/studies/OR2UUPB5 to verify exact study data format"""
        print("\n=== Testing Study OR2UUPB5 Access ===")
        
        if not self.auth_token:
            self.log_test("Study OR2UUPB5 Access", False, "No authentication token available")
            return None
        
        try:
            response = self.session.get(f"{BASE_URL}/studies/OR2UUPB5")
            
            if response.status_code == 200:
                study_data = response.json()
                
                # Extract key information
                study_info = {
                    "study.id": study_data.get("id"),
                    "study.study_id": study_data.get("study_id"),
                    "patient_name": study_data.get("patient_name"),
                    "file_ids_count": len(study_data.get("file_ids", [])),
                    "first_5_file_ids": study_data.get("file_ids", [])[:5],
                    "modality": study_data.get("modality"),
                    "status": study_data.get("status")
                }
                
                self.log_test("Study OR2UUPB5 Access", True, 
                            f"Successfully retrieved study data for patient '{study_data.get('patient_name')}'", 
                            study_info)
                
                # Verify patient name is "reema"
                if study_data.get("patient_name", "").lower() == "reema":
                    self.log_test("Patient Name Verification", True, "Confirmed patient name is 'reema'")
                else:
                    self.log_test("Patient Name Verification", False, 
                                f"Expected patient name 'reema', got '{study_data.get('patient_name')}'")
                
                return study_data
                
            elif response.status_code == 404:
                self.log_test("Study OR2UUPB5 Access", False, "Study OR2UUPB5 not found (404)")
                return None
            else:
                self.log_test("Study OR2UUPB5 Access", False, 
                            f"Failed to retrieve study: {response.status_code}", 
                            {"response": response.text})
                return None
                
        except Exception as e:
            self.log_test("Study OR2UUPB5 Access", False, f"Request failed: {str(e)}")
            return None
    
    def test_file_access(self, file_ids):
        """Test direct file access for the first few file_ids"""
        print("\n=== Testing Direct File Access ===")
        
        if not file_ids:
            self.log_test("File Access Test", False, "No file_ids provided")
            return
        
        # Test first 3 files to verify they're valid MongoDB ObjectIds and accessible
        test_files = file_ids[:3]
        
        for i, file_id in enumerate(test_files):
            try:
                response = self.session.get(f"{BASE_URL}/files/{file_id}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    content_length = len(response.content)
                    
                    # Check if it's a valid DICOM file
                    is_dicom = content_type == 'application/dicom'
                    has_dicom_header = response.content[:4] == b'DICM' if len(response.content) >= 132 else False
                    
                    # Check DICOM header at offset 128
                    if len(response.content) >= 132:
                        has_dicom_header = response.content[128:132] == b'DICM'
                    
                    file_info = {
                        "file_id": file_id,
                        "content_type": content_type,
                        "content_length": content_length,
                        "is_dicom_content_type": is_dicom,
                        "has_dicom_header": has_dicom_header,
                        "is_valid_mongodb_objectid": len(file_id) == 24 and all(c in '0123456789abcdef' for c in file_id.lower())
                    }
                    
                    self.log_test(f"File Access {i+1}", True, 
                                f"Successfully accessed file {file_id} ({content_length} bytes)", 
                                file_info)
                    
                elif response.status_code == 404:
                    self.log_test(f"File Access {i+1}", False, f"File {file_id} not found (404)")
                else:
                    self.log_test(f"File Access {i+1}", False, 
                                f"Failed to access file {file_id}: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"File Access {i+1}", False, f"Request failed for file {file_id}: {str(e)}")
    
    def test_jwt_token_validation(self):
        """Verify JWT token is working properly"""
        print("\n=== Testing JWT Token Validation ===")
        
        if not self.auth_token:
            self.log_test("JWT Token Validation", False, "No authentication token available")
            return
        
        try:
            # Test authenticated endpoint
            response = self.session.get(f"{BASE_URL}/auth/me")
            
            if response.status_code == 200:
                user_data = response.json()
                self.log_test("JWT Token Validation", True, 
                            f"JWT token valid - authenticated as {user_data.get('email')}")
                
                # Test without token to verify 401 response
                temp_headers = self.session.headers.copy()
                del self.session.headers['Authorization']
                
                unauth_response = self.session.get(f"{BASE_URL}/auth/me")
                
                # Restore headers
                self.session.headers = temp_headers
                
                if unauth_response.status_code == 401:
                    self.log_test("Unauthenticated Access Control", True, 
                                "Properly returns 401 for unauthenticated requests")
                else:
                    self.log_test("Unauthenticated Access Control", False, 
                                f"Expected 401, got {unauth_response.status_code}")
                    
            else:
                self.log_test("JWT Token Validation", False, 
                            f"Token validation failed: {response.status_code}")
                
        except Exception as e:
            self.log_test("JWT Token Validation", False, f"Request failed: {str(e)}")
    
    def determine_viewer_url_path(self, study_data):
        """Determine the correct URL path for DICOM viewer"""
        print("\n=== Determining DICOM Viewer URL Path ===")
        
        if not study_data:
            self.log_test("Viewer URL Path", False, "No study data available")
            return
        
        study_id = study_data.get("id")
        study_study_id = study_data.get("study_id")
        
        url_analysis = {
            "study.id_value": study_id,
            "study.study_id_value": study_study_id,
            "recommended_viewer_path_option_1": f"/viewer/{study_study_id}",
            "recommended_viewer_path_option_2": f"/viewer/{study_id}",
            "current_test_path": "/viewer/OR2UUPB5",
            "path_matches_study_id": study_study_id == "OR2UUPB5",
            "path_matches_id": study_id == "OR2UUPB5"
        }
        
        if study_study_id == "OR2UUPB5":
            recommended_path = f"/viewer/{study_study_id}"
            self.log_test("Viewer URL Path", True, 
                        f"Current path /viewer/OR2UUPB5 matches study.study_id - use /viewer/{study_study_id}", 
                        url_analysis)
        elif study_id == "OR2UUPB5":
            recommended_path = f"/viewer/{study_id}"
            self.log_test("Viewer URL Path", True, 
                        f"Current path /viewer/OR2UUPB5 matches study.id - use /viewer/{study_id}", 
                        url_analysis)
        else:
            self.log_test("Viewer URL Path", False, 
                        "OR2UUPB5 doesn't match either study.id or study.study_id", 
                        url_analysis)
    
    def run_debug_tests(self):
        """Run all debug tests for Study OR2UUPB5"""
        print("🔍 Starting Study OR2UUPB5 Debug Testing")
        print(f"Testing against: {BASE_URL}")
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Test study access
        study_data = self.test_study_or2uupb5_access()
        
        # Test JWT token validation
        self.test_jwt_token_validation()
        
        # Test file access if we have file_ids
        if study_data and study_data.get("file_ids"):
            self.test_file_access(study_data["file_ids"])
        
        # Determine correct viewer URL path
        self.determine_viewer_url_path(study_data)
        
        # Print summary
        self.print_summary()
        
        return len([r for r in self.test_results if not r["success"]]) == 0
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("🏁 STUDY OR2UUPB5 DEBUG SUMMARY")
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
        
        print("\n📋 KEY FINDINGS:")
        for result in self.test_results:
            if result["success"] and result["details"]:
                print(f"  ✅ {result['test']}")
                if "study.id" in result["details"]:
                    print(f"     study.id: {result['details']['study.id']}")
                if "study.study_id" in result["details"]:
                    print(f"     study.study_id: {result['details']['study.study_id']}")
                if "patient_name" in result["details"]:
                    print(f"     patient_name: {result['details']['patient_name']}")
                if "file_ids_count" in result["details"]:
                    print(f"     file_ids_count: {result['details']['file_ids_count']}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    tester = StudyOR2UUPB5Tester()
    success = tester.run_debug_tests()
    sys.exit(0 if success else 1)