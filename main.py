"""
FastAPI Backend for Loan Reminder Voice Agent POC
Main application entry point with MVC architecture
"""
import uvicorn
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Import configuration
from config import STATIC_DIR, PORT, RELOAD, ELEVENLABS_API_KEY, AGENT_ID, PHONE_NUMBER_ID

# Import routes
from routes import main_routes, customer_routes, webhook_routes

# Import database to initialize
from database import customers_db

# Create FastAPI app
app = FastAPI(title="Loan Reminder Voice Agent API")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(main_routes.router)
app.include_router(customer_routes.router)
app.include_router(webhook_routes.router)


if __name__ == "__main__":
    # Get port from command line or environment, default to 8000
    port = int(os.getenv("PORT", str(PORT)))
    reload = "--reload" in sys.argv or RELOAD
    
    print("\n" + "="*60)
    print("Loan Reminder Voice Agent - FastAPI Backend")
    print("="*60)
    print(f"ElevenLabs Configured: {bool(ELEVENLABS_API_KEY and AGENT_ID and PHONE_NUMBER_ID)}")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Phone Number ID: {PHONE_NUMBER_ID}")
    print(f"Total Customers: {len(customers_db)}")
    print("="*60)
    print(f"\nStarting server on http://localhost:{port}")
    print(f"Frontend available at http://localhost:{port}")
    if reload:
        print("Reload mode: ENABLED (auto-reload on code changes)")
    print("="*60 + "\n")
    
    # Use import string format for reload to work properly
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
