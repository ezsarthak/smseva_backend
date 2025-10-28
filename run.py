import uvicorn
import os
from app.main import app

if __name__ == "__main__":
    port = int(8000)  # Default to 5600 if PORT not set
    uvicorn.run(
        "app.main:app",
        port=port,
        host="0.0.0.0",
        reload=True,
        log_level="info"
    )
