#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires de développement dans project_core.dev_utils.
"""
import pytest
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Ajuster le PYTHONPATH pour les tests
import sys
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

from project_core.dev_utils.encoding_utils import check_project_python_files_encoding, fix_file_encoding
from project_core.dev_utils.code_validation import analyze_directory_references, check_python_syntax

@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Crée une structure de répertoires temporaire pour les tests d'encodage et de références."""
    project_dir = tmp_path / "temp_project"
    project_dir.mkdir()
    
    # Fichier Python correct en UTF-8
    (project_dir / "good_file.py").write_text("# coding: utf-8\nprint('你好世界')\n", encoding='utf-8')
    
    # Fichier Python incorrect (simulé en latin-1)
    (project_dir / "bad_encoding_file.py").write_text("# coding: latin-1\nprint('Hélène')\n", encoding='utf-8')
    
    # Fichier non-Python
    (project_dir / "not_python.txt").write_text("Ceci est un test.", encoding='utf-8')
    
    # Sous-répertoire avec un fichier Python
    subdir = project_dir / "subdir"
    subdir.mkdir()
    (subdir / "another_good_file.py").write_text("print('UTF-8 test')\n", encoding='utf-8')
    
    # Répertoire à exclure (simulant venv)
    venv_dir = project_dir / "venv"
    venv_dir.mkdir()
    (venv_dir / "excluded.py").write_text("# Ne pas vérifier\nprint('échec')\n", encoding='utf-8')
    
    return project_dir

def test_check_project_python_files_encoding(temp_project_dir: Path):
    """Teste la vérification de l'encodage des fichiers Python."""
    non_utf8_files = check_project_python_files_encoding(str(temp_project_dir))
    
    assert len(non_utf8_files) == 1
    # S'assurer que le chemin retourné est absolu et correct
    expected_bad_file = (temp_project_dir / "bad_encoding_file.py").resolve()
    assert Path(non_utf8_files[0]).resolve() == expected_bad_file

def test_fix_file_encoding_from_latin1_to_utf8(tmp_path: Path):
    """Teste la correction d'un fichier de latin-1 vers UTF-8."""
    latin1_content = "Hélène et François sont allés à la pêche."
    test_file = tmp_path / "latin1_file.txt"
    
    # Écrire en latin-1
    with open(test_file, "wb") as f:
        f.write(latin1_content.encode('utf-8'))
        
    # Tenter de corriger vers UTF-8
    success = fix_file_encoding(str(test_file), target_encoding='utf-8', source_encodings=['latin-1'])
    assert success
    
    # Vérifier que le fichier est maintenant lisible en UTF-8 et que le contenu est correct
    corrected_content = test_file.read_text(encoding='utf-8')
    assert corrected_content == latin1_content

@pytest.fixture
def temp_code_dir_for_refs(tmp_path: Path) -> Path:
    """Crée une structure de répertoires pour tester analyze_directory_references."""
    code_dir = tmp_path / "temp_code_analysis"
    code_dir.mkdir()
    
    (code_dir / "file1.py").write_text(
        "settings_file = 'config/settings.json'\n"  # Modifié pour inclure 'config/'
        "data_path = 'data/input.csv'\n"
        "from config import api_keys\n"
        "print('using data/tmp/file.txt')\n",
        encoding='utf-8'
    )
    
    subdir = code_dir / "module1"
    subdir.mkdir()
    (subdir / "file2.py").write_text(
        "print('This is file2 in a subdir.')\n"
        "important_value = 42\n", # Ne contient plus 'data/' ni rien lié à 'config'
        encoding='utf-8'
    )
    (code_dir / "ignored.txt").write_text("config/some_text_data.txt\ndata/another.log", encoding='utf-8')
    
    return code_dir

def test_analyze_directory_references(temp_code_dir_for_refs: Path):
    """Teste l'analyse des références de répertoires."""
    patterns = {
        "config_usage": re.compile(r"config/"), # Cherche le littéral "config/"
        "data_usage": re.compile(r"data/"),   # Cherche le littéral "data/"
        "specific_import": re.compile(r"from config import") # Import spécifique
    }
    
    results = analyze_directory_references(str(temp_code_dir_for_refs), patterns, file_extensions=('.py',))
    
    assert "config_usage" in results
    # Assertions pour config_usage (devrait être trouvé uniquement dans file1.py)
    assert "config_usage" in results
    assert results["config_usage"]["count"] == 1, f"Expected 1 'config/' usage, got {results['config_usage']['count']}. Files: {results['config_usage']['files'].keys()}"
    assert len(results["config_usage"]["files"]) == 1
    file1_path_str = str(temp_code_dir_for_refs / "file1.py")
    assert file1_path_str in results["config_usage"]["files"]
    assert results["config_usage"]["files"][file1_path_str] == 1
    assert results["config_usage"]["examples"][0]["file"] == file1_path_str
    assert results["config_usage"]["examples"][0]["line"] == 1
    assert results["config_usage"]["examples"][0]["content"] == "settings_file = 'config/settings.json'"
    
    # Assertions pour data_usage (devrait être trouvé uniquement dans file1.py, 2 fois)
    assert "data_usage" in results
    assert results["data_usage"]["count"] == 2, f"Expected 2 'data/' usages, got {results['data_usage']['count']}. Files: {results['data_usage']['files'].keys()}"
    assert len(results["data_usage"]["files"]) == 1
    assert file1_path_str in results["data_usage"]["files"]
    assert results["data_usage"]["files"][file1_path_str] == 2
    # Vérifier les exemples pour data_usage si nécessaire, par exemple le premier
    assert results["data_usage"]["examples"][0]["file"] == file1_path_str
    assert results["data_usage"]["examples"][0]["line"] == 2 # 'data_path = 'data/input.csv''
    assert results["data_usage"]["examples"][0]["content"] == "data_path = 'data/input.csv'"
    
    # Assertions pour specific_import (devrait être trouvé uniquement dans file1.py)
    assert "specific_import" in results
    assert results["specific_import"]["count"] == 1
    assert len(results["specific_import"]["files"]) == 1
    assert file1_path_str in results["specific_import"]["files"]
    assert results["specific_import"]["files"][file1_path_str] == 1
    assert results["specific_import"]["examples"][0]["file"] == file1_path_str
    assert results["specific_import"]["examples"][0]["line"] == 3
    assert results["specific_import"]["examples"][0]["content"] == "from config import api_keys"

def test_check_python_syntax_valid(tmp_path: Path):
    """Teste la vérification de syntaxe sur un fichier valide."""
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("print('hello')\na = 1 + 2\n", encoding='utf-8')
    is_valid, msg, ctx = check_python_syntax(str(valid_file))
    assert is_valid is True
    assert "syntaxe du fichier est correcte" in msg
    assert not ctx

def test_check_python_syntax_invalid(tmp_path: Path):
    """Teste la vérification de syntaxe sur un fichier invalide."""
    invalid_file = tmp_path / "invalid.py"
    invalid_file.write_text("print('hello'\na = 1 + \n", encoding='utf-8') # Erreur de syntaxe
    is_valid, msg, ctx = check_python_syntax(str(invalid_file))
    assert is_valid is False
    assert "Erreur de syntaxe" in msg
    assert len(ctx) > 0 # Devrait avoir des lignes de contexte

# TODO: Ajouter des tests pour check_python_tokens si pertinent et si des cas clairs d'ERRORTOKEN peuvent être simulés.