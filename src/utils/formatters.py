"""
Formatting utilities for displaying data in the UI.
"""
from datetime import datetime
from typing import Optional, Any


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object to string.

    Args:
        dt: Datetime object
        format_str: Format string

    Returns:
        Formatted datetime string
    """
    if not dt:
        return "N/A"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt

    return dt.strftime(format_str)


def format_phone(phone: str) -> str:
    """
    Format phone number for display.

    Args:
        phone: Phone number

    Returns:
        Formatted phone number
    """
    if not phone:
        return "N/A"

    # Remove non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())

    # Format based on length
    if len(digits) == 10:
        # US format: (XXX) XXX-XXXX
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        # US with country code: +1 (XXX) XXX-XXXX
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        # International or unknown format
        return phone


def format_email(email: str) -> str:
    """
    Format email for display.

    Args:
        email: Email address

    Returns:
        Formatted email
    """
    if not email:
        return "N/A"
    return email.lower().strip()


def format_merchant_id(merchant_id: Any) -> str:
    """
    Format merchant ID for display.

    Args:
        merchant_id: Merchant ID

    Returns:
        Formatted merchant ID
    """
    if merchant_id is None:
        return "N/A"
    return f"#{merchant_id}"


def format_status(status: str) -> str:
    """
    Format status string for display.

    Args:
        status: Status string

    Returns:
        Formatted status
    """
    if not status:
        return "Unknown"

    # Convert to title case and replace underscores
    return status.replace('_', ' ').title()


def format_auth_id(auth_id: Optional[str]) -> str:
    """
    Format authentication ID for display.

    Args:
        auth_id: Authentication ID (UUID)

    Returns:
        Formatted auth ID (first 8 characters)
    """
    if not auth_id:
        return "N/A"

    # Show first 8 characters of UUID
    return f"{auth_id[:8]}..." if len(auth_id) > 8 else auth_id


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_verification_method(method: str) -> str:
    """
    Format verification method for display.

    Args:
        method: Verification method (email, sms, etc.)

    Returns:
        Formatted method name
    """
    method_names = {
        'email': 'Email',
        'sms': 'SMS',
        'pin': 'PIN Code'
    }

    return method_names.get(method.lower(), method.title())


def format_boolean(value: bool) -> str:
    """
    Format boolean value for display.

    Args:
        value: Boolean value

    Returns:
        "Yes" or "No"
    """
    return "Yes" if value else "No"


def format_role(role: str) -> str:
    """
    Format user role for display.

    Args:
        role: User role

    Returns:
        Formatted role name
    """
    role_names = {
        'admin': 'Administrator',
        'staff': 'Staff Member',
        'user': 'User'
    }

    return role_names.get(role.lower(), role.title())


# Backward compatibility aliases
format_timestamp = format_datetime