"""
Email Service
Handles sending emails via Mailtrap Email API
"""
import httpx
from typing import Dict, Any


class EmailService:
    """Service for sending emails using Mailtrap Email API"""
    
    @staticmethod
    async def send_payment_link_email(
        customer_email: str,
        customer_name: str,
        loan_amount: str,
        due_date: str,
        customer_id: Any
    ) -> Dict[str, Any]:
        """
        Send payment link email to customer using Mailtrap Email API
        
        Args:
            customer_email: Customer's email address
            customer_name: Customer's full name
            loan_amount: Loan amount
            due_date: Due date
            customer_id: Customer ID for payment link
            
        Returns:
            Dict with success status and message
        """
        try:
            from config import (
                MAILTRAP_API_TOKEN,
                MAILTRAP_INBOX_ID,
                MAILTRAP_API_URL,
                MAIL_FROM_EMAIL,
                MAIL_FROM_NAME
            )
            
            # Validate required email configuration
            if not MAILTRAP_API_TOKEN:
                return {
                    "success": False,
                    "message": "MAILTRAP_API_TOKEN not configured. Please set it in environment variables.",
                    "email": customer_email
                }
            if not MAILTRAP_INBOX_ID:
                return {
                    "success": False,
                    "message": "MAILTRAP_INBOX_ID not configured. Please set it in environment variables.",
                    "email": customer_email
                }
            if not MAIL_FROM_EMAIL:
                return {
                    "success": False,
                    "message": "MAIL_FROM_EMAIL not configured. Please set it in environment variables.",
                    "email": customer_email
                }
            if not MAIL_FROM_NAME:
                return {
                    "success": False,
                    "message": "MAIL_FROM_NAME not configured. Please set it in environment variables.",
                    "email": customer_email
                }
            
            # Generate payment link (dummy for now)
            payment_link = f"https://payment.tech.com/pay/{customer_id}?amount={loan_amount}"
            
            # Create email body (text version)
            text_content = f"""
Dear {customer_name},

Thank you for confirming your interest in paying your loan early.

Loan Details:
- Loan Amount: ₹{loan_amount}
- Due Date: {due_date}

Please use the following link to complete your early payment:
{payment_link}

This link will be valid for 7 days.

If you have any questions, please contact us.

Best regards,
Tech Loan Services
"""
            
            # Create email body (HTML version)
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 30px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Early Payment Confirmation</h1>
        </div>
        <div class="content">
            <p>Dear {customer_name},</p>
            <p>Thank you for confirming your interest in paying your loan early.</p>
            
            <h3>Loan Details:</h3>
            <ul>
                <li><strong>Loan Amount:</strong> ₹{loan_amount}</li>
                <li><strong>Due Date:</strong> {due_date}</li>
            </ul>
            
            <p>Please use the following link to complete your early payment:</p>
            <p style="text-align: center;">
                <a href="{payment_link}" class="button">Pay Now</a>
            </p>
            <p style="font-size: 12px; color: #666;">This link will be valid for 7 days.</p>
            
            <p>If you have any questions, please contact us.</p>
            <p>Best regards,<br>Tech Loan Services</p>
        </div>
        <div class="footer">
            <p>This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
            
            # Prepare API request payload
            api_url = f"{MAILTRAP_API_URL}/{MAILTRAP_INBOX_ID}"
            payload = {
                "from": {
                    "email": MAIL_FROM_EMAIL,
                    "name": MAIL_FROM_NAME
                },
                "to": [
                    {
                        "email": customer_email
                    }
                ],
                "subject": f"Early Payment Link - Loan Amount ₹{loan_amount}",
                "text": text_content,
                "html": html_content,
                "category": "Payment Link"
            }
            
            # Send email via Mailtrap Email API
            print(f"\nSending email to {customer_email} via Mailtrap API...")
            print(f"   Subject: {payload['subject']}")
            print(f"   Payment Link: {payment_link}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {MAILTRAP_API_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                # Check response
                if response.status_code == 200:
                    response_data = response.json()
                    print(f"Email sent successfully to {customer_email}")
                    print(f"   Response: {response_data}")
                    
                    return {
                        "success": True,
                        "message": f"Payment link email sent to {customer_email}",
                        "email": customer_email,
                        "payment_link": payment_link,
                        "api_response": response_data
                    }
                else:
                    error_msg = f"API returned status {response.status_code}: {response.text}"
                    print(f"Error sending email: {error_msg}")
                    
                    return {
                        "success": False,
                        "message": error_msg,
                        "email": customer_email,
                        "status_code": response.status_code
                    }
            
        except Exception as e:
            print(f"\nError sending email: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "email": customer_email
            }
