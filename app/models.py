from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum
from pydantic import ConfigDict

class Location(BaseModel):
    longitude: float
    latitude: float

class IssueRequest(BaseModel):
    text: str = Field(..., description="Text content describing the issue")
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., description="User's name")
    location: Optional[Location] = None
    photo: Optional[str] = None

class IssueResponse(BaseModel):
    ticket_id: str
    category: str
    address: str
    location: Optional[Location] = None
    description: str
    title: str
    photo: Optional[str] = None
    status: str
    created_at: str
    users: List[str]
    issue_count: int
    original_text: Optional[str] = None
    in_progress_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_by_email: Optional[str] = None
    updated_at: Optional[str] = None
    admin_completed_at: Optional[str] = None
    user_completed_at: Optional[str] = None
    admin_completed_by: Optional[str] = None
    user_completed_by: Optional[str] = None

class IssueDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    ticket_id: str
    category: str
    address: str
    location: Optional[Location] = None
    description: str
    title: str
    photo: Optional[str] = None
    status: str
    created_at: str
    users: List[str]
    issue_count: int
    content_hash: str
    original_text: str
    in_progress_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_by_email: Optional[str] = None
    updated_at: Optional[str] = None
    admin_completed_at: Optional[str] = None
    user_completed_at: Optional[str] = None
    admin_completed_by: Optional[str] = None
    user_completed_by: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )

class StatusUpdateRequest(BaseModel):
    status: str
    email: EmailStr

class UserEmailRequest(BaseModel):
    email: EmailStr

class CompletionRequest(BaseModel):
    email: EmailStr
    completion_type: str

class CompletionResponse(BaseModel):
    message: str
    ticket_id: str
    completion_type: str
    completed_by: str
    completed_at: str
    current_status: str
    is_fully_completed: bool

class UserRole(str, Enum):
    AUTHORITY = "authority"
    WORKER = "worker"
    CITIZEN = "citizen"

class Department(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    description: Optional[str] = None
    categories: List[str] = []
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M %d-%m-%Y"))

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
    
# Role-based system models
class UserRole(str, Enum):
    AUTHORITY = "authority"
    WORKER = "worker"
    CITIZEN = "citizen"

class Department(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="Department name")
    description: Optional[str] = Field(None, description="Department description")
    categories: List[str] = Field(default_factory=list, description="Issue categories handled by this department")
    is_active: bool = Field(default=True, description="Whether department is active")
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M %d-%m-%Y"))

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
    current_workload: int = Field(default=0, description="Current number of assigned tasks")
    max_capacity: int = Field(default=5, description="Maximum tasks this worker can handle")
    is_available: bool = Field(default=True, description="Whether worker is available for new assignments")
    specialization: Optional[str] = Field(None, description="Worker's primary specialization")
    experience_years: int = Field(default=0, description="Years of experience")
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
    ticket_id: str
    assigned_to: str
    assigned_by: str
    assigned_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M %d-%m-%Y"))
    status: str = "assigned"
    notes: Optional[str] = None
    completed_at: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )


class AssignmentRequest(BaseModel):
    ticket_id: str
    assigned_to: EmailStr
    notes: Optional[str] = None
    assigned_by: EmailStr

class AssignmentResponse(BaseModel):
    message: str
    assignment_id: str
    ticket_id: str
    assigned_to: str
    assigned_by: str
    assigned_at: str
    status: str
    
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