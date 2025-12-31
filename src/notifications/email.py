from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

async def send_expiry_reminder_email(email: str, user_id: str, days_remaining: int):
    try:
        message = Mail(
            from_email=os.getenv('FROM_EMAIL'),
            to_emails=email,
            subject=f'⏰ Your Deployr trial expires in {days_remaining} day{"s" if days_remaining > 1 else ""}',
            html_content=f"""
                <h2>Your trial is ending soon!</h2>
                <p>You have <strong>{days_remaining} day{"s" if days_remaining > 1 else ""}</strong> left.</p>
                <p><a href="https://deployr.com/upgrade?user={user_id}">Upgrade Now</a></p>
            """
        )
        
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        print(f"[EMAIL] ✓ Sent reminder to {email} (status: {response.status_code})")
        return True
        
    except Exception as e:
        print(f"[EMAIL] ✗ Failed to send to {email}: {e}")
        return False