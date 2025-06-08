<<<<<<< MAIN
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test d'intégration avancé pour la refactorisation Enhanced du script advanced_rhetorical_analysis.py
=====================================================================================================

Ce test valide l'intégration complète de :
- Pipeline Enhanced extended (run_enhanced_rhetoric_pipeline)
- Script refactorisé avec nouveaux orchestrateurs
- Arguments CLI étendus
- Compatibilité avec l'écosystème refactorisé
"""

import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# Configuration du logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("TestAdvancedRhetoricalEnhanced")


def create_test_extracts() -> List[Dict[str, Any]]:
    """Crée des extraits de test pour les tests d'intégration."""
    return [
        {
            "source_name": "Test Corpus Philosophique",
            "extracts": [
                {
                    "extract_name": "Argument Fallacieux Test",
                    "extract_text": "Tous les politiciens sont corrompus car mon voisin dit que son maire a accepté un pot-de-vin.",
                    "context": "Test de sophisme de généralisation hâtive"
                },
                {
                    "extract_name": "Argument Complexe Test", 
                    "extract_text": "Si nous acceptons cette loi, alors nous devrons accepter toutes les lois similaires, ce qui mènera inevitablement à la dictature. Donc nous devons rejeter cette loi.",
                    "context": "Test de sophisme de pente glissante"
                }
            ]
        }
    ]


def create_test_base_results() -> List[Dict[str, Any]]:
    """Crée des résultats de base de test."""
    return [
        {
            "extract_name": "Argument Fallacieux Test",
            "source_name": "Test Corpus Philosophique",
            "analyses": {
                "contextual_fallacies": {"detected": ["hasty_generalization"]},
                "argument_coherence": {"score": 0.3},
                "semantic_analysis": {"sentiment": "negative"}
            }
        }
    ]


def test_pipeline_classic():
    """Test du pipeline classique (mode de compatibilité)."""
    logger.info("🧪 Test du pipeline classique...")
    
    try:
        from argumentation_analysis.pipelines.advanced_rhetoric import run_advanced_rhetoric_pipeline
        
        extracts = create_test_extracts()
        base_results = create_test_base_results()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        # Test du pipeline classique
        run_advanced_rhetoric_pipeline(
            extract_definitions=extracts,
            base_results=base_results,
            output_file=output_path,
            use_real_tools=False  # Utiliser les mocks pour le test
        )
        
        # Vérifier que le fichier de sortie existe et contient des données
        assert output_path.exists(), "Le fichier de sortie n'a pas été créé"
        
        with open(output_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        assert isinstance(results, list), "Les résultats doivent être une liste"
        assert len(results) > 0, "Les résultats ne doivent pas être vides"
        
        # Nettoyer
        output_path.unlink()
        
        logger.info("✅ Test pipeline classique : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test pipeline classique : ÉCHEC - {e}")
        return False


def test_pipeline_enhanced():
    """Test du pipeline Enhanced avec orchestrateurs."""
    logger.info("🧪 Test du pipeline Enhanced...")
    
    try:
        from argumentation_analysis.pipelines.advanced_rhetoric import run_enhanced_rhetoric_pipeline
        
        extracts = create_test_extracts()
        base_results = create_test_base_results()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        # Test avec orchestrateur real_llm (devrait fallback vers classic si non disponible)
        run_enhanced_rhetoric_pipeline(
            extract_definitions=extracts,
            base_results=base_results,
            output_file=output_path,
            orchestrator_type="real_llm",
            use_real_tools=False,
            llm_config={"model": "test-model", "temperature": 0.5}
        )
        
        # Vérifier que le fichier de sortie existe
        assert output_path.exists(), "Le fichier de sortie Enhanced n'a pas été créé"
        
        with open(output_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Vérifier la structure Enhanced
        assert "metadata" in results, "Les métadonnées Enhanced sont manquantes"
        assert "results" in results, "Les résultats Enhanced sont manquants"
        
        metadata = results["metadata"]
        assert metadata["pipeline_type"] == "enhanced_rhetoric", "Type de pipeline incorrect"
        assert "orchestrator_used" in metadata, "Orchestrateur utilisé non spécifié"
        
        # Nettoyer
        output_path.unlink()
        
        logger.info("✅ Test pipeline Enhanced : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test pipeline Enhanced : ÉCHEC - {e}")
        return False


def test_cli_arguments():
    """Test des nouveaux arguments CLI."""
    logger.info("🧪 Test des arguments CLI Enhanced...")
    
    try:
        from argumentation_analysis.utils.core_utils.cli_utils import parse_advanced_analysis_arguments
        import sys
        
        # Sauvegarder les arguments originaux
        original_argv = sys.argv.copy()
        
        # Tester les nouveaux arguments Enhanced
        test_args = [
            "test_script.py",
            "--enhanced",
            "--orchestrator", "real_llm",
            "--use-real-tools",
            "--llm-model", "gpt-3.5-turbo",
            "--temperature", "0.8",
            "--max-tokens", "2000"
        ]
        
        sys.argv = test_args
        args = parse_advanced_analysis_arguments()
        
        # Vérifier les nouveaux attributs
        assert hasattr(args, 'enhanced'), "Attribut 'enhanced' manquant"
        assert hasattr(args, 'orchestrator'), "Attribut 'orchestrator' manquant"
        assert hasattr(args, 'use_real_tools'), "Attribut 'use_real_tools' manquant"
        assert hasattr(args, 'llm_model'), "Attribut 'llm_model' manquant"
        assert hasattr(args, 'temperature'), "Attribut 'temperature' manquant"
        assert hasattr(args, 'max_tokens'), "Attribut 'max_tokens' manquant"
        
        # Vérifier les valeurs
        assert args.enhanced == True, "Valeur 'enhanced' incorrecte"
        assert args.orchestrator == "real_llm", "Valeur 'orchestrator' incorrecte"
        assert args.use_real_tools == True, "Valeur 'use_real_tools' incorrecte"
        assert args.llm_model == "gpt-3.5-turbo", "Valeur 'llm_model' incorrecte"
        assert args.temperature == 0.8, "Valeur 'temperature' incorrecte"
        assert args.max_tokens == 2000, "Valeur 'max_tokens' incorrecte"
        
        # Restaurer les arguments originaux
        sys.argv = original_argv
        
        logger.info("✅ Test arguments CLI Enhanced : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test arguments CLI Enhanced : ÉCHEC - {e}")
        # Restaurer les arguments en cas d'erreur
        sys.argv = original_argv
        return False


def test_integration_with_orchestrators():
    """Test d'intégration avec les orchestrateurs refactorisés."""
    logger.info("🧪 Test d'intégration avec orchestrateurs...")
    
    try:
        # Tester l'import des orchestrateurs
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
        
        # Tester l'instanciation
        real_llm_orch = RealLLMOrchestrator()
        conv_orch = ConversationOrchestrator()
        
        assert real_llm_orch is not None, "RealLLMOrchestrator non instancié"
        assert conv_orch is not None, "ConversationOrchestrator non instancié"
        
        # Tester les méthodes réellement disponibles pour le pipeline Enhanced
        assert hasattr(real_llm_orch, 'run_orchestration'), "Méthode run_orchestration manquante sur RealLLMOrchestrator"
        assert hasattr(conv_orch, 'run_orchestration'), "Méthode run_orchestration manquante sur ConversationOrchestrator"
        
        logger.info("✅ Test intégration orchestrateurs : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test intégration orchestrateurs : ÉCHEC - {e}")
        return False


def run_all_tests():
    """Exécute tous les tests d'intégration."""
    logger.info("🚀 Début des tests d'intégration Advanced Rhetorical Enhanced")
    
    tests = [
        ("Pipeline Classique", test_pipeline_classic),
        ("Pipeline Enhanced", test_pipeline_enhanced),
        ("Arguments CLI", test_cli_arguments),
        ("Intégration Orchestrateurs", test_integration_with_orchestrators)
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Test: {test_name}")
        logger.info('='*50)
        
        success = test_func()
        results[test_name] = success
    
    # Rapport final
    logger.info(f"\n{'='*60}")
    logger.info("📊 RAPPORT FINAL DES TESTS")
    logger.info('='*60)
    
    total_tests = len(tests)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results.items():
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nRésumé: {passed_tests}/{total_tests} tests réussis")
    
    if failed_tests == 0:
        logger.info("🎉 TOUS LES TESTS SONT PASSÉS !")
        return True
    else:
        logger.warning(f"⚠️ {failed_tests} test(s) ont échoué")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test d'intégration avancé pour la refactorisation Enhanced du script advanced_rhetorical_analysis.py
=====================================================================================================

Ce test valide l'intégration complète de :
- Pipeline Enhanced extended (run_enhanced_rhetoric_pipeline)
- Script refactorisé avec nouveaux orchestrateurs
- Arguments CLI étendus
- Compatibilité avec l'écosystème refactorisé
"""

import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# Configuration du logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("TestAdvancedRhetoricalEnhanced")


def create_test_extracts() -> List[Dict[str, Any]]:
    """Crée des extraits de test pour les tests d'intégration."""
    return [
        {
            "source_name": "Test Corpus Philosophique",
            "extracts": [
                {
                    "extract_name": "Argument Fallacieux Test",
                    "extract_text": "Tous les politiciens sont corrompus car mon voisin dit que son maire a accepté un pot-de-vin.",
                    "context": "Test de sophisme de généralisation hâtive"
                },
                {
                    "extract_name": "Argument Complexe Test", 
                    "extract_text": "Si nous acceptons cette loi, alors nous devrons accepter toutes les lois similaires, ce qui mènera inevitablement à la dictature. Donc nous devons rejeter cette loi.",
                    "context": "Test de sophisme de pente glissante"
                }
            ]
        }
    ]


def create_test_base_results() -> List[Dict[str, Any]]:
    """Crée des résultats de base de test."""
    return [
        {
            "extract_name": "Argument Fallacieux Test",
            "source_name": "Test Corpus Philosophique",
            "analyses": {
                "contextual_fallacies": {"detected": ["hasty_generalization"]},
                "argument_coherence": {"score": 0.3},
                "semantic_analysis": {"sentiment": "negative"}
            }
        }
    ]


def test_pipeline_classic():
    """Test du pipeline classique (mode de compatibilité)."""
    logger.info("🧪 Test du pipeline classique...")
    
    try:
        from argumentation_analysis.pipelines.advanced_rhetoric import run_advanced_rhetoric_pipeline
        
        extracts = create_test_extracts()
        base_results = create_test_base_results()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        # Test du pipeline classique
        run_advanced_rhetoric_pipeline(
            extract_definitions=extracts,
            base_results=base_results,
            output_file=output_path,
            use_real_tools=False  # Utiliser les mocks pour le test
        )
        
        # Vérifier que le fichier de sortie existe et contient des données
        assert output_path.exists(), "Le fichier de sortie n'a pas été créé"
        
        with open(output_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        assert isinstance(results, list), "Les résultats doivent être une liste"
        assert len(results) > 0, "Les résultats ne doivent pas être vides"
        
        # Nettoyer
        output_path.unlink()
        
        logger.info("✅ Test pipeline classique : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test pipeline classique : ÉCHEC - {e}")
        return False


def test_pipeline_enhanced():
    """Test du pipeline Enhanced avec orchestrateurs."""
    logger.info("🧪 Test du pipeline Enhanced...")
    
    try:
        from argumentation_analysis.pipelines.advanced_rhetoric import run_enhanced_rhetoric_pipeline
        
        extracts = create_test_extracts()
        base_results = create_test_base_results()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        # Test avec orchestrateur real_llm (devrait fallback vers classic si non disponible)
        run_enhanced_rhetoric_pipeline(
            extract_definitions=extracts,
            base_results=base_results,
            output_file=output_path,
            orchestrator_type="real_llm",
            use_real_tools=False,
            llm_config={"model": "test-model", "temperature": 0.5}
        )
        
        # Vérifier que le fichier de sortie existe
        assert output_path.exists(), "Le fichier de sortie Enhanced n'a pas été créé"
        
        with open(output_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Vérifier la structure Enhanced
        assert "metadata" in results, "Les métadonnées Enhanced sont manquantes"
        assert "results" in results, "Les résultats Enhanced sont manquants"
        
        metadata = results["metadata"]
        assert metadata["pipeline_type"] == "enhanced_rhetoric", "Type de pipeline incorrect"
        assert "orchestrator_used" in metadata, "Orchestrateur utilisé non spécifié"
        
        # Nettoyer
        output_path.unlink()
        
        logger.info("✅ Test pipeline Enhanced : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test pipeline Enhanced : ÉCHEC - {e}")
        return False


def test_cli_arguments():
    """Test des nouveaux arguments CLI."""
    logger.info("🧪 Test des arguments CLI Enhanced...")
    
    try:
        from argumentation_analysis.utils.core_utils.cli_utils import parse_advanced_analysis_arguments
        import sys
        
        # Sauvegarder les arguments originaux
        original_argv = sys.argv.copy()
        
        # Tester les nouveaux arguments Enhanced
        test_args = [
            "test_script.py",
            "--enhanced",
            "--orchestrator", "real_llm",
            "--use-real-tools",
            "--llm-model", "gpt-3.5-turbo",
            "--temperature", "0.8",
            "--max-tokens", "2000"
        ]
        
        sys.argv = test_args
        args = parse_advanced_analysis_arguments()
        
        # Vérifier les nouveaux attributs
        assert hasattr(args, 'enhanced'), "Attribut 'enhanced' manquant"
        assert hasattr(args, 'orchestrator'), "Attribut 'orchestrator' manquant"
        assert hasattr(args, 'use_real_tools'), "Attribut 'use_real_tools' manquant"
        assert hasattr(args, 'llm_model'), "Attribut 'llm_model' manquant"
        assert hasattr(args, 'temperature'), "Attribut 'temperature' manquant"
        assert hasattr(args, 'max_tokens'), "Attribut 'max_tokens' manquant"
        
        # Vérifier les valeurs
        assert args.enhanced == True, "Valeur 'enhanced' incorrecte"
        assert args.orchestrator == "real_llm", "Valeur 'orchestrator' incorrecte"
        assert args.use_real_tools == True, "Valeur 'use_real_tools' incorrecte"
        assert args.llm_model == "gpt-3.5-turbo", "Valeur 'llm_model' incorrecte"
        assert args.temperature == 0.8, "Valeur 'temperature' incorrecte"
        assert args.max_tokens == 2000, "Valeur 'max_tokens' incorrecte"
        
        # Restaurer les arguments originaux
        sys.argv = original_argv
        
        logger.info("✅ Test arguments CLI Enhanced : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test arguments CLI Enhanced : ÉCHEC - {e}")
        # Restaurer les arguments en cas d'erreur
        sys.argv = original_argv
        return False


def test_integration_with_orchestrators():
    """Test d'intégration avec les orchestrateurs refactorisés."""
    logger.info("🧪 Test d'intégration avec orchestrateurs...")
    
    try:
        # Tester l'import des orchestrateurs
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
        
        # Tester l'instanciation
        real_llm_orch = RealLLMOrchestrator()
        conv_orch = ConversationOrchestrator()
        
        assert real_llm_orch is not None, "RealLLMOrchestrator non instancié"
        assert conv_orch is not None, "ConversationOrchestrator non instancié"
        
        # Tester les méthodes réellement disponibles pour le pipeline Enhanced
        assert hasattr(real_llm_orch, 'run_orchestration'), "Méthode run_orchestration manquante sur RealLLMOrchestrator"
        assert hasattr(conv_orch, 'run_orchestration'), "Méthode run_orchestration manquante sur ConversationOrchestrator"
        
        logger.info("✅ Test intégration orchestrateurs : SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test intégration orchestrateurs : ÉCHEC - {e}")
        return False


def run_all_tests():
    """Exécute tous les tests d'intégration."""
    logger.info("🚀 Début des tests d'intégration Advanced Rhetorical Enhanced")
    
    tests = [
        ("Pipeline Classique", test_pipeline_classic),
        ("Pipeline Enhanced", test_pipeline_enhanced),
        ("Arguments CLI", test_cli_arguments),
        ("Intégration Orchestrateurs", test_integration_with_orchestrators)
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Test: {test_name}")
        logger.info('='*50)
        
        success = test_func()
        results[test_name] = success
    
    # Rapport final
    logger.info(f"\n{'='*60}")
    logger.info("📊 RAPPORT FINAL DES TESTS")
    logger.info('='*60)
    
    total_tests = len(tests)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results.items():
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nRésumé: {passed_tests}/{total_tests} tests réussis")
    
    if failed_tests == 0:
        logger.info("🎉 TOUS LES TESTS SONT PASSÉS !")
        return True
    else:
        logger.warning(f"⚠️ {failed_tests} test(s) ont échoué")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
>>>>>>> BACKUP
