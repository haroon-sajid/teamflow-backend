import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.sender_email = os.getenv("MAIL_FROM")
        self.enabled = bool(self.sendgrid_api_key and self.sender_email)
        if not self.enabled:
            logger.warning("📧 Email service not configured. SendGrid API key or MAIL_FROM missing.")
        else:
            logger.info(f"📧 Email service configured with SendGrid from {self.sender_email}")

    async def send_invitation_email(
        self, 
        to_email: str, 
        invitation_link: str, 
        role: str, 
        invited_by: str = "Admin"
    ) -> bool:
        """
        Send an invitation email with a direct link.
        ⚠️ IMPORTANT: invitation_link must already be a valid, safe URL.
        Do NOT URL-encode the entire link — it breaks query parameters.
        """
        if not self.enabled:
            logger.info(f"Would send email to {to_email} (SendGrid not configured).")
            logger.info(f"Invitation link: {invitation_link}")
            return True

        # ✅ DO NOT encode the full URL — it corrupts ? and = in query params
        # The token from secrets.token_urlsafe() is already URL-safe.
        subject = f"🎉 You're invited to join TeamFlow as {role.title()}!"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello!</h2>
            <p>{invited_by} has invited you to join TeamFlow as <strong>{role.title()}</strong>.</p>
            <p>Click the button below to accept your invitation:</p>
            <p style="text-align: center;">
                <a href="{invitation_link}" style="
                    background-color: #667eea;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    display: inline-block;
                ">✅ Accept Invitation</a>
            </p>
            <p>If the button doesn’t work, copy-paste this link into your browser:</p>
            <p style="word-break: break-all;">{invitation_link}</p>
            <p>Invitation expires in 7 days.</p>
            <p>Best regards,<br><strong>The TeamFlow Team</strong></p>
        </div>
        """

        try:
            message = Mail(
                from_email=self.sender_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            logger.info(f"✅ Email sent to {to_email}, status code: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False

# Global instance
email_service = EmailService()