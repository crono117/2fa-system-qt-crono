"""
Error translation utilities for user-friendly error messages.
"""
from typing import Dict, Any, Optional


class ErrorTranslator:
    """
    Translates API and system errors into user-friendly messages.
    """

    # Error message mappings
    ERROR_MESSAGES = {
        # Authentication errors
        "invalid_credentials": "Invalid username or password",
        "invalid_token": "Your session has expired. Please log in again",
        "token_expired": "Your session has expired. Please log in again",
        "unauthorized": "You are not authorized to perform this action",
        "permission_denied": "You don't have permission to access this resource",

        # Verification errors
        "invalid_pin": "The PIN code you entered is incorrect",
        "pin_expired": "This PIN code has expired. Please request a new one",
        "max_attempts_exceeded": "Maximum verification attempts exceeded. Please try again later",
        "verification_failed": "Verification failed. Please try again",

        # Merchant errors
        "invalid_email": "Invalid email address format",
        "invalid_phone": "Invalid phone number format",

        # Network errors
        "connection_error": "Unable to connect to server. Please check your internet connection",
        "timeout": "Request timed out. Please try again",
        "network_error": "Network error occurred. Please try again",

        # API errors
        "server_error": "Server error occurred. Please try again later",
        "bad_request": "Invalid request. Please check your input",
        "not_found": "Resource not found",
        "rate_limit_exceeded": "Too many requests. Please wait a moment and try again",

        # Validation errors
        "validation_error": "Please check your input and try again",
        "required_field": "This field is required",
        "invalid_format": "Invalid format. Please check your input",

        # WebSocket errors
        "websocket_error": "Real-time connection error. Updates may be delayed",
        "websocket_closed": "Real-time connection closed. Attempting to reconnect..."
    }

    @classmethod
    def translate(cls, error: Any, default_message: str = "An error occurred") -> str:
        """
        Translate an error to a user-friendly message.

        Args:
            error: Error object (can be string, dict, or exception)
            default_message: Default message if translation not found

        Returns:
            User-friendly error message
        """
        if isinstance(error, str):
            # Direct error code
            return cls.ERROR_MESSAGES.get(error, default_message)

        if isinstance(error, dict):
            # API error response
            error_code = error.get('code', '')
            error_message = error.get('message', '')
            detail = error.get('detail', '')

            # Try to translate error code
            if error_code and error_code in cls.ERROR_MESSAGES:
                return cls.ERROR_MESSAGES[error_code]

            # Return API message if available
            if error_message:
                return error_message
            if detail:
                return detail

        if isinstance(error, Exception):
            # Exception object
            error_str = str(error).lower()

            # Check for known error patterns
            if 'connection' in error_str or 'refused' in error_str:
                return cls.ERROR_MESSAGES['connection_error']
            if 'timeout' in error_str:
                return cls.ERROR_MESSAGES['timeout']
            if 'unauthorized' in error_str or '401' in error_str:
                return cls.ERROR_MESSAGES['unauthorized']
            if '404' in error_str:
                return cls.ERROR_MESSAGES['not_found']
            if '500' in error_str or 'server error' in error_str:
                return cls.ERROR_MESSAGES['server_error']

            # Return exception message
            return str(error)

        return default_message

    @classmethod
    def translate_validation_errors(cls, errors: Dict[str, Any]) -> Dict[str, str]:
        """
        Translate validation errors for form fields.

        Args:
            errors: Dictionary of field names to error messages

        Returns:
            Dictionary of field names to translated messages
        """
        translated = {}

        for field, error_msg in errors.items():
            if isinstance(error_msg, list):
                # Multiple errors for one field
                translated[field] = ' '.join(cls.translate(e) for e in error_msg)
            else:
                translated[field] = cls.translate(error_msg)

        return translated

    @classmethod
    def get_retry_message(cls, error: Any) -> Optional[str]:
        """
        Get a retry message if the error is retryable.

        Args:
            error: Error object

        Returns:
            Retry message or None if not retryable
        """
        retryable_errors = [
            'connection_error',
            'timeout',
            'network_error',
            'server_error',
            'rate_limit_exceeded'
        ]

        if isinstance(error, str) and error in retryable_errors:
            return "Please try again in a few moments"

        if isinstance(error, dict):
            error_code = error.get('code', '')
            if error_code in retryable_errors:
                return "Please try again in a few moments"

        return None


# Global instance
error_translator = ErrorTranslator()