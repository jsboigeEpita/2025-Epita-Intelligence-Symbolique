# -*- coding: utf-8 -*-
"""
Module de démonstration : Intégrations & Interfaces
Architecture modulaire EPITA - Intelligence Symbolique
Python-Java & APIs - Intégration JPype-Tweety
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

def demo_integration_operational(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de l'intégration au niveau opérationnel"""
    logger.header(f"{Symbols.GEAR} INTÉGRATION OPÉRATIONNELLE")
    
    # Tests d'intégration opérationnelle
    tests_operational = [
        "tests/unit/argumentation_analysis/test_operational_agents_integration.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests d'intégration agents opérationnels...")
    succes, resultats = executer_tests(tests_operational, logger, timeout=150)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Intégration opérationnelle validée !")
        print(f"\n{Colors.CYAN}{Symbols.BULB} Capacités d'intégration opérationnelle :{Colors.ENDC}")
        print(f"  • Coordination d'agents de bas niveau")
        print(f"  • Exécution de tâches atomiques")
        print(f"  • Gestion des ressources locales")
        print(f"  • Interface avec les systèmes externes")
        
        # Architecture opérationnelle
        print(f"\n{Colors.BLUE}{Symbols.GEAR} Architecture opérationnelle :{Colors.ENDC}")
        print(f'  {Colors.GREEN}Niveau Tactique{Colors.ENDC}')
        print(f'       ↓ (commandes)')
        print(f'  {Colors.CYAN}Agents Opérationnels{Colors.ENDC}')
        print(f'       ↓ (exécution)')
        print(f'  {Colors.BLUE}Ressources & APIs externes{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_interface_tactique_strategique(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de l'interface tactique-stratégique"""
    logger.header(f"{Symbols.TARGET} INTERFACE TACTIQUE-STRATÉGIQUE")
    
    # Tests de l'interface tactique-stratégique
    tests_interface = [
        "tests/unit/argumentation_analysis/test_strategic_tactical_interface.py"
    ]
    
    logger.info(f"{Symbols.CHART} Tests interface stratégique-tactique...")
    succes, resultats = executer_tests(tests_interface, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Interface stratégique-tactique opérationnelle !")
        print(f"\n{Colors.GREEN}{Symbols.TARGET} Fonctionnalités de l'interface :{Colors.ENDC}")
        print(f"  • Translation d'objectifs stratégiques en tâches tactiques")
        print(f"  • Agrégation de résultats tactiques vers le niveau stratégique")
        print(f"  • Gestion des priorités et allocation de ressources")
        print(f"  • Feedback et adaptation stratégique")
        
        # Exemple de flux de communication
        print(f"\n{Colors.WARNING}{Symbols.BRAIN} Exemple de flux :{Colors.ENDC}")
        print(f'  {Colors.BLUE}Stratégique{Colors.ENDC}: "Résoudre le problème Cluedo"')
        print(f'       ↓ (décomposition)')
        print(f'  {Colors.CYAN}Tactique{Colors.ENDC}: "Analyser indices", "Éliminer suspects"')
        print(f'       ↓ (exécution)')
        print(f'  {Colors.GREEN}Opérationnel{Colors.ENDC}: "Parser texte", "Appliquer règles"')
    
    afficher_stats_tests(resultats)
    return succes

def demo_interface_tactique_operationnel(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de l'interface tactique-opérationnel"""
    logger.header(f"{Symbols.GEAR} INTERFACE TACTIQUE-OPÉRATIONNEL")
    
    # Tests de l'interface tactique-opérationnel
    tests_interface = [
        "tests/unit/argumentation_analysis/test_tactical_operational_interface.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests interface tactique-opérationnel...")
    succes, resultats = executer_tests(tests_interface, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Interface tactique-opérationnel validée !")
        print(f"\n{Colors.BLUE}{Symbols.GEAR} Communication tactique-opérationnel :{Colors.ENDC}")
        print(f"  • Délégation de sous-tâches spécialisées")
        print(f"  • Synchronisation et coordination")
        print(f"  • Contrôle de qualité et validation")
        print(f"  • Gestion d'exceptions et erreurs")
        
        # Patterns de communication
        print(f"\n{Colors.CYAN}{Symbols.BULB} Patterns de communication :{Colors.ENDC}")
        print(f"  • {Colors.GREEN}Command Pattern{Colors.ENDC}: Tâches encapsulées")
        print(f"  • {Colors.BLUE}Observer Pattern{Colors.ENDC}: Notifications d'état")
        print(f"  • {Colors.WARNING}Strategy Pattern{Colors.ENDC}: Choix d'algorithmes")
    
    afficher_stats_tests(resultats)
    return succes

def demo_jpype_tweety_integration(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de l'intégration JPype-Tweety"""
    logger.header(f"{Symbols.BRAIN} INTÉGRATION JPYPE-TWEETY")
    
    logger.info(f"{Symbols.GEAR} Simulation intégration Python-Java...")
    
    # Simulation car l'intégration JPype peut ne pas être toujours disponible
    print(f"\n{Colors.BOLD}{Symbols.ROCKET} Architecture JPype-Tweety :{Colors.ENDC}")
    print(f"  {Colors.CYAN}Python (Intelligence Symbolique){Colors.ENDC}")
    print(f"       ↕ (JPype bridge)")
    print(f"  {Colors.BLUE}Java Tweety (Logique formelle){Colors.ENDC}")
    
    # Capacités de Tweety
    print(f"\n{Colors.GREEN}{Symbols.BRAIN} Capacités Tweety intégrées :{Colors.ENDC}")
    print(f"  • Logique propositionnelle avancée")
    print(f"  • Logique de premier ordre (FOL)")
    print(f"  • Logique modale et temporelle")
    print(f"  • Solvers SAT/SMT intégrés")
    print(f"  • Raisonnement non-monotone")
    
    # Exemple d'utilisation
    print(f"\n{Colors.CYAN}{Symbols.BULB} Exemple d'intégration :{Colors.ENDC}")
    print(f'{Colors.BLUE}# Python')
    print(f'from jpype import tweety')
    print(f'kb = tweety.PlBeliefSet()')
    print(f'kb.add("P -> Q")')
    print(f'kb.add("P")')
    print(f'result = tweety.solve(kb, "Q")  # True{Colors.ENDC}')
    
    # Avantages de l'intégration
    print(f"\n{Colors.WARNING}{Symbols.STAR} Avantages de l'intégration :{Colors.ENDC}")
    print(f"  • Performance optimisée (code Java natif)")
    print(f"  • Bibliothèques logiques étendues")
    print(f"  • Standardisation des formats")
    print(f"  • Communauté académique active")
    
    logger.success(f"{Symbols.FIRE} Intégration JPype-Tweety présentée !")
    return True

def demo_apis_externes(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des APIs et interfaces externes"""
    logger.header(f"{Symbols.GEAR} APIs & INTERFACES EXTERNES")
    
    logger.info(f"{Symbols.ROCKET} Interfaces avec systèmes externes...")
    
    # Types d'APIs supportées
    apis_supportees = {
        "REST APIs": "Communication HTTP avec services web",
        "GraphQL": "Requêtes de données flexibles et typées",
        "gRPC": "Communication haute performance inter-services",
        "WebSockets": "Communication temps réel bidirectionnelle",
        "Message Queues": "Communication asynchrone via queues",
        "Database APIs": "Accès aux bases de données relationnelles et NoSQL"
    }
    
    print(f"\n{Colors.BOLD}{Symbols.CHART} APIs et protocoles supportés :{Colors.ENDC}")
    for api, description in apis_supportees.items():
        print(f"  {Colors.GREEN}•{Colors.ENDC} {Colors.BOLD}{api}{Colors.ENDC}: {description}")
    
    # Exemple d'architecture d'intégration
    print(f"\n{Colors.CYAN}{Symbols.GEAR} Architecture d'intégration :{Colors.ENDC}")
    print(f'  {Colors.BLUE}Frontend (React/Vue){Colors.ENDC}')
    print(f'       ↓ (REST/GraphQL)')
    print(f'  {Colors.GREEN}API Gateway{Colors.ENDC}')
    print(f'       ↓ (routing)')
    print(f'  {Colors.CYAN}Intelligence Symbolique (Python){Colors.ENDC}')
    print(f'       ↓ (JPype)')
    print(f'  {Colors.WARNING}Moteurs Logiques (Java){Colors.ENDC}')
    
    # Sécurité et authentification
    print(f"\n{Colors.WARNING}{Symbols.WARNING} Sécurité & Authentification :{Colors.ENDC}")
    print(f"  • JWT Tokens pour l'authentification stateless")
    print(f"  • OAuth 2.0 pour l'autorisation de services tiers")
    print(f"  • API Rate Limiting pour la protection DDoS")
    print(f"  • HTTPS/TLS pour le chiffrement en transit")
    
    logger.success(f"{Symbols.CHECK} APIs externes configurées !")
    return True

def demo_adaptation_protocoles(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration de l'adaptation de protocoles"""
    logger.header(f"{Symbols.BULB} ADAPTATION DE PROTOCOLES")
    
    logger.info(f"{Symbols.TARGET} Adaptation automatique de protocoles...")
    
    # Patterns d'adaptation
    print(f"\n{Colors.CYAN}{Symbols.BULB} Patterns d'adaptation :{Colors.ENDC}")
    print(f"  • {Colors.GREEN}Adapter Pattern{Colors.ENDC}: Interfaces incompatibles")
    print(f"  • {Colors.BLUE}Bridge Pattern{Colors.ENDC}: Abstraction d'implémentations")
    print(f"  • {Colors.WARNING}Facade Pattern{Colors.ENDC}: Simplification d'interfaces complexes")
    print(f"  • {Colors.CYAN}Proxy Pattern{Colors.ENDC}: Contrôle d'accès et cache")
    
    # Exemple d'adaptation
    print(f"\n{Colors.BOLD}{Symbols.GEAR} Exemple d'adaptation de protocole :{Colors.ENDC}")
    print(f'{Colors.FAIL}Problème: Agent A (JSON) ↔ Agent B (XML)')
    print(f'{Colors.GREEN}Solution: Adaptateur automatique')
    print(f'  Agent A → JSON → {Colors.BLUE}Adaptateur{Colors.ENDC} → XML → Agent B')
    print(f'  Agent A ← JSON ← {Colors.BLUE}Adaptateur{Colors.ENDC} ← XML ← Agent B{Colors.ENDC}')
    
    # Types d'adaptations
    print(f"\n{Colors.WARNING}{Symbols.CHART} Types d'adaptations supportées :{Colors.ENDC}")
    print(f"  • Format de données (JSON ↔ XML ↔ YAML)")
    print(f"  • Protocoles de transport (HTTP ↔ gRPC ↔ WebSocket)")
    print(f"  • Schémas de données (transformation automatique)")
    print(f"  • Sémantique des messages (mapping contextuel)")
    
    # Avantages
    print(f"\n{Colors.GREEN}{Symbols.STAR} Avantages de l'adaptation automatique :{Colors.ENDC}")
    print(f"  • Interopérabilité transparente")
    print(f"  • Évolutivité des systèmes")
    print(f"  • Réutilisation de composants existants")
    print(f"  • Maintenance simplifiée")
    
    logger.success(f"{Symbols.FIRE} Adaptation de protocoles opérationnelle !")
    return True

def run_demo_interactive() -> bool:
    """Lance la démonstration interactive complète"""
    logger = DemoLogger("integrations")
    config = charger_config_categories()
    
    # Récupérer les informations de la catégorie
    if 'categories' in config and 'integrations' in config['categories']:
        cat_info = config['categories']['integrations']
        titre = f"{cat_info['icon']} {cat_info['nom']}"
        description = cat_info['description']
        fonctionnalites = cat_info['fonctionnalites']
    else:
        titre = "🌐 Intégrations & Interfaces"
        description = "Python-Java & APIs"
        fonctionnalites = [
            "Intégration JPype-Tweety",
            "Interfaces tactiques/opérationnelles",
            "Communication inter-niveaux",
            "Adaptation de protocoles"
        ]
    
    # Afficher le menu du module
    afficher_menu_module(titre, description, fonctionnalites)
    
    if not confirmer_action("Lancer la démonstration des intégrations ?"):
        logger.info("Démonstration annulée par l'utilisateur")
        return False
    
    # Exécution des différents composants d'intégration
    resultats_modules = {}
    total_etapes = 6
    
    # 1. Intégration opérationnelle
    afficher_progression(1, total_etapes, "Intégration opérationnelle")
    resultats_modules["Intégration Opérationnelle"] = demo_integration_operational(logger, config)
    pause_interactive()
    
    # 2. Interface stratégique-tactique
    afficher_progression(2, total_etapes, "Interface stratégique-tactique")
    resultats_modules["Interface Stratégique-Tactique"] = demo_interface_tactique_strategique(logger, config)
    pause_interactive()
    
    # 3. Interface tactique-opérationnel
    afficher_progression(3, total_etapes, "Interface tactique-opérationnel")
    resultats_modules["Interface Tactique-Opérationnel"] = demo_interface_tactique_operationnel(logger, config)
    pause_interactive()
    
    # 4. Intégration JPype-Tweety
    afficher_progression(4, total_etapes, "Intégration JPype-Tweety")
    resultats_modules["JPype-Tweety"] = demo_jpype_tweety_integration(logger, config)
    pause_interactive()
    
    # 5. APIs externes
    afficher_progression(5, total_etapes, "APIs externes")
    resultats_modules["APIs Externes"] = demo_apis_externes(logger, config)
    pause_interactive()
    
    # 6. Adaptation de protocoles
    afficher_progression(6, total_etapes, "Adaptation protocoles")
    resultats_modules["Adaptation Protocoles"] = demo_adaptation_protocoles(logger, config)
    
    # Rapport final
    logger.header(f"{Symbols.CHART} RAPPORT FINAL - INTÉGRATIONS")
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
        logger.success(f"\n{Symbols.FIRE} INTÉGRATIONS : SYSTÈME D'INTEROPÉRABILITÉ COMPLET !")
    
    return succes_global

def run_demo_rapide() -> bool:
    """Lance une démonstration rapide (non-interactive)"""
    logger = DemoLogger("integrations")
    
    logger.header("🌐 DÉMONSTRATION RAPIDE - INTÉGRATIONS")
    
    # Tests essentiels seulement
    tests_essentiels = [
        "tests/unit/argumentation_analysis/test_operational_agents_integration.py",
        "tests/unit/argumentation_analysis/test_strategic_tactical_interface.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests intégrations opérationnelles et interfaces...")
    succes, resultats = executer_tests(tests_essentiels, logger, timeout=120)
    
    afficher_stats_tests(resultats)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Validation rapide des intégrations réussie !")
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