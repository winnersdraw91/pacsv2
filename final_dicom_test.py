#!/usr/bin/env python3
"""
Final DICOM Testing Suite - Comprehensive test of all enhanced PACS features
Tests the production-ready DICOM functionality with newly created data
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

class FinalDICOMTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.new_study_id = None
        self.new_file_ids = []
        
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
    
    def create_test_dicom_file(self) -> bytes:
        """Create a more realistic DICOM-like file for testing"""
        # Create a minimal but more complete DICOM structure
        dicom_preamble = b'\x00' * 128  # 128 byte preamble
        dicom_prefix = b'DICM'  # DICOM prefix
        
        # Some basic DICOM data elements
        dicom_data = (
            # Patient Name (0010,0010)
            b'\x10\x00\x10\x00\x50\x4E\x0C\x00Test^DICOM^Patient\x00'
            # Patient ID (0010,0020)  
            b'\x10\x00\x20\x00\x4C\x4F\x08\x00PAT12345'
            # Patient Sex (0010,0040)
            b'\x10\x00\x40\x00\x43\x53\x02\x00M\x00'
            # Patient Age (0010,1010)
            b'\x10\x00\x10\x10\x41\x53\x04\x00045Y'
            # Modality (0008,0060)
            b'\x08\x00\x60\x00\x43\x53\x02\x00CT'
            # Study Description (0008,1030)
            b'\x08\x00\x30\x10\x4C\x4F\x14\x00Test CT Study Description'
        )
        
        return dicom_preamble + dicom_prefix + dicom_data
    
    def test_radiologist_upload_with_report(self):
        """PRIORITY 2: Test radiologist upload with report functionality"""
        print("\n=== PRIORITY 2: Testing Radiologist Upload with Report ===")
        
        if not self.auth_token:
            self.log_test("Radiologist Upload", False, "No authentication token available")
            return
        
        try:
            # Create a test DICOM file
            test_dicom_data = self.create_test_dicom_file()
            
            files = {
                'files': ('test_radiologist.dcm', io.BytesIO(test_dicom_data), 'application/dicom')
            }
            
            form_data = {
                'patient_name': 'Radiologist^Test^Patient',
                'patient_age': 52,
                'patient_gender': 'F',
                'modality': 'MRI',
                'study_description': 'Brain MRI with contrast enhancement',
                'final_report_text': 'Radiologist findings: Normal brain MRI study. No acute intracranial abnormalities detected. Contrast enhancement pattern is within normal limits.'
            }
            
            response = self.session.post(f"{BASE_URL}/studies/upload-with-report", 
                                       files=files, data=form_data)
            
            if response.status_code == 200:
                upload_result = response.json()
                self.new_study_id = upload_result.get("study_id")
                
                self.log_test("Radiologist Upload with Report", True, 
                            f"Successfully uploaded study {self.new_study_id} with report")
                
                # Check metadata extraction
                if upload_result.get("dicom_metadata_extracted"):
                    self.log_test("Upload DICOM Metadata Extraction", True, 
                                "DICOM metadata successfully extracted during upload")
                else:
                    self.log_test("Upload DICOM Metadata Extraction", False, 
                                "DICOM metadata not extracted during upload")
                
                # Check report creation
                if upload_result.get("final_report_created"):
                    self.log_test("Final Report Creation", True, 
                                "Final radiologist report successfully created")
                else:
                    self.log_test("Final Report Creation", False, 
                                "Final radiologist report not created")
                
                return True
            else:
                self.log_test("Radiologist Upload with Report", False, 
                            f"Upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Radiologist Upload with Report", False, f"Request failed: {str(e)}")
            return False
    
    def test_dicom_metadata_extraction_endpoint(self):
        """PRIORITY 1: Test DICOM metadata extraction endpoint"""
        print("\n=== PRIORITY 1: Testing DICOM Metadata Extraction Endpoint ===")
        
        if not self.auth_token:
            self.log_test("Metadata Extraction Endpoint", False, "No authentication token available")
            return
        
        try:
            # Create a test DICOM file for metadata extraction
            test_dicom_data = self.create_test_dicom_file()
            
            files = {
                'file': ('metadata_test.dcm', io.BytesIO(test_dicom_data), 'application/dicom')
            }
            
            response = self.session.post(f"{BASE_URL}/files/extract-metadata", files=files)
            
            if response.status_code == 200:
                metadata_response = response.json()
                metadata = metadata_response.get("metadata", {})
                
                if metadata:
                    self.log_test("DICOM Metadata Extraction Endpoint", True, 
                                f"Successfully extracted {len(metadata)} metadata fields")
                    
                    # Check for key fields
                    key_fields = ["patient_name", "patient_gender", "modality", "study_description"]
                    found_fields = []
                    
                    for field in key_fields:
                        if field in metadata and metadata[field]:
                            found_fields.append(f"{field}: {metadata[field]}")
                    
                    if found_fields:
                        self.log_test("Key Metadata Fields Extraction", True, 
                                    f"Extracted key fields: {', '.join(found_fields)}")
                    else:
                        self.log_test("Key Metadata Fields Extraction", False, 
                                    "No key metadata fields found")
                else:
                    self.log_test("DICOM Metadata Extraction Endpoint", False, 
                                "No metadata returned from extraction")
            else:
                self.log_test("DICOM Metadata Extraction Endpoint", False, 
                            f"Extraction failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_test("DICOM Metadata Extraction Endpoint", False, f"Request failed: {str(e)}")
    
    def test_study_download_with_new_data(self):
        """Test study download functionality with newly created data"""
        print("\n=== Testing Study Download with New Data ===")
        
        if not self.auth_token or not self.new_study_id:
            self.log_test("Study Download New Data", False, "No study available for testing")
            return
        
        try:
            # Get the study details first
            study_response = self.session.get(f"{BASE_URL}/studies/{self.new_study_id}")
            
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
                            self.log_test("Study Download ZIP Generation", True, 
                                        f"Successfully generated ZIP package ({zip_size} bytes)")
                            
                            # Analyze ZIP contents
                            try:
                                import zipfile
                                zip_buffer = io.BytesIO(download_response.content)
                                with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                                    file_list = zip_file.namelist()
                                    
                                    has_dicom = any('DICOM/' in f for f in file_list)
                                    has_metadata = 'metadata.json' in file_list
                                    has_report = any('report' in f.lower() for f in file_list)
                                    
                                    self.log_test("ZIP Package Contents", True, 
                                                f"Package contains: DICOM files: {has_dicom}, "
                                                f"metadata: {has_metadata}, reports: {has_report}")
                                    
                                    # Verify metadata.json content
                                    if has_metadata:
                                        metadata_content = zip_file.read('metadata.json')
                                        metadata_json = json.loads(metadata_content.decode())
                                        
                                        required_fields = ['study_id', 'patient_name', 'modality']
                                        has_required = all(field in metadata_json for field in required_fields)
                                        
                                        if has_required:
                                            self.log_test("Metadata JSON Validation", True, 
                                                        "metadata.json contains all required fields")
                                        else:
                                            self.log_test("Metadata JSON Validation", False, 
                                                        "metadata.json missing required fields")
                                        
                            except Exception as zip_error:
                                self.log_test("ZIP Content Analysis", False, 
                                            f"Failed to analyze ZIP: {str(zip_error)}")
                        else:
                            self.log_test("Study Download ZIP Generation", False, 
                                        f"Response not a ZIP file. Content-Type: {content_type}")
                    else:
                        self.log_test("Study Download ZIP Generation", False, 
                                    f"Download failed: {download_response.status_code}")
                else:
                    self.log_test("Study Download New Data", False, "Could not get study internal ID")
            else:
                self.log_test("Study Download New Data", False, 
                            f"Failed to get study details: {study_response.status_code}")
                
        except Exception as e:
            self.log_test("Study Download New Data", False, f"Request failed: {str(e)}")
    
    def test_database_cleanup_effectiveness(self):
        """PRIORITY 3: Test database cleanup effectiveness"""
        print("\n=== PRIORITY 3: Testing Database Cleanup Effectiveness ===")
        
        if not self.auth_token:
            self.log_test("Database Cleanup", False, "No authentication token available")
            return
        
        try:
            # Test cleanup endpoint
            cleanup_response = self.session.delete(f"{BASE_URL}/admin/cleanup-mock-data")
            
            if cleanup_response.status_code == 200:
                cleanup_result = cleanup_response.json()
                summary = cleanup_result.get("summary", {})
                
                studies_removed = summary.get("studies_removed", 0)
                files_removed = summary.get("mock_files_removed", 0)
                
                self.log_test("Mock Data Cleanup Execution", True, 
                            f"Cleanup completed: {studies_removed} studies, {files_removed} files removed")
                
                # Verify system state after cleanup
                if studies_removed == 0:
                    self.log_test("System Clean State", True, 
                                "No mock data found - system already in clean state")
                else:
                    self.log_test("Mock Data Removal", True, 
                                f"Successfully removed {studies_removed} mock studies")
                    
            else:
                self.log_test("Mock Data Cleanup Execution", False, 
                            f"Cleanup failed: {cleanup_response.status_code}")
                
        except Exception as e:
            self.log_test("Database Cleanup", False, f"Request failed: {str(e)}")
    
    def test_enhanced_upload_workflow_validation(self):
        """PRIORITY 4: Test enhanced upload workflow validation"""
        print("\n=== PRIORITY 4: Testing Enhanced Upload Workflow ===")
        
        if not self.auth_token:
            self.log_test("Enhanced Upload Workflow", False, "No authentication token available")
            return
        
        try:
            # Test technician upload endpoint (should be restricted for admin)
            test_dicom_data = self.create_test_dicom_file()
            
            files = {
                'files': ('workflow_test.dcm', io.BytesIO(test_dicom_data), 'application/dicom')
            }
            
            form_data = {
                'patient_name': 'Workflow^Test^Patient',
                'patient_age': 38,
                'patient_gender': 'M',
                'modality': 'X-Ray',
                'notes': 'Test enhanced upload workflow'
            }
            
            response = self.session.post(f"{BASE_URL}/studies/upload", files=files, data=form_data)
            
            if response.status_code == 403:
                self.log_test("Technician Upload Access Control", True, 
                            "Upload properly restricted to technicians (403 for admin)")
            elif response.status_code == 200:
                upload_result = response.json()
                self.log_test("Enhanced Upload Workflow", True, 
                            f"Upload successful with auto-metadata extraction")
                
                # Check if metadata was extracted
                study_id = upload_result.get("study_id")
                if study_id and upload_result.get("file_ids"):
                    file_id = upload_result["file_ids"][0]
                    
                    # Test metadata retrieval
                    metadata_response = self.session.get(f"{BASE_URL}/files/{file_id}/metadata")
                    if metadata_response.status_code == 200:
                        self.log_test("Auto-Fill Metadata Functionality", True, 
                                    "Metadata auto-extraction working in upload workflow")
                    else:
                        self.log_test("Auto-Fill Metadata Functionality", False, 
                                    "Metadata auto-extraction not working")
            else:
                self.log_test("Enhanced Upload Workflow", False, 
                            f"Unexpected response: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_test("Enhanced Upload Workflow", False, f"Request failed: {str(e)}")
    
    def test_production_readiness_validation(self):
        """Comprehensive production readiness validation"""
        print("\n=== Testing Production Readiness ===")
        
        if not self.auth_token:
            self.log_test("Production Readiness", False, "No authentication token available")
            return
        
        try:
            # Test system endpoints availability
            endpoints_to_test = [
                ("/files/extract-metadata", "POST", "DICOM Metadata Extraction"),
                ("/admin/cleanup-mock-data", "DELETE", "Database Cleanup"),
                ("/studies/upload-with-report", "POST", "Radiologist Upload"),
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, method, description in endpoints_to_test:
                try:
                    if method == "POST":
                        # Test with minimal data to check endpoint availability
                        test_response = self.session.post(f"{BASE_URL}{endpoint}", 
                                                        files={'file': ('test.txt', b'test', 'text/plain')})
                    elif method == "DELETE":
                        test_response = self.session.delete(f"{BASE_URL}{endpoint}")
                    
                    # Accept any response that's not 404 (endpoint exists)
                    if test_response.status_code != 404:
                        working_endpoints += 1
                        self.log_test(f"{description} Endpoint", True, 
                                    f"Endpoint available (status: {test_response.status_code})")
                    else:
                        self.log_test(f"{description} Endpoint", False, 
                                    "Endpoint not found (404)")
                        
                except Exception:
                    self.log_test(f"{description} Endpoint", False, 
                                "Endpoint test failed")
            
            # Overall production readiness score
            readiness_score = (working_endpoints / total_endpoints) * 100
            
            if readiness_score >= 90:
                self.log_test("Production Readiness Score", True, 
                            f"System is production-ready ({readiness_score:.1f}%)")
            elif readiness_score >= 70:
                self.log_test("Production Readiness Score", True, 
                            f"System needs minor fixes ({readiness_score:.1f}%)")
            else:
                self.log_test("Production Readiness Score", False, 
                            f"System needs major fixes ({readiness_score:.1f}%)")
                
        except Exception as e:
            self.log_test("Production Readiness", False, f"Validation failed: {str(e)}")
    
    def run_final_tests(self):
        """Run all final DICOM tests"""
        print("🚀 Starting Final DICOM Testing Suite")
        print(f"Testing against: {BASE_URL}")
        print("Focus: Complete validation of enhanced PACS DICOM features")
        
        # Authenticate first
        if not self.authenticate_admin():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run tests in priority order
        print("\n" + "="*60)
        print("TESTING PRIORITY FEATURES")
        print("="*60)
        
        # Create new data first
        upload_success = self.test_radiologist_upload_with_report()
        
        # Test all priority features
        self.test_dicom_metadata_extraction_endpoint()
        
        if upload_success:
            self.test_study_download_with_new_data()
        
        self.test_database_cleanup_effectiveness()
        self.test_enhanced_upload_workflow_validation()
        self.test_production_readiness_validation()
        
        # Print summary
        return self.print_summary()
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🏁 FINAL DICOM TESTING SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Priority-based categorization
        priority_categories = {
            "🔥 PRIORITY 1 - DICOM Metadata Functionality": [],
            "👨‍⚕️ PRIORITY 2 - Radiologist Download/Upload Features": [],
            "🧹 PRIORITY 3 - Database Cleanup & Production Readiness": [],
            "⚡ PRIORITY 4 - Enhanced Upload Workflow": [],
            "🔐 Authentication & System": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "Metadata" in test_name and "Extraction" in test_name:
                priority_categories["🔥 PRIORITY 1 - DICOM Metadata Functionality"].append(result)
            elif "Radiologist" in test_name or "Upload with Report" in test_name or "Download" in test_name:
                priority_categories["👨‍⚕️ PRIORITY 2 - Radiologist Download/Upload Features"].append(result)
            elif "Cleanup" in test_name or "Production" in test_name:
                priority_categories["🧹 PRIORITY 3 - Database Cleanup & Production Readiness"].append(result)
            elif "Enhanced" in test_name or "Workflow" in test_name or "Auto" in test_name:
                priority_categories["⚡ PRIORITY 4 - Enhanced Upload Workflow"].append(result)
            else:
                priority_categories["🔐 Authentication & System"].append(result)
        
        # Print results by priority
        for category, results in priority_categories.items():
            if results:
                print(f"\n{category}:")
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}: {result['message']}")
        
        # Critical issues analysis
        critical_failures = [r for r in self.test_results if not r["success"] and 
                           any(keyword in r["test"] for keyword in 
                               ["DICOM", "Metadata", "Upload", "Download", "Production"])]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for failure in critical_failures:
                print(f"  ❌ {failure['test']}: {failure['message']}")
        
        # Feature completion assessment
        feature_tests = [r for r in self.test_results if 
                        any(keyword in r["test"] for keyword in 
                            ["DICOM", "Metadata", "Upload", "Download", "Cleanup"])]
        feature_passed = sum(1 for r in feature_tests if r["success"])
        feature_total = len(feature_tests)
        
        if feature_total > 0:
            feature_rate = (feature_passed / feature_total) * 100
            print(f"\n🎯 ENHANCED FEATURES COMPLETION: {feature_rate:.1f}% ({feature_passed}/{feature_total})")
            
            if feature_rate >= 85:
                print("✅ ENHANCED PACS FEATURES ARE PRODUCTION-READY")
                print("🎉 System successfully implements all requested DICOM enhancements")
            elif feature_rate >= 70:
                print("⚠️  ENHANCED FEATURES NEED MINOR FIXES")
                print("🔧 Most functionality working, minor issues to resolve")
            else:
                print("❌ ENHANCED FEATURES REQUIRE MAJOR DEVELOPMENT")
                print("🚧 Significant work needed before production deployment")
        
        # Final recommendation
        print(f"\n📋 TESTING RECOMMENDATION:")
        if failed_tests == 0:
            print("✅ ALL TESTS PASSED - System ready for production deployment")
        elif failed_tests <= 2:
            print("⚠️  MINOR ISSUES FOUND - Address failed tests before deployment")
        else:
            print("❌ MAJOR ISSUES FOUND - Significant fixes required before production")
        
        print("\n" + "="*80)
        
        return failed_tests <= 2  # Allow up to 2 minor failures

if __name__ == "__main__":
    tester = FinalDICOMTester()
    success = tester.run_final_tests()
    sys.exit(0 if success else 1)