# get otp email template
def get_otp_email_html(otp):
    return f"""
    <!DOCTYPE html>
    <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
                <div style="background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); padding: 40px 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Verification Required</h1>
                </div>
                <div style="padding: 40px; text-align: center;">
                    <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Thank you for choosing our platform. To complete your verification, please use the following One-Time Password (OTP):</p>
                    <div style="background-color: #f3f4f6; border-radius: 12px; padding: 20px 40px; display: inline-block; margin-bottom: 24px; border: 1px solid #e5e7eb;">
                        <span style="font-size: 36px; font-weight: 800; color: #1f2937; letter-spacing: 8px; font-family: 'Courier New', Courier, monospace;">{otp}</span>
                    </div>
                    <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">This code is valid for <b>5 minutes</b>. If you did not request this, please ignore this email or contact support if you have concerns.</p>
                </div>
                <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                    <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
# password reset email template
def get_password_reset_html(password_reset_url):
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Password Reset</h1>
            </div>
            <div style="padding: 40px; text-align: center;">
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">We received a request to reset your password. Click the button below to set a new password for your account.</p>
                <a href="{password_reset_url}" style="display: inline-block; background-color: #3b82f6; color: #ffffff; padding: 16px 32px; border-radius: 8px; font-weight: 600; text-decoration: none; box-shadow: 0 4px 6px rgba(59, 130, 246, 0.2);">Reset Password</a>
                <p style="color: #9ca3af; font-size: 14px; margin-top: 35px; line-height: 1.5;">This link is valid for <b>15 minutes</b>. If you didn't request a password reset, you can safely ignore this email.</p>
            </div>
            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_order_confirmation_html(order_id, user_first_name, amount, order_items_summary, total_amount):
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Order Confirmed!</h1>
                <p style="color: #d1fae5; margin-top: 8px; font-size: 16px;">Order #{order_id}</p>
            </div>
            <div style="padding: 40px;">
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Hello {user_first_name or 'Valued Customer'},</p>
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Your payment of <b>GHS {amount}</b> has been successfully processed. We're now preparing your order for shipment.</p>
                
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; border: 1px solid #e5e7eb; margin-bottom: 24px;">
                    <h2 style="font-size: 18px; color: #1f2937; margin-top: 0; margin-bottom: 16px;">Order Summary</h2>
                    <pre style="white-space: pre-wrap; font-family: inherit; color: #4b5563; margin: 0; font-size: 14px;">{order_items_summary}</pre>
                    <div style="margin-top: 16px; border-top: 1px solid #e5e7eb; padding-top: 12px; font-weight: 700; color: #1f2937;">
                        Total: GHS {total_amount}
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">You can track your order status in your profile. Thank you for shopping with Sneda Ecommerce!</p>
            </div>
            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
