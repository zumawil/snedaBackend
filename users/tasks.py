from celery import shared_task
from django.contrib.auth import get_user_model
from utils.sendEmail import send_otp_email, send_password_reset_email
from utils.email_templates import get_otp_email_html, get_password_reset_html, get_manual_otp_email_html
import logging
import pyotp
from background_tasks.models import BackgroundJob

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_email_task(self, job_id, user_id):
    job = None
    User = get_user_model()

    try:
        # Fetch job
        try:
            job = BackgroundJob.objects.get(id=job_id)
        except BackgroundJob.DoesNotExist:
            logger.error(f"Job with id {job_id} not found for OTP email task")
            return

        # Mark job as processing
        job.mark_processing()
        logger.info(f"Started processing job {job_id}")

        # Fetch user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found for OTP email task")
            job.mark_failed(f"User with id {user_id} not found")
            return

        # Generate OTP secret if missing
        if not user.otp_secret:
            user.otp_secret = pyotp.random_base32()
            user.save(update_fields=["otp_secret"])

        # Generate OTP (valid for 5 minutes)
        totp = pyotp.TOTP(user.otp_secret, interval=300)
        otp = totp.now()

        # Generate email HTML
        otp_html = get_otp_email_html(otp)

        # Send email
        send_otp_email(
            user.email,
            "Your verification code from Sneda Ecommerce",
            otp_html,
        )

        # Mark job completed
        job.mark_completed()
        logger.info(f"Successfully completed job {job_id}")

        return f"OTP email sent to {user.email}"

    except Exception as e:
        logger.exception("Error sending OTP email task")

        # If retries exhausted → mark failed
        if job and self.request.retries >= self.max_retries:
            job.mark_failed(f"Error sending OTP email task: {str(e)}")
        else:
            raise self.retry(exc=e)  

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_manual_otp_email_task(self, job_id, user_id):
    job = None
    User = get_user_model()

    try:
        # Fetch job
        try:
            job = BackgroundJob.objects.get(id=job_id)
        except BackgroundJob.DoesNotExist:
            logger.error(f"Job with id {job_id} not found for manual OTP email task")
            return

        # Mark job as processing
        job.mark_processing()
        logger.info(f"Started processing job {job_id}")

        # Fetch user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found for manual OTP email task")
            job.mark_failed(f"User with id {user_id} not found")
            return
        
        if not user.otp_secret:
            user.otp_secret = pyotp.random_base32()
            user.save(update_fields=["otp_secret"])

        totp = pyotp.TOTP(user.otp_secret, interval=300)
        otp = totp.now()
        
        otp_html = get_manual_otp_email_html(otp)
        
        send_otp_email(
            user.email,
            "Your New Verification Code - Sneda Ecommerce",
            otp_html,
        )

        # Mark job completed
        job.mark_completed()
        logger.info(f"Successfully completed job {job_id}")

        return f"Manual OTP email sent to {user.email}"

    except Exception as e:
        logger.exception("Error sending manual OTP email task")
        
        # If retries exhausted → mark failed
        if job and self.request.retries >= self.max_retries:
            job.mark_failed(f"Error sending manual OTP email task: {str(e)}")
        else:
            raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, job_id, user_id, password_reset_url):
    job = None
    User = get_user_model()

    try:
        # Fetch job
        try:
            job = BackgroundJob.objects.get(id=job_id)
        except BackgroundJob.DoesNotExist:
            logger.error(f"Job with id {job_id} not found for password reset email task")
            return

        # Mark job as processing
        job.mark_processing()
        logger.info(f"Started processing job {job_id}")

        # Fetch user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with id {user_id} not found for password reset email task")
            job.mark_failed(f"User with id {user_id} not found")
            return
        
        reset_html = get_password_reset_html(password_reset_url)
        
        send_password_reset_email(
            user.email,
            "Password Reset Request",
            reset_html,
        )

        # Mark job completed
        job.mark_completed()
        logger.info(f"Successfully completed job {job_id}")

        return f"Password reset email sent to {user.email}"

    except Exception as e:
        logger.exception("Error sending password reset email task")
        
        # If retries exhausted → mark failed
        if job and self.request.retries >= self.max_retries:
            job.mark_failed(f"Error sending password reset email task: {str(e)}")
        else:
            raise self.retry(exc=e)
