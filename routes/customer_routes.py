"""
Customer Routes
API endpoints for customer operations
"""
from fastapi import APIRouter, HTTPException
from models import Customer, CallRequest, BatchCallRequest
from controllers.customer_controller import CustomerController
from services.email_service import EmailService

router = APIRouter(prefix="/api", tags=["customers"])

controller = CustomerController()


@router.get("/customers")
async def get_customers():
    """Get all customers"""
    return await controller.get_all_customers()


@router.post("/customers")
async def add_customer(customer: Customer):
    """Add a new customer"""
    return await controller.create_customer(customer)


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: int):
    """Delete a customer"""
    return await controller.delete_customer(customer_id)


@router.put("/customers/{customer_id}/reset")
async def reset_customer_status(customer_id: int):
    """Reset customer status to pending"""
    return await controller.reset_customer_status(customer_id)


@router.post("/make-call")
async def make_call(request: CallRequest):
    """Initiate a single outbound call to a customer"""
    return await controller.make_call(request.customer_id, request.first_message)


@router.get("/call-status/{conversation_id}")
async def get_call_status(conversation_id: str):
    """Get the status of a call"""
    return await controller.get_call_status(conversation_id)


@router.post("/batch-call")
async def submit_batch_call(request: BatchCallRequest):
    """
    Submit a batch call for multiple customers
    
    - If customer_ids is provided, calls only those specific customers
    - If customer_ids is not provided, calls all pending customers
    """
    return await controller.submit_batch_call(
        call_name=request.call_name,
        customer_ids=request.customer_ids,
        scheduled_time_unix=request.scheduled_time_unix
    )


@router.get("/batch-call/{batch_id}")
async def get_batch_call_status(batch_id: str):
    """Get the status of a batch call"""
    from services.elevenlabs_service import ElevenLabsService
    return await ElevenLabsService.get_batch_call_status(batch_id)


@router.post("/validate-statuses")
async def validate_statuses():
    """Validate and cleanup stale 'calling' or 'in_progress' statuses"""
    return await controller.validate_and_cleanup_stale_statuses()


@router.post("/test-email")
async def test_email():
    """
    Test endpoint to verify email delivery via Mailtrap API
    Sends a test email to aniketbasu23@gmail.com
    """
    try:
        result = await EmailService.send_payment_link_email(
            customer_email="aniketbasu23@gmail.com",
            customer_name="Test Customer",
            loan_amount="50000",
            due_date="2024-12-31",
            customer_id=999
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Test email sent successfully!",
                "details": {
                    "email": result.get("email"),
                    "payment_link": result.get("payment_link"),
                    "api_response": result.get("api_response")
                },
                "note": "Check your Mailtrap inbox at https://mailtrap.io"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "message": "Failed to send test email",
                    "error": result.get("message"),
                    "status_code": result.get("status_code")
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Error testing email: {str(e)}"
            }
        )
