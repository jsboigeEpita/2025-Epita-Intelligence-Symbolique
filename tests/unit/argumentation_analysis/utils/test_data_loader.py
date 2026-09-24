#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires de chargement de données de argumentation_analysis.utils.data_loader.
"""

import pytest
import json
from pathlib import Path
from typing import List, Dict, Any

# Ajuster le PYTHONPATH pour les tests
import sys

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

from argumentation_analysis.utils.data_loader import load_results_from_json


@pytest.fixture
def temp_json_file(tmp_path: Path) -> Path:
    """Crée un fichier JSON temporaire pour les tests."""
    file_path = tmp_path / "test_data.json"
    return file_path


def test_load_results_from_json_success(temp_json_file: Path):
    """Teste le chargement réussi d'un fichier JSON valide."""
    sample_data: List[Dict[str, Any]] = [
        {"id": 1, "name": "Test1"},
        {"id": 2, "name": "Test2"},
    ]
    with open(temp_json_file, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    loaded_data = load_results_from_json(temp_json_file)
    assert loaded_data == sample_data
    assert len(loaded_data) == 2


def test_load_results_from_json_empty_list(temp_json_file: Path):
    """Teste le chargement d'un fichier JSON contenant une liste vide."""
    sample_data: List[Dict[str, Any]] = []
    with open(temp_json_file, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    loaded_data = load_results_from_json(temp_json_file)
    assert loaded_data == []


def test_load_results_from_json_not_a_list(temp_json_file: Path):
    """Teste le chargement d'un fichier JSON qui ne contient pas une liste."""
    sample_data: Dict[str, Any] = {
        "id": 1,
        "name": "Test_dict",
    }  # Un dictionnaire, pas une liste
    with open(temp_json_file, "w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    # #2344 : une liste vide est un résultat, un contenu qui n'est pas une
    # liste est un fichier en échec — l'appelant ne doit pas les confondre.
    with pytest.raises(ValueError, match="liste JSON"):
        load_results_from_json(temp_json_file)


def test_load_results_from_json_file_not_found(tmp_path: Path):
    """Teste le cas où le fichier JSON n'existe pas."""
    with pytest.raises(FileNotFoundError, match="absent.json"):
        load_results_from_json(tmp_path / "absent.json")


def test_load_results_from_json_directory(tmp_path: Path):
    """Un répertoire n'est pas un fichier de résultats."""
    with pytest.raises(FileNotFoundError, match="n'est pas un fichier"):
        load_results_from_json(tmp_path)


def test_load_results_from_json_invalid_json(temp_json_file: Path):
    """Teste le chargement d'un fichier avec un contenu JSON invalide."""
    with open(temp_json_file, "w", encoding="utf-8") as f:
        f.write("ceci n'est pas du json valide {")

    with pytest.raises(json.JSONDecodeError):
        load_results_from_json(temp_json_file)
