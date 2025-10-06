from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Body, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import os
import logging
import random
import string
import io
import base64
import uuid
import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'pacs_database')]
fs = AsyncIOMotorGridFSBucket(db)

# JWT Settings
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="PACS System")
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    ADMIN = "admin"
    CENTRE = "centre"
    DOCTOR = "doctor"
    TECHNICIAN = "technician"
    RADIOLOGIST = "radiologist"
    PATIENT = "patient"

class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    centre_id: Optional[str] = None
    created_at: datetime
    is_active: bool = True
    phone: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    centre_id: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class DiagnosticCentre(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    email: EmailStr
    created_at: datetime
    is_active: bool = True

class DiagnosticCentreCreate(BaseModel):
    name: str
    address: str
    phone: str
    email: EmailStr

class DicomStudy(BaseModel):
    id: str
    study_id: str  # 8-digit alphanumeric
    patient_name: str
    patient_age: int
    patient_gender: str
    modality: str
    centre_id: str
    technician_id: str
    radiologist_id: Optional[str] = None
    status: str  # pending, assigned, completed, draft, delete_requested
    notes: Optional[str] = None
    file_ids: List[str] = []
    uploaded_at: datetime
    ai_report_id: Optional[str] = None
    final_report_id: Optional[str] = None
    is_draft: bool = False
    delete_requested: bool = False
    delete_requested_at: Optional[datetime] = None
    delete_requested_by: Optional[str] = None

class DicomStudyCreate(BaseModel):
    patient_name: str
    patient_age: int
    patient_gender: str
    modality: str
    notes: Optional[str] = None

class AIReport(BaseModel):
    id: str
    study_id: str
    findings: str
    preliminary_diagnosis: str
    confidence_score: float
    generated_at: datetime
    model_version: str = "MONAI-v1.0-MOCK"

class FinalReport(BaseModel):
    id: str
    study_id: str
    radiologist_id: str
    findings: str
    diagnosis: str
    recommendations: Optional[str] = None
    approved_at: datetime
    last_edited_at: Optional[datetime] = None
    last_edited_by: Optional[str] = None
    edit_history: List[Dict[str, Any]] = []

class FinalReportCreate(BaseModel):
    findings: str
    diagnosis: str
    recommendations: Optional[str] = None

class BillingRate(BaseModel):
    id: str
    modality: str
    base_rate: float
    currency: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class BillingRateCreate(BaseModel):
    modality: str
    base_rate: float
    currency: str = "USD"
    description: Optional[str] = None

class Invoice(BaseModel):
    id: str
    invoice_number: str
    centre_id: str
    centre_name: str
    period_start: datetime
    period_end: datetime
    total_studies: int
    study_breakdown: Dict[str, int]  # modality: count
    total_amount: float
    currency: str
    status: str  # pending, paid, overdue
    generated_at: datetime
    paid_at: Optional[datetime] = None

class InvoiceCreate(BaseModel):
    centre_id: str
    period_start: str
    period_end: str
    currency: str = "USD"

class PaymentTransaction(BaseModel):
    id: str
    session_id: str
    amount: float
    currency: str
    metadata: Dict[str, str]
    payment_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    payment_status: str  # initiated, pending, paid, failed, expired
    invoice_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CheckoutRequest(BaseModel):
    invoice_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

# ==================== UTILITIES ====================

def generate_study_id() -> str:
    """Generate 8-digit alphanumeric study ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user_data = await db.users.find_one({"email": email})
        if user_data is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_data)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def extract_dicom_metadata(file_data: bytes) -> Dict[str, Any]:
    """Extract patient and study metadata from DICOM file"""
    try:
        # Parse DICOM data
        ds = pydicom.dcmread(io.BytesIO(file_data))
        
        metadata = {
            # Patient Information
            "patient_name": str(getattr(ds, 'PatientName', '')),
            "patient_id": str(getattr(ds, 'PatientID', '')),
            "patient_birth_date": str(getattr(ds, 'PatientBirthDate', '')),
            "patient_gender": str(getattr(ds, 'PatientSex', '')),
            "patient_age": str(getattr(ds, 'PatientAge', '')),
            
            # Study Information  
            "study_instance_uid": str(getattr(ds, 'StudyInstanceUID', '')),
            "study_date": str(getattr(ds, 'StudyDate', '')),
            "study_time": str(getattr(ds, 'StudyTime', '')),
            "study_description": str(getattr(ds, 'StudyDescription', '')),
            "accession_number": str(getattr(ds, 'AccessionNumber', '')),
            
            # Series Information
            "series_instance_uid": str(getattr(ds, 'SeriesInstanceUID', '')),
            "series_number": str(getattr(ds, 'SeriesNumber', '')),
            "series_description": str(getattr(ds, 'SeriesDescription', '')),
            "modality": str(getattr(ds, 'Modality', '')),
            
            # Image Information
            "sop_instance_uid": str(getattr(ds, 'SOPInstanceUID', '')),
            "instance_number": str(getattr(ds, 'InstanceNumber', '')),
            "rows": int(getattr(ds, 'Rows', 0)) if hasattr(ds, 'Rows') else 0,
            "columns": int(getattr(ds, 'Columns', 0)) if hasattr(ds, 'Columns') else 0,
            "pixel_spacing": getattr(ds, 'PixelSpacing', []) if hasattr(ds, 'PixelSpacing') else [],
            "slice_thickness": str(getattr(ds, 'SliceThickness', '')),
            
            # Technical Parameters
            "window_center": getattr(ds, 'WindowCenter', []) if hasattr(ds, 'WindowCenter') else [],
            "window_width": getattr(ds, 'WindowWidth', []) if hasattr(ds, 'WindowWidth') else [],
            "rescale_intercept": str(getattr(ds, 'RescaleIntercept', '')),
            "rescale_slope": str(getattr(ds, 'RescaleSlope', '')),
            
            # Equipment Information
            "manufacturer": str(getattr(ds, 'Manufacturer', '')),
            "manufacturer_model": str(getattr(ds, 'ManufacturerModelName', '')),
            "station_name": str(getattr(ds, 'StationName', '')),
            
            # Institution Information
            "institution_name": str(getattr(ds, 'InstitutionName', '')),
            "institution_address": str(getattr(ds, 'InstitutionAddress', ''))
        }
        
        # Calculate patient age if birth date is available and age is not
        if metadata["patient_birth_date"] and not metadata["patient_age"]:
            try:
                from datetime import datetime
                birth_date = datetime.strptime(metadata["patient_birth_date"], "%Y%m%d")
                study_date = datetime.strptime(metadata["study_date"], "%Y%m%d") if metadata["study_date"] else datetime.now()
                age = study_date.year - birth_date.year
                if study_date.month < birth_date.month or (study_date.month == birth_date.month and study_date.day < birth_date.day):
                    age -= 1
                metadata["calculated_age"] = age
            except Exception:
                metadata["calculated_age"] = None
        
        return metadata
        
    except Exception as e:
        logging.error(f"Failed to extract DICOM metadata: {str(e)}")
        return {}

def modify_dicom_metadata(file_data: bytes, patient_updates: Dict[str, Any]) -> bytes:
    """Modify DICOM file metadata with updated patient information"""
    try:
        # Parse DICOM data
        ds = pydicom.dcmread(io.BytesIO(file_data))
        
        # Update patient information if provided
        if "patient_name" in patient_updates:
            ds.PatientName = patient_updates["patient_name"]
        if "patient_id" in patient_updates:
            ds.PatientID = patient_updates["patient_id"]
        if "patient_birth_date" in patient_updates:
            ds.PatientBirthDate = patient_updates["patient_birth_date"]
        if "patient_gender" in patient_updates:
            ds.PatientSex = patient_updates["patient_gender"]
        if "patient_age" in patient_updates:
            ds.PatientAge = patient_updates["patient_age"]
            
        # Update study information if provided
        if "study_description" in patient_updates:
            ds.StudyDescription = patient_updates["study_description"]
        if "accession_number" in patient_updates:
            ds.AccessionNumber = patient_updates["accession_number"]
            
        # Save modified DICOM to bytes
        output = io.BytesIO()
        ds.save_as(output)
        return output.getvalue()
        
    except Exception as e:
        logging.error(f"Failed to modify DICOM metadata: {str(e)}")
        return file_data  # Return original if modification fails

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user document
    user_dict = {
        "id": f"user_{generate_study_id()}",
        "email": user_data.email,
        "password": hashed_password,
        "name": user_data.name,
        "role": user_data.role,
        "centre_id": user_data.centre_id,
        "phone": user_data.phone,
        "created_at": datetime.now(timezone.utc),
        "is_active": True
    }
    
    await db.users.insert_one(user_dict)
    
    # Return user without password
    user_dict.pop("password")
    return User(**user_dict)

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    access_token = create_access_token(data={"sub": user["email"]})
    
    user.pop("password")
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User(**user)
    )

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ==================== DIAGNOSTIC CENTRE ROUTES ====================

@api_router.post("/centres", response_model=DiagnosticCentre)
async def create_centre(centre: DiagnosticCentreCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create centres")
    
    centre_dict = {
        "id": f"centre_{generate_study_id()}",
        **centre.dict(),
        "created_at": datetime.now(timezone.utc),
        "is_active": True
    }
    
    await db.centres.insert_one(centre_dict)
    return DiagnosticCentre(**centre_dict)

@api_router.get("/centres", response_model=List[DiagnosticCentre])
async def get_centres(current_user: User = Depends(get_current_user)):
    centres = await db.centres.find().to_list(1000)
    return [DiagnosticCentre(**c) for c in centres]

@api_router.get("/centres/{centre_id}", response_model=DiagnosticCentre)
async def get_centre(centre_id: str, current_user: User = Depends(get_current_user)):
    centre = await db.centres.find_one({"id": centre_id})
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")
    return DiagnosticCentre(**centre)

# ==================== USER MANAGEMENT ROUTES ====================

@api_router.get("/users", response_model=List[User])
async def get_users(role: Optional[str] = None, centre_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if role:
        query["role"] = role
    if centre_id:
        query["centre_id"] = centre_id
    
    users = await db.users.find(query).to_list(1000)
    return [User(**{k: v for k, v in u.items() if k != 'password'}) for u in users]

@api_router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.CENTRE]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_status = not user.get("is_active", True)
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": new_status}})
    
    return {"message": "User status updated", "is_active": new_status}

# ==================== DICOM STUDY ROUTES ====================

@api_router.post("/studies/upload", response_model=DicomStudy)
async def upload_dicom_study(
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    modality: str = Form(...),
    notes: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Only technicians can upload studies")
    
    # Generate study ID
    study_id = generate_study_id()
    
    # Upload files to GridFS and extract DICOM metadata
    file_ids = []
    dicom_metadata = {}
    
    for file in files:
        content = await file.read()
        
        # Extract DICOM metadata from the first file
        if not dicom_metadata and file.filename.lower().endswith('.dcm'):
            dicom_metadata = extract_dicom_metadata(content)
        
        file_id = await fs.upload_from_stream(
            f"{study_id}_{file.filename}",
            io.BytesIO(content),
            metadata={
                "study_id": study_id, 
                "original_name": file.filename,
                "dicom_metadata": dicom_metadata if file.filename.lower().endswith('.dcm') else {}
            }
        )
        file_ids.append(str(file_id))
    
    # Generate AI report with DICOM metadata context
    findings = []
    if dicom_metadata:
        findings.append(f"DICOM study processed: {dicom_metadata.get('study_description', 'Unknown study')}")
        findings.append(f"Modality: {dicom_metadata.get('modality', modality)}")
        findings.append(f"Institution: {dicom_metadata.get('institution_name', 'Unknown')}")
        if dicom_metadata.get('manufacturer'):
            findings.append(f"Equipment: {dicom_metadata.get('manufacturer')} {dicom_metadata.get('manufacturer_model', '')}")
    else:
        findings.append(f"Study uploaded for {modality} imaging")
        findings.append("DICOM metadata extraction pending")
    
    ai_report_dict = {
        "id": f"ai_{generate_study_id()}",
        "study_id": study_id,
        "findings": ". ".join(findings),
        "preliminary_diagnosis": f"DICOM {modality} study - Metadata extracted successfully" if dicom_metadata else f"{modality} study uploaded - Awaiting processing",
        "confidence_score": 0.95 if dicom_metadata else 0.80,
        "generated_at": datetime.now(timezone.utc),
        "model_version": "DICOM-Metadata-v1.0"
    }
    await db.ai_reports.insert_one(ai_report_dict)
    
    # Create study document
    study_dict = {
        "id": f"study_{generate_study_id()}",
        "study_id": study_id,
        "patient_name": patient_name,
        "patient_age": patient_age,
        "patient_gender": patient_gender,
        "modality": modality,
        "centre_id": current_user.centre_id,
        "technician_id": current_user.id,
        "radiologist_id": None,
        "status": "pending",
        "notes": notes,
        "file_ids": file_ids,
        "uploaded_at": datetime.now(timezone.utc),
        "ai_report_id": ai_report_dict["id"],
        "final_report_id": None,
        "is_draft": False,
        "delete_requested": False,
        "delete_requested_at": None,
        "delete_requested_by": None
    }
    
    await db.studies.insert_one(study_dict)
    return DicomStudy(**study_dict)

@api_router.get("/studies", response_model=List[DicomStudy])
async def get_studies(
    status: Optional[str] = None,
    centre_id: Optional[str] = None,
    radiologist_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    # Role-based filtering
    if current_user.role == UserRole.TECHNICIAN:
        query["centre_id"] = current_user.centre_id
    elif current_user.role == UserRole.CENTRE:
        query["centre_id"] = current_user.centre_id
    elif current_user.role == UserRole.RADIOLOGIST:
        if radiologist_id:
            query["radiologist_id"] = radiologist_id
    
    if status:
        query["status"] = status
    if centre_id and current_user.role == UserRole.ADMIN:
        query["centre_id"] = centre_id
    
    studies = await db.studies.find(query).sort("uploaded_at", -1).to_list(1000)
    return [DicomStudy(**s) for s in studies]

@api_router.get("/studies/{study_id}", response_model=DicomStudy)
async def get_study(study_id: str, current_user: User = Depends(get_current_user)):
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return DicomStudy(**study)

@api_router.post("/studies/search")
async def search_studies(
    search_params: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Advanced search with filters"""
    query = {}
    
    # Role-based filtering
    if current_user.role == UserRole.TECHNICIAN:
        query["centre_id"] = current_user.centre_id
    elif current_user.role == UserRole.CENTRE:
        query["centre_id"] = current_user.centre_id
    
    # Search filters
    if search_params.get("patient_name"):
        query["patient_name"] = {"$regex": search_params["patient_name"], "$options": "i"}
    
    if search_params.get("study_id"):
        query["study_id"] = {"$regex": search_params["study_id"], "$options": "i"}
    
    if search_params.get("modality"):
        query["modality"] = search_params["modality"]
    
    if search_params.get("status"):
        query["status"] = search_params["status"]
    
    if search_params.get("date_from"):
        query["uploaded_at"] = {"$gte": datetime.fromisoformat(search_params["date_from"])}
    
    if search_params.get("date_to"):
        if "uploaded_at" not in query:
            query["uploaded_at"] = {}
        query["uploaded_at"]["$lte"] = datetime.fromisoformat(search_params["date_to"])
    
    if search_params.get("patient_age_min"):
        query["patient_age"] = {"$gte": search_params["patient_age_min"]}
    
    if search_params.get("patient_age_max"):
        if "patient_age" not in query:
            query["patient_age"] = {}
        query["patient_age"]["$lte"] = search_params["patient_age_max"]
    
    if search_params.get("patient_gender"):
        query["patient_gender"] = search_params["patient_gender"]
    
    # Filter out drafts unless explicitly requested
    if not search_params.get("include_drafts"):
        query["is_draft"] = {"$ne": True}
    
    studies = await db.studies.find(query).sort("uploaded_at", -1).to_list(1000)
    return [DicomStudy(**s) for s in studies]

@api_router.patch("/studies/{study_id}/request-delete")
async def request_delete_study(study_id: str, current_user: User = Depends(get_current_user)):
    """Technician requests study deletion"""
    if current_user.role != UserRole.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Only technicians can request deletion")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if study["technician_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only request deletion of your own uploads")
    
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {
            "delete_requested": True,
            "delete_requested_at": datetime.now(timezone.utc),
            "delete_requested_by": current_user.id
        }}
    )
    
    return {"message": "Delete request submitted. Awaiting approval from centre admin."}

@api_router.patch("/studies/{study_id}/mark-draft")
async def mark_study_as_draft(study_id: str, current_user: User = Depends(get_current_user)):
    """Mark study as draft"""
    if current_user.role != UserRole.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Only technicians can mark studies as draft")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if study["technician_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only mark your own uploads as draft")
    
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {"is_draft": True, "status": "draft"}}
    )
    
    return {"message": "Study marked as draft"}

@api_router.patch("/studies/{study_id}/unmark-draft")
async def unmark_study_draft(study_id: str, current_user: User = Depends(get_current_user)):
    """Remove draft status"""
    if current_user.role != UserRole.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Only technicians can unmark drafts")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if study["technician_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only unmark your own drafts")
    
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {"is_draft": False, "status": "pending"}}
    )
    
    return {"message": "Study unmarked as draft"}

@api_router.delete("/studies/{study_id}/approve-delete")
async def approve_delete_request(study_id: str, current_user: User = Depends(get_current_user)):
    """Centre or Admin approves deletion request"""
    if current_user.role not in [UserRole.CENTRE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only centre managers or admins can approve deletion")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if not study.get("delete_requested"):
        raise HTTPException(status_code=400, detail="No delete request for this study")
    
    # Delete files from GridFS
    for file_id in study.get("file_ids", []):
        try:
            from bson import ObjectId
            await fs.delete(ObjectId(file_id))
        except Exception as e:
            logger.warning(f"Failed to delete file {file_id}: {e}")
    
    # Delete study
    await db.studies.delete_one({"study_id": study_id})
    
    # Delete associated reports
    if study.get("ai_report_id"):
        await db.ai_reports.delete_one({"id": study["ai_report_id"]})
    if study.get("final_report_id"):
        await db.final_reports.delete_one({"id": study["final_report_id"]})
    
    return {"message": "Study deleted successfully"}

@api_router.patch("/studies/{study_id}/reject-delete")
async def reject_delete_request(study_id: str, current_user: User = Depends(get_current_user)):
    """Centre or Admin rejects deletion request"""
    if current_user.role not in [UserRole.CENTRE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only centre managers or admins can reject deletion")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {
            "delete_requested": False,
            "delete_requested_at": None,
            "delete_requested_by": None
        }}
    )
    
    return {"message": "Delete request rejected"}

@api_router.patch("/studies/{study_id}/assign")
async def assign_study(study_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.RADIOLOGIST:
        raise HTTPException(status_code=403, detail="Only radiologists can assign studies to themselves")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {"radiologist_id": current_user.id, "status": "assigned"}}
    )
    
    return {"message": "Study assigned successfully"}

# ==================== AI REPORT ROUTES ====================

@api_router.get("/studies/{study_id}/ai-report", response_model=AIReport)
async def get_ai_report(study_id: str, current_user: User = Depends(get_current_user)):
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if not study.get("ai_report_id"):
        raise HTTPException(status_code=404, detail="AI report not available")
    
    ai_report = await db.ai_reports.find_one({"id": study["ai_report_id"]})
    if not ai_report:
        raise HTTPException(status_code=404, detail="AI report not found")
    
    return AIReport(**ai_report)

# ==================== FINAL REPORT ROUTES ====================

@api_router.post("/studies/{study_id}/final-report", response_model=FinalReport)
async def create_final_report(
    study_id: str,
    report: FinalReportCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.RADIOLOGIST:
        raise HTTPException(status_code=403, detail="Only radiologists can create final reports")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    final_report_dict = {
        "id": f"report_{generate_study_id()}",
        "study_id": study_id,
        "radiologist_id": current_user.id,
        **report.dict(),
        "approved_at": datetime.now(timezone.utc),
        "last_edited_at": None,
        "last_edited_by": None,
        "edit_history": []
    }
    
    await db.final_reports.insert_one(final_report_dict)
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {"final_report_id": final_report_dict["id"], "status": "completed"}}
    )
    
    return FinalReport(**final_report_dict)

@api_router.put("/studies/{study_id}/final-report", response_model=FinalReport)
async def edit_final_report(
    study_id: str,
    report: FinalReportCreate,
    current_user: User = Depends(get_current_user)
):
    """Edit existing final report with audit trail"""
    if current_user.role != UserRole.RADIOLOGIST:
        raise HTTPException(status_code=403, detail="Only radiologists can edit reports")
    
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if not study.get("final_report_id"):
        raise HTTPException(status_code=404, detail="No final report exists for this study")
    
    existing_report = await db.final_reports.find_one({"id": study["final_report_id"]})
    if not existing_report:
        raise HTTPException(status_code=404, detail="Final report not found")
    
    # Create audit trail entry
    edit_entry = {
        "edited_at": datetime.now(timezone.utc).isoformat(),
        "edited_by": current_user.id,
        "radiologist_name": current_user.name,
        "previous_findings": existing_report.get("findings"),
        "previous_diagnosis": existing_report.get("diagnosis"),
        "previous_recommendations": existing_report.get("recommendations")
    }
    
    # Get existing edit history
    edit_history = existing_report.get("edit_history", [])
    edit_history.append(edit_entry)
    
    # Update report
    updated_report = {
        "findings": report.findings,
        "diagnosis": report.diagnosis,
        "recommendations": report.recommendations,
        "last_edited_at": datetime.now(timezone.utc),
        "last_edited_by": current_user.id,
        "edit_history": edit_history
    }
    
    await db.final_reports.update_one(
        {"id": study["final_report_id"]},
        {"$set": updated_report}
    )
    
    # Fetch updated report
    updated_report_doc = await db.final_reports.find_one({"id": study["final_report_id"]})
    return FinalReport(**updated_report_doc)

@api_router.get("/studies/{study_id}/final-report", response_model=FinalReport)
async def get_final_report(study_id: str, current_user: User = Depends(get_current_user)):
    study = await db.studies.find_one({"study_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    if not study.get("final_report_id"):
        raise HTTPException(status_code=404, detail="Final report not available")
    
    final_report = await db.final_reports.find_one({"id": study["final_report_id"]})
    if not final_report:
        raise HTTPException(status_code=404, detail="Final report not found")
    
    return FinalReport(**final_report)

# ==================== DICOM FILE ROUTES ====================

@api_router.get("/files/{file_id}")
async def get_dicom_file(file_id: str, current_user: User = Depends(get_current_user)):
    try:
        from bson import ObjectId
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        contents = await grid_out.read()
        return StreamingResponse(io.BytesIO(contents), media_type="application/dicom")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    stats = {}
    
    if current_user.role == UserRole.ADMIN:
        stats["total_centres"] = await db.centres.count_documents({})
        stats["total_studies"] = await db.studies.count_documents({})
        stats["total_radiologists"] = await db.users.count_documents({"role": UserRole.RADIOLOGIST})
        stats["pending_studies"] = await db.studies.count_documents({"status": "pending"})
        stats["total_revenue"] = await calculate_total_revenue()
        stats["pending_invoices"] = await db.invoices.count_documents({"status": "pending"})
    elif current_user.role == UserRole.CENTRE:
        stats["total_studies"] = await db.studies.count_documents({"centre_id": current_user.centre_id})
        stats["pending_studies"] = await db.studies.count_documents({"centre_id": current_user.centre_id, "status": "pending"})
        stats["completed_studies"] = await db.studies.count_documents({"centre_id": current_user.centre_id, "status": "completed"})
    elif current_user.role == UserRole.TECHNICIAN:
        stats["uploaded_studies"] = await db.studies.count_documents({"technician_id": current_user.id})
    elif current_user.role == UserRole.RADIOLOGIST:
        stats["assigned_studies"] = await db.studies.count_documents({"radiologist_id": current_user.id, "status": "assigned"})
        stats["completed_studies"] = await db.studies.count_documents({"radiologist_id": current_user.id, "status": "completed"})
    
    return stats

async def calculate_total_revenue():
    """Calculate total revenue from all invoices"""
    invoices = await db.invoices.find({"status": "paid"}).to_list(10000)
    return sum(inv.get("total_amount", 0) for inv in invoices)

# ==================== BILLING ROUTES ====================

@api_router.post("/billing/rates", response_model=BillingRate)
async def create_billing_rate(rate: BillingRateCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create billing rates")
    
    rate_dict = {
        "id": f"rate_{generate_study_id()}",
        **rate.dict(),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.billing_rates.insert_one(rate_dict)
    return BillingRate(**rate_dict)

@api_router.get("/billing/rates", response_model=List[BillingRate])
async def get_billing_rates(current_user: User = Depends(get_current_user)):
    rates = await db.billing_rates.find().to_list(1000)
    return [BillingRate(**r) for r in rates]

@api_router.put("/billing/rates/{rate_id}", response_model=BillingRate)
async def update_billing_rate(rate_id: str, rate: BillingRateCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update billing rates")
    
    existing_rate = await db.billing_rates.find_one({"id": rate_id})
    if not existing_rate:
        raise HTTPException(status_code=404, detail="Billing rate not found")
    
    update_dict = {
        **rate.dict(),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.billing_rates.update_one({"id": rate_id}, {"$set": update_dict})
    
    updated_rate = await db.billing_rates.find_one({"id": rate_id})
    return BillingRate(**updated_rate)

@api_router.post("/billing/invoices/generate", response_model=Invoice)
async def generate_invoice(invoice_data: InvoiceCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can generate invoices")
    
    centre = await db.centres.find_one({"id": invoice_data.centre_id})
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")
    
    # Get billing rates
    billing_rates = {}
    rates = await db.billing_rates.find({"currency": invoice_data.currency}).to_list(100)
    for rate in rates:
        billing_rates[rate["modality"]] = rate["base_rate"]
    
    # Get studies for period
    period_start = datetime.fromisoformat(invoice_data.period_start)
    period_end = datetime.fromisoformat(invoice_data.period_end)
    
    studies = await db.studies.find({
        "centre_id": invoice_data.centre_id,
        "uploaded_at": {
            "$gte": period_start,
            "$lte": period_end
        },
        "status": "completed"
    }).to_list(10000)
    
    # Calculate breakdown and total
    study_breakdown = {}
    total_amount = 0
    
    for study in studies:
        modality = study["modality"]
        study_breakdown[modality] = study_breakdown.get(modality, 0) + 1
        rate = billing_rates.get(modality, 100)  # Default $100
        total_amount += rate
    
    # Generate invoice number
    invoice_number = f"INV-{generate_study_id()}"
    
    invoice_dict = {
        "id": f"invoice_{generate_study_id()}",
        "invoice_number": invoice_number,
        "centre_id": invoice_data.centre_id,
        "centre_name": centre["name"],
        "period_start": period_start,
        "period_end": period_end,
        "total_studies": len(studies),
        "study_breakdown": study_breakdown,
        "total_amount": total_amount,
        "currency": invoice_data.currency,
        "status": "pending",
        "generated_at": datetime.now(timezone.utc),
        "paid_at": None
    }
    
    await db.invoices.insert_one(invoice_dict)
    return Invoice(**invoice_dict)

@api_router.get("/billing/invoices", response_model=List[Invoice])
async def get_invoices(
    centre_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    if current_user.role == UserRole.CENTRE:
        query["centre_id"] = current_user.centre_id
    elif centre_id and current_user.role == UserRole.ADMIN:
        query["centre_id"] = centre_id
    
    if status:
        query["status"] = status
    
    invoices = await db.invoices.find(query).sort("generated_at", -1).to_list(1000)
    return [Invoice(**inv) for inv in invoices]

@api_router.patch("/billing/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(invoice_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.CENTRE]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Invoice marked as paid"}

# ==================== STRIPE PAYMENT INTEGRATION ====================

# Initialize Stripe
stripe_api_key = os.environ.get('STRIPE_API_KEY')
if not stripe_api_key:
    logging.warning("STRIPE_API_KEY not found in environment variables")

@api_router.post("/billing/checkout/create", response_model=Dict[str, Any])
async def create_checkout_session(
    request: Request,
    checkout_request: CheckoutRequest,
    current_user: User = Depends(get_current_user)
):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    # Get invoice details
    invoice = await db.invoices.find_one({"id": checkout_request.invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Verify user can access this invoice
    if (current_user.role == UserRole.CENTRE and 
        invoice.get("centre_id") != current_user.centre_id):
        raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")
    
    try:
        # Get host URL for success/cancel URLs
        host_url = str(request.base_url).rstrip('/')
        webhook_url = f"{host_url}/api/webhook/stripe"
        
        # Initialize Stripe checkout
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
        
        # Build URLs
        success_url = checkout_request.success_url or f"{host_url}/billing/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = checkout_request.cancel_url or f"{host_url}/billing/payment-cancel"
        
        # Create checkout session request
        amount = float(invoice["total_amount"])
        currency = invoice.get("currency", "USD").lower()
        
        checkout_session_request = CheckoutSessionRequest(
            amount=amount,
            currency=currency,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "invoice_id": checkout_request.invoice_id,
                "centre_id": invoice["centre_id"],
                "user_id": current_user.id,
                "user_email": current_user.email
            }
        )
        
        # Create session with Stripe
        session = await stripe_checkout.create_checkout_session(checkout_session_request)
        
        # Create payment transaction record
        transaction_id = str(uuid.uuid4())
        payment_transaction = {
            "id": transaction_id,
            "session_id": session.session_id,
            "amount": amount,
            "currency": currency,
            "metadata": {
                "invoice_id": checkout_request.invoice_id,
                "centre_id": invoice["centre_id"],
                "user_id": current_user.id,
                "user_email": current_user.email
            },
            "payment_id": None,
            "user_id": current_user.id,
            "user_email": current_user.email,
            "payment_status": "initiated",
            "invoice_id": checkout_request.invoice_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.payment_transactions.insert_one(payment_transaction)
        
        return {
            "url": session.url,
            "session_id": session.session_id,
            "transaction_id": transaction_id
        }
    
    except Exception as e:
        logging.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")

@api_router.get("/billing/checkout/status/{session_id}")
async def get_checkout_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    # Get transaction from database
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify user can access this transaction
    if transaction.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Check with Stripe
        webhook_url = "dummy_webhook_url"  # Not used for status check
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
        
        status_response = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction status if changed
        new_status = status_response.payment_status
        if transaction["payment_status"] != new_status:
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "payment_status": new_status,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # If payment is successful and not already processed, mark invoice as paid
            if (new_status == "paid" and 
                transaction.get("payment_status") != "paid"):
                
                await db.invoices.update_one(
                    {"id": transaction["invoice_id"]},
                    {
                        "$set": {
                            "status": "paid",
                            "paid_at": datetime.now(timezone.utc)
                        }
                    }
                )
        
        return {
            "status": status_response.status,
            "payment_status": status_response.payment_status,
            "amount_total": status_response.amount_total,
            "currency": status_response.currency,
            "transaction_status": new_status
        }
    
    except Exception as e:
        logging.error(f"Error checking payment status with Stripe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check payment status: {str(e)}")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        # Initialize Stripe checkout for webhook handling
        webhook_url = "dummy_webhook_url"  # Not used for webhook handling
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
        
        # Handle webhook
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction based on webhook event
        if webhook_response.session_id:
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {
                    "$set": {
                        "payment_status": webhook_response.payment_status,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # If payment completed, mark invoice as paid
            if webhook_response.payment_status == "paid":
                transaction = await db.payment_transactions.find_one(
                    {"session_id": webhook_response.session_id}
                )
                if transaction and transaction.get("invoice_id"):
                    await db.invoices.update_one(
                        {"id": transaction["invoice_id"]},
                        {
                            "$set": {
                                "status": "paid",
                                "paid_at": datetime.now(timezone.utc)
                            }
                        }
                    )
        
        return {"received": True}
    
    except Exception as e:
        logging.error(f"Error handling Stripe webhook: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook handling failed")

@api_router.get("/billing/transactions", response_model=List[PaymentTransaction])
async def get_payment_transactions(
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    # Filter based on user role
    if current_user.role == UserRole.CENTRE:
        query["user_id"] = current_user.id
    elif current_user.role != UserRole.ADMIN:
        query["user_id"] = current_user.id
    
    transactions = await db.payment_transactions.find(query).sort("created_at", -1).to_list(1000)
    return [PaymentTransaction(**txn) for txn in transactions]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

@app.on_event("startup")
async def startup_event():
    # Create default admin user if not exists
    admin = await db.users.find_one({"email": "admin@pacs.com"})
    if not admin:
        admin_dict = {
            "id": f"user_{generate_study_id()}",
            "email": "admin@pacs.com",
            "password": hash_password("admin123"),
            "name": "System Administrator",
            "role": UserRole.ADMIN,
            "centre_id": None,
            "phone": None,
            "created_at": datetime.now(timezone.utc),
            "is_active": True
        }
        await db.users.insert_one(admin_dict)
        logger.info("Default admin user created: admin@pacs.com / admin123")