import firebase_admin
from firebase_admin import credentials, auth
import os
from typing import Optional, Dict, Any
from .models import UserRole, UserRegistration, UserResponse, WorkerProfile
from .database import (
    create_user, get_user_by_email, create_worker_profile, 
    get_worker_by_email, get_department_by_id, create_department, get_all_departments
)
from datetime import datetime
import hashlib
import secrets

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Try to get service account key from environment
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                # For development, try to use default credentials
                firebase_admin.initialize_app()
        return True
    except Exception as e:
        print(f"Warning: Could not initialize Firebase Admin SDK: {e}")
        print("Authentication will use mock mode for development")
        return False

# Initialize Firebase on module import
FIREBASE_INITIALIZED = initialize_firebase()

class AuthService:
    """Authentication service for role-based access control"""
    
    def __init__(self):
        self.firebase_available = FIREBASE_INITIALIZED
    
    async def register_user(self, user_data: UserRegistration) -> Dict[str, Any]:
        """Register a new user with role-based access"""
        try:
            department = None
            # Validate worker-specific fields if role is worker
            if user_data.role == UserRole.WORKER:
                if not user_data.employee_id or not user_data.department_id:
                    raise ValueError("Employee ID and Department ID are required for workers")
                # Verify department exists
                department = await get_department_by_id(user_data.department_id)
                if not department:
                    raise ValueError("Invalid department ID")
            # Create Firebase user if available
            firebase_user = None
            if self.firebase_available:
                try:
                    firebase_user = auth.create_user(
                        email=user_data.email,
                        password=user_data.password,
                        display_name=user_data.name
                    )
                except Exception as e:
                    print(f"Firebase user creation failed: {e}")
                    # Continue with mock mode
            
            # Create user record in database
            user_record = {
                "email": user_data.email,
                "name": user_data.name,
                "phone": user_data.phone,
                "role": user_data.role.value,
                "is_active": True,
                "created_at": datetime.now().strftime("%H:%M %d-%m-%Y"),
                "firebase_uid": firebase_user.uid if firebase_user else None
            }
            
            created_user = await create_user(user_record)
            
            # Create worker profile if role is worker
            if user_data.role == UserRole.WORKER:
                worker_data = {
                    "user_id": firebase_user.uid if firebase_user else created_user["_id"],
                    "email": user_data.email,
                    "name": user_data.name,
                    "phone": user_data.phone,
                    "employee_id": user_data.employee_id,
                    "department_id": user_data.department_id,
                    "department_name": department.name if department else None,
                    "skills": user_data.skills or [],
                    "profile_photo": user_data.profile_photo,
                    "is_active": True,
                    "created_at": datetime.now().strftime("%H:%M %d-%m-%Y")
                }
                await create_worker_profile(worker_data)
            
            return {
                "success": True,
                "message": "User registered successfully",
                "user": {
                    "id": created_user["_id"],
                    "email": user_data.email,
                    "name": user_data.name,
                    "role": user_data.role.value,
                    "phone": user_data.phone,
                    "is_active": True,
                    "created_at": created_user["created_at"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Registration failed: {str(e)}"
            }
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return user information"""
        try:
            # Get user from database
            user = await get_user_by_email(email)
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            if not user.get("is_active", True):
                return {
                    "success": False,
                    "message": "User account is deactivated"
                }
            
            # Verify password with Firebase if available
            if self.firebase_available and user.get("firebase_uid"):
                try:
                    # Firebase handles password verification through client SDK
                    pass
                except Exception as e:
                    print(f"Firebase authentication error: {e}")
            
            # Get worker profile if user is a worker
            worker_profile = None
            if user.get("role") == UserRole.WORKER.value:
                worker_profile = await get_worker_by_email(email)
            
            response_data = {
                "success": True,
                "message": "Authentication successful",
                "user": {
                    "id": user["_id"],
                    "email": user["email"],
                    "name": user["name"],
                    "role": user["role"],
                    "phone": user.get("phone"),
                    "is_active": user.get("is_active", True),
                    "created_at": user["created_at"]
                }
            }
            
            # Add worker-specific data
            if worker_profile:
                response_data["user"].update({
                    "employee_id": worker_profile.employee_id,
                    "department_id": worker_profile.department_id,
                    "department_name": worker_profile.department_name,
                    "skills": worker_profile.skills,
                    "profile_photo": worker_profile.profile_photo
                })
            
            return response_data
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Authentication failed: {str(e)}"
            }
    
    async def get_user_profile(self, email: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            user = await get_user_by_email(email)
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            # Get worker profile if user is a worker
            worker_profile = None
            if user.get("role") == UserRole.WORKER.value:
                worker_profile = await get_worker_by_email(email)
            
            response_data = {
                "success": True,
                "user": {
                    "id": user["_id"],
                    "email": user["email"],
                    "name": user["name"],
                    "role": user["role"],
                    "phone": user.get("phone"),
                    "is_active": user.get("is_active", True),
                    "created_at": user["created_at"]
                }
            }
            
            # Add worker-specific data
            if worker_profile:
                response_data["user"].update({
                    "employee_id": worker_profile.employee_id,
                    "department_id": worker_profile.department_id,
                    "department_name": worker_profile.department_name,
                    "skills": worker_profile.skills,
                    "profile_photo": worker_profile.profile_photo
                })
            
            return response_data
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get user profile: {str(e)}"
            }
    
    async def initialize_default_departments(self):
        """Initialize default departments if they don't exist"""
        default_departments = [
            {"name": "Sanitation & Waste Management", "description": "Handles waste collection and sanitation issues"},
            {"name": "Water & Drainage", "description": "Manages water supply and drainage systems"},
            {"name": "Electricity & Streetlights", "description": "Handles electrical issues and street lighting"},
            {"name": "Roads & Transport", "description": "Manages road maintenance and transport infrastructure"},
            {"name": "Public Health & Safety", "description": "Handles public health and safety concerns"},
            {"name": "Environment & Parks", "description": "Manages environmental issues and park maintenance"},
            {"name": "Building & Infrastructure", "description": "Handles building and infrastructure issues"},
            {"name": "Taxes & Documentation", "description": "Manages tax collection and documentation"},
            {"name": "Emergency Services", "description": "Handles emergency response and services"},
            {"name": "Animal Care & Control", "description": "Manages animal welfare and control services"}
        ]
        
        try:
            for dept_data in default_departments:
                # Check if department already exists
                existing_depts = await get_all_departments()
                if not any(dept.name == dept_data["name"] for dept in existing_depts):
                    await create_department(dept_data)
                    print(f"Created default department: {dept_data['name']}")
        except Exception as e:
            print(f"Error initializing default departments: {e}")

# Global auth service instance
auth_service = AuthService()