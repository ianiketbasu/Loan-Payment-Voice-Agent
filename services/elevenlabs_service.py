"""
ElevenLabs API Service
Handles all interactions with ElevenLabs API
"""
import httpx
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import HTTPException
from config import ELEVENLABS_API_KEY, BASE_URL, AGENT_ID, PHONE_NUMBER_ID


class ElevenLabsService:
    """Service for interacting with ElevenLabs API"""
    
    @staticmethod
    async def make_outbound_call(
        phone_number: str,
        dynamic_variables: Dict[str, str],
        first_message: Optional[str] = None,
        use_override: bool = True
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call via ElevenLabs API
        
        Args:
            phone_number: Target phone number (E.164 format: +1234567890)
            dynamic_variables: Variables to pass to the agent (use {{variable_name}} in agent prompts)
            first_message: Optional initial message to override agent's default first message
            
        Returns:
            Response from ElevenLabs API containing conversation_id and call_sid
            
        Important Notes:
            - For first_message_override to work, you MUST enable "First message" override in:
              ElevenLabs Dashboard → Your Agent → Settings → Security tab
            - Dynamic variables can be used in agent prompts with {{variable_name}} syntax
            - If override is not enabled, the agent will use its default first message
        """
        if not all([ELEVENLABS_API_KEY, AGENT_ID, PHONE_NUMBER_ID]):
            raise HTTPException(
                status_code=500,
                detail="ElevenLabs not configured. Please set environment variables."
            )
        
        url = f"{BASE_URL}/convai/twilio/outbound-call"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "agent_id": AGENT_ID,
            "agent_phone_number_id": PHONE_NUMBER_ID,
            "to_number": phone_number,
            "dynamic_variables": dynamic_variables,
        }
        
        # Add first_message_override if provided and enabled
        # NOTE: Overrides must be enabled in ElevenLabs Agent Settings → Security tab
        # Enable "First message" override for this to work
        # If override is not enabled, the API will silently ignore this field
        # TEMPORARILY DISABLED: Set to False to test if override is breaking the call
        # TODO: Re-enable once agent is working properly
        if first_message and use_override:
            # Use top-level first_message_override format for Twilio outbound call endpoint
            # This is the documented format per POC guide and API documentation
            payload["first_message_override"] = first_message
            print("First message override ENABLED in payload")
        elif first_message and not use_override:
            print("First message override DISABLED (testing mode - using agent default)")
            print("   This will use the agent's default first message from dashboard")
        
        # Debug logging
        print("\n" + "="*60)
        print("MAKING OUTBOUND CALL")
        print("="*60)
        print(f"URL: {url}")
        print(f"To Number: {phone_number}")
        print(f"Agent ID: {AGENT_ID}")
        print(f"Phone Number ID: {PHONE_NUMBER_ID}")
        print(f"Dynamic Variables: {json.dumps(dynamic_variables, indent=2)}")
        if first_message:
            print("\nFirst Message Override:")
            print(f"   {first_message}")
            print("\nCRITICAL: If you're hearing the default message, the override is NOT enabled!")
            print("   Action Required: ElevenLabs Dashboard → Your Agent → Settings → Security tab")
            print("   → Enable 'First message' override toggle")
        print("\nComplete Payload:")
        print(json.dumps(payload, indent=2))
        print("="*60 + "\n")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # Debug response
                print("\n" + "="*60)
                print("ELEVENLABS RESPONSE")
                print("="*60)
                print(f"Status Code: {response.status_code}")
                print(f"Response Body: {response.text}")
                
                # Parse response to check if override was accepted
                try:
                    response_data = response.json()
                    if "conversation_id" in response_data:
                        print("Call initiated successfully")
                        print(f"Conversation ID: {response_data.get('conversation_id')}")
                        if first_message:
                            print("\nTROUBLESHOOTING STEPS:")
                            print("   1. Verify override is enabled: Dashboard → Agent → Settings → Security")
                            print("   2. Check if agent's default first message uses {{variables}}")
                            print("   3. Ensure you're testing with a NEW call (not cached)")
                            print("   4. Check ElevenLabs Call History for any errors")
                            print(f"   5. Verify payload sent includes: {json.dumps({'first_message_override': first_message[:50] + '...' if len(first_message) > 50 else first_message}, indent=2)}")
                except Exception:
                    pass
                
                print("="*60 + "\n")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            print(f"\nHTTP Error: {error_detail}\n")
            
            # Check if error is related to overrides not being enabled
            if e.response and "override" in error_detail.lower():
                error_detail += (
                    "\n\nTROUBLESHOOTING: This error suggests overrides may not be enabled. "
                    "Please check: ElevenLabs Dashboard → Your Agent → Settings → Security tab → "
                    "Enable 'First message' override"
                )
            
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except Exception as e:
            print(f"\nException: {str(e)}\n")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def submit_batch_call(
        call_name: str,
        agent_id: str,
        agent_phone_number_id: str,
        recipients: List[Dict[str, Any]],
        scheduled_time_unix: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit a batch call via ElevenLabs Batch Calling API
        
        Args:
            call_name: Name of the batch call
            agent_id: Agent ID to use
            agent_phone_number_id: Phone number ID to use
            recipients: List of recipient dictionaries with phone_number and conversation data
            scheduled_time_unix: Optional Unix timestamp for scheduling (defaults to now)
            
        Returns:
            Response from ElevenLabs API containing batch_id
        """
        if not all([ELEVENLABS_API_KEY, AGENT_ID, PHONE_NUMBER_ID]):
            raise HTTPException(
                status_code=500,
                detail="ElevenLabs not configured. Please set environment variables."
            )
        
        url = f"{BASE_URL}/convai/batch-calling/submit"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        if scheduled_time_unix is None:
            scheduled_time_unix = int(datetime.now().timestamp())
        
        payload = {
            "call_name": call_name,
            "agent_id": agent_id,
            "agent_phone_number_id": agent_phone_number_id,
            "recipients": recipients,
            "scheduled_time_unix": scheduled_time_unix
        }
        
        # Debug logging - print full payload structure
        print("\n" + "="*60)
        print("SUBMITTING BATCH CALL")
        print("="*60)
        print(f"URL: {url}")
        print(f"Call Name: {call_name}")
        print(f"Agent ID: {agent_id}")
        print(f"Phone Number ID: {agent_phone_number_id}")
        print(f"Recipients Count: {len(recipients)}")
        print(f"Scheduled Time: {scheduled_time_unix}")
        print("\nFULL PAYLOAD STRUCTURE:")
        print(json.dumps(payload, indent=2, default=str))
        print("="*60 + "\n")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # Debug response
                print("\n" + "="*60)
                print("ELEVENLABS BATCH CALL RESPONSE")
                print("="*60)
                print(f"Status Code: {response.status_code}")
                print(f"Response Body: {response.text}")
                print("="*60 + "\n")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            print(f"\nHTTP Error: {error_detail}\n")
            
            # Check for Terms & Conditions error
            if e.response and e.response.status_code == 403:
                try:
                    error_data = e.response.json()
                    if "batch_calling_agreement_required" in str(error_data):
                        error_detail = (
                            "BATCH CALLING TERMS & CONDITIONS REQUIRED\n\n"
                            "You need to accept the Batch Calling Terms & Conditions in your ElevenLabs account.\n\n"
                            "Steps to fix:\n"
                            "1. Go to https://elevenlabs.io and log in\n"
                            "2. Navigate to Settings or Batch Calling section\n"
                            "3. Accept the Batch Calling Terms & Conditions\n"
                            "4. Try again after accepting\n\n"
                            f"Original error: {error_data.get('detail', {}).get('message', 'Unknown error')}"
                        )
                except Exception:
                    pass
            
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except Exception as e:
            print(f"\nException: {str(e)}\n")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_batch_call_status(batch_id: str) -> Dict[str, Any]:
        """
        Get the status of a batch call
        
        Args:
            batch_id: The batch call ID to check
            
        Returns:
            Batch call data from ElevenLabs API
        """
        if not ELEVENLABS_API_KEY:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")
        
        url = f"{BASE_URL}/convai/batch-calling/{batch_id}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_conversation_status(conversation_id: str) -> Dict[str, Any]:
        """
        Get the status of a conversation
        
        Args:
            conversation_id: The conversation ID to check
            
        Returns:
            Conversation data from ElevenLabs API
        """
        if not ELEVENLABS_API_KEY:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")
        
        url = f"{BASE_URL}/convai/conversations/{conversation_id}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Debug: Check what first message was actually used
                if "metadata" in data:
                    metadata = data.get("metadata", {})
                    config_override = metadata.get("conversation_config_override", {})
                    if config_override:
                        agent_config = config_override.get("agent", {})
                        actual_first_message = agent_config.get("first_message")
                        if actual_first_message:
                            print(f"\nVerified: Conversation used override first message: {actual_first_message}")
                        else:
                            print("\nWARNING: Conversation metadata shows no override was applied")
                
                return data
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))