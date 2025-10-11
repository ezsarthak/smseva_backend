# SMTP Email Setup Guide for Municipal Voice Assistant API

This guide will help you set up SMTP-based email notifications using Gmail for your municipal voice assistant system.

## 🚀 What is SMTP?

SMTP (Simple Mail Transfer Protocol) is the standard protocol for sending emails. This solution uses Gmail's SMTP server to send emails directly from your backend, which is more reliable and secure than third-party services.

## 📋 Prerequisites

1. **Gmail Account**: A Gmail account for sending emails
2. **App Password**: A Gmail app password (not your regular password)
3. **Python Environment**: Your existing FastAPI backend

## 🔧 Step-by-Step Setup

### 1. Enable 2-Factor Authentication on Gmail

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Navigate to **Security**
3. Enable **2-Step Verification** if not already enabled

### 2. Generate Gmail App Password

1. **Go to Google Account Settings** → **Security**
2. Under **2-Step Verification**, click **App passwords**
3. Select **Mail** as the app and **Other** as the device
4. Click **Generate**
5. **Copy the 16-character password** (you'll need this for SMTP_PASSWORD)

### 3. Configure Environment Variables

Create a `.env` file in your project root with:

```env
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_character_app_password
FROM_EMAIL=your_email@gmail.com
FROM_NAME=Municipal Voice Assistant
```

**Important**: 
- Use your **Gmail address** for `SMTP_USERNAME` and `FROM_EMAIL`
- Use the **16-character app password** for `SMTP_PASSWORD` (NOT your regular Gmail password)
- The `FROM_NAME` can be customized to whatever you want

### 4. Test the Integration

1. Start your FastAPI server
2. Submit a test issue using the `/submit-issue` endpoint
3. Check your email for the confirmation
4. Update the issue status using `/issues/{ticket_id}/status`
5. Check for status update notifications

## 📧 Email Features

### **Ticket Confirmation Emails**
- Beautiful HTML formatting with professional styling
- Complete ticket details including ID, category, address, description
- Responsive design that works on all devices
- Clear status indicators and creation timestamps

### **Status Update Emails**
- Notifications when issue status changes
- Clear before/after status display
- Professional formatting with color-coded status indicators
- Sent to all users associated with the issue

## 🔍 Troubleshooting

### Common Issues:

1. **"Authentication failed" error**
   - Verify you're using the app password, not your regular Gmail password
   - Ensure 2-factor authentication is enabled
   - Check that the app password was generated correctly

2. **"SMTP not configured" warning**
   - Check all environment variables are set correctly
   - Verify the `.env` file is in the project root
   - Ensure SMTP_USERNAME and SMTP_PASSWORD are set

3. **"Connection refused" error**
   - Verify SMTP_SERVER is correct (smtp.gmail.com)
   - Check SMTP_PORT is 587
   - Ensure your firewall allows outbound connections on port 587

4. **Emails not received**
   - Check spam/junk folder
   - Verify email address in the request
   - Check Gmail's "Sent" folder to see if emails were sent

### Debug Steps:

1. **Check Environment Variables**:
   ```bash
   echo $SMTP_USERNAME
   echo $SMTP_PASSWORD
   echo $SMTP_SERVER
   echo $SMTP_PORT
   ```

2. **Test SMTP Connection**:
   ```bash
   telnet smtp.gmail.com 587
   ```

3. **Check Server Logs**:
   - Look for SMTP connection messages
   - Check for authentication success/failure
   - Monitor email sending attempts

## 🛡️ Security Features

- **TLS Encryption**: All emails are sent over encrypted connections
- **App Passwords**: Uses Gmail app passwords instead of account passwords
- **No Password Storage**: Passwords are only stored in environment variables
- **Rate Limiting**: Gmail has built-in rate limiting to prevent abuse

## 📊 Gmail Limits

Gmail has the following sending limits:
- **Regular Gmail**: 500 emails/day
- **Google Workspace**: 2000 emails/day
- **App Passwords**: Same limits as regular account

## 🚀 Production Considerations

1. **Environment Variables**: Use proper environment variable management in production
2. **Error Handling**: The system gracefully handles email failures
3. **Logging**: All email attempts are logged for debugging
4. **Fallback**: System continues to work even if emails fail
5. **Monitoring**: Monitor email delivery success rates

## 🔗 Alternative SMTP Providers

If you prefer not to use Gmail, you can use:

### **Outlook/Hotmail**:
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

### **Yahoo Mail**:
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

### **Custom SMTP Server**:
```env
SMTP_SERVER=your_smtp_server.com
SMTP_PORT=587
```

## 💡 Best Practices

1. **Use App Passwords**: Never use your main Gmail password
2. **Environment Variables**: Keep credentials secure in environment files
3. **Error Handling**: Always handle email failures gracefully
4. **Testing**: Test email functionality before deploying to production
5. **Monitoring**: Monitor email delivery rates and failures

## 📝 Support

If you encounter issues:

1. **Check Gmail Settings**: Ensure 2FA and app passwords are configured
2. **Verify Environment Variables**: Confirm all SMTP variables are set
3. **Check Server Logs**: Look for specific error messages
4. **Test SMTP Connection**: Verify connectivity to Gmail servers
5. **Review Gmail Limits**: Ensure you haven't exceeded daily sending limits

---

**Note**: This SMTP-based solution is more reliable and secure than third-party services, providing direct email delivery through Gmail's infrastructure while maintaining professional email formatting and delivery reliability.
