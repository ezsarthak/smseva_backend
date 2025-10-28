import uvicorn
import os
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5600))  # Default to 5600 if PORT not set
    uvicorn.run(
        "app.main:app",
        port=port,
        reload=True,
        log_level="info"
    )
