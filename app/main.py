from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uuid
import re
from datetime import datetime
from typing import List, Set
import logging
from collections import deque
import time

logger = logging.getLogger(__name__)

# Message deduplication cache - stores recently processed message IDs
# Using deque for automatic size limiting and efficient operations
_processed_message_cache: deque = deque(maxlen=1000)  # Keep last 1000 message IDs
_processed_message_timestamps: dict = {}  # Track when messages were processed

from .models import (
    IssueRequest, IssueResponse, IssueDB, StatusUpdateRequest, UserEmailRequest, 
    CompletionRequest, CompletionResponse, UserRegistration, UserLogin, UserResponse,
    AssignmentRequest, AssignmentResponse, Department, WorkerProfile, IssueAssignment,  
    UserRole
)
from .database import (
    create_content_hash,
    find_existing_issue,
    create_new_issue,
    update_existing_issue,
    get_all_issues,
    update_issue_status_in_db,
    get_issues_by_user_email,
    get_issue_by_ticket_id,
    mark_issue_completion,
    issues_collection,
    _in_memory_issues,
    # New database functions
    get_all_departments,
    get_workers_by_department,
    get_all_workers,
    get_worker_by_email,
    create_issue_assignment,
    get_assignments_by_worker,
    get_assignment_by_ticket,
    update_assignment_status
)
from .gemini_service import analyze_text
from .auth_service import auth_service
from .telerivet_service import telerivet_service

app = FastAPI(
    title="Municipal Voice Assistant API",
    description="API for processing municipal issues from voice input",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Municipal Voice Assistant API is running!"}

@app.post("/submit-issue", response_model=IssueResponse)
async def submit_issue(issue_request: IssueRequest):
    """
    Submit a new municipal issue or update existing one if duplicate
    """
    try:
        # Create content hash for duplicate detection
        location_dict = None
        if issue_request.location:
            location_dict = {
                "longitude": issue_request.location.longitude,
                "latitude": issue_request.location.latitude
            }
        
        content_hash = await create_content_hash(issue_request.text, location_dict)
        
        # Analyze text using Gemini API first
        analysis_result = await analyze_text(issue_request.text)
        
        # Check if issue already exists
        existing_issue = await find_existing_issue(
            content_hash, 
            issue_request.text, 
            location_dict, 
            analysis_result["category"],
            issue_request.email
        )
        
        if existing_issue:
            # Update existing issue
            updated_issue = await update_existing_issue(
                existing_issue.id, 
                issue_request.email
            )
            
            return IssueResponse(
                ticket_id=updated_issue.ticket_id,
                category=updated_issue.category,
                address=updated_issue.address,
                location=updated_issue.location,
                description=updated_issue.description,
                title=updated_issue.title,
                photo=updated_issue.photo,
                status=updated_issue.status,
                created_at=updated_issue.created_at,
                users=updated_issue.users,
                issue_count=updated_issue.issue_count,
                original_text=updated_issue.original_text,
                in_progress_at=updated_issue.in_progress_at,
                completed_at=updated_issue.completed_at,
                updated_by_email=getattr(updated_issue, 'updated_by_email', None),
                updated_at=getattr(updated_issue, 'updated_at', None),
                admin_completed_at=getattr(updated_issue, 'admin_completed_at', None),
                user_completed_at=getattr(updated_issue, 'user_completed_at', None),
                admin_completed_by=getattr(updated_issue, 'admin_completed_by', None),
                user_completed_by=getattr(updated_issue, 'user_completed_by', None)
            )
        
        # Analyze text using Gemini API
        analysis_result = await analyze_text(issue_request.text)
        
        # Generate unique ticket ID
        ticket_id = f"TKT-{datetime.now().strftime('%d%m%Y')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Format current date and time
        current_datetime = datetime.now().strftime("%H:%M %d-%m-%Y")
        
        # Create new issue data
        new_issue_data = {
            "ticket_id": ticket_id,
            "category": analysis_result["category"],
            "address": analysis_result["address"],
            "location": location_dict,
            "description": analysis_result["description"],
            "title": analysis_result["title"],
            "photo": issue_request.photo,
            "status": "new",
            "created_at": current_datetime,
            "users": [issue_request.email],
            "issue_count": 1,
            "content_hash": content_hash,
            "original_text": issue_request.text,  # Store original user input
            "in_progress_at": None,  # Initialize timestamp fields
            "completed_at": None,
            "updated_by_email": issue_request.email,  # Set initial updater as the creator
            "updated_at": current_datetime,  # Set initial update time as creation time
            "admin_completed_at": None,  # Initialize completion fields
            "user_completed_at": None,
            "admin_completed_by": None,
            "user_completed_by": None
        }
        
        # Save to database
        created_issue = await create_new_issue(new_issue_data)

        return IssueResponse(
            ticket_id=created_issue.ticket_id,
            category=created_issue.category,
            address=created_issue.address,
            location=created_issue.location,
            description=created_issue.description,
            title=created_issue.title,
            photo=created_issue.photo,
            status=created_issue.status,
            created_at=created_issue.created_at,
            users=created_issue.users,
            issue_count=created_issue.issue_count,
            original_text=created_issue.original_text,
            in_progress_at=created_issue.in_progress_at,
            completed_at=created_issue.completed_at,
            updated_by_email=getattr(created_issue, 'updated_by_email', None),
            updated_at=getattr(created_issue, 'updated_at', None),
            admin_completed_at=getattr(created_issue, 'admin_completed_at', None),
            user_completed_at=getattr(created_issue, 'user_completed_at', None),
            admin_completed_by=getattr(created_issue, 'admin_completed_by', None),
            user_completed_by=getattr(created_issue, 'user_completed_by', None)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing issue: {str(e)}")

@app.get("/issues", response_model=List[IssueResponse])
async def get_issues(
    category: str = None,
    status: str = None,
    limit: int = 100,
    skip: int = 0
):
    """
    Get all issues from the database with optional filtering and pagination
    
    Parameters:
    - category: Filter by issue category (e.g., "Roads & Transport", "Water & Drainage")
    - status: Filter by issue status (e.g., "new", "in_progress", "resolved")
    - limit: Maximum number of issues to return (default: 100, max: 1000)
    - skip: Number of issues to skip for pagination (default: 0)
    """
    try:
        # Validate pagination parameters
        if limit > 1000:
            limit = 1000
        if limit < 1:
            limit = 100
        if skip < 0:
            skip = 0
            
        issues = await get_all_issues()
        
        # Apply filters
        filtered_issues = []
        for issue in issues:
            # Category filter
            if category and issue.category != category:
                continue
            # Status filter
            if status and issue.status != status:
                continue
            filtered_issues.append(issue)
        
        # Apply pagination
        paginated_issues = filtered_issues[skip:skip + limit]
        
        return [
            IssueResponse(
                ticket_id=issue.ticket_id,
                category=issue.category,
                address=issue.address,
                location=issue.location,
                description=issue.description,
                title=issue.title,
                photo=issue.photo,
                status=issue.status,
                created_at=issue.created_at,
                users=issue.users,
                issue_count=issue.issue_count,
                original_text=issue.original_text,
                in_progress_at=issue.in_progress_at,
                completed_at=issue.completed_at,
                updated_by_email=getattr(issue, 'updated_by_email', None),
                updated_at=getattr(issue, 'updated_at', None),
                admin_completed_at=getattr(issue, 'admin_completed_at', None),
                user_completed_at=getattr(issue, 'user_completed_at', None),
                admin_completed_by=getattr(issue, 'admin_completed_by', None),
                user_completed_by=getattr(issue, 'user_completed_by', None)
            )
            for issue in paginated_issues
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issues: {str(e)}")

@app.get("/issues/categories")
async def get_issue_categories():
    """
    Get all available issue categories
    """
    categories = [
        "Sanitation & Waste",
        "Water & Drainage", 
        "Electricity & Streetlights",
        "Roads & Transport",
        "Public Health & Safety",
        "Environment & Parks",
        "Building & Infrastructure",
        "Taxes & Documentation",
        "Emergency Services",
        "Animal Care & Control",
        "Other"
    ]
    return {"categories": categories}

@app.get("/issues/count")
async def get_issues_count(
    category: str = None,
    status: str = None
):
    """
    Get count of issues with optional filtering
    
    Parameters:
    - category: Filter by issue category
    - status: Filter by issue status
    """
    try:
        issues = await get_all_issues()
        
        # Apply filters
        filtered_issues = []
        for issue in issues:
            if category and issue.category != category:
                continue
            if status and issue.status != status:
                continue
            filtered_issues.append(issue)
        
        return {
            "total_count": len(filtered_issues),
            "category": category,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting issues: {str(e)}")

@app.put("/issues/{ticket_id}/status")
async def update_issue_status(ticket_id: str, status_update: StatusUpdateRequest):
    """
    Update the status of an existing issue by ticket ID
    
    Parameters:
    - ticket_id: The ticket ID of the issue to update
    - status_update: JSON body containing the new status and email
    
    Request Body:
    {
        "status": "new_status_value",
        "email": "user@example.com"
    }
    
    Valid status values: "new", "in_progress", "resolved", "closed", "rejected"
    """
    try:
        print(f"Received status update request for ticket: {ticket_id}")
        print(f"Status update data: {status_update}")
        
        # Validate status value
        new_status = status_update.status
        updated_by_email = status_update.email
        print(f"New status: {new_status}")
        print(f"Updated by email: {updated_by_email}")
        
        # Define valid status values (only 3 types as requested)
        valid_statuses = [
            "new", 
            "in_progress", 
            "in progress", 
            "admin_completed"  # New status for admin completion
        ]
        
        # Normalize the status (convert "in progress" to "in_progress")
        normalized_status = new_status
        if new_status == "in progress":
            normalized_status = "in_progress"
        
        print(f"Status normalization: '{new_status}' -> '{normalized_status}'")
        
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Prevent direct completion - must use completion endpoint
        if normalized_status == "completed":
            raise HTTPException(
                status_code=400, 
                detail="Cannot directly set status to 'completed'. Use the completion endpoint to mark completion by admin and user."
            )
        
        # Find and update the issue
        updated_issue = await update_issue_status_in_db(ticket_id, normalized_status, updated_by_email)
        
        if not updated_issue:
            raise HTTPException(status_code=404, detail=f"Issue with ticket ID {ticket_id} not found")
        
        # Send SMS notifications to users when status changes to in_progress or completed
        previous_status = updated_issue.get("previous_status", "unknown")
        print(f"📊 Status Update: {previous_status} → {normalized_status}")

        if normalized_status in ["in_progress", "completed", "admin_completed"]:
            # Only send SMS if status actually changed
            if previous_status != normalized_status:
                print(f"📲 Status changed - sending SMS notifications to all reporters")
                users_list = updated_issue.get("users", [])
                print(f"   👥 Number of users to notify: {len(users_list)}")

                if users_list:
                    sms_sent_count = 0
                    for user_identifier in users_list:
                        # Check if user_identifier is a phone number (starts with + or contains only digits)
                        if user_identifier.startswith("+") or (user_identifier.replace(" ", "").replace("-", "").isdigit() and len(user_identifier.replace(" ", "").replace("-", "")) >= 10):
                            print(f"   📱 Sending SMS to: {user_identifier}")
                            try:
                                await telerivet_service.send_status_update_sms_bilingual(
                                    user_identifier,
                                    ticket_id,
                                    previous_status,
                                    normalized_status
                                )
                                sms_sent_count += 1
                                print(f"   ✅ SMS sent successfully")
                            except Exception as sms_error:
                                print(f"   ⚠️ Error sending SMS to {user_identifier}: {sms_error}")
                                logger.error(f"Error sending SMS notification: {sms_error}")
                        else:
                            print(f"   ℹ️  Skipping {user_identifier} (not a phone number)")

                    print(f"✅ Status update SMS notifications completed - {sms_sent_count} SMS sent")
                else:
                    print(f"ℹ️  No users to notify")
            else:
                print(f"ℹ️  Status unchanged - skipping SMS notifications")
        else:
            print(f"ℹ️  Status '{normalized_status}' doesn't trigger SMS notifications")

        # Prepare response with timestamp information
        response_data = {
            "message": "Issue status updated successfully",
            "ticket_id": ticket_id,
            "old_status": updated_issue.get("previous_status"),
            "new_status": normalized_status,
            "updated_by_email": updated_by_email,
            "updated_at": datetime.now().strftime("%H:%M %d-%m-%Y")
        }
        
        # Add timestamp information if status was changed to in_progress or completed
        if normalized_status == "in_progress" and updated_issue.get("in_progress_at"):
            response_data["in_progress_at"] = updated_issue.get("in_progress_at")
        
        if normalized_status == "completed" and updated_issue.get("completed_at"):
            response_data["completed_at"] = updated_issue.get("completed_at")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_issue_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating issue status: {str(e)}")

@app.post("/issues/{ticket_id}/complete", response_model=CompletionResponse)
async def mark_issue_completion_endpoint(ticket_id: str, completion_request: CompletionRequest):
    """
    Mark issue completion by admin or user
    
    Parameters:
    - ticket_id: The ticket ID of the issue to mark as completed
    - completion_request: JSON body containing completion type and email
    
    Request Body:
    {
        "email": "user@example.com",
        "completion_type": "admin" or "user"
    }
    
    Rules:
    - Admin must mark completion first
    - User can only mark completion after admin has marked it
    - Issue is fully completed only when both admin and user have marked it
    """
    try:
        print(f"Received completion request for ticket: {ticket_id}")
        print(f"Completion data: {completion_request}")
        
        completion_type = completion_request.completion_type
        completed_by_email = completion_request.email
        
        # Validate completion type
        if completion_type not in ["admin", "user"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid completion_type. Must be 'admin' or 'user'"
            )
        
        # Get current issue data to check completion status
        if issues_collection is not None:
            try:
                from bson import ObjectId
                current_issue = await issues_collection.find_one({"ticket_id": ticket_id})
            except Exception as e:
                print(f"Error querying current issue: {e}")
                current_issue = None
        else:
            # Use in-memory storage
            current_issue = None
            for issue in _in_memory_issues:
                if issue.get("ticket_id") == ticket_id:
                    current_issue = issue
                    break
        
        if not current_issue:
            raise HTTPException(status_code=404, detail=f"Issue with ticket ID {ticket_id} not found")
        
        # Validation: User cannot mark completion before admin
        if completion_type == "user":
            admin_completed = current_issue.get("admin_completed_at")
            if not admin_completed:
                raise HTTPException(
                    status_code=400, 
                    detail="Admin must mark completion first before user can mark completion"
                )
        
        # Mark completion in database
        updated_issue = await mark_issue_completion(ticket_id, completion_type, completed_by_email)
        
        if not updated_issue:
            raise HTTPException(status_code=404, detail=f"Issue with ticket ID {ticket_id} not found")
        
        # Check if both completions are done
        admin_completed = updated_issue.get("admin_completed_at")
        user_completed = updated_issue.get("user_completed_at")
        is_fully_completed = bool(admin_completed and user_completed)

        # Prepare response
        response_data = {
            "message": f"Issue marked as {completion_type} completed successfully",
            "ticket_id": ticket_id,
            "completion_type": completion_type,
            "completed_by": completed_by_email,
            "completed_at": datetime.now().strftime("%H:%M %d-%m-%Y"),
            "current_status": updated_issue.get("status", "unknown"),
            "is_fully_completed": is_fully_completed
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in mark_issue_completion_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error marking issue completion: {str(e)}")

@app.post("/issues/user", response_model=List[IssueResponse])
async def get_user_issues(user_email_request: UserEmailRequest):
    """
    Get all issues created by a specific user email
    
    Parameters:
    - user_email_request: JSON body containing the user's email address
    
    Request Body:
    {
        "email": "user@example.com"
    }
    
    Returns:
    - List of all issues where the user's email is in the users array
    """
    try:
        user_email = user_email_request.email
        
        # Get issues for the user
        user_issues = await get_issues_by_user_email(user_email)
        
        # Convert to response format
        return [
            IssueResponse(
                ticket_id=issue.ticket_id,
                category=issue.category,
                address=issue.address,
                location=issue.location,
                description=issue.description,
                title=issue.title,
                photo=issue.photo,
                status=issue.status,
                created_at=issue.created_at,
                users=issue.users,
                issue_count=issue.issue_count,
                original_text=issue.original_text,
                in_progress_at=issue.in_progress_at,
                completed_at=issue.completed_at,
                updated_by_email=getattr(issue, 'updated_by_email', None),
                updated_at=getattr(issue, 'updated_at', None),
                admin_completed_at=getattr(issue, 'admin_completed_at', None),
                user_completed_at=getattr(issue, 'user_completed_at', None),
                admin_completed_by=getattr(issue, 'admin_completed_by', None),
                user_completed_by=getattr(issue, 'user_completed_by', None)
            )
            for issue in user_issues
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user issues: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "timestamp": datetime.now().strftime("%H:%M %d-%m-%Y")}

# Role-based authentication endpoints
@app.post("/auth/register")
async def register_user(user_data: UserRegistration):
    """
    Register a new user with role-based access
    """
    try:
        result = await auth_service.register_user(user_data)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/auth/login")
async def login_user(login_data: UserLogin):
    """
    Authenticate user and return user information
    """
    try:
        result = await auth_service.authenticate_user(login_data.email, login_data.password)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=401, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@app.get("/auth/profile/{email}")
async def get_user_profile(email: str):
    """
    Get user profile information
    """
    try:
        result = await auth_service.get_user_profile(email)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

# Department management endpoints
@app.get("/departments", response_model=List[Department])
async def get_departments():
    """
    Get all active departments
    """
    try:
        departments = await get_all_departments()
        return departments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching departments: {str(e)}")

@app.post("/departments", response_model=Department)
async def create_department_endpoint(department_data: dict):
    """
    Create a new department
    """
    try:
        from .database import create_department
        department = await create_department(department_data)
        return department
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating department: {str(e)}")

# Worker management endpoints
@app.get("/workers", response_model=List[WorkerProfile])
async def get_workers(department_id: str = None):
    """
    Get all workers, optionally filtered by department
    """
    try:
        if department_id:
            workers = await get_workers_by_department(department_id)
        else:
            workers = await get_all_workers()
        return workers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching workers: {str(e)}")

@app.get("/workers/{email}", response_model=WorkerProfile)
async def get_worker_by_email_endpoint(email: str):
    """
    Get worker profile by email
    """
    try:
        worker = await get_worker_by_email(email)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        return worker
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching worker: {str(e)}")

# Issue assignment endpoints
@app.post("/assignments", response_model=AssignmentResponse)
async def create_assignment_endpoint(assignment_request: AssignmentRequest, assigned_by_email: str = "admin@example.com"):
    """Create a new assignment"""
    try:
        # Verify issue exists
        issues = await get_all_issues()
        issue = next((i for i in issues if i.ticket_id == assignment_request.ticket_id), None)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        # Verify worker exists
        worker = await get_worker_by_email(assignment_request.assigned_to)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        # Check for existing assignment
        existing_assignment = await get_assignment_by_ticket(assignment_request.ticket_id)
        if existing_assignment:
            raise HTTPException(status_code=400, detail="Issue is already assigned")
        
        # Create assignment data
        assignment_data = {
            "ticket_id": assignment_request.ticket_id,
            "assigned_to": assignment_request.assigned_to,
            "assigned_by": assigned_by_email,
            "assigned_at": datetime.now().strftime("%H:%M %d-%m-%Y"),
            "status": "assigned",
            "notes": assignment_request.notes or ""
        }
        
        # Create the assignment
        assignment = await create_issue_assignment(assignment_data)

        # Update issue status to in_progress
        await update_issue_status_in_db(assignment_request.ticket_id, "in_progress", assigned_by_email)

        return AssignmentResponse(
            message="Issue assigned successfully",
            assignment_id=str(assignment.id) if hasattr(assignment, 'id') else str(assignment._id),
            ticket_id=assignment.ticket_id,
            assigned_to=assignment.assigned_to,
            assigned_by=assignment.assigned_by,
            assigned_at=assignment.assigned_at,
            status=assignment.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating assignment: {str(e)}")



@app.get("/assignments/worker/{worker_email}", response_model=List[IssueAssignment])
async def get_worker_assignments_endpoint(worker_email: str):
    """Get all assignments for a specific worker"""
    return await get_assignments_by_worker(worker_email)


@app.put("/assignments/{ticket_id}/status")
async def update_assignment_status_endpoint(ticket_id: str, status: str, notes: str = None):
    """
    Update assignment status
    """
    try:
        assignment = await update_assignment_status(ticket_id, status, notes)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {
            "message": "Assignment status updated successfully",
            "ticket_id": ticket_id,
            "status": status,
            "updated_at": datetime.now().strftime("%H:%M %d-%m-%Y")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating assignment: {str(e)}")

# in main.py

@app.post("/workers/register", response_model=UserResponse)
async def register_worker(worker_data: dict):
    """Register a new worker"""
    try:
        # Automatically add the 'role' for worker registration
        worker_data['role'] = UserRole.WORKER
        
        # This is the fix: Let Pydantic create the object directly from the dictionary.
        # This is more robust and prevents data from being lost.
        user_registration = UserRegistration(**worker_data)
        
        # Now, call the auth service with the correctly populated object
        result = await auth_service.register_user(user_registration)
        
        if result["success"]:
            # The result from the service contains a nested 'user' object
            return UserResponse(**result["user"])
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Registration failed."))

    except Exception as e:
        # This will log the actual error to your Render logs for easier debugging
        print(f"CRASH in /workers/register: {e}") 
        raise HTTPException(status_code=500, detail=f"Worker registration failed: {str(e)}")
    
@app.post("/workers/login")
async def worker_login(login_data: UserLogin):
    """Worker login endpoint"""
    try:
        result = await auth_service.authenticate_user(login_data.email, login_data.password)
        
        if result["success"] and result["user"]["role"] == UserRole.WORKER.value:
            return result
        elif result["success"] and result["user"]["role"] != UserRole.WORKER.value:
            raise HTTPException(status_code=403, detail="Access denied. Worker account required.")
        else:
            raise HTTPException(status_code=401, detail=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker login failed: {str(e)}")

@app.get("/workers", response_model=List[WorkerProfile])
async def get_all_workers_endpoint():
    """Get all active workers"""
    try:
        workers = await get_all_workers()
        return workers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching workers: {str(e)}")

@app.get("/workers/department/{department_id}", response_model=List[WorkerProfile])
async def get_workers_by_department_endpoint(department_id: str):
    """Get workers by department ID"""
    try:
        workers = await get_workers_by_department(department_id)
        return workers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching workers by department: {str(e)}")

@app.get("/workers/profile/{email}", response_model=WorkerProfile)
async def get_worker_profile_endpoint(email: str):
    """Get worker profile by email"""
    try:
        worker = await get_worker_by_email(email)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        return worker
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching worker profile: {str(e)}")

# ============= ASSIGNMENT ROUTES =============

@app.get("/assignments", response_model=List[IssueAssignment])
async def get_all_assignments():
    """Get all assignments"""
    try:
        from .database import get_all_assignments
        all_assignments = await get_all_assignments()
        return all_assignments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching assignments: {str(e)}")

@app.post("/assignments", response_model=AssignmentResponse)
async def create_assignment_endpoint(assignment_request: AssignmentRequest, assigned_by_email: str = "admin@example.com"):
    """Create a new assignment"""
    try:
        issues = await get_all_issues()
        issue = next((i for i in issues if i.ticket_id == assignment_request.ticket_id), None)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        worker = await get_worker_by_email(assignment_request.assigned_to)
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        existing_assignment = await get_assignment_by_ticket(assignment_request.ticket_id)
        if existing_assignment:
            raise HTTPException(status_code=400, detail="Issue is already assigned")
        
        assignment_data = {
            "ticket_id": assignment_request.ticket_id,
            "assigned_to": assignment_request.assigned_to,
            "assigned_by": assigned_by_email,
            "assigned_at": datetime.now().strftime("%H:%M %d-%m-%Y"),
            "status": "assigned",
            "notes": assignment_request.notes or ""
        }
        
        assignment = await create_issue_assignment(assignment_data)
        await update_issue_status_in_db(assignment_request.ticket_id, "in_progress", assigned_by_email)
        
        try:
            current_workload = getattr(worker, 'current_workload', 0)
            await update_worker_profile(assignment_request.assigned_to, {
                "current_workload": current_workload + 1
            })
        except Exception as e:
            print(f"Warning: Could not update worker workload: {e}")

        return AssignmentResponse(
            message="Issue assigned successfully",
            assignment_id=assignment.id if hasattr(assignment, 'id') else str(assignment._id),
            ticket_id=assignment.ticket_id,
            assigned_to=assignment.assigned_to,
            assigned_by=assignment.assigned_by,
            assigned_at=assignment.assigned_at,
            status=assignment.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating assignment: {str(e)}")

@app.get("/assignments/worker/{worker_email}", response_model=List[IssueAssignment])
async def get_worker_assignments_endpoint(worker_email: str):
    """Get all assignments for a specific worker"""
    try:
        assignments = await get_assignments_by_worker(worker_email)
        return assignments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching worker assignments: {str(e)}")

@app.get("/issues/unassigned")
async def get_unassigned_issues():
    """Get issues that haven't been assigned to any worker"""
    try:
        all_issues = await get_all_issues()
        
        if assignments_collection is not None:
            try:
                assigned_tickets = set()
                cursor = assignments_collection.find({}, {"ticket_id": 1})
                async for assignment in cursor:
                    assigned_tickets.add(assignment["ticket_id"])
            except Exception as e:
                print(f"Error querying assignments: {e}")
                assigned_tickets = set()
        else:
            from .database import _in_memory_assignments
            assigned_tickets = {assignment.get("ticket_id") for assignment in _in_memory_assignments}
        
        unassigned_issues = [
            issue for issue in all_issues 
            if issue.ticket_id not in assigned_tickets
        ]
        
        return [
            IssueResponse(
                ticket_id=issue.ticket_id,
                category=issue.category,
                address=issue.address,
                location=issue.location,
                description=issue.description,
                title=issue.title,
                photo=issue.photo,
                status=issue.status,
                created_at=issue.created_at,
                users=issue.users,
                issue_count=issue.issue_count,
                original_text=issue.original_text,
                in_progress_at=issue.in_progress_at,
                completed_at=issue.completed_at,
                updated_by_email=getattr(issue, 'updated_by_email', None),
                updated_at=getattr(issue, 'updated_at', None),
                admin_completed_at=getattr(issue, 'admin_completed_at', None),
                user_completed_at=getattr(issue, 'user_completed_at', None),
                admin_completed_by=getattr(issue, 'admin_completed_by', None),
                user_completed_by=getattr(issue, 'user_completed_by', None)
            )
            for issue in unassigned_issues
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching unassigned issues: {str(e)}")


# ============= TELERIVET SMS WEBHOOK =============

@app.post("/telerivet/webhook")
async def telerivet_webhook(request: Request):
    """
    Telerivet webhook endpoint to receive incoming SMS messages

    When a user sends an SMS to your Telerivet phone number, this endpoint:
    1. Receives the SMS content from Telerivet
    2. Processes it using Gemini AI to extract issue details
    3. Creates a new issue in the database
    4. Sends a confirmation SMS back to the user

    Note: Configure this URL in your Telerivet dashboard under
    Phones > Your Phone > Services > Webhook
    """
    try:
        # Telerivet can send data as form data OR JSON
        # Try to parse as form data first (most common)
        content_type = request.headers.get('content-type', '')

        if 'application/json' in content_type:
            webhook_data = await request.json()
        else:
            # Parse form data
            form_data = await request.form()
            webhook_data = dict(form_data)

        print("=" * 50)
        print("📨 TELERIVET WEBHOOK RECEIVED")
        print(f"Content-Type: {content_type}")
        print(f"Data keys: {list(webhook_data.keys())}")
        print(f"Full data: {webhook_data}")
        print("=" * 50)
        logger.info(f"Received Telerivet webhook: {webhook_data}")

        # === CRITICAL FILTERING SECTION ===
        # Use BLACKLIST approach: Only reject webhooks we KNOW are not incoming user messages
        # Be LENIENT with missing/empty fields (they might be legitimate incoming messages)

        # 1. BLACKLIST: Reject known outgoing/status event types
        event_type = webhook_data.get('event', '').lower().strip()
        print(f"🔍 Event type: '{event_type}'")

        # List of events we DON'T want to process (outgoing messages, status updates, etc.)
        BLACKLISTED_EVENTS = [
            'send_status',      # When bot sends a message
            'delivery_status',  # Delivery confirmation
            'sent',            # Message sent event
            'delivered',       # Message delivered event
            'failed',          # Send failed event
            'message_sent',    # Alternative sent event
        ]

        if event_type and event_type in BLACKLISTED_EVENTS:
            print(f"⏭️  IGNORING: Event type '{event_type}' is blacklisted (outgoing/status event)")
            logger.info(f"Ignored webhook - blacklisted event: {event_type}")
            return {"status": "ignored", "reason": f"blacklisted_event: {event_type}"}

        print(f"✅ Event type OK ('{event_type}' not in blacklist)")

        # 2. BLACKLIST: Reject if direction is explicitly outgoing
        message_direction = webhook_data.get('direction', '').lower().strip()
        print(f"🔍 Message direction: '{message_direction}'")

        if message_direction in ['outgoing', 'sent', 'sending']:
            print(f"⏭️  IGNORING: Direction is '{message_direction}' (outgoing message)")
            logger.info(f"Ignored webhook - outgoing direction: {message_direction}")
            return {"status": "ignored", "reason": f"outgoing_direction: {message_direction}"}

        print(f"✅ Direction OK ('{message_direction}' not outgoing)")

        # 3. BLACKLIST: Reject if status indicates sent/sending (but allow empty/received)
        message_status = webhook_data.get('status', '').lower().strip()
        print(f"🔍 Message status: '{message_status}'")

        BLACKLISTED_STATUSES = [
            'sent',
            'sending',
            'queued',
            'failed',
            'delivered'
        ]

        if message_status and message_status in BLACKLISTED_STATUSES:
            print(f"⏭️  IGNORING: Message status '{message_status}' indicates outgoing/failed message")
            logger.info(f"Ignored webhook - blacklisted status: {message_status}")
            return {"status": "ignored", "reason": f"blacklisted_status: {message_status}"}

        print(f"✅ Status OK ('{message_status}' not in blacklist)")

        # Extract webhook secret for validation (if configured)
        secret = webhook_data.get('secret', '')

        # Skip validation if no data at all (for initial testing)
        if not webhook_data:
            logger.warning("Empty webhook data received")
            return {"status": "error", "message": "Empty webhook data"}

        # Process incoming SMS
        sms_data = telerivet_service.process_incoming_sms(webhook_data)
        from_phone = sms_data["phone"]
        message_text = sms_data["text"]
        message_id = sms_data["message_id"]

        print(f"📋 Extracted data:")
        print(f"  📱 Phone: {from_phone}")
        print(f"  💬 Message: {message_text}")
        print(f"  🆔 Message ID: {message_id}")

        if not message_text:
            print("❌ ERROR: Empty message text")
            logger.warning("Empty message received")
            return {"status": "error", "message": "Empty message"}

        if not from_phone:
            print("❌ ERROR: No phone number in webhook data")
            logger.warning("No phone number in webhook data")
            return {"status": "error", "message": "No phone number"}

        # 4. MESSAGE DEDUPLICATION - Only if message_id exists
        if message_id:
            print(f"🔍 Checking deduplication for message ID: {message_id}")
            if message_id in _processed_message_cache:
                print(f"⏭️  IGNORING: Message ID '{message_id}' already processed")
                # Check how recently it was processed
                if message_id in _processed_message_timestamps:
                    time_ago = time.time() - _processed_message_timestamps[message_id]
                    print(f"   ⏱️  Originally processed {time_ago:.1f} seconds ago")
                logger.info(f"Duplicate message ignored - ID: {message_id}")
                return {"status": "ignored", "reason": "duplicate message ID"}

            # Add to cache - this is a new message
            _processed_message_cache.append(message_id)
            _processed_message_timestamps[message_id] = time.time()
            print(f"✅ Message ID '{message_id}' cached for deduplication")

            # Clean old timestamps (keep only last 1000)
            if len(_processed_message_timestamps) > 1000:
                # Remove oldest entries
                sorted_ids = sorted(_processed_message_timestamps.items(), key=lambda x: x[1])
                for old_id, _ in sorted_ids[:-1000]:
                    del _processed_message_timestamps[old_id]
        else:
            print(f"ℹ️  No message ID provided - deduplication skipped (will process)")

        print(f"=" * 50)
        print(f"✅ ALL FILTERS PASSED - Processing incoming message")
        print(f"=" * 50)

        # Check if message is a status query (format: "status:ticket_id" or "STATUS:TKT-...")
        status_query_pattern = r'^status\s*:\s*(.+)$'
        status_match = re.match(status_query_pattern, message_text.strip(), re.IGNORECASE)

        if status_match:
            # User is querying status of an issue
            ticket_id = status_match.group(1).strip()
            print(f"🔍 STATUS QUERY DETECTED")
            print(f"   📋 Ticket ID: {ticket_id}")
            print(f"   📱 From: {from_phone}")

            # Look up the issue
            issue = await get_issue_by_ticket_id(ticket_id)

            if not issue:
                # Send error message in bilingual format
                error_message = (
                    f"❌ Ticket not found / टिकट नहीं मिला\n\n"
                    f"Ticket: {ticket_id}\n\n"
                    f"Please check the ticket ID and try again.\n"
                    f"कृपया टिकट आईडी जांचें और पुनः प्रयास करें।"
                )
                print(f"❌ Ticket {ticket_id} not found in database")
                print(f"📤 Sending error SMS to {from_phone}")
                telerivet_service.send_sms(from_phone, error_message)

                return {
                    "status": "error",
                    "message": "Ticket not found",
                    "ticket_id": ticket_id
                }

            # Send issue details
            print(f"✅ Ticket found in database")
            print(f"📤 Sending issue details SMS to {from_phone}")
            issue_dict = issue.dict() if hasattr(issue, 'dict') else issue.__dict__

            sms_sent = await telerivet_service.send_issue_details_sms(from_phone, issue_dict)
            print(f"✅ STATUS QUERY COMPLETED - SMS sent: {sms_sent}")

            return {
                "status": "success",
                "message": "Status query processed - issue details sent",
                "ticket_id": ticket_id,
                "sms_sent": sms_sent
            }

        print("=" * 50)
        print("📝 NEW ISSUE CREATION FLOW")
        print(f"   📱 From: {from_phone}")
        print(f"   💬 Message: {message_text[:50]}...")
        print("=" * 50)

        # Extract issue information using Gemini
        try:
            print("🤖 Starting Gemini AI analysis...")
            analysis_result = await analyze_text(message_text)
            print(f"✅ Gemini AI analysis complete")
            print(f"   📂 Category: {analysis_result.get('category')}")
            print(f"   📌 Title: {analysis_result.get('title')}")
            print(f"   📍 Address: {analysis_result.get('address')}")
        except Exception as e:
            print(f"❌ Gemini AI analysis failed: {e}")
            logger.error(f"Gemini AI error: {e}")
            return {"status": "error", "message": f"AI analysis failed: {str(e)}"}

        # Create content hash for duplicate detection
        content_hash = await create_content_hash(message_text, None)
        print(f"✅ Content hash created: {content_hash[:16]}...")

        # Check if issue already exists
        print("🔍 Checking for duplicate issues...")
        existing_issue = await find_existing_issue(
            content_hash,
            message_text,
            None,
            analysis_result["category"],
            from_phone  # Use phone number as identifier
        )

        if existing_issue:
            print(f"🔄 DUPLICATE DETECTED!")
            print(f"   📋 Existing Ticket: {existing_issue.ticket_id}")
            print(f"   👥 Current reporters: {existing_issue.issue_count}")
            print(f"   📱 Adding {from_phone} to reporters list")

            # Update existing issue with the new phone number
            updated_issue = await update_existing_issue(existing_issue.id, from_phone)

            # Send SMS confirmation with full details
            print(f"📤 Sending duplicate confirmation SMS to {from_phone}...")
            sms_sent = await telerivet_service.send_ticket_confirmation_sms(
                phone=from_phone,
                ticket_id=updated_issue.ticket_id,
                category=updated_issue.category,
                title=updated_issue.title,
                address=updated_issue.address,
                description=updated_issue.description
            )
            print(f"✅ DUPLICATE HANDLING COMPLETED - SMS sent: {sms_sent}")

            return {
                "status": "success",
                "message": "Duplicate issue - added to reporters",
                "ticket_id": updated_issue.ticket_id,
                "issue_count": updated_issue.issue_count,
                "sms_sent": sms_sent
            }

        print("✨ No duplicate found - Creating NEW issue...")

        # Generate unique ticket ID
        ticket_id = f"TKT-{datetime.now().strftime('%d%m%Y')}-{str(uuid.uuid4())[:8].upper()}"
        current_datetime = datetime.now().strftime("%H:%M %d-%m-%Y")
        print(f"   🎫 Generated ticket ID: {ticket_id}")

        # Create new issue
        new_issue_data = {
            "ticket_id": ticket_id,
            "category": analysis_result["category"],
            "address": analysis_result["address"],
            "location": None,
            "description": analysis_result["description"],
            "title": analysis_result["title"],
            "photo": None,
            "status": "new",
            "created_at": current_datetime,
            "users": [from_phone],  # Store phone number
            "issue_count": 1,
            "content_hash": content_hash,
            "original_text": message_text,
            "updated_by_email": from_phone,
            "updated_at": current_datetime,
            "in_progress_at": None,
            "completed_at": None,
            "admin_completed_at": None,
            "user_completed_at": None,
            "admin_completed_by": None,
            "user_completed_by": None
        }

        # Save to database
        print(f"💾 Saving new issue to database...")
        created_issue = await create_new_issue(new_issue_data)
        print(f"✅ Issue saved to database")
        print(f"   🎫 Ticket ID: {created_issue.ticket_id}")
        print(f"   📂 Category: {created_issue.category}")
        print(f"   📍 Address: {created_issue.address}")

        # Send SMS confirmation with full details
        print(f"📤 Sending new issue confirmation SMS to {from_phone}...")
        sms_sent = await telerivet_service.send_ticket_confirmation_sms(
            phone=from_phone,
            ticket_id=created_issue.ticket_id,
            category=created_issue.category,
            title=created_issue.title,
            address=created_issue.address,
            description=created_issue.description
        )
        print(f"✅ NEW ISSUE CREATION COMPLETED - SMS sent: {sms_sent}")
        print("=" * 50)

        logger.info(f"New issue created successfully: {ticket_id}")

        return {
            "status": "success",
            "message": "New issue created",
            "ticket_id": created_issue.ticket_id,
            "category": created_issue.category,
            "sms_sent": sms_sent
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Telerivet webhook: {str(e)}")
        return {
            "status": "error",
            "message": "Failed to process message"
        }


# ============= TELERIVET SMS DIAGNOSTICS =============

@app.get("/telerivet/check_phone_status")
async def check_telerivet_phone_status():
    """
    Check the status of the Telerivet phone and recent messages
    Useful for debugging SMS delivery issues
    """
    try:
        import requests

        if not telerivet_service.is_configured:
            return {
                "error": "Telerivet not configured",
                "configured": False
            }

        # Get phone status
        phone_url = f"{telerivet_service.base_url}/projects/{telerivet_service.project_id}/phones/{telerivet_service.phone_id}"

        phone_response = requests.get(
            phone_url,
            auth=(telerivet_service.api_key, ''),
            timeout=10
        )

        phone_data = phone_response.json() if phone_response.status_code == 200 else {}

        # Get recent messages
        messages_url = f"{telerivet_service.base_url}/projects/{telerivet_service.project_id}/messages"

        messages_response = requests.get(
            messages_url,
            auth=(telerivet_service.api_key, ''),
            params={"limit": 10, "direction": "outgoing"},
            timeout=10
        )

        messages_data = messages_response.json() if messages_response.status_code == 200 else {}

        return {
            "phone_status": {
                "name": phone_data.get("name"),
                "phone_number": phone_data.get("phone_number"),
                "phone_type": phone_data.get("phone_type"),
                "battery": phone_data.get("battery"),
                "charging": phone_data.get("charging"),
                "internet_type": phone_data.get("internet_type"),
                "last_active_time": phone_data.get("last_active_time"),
                "send_paused": phone_data.get("send_paused"),
                "send_limit": phone_data.get("send_limit"),
                "app_version": phone_data.get("app_version")
            },
            "recent_messages": [
                {
                    "id": msg.get("id"),
                    "to_number": msg.get("to_number"),
                    "status": msg.get("status"),
                    "time_created": msg.get("time_created"),
                    "time_sent": msg.get("time_sent"),
                    "error_message": msg.get("error_message")
                }
                for msg in messages_data.get("data", [])[:5]
            ],
            "diagnostics": {
                "queued_messages": sum(1 for msg in messages_data.get("data", []) if msg.get("status") == "queued"),
                "failed_messages": sum(1 for msg in messages_data.get("data", []) if msg.get("status") == "failed"),
                "sent_messages": sum(1 for msg in messages_data.get("data", []) if msg.get("status") == "sent"),
                "delivered_messages": sum(1 for msg in messages_data.get("data", []) if msg.get("status") == "delivered")
            }
        }

    except Exception as e:
        logger.error(f"Error checking Telerivet status: {e}")
        return {
            "error": str(e),
            "configured": telerivet_service.is_configured
        }


# ============= TELERIVET SMS DELIVERY STATUS WEBHOOK =============

@app.post("/telerivet/delivery_status")
async def telerivet_delivery_status_webhook(request: Request):
    """
    Telerivet delivery status webhook to track SMS delivery

    This endpoint receives callbacks from Telerivet when:
    - SMS is queued for sending
    - SMS is sent successfully
    - SMS fails to send
    - SMS is delivered to recipient
    - SMS delivery fails

    Configure this URL in Telerivet dashboard under:
    Phones > Your Phone > Services > Webhook for Message Events
    """
    try:
        # Parse webhook data
        content_type = request.headers.get('content-type', '')

        if 'application/json' in content_type:
            webhook_data = await request.json()
        else:
            form_data = await request.form()
            webhook_data = dict(form_data)

        print("=" * 50)
        print("DELIVERY STATUS WEBHOOK:")
        print(f"Webhook data: {webhook_data}")
        print("=" * 50)

        # Extract key delivery information
        message_id = webhook_data.get('id', webhook_data.get('message_id', ''))
        status = webhook_data.get('status', '')
        to_number = webhook_data.get('to_number', '')
        error_message = webhook_data.get('error_message', '')
        error_code = webhook_data.get('error_code', '')

        # Log the delivery status
        log_message = f"""
        SMS Delivery Status Update:
        - Message ID: {message_id}
        - To Number: {to_number}
        - Status: {status}
        - Error Code: {error_code}
        - Error Message: {error_message}
        """

        if error_message or error_code:
            logger.error(log_message)
            print(f"❌ SMS DELIVERY FAILED: {error_message} (Code: {error_code})")
        elif status == 'sent':
            logger.info(log_message)
            print(f"✅ SMS SENT: Message {message_id} to {to_number}")
        elif status == 'delivered':
            logger.info(log_message)
            print(f"✅ SMS DELIVERED: Message {message_id} to {to_number}")
        elif status == 'queued':
            logger.info(log_message)
            print(f"📤 SMS QUEUED: Message {message_id} to {to_number}")
        else:
            logger.info(log_message)
            print(f"📊 SMS STATUS: {status} for message {message_id}")

        return {
            "status": "received",
            "message_id": message_id,
            "acknowledged": True
        }

    except Exception as e:
        logger.error(f"Error processing delivery status webhook: {str(e)}")
        print(f"❌ Error in delivery status webhook: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to process delivery status: {str(e)}"
        }


# Initialize default departments on startup
@app.on_event("startup")
async def startup_event():
    """Initialize default departments on application startup"""
    await auth_service.initialize_default_departments()
    
    # Initialize departments with categories
    default_departments_with_categories = [
        {
            "name": "Electricity Department", 
            "description": "Handles electrical issues and street lighting",
            "categories": ["Electricity & Streetlights"],
            "is_active": True,
            "created_at": datetime.now().strftime("%H:%M %d-%m-%Y")
        },
        {
            "name": "Water Supply Department",
            "description": "Manages water supply and drainage systems", 
            "categories": ["Water & Drainage"],
            "is_active": True,
            "created_at": datetime.now().strftime("%H:%M %d-%m-%Y")
        },
        {
            "name": "Road Maintenance Department",
            "description": "Manages road maintenance and transport infrastructure",
            "categories": ["Roads & Transport"], 
            "is_active": True,
            "created_at": datetime.now().strftime("%H:%M %d-%m-%Y")
        },
        {
            "name": "Sanitation Department",
            "description": "Handles waste collection and sanitation issues",
            "categories": ["Sanitation & Waste"],
            "is_active": True, 
            "created_at": datetime.now().strftime("%H:%M %d-%m-%Y")
        }
    ]
    
    # Create departments if they don't exist
    try:
        existing_depts = await get_all_departments()
        existing_names = {dept.name for dept in existing_depts}
        
        from .database import create_department
        for dept_data in default_departments_with_categories:
            if dept_data["name"] not in existing_names:
                await create_department(dept_data)
                print(f"Created department: {dept_data['name']}")
    except Exception as e:
        print(f"Error initializing departments: {e}")
        
        app = FastAPI(
    title="Municipal Voice Assistant API",
    description="API for processing municipal issues from voice input",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, you should restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Initialize default departments on application startup"""
    await auth_service.initialize_default_departments()


# --- Root and Health Check ---
@app.get("/")
async def root():
    return {"message": "Municipal Voice Assistant API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().strftime("%H:%M %d-%m-%Y")}


# --- Issue Routes ---

@app.post("/submit-issue", response_model=IssueResponse)
async def submit_issue(issue_request: IssueRequest):
    """Submit a new municipal issue or update existing one if duplicate"""
    # This function appears correct and is left as is.
    try:
        location_dict = issue_request.location.model_dump() if issue_request.location else None
        content_hash = await create_content_hash(issue_request.text, location_dict)
        analysis_result = await analyze_text(issue_request.text)
        
        existing_issue = await find_existing_issue(
            content_hash, issue_request.text, location_dict,
            analysis_result["category"], issue_request.email
        )
        
        if existing_issue:
            updated_issue = await update_existing_issue(existing_issue.id, issue_request.email)
            return updated_issue
        
        ticket_id = f"TKT-{datetime.now().strftime('%d%m%Y')}-{str(uuid.uuid4())[:8].upper()}"
        current_datetime = datetime.now().strftime("%H:%M %d-%m-%Y")
        
        new_issue_data = {
            "ticket_id": ticket_id, "category": analysis_result["category"],
            "address": analysis_result["address"], "location": location_dict,
            "description": analysis_result["description"], "title": analysis_result["title"],
            "photo": issue_request.photo, "status": "new", "created_at": current_datetime,
            "users": [issue_request.email], "issue_count": 1, "content_hash": content_hash,
            "original_text": issue_request.text, "updated_by_email": issue_request.email,
            "updated_at": current_datetime
        }
        
        created_issue = await create_new_issue(new_issue_data)
        return created_issue
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing issue: {str(e)}")

# ... (All your other non-conflicting routes for issues, etc., go here) ...
# I am including the routes from your original file.

@app.get("/issues", response_model=List[IssueResponse])
async def get_issues(category: str = None, status: str = None, limit: int = 100, skip: int = 0):
    all_issues = await get_all_issues()
    filtered_issues = [
        issue for issue in all_issues
        if (category is None or issue.category == category) and (status is None or issue.status == status)
    ]
    return filtered_issues[skip : skip + limit]

@app.get("/issues/categories")
async def get_issue_categories():
    departments = await get_all_departments()
    categories = set()
    for dept in departments:
        categories.update(dept.categories)
    return list(categories)

@app.put("/issues/{ticket_id}/status")
async def update_issue_status(ticket_id: str, status_update: StatusUpdateRequest):
    """Update the status of an existing issue by ticket ID"""
    try:
        print(f"📧 Status update request - Ticket: {ticket_id}, New Status: {status_update.status}")
        
        # Validate status value
        valid_statuses = ["new", "in_progress", "in progress", "admin_completed"]
        
        # Normalize the status
        normalized_status = status_update.status
        if status_update.status == "in progress":
            normalized_status = "in_progress"
        
        if status_update.status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Get the issue first to capture old status
        all_issues = await get_all_issues()
        current_issue = next((i for i in all_issues if i.ticket_id == ticket_id), None)
        
        if not current_issue:
            raise HTTPException(status_code=404, detail=f"Issue with ticket ID {ticket_id} not found")
        
        old_status = current_issue.status
        
        # Update the issue
        updated_issue = await update_issue_status_in_db(ticket_id, normalized_status, status_update.email)
        
        if not updated_issue:
            raise HTTPException(status_code=404, detail=f"Issue with ticket ID {ticket_id} not found")
        
        return {
            "message": "Issue status updated successfully",
            "ticket_id": ticket_id,
            "old_status": old_status,
            "new_status": normalized_status,
            "updated_by_email": status_update.email,
            "updated_at": datetime.now().strftime("%H:%M %d-%m-%Y"),
            "notification_sent": len(updated_issue.get("users", [])) > 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in update_issue_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating issue status: {str(e)}")

# --- Worker and Auth Routes ---

@app.post("/workers/register", response_model=UserResponse)
async def register_worker(worker_data: dict):
    """Register a new worker"""
    try:
        # Automatically add the 'role' for worker registration
        worker_data['role'] = UserRole.WORKER
        
        # This is the final fix: Let Pydantic create the object directly from the dictionary.
        user_registration = UserRegistration(**worker_data)
        
        # Call the auth service with the correctly populated object
        result = await auth_service.register_user(user_registration)
        
        if result["success"]:
            # The result from the service contains a nested 'user' object
            return UserResponse(**result["user"])
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Registration failed."))

    except Exception as e:
        # This will log the actual error to your Render logs for easier debugging
        print(f"CRASH in /workers/register: {e}") 
        raise HTTPException(status_code=500, detail=f"Worker registration failed: {str(e)}")


@app.post("/workers/login")
async def worker_login(login_data: UserLogin):
    """Worker login endpoint"""
    try:
        result = await auth_service.authenticate_user(login_data.email, login_data.password)
        
        if result["success"] and result["user"]["role"] == UserRole.WORKER.value:
            return result
        elif result["success"]:
            raise HTTPException(status_code=403, detail="Access denied. Worker account required.")
        else:
            raise HTTPException(status_code=401, detail=result["message"])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker login failed: {str(e)}")


@app.get("/workers", response_model=List[WorkerProfile])
async def get_workers(department_id: str = None):
    """Get all workers, optionally filtered by department"""
    if department_id:
        return await get_workers_by_department(department_id)
    else:
        return await get_all_workers()


@app.get("/workers/profile/{email}", response_model=WorkerProfile)
async def get_worker_profile_endpoint(email: str):
    """Get worker profile by email"""
    worker = await auth_service.get_user_profile(email)
    if worker["success"]:
        return WorkerProfile(**worker["user"])
    else:
        raise HTTPException(status_code=404, detail="Worker not found")


# --- Department Route ---

@app.get("/departments", response_model=List[Department])
async def get_departments_endpoint():
    """Get all active departments"""
    return await get_all_departments()


# --- Assignment Routes ---

@app.get("/assignments", response_model=List[IssueAssignment])
async def get_all_assignments_endpoint():
    """Get all assignments"""
    return await get_all_assignments()


@app.post("/assignments", response_model=AssignmentResponse)
async def create_assignment_endpoint(assignment_request: AssignmentRequest):
    """Create a new assignment"""
    # This logic assumes 'assigned_by' comes from an auth system later.
    # For now, we'll hardcode it or take it as a query param.
    assigned_by_email = "admin@example.com"

    # Verify issue and worker exist
    issue = await get_assignment_by_ticket(assignment_request.ticket_id) # Simplified
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    worker = await get_worker_by_email(assignment_request.assigned_to)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    assignment_data = assignment_request.model_dump()
    assignment_data["assigned_by"] = assigned_by_email
    assignment_data["assigned_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
    assignment_data["status"] = "assigned"

    new_assignment = await create_issue_assignment(assignment_data)
    
    # Update issue status
    await update_issue_status_in_db(assignment_request.ticket_id, "in_progress", assigned_by_email)
    
    return new_assignment

@app.get("/assignments/worker/{worker_email}", response_model=List[IssueAssignment])
async def get_worker_assignments_endpoint(worker_email: str):
    """Get all assignments for a specific worker"""
    return await get_assignments_by_worker(worker_email)