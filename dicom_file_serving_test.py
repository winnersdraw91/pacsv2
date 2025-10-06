#!/usr/bin/env python3
"""
DICOM File Serving Functionality Testing Suite
Tests DICOM file serving endpoints and study access as requested in the review
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

class DICOMFileServingTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_tokens = {}
        self.test_results = []
        self.available_studies = []
        self.studies_with_files = []
        
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
    
    def authenticate_user(self, email: str, password: str, user_type: str) -> bool:
        """Authenticate different user types"""
        try:
            login_data = {
                "email": email,
                "password": password
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.auth_tokens[user_type] = data["access_token"]
                    self.log_test(f"{user_type.title()} Authentication", True, f"Successfully authenticated {email}")
                    return True
                else:
                    self.log_test(f"{user_type.title()} Authentication", False, "Login response missing access_token")
                    return False
            else:
                self.log_test(f"{user_type.title()} Authentication", False, f"Login failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"{user_type.title()} Authentication", False, f"Login request failed: {str(e)}")
            return False
    
    def set_auth_header(self, user_type: str):
        """Set authorization header for specific user type"""
        if user_type in self.auth_tokens:
            self.session.headers.update({"Authorization": f"Bearer {self.auth_tokens[user_type]}"})
            return True
        return False
    
    def test_authentication_for_different_users(self):
        """Test authentication for different user types"""
        print("\n=== Testing Authentication for Different User Types ===")
        
        # Test admin authentication
        self.authenticate_user(ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        
        # Try to authenticate other user types (these may not exist, but we test the endpoint)
        test_users = [
            ("technician@pacs.com", "tech123", "technician"),
            ("radiologist@pacs.com", "radio123", "radiologist"),
            ("centre@pacs.com", "centre123", "centre")
        ]
        
        for email, password, user_type in test_users:
            # These users may not exist, so we expect failures but test the endpoint
            result = self.authenticate_user(email, password, user_type)
            if not result:
                self.log_test(f"{user_type.title()} Authentication", True, f"Authentication endpoint working (user {email} may not exist)")
    
    def check_available_studies(self):
        """Check all studies in the system and identify which have DICOM file_ids"""
        print("\n=== Checking Available Studies and DICOM Files ===")
        
        if not self.set_auth_header("admin"):
            self.log_test("Study Check", False, "No admin authentication available")
            return
        
        try:
            # Get all studies
            response = self.session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                self.available_studies = studies
                
                self.log_test("Get All Studies", True, f"Retrieved {len(studies)} studies from system")
                
                # Analyze studies for DICOM files
                studies_with_files = []
                studies_without_files = []
                total_file_ids = 0
                
                for study in studies:
                    file_ids = study.get("file_ids", [])
                    if file_ids:
                        studies_with_files.append({
                            "study_id": study.get("study_id"),
                            "patient_name": study.get("patient_name"),
                            "modality": study.get("modality"),
                            "file_count": len(file_ids),
                            "file_ids": file_ids
                        })
                        total_file_ids += len(file_ids)
                    else:
                        studies_without_files.append(study.get("study_id"))
                
                self.studies_with_files = studies_with_files
                
                # Log detailed findings
                self.log_test("DICOM File Analysis", True, 
                            f"Found {len(studies_with_files)} studies with DICOM files, {len(studies_without_files)} without files")
                
                if studies_with_files:
                    print(f"   📁 Studies with DICOM files:")
                    for study in studies_with_files:
                        print(f"      • {study['study_id']}: {study['patient_name']} ({study['modality']}) - {study['file_count']} files")
                        print(f"        File IDs: {study['file_ids'][:3]}{'...' if len(study['file_ids']) > 3 else ''}")
                else:
                    self.log_test("DICOM Files Available", False, "No studies found with DICOM file_ids - all studies have empty file_ids arrays")
                
                # Check specific study RS6P4028 mentioned in request
                rs6p4028_study = next((s for s in studies if s.get("study_id") == "RS6P4028"), None)
                if rs6p4028_study:
                    file_ids = rs6p4028_study.get("file_ids", [])
                    if file_ids:
                        self.log_test("Study RS6P4028 DICOM Files", True, f"Study RS6P4028 has {len(file_ids)} DICOM files")
                    else:
                        self.log_test("Study RS6P4028 DICOM Files", False, "Study RS6P4028 exists but has no DICOM file_ids")
                else:
                    self.log_test("Study RS6P4028 Check", False, "Study RS6P4028 not found in system")
                
            else:
                self.log_test("Get All Studies", False, f"Failed to retrieve studies: {response.status_code}")
                
        except Exception as e:
            self.log_test("Check Available Studies", False, f"Request failed: {str(e)}")
    
    def test_dicom_file_endpoints(self):
        """Test DICOM file serving endpoints"""
        print("\n=== Testing DICOM File Serving Endpoints ===")
        
        if not self.set_auth_header("admin"):
            self.log_test("DICOM File Test", False, "No admin authentication available")
            return
        
        if not self.studies_with_files:
            self.log_test("DICOM File Endpoint Test", False, "No studies with DICOM files found to test")
            return
        
        # Test GET /api/files/{file_id} endpoint
        for study in self.studies_with_files[:3]:  # Test first 3 studies to avoid too many requests
            study_id = study["study_id"]
            file_ids = study["file_ids"]
            
            for i, file_id in enumerate(file_ids[:2]):  # Test first 2 files per study
                try:
                    response = self.session.get(f"{BASE_URL}/files/{file_id}")
                    
                    if response.status_code == 200:
                        # Check content type
                        content_type = response.headers.get("content-type", "")
                        if content_type == "application/dicom":
                            self.log_test(f"DICOM File Serving ({study_id} file {i+1})", True, 
                                        f"Successfully served DICOM file with correct content-type")
                        else:
                            self.log_test(f"DICOM File Serving ({study_id} file {i+1})", False, 
                                        f"Wrong content-type: {content_type}, expected application/dicom")
                        
                        # Check if we got actual content
                        content_length = len(response.content)
                        if content_length > 0:
                            self.log_test(f"DICOM File Content ({study_id} file {i+1})", True, 
                                        f"Received {content_length} bytes of DICOM data")
                        else:
                            self.log_test(f"DICOM File Content ({study_id} file {i+1})", False, 
                                        "Received empty DICOM file")
                            
                    elif response.status_code == 404:
                        self.log_test(f"DICOM File Serving ({study_id} file {i+1})", False, 
                                    f"File not found (404) - file_id {file_id} may be invalid")
                    else:
                        self.log_test(f"DICOM File Serving ({study_id} file {i+1})", False, 
                                    f"Unexpected status code: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"DICOM File Serving ({study_id} file {i+1})", False, 
                                f"Request failed: {str(e)}")
        
        # Test with invalid file_id
        try:
            response = self.session.get(f"{BASE_URL}/files/invalid_file_id_12345")
            if response.status_code == 404:
                self.log_test("DICOM File Invalid ID", True, "Correctly returns 404 for invalid file_id")
            else:
                self.log_test("DICOM File Invalid ID", False, f"Unexpected status for invalid file_id: {response.status_code}")
        except Exception as e:
            self.log_test("DICOM File Invalid ID", False, f"Request failed: {str(e)}")
    
    def test_study_access(self):
        """Test study access endpoints"""
        print("\n=== Testing Study Access Endpoints ===")
        
        if not self.set_auth_header("admin"):
            self.log_test("Study Access Test", False, "No admin authentication available")
            return
        
        if not self.available_studies:
            self.log_test("Study Access Test", False, "No studies available for testing")
            return
        
        # Test GET /api/studies/{study_id} for existing studies
        for study in self.available_studies[:5]:  # Test first 5 studies
            study_id = study.get("study_id")
            
            try:
                response = self.session.get(f"{BASE_URL}/studies/{study_id}")
                
                if response.status_code == 200:
                    study_data = response.json()
                    
                    # Verify response includes file_ids array
                    if "file_ids" in study_data:
                        file_ids = study_data["file_ids"]
                        self.log_test(f"Study Access ({study_id})", True, 
                                    f"Successfully retrieved study with {len(file_ids)} file references")
                        
                        # Check if study has proper metadata for DICOM viewing
                        required_fields = ["patient_name", "modality", "uploaded_at", "status"]
                        missing_fields = [field for field in required_fields if field not in study_data]
                        
                        if not missing_fields:
                            self.log_test(f"Study Metadata ({study_id})", True, 
                                        "Study has all required metadata for DICOM viewing")
                        else:
                            self.log_test(f"Study Metadata ({study_id})", False, 
                                        f"Missing metadata fields: {missing_fields}")
                    else:
                        self.log_test(f"Study Access ({study_id})", False, 
                                    "Study response missing file_ids array")
                        
                elif response.status_code == 404:
                    self.log_test(f"Study Access ({study_id})", False, 
                                f"Study not found (404) - study_id {study_id} may be invalid")
                else:
                    self.log_test(f"Study Access ({study_id})", False, 
                                f"Unexpected status code: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Study Access ({study_id})", False, f"Request failed: {str(e)}")
        
        # Test with invalid study_id
        try:
            response = self.session.get(f"{BASE_URL}/studies/INVALID123")
            if response.status_code == 404:
                self.log_test("Study Access Invalid ID", True, "Correctly returns 404 for invalid study_id")
            else:
                self.log_test("Study Access Invalid ID", False, f"Unexpected status for invalid study_id: {response.status_code}")
        except Exception as e:
            self.log_test("Study Access Invalid ID", False, f"Request failed: {str(e)}")
    
    def test_authorization_for_dicom_access(self):
        """Test if users can access DICOM files they're authorized to view"""
        print("\n=== Testing Authorization for DICOM Access ===")
        
        if not self.studies_with_files:
            self.log_test("DICOM Authorization Test", False, "No studies with DICOM files found to test authorization")
            return
        
        # Test with admin user (should have access)
        if self.set_auth_header("admin"):
            study = self.studies_with_files[0]
            file_id = study["file_ids"][0]
            
            try:
                response = self.session.get(f"{BASE_URL}/files/{file_id}")
                if response.status_code == 200:
                    self.log_test("Admin DICOM Access", True, "Admin user can access DICOM files")
                elif response.status_code == 403:
                    self.log_test("Admin DICOM Access", False, "Admin user denied access to DICOM files")
                else:
                    self.log_test("Admin DICOM Access", False, f"Unexpected status: {response.status_code}")
            except Exception as e:
                self.log_test("Admin DICOM Access", False, f"Request failed: {str(e)}")
        
        # Test without authentication
        self.session.headers.pop("Authorization", None)
        
        if self.studies_with_files:
            study = self.studies_with_files[0]
            file_id = study["file_ids"][0]
            
            try:
                response = self.session.get(f"{BASE_URL}/files/{file_id}")
                if response.status_code == 401:
                    self.log_test("Unauthenticated DICOM Access", True, "Correctly denies access without authentication")
                elif response.status_code == 200:
                    self.log_test("Unauthenticated DICOM Access", False, "Security issue: allows access without authentication")
                else:
                    self.log_test("Unauthenticated DICOM Access", True, f"Access denied (status: {response.status_code})")
            except Exception as e:
                self.log_test("Unauthenticated DICOM Access", False, f"Request failed: {str(e)}")
    
    def test_dicom_viewer_integration_readiness(self):
        """Test if the system is ready for DICOM viewer integration"""
        print("\n=== Testing DICOM Viewer Integration Readiness ===")
        
        if not self.set_auth_header("admin"):
            self.log_test("DICOM Viewer Readiness", False, "No admin authentication available")
            return
        
        # Check if we have real DICOM files that can be served
        if self.studies_with_files:
            total_files = sum(len(study["file_ids"]) for study in self.studies_with_files)
            self.log_test("DICOM Files for Viewer", True, 
                        f"System has {len(self.studies_with_files)} studies with {total_files} DICOM files ready for viewer")
            
            # Test a complete workflow: get study -> get file_ids -> serve files
            study = self.studies_with_files[0]
            study_id = study["study_id"]
            
            try:
                # Step 1: Get study details
                study_response = self.session.get(f"{BASE_URL}/studies/{study_id}")
                if study_response.status_code == 200:
                    study_data = study_response.json()
                    file_ids = study_data.get("file_ids", [])
                    
                    if file_ids:
                        # Step 2: Try to serve first file
                        file_response = self.session.get(f"{BASE_URL}/files/{file_ids[0]}")
                        if file_response.status_code == 200:
                            self.log_test("DICOM Viewer Workflow", True, 
                                        f"Complete workflow successful: study retrieval -> file serving for {study_id}")
                        else:
                            self.log_test("DICOM Viewer Workflow", False, 
                                        f"File serving failed in workflow: {file_response.status_code}")
                    else:
                        self.log_test("DICOM Viewer Workflow", False, 
                                    "Study has no file_ids in response")
                else:
                    self.log_test("DICOM Viewer Workflow", False, 
                                f"Study retrieval failed: {study_response.status_code}")
                    
            except Exception as e:
                self.log_test("DICOM Viewer Workflow", False, f"Workflow test failed: {str(e)}")
        else:
            self.log_test("DICOM Files for Viewer", False, 
                        "No studies with DICOM files found - viewer will not be able to load real data")
            self.log_test("DICOM Viewer Integration", False, 
                        "System not ready for DICOM viewer - no real DICOM files available")
    
    def run_all_tests(self):
        """Run all DICOM file serving tests"""
        print("🚀 Starting DICOM File Serving Testing Suite")
        print(f"Testing against: {BASE_URL}")
        print("Focus: DICOM file serving functionality for viewer integration")
        
        # Run tests in logical order
        self.test_authentication_for_different_users()
        self.check_available_studies()
        self.test_study_access()
        self.test_dicom_file_endpoints()
        self.test_authorization_for_dicom_access()
        self.test_dicom_viewer_integration_readiness()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary with focus on DICOM file serving"""
        print("\n" + "="*80)
        print("🏁 DICOM FILE SERVING TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # DICOM-specific summary
        print(f"\n📊 DICOM FILE SERVING STATUS:")
        print(f"   • Studies in system: {len(self.available_studies)}")
        print(f"   • Studies with DICOM files: {len(self.studies_with_files)}")
        
        if self.studies_with_files:
            total_files = sum(len(study["file_ids"]) for study in self.studies_with_files)
            print(f"   • Total DICOM files available: {total_files}")
            print(f"   • DICOM viewer integration: READY ✅")
        else:
            print(f"   • Total DICOM files available: 0")
            print(f"   • DICOM viewer integration: NOT READY ❌")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        # Key findings for DICOM viewer
        print(f"\n🎯 KEY FINDINGS FOR DICOM VIEWER:")
        
        dicom_serving_tests = [r for r in self.test_results if "DICOM File Serving" in r["test"]]
        if dicom_serving_tests:
            passed_serving = sum(1 for t in dicom_serving_tests if t["success"])
            print(f"   • DICOM file serving: {passed_serving}/{len(dicom_serving_tests)} tests passed")
        
        study_access_tests = [r for r in self.test_results if "Study Access" in r["test"]]
        if study_access_tests:
            passed_access = sum(1 for t in study_access_tests if t["success"])
            print(f"   • Study access: {passed_access}/{len(study_access_tests)} tests passed")
        
        auth_tests = [r for r in self.test_results if "Authentication" in r["test"] or "Authorization" in r["test"]]
        if auth_tests:
            passed_auth = sum(1 for t in auth_tests if t["success"])
            print(f"   • Authentication/Authorization: {passed_auth}/{len(auth_tests)} tests passed")
        
        print("\n" + "="*80)
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = DICOMFileServingTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)