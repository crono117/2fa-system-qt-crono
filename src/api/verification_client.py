"""
Verification API Client — PySide2 port.

Identical to frontend_ii version except the SMS fallback endpoint
is corrected to the canonical verification/initiate/ path.
"""
from typing import Optional, Dict, Any

from .base_client import BaseApiClient, ApiResponse
from config.settings import settings
from utils.logger import logger


class VerificationClient(BaseApiClient):
    """Verification API client for 2FA operations."""

    # ------------------------------------------------------------------
    # Email 2FA
    # ------------------------------------------------------------------

    def send_email_auth(
        self,
        email: str,
        merchant_id: str,
        user_id: Optional[int] = None,
    ) -> ApiResponse:
        """Send email PIN.  Correct payload: merchant_id, email, user_id."""
        logger.info(f"Sending email auth to {email} for merchant {merchant_id}")

        if not email:
            return ApiResponse(success=False, error="Email address is required")
        if not merchant_id:
            return ApiResponse(success=False, error="Merchant ID is required")

        payload: Dict[str, Any] = {"email": email, "merchant_id": merchant_id}
        if user_id is not None:
            payload["user_id"] = user_id

        return self.post(settings.get_api_endpoints()["send_email_auth"], json=payload)

    def verify_pin(
        self,
        pin: str,
        merchant_id: str,
        user_id: Optional[int] = None,
    ) -> ApiResponse:
        """Verify PIN.  Correct payload: pin, merchant_id, user_id (no token)."""
        logger.info(f"Verifying PIN for merchant {merchant_id}")

        if not pin or len(pin) != 6 or not pin.isdigit():
            return ApiResponse(success=False, error="PIN must be 6 digits")
        if not merchant_id:
            return ApiResponse(success=False, error="Merchant ID is required")

        payload: Dict[str, Any] = {"pin": pin, "merchant_id": merchant_id}
        if user_id is not None:
            payload["user_id"] = user_id

        return self.post(settings.get_api_endpoints()["verify_pin"], json=payload)

    # ------------------------------------------------------------------
    # SMS 2FA (verification/initiate + verification/confirm)
    # ------------------------------------------------------------------

    def initiate_sms_verification(
        self,
        merchant_id: str,
        phone: str,
    ) -> ApiResponse:
        """
        Initiate SMS verification session.
        Payload: merchant_id, verification_method, delivery_address
        """
        logger.info(f"Initiating SMS verification for merchant {merchant_id}")

        payload = {
            "merchant_id": merchant_id,
            "verification_method": "sms",
            "delivery_address": phone,
        }
        return self.post(settings.get_api_endpoints()["verification_initiate"], json=payload)

    def confirm_sms_verification(
        self,
        session_id: str,
        code: str,
    ) -> ApiResponse:
        """
        Confirm SMS verification code.
        Payload: session_id, verification_code
        """
        logger.info(f"Confirming SMS code for session {session_id}")

        if not code or not session_id:
            return ApiResponse(success=False, error="session_id and code are required")

        payload = {"session_id": session_id, "verification_code": code}
        return self.post(settings.get_api_endpoints()["verification_confirm"], json=payload)

    # ------------------------------------------------------------------
    # Merchant search
    # ------------------------------------------------------------------

    def universal_search(self, query: str, page: int = 1, page_size: int = 20) -> ApiResponse:
        """Universal merchant search using ?q= parameter."""
        logger.info(f"Universal search: {query}")
        params = {"q": query, "page": page, "page_size": page_size}
        return self.get("merchants/merchants/universal_search/", params=params)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_authentication_history(
        self,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> ApiResponse:
        """Fetch authentication history with optional Django ORM filters."""
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if filters:
            params.update(filters)
        return self.get(
            settings.get_api_endpoints()["authentication_history"],
            params=params,
        )


# Module-level singleton used by service layer
verification_client = VerificationClient()
