#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour l'utilitaire de lazy loading de la taxonomie des sophismes.
Ce script vérifie que le fichier de taxonomie peut être correctement téléchargé et validé.
"""

import codecs
import csv
import json
import os
import logging
from pathlib import Path

import pytest

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TestTaxonomyLoader")

from argumentation_analysis.paths import DATA_DIR

# Import de l'utilitaire de lazy loading
from argumentation_analysis.utils.taxonomy_loader import (
    TAXONOMY_FILE,
    TAXONOMY_REGIME_ENV,
    TaxonomyLoader,
    get_taxonomy_path,
    get_taxonomy_regime,
    get_taxonomy_source_for_regime,
    validate_taxonomy_file,
)


def test_taxonomy_loader():
    """
    Teste l'utilitaire de lazy loading de la taxonomie des sophismes.
    """
    logger.info("Test de l'utilitaire de lazy loading de la taxonomie...")

    try:
        # Obtenir le chemin du fichier de taxonomie
        taxonomy_path = get_taxonomy_path()
        logger.info(f"Chemin du fichier de taxonomie: {taxonomy_path}")

        # Vérifier que le fichier existe
        assert os.path.exists(
            taxonomy_path
        ), f"Le fichier de taxonomie n'existe pas: {taxonomy_path}"

        # Vérifier la taille du fichier
        file_size = os.path.getsize(taxonomy_path)
        logger.info(f"Taille du fichier de taxonomie: {file_size} octets")

        assert file_size > 0, "Le fichier de taxonomie est vide"

        # Valider le fichier
        is_valid = validate_taxonomy_file()
        logger.info(f"Validation du fichier de taxonomie: {is_valid}")

        assert is_valid is True, "La validation du fichier de taxonomie a échoué"

    except Exception as e:
        logger.error(f"Erreur lors du test de l'utilitaire de lazy loading: {e}")
        raise


# --- #2141 temps 2: the funnel is a parameter, and its default is the old behaviour ---


def test_regime_defaults_to_one_shot_when_unset(monkeypatch):
    monkeypatch.delenv(TAXONOMY_REGIME_ENV, raising=False)
    assert get_taxonomy_regime() == "one_shot"


def test_regime_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv(TAXONOMY_REGIME_ENV, "funnel")
    assert get_taxonomy_regime() == "funnel"


def test_regime_ignores_case_and_surrounding_space(monkeypatch):
    monkeypatch.setenv(TAXONOMY_REGIME_ENV, "  FUNNEL  ")
    assert get_taxonomy_regime() == "funnel"


def test_unknown_regime_is_ignored_not_honoured(monkeypatch, caplog):
    """A typo must not look like a working config: it warns, then defaults."""
    monkeypatch.setenv(TAXONOMY_REGIME_ENV, "funnell")
    with caplog.at_level(logging.WARNING):
        assert get_taxonomy_regime() == "one_shot"
    warnings = " ".join(r.message for r in caplog.records)
    assert TAXONOMY_REGIME_ENV in warnings
    assert "funnel" in warnings and "one_shot" in warnings


def test_one_shot_regime_hands_the_funnel_no_taxonomy(monkeypatch):
    monkeypatch.setenv(TAXONOMY_REGIME_ENV, "one_shot")
    assert get_taxonomy_source_for_regime() is None


def test_unset_regime_hands_the_funnel_no_taxonomy(monkeypatch):
    monkeypatch.delenv(TAXONOMY_REGIME_ENV, raising=False)
    assert get_taxonomy_source_for_regime() is None


def test_funnel_regime_hands_the_funnel_the_resolved_path(monkeypatch):
    sentinel = Path("some") / "taxonomy.csv"
    monkeypatch.setattr(
        "argumentation_analysis.utils.taxonomy_loader.get_taxonomy_path",
        lambda: sentinel,
    )
    # A str, because the call sites declare their taxonomy parameter as str.
    assert get_taxonomy_source_for_regime("funnel") == str(sentinel)


# --- #2346: no simulated mode, and a read failure is not replaced by invented entries ---


def test_load_taxonomy_reads_every_row_of_the_vendored_file():
    with open(TAXONOMY_FILE, encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if any(row.values())]

    entries = TaxonomyLoader().load_taxonomy()

    assert len(entries) == len(rows)
    assert [e["PK"] for e in entries] == [r["PK"].strip() for r in rows]


def test_load_taxonomy_raises_when_the_file_cannot_be_read(monkeypatch, tmp_path):
    """The loader used to return five invented fallacies here, logged as a warning."""
    missing = tmp_path / "absent.csv"
    monkeypatch.setattr(
        "argumentation_analysis.utils.taxonomy_loader.get_taxonomy_path",
        lambda: missing,
    )

    with pytest.raises(FileNotFoundError):
        TaxonomyLoader().load_taxonomy()


# --- #2346: a missing copy is downloaded at the pinned commit, and checked ---


def _serve(monkeypatch, body, calls):
    """``requests.get`` answers ``body`` and records each call, with no network."""
    import requests

    class _Response:
        content = body

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr(requests, "get", fake_get)


def test_a_missing_copy_is_downloaded_at_the_pinned_commit(monkeypatch, tmp_path):
    """The download used to fetch ``master``, with no timeout, and write whatever
    came back. Upstream ``master`` has moved past the pinned commit."""
    vendored = TAXONOMY_FILE.read_bytes()
    target = tmp_path / TAXONOMY_FILE.name
    monkeypatch.setattr(
        "argumentation_analysis.utils.taxonomy_loader.TAXONOMY_FILE", target
    )
    calls = []
    _serve(monkeypatch, codecs.BOM_UTF8 + vendored, calls)

    assert get_taxonomy_path() == target

    provenance = DATA_DIR / "argumentum_taxonomy_provenance.json"
    pin = json.loads(provenance.read_text(encoding="utf-8"))["fallacies"]
    [(url, kwargs)] = calls
    assert f"/{pin['upstream_commit']}/" in url
    assert "/master/" not in url
    assert kwargs.get("timeout")
    assert target.read_bytes() == vendored


def test_a_download_with_another_fingerprint_is_not_written(monkeypatch, tmp_path):
    target = tmp_path / TAXONOMY_FILE.name
    monkeypatch.setattr(
        "argumentation_analysis.utils.taxonomy_loader.TAXONOMY_FILE", target
    )
    _serve(monkeypatch, b"PK,path\n1,1\n", [])

    with pytest.raises(ValueError, match="empreinte"):
        get_taxonomy_path()

    assert list(tmp_path.iterdir()) == []


if __name__ == "__main__":
    result = test_taxonomy_loader()
    print(f"\nRésultat du test: {'SUCCÈS' if result else 'ÉCHEC'}")
