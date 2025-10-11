import motor.motor_asyncio
import hashlib
import re
from typing import Optional, List
from models import IssueDB
import os
# from dotenv import load_dotenv
from difflib import SequenceMatcher
from datetime import datetime

# Database configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "municipal_issues")

# Create motor client with proper error handling
try:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    database = client[DATABASE_NAME]
    issues_collection = database.issues
    departments_collection = database.departments
    workers_collection = database.workers
    assignments_collection = database.assignments
    users_collection = database.users
except Exception as e:
    print(f"Warning: Could not connect to MongoDB: {e}")
    print("Using in-memory storage for development")
    client = None
    database = None
    issues_collection = None
    departments_collection = None
    workers_collection = None
    assignments_collection = None
    users_collection = None

# In-memory storage for development when MongoDB is not available
_in_memory_issues = []

async def create_new_issue(issue_data: dict) -> IssueDB:
    """Create a new issue in the database"""
    if issues_collection is not None:
        try:
            result = await issues_collection.insert_one(issue_data)
            issue_data["_id"] = str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting to MongoDB: {e}")
            # Fallback to in-memory storage
            import uuid
            issue_data["_id"] = str(uuid.uuid4())
            _in_memory_issues.append(issue_data)
    else:
        # Use in-memory storage
        import uuid
        issue_data["_id"] = str(uuid.uuid4())
        _in_memory_issues.append(issue_data)
    return IssueDB(**issue_data)

async def update_existing_issue(issue_id: str, new_email: str) -> IssueDB:
    """Update existing issue by adding new user email and incrementing count"""
    if issues_collection is not None:
        try:
            from bson import ObjectId
            result = await issues_collection.find_one_and_update(
                {"_id": ObjectId(issue_id)},
                {
                    "$addToSet": {"users": new_email},
                    "$inc": {"issue_count": 1}
                },
                return_document=True
            )
            if result:
                # Convert ObjectId to string
                if "_id" in result:
                    result["_id"] = str(result["_id"])
                return IssueDB(**result)
        except Exception as e:
            print(f"Error updating MongoDB: {e}")
    
    # Use in-memory storage
    for issue in _in_memory_issues:
        if issue.get("_id") == issue_id:
            if "users" not in issue:
                issue["users"] = []
            if new_email not in issue["users"]:
                issue["users"].append(new_email)
            issue["issue_count"] = issue.get("issue_count", 1) + 1
            return IssueDB(**issue)
    return None

async def get_all_issues() -> list[IssueDB]:
    """Get all issues from database"""
    if issues_collection is not None:
        try:
            cursor = issues_collection.find()
            issues = []
            async for issue in cursor:
                # Convert ObjectId to string
                if "_id" in issue:
                    issue["_id"] = str(issue["_id"])
                issues.append(IssueDB(**issue))
            return issues
        except Exception as e:
            print(f"Error querying MongoDB: {e}")
    
    # Use in-memory storage
    return [IssueDB(**issue) for issue in _in_memory_issues]

async def mark_issue_completion(ticket_id: str, completion_type: str, completed_by_email: str) -> Optional[dict]:
    """Mark issue completion by admin or user"""
    print(f"Database: Marking {completion_type} completion for ticket {ticket_id} by {completed_by_email}")
    
    if issues_collection is not None:
        try:
            from bson import ObjectId
            print("Database: Using MongoDB")
            
            # Find the issue first
            issue_data = await issues_collection.find_one({"ticket_id": ticket_id})
            if not issue_data:
                print(f"Database: No issue found with ticket_id {ticket_id}")
                return None
            
            current_time = datetime.now().strftime("%H:%M %d-%m-%Y")
            update_data = {
                "updated_at": current_time,
                "updated_by_email": completed_by_email
            }
            
            # Set completion fields based on type
            if completion_type == "admin":
                update_data["admin_completed_at"] = current_time
                update_data["admin_completed_by"] = completed_by_email
                # Update status to "admin_completed" if not already completed
                if issue_data.get("status") != "completed":
                    update_data["status"] = "admin_completed"
            elif completion_type == "user":
                update_data["user_completed_at"] = current_time
                update_data["user_completed_by"] = completed_by_email
            
            # Check if both admin and user have completed
            admin_completed = issue_data.get("admin_completed_at") or update_data.get("admin_completed_at")
            user_completed = issue_data.get("user_completed_at") or update_data.get("user_completed_at")
            
            if admin_completed and user_completed:
                update_data["status"] = "completed"
                update_data["completed_at"] = current_time
            
            # Update the issue
            result = await issues_collection.find_one_and_update(
                {"ticket_id": ticket_id},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                # Convert ObjectId to string
                if "_id" in result:
                    result["_id"] = str(result["_id"])
                print(f"Database: Successfully updated completion in MongoDB")
                return result
                
        except Exception as e:
            print(f"Database: Error updating completion in MongoDB: {e}")
    
    # Use in-memory storage
    print("Database: Using in-memory storage")
    for issue in _in_memory_issues:
        if issue.get("ticket_id") == ticket_id:
            current_time = datetime.now().strftime("%H:%M %d-%m-%Y")
            issue["updated_at"] = current_time
            issue["updated_by_email"] = completed_by_email
            
            # Set completion fields based on type
            if completion_type == "admin":
                issue["admin_completed_at"] = current_time
                issue["admin_completed_by"] = completed_by_email
                if issue.get("status") != "completed":
                    issue["status"] = "admin_completed"
            elif completion_type == "user":
                issue["user_completed_at"] = current_time
                issue["user_completed_by"] = completed_by_email
            
            # Check if both admin and user have completed
            admin_completed = issue.get("admin_completed_at")
            user_completed = issue.get("user_completed_at")
            
            if admin_completed and user_completed:
                issue["status"] = "completed"
                issue["completed_at"] = current_time
            
            print(f"Database: Successfully updated completion in memory")
            return issue
    
    print(f"Database: No issue found in memory with ticket_id {ticket_id}")
    return None