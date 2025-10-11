from fastapi import FastAPI, HTTPException
from .auth_service import auth_service
from datetime import datetime
import uuid
from typing import List

from .models import (
    IssueRequest, IssueResponse, IssueDB, StatusUpdateRequest, UserEmailRequest, 
    CompletionRequest, CompletionResponse, UserRegistration, UserLogin, UserResponse,
    AssignmentRequest, AssignmentResponse, Department, WorkerProfile, IssueAssignment
)

from .database import (
    create_content_hash, 
    find_existing_issue, 
    create_new_issue, 
    update_existing_issue,
    get_all_issues,
    update_issue_status_in_db,
    get_issues_by_user_email,
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

from .email_service import email_service
from .gemini_service import analyze_text

app = FastAPI(
    title="Municipal Voice Assistant API",
    description="API for processing municipal issues from voice input",
    version="1.0.0"
)

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
            
            # Send email notification for duplicate issue
            await email_service.send_ticket_confirmation(
                updated_issue, 
                issue_request.email, 
                issue_request.name
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
        
        # Send email notification for new issue
        await email_service.send_ticket_confirmation(
            created_issue, 
            issue_request.email, 
            issue_request.name
        )
        
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
        
        # Send status update notifications to all users
        if updated_issue.get("users"):
            await email_service.send_status_update_notification(
                ticket_id,
                updated_issue.get("previous_status", "unknown"),
                normalized_status,
                updated_issue.get("users", [])
            )
        
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
        
        # Send completion notifications
        if updated_issue.get("users"):
            await email_service.send_status_update_notification(
                ticket_id,
                "in_progress",  # Previous status
                updated_issue.get("status", "unknown"),
                updated_issue.get("users", [])
            )
        
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