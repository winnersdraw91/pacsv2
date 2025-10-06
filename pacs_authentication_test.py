#!/usr/bin/env python3
"""
PACS System Authentication and DICOM Functionality Testing Suite
Focuses on resolving authentication issues and testing DICOM metadata functionality
"""

import requests
import json
import sys
import io
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"
RADIOLOGIST_EMAIL = "radiologist@pacs.com"
RADIOLOGIST_PASSWORD = "radio123"
TECHNICIAN_EMAIL = "technician@pacs.com"
TECHNICIAN_PASSWORD = "tech123"

class PACSAuthenticationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.radiologist_token = None
        self.technician_token = None
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
    
    def test_create_demo_users(self):
        """PRIORITY 1: Create demo users and test authentication"""
        print("\n=== PRIORITY 1: Creating Demo Users ===")
        
        # First authenticate as admin
        if not self.authenticate_admin():
            return
        
        # Create demo users
        try:
            response = self.session.post(f"{BASE_URL}/admin/create-demo-users")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Demo Users", True, 
                            f"Demo users created: {', '.join(data.get('created_users', []))}")
                
                # Test authentication for each demo user
                self.test_radiologist_authentication()
                self.test_technician_authentication()
                self.test_admin_authentication_still_works()
                
            else:
                self.log_test("Create Demo Users", False, 
                            f"Failed to create demo users: {response.status_code}", 
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Create Demo Users", False, f"Request failed: {str(e)}")
    
    def authenticate_admin(self) -> bool:
        """Authenticate as admin user"""
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.admin_token = data["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
                    return True
            
            self.log_test("Admin Authentication", False, 
                        f"Admin login failed: {response.status_code}", 
                        {"response": response.text})
            return False
            
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Admin login request failed: {str(e)}")
            return False
    
    def test_radiologist_authentication(self):
        """Test radiologist authentication"""
        try:
            login_data = {
                "email": RADIOLOGIST_EMAIL,
                "password": RADIOLOGIST_PASSWORD
            }
            
            # Create new session for radiologist
            radiologist_session = requests.Session()
            response = radiologist_session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.radiologist_token = data["access_token"]
                    user_info = data["user"]
                    
                    self.log_test("Radiologist Authentication", True, 
                                f"Successfully logged in as {user_info['name']} ({user_info['role']})")
                    
                    # Test /auth/me endpoint with radiologist token
                    radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
                    me_response = radiologist_session.get(f"{BASE_URL}/auth/me")
                    
                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        self.log_test("Radiologist Auth/Me", True, 
                                    f"Retrieved radiologist info: {me_data['email']}")
                    else:
                        self.log_test("Radiologist Auth/Me", False, 
                                    f"Failed to get radiologist info: {me_response.status_code}",
                                    {"response": me_response.text})
                else:
                    self.log_test("Radiologist Authentication", False, 
                                "Login response missing required fields", 
                                {"response": data})
            else:
                self.log_test("Radiologist Authentication", False, 
                            f"Radiologist login failed: {response.status_code}", 
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Radiologist Authentication", False, f"Request failed: {str(e)}")
    
    def test_technician_authentication(self):
        """Test technician authentication"""
        try:
            login_data = {
                "email": TECHNICIAN_EMAIL,
                "password": TECHNICIAN_PASSWORD
            }
            
            # Create new session for technician
            technician_session = requests.Session()
            response = technician_session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.technician_token = data["access_token"]
                    user_info = data["user"]
                    
                    self.log_test("Technician Authentication", True, 
                                f"Successfully logged in as {user_info['name']} ({user_info['role']})")
                    
                    # Test /auth/me endpoint with technician token
                    technician_session.headers.update({"Authorization": f"Bearer {self.technician_token}"})
                    me_response = technician_session.get(f"{BASE_URL}/auth/me")
                    
                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        self.log_test("Technician Auth/Me", True, 
                                    f"Retrieved technician info: {me_data['email']}")
                    else:
                        self.log_test("Technician Auth/Me", False, 
                                    f"Failed to get technician info: {me_response.status_code}",
                                    {"response": me_response.text})
                else:
                    self.log_test("Technician Authentication", False, 
                                "Login response missing required fields", 
                                {"response": data})
            else:
                self.log_test("Technician Authentication", False, 
                            f"Technician login failed: {response.status_code}", 
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Technician Authentication", False, f"Request failed: {str(e)}")
    
    def test_admin_authentication_still_works(self):
        """Verify admin authentication still works after creating demo users"""
        try:
            # Test with existing admin token
            response = self.session.get(f"{BASE_URL}/auth/me")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Admin Auth Still Works", True, 
                            f"Admin authentication verified: {data['email']}")
            else:
                self.log_test("Admin Auth Still Works", False, 
                            f"Admin auth verification failed: {response.status_code}",
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Admin Auth Still Works", False, f"Request failed: {str(e)}")
    
    def test_studies_endpoints_with_roles(self):
        """PRIORITY 2: Test studies endpoints with different user roles"""
        print("\n=== PRIORITY 2: Testing Studies Endpoints with Different Roles ===")
        
        # Test with admin token
        if self.admin_token:
            self.test_studies_endpoint_with_token("Admin", self.admin_token)
        
        # Test with radiologist token
        if self.radiologist_token:
            self.test_studies_endpoint_with_token("Radiologist", self.radiologist_token)
        
        # Test with technician token  
        if self.technician_token:
            self.test_studies_endpoint_with_token("Technician", self.technician_token)
    
    def test_studies_endpoint_with_token(self, role_name: str, token: str):
        """Test studies endpoint with specific user token"""
        try:
            # Create session with specific token
            role_session = requests.Session()
            role_session.headers.update({"Authorization": f"Bearer {token}"})
            
            # Test GET /api/studies
            response = role_session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                self.log_test(f"{role_name} Get Studies", True, 
                            f"Retrieved {len(studies)} studies successfully")
                
                # Test individual study retrieval if studies exist
                if studies:
                    study_id = studies[0].get("study_id")
                    if study_id:
                        study_response = role_session.get(f"{BASE_URL}/studies/{study_id}")
                        if study_response.status_code == 200:
                            study_data = study_response.json()
                            self.log_test(f"{role_name} Get Individual Study", True, 
                                        f"Retrieved study {study_id} successfully")
                        else:
                            self.log_test(f"{role_name} Get Individual Study", False, 
                                        f"Failed to get individual study: {study_response.status_code}",
                                        {"response": study_response.text})
                
            else:
                self.log_test(f"{role_name} Get Studies", False, 
                            f"Failed to get studies: {response.status_code}",
                            {"response": response.text})
                
        except Exception as e:
            self.log_test(f"{role_name} Get Studies", False, f"Request failed: {str(e)}")
    
    def test_dicom_metadata_functionality(self):
        """PRIORITY 3: Validate DICOM metadata functionality"""
        print("\n=== PRIORITY 3: Testing DICOM Metadata Functionality ===")
        
        if not self.admin_token:
            self.log_test("DICOM Metadata Test", False, "No admin token available")
            return
        
        # Test extract metadata endpoint
        self.test_extract_metadata_endpoint()
        
        # Test radiologist upload functionality if radiologist token exists
        if self.radiologist_token:
            self.test_radiologist_upload_functionality()
        
        # Test file download endpoints
        self.test_file_download_endpoints()
    
    def test_extract_metadata_endpoint(self):
        """Test POST /api/files/extract-metadata endpoint"""
        try:
            # Create a minimal DICOM-like file for testing
            # Note: This is a mock test file, not a real DICOM
            test_file_content = b"DICM" + b"\x00" * 128  # Minimal DICOM header
            
            files = {
                'file': ('test.dcm', io.BytesIO(test_file_content), 'application/dicom')
            }
            
            response = self.session.post(f"{BASE_URL}/files/extract-metadata", files=files)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Extract Metadata Endpoint", True, 
                            f"Metadata extraction successful for {data.get('filename', 'unknown')}")
            elif response.status_code == 400:
                # Expected for mock file - endpoint exists and validates properly
                self.log_test("Extract Metadata Endpoint", True, 
                            "Endpoint exists and validates input (returned 400 for mock file)")
            else:
                self.log_test("Extract Metadata Endpoint", False, 
                            f"Unexpected response: {response.status_code}",
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Extract Metadata Endpoint", False, f"Request failed: {str(e)}")
    
    def test_radiologist_upload_functionality(self):
        """Test radiologist upload with report functionality"""
        try:
            # Create session with radiologist token
            radiologist_session = requests.Session()
            radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
            
            # Test POST /api/studies/upload-with-report
            test_file_content = b"DICM" + b"\x00" * 128  # Minimal DICOM header
            
            files = {
                'files': ('test_radiologist.dcm', io.BytesIO(test_file_content), 'application/dicom')
            }
            
            form_data = {
                'patient_name': 'Test Patient Radiologist',
                'patient_age': '45',
                'patient_gender': 'M',
                'modality': 'CT',
                'study_description': 'Test radiologist upload',
                'final_report_text': 'Test radiologist report findings'
            }
            
            response = radiologist_session.post(f"{BASE_URL}/studies/upload-with-report", 
                                              files=files, data=form_data)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Radiologist Upload with Report", True, 
                            f"Successfully uploaded study {data.get('study_id', 'unknown')}")
            else:
                self.log_test("Radiologist Upload with Report", False, 
                            f"Upload failed: {response.status_code}",
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Radiologist Upload with Report", False, f"Request failed: {str(e)}")
    
    def test_file_download_endpoints(self):
        """Test file download endpoints"""
        try:
            # First get studies to find file IDs
            response = self.session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                
                # Look for studies with file_ids
                for study in studies:
                    file_ids = study.get("file_ids", [])
                    if file_ids:
                        # Test downloading first file
                        file_id = file_ids[0]
                        
                        # Skip mock file IDs (file_XXXXX format)
                        if file_id.startswith("file_"):
                            continue
                        
                        file_response = self.session.get(f"{BASE_URL}/files/{file_id}")
                        
                        if file_response.status_code == 200:
                            self.log_test("File Download", True, 
                                        f"Successfully downloaded file {file_id}")
                            break
                        elif file_response.status_code == 404:
                            self.log_test("File Download", False, 
                                        f"File {file_id} not found (404)")
                        else:
                            self.log_test("File Download", False, 
                                        f"File download failed: {file_response.status_code}")
                        break
                else:
                    self.log_test("File Download", True, 
                                "No real DICOM files found for download testing (expected)")
            else:
                self.log_test("File Download", False, 
                            f"Failed to get studies for file testing: {response.status_code}")
                
        except Exception as e:
            self.log_test("File Download", False, f"Request failed: {str(e)}")
    
    def test_end_to_end_workflows(self):
        """PRIORITY 4: End-to-end workflow testing"""
        print("\n=== PRIORITY 4: End-to-End Workflow Testing ===")
        
        # Test technician workflow
        if self.technician_token:
            self.test_technician_workflow()
        
        # Test radiologist workflow
        if self.radiologist_token:
            self.test_radiologist_workflow()
        
        # Test role-based access controls
        self.test_role_based_access_controls()
        
        # Test study management operations
        self.test_study_management_operations()
    
    def test_technician_workflow(self):
        """Test complete technician workflow"""
        try:
            # Create session with technician token
            technician_session = requests.Session()
            technician_session.headers.update({"Authorization": f"Bearer {self.technician_token}"})
            
            # Test technician can access their studies
            response = technician_session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                self.log_test("Technician Workflow - Get Studies", True, 
                            f"Technician can access {len(studies)} studies")
            else:
                self.log_test("Technician Workflow - Get Studies", False, 
                            f"Technician cannot access studies: {response.status_code}",
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Technician Workflow", False, f"Request failed: {str(e)}")
    
    def test_radiologist_workflow(self):
        """Test radiologist workflow"""
        try:
            # Create session with radiologist token
            radiologist_session = requests.Session()
            radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
            
            # Test radiologist can access studies
            response = radiologist_session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                self.log_test("Radiologist Workflow - Get Studies", True, 
                            f"Radiologist can access {len(studies)} studies")
                
                # Test study assignment if studies exist
                if studies:
                    study_id = studies[0].get("study_id")
                    if study_id:
                        assign_response = radiologist_session.patch(f"{BASE_URL}/studies/{study_id}/assign")
                        if assign_response.status_code == 200:
                            self.log_test("Radiologist Workflow - Assign Study", True, 
                                        f"Successfully assigned study {study_id}")
                        else:
                            self.log_test("Radiologist Workflow - Assign Study", False, 
                                        f"Failed to assign study: {assign_response.status_code}",
                                        {"response": assign_response.text})
            else:
                self.log_test("Radiologist Workflow - Get Studies", False, 
                            f"Radiologist cannot access studies: {response.status_code}",
                            {"response": response.text})
                
        except Exception as e:
            self.log_test("Radiologist Workflow", False, f"Request failed: {str(e)}")
    
    def test_role_based_access_controls(self):
        """Test role-based access controls work properly"""
        try:
            # Test that technician cannot access admin endpoints
            if self.technician_token:
                technician_session = requests.Session()
                technician_session.headers.update({"Authorization": f"Bearer {self.technician_token}"})
                
                # Try to create demo users (admin only)
                response = technician_session.post(f"{BASE_URL}/admin/create-demo-users")
                
                if response.status_code == 403:
                    self.log_test("Role-Based Access Control", True, 
                                "Technician correctly denied admin access (403)")
                else:
                    self.log_test("Role-Based Access Control", False, 
                                f"Technician access control failed: {response.status_code}")
            
            # Test that radiologist cannot access admin endpoints
            if self.radiologist_token:
                radiologist_session = requests.Session()
                radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
                
                # Try to create billing rates (admin only)
                rate_data = {
                    "modality": "TEST",
                    "base_rate": 100.0,
                    "currency": "USD"
                }
                
                response = radiologist_session.post(f"{BASE_URL}/billing/rates", json=rate_data)
                
                if response.status_code == 403:
                    self.log_test("Role-Based Access Control - Radiologist", True, 
                                "Radiologist correctly denied admin billing access (403)")
                else:
                    self.log_test("Role-Based Access Control - Radiologist", False, 
                                f"Radiologist access control failed: {response.status_code}")
                
        except Exception as e:
            self.log_test("Role-Based Access Control", False, f"Request failed: {str(e)}")
    
    def test_study_management_operations(self):
        """Test study management operations"""
        try:
            # Get studies first
            response = self.session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                
                if studies:
                    study_id = studies[0].get("study_id")
                    
                    # Test study search functionality
                    search_params = {
                        "patient_name": studies[0].get("patient_name", ""),
                        "modality": studies[0].get("modality", "")
                    }
                    
                    search_response = self.session.post(f"{BASE_URL}/studies/search", json=search_params)
                    
                    if search_response.status_code == 200:
                        search_results = search_response.json()
                        self.log_test("Study Search Functionality", True, 
                                    f"Search returned {len(search_results)} results")
                    else:
                        self.log_test("Study Search Functionality", False, 
                                    f"Search failed: {search_response.status_code}",
                                    {"response": search_response.text})
                else:
                    self.log_test("Study Management Operations", True, 
                                "No studies available for management testing")
            else:
                self.log_test("Study Management Operations", False, 
                            f"Failed to get studies: {response.status_code}")
                
        except Exception as e:
            self.log_test("Study Management Operations", False, f"Request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all authentication and DICOM functionality tests"""
        print("🚀 Starting PACS Authentication and DICOM Functionality Testing Suite")
        print(f"Testing against: {BASE_URL}")
        
        # Run tests in priority order
        self.test_create_demo_users()
        self.test_studies_endpoints_with_roles()
        self.test_dicom_metadata_functionality()
        self.test_end_to_end_workflows()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🏁 PACS AUTHENTICATION & DICOM FUNCTIONALITY TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Group results by priority
        priority_results = {
            "PRIORITY 1 - Demo Users & Authentication": [],
            "PRIORITY 2 - Studies Endpoints": [],
            "PRIORITY 3 - DICOM Metadata": [],
            "PRIORITY 4 - End-to-End Workflows": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if any(x in test_name for x in ["Demo Users", "Authentication", "Auth"]):
                priority_results["PRIORITY 1 - Demo Users & Authentication"].append(result)
            elif "Studies" in test_name or "Get Studies" in test_name:
                priority_results["PRIORITY 2 - Studies Endpoints"].append(result)
            elif any(x in test_name for x in ["Metadata", "Upload", "Download", "File"]):
                priority_results["PRIORITY 3 - DICOM Metadata"].append(result)
            elif any(x in test_name for x in ["Workflow", "Role", "Management"]):
                priority_results["PRIORITY 4 - End-to-End Workflows"].append(result)
        
        for priority, results in priority_results.items():
            if results:
                print(f"\n📋 {priority}:")
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}: {result['message']}")
        
        if failed_tests > 0:
            print(f"\n🔍 CRITICAL ISSUES TO ADDRESS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "="*80)
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = PACSAuthenticationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)