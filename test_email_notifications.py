#!/usr/bin/env python3
"""
Test script for SMTP email notifications
This script tests the email functionality without requiring the full API server
"""

import os
import asyncio
import sys
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Import after adding to path
from app.email_service import email_service
from app.models import IssueResponse, Location

# Load environment variables
load_dotenv()

async def test_email_service():
    """Test the email service functionality"""
    
    print("🧪 Testing SMTP Email Service")
    print("=" * 50)
    
    # Check configuration
    print("\n📋 Configuration Check:")
    print(f"SMTP Server: {'✅ Set' if email_service.smtp_server else '❌ Not Set'}")
    print(f"SMTP Port: {'✅ Set' if email_service.smtp_port else '❌ Not Set'}")
    print(f"SMTP Username: {'✅ Set' if email_service.smtp_username else '❌ Not Set'}")
    print(f"SMTP Password: {'✅ Set' if email_service.smtp_password else '❌ Not Set'}")
    print(f"From Email: {'✅ Set' if email_service.from_email else '❌ Not Set'}")
    print(f"From Name: {'✅ Set' if email_service.from_name else '❌ Not Set'}")
    print(f"Overall Status: {'✅ Configured' if email_service.is_configured else '❌ Not Configured'}")
    
    if not email_service.is_configured:
        print("\n⚠️  SMTP is not configured. Please set the required environment variables:")
        print("   SMTP_USERNAME")
        print("   SMTP_PASSWORD")
        print("\nSee SMTP_SETUP.md for detailed setup instructions.")
        return
    
    # Create a test issue
    test_issue = IssueResponse(
        ticket_id="TKT-20241201-TEST123",
        category="Roads & Transport",
        address="Sector 5, Main Street",
        location=Location(longitude=77.2090, latitude=28.6139),
        description="A significant pothole has developed on the main road in Sector 5, posing safety risks to vehicles and pedestrians.",
        title="Large Pothole on Main Road",
        photo=None,
        status="new",
        created_at="14:30 01-12-2024",
        users=["test@example.com"],
        issue_count=1,
        original_text="मेरा नाम अजय है, गली में गड्ढा है, सेक्टर 5 में",
        in_progress_at=None,
        completed_at=None,
        updated_by_email="test@example.com",
        updated_at="14:30 01-12-2024",
        admin_completed_at=None,
        user_completed_at=None,
        admin_completed_by=None,
        user_completed_by=None
    )
    
    # Test ticket confirmation email
    print("\n📧 Testing Ticket Confirmation Email:")
    test_email = "test@example.com"  # Change this to your email for testing
    test_name = "Test User"
    
    print(f"Sending test email to: {test_email}")
    print("Note: Change the test_email variable to your actual email address for testing")
    
    success = await email_service.send_ticket_confirmation(
        test_issue, 
        test_email, 
        test_name
    )
    
    if success:
        print("✅ Ticket confirmation email sent successfully!")
        print("Check your email (and spam folder) for the confirmation")
    else:
        print("❌ Failed to send ticket confirmation email")
    
    # Test status update notification
    print("\n🔄 Testing Status Update Notification:")
    success = await email_service.send_status_update_notification(
        "TKT-20241201-TEST123",
        "new",
        "in_progress",
        ["test@example.com", "another@example.com"]
    )
    
    if success:
        print("✅ Status update notifications sent successfully!")
    else:
        print("❌ Failed to send status update notifications")
    
    print("\n" + "=" * 50)
    print("🎯 Test completed!")

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Environment Variables Check:")
    print("=" * 30)
    
    required_vars = [
        "SMTP_USERNAME",
        "SMTP_PASSWORD"
    ]
    
    optional_vars = [
        "SMTP_SERVER",
        "SMTP_PORT",
        "FROM_EMAIL",
        "FROM_NAME"
    ]
    
    all_required_set = True
    for var in required_vars:
        value = os.getenv(var)
        status = "✅ Set" if value else "❌ Not Set"
        print(f"{var}: {status}")
        if not value:
            all_required_set = False
    
    print("\n📝 Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        status = "✅ Set" if value else "⚠️  Using Default"
        print(f"{var}: {status}")
    
    print(f"\nOverall Status: {'✅ All Required Variables Set' if all_required_set else '❌ Missing Required Variables'}")
    return all_required_set

if __name__ == "__main__":
    print("🚀 SMTP Email Integration Test Script")
    print("=" * 40)
    
    # Check environment first
    env_ok = check_environment()
    
    if env_ok:
        # Run the async test
        asyncio.run(test_email_service())
    else:
        print("\n⚠️  Please set all required environment variables before running tests.")
        print("   See SMTP_SETUP.md for setup instructions.")
