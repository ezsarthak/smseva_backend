# Telerivet SMS Troubleshooting Guide

## Problem: SMS Received but No Reply Sent

If you're experiencing issues where:
- SMS messages sent via Telerivet dashboard test feature work fine
- SMS messages sent from actual phone to Telerivet-connected Android device are received
- Issues are created in the database
- But SMS replies are not being delivered back to the sender

### Root Cause Analysis

Based on the logs you provided, the API is working correctly:
- Webhooks are receiving messages successfully
- Issues are being created in database
- API calls to Telerivet show status 200 (success)
- Messages show "status": "queued" which means Telerivet accepted them for delivery

**The issue is likely with the Telerivet Android app not actually sending the queued SMS messages.**

---

## Troubleshooting Steps

### 1. Check Telerivet Android App Status

#### A. Ensure App is Running
```
- Open the Telerivet app on your Android phone
- Check if it shows "Connected" status
- If it shows "Disconnected", tap to reconnect
```

#### B. Check Background Permissions
The Telerivet app must be allowed to run in the background:

**For most Android phones:**
1. Go to Settings > Apps > Telerivet
2. Battery > Battery optimization
3. Select "Don't optimize" or "Unrestricted"

**For Samsung phones:**
1. Settings > Apps > Telerivet > Battery
2. Turn off "Put app to sleep"
3. Allow background activity

**For Xiaomi/MIUI:**
1. Settings > Apps > Manage apps > Telerivet
2. Battery saver > No restrictions
3. Autostart > Enable

**For Huawei/EMUI:**
1. Settings > Apps > Apps > Telerivet
2. App launch > Manage manually
3. Enable all three options (Auto-launch, Secondary launch, Run in background)

#### C. Check SMS Permissions
1. Settings > Apps > Telerivet > Permissions
2. Ensure SMS permission is set to "Allow"
3. Enable "Set as default SMS app" if prompted

### 2. Check Phone Carrier/Network Issues

#### A. SMS Balance
```
- Ensure the Android phone has sufficient SMS balance
- Try manually sending an SMS to verify carrier service works
```

#### B. Network Signal
```
- Check if phone has good cellular signal
- Try moving to area with better signal
- Restart phone if signal is weak
```

#### C. Carrier Restrictions
```
- Some carriers block automated SMS sending
- Check with carrier if bulk/automated SMS is allowed
- Consider using a dedicated business SMS plan
```

### 3. Check Telerivet Dashboard Configuration

#### A. Phone Status
1. Log into https://telerivet.com
2. Go to "Phones" section
3. Check your connected phone status:
   - Should show "Connected" in green
   - Last seen time should be recent (within last few minutes)
   - Battery level should be visible

#### B. Webhook Configuration
1. Go to Phones > [Your Phone] > Services
2. Verify webhook URL is correct:
   ```
   https://your-api-domain.com/telerivet/webhook
   ```
3. Check webhook secret matches your .env file

#### C. Message Logs
1. Go to "Messages" tab in Telerivet dashboard
2. Filter by "Outgoing" messages
3. Check status of recent messages:
   - **Queued**: Waiting to be sent by Android app
   - **Sent**: Successfully sent from phone
   - **Delivered**: Confirmed delivered to recipient
   - **Failed**: Error occurred (check error message)

### 4. Debug Using Telerivet App Logs

#### View Logs in Android App
1. Open Telerivet app
2. Tap menu (three lines) > View Logs
3. Look for errors related to sending messages
4. Common errors:
   - "SMS send failed: Generic failure" - Phone issue
   - "No SMS permission" - Permission issue
   - "Default SMS app required" - Set as default SMS app

#### Enable Verbose Logging
1. In Telerivet app, go to Settings
2. Enable "Verbose logging"
3. Try sending another test message
4. Check logs for detailed error information

### 5. Test Methodology

#### Progressive Testing:
```bash
# Test 1: Test via Telerivet Dashboard
1. Go to Telerivet dashboard > Messages
2. Click "Send Message"
3. Enter test number and message
4. Check if SMS is delivered
   ✅ If works: Android app is functional
   ❌ If fails: Check phone/carrier issues

# Test 2: Test API Directly
1. Send SMS via your API:
   curl -X POST https://your-api.com/test-sms
2. Check Telerivet dashboard > Messages
3. Verify message appears as "Queued"
   ✅ If queued: API to Telerivet connection works
   ❌ If not queued: Check API credentials

# Test 3: Monitor Delivery Status
1. Configure delivery status webhook:
   URL: https://your-api.com/telerivet/delivery_status
2. In Telerivet: Phones > [Your Phone] > Services
3. Add webhook for "Message Status Events"
4. Send test SMS and watch webhook logs
   ✅ If webhook receives "sent" or "delivered": Success
   ❌ If stuck on "queued": Android app issue
```

### 6. Common Issues and Solutions

#### Issue: Messages Stuck in "Queued" Status
**Solution:**
- Force stop Telerivet app and restart it
- Check if phone has internet connection
- Verify app has SMS permissions
- Ensure phone is not in airplane mode

#### Issue: "Invalid recipient phone number" Error
**Solution:**
- Ensure phone numbers include country code (e.g., +917447417740)
- Remove any spaces or special characters
- Verify number format matches E.164 standard

#### Issue: Messages Sent from Dashboard Work, but Not from Webhook
**Solution:**
- Check webhook authentication (secret key)
- Verify webhook URL is publicly accessible
- Test webhook with tools like webhook.site
- Check firewall/security group settings

#### Issue: High Message Delays
**Solution:**
- Android phone may be in battery saving mode
- Disable battery optimization for Telerivet app
- Keep phone plugged in and screen on during testing
- Check for pending Android system updates

### 7. Advanced Diagnostics

#### Check Android System Logs
If you have ADB (Android Debug Bridge) access:
```bash
# Connect phone to computer
adb logcat | grep -i telerivet

# Look for SMS-related errors
adb logcat | grep -i sms
```

#### Monitor Network Traffic
```bash
# Check if Android app is making API calls to Telerivet servers
adb shell tcpdump -i any -s 0 -w /sdcard/telerivet.pcap

# Analyze traffic to see if messages are being sent
```

### 8. Recommended Configuration for Production

```env
# Keep-Alive Settings
- Enable "Keep service alive" in Telerivet app settings
- Set up automatic restart on boot
- Use a dedicated phone for Telerivet (not daily driver)

# Phone Settings
- Keep phone plugged in 24/7
- Disable auto-updates
- Disable battery optimization for Telerivet
- Use stable WiFi connection as backup

# Monitoring
- Set up delivery status webhooks
- Monitor phone battery and connectivity
- Set up alerts for phone disconnections
```

### 9. Alternative Solutions

If Android app issues persist:

#### Option A: Use Telerivet Gateway (Recommended for Production)
- More reliable than Android app
- No phone hardware required
- Better for high-volume SMS
- Contact Telerivet support for gateway access

#### Option B: Switch to Twilio
- More reliable infrastructure
- Better documentation and support
- Higher cost but better uptime
- Your code already has Twilio integration

#### Option C: Use Multiple Phones
- Set up redundancy with 2-3 phones
- Telerivet can route between them
- Increases reliability

---

## Quick Diagnostic Checklist

Use this checklist to quickly identify issues:

- [ ] Telerivet app shows "Connected" status
- [ ] Phone has cellular signal and SMS balance
- [ ] Battery optimization is disabled for Telerivet app
- [ ] Telerivet has SMS permissions enabled
- [ ] Phone internet connection is stable
- [ ] Telerivet dashboard shows phone as "Connected"
- [ ] Webhook URL is correct and publicly accessible
- [ ] Test message from dashboard works
- [ ] API credentials (API key, Project ID) are correct
- [ ] Phone is not in battery saver mode
- [ ] No pending app updates for Telerivet
- [ ] Android system is up to date
- [ ] Carrier allows automated SMS sending

---

## Getting Help

If issues persist after following this guide:

1. **Telerivet Support:**
   - Email: support@telerivet.com
   - Include phone ID, message IDs, and error logs
   - Response time: Usually 24-48 hours

2. **Check Status Page:**
   - Visit: https://status.telerivet.com
   - Verify no ongoing service outages

3. **Community Forum:**
   - Search Telerivet community forums
   - Check for similar issues and solutions

4. **Contact Your Carrier:**
   - Verify SMS sending limits
   - Ask about automated SMS policies
   - Consider business SMS plans

---

## Monitoring Your Setup

### Set Up Delivery Status Webhook

Add this to your Telerivet dashboard:

**Webhook URL:**
```
https://your-api-domain.com/telerivet/delivery_status
```

**Event:** Message Status Events

This will help you track:
- When messages are queued
- When messages are sent from phone
- When messages are delivered
- When messages fail and why

### Check Logs Regularly

Monitor your application logs for:
```bash
# Successful deliveries
✅ SMS DELIVERED: Message XXX to +917447417740

# Failures
❌ SMS DELIVERY FAILED: Invalid recipient (Code: -9001)

# Queued messages (investigate if stuck)
📤 SMS QUEUED: Message XXX to +917447417740
```

---

## Next Steps

Based on your current situation:

1. **Immediate Action:**
   - Check Telerivet Android app status (is it connected?)
   - Verify battery optimization is disabled
   - Check if phone has SMS balance

2. **Testing:**
   - Send manual SMS from the phone to verify carrier works
   - Send test message via Telerivet dashboard
   - Configure delivery status webhook

3. **Monitoring:**
   - Watch delivery status webhook logs
   - Check Telerivet dashboard message status
   - Monitor Android app logs

4. **Long-term:**
   - Consider Telerivet gateway for production
   - Set up redundancy with multiple phones
   - Implement retry logic for failed messages

---

**Last Updated:** October 2025
**API Version:** 1.0.0
**Telerivet Android App:** Latest
