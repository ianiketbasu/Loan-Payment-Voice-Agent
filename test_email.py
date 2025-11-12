"""
Simple Email Test Script
Tests if Mailtrap Email API is working correctly
"""
import asyncio
import sys
from services.email_service import EmailService


async def test_email():
    """Test sending an email via Mailtrap API"""
    print("=" * 60)
    print("Testing Mailtrap Email API")
    print("=" * 60)
    
    # Test data
    test_email = "aniketbasu23@gmail.com"
    test_name = "Test Customer"
    loan_amount = "50000"
    due_date = "2024-12-31"
    customer_id = 999  # Test ID
    
    print("\nTest Details:")
    print(f"   To: {test_email}")
    print(f"   Name: {test_name}")
    print(f"   Loan Amount: ₹{loan_amount}")
    print(f"   Due Date: {due_date}")
    print("\nSending test email...\n")
    
    try:
        result = await EmailService.send_payment_link_email(
            customer_email=test_email,
            customer_name=test_name,
            loan_amount=loan_amount,
            due_date=due_date,
            customer_id=customer_id
        )
        
        print("\n" + "=" * 60)
        if result.get("success"):
            print("SUCCESS! Email sent successfully!")
            print(f"   Email: {result.get('email')}")
            print(f"   Payment Link: {result.get('payment_link')}")
            print("\nCheck your Mailtrap inbox:")
            print("   https://mailtrap.io")
            return 0
        else:
            print("FAILED! Email could not be sent")
            print(f"   Error: {result.get('message')}")
            if result.get('status_code'):
                print(f"   Status Code: {result.get('status_code')}")
            return 1
            
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"ERROR! Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        print("=" * 60 + "\n")


if __name__ == "__main__":
    exit_code = asyncio.run(test_email())
    sys.exit(exit_code)

