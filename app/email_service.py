import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from dotenv import load_dotenv
from .models import IssueResponse

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "Municipal Voice Assistant")
        
        # Check if SMTP is configured
        self.is_configured = all([
            self.smtp_username,
            self.smtp_password
        ])
        
        if not self.is_configured:
            print("Warning: SMTP not fully configured. Email notifications will be disabled.")
            print("Please set SMTP_USERNAME and SMTP_PASSWORD environment variables")
        else:
            print(f"✅ SMTP configured: {self.smtp_server}:{self.smtp_port}")
    
    def _create_ticket_confirmation_html(self, issue: IssueResponse, user_name: str) -> str:
        """Create HTML content for ticket confirmation email"""
        html_content = f"""
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
        return html_content
    
    def _create_status_update_html(self, ticket_id: str, old_status: str, new_status: str) -> str:
        """Create HTML content for status update email"""
        html_content = f"""
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
        return html_content
    
    async def send_ticket_confirmation(self, issue: IssueResponse, user_email: str, user_name: str) -> bool:
        """
        Send ticket confirmation email using SMTP
        
        Args:
            issue: The created/updated issue
            user_email: User's email address
            user_name: User's name
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            print(f"SMTP not configured. Skipping email to {user_email}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🎫 Ticket Confirmed - {issue.ticket_id}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = user_email
            
            # Create HTML content
            html_content = self._create_ticket_confirmation_html(issue, user_name)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email notification sent successfully to {user_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email to {user_email}: {str(e)}")
            return False
    
    async def send_status_update_notification(self, ticket_id: str, old_status: str, new_status: str, user_emails: list) -> bool:
        """
        Send status update notification emails
        
        Args:
            ticket_id: The ticket ID
            old_status: Previous status
            new_status: New status
            user_emails: List of user emails to notify
            
        Returns:
            bool: True if all emails sent successfully, False otherwise
        """
        if not self.is_configured:
            print(f"SMTP not configured. Skipping status update emails for ticket {ticket_id}")
            return False
        
        success_count = 0
        total_count = len(user_emails)
        
        for user_email in user_emails:
            try:
                # Create message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"🔄 Status Update - Ticket {ticket_id}"
                msg['From'] = f"{self.from_name} <{self.from_email}>"
                msg['To'] = user_email
                
                # Create HTML content
                html_content = self._create_status_update_html(ticket_id, old_status, new_status)
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
                
                # Send email via SMTP
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()  # Enable TLS
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
                
                print(f"✅ Status update email sent to {user_email}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error sending status update email to {user_email}: {str(e)}")
        
        print(f"📧 Status update emails: {success_count}/{total_count} sent successfully")
        return success_count == total_count
    
    def _create_assignment_notification_html(self, ticket_id: str, assigned_to: str, assigned_by: str, notes: str = None) -> str:
        """Create HTML content for assignment notification email"""
        html_content = f"""
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
        return html_content
    
    def _get_current_time(self) -> str:
        """Get current time formatted"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M %d-%m-%Y")
    
    async def send_assignment_notification(self, ticket_id: str, assigned_to: str, assigned_by: str, notes: str = None) -> bool:
        """
        Send assignment notification email
        
        Args:
            ticket_id: The ticket ID
            assigned_to: Worker email
            assigned_by: Authority email who assigned
            notes: Optional assignment notes
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            print(f"SMTP not configured. Skipping assignment notification for ticket {ticket_id}")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📋 New Assignment - Ticket {ticket_id}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = assigned_to
            
            # Create HTML content
            html_content = self._create_assignment_notification_html(ticket_id, assigned_to, assigned_by, notes)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Assignment notification sent successfully to {assigned_to}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending assignment notification to {assigned_to}: {str(e)}")
            return False

# Create global instance
email_service = EmailService()