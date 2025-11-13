"""
Customer Controller
Business logic for customer operations
"""
import uuid
from typing import Dict, Any, Optional, List
from fastapi import HTTPException
from models import Customer
from database import (
    find_customer_by_id,
    find_customer_by_conversation_id,
    update_customer_status,
    get_all_customers,
    add_customer as db_add_customer,
    delete_customer as db_delete_customer
)
from services.elevenlabs_service import ElevenLabsService
from utils.webhook_logger import WebhookLogger
from config import AGENT_ID, PHONE_NUMBER_ID


class CustomerController:
    """Controller for customer-related operations"""
    
    @staticmethod
    async def get_all_customers() -> Dict[str, Any]:
        """Get all customers"""
        return {"customers": get_all_customers()}
    
    @staticmethod
    async def create_customer(customer: Customer) -> Dict[str, Any]:
        """Add a new customer"""
        customer_dict = customer.dict()
        new_customer = db_add_customer(customer_dict)
        return {"success": True, "customer": new_customer}
    
    @staticmethod
    async def delete_customer(customer_id: int) -> Dict[str, Any]:
        """Delete a customer"""
        if not db_delete_customer(customer_id):
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"success": True}
    
    @staticmethod
    async def reset_customer_status(customer_id: int) -> Dict[str, Any]:
        """Reset customer status to pending"""
        customer = update_customer_status(customer_id, {
            "status": "pending",
            "response": None,
            "conversation_id": None
        })
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"success": True, "customer": customer}
    
    @staticmethod
    async def make_call(customer_id: int, first_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiate a call to a customer
        """
        # Find customer
        customer = find_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Check if already in progress
        if customer["status"] in ["calling", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail="Call already in progress for this customer"
            )
        
        # Prepare dynamic variables
        dynamic_variables = {
            "first_name": customer["first_name"],
            "last_name": customer["last_name"],
            "loan_amount": customer["loan_amount"],
            "due_date": customer["due_date"],
            "customer_id": str(customer["id"])
        }
        
        # CRITICAL: Always generate personalized first_message
        if not first_message:
            first_message = (
                f"Hello {customer['first_name']}, this is a reminder about your loan payment "
                f"of rupees {customer['loan_amount']} which is due on {customer['due_date']}. "
                f"Can you please confirm if you will be able to make the payment on time?"
            )
        
        # DEBUG: Print to verify
        print("\n" + "="*60)
        print("Generated First Message:")
        print(first_message)
        print("="*60 + "\n")
        
        # Make the call
        result = await ElevenLabsService.make_outbound_call(
            phone_number=customer["phone_number"],
            dynamic_variables=dynamic_variables,
            first_message=first_message  # Pass the personalized message
        )
        
        # Update customer status
        update_customer_status(customer["id"], {
            "status": "calling",
            "conversation_id": result.get("conversation_id")
        })
        
        return {
            "success": True,
            "conversation_id": result.get("conversation_id"),
            "call_sid": result.get("call_sid"),
            "customer_id": customer["id"],
            "message": f"Call initiated to {customer['first_name']} {customer['last_name']}"
        }
    @staticmethod
    async def get_call_status(conversation_id: str) -> Dict[str, Any]:
        """Get the status of a call"""
        data = await ElevenLabsService.get_conversation_status(conversation_id)
        
        status = data.get("status")
        analysis = data.get("analysis", {})
        data_collection = analysis.get("data_collection", {})
        
        if status == "done":
            customer = find_customer_by_conversation_id(conversation_id)
            if customer:
                update_customer_status(customer["id"], {
                    "status": "completed",
                    "response": data_collection.get("customer_response", "UNCLEAR")
                })
        
        return {
            "conversation_id": conversation_id,
            "status": status,
            "customer_response": data_collection.get("customer_response"),
            "payment_intent": data_collection.get("payment_intent"),
            "callback_requested": data_collection.get("callback_requested"),
            "call_duration": data.get("metadata", {}).get("call_duration_secs"),
            "cost": data.get("metadata", {}).get("cost")
        }
    
    @staticmethod
    async def handle_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle webhook from ElevenLabs"""
        from datetime import datetime
        
        print(f"\n{'='*60}")
        print(f"Webhook received at {datetime.now().isoformat()}")
        print(f"Type: {webhook_data.get('type')}")
        
        additional_info = {}
        
        if webhook_data.get("type") == "post_call_transcription":
            conversation_data = webhook_data.get("data", {})
            
            conversation_id = conversation_data.get("conversation_id")
            status = conversation_data.get("status")
            
            analysis = conversation_data.get("analysis", {})
            data_collection = analysis.get("data_collection", {})
            
            metadata = conversation_data.get("metadata", {})
            dynamic_vars = metadata.get("dynamic_variables", {})
            
            customer_id = dynamic_vars.get("customer_id")
            
            print(f"Conversation ID: {conversation_id}")
            print(f"Customer ID: {customer_id}")
            print(f"Status: {status}")
            print(f"Response: {data_collection.get('customer_response')}")
            print(f"Payment Intent: {data_collection.get('payment_intent')}")
            print(f"{'='*60}\n")
            
            additional_info = {
                "conversation_id": conversation_id,
                "status": status,
                "customer_id": customer_id,
                "data_collection": data_collection,
                "metadata": metadata,
                "dynamic_variables": dynamic_vars
            }
            
            if customer_id:
                # Note: wants_to_pay_early is updated by tool webhook, not here
                update_customer_status(int(customer_id), {
                    "status": "completed",
                    "conversation_id": conversation_id
                    # response field removed - using wants_to_pay_early instead
                })
        
        try:
            WebhookLogger.log_webhook(webhook_data, additional_info)
            print(f"Webhook logged to: {WebhookLogger.get_log_file_path()}")
        except Exception as e:
            print(f"Error logging webhook: {str(e)}")
            
        return {"status": "received"}
    
    @staticmethod
    async def validate_and_cleanup_stale_statuses() -> Dict[str, Any]:
        """
        Validate and cleanup stale 'calling' or 'in_progress' statuses.
        This is called on page load to ensure UI state matches actual call status.
        """
        from datetime import datetime, timedelta
        
        all_customers = get_all_customers()
        stale_customers = []
        cleaned_count = 0
        
        # Check customers with 'calling' or 'in_progress' status
        for customer in all_customers:
            if customer.get("status") in ["calling", "in_progress"]:
                last_updated = customer.get("last_updated")
                
                # If last_updated is more than 10 minutes ago, consider it stale
                if last_updated:
                    try:
                        last_updated_dt = datetime.fromisoformat(last_updated)
                        time_diff = datetime.now() - last_updated_dt
                        
                        # If status is older than 10 minutes, reset to pending
                        if time_diff > timedelta(minutes=10):
                            update_customer_status(customer["id"], {
                                "status": "pending"
                            })
                            cleaned_count += 1
                            stale_customers.append({
                                "id": customer["id"],
                                "name": f"{customer.get('first_name')} {customer.get('last_name')}",
                                "old_status": customer.get("status"),
                                "reason": "Status older than 10 minutes"
                            })
                            continue
                    except (ValueError, TypeError):
                        # If date parsing fails, also consider it stale
                        update_customer_status(customer["id"], {
                            "status": "pending"
                        })
                        cleaned_count += 1
                        stale_customers.append({
                            "id": customer["id"],
                            "name": f"{customer.get('first_name')} {customer.get('last_name')}",
                            "old_status": customer.get("status"),
                            "reason": "Invalid last_updated timestamp"
                        })
                        continue
                else:
                    # No last_updated timestamp, consider it stale
                    update_customer_status(customer["id"], {
                        "status": "pending"
                    })
                    cleaned_count += 1
                    stale_customers.append({
                        "id": customer["id"],
                        "name": f"{customer.get('first_name')} {customer.get('last_name')}",
                        "old_status": customer.get("status"),
                        "reason": "Missing last_updated timestamp"
                    })
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "stale_customers": stale_customers,
            "message": f"Cleaned up {cleaned_count} stale status(es)"
        }
    
    @staticmethod
    async def submit_batch_call(
        call_name: str,
        customer_ids: Optional[List[int]] = None,
        scheduled_time_unix: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit a batch call for multiple customers
        
        Args:
            call_name: Name for the batch call
            customer_ids: Optional list of specific customer IDs to call
                         If None, will use all pending customers
            scheduled_time_unix: Optional Unix timestamp for scheduling
            
        Returns:
            Batch call submission result
        """
        # Get customers to call
        if customer_ids:
            # Use specific customer IDs
            customers = []
            for customer_id in customer_ids:
                customer = find_customer_by_id(customer_id)
                if not customer:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Customer with ID {customer_id} not found"
                    )
                # Only include pending customers
                if customer["status"] == "pending":
                    customers.append(customer)
        else:
            # Use all pending customers
            all_customers = get_all_customers()
            customers = [c for c in all_customers if c["status"] == "pending"]
        
        if len(customers) == 0:
            raise HTTPException(
                status_code=400,
                detail="No pending customers found to call"
            )
        
        # Prepare recipients for batch call
        recipients = []
        for customer in customers:
            # Generate personalized first message
            first_message = (
                f"Hello {customer['first_name']}, this is a reminder about your loan payment "
                f"of rupees {customer['loan_amount']} which is due on {customer['due_date']}. "
                f"Can you please confirm if you will be able to make the payment on time?"
            )
            
            # Prepare dynamic variables
            dynamic_variables = {
                "first_name": customer["first_name"],
                "last_name": customer["last_name"],
                "loan_amount": customer["loan_amount"],
                "due_date": customer["due_date"],
                "customer_id": str(customer["id"])
            }
            
            # Format recipient for batch call API
            # Using conversation_config_override format as per event-management implementation
            # Structure must match exactly: id, phone_number, conversation_initiation_client_data
            # NOTE: Prompt is NOT overridden here - it will use the prompt set in ElevenLabs dashboard
            recipient = {
                "id": str(uuid.uuid4()),
                "phone_number": customer["phone_number"],
                "conversation_initiation_client_data": {
                    "conversation_config_override": {
                        "agent": {
                            # Prompt override removed - using dashboard prompt instead
                            # If you need to override prompt, uncomment below:
                            # "prompt": {
                            #     "prompt": "Your custom prompt here"
                            # },
                            "first_message": first_message,
                            "language": "en"
                        },
                        "tts": {
                            "voice_id": None  # None becomes null in JSON - matches event-management
                        }
                    },
                    "dynamic_variables": dynamic_variables
                }
            }
            recipients.append(recipient)
        
        print("\n" + "="*60)
        print("BATCH CALL PREPARATION")
        print("="*60)
        print(f"Call Name: {call_name}")
        print(f"Total Recipients: {len(recipients)}")
        print(f"Agent ID: {AGENT_ID}")
        print(f"Phone Number ID: {PHONE_NUMBER_ID}")
        print("\nRECIPIENT STRUCTURE (First Recipient):")
        if recipients:
            import json
            print(json.dumps(recipients[0], indent=2, default=str))
        print("="*60 + "\n")
        
        # Submit batch call
        result = await ElevenLabsService.submit_batch_call(
            call_name=call_name,
            agent_id=AGENT_ID,
            agent_phone_number_id=PHONE_NUMBER_ID,
            recipients=recipients,
            scheduled_time_unix=scheduled_time_unix
        )
        
        # Update customer statuses to "calling"
        for customer in customers:
            update_customer_status(customer["id"], {
                "status": "calling"
            })
        
        batch_id = result.get("batch_id") or result.get("id")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "call_name": call_name,
            "recipients_count": len(recipients),
            "message": f"Batch call '{call_name}' submitted successfully with {len(recipients)} recipients",
            "result": result
        }