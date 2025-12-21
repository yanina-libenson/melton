"""Unit tests for encryption utilities."""

import pytest

from app.utils.encryption import EncryptionService


def test_encrypt_decrypt():
    """Test encryption and decryption."""
    service = EncryptionService()

    plaintext = "my-secret-api-key"
    encrypted = service.encrypt(plaintext)

    assert encrypted != plaintext
    assert len(encrypted) > 0

    decrypted = service.decrypt(encrypted)
    assert decrypted == plaintext


def test_decrypt_invalid_data():
    """Test decrypting invalid data raises error."""
    service = EncryptionService()

    with pytest.raises(ValueError, match="Decryption failed"):
        service.decrypt("invalid-encrypted-data")


def test_encrypt_different_values_produce_different_ciphertexts():
    """Test that encrypting different values produces different ciphertexts."""
    service = EncryptionService()

    encrypted1 = service.encrypt("value1")
    encrypted2 = service.encrypt("value2")

    assert encrypted1 != encrypted2


def test_encrypt_same_value_produces_different_ciphertexts():
    """Test that encrypting the same value twice produces different ciphertexts."""
    service = EncryptionService()

    encrypted1 = service.encrypt("same-value")
    encrypted2 = service.encrypt("same-value")

    # Fernet encryption includes a timestamp, so same plaintext produces different ciphertext
    assert encrypted1 != encrypted2

    # But both decrypt to the same value
    assert service.decrypt(encrypted1) == "same-value"
    assert service.decrypt(encrypted2) == "same-value"
