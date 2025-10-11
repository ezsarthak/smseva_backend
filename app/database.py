import motor.motor_asyncio
import hashlib
import re
from typing import Optional, List
from models import IssueDB, Department, WorkerProfile, IssueAssignment, UserRole
import os
from dotenv import load_dotenv
from difflib import SequenceMatcher
from datetime import datetime

load_dotenv()

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

# Configuration for duplicate detection
LOCATION_THRESHOLD_KM = 0.5  # 500 meters
CONTENT_SIMILARITY_THRESHOLD = 0.7  # 70% similarity
CATEGORY_MATCH_REQUIRED = True

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula (in km)"""
    from math import radians, cos, sin, asin, sqrt
    
    # Validate coordinates
    if not (-90 <= lat1 <= 90) or not (-90 <= lat2 <= 90):
        print(f"Warning: Invalid latitude values: {lat1}, {lat2}")
        # For invalid coordinates, treat as very close (assume same location)
        return 0.0
    
    if not (-180 <= lon1 <= 180) or not (-180 <= lon2 <= 180):
        print(f"Warning: Invalid longitude values: {lon1}, {lon2}")
        # For invalid coordinates, treat as very close (assume same location)
        return 0.0
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts"""
    # Clean and normalize texts
    text1_clean = re.sub(r'[^\w\s]', '', text1.lower().strip())
    text2_clean = re.sub(r'[^\w\s]', '', text2.lower().strip())
    
    # Use SequenceMatcher for similarity
    return SequenceMatcher(None, text1_clean, text2_clean).ratio()

def extract_keywords(text: str) -> List[str]:
    """Extract key words from text for better matching"""
    # Remove common words and extract meaningful keywords
    common_words = {'मेरा', 'नाम', 'है', 'में', 'की', 'का', 'के', 'और', 'या', 'पर', 'से', 'तक', 'दूर', 'पास'}
    words = re.findall(r'\w+', text.lower())
    keywords = [word for word in words if word not in common_words and len(word) > 2]
    return keywords

async def create_content_hash(text: str, location: Optional[dict] = None) -> str:
    """Create a hash of the content for duplicate detection"""
    content = text.lower().strip()
    if location:
        content += f"_{location.get('longitude', 0)}_{location.get('latitude', 0)}"
    
    return hashlib.md5(content.encode()).hexdigest()

async def is_similar_issue(new_text: str, new_location: Optional[dict], new_category: str, 
                          existing_issue: dict, user_email: str = None) -> bool:
    """Check if new issue is similar to existing issue"""
    
    # 0. Check if same user already reported this issue
    if user_email and existing_issue.get('users'):
        if user_email in existing_issue['users']:
            return False  # Same user, don't count as duplicate
    
    # 1. Category must match (if required)
    if CATEGORY_MATCH_REQUIRED and new_category != existing_issue.get('category'):
        return False
    
    # 2. Location similarity check
    if new_location and existing_issue.get('location'):
        new_lat = new_location.get('latitude')
        new_lon = new_location.get('longitude')
        existing_lat = existing_issue['location'].get('latitude')
        existing_lon = existing_issue['location'].get('longitude')
        
        if new_lat and new_lon and existing_lat and existing_lon:
            distance = calculate_distance(new_lat, new_lon, existing_lat, existing_lon)
            if distance > LOCATION_THRESHOLD_KM:
                return False
    
    # 3. Text similarity check
    existing_text = existing_issue.get('original_text', existing_issue.get('title', '') + ' ' + existing_issue.get('description', ''))
    text_similarity = calculate_text_similarity(new_text, existing_text)
    
    if text_similarity >= CONTENT_SIMILARITY_THRESHOLD:
        return True
    
    # 4. Keyword-based similarity check
    new_keywords = extract_keywords(new_text)
    existing_keywords = extract_keywords(existing_text)  # existing_text already contains original_text
    
    if new_keywords and existing_keywords:
        common_keywords = set(new_keywords) & set(existing_keywords)
        keyword_similarity = len(common_keywords) / max(len(new_keywords), len(existing_keywords))
        
        if keyword_similarity >= 0.5:  # 50% keyword overlap
            return True
    
    return False


# In-memory storage for development when MongoDB is not available
_in_memory_issues = []
_in_memory_departments = []
_in_memory_workers = []
_in_memory_assignments = []
_in_memory_users = []

async def find_existing_issue(content_hash: str, text: str = None, location: dict = None, category: str = None, user_email: str = None) -> Optional[IssueDB]:
    """Find existing issue by content hash or similarity"""
    
    # First, try exact hash match
    if issues_collection is not None:
        try:
            issue_data = await issues_collection.find_one({"content_hash": content_hash})
            if issue_data:
                # Convert ObjectId to string
                if "_id" in issue_data:
                    issue_data["_id"] = str(issue_data["_id"])
                return IssueDB(**issue_data)
        except Exception as e:
            print(f"Error querying MongoDB: {e}")
    
    # Use in-memory storage for exact match
    for issue in _in_memory_issues:
        if issue.get("content_hash") == content_hash:
            return IssueDB(**issue)
    
    # If no exact match and we have text/location/category, try similarity matching
    if text and category:
        if issues_collection is not None:
            try:
                # Get all issues of the same category
                cursor = issues_collection.find({"category": category})
                async for issue_data in cursor:
                    if "_id" in issue_data:
                        issue_data["_id"] = str(issue_data["_id"])
                    
                    if await is_similar_issue(text, location, category, issue_data, user_email):
                        return IssueDB(**issue_data)
            except Exception as e:
                print(f"Error similarity matching in MongoDB: {e}")
        
        # Check in-memory storage for similarity
        for issue in _in_memory_issues:
            if issue.get("category") == category:
                if await is_similar_issue(text, location, category, issue, user_email):
                    return IssueDB(**issue)
    
    return None

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

async def update_issue_status_in_db(ticket_id: str, new_status: str, updated_by_email: str) -> Optional[dict]:
    """Update issue status by ticket ID"""
    print(f"Database: Updating status for ticket {ticket_id} to {new_status} by {updated_by_email}")
    
    if issues_collection is not None:
        try:
            from bson import ObjectId
            print("Database: Using MongoDB")
            
            # Find the issue first to get current status
            issue_data = await issues_collection.find_one({"ticket_id": ticket_id})
            if not issue_data:
                print(f"Database: No issue found with ticket_id {ticket_id}")
                return None
            
            previous_status = issue_data.get("status", "unknown")
            print(f"Database: Previous status was {previous_status}")
            
            # Prepare update data with timestamp tracking and email
            update_data = {
                "status": new_status,
                "updated_at": datetime.now().strftime("%H:%M %d-%m-%Y"),
                "updated_by_email": updated_by_email
            }
            
            # Track when status is changed to in_progress
            if new_status == "in_progress" and previous_status != "in_progress":
                update_data["in_progress_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            
            # Track when status is changed to completed
            if new_status == "completed" and previous_status != "completed":
                update_data["completed_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            
            # Update the status
            result = await issues_collection.find_one_and_update(
                {"ticket_id": ticket_id},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                # Convert ObjectId to string
                if "_id" in result:
                    result["_id"] = str(result["_id"])
                result["previous_status"] = previous_status
                print(f"Database: Successfully updated in MongoDB")
                return result
                
        except Exception as e:
            print(f"Database: Error updating issue status in MongoDB: {e}")
    
    # Use in-memory storage
    print("Database: Using in-memory storage")
    for issue in _in_memory_issues:
        if issue.get("ticket_id") == ticket_id:
            previous_status = issue.get("status", "unknown")
            issue["status"] = new_status
            issue["updated_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            issue["updated_by_email"] = updated_by_email
            
            # Track when status is changed to in_progress
            if new_status == "in_progress" and previous_status != "in_progress":
                issue["in_progress_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            
            # Track when status is changed to completed
            if new_status == "completed" and previous_status != "completed":
                issue["completed_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            
            print(f"Database: Successfully updated in memory")
            return {
                **issue,
                "previous_status": previous_status
            }
    
    print(f"Database: No issue found in memory with ticket_id {ticket_id}")
    return None

async def get_issues_by_user_email(user_email: str) -> list[IssueDB]:
    """Get all issues created by a specific user email"""
    if issues_collection is not None:
        try:
            # Find issues where the user's email is in the users array
            cursor = issues_collection.find({"users": user_email})
            issues = []
            async for issue in cursor:
                # Convert ObjectId to string
                if "_id" in issue:
                    issue["_id"] = str(issue["_id"])
                issues.append(IssueDB(**issue))
            return issues
        except Exception as e:
            print(f"Error querying MongoDB for user issues: {e}")
    
    # Use in-memory storage
    user_issues = []
    for issue in _in_memory_issues:
        if "users" in issue and user_email in issue["users"]:
            user_issues.append(IssueDB(**issue))
    return user_issues

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

# Department management functions
async def create_department(department_data: dict) -> Department:
    """Create a new department"""
    if departments_collection is not None:
        try:
            result = await departments_collection.insert_one(department_data)
            department_data["_id"] = str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting department to MongoDB: {e}")
            import uuid
            department_data["_id"] = str(uuid.uuid4())
            _in_memory_departments.append(department_data)
    else:
        import uuid
        department_data["_id"] = str(uuid.uuid4())
        _in_memory_departments.append(department_data)
    return Department(**department_data)

async def get_all_departments() -> List[Department]:
    """Get all active departments"""
    if departments_collection is not None:
        try:
            cursor = departments_collection.find({"is_active": True})
            departments = []
            async for dept in cursor:
                if "_id" in dept:
                    dept["_id"] = str(dept["_id"])
                departments.append(Department(**dept))
            return departments
        except Exception as e:
            print(f"Error querying departments from MongoDB: {e}")
    
    return [Department(**dept) for dept in _in_memory_departments if dept.get("is_active", True)]

async def get_department_by_id(department_id: str) -> Optional[Department]:
    """Get department by ID"""
    if departments_collection is not None:
        try:
            from bson import ObjectId
            dept_data = await departments_collection.find_one({"_id": ObjectId(department_id)})
            if dept_data:
                if "_id" in dept_data:
                    dept_data["_id"] = str(dept_data["_id"])
                return Department(**dept_data)
        except Exception as e:
            print(f"Error querying department from MongoDB: {e}")
    
    for dept in _in_memory_departments:
        if dept.get("_id") == department_id:
            return Department(**dept)
    return None

# Worker management functions
async def create_worker_profile(worker_data: dict) -> WorkerProfile:
    """Create a new worker profile"""
    if workers_collection is not None:
        try:
            result = await workers_collection.insert_one(worker_data)
            worker_data["_id"] = str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting worker to MongoDB: {e}")
            import uuid
            worker_data["_id"] = str(uuid.uuid4())
            _in_memory_workers.append(worker_data)
    else:
        import uuid
        worker_data["_id"] = str(uuid.uuid4())
        _in_memory_workers.append(worker_data)
    return WorkerProfile(**worker_data)

async def get_all_workers() -> List[WorkerProfile]:
    """Get all active workers"""
    if workers_collection is not None:
        try:
            cursor = workers_collection.find({"is_active": True})
            workers = []
            async for worker in cursor:
                if "_id" in worker:
                    worker["_id"] = str(worker["_id"])
                workers.append(WorkerProfile(**worker))
            return workers
        except Exception as e:
            print(f"Error querying workers from MongoDB: {e}")
    
    return [WorkerProfile(**worker) for worker in _in_memory_workers if worker.get("is_active", True)]

async def get_workers_by_department(department_id: str) -> List[WorkerProfile]:
    """Get workers by department"""
    if workers_collection is not None:
        try:
            cursor = workers_collection.find({"department_id": department_id, "is_active": True})
            workers = []
            async for worker in cursor:
                if "_id" in worker:
                    worker["_id"] = str(worker["_id"])
                workers.append(WorkerProfile(**worker))
            return workers
        except Exception as e:
            print(f"Error querying workers by department from MongoDB: {e}")
    
    return [WorkerProfile(**worker) for worker in _in_memory_workers 
            if worker.get("department_id") == department_id and worker.get("is_active", True)]

async def get_worker_by_email(email: str) -> Optional[WorkerProfile]:
    """Get worker by email"""
    if workers_collection is not None:
        try:
            worker_data = await workers_collection.find_one({"email": email})
            if worker_data:
                if "_id" in worker_data:
                    worker_data["_id"] = str(worker_data["_id"])
                return WorkerProfile(**worker_data)
        except Exception as e:
            print(f"Error querying worker from MongoDB: {e}")
    
    for worker in _in_memory_workers:
        if worker.get("email") == email:
            return WorkerProfile(**worker)
    return None

async def update_worker_profile(email: str, update_data: dict) -> Optional[WorkerProfile]:
    """Update worker profile"""
    if workers_collection is not None:
        try:
            update_data["updated_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            result = await workers_collection.find_one_and_update(
                {"email": email},
                {"$set": update_data},
                return_document=True
            )
            if result:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
                return WorkerProfile(**result)
        except Exception as e:
            print(f"Error updating worker in MongoDB: {e}")
    
    for worker in _in_memory_workers:
        if worker.get("email") == email:
            worker.update(update_data)
            worker["updated_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            return WorkerProfile(**worker)
    return None

# Issue assignment functions
async def create_issue_assignment(assignment_data: dict) -> IssueAssignment:
    """Create a new issue assignment"""
    if assignments_collection is not None:
        try:
            result = await assignments_collection.insert_one(assignment_data)
            assignment_data["_id"] = str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting assignment to MongoDB: {e}")
            import uuid
            assignment_data["_id"] = str(uuid.uuid4())
            _in_memory_assignments.append(assignment_data)
    else:
        import uuid
        assignment_data["_id"] = str(uuid.uuid4())
        _in_memory_assignments.append(assignment_data)
    return IssueAssignment(**assignment_data)

async def get_assignments_by_worker(worker_email: str) -> List[IssueAssignment]:
    """Get all assignments for a worker"""
    if assignments_collection is not None:
        try:
            cursor = assignments_collection.find({"assigned_to": worker_email})
            assignments = []
            async for assignment in cursor:
                if "_id" in assignment:
                    assignment["_id"] = str(assignment["_id"])
                assignments.append(IssueAssignment(**assignment))
            return assignments
        except Exception as e:
            print(f"Error querying assignments from MongoDB: {e}")
    
    return [IssueAssignment(**assignment) for assignment in _in_memory_assignments 
            if assignment.get("assigned_to") == worker_email]

async def get_assignment_by_ticket(ticket_id: str) -> Optional[IssueAssignment]:
    """Get assignment by ticket ID"""
    if assignments_collection is not None:
        try:
            assignment_data = await assignments_collection.find_one({"ticket_id": ticket_id})
            if assignment_data:
                if "_id" in assignment_data:
                    assignment_data["_id"] = str(assignment_data["_id"])
                return IssueAssignment(**assignment_data)
        except Exception as e:
            print(f"Error querying assignment from MongoDB: {e}")
    
    for assignment in _in_memory_assignments:
        if assignment.get("ticket_id") == ticket_id:
            return IssueAssignment(**assignment)
    return None

async def update_assignment_status(ticket_id: str, status: str, notes: Optional[str] = None) -> Optional[IssueAssignment]:
    """Update assignment status"""
    if assignments_collection is not None:
        try:
            update_data = {"status": status}
            if notes:
                update_data["notes"] = notes
            if status == "completed":
                update_data["completed_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            
            result = await assignments_collection.find_one_and_update(
                {"ticket_id": ticket_id},
                {"$set": update_data},
                return_document=True
            )
            if result:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
                return IssueAssignment(**result)
        except Exception as e:
            print(f"Error updating assignment in MongoDB: {e}")
    
    for assignment in _in_memory_assignments:
        if assignment.get("ticket_id") == ticket_id:
            assignment["status"] = status
            if notes:
                assignment["notes"] = notes
            if status == "completed":
                assignment["completed_at"] = datetime.now().strftime("%H:%M %d-%m-%Y")
            return IssueAssignment(**assignment)
    return None

# User management functions
async def create_user(user_data: dict) -> dict:
    """Create a new user"""
    if users_collection is not None:
        try:
            result = await users_collection.insert_one(user_data)
            user_data["_id"] = str(result.inserted_id)
        except Exception as e:
            print(f"Error inserting user to MongoDB: {e}")
            import uuid
            user_data["_id"] = str(uuid.uuid4())
            _in_memory_users.append(user_data)
    else:
        import uuid
        user_data["_id"] = str(uuid.uuid4())
        _in_memory_users.append(user_data)
    return user_data

async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    if users_collection is not None:
        try:
            user_data = await users_collection.find_one({"email": email})
            if user_data:
                if "_id" in user_data:
                    user_data["_id"] = str(user_data["_id"])
                return user_data
        except Exception as e:
            print(f"Error querying user from MongoDB: {e}")
    
    for user in _in_memory_users:
        if user.get("email") == email:
            return user
    return None

async def update_user_status(email: str, is_active: bool) -> Optional[dict]:
    """Update user active status"""
    if users_collection is not None:
        try:
            result = await users_collection.find_one_and_update(
                {"email": email},
                {"$set": {"is_active": is_active}},
                return_document=True
            )
            if result:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
                return result
        except Exception as e:
            print(f"Error updating user in MongoDB: {e}")
    
    for user in _in_memory_users:
        if user.get("email") == email:
            user["is_active"] = is_active
            return user
    return None