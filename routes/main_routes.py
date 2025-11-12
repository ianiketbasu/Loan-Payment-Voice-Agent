"""
Main Routes
Root and health check endpoints
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from config import STATIC_DIR, ELEVENLABS_API_KEY, AGENT_ID, PHONE_NUMBER_ID
from database import get_all_customers

router = APIRouter(tags=["main"])


@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend HTML"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return """
    <html>
        <head><title>Loan Reminder Voice Agent</title></head>
        <body>
            <h1>Loan Reminder Voice Agent API</h1>
            <p>Status: OK</p>
            <p>Frontend files not found. Please ensure index.html exists in static/ directory.</p>
        </body>
    </html>
    """


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Loan Reminder Voice Agent API",
        "elevenlabs_configured": bool(ELEVENLABS_API_KEY and AGENT_ID and PHONE_NUMBER_ID),
        "total_customers": len(get_all_customers())
    }

