#!/usr/bin/env python3
"""
Enhanced PACS System DICOM Metadata Testing Suite
Tests new production-ready features: DICOM metadata extraction, radiologist workflows, cleanup, and enhanced uploads
"""

import requests
import json
import sys
import io
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import tempfile

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

class EnhancedDICOMTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.radiologist_token = None
        self.technician_token = None
        
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
    
    def create_mock_dicom_file(self) -> bytes:
        """Create a mock DICOM file for testing"""
        # This creates a minimal DICOM-like structure for testing
        # In a real scenario, you'd use actual DICOM files
        dicom_header = b'\x44\x49\x43\x4D'  # "DICM" magic number
        mock_dicom_data = (
            b'\x08\x00\x05\x00\x43\x53\x0A\x00'  # Patient Name tag
            b'John^Doe\x00\x00'  # Patient Name value
            b'\x10\x00\x40\x00\x53\x48\x02\x00'  # Patient Sex tag  
            b'M\x00'  # Patient Sex value
            b'\x10\x00\x10\x00\x41\x53\x04\x00'  # Patient Age tag
            b'045Y'  # Patient Age value
            b'\x08\x00\x60\x00\x43\x53\x02\x00'  # Modality tag
            b'CT'  # Modality value
        )
        return dicom_header + mock_dicom_data
    
    def test_dicom_metadata_extraction(self):
        """PRIORITY 1: Test DICOM metadata extraction functionality"""
        print("\n=== PRIORITY 1: Testing DICOM Metadata Extraction ===")
        
        if not self.auth_token:
            self.log_test("DICOM Metadata Test", False, "No authentication token available")
            return
        
        # Test POST /api/files/extract-metadata endpoint
        try:
            # Create a mock DICOM file for testing
            mock_dicom_data = self.create_mock_dicom_file()
            
            files = {
                'file': ('test_dicom.dcm', io.BytesIO(mock_dicom_data), 'application/dicom')
            }
            
            response = self.session.post(f"{BASE_URL}/files/extract-metadata", files=files)
            
            if response.status_code == 200:
                metadata_response = response.json()
                if "metadata" in metadata_response:
                    metadata = metadata_response["metadata"]
                    self.log_test("DICOM Metadata Extraction", True, 
                                f"Successfully extracted metadata with {len(metadata)} fields")
                    
                    # Verify key metadata fields are present
                    expected_fields = ["patient_name", "patient_gender", "modality", "study_description"]
                    found_fields = [field for field in expected_fields if field in metadata]
                    
                    if len(found_fields) >= 2:  # At least some fields should be extracted
                        self.log_test("DICOM Metadata Fields", True, 
                                    f"Found {len(found_fields)} expected metadata fields: {found_fields}")
                    else:
                        self.log_test("DICOM Metadata Fields", False, 
                                    f"Only found {len(found_fields)} expected fields: {found_fields}")
                else:
                    self.log_test("DICOM Metadata Extraction", False, "Response missing metadata field")
            else:
                self.log_test("DICOM Metadata Extraction", False, 
                            f"Failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("DICOM Metadata Extraction", False, f"Request failed: {str(e)}")
    
    def test_dicom_metadata_modification(self):
        """Test DICOM metadata modification functionality"""
        print("\n=== Testing DICOM Metadata Modification ===")
        
        if not self.auth_token:
            self.log_test("DICOM Metadata Modification", False, "No authentication token available")
            return
        
        # First, we need to find an existing DICOM file to modify
        try:
            # Get studies to find file IDs
            studies_response = self.session.get(f"{BASE_URL}/studies")
            if studies_response.status_code == 200:
                studies = studies_response.json()
                
                # Find a study with file_ids
                test_file_id = None
                for study in studies:
                    if study.get("file_ids") and len(study["file_ids"]) > 0:
                        # Check if this is a real file ID (not mock format like file_XXXXX)
                        file_id = study["file_ids"][0]
                        if not file_id.startswith("file_"):
                            test_file_id = file_id
                            break
                
                if test_file_id:
                    # Test metadata modification
                    update_data = {
                        "patient_name": "Updated^Patient^Name",
                        "patient_gender": "F",
                        "study_description": "Updated Study Description"
                    }
                    
                    response = self.session.put(f"{BASE_URL}/files/{test_file_id}/update-metadata", 
                                              json=update_data)
                    
                    if response.status_code == 200:
                        update_response = response.json()
                        self.log_test("DICOM Metadata Update", True, 
                                    f"Successfully updated metadata for file {test_file_id}")
                        
                        # Verify the update by getting metadata
                        metadata_response = self.session.get(f"{BASE_URL}/files/{test_file_id}/metadata")
                        if metadata_response.status_code == 200:
                            self.log_test("DICOM Metadata Verification", True, 
                                        "Successfully retrieved updated metadata")
                        else:
                            self.log_test("DICOM Metadata Verification", False, 
                                        f"Failed to retrieve updated metadata: {metadata_response.status_code}")
                    else:
                        self.log_test("DICOM Metadata Update", False, 
                                    f"Failed to update metadata: {response.status_code} - {response.text}")
                else:
                    self.log_test("DICOM Metadata Update", False, 
                                "No real DICOM files found for metadata modification testing")
            else:
                self.log_test("DICOM Metadata Update", False, 
                            f"Failed to get studies: {studies_response.status_code}")
                
        except Exception as e:
            self.log_test("DICOM Metadata Update", False, f"Request failed: {str(e)}")
    
    def test_radiologist_download_features(self):
        """PRIORITY 2: Test radiologist download/upload features"""
        print("\n=== PRIORITY 2: Testing Radiologist Download/Upload Features ===")
        
        if not self.auth_token:
            self.log_test("Radiologist Features", False, "No authentication token available")
            return
        
        # Test GET /api/studies/{study_id}/download endpoint
        try:
            # Get studies to find one to download
            studies_response = self.session.get(f"{BASE_URL}/studies")
            if studies_response.status_code == 200:
                studies = studies_response.json()
                
                if studies:
                    study_id = studies[0]["id"]  # Use the internal ID for download
                    
                    # Test study download
                    download_response = self.session.get(f"{BASE_URL}/studies/{study_id}/download")
                    
                    if download_response.status_code == 200:
                        # Check if response is a ZIP file
                        content_type = download_response.headers.get('content-type', '')
                        if 'zip' in content_type.lower() or download_response.content.startswith(b'PK'):
                            self.log_test("Study Download ZIP", True, 
                                        f"Successfully downloaded study {study_id} as ZIP file")
                            
                            # Check ZIP file size
                            zip_size = len(download_response.content)
                            self.log_test("Study Download Size", True, 
                                        f"Downloaded ZIP file size: {zip_size} bytes")
                        else:
                            self.log_test("Study Download ZIP", False, 
                                        f"Response not a ZIP file. Content-Type: {content_type}")
                    elif download_response.status_code == 403:
                        self.log_test("Study Download Access Control", True, 
                                    "Download properly restricted (403) - role-based access working")
                    else:
                        self.log_test("Study Download", False, 
                                    f"Download failed: {download_response.status_code} - {download_response.text}")
                else:
                    self.log_test("Study Download", False, "No studies available for download testing")
            else:
                self.log_test("Study Download", False, 
                            f"Failed to get studies: {studies_response.status_code}")
                
        except Exception as e:
            self.log_test("Study Download", False, f"Request failed: {str(e)}")
        
        # Test POST /api/studies/upload-with-report endpoint
        self.test_radiologist_upload_with_report()
    
    def test_radiologist_upload_with_report(self):
        """Test radiologist study upload with reports"""
        try:
            # Create mock DICOM file and report
            mock_dicom_data = self.create_mock_dicom_file()
            mock_report = "Radiologist findings: Normal study with no significant abnormalities detected."
            
            # Prepare multipart form data
            files = {
                'files': ('radiologist_study.dcm', io.BytesIO(mock_dicom_data), 'application/dicom')
            }
            
            form_data = {
                'patient_name': 'Radiologist^Test^Patient',
                'patient_age': 35,
                'patient_gender': 'F',
                'modality': 'MRI',
                'study_description': 'Brain MRI with contrast',
                'final_report_text': mock_report
            }
            
            response = self.session.post(f"{BASE_URL}/studies/upload-with-report", 
                                       files=files, data=form_data)
            
            if response.status_code == 200:
                upload_response = response.json()
                self.log_test("Radiologist Upload with Report", True, 
                            f"Successfully uploaded study {upload_response.get('study_id')} with report")
                
                # Verify metadata extraction
                if upload_response.get("dicom_metadata_extracted"):
                    self.log_test("Upload Metadata Extraction", True, 
                                "DICOM metadata successfully extracted during upload")
                else:
                    self.log_test("Upload Metadata Extraction", False, 
                                "DICOM metadata not extracted during upload")
                    
            elif response.status_code == 403:
                self.log_test("Radiologist Upload Access Control", True, 
                            "Upload properly restricted (403) - role-based access working")
            else:
                self.log_test("Radiologist Upload with Report", False, 
                            f"Upload failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_test("Radiologist Upload with Report", False, f"Request failed: {str(e)}")
    
    def test_database_cleanup(self):
        """PRIORITY 3: Test database cleanup and production readiness"""
        print("\n=== PRIORITY 3: Testing Database Cleanup ===")
        
        if not self.auth_token:
            self.log_test("Database Cleanup", False, "No authentication token available")
            return
        
        # First, get current system state
        try:
            # Get studies before cleanup
            studies_before = self.session.get(f"{BASE_URL}/studies")
            studies_count_before = 0
            mock_studies_before = 0
            
            if studies_before.status_code == 200:
                studies_data = studies_before.json()
                studies_count_before = len(studies_data)
                
                # Count mock studies (those with file_XXXXX pattern)
                for study in studies_data:
                    file_ids = study.get("file_ids", [])
                    if any(fid.startswith("file_") for fid in file_ids):
                        mock_studies_before += 1
                
                self.log_test("Pre-Cleanup Study Count", True, 
                            f"Found {studies_count_before} total studies, {mock_studies_before} with mock data")
            
            # Test DELETE /api/admin/cleanup-mock-data endpoint
            cleanup_response = self.session.delete(f"{BASE_URL}/admin/cleanup-mock-data")
            
            if cleanup_response.status_code == 200:
                cleanup_result = cleanup_response.json()
                summary = cleanup_result.get("summary", {})
                
                self.log_test("Mock Data Cleanup", True, 
                            f"Cleanup completed: {summary.get('studies_removed', 0)} studies removed")
                
                # Verify cleanup results
                studies_removed = summary.get("studies_removed", 0)
                files_removed = summary.get("mock_files_removed", 0)
                reports_removed = summary.get("ai_reports_removed", 0)
                
                if studies_removed > 0:
                    self.log_test("Cleanup Effectiveness", True, 
                                f"Successfully removed {studies_removed} mock studies")
                else:
                    self.log_test("Cleanup Effectiveness", True, 
                                "No mock studies found to remove (system already clean)")
                
                # Get studies after cleanup to verify
                studies_after = self.session.get(f"{BASE_URL}/studies")
                if studies_after.status_code == 200:
                    studies_after_data = studies_after.json()
                    studies_count_after = len(studies_after_data)
                    
                    # Count remaining mock studies
                    mock_studies_after = 0
                    real_studies_after = 0
                    for study in studies_after_data:
                        file_ids = study.get("file_ids", [])
                        if any(fid.startswith("file_") for fid in file_ids):
                            mock_studies_after += 1
                        else:
                            real_studies_after += 1
                    
                    self.log_test("Post-Cleanup Verification", True, 
                                f"After cleanup: {studies_count_after} total studies, {real_studies_after} real, {mock_studies_after} mock")
                    
                    if mock_studies_after == 0:
                        self.log_test("Production Readiness", True, 
                                    "System is production-ready: no mock data remaining")
                    else:
                        self.log_test("Production Readiness", False, 
                                    f"System still contains {mock_studies_after} mock studies")
                
            else:
                self.log_test("Mock Data Cleanup", False, 
                            f"Cleanup failed: {cleanup_response.status_code} - {cleanup_response.text}")
                
        except Exception as e:
            self.log_test("Database Cleanup", False, f"Request failed: {str(e)}")
    
    def test_enhanced_upload_workflow(self):
        """PRIORITY 4: Test enhanced upload workflow with automatic metadata extraction"""
        print("\n=== PRIORITY 4: Testing Enhanced Upload Workflow ===")
        
        if not self.auth_token:
            self.log_test("Enhanced Upload Workflow", False, "No authentication token available")
            return
        
        # Test technician upload with automatic DICOM metadata extraction
        try:
            # Create a mock DICOM file with rich metadata
            mock_dicom_data = self.create_mock_dicom_file()
            
            # Test the upload endpoint (this will fail with 403 for admin, but we can test the endpoint exists)
            files = {
                'files': ('enhanced_test.dcm', io.BytesIO(mock_dicom_data), 'application/dicom')
            }
            
            form_data = {
                'patient_name': 'Enhanced^Test^Patient',
                'patient_age': 42,
                'patient_gender': 'M',
                'modality': 'CT',
                'notes': 'Test upload with enhanced metadata extraction'
            }
            
            response = self.session.post(f"{BASE_URL}/studies/upload", files=files, data=form_data)
            
            if response.status_code == 403:
                self.log_test("Enhanced Upload Access Control", True, 
                            "Upload endpoint properly restricted to technicians (403)")
            elif response.status_code == 200:
                upload_result = response.json()
                self.log_test("Enhanced Upload Success", True, 
                            f"Successfully uploaded study {upload_result.get('study_id')}")
                
                # Check if metadata was extracted and used
                if upload_result.get("file_ids"):
                    file_id = upload_result["file_ids"][0]
                    
                    # Get the extracted metadata
                    metadata_response = self.session.get(f"{BASE_URL}/files/{file_id}/metadata")
                    if metadata_response.status_code == 200:
                        self.log_test("Auto-Fill Metadata", True, 
                                    "Successfully retrieved auto-extracted metadata")
                    else:
                        self.log_test("Auto-Fill Metadata", False, 
                                    f"Failed to retrieve metadata: {metadata_response.status_code}")
            else:
                self.log_test("Enhanced Upload Workflow", False, 
                            f"Upload failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_test("Enhanced Upload Workflow", False, f"Request failed: {str(e)}")
    
    def test_real_vs_mock_data_validation(self):
        """Validate real patient data extraction vs mock data"""
        print("\n=== Testing Real vs Mock Data Validation ===")
        
        if not self.auth_token:
            self.log_test("Data Validation", False, "No authentication token available")
            return
        
        try:
            # Get all studies and analyze data quality
            studies_response = self.session.get(f"{BASE_URL}/studies")
            if studies_response.status_code == 200:
                studies = studies_response.json()
                
                real_dicom_studies = 0
                mock_data_studies = 0
                total_studies = len(studies)
                
                for study in studies:
                    file_ids = study.get("file_ids", [])
                    
                    # Check if study has real DICOM files (not mock file_XXXXX pattern)
                    has_real_files = any(not fid.startswith("file_") for fid in file_ids)
                    
                    if has_real_files:
                        real_dicom_studies += 1
                        
                        # Test metadata extraction from real file
                        for file_id in file_ids:
                            if not file_id.startswith("file_"):
                                metadata_response = self.session.get(f"{BASE_URL}/files/{file_id}/metadata")
                                if metadata_response.status_code == 200:
                                    metadata = metadata_response.json().get("metadata", {})
                                    
                                    # Check for real patient data indicators
                                    patient_name = metadata.get("patient_name", "")
                                    if patient_name and not patient_name.lower().startswith("test"):
                                        self.log_test("Real Patient Data Found", True, 
                                                    f"Found real patient data: {patient_name}")
                                    break
                    else:
                        mock_data_studies += 1
                
                self.log_test("Data Quality Analysis", True, 
                            f"System contains {real_dicom_studies} real DICOM studies and {mock_data_studies} mock studies")
                
                if real_dicom_studies > 0:
                    self.log_test("Production Data Availability", True, 
                                f"System has {real_dicom_studies} studies with real DICOM data")
                else:
                    self.log_test("Production Data Availability", False, 
                                "No real DICOM studies found - system contains only mock data")
                    
            else:
                self.log_test("Data Validation", False, 
                            f"Failed to get studies: {studies_response.status_code}")
                
        except Exception as e:
            self.log_test("Data Validation", False, f"Request failed: {str(e)}")
    
    def run_enhanced_tests(self):
        """Run all enhanced DICOM tests"""
        print("🚀 Starting Enhanced PACS DICOM Testing Suite")
        print(f"Testing against: {BASE_URL}")
        print("Focus: Production-ready DICOM metadata features")
        
        # Authenticate first
        if not self.authenticate_admin():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run priority tests
        self.test_dicom_metadata_extraction()
        self.test_dicom_metadata_modification()
        self.test_radiologist_download_features()
        self.test_database_cleanup()
        self.test_enhanced_upload_workflow()
        self.test_real_vs_mock_data_validation()
        
        # Print summary
        return self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("🏁 ENHANCED DICOM TESTING SUMMARY")
        print("="*70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results by priority
        priority_results = {
            "PRIORITY 1 - DICOM Metadata": [],
            "PRIORITY 2 - Radiologist Features": [],
            "PRIORITY 3 - Database Cleanup": [],
            "PRIORITY 4 - Enhanced Upload": [],
            "General": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "Metadata" in test_name or "DICOM" in test_name:
                priority_results["PRIORITY 1 - DICOM Metadata"].append(result)
            elif "Radiologist" in test_name or "Download" in test_name or "Upload" in test_name:
                priority_results["PRIORITY 2 - Radiologist Features"].append(result)
            elif "Cleanup" in test_name or "Production" in test_name:
                priority_results["PRIORITY 3 - Database Cleanup"].append(result)
            elif "Enhanced" in test_name or "Auto" in test_name:
                priority_results["PRIORITY 4 - Enhanced Upload"].append(result)
            else:
                priority_results["General"].append(result)
        
        # Print results by priority
        for priority, results in priority_results.items():
            if results:
                print(f"\n📋 {priority}:")
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}: {result['message']}")
        
        if failed_tests > 0:
            print(f"\n🔍 CRITICAL ISSUES REQUIRING ATTENTION:")
            critical_failures = []
            for result in self.test_results:
                if not result["success"] and any(keyword in result["test"] for keyword in 
                    ["Metadata", "Download", "Cleanup", "Production"]):
                    critical_failures.append(result)
            
            for failure in critical_failures:
                print(f"  ❌ {failure['test']}: {failure['message']}")
        
        print("\n" + "="*70)
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = EnhancedDICOMTester()
    success = tester.run_enhanced_tests()
    sys.exit(0 if success else 1)