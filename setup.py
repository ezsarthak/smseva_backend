#!/usr/bin/env python3
"""
Setup script for Municipal Voice Assistant API
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("📝 Creating .env file...")
    
    env_content = """# Municipal Voice Assistant API Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=municipal_issues
GEMINI_API_KEY=your_gemini_api_key_here

# Instructions:
# 1. Replace 'your_gemini_api_key_here' with your actual Gemini API key
# 2. Update MONGODB_URL if using a different MongoDB instance
# 3. You can get a Gemini API key from: https://makersuite.google.com/app/apikey
"""
    
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")
    print("⚠️  Please update the GEMINI_API_KEY in the .env file")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "pydantic",
        "motor",
        "google.generativeai",
        "dotenv",
        "pymongo"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies are installed!")
    return True

def check_mongodb():
    """Check if MongoDB is accessible"""
    print("🔍 Checking MongoDB connection...")
    
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        
        load_dotenv()
        
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("\nTo fix this:")
        print("1. Install MongoDB locally, or")
        print("2. Use MongoDB Atlas (cloud service), or")
        print("3. Run with Docker: docker run -d -p 27017:27017 --name mongodb mongo:latest")
        return False

def main():
    """Main setup function"""
    print("🚀 Municipal Voice Assistant API Setup")
    print("=" * 50)
    
    # Create .env file
    create_env_file()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check MongoDB
    mongo_ok = check_mongodb()
    
    print("\n" + "=" * 50)
    
    if deps_ok:
        print("✅ Setup complete! You can now run the API:")
        print("   python run.py")
        print("\n📚 Next steps:")
        print("1. Update GEMINI_API_KEY in .env file")
        print("2. Run: python run.py")
        print("3. Test with: python test_api.py")
        print("4. View docs at: http://localhost:8000/docs")
        if not mongo_ok:
            print("\n⚠️  Note: MongoDB is not available, using in-memory storage for development")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()