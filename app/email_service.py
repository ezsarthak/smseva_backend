import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import List
from dotenv import load_dotenv
from .models import IssueResponse

load_dotenv()


class EmailService:
    def __init__(self):
        # SendGrid Configuration
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@suvidha.app")
        self.from_name = os.getenv("FROM_NAME", "Municipal Voice Assistant")

        # Check configuration
        self.is_configured = bool(self.sendgrid_api_key)
        if self.is_configured:
            print("✅ SendGrid email service configured.")
        else:
            print("⚠️ SendGrid not configured. Email notifications disabled.")

    # ==========================================================
    # 📩 EMAIL TEMPLATE METHODS
    # ==========================================================

    def _create_ticket_confirmation_html(self, issue: IssueResponse, user_name: str) -> str:
        """Create HTML content for ticket confirmation email"""
        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Ticket Confirmation</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #007bff; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                    .ticket-details {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
                    .status-new {{ color: #007bff; font-weight: bold; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎫 Ticket Created Successfully!</h1>
                    </div>
                    <div class="content">
                        <p>Dear <strong>{user_name}</strong>,</p>
                        <p>Your municipal issue has been registered successfully. Here are the details:</p>
                        <div class="ticket-details">
                            <h3>📋 Ticket Details</h3>
                            <p><strong>Ticket ID:</strong> <code>{issue.ticket_id}</code></p>
                            <p><strong>Title:</strong> {issue.title}</p>
                            <p><strong>Category:</strong> {issue.category}</p>
                            <p><strong>Address:</strong> {issue.address}</p>
                            <p><strong>Description:</strong> {issue.description}</p>
                            <p><strong>Status:</strong> <span class="status-new">{issue.status}</span></p>
                            <p><strong>Created:</strong> {issue.created_at}</p>
                            <p><strong>Report Count:</strong> {issue.issue_count}</p>
                        </div>
                        <p>We will keep you updated on the progress. You can track your ticket using the Ticket ID above.</p>
                        <p>Thank you for helping improve our city!</p>
                    </div>
                    <div class="footer">
                        <hr>
                        <p>This is an automated message from the Municipal Voice Assistant System.</p>
                    </div>
                </div>
            </body>
            </html>
        """

    def _create_status_update_html(self, ticket_id: str, old_status: str, new_status: str) -> str:
        """Create HTML content for status update email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Status Update</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                .status-update {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #28a745; }}
                .old-status {{ color: #6c757d; }}
                .new-status {{ color: #28a745; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔄 Ticket Status Updated</h1>
                </div>
                <div class="content">
                    <p>Dear User,</p>
                    <p>The status of your municipal issue has been updated:</p>
                    <div class="status-update">
                        <h3>📋 Status Update</h3>
                        <p><strong>Ticket ID:</strong> <code>{ticket_id}</code></p>
                        <p><strong>Previous Status:</strong> <span class="old-status">{old_status}</span></p>
                        <p><strong>New Status:</strong> <span class="new-status">{new_status}</span></p>
                    </div>
                    <p>We will continue to keep you informed of any further updates.</p>
                    <p>Thank you for your patience!</p>
                </div>
                <div class="footer">
                    <hr>
                    <p>This is an automated message from the Municipal Voice Assistant System.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_assignment_notification_html(self, ticket_id: str, assigned_to: str, assigned_by: str, notes: str = None) -> str:
        """Create HTML content for assignment notification email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Issue Assignment</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ffc107; color: #212529; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                .assignment-details {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #ffc107; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 New Issue Assignment</h1>
                </div>
                <div class="content">
                    <p>Dear <strong>{assigned_to}</strong>,</p>
                    <p>You have been assigned a new municipal issue to resolve:</p>
                    <div class="assignment-details">
                        <h3>📋 Assignment Details</h3>
                        <p><strong>Ticket ID:</strong> <code>{ticket_id}</code></p>
                        <p><strong>Assigned By:</strong> {assigned_by}</p>
                        <p><strong>Assigned To:</strong> {assigned_to}</p>
                        <p><strong>Assigned At:</strong> {self._get_current_time()}</p>
                        {f'<p><strong>Notes:</strong> {notes}</p>' if notes else ''}
                    </div>
                    <p>Please log into the system to view the full issue details and update the status as you work on it.</p>
                    <p>Thank you for your service!</p>
                </div>
                <div class="footer">
                    <hr>
                    <p>This is an automated message from the Municipal Voice Assistant System.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_current_time(self) -> str:
        """Get current time formatted"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M %d-%m-%Y")

    # ==========================================================
    # 📤 EMAIL SENDING METHODS (SendGrid)
    # ==========================================================

    async def send_ticket_confirmation(self, issue: IssueResponse, user_email: str, user_name: str) -> bool:
        """Send ticket confirmation email"""
        if not self.is_configured:
            print(f"SendGrid not configured. Skipping email to {user_email}")
            return False

        subject = f"🎫 Ticket Confirmed - {issue.ticket_id}"
        html_content = self._create_ticket_confirmation_html(issue, user_name)
        return self._send_email(user_email, subject, html_content)

    async def send_status_update_notification(self, ticket_id: str, old_status: str, new_status: str, user_emails: List[str]) -> bool:
        """Send ticket status update emails"""
        if not self.is_configured:
            print(f"SendGrid not configured. Skipping status update for {ticket_id}")
            return False

        subject = f"🔄 Status Update - Ticket {ticket_id}"
        html_content = self._create_status_update_html(ticket_id, old_status, new_status)
        success_count = sum([self._send_email(email, subject, html_content) for email in user_emails])
        print(f"📧 Status update emails: {success_count}/{len(user_emails)} sent successfully")
        return success_count == len(user_emails)

    async def send_assignment_notification(self, ticket_id: str, assigned_to: str, assigned_by: str, notes: str = None) -> bool:
        """Send assignment notification"""
        if not self.is_configured:
            print(f"SendGrid not configured. Skipping assignment for {ticket_id}")
            return False

        subject = f"📋 New Assignment - Ticket {ticket_id}"
        html_content = self._create_assignment_notification_html(ticket_id, assigned_to, assigned_by, notes)
        return self._send_email(assigned_to, subject, html_content)

    # ==========================================================
    # 🧠 CORE EMAIL SENDER (SendGrid)
    # ==========================================================

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid API"""
        try:
            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(self.sendgrid_api_key)
            sg.send(message)
            print(f"✅ Email sent to {to_email}")
            return True
        except Exception as e:
            print(f"❌ Error sending email to {to_email}: {e}")
            return False


# Global instance
email_service = EmailService()
