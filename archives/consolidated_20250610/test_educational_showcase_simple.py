#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test simplifié pour le système éducatif EPITA
======================================================

Tests de base sans émojis pour éviter les problèmes d'encodage Windows.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Configuration encodage Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ajouter la racine du projet au sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports du système éducatif
try:
    from scripts.consolidated.educational_showcase_system import (
        EducationalShowcaseSystem,
        EducationalConfiguration,
        EducationalMode,
        EducationalLanguage,
        EducationalProjectManager,
        EducationalConversationLogger,
        EducationalTextLibrary,
        EducationalMetrics
    )
    EDUCATIONAL_IMPORTS_OK = True
except ImportError as e:
    print(f"[ERREUR] Impossible d'importer le système éducatif: {e}")
    EDUCATIONAL_IMPORTS_OK = False

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("TestEducationalSimple")

async def test_basic_configuration():
    """Test de base de la configuration éducative."""
    print("[TEST] Configuration de base...")
    
    try:
        config = EducationalConfiguration(
            mode=EducationalMode.DEBUTANT,
            student_level="L1",
            language=EducationalLanguage.FRANCAIS,
            enable_real_llm=False
        )
        
        assert config.mode == EducationalMode.DEBUTANT
        assert config.student_level == "L1"
        assert config.language == EducationalLanguage.FRANCAIS
        
        print("[OK] Configuration créée avec succès")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test configuration: {e}")
        return False

async def test_text_library():
    """Test de la bibliothèque de textes."""
    print("[TEST] Bibliothèque de textes...")
    
    try:
        library = EducationalTextLibrary()
        sample_texts = library.get_sample_texts()
        
        expected_keys = [
            "L1_sophismes_basiques",
            "L2_logique_propositionnelle", 
            "L3_logique_modale",
            "M1_orchestration_complexe"
        ]
        
        for key in expected_keys:
            assert key in sample_texts, f"Texte manquant: {key}"
            
            text_data = sample_texts[key]
            assert "title" in text_data
            assert "content" in text_data
            assert len(text_data["content"]) > 50
        
        print(f"[OK] {len(sample_texts)} textes éducatifs disponibles")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test bibliothèque: {e}")
        return False

async def test_conversation_logger():
    """Test du logger conversationnel."""
    print("[TEST] Logger conversationnel...")
    
    try:
        config = EducationalConfiguration(
            mode=EducationalMode.INTERMEDIAIRE,
            student_level="L3",
            max_conversation_length=5
        )
        
        logger_conv = EducationalConversationLogger(config)
        
        # Test d'ajout de messages
        logger_conv.log_agent_message(
            "TestAgent", 
            "Message de test",
            "test_phase"
        )
        
        assert len(logger_conv.conversations) == 1
        assert logger_conv.conversations[0].agent == "TestAgent"
        
        # Test d'interaction d'outil
        logger_conv.log_tool_interaction(
            "TestAgent", "test_tool", "param1", "result_ok", 123.5
        )
        
        assert len(logger_conv.conversations) == 2
        assert logger_conv.conversations[1].duration_ms == 123.5
        
        print(f"[OK] {len(logger_conv.conversations)} messages capturés")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test logger: {e}")
        return False

async def test_project_manager():
    """Test du Project Manager éducatif."""
    print("[TEST] Project Manager...")
    
    try:
        config = EducationalConfiguration(
            mode=EducationalMode.INTERMEDIAIRE,
            student_level="L2",
            enable_real_llm=False
        )
        
        pm = EducationalProjectManager(config)
        
        assert pm.config == config
        assert isinstance(pm.conversation_logger, EducationalConversationLogger)
        assert isinstance(pm.metrics, EducationalMetrics)
        assert pm.metrics.learning_level == "intermediaire"
        assert pm.current_phase == "initialisation"
        
        print("[OK] Project Manager initialisé")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test PM: {e}")
        return False

async def test_educational_system():
    """Test du système éducatif complet."""
    print("[TEST] Système éducatif complet...")
    
    try:
        config = EducationalConfiguration(
            mode=EducationalMode.DEBUTANT,
            student_level="L1", 
            enable_real_llm=False
        )
        
        system = EducationalShowcaseSystem(config)
        
        assert system.config == config
        assert isinstance(system.project_manager, EducationalProjectManager)
        assert isinstance(system.text_library, EducationalTextLibrary)
        
        # Test de sélection de texte
        selected_text = system._select_appropriate_text()
        assert len(selected_text) > 50
        
        print("[OK] Système éducatif initialisé")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test système: {e}")
        return False

async def main():
    """Point d'entrée principal des tests."""
    print("=" * 60)
    print("TESTS DU SYSTEME EDUCATIF EPITA")
    print("=" * 60)
    
    if not EDUCATIONAL_IMPORTS_OK:
        print("[ERREUR CRITIQUE] Impossible d'importer le système éducatif")
        return 1
    
    # Liste des tests
    tests = [
        ("Configuration de base", test_basic_configuration),
        ("Bibliothèque de textes", test_text_library),
        ("Logger conversationnel", test_conversation_logger),
        ("Project Manager", test_project_manager),
        ("Système éducatif", test_educational_system)
    ]
    
    # Exécution des tests
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[EXECUTION] {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                print(f"[ECHEC] {test_name}")
        except Exception as e:
            print(f"[EXCEPTION] {test_name}: {e}")
    
    # Résumé
    print("\n" + "=" * 60)
    print("RESUME DES TESTS")
    print("=" * 60)
    print(f"Tests réussis: {passed}/{total}")
    print(f"Taux de réussite: {(passed/total*100):.1f}%")
    
    if passed == total:
        print("\n[SUCCES] Tous les tests sont passés !")
        print("Le système éducatif est opérationnel.")
        return 0
    else:
        print(f"\n[ATTENTION] {total-passed} test(s) échoué(s)")
        print("Des corrections sont nécessaires.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)