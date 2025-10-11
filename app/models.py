from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum


class Location(BaseModel):
    longitude: float
    latitude: float

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