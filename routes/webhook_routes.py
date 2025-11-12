"""
Webhook Routes
API endpoints for webhook handling
"""
import json
from fastapi import APIRouter, Request
from controllers.customer_controller import CustomerController

router = APIRouter(prefix="/api", tags=["webhooks"])

controller = CustomerController()


@router.post("/webhook")
async def webhook_handler(request: Request):
    """
    Webhook endpoint to receive post-call data from ElevenLabs
    """
    try:
        webhook_data = await request.json()
        return await controller.handle_webhook(webhook_data)
    except Exception as e:
        error_msg = f"Webhook error: {str(e)}"
        print(error_msg)
        # Log error to webhook log file
        try:
            from utils.webhook_logger import WebhookLogger
            WebhookLogger.log_webhook(
                {"type": "error", "error": str(e)},
                {"error_type": type(e).__name__, "error_message": str(e)}
            )
        except Exception as log_error:
            print(f"Failed to log webhook error: {str(log_error)}")
        return {"status": "error", "message": str(e)}


@router.post("/tool-webhook")
async def tool_webhook_handler(request: Request):
    """
    Handle tool calls from ElevenLabs agent
    When agent calls send_payment_link tool, this endpoint receives the request
    
    Expected payload format from ElevenLabs:
    {
        "tool_name": "send_payment_link",
        "conversation_id": "conv_xxxxx",
        "parameters": {
            "wants_to_pay_early": true/false
        }
    }
    Or directly:
    {
        "wants_to_pay_early": true/false
    }
    """
    try:
        tool_data = await request.json()
        
        # Check if conversation_id is in headers (ElevenLabs might send it there)
        conversation_id_from_header = request.headers.get("x-conversation-id") or request.headers.get("conversation-id")
        
        print("\n" + "="*60)
        print("TOOL WEBHOOK RECEIVED")
        print("="*60)
        print(f"Full tool data: {json.dumps(tool_data, indent=2, default=str)}")
        print("="*60 + "\n")
        
        # Extract tool call information (handle different possible formats)
        # ElevenLabs may send the data directly or nested
        tool_name = tool_data.get("tool_name") or tool_data.get("name") or tool_data.get("tool")
        
        # If tool_data itself contains wants_to_pay_early, it's the parameters
        if "wants_to_pay_early" in tool_data and not tool_name:
            # The entire payload is the parameters
            parameters = tool_data
            tool_name = "send_payment_link"  # Assume it's our tool
        else:
            parameters = tool_data.get("parameters") or tool_data.get("body") or tool_data.get("data") or {}
        
        conversation_id = (
            tool_data.get("conversation_id") or 
            tool_data.get("conversationId") or 
            conversation_id_from_header or
            None
        )
        
        print(f"Tool Name: {tool_name}")
        print(f"Parameters: {parameters}")
        print(f"Conversation ID: {conversation_id}")
        
        if tool_name == "send_payment_link" or "wants_to_pay_early" in tool_data:
            # Get the yes/no response - check both parameters and tool_data directly
            wants_to_pay_early = parameters.get("wants_to_pay_early") or tool_data.get("wants_to_pay_early", False)
            
            # Handle boolean as string
            if isinstance(wants_to_pay_early, str):
                wants_to_pay_early = wants_to_pay_early.lower() in ["true", "yes", "1"]
            
            print(f"\nCustomer wants to pay early: {wants_to_pay_early}")
            
            if wants_to_pay_early:
                # Find customer by conversation_id or other means
                from database import find_customer_by_conversation_id, get_all_customers
                customer = None
                
                if conversation_id:
                    customer = find_customer_by_conversation_id(conversation_id)
                    if not customer:
                        print(f"Customer not found by conversation_id: {conversation_id}")
                        # Try to find by batch_id stored in conversation_id field
                        all_customers = get_all_customers()
                        customer = next((c for c in all_customers if c.get("conversation_id") == conversation_id), None)
                
                # If still not found, find the most recent "calling" customer (for batch calls)
                if not customer:
                    all_customers = get_all_customers()
                    calling_customers = [c for c in all_customers if c.get("status") == "calling"]
                    if calling_customers:
                        # Get the most recently updated one
                        calling_customers.sort(key=lambda x: x.get("last_updated") or "", reverse=True)
                        customer = calling_customers[0]
                        print(f"Found customer by status (most recent calling): {customer['first_name']} {customer['last_name']}")
                
                if customer:
                    print(f"Found customer: {customer['first_name']} {customer['last_name']}")
                    print(f"   Phone: {customer['phone_number']}")
                    print(f"   Loan Amount: {customer['loan_amount']}")
                    print(f"   Due Date: {customer['due_date']}")
                    
                    # Update customer record with wants_to_pay_early
                    from database import update_customer_status
                    update_customer_status(customer.get("id"), {
                        "wants_to_pay_early": "YES" if wants_to_pay_early else "NO",
                        "status": "completed"  # Mark as completed after tool call
                    })
                    
                    # Send payment link email
                    from services.email_service import EmailService
                    
                    customer_email = customer.get("email")
                    if not customer_email:
                        print("Customer email not found - cannot send email")
                        return {
                            "success": False,
                            "message": "Customer email not found",
                            "email_sent": False
                        }
                    
                    email_result = await EmailService.send_payment_link_email(
                        customer_email=customer_email,
                        customer_name=f"{customer['first_name']} {customer['last_name']}",
                        loan_amount=customer['loan_amount'],
                        due_date=customer['due_date'],
                        customer_id=customer.get("id")
                    )
                    
                    email_sent = email_result.get("success", False)
                    email_message = email_result.get("message", "")
                    
                    if not email_sent:
                        print(f"Email sending failed: {email_message}")
                        # Still update customer status even if email fails
                    else:
                        print(f"Email sent successfully: {email_result.get('payment_link')}")
                    
                    # Log to webhook logger
                    try:
                        from utils.webhook_logger import WebhookLogger
                        WebhookLogger.log_webhook(
                            {"type": "tool_call", "tool_name": tool_name},
                            {
                                "conversation_id": conversation_id,
                                "customer_id": customer.get("id"),
                                "wants_to_pay_early": wants_to_pay_early,
                                "email_sent": email_sent,
                                "email_address": customer_email,
                                "payment_link": email_result.get("payment_link") if email_sent else None
                            }
                        )
                    except Exception as log_error:
                        print(f"Error logging tool webhook: {str(log_error)}")
                    
                    # Return success response to ElevenLabs
                    return {
                        "success": True,
                        "message": email_message if email_sent else f"Customer confirmed but email failed: {email_message}",
                        "email_sent": email_sent,
                        "customer_id": customer.get("id"),
                        "payment_link": email_result.get("payment_link") if email_sent else None
                    }
                else:
                    print("Customer not found - cannot send email")
                    return {
                        "success": False,
                        "message": "Customer not found for this conversation",
                        "email_sent": False
                    }
            else:
                # Customer said no - still update the customer record
                print("Customer declined to pay early")
                
                # Find customer and update status
                from database import find_customer_by_conversation_id, update_customer_status, get_all_customers
                customer = None
                
                if conversation_id:
                    customer = find_customer_by_conversation_id(conversation_id)
                    if not customer:
                        all_customers = get_all_customers()
                        customer = next((c for c in all_customers if c.get("conversation_id") == conversation_id), None)
                
                # If still not found, find the most recent "calling" customer
                if not customer:
                    all_customers = get_all_customers()
                    calling_customers = [c for c in all_customers if c.get("status") == "calling"]
                    if calling_customers:
                        calling_customers.sort(key=lambda x: x.get("last_updated") or "", reverse=True)
                        customer = calling_customers[0]
                        print(f"Found customer by status (most recent calling): {customer['first_name']} {customer['last_name']}")
                
                if customer:
                    # Update customer record with wants_to_pay_early = NO
                    update_customer_status(customer.get("id"), {
                        "wants_to_pay_early": "NO",
                        "status": "completed"  # Mark as completed after tool call
                    })
                    print(f"Updated customer {customer.get('id')}: wants_to_pay_early = NO")
                
                # Log to webhook logger
                try:
                    from utils.webhook_logger import WebhookLogger
                    WebhookLogger.log_webhook(
                        {"type": "tool_call", "tool_name": tool_name},
                        {
                            "conversation_id": conversation_id,
                            "customer_id": customer.get("id") if customer else None,
                            "wants_to_pay_early": False,
                            "email_sent": False
                        }
                    )
                except Exception as log_error:
                    print(f"Error logging tool webhook: {str(log_error)}")
                
                return {
                    "success": True,
                    "message": "Customer declined early payment",
                    "email_sent": False
                }
        
        # Unknown tool
        print(f"Unknown tool: {tool_name}")
        return {
            "success": False,
            "message": f"Unknown tool: {tool_name}"
        }
        
    except Exception as e:
        print(f"\nTool webhook error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        
        # Log error
        try:
            from utils.webhook_logger import WebhookLogger
            WebhookLogger.log_webhook(
                {"type": "tool_call_error", "error": str(e)},
                {"error_type": type(e).__name__, "error_message": str(e)}
            )
        except Exception:
            pass
        
        return {
            "success": False,
            "error": str(e)
        }

