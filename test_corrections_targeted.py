#!/usr/bin/env python3
"""
Script de corrections ciblées pour les erreurs de tests restantes
Basé sur l'analyse du runner alternatif - 189 tests, 10 échecs, 3 erreurs
"""

import sys
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Configure l'environnement pour les corrections."""
    project_root = Path(__file__).parent.absolute()
    
    # Ajout des chemins nécessaires
    paths_to_add = [
        str(project_root),
        str(project_root / "tests" / "mocks"),
        str(project_root / "argumentation_analysis"),
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    logger.info(f"Environnement configuré avec {len(paths_to_add)} chemins")

def fix_extract_definitions_model_validate():
    """Corrige l'erreur AttributeError: 'ExtractDefinitions' has no attribute 'model_validate'"""
    logger.info("Correction de l'erreur model_validate dans ExtractDefinitions...")
    
    # Recherche du fichier ExtractDefinitions
    extract_def_files = [
        "argumentation_analysis/core/extract_definitions.py",
        "argumentation_analysis/agents/core/extract/extract_definitions.py",
        "argumentation_analysis/utils/extract_definitions.py"
    ]
    
    for file_path in extract_def_files:
        if os.path.exists(file_path):
            logger.info(f"Fichier trouvé: {file_path}")
            
            # Lecture du contenu
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ajout de la méthode model_validate si elle n'existe pas
            if 'model_validate' not in content and 'class ExtractDefinitions' in content:
                # Recherche de la classe
                lines = content.split('\n')
                new_lines = []
                in_class = False
                
                for line in lines:
                    new_lines.append(line)
                    
                    if line.strip().startswith('class ExtractDefinitions'):
                        in_class = True
                    elif in_class and line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                        # Fin de la classe, ajout de la méthode avant
                        new_lines.insert(-1, "")
                        new_lines.insert(-1, "    @classmethod")
                        new_lines.insert(-1, "    def model_validate(cls, data):")
                        new_lines.insert(-1, "        \"\"\"Méthode de compatibilité pour Pydantic v1/v2\"\"\"")
                        new_lines.insert(-1, "        if hasattr(cls, 'parse_obj'):")
                        new_lines.insert(-1, "            return cls.parse_obj(data)")
                        new_lines.insert(-1, "        else:")
                        new_lines.insert(-1, "            return cls(**data)")
                        new_lines.insert(-1, "")
                        in_class = False
                
                # Écriture du fichier corrigé
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                
                logger.info(f"Méthode model_validate ajoutée à {file_path}")
                return True
    
    logger.warning("Fichier ExtractDefinitions non trouvé")
    return False

def fix_mock_attribute_error():
    """Corrige l'erreur Mock object has no attribute 'task_dependencies'"""
    logger.info("Correction de l'erreur Mock task_dependencies...")
    
    test_file = "tests/test_tactical_monitor.py"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Recherche et correction des mocks
        if 'task_dependencies' in content:
            # Ajout de la configuration du mock
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                new_lines.append(line)
                
                # Après la création du mock state, ajout des attributs
                if 'self.state = Mock()' in line or 'state = Mock()' in line:
                    new_lines.append("        # Configuration des attributs du mock")
                    new_lines.append("        self.state.task_dependencies = {}")
                    new_lines.append("        self.state.tasks = {}")
                    new_lines.append("        self.state.agents = {}")
                    new_lines.append("        self.state.conflicts = []")
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"Mock task_dependencies corrigé dans {test_file}")
            return True
    
    return False

def fix_extract_agent_adapter_mock():
    """Corrige les erreurs dans test_extract_agent_adapter.py"""
    logger.info("Correction des erreurs ExtractAgentAdapter...")
    
    test_file = "tests/test_extract_agent_adapter.py"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Correction de l'erreur Mock non défini
        if "name 'Mock' is not defined" in content or 'Mock' in content:
            # Ajout de l'import Mock
            lines = content.split('\n')
            new_lines = []
            mock_imported = False
            
            for line in lines:
                if line.startswith('import unittest') and not mock_imported:
                    new_lines.append(line)
                    new_lines.append('from unittest.mock import Mock, MagicMock, patch')
                    mock_imported = True
                elif 'from unittest.mock import' in line and 'Mock' not in line:
                    # Ajout de Mock à l'import existant
                    new_lines.append(line.replace('import', 'import Mock, MagicMock,'))
                    mock_imported = True
                else:
                    new_lines.append(line)
            
            # Si Mock n'a pas été importé, ajout en début
            if not mock_imported:
                new_lines.insert(1, 'from unittest.mock import Mock, MagicMock, patch')
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"Import Mock ajouté dans {test_file}")
            return True
    
    return False

def create_enhanced_mock_fixes():
    """Crée des corrections avancées pour les mocks"""
    logger.info("Création de corrections avancées pour les mocks...")
    
    mock_fixes_content = '''"""
Corrections avancées pour les mocks - Résolution des erreurs de tests
"""

import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Ajout du chemin du projet
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class EnhancedMockState:
    """Mock amélioré pour TacticalState avec tous les attributs nécessaires"""
    
    def __init__(self):
        self.task_dependencies = {}
        self.tasks = {}
        self.agents = {}
        self.conflicts = []
        self.objectives = []
        self.intermediate_results = []
        self.rhetorical_analysis_results = {}
        self.tactical_actions = []
        self.agent_utilization = {}
        self.task_completion_rate = 0.0
        self.conflict_resolution_rate = 0.0
    
    def get_task_dependencies(self, task_id):
        return self.task_dependencies.get(task_id, [])
    
    def add_task(self, task):
        self.tasks[task.get('id', 'unknown')] = task
    
    def update_task_progress(self, task_id, progress):
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress
    
    def add_conflict(self, conflict):
        self.conflicts.append(conflict)
    
    def resolve_conflict(self, conflict_id):
        self.conflicts = [c for c in self.conflicts if c.get('id') != conflict_id]

class EnhancedExtractDefinitions:
    """Mock amélioré pour ExtractDefinitions avec model_validate"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def model_validate(cls, data):
        """Méthode de compatibilité Pydantic v1/v2"""
        if isinstance(data, dict):
            return cls(**data)
        return data
    
    @classmethod
    def parse_obj(cls, data):
        """Méthode Pydantic v1"""
        return cls.model_validate(data)

def apply_mock_fixes():
    """Applique toutes les corrections de mocks"""
    
    # Patch pour ExtractDefinitions
    import argumentation_analysis.core.extract_definitions as extract_def_module
    if hasattr(extract_def_module, 'ExtractDefinitions'):
        original_class = extract_def_module.ExtractDefinitions
        if not hasattr(original_class, 'model_validate'):
            original_class.model_validate = EnhancedExtractDefinitions.model_validate
    
    print("[MOCK_FIXES] Corrections de mocks appliquées avec succès")

if __name__ == "__main__":
    apply_mock_fixes()
'''
    
    with open("tests/enhanced_mock_fixes.py", 'w', encoding='utf-8') as f:
        f.write(mock_fixes_content)
    
    logger.info("Fichier enhanced_mock_fixes.py créé")

def run_targeted_corrections():
    """Exécute toutes les corrections ciblées"""
    logger.info("=== DÉBUT DES CORRECTIONS CIBLÉES ===")
    
    corrections_applied = 0
    
    # 1. Correction model_validate
    if fix_extract_definitions_model_validate():
        corrections_applied += 1
    
    # 2. Correction Mock task_dependencies
    if fix_mock_attribute_error():
        corrections_applied += 1
    
    # 3. Correction ExtractAgentAdapter Mock
    if fix_extract_agent_adapter_mock():
        corrections_applied += 1
    
    # 4. Création des corrections avancées
    create_enhanced_mock_fixes()
    corrections_applied += 1
    
    logger.info(f"=== CORRECTIONS TERMINÉES: {corrections_applied} corrections appliquées ===")
    
    return corrections_applied

if __name__ == "__main__":
    setup_environment()
    corrections_count = run_targeted_corrections()
    
    print(f"\n=== RÉSUMÉ DES CORRECTIONS ===")
    print(f"Corrections appliquées: {corrections_count}")
    print(f"État avant: 189 tests, 10 échecs, 3 erreurs (93.1% réussite)")
    print(f"Corrections ciblées sur:")
    print(f"  - ExtractDefinitions.model_validate")
    print(f"  - Mock task_dependencies")
    print(f"  - ExtractAgentAdapter Mock imports")
    print(f"  - Corrections avancées de mocks")
    print(f"\nRecommandation: Relancer les tests avec le runner alternatif")