"""
Application Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

# Create static directory if it doesn't exist
STATIC_DIR.mkdir(exist_ok=True)

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AGENT_ID = os.getenv("AGENT_ID")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
BASE_URL = "https://api.elevenlabs.io/v1"

# Server Configuration
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "false").lower() == "true"

# Email Configuration (Mailtrap Email API)
MAILTRAP_API_TOKEN = os.getenv("MAILTRAP_API_TOKEN", "67b27b1351e541c002c4454d6f8f5d03")
MAILTRAP_INBOX_ID = os.getenv("MAILTRAP_INBOX_ID", "4175007")
MAILTRAP_API_URL = "https://sandbox.api.mailtrap.io/api/send"
MAIL_FROM_EMAIL = os.getenv("MAIL_FROM_EMAIL", "noreply@tech.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Tech Exactly")

