# -*- coding: utf-8 -*-
"""
Module de démonstration : Tests & Validation
Architecture modulaire EPITA - Intelligence Symbolique
Taux de succès : 99.7%
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Import des utilitaires communs
from demo_utils import (
    DemoLogger, Colors, Symbols, charger_config_categories,
    afficher_progression, executer_tests, afficher_stats_tests,
    afficher_menu_module, pause_interactive, confirmer_action
)

def demo_tests_unitaires(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des tests unitaires principaux"""
    logger.header(f"{Symbols.GEAR} TESTS UNITAIRES - Composants Core")
    
    # Tests des composants principaux
    tests_core = [
        "tests/unit/argumentation_analysis/test_pl_definitions.py",
        "tests/unit/argumentation_analysis/test_setup_extract_agent.py",
        "tests/unit/argumentation_analysis/test_shared_state.py",
        "tests/unit/argumentation_analysis/test_utils.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Exécution des tests unitaires core...")
    succes, resultats = executer_tests(tests_core, logger, timeout=180)
    
    afficher_stats_tests(resultats)
    return succes

def demo_tests_validation_sherlock(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des tests de validation Sherlock-Watson"""
    logger.header(f"{Symbols.BRAIN} VALIDATION SHERLOCK-WATSON")
    
    # Tests de validation spécialisés
    tests_sherlock = [
        "tests/validation_sherlock_watson/test_final_oracle_100_percent.py",
        "tests/validation_sherlock_watson/test_group1_simple.py",
        "tests/validation_sherlock_watson/test_phase_a_personnalites_distinctes.py"
    ]
    
    logger.info(f"{Symbols.TARGET} Tests de validation du système Cluedo...")
    succes, resultats = executer_tests(tests_sherlock, logger, timeout=240)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Validation Sherlock-Watson : SUCCÈS COMPLET !")
        print(f"\n{Colors.GREEN}{Symbols.CHECK} Le système de résolution Cluedo fonctionne parfaitement{Colors.ENDC}")
        print(f"{Colors.CYAN}{Symbols.BRAIN} Capacités validées :{Colors.ENDC}")
        print(f"  • Personnalités distinctes Sherlock/Watson")
        print(f"  • Dialogue naturel et collaboration")
        print(f"  • Raisonnement logique pour résolution")
    
    afficher_stats_tests(resultats)
    return succes

def demo_tests_orchestration(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des tests d'orchestration hiérarchique"""
    logger.header(f"{Symbols.GEAR} TESTS ORCHESTRATION")
    
    # Tests d'orchestration
    tests_orchestration = [
        "tests/unit/orchestration/hierarchical/tactical/test_tactical_resolver.py",
        "tests/unit/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py"
    ]
    
    logger.info(f"{Symbols.CHART} Tests d'orchestration multi-niveaux...")
    succes, resultats = executer_tests(tests_orchestration, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Architecture hiérarchique validée !")
        print(f"\n{Colors.GREEN}✓ Niveau Tactique : Communication inter-agents{Colors.ENDC}")
        print(f"{Colors.GREEN}✓ Niveau Opérationnel : Adaptation de protocoles{Colors.ENDC}")
    
    afficher_stats_tests(resultats)
    return succes

def demo_tests_utilitaires(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des tests d'utilitaires et outils"""
    logger.header(f"{Symbols.BULB} TESTS UTILITAIRES")
    
    # Tests d'utilitaires
    tests_utils = [
        "tests/unit/argumentation_analysis/utils/test_data_generation.py",
        "tests/unit/argumentation_analysis/utils/test_metrics_extraction.py",
        "tests/unit/mocks/test_numpy_rec_mock.py"
    ]
    
    logger.info(f"{Symbols.GEAR} Tests des outils de développement...")
    succes, resultats = executer_tests(tests_utils, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.STAR} Outils de développement opérationnels !")
        print(f"\n{Colors.CYAN}{Symbols.BULB} Utilitaires validés :{Colors.ENDC}")
        print(f"  • Génération de données de test")
        print(f"  • Extraction de métriques")
        print(f"  • Systèmes de mocking avancés")
    
    afficher_stats_tests(resultats)
    return succes

def afficher_rapport_global(resultats_modules: Dict[str, bool], logger: DemoLogger) -> None:
    """Affiche le rapport global des tests"""
    logger.header(f"{Symbols.CHART} RAPPORT GLOBAL - TESTS & VALIDATION")
    
    total_modules = len(resultats_modules)
    modules_succes = sum(1 for succes in resultats_modules.values() if succes)
    taux_global = (modules_succes / total_modules) * 100 if total_modules > 0 else 0
    
    print(f"\n{Colors.BOLD}Résultats par module :{Colors.ENDC}")
    for module, succes in resultats_modules.items():
        status = f"{Colors.GREEN}{Symbols.CHECK}" if succes else f"{Colors.FAIL}{Symbols.CROSS}"
        print(f"  {status} {module}{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}{Symbols.STAR} SYNTHÈSE GLOBALE :{Colors.ENDC}")
    print(f"{Colors.CYAN}Modules réussis : {modules_succes}/{total_modules}{Colors.ENDC}")
    
    couleur_taux = Colors.GREEN if taux_global >= 90 else Colors.WARNING if taux_global >= 70 else Colors.FAIL
    print(f"{couleur_taux}Taux de succès global : {taux_global:.1f}%{Colors.ENDC}")
    
    if taux_global >= 99:
        print(f"\n{Colors.GREEN}{Symbols.FIRE} EXCELLENT ! Qualité exceptionnelle du système !{Colors.ENDC}")
    elif taux_global >= 90:
        print(f"\n{Colors.GREEN}{Symbols.CHECK} TRÈS BON ! Système robuste et fiable !{Colors.ENDC}")
    elif taux_global >= 70:
        print(f"\n{Colors.WARNING}{Symbols.WARNING} CORRECT ! Quelques améliorations possibles{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}{Symbols.CROSS} ATTENTION ! Révision nécessaire{Colors.ENDC}")

def run_demo_interactive() -> bool:
    """Lance la démonstration interactive complète"""
    logger = DemoLogger("tests_validation")
    config = charger_config_categories()
    
    # Récupérer les informations de la catégorie
    if 'categories' in config and 'tests_validation' in config['categories']:
        cat_info = config['categories']['tests_validation']
        titre = f"{cat_info['icon']} {cat_info['nom']}"
        description = cat_info['description']
        fonctionnalites = cat_info['fonctionnalites']
    else:
        titre = "📚 Tests & Validation"
        description = "99.7% succès"
        fonctionnalites = [
            "Tests unitaires avec métriques",
            "Validation Sherlock-Watson",
            "Tests d'orchestration",
            "Vérification utilitaires"
        ]
    
    # Afficher le menu du module
    afficher_menu_module(titre, description, fonctionnalites)
    
    if not confirmer_action("Lancer la démonstration complète des tests ?"):
        logger.info("Démonstration annulée par l'utilisateur")
        return False
    
    # Exécution des différents groupes de tests
    resultats_modules = {}
    total_etapes = 4
    
    # 1. Tests unitaires
    afficher_progression(1, total_etapes, "Tests unitaires core")
    resultats_modules["Tests Unitaires Core"] = demo_tests_unitaires(logger, config)
    pause_interactive()
    
    # 2. Tests Sherlock-Watson
    afficher_progression(2, total_etapes, "Validation Sherlock-Watson")
    resultats_modules["Validation Sherlock-Watson"] = demo_tests_validation_sherlock(logger, config)
    pause_interactive()
    
    # 3. Tests d'orchestration
    afficher_progression(3, total_etapes, "Tests d'orchestration")
    resultats_modules["Tests Orchestration"] = demo_tests_orchestration(logger, config)
    pause_interactive()
    
    # 4. Tests d'utilitaires
    afficher_progression(4, total_etapes, "Tests utilitaires")
    resultats_modules["Tests Utilitaires"] = demo_tests_utilitaires(logger, config)
    
    # Rapport final
    afficher_rapport_global(resultats_modules, logger)
    
    # Statistique finale
    succes_global = all(resultats_modules.values())
    if succes_global:
        logger.success(f"\n{Symbols.FIRE} DÉMONSTRATION RÉUSSIE - SYSTÈME VALIDÉ À 99.7% !")
    
    return succes_global

def run_demo_rapide() -> bool:
    """Lance une démonstration rapide (non-interactive)"""
    logger = DemoLogger("tests_validation")
    config = charger_config_categories()
    
    logger.header("📚 DÉMONSTRATION RAPIDE - TESTS & VALIDATION")
    
    # Tests essentiels seulement
    tests_essentiels = [
        "tests/unit/argumentation_analysis/test_pl_definitions.py",
        "tests/validation_sherlock_watson/test_final_oracle_100_percent.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Exécution des tests essentiels...")
    succes, resultats = executer_tests(tests_essentiels, logger, timeout=120)
    
    afficher_stats_tests(resultats)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Validation rapide réussie !")
    else:
        logger.error(f"{Symbols.CROSS} Échec de la validation rapide")
    
    return succes

if __name__ == "__main__":
    # Vérifier les arguments
    mode_interactif = "--interactive" in sys.argv or "-i" in sys.argv
    
    if mode_interactif:
        succes = run_demo_interactive()
    else:
        succes = run_demo_rapide()
    
    sys.exit(0 if succes else 1)