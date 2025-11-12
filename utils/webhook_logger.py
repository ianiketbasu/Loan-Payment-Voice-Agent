"""
Webhook Logger Utility
Logs all webhook data to a file for debugging and analysis
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class WebhookLogger:
    """Logger for webhook events"""
    
    LOG_DIR = Path(__file__).parent.parent / "logs"
    LOG_FILE = LOG_DIR / "webhook_logs.jsonl"  # JSON Lines format
    
    @classmethod
    def _ensure_log_dir(cls):
        """Create logs directory if it doesn't exist"""
        cls.LOG_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def log_webhook(cls, webhook_data: Dict[str, Any], additional_info: Dict[str, Any] = None):
        """
        Log webhook data to file
        
        Args:
            webhook_data: The raw webhook payload from ElevenLabs
            additional_info: Any additional information to include in the log
        """
        cls._ensure_log_dir()
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "webhook_type": webhook_data.get("type"),
            "raw_webhook": webhook_data,
        }
        
        # Add additional parsed information if provided
        if additional_info:
            log_entry["parsed_info"] = additional_info
        
        # Extract and structure key information for easier reading
        if webhook_data.get("type") == "post_call_transcription":
            conversation_data = webhook_data.get("data", {})
            analysis = conversation_data.get("analysis", {})
            metadata = conversation_data.get("metadata", {})
            data_collection = analysis.get("data_collection", {})
            dynamic_vars = metadata.get("dynamic_variables", {})
            
            log_entry["summary"] = {
                "conversation_id": conversation_data.get("conversation_id"),
                "status": conversation_data.get("status"),
                "customer_id": dynamic_vars.get("customer_id"),
                "customer_name": f"{dynamic_vars.get('first_name', '')} {dynamic_vars.get('last_name', '')}".strip(),
                "phone_number": dynamic_vars.get("phone_number"),
                "loan_amount": dynamic_vars.get("loan_amount"),
                "due_date": dynamic_vars.get("due_date"),
                "customer_response": data_collection.get("customer_response"),
                "payment_intent": data_collection.get("payment_intent"),
                "callback_requested": data_collection.get("callback_requested"),
                "call_duration_secs": metadata.get("call_duration_secs"),
                "cost": metadata.get("cost"),
            }
            
            # Include full transcript if available
            transcript = conversation_data.get("transcript", [])
            if transcript:
                log_entry["transcript"] = transcript
        
        # Write to log file (JSON Lines format - one JSON object per line)
        try:
            with open(cls.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Error writing to webhook log: {str(e)}")
    
    @classmethod
    def get_log_file_path(cls) -> str:
        """Get the path to the log file"""
        return str(cls.LOG_FILE)

