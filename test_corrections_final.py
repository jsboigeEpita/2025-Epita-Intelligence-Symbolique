#!/usr/bin/env python3
"""
Script de corrections finales pour les tests restants
Cible les 3 erreurs et 10 échecs restants
"""

import os
import sys
import re
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def apply_extract_agent_adapter_fixes():
    """Corrige les problèmes dans test_extract_agent_adapter.py"""
    print("Correction des problemes ExtractAgentAdapter...")
    
    test_file = project_root / "tests" / "test_extract_agent_adapter.py"
    if not test_file.exists():
        print(f"Fichier non trouve: {test_file}")
        return False
    
    content = test_file.read_text(encoding='utf-8')
    
    # Correction 1: Ajout de l'import Mock manquant
    if "from unittest.mock import Mock" not in content:
        content = content.replace(
            "import unittest",
            "import unittest\nfrom unittest.mock import Mock"
        )
    
    # Correction 2: Correction du MockExtractAgent pour accepter extract_agent
    mock_extract_agent_pattern = r'class MockExtractAgent:\s*def __init__\(self\):'
    if re.search(mock_extract_agent_pattern, content):
        content = re.sub(
            mock_extract_agent_pattern,
            'class MockExtractAgent:\n    def __init__(self, extract_agent=None):',
            content
        )
    
    test_file.write_text(content, encoding='utf-8')
    print("Corrections ExtractAgentAdapter appliquees")
    return True

def apply_tactical_monitor_fixes():
    """Corrige les problèmes dans test_tactical_monitor.py"""
    print("Correction des problemes TacticalMonitor...")
    
    test_file = project_root / "tests" / "test_tactical_monitor.py"
    if not test_file.exists():
        print(f"Fichier non trouve: {test_file}")
        return False
    
    content = test_file.read_text(encoding='utf-8')
    
    # Correction: Ajout de l'attribut task_dependencies au mock state
    setup_method_pattern = r'def setUp\(self\):(.*?)def tearDown'
    match = re.search(setup_method_pattern, content, re.DOTALL)
    
    if match and "task_dependencies" not in match.group(1):
        # Ajouter task_dependencies au mock state
        content = content.replace(
            "self.mock_state = Mock()",
            """self.mock_state = Mock()
        self.mock_state.task_dependencies = {}
        self.mock_state.get_task_dependencies.return_value = []"""
        )
    
    test_file.write_text(content, encoding='utf-8')
    print("Corrections TacticalMonitor appliquees")
    return True

def apply_load_extract_definitions_fixes():
    """Corrige les problèmes dans test_load_extract_definitions.py"""
    print("Correction des problemes LoadExtractDefinitions...")
    
    test_file = project_root / "tests" / "test_load_extract_definitions.py"
    if not test_file.exists():
        print(f"Fichier non trouve: {test_file}")
        return False
    
    content = test_file.read_text(encoding='utf-8')
    
    # Correction: Remplacer definitions_path par le bon nom de paramètre
    content = content.replace(
        "definitions_path=",
        "file_path="
    )
    
    test_file.write_text(content, encoding='utf-8')
    print("Corrections LoadExtractDefinitions appliquees")
    return True

def apply_tactical_monitor_advanced_fixes():
    """Corrige les problèmes dans test_tactical_monitor_advanced.py"""
    print("Correction des problemes TacticalMonitorAdvanced...")
    
    test_file = project_root / "tests" / "test_tactical_monitor_advanced.py"
    if not test_file.exists():
        print(f"Fichier non trouve: {test_file}")
        return False
    
    content = test_file.read_text(encoding='utf-8')
    
    # Correction: Ajout de task_dependencies au mock state
    if "task_dependencies" not in content:
        content = content.replace(
            "self.mock_state = Mock()",
            """self.mock_state = Mock()
        self.mock_state.task_dependencies = {}
        self.mock_state.get_task_dependencies.return_value = []"""
        )
    
    # Correction: Ajout de 'recommendations' dans _evaluate_overall_coherence
    coherence_method_pattern = r'def _evaluate_overall_coherence\(self.*?\):(.*?)return overall_coherence'
    match = re.search(coherence_method_pattern, content, re.DOTALL)
    
    if match and "recommendations" not in match.group(1):
        content = content.replace(
            "return overall_coherence",
            """overall_coherence['recommendations'] = []
        return overall_coherence"""
        )
    
    test_file.write_text(content, encoding='utf-8')
    print("Corrections TacticalMonitorAdvanced appliquees")
    return True

def main():
    """Fonction principale"""
    print("Debut des corrections finales des tests...")
    
    corrections_applied = 0
    
    # Application des corrections
    if apply_extract_agent_adapter_fixes():
        corrections_applied += 1
    
    if apply_tactical_monitor_fixes():
        corrections_applied += 1
    
    if apply_load_extract_definitions_fixes():
        corrections_applied += 1
    
    if apply_tactical_monitor_advanced_fixes():
        corrections_applied += 1
    
    print(f"\n{corrections_applied} corrections appliquees avec succes")
    print("Pret pour la validation finale des tests")

if __name__ == "__main__":
    main()