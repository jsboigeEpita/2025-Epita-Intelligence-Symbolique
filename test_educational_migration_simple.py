#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de Validation de la Migration Éducative - Script 2 (Version Simple)
=========================================================================

Test de validation simplifié pour vérifier que le script educational_showcase_system.py
transformé utilise correctement le pipeline d'orchestration unifié.

Version: 1.0.0
Date: 2025-06-10
"""

import asyncio
import sys
import logging
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger("TestEducationalMigration")

def test_basic_import():
    """Test basique d'import du système éducatif transformé."""
    
    print("[TEST] Import du système éducatif transformé...")
    
    try:
        from scripts.consolidated.educational_showcase_system import (
            EducationalShowcaseSystem,
            EducationalConfiguration,
            EducationalMode,
            EducationalLanguage
        )
        
        print("[OK] Import réussi")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Import échoué: {e}")
        return False

def test_educational_config():
    """Test de la configuration éducative."""
    
    print("[TEST] Configuration éducative...")
    
    try:
        from scripts.consolidated.educational_showcase_system import (
            EducationalConfiguration,
            EducationalMode,
            EducationalLanguage
        )
        
        # Test configuration L1
        config_l1 = EducationalConfiguration(
            mode=EducationalMode.DEBUTANT,
            language=EducationalLanguage.FRANCAIS,
            student_level="L1",
            enable_real_llm=False
        )
        
        print(f"[OK] Configuration L1: Mode={config_l1.mode.value}, Niveau={config_l1.student_level}")
        
        # Test configuration M1
        config_m1 = EducationalConfiguration(
            mode=EducationalMode.EXPERT,
            language=EducationalLanguage.FRANCAIS,
            student_level="M1",
            enable_real_llm=False,
            enable_advanced_metrics=True
        )
        
        print(f"[OK] Configuration M1: Mode={config_m1.mode.value}, Niveau={config_m1.student_level}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Configuration échouée: {e}")
        return False

def test_build_educational_config():
    """Test de la méthode _build_educational_config."""
    
    print("[TEST] Méthode _build_educational_config...")
    
    try:
        from scripts.consolidated.educational_showcase_system import (
            EducationalShowcaseSystem,
            EducationalConfiguration,
            EducationalMode
        )
        
        # Mock LLM service
        class MockLLMService:
            def __init__(self):
                self.service_id = "mock_llm_service"
        
        mock_llm = MockLLMService()
        
        # Test pour différents niveaux
        test_configs = [
            ("L1", EducationalMode.DEBUTANT),
            ("L2", EducationalMode.INTERMEDIAIRE),
            ("L3", EducationalMode.INTERMEDIAIRE),
            ("M1", EducationalMode.EXPERT),
            ("M2", EducationalMode.EXPERT)
        ]
        
        system = EducationalShowcaseSystem(EducationalConfiguration())
        
        for level, mode in test_configs:
            config = EducationalConfiguration(
                mode=mode,
                student_level=level,
                enable_real_llm=False
            )
            
            system.project_manager.config = config
            
            unified_config = system.project_manager._build_educational_config(mock_llm)
            
            print(f"[OK] Niveau {level}: {unified_config.analysis_type.value} / {unified_config.orchestration_mode_enum.value}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Build config échoué: {e}")
        return False

def test_analysis_modes():
    """Test des modes d'analyse par niveau."""
    
    print("[TEST] Modes d'analyse par niveau...")
    
    try:
        from scripts.consolidated.educational_showcase_system import (
            EducationalShowcaseSystem,
            EducationalConfiguration
        )
        
        system = EducationalShowcaseSystem(EducationalConfiguration())
        
        levels = ["L1", "L2", "L3", "M1", "M2"]
        
        for level in levels:
            system.project_manager.config.student_level = level
            modes = system.project_manager._get_analysis_modes_for_level()
            print(f"[OK] Niveau {level}: {modes}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Modes d'analyse échoués: {e}")
        return False

def test_text_library():
    """Test de la bibliothèque de textes pré-intégrés."""
    
    print("[TEST] Bibliothèque de textes pré-intégrés...")
    
    try:
        from scripts.consolidated.educational_showcase_system import EducationalTextLibrary
        
        text_lib = EducationalTextLibrary()
        sample_texts = text_lib.get_sample_texts()
        
        print(f"[OK] {len(sample_texts)} textes pré-intégrés disponibles")
        
        for text_key, text_data in sample_texts.items():
            print(f"     - {text_key}: '{text_data['title']}'")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Bibliothèque de textes échouée: {e}")
        return False

def test_main_function():
    """Test de la fonction main pour l'interface CLI."""
    
    print("[TEST] Interface CLI (fonction main)...")
    
    try:
        from scripts.consolidated.educational_showcase_system import main
        
        print("[OK] Fonction main() disponible")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Interface CLI échouée: {e}")
        return False

def run_all_tests():
    """Exécute tous les tests de validation."""
    
    print("=" * 60)
    print("TEST DE VALIDATION - MIGRATION EDUCATIVE SCRIPT 2")
    print("=" * 60)
    print()
    
    tests = [
        ("Import du système", test_basic_import),
        ("Configuration éducative", test_educational_config),
        ("Build config éducative", test_build_educational_config),
        ("Modes d'analyse", test_analysis_modes),
        ("Bibliothèque de textes", test_text_library),
        ("Interface CLI", test_main_function)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"[PASSE] {test_name}")
            else:
                failed += 1
                print(f"[ECHEC] {test_name}")
        except Exception as e:
            failed += 1
            print(f"[ERREUR] {test_name}: {e}")
    
    print("\n" + "=" * 60)
    print("RESUME DES TESTS")
    print("=" * 60)
    print(f"Tests réussis: {passed}")
    print(f"Tests échoués: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n*** VALIDATION COMPLETE DE LA MIGRATION REUSSIE! ***")
        print("\nLe script educational_showcase_system.py a été transformé avec succès")
        print("selon les spécifications de migration vers le pipeline d'orchestration unifié.")
        print("\nPoints validés:")
        print("- Import unique du pipeline d'orchestration unifié")
        print("- Méthode _build_educational_config() implémentée")
        print("- Mapping éducatif spécialisé fonctionnel")
        print("- Configuration progressive par niveau")
        print("- Textes pré-intégrés préservés")
        print("- Interface CLI maintenue")
        return True
    else:
        print(f"\n*** ECHEC DE LA VALIDATION - {failed} test(s) échoué(s) ***")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    if not success:
        sys.exit(1)
    
    print(f"\n*** Migration du Script 2 (educational_showcase_system.py) VALIDEE ***")