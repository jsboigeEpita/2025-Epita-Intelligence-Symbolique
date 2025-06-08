#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Démonstration rapide des tests FOL Agent.

Ce script teste rapidement l'agent FOL et la suite de tests créée
pour valider que l'implémentation fonctionne correctement.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ajout du chemin pour imports
sys.path.insert(0, str(Path.cwd()))

async def test_fol_agent_basic():
    """Test basique de l'agent FOL."""
    try:
        from argumentation_analysis.agents.core.logic.fol_logic_agent import (
            FOLLogicAgent, 
            FOLAnalysisResult, 
            create_fol_agent
        )
        
        logger.info("✅ Import agent FOL réussi")
        
        # Création agent
        agent = create_fol_agent(agent_name="DemoAgent")
        logger.info(f"✅ Agent créé: {agent.agent_name}")
        
        # Test analyse basique
        test_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        result = await agent.analyze(test_text)
        
        # Vérifications
        assert isinstance(result, FOLAnalysisResult), "Résultat doit être FOLAnalysisResult"
        assert len(result.formulas) > 0, "Doit générer des formules"
        assert result.confidence_score >= 0.0, "Score confiance valide"
        
        logger.info(f"✅ Analyse réussie:")
        logger.info(f"   Formules: {result.formulas}")
        logger.info(f"   Cohérence: {result.consistency_check}")
        logger.info(f"   Confiance: {result.confidence_score:.2f}")
        logger.info(f"   Inférences: {len(result.inferences)}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Erreur import agent FOL: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur test agent FOL: {e}")
        return False

def test_unified_config():
    """Test configuration unifiée FOL."""
    try:
        from config.unified_config import (
            UnifiedConfig, 
            LogicType, 
            AgentType, 
            PresetConfigs
        )
        
        logger.info("✅ Import configuration réussi")
        
        # Test configuration FOL
        config = PresetConfigs.authentic_fol()
        assert config.logic_type == LogicType.FOL
        assert AgentType.FOL_LOGIC in config.agents
        
        # Test mapping agent
        agent_classes = config.get_agent_classes()
        assert "fol_logic" in agent_classes
        assert agent_classes["fol_logic"] == "FirstOrderLogicAgent"
        
        logger.info("✅ Configuration FOL validée")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Erreur import configuration: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur test configuration: {e}")
        return False

def test_files_structure():
    """Test structure des fichiers de tests."""
    test_files = [
        "tests/unit/agents/test_fol_logic_agent.py",
        "tests/integration/test_fol_tweety_integration.py", 
        "tests/validation/test_fol_complete_validation.py",
        "tests/migration/test_modal_to_fol_migration.py",
        "scripts/run_fol_tests.py",
        "tests/README_FOL_TESTS.md"
    ]
    
    missing_files = []
    for file_path in test_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"❌ Fichiers manquants: {missing_files}")
        return False
    
    logger.info("✅ Structure fichiers tests validée")
    return True

async def run_demo():
    """Exécute la démonstration complète."""
    logger.info("🚀 Début démonstration tests FOL Agent")
    
    tests = [
        ("Structure fichiers", test_files_structure),
        ("Configuration unifiée", test_unified_config),
        ("Agent FOL basique", test_fol_agent_basic)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"▶️ Test: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} réussi")
            else:
                logger.error(f"❌ {test_name} échoué")
                
        except Exception as e:
            logger.error(f"❌ Erreur {test_name}: {e}")
            results[test_name] = False
    
    # Résumé
    total_tests = len(results)
    passed_tests = sum(results.values())
    success_rate = passed_tests / total_tests
    
    logger.info("\n" + "="*60)
    logger.info("📋 RÉSUMÉ DÉMONSTRATION FOL")
    logger.info("="*60)
    logger.info(f"Tests réussis: {passed_tests}/{total_tests} ({success_rate:.1%})")
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"  {status} {test_name}")
    
    if success_rate == 1.0:
        logger.info("\n🎉 Démonstration réussie - Suite tests FOL opérationnelle!")
        logger.info("\n📋 Prochaines étapes:")
        logger.info("  1. Exécuter: python scripts/run_fol_tests.py --unit-only")
        logger.info("  2. Puis: python scripts/run_fol_tests.py --integration")
        logger.info("  3. Enfin: python scripts/run_fol_tests.py --all --real-tweety")
    else:
        logger.warning("\n⚠️ Problèmes détectés - Corrections nécessaires")
    
    return success_rate == 1.0

if __name__ == "__main__":
    success = asyncio.run(run_demo())
    sys.exit(0 if success else 1)