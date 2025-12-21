"""Encryption utilities for secure credential storage."""

import base64

from cryptography.fernet import Fernet

from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting credentials. Single responsibility."""

    def __init__(self) -> None:
        # Generate key from settings
        key = base64.urlsafe_b64encode(settings.encryption_key.encode().ljust(32)[:32])
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted_bytes).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted string.

        Args:
            encrypted_text: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Global instance
encryption_service = EncryptionService()
