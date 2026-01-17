import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
SENDER_NAME = os.getenv('SENDER_NAME', 'Fitness Club')

# Email templates
EMAIL_TEMPLATES = {
    'payment_due': {
        'subject': '💳 Membership Expiring Soon',
        'body': """
Hello {name},

Your fitness club membership is expiring in {days} days.

Membership Details:
- Current Status: ACTIVE
- Expiry Date: {expiry_date}
- Amount Due: ₹{amount}

Renew your membership now to continue enjoying all benefits!

Visit our bot: @fitness_club_bot
Command: /payment_status

Best regards,
Fitness Club Team
        """
    },
    'membership_expired': {
        'subject': '❌ Membership Expired',
        'body': """
Hello {name},

Your fitness club membership has expired.

Previous Membership:
- Ended: {expiry_date}

Please renew your membership to regain access.

Visit our bot: @fitness_club_bot
Command: /payment_status

Best regards,
Fitness Club Team
        """
    },
    'points_awarded': {
        'subject': '✨ Points Earned!',
        'body': """
Hello {name},

Congratulations! You earned {points} points!

Activity: {activity}
Current Total: {total_points} points
Rank: {rank}

Keep up the great work! 💪

Visit our bot: @fitness_club_bot
Command: /leaderboard

Best regards,
Fitness Club Team
        """
    },
    'achievement_unlocked': {
        'subject': '🏆 Achievement Unlocked!',
        'body': """
Hello {name},

Congratulations! You unlocked a new achievement! 🎉

Achievement: {achievement}
Description: {description}
Reward: {reward} points

You're doing amazing! Keep pushing forward!

Visit our bot: @fitness_club_bot
Command: /profile

Best regards,
Fitness Club Team
        """
    },
    'challenge_reminder': {
        'subject': '🔔 Challenge Deadline Approaching',
        'body': """
Hello {name},

Your challenge deadline is approaching! ⏰

Challenge: {challenge_type}
Days Remaining: {days_remaining}
Your Progress: {progress}

Don't miss this opportunity to complete the challenge!

Visit our bot: @fitness_club_bot
Command: /my_challenges

Best regards,
Fitness Club Team
        """
    },
    'daily_reminder': {
        'subject': '📱 Daily Activity Reminder',
        'body': """
Hello {name},

It's time to log your daily activities! 📝

Today's Goal:
- Log weight/measurements
- Track water intake
- Log meals
- Record workouts

Keep your streak alive! 🔥

Visit our bot: @fitness_club_bot
Command: /menu

Best regards,
Fitness Club Team
        """
    }
}

def send_email(recipient_email, subject, body, template_vars=None):
    """Send email using SMTP"""
    try:
        if not recipient_email or not subject or not body:
            logger.warning("Invalid email parameters")
            return False
        
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            logger.warning("Email credentials not configured")
            return False
        
        # Replace template variables if provided
        if template_vars:
            body = body.format(**template_vars)
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        message["To"] = recipient_email
        message["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        # Create plain text and HTML versions
        text_part = MIMEText(body, "plain")
        html_part = MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
        
        logger.info(f"Email sent to {recipient_email}: {subject}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("Email authentication failed - check credentials")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def send_payment_due_email(recipient_email, name, days, expiry_date, amount):
    """Send payment due reminder email"""
    template = EMAIL_TEMPLATES['payment_due']
    
    template_vars = {
        'name': name,
        'days': days,
        'expiry_date': expiry_date,
        'amount': amount
    }
    
    return send_email(recipient_email, template['subject'], template['body'], template_vars)

def send_membership_expired_email(recipient_email, name, expiry_date):
    """Send membership expired notification email"""
    template = EMAIL_TEMPLATES['membership_expired']
    
    template_vars = {
        'name': name,
        'expiry_date': expiry_date
    }
    
    return send_email(recipient_email, template['subject'], template['body'], template_vars)

def send_points_awarded_email(recipient_email, name, points, activity, total_points, rank):
    """Send points awarded notification email"""
    template = EMAIL_TEMPLATES['points_awarded']
    
    template_vars = {
        'name': name,
        'points': points,
        'activity': activity,
        'total_points': total_points,
        'rank': rank
    }
    
    return send_email(recipient_email, template['subject'], template['body'], template_vars)

def send_achievement_email(recipient_email, name, achievement, description, reward):
    """Send achievement unlocked email"""
    template = EMAIL_TEMPLATES['achievement_unlocked']
    
    template_vars = {
        'name': name,
        'achievement': achievement,
        'description': description,
        'reward': reward
    }
    
    return send_email(recipient_email, template['subject'], template['body'], template_vars)

def send_challenge_reminder_email(recipient_email, name, challenge_type, days_remaining, progress):
    """Send challenge deadline reminder email"""
    template = EMAIL_TEMPLATES['challenge_reminder']
    
    template_vars = {
        'name': name,
        'challenge_type': challenge_type,
        'days_remaining': days_remaining,
        'progress': progress
    }
    
    return send_email(recipient_email, template['subject'], template['body'], template_vars)

def send_daily_reminder_email(recipient_email, name):
    """Send daily activity reminder email"""
    template = EMAIL_TEMPLATES['daily_reminder']
    
    template_vars = {
        'name': name
    }
    
    return send_email(recipient_email, template['subject'], template['body'], template_vars)

def verify_email_configuration():
    """Verify email service is properly configured"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        logger.warning("Email service not configured - SENDER_EMAIL or SENDER_PASSWORD missing")
        return False
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        logger.info("Email service configuration verified")
        return True
    except Exception as e:
        logger.error(f"Email configuration verification failed: {str(e)}")
        return False
