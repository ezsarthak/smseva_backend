import os
import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class TelerivetService:
    def __init__(self):
        """Initialize Telerivet service with credentials from environment"""
        self.api_key = os.getenv("TELERIVET_API_KEY")
        self.project_id = os.getenv("TELERIVET_PROJECT_ID")
        self.phone_id = os.getenv("TELERIVET_PHONE_ID")  # Optional: for specific phone
        self.webhook_secret = os.getenv("TELERIVET_WEBHOOK_SECRET")  # For webhook validation

        # Base URL for Telerivet API
        self.base_url = "https://api.telerivet.com/v1"

        # Check if Telerivet is configured
        self.is_configured = all([
            self.api_key,
            self.project_id
        ])

        if self.is_configured:
            logger.info("Telerivet service initialized successfully")
        else:
            logger.warning("Telerivet credentials not configured. SMS features will be disabled.")

    def send_sms(self, to_phone: str, message: str) -> bool:
        """
        Send an SMS message via Telerivet

        Args:
            to_phone: Recipient phone number (e.g., +1234567890)
            message: Message content

        Returns:
            bool: True if sent successfully, False otherwise
        """
        print(f"📤 send_sms called for: {to_phone}")
        print(f"   API Key present: {bool(self.api_key)}")
        print(f"   Project ID: {self.project_id}")
        print(f"   Phone ID: {self.phone_id}")
        print(f"   Configured: {self.is_configured}")

        if not self.is_configured:
            logger.warning("Cannot send SMS: Telerivet not configured")
            print("❌ Telerivet not configured!")
            return False

        try:
            url = f"{self.base_url}/projects/{self.project_id}/messages/send"
            print(f"📡 API URL: {url}")

            payload = {
                "to_number": to_phone,
                "content": message
            }

            # Add phone_id if configured (to send from specific number)
            if self.phone_id:
                payload["phone_id"] = self.phone_id

            print(f"📦 Payload: {payload}")

            response = requests.post(
                url,
                auth=(self.api_key, ''),  # Telerivet uses API key as username
                json=payload,
                timeout=10
            )

            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response body: {response.text}")

            if response.status_code == 200:
                result = response.json()
                message_id = result.get('id')
                message_status = result.get('status')

                logger.info(f"SMS sent successfully to {to_phone}. Message ID: {message_id}, Status: {message_status}")
                print(f"✅ SMS sent successfully! Message ID: {message_id}")
                print(f"📊 Message Status: {message_status}")
                print(f"⚠️ IMPORTANT: Message is '{message_status}' - Check Telerivet Android app to ensure it sends!")
                print(f"🔍 Track delivery: Check https://telerivet.com/p/{self.project_id}/messages/{message_id}")

                # Log details for debugging
                print(f"📱 Phone ID being used: {result.get('phone_id')}")
                print(f"📱 From number: {result.get('from_number')}")
                print(f"📱 To number: {result.get('to_number')}")
                print(f"⏰ Time created: {result.get('time_created')}")

                return True
            else:
                logger.error(f"Error sending SMS to {to_phone}: {response.status_code} - {response.text}")
                print(f"❌ SMS send failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception sending SMS to {to_phone}: {e}")
            print(f"❌ Exception sending SMS: {e}")
            return False

    def process_incoming_sms(self, webhook_data: Dict) -> Dict:
        """
        Process incoming SMS webhook data from Telerivet

        Args:
            webhook_data: Dictionary containing webhook data from Telerivet

        Returns:
            Dict containing extracted information
        """
        try:
            # Telerivet can send field names with different cases or variations
            # Try multiple field name variations
            from_phone = (
                webhook_data.get('from_number') or
                webhook_data.get('from') or
                webhook_data.get('sender') or
                ''
            )

            message_body = (
                webhook_data.get('content') or
                webhook_data.get('message') or
                webhook_data.get('text') or
                webhook_data.get('body') or
                ''
            )

            message_id = (
                webhook_data.get('id') or
                webhook_data.get('message_id') or
                ''
            )

            logger.info(f"Processing SMS from {from_phone}: {message_body}")

            # Strip whitespace from message
            if message_body:
                message_body = message_body.strip()

            result = {
                "phone": from_phone,
                "text": message_body,
                "message_id": message_id,
                "source": "sms"
            }

            return result

        except Exception as e:
            logger.error(f"Error processing incoming SMS: {e}")
            return {
                "phone": "",
                "text": "",
                "message_id": "",
                "source": "sms"
            }

    def validate_webhook_secret(self, request_secret: str) -> bool:
        """
        Validate webhook secret to ensure request is from Telerivet

        Args:
            request_secret: Secret from webhook request

        Returns:
            bool: True if valid, False otherwise
        """
        if not self.webhook_secret:
            # If no secret configured, skip validation (not recommended for production)
            logger.warning("Webhook secret not configured - skipping validation")
            return True

        return request_secret == self.webhook_secret

    async def send_ticket_confirmation_sms(
        self,
        phone: str,
        ticket_id: str,
        category: str,
        title: str = None,
        address: str = None,
        description: str = None
    ) -> bool:
        """
        Send SMS confirmation with ticket ID and details in English and Hindi

        Args:
            phone: Recipient phone number
            ticket_id: Generated ticket ID
            category: Issue category
            title: Issue title (optional)
            address: Issue address (optional)
            description: Issue description (optional)

        Returns:
            bool: True if sent successfully
        """
        # Import here to avoid circular import
        from .gemini_service import translate_to_hindi

        try:
            print("🌐 Translating issue details to Hindi...")

            # Translate to Hindi
            category_hi = await translate_to_hindi(category)
            title_hi = await translate_to_hindi(title) if title else ""
            address_hi = await translate_to_hindi(address) if address else ""
            description_hi = await translate_to_hindi(description) if description else ""

            print("✅ Translation complete")

            # Create bilingual message
            message_parts = [
                "✅ Issue Registered / मुद्दा दर्ज किया गया",
                "",
                f"🎫 Ticket ID: {ticket_id}",
                ""
            ]

            # Add title if available
            if title:
                message_parts.extend([
                    f"📌 Title / शीर्षक:",
                    f"EN: {title}",
                    f"HI: {title_hi}",
                    ""
                ])

            # Add category
            message_parts.extend([
                f"📂 Category / श्रेणी:",
                f"EN: {category}",
                f"HI: {category_hi}",
                ""
            ])

            # Add address if available
            if address:
                message_parts.extend([
                    f"📍 Location / स्थान:",
                    f"EN: {address}",
                    f"HI: {address_hi}",
                    ""
                ])

            # Add description if available
            if description:
                message_parts.extend([
                    f"📝 Description / विवरण:",
                    f"EN: {description}",
                    f"HI: {description_hi}",
                    ""
                ])

            # Add footer
            message_parts.extend([
                "We will process your request shortly.",
                "हम जल्द ही आपके अनुरोध पर कार्रवाई करेंगे।"
            ])

            message = "\n".join(message_parts)

            print(f"📨 SMS message length: {len(message)} characters")

            return self.send_sms(phone, message)

        except Exception as e:
            print(f"❌ Error creating bilingual message: {e}")
            logger.error(f"Error in send_ticket_confirmation_sms: {e}")

            # Fallback to simple English message
            simple_message = (
                f"✅ Issue Registered\n\n"
                f"Ticket ID: {ticket_id}\n"
                f"Category: {category}\n\n"
                f"We will process your request shortly."
            )
            return self.send_sms(phone, simple_message)

    def send_status_update_sms(self, phone: str, ticket_id: str, old_status: str, new_status: str) -> bool:
        """
        Send SMS notification about status update

        Args:
            phone: Recipient phone number
            ticket_id: Ticket ID
            old_status: Previous status
            new_status: New status

        Returns:
            bool: True if sent successfully
        """
        status_messages = {
            "new": "registered",
            "in_progress": "being worked on",
            "admin_completed": "completed by our team",
            "completed": "fully resolved"
        }

        new_status_text = status_messages.get(new_status, new_status)

        message = (
            f"Update on your issue (Ticket: {ticket_id}):\n\n"
            f"Status changed to: {new_status_text.upper()}\n\n"
            f"Thank you for your patience."
        )

        return self.send_sms(phone, message)

    async def send_status_update_sms_bilingual(self, phone: str, ticket_id: str, old_status: str, new_status: str) -> bool:
        """
        Send bilingual (English + Hindi) SMS notification about status update

        Args:
            phone: Recipient phone number
            ticket_id: Ticket ID
            old_status: Previous status
            new_status: New status

        Returns:
            bool: True if sent successfully
        """
        # Import here to avoid circular import
        from .gemini_service import translate_to_hindi

        try:
            print(f"📤 Sending bilingual status update SMS to {phone}")
            print(f"   Ticket: {ticket_id}, Status: {old_status} → {new_status}")

            # Status messages in English
            status_messages_en = {
                "new": "Registered",
                "in_progress": "In Progress - Work Started",
                "admin_completed": "Completed by Team",
                "completed": "Fully Resolved"
            }

            # Status messages in Hindi
            status_messages_hi = {
                "new": "पंजीकृत",
                "in_progress": "प्रगति में - कार्य शुरू",
                "admin_completed": "टीम द्वारा पूर्ण",
                "completed": "पूर्णतः हल"
            }

            status_text_en = status_messages_en.get(new_status, new_status)
            status_text_hi = status_messages_hi.get(new_status, await translate_to_hindi(new_status))

            # Create bilingual message
            message_parts = [
                "🔔 Status Update / स्थिति अपडेट",
                "",
                f"🎫 Ticket: {ticket_id}",
                "",
                f"📊 New Status / नई स्थिति:",
                f"EN: {status_text_en}",
                f"HI: {status_text_hi}",
                "",
            ]

            # Add specific message based on status
            if new_status == "in_progress":
                message_parts.extend([
                    "✅ Your issue is being worked on!",
                    "✅ आपके मुद्दे पर काम शुरू हो गया है!",
                    "",
                    "We will update you once completed.",
                    "पूर्ण होने पर हम आपको सूचित करेंगे।"
                ])
            elif new_status == "admin_completed":
                message_parts.extend([
                    "✅ Work completed by our team!",
                    "✅ हमारी टीम द्वारा कार्य पूर्ण किया गया!",
                    "",
                    "❓ Is the issue actually resolved?",
                    "❓ क्या समस्या वास्तव में हल हो गई है?",
                    "",
                    "Please reply:",
                    "कृपया जवाब दें:",
                    "✓ YES (हाँ) - Issue resolved",
                    "✗ NO (नहीं) - Issue not resolved",
                    "",
                    "Your feedback helps us serve you better!",
                    "आपकी प्रतिक्रिया हमें बेहतर सेवा देने में मदद करती है!"
                ])
            elif new_status == "completed":
                message_parts.extend([
                    "✅ Your issue has been resolved!",
                    "✅ आपका मुद्दा हल हो गया है!",
                    "",
                    "Thank you for your patience.",
                    "आपके धैर्य के लिए धन्यवाद।"
                ])
            else:
                message_parts.extend([
                    "Thank you for your patience.",
                    "आपके धैर्य के लिए धन्यवाद।"
                ])

            message = "\n".join(message_parts)

            print(f"📨 Bilingual SMS message length: {len(message)} characters")

            return self.send_sms(phone, message)

        except Exception as e:
            print(f"❌ Error creating bilingual status update message: {e}")
            logger.error(f"Error in send_status_update_sms_bilingual: {e}")

            # Fallback to simple bilingual message
            simple_message = (
                f"🔔 Status Update / स्थिति अपडेट\n\n"
                f"Ticket: {ticket_id}\n"
                f"New Status: {new_status}\n\n"
                f"Thank you for your patience.\n"
                f"आपके धैर्य के लिए धन्यवाद।"
            )
            return self.send_sms(phone, simple_message)

    async def send_issue_details_sms(self, phone: str, issue_data: dict) -> bool:
        """
        Send bilingual SMS with complete issue details

        Args:
            phone: Recipient phone number
            issue_data: Issue data dictionary containing all issue fields

        Returns:
            bool: True if sent successfully
        """
        from .gemini_service import translate_to_hindi

        try:
            print(f"📤 Sending issue details SMS to {phone}")
            print(f"   Ticket: {issue_data.get('ticket_id')}")

            ticket_id = issue_data.get('ticket_id', 'N/A')
            status = issue_data.get('status', 'unknown')
            category = issue_data.get('category', 'N/A')
            title = issue_data.get('title', 'N/A')
            description = issue_data.get('description', 'N/A')
            address = issue_data.get('address', 'N/A')
            created_at = issue_data.get('created_at', 'N/A')

            # Status messages in English and Hindi
            status_messages_en = {
                "new": "Registered - Pending Review",
                "in_progress": "In Progress - Work Started",
                "admin_completed": "Completed by Team",
                "completed": "Fully Resolved"
            }

            status_messages_hi = {
                "new": "पंजीकृत - समीक्षा लंबित",
                "in_progress": "प्रगति में - कार्य शुरू",
                "admin_completed": "टीम द्वारा पूर्ण",
                "completed": "पूर्णतः हल"
            }

            status_text_en = status_messages_en.get(status, status)
            status_text_hi = status_messages_hi.get(status, await translate_to_hindi(status))

            # Translate details to Hindi
            print("🌐 Translating issue details to Hindi...")
            category_hi = await translate_to_hindi(category)
            title_hi = await translate_to_hindi(title) if title != 'N/A' else 'N/A'
            description_hi = await translate_to_hindi(description) if description != 'N/A' else 'N/A'
            address_hi = await translate_to_hindi(address) if address != 'N/A' else 'N/A'
            print("✅ Translation complete")

            # Create bilingual message
            message_parts = [
                "📋 Issue Details / मुद्दे का विवरण",
                "",
                f"🎫 Ticket: {ticket_id}",
                "",
                f"📊 Status / स्थिति:",
                f"EN: {status_text_en}",
                f"HI: {status_text_hi}",
                "",
                f"📂 Category / श्रेणी:",
                f"EN: {category}",
                f"HI: {category_hi}",
                ""
            ]

            # Add title if available
            if title != 'N/A':
                message_parts.extend([
                    f"📌 Title / शीर्षक:",
                    f"EN: {title}",
                    f"HI: {title_hi}",
                    ""
                ])

            # Add location if available
            if address != 'N/A':
                message_parts.extend([
                    f"📍 Location / स्थान:",
                    f"EN: {address}",
                    f"HI: {address_hi}",
                    ""
                ])

            # Add description if available
            if description != 'N/A':
                message_parts.extend([
                    f"📝 Description / विवरण:",
                    f"EN: {description}",
                    f"HI: {description_hi}",
                    ""
                ])

            # Add created date
            message_parts.extend([
                f"📅 Created / बनाया गया: {created_at}",
                "",
                "Thank you for checking!",
                "जानकारी के लिए धन्यवाद!"
            ])

            message = "\n".join(message_parts)

            print(f"📨 Issue details SMS length: {len(message)} characters")

            return self.send_sms(phone, message)

        except Exception as e:
            print(f"❌ Error creating issue details SMS: {e}")
            logger.error(f"Error in send_issue_details_sms: {e}")

            # Fallback to simple bilingual message
            simple_message = (
                f"📋 Issue Details / मुद्दे का विवरण\n\n"
                f"Ticket: {issue_data.get('ticket_id', 'N/A')}\n"
                f"Status / स्थिति: {issue_data.get('status', 'N/A')}\n"
                f"Category / श्रेणी: {issue_data.get('category', 'N/A')}\n\n"
                f"Created / बनाया गया: {issue_data.get('created_at', 'N/A')}"
            )
            return self.send_sms(phone, simple_message)

    def get_message_details(self, message_id: str) -> Optional[Dict]:
        """
        Get details of a sent/received message

        Args:
            message_id: Telerivet message ID

        Returns:
            Dict with message details or None if error
        """
        if not self.is_configured:
            logger.warning("Cannot get message details: Telerivet not configured")
            return None

        try:
            url = f"{self.base_url}/projects/{self.project_id}/messages/{message_id}"

            response = requests.get(
                url,
                auth=(self.api_key, ''),
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting message details: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Exception getting message details: {e}")
            return None

    def reply_to_message(self, message_id: str, reply_text: str) -> bool:
        """
        Reply to an incoming message

        Args:
            message_id: ID of the message to reply to
            reply_text: Reply text

        Returns:
            bool: True if sent successfully
        """
        if not self.is_configured:
            logger.warning("Cannot reply to message: Telerivet not configured")
            return False

        try:
            # Get original message details to get sender's number
            message_details = self.get_message_details(message_id)
            if not message_details:
                return False

            from_number = message_details.get('from_number')
            if not from_number:
                logger.error("Could not extract sender number from message")
                return False

            # Send reply
            return self.send_sms(from_number, reply_text)

        except Exception as e:
            logger.error(f"Exception replying to message: {e}")
            return False

# Create a singleton instance
telerivet_service = TelerivetService()
