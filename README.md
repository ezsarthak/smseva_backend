# Municipal Voice Assistant API

A FastAPI-based backend system for processing municipal issues from voice input. This system converts speech-to-text output into structured issue tickets using AI analysis.

## Features

- **Voice Input Processing**: Accepts text input from speech-to-text conversion
- **AI-Powered Analysis**: Uses Google Gemini API for intelligent text analysis
- **Duplicate Detection**: Prevents duplicate issues and tracks issue frequency
- **MongoDB Integration**: Scalable database storage for issues
- **RESTful API**: Clean, documented API endpoints
- **Multi-language Support**: Handles Hindi and English input
- **Email Notifications**: Automatic email notifications via SMTP (Gmail) for ticket confirmations and status updates

## Project Structure

```
├── app/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application and routes
│   ├── models.py                # Pydantic models for request/response
│   ├── database.py              # MongoDB operations and duplicate detection
│   ├── gemini_service.py        # Google Gemini AI integration
│   └── email_service.py         # SMTP integration for email notifications
├── requirements.txt              # Python dependencies
├── run.py                       # Application entry point (runs on port 5600)
├── env_example.txt              # Environment variables template
├── SMTP_SETUP.md                # SMTP setup and configuration guide
├── test_email_notifications.py  # Test script for email functionality
└── README.md                    # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory with the following variables:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=municipal_issues
GEMINI_API_KEY=your_gemini_api_key_here

# SMTP Configuration (for email notifications)
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
```

### 3. MongoDB Setup

Make sure MongoDB is running on your system. You can use:
- Local MongoDB installation
- MongoDB Atlas (cloud service)
- Docker: `docker run -d -p 27017:27017 --name mongodb mongo:latest`

### 4. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

### 5. Setup SMTP Email (Optional - for email notifications)

1. Enable 2-Factor Authentication on your Gmail account
2. Generate a Gmail App Password (not your regular password)
3. Add your Gmail credentials to your `.env` file
4. See `SMTP_SETUP.md` for detailed setup instructions

### 6. Run the Application

```bash
python run.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Submit Issue
**POST** `/submit-issue`

Submit a new municipal issue or update existing one if duplicate.

**Request Body:**
```json
{
  "text": "मेरा नाम अजय है, गली में गड्ढा है, सेक्टर 5 में",
  "email": "ajay@example.com",
  "name": "Ajay",
  "location": {
    "longitude": 77.2090,
    "latitude": 28.6139
  },
  "photo": "base64_encoded_photo_string"
}
```

**Response:**
```json
{
  "ticket_id": "TKT-20241201-ABC12345",
  "category": "Roads & Transport",
  "address": "Sector 5, Main Street",
  "location": {
    "longitude": 77.2090,
    "latitude": 28.6139
  },
  "description": "A significant pothole has developed on the main road in Sector 5, posing safety risks to vehicles and pedestrians. The hole is approximately 2 feet in diameter and 6 inches deep, located near the market area. This road hazard affects daily traffic flow and requires immediate attention from the road maintenance department to prevent accidents and vehicle damage.",
  "title": "Large Pothole on Main Road",
  "urgency_level": "high",
  "photo": "base64_encoded_photo_string",
  "status": "new",
  "created_at": "011224 14:30:25",
  "users": ["ajay@example.com"],
  "issue_count": 1
}
```

### 2. Get All Issues
**GET** `/issues`

Retrieve all issues from the database with optional filtering and pagination.

**Query Parameters:**
- `category` (optional): Filter by issue category
- `status` (optional): Filter by issue status
- `limit` (optional): Maximum number of issues to return (default: 100, max: 1000)
- `skip` (optional): Number of issues to skip for pagination (default: 0)

**Examples:**
```bash
# Get all issues
GET /issues

# Get only Roads & Transport issues
GET /issues?category=Roads%20%26%20Transport

# Get first 10 issues
GET /issues?limit=10

# Get issues with pagination
GET /issues?limit=20&skip=40

# Get issues by category and status
GET /issues?category=Water%20%26%20Drainage&status=new
```

### 3. Get Issue Categories
**GET** `/issues/categories`

Get all available issue categories.

**Response:**
```json
{
  "categories": [
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
}
```

### 4. Get Issues Count
**GET** `/issues/count`

Get count of issues with optional filtering.

**Query Parameters:**
- `category` (optional): Filter by issue category
- `status` (optional): Filter by issue status

**Examples:**
```bash
# Get total count of all issues
GET /issues/count

# Get count of Roads & Transport issues
GET /issues/count?category=Roads%20%26%20Transport

# Get count of new issues
GET /issues/count?status=new

# Get count of Water & Drainage issues with new status
GET /issues/count?category=Water%20%26%20Drainage&status=new
```

**Response:**
```json
{
  "total_count": 25,
  "category": "Roads & Transport",
  "status": null
}
```

### 5. Update Issue Status
**PUT** `/issues/{ticket_id}/status`

Update the status of an existing issue by ticket ID.

**Path Parameters:**
- `ticket_id`: The ticket ID of the issue to update

**Request Body:**
```json
{
  "status": "in_progress"
}
```

**Valid Status Values:**
- `new` - Issue is newly reported
- `in_progress` or `in progress` - Issue is being worked on
- `completed` - Issue has been completed

**Response:**
```json
{
  "message": "Issue status updated successfully",
  "ticket_id": "TKT-20241201-ABC12345",
  "old_status": "new",
  "new_status": "in_progress",
  "updated_at": "14:30 01-12-2024",
  "in_progress_at": "14:30 01-12-2024"
}
```

**Timestamp Tracking:**
The system automatically tracks when issues are marked for specific statuses:
- `in_progress_at`: Timestamp when the issue was first marked as "in_progress"
- `completed_at`: Timestamp when the issue was first marked as "completed"

These timestamps are only set once when the status first changes to these values and are preserved even if the status changes again.

**Example:**
```bash
curl -X PUT "http://localhost:8000/issues/TKT-20241201-ABC12345/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

### 6. Health Check
**GET** `/health`

Check API health status.

### 7. API Documentation
**GET** `/docs`

Interactive API documentation (Swagger UI).

## How It Works

1. **AI-Powered Analysis**: Uses Google Gemini AI to intelligently analyze issue reports and extract accurate information
2. **Smart Categorization**: Automatically categorizes issues into appropriate municipal departments with high accuracy
3. **Precise Address Extraction**: Identifies exact location details, sector numbers, and nearby landmarks
4. **Context-Aware Descriptions**: Generates detailed, professional descriptions that explain the exact issue, location, impact, and required actions
5. **Intelligent Title Generation**: Creates specific, descriptive titles that clearly identify each issue
6. **Urgency Assessment**: Automatically determines issue priority based on content analysis
7. **Fallback System**: Includes rule-based fallback when AI is unavailable
8. **Duplicate Detection**: Prevents duplicate submissions using content hashing and similarity analysis
9. **Database Storage**: Stores issues in MongoDB with proper indexing and validation

## Email Notifications

The system automatically sends email notifications to users via SMTP (Gmail):

### **Features**
- **Ticket Confirmations**: Users receive immediate confirmation when they submit issues
- **Status Updates**: Notifications when issue status changes (new → in_progress → completed)
- **Professional Templates**: Beautiful, responsive email templates
- **Multi-user Support**: Notifies all users associated with an issue
- **Fallback Handling**: System continues to work even if emails fail

### **Setup**
1. Follow the SMTP setup guide in `SMTP_SETUP.md`
2. Enable 2-Factor Authentication on your Gmail account
3. Generate a Gmail App Password
4. Add your Gmail credentials to the `.env` file

### **Testing**
Run the email test script to verify your setup:
```bash
python test_email_notifications.py
```

## Gemini AI Integration

The system now uses Google's Gemini AI for intelligent issue analysis:

### **Features**
- **Accurate Categorization**: AI understands context and categorizes issues correctly
- **Smart Address Extraction**: Identifies exact locations, sectors, and landmarks
- **Context-Aware Descriptions**: Generates professional descriptions explaining the exact issue
- **Intelligent Titles**: Creates specific, descriptive titles for each issue
- **Urgency Assessment**: Automatically determines priority based on content analysis

### **Setup**
1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to your `.env` file: `GEMINI_API_KEY=your_key_here`
3. The system will automatically use AI when available

### **Fallback System**
- If Gemini AI is unavailable, the system falls back to rule-based analysis
- Ensures reliability even when AI services are down
- Maintains all existing functionality

## Duplicate Detection Logic

The system uses content hashing to detect duplicate issues:
- Combines text content and location coordinates
- Creates MD5 hash for comparison
- If duplicate found, updates existing issue instead of creating new one
- Tracks how many times the same issue has been reported

## Response Fields

All issue responses now include additional timestamp tracking fields:

### **Standard Fields**
- `ticket_id`: Unique identifier for the issue
- `category`: Issue category (e.g., "Roads & Transport", "Water & Drainage")
- `address`: Extracted address from the issue description
- `location`: GPS coordinates (longitude, latitude)
- `description`: Detailed description of the issue
- `title`: Generated title for the issue
- `photo`: Base64 encoded photo (if provided)
- `status`: Current status of the issue
- `created_at`: When the issue was first reported
- `users`: List of email addresses who reported this issue
- `issue_count`: Number of times this issue has been reported
- `original_text`: Original user input text

### **Timestamp Tracking Fields**
- `in_progress_at`: Timestamp when the issue was first marked as "in_progress" (null if never)
- `completed_at`: Timestamp when the issue was first marked as "completed" (null if never)

These timestamp fields are automatically managed by the system and provide valuable insights into issue lifecycle and response times.

## Error Handling

- Invalid input validation using Pydantic models
- Graceful handling of Gemini API failures
- MongoDB connection error handling
- Proper HTTP status codes and error messages

## Development

### Running in Development Mode

```bash
python run.py
```

The application runs with auto-reload enabled for development.

### Testing

You can test the API using:
- The interactive docs at `http://localhost:8000/docs`
- curl commands
- Postman or similar API testing tools

### Example Test Request

```bash
curl -X POST "http://localhost:8000/submit-issue" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "मेरा नाम अजय है, गली में गड्ढा है, सेक्टर 5 में",
    "email": "ajay@example.com",
    "name": "Ajay",
    "location": {
      "longitude": 77.2090,
      "latitude": 28.6139
    }
  }'
```

## Production Deployment

For production deployment:

1. Set proper CORS origins in `app/main.py`
2. Use environment variables for all configuration
3. Set up proper MongoDB authentication
4. Use a production WSGI server like Gunicorn
5. Set up proper logging and monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of a hackathon submission for municipal voice assistant development.