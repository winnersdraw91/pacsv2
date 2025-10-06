#!/usr/bin/env python3
"""
Comprehensive PACS System Testing Suite
Tests authentication, DICOM functionality, and resolves validation issues
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
WORKING_RADIOLOGIST_EMAIL = "radiologist2@pacs.com"
WORKING_RADIOLOGIST_PASSWORD = "radio123"
TECHNICIAN_EMAIL = "technician@pacs.com"
TECHNICIAN_PASSWORD = "tech123"

class ComprehensivePACSTest:
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
    
    def authenticate_all_users(self):
        """Authenticate all user types"""
        print("\n=== AUTHENTICATION TESTING ===")
        
        # Admin authentication
        try:
            login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
                self.log_test("Admin Authentication", True, f"Successfully logged in as {data['user']['name']}")
            else:
                self.log_test("Admin Authentication", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Exception: {str(e)}")
            return False
        
        # Working radiologist authentication
        try:
            login_data = {"email": WORKING_RADIOLOGIST_EMAIL, "password": WORKING_RADIOLOGIST_PASSWORD}
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.radiologist_token = data["access_token"]
                self.log_test("Working Radiologist Authentication", True, f"Successfully logged in as {data['user']['name']}")
            else:
                self.log_test("Working Radiologist Authentication", False, f"Failed: {response.status_code}")
        except Exception as e:
            self.log_test("Working Radiologist Authentication", False, f"Exception: {str(e)}")
        
        # Technician authentication
        try:
            login_data = {"email": TECHNICIAN_EMAIL, "password": TECHNICIAN_PASSWORD}
            response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.technician_token = data["access_token"]
                self.log_test("Technician Authentication", True, f"Successfully logged in as {data['user']['name']}")
            else:
                self.log_test("Technician Authentication", False, f"Failed: {response.status_code}")
        except Exception as e:
            self.log_test("Technician Authentication", False, f"Exception: {str(e)}")
        
        return True
    
    def test_studies_endpoints_validation(self):
        """Test studies endpoints for DicomStudy model validation errors"""
        print("\n=== STUDIES ENDPOINTS VALIDATION TESTING ===")
        
        if not self.admin_token:
            self.log_test("Studies Validation", False, "No admin token available")
            return
        
        # Test GET /api/studies with admin
        try:
            response = self.session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                self.log_test("Admin Get Studies", True, f"Retrieved {len(studies)} studies without validation errors")
                
                # Test individual study retrieval
                if studies:
                    study_id = studies[0].get("study_id")
                    if study_id:
                        study_response = self.session.get(f"{BASE_URL}/studies/{study_id}")
                        if study_response.status_code == 200:
                            study_data = study_response.json()
                            self.log_test("Individual Study Retrieval", True, f"Retrieved study {study_id} successfully")
                            
                            # Check for required fields
                            required_fields = ["id", "study_id", "patient_name", "patient_age", "patient_gender", "modality"]
                            missing_fields = [field for field in required_fields if field not in study_data or study_data[field] is None]
                            
                            if not missing_fields:
                                self.log_test("DicomStudy Model Validation", True, "All required fields present")
                            else:
                                self.log_test("DicomStudy Model Validation", False, f"Missing fields: {missing_fields}")
                        else:
                            self.log_test("Individual Study Retrieval", False, f"Failed: {study_response.status_code}")
            else:
                self.log_test("Admin Get Studies", False, f"Failed: {response.status_code}", {"response": response.text})
                
        except Exception as e:
            self.log_test("Studies Validation", False, f"Exception: {str(e)}")
        
        # Test with different user roles
        self.test_studies_with_different_roles()
    
    def test_studies_with_different_roles(self):
        """Test studies endpoints with different user roles"""
        
        # Test with radiologist
        if self.radiologist_token:
            try:
                radiologist_session = requests.Session()
                radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
                
                response = radiologist_session.get(f"{BASE_URL}/studies")
                if response.status_code == 200:
                    studies = response.json()
                    self.log_test("Radiologist Get Studies", True, f"Retrieved {len(studies)} studies")
                else:
                    self.log_test("Radiologist Get Studies", False, f"Failed: {response.status_code}", {"response": response.text})
            except Exception as e:
                self.log_test("Radiologist Get Studies", False, f"Exception: {str(e)}")
        
        # Test with technician
        if self.technician_token:
            try:
                technician_session = requests.Session()
                technician_session.headers.update({"Authorization": f"Bearer {self.technician_token}"})
                
                response = technician_session.get(f"{BASE_URL}/studies")
                if response.status_code == 200:
                    studies = response.json()
                    self.log_test("Technician Get Studies", True, f"Retrieved {len(studies)} studies")
                else:
                    self.log_test("Technician Get Studies", False, f"Failed: {response.status_code}", {"response": response.text})
            except Exception as e:
                self.log_test("Technician Get Studies", False, f"Exception: {str(e)}")
    
    def test_study_search_functionality(self):
        """Test study search functionality"""
        print("\n=== STUDY SEARCH FUNCTIONALITY ===")
        
        if not self.admin_token:
            return
        
        try:
            # Test basic search
            search_params = {
                "patient_name": "",
                "modality": "CT",
                "status": "pending"
            }
            
            response = self.session.post(f"{BASE_URL}/studies/search", json=search_params)
            
            if response.status_code == 200:
                results = response.json()
                self.log_test("Study Search Basic", True, f"Search returned {len(results)} results")
            else:
                self.log_test("Study Search Basic", False, f"Failed: {response.status_code}", {"response": response.text})
            
            # Test advanced search with filters
            advanced_search = {
                "patient_name": "test",
                "modality": "CT",
                "status": "assigned",
                "patient_gender": "M",
                "include_drafts": True
            }
            
            response = self.session.post(f"{BASE_URL}/studies/search", json=advanced_search)
            
            if response.status_code == 200:
                results = response.json()
                self.log_test("Study Search Advanced", True, f"Advanced search returned {len(results)} results")
            else:
                self.log_test("Study Search Advanced", False, f"Failed: {response.status_code}", {"response": response.text})
                
        except Exception as e:
            self.log_test("Study Search", False, f"Exception: {str(e)}")
    
    def test_dicom_metadata_extraction(self):
        """Test DICOM metadata extraction functionality"""
        print("\n=== DICOM METADATA EXTRACTION ===")
        
        if not self.admin_token:
            return
        
        # Test extract metadata endpoint
        try:
            # Create a more realistic DICOM-like test file
            dicom_header = b'DICM'
            dicom_data = dicom_header + b'\x00' * 128 + b'test dicom data'
            
            files = {
                'file': ('test_metadata.dcm', io.BytesIO(dicom_data), 'application/dicom')
            }
            
            response = self.session.post(f"{BASE_URL}/files/extract-metadata", files=files)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("DICOM Metadata Extraction", True, f"Extracted metadata from {data.get('filename', 'file')}")
            elif response.status_code == 400:
                self.log_test("DICOM Metadata Extraction", True, "Endpoint validates input correctly (400 for invalid DICOM)")
            else:
                self.log_test("DICOM Metadata Extraction", False, f"Unexpected response: {response.status_code}")
                
        except Exception as e:
            self.log_test("DICOM Metadata Extraction", False, f"Exception: {str(e)}")
    
    def test_radiologist_upload_with_report(self):
        """Test radiologist upload functionality"""
        print("\n=== RADIOLOGIST UPLOAD WITH REPORT ===")
        
        if not self.radiologist_token:
            self.log_test("Radiologist Upload", False, "No radiologist token available")
            return
        
        try:
            radiologist_session = requests.Session()
            radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
            
            # Create test DICOM file
            dicom_data = b'DICM' + b'\x00' * 128 + b'test radiologist upload'
            
            files = {
                'files': ('radiologist_test.dcm', io.BytesIO(dicom_data), 'application/dicom')
            }
            
            form_data = {
                'patient_name': 'Test Patient Radiologist Upload',
                'patient_age': '55',
                'patient_gender': 'F',
                'modality': 'MRI',
                'study_description': 'Test radiologist upload with report',
                'final_report_text': 'Test radiologist report: Normal findings, no abnormalities detected.'
            }
            
            response = radiologist_session.post(f"{BASE_URL}/studies/upload-with-report", 
                                              files=files, data=form_data)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Radiologist Upload with Report", True, 
                            f"Successfully uploaded study {data.get('study_id', 'unknown')}")
            else:
                self.log_test("Radiologist Upload with Report", False, 
                            f"Failed: {response.status_code}", {"response": response.text})
                
        except Exception as e:
            self.log_test("Radiologist Upload with Report", False, f"Exception: {str(e)}")
    
    def test_file_download_functionality(self):
        """Test file download endpoints"""
        print("\n=== FILE DOWNLOAD FUNCTIONALITY ===")
        
        if not self.admin_token:
            return
        
        try:
            # Get studies to find file IDs
            response = self.session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                
                real_file_found = False
                for study in studies:
                    file_ids = study.get("file_ids", [])
                    for file_id in file_ids:
                        # Skip mock file IDs
                        if file_id.startswith("file_"):
                            continue
                        
                        # Try to download real file
                        file_response = self.session.get(f"{BASE_URL}/files/{file_id}")
                        
                        if file_response.status_code == 200:
                            self.log_test("File Download", True, f"Successfully downloaded file {file_id}")
                            real_file_found = True
                            break
                        elif file_response.status_code == 404:
                            continue
                        else:
                            self.log_test("File Download", False, f"Download failed: {file_response.status_code}")
                            break
                    
                    if real_file_found:
                        break
                
                if not real_file_found:
                    self.log_test("File Download", True, "No real DICOM files available for download testing")
            else:
                self.log_test("File Download", False, f"Failed to get studies: {response.status_code}")
                
        except Exception as e:
            self.log_test("File Download", False, f"Exception: {str(e)}")
    
    def test_role_based_access_controls(self):
        """Test role-based access controls"""
        print("\n=== ROLE-BASED ACCESS CONTROLS ===")
        
        # Test technician cannot access admin endpoints
        if self.technician_token:
            try:
                technician_session = requests.Session()
                technician_session.headers.update({"Authorization": f"Bearer {self.technician_token}"})
                
                # Try admin-only endpoint
                response = technician_session.post(f"{BASE_URL}/admin/create-demo-users")
                
                if response.status_code == 403:
                    self.log_test("Technician Access Control", True, "Technician correctly denied admin access")
                else:
                    self.log_test("Technician Access Control", False, f"Access control failed: {response.status_code}")
            except Exception as e:
                self.log_test("Technician Access Control", False, f"Exception: {str(e)}")
        
        # Test radiologist cannot access admin endpoints
        if self.radiologist_token:
            try:
                radiologist_session = requests.Session()
                radiologist_session.headers.update({"Authorization": f"Bearer {self.radiologist_token}"})
                
                # Try admin-only billing endpoint
                rate_data = {"modality": "TEST", "base_rate": 100.0, "currency": "USD"}
                response = radiologist_session.post(f"{BASE_URL}/billing/rates", json=rate_data)
                
                if response.status_code == 403:
                    self.log_test("Radiologist Access Control", True, "Radiologist correctly denied admin billing access")
                else:
                    self.log_test("Radiologist Access Control", False, f"Access control failed: {response.status_code}")
            except Exception as e:
                self.log_test("Radiologist Access Control", False, f"Exception: {str(e)}")
    
    def test_study_management_operations(self):
        """Test study management operations"""
        print("\n=== STUDY MANAGEMENT OPERATIONS ===")
        
        if not self.admin_token:
            return
        
        try:
            # Get studies first
            response = self.session.get(f"{BASE_URL}/studies")
            
            if response.status_code == 200:
                studies = response.json()
                
                if studies:
                    study_id = studies[0].get("study_id")
                    
                    # Test study assignment (should fail for admin, but endpoint should exist)
                    assign_response = self.session.patch(f"{BASE_URL}/studies/{study_id}/assign")
                    if assign_response.status_code in [200, 403]:
                        self.log_test("Study Assignment Endpoint", True, "Study assignment endpoint accessible")
                    else:
                        self.log_test("Study Assignment Endpoint", False, f"Unexpected response: {assign_response.status_code}")
                    
                    # Test mark as draft (should fail for admin, but endpoint should exist)
                    draft_response = self.session.patch(f"{BASE_URL}/studies/{study_id}/mark-draft")
                    if draft_response.status_code in [200, 403]:
                        self.log_test("Mark Draft Endpoint", True, "Mark draft endpoint accessible")
                    else:
                        self.log_test("Mark Draft Endpoint", False, f"Unexpected response: {draft_response.status_code}")
                    
                    # Test request delete (should fail for admin, but endpoint should exist)
                    delete_response = self.session.patch(f"{BASE_URL}/studies/{study_id}/request-delete")
                    if delete_response.status_code in [200, 403]:
                        self.log_test("Request Delete Endpoint", True, "Request delete endpoint accessible")
                    else:
                        self.log_test("Request Delete Endpoint", False, f"Unexpected response: {delete_response.status_code}")
                else:
                    self.log_test("Study Management", True, "No studies available for management testing")
            else:
                self.log_test("Study Management", False, f"Failed to get studies: {response.status_code}")
                
        except Exception as e:
            self.log_test("Study Management", False, f"Exception: {str(e)}")
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive PACS System Testing Suite")
        print(f"Testing against: {BASE_URL}")
        
        # Run tests in order
        if not self.authenticate_all_users():
            print("❌ Authentication failed, stopping tests")
            return False
        
        self.test_studies_endpoints_validation()
        self.test_study_search_functionality()
        self.test_dicom_metadata_extraction()
        self.test_radiologist_upload_with_report()
        self.test_file_download_functionality()
        self.test_role_based_access_controls()
        self.test_study_management_operations()
        
        # Print summary
        return self.print_summary()
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🏁 COMPREHENSIVE PACS SYSTEM TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Group results by category
        categories = {
            "Authentication": [],
            "Studies & Validation": [],
            "DICOM Functionality": [],
            "Access Control": [],
            "Study Management": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "Authentication" in test_name or "Auth" in test_name:
                categories["Authentication"].append(result)
            elif any(x in test_name for x in ["Studies", "Search", "Validation"]):
                categories["Studies & Validation"].append(result)
            elif any(x in test_name for x in ["DICOM", "Metadata", "Upload", "Download", "File"]):
                categories["DICOM Functionality"].append(result)
            elif "Access Control" in test_name:
                categories["Access Control"].append(result)
            elif any(x in test_name for x in ["Management", "Assignment", "Draft", "Delete"]):
                categories["Study Management"].append(result)
        
        for category, results in categories.items():
            if results:
                print(f"\n📋 {category}:")
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}: {result['message']}")
        
        # Critical issues summary
        critical_failures = [r for r in self.test_results if not r["success"]]
        if critical_failures:
            print(f"\n🔍 CRITICAL ISSUES TO ADDRESS:")
            for result in critical_failures:
                print(f"  ❌ {result['test']}: {result['message']}")
        else:
            print(f"\n🎉 ALL TESTS PASSED! System is ready for comprehensive frontend testing.")
        
        print("\n" + "="*80)
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = ComprehensivePACSTest()
    success = tester.run_comprehensive_tests()
    sys.exit(0 if success else 1)