# -*- coding: utf-8 -*-
"""Né-rouge guard for #2639 — le lanceur utils/run_verify_extracts_with_llm.

Jumeau du lanceur scripts/ : même lecture du message de succès comme une
erreur, même retour prématuré avant ``create_llm_service``. Ses imports
vivent DANS ``main()`` : les patchs visent donc les modules sources
(``ui.config``, ``core.llm_service``, ``extract_repair``). Fixtures
synthétiques uniquement (#2639).
"""

import asyncio
import gzip
import json
import sys
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


def _write_synthetic_encrypted(target: Path) -> bytes:
    from argumentation_analysis.core.utils.crypto_utils import (
        derive_encryption_key,
        encrypt_data_with_fernet,
    )

    key = derive_encryption_key(TEST_PASSPHRASE)
    assert key is not None, "la dérivation de la clé de test a échoué"
    payload = gzip.compress(json.dumps(SYNTHETIC_DEFINITIONS).encode("utf-8"))
    target.write_bytes(encrypt_data_with_fernet(payload, key))
    return key


def test_main_reaches_the_llm_service_after_encrypted_load(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Un chiffré valide ⇒ le script passe le chargement et crée le service.

    Né-rouge attendu sur l'arbre cassé : le script return au message lu
    comme erreur, ``create_llm_service`` n'est jamais appelé.
    """
    from argumentation_analysis.core import llm_service as llm_module
    from argumentation_analysis.ui import config as ui_config
    from argumentation_analysis.utils.extract_repair import (
        verify_extracts_with_llm as repair_module,
    )
    from argumentation_analysis.utils import run_verify_extracts_with_llm as runner

    enc_file = tmp_path / "extract_sources.json.gz.enc"
    key = _write_synthetic_encrypted(enc_file)

    calls = {"llm": 0, "verify": 0, "report": 0, "definitions": None}

    def fake_llm_service(*args, **kwargs):
        calls["llm"] += 1
        return object()

    async def fake_verify(definitions, llm_service):
        calls["verify"] += 1
        calls["definitions"] = definitions
        return []

    def fake_report(results, output):
        calls["report"] += 1

    monkeypatch.setattr(ui_config, "ENCRYPTION_KEY", key)
    monkeypatch.setattr(ui_config, "CONFIG_FILE_JSON", tmp_path / "absent.json")
    monkeypatch.setattr(llm_module, "create_llm_service", fake_llm_service)
    monkeypatch.setattr(repair_module, "verify_extracts_with_llm", fake_verify)
    monkeypatch.setattr(repair_module, "generate_report", fake_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_verify_extracts_with_llm",
            "--input",
            str(enc_file),
            "--output",
            "unused.html",
        ],
    )

    asyncio.run(runner.main())

    assert calls["llm"] == 1, "le service LLM doit être créé après un chargement valide"
    assert calls["verify"] == 1
    assert (
        calls["definitions"] == SYNTHETIC_DEFINITIONS
    ), "l'agent de vérification doit recevoir les définitions chargées"
    assert calls["report"] == 1
