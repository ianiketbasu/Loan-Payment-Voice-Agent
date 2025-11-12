"""
Pydantic Models for Request/Response validation
"""
from pydantic import BaseModel
from typing import Optional


class Customer(BaseModel):
    """Customer model"""
    id: Optional[int] = None
    phone_number: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    due_date: str
    loan_amount: str
    status: Optional[str] = "pending"
    response: Optional[str] = None
    wants_to_pay_early: Optional[str] = None
    conversation_id: Optional[str] = None
    last_updated: Optional[str] = None


class CallRequest(BaseModel):
    """Request model for making a call"""
    customer_id: int
    first_message: Optional[str] = None  # Optional override


class BatchCallRequest(BaseModel):
    """Request model for batch calling"""
    call_name: str
    customer_ids: Optional[list[int]] = None  # If provided, use these specific customers
    # If customer_ids not provided, will use all pending customers
    scheduled_time_unix: Optional[int] = None  # Optional scheduling