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