"""
Notification service for emailing users about their orders.
"""

def send_email_notification(email: str, subject: str, body: str) -> bool:
    """Sends a mock email notification to the user."""
    print(f"Sending email to {email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    return True

def notify_order_success(user_email: str, order_id: int) -> bool:
    """Convenience helper to send a successful order email."""
    subject = f"Order #{order_id} Confirmed!"
    body = "Thank you for shopping with us! Your order is being processed."
    return send_email_notification(user_email, subject, body)
