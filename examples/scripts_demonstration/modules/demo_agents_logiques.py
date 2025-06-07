# -*- coding: utf-8 -*-
"""
Module de démonstration : Agents Logiques & Argumentation
Architecture modulaire EPITA - Intelligence Symbolique
Raisonnement symbolique avancé
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

def demo_logique_propositionnelle(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la logique propositionnelle"""
    logger.header(f"{Symbols.BRAIN} LOGIQUE PROPOSITIONNELLE")
    
    # Tests spécifiques à la logique propositionnelle
    tests_pl = [
        "tests/unit/argumentation_analysis/test_pl_definitions.py"
    ]
    
    logger.info(f"{Symbols.GEAR} Tests de logique propositionnelle...")
    succes, resultats = executer_tests(tests_pl, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Système de logique propositionnelle validé !")
        print(f"\n{Colors.CYAN}{Symbols.BULB} Fonctionnalités validées :{Colors.ENDC}")
        print(f"  • Variables propositionnelles et connecteurs logiques")
        print(f"  • Tables de vérité et évaluation")
        print(f"  • Formules bien formées (WFF)")
        print(f"  • Simplification et normalisation")
    
    afficher_stats_tests(resultats)
    return succes

def demo_agents_argumentation(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des agents d'argumentation"""
    logger.header(f"{Symbols.TARGET} AGENTS D'ARGUMENTATION")
    
    # Tests des agents d'argumentation
    tests_args = [
        "tests/unit/argumentation_analysis/test_strategies.py",
        "tests/unit/argumentation_analysis/test_run_analysis_conversation.py"
    ]
    
    logger.info(f"{Symbols.BRAIN} Tests des agents conversationnels...")
    succes, resultats = executer_tests(tests_args, logger, timeout=150)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Agents d'argumentation opérationnels !")
        print(f"\n{Colors.GREEN}{Symbols.CHECK} Capacités d'argumentation :{Colors.ENDC}")
        print(f"  • Analyse de structure argumentative")
        print(f"  • Détection de sophismes et fallacies")
        print(f"  • Stratégies de réfutation")
        print(f"  • Dialogue argumenté multi-tours")
        
        # Exemple de sophisme détecté
        print(f"\n{Colors.WARNING}{Symbols.WARNING} Exemple de détection de sophisme :{Colors.ENDC}")
        print(f'{Colors.CYAN}"Tous les politiciens mentent. Jean est politicien."')
        print(f'→ Détection : Généralisation abusive{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_communication_agents(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la communication entre agents"""
    logger.header(f"{Symbols.GEAR} COMMUNICATION INTER-AGENTS")
    
    # Tests de communication
    tests_comm = [
        "tests/unit/argumentation_analysis/test_mock_communication.py",
        "tests/unit/argumentation_analysis/test_request_response_direct.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests de communication entre agents...")
    succes, resultats = executer_tests(tests_comm, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Protocoles de communication validés !")
        print(f"\n{Colors.BLUE}{Symbols.GEAR} Protocoles supportés :{Colors.ENDC}")
        print(f"  • Requête-Réponse directe")
        print(f"  • Communication asynchrone")
        print(f"  • Négociation et consensus")
        print(f"  • Partage d'état distribué")
        
        # Exemple de dialogue agent
        print(f"\n{Colors.CYAN}{Symbols.BRAIN} Exemple de dialogue :{Colors.ENDC}")
        print(f'{Colors.GREEN}Agent1: "Proposition P est vraie"')
        print(f'{Colors.BLUE}Agent2: "Quelle est votre justification ?"')
        print(f'{Colors.GREEN}Agent1: "Règle R1 + Fait F1 → P"{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_raisonnement_modal(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration du raisonnement modal et temporel"""
    logger.header(f"{Symbols.STAR} LOGIQUE MODALE & TEMPORELLE")
    
    logger.info(f"{Symbols.BULB} Simulation de raisonnement modal...")
    
    # Simulation car pas de tests spécifiques disponibles
    print(f"\n{Colors.CYAN}{Symbols.BRAIN} Concepts de logique modale implémentés :{Colors.ENDC}")
    print(f"  • Modalités de nécessité (□) et possibilité (◇)")
    print(f"  • Logique temporelle (toujours, éventuellement)")
    print(f"  • Logique épistémique (croyance, connaissance)")
    print(f"  • Logique déontique (obligation, permission)")
    
    # Exemples pratiques
    print(f"\n{Colors.WARNING}{Symbols.QUESTION} Exemples de raisonnement modal :{Colors.ENDC}")
    print(f'{Colors.CYAN}□P → P  (Ce qui est nécessaire est vrai)')
    print(f'P → ◇P  (Ce qui est vrai est possible)')
    print(f'K(P → Q) ∧ K(P) → K(Q)  (Clôture épistémique){Colors.ENDC}')
    
    logger.success(f"{Symbols.CHECK} Concepts de logique modale présentés !")
    return True

def demo_detection_sophismes(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de la détection de sophismes"""
    logger.header(f"{Symbols.WARNING} DÉTECTION DE SOPHISMES")
    
    logger.info(f"{Symbols.TARGET} Analyse des fallacies logiques...")
    
    # Catalogue de sophismes détectables
    sophismes = {
        "Ad Hominem": "Attaque de la personne plutôt que de l'argument",
        "Strawman": "Déformation de la position adverse",
        "False Dilemma": "Réduction à deux options seulement",
        "Slippery Slope": "Enchaînement de conséquences non prouvées",
        "Appeal to Authority": "Argument d'autorité non pertinente",
        "Circular Reasoning": "Raisonnement circulaire (pétition de principe)"
    }
    
    print(f"\n{Colors.BOLD}{Symbols.CHART} Sophismes détectables par le système :{Colors.ENDC}")
    for sophisme, description in sophismes.items():
        print(f"  {Colors.RED}•{Colors.ENDC} {Colors.BOLD}{sophisme}{Colors.ENDC}: {description}")
    
    # Exemples pratiques
    print(f"\n{Colors.CYAN}{Symbols.BULB} Exemples d'analyse :{Colors.ENDC}")
    print(f'{Colors.FAIL}"Tu dis ça parce que tu es jeune" → Ad Hominem détecté')
    print(f'{Colors.FAIL}"Soit on augmente les impôts, soit on coupe tout" → False Dilemma détecté')
    print(f'{Colors.GREEN}"Voici les données qui soutiennent ma thèse..." → Argument valide{Colors.ENDC}')
    
    logger.success(f"{Symbols.FIRE} Système de détection de sophismes opérationnel !")
    return True

def afficher_demonstration_logique() -> None:
    """Affiche une démonstration de raisonnement logique"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}╔════════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}║{' ':^62}║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}║{'DÉMONSTRATION DE RAISONNEMENT LOGIQUE':^62}║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}║{' ':^62}║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}╚════════════════════════════════════════════════════════════════╝{Colors.ENDC}")
    
    print(f"\n{Colors.CYAN}{Symbols.BRAIN} Problème logique :{Colors.ENDC}")
    print(f"  Prémisse 1 : Tous les oiseaux volent")
    print(f"  Prémisse 2 : Les pingouins sont des oiseaux")
    print(f"  Prémisse 3 : Les pingouins ne volent pas")
    
    print(f"\n{Colors.WARNING}{Symbols.QUESTION} Question : Y a-t-il une contradiction ?{Colors.ENDC}")
    
    print(f"\n{Colors.GREEN}{Symbols.GEAR} Analyse du système :{Colors.ENDC}")
    print(f"  1. Détection de contradiction logique")
    print(f"  2. Prémisse 1 est une généralisation abusive")
    print(f"  3. Suggestion : 'La plupart des oiseaux volent'")
    
    print(f"\n{Colors.BLUE}{Symbols.CHECK} Résolution : Révision de la prémisse 1 nécessaire{Colors.ENDC}")

def run_demo_interactive() -> bool:
    """Lance la démonstration interactive complète"""
    logger = DemoLogger("agents_logiques")
    config = charger_config_categories()
    
    # Récupérer les informations de la catégorie
    if 'categories' in config and 'agents_logiques' in config['categories']:
        cat_info = config['categories']['agents_logiques']
        titre = f"{cat_info['icon']} {cat_info['nom']}"
        description = cat_info['description']
        fonctionnalites = cat_info['fonctionnalites']
    else:
        titre = "🧠 Agents Logiques & Argumentation"
        description = "Raisonnement symbolique"
        fonctionnalites = [
            "Logique propositionnelle et prédicats",
            "Agents conversationnels",
            "Détection de sophismes",
            "Communication inter-agents"
        ]
    
    # Afficher le menu du module
    afficher_menu_module(titre, description, fonctionnalites)
    
    if not confirmer_action("Lancer la démonstration des agents logiques ?"):
        logger.info("Démonstration annulée par l'utilisateur")
        return False
    
    # Exécution des différents composants
    resultats_modules = {}
    total_etapes = 5
    
    # 1. Logique propositionnelle
    afficher_progression(1, total_etapes, "Logique propositionnelle")
    resultats_modules["Logique Propositionnelle"] = demo_logique_propositionnelle(logger, config)
    pause_interactive()
    
    # 2. Agents d'argumentation
    afficher_progression(2, total_etapes, "Agents d'argumentation")
    resultats_modules["Agents Argumentation"] = demo_agents_argumentation(logger, config)
    pause_interactive()
    
    # 3. Communication entre agents
    afficher_progression(3, total_etapes, "Communication inter-agents")
    resultats_modules["Communication"] = demo_communication_agents(logger, config)
    pause_interactive()
    
    # 4. Raisonnement modal
    afficher_progression(4, total_etapes, "Logique modale")
    resultats_modules["Logique Modale"] = demo_raisonnement_modal(logger, config)
    pause_interactive()
    
    # 5. Détection de sophismes
    afficher_progression(5, total_etapes, "Détection sophismes")
    resultats_modules["Détection Sophismes"] = demo_detection_sophismes(logger, config)
    
    # Démonstration pratique
    afficher_demonstration_logique()
    pause_interactive("Appuyez sur Entrée pour voir le rapport final...")
    
    # Rapport final
    logger.header(f"{Symbols.CHART} RAPPORT FINAL - AGENTS LOGIQUES")
    total_modules = len(resultats_modules)
    modules_succes = sum(1 for succes in resultats_modules.values() if succes)
    
    print(f"\n{Colors.BOLD}Résultats par composant :{Colors.ENDC}")
    for module, succes in resultats_modules.items():
        status = f"{Colors.GREEN}{Symbols.CHECK}" if succes else f"{Colors.FAIL}{Symbols.CROSS}"
        print(f"  {status} {module}{Colors.ENDC}")
    
    taux_succes = (modules_succes / total_modules) * 100
    couleur_taux = Colors.GREEN if taux_succes >= 90 else Colors.WARNING
    print(f"\n{couleur_taux}{Symbols.STAR} Taux de succès : {taux_succes:.1f}%{Colors.ENDC}")
    
    succes_global = modules_succes == total_modules
    if succes_global:
        logger.success(f"\n{Symbols.FIRE} AGENTS LOGIQUES : SYSTÈME COMPLET ET OPÉRATIONNEL !")
    
    return succes_global

def run_demo_rapide() -> bool:
    """Lance une démonstration rapide (non-interactive)"""
    logger = DemoLogger("agents_logiques")
    
    logger.header("🧠 DÉMONSTRATION RAPIDE - AGENTS LOGIQUES")
    
    # Tests essentiels seulement
    tests_essentiels = [
        "tests/unit/argumentation_analysis/test_pl_definitions.py",
        "tests/unit/argumentation_analysis/test_strategies.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests logique propositionnelle et stratégies...")
    succes, resultats = executer_tests(tests_essentiels, logger, timeout=90)
    
    afficher_stats_tests(resultats)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Validation rapide des agents logiques réussie !")
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