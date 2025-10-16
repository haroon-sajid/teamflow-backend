# # services/email_service.py
# import smtplib
# import os
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# import logging
# from typing import Optional

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class EmailService:
#     def __init__(self):
#         self.smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
#         self.smtp_port = int(os.getenv("MAIL_PORT", 587))
#         self.sender_email = os.getenv("MAIL_USERNAME")
#         self.sender_password = os.getenv("MAIL_PASSWORD")
        
#         # Debug: Print what's loaded
#         logger.info(f"📧 MAIL_USERNAME loaded: {bool(self.sender_email)}")
#         logger.info(f"📧 MAIL_PASSWORD loaded: {bool(self.sender_password)}")
#         logger.info(f"📧 Current MAIL_USERNAME: {self.sender_email}")
#         logger.info(f"📧 Current MAIL_SERVER: {self.smtp_server}")
        
#         self.enabled = bool(self.sender_email and self.sender_password)
        
#         if not self.enabled:
#             logger.warning("📧 Email service not configured. Set MAIL_USERNAME and MAIL_PASSWORD environment variables.")
#         else:
#             logger.info(f"📧 Email service configured for: {self.sender_email}")
    
#     async def send_invitation_email(self, to_email: str, invitation_link: str, role: str, invited_by: str = "Admin") -> bool:
#         """
#         Send invitation email to new user
#         Returns True if successful, False if failed
#         """
#         # If email not configured, just log and return True
#         if not self.enabled:
#             logger.info(f"📧 Email service not configured. Would send invitation to {to_email}")
#             logger.info(f"📧 Invitation link: {invitation_link}")
#             return True
            
#         try:
#             subject = f"🎉 You're invited to join TeamFlow as {role.title()}!"
            
#             html_content = f"""
#             <!DOCTYPE html>
#             <html>
#             <head>
#                 <meta charset="utf-8">
#                 <style>
#                     body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
#                     .container {{ max-width: 600px; margin: 0 auto; background: white; }}
#                     .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
#                     .content {{ padding: 30px; background: #f8f9fa; }}
#                     .button {{ background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; font-size: 16px; font-weight: bold; }}
#                     .footer {{ text-align: center; margin-top: 30px; padding: 20px; font-size: 12px; color: #666; border-top: 1px solid #ddd; }}
#                     .link-box {{ background: #e9ecef; padding: 15px; border-radius: 5px; word-break: break-all; font-family: monospace; margin: 20px 0; }}
#                 </style>
#             </head>
#             <body>
#                 <div class="container">
#                     <div class="header">
#                         <h1 style="margin: 0; font-size: 28px;">Welcome to TeamFlow! 🚀</h1>
#                         <p style="margin: 10px 0 0 0; opacity: 0.9;">Collaborate, Create, Succeed Together</p>
#                     </div>
#                     <div class="content">
#                         <h2>Hello!</h2>
#                         <p>You've been invited by <strong>{invited_by}</strong> to join TeamFlow as a <strong>{role.title()}</strong>.</p>
#                         <p>TeamFlow helps teams collaborate on projects and tasks efficiently.</p>
                        
#                         <div style="text-align: center;">
#                             <a href="{invitation_link}" class="button">
#                                 ✅ Accept Invitation & Create Account
#                             </a>
#                         </div>
                        
#                         <p><strong>⚠️ Important:</strong> This invitation link will expire in 7 days.</p>
                        
#                         <p>If the button doesn't work, copy and paste this link into your browser:</p>
#                         <div class="link-box">
#                             {invitation_link}
#                         </div>
                        
#                         <p>We're excited to have you on board!</p>
#                         <p>Best regards,<br><strong>The TeamFlow Team</strong></p>
#                     </div>
#                     <div class="footer">
#                         <p>This is an automated message. Please do not reply to this email.</p>
#                         <p>© 2024 TeamFlow. All rights reserved.</p>
#                     </div>
#                 </div>
#             </body>
#             </html>
#             """
            
#             # Create message
#             msg = MIMEMultipart('alternative')
#             msg['From'] = os.getenv("MAIL_FROM", f"TeamFlow <{self.sender_email}>")
#             msg['To'] = to_email
#             msg['Subject'] = subject
            
#             # Create plain text version as fallback
#             text_content = f"""
#             Welcome to TeamFlow!
            
#             You've been invited by {invited_by} to join TeamFlow as a {role.title()}.
            
#             Click here to accept your invitation:
#             {invitation_link}
            
#             This invitation link will expire in 7 days.
            
#             Best regards,
#             The TeamFlow Team
#             """
            
#             # Attach both HTML and plain text versions
#             part1 = MIMEText(text_content, 'plain')
#             part2 = MIMEText(html_content, 'html')
            
#             msg.attach(part1)
#             msg.attach(part2)
            
#             # Send email
#             with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
#                 server.starttls()
#                 server.login(self.sender_email, self.sender_password)
#                 server.send_message(msg)
                
#             logger.info(f"✅ Invitation email sent successfully to: {to_email}")
#             return True
            
#         except Exception as e:
#             logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
#             return False

# # Create global instance
# email_service = EmailService()


















# services/email_service.py
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.sender_email = os.getenv("MAIL_FROM")
        self.enabled = bool(self.api_key and self.sender_email)

        if not self.enabled:
            logger.warning("📧 Email service not configured. Set SENDGRID_API_KEY and MAIL_FROM environment variables.")
        else:
            logger.info(f"📧 Email service configured for: {self.sender_email}")

    async def send_invitation_email(self, to_email: str, invitation_link: str, role: str, invited_by: str = "Admin") -> bool:
        if not self.enabled:
            logger.info(f"📧 Email service not configured. Would send invitation to {to_email}")
            logger.info(f"📧 Invitation link: {invitation_link}")
            return True

        subject = f"🎉 You're invited to join TeamFlow as {role.title()}!"
        html_content = f"""
        <h2>Hello!</h2>
        <p>You've been invited by <strong>{invited_by}</strong> to join TeamFlow as a <strong>{role.title()}</strong>.</p>
        <p>Click here to accept the invitation:</p>
        <a href="{invitation_link}">{invitation_link}</a>
        <p>This link will expire in 7 days.</p>
        """

        try:
            message = Mail(
                from_email=self.sender_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            logger.info(f"✅ Invitation email sent to {to_email}, Status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

# Global instance
email_service = EmailService()
