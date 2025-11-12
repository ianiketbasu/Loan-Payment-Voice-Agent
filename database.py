"""
Database/Storage Layer
In-memory storage for demo (use database in production)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

# In-memory storage for demo (use database in production)
customers_db: List[Dict[str, Any]] = [
    {
        "id": 1,
        "phone_number": "+918515953686",
        "first_name": "AV",
        "last_name": "AV",
        "email": "aniketbasu23@gmail.com",
        "due_date": "2024-12-31",
        "loan_amount": "50000",
        "status": "pending",
        "response": None,
        "conversation_id": None,
        "last_updated": None
    },
    {
        "id": 2,
        "phone_number": "+919038345917",
        "first_name": "AB",
        "last_name": "AB",
        "email": "customer2@example.com",
        "due_date": "2024-11-15",
        "loan_amount": "75000",
        "status": "pending",
        "response": None,
        "conversation_id": None,
        "last_updated": None
    },
    {
        "id": 3,
        "phone_number": "+919547910980",
        "first_name": "AB",
        "last_name": "AB",
        "email": "customer3@example.com",
        "due_date": "2024-10-20",
        "loan_amount": "30000",
        "status": "pending",
        "response": None,
        "conversation_id": None,
        "last_updated": None
    },
    {
        "id": 4,
        "phone_number": "+918609300739",
        "first_name": "AB",
        "last_name": "AB",
        "email": "customer4@example.com",
        "due_date": "2024-12-05",
        "loan_amount": "45000",
        "status": "pending",
        "response": None,
        "conversation_id": None,
        "last_updated": None
    }
]


def find_customer_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    """Find customer by ID"""
    for customer in customers_db:
        if customer["id"] == customer_id:
            return customer
    return None


def find_customer_by_conversation_id(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Find customer by conversation ID"""
    for customer in customers_db:
        if customer.get("conversation_id") == conversation_id:
            return customer
    return None


def update_customer_status(customer_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update customer record"""
    for customer in customers_db:
        if customer["id"] == customer_id:
            customer.update(updates)
            customer["last_updated"] = datetime.now().isoformat()
            return customer
    return None


def get_all_customers() -> List[Dict[str, Any]]:
    """Get all customers"""
    return customers_db


def add_customer(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new customer"""
    new_id = max([c["id"] for c in customers_db]) + 1 if customers_db else 1
    customer_data["id"] = new_id
    customer_data["status"] = "pending"
    customer_data["last_updated"] = datetime.now().isoformat()
    customers_db.append(customer_data)
    return customer_data


def delete_customer(customer_id: int) -> bool:
    """Delete a customer"""
    global customers_db
    initial_length = len(customers_db)
    customers_db = [c for c in customers_db if c["id"] != customer_id]
    return len(customers_db) < initial_length

