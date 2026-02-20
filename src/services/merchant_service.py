"""
Merchant service — PySide2 port.

Cache logic unchanged from frontend_ii.
Qt signal emissions added for post-search hooks (no Tkinter event_bus calls).
"""
from typing import List, Dict, Any, Optional
from threading import Lock
from datetime import datetime, timedelta

from api.verification_client import verification_client
from utils.validators import sanitize_input
from utils.error_translator import error_translator
from utils.logger import logger


class MerchantService:
    """
    Business-logic service for merchant data operations.

    All methods are blocking — use ApiWorker for background calls.
    """

    def __init__(self):
        self._lock = Lock()
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(seconds=30)

    def search_merchants(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Universal merchant search.  Uses ?q= parameter for partial matching.

        Returns list of merchant dicts.  Each dict contains:
          merchant_id   — UUID (use in all API payloads)
          back_end_mid  — processor MID (display only)
          dba           — business name (display)
          contact_email — email
          contact_phone — phone
        """
        logger.info(f"[MerchantService] search: {query!r}")

        if not query or len(query) < 2:
            return []

        query = sanitize_input(query)

        response = verification_client.universal_search(
            query=query,
            page=page,
            page_size=page_size,
        )

        if response.success:
            data = response.data or {}
            results = data.get('results', [])
            logger.info(f"[MerchantService] {len(results)} results for {query!r}")
            return results
        else:
            err = error_translator.translate(response.error)
            logger.error(f"[MerchantService] Search failed: {err}")
            return []

    def format_merchant_display(self, merchant: Dict[str, Any]) -> str:
        """Format merchant for list display."""
        if not merchant:
            return "No merchant data"
        name = merchant.get('dba', merchant.get('name', 'Unknown'))
        mid = merchant.get('back_end_mid', 'N/A')
        email = merchant.get('contact_email', 'N/A')
        return f"{name} ({mid}) - {email}"

    def invalidate_merchant(self, merchant_id: str) -> None:
        """Remove specific merchant from cache."""
        with self._lock:
            for key in [f"merchant_{merchant_id}", f"customer_{merchant_id}"]:
                self._cache.pop(key, None)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
        logger.info("Merchant cache cleared")

    # ------------------------------------------------------------------
    # Internal cache helpers
    # ------------------------------------------------------------------

    def _get_from_cache(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, ts = self._cache[key]
                if datetime.now() - ts < self._cache_ttl:
                    return value
                del self._cache[key]
        return None

    def _add_to_cache(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (value, datetime.now())
            if len(self._cache) > 100:
                self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        now = datetime.now()
        expired = [k for k, (_, ts) in self._cache.items()
                   if now - ts >= self._cache_ttl]
        for k in expired:
            del self._cache[k]


# Global singleton
merchant_service = MerchantService()
