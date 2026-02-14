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

    loaded_data = load_results_from_json(temp_json_file)
    # La fonction est censée retourner une liste vide si le contenu n'est pas une liste
    assert loaded_data == []


def test_load_results_from_json_file_not_found():
    """Teste le cas où le fichier JSON n'existe pas."""
    non_existent_file = Path("non_existent_test_file.json")
    loaded_data = load_results_from_json(non_existent_file)
    assert loaded_data == []


def test_load_results_from_json_invalid_json(temp_json_file: Path):
    """Teste le chargement d'un fichier avec un contenu JSON invalide."""
    with open(temp_json_file, "w", encoding="utf-8") as f:
        f.write("ceci n'est pas du json valide {")

    loaded_data = load_results_from_json(temp_json_file)
    assert loaded_data == []
