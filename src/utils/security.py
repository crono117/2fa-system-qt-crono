"""
Security utilities for credential management and data protection.
"""
import os
import json
import base64
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.settings import settings
from utils.logger import logger


class CredentialManager:
    """
    Secure credential storage and retrieval.
    Uses system keyring when available, falls back to encrypted local storage.
    """
    
    def __init__(self):
        self.service_name = settings.CREDENTIAL_STORE_SERVICE
        self._encryption_key: Optional[bytes] = None
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption for local credential storage."""
        if not settings.ENCRYPT_LOCAL_DATA:
            return
        
        try:
            # Try to get key from keyring first
            if KEYRING_AVAILABLE:
                key_b64 = keyring.get_password(self.service_name, "encryption_key")
                if key_b64:
                    self._encryption_key = base64.b64decode(key_b64)
                    return
            
            # Generate new key and store it
            self._encryption_key = self._generate_key()
            
            if KEYRING_AVAILABLE:
                key_b64 = base64.b64encode(self._encryption_key).decode()
                keyring.set_password(self.service_name, "encryption_key", key_b64)
            else:
                logger.warning("Keyring not available, using weaker local key storage")
                self._store_key_locally()
        
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._encryption_key = None
    
    def _generate_key(self) -> bytes:
        """Generate encryption key."""
        return Fernet.generate_key()
    
    def _store_key_locally(self):
        """Store encryption key locally (less secure fallback)."""
        key_file = settings.CONFIG_DIR / ".key"
        key_b64 = base64.b64encode(self._encryption_key).decode()
        
        try:
            key_file.write_text(key_b64, encoding='utf-8')
            # Set restrictive permissions (Unix-like systems)
            if hasattr(os, 'chmod'):
                os.chmod(key_file, 0o600)
        except Exception as e:
            logger.error(f"Failed to store encryption key: {e}")
    
    def _load_key_locally(self) -> Optional[bytes]:
        """Load encryption key from local storage."""
        key_file = settings.CONFIG_DIR / ".key"
        
        try:
            if key_file.exists():
                key_b64 = key_file.read_text(encoding='utf-8').strip()
                return base64.b64decode(key_b64)
        except Exception as e:
            logger.error(f"Failed to load encryption key: {e}")
        
        return None
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt string data."""
        if not self._encryption_key:
            return data  # No encryption available
        
        try:
            fernet = Fernet(self._encryption_key)
            encrypted = fernet.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        if not self._encryption_key:
            return encrypted_data  # No encryption available
        
        try:
            fernet = Fernet(self._encryption_key)
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def store_credentials(self, username: str, password: str) -> bool:
        """
        Store user credentials securely.
        
        Args:
            username: Username to store
            password: Password to store
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if KEYRING_AVAILABLE:
                # Use system keyring (most secure)
                keyring.set_password(self.service_name, username, password)
                keyring.set_password(self.service_name, "last_username", username)
                logger.info("Credentials stored in system keyring")
                return True
            else:
                # Fallback to encrypted local storage
                credentials = {
                    "username": username,
                    "password": self._encrypt_data(password)
                }
                
                creds_file = settings.CONFIG_DIR / ".credentials"
                settings.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                
                with open(creds_file, 'w', encoding='utf-8') as f:
                    json.dump(credentials, f)
                
                # Set restrictive permissions
                if hasattr(os, 'chmod'):
                    os.chmod(creds_file, 0o600)
                
                logger.info("Credentials stored in encrypted local file")
                return True
        
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False
    
    def get_credentials(self) -> Optional[Dict[str, str]]:
        """
        Retrieve stored credentials.
        
        Returns:
            Dictionary with 'username' and 'password' keys, or None if not found
        """
        try:
            if KEYRING_AVAILABLE:
                username = keyring.get_password(self.service_name, "last_username")
                if username:
                    password = keyring.get_password(self.service_name, username)
                    if password:
                        return {"username": username, "password": password}
            else:
                # Try local encrypted storage
                creds_file = settings.CONFIG_DIR / ".credentials"
                if creds_file.exists():
                    with open(creds_file, 'r', encoding='utf-8') as f:
                        credentials = json.load(f)
                    
                    username = credentials.get("username")
                    encrypted_password = credentials.get("password")
                    
                    if username and encrypted_password:
                        password = self._decrypt_data(encrypted_password)
                        return {"username": username, "password": password}
        
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
        
        return None
    
    def clear_credentials(self) -> bool:
        """
        Clear stored credentials.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if KEYRING_AVAILABLE:
                # Clear from keyring
                last_username = keyring.get_password(self.service_name, "last_username")
                if last_username:
                    try:
                        keyring.delete_password(self.service_name, last_username)
                    except keyring.errors.PasswordDeleteError:
                        pass  # Password might not exist
                
                try:
                    keyring.delete_password(self.service_name, "last_username")
                except keyring.errors.PasswordDeleteError:
                    pass
                
                logger.info("Credentials cleared from keyring")
            
            # Clear local storage
            creds_file = settings.CONFIG_DIR / ".credentials"
            if creds_file.exists():
                creds_file.unlink()
                logger.info("Local credentials file deleted")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")
            return False
    
    def has_stored_credentials(self) -> bool:
        """Check if credentials are stored."""
        try:
            if KEYRING_AVAILABLE:
                username = keyring.get_password(self.service_name, "last_username")
                if username:
                    password = keyring.get_password(self.service_name, username)
                    return password is not None
            
            # Check local storage
            creds_file = settings.CONFIG_DIR / ".credentials"
            return creds_file.exists()
        
        except Exception:
            return False


class DataProtection:
    """Utility class for data protection and validation."""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        if not isinstance(text, str):
            return str(text)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
        
        # Limit length to prevent DoS
        return sanitized[:1000]  # Reasonable limit
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """
        Mask sensitive data for display purposes.
        
        Args:
            data: Sensitive data to mask
            mask_char: Character to use for masking
            visible_chars: Number of characters to show at the end
        
        Returns:
            Masked string
        """
        if not data or len(data) <= visible_chars:
            return mask_char * len(data) if data else ""
        
        return mask_char * (len(data) - visible_chars) + data[-visible_chars:]
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Basic phone number validation."""
        import re
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        # Check if it's a reasonable length (10-15 digits)
        return 10 <= len(digits_only) <= 15