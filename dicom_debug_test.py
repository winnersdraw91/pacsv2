#!/usr/bin/env python3
"""
DICOM File Serving Debug Test Suite
Investigates DICOM image display issues by testing file serving and study data
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import io

# Configuration
BASE_URL = "https://medimage.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@pacs.com"
ADMIN_PASSWORD = "admin123"

class DICOMDebugTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.studies_data = []
        self.real_dicom_files = []
        
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
    
    def priority1_check_available_studies(self):
        """PRIORITY 1: Check Available DICOM Studies and Files"""
        print("\n=== PRIORITY 1: Checking Available DICOM Studies and Files ===")
        
        if not self.auth_token:
            self.log_test("Study Data Check", False, "No authentication token available")
            return
        
        # Get all studies
        try:
            response = self.session.get(f"{BASE_URL}/studies")
            if response.status_code == 200:
                studies = response.json()
                self.studies_data = studies
                self.log_test("Get All Studies", True, f"Retrieved {len(studies)} studies from database")
                
                # Analyze each study's file_ids
                real_dicom_count = 0
                mock_file_count = 0
                
                print(f"\n📊 STUDY ANALYSIS:")
                for i, study in enumerate(studies):
                    study_id = study.get("study_id", "Unknown")
                    patient_name = study.get("patient_name", "Unknown")
                    file_ids = study.get("file_ids", [])
                    
                    print(f"\n  Study {i+1}: {study_id} - {patient_name}")
                    print(f"    File IDs: {len(file_ids)} files")
                    
                    # Check if file_ids are real MongoDB ObjectIds or mock file_ prefixes
                    real_files = []
                    mock_files = []
                    
                    for file_id in file_ids:
                        if file_id.startswith("file_"):
                            mock_files.append(file_id)
                            mock_file_count += 1
                        else:
                            # Check if it looks like a MongoDB ObjectId (24 hex characters)
                            if len(file_id) == 24 and all(c in '0123456789abcdef' for c in file_id.lower()):
                                real_files.append(file_id)
                                real_dicom_count += 1
                            else:
                                print(f"    ⚠️  Unusual file_id format: {file_id}")
                    
                    if real_files:
                        print(f"    ✅ Real DICOM files: {len(real_files)}")
                        for file_id in real_files:
                            print(f"       - {file_id}")
                            self.real_dicom_files.append({
                                "study_id": study_id,
                                "patient_name": patient_name,
                                "file_id": file_id,
                                "study_data": study
                            })
                    
                    if mock_files:
                        print(f"    ❌ Mock files: {len(mock_files)}")
                        for file_id in mock_files[:3]:  # Show first 3
                            print(f"       - {file_id}")
                        if len(mock_files) > 3:
                            print(f"       - ... and {len(mock_files) - 3} more")
                
                print(f"\n📈 SUMMARY:")
                print(f"  Total Studies: {len(studies)}")
                print(f"  Real DICOM Files: {real_dicom_count}")
                print(f"  Mock Files: {mock_file_count}")
                print(f"  Studies with Real DICOM: {len([s for s in studies if any(not fid.startswith('file_') for fid in s.get('file_ids', []))])}")
                
                if real_dicom_count > 0:
                    self.log_test("Real DICOM Files Found", True, f"Found {real_dicom_count} real DICOM files across {len(self.real_dicom_files)} studies")
                else:
                    self.log_test("Real DICOM Files Found", False, "No real DICOM files found - all file_ids are mock (file_XXXXX format)")
                
            else:
                self.log_test("Get All Studies", False, f"Failed to get studies: {response.status_code}", 
                            {"response": response.text})
        except Exception as e:
            self.log_test("Get All Studies", False, f"Request failed: {str(e)}")
    
    def priority2_test_dicom_file_serving(self):
        """PRIORITY 2: Test DICOM File Serving Endpoint"""
        print("\n=== PRIORITY 2: Testing DICOM File Serving Endpoint ===")
        
        if not self.auth_token:
            self.log_test("DICOM File Serving Test", False, "No authentication token available")
            return
        
        if not self.real_dicom_files:
            self.log_test("DICOM File Serving Test", False, "No real DICOM files available for testing")
            return
        
        # Test each real DICOM file
        successful_downloads = 0
        failed_downloads = 0
        
        for dicom_file in self.real_dicom_files:
            file_id = dicom_file["file_id"]
            study_id = dicom_file["study_id"]
            patient_name = dicom_file["patient_name"]
            
            print(f"\n🔍 Testing file: {file_id} (Study: {study_id} - {patient_name})")
            
            try:
                # Test file download
                response = self.session.get(f"{BASE_URL}/files/{file_id}")
                
                if response.status_code == 200:
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    content_length = len(response.content)
                    
                    print(f"    ✅ File downloaded successfully")
                    print(f"    📄 Content-Type: {content_type}")
                    print(f"    📏 File Size: {content_length} bytes ({content_length/1024:.1f} KB)")
                    
                    # Verify DICOM content-type
                    if content_type == "application/dicom":
                        self.log_test(f"DICOM File {file_id} Content-Type", True, "Correct application/dicom content-type")
                    else:
                        self.log_test(f"DICOM File {file_id} Content-Type", False, f"Incorrect content-type: {content_type}")
                    
                    # Check if file is not empty
                    if content_length > 0:
                        self.log_test(f"DICOM File {file_id} Size", True, f"File has content: {content_length} bytes")
                        
                        # Try to verify DICOM header (basic check)
                        if len(response.content) >= 132:
                            # DICOM files should have "DICM" at offset 128
                            dicm_header = response.content[128:132]
                            if dicm_header == b'DICM':
                                self.log_test(f"DICOM File {file_id} Format", True, "Valid DICOM file header found")
                            else:
                                self.log_test(f"DICOM File {file_id} Format", False, f"Invalid DICOM header: {dicm_header}")
                        else:
                            self.log_test(f"DICOM File {file_id} Format", False, "File too small to be valid DICOM")
                    else:
                        self.log_test(f"DICOM File {file_id} Size", False, "File is empty")
                    
                    successful_downloads += 1
                    
                elif response.status_code == 404:
                    self.log_test(f"DICOM File {file_id} Download", False, "File not found (404)")
                    failed_downloads += 1
                    
                elif response.status_code == 403:
                    self.log_test(f"DICOM File {file_id} Download", False, "Access denied (403)")
                    failed_downloads += 1
                    
                else:
                    self.log_test(f"DICOM File {file_id} Download", False, f"Unexpected status: {response.status_code}")
                    failed_downloads += 1
                    
            except Exception as e:
                self.log_test(f"DICOM File {file_id} Download", False, f"Request failed: {str(e)}")
                failed_downloads += 1
        
        # Summary
        total_files = len(self.real_dicom_files)
        print(f"\n📊 FILE SERVING SUMMARY:")
        print(f"  Total Real DICOM Files Tested: {total_files}")
        print(f"  Successful Downloads: {successful_downloads}")
        print(f"  Failed Downloads: {failed_downloads}")
        print(f"  Success Rate: {(successful_downloads/total_files)*100:.1f}%" if total_files > 0 else "  Success Rate: N/A")
        
        if successful_downloads > 0:
            self.log_test("DICOM File Serving Overall", True, f"Successfully served {successful_downloads}/{total_files} DICOM files")
        else:
            self.log_test("DICOM File Serving Overall", False, f"Failed to serve any DICOM files ({failed_downloads}/{total_files} failed)")
    
    def priority3_validate_study_rs6p4028(self):
        """PRIORITY 3: Validate Study RS6P4028 DICOM Files"""
        print("\n=== PRIORITY 3: Validating Study RS6P4028 DICOM Files ===")
        
        if not self.auth_token:
            self.log_test("Study RS6P4028 Validation", False, "No authentication token available")
            return
        
        # Find study RS6P4028
        rs6p4028_study = None
        for study in self.studies_data:
            if study.get("study_id") == "RS6P4028":
                rs6p4028_study = study
                break
        
        if not rs6p4028_study:
            self.log_test("Study RS6P4028 Found", False, "Study RS6P4028 not found in database")
            return
        
        self.log_test("Study RS6P4028 Found", True, f"Found study RS6P4028 - Patient: {rs6p4028_study.get('patient_name', 'Unknown')}")
        
        # Check file_ids
        file_ids = rs6p4028_study.get("file_ids", [])
        print(f"\n📋 Study RS6P4028 Details:")
        print(f"  Patient: {rs6p4028_study.get('patient_name', 'Unknown')}")
        print(f"  Age: {rs6p4028_study.get('patient_age', 'Unknown')}")
        print(f"  Gender: {rs6p4028_study.get('patient_gender', 'Unknown')}")
        print(f"  Modality: {rs6p4028_study.get('modality', 'Unknown')}")
        print(f"  Status: {rs6p4028_study.get('status', 'Unknown')}")
        print(f"  File IDs: {len(file_ids)} files")
        
        # Analyze file_ids
        real_files = []
        mock_files = []
        
        for file_id in file_ids:
            if file_id.startswith("file_"):
                mock_files.append(file_id)
            else:
                if len(file_id) == 24 and all(c in '0123456789abcdef' for c in file_id.lower()):
                    real_files.append(file_id)
        
        print(f"  Real DICOM Files: {len(real_files)}")
        print(f"  Mock Files: {len(mock_files)}")
        
        if real_files:
            self.log_test("Study RS6P4028 Real Files", True, f"Study has {len(real_files)} real DICOM files")
            
            # Test downloading each real file
            for file_id in real_files:
                print(f"\n🔍 Testing RS6P4028 file: {file_id}")
                
                try:
                    response = self.session.get(f"{BASE_URL}/files/{file_id}")
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '')
                        content_length = len(response.content)
                        
                        print(f"    ✅ File downloaded: {content_length} bytes")
                        print(f"    📄 Content-Type: {content_type}")
                        
                        # Verify DICOM format
                        if len(response.content) >= 132:
                            dicm_header = response.content[128:132]
                            if dicm_header == b'DICM':
                                self.log_test(f"RS6P4028 File {file_id} DICOM Format", True, "Valid DICOM file with proper header")
                            else:
                                self.log_test(f"RS6P4028 File {file_id} DICOM Format", False, "Invalid DICOM header")
                        
                        # Test metadata extraction
                        try:
                            metadata_response = self.session.get(f"{BASE_URL}/files/{file_id}/metadata")
                            if metadata_response.status_code == 200:
                                metadata = metadata_response.json()
                                print(f"    📊 Metadata extracted: {len(metadata.get('metadata', {}))} fields")
                                
                                # Show key metadata fields
                                meta = metadata.get('metadata', {})
                                if meta.get('patient_name'):
                                    print(f"       Patient Name: {meta['patient_name']}")
                                if meta.get('modality'):
                                    print(f"       Modality: {meta['modality']}")
                                if meta.get('study_description'):
                                    print(f"       Study Description: {meta['study_description']}")
                                
                                self.log_test(f"RS6P4028 File {file_id} Metadata", True, "Successfully extracted DICOM metadata")
                            else:
                                self.log_test(f"RS6P4028 File {file_id} Metadata", False, f"Metadata extraction failed: {metadata_response.status_code}")
                        except Exception as e:
                            self.log_test(f"RS6P4028 File {file_id} Metadata", False, f"Metadata request failed: {str(e)}")
                    
                    else:
                        self.log_test(f"RS6P4028 File {file_id} Download", False, f"Download failed: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"RS6P4028 File {file_id} Download", False, f"Request failed: {str(e)}")
        else:
            self.log_test("Study RS6P4028 Real Files", False, "Study RS6P4028 has no real DICOM files - all are mock")
    
    def priority4_debug_file_access_issues(self):
        """PRIORITY 4: Debug File Access Issues"""
        print("\n=== PRIORITY 4: Debugging File Access Issues ===")
        
        if not self.auth_token:
            self.log_test("File Access Debug", False, "No authentication token available")
            return
        
        # Test authentication with different scenarios
        print("\n🔐 Testing Authentication Scenarios:")
        
        # Test with current admin token
        if self.real_dicom_files:
            test_file_id = self.real_dicom_files[0]["file_id"]
            
            # Test with valid token
            response = self.session.get(f"{BASE_URL}/files/{test_file_id}")
            if response.status_code == 200:
                self.log_test("File Access with Admin Token", True, "Admin can access DICOM files")
            else:
                self.log_test("File Access with Admin Token", False, f"Admin access failed: {response.status_code}")
            
            # Test without token
            headers_backup = self.session.headers.copy()
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            
            response = self.session.get(f"{BASE_URL}/files/{test_file_id}")
            if response.status_code == 401 or response.status_code == 403:
                self.log_test("File Access without Token", True, "Properly denied access without authentication")
            else:
                self.log_test("File Access without Token", False, f"Unexpected response without auth: {response.status_code}")
            
            # Restore headers
            self.session.headers = headers_backup
        
        # Test CORS and networking
        print("\n🌐 Testing Network and CORS:")
        
        try:
            # Test basic connectivity to API
            response = self.session.get(f"{BASE_URL}/auth/me")
            if response.status_code == 200:
                self.log_test("API Connectivity", True, "API is accessible and responding")
            else:
                self.log_test("API Connectivity", False, f"API connectivity issue: {response.status_code}")
        except Exception as e:
            self.log_test("API Connectivity", False, f"Network error: {str(e)}")
        
        # Test GridFS storage status
        print("\n💾 Testing GridFS Storage:")
        
        # Test file metadata extraction endpoint
        try:
            # Create a minimal test to check if GridFS is working
            response = self.session.post(f"{BASE_URL}/files/extract-metadata", 
                                       files={'file': ('test.txt', b'test content', 'text/plain')})
            
            if response.status_code == 400:
                # Expected - not a DICOM file, but endpoint is working
                self.log_test("GridFS Metadata Endpoint", True, "Metadata extraction endpoint is functional")
            elif response.status_code == 200:
                self.log_test("GridFS Metadata Endpoint", True, "Metadata extraction endpoint working")
            else:
                self.log_test("GridFS Metadata Endpoint", False, f"Metadata endpoint issue: {response.status_code}")
                
        except Exception as e:
            self.log_test("GridFS Metadata Endpoint", False, f"Metadata endpoint error: {str(e)}")
        
        # Test invalid file ID handling
        print("\n🚫 Testing Invalid File ID Handling:")
        
        try:
            # Test with invalid ObjectId
            response = self.session.get(f"{BASE_URL}/files/invalid_file_id_123")
            if response.status_code == 404:
                self.log_test("Invalid File ID Handling", True, "Properly returns 404 for invalid file IDs")
            else:
                self.log_test("Invalid File ID Handling", False, f"Unexpected response for invalid ID: {response.status_code}")
        except Exception as e:
            self.log_test("Invalid File ID Handling", False, f"Error testing invalid ID: {str(e)}")
    
    def test_study_metadata_consistency(self):
        """Test study metadata consistency"""
        print("\n=== Testing Study Metadata Consistency ===")
        
        if not self.studies_data:
            self.log_test("Study Metadata Consistency", False, "No study data available")
            return
        
        consistent_studies = 0
        inconsistent_studies = 0
        
        for study in self.studies_data:
            study_id = study.get("study_id")
            
            # Test individual study retrieval
            try:
                response = self.session.get(f"{BASE_URL}/studies/{study_id}")
                if response.status_code == 200:
                    individual_study = response.json()
                    
                    # Compare key fields
                    fields_to_check = ["patient_name", "patient_age", "patient_gender", "modality", "status"]
                    all_consistent = True
                    
                    for field in fields_to_check:
                        if study.get(field) != individual_study.get(field):
                            all_consistent = False
                            print(f"    ⚠️  {study_id}: {field} mismatch - List: {study.get(field)}, Individual: {individual_study.get(field)}")
                    
                    if all_consistent:
                        consistent_studies += 1
                    else:
                        inconsistent_studies += 1
                        
                else:
                    self.log_test(f"Study {study_id} Individual Retrieval", False, f"Failed to retrieve: {response.status_code}")
                    inconsistent_studies += 1
                    
            except Exception as e:
                self.log_test(f"Study {study_id} Individual Retrieval", False, f"Request failed: {str(e)}")
                inconsistent_studies += 1
        
        total_studies = len(self.studies_data)
        if consistent_studies == total_studies:
            self.log_test("Study Metadata Consistency", True, f"All {total_studies} studies have consistent metadata")
        else:
            self.log_test("Study Metadata Consistency", False, f"{inconsistent_studies}/{total_studies} studies have metadata inconsistencies")
    
    def run_dicom_debug_tests(self):
        """Run all DICOM debugging tests"""
        print("🔍 Starting DICOM File Serving Debug Test Suite")
        print(f"Testing against: {BASE_URL}")
        print("="*80)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run tests in priority order
        self.priority1_check_available_studies()
        self.priority2_test_dicom_file_serving()
        self.priority3_validate_study_rs6p4028()
        self.priority4_debug_file_access_issues()
        self.test_study_metadata_consistency()
        
        # Print summary
        self.print_summary()
        
        return len([r for r in self.test_results if not r["success"]]) == 0
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("🏁 DICOM DEBUG TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        print(f"  Total Studies in Database: {len(self.studies_data)}")
        print(f"  Studies with Real DICOM Files: {len(set(f['study_id'] for f in self.real_dicom_files))}")
        print(f"  Total Real DICOM Files: {len(self.real_dicom_files)}")
        
        if self.real_dicom_files:
            print(f"\n📋 REAL DICOM FILES FOUND:")
            for dicom_file in self.real_dicom_files:
                print(f"  - Study {dicom_file['study_id']} ({dicom_file['patient_name']}): {dicom_file['file_id']}")
        
        if failed_tests > 0:
            print(f"\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    tester = DICOMDebugTester()
    success = tester.run_dicom_debug_tests()
    sys.exit(0 if success else 1)