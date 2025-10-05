from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Body, status
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
import os
import logging
import random
import string
import io
import base64
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

class FinalReportCreate(BaseModel):
    findings: str
    diagnosis: str
    recommendations: Optional[str] = None

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

def generate_mock_ai_report(modality: str, patient_age: int, patient_gender: str) -> Dict[str, Any]:
    """Generate mock AI report based on modality"""
    reports = {
        "CT": {
            "findings": "Brain CT scan shows normal gray-white matter differentiation. No acute intracranial hemorrhage, mass effect, or midline shift. Ventricular system is normal in size and configuration. No extra-axial fluid collections.",
            "diagnosis": "Normal Brain CT - No acute intracranial abnormality detected"
        },
        "MRI": {
            "findings": "MRI Brain: Normal brain parenchyma signal intensity on all sequences. No evidence of mass lesion, hemorrhage, or acute infarction. Ventricular system and sulci are age-appropriate.",
            "diagnosis": "Normal MRI Brain study"
        },
        "X-ray": {
            "findings": "Chest X-ray: Heart size is normal. Lungs are clear bilaterally. No pleural effusion or pneumothorax. Bony thorax is intact.",
            "diagnosis": "Normal Chest X-ray - No acute cardiopulmonary abnormality"
        },
        "Ultrasound": {
            "findings": "Abdomen ultrasound: Liver, gallbladder, pancreas, spleen, and kidneys appear normal in size and echogenicity. No focal lesions or free fluid detected.",
            "diagnosis": "Normal abdominal ultrasound"
        }
    }
    
    default_report = {
        "findings": f"Imaging study of {modality} modality reviewed. Structures within normal limits for age and gender.",
        "diagnosis": f"Normal {modality} study - No significant abnormality detected"
    }
    
    return reports.get(modality, default_report)

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
    
    # Upload files to GridFS
    file_ids = []
    for file in files:
        content = await file.read()
        file_id = await fs.upload_from_stream(
            f"{study_id}_{file.filename}",
            io.BytesIO(content),
            metadata={"study_id": study_id, "original_name": file.filename}
        )
        file_ids.append(str(file_id))
    
    # Generate AI report
    mock_report = generate_mock_ai_report(modality, patient_age, patient_gender)
    ai_report_dict = {
        "id": f"ai_{generate_study_id()}",
        "study_id": study_id,
        "findings": mock_report["findings"],
        "preliminary_diagnosis": mock_report["diagnosis"],
        "confidence_score": random.uniform(0.85, 0.98),
        "generated_at": datetime.now(timezone.utc),
        "model_version": "MONAI-v1.0-MOCK"
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
        "final_report_id": None
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
        "approved_at": datetime.now(timezone.utc)
    }
    
    await db.final_reports.insert_one(final_report_dict)
    await db.studies.update_one(
        {"study_id": study_id},
        {"$set": {"final_report_id": final_report_dict["id"], "status": "completed"}}
    )
    
    return FinalReport(**final_report_dict)

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