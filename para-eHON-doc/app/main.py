"""
Paraplanner FastAPI Application
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.apis import process_router

# Ensure output directory exists BEFORE app starts
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title="Paraplanner API",
    description="API for processing financial transcripts and generating PDF reports",
    version="1.0.0"
)

# Add CORS middleware FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files AFTER CORS middleware
app.mount("/static/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# Include routers
app.include_router(process_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Paraplanner API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)