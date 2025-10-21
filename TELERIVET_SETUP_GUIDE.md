# Telerivet SMS Integration Guide

## Overview
This guide will help you integrate Telerivet SMS functionality into your Municipal Voice Assistant API. Telerivet is ideal for international SMS, works with Android phones, and supports many countries where Twilio might not be available.

**Key Advantages of Telerivet:**
- Works with any Android phone (no need to buy special numbers)
- Lower costs for international SMS
- Available in countries where Twilio is not supported
- Can use your existing SIM card and phone number
- Great for local/regional deployments

---

## Part 1: Telerivet Console Setup

### Step 1: Create a Telerivet Account
1. Visit https://telerivet.com/
2. Click **Sign Up** (top right)
3. Create your account (free trial available)
4. Verify your email address
5. Log in to your Telerivet Dashboard

### Step 2: Create a New Project
1. After login, you'll be at the **Projects** page
2. Click **Create New Project**
3. Enter:
   - **Project Name**: Municipal Voice Assistant
   - **Description**: SMS-based issue reporting system
4. Click **Create Project**
5. **Copy and save your Project ID** (found in the project settings/URL)

### Step 3: Get Your API Key
1. In your project dashboard, click your **profile icon** (top right)
2. Go to **API Keys**
3. Click **Create API Key**
4. Give it a name: "Municipal API"
5. **Copy and save the API Key** (looks like: `xxxxxxxxxxxxxxxxxxxxx`)
6. Keep this secure - it won't be shown again!

### Step 4: Add a Phone Number

You have **two options** for phone numbers with Telerivet:

#### Option A: Use Your Own Android Phone (Recommended for Testing)

1. **Install Telerivet Android App:**
   - On your Android phone, go to Google Play Store
   - Search for "Telerivet"
   - Install **Telerivet** app
   - Open the app

2. **Connect Your Phone:**
   - In the app, click **Sign In**
   - Log in with your Telerivet account
   - Click **Add Phone to Project**
   - Select your project (Municipal Voice Assistant)
   - Grant necessary permissions (SMS, Phone)
   - Your phone will now appear in the dashboard

3. **Get Phone ID:**
   - In Telerivet web dashboard, go to **Phones**
   - Click on your connected phone
   - **Copy the Phone ID** (looks like: `PN123456789abcdef`)

#### Option B: Purchase a Virtual Number

1. In dashboard, go to **Phones** → **Add Phone**
2. Choose **Virtual Number**
3. Select country and number
4. Complete purchase
5. Copy the Phone ID

### Step 5: Configure Environment Variables
1. Open your `.env` file
2. Add your Telerivet credentials:

```env
# Replace with your actual credentials
TELERIVET_API_KEY=your_api_key_from_step_3
TELERIVET_PROJECT_ID=your_project_id_from_step_2
TELERIVET_PHONE_ID=your_phone_id_from_step_4
TELERIVET_WEBHOOK_SECRET=create_a_random_secret_here
```

**For webhook secret**, generate a random string:
```bash
# Linux/Mac
openssl rand -hex 32

# Or just use a strong password
TELERIVET_WEBHOOK_SECRET=MySecretKey12345!@#
```

### Step 6: Install Dependencies
```bash
pip install -r requirements.txt
```
(No additional packages needed - `requests` is already included)

---

## Part 2: Testing Locally with ngrok

Since Telerivet needs a public URL to send webhooks, you'll need **ngrok** for local testing.

### Step 1: Install ngrok
1. Download ngrok: https://ngrok.com/download
2. Extract and install
3. Sign up: https://dashboard.ngrok.com/signup
4. Get authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
5. Configure:
```bash
ngrok authtoken YOUR_AUTHTOKEN
```

### Step 2: Start Your FastAPI Server
```bash
python run.py
```
Server runs on `http://localhost:5600`

### Step 3: Start ngrok Tunnel
In a new terminal:
```bash
ngrok http 5600
```

Output will show:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:5600
```

Copy the `https://abc123.ngrok.io` URL.

### Step 4: Configure Telerivet Webhook

1. Go to **Telerivet Dashboard** → **Services**
2. Click **Add Service** → **Webhook**
3. Configure:
   - **Service Name**: Issue Reporter Webhook
   - **Active**: ✓ (checked)
   - **Trigger**: When message is received
   - **Webhook URL**: `https://abc123.ngrok.io/telerivet/webhook`
   - **HTTP Method**: POST
   - **Secret**: (paste your webhook secret from .env)
4. Click **Save**

5. **Connect webhook to your phone:**
   - Go to **Phones** → Click your phone
   - Go to **Services** tab
   - Enable your webhook service

### Step 5: Test SMS

#### If using Android phone:
1. Send SMS **to your Android phone number** (the one running Telerivet app)
2. Message example: "There is a pothole on Main Street near the traffic light."
3. You should receive:
   - Issue created in database
   - Automatic SMS reply with ticket ID
   - Confirmation visible in Telerivet dashboard

#### Important Notes:
- When using Android phone, people send SMS **TO your phone number**
- The Telerivet app forwards messages to your webhook
- Your phone must be online and connected to internet
- SMS replies are sent from your phone number

---

## Part 3: Deploy to Production

### Production Setup (Without ngrok)

1. **Deploy your FastAPI application** to:
   - Render: https://render.com
   - Railway: https://railway.app
   - Heroku: https://heroku.com
   - Your own server with domain

2. **Get your production URL**
   - Example: `https://your-app.onrender.com`

3. **Update Telerivet webhook:**
   - Go to **Services** → Edit your webhook
   - Change URL to: `https://your-app.onrender.com/telerivet/webhook`
   - Save

4. **Keep your Android phone online** (if using Option A)
   - Phone should remain connected to internet
   - Telerivet app should run in background
   - Or consider using a dedicated device

---

## How It Works

### SMS Flow

```
User sends SMS
    ↓
Your Telerivet Phone Number
    ↓
Telerivet App (if Android) / Telerivet Cloud (if virtual)
    ↓
Telerivet sends webhook POST to your API
    ↓
Your API /telerivet/webhook endpoint
    ↓
• Validates webhook secret
• Extracts SMS content
• Uses Gemini AI to analyze
• Creates issue in database
• Generates ticket ID
    ↓
Sends confirmation SMS back
    ↓
User receives ticket ID
```

### Webhook Data Format

Telerivet sends JSON data:
```json
{
  "event": "incoming_message",
  "id": "MSG123456",
  "from_number": "+1234567890",
  "to_number": "+9876543210",
  "content": "Broken streetlight on Baker Street",
  "time_created": 1697123456,
  "secret": "your_webhook_secret"
}
```

---

## API Endpoint Details

### POST `/telerivet/webhook`
Receives incoming SMS from Telerivet.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body (from Telerivet):**
```json
{
  "event": "incoming_message",
  "id": "MSG123",
  "from_number": "+1234567890",
  "content": "Issue description",
  "secret": "your_secret"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Issue created",
  "ticket_id": "TKT-17102025-ABC123",
  "category": "Roads & Transport"
}
```

---

## Status Update Notifications

When admin updates issue status, users receive SMS:

```
Update on your issue (Ticket: TKT-17102025-ABC123):

Status changed to: BEING WORKED ON

Thank you for your patience.
```

---

## Testing Checklist

- [ ] Telerivet account created
- [ ] Project created and Project ID copied
- [ ] API Key generated and saved
- [ ] Phone added (Android app or virtual number)
- [ ] Phone ID copied
- [ ] Credentials added to `.env`
- [ ] Dependencies installed
- [ ] FastAPI server running
- [ ] ngrok tunnel active (for testing)
- [ ] Webhook service created in Telerivet
- [ ] Webhook connected to phone
- [ ] Test SMS sent
- [ ] Issue created in database
- [ ] Auto-reply SMS received

---

## Troubleshooting

### Issue: Webhook not receiving messages
**Solutions:**
- Check Android phone has internet connection
- Verify Telerivet app is running and not killed by battery optimization
- Check webhook service is enabled for your phone
- Verify ngrok is running with correct URL
- Check FastAPI logs for errors

### Issue: No auto-reply SMS
**Solutions:**
- Check API key is correct in `.env`
- Verify phone has SMS credits (Android: carrier plan, Virtual: Telerivet credits)
- Check logs for API errors
- Verify `send_sms` function is being called

### Issue: Webhook secret validation failing
**Solutions:**
- Ensure secret in `.env` matches secret in Telerivet webhook config
- Check there are no extra spaces in secret
- Try removing secret validation temporarily for testing

### Issue: Android phone goes offline
**Solutions:**
- Disable battery optimization for Telerivet app:
  - Settings → Apps → Telerivet → Battery → Unrestricted
- Keep phone charging and connected to WiFi
- Consider using a dedicated phone for production

### Issue: International SMS not working
**Solutions:**
- Ensure phone numbers include country code (e.g., +91 for India)
- Check your carrier/virtual number supports international SMS
- Verify sender has international SMS enabled

---

## Cost Comparison

### Telerivet Pricing (as of 2024):
- **Android Phone**: FREE (uses your SIM card/carrier plan)
- **Virtual Numbers**: Varies by country ($1-5/month + per-SMS)
- **API Usage**: FREE for basic use
- **Messages**: Depends on carrier (Android) or country rates (Virtual)

### When to Use Telerivet vs Twilio:
- **Use Telerivet if:**
  - Operating in countries where Twilio is restricted
  - Want to use your own phone number
  - Budget constraints
  - Local/regional deployment
  - Need lower per-SMS costs

- **Use Twilio if:**
  - Need high scalability
  - Want fully managed service
  - Require advanced features (MMS, etc.)
  - Operating in US/Europe primarily

---

## Production Best Practices

### 1. Use Dedicated Phone (Android Option)
- Don't use personal phone
- Get a dedicated Android phone
- Keep it plugged in and online 24/7
- Regular monitoring

### 2. Security
- **Always use webhook secret validation** in production
- Don't commit secrets to git
- Use environment variables
- Rotate API keys periodically

### 3. Monitoring
- Set up logging for all webhook calls
- Monitor phone connectivity (Android)
- Track SMS delivery status
- Set up alerts for failures

### 4. Rate Limiting
- Implement rate limiting to prevent abuse
- Track and limit messages per phone number
- Add cooldown periods

### 5. Message Validation
- Validate phone number format
- Check message length
- Filter spam/test messages
- Implement profanity filtering

### 6. Backup
- Configure multiple phones for redundancy
- Have backup virtual number ready
- Document all phone configurations

---

## Advanced Features

### 1. Send SMS Programmatically

```python
from app.telerivet_service import telerivet_service

# Send custom SMS
telerivet_service.send_sms(
    to_phone="+1234567890",
    message="Your issue has been resolved!"
)
```

### 2. Check Message Status

```python
# Get message details
message_details = telerivet_service.get_message_details("MSG123")
print(message_details)
```

### 3. Reply to Specific Message

```python
# Reply to incoming message
telerivet_service.reply_to_message(
    message_id="MSG123",
    reply_text="Thank you for reporting!"
)
```

---

## Support Resources

- **Telerivet Docs**: https://telerivet.com/api
- **Telerivet Support**: https://telerivet.com/help
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **ngrok Docs**: https://ngrok.com/docs

---

## Example Messages to Test

Send these to your Telerivet number:

1. "Streetlight not working on Baker Street near the park"
2. "Water leakage from pipe on 123 Main Street"
3. "Garbage bins overflowing at Market Square"
4. "Pothole on Highway 5 causing traffic issues"
5. "Stray dogs in residential area near school"

Each creates a properly categorized issue with ticket ID!

---

## Comparison: Android Phone vs Virtual Number

| Feature | Android Phone | Virtual Number |
|---------|--------------|----------------|
| Setup Cost | FREE (use existing phone) | $1-5/month |
| SMS Cost | Your carrier plan | Per-SMS billing |
| Requirements | Android phone + internet | Internet only |
| Reliability | Depends on phone/internet | High (cloud-based) |
| Scalability | Limited (1 phone) | High (multiple numbers) |
| Maintenance | Keep phone online | None |
| Best For | Testing, small scale | Production, large scale |

---

## Migration from Twilio

If you're switching from Twilio:

1. **Both can coexist** - You can keep both integrations active
2. **Twilio endpoint**: `/twilio/sms` (Form data)
3. **Telerivet endpoint**: `/telerivet/webhook` (JSON data)
4. **Choose one** based on your region and requirements
5. **To disable Twilio**: Don't configure Twilio credentials in .env

---

## Quick Start Summary

```bash
# 1. Set up Telerivet account
# 2. Add phone (Android app or virtual)
# 3. Configure .env
TELERIVET_API_KEY=your_key
TELERIVET_PROJECT_ID=your_project_id
TELERIVET_PHONE_ID=your_phone_id
TELERIVET_WEBHOOK_SECRET=your_secret

# 4. Start server
python run.py

# 5. Start ngrok
ngrok http 5600

# 6. Configure webhook in Telerivet
# URL: https://your-ngrok-url.ngrok.io/telerivet/webhook

# 7. Test by sending SMS to your number!
```

---

## Need Help?

Common issues and solutions are in the **Troubleshooting** section above. For additional help:
- Check Telerivet dashboard logs
- Review FastAPI application logs
- Test webhook URL manually using curl
- Contact Telerivet support for API issues

Happy SMS integration! 🚀
