"""Unit tests for apps/agent/services/encryption_service.py

Tests AES-256-GCM encryption / decryption:
- Encrypt/decrypt roundtrip returns original plaintext
- Encrypted ciphertext differs from plaintext
- Two encryptions of the same string produce different ciphertexts (random nonce)
- Decrypting with a wrong key raises an exception
- Missing ENCRYPTION_KEY env var raises RuntimeError on init
- Wrong-length key raises RuntimeError on init
- Empty string can be encrypted and decrypted
- Unicode strings are handled correctly
"""

import sys
import os
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

# A valid 32-byte key, base64-encoded
_VALID_KEY = base64.b64encode(b"a" * 32).decode()
# A different valid key for wrong-key tests
_OTHER_KEY = base64.b64encode(b"b" * 32).decode()
# A 16-byte key (invalid for AES-256)
_SHORT_KEY = base64.b64encode(b"a" * 16).decode()


def _make_service(key: str = _VALID_KEY):
    """Create an EncryptionService with the given base64 key."""
    with patch.dict(os.environ, {"ENCRYPTION_KEY": key}):
        from services.encryption_service import EncryptionService
        return EncryptionService()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove ENCRYPTION_KEY if present
            env = {k: v for k, v in os.environ.items() if k != "ENCRYPTION_KEY"}
            with patch.dict(os.environ, env, clear=True):
                from services import encryption_service
                import importlib
                with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
                    with patch.dict(os.environ, {"ENCRYPTION_KEY": ""}):
                        import importlib
                        import services.encryption_service as enc_mod
                        importlib.reload(enc_mod)
                        enc_mod.EncryptionService()

    def test_short_key_raises(self):
        with pytest.raises(RuntimeError, match="32 bytes"):
            _make_service(_SHORT_KEY)

    def test_valid_key_does_not_raise(self):
        svc = _make_service(_VALID_KEY)
        assert svc is not None


# ---------------------------------------------------------------------------
# Encrypt / Decrypt roundtrip
# ---------------------------------------------------------------------------

class TestRoundtrip:
    def test_basic_roundtrip(self):
        svc = _make_service()
        plaintext = "postgresql://user:password@host:5432/mydb"
        encrypted = svc.encrypt(plaintext)
        decrypted = svc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_empty_string_roundtrip(self):
        svc = _make_service()
        encrypted = svc.encrypt("")
        assert svc.decrypt(encrypted) == ""

    def test_unicode_roundtrip(self):
        svc = _make_service()
        plaintext = "postgresql://user:pässwörd@host/db"
        assert svc.decrypt(svc.encrypt(plaintext)) == plaintext

    def test_long_connection_string_roundtrip(self):
        svc = _make_service()
        plaintext = "postgresql://someuser:s0me!C0mpl3xP@$$w0rd@very-long-hostname.example.com:5432/production_database?sslmode=require&sslrootcert=/etc/ssl/certs/ca-bundle.crt"
        assert svc.decrypt(svc.encrypt(plaintext)) == plaintext


# ---------------------------------------------------------------------------
# Ciphertext properties
# ---------------------------------------------------------------------------

class TestCiphertextProperties:
    def test_encrypted_differs_from_plaintext(self):
        svc = _make_service()
        plaintext = "postgresql://user:pass@host/db"
        encrypted = svc.encrypt(plaintext)
        assert encrypted != plaintext

    def test_two_encryptions_differ(self):
        """Random nonce means two encryptions of same string produce different output."""
        svc = _make_service()
        plaintext = "mysql://root:secret@localhost/mydb"
        enc1 = svc.encrypt(plaintext)
        enc2 = svc.encrypt(plaintext)
        assert enc1 != enc2

    def test_encrypted_is_base64(self):
        svc = _make_service()
        encrypted = svc.encrypt("test_connection_string")
        # Should not raise
        decoded = base64.b64decode(encrypted.encode())
        assert len(decoded) > 12  # nonce (12) + ciphertext + tag (16)


# ---------------------------------------------------------------------------
# Wrong-key decryption
# ---------------------------------------------------------------------------

class TestWrongKey:
    def test_wrong_key_raises_on_decrypt(self):
        svc_a = _make_service(_VALID_KEY)
        svc_b = _make_service(_OTHER_KEY)
        encrypted = svc_a.encrypt("mongodb://user:pass@host/db")
        with pytest.raises(Exception):
            svc_b.decrypt(encrypted)

    def test_tampered_ciphertext_raises(self):
        svc = _make_service()
        encrypted = svc.encrypt("redis://localhost:6379/0")
        # Flip a byte in the ciphertext
        raw = bytearray(base64.b64decode(encrypted.encode()))
        raw[-1] ^= 0xFF
        tampered = base64.b64encode(bytes(raw)).decode()
        with pytest.raises(Exception):
            svc.decrypt(tampered)
