# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de reporting."""

import pytest
import json
from pathlib import Path
from typing import List, Dict, Any, Union

from project_core.utils.reporting_utils import save_json_report, generate_json_report, save_text_report

@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Crée un répertoire de sortie temporaire pour les tests."""
    output_dir = tmp_path / "test_reports"
    # Pas besoin de le créer ici, la fonction testée doit le faire si nécessaire.
    return output_dir

def test_save_json_report_list_success(temp_output_dir: Path):
    """Teste la sauvegarde réussie d'une liste de dictionnaires."""
    sample_data: List[Dict[str, Any]] = [
        {"id": 1, "value": "test1", "nested": {"n_id": 10}},
        {"id": 2, "value": "test2", "nested": {"n_id": 20}}
    ]
    output_file = temp_output_dir / "report_list.json"

    result = save_json_report(sample_data, output_file)
    assert result is True
    assert output_file.exists()

    with open(output_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    assert loaded_data == sample_data

def test_save_json_report_dict_success(temp_output_dir: Path):
    """Teste la sauvegarde réussie d'un dictionnaire."""
    sample_data: Dict[str, Any] = {
        "report_title": "Mon Rapport",
        "version": 1.0,
        "items": [1, 2, 3],
        "config": {"enabled": True, "threshold": 0.5}
    }
    output_file = temp_output_dir / "report_dict.json"

    result = save_json_report(sample_data, output_file)
    assert result is True
    assert output_file.exists()

    with open(output_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    assert loaded_data == sample_data

def test_save_json_report_creates_parent_dir(tmp_path: Path):
    """Teste que le répertoire parent est créé si nécessaire."""
    deep_output_dir = tmp_path / "deep" / "nested" / "reports"
    # Le répertoire "deep/nested/reports" n'existe pas encore.
    output_file = deep_output_dir / "deep_report.json"
    sample_data = {"message": "hello"}

    result = save_json_report(sample_data, output_file)
    assert result is True
    assert output_file.exists()
    assert deep_output_dir.exists() # Vérifie que le répertoire parent a été créé

def test_generate_json_report_wrapper_success(temp_output_dir: Path):
    """Teste le wrapper generate_json_report pour un cas de succès."""
    sample_results: List[Dict[str, Any]] = [{"result_id": "res1", "data": "abc"}]
    output_file = temp_output_dir / "analysis_report.json"

    # generate_json_report ne retourne rien, on vérifie l'existence du fichier et son contenu.
    generate_json_report(sample_results, output_file) 
    assert output_file.exists()

    with open(output_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    assert loaded_data == sample_results

@patch('builtins.open', side_effect=IOError("Test permission error"))
def test_save_json_report_write_failure(mock_open, temp_output_dir: Path, caplog):
    """
    Teste la gestion d'une erreur lors de l'écriture du fichier.
    On mock 'open' pour simuler une IOError.
    """
    sample_data = {"error_test": True}
    output_file = temp_output_dir / "unwritable_report.json"
    
    # S'assurer que le répertoire parent existe pour que l'erreur vienne bien de open()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    result = save_json_report(sample_data, output_file)
    assert result is False
    assert not output_file.exists() # Le fichier ne devrait pas être créé en cas d'erreur d'écriture
    assert "Erreur lors de la sauvegarde des données JSON" in caplog.text
    assert "Test permission error" in caplog.text # Vérifie que l'erreur originale est loggée

@patch('builtins.open', side_effect=IOError("Test permission error generate"))
def test_generate_json_report_wrapper_failure(mock_open, temp_output_dir: Path, caplog):
    """Teste que generate_json_report logue une erreur si save_json_report échoue."""
    sample_results: List[Dict[str, Any]] = [{"result_id": "res_fail", "data": "xyz"}]
    output_file = temp_output_dir / "failing_analysis_report.json"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)

    generate_json_report(sample_results, output_file)
    # save_json_report retourne False et logue l'erreur.
    # generate_json_report logue un message d'échec supplémentaire.
    assert "Échec final de la génération du rapport JSON" in caplog.text
    assert "Test permission error generate" in caplog.text
# Tests for save_text_report
def test_save_text_report_success(temp_output_dir: Path):
    """Teste la sauvegarde réussie d'un rapport textuel."""
    report_content = "# Titre du Rapport\n\nCeci est le contenu.\nLigne multiple."
    output_file = temp_output_dir / "report.md"

    result = save_text_report(report_content, output_file)
    assert result is True
    assert output_file.exists()

    with open(output_file, 'r', encoding='utf-8') as f:
        loaded_content = f.read()
    assert loaded_content == report_content

def test_save_text_report_creates_parent_dir(tmp_path: Path):
    """Teste que le répertoire parent est créé pour save_text_report."""
    deep_output_dir = tmp_path / "text" / "deeply" / "nested"
    output_file = deep_output_dir / "my_text_report.txt"
    report_content = "Contenu simple."

    result = save_text_report(report_content, output_file)
    assert result is True
    assert output_file.exists()
    assert deep_output_dir.exists()

@patch('builtins.open', side_effect=IOError("Test text write error"))
def test_save_text_report_write_failure(mock_open, temp_output_dir: Path, caplog):
    """Teste la gestion d'une erreur d'écriture pour save_text_report."""
    report_content = "Contenu qui ne sera pas écrit."
    output_file = temp_output_dir / "unwritable_text_report.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True) # S'assurer que le parent existe

    result = save_text_report(report_content, output_file)
    assert result is False
    assert not output_file.exists()
    assert "Erreur lors de la sauvegarde du rapport textuel" in caplog.text
    assert "Test text write error" in caplog.text