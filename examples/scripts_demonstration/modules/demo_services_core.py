# -*- coding: utf-8 -*-
"""
Module de démonstration : Services Core & Extraction
Architecture modulaire EPITA - Intelligence Symbolique
Architecture fondamentale du système
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Import des utilitaires communs
from .demo_utils import (
    DemoLogger, Colors, Symbols, charger_config_categories,
    afficher_progression, executer_tests, afficher_stats_tests,
    afficher_menu_module, pause_interactive, confirmer_action
)

def demo_agents_extraction(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des agents d'extraction de données"""
    logger.header(f"{Symbols.GEAR} AGENTS D'EXTRACTION")
    
    # Tests des agents d'extraction
    tests_extraction = [
        "tests/unit/argumentation_analysis/test_setup_extract_agent_real.py",
        "tests/unit/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests des agents d'extraction...")
    succes, resultats = executer_tests(tests_extraction, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Agents d'extraction opérationnels !")
        print(f"\n{Colors.CYAN}{Symbols.BULB} Fonctionnalités d'extraction :{Colors.ENDC}")
        print(f"  • Extraction automatique de définitions")
        print(f"  • Parsing de structures argumentatives")
        print(f"  • Identification d'entités logiques")
        print(f"  • Adaptation de formats de données")
        
        # Exemple d'extraction
        print(f"\n{Colors.GREEN}{Symbols.GEAR} Exemple d'extraction :{Colors.ENDC}")
        print(f'{Colors.CYAN}Texte: "Si P alors Q. P est vrai."')
        print(f'→ Extraction: Règle(P→Q), Fait(P), Conclusion(Q){Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_reparation_marqueurs(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la réparation de marqueurs"""
    logger.header(f"{Symbols.GEAR} RÉPARATION DE MARQUEURS")
    
    # Tests de réparation
    tests_reparation = [
        "tests/unit/argumentation_analysis/test_repair_extract_markers.py"
    ]
    
    logger.info(f"{Symbols.TARGET} Tests de réparation de marqueurs...")
    succes, resultats = executer_tests(tests_reparation, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Système de réparation fonctionnel !")
        print(f"\n{Colors.BLUE}{Symbols.GEAR} Capacités de réparation :{Colors.ENDC}")
        print(f"  • Détection d'inconsistances dans les marqueurs")
        print(f"  • Correction automatique des erreurs de format")
        print(f"  • Validation de cohérence syntaxique")
        print(f"  • Récupération d'erreurs de parsing")
        
        # Exemple de réparation
        print(f"\n{Colors.WARNING}{Symbols.WARNING} Exemple de réparation :{Colors.ENDC}")
        print(f'{Colors.FAIL}Erreur: "Si P alord Q" (typo)')
        print(f'{Colors.GREEN}Réparé: "Si P alors Q" (correction automatique){Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_verification_extraits(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la vérification d'extraits"""
    logger.header(f"{Symbols.CHECK} VÉRIFICATION D'EXTRAITS")
    
    # Tests de vérification
    tests_verification = [
        "tests/unit/argumentation_analysis/test_verify_extracts.py"
    ]
    
    logger.info(f"{Symbols.CHART} Tests de vérification d'extraits...")
    succes, resultats = executer_tests(tests_verification, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Système de vérification validé !")
        print(f"\n{Colors.GREEN}{Symbols.CHECK} Processus de vérification :{Colors.ENDC}")
        print(f"  • Validation sémantique des extraits")
        print(f"  • Contrôle de cohérence logique")
        print(f"  • Vérification de complétude")
        print(f"  • Détection d'ambiguïtés")
        
        # Processus de vérification
        print(f"\n{Colors.CYAN}{Symbols.GEAR} Pipeline de vérification :{Colors.ENDC}")
        print(f"  1. {Colors.BLUE}Extraction{Colors.ENDC} → Analyse syntaxique")
        print(f"  2. {Colors.WARNING}Réparation{Colors.ENDC} → Correction d'erreurs")
        print(f"  3. {Colors.GREEN}Vérification{Colors.ENDC} → Validation finale")
    
    afficher_stats_tests(resultats)
    return succes

def demo_gestion_definitions(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la gestion des définitions"""
    logger.header(f"{Symbols.BOOK} GESTION DES DÉFINITIONS")
    
    logger.info(f"{Symbols.BRAIN} Système de gestion des définitions...")
    
    # Simulation car pas de tests spécifiques
    print(f"\n{Colors.CYAN}{Symbols.BULB} Capacités de gestion des définitions :{Colors.ENDC}")
    print(f"  • Stockage hiérarchique de définitions")
    print(f"  • Résolution de conflits de définitions")
    print(f"  • Héritage et spécialisation de concepts")
    print(f"  • Validation de cohérence sémantique")
    
    # Exemple de hiérarchie
    print(f"\n{Colors.BOLD}{Symbols.TARGET} Exemple de hiérarchie de définitions :{Colors.ENDC}")
    print(f'{Colors.GREEN}Animal{Colors.ENDC}')
    print(f'  ├─ {Colors.BLUE}Mammifère{Colors.ENDC}')
    print(f'  │   ├─ {Colors.CYAN}Chat{Colors.ENDC} (carnivore, domestique)')
    print(f'  │   └─ {Colors.CYAN}Chien{Colors.ENDC} (omnivore, domestique)')
    print(f'  └─ {Colors.BLUE}Oiseau{Colors.ENDC}')
    print(f'      ├─ {Colors.CYAN}Aigle{Colors.ENDC} (carnivore, vole)')
    print(f'      └─ {Colors.CYAN}Pingouin{Colors.ENDC} (carnivore, ne vole pas)')
    
    # Relations logiques
    print(f"\n{Colors.WARNING}{Symbols.BRAIN} Relations logiques :{Colors.ENDC}")
    print(f'  Chat(x) → Mammifère(x) ∧ Animal(x)')
    print(f'  Mammifère(x) → Animal(x)')
    print(f'  ∀x: Chat(x) → ¬Oiseau(x)')
    
    logger.success(f"{Symbols.CHECK} Gestion des définitions présentée !")
    return True

def demo_communication_services(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des services de communication"""
    logger.header(f"{Symbols.GEAR} SERVICES DE COMMUNICATION")
    
    # Tests de communication
    tests_communication = [
        "tests/unit/argumentation_analysis/test_mock_communication.py",
        "tests/unit/argumentation_analysis/test_request_response_direct.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests des services de communication...")
    succes, resultats = executer_tests(tests_communication, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Services de communication validés !")
        print(f"\n{Colors.BLUE}{Symbols.GEAR} Architecture de communication :{Colors.ENDC}")
        print(f"  • Messages asynchrones inter-services")
        print(f"  • Protocoles de requête-réponse")
        print(f"  • Files d'attente et bufferisation")
        print(f"  • Gestion d'erreurs et retry automatique")
        
        # Exemple de communication
        print(f"\n{Colors.CYAN}{Symbols.ROCKET} Exemple de flux de communication :{Colors.ENDC}")
        print(f'  Service A: {Colors.GREEN}Request(analyze_text, "Si P alors Q"){Colors.ENDC}')
        print(f'           ↓')
        print(f'  Service B: {Colors.BLUE}Processing...{Colors.ENDC}')
        print(f'           ↓')
        print(f'  Service A: {Colors.GREEN}Response(rules=[P→Q], facts=[], conclusions=[]){Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_etat_partage(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la gestion d'état partagé"""
    logger.header(f"{Symbols.CHART} ÉTAT PARTAGÉ")
    
    # Tests d'état partagé
    tests_etat = [
        "tests/unit/argumentation_analysis/test_shared_state.py",
        "tests/unit/argumentation_analysis/test_state_manager_plugin.py"
    ]
    
    logger.info(f"{Symbols.CHART} Tests de gestion d'état partagé...")
    succes, resultats = executer_tests(tests_etat, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Gestion d'état partagé opérationnelle !")
        print(f"\n{Colors.GREEN}{Symbols.CHART} Fonctionnalités d'état partagé :{Colors.ENDC}")
        print(f"  • Synchronisation multi-agents")
        print(f"  • Cohérence transactionnelle")
        print(f"  • Versioning et rollback")
        print(f"  • Notification de changements")
        
        # Architecture d'état
        print(f"\n{Colors.BOLD}{Symbols.GEAR} Architecture d'état distribué :{Colors.ENDC}")
        print(f'  {Colors.CYAN}Agent 1{Colors.ENDC} ←→ {Colors.BLUE}State Manager{Colors.ENDC} ←→ {Colors.CYAN}Agent 2{Colors.ENDC}')
        print(f'               ↕')
        print(f'        {Colors.GREEN}Shared Knowledge Base{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def run_demo_interactive() -> bool:
    """Lance la démonstration interactive complète"""
    logger = DemoLogger("services_core")
    config = charger_config_categories()
    
    # Récupérer les informations de la catégorie
    if 'categories' in config and 'services_core' in config['categories']:
        cat_info = config['categories']['services_core']
        titre = f"{cat_info['icon']} {cat_info['nom']}"
        description = cat_info['description']
        fonctionnalites = cat_info['fonctionnalites']
    else:
        titre = "[CORE] Services Core & Extraction"
        description = "Architecture fondamentale"
        fonctionnalites = [
            "Agents d'extraction de données",
            "Services de communication",
            "Gestion des définitions",
            "État partagé et synchronisation"
        ]
    
    # Afficher le menu du module
    afficher_menu_module(titre, description, fonctionnalites)
    
    if not confirmer_action("Lancer la démonstration des services core ?"):
        logger.info("Démonstration annulée par l'utilisateur")
        return False
    
    # Exécution des différents services
    resultats_modules = {}
    total_etapes = 6
    
    # 1. Agents d'extraction
    afficher_progression(1, total_etapes, "Agents d'extraction")
    resultats_modules["Agents Extraction"] = demo_agents_extraction(logger, config)
    pause_interactive()
    
    # 2. Réparation de marqueurs
    afficher_progression(2, total_etapes, "Réparation marqueurs")
    resultats_modules["Réparation Marqueurs"] = demo_reparation_marqueurs(logger, config)
    pause_interactive()
    
    # 3. Vérification d'extraits
    afficher_progression(3, total_etapes, "Vérification extraits")
    resultats_modules["Vérification Extraits"] = demo_verification_extraits(logger, config)
    pause_interactive()
    
    # 4. Gestion des définitions
    afficher_progression(4, total_etapes, "Gestion définitions")
    resultats_modules["Gestion Définitions"] = demo_gestion_definitions(logger, config)
    pause_interactive()
    
    # 5. Services de communication
    afficher_progression(5, total_etapes, "Services communication")
    resultats_modules["Services Communication"] = demo_communication_services(logger, config)
    pause_interactive()
    
    # 6. État partagé
    afficher_progression(6, total_etapes, "État partagé")
    resultats_modules["État Partagé"] = demo_etat_partage(logger, config)
    
    # Rapport final
    logger.header(f"{Symbols.CHART} RAPPORT FINAL - SERVICES CORE")
    total_modules = len(resultats_modules)
    modules_succes = sum(1 for succes in resultats_modules.values() if succes)
    
    print(f"\n{Colors.BOLD}Résultats par service :{Colors.ENDC}")
    for module, succes in resultats_modules.items():
        status = f"{Colors.GREEN}{Symbols.CHECK}" if succes else f"{Colors.FAIL}{Symbols.CROSS}"
        print(f"  {status} {module}{Colors.ENDC}")
    
    taux_succes = (modules_succes / total_modules) * 100
    couleur_taux = Colors.GREEN if taux_succes >= 90 else Colors.WARNING
    print(f"\n{couleur_taux}{Symbols.STAR} Taux de succès : {taux_succes:.1f}%{Colors.ENDC}")
    
    succes_global = modules_succes == total_modules
    if succes_global:
        logger.success(f"\n{Symbols.FIRE} SERVICES CORE : ARCHITECTURE FONDAMENTALE VALIDÉE !")
    
    return succes_global

def run_demo_rapide() -> bool:
    """Lance une démonstration rapide (non-interactive)"""
    logger = DemoLogger("services_core")
    
    logger.header("[CORE] DÉMONSTRATION RAPIDE - SERVICES CORE")
    
    # Tests essentiels seulement
    tests_essentiels = [
        "tests/unit/argumentation_analysis/test_setup_extract_agent_real.py",
        "tests/unit/argumentation_analysis/test_shared_state.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests agents d'extraction et état partagé...")
    succes, resultats = executer_tests(tests_essentiels, logger, timeout=90)
    
    afficher_stats_tests(resultats)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Validation rapide des services core réussie !")
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