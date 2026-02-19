import resend
import os

resend.api_key = os.environ.get('RESEND_EMAIL_API_KEY')

def send_otp_email(to, subject, html):
    r = resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": to,
        "subject": subject,
        "html": html
    })

    return r


def send_order_confirmation_email(to, subject, html):
    r = resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": to,
        "subject": subject,
        "html": html
    })

    return r