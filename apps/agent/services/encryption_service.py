import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:
    """AES-256-GCM encryption/decryption for database connection strings.

    The key must be a 32-byte (256-bit) secret stored as a base64-encoded
    string in the ENCRYPTION_KEY environment variable. Connection strings
    are never logged in decrypted form.
    """

    def __init__(self):
        key_b64 = os.environ.get("ENCRYPTION_KEY", "")
        if not key_b64:
            raise RuntimeError("ENCRYPTION_KEY environment variable is not set")
        key = base64.b64decode(key_b64)
        if len(key) != 32:
            raise RuntimeError(
                "ENCRYPTION_KEY must decode to exactly 32 bytes (256-bit AES key)"
            )
        self._key = key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a connection string. Returns a base64-encoded ciphertext."""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a connection string. Never log the return value."""
        payload = base64.b64decode(encrypted.encode("utf-8"))
        nonce = payload[:12]
        ciphertext = payload[12:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
