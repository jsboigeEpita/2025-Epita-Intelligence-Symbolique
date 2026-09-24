# -*- coding: utf-8 -*-
"""#2344 family (d) — CryptoService failure causes are named in the state.

``encrypt_data``/``decrypt_data`` (and their JSON wrappers) return ``None``
on ANY failure, conflating three distinct causes: no key configured, an
invalid/malformed key, and bad-token/corrupted data. The caller of
``definition_service`` (the production consumer) can only report a generic
"Échec du chiffrement/déchiffrement". Doctrine #1019: degrade, but tag the
cause IN THE STATE, not only in the log — ``last_error`` carries the named
cause ("no-key" / "invalid-key" / "bad-token" / ...) and is reset on
success (tri-state: no failure is not a measured failure).

Honesty note: Fernet cannot distinguish wrong-key from corrupted data — the
MAC fails the same way — so both surface as one honest cause ("bad-token").
"""

from cryptography.fernet import Fernet

from argumentation_analysis.services.crypto_service import CryptoService


class TestNamedFailureCauses:
    def test_encrypt_without_key_names_no_key(self):
        svc = CryptoService()
        assert svc.encrypt_data(b"data") is None
        assert svc.last_error == "no-key"

    def test_encrypt_with_malformed_key_names_invalid_key(self):
        svc = CryptoService(encryption_key=b"garbage-not-a-fernet-key")
        assert svc.encrypt_data(b"data") is None
        assert svc.last_error == "invalid-key"

    def test_decrypt_wrong_key_names_bad_token(self):
        svc = CryptoService(encryption_key=Fernet.generate_key())
        other = Fernet.generate_key()
        blob = Fernet(other).encrypt(b"secret")
        assert svc.decrypt_data(blob) is None
        assert svc.last_error == "bad-token"

    def test_decrypt_corrupted_blob_names_bad_token(self):
        svc = CryptoService(encryption_key=Fernet.generate_key())
        assert svc.decrypt_data(b"not-a-fernet-token") is None
        assert svc.last_error == "bad-token"

    def test_json_wrapper_propagates_the_decrypt_cause(self):
        svc = CryptoService(encryption_key=Fernet.generate_key())
        assert svc.decrypt_and_decompress_json(b"bad_data") is None
        assert svc.last_error == "bad-token"

    def test_success_resets_last_error(self):
        svc = CryptoService(encryption_key=Fernet.generate_key())
        assert svc.decrypt_data(b"bad") is None
        assert svc.last_error == "bad-token"
        encrypted = svc.encrypt_data(b"ok")
        assert encrypted is not None
        assert svc.decrypt_data(encrypted) == b"ok"
        assert svc.last_error is None, "a success must clear the stale failure"
