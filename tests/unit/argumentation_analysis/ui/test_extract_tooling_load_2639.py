# -*- coding: utf-8 -*-
"""Né-rouge guards for #2639 — the extract tooling load path.

Deux bris sur le même chemin, plus un troisième découvert au recensement :

1. ``load_extract_definitions_safely`` rend un message **non vide en cas de
   succès** ; quatre appelants sur cinq le lisent comme une erreur.
2. Les constantes ``ENCRYPTION_KEY`` (``ui/config.py``, ``restore_config``,
   ``cleanup_sensitive_files``) lisent ``settings.encryption_key`` — la
   variable d'environnement ``ENCRYPTION_KEY`` qu'aucun ``.env`` ne définit.
   La dérivation canonique part de la passphrase.
3. Le chargeur appelle ``crypto_service.decrypt_file`` / ``encrypt_file`` —
   des méthodes qui n'existent pas sur ``CryptoService`` (AttributeError
   avalée par le ``except`` du chargeur, repli silencieux).

Ces témoins restent synthétiques : passphrase de test, fichier chiffré
synthétique, jamais le dataset réel (discipline #2639).
"""

import gzip
import importlib
import json
from pathlib import Path

from pydantic import SecretStr

TEST_PASSPHRASE = "test_passphrase_2639"

SYNTHETIC_DEFINITIONS = [
    {
        "source_name": "synthetic_source_2639",
        "source_type": "url",
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/test",
        "extracts": [{"name": "extract_1"}],
    }
]


def _derive_test_key():
    from argumentation_analysis.core.utils.crypto_utils import (
        derive_encryption_key,
    )

    key = derive_encryption_key(TEST_PASSPHRASE)
    assert key is not None, "la dérivation de la clé de test a échoué"
    return key


def _write_synthetic_encrypted(target: Path) -> bytes:
    """Écrit un fichier chiffré synthétique ; renvoie la clé (bytes) utilisée."""
    from argumentation_analysis.core.utils.crypto_utils import (
        encrypt_data_with_fernet,
    )

    key = _derive_test_key()
    payload = gzip.compress(json.dumps(SYNTHETIC_DEFINITIONS).encode("utf-8"))
    target.write_bytes(encrypt_data_with_fernet(payload, key))
    return key


def test_encrypted_success_returns_none_message(tmp_path: Path) -> None:
    """Branche chiffrée : un chargement réussi ne rend plus de message.

    Né-rouge attendu sur l'arbre cassé : le chargeur appelle une méthode
    fantôme (``decrypt_file``), l'AttributeError est avalée et la fonction
    rend ``([], "Aucun fichier de définitions trouvé")``.
    """
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    key = _write_synthetic_encrypted(enc_file)

    defs, message = load_extract_definitions_safely(enc_file, key)

    assert (
        defs == SYNTHETIC_DEFINITIONS
    ), "la branche chiffrée doit livrer les définitions du fichier"
    assert (
        message is None
    ), f"un succès ne doit pas porter de message d'erreur, reçu: {message!r}"


def test_fallback_success_returns_none_message(tmp_path: Path) -> None:
    """Branche de repli JSON : même contrat — le succès ne dit rien.

    Né-rouge attendu sur l'arbre cassé : c'est la mesure de l'issue — le
    message de succès (« Définitions chargées depuis … ») est non vide et
    quatre appelants le lisent comme une erreur.
    """
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    fallback = tmp_path / "defs.json"
    fallback.write_text(json.dumps(SYNTHETIC_DEFINITIONS), encoding="utf-8")

    defs, message = load_extract_definitions_safely(
        tmp_path / "missing.enc", None, fallback_json_file=fallback
    )

    assert defs == SYNTHETIC_DEFINITIONS
    assert (
        message is None
    ), f"un succès ne doit pas porter de message d'erreur, reçu: {message!r}"


def test_total_failure_keeps_an_error_message(tmp_path: Path) -> None:
    """Contre-pendule : l'échec total garde un message non vide."""
    from argumentation_analysis.ui.extract_utils import load_extract_definitions_safely

    defs, message = load_extract_definitions_safely(tmp_path / "missing.enc", None)

    assert defs == []
    assert message, "un échec total doit toujours nommer la cause"


def test_ui_config_key_derives_from_passphrase(tmp_path: Path, monkeypatch) -> None:
    """La clé de compatibilité ``ui.config.ENCRYPTION_KEY`` vient de la
    passphrase (dérivation canonique), pas d'une variable d'environnement
    que rien ne définit.

    Né-rouge attendu sur l'arbre cassé : la constante vaut ``None`` même
    quand ``settings.passphrase`` est présent.
    """
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.ui import config as ui_config

    expected = _derive_test_key()
    original = ui_config.ENCRYPTION_KEY

    try:
        monkeypatch.setattr(settings, "passphrase", SecretStr(TEST_PASSPHRASE))
        importlib.reload(ui_config)
        assert (
            ui_config.ENCRYPTION_KEY == expected
        ), "ui.config.ENCRYPTION_KEY doit être la clé dérivée de la passphrase"
    finally:
        # Le reload a figé la valeur dérivée de la passphrase de test dans
        # le module : on restaure la valeur d'origine à la main (monkeypatch
        # ne couvre pas les effets d'importlib.reload).
        ui_config.ENCRYPTION_KEY = original
