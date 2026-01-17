import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# SMS configuration - using Twilio or AWS SNS
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'twilio')  # 'twilio' or 'aws'
SMS_ACCOUNT_SID = os.getenv('SMS_ACCOUNT_SID', '')
SMS_AUTH_TOKEN = os.getenv('SMS_AUTH_TOKEN', '')
SMS_PHONE_NUMBER = os.getenv('SMS_PHONE_NUMBER', '')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY', '')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# SMS templates (limited to 160 characters for SMS standard)
SMS_TEMPLATES = {
    'payment_due': "Hi {name}! Your fitness club membership expires in {days} days. Renew now to stay active! Visit: @fitness_club_bot /payment_status",
    'membership_expired': "Hi {name}, your membership expired on {expiry_date}. Renew now to regain access! @fitness_club_bot /payment_status",
    'points_awarded': "Great job {name}! You earned {points} points for {activity}. Total: {total_points} pts! 🎉 @fitness_club_bot",
    'achievement_unlocked': "Congrats {name}! You unlocked: {achievement}! Reward: {reward} points! 🏆 @fitness_club_bot",
    'challenge_reminder': "{name}, your challenge deadline is in {days_remaining} days! Progress: {progress}. Don't miss it! @fitness_club_bot",
    'daily_reminder': "Hi {name}! Log your activities today to stay on track. Visit @fitness_club_bot /menu 💪"
}

def validate_phone_number(phone_number):
    """Validate phone number format (Indian format)"""
    if not phone_number:
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone_number)
    
    # Check if it's a valid Indian phone number (10 digits)
    if re.match(r'^(\+91|91)?[6-9]\d{9}$', cleaned):
        return True
    
    logger.warning(f"Invalid phone number format: {phone_number}")
    return False

def format_phone_number(phone_number):
    """Format phone number to international format"""
    if not phone_number:
        return None
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone_number)
    
    # If starts with 91 or +91, keep it
    if cleaned.startswith('91'):
        return f"+{cleaned}"
    
    if cleaned.startswith('+91'):
        return cleaned
    
    # If 10 digits, assume Indian and add +91
    if len(cleaned) == 10 and cleaned[0] in '6789':
        return f"+91{cleaned}"
    
    return None

def send_sms_twilio(phone_number, message):
    """Send SMS using Twilio"""
    try:
        if not SMS_ACCOUNT_SID or not SMS_AUTH_TOKEN or not SMS_PHONE_NUMBER:
            logger.warning("Twilio credentials not configured")
            return False
        
        # Import Twilio only if configured
        from twilio.rest import Client
        
        client = Client(SMS_ACCOUNT_SID, SMS_AUTH_TOKEN)
        
        message_obj = client.messages.create(
            body=message,
            from_=SMS_PHONE_NUMBER,
            to=phone_number
        )
        
        logger.info(f"SMS sent via Twilio to {phone_number}: {message_obj.sid}")
        return True
        
    except ImportError:
        logger.warning("Twilio library not installed - install with: pip install twilio")
        return False
    except Exception as e:
        logger.error(f"Error sending SMS via Twilio: {str(e)}")
        return False

def send_sms_aws(phone_number, message):
    """Send SMS using AWS SNS"""
    try:
        if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
            logger.warning("AWS credentials not configured")
            return False
        
        # Import boto3 only if configured
        import boto3
        
        client = boto3.client(
            'sns',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        response = client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': 'FitnessClub'
                },
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        
        logger.info(f"SMS sent via AWS SNS to {phone_number}: {response['MessageId']}")
        return True
        
    except ImportError:
        logger.warning("boto3 library not installed - install with: pip install boto3")
        return False
    except Exception as e:
        logger.error(f"Error sending SMS via AWS SNS: {str(e)}")
        return False

def send_sms(phone_number, message):
    """Send SMS using configured provider"""
    try:
        if not phone_number or not message:
            logger.warning("Invalid phone number or message")
            return False
        
        # Validate phone number
        if not validate_phone_number(phone_number):
            logger.warning(f"Invalid phone number: {phone_number}")
            return False
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        if not formatted_phone:
            logger.warning(f"Could not format phone number: {phone_number}")
            return False
        
        # Limit message to 160 characters (SMS standard)
        if len(message) > 160:
            message = message[:157] + "..."
        
        # Send via configured provider
        if SMS_PROVIDER == 'twilio':
            return send_sms_twilio(formatted_phone, message)
        elif SMS_PROVIDER == 'aws':
            return send_sms_aws(formatted_phone, message)
        else:
            logger.warning(f"Unknown SMS provider: {SMS_PROVIDER}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return False

def send_payment_due_sms(phone_number, name, days, expiry_date):
    """Send payment due reminder SMS"""
    template = SMS_TEMPLATES['payment_due']
    
    message = template.format(
        name=name[:10],  # Limit name length
        days=days,
        expiry_date=expiry_date
    )
    
    return send_sms(phone_number, message)

def send_membership_expired_sms(phone_number, name, expiry_date):
    """Send membership expired notification SMS"""
    template = SMS_TEMPLATES['membership_expired']
    
    message = template.format(
        name=name[:10],
        expiry_date=expiry_date
    )
    
    return send_sms(phone_number, message)

def send_points_awarded_sms(phone_number, name, points, activity):
    """Send points awarded notification SMS"""
    template = SMS_TEMPLATES['points_awarded']
    
    message = template.format(
        name=name[:10],
        points=points,
        activity=activity[:15]
    )
    
    return send_sms(phone_number, message)

def send_achievement_sms(phone_number, name, achievement, reward):
    """Send achievement unlocked SMS"""
    template = SMS_TEMPLATES['achievement_unlocked']
    
    message = template.format(
        name=name[:10],
        achievement=achievement[:20],
        reward=reward
    )
    
    return send_sms(phone_number, message)

def send_challenge_reminder_sms(phone_number, name, challenge_type, days_remaining, progress):
    """Send challenge deadline reminder SMS"""
    template = SMS_TEMPLATES['challenge_reminder']
    
    message = template.format(
        name=name[:10],
        days_remaining=days_remaining,
        progress=progress
    )
    
    return send_sms(phone_number, message)

def send_daily_reminder_sms(phone_number, name):
    """Send daily activity reminder SMS"""
    template = SMS_TEMPLATES['daily_reminder']
    
    message = template.format(name=name[:10])
    
    return send_sms(phone_number, message)

def verify_sms_configuration():
    """Verify SMS service is properly configured"""
    if SMS_PROVIDER == 'twilio':
        if not SMS_ACCOUNT_SID or not SMS_AUTH_TOKEN or not SMS_PHONE_NUMBER:
            logger.warning("Twilio not configured - SMS_ACCOUNT_SID, SMS_AUTH_TOKEN, SMS_PHONE_NUMBER missing")
            return False
        logger.info("SMS (Twilio) configuration verified")
        return True
    elif SMS_PROVIDER == 'aws':
        if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
            logger.warning("AWS SNS not configured - AWS_ACCESS_KEY, AWS_SECRET_KEY missing")
            return False
        logger.info("SMS (AWS SNS) configuration verified")
        return True
    else:
        logger.warning(f"Unknown SMS provider: {SMS_PROVIDER}")
        return False
