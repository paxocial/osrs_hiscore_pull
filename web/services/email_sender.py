"""
Email Sender Service
Phase 3, Task 3.3: Email Verification Flow

Handles SMTP email sending for verification emails, password resets, and other
transactional emails. Uses configuration from AppConfig.smtp settings.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from config.settings import AppConfig

logger = logging.getLogger(__name__)


def send_verification_email(email: str, token: str, base_url: str = "http://localhost:8001") -> bool:
    """
    Send email verification link to user.

    Args:
        email: Recipient email address
        token: Verification token (URL-safe)
        base_url: Base URL for application (e.g., https://catherby.net)

    Returns:
        True if email sent successfully, False otherwise

    Example:
        token = secrets.token_urlsafe(32)
        send_verification_email("user@example.com", token, "https://catherby.net")
    """
    config = AppConfig()

    # Check if email verification enabled
    if not config.features.enable_email_verification:
        logger.info("Email verification disabled, skipping email send")
        return False

    verification_link = f"{base_url}/auth/verify?token={token}"

    subject = "Verify your OSRS Dashboard account"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c5282;">Verify Your Email Address</h2>
            <p>Thank you for registering with OSRS Dashboard!</p>
            <p>Please click the button below to verify your email address:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_link}"
                   style="background-color: #2c5282; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #4a5568; font-size: 14px;">
                {verification_link}
            </p>
            <p style="color: #718096; font-size: 12px; margin-top: 30px;">
                This verification link will expire in 24 hours.
            </p>
            <p style="color: #718096; font-size: 12px;">
                If you did not create an account, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
Verify Your Email Address

Thank you for registering with OSRS Dashboard!

Please click the link below to verify your email address:
{verification_link}

This verification link will expire in 24 hours.

If you did not create an account, please ignore this email.
    """

    return _send_email(
        to_email=email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )


def send_password_reset_email(email: str, token: str, base_url: str = "http://localhost:8001") -> bool:
    """
    Send password reset link to user.

    Args:
        email: Recipient email address
        token: Password reset token (URL-safe)
        base_url: Base URL for application

    Returns:
        True if email sent successfully, False otherwise
    """
    config = AppConfig()

    reset_link = f"{base_url}/auth/reset-password?token={token}"

    subject = "Reset your OSRS Dashboard password"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c5282;">Reset Your Password</h2>
            <p>You requested to reset your password for OSRS Dashboard.</p>
            <p>Click the button below to reset your password:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}"
                   style="background-color: #2c5282; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #4a5568; font-size: 14px;">
                {reset_link}
            </p>
            <p style="color: #718096; font-size: 12px; margin-top: 30px;">
                This password reset link will expire in 1 hour.
            </p>
            <p style="color: #718096; font-size: 12px;">
                If you did not request a password reset, please ignore this email or contact support.
            </p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
Reset Your Password

You requested to reset your password for OSRS Dashboard.

Click the link below to reset your password:
{reset_link}

This password reset link will expire in 1 hour.

If you did not request a password reset, please ignore this email.
    """

    return _send_email(
        to_email=email,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )


def _send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str
) -> bool:
    """
    Send email via SMTP.

    Internal helper function that handles SMTP connection and message sending.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML version of email body
        text_body: Plain text version of email body

    Returns:
        True if email sent successfully, False on error
    """
    config = AppConfig()

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.smtp.from_address
    msg["To"] = to_email

    # Attach text and HTML parts
    part1 = MIMEText(text_body, "plain")
    part2 = MIMEText(html_body, "html")
    msg.attach(part1)
    msg.attach(part2)

    try:
        # Connect to SMTP server
        if config.smtp.use_tls:
            server = smtplib.SMTP(config.smtp.host, config.smtp.port)
            server.starttls()
        else:
            server = smtplib.SMTP(config.smtp.host, config.smtp.port)

        # Login if credentials provided
        if config.smtp.username and config.smtp.password:
            server.login(config.smtp.username, config.smtp.password)

        # Send email
        server.send_message(msg)
        server.quit()

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False
