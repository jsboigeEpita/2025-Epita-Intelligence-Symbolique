# tests/unit/argumentation_analysis/services/test_crypto_service.py
"""Tests for CryptoService — encryption, decryption, key management."""

import pytest
from cryptography.fernet import Fernet

from argumentation_analysis.services.crypto_service import CryptoService


@pytest.fixture
def key():
    return Fernet.generate_key()


@pytest.fixture
def svc(key):
    return CryptoService(encryption_key=key)


@pytest.fixture
def svc_no_key():
    return CryptoService()


# ── Init ──


class TestInit:
    def test_init_with_key(self, key):
        svc = CryptoService(encryption_key=key)
        assert svc.encryption_key == key
        assert svc.is_encryption_enabled() is True

    def test_init_without_key(self):
        svc = CryptoService()
        assert svc.encryption_key is None
        assert svc.is_encryption_enabled() is False

    def test_default_salt(self):
        svc = CryptoService()
        assert svc.fixed_salt is not None
        assert len(svc.fixed_salt) == 16

    def test_custom_salt(self):
        salt = b"custom_salt_1234"
        svc = CryptoService(fixed_salt=salt)
        assert svc.fixed_salt == salt


# ── Key management ──


class TestKeyManagement:
    def test_set_encryption_key(self, svc_no_key, key):
        svc_no_key.set_encryption_key(key)
        assert svc_no_key.encryption_key == key
        assert svc_no_key.is_encryption_enabled() is True

    def test_generate_key(self, svc):
        new_key = svc.generate_key()
        assert isinstance(new_key, bytes)
        assert len(new_key) > 0
        # Should be a valid Fernet key
        Fernet(new_key)

    def test_generate_static_key(self):
        key = CryptoService.generate_static_key()
        assert isinstance(key, bytes)
        Fernet(key)  # Valid Fernet key

    def test_derive_key_from_passphrase(self, svc):
        derived = svc.derive_key_from_passphrase("my_secret_passphrase")
        assert derived is not None
        assert isinstance(derived, bytes)
        # Should be a valid Fernet key
        Fernet(derived)

    def test_derive_key_empty_passphrase(self, svc):
        assert svc.derive_key_from_passphrase("") is None

    def test_derive_key_deterministic(self, svc):
        k1 = svc.derive_key_from_passphrase("same_passphrase", iterations=1000)
        k2 = svc.derive_key_from_passphrase("same_passphrase", iterations=1000)
        assert k1 == k2

    def test_derive_key_different_passphrases(self, svc):
        k1 = svc.derive_key_from_passphrase("pass1", iterations=1000)
        k2 = svc.derive_key_from_passphrase("pass2", iterations=1000)
        assert k1 != k2

    def test_save_and_load_key(self, svc, key, tmp_path):
        key_file = str(tmp_path / "test_key.bin")
        assert svc.save_key(key, key_file) is True
        loaded = svc.load_key(key_file)
        assert loaded == key

    def test_save_key_bad_path(self, svc, key):
        # Use a truly non-existent path - Windows UNC path to non-existent server
        # (or use a drive letter that's unlikely to exist)
        bad_path = "Z:\\this_drive_does_not_exist\\path\\key.bin"
        assert svc.save_key(key, bad_path) is False

    def test_load_key_nonexistent(self, svc):
        # Use a truly non-existent path
        bad_path = "Z:\\this_drive_does_not_exist\\path\\key.bin"
        assert svc.load_key(bad_path) is None


# ── Encrypt / Decrypt ──


class TestEncryptDecrypt:
    def test_roundtrip(self, svc):
        data = b"Hello, World!"
        encrypted = svc.encrypt_data(data)
        assert encrypted is not None
        assert encrypted != data
        decrypted = svc.decrypt_data(encrypted)
        assert decrypted == data

    def test_encrypt_no_key(self, svc_no_key):
        assert svc_no_key.encrypt_data(b"data") is None

    def test_decrypt_no_key(self, svc_no_key):
        assert svc_no_key.decrypt_data(b"data") is None

    def test_decrypt_wrong_key(self, svc, key):
        encrypted = svc.encrypt_data(b"secret")
        wrong_key = Fernet.generate_key()
        assert svc.decrypt_data(encrypted, key=wrong_key) is None

    def test_decrypt_corrupted_data(self, svc):
        assert svc.decrypt_data(b"not_valid_encrypted") is None

    def test_encrypt_with_explicit_key(self, svc_no_key):
        explicit_key = Fernet.generate_key()
        encrypted = svc_no_key.encrypt_data(b"data", key=explicit_key)
        assert encrypted is not None
        decrypted = svc_no_key.decrypt_data(encrypted, key=explicit_key)
        assert decrypted == b"data"

    def test_encrypt_empty_data(self, svc):
        encrypted = svc.encrypt_data(b"")
        assert encrypted is not None
        decrypted = svc.decrypt_data(encrypted)
        assert decrypted == b""

    def test_encrypt_large_data(self, svc):
        data = b"x" * 100000
        encrypted = svc.encrypt_data(data)
        decrypted = svc.decrypt_data(encrypted)
        assert decrypted == data


# ── JSON encrypt/compress ──


class TestJsonEncryptCompress:
    def test_roundtrip_dict(self, svc):
        data = {"key": "value", "count": 42, "nested": {"a": 1}}
        encrypted = svc.encrypt_and_compress_json(data)
        assert encrypted is not None
        recovered = svc.decrypt_and_decompress_json(encrypted)
        assert recovered == data

    def test_roundtrip_list(self, svc):
        data = [1, 2, 3, "hello", {"nested": True}]
        encrypted = svc.encrypt_and_compress_json(data)
        recovered = svc.decrypt_and_decompress_json(encrypted)
        assert recovered == data

    def test_encrypt_json_no_key(self, svc_no_key):
        assert svc_no_key.encrypt_and_compress_json({"k": "v"}) is None

    def test_decrypt_json_no_key(self, svc_no_key):
        assert svc_no_key.decrypt_and_decompress_json(b"data") is None

    def test_decrypt_json_corrupted(self, svc):
        assert svc.decrypt_and_decompress_json(b"bad_data") is None

    def test_unicode_data(self, svc):
        data = {"message": "Bonjour le monde", "emoji": "Test accent: e"}
        encrypted = svc.encrypt_and_compress_json(data)
        recovered = svc.decrypt_and_decompress_json(encrypted)
        assert recovered == data

    def test_large_json(self, svc):
        data = {"items": [{"id": i, "value": f"item_{i}"} for i in range(1000)]}
        encrypted = svc.encrypt_and_compress_json(data)
        recovered = svc.decrypt_and_decompress_json(encrypted)
        assert recovered == data
