"""
Paraplanner FastAPI Application
===============================
Two endpoints:
1. POST /process - Process transcript/audio and generate PDF
2. GET /download/{filename} - Download the generated PDF
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.apis import process_router

# Create FastAPI app
app = FastAPI(
    title="Paraplanner API",
    description="API for processing financial transcripts and generating PDF reports",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(process_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Paraplanner API is running"}


# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    # Create output directory
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)