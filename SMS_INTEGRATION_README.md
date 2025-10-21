# SMS Integration - Quick Reference

This project supports **two SMS providers**:

1. **Twilio** - Fully managed, global SMS service
2. **Telerivet** - Use your own Android phone or virtual numbers

---

## Quick Decision Guide

### Choose Telerivet if:
- ✅ Operating in India, Africa, or regions where Twilio is restricted
- ✅ Want to use your existing phone number
- ✅ Have budget constraints
- ✅ Small to medium scale deployment
- ✅ Need lower per-SMS costs
- ✅ Can manage an Android phone connection

### Choose Twilio if:
- ✅ Need fully managed cloud service
- ✅ Operating primarily in US/Europe
- ✅ Require high scalability (100,000+ SMS/month)
- ✅ Want advanced features (MMS, WhatsApp, etc.)
- ✅ Prefer not to manage hardware

---

## Setup Guides

📘 **Telerivet Setup**: See [`TELERIVET_SETUP_GUIDE.md`](./TELERIVET_SETUP_GUIDE.md)

📗 **Twilio Setup**: See [`TWILIO_SETUP_GUIDE.md`](./TWILIO_SETUP_GUIDE.md)

---

## Quick Start - Telerivet (Recommended)

### 1. Create Account
Visit https://telerivet.com/ and sign up

### 2. Install Android App (Option A - Free)
- Install "Telerivet" from Google Play Store
- Log in and connect phone to your project
- Your existing SIM/number works!

### 3. Configure .env
```env
TELERIVET_API_KEY=your_api_key_here
TELERIVET_PROJECT_ID=your_project_id_here
TELERIVET_PHONE_ID=your_phone_id_here
TELERIVET_WEBHOOK_SECRET=random_secret_string
```

### 4. Set Webhook URL
- **Local Testing**: `https://your-ngrok-url.ngrok.io/telerivet/webhook`
- **Production**: `https://your-domain.com/telerivet/webhook`

### 5. Test
Send SMS to your phone number:
```
"Broken streetlight on Main Street"
```

You'll receive ticket ID instantly!

---

## Quick Start - Twilio (Alternative)

### 1. Create Account
Visit https://www.twilio.com/try-twilio

### 2. Buy Number
- Go to Console → Buy a Number
- Choose number with SMS capability

### 3. Configure .env
```env
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
```

### 4. Set Webhook URL
- **Local Testing**: `https://your-ngrok-url.ngrok.io/twilio/sms`
- **Production**: `https://your-domain.com/twilio/sms`

### 5. Test
Send SMS to your Twilio number

---

## API Endpoints

### Telerivet
```
POST /telerivet/webhook
Content-Type: application/json

Response Format: JSON
```

### Twilio
```
POST /twilio/sms
Content-Type: application/x-www-form-urlencoded

Response Format: TwiML (XML)
```

---

## Features Comparison

| Feature | Telerivet | Twilio |
|---------|-----------|--------|
| **Setup** | 15 min | 10 min |
| **Cost** | Free (Android) or $1-5/mo | $1-5/mo + per-SMS |
| **SMS Cost** | Carrier rates | $0.0075-0.02/SMS |
| **Countries** | 200+ | 200+ |
| **Own Number** | ✅ Yes (Android) | ❌ No |
| **Scalability** | Medium | Very High |
| **Reliability** | Phone-dependent | Very High |
| **Setup Complexity** | Medium | Low |
| **Best For** | Local/Regional | Global/Enterprise |

---

## Environment Variables

### Telerivet (Primary)
```env
TELERIVET_API_KEY=your_api_key_here
TELERIVET_PROJECT_ID=your_project_id_here
TELERIVET_PHONE_ID=your_phone_id_here
TELERIVET_WEBHOOK_SECRET=your_webhook_secret
```

### Twilio (Backup/Alternative)
```env
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
```

**Note**: You can configure both! The system will use whichever service receives the SMS.

---

## How Users Report Issues via SMS

### Step 1: User sends SMS
```
"Water leaking on Oak Street near the library"
```

### Step 2: System processes
- ✅ Receives SMS via webhook
- ✅ Uses Gemini AI to analyze
- ✅ Extracts category, location, description
- ✅ Creates issue in database
- ✅ Generates ticket ID

### Step 3: User receives confirmation
```
Thank you for reporting the issue!

Your ticket ID: TKT-17102025-A1B2C3D4
Category: Water & Drainage

We will process your request shortly.
```

### Step 4: Status updates
When admin updates status, user receives:
```
Update on your issue (Ticket: TKT-17102025-A1B2C3D4):

Status changed to: BEING WORKED ON

Thank you for your patience.
```

---

## Testing Locally

### 1. Start Server
```bash
python run.py
```

### 2. Start ngrok
```bash
ngrok http 5600
```

### 3. Update Webhook
Copy ngrok URL and update in:
- **Telerivet**: Dashboard → Services → Your Webhook
- **Twilio**: Console → Phone Numbers → Messaging Config

### 4. Send Test SMS
Send to your phone number and watch the magic! ✨

---

## Production Deployment

### Step 1: Deploy your app
Deploy to Render, Railway, Heroku, or your server

### Step 2: Get production URL
Example: `https://municipal-api.onrender.com`

### Step 3: Update webhooks
**Telerivet**:
```
https://municipal-api.onrender.com/telerivet/webhook
```

**Twilio**:
```
https://municipal-api.onrender.com/twilio/sms
```

### Step 4: Monitor
- Check logs regularly
- Monitor SMS delivery
- Track issue creation
- Set up alerts

---

## Code Examples

### Send SMS Manually (Telerivet)
```python
from app.telerivet_service import telerivet_service

telerivet_service.send_sms(
    to_phone="+1234567890",
    message="Your issue has been resolved!"
)
```

### Send SMS Manually (Twilio)
```python
from app.twilio_service import twilio_service

twilio_service.send_sms(
    to_phone="+1234567890",
    message="Your issue has been resolved!"
)
```

### Send Status Update
```python
# Automatically called when status changes
telerivet_service.send_status_update_sms(
    phone="+1234567890",
    ticket_id="TKT-123",
    old_status="new",
    new_status="in_progress"
)
```

---

## Troubleshooting

### Webhook not receiving messages?

**Telerivet**:
- Check Android phone is online
- Verify Telerivet app is running
- Check webhook is enabled for phone
- Test webhook URL with curl

**Twilio**:
- Verify webhook URL is correct
- Check Twilio debugger logs
- Ensure server is accessible

### SMS not sending?

**Telerivet**:
- Check API key is valid
- Verify phone has connectivity
- Check carrier has SMS enabled
- Review Telerivet logs

**Twilio**:
- Check account has credits
- Verify phone number is valid
- Review Twilio console logs

### Issue not created?

- Check FastAPI logs for errors
- Verify Gemini API key is valid
- Test `/submit-issue` endpoint manually
- Check database connection

---

## File Structure

```
app/
├── telerivet_service.py    # Telerivet SMS service
├── twilio_service.py       # Twilio SMS service
├── main.py                 # API endpoints
│   ├── POST /telerivet/webhook
│   └── POST /twilio/sms
└── ...

TELERIVET_SETUP_GUIDE.md   # Complete Telerivet guide
TWILIO_SETUP_GUIDE.md       # Complete Twilio guide
SMS_INTEGRATION_README.md   # This file
.env                        # Configuration
```

---

## Security Best Practices

### 1. Webhook Validation
Always validate webhook secrets in production:

```python
# Telerivet validates automatically
if not telerivet_service.validate_webhook_secret(secret):
    raise HTTPException(status_code=401)
```

### 2. Rate Limiting
Prevent abuse:
```python
# Add rate limiting middleware
# Limit: 10 SMS per phone number per hour
```

### 3. Environment Variables
Never commit credentials:
```bash
# .gitignore
.env
*.env
```

### 4. HTTPS Only
Always use HTTPS in production:
```
✅ https://your-api.com/telerivet/webhook
❌ http://your-api.com/telerivet/webhook
```

---

## Cost Estimation

### Small Scale (100 SMS/month)
**Telerivet (Android)**: ~$0 (carrier plan)
**Telerivet (Virtual)**: ~$5-10
**Twilio**: ~$2-5

### Medium Scale (1,000 SMS/month)
**Telerivet (Android)**: ~$0-10 (carrier plan)
**Telerivet (Virtual)**: ~$20-50
**Twilio**: ~$10-30

### Large Scale (10,000 SMS/month)
**Telerivet**: ~$100-200
**Twilio**: ~$100-300

*Costs vary by country and carrier*

---

## Recommended Setup

### For Testing/Development:
- ✅ Use Telerivet with Android phone
- ✅ Use ngrok for webhooks
- ✅ Test with personal phone number
- ✅ Monitor logs carefully

### For Small Production:
- ✅ Telerivet Android (dedicated phone)
- ✅ Deploy to Render/Railway
- ✅ Use custom domain
- ✅ Enable webhook secret validation

### For Large Production:
- ✅ Twilio or Telerivet Virtual Numbers
- ✅ Deploy to scalable infrastructure
- ✅ Implement rate limiting
- ✅ Set up monitoring and alerts
- ✅ Use CDN/caching

---

## Support

**Telerivet Issues**: Check `TELERIVET_SETUP_GUIDE.md` troubleshooting section

**Twilio Issues**: Check `TWILIO_SETUP_GUIDE.md` troubleshooting section

**API Issues**: Check FastAPI logs with `python run.py`

**Database Issues**: Verify MongoDB connection in `.env`

---

## Next Steps

1. ✅ Choose SMS provider (Telerivet or Twilio)
2. ✅ Follow setup guide
3. ✅ Configure environment variables
4. ✅ Test locally with ngrok
5. ✅ Deploy to production
6. ✅ Update webhook URLs
7. ✅ Monitor and iterate

---

## Example Test Scenarios

Send these SMS to test:

1. **Road Issue**:
   ```
   "Large pothole on Highway 23 near the gas station causing accidents"
   ```
   Expected: Category = "Roads & Transport"

2. **Water Issue**:
   ```
   "Water pipe burst on Elm Street flooding the road"
   ```
   Expected: Category = "Water & Drainage"

3. **Electricity Issue**:
   ```
   "Street lights not working on Baker Street for 3 days"
   ```
   Expected: Category = "Electricity & Streetlights"

4. **Sanitation Issue**:
   ```
   "Garbage collection missed for one week on Pine Avenue"
   ```
   Expected: Category = "Sanitation & Waste"

All should generate ticket IDs and create issues in database!

---

**Congratulations!** 🎉 Your SMS integration is ready to receive citizen complaints via text message!
