from celery import shared_task
from django.contrib.auth import get_user_model
from utils.sendEmail import send_otp_email, send_password_reset_email
from utils.email_templates import get_otp_email_html, get_password_reset_html, get_manual_otp_email_html
import logging
import pyotp

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_email_task(self, user_id):
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        if not user.otp_secret:
            user.otp_secret = pyotp.random_base32()
            user.save()

        totp = pyotp.TOTP(user.otp_secret, interval=300)
        otp = totp.now()
        
        otp_html = get_otp_email_html(otp)
        
        send_otp_email(
            user.email,
            "Your verification code from Sneda Ecommerce",
            otp_html,
        )
        return f"OTP email sent to {user.email}"
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found for OTP email task")
    except Exception as e:
        logger.exception("Error sending OTP email task")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_manual_otp_email_task(self, user_id):
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        if not user.otp_secret:
            user.otp_secret = pyotp.random_base32()
            user.save()

        totp = pyotp.TOTP(user.otp_secret, interval=300)
        otp = totp.now()
        
        otp_html = get_manual_otp_email_html(otp)
        
        send_otp_email(
            user.email,
            "Your New Verification Code - Sneda Ecommerce",
            otp_html,
        )
        return f"Manual OTP email sent to {user.email}"
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found for manual OTP email task")
    except Exception as e:
        logger.exception("Error sending manual OTP email task")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_id, password_reset_url):
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        reset_html = get_password_reset_html(password_reset_url)
        
        send_password_reset_email(
            user.email,
            "Password Reset Request",
            reset_html,
        )
        return f"Password reset email sent to {user.email}"
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found for password reset email task")
    except Exception as e:
        logger.exception("Error sending password reset email task")
        raise self.retry(exc=e)
