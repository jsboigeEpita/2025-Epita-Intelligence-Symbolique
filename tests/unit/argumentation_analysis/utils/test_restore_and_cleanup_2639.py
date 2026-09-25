# -*- coding: utf-8 -*-
"""Né-rouge guards for #2639 — restore_config et cleanup_sensitive_files.

Les deux scripts utilitaires appellent ``load_extract_definitions_safely``
et lisent tout message non vide comme un échec. Sur l'arbre cassé, aucun
chargement chiffré ne peut réussir (clé jamais dérivée + méthode fantôme
``decrypt_file``), donc ``restore_config_files()`` rend toujours False et
la porte de suppression de ``cleanup_sensitive_files`` ne s'ouvre jamais.

Fixtures 100 % synthétiques (passphrase de test, fichier chiffré écrit en
tmp_path). Le garde de suppression cible des chemins patchés — il ne touche
jamais les fichiers réels du dépôt.
"""

import gzip
import json
from pathlib import Path

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
    from argumentation_analysis.core.utils.crypto_utils import (
        encrypt_data_with_fernet,
    )

    key = _derive_test_key()
    payload = gzip.compress(json.dumps(SYNTHETIC_DEFINITIONS).encode("utf-8"))
    target.write_bytes(encrypt_data_with_fernet(payload, key))
    return key


def test_restore_config_succeeds_on_valid_encrypted_file(
    tmp_path: Path, monkeypatch
) -> None:
    """Un fichier chiffré valide + sa clé ⇒ la restauration rend True.

    Né-rouge attendu sur l'arbre cassé : le chargement échoue (message
    « Aucun fichier de définitions trouvé ») et la fonction rend False.
    """
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.utils import restore_config

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    key = _write_synthetic_encrypted(enc_file)
    target_json = tmp_path / "restored" / "extract_sources.json"

    monkeypatch.setattr(restore_config, "ENCRYPTION_KEY", key)
    monkeypatch.setattr(restore_config, "CONFIG_FILE_ENC", enc_file)
    monkeypatch.setattr(restore_config, "CONFIG_FILE_JSON", target_json)
    monkeypatch.setattr(settings, "project_root", tmp_path)

    assert (
        restore_config.restore_config_files() is True
    ), "un chargement chiffré valide doit aboutir à une restauration"
    restored = json.loads(target_json.read_text(encoding="utf-8"))
    assert restored == SYNTHETIC_DEFINITIONS


def test_cleanup_verify_accepts_valid_encrypted_file(
    tmp_path: Path, monkeypatch
) -> None:
    """La porte de vérification du nettoyage s'ouvre sur un chiffré valide.

    Né-rouge attendu sur l'arbre cassé : ``verify_encrypted_file`` rend
    False — la suppression reste donc armée mais jamais déclenchée.
    """
    from argumentation_analysis.utils import cleanup_sensitive_files as cleanup

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    key = _write_synthetic_encrypted(enc_file)

    monkeypatch.setattr(cleanup, "ENCRYPTION_KEY", key)
    monkeypatch.setattr(cleanup, "CONFIG_FILE_ENC", enc_file)

    assert cleanup.verify_encrypted_file() is True


def test_cleanup_delete_removes_exactly_the_plaintext_targets(
    tmp_path: Path, monkeypatch
) -> None:
    """Garde du chemin destructeur : la suppression ne vise que le JSON en
    clair patché et le cache de texte du périmètre patché — rien d'autre.

    ``__file__`` du module est détourné vers le scratchpad pour isoler la
    branche text_cache des vrais répertoires du dépôt.
    """
    from argumentation_analysis.utils import cleanup_sensitive_files as cleanup

    plaintext = tmp_path / "data" / "extract_sources.json"
    plaintext.parent.mkdir(parents=True)
    plaintext.write_text("plaintext à supprimer", encoding="utf-8")
    survivor = tmp_path / "data" / "autre_fichier.txt"
    survivor.write_text("ne doit pas être touché", encoding="utf-8")

    fake_module_dir = tmp_path / "pkg" / "utils"
    fake_module_dir.mkdir(parents=True)

    monkeypatch.setattr(cleanup, "CONFIG_FILE_JSON", plaintext)
    monkeypatch.setattr(cleanup, "__file__", str(fake_module_dir / "cleanup.py"))

    deleted = cleanup.delete_sensitive_files()

    assert str(plaintext) in deleted
    assert not plaintext.exists()
    assert survivor.exists(), "la suppression ne doit pas dépasser ses cibles"
