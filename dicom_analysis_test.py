#!/usr/bin/env python3
"""
DICOM File Analysis - Deep dive into file_ids and actual file availability
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

class DICOMAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        
    def authenticate(self):
        """Authenticate as admin"""
        try:
            login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.auth_token = data["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                    return True
            return False
        except Exception:
            return False
    
    def analyze_dicom_files(self):
        """Analyze all DICOM files in the system"""
        if not self.authenticate():
            print("❌ Failed to authenticate")
            return
        
        print("🔍 DICOM File Analysis Report")
        print("="*60)
        
        # Get all studies
        try:
            response = self.session.get(f"{BASE_URL}/studies")
            if response.status_code != 200:
                print(f"❌ Failed to get studies: {response.status_code}")
                return
            
            studies = response.json()
            print(f"📊 Total Studies: {len(studies)}")
            
            real_files = []
            mock_files = []
            empty_studies = []
            
            for study in studies:
                study_id = study.get("study_id")
                patient_name = study.get("patient_name")
                modality = study.get("modality")
                file_ids = study.get("file_ids", [])
                
                if not file_ids:
                    empty_studies.append(study_id)
                    continue
                
                print(f"\n📁 Study {study_id} ({patient_name} - {modality})")
                print(f"   File IDs: {len(file_ids)} files")
                
                # Test first few file_ids to determine type
                working_files = 0
                for i, file_id in enumerate(file_ids[:3]):  # Test first 3 files
                    try:
                        file_response = self.session.get(f"{BASE_URL}/files/{file_id}")
                        if file_response.status_code == 200:
                            content_length = len(file_response.content)
                            content_type = file_response.headers.get("content-type", "")
                            print(f"   ✅ {file_id}: {content_length} bytes ({content_type})")
                            working_files += 1
                            
                            # Determine if this is a real MongoDB ObjectId or mock
                            if len(file_id) == 24 and all(c in '0123456789abcdef' for c in file_id):
                                real_files.append({
                                    "study_id": study_id,
                                    "file_id": file_id,
                                    "size": content_length,
                                    "patient": patient_name,
                                    "modality": modality
                                })
                            else:
                                mock_files.append({
                                    "study_id": study_id,
                                    "file_id": file_id,
                                    "patient": patient_name,
                                    "modality": modality
                                })
                        else:
                            print(f"   ❌ {file_id}: {file_response.status_code}")
                            mock_files.append({
                                "study_id": study_id,
                                "file_id": file_id,
                                "patient": patient_name,
                                "modality": modality,
                                "error": file_response.status_code
                            })
                    except Exception as e:
                        print(f"   ❌ {file_id}: Error - {str(e)}")
                
                if working_files > 0:
                    print(f"   📈 Working files: {working_files}/{min(len(file_ids), 3)} tested")
                else:
                    print(f"   📉 No working files found")
            
            # Summary
            print(f"\n" + "="*60)
            print("📋 SUMMARY")
            print("="*60)
            print(f"Real DICOM files (MongoDB GridFS): {len(real_files)}")
            print(f"Mock/Invalid file_ids: {len(mock_files)}")
            print(f"Studies with no files: {len(empty_studies)}")
            
            if real_files:
                print(f"\n✅ REAL DICOM FILES AVAILABLE:")
                for file_info in real_files:
                    print(f"   • {file_info['study_id']}: {file_info['patient']} ({file_info['modality']}) - {file_info['size']} bytes")
                    print(f"     File ID: {file_info['file_id']}")
            
            if mock_files:
                print(f"\n❌ MOCK/INVALID FILES:")
                for file_info in mock_files[:5]:  # Show first 5
                    error_info = f" (Error: {file_info.get('error', 'Unknown')})" if 'error' in file_info else ""
                    print(f"   • {file_info['study_id']}: {file_info['file_id']}{error_info}")
                if len(mock_files) > 5:
                    print(f"   ... and {len(mock_files) - 5} more")
            
            # DICOM Viewer Readiness Assessment
            print(f"\n🎯 DICOM VIEWER READINESS ASSESSMENT:")
            if real_files:
                print(f"✅ READY: {len(real_files)} real DICOM files available for viewer")
                print(f"✅ Studies with real files: {len(set(f['study_id'] for f in real_files))}")
                print(f"✅ File serving endpoint working for real files")
                print(f"✅ Authentication and authorization working")
                
                # Test specific study RS6P4028
                rs6p4028_files = [f for f in real_files if f['study_id'] == 'RS6P4028']
                if rs6p4028_files:
                    print(f"✅ Study RS6P4028 has {len(rs6p4028_files)} real DICOM file(s)")
                else:
                    print(f"⚠️  Study RS6P4028 not found in real files")
            else:
                print(f"❌ NOT READY: No real DICOM files found")
                print(f"❌ All file_ids appear to be mock data")
                print(f"❌ DICOM viewer will not be able to load actual medical images")
            
            # Recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            if real_files:
                print(f"✅ System is ready for DICOM viewer integration")
                print(f"✅ Use studies with real file_ids for testing viewer")
                print(f"⚠️  Consider cleaning up mock file_ids from database")
            else:
                print(f"❌ Upload real DICOM files to enable viewer functionality")
                print(f"❌ Current mock file_ids will not work with DICOM viewer")
                print(f"❌ Need actual medical imaging data for proper testing")
                
        except Exception as e:
            print(f"❌ Analysis failed: {str(e)}")

if __name__ == "__main__":
    analyzer = DICOMAnalyzer()
    analyzer.analyze_dicom_files()