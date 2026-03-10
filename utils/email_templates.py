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

def get_order_approved_html(order_id, user_first_name, items_summary, total_amount):
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Order Approved!</h1>
                <p style="color: #d1fae5; margin-top: 8px; font-size: 16px;">Order #{order_id}</p>
            </div>
            <div style="padding: 40px;">
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Hello {user_first_name or 'Valued Customer'},</p>
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Great news! Your order has been <b style="color: #10b981;">approved</b> and is now being processed for shipment.</p>
                
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; border: 1px solid #e5e7eb; margin-bottom: 24px;">
                    <h2 style="font-size: 18px; color: #1f2937; margin-top: 0; margin-bottom: 16px;">Order Details</h2>
                    <pre style="white-space: pre-wrap; font-family: inherit; color: #4b5563; margin: 0; font-size: 14px;">{items_summary}</pre>
                    <div style="margin-top: 16px; border-top: 1px solid #e5e7eb; padding-top: 12px; font-weight: 700; color: #1f2937;">
                        Total: GHS {total_amount}
                    </div>
                </div>
                
                <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">We'll notify you once your order has been shipped. You can track your order status in your profile.</p>
            </div>
            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_order_disapproved_html(order_id, user_first_name, reason=None):
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
            <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Order Update</h1>
                <p style="color: #fee2e2; margin-top: 8px; font-size: 16px;">Order #{order_id}</p>
            </div>
            <div style="padding: 40px;">
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Hello {user_first_name or 'Valued Customer'},</p>
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">We regret to inform you that your order has been <b style="color: #ef4444;">not approved</b> at this time.</p>
                {f'<div style="background-color: #fef2f2; border-radius: 8px; padding: 16px; border: 1px solid #fecaca; margin-bottom: 24px;"><p style="color: #dc2626; font-size: 14px; margin: 0;"><b>Reason:</b> {reason}</p></div>' if reason else ''}
                <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">If you have any questions, please contact our support team. We apologize for any inconvenience.</p>
            </div>
            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_shipping_status_update_html(order_id, user_first_name, new_status, tracking_number=None):
    # Status display mapping
    status_display = {
        'pending': ('Pending', '#f59e0b'),
        'processing': ('Processing', '#3b82f6'),
        'shipped': ('Shipped', '#8b5cf6'),
        'in_transit': ('In Transit', '#6366f1'),
        'out_for_delivery': ('Out for Delivery', '#14b8a6'),
        'delivered': ('Delivered', '#10b981'),
        'cancelled': ('Cancelled', '#ef4444'),
    }
    
    status_text, status_color = status_display.get(new_status.lower(), (new_status, '#6b7280'))
    
    tracking_section = f"""
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 16px; margin-top: 16px; border: 1px solid #e5e7eb;">
                    <p style="color: #4b5563; font-size: 14px; margin: 0;"><b>Tracking Number:</b> {tracking_number}</p>
                </div>
    """ if tracking_number else ""
    
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e1e4e8;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 40px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">Shipping Update</h1>
                <p style="color: #e0e7ff; margin-top: 8px; font-size: 16px;">Order #{order_id}</p>
            </div>
            <div style="padding: 40px;">
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Hello {user_first_name or 'Valued Customer'},</p>
                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">Your order status has been updated to:</p>
                
                <div style="background-color: #f3f4f6; border-radius: 12px; padding: 24px; text-align: center; border: 2px solid {status_color};">
                    <span style="font-size: 24px; font-weight: 700; color: {status_color}; text-transform: uppercase;">{status_text}</span>
                </div>
                
                {tracking_section}
                
                <p style="color: #6b7280; font-size: 14px; line-height: 1.5; margin-top: 24px;">Thank you for shopping with Sneda Ecommerce!</p>
            </div>
            <div style="background-color: #f9fafb; padding: 24px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">&copy; 2026 Sneda Ecommerce. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
