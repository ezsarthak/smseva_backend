from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum


class Location(BaseModel):
    longitude: float
    latitude: float

class IssueRequest(BaseModel):
    text: str = Field(..., description="Text content describing the issue")
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., description="User's name")
    location: Optional[Location] = Field(None, description="Location coordinates (longitude, latitude)")
    photo: Optional[str] = Field(None, description="Base64 encoded photo string")

class IssueResponse(BaseModel):
    ticket_id: str
    category: str
    address: str
    location: Optional[Location]
    description: str
    title: str
    photo: Optional[str]
    status: str
    created_at: str
    users: List[str]
    issue_count: int
    original_text: Optional[str] = None
    in_progress_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_by_email: Optional[str] = None  # Email of who last updated the status
    updated_at: Optional[str] = None  # When the status was last updated
    admin_completed_at: Optional[str] = None  # When admin marked as completed
    user_completed_at: Optional[str] = None  # When user marked as completed
    admin_completed_by: Optional[str] = None  # Email of admin who marked completed
    user_completed_by: Optional[str] = None  # Email of user who marked completed

class IssueDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    ticket_id: str
    category: str
    address: str
    location: Optional[Location]
    description: str
    title: str
    photo: Optional[str]
    status: str
    created_at: str
    users: List[str]
    issue_count: int
    content_hash: str  # For duplicate detection
    original_text: str  # Store original user input for similarity comparison
    in_progress_at: Optional[str] = None  # When status was changed to in_progress
    completed_at: Optional[str] = None    # When status was changed to completed
    updated_by_email: Optional[str] = None  # Email of who last updated the status
    updated_at: Optional[str] = None  # When the status was last updated
    admin_completed_at: Optional[str] = None  # When admin marked as completed
    user_completed_at: Optional[str] = None  # When user marked as completed
    admin_completed_by: Optional[str] = None  # Email of admin who marked completed
    user_completed_by: Optional[str] = None  # Email of user who marked completed

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New status for the issue")
    email: EmailStr = Field(..., description="Email of the user updating the status")

class UserEmailRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address to get their issues")

class CompletionRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user/admin marking completion")
    completion_type: str = Field(..., description="Type of completion: 'admin' or 'user'")

class CompletionResponse(BaseModel):
    message: str
    ticket_id: str
    completion_type: str
    completed_by: str
    completed_at: str
    current_status: str
    is_fully_completed: bool

# Role-based system models
class UserRole(str, Enum):
    AUTHORITY = "authority"
    WORKER = "worker"
    CITIZEN = "citizen"

class Department(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="Department name")
    description: Optional[str] = Field(None, description="Department description")
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M %d-%m-%Y"))
    is_active: bool = Field(default=True, description="Whether department is active")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }

class WorkerProfile(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="Firebase user ID")
    email: EmailStr = Field(..., description="Worker's email")
    name: str = Field(..., description="Worker's full name")
    phone: Optional[str] = Field(None, description="Worker's phone number")
    employee_id: str = Field(..., description="Employee ID")
    department_id: str = Field(..., description="Department ID")
    department_name: str = Field(..., description="Department name")
    skills: List[str] = Field(default_factory=list, description="Worker's skills/specializations")
    profile_photo: Optional[str] = Field(None, description="Base64 encoded profile photo")
    is_active: bool = Field(default=True, description="Whether worker is active")
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M %d-%m-%Y"))
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }

class UserRegistration(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")
    name: str = Field(..., description="User's full name")
    phone: Optional[str] = Field(None, description="User's phone number")
    role: UserRole = Field(..., description="User role")
    # Worker-specific fields
    employee_id: Optional[str] = Field(None, description="Employee ID (required for workers)")
    department_id: Optional[str] = Field(None, description="Department ID (required for workers)")
    skills: Optional[List[str]] = Field(None, description="Worker skills")
    profile_photo: Optional[str] = Field(None, description="Base64 encoded profile photo")

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    phone: Optional[str] = None
    is_active: bool = True
    created_at: str
    # Worker-specific fields
    employee_id: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    skills: Optional[List[str]] = None
    profile_photo: Optional[str] = None

class IssueAssignment(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    ticket_id: str = Field(..., description="Issue ticket ID")
    assigned_to: str = Field(..., description="Worker email assigned to the issue")
    assigned_by: str = Field(..., description="Authority email who assigned the issue")
    assigned_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M %d-%m-%Y"))
    status: str = Field(default="assigned", description="Assignment status")
    notes: Optional[str] = Field(None, description="Assignment notes")
    completed_at: Optional[str] = Field(None, description="When assignment was completed")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }

class AssignmentRequest(BaseModel):
    ticket_id: str = Field(..., description="Issue ticket ID to assign")
    assigned_to: EmailStr = Field(..., description="Worker email to assign to")
    notes: Optional[str] = Field(None, description="Assignment notes")

class AssignmentResponse(BaseModel):
    message: str
    assignment_id: str
    ticket_id: str
    assigned_to: str
    assigned_by: str
    assigned_at: str
    status: str