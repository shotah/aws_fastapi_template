# Email Service Setup Guide

## AWS SES Configuration

### Step 1: Verify Email Address or Domain

You need to verify at least one email address to send from (or a domain for production).

#### Option A: Automated via CloudFormation (Recommended - Added June 2022)

In `template.yaml`, uncomment the `SESEmailIdentity` resource (lines 292-301):
- Automatically verifies email or domain on deployment
- If using a domain with Route53, also uncomment `SESRoute53DKIMRecords` (lines 305-324) for automatic DKIM setup
- Handles verification and DKIM configuration in one deployment

**Benefits:**
- ✅ Infrastructure as code
- ✅ Automated DKIM setup with Route53
- ✅ No manual verification steps
- ✅ Repeatable across environments

#### Option B: Verify Single Email Manually (Quick - Good for Dev/Testing)
```bash
aws ses verify-email-identity --email-address your-email@example.com
```
- Check your inbox and click the verification link
- This email can now be used as the `Source` in SES send operations

#### Option C: Verify Domain Manually (Production)
```bash
aws ses verify-domain-identity --domain example.com
```
- Add the verification TXT record to your DNS
- Optionally add DKIM records for better deliverability

### Step 2: Request Production Access (If Needed)

By default, SES starts in **sandbox mode**:
- ✅ Can send emails
- ❌ Can only send TO verified email addresses
- ❌ Limited to 200 emails/day

For production (send to any email):
```bash
# Request production access via AWS Console
# AWS Console > SES > Account dashboard > Request production access
```

### Step 3: Deploy Your Stack

```bash
make deploy ENV=dev
```

This will:
- Deploy Lambda with SES permissions
- Configure the midnight cron schedule (already set up)
- Lambda will run daily at 00:00 UTC

### Step 4: Configure Email Settings

Update your environment variables (in `env.json` for local, or Lambda environment):
```json
{
  "HelloWorldFunction": {
    "FROM_EMAIL": "your-verified-email@example.com",
    "ADMIN_EMAIL": "admin@example.com"
  }
}
```

### Step 5: Test Email Sending

#### Local Test
```bash
sam local invoke HelloWorldFunction --event events/scheduled_email.json
```

#### Remote Test (after deployment)
```bash
aws lambda invoke \
  --function-name YOUR-STACK-NAME-HelloWorldFunction-XXXX \
  --payload '{"source": "scheduled-event", "action": "send-emails"}' \
  response.json
```

## Email Service Usage

The email functionality is handled by the `EmailService` class in `src/services/email.py`.

### Basic Usage

```python
from services.email import get_email_service

# Get the email service
email_service = get_email_service()

# Send a simple templated email
email_service.send_templated_email(
    to_addresses=["user@example.com"],
    subject="Welcome!",
    title="Welcome to Our Service",
    body_content="<h2>Hello!</h2><p>Welcome to our platform.</p>"
)

# Send the default daily report
email_service.send_daily_report(
    to_addresses=["admin@example.com"]
)

# Send a custom daily report
custom_report = """
    <h2>Daily Metrics</h2>
    <ul>
        <li>Users: 150</li>
        <li>Revenue: $1,234</li>
    </ul>
"""
email_service.send_daily_report(
    to_addresses=["admin@example.com"],
    report_content=custom_report
)
```

### Email Templates

The base HTML template is stored in `src/services/email.py` in the `EmailService.BASE_EMAIL_TEMPLATE` constant.

To customize:
1. Edit the `BASE_EMAIL_TEMPLATE` in `src/services/email.py`
2. Modify the CSS styles, header, footer as needed
3. Use `{title}`, `{body}`, and `{environment}` placeholders
4. Deploy changes with `make deploy ENV=dev`

### Scheduled Emails

The `send_scheduled_emails()` function in `src/app.py` is called by the midnight cron.
- It uses `email_service.send_daily_report()`
- Customize by passing `report_content` parameter
- Add your own business logic before calling the service

## Monitoring

### CloudWatch Logs
```bash
# View Lambda logs
sam logs -n HelloWorldFunction --stack-name YOUR-STACK-NAME --tail
```

### SES Sending Statistics
```bash
# Check SES sending quota and stats
aws ses get-send-quota
aws ses get-send-statistics
```

### CloudWatch Metrics
- Monitor Lambda execution in CloudWatch
- Check SES sending metrics (bounces, complaints)

## Troubleshooting

### Email Not Sending
- ✅ Verify sender email is verified in SES
- ✅ Check you're in sandbox mode (can only send to verified recipients)
- ✅ Check Lambda logs for errors
- ✅ Verify IAM permissions (SESCrudPolicy in template.yaml)

### Email in Spam
- Add SPF record to your DNS
- Enable DKIM signing in SES
- Verify domain (not just email)
- Use proper email formatting

## Next Steps

- [ ] Verify sender email address in SES
- [ ] Test email sending locally
- [ ] Deploy stack with `make deploy ENV=dev`
- [ ] Test midnight cron trigger (or manually invoke)
- [ ] Request production access if needed
- [ ] Add proper email templates/formatting
- [ ] Monitor logs and metrics
