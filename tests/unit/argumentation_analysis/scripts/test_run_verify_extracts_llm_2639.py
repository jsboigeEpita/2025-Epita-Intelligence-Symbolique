# -*- coding: utf-8 -*-
"""Né-rouge guard for #2639 — le lanceur scripts/run_verify_extracts_llm.

Mesure de #2634 (chemin C) : le script ne va jamais au-delà du chargement —
il lit le message de succès du chargeur comme une erreur et return avant
``create_llm_service``. Ce témoin exige qu'un chargement chiffré valide
mène jusqu'au service LLM. Fixtures synthétiques uniquement (#2639).
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
    from argumentation_analysis.scripts import run_verify_extracts_llm as runner

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

    monkeypatch.setattr(runner, "ENCRYPTION_KEY", key)
    monkeypatch.setattr(runner, "CONFIG_FILE_JSON", tmp_path / "absent.json")
    monkeypatch.setattr(runner, "create_llm_service", fake_llm_service)
    monkeypatch.setattr(runner, "verify_extracts_with_llm", fake_verify)
    monkeypatch.setattr(runner, "generate_llm_report", fake_report)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_verify_extracts_llm",
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
