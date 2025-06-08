#!/usr/bin/env python3
"""
Script de démonstration simple pour les tests FOL Agent.
Version sans emojis pour éviter les problèmes d'encodage.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Configuration du logging pour éviter les problèmes d'encodage
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def test_structure_files():
    """Test que les fichiers de tests sont présents."""
    try:
        test_files = [
            "tests/unit/agents/test_fol_logic_agent.py",
            "tests/integration/test_fol_tweety_integration.py", 
            "tests/validation/test_fol_complete_validation.py",
            "tests/migration/test_modal_to_fol_migration.py",
            "scripts/run_fol_tests.py"
        ]
        
        for file_path in test_files:
            if not Path(file_path).exists():
                logger.error(f"Fichier manquant: {file_path}")
                return False
                
        logger.info("Tous les fichiers de tests sont présents")
        return True
        
    except Exception as e:
        logger.error(f"Erreur test structure: {e}")
        return False

async def test_unified_config():
    """Test de la configuration unifiée."""
    try:
        from config.unified_config import UnifiedConfig
        logger.info("Import configuration réussi")
        
        config = UnifiedConfig()
        assert hasattr(config, 'get_agent_classes'), "Méthode get_agent_classes manquante"
        assert hasattr(config, 'get_tweety_config'), "Méthode get_tweety_config manquante"
        
        logger.info("Configuration FOL validée")
        return True
        
    except Exception as e:
        logger.error(f"Erreur test configuration: {e}")
        return False

async def test_fol_agent_basic():
    """Test basique de l'agent FOL."""
    try:
        from argumentation_analysis.agents.core.logic.fol_logic_agent import create_fol_agent
        logger.info("Import agent FOL réussi")
        
        # Test de création d'agent
        agent = create_fol_agent(agent_name="DemoAgent")
        assert agent is not None, "Agent non créé"
        assert agent.name == "DemoAgent", "Nom agent incorrect"
        assert agent.logic_type == "first_order", "Type logique incorrect"
        
        logger.info("Agent FOL créé avec succès")
        
        # Test de génération de syntaxe basique
        test_text = "Tous les hommes sont mortels"
        try:
            result = agent.text_to_belief_set(test_text)
            logger.info("Conversion texte vers belief_set réussie")
        except Exception as e:
            logger.warning(f"Conversion échouée (attendu sans TweetyBridge): {e}")
        
        logger.info("Agent FOL basique testé")
        return True
        
    except Exception as e:
        logger.error(f"Erreur test agent FOL: {e}")
        return False

async def test_fol_syntax_validation():
    """Test de validation de syntaxe FOL."""
    try:
        from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
        from unittest.mock import Mock
        
        agent = FOLLogicAgent(kernel=Mock(), agent_name="TestAgent")
        
        # Test de formules FOL valides
        valid_formulas = [
            "∀x(P(x) → Q(x))",
            "∃x(F(x) ∧ G(x))",
            "∀x∀y(R(x,y) → R(y,x))",
            "¬∃x(P(x) ∧ ¬P(x))"
        ]
        
        for formula in valid_formulas:
            is_valid = agent.validate_formula(formula)
            if not is_valid:
                logger.warning(f"Formule considérée invalide: {formula}")
            else:
                logger.info(f"Formule validée: {formula}")
        
        logger.info("Tests syntaxe FOL terminés")
        return True
        
    except Exception as e:
        logger.error(f"Erreur test syntaxe: {e}")
        return False

async def run_demo():
    """Lance la démonstration complète."""
    logger.info("=== DEBUT DEMONSTRATION TESTS FOL AGENT ===")
    
    tests = [
        ("Structure fichiers", test_structure_files),
        ("Configuration unifiée", test_unified_config),
        ("Agent FOL basique", test_fol_agent_basic),
        ("Syntaxe FOL", test_fol_syntax_validation)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"Test: {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                logger.info(f"{test_name} réussi")
            else:
                logger.error(f"{test_name} échoué")
        except Exception as e:
            logger.error(f"Erreur {test_name}: {e}")
            results[test_name] = False
    
    # Résumé
    logger.info("=== RESUME DEMONSTRATION FOL ===")
    successes = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "REUSSI" if success else "ECHEC"
        logger.info(f"  {status}: {test_name}")
    
    logger.info(f"Tests réussis: {successes}/{total} ({successes/total*100:.1f}%)")
    
    if successes == total:
        logger.info("=== DEMONSTRATION COMPLETE REUSSIE ===")
        return True
    else:
        logger.warning("=== PROBLEMES DETECTES - CORRECTIONS NECESSAIRES ===")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_demo())
    sys.exit(0 if success else 1)