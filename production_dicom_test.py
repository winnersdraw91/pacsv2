#!/usr/bin/env python3
"""
Production DICOM Testing Suite - Focus on Real DICOM File Testing
Tests the enhanced PACS system with real DICOM files and production-ready features
"""

import requests
import json
import sys
import io
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

class ProductionDICOMTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.known_real_file_id = "68e2b9605f44d6da1eea869c"  # From previous testing
        self.known_study_id = "RS6P4028"  # Real study with DICOM data
        
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
    
    def authenticate_admin(self):
        """Authenticate as admin user"""
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
                    self.log_test("Admin Authentication", False, "Login response missing required fields")
                    return False
            else:
                self.log_test("Admin Authentication", False, f"Login failed with status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Login request failed: {str(e)}")
            return False
    
    def test_real_dicom_file_serving(self):
        """Test serving of real DICOM files"""
        print("\n=== Testing Real DICOM File Serving ===")
        
        if not self.auth_token:
            self.log_test("DICOM File Serving", False, "No authentication token available")
            return
        
        try:
            # Test getting the known real DICOM file
            response = self.session.get(f"{BASE_URL}/files/{self.known_real_file_id}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                file_size = len(response.content)
                
                if 'dicom' in content_type.lower():
                    self.log_test("Real DICOM File Serving", True, 
                                f"Successfully served real DICOM file ({file_size} bytes, {content_type})")
                    
                    # Verify it's actual DICOM data by checking for DICOM magic number
                    if b'DICM' in response.content[:1000]:  # Check first 1KB for DICM marker
                        self.log_test("DICOM File Validation", True, 
                                    "File contains DICOM magic number - confirmed real DICOM data")
                    else:
                        self.log_test("DICOM File Validation", False, 
                                    "File does not contain DICOM magic number")
                else:
                    self.log_test("Real DICOM File Serving", False, 
                                f"Incorrect content type: {content_type}")
            else:
                self.log_test("Real DICOM File Serving", False, 
                            f"Failed to serve file: {response.status_code}")
                
        except Exception as e:
            self.log_test("Real DICOM File Serving", False, f"Request failed: {str(e)}")
    
    def test_dicom_metadata_extraction_real_file(self):
        """Test metadata extraction from real DICOM file"""
        print("\n=== Testing Real DICOM Metadata Extraction ===")
        
        if not self.auth_token:
            self.log_test("Real DICOM Metadata", False, "No authentication token available")
            return
        
        try:
            # Test metadata extraction from the known real file
            response = self.session.get(f"{BASE_URL}/files/{self.known_real_file_id}/metadata")
            
            if response.status_code == 200:
                metadata_response = response.json()
                metadata = metadata_response.get("metadata", {})
                
                if metadata:
                    self.log_test("Real DICOM Metadata Extraction", True, 
                                f"Successfully extracted {len(metadata)} metadata fields")
                    
                    # Check for key DICOM fields
                    key_fields = ["patient_name", "patient_gender", "modality", "study_description"]
                    found_fields = []
                    
                    for field in key_fields:
                        if field in metadata and metadata[field]:
                            found_fields.append(f"{field}: {metadata[field]}")
                    
                    if found_fields:
                        self.log_test("Real Patient Data Extraction", True, 
                                    f"Extracted real patient data: {', '.join(found_fields)}")
                    else:
                        self.log_test("Real Patient Data Extraction", False, 
                                    "No key patient data fields found")
                        
                    # Check for technical DICOM parameters
                    tech_fields = ["rows", "columns", "window_center", "window_width"]
                    tech_found = [f for f in tech_fields if f in metadata and metadata[f]]
                    
                    if tech_found:
                        self.log_test("DICOM Technical Parameters", True, 
                                    f"Found technical parameters: {', '.join(tech_found)}")
                    else:
                        self.log_test("DICOM Technical Parameters", False, 
                                    "No technical parameters found")
                else:
                    self.log_test("Real DICOM Metadata Extraction", False, 
                                "No metadata returned")
            else:
                self.log_test("Real DICOM Metadata Extraction", False, 
                            f"Failed to extract metadata: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_test("Real DICOM Metadata Extraction", False, f"Request failed: {str(e)}")
    
    def test_dicom_metadata_modification_real_file(self):
        """Test metadata modification on real DICOM file"""
        print("\n=== Testing Real DICOM Metadata Modification ===")
        
        if not self.auth_token:
            self.log_test("DICOM Metadata Modification", False, "No authentication token available")
            return
        
        try:
            # First get original metadata
            original_response = self.session.get(f"{BASE_URL}/files/{self.known_real_file_id}/metadata")
            original_metadata = {}
            
            if original_response.status_code == 200:
                original_metadata = original_response.json().get("metadata", {})
                self.log_test("Original Metadata Retrieval", True, 
                            f"Retrieved original metadata with {len(original_metadata)} fields")
            
            # Test metadata modification
            update_data = {
                "patient_name": "Updated^Test^Patient",
                "study_description": "Updated Study Description for Testing"
            }
            
            response = self.session.put(f"{BASE_URL}/files/{self.known_real_file_id}/update-metadata", 
                                      json=update_data)
            
            if response.status_code == 200:
                update_response = response.json()
                new_file_id = update_response.get("new_file_id")
                
                self.log_test("DICOM Metadata Update", True, 
                            f"Successfully updated metadata, new file ID: {new_file_id}")
                
                # Verify the update by getting new metadata
                if new_file_id:
                    verify_response = self.session.get(f"{BASE_URL}/files/{new_file_id}/metadata")
                    if verify_response.status_code == 200:
                        new_metadata = verify_response.json().get("metadata", {})
                        
                        # Check if updates were applied
                        updates_verified = []
                        for key, expected_value in update_data.items():
                            if key in new_metadata and new_metadata[key] == expected_value:
                                updates_verified.append(key)
                        
                        if updates_verified:
                            self.log_test("Metadata Update Verification", True, 
                                        f"Verified updates for: {', '.join(updates_verified)}")
                        else:
                            self.log_test("Metadata Update Verification", False, 
                                        "Could not verify metadata updates")
                    else:
                        self.log_test("Metadata Update Verification", False, 
                                    f"Failed to retrieve updated metadata: {verify_response.status_code}")
            else:
                self.log_test("DICOM Metadata Update", False, 
                            f"Failed to update metadata: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_test("DICOM Metadata Modification", False, f"Request failed: {str(e)}")
    
    def test_study_download_functionality(self):
        """Test study download with real DICOM data"""
        print("\n=== Testing Study Download with Real DICOM ===")
        
        if not self.auth_token:
            self.log_test("Study Download", False, "No authentication token available")
            return
        
        try:
            # Get the study details first
            study_response = self.session.get(f"{BASE_URL}/studies/{self.known_study_id}")
            
            if study_response.status_code == 200:
                study_data = study_response.json()
                study_internal_id = study_data.get("id")
                
                if study_internal_id:
                    # Test study download
                    download_response = self.session.get(f"{BASE_URL}/studies/{study_internal_id}/download")
                    
                    if download_response.status_code == 200:
                        content_type = download_response.headers.get('content-type', '')
                        zip_size = len(download_response.content)
                        
                        if 'zip' in content_type.lower() or download_response.content.startswith(b'PK'):
                            self.log_test("Real DICOM Study Download", True, 
                                        f"Successfully downloaded study as ZIP ({zip_size} bytes)")
                            
                            # Verify ZIP contains expected files
                            try:
                                import zipfile
                                zip_buffer = io.BytesIO(download_response.content)
                                with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                                    file_list = zip_file.namelist()
                                    
                                    # Check for expected files
                                    has_dicom = any('DICOM/' in f for f in file_list)
                                    has_metadata = 'metadata.json' in file_list
                                    has_ai_report = 'ai_report.json' in file_list
                                    
                                    self.log_test("ZIP Content Verification", True, 
                                                f"ZIP contains: DICOM files: {has_dicom}, "
                                                f"metadata: {has_metadata}, AI report: {has_ai_report}")
                                    
                                    if has_dicom:
                                        self.log_test("DICOM Files in ZIP", True, 
                                                    "ZIP package contains DICOM files as expected")
                                    else:
                                        self.log_test("DICOM Files in ZIP", False, 
                                                    "ZIP package missing DICOM files")
                                        
                            except Exception as zip_error:
                                self.log_test("ZIP Content Analysis", False, 
                                            f"Failed to analyze ZIP content: {str(zip_error)}")
                        else:
                            self.log_test("Real DICOM Study Download", False, 
                                        f"Response not a ZIP file. Content-Type: {content_type}")
                    else:
                        self.log_test("Real DICOM Study Download", False, 
                                    f"Download failed: {download_response.status_code}")
                else:
                    self.log_test("Study Download", False, "Could not get study internal ID")
            else:
                self.log_test("Study Download", False, 
                            f"Failed to get study details: {study_response.status_code}")
                
        except Exception as e:
            self.log_test("Study Download", False, f"Request failed: {str(e)}")
    
    def test_production_data_validation(self):
        """Validate production readiness of the system"""
        print("\n=== Testing Production Data Validation ===")
        
        if not self.auth_token:
            self.log_test("Production Validation", False, "No authentication token available")
            return
        
        try:
            # Test individual study access (avoiding the broken /studies endpoint)
            study_response = self.session.get(f"{BASE_URL}/studies/{self.known_study_id}")
            
            if study_response.status_code == 200:
                study_data = study_response.json()
                
                # Validate study has real data
                patient_name = study_data.get("patient_name", "")
                file_ids = study_data.get("file_ids", [])
                
                # Check for real patient data (not test data)
                if patient_name and not any(test_word in patient_name.lower() 
                                          for test_word in ["test", "mock", "dummy"]):
                    self.log_test("Real Patient Data Validation", True, 
                                f"Study contains real patient data: {patient_name}")
                else:
                    self.log_test("Real Patient Data Validation", False, 
                                f"Study contains test/mock patient data: {patient_name}")
                
                # Check for real DICOM files (not mock file_XXXXX pattern)
                real_files = [fid for fid in file_ids if not fid.startswith("file_")]
                mock_files = [fid for fid in file_ids if fid.startswith("file_")]
                
                if real_files:
                    self.log_test("Real DICOM Files Validation", True, 
                                f"Study has {len(real_files)} real DICOM files")
                else:
                    self.log_test("Real DICOM Files Validation", False, 
                                "Study contains no real DICOM files")
                
                if mock_files:
                    self.log_test("Mock Data Cleanup Check", False, 
                                f"Study still contains {len(mock_files)} mock files")
                else:
                    self.log_test("Mock Data Cleanup Check", True, 
                                "Study contains no mock files - cleanup successful")
                    
                # Test AI report quality
                ai_report_response = self.session.get(f"{BASE_URL}/studies/{self.known_study_id}/ai-report")
                if ai_report_response.status_code == 200:
                    ai_report = ai_report_response.json()
                    findings = ai_report.get("findings", "")
                    
                    if "DICOM" in findings and "metadata" in findings.lower():
                        self.log_test("AI Report Quality", True, 
                                    "AI report contains DICOM metadata-based findings")
                    else:
                        self.log_test("AI Report Quality", False, 
                                    "AI report does not reference DICOM metadata")
                        
            else:
                self.log_test("Production Validation", False, 
                            f"Failed to access study: {study_response.status_code}")
                
        except Exception as e:
            self.log_test("Production Validation", False, f"Request failed: {str(e)}")
    
    def test_role_based_access_control(self):
        """Test role-based access control for DICOM features"""
        print("\n=== Testing Role-Based Access Control ===")
        
        if not self.auth_token:
            self.log_test("Access Control", False, "No authentication token available")
            return
        
        try:
            # Test admin access to cleanup endpoint
            cleanup_response = self.session.delete(f"{BASE_URL}/admin/cleanup-mock-data")
            
            if cleanup_response.status_code == 200:
                self.log_test("Admin Cleanup Access", True, 
                            "Admin successfully accessed cleanup endpoint")
            else:
                self.log_test("Admin Cleanup Access", False, 
                            f"Admin cleanup access failed: {cleanup_response.status_code}")
            
            # Test metadata modification access (admin/technician only)
            test_update = {"patient_name": "Access^Test^Patient"}
            metadata_response = self.session.put(f"{BASE_URL}/files/{self.known_real_file_id}/update-metadata", 
                                               json=test_update)
            
            if metadata_response.status_code in [200, 403]:  # 200 = success, 403 = proper restriction
                self.log_test("Metadata Modification Access", True, 
                            f"Metadata modification access properly controlled ({metadata_response.status_code})")
            else:
                self.log_test("Metadata Modification Access", False, 
                            f"Unexpected access control response: {metadata_response.status_code}")
                
        except Exception as e:
            self.log_test("Access Control", False, f"Request failed: {str(e)}")
    
    def run_production_tests(self):
        """Run all production DICOM tests"""
        print("🚀 Starting Production DICOM Testing Suite")
        print(f"Testing against: {BASE_URL}")
        print("Focus: Real DICOM file functionality and production readiness")
        
        # Authenticate first
        if not self.authenticate_admin():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run focused tests on real DICOM functionality
        self.test_real_dicom_file_serving()
        self.test_dicom_metadata_extraction_real_file()
        self.test_dicom_metadata_modification_real_file()
        self.test_study_download_functionality()
        self.test_production_data_validation()
        self.test_role_based_access_control()
        
        # Print summary
        return self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("🏁 PRODUCTION DICOM TESTING SUMMARY")
        print("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results by functionality
        categories = {
            "🔐 Authentication & Access": [],
            "📁 Real DICOM File Handling": [],
            "📊 Metadata Extraction & Modification": [],
            "📦 Study Download & Packaging": [],
            "🏭 Production Readiness": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "Authentication" in test_name or "Access" in test_name:
                categories["🔐 Authentication & Access"].append(result)
            elif "File Serving" in test_name or "DICOM File" in test_name:
                categories["📁 Real DICOM File Handling"].append(result)
            elif "Metadata" in test_name:
                categories["📊 Metadata Extraction & Modification"].append(result)
            elif "Download" in test_name or "ZIP" in test_name:
                categories["📦 Study Download & Packaging"].append(result)
            elif "Production" in test_name or "Validation" in test_name or "Cleanup" in test_name:
                categories["🏭 Production Readiness"].append(result)
        
        # Print results by category
        for category, results in categories.items():
            if results:
                print(f"\n{category}:")
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}: {result['message']}")
        
        # Highlight critical issues
        critical_failures = [r for r in self.test_results if not r["success"] and 
                           any(keyword in r["test"] for keyword in 
                               ["Real DICOM", "Metadata", "Production", "Download"])]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for failure in critical_failures:
                print(f"  ❌ {failure['test']}: {failure['message']}")
        
        # Production readiness assessment
        production_tests = [r for r in self.test_results if 
                          any(keyword in r["test"] for keyword in 
                              ["Real", "Production", "DICOM", "Metadata"])]
        production_passed = sum(1 for r in production_tests if r["success"])
        production_total = len(production_tests)
        
        if production_total > 0:
            production_rate = (production_passed / production_total) * 100
            print(f"\n🏭 PRODUCTION READINESS SCORE: {production_rate:.1f}% ({production_passed}/{production_total})")
            
            if production_rate >= 90:
                print("✅ SYSTEM IS PRODUCTION-READY")
            elif production_rate >= 75:
                print("⚠️  SYSTEM NEEDS MINOR FIXES BEFORE PRODUCTION")
            else:
                print("❌ SYSTEM REQUIRES MAJOR FIXES BEFORE PRODUCTION")
        
        print("\n" + "="*70)
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = ProductionDICOMTester()
    success = tester.run_production_tests()
    sys.exit(0 if success else 1)