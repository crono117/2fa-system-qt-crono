"""
Validation utilities for input validation and data sanitization.
"""
import re
from typing import Optional, Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email address is required"

    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False, "Invalid email address format"

    if len(email) > 254:  # RFC 5321
        return False, "Email address is too long"

    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"

    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)

    # Check if it contains only digits and optional + prefix
    if not re.match(r'^\+?\d{10,15}$', cleaned):
        return False, "Invalid phone number format (10-15 digits required)"

    return True, ""


def validate_pin(pin: str) -> Tuple[bool, str]:
    """
    Validate PIN code format.

    Args:
        pin: PIN code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pin:
        return False, "PIN is required"

    if not pin.isdigit():
        return False, "PIN must contain only digits"

    if len(pin) != 6:
        return False, "PIN must be exactly 6 digits"

    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 150:
        return False, "Username is too long (max 150 characters)"

    # Allow alphanumeric, underscore, hyphen, and period
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return False, "Username can only contain letters, numbers, and ._-"

    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    # Check for at least one number
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"

    # Check for at least one letter
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"

    return True, ""


def sanitize_input(text: str) -> str:
    """
    Sanitize user input by removing potentially dangerous characters.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace('\x00', '')

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def validate_merchant_id(merchant_id: str) -> Tuple[bool, str]:
    """
    Validate merchant ID format.

    Accepts both UUID format (v1.9.43+) and numeric format (back_end_mid).

    Args:
        merchant_id: Merchant ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not merchant_id:
        return False, "Merchant ID is required"

    merchant_id = str(merchant_id).strip()
    if not merchant_id:
        return False, "Merchant ID is required"

    # Accept UUID format (merchant_id is UUID since v1.9.43)
    uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    if re.match(uuid_pattern, merchant_id):
        return True, ""

    # Accept numeric format (back_end_mid for backward compatibility)
    try:
        int_id = int(merchant_id)
        if int_id <= 0:
            return False, "Merchant ID must be a positive number"
        return True, ""
    except ValueError:
        pass

    # Accept any reasonable non-empty string (postgres_merchant_id, etc.)
    if len(merchant_id) > 50:
        return False, "Merchant ID is too long (max 50 characters)"

    return True, ""


# Backward compatibility aliases
validate_phone_number = validate_phone