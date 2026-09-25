# -*- coding: utf-8 -*-
"""Né-rouge guards for #2655 — le chargeur nomme la cause d'un déchiffrement raté.

Depuis #2654, le second élément est un message d'erreur (`None` en succès) et
la branche chiffrée déchiffre réellement. Mais quand le fichier chiffré existe
et que le déchiffrement échoue, le chargeur rend « Aucun fichier de définitions
trouvé » — il perd la cause que `CryptoService.last_error` détient pourtant
déjà, et conduit l'opérateur (`cleanup_sensitive_files`, `restore_config`) à
lire « pas de fichier » là où la clé est fausse.

Fixtures synthétiques uniquement (passphrase de test, `tmp_path`) — #2639/#2655.
"""

import gzip
import json
import logging
from pathlib import Path

TEST_PASSPHRASE = "test_passphrase_2655"

SYNTHETIC_DEFINITIONS = [
    {
        "source_name": "synthetic_source_2655",
        "source_type": "url",
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/test",
        "extracts": [{"name": "extract_1"}],
    }
]


def _derive_test_key(passphrase: str = TEST_PASSPHRASE) -> bytes:
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    key = derive_encryption_key(passphrase)
    assert key is not None, "la dérivation de la clé de test a échoué"
    return key


def _write_synthetic_encrypted(target: Path) -> None:
    from argumentation_analysis.core.utils.crypto_utils import (
        encrypt_data_with_fernet,
    )

    payload = gzip.compress(json.dumps(SYNTHETIC_DEFINITIONS).encode("utf-8"))
    target.write_bytes(encrypt_data_with_fernet(payload, _derive_test_key()))


def test_wrong_key_names_the_file_and_the_cause(tmp_path: Path) -> None:
    """Fichier chiffré présent + mauvaise clé : le message nomme fichier et cause.

    Né-rouge attendu : « Aucun fichier de définitions trouvé » alors que le
    fichier existe et que la cause (`bad-token`) est connue.
    """
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    _write_synthetic_encrypted(enc_file)
    wrong_key = _derive_test_key("another_passphrase_2655")

    defs, message = load_extract_definitions_safely(enc_file, wrong_key)

    assert defs == []
    assert message is not None
    assert str(enc_file) in message, "le message doit nommer le fichier"
    assert (
        "bad-token" in message
    ), f"le message doit nommer la cause du déchiffrement, reçu: {message!r}"


def test_malformed_key_names_invalid_key(tmp_path: Path) -> None:
    """Une clé mal formée est un défaut de configuration, nommé comme tel."""
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    _write_synthetic_encrypted(enc_file)

    defs, message = load_extract_definitions_safely(enc_file, "not-a-fernet-key")

    assert defs == []
    assert message is not None
    assert (
        "invalid-key" in message
    ), f"clé mal formée et mauvais jeton ne doivent pas se confondre, reçu: {message!r}"


def test_missing_key_says_so_and_never_reads_a_stale_cause(tmp_path: Path) -> None:
    """Fichier chiffré présent sans clé : le message dit la clé absente.

    La cause ne doit pas être lue : `crypto_service` est un singleton, et un
    appel précédent y a laissé `bad-token`. Le chargeur amorce donc la cause
    par un vrai échec avant l'appel sans clé.
    """
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    _write_synthetic_encrypted(enc_file)

    # Amorce : un premier appel en échec laisse une cause dans le singleton.
    load_extract_definitions_safely(enc_file, _derive_test_key("prime_passphrase_2655"))

    defs, message = load_extract_definitions_safely(enc_file, None)

    assert defs == []
    assert message is not None
    assert (
        "clé" in message.lower()
    ), f"le message doit dire que la clé manque, reçu: {message!r}"
    assert (
        "bad-token" not in message
    ), f"une cause périmée ne doit pas être lue, reçu: {message!r}"


def test_fallback_after_failed_decryption_warns_with_the_cause(
    tmp_path: Path, caplog
) -> None:
    """Le repli JSON ne doit pas masquer une mauvaise clé en silence.

    Le chargement réussit par le repli (`(defs, None)`), mais l'échec du
    déchiffrement est journalisé en WARNING avec sa cause.
    """
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    _write_synthetic_encrypted(enc_file)
    fallback = tmp_path / "defs.json"
    fallback.write_text(json.dumps(SYNTHETIC_DEFINITIONS), encoding="utf-8")
    wrong_key = _derive_test_key("another_passphrase_2655b")

    with caplog.at_level(logging.WARNING, logger="UI.ExtractUtils"):
        defs, message = load_extract_definitions_safely(
            enc_file, wrong_key, fallback_json_file=fallback
        )

    assert defs == SYNTHETIC_DEFINITIONS
    assert message is None, "un succès par le repli reste un succès silencieux"
    assert (
        "bad-token" in caplog.text
    ), f"l'échec du déchiffrement doit être journalisé avec sa cause, reçu: {caplog.text!r}"


def test_missing_files_keep_the_literal_message(tmp_path: Path) -> None:
    """Contre-pendule : « Aucun fichier » reste le cas littéral (rien n'existe)."""
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    defs, message = load_extract_definitions_safely(
        tmp_path / "absent.enc", _derive_test_key(), tmp_path / "absent.json"
    )

    assert defs == []
    assert message == "Aucun fichier de définitions trouvé"
