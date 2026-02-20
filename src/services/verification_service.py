"""
Verification service — PySide2 port with both payload bugs fixed.

Bug 1 FIX (Email Send):
  OLD: {"customer_id": ..., "email": ..., "staff_user_id": ...}
  NEW: {"merchant_id": ..., "email": ..., "user_id": ...}

Bug 2 FIX (PIN Verify):
  OLD: {"token": ..., "pin": ..., "staff_user_id": ...}
  NEW: {"pin": ..., "merchant_id": ..., "user_id": ...}

Field rules:
  merchant.get('merchant_id') → UUID  → use in ALL API payloads
  merchant.get('back_end_mid') → processor MID → display only
  merchant.get('dba') → business name → display only
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from threading import Lock

from api.base_client import ApiResponse
from api.verification_client import verification_client
from state.verification_state import verification_state
from utils.validators import validate_pin, validate_merchant_id, validate_email, validate_phone
from utils.error_translator import error_translator
from utils.logger import logger


@dataclass
class VerificationResult:
    """Result container for verification operations."""
    success: bool
    message: str
    auth_id: Optional[str] = None
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class VerificationService:
    """
    Business-logic service for 2FA verification workflows.

    All methods are blocking — call from ApiWorker threads, never from
    the main thread directly.
    """

    def __init__(self):
        self._lock = Lock()
        self._max_retry_attempts = 3

    # ------------------------------------------------------------------
    # Email verification (Bug 1 + Bug 2 fixed)
    # ------------------------------------------------------------------

    def start_email_verification(
        self,
        merchant_data: Dict[str, Any],
        user_id: int,
    ) -> VerificationResult:
        """
        Start email PIN verification.

        BUG 1 FIX: payload now uses merchant_id (UUID) and user_id.
        """
        # Correct field: merchant_id is the UUID
        merchant_id = merchant_data.get('merchant_id')
        email = merchant_data.get('contact_email') or merchant_data.get('email')

        if not merchant_id:
            return VerificationResult(success=False, message="Merchant ID (UUID) is required")

        is_valid, err = validate_merchant_id(str(merchant_id))
        if not is_valid:
            return VerificationResult(success=False, message=err)

        if not email:
            return VerificationResult(success=False, message="Merchant email is required")

        is_valid, err = validate_email(email)
        if not is_valid:
            return VerificationResult(success=False, message=err)

        # BUG 1 FIX: correct field names for backend
        response = verification_client.send_email_auth(
            email=email,
            merchant_id=str(merchant_id),
            user_id=user_id,
        )

        if response.success:
            data = response.data or {}
            auth_id = data.get('auth_id')

            verification_state.start_verification(
                customer_id=merchant_id,
                method='email',
                token=None,          # token no longer used for PIN verify
                auth_id=auth_id,
            )

            logger.info(f"Email verification started: merchant={merchant_id}, auth_id={auth_id}")
            return VerificationResult(
                success=True,
                message=data.get('message', 'Email verification sent successfully'),
                auth_id=auth_id,
                data=data,
            )
        else:
            err = error_translator.translate(response.error)
            logger.error(f"Email verification failed: {err}")
            return VerificationResult(success=False, message=err)

    def verify_pin_code(
        self,
        pin: str,
        merchant_id: str,
        user_id: int,
    ) -> VerificationResult:
        """
        Verify PIN code.

        BUG 2 FIX: payload now uses merchant_id + user_id; token removed.
        """
        is_valid, err = validate_pin(pin)
        if not is_valid:
            return VerificationResult(success=False, message=err)

        if not merchant_id:
            return VerificationResult(success=False, message="Merchant ID is required")

        if verification_state.is_max_attempts_reached():
            return VerificationResult(
                success=False,
                message="Maximum verification attempts exceeded",
            )

        verification_state.increment_attempts()

        # BUG 2 FIX: correct payload — no token, has merchant_id + user_id
        response = verification_client.verify_pin(
            pin=pin,
            merchant_id=str(merchant_id),
            user_id=user_id,
        )

        if response.success:
            data = response.data or {}
            auth_id = data.get('auth_id')

            verification_state.complete_verification(
                success=True,
                message='PIN verified successfully',
            )
            logger.info(f"PIN verification successful: auth_id={auth_id}")

            return VerificationResult(
                success=True,
                message=data.get('message', 'PIN verified successfully'),
                auth_id=auth_id,
                data=data,
            )
        else:
            err = error_translator.translate(response.error)
            logger.warning(f"PIN verification failed: {err}")
            verification_state.update_status('failed_attempt', err)
            return VerificationResult(success=False, message=err)

    # ------------------------------------------------------------------
    # SMS verification (always correct in original — kept as-is)
    # ------------------------------------------------------------------

    def start_sms_verification(
        self,
        merchant_data: Dict[str, Any],
        user_id: int,
    ) -> VerificationResult:
        """
        Initiate SMS verification session.
        Payload: merchant_id (UUID), verification_method, delivery_address
        """
        merchant_id = merchant_data.get('merchant_id')
        phone = (
            merchant_data.get('contact_phone')
            or merchant_data.get('phone')
        )

        if not merchant_id:
            return VerificationResult(success=False, message="Merchant ID (UUID) is required")

        if not phone:
            return VerificationResult(success=False, message="Merchant phone is required")

        is_valid, err = validate_phone(phone)
        if not is_valid:
            return VerificationResult(success=False, message=err)

        response = verification_client.initiate_sms_verification(
            merchant_id=str(merchant_id),
            phone=phone,
        )

        if response.success:
            data = response.data or {}
            session_id = data.get('session_id')

            verification_state.start_verification(
                customer_id=merchant_id,
                method='sms',
                auth_id=session_id,
            )
            logger.info(f"SMS verification started: merchant={merchant_id}, session={session_id}")

            return VerificationResult(
                success=True,
                message=data.get('message', 'SMS verification sent successfully'),
                auth_id=session_id,
                session_id=session_id,
                data=data,
            )
        else:
            err = error_translator.translate(response.error)
            logger.error(f"SMS verification failed: {err}")
            return VerificationResult(success=False, message=err)

    def verify_sms_code(
        self,
        code: str,
        session_id: str,
    ) -> VerificationResult:
        """Confirm SMS verification code.  Payload: session_id, verification_code."""
        if not code:
            return VerificationResult(success=False, message="Verification code is required")
        if not session_id:
            return VerificationResult(success=False, message="Session ID is required")

        response = verification_client.confirm_sms_verification(
            session_id=session_id,
            code=code,
        )

        if response.success:
            data = response.data or {}
            verification_state.complete_verification(success=True, message='SMS verified')
            logger.info(f"SMS verification successful: session={session_id}")

            return VerificationResult(
                success=True,
                message=data.get('message', 'SMS verified successfully'),
                auth_id=session_id,
                data=data,
            )
        else:
            err = error_translator.translate(response.error)
            logger.warning(f"SMS verification failed: {err}")
            return VerificationResult(success=False, message=err)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_authentication_history(
        self,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> ApiResponse:
        """Fetch authentication history with optional filters."""
        return verification_client.get_authentication_history(limit=limit, filters=filters)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def cancel_session(self) -> bool:
        if not verification_state.is_active():
            return False
        verification_state.complete_verification(success=False, message='Cancelled by user')
        return True


# Global singleton
verification_service = VerificationService()
