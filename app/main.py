from fastapi import FastAPI, HTTPException
from .auth_service import auth_service

from .models import (
    UserRegistration, UserLogin
)

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