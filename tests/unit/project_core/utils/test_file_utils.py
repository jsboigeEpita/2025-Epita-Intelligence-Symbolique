# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de fichiers."""

import json
import tempfile
from pathlib import Path
import pytest # Ajout de l'import pytest

from project_core.utils.file_utils import load_json_file, load_extracts, load_base_analysis_results

# Fixture pour créer un répertoire temporaire pour les tests
@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

def test_load_json_file_list_success(temp_dir):
    """Teste le chargement réussi d'un fichier JSON contenant une liste."""
    sample_data = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]
    file_path = temp_dir / "sample_list.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    loaded_data = load_json_file(file_path)
    assert loaded_data == sample_data

def test_load_json_file_dict_success(temp_dir):
    """Teste le chargement réussi d'un fichier JSON contenant un dictionnaire."""
    sample_data = {"config_key": "value", "number": 123}
    file_path = temp_dir / "sample_dict.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    loaded_data = load_json_file(file_path)
    assert loaded_data == sample_data

def test_load_json_file_not_found(temp_dir, caplog):
    """Teste le cas où le fichier JSON n'existe pas."""
    file_path = temp_dir / "non_existent.json"
    loaded_data = load_json_file(file_path)
    assert loaded_data is None
    assert f"Fichier non trouvé: {file_path}" in caplog.text

def test_load_json_file_decode_error(temp_dir, caplog):
    """Teste le cas où le fichier JSON est malformé."""
    file_path = temp_dir / "malformed.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("this is not json")

    loaded_data = load_json_file(file_path)
    assert loaded_data is None
    assert f"Erreur de décodage JSON dans {file_path}" in caplog.text

def test_load_extracts_success(temp_dir):
    """Teste le chargement réussi avec load_extracts (qui attend une liste)."""
    sample_extracts = [{"id": "extract1", "content": "Some text"}, {"id": "extract2", "content": "More text"}]
    file_path = temp_dir / "extracts.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_extracts, f)

    loaded_extracts = load_extracts(file_path)
    assert loaded_extracts == sample_extracts

def test_load_extracts_file_not_found(temp_dir, caplog):
    """Teste load_extracts quand le fichier n'existe pas."""
    file_path = temp_dir / "non_existent_extracts.json"
    loaded_extracts = load_extracts(file_path)
    assert loaded_extracts == []
    assert f"Fichier non trouvé: {file_path}" in caplog.text # Vérifie que load_json_file a loggué l'erreur

def test_load_extracts_decode_error(temp_dir, caplog):
    """Teste load_extracts quand le JSON est malformé."""
    file_path = temp_dir / "malformed_extracts.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("not a valid json list")
    
    loaded_extracts = load_extracts(file_path)
    assert loaded_extracts == []
    assert f"Erreur de décodage JSON dans {file_path}" in caplog.text

def test_load_extracts_returns_list_even_if_dict_loaded(temp_dir, caplog):
    """Teste que load_extracts retourne une liste vide si le JSON est un dict."""
    sample_data = {"config_key": "value"}
    file_path = temp_dir / "dict_for_extracts.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    loaded_extracts = load_extracts(file_path)
    assert loaded_extracts == []
    assert f"Les données chargées depuis {file_path} ne sont pas une liste comme attendu pour des extraits." in caplog.text
def test_load_base_analysis_results_success(temp_dir):
    """Teste le chargement réussi avec load_base_analysis_results (qui attend une liste)."""
    sample_results = [{"analysis_id": "base1", "score": 0.8}, {"analysis_id": "base2", "score": 0.9}]
    file_path = temp_dir / "base_results.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_results, f)

    loaded_results = load_base_analysis_results(file_path)
    assert loaded_results == sample_results

def test_load_base_analysis_results_returns_list_even_if_dict_loaded(temp_dir, caplog):
    """Teste que load_base_analysis_results retourne une liste vide si le JSON est un dict."""
    sample_data = {"summary": "Overall good"}
    file_path = temp_dir / "dict_for_base_results.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f)

    loaded_results = load_base_analysis_results(file_path)
    assert loaded_results == []
    assert f"Les données chargées depuis {file_path} pour les résultats d'analyse de base ne sont pas une liste." in caplog.text