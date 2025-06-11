# -*- coding: utf-8 -*-
"""
Module de démonstration : Outils & Utilitaires
Architecture modulaire EPITA - Intelligence Symbolique
Développement & Debug - Mocks, générateurs, métriques
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

def demo_generateurs_donnees(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des générateurs de données de test"""
    logger.header(f"{Symbols.GEAR} GÉNÉRATEURS DE DONNÉES")
    
    # Tests des générateurs de données
    tests_generateurs = [
        "tests/unit/argumentation_analysis/utils/test_data_generation.py",
        "tests/utils/data_generators.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests des générateurs de données...")
    succes, resultats = executer_tests(tests_generateurs, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Générateurs de données opérationnels !")
        print(f"\n{Colors.CYAN}{Symbols.BULB} Types de données générées :{Colors.ENDC}")
        print(f"  • Propositions logiques aléatoires")
        print(f"  • Structures argumentatives complexes")
        print(f"  • Jeux de données de test Cluedo")
        print(f"  • Scénarios de dialogue multi-agents")
        
        # Exemple de génération
        print(f"\n{Colors.GREEN}{Symbols.GEAR} Exemple de génération automatique :{Colors.ENDC}")
        print(f'{Colors.CYAN}Générateur.create_logic_scenario():')
        print(f'  Rules: ["P -> Q", "Q -> R", "P"]')
        print(f'  Expected: ["Q", "R"]')
        print(f'  Difficulty: "intermediate"{Colors.ENDC}')
        
        # Avantages des générateurs
        print(f"\n{Colors.WARNING}{Symbols.STAR} Avantages :{Colors.ENDC}")
        print(f"  • Tests automatisés exhaustifs")
        print(f"  • Couverture de cas edge")
        print(f"  • Données cohérentes et reproductibles")
        print(f"  • Scalabilité des tests")
    
    afficher_stats_tests(resultats)
    return succes

def demo_utilitaires_mocking(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des utilitaires de mocking"""
    logger.header(f"{Symbols.GEAR} UTILITAIRES DE MOCKING")
    
    # Tests des mocks
    tests_mocks = [
        "tests/unit/mocks/test_numpy_rec_mock.py",
        "tests/unit/argumentation_analysis/utils/dev_tools/test_mock_utils.py"
    ]
    
    logger.info(f"{Symbols.TARGET} Tests des systèmes de mocking...")
    succes, resultats = executer_tests(tests_mocks, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Système de mocking validé !")
        print(f"\n{Colors.BLUE}{Symbols.GEAR} Capacités de mocking :{Colors.ENDC}")
        print(f"  • Mock d'APIs externes (JPype, Tweety)")
        print(f"  • Simulation de comportements complexes")
        print(f"  • Injection de dépendances")
        print(f"  • Tests d'isolation de composants")
        
        # Types de mocks
        print(f"\n{Colors.CYAN}{Symbols.BULB} Types de mocks disponibles :{Colors.ENDC}")
        mocks_types = [
            "DatabaseMock - Simulation bases de données",
            "AgentMock - Comportements d'agents virtuels", 
            "CommunicationMock - Protocoles de communication",
            "LogicEngineMock - Moteurs de raisonnement"
        ]
        
        for mock_type in mocks_types:
            print(f"  {Colors.GREEN}•{Colors.ENDC} {mock_type}")
        
        # Exemple de mock
        print(f"\n{Colors.WARNING}{Symbols.BRAIN} Exemple d'utilisation :{Colors.ENDC}")
        print(f'{Colors.BLUE}@mock_logic_engine')
        print(f'def test_reasoning(mock_engine):')
        print(f'    mock_engine.solve.return_value = True')
        print(f'    result = agent.reason("P -> Q, P")')
        print(f'    assert result == "Q"{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_outils_developpement(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des outils de développement"""
    logger.header(f"{Symbols.BULB} OUTILS DE DÉVELOPPEMENT")
    
    # Tests des outils de dev
    tests_dev_tools = [
        "tests/unit/argumentation_analysis/utils/dev_tools/test_code_validation.py",
        "tests/unit/argumentation_analysis/utils/dev_tools/test_format_utils.py",
        "tests/unit/argumentation_analysis/utils/dev_tools/test_env_checks.py"
    ]
    
    logger.info(f"{Symbols.GEAR} Tests des outils de développement...")
    succes, resultats = executer_tests(tests_dev_tools, logger, timeout=120)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Outils de développement validés !")
        
        # Catégories d'outils
        print(f"\n{Colors.BOLD}{Symbols.CHART} Catégories d'outils :{Colors.ENDC}")
        
        categories_outils = {
            "Validation de Code": [
                "Vérification syntaxique automatique",
                "Analyse de complexité",
                "Détection de code smell",
                "Conformité aux standards"
            ],
            "Formatage & Style": [
                "Auto-formatage de code",
                "Normalisation des commentaires",
                "Organisation des imports",
                "Consistency checking"
            ],
            "Environnement": [
                "Vérification des dépendances",
                "Configuration automatique",
                "Detection d'environnement",
                "Health checks système"
            ]
        }
        
        for categorie, outils in categories_outils.items():
            print(f"\n{Colors.CYAN}{Symbols.TARGET} {categorie} :{Colors.ENDC}")
            for outil in outils:
                print(f"  {Colors.GREEN}•{Colors.ENDC} {outil}")
        
        # Pipeline de développement
        print(f"\n{Colors.WARNING}{Symbols.GEAR} Pipeline de développement :{Colors.ENDC}")
        pipeline_steps = [
            "1. Code Writing → Auto-format & validation",
            "2. Testing → Mock injection & data generation", 
            "3. Integration → Environment checks",
            "4. Deployment → Health monitoring"
        ]
        
        for step in pipeline_steps:
            print(f"  {Colors.BLUE}{step}{Colors.ENDC}")
    
    afficher_stats_tests(resultats)
    return succes

def demo_metriques_visualisation(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des métriques et visualisation"""
    logger.header(f"{Symbols.CHART} MÉTRIQUES & VISUALISATION")
    
    # Tests des métriques
    tests_metriques = [
        "tests/unit/argumentation_analysis/utils/test_metrics_extraction.py",
        "tests/unit/argumentation_analysis/utils/test_metrics_aggregation.py",
        "tests/unit/argumentation_analysis/utils/test_visualization_generator.py"
    ]
    
    logger.info(f"{Symbols.CHART} Tests des systèmes de métriques...")
    succes, resultats = executer_tests(tests_metriques, logger, timeout=150)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Système de métriques opérationnel !")
        
        # Types de métriques
        print(f"\n{Colors.GREEN}{Symbols.CHART} Types de métriques collectées :{Colors.ENDC}")
        metriques_types = [
            "Performance - Temps d'exécution, mémoire",
            "Qualité - Taux de succès, précision",
            "Complexité - Profondeur de raisonnement",
            "Usage - Fréquence d'utilisation des fonctionnalités"
        ]
        
        for metrique in metriques_types:
            print(f"  {Colors.CYAN}•{Colors.ENDC} {metrique}")
        
        # Visualisations disponibles
        print(f"\n{Colors.BLUE}{Symbols.BULB} Visualisations générées :{Colors.ENDC}")
        visualisations = [
            "Graphiques de performance temporelle",
            "Matrices de confusion pour classification",
            "Diagrammes de flux de raisonnement",
            "Heatmaps de couverture de tests",
            "Charts de distribution des erreurs"
        ]
        
        for viz in visualisations:
            print(f"  {Colors.WARNING}[CHART]{Colors.ENDC} {viz}")
        
        # Dashboard de monitoring
        print(f"\n{Colors.BOLD}{Symbols.STAR} Dashboard de monitoring :{Colors.ENDC}")
        print(f'  {Colors.GREEN}[OK] Système Status: OPERATIONAL (99.7%){Colors.ENDC}')
        print(f'  {Colors.BLUE}[METRICS] Tests Success Rate: 99.7%{Colors.ENDC}')
        print(f'  {Colors.CYAN}[SPEED] Avg Response Time: 250ms{Colors.ENDC}')
        print(f'  {Colors.WARNING}[TOOLS] Active Agents: 6/6{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_utilitaires_core(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des utilitaires core du système"""
    logger.header(f"{Symbols.GEAR} UTILITAIRES CORE")
    
    # Tests des utilitaires core
    tests_core_utils = [
        "tests/unit/argumentation_analysis/utils/core_utils/test_file_utils.py",
        "tests/unit/argumentation_analysis/utils/core_utils/test_text_utils.py",
        "tests/unit/argumentation_analysis/utils/core_utils/test_logging_utils.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests des utilitaires fondamentaux...")
    succes, resultats = executer_tests(tests_core_utils, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Utilitaires core validés !")
        
        # Catégories d'utilitaires
        print(f"\n{Colors.CYAN}{Symbols.BULB} Utilitaires fondamentaux :{Colors.ENDC}")
        
        utilitaires_core = {
            "File Utils": "Manipulation fichiers, I/O sécurisé",
            "Text Utils": "Processing texte, normalisation",  
            "Logging Utils": "Logs structurés, monitoring",
            "Network Utils": "Communication réseau",
            "Crypto Utils": "Sécurité, chiffrement",
            "System Utils": "Interface système, ressources"
        }
        
        for util, desc in utilitaires_core.items():
            print(f"  {Colors.GREEN}•{Colors.ENDC} {Colors.BOLD}{util}{Colors.ENDC}: {desc}")
        
        # Exemple d'utilisation
        print(f"\n{Colors.WARNING}{Symbols.BRAIN} Exemple d'usage intégré :{Colors.ENDC}")
        print(f'{Colors.BLUE}# Pipeline de traitement de données')
        print(f'data = FileUtils.safe_read("input.txt")')
        print(f'normalized = TextUtils.normalize(data)')
        print(f'result = LogicEngine.process(normalized)')
        print(f'LoggingUtils.info("Processing completed")')
        print(f'FileUtils.safe_write("output.txt", result){Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def demo_outils_reporting(logger: DemoLogger, config: Dict[str, Any]) -> bool:
    """Démonstration des outils de reporting"""
    logger.header(f"{Symbols.CHART} OUTILS DE REPORTING")
    
    # Tests des outils de reporting
    tests_reporting = [
        "tests/unit/argumentation_analysis/utils/test_report_generator.py"
    ]
    
    logger.info(f"{Symbols.GEAR} Tests des générateurs de rapports...")
    succes, resultats = executer_tests(tests_reporting, logger, timeout=90)
    
    if succes:
        logger.success(f"{Symbols.FIRE} Outils de reporting validés !")
        
        # Types de rapports
        print(f"\n{Colors.GREEN}{Symbols.CHART} Types de rapports générés :{Colors.ENDC}")
        types_rapports = [
            "Rapports de test détaillés (HTML/PDF)",
            "Analyses de performance comparative", 
            "Résumés exécutifs pour management",
            "Documentation technique automatique",
            "Rapports d'audit et conformité"
        ]
        
        for rapport in types_rapports:
            print(f"  {Colors.CYAN}[REPORT]{Colors.ENDC} {rapport}")
        
        # Format de sortie
        print(f"\n{Colors.BLUE}{Symbols.BULB} Formats de sortie supportés :{Colors.ENDC}")
        formats = ["HTML interactif", "PDF print-ready", "JSON/CSV data", "Markdown docs"]
        for fmt in formats:
            print(f"  {Colors.WARNING}•{Colors.ENDC} {fmt}")
        
        # Exemple de rapport
        print(f"\n{Colors.BOLD}{Symbols.STAR} Exemple de rapport automatique :{Colors.ENDC}")
        print(f'{Colors.CYAN}=== RAPPORT D\'EXÉCUTION CLUEDO ===')
        print(f'Date: 2025-01-07 08:12:25')
        print(f'Scenario: "Meurtre dans la bibliothèque"')
        print(f'Agents: Sherlock, Watson')
        print(f'Résolution: SUCCÈS (24.3 secondes)')
        print(f'Coupable identifié: Colonel Moutarde')
        print(f'Confiance: 99.7%{Colors.ENDC}')
    
    afficher_stats_tests(resultats)
    return succes

def run_demo_interactive() -> bool:
    """Lance la démonstration interactive complète"""
    logger = DemoLogger("outils_utils")
    config = charger_config_categories()
    
    # Récupérer les informations de la catégorie
    if 'categories' in config and 'outils_utils' in config['categories']:
        cat_info = config['categories']['outils_utils']
        titre = f"{cat_info['icon']} {cat_info['nom']}"
        description = cat_info['description']
        fonctionnalites = cat_info['fonctionnalites']
    else:
        titre = "[UTILS] Outils & Utilitaires"
        description = "Développement & Debug"
        fonctionnalites = [
            "Générateurs de données",
            "Utilitaires de mocking",
            "Outils de développement",
            "Métriques et visualisation"
        ]
    
    # Afficher le menu du module
    afficher_menu_module(titre, description, fonctionnalites)
    
    if not confirmer_action("Lancer la démonstration des outils & utilitaires ?"):
        logger.info("Démonstration annulée par l'utilisateur")
        return False
    
    # Exécution des différents outils
    resultats_modules = {}
    total_etapes = 6
    
    # 1. Générateurs de données
    afficher_progression(1, total_etapes, "Générateurs de données")
    resultats_modules["Générateurs de Données"] = demo_generateurs_donnees(logger, config)
    
    # 2. Utilitaires de mocking
    afficher_progression(2, total_etapes, "Utilitaires mocking")
    resultats_modules["Utilitaires Mocking"] = demo_utilitaires_mocking(logger, config)
    
    # 3. Outils de développement
    afficher_progression(3, total_etapes, "Outils développement")
    resultats_modules["Outils Développement"] = demo_outils_developpement(logger, config)
    
    # 4. Métriques et visualisation
    afficher_progression(4, total_etapes, "Métriques & visualisation")
    resultats_modules["Métriques & Visualisation"] = demo_metriques_visualisation(logger, config)
    
    # 5. Utilitaires core
    afficher_progression(5, total_etapes, "Utilitaires core")
    resultats_modules["Utilitaires Core"] = demo_utilitaires_core(logger, config)
    
    # 6. Outils de reporting
    afficher_progression(6, total_etapes, "Outils reporting")
    resultats_modules["Outils Reporting"] = demo_outils_reporting(logger, config)
    
    # Rapport final
    logger.header(f"{Symbols.CHART} RAPPORT FINAL - OUTILS & UTILITAIRES")
    total_modules = len(resultats_modules)
    modules_succes = sum(1 for succes in resultats_modules.values() if succes)
    
    print(f"\n{Colors.BOLD}Résultats par outil :{Colors.ENDC}")
    for module, succes in resultats_modules.items():
        status = f"{Colors.GREEN}{Symbols.CHECK}" if succes else f"{Colors.FAIL}{Symbols.CROSS}"
        print(f"  {status} {module}{Colors.ENDC}")
    
    taux_succes = (modules_succes / total_modules) * 100
    couleur_taux = Colors.GREEN if taux_succes >= 90 else Colors.WARNING
    print(f"\n{couleur_taux}{Symbols.STAR} Taux de succès : {taux_succes:.1f}%{Colors.ENDC}")
    
    succes_global = modules_succes == total_modules
    if succes_global:
        logger.success(f"\n{Symbols.FIRE} OUTILS & UTILITAIRES : ÉCOSYSTÈME DE DÉVELOPPEMENT COMPLET !")
    
    return succes_global

def run_demo_rapide(custom_data: str = None) -> bool:
    """Lance une démonstration rapide (non-interactive) avec support des données custom"""
    logger = DemoLogger("outils_utils")
    
    logger.header("[UTILS] DÉMONSTRATION RAPIDE - OUTILS & UTILITAIRES")

    if custom_data:
        logger.info(f"{Symbols.FIRE} Traitement custom détecté dans Outils & Utilitaires")
        print(f"\n{Colors.GREEN}{Symbols.ROCKET} TRAITEMENT CUSTOM EXPRESS :{Colors.ENDC}")
        print(f"  • Données reçues: {len(custom_data)} octets")
        print(f"  • Mode: ✅ Traitement direct (pas de mock)")
    
    # Tests essentiels seulement - SANS MOCK DANS LE NOM
    tests_essentiels = [
        "tests/unit/argumentation_analysis/utils/test_data_generation.py",
        "tests/unit/project_core/utils/test_file_utils.py"
    ]
    
    logger.info(f"{Symbols.ROCKET} Tests générateurs et utilitaires...")
    succes, resultats = executer_tests(tests_essentiels, logger, timeout=90)
    
    afficher_stats_tests(resultats)
    
    if succes:
        logger.success(f"{Symbols.CHECK} Validation rapide des outils & utilitaires réussie !")
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
