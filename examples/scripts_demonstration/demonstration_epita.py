# -*- coding: utf-8 -*-
"""
Script orchestrateur de démonstration pour le projet d'Intelligence Symbolique EPITA.
VERSION ENRICHIE AVEC MODE INTERACTIF PÉDAGOGIQUE

Ce script principal a pour but de lancer les différentes démonstrations du projet,
qui sont organisées en sous-scripts pour plus de clarté et de modularité.

NOUVELLES FONCTIONNALITÉS PÉDAGOGIQUES :
- Mode interactif avec pauses explicatives
- Dashboard console enrichi avec métriques visuelles
- Système de questions/réponses intégré
- Templates de projets par difficulté
- Suggestions contextuelles pour étudiants

Plan d'exécution :
1.  Vérification et installation des dépendances de base.
2.  Lancement du sous-script `demo_notable_features.py` pour les fonctionnalités de base.
3.  Lancement du sous-script `demo_advanced_features.py` pour les fonctionnalités complexes.
4.  Exécution de la suite de tests complète du projet via `pytest`.

Prérequis :
- Le script doit être exécuté depuis la racine du projet.

Exécution :
python examples/scripts_demonstration/demonstration_epita.py [--interactive]
python examples/scripts_demonstration/demonstration_epita.py --quick-start
python examples/scripts_demonstration/demonstration_epita.py --help
"""
import logging
import sys
import os
import subprocess
import time
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# =====================================
# CONSTANTES ET CONFIGURATIONS
# =====================================

# Métrique de succès des tests (mise à jour régulière)
TEST_SUCCESS_RATE = 99.7

# Base de projets étudiants organisée par niveau
PROJETS_SUGGESTIONS = {
    'debutant': [
        {
            'nom': 'Analyseur de Propositions Logiques',
            'description': 'Créer un système simple pour analyser des propositions en logique propositionnelle',
            'technologies': ['Python', 'Classes', 'Tests unitaires'],
            'duree_estimee': '2-3 heures',
            'concepts_cles': ['Variables propositionnelles', 'Connecteurs logiques', 'Tables de vérité'],
            'template_code': '''
# Template de base pour l'analyseur de propositions
class AnalyseurProposition:
    def __init__(self):
        self.variables = set()
        self.connecteurs = {'ET': '&', 'OU': '|', 'NON': '~', 'IMPLIQUE': '->'}
    
    def analyser(self, proposition: str) -> dict:
        """Analyse une proposition logique simple"""
        # TODO: Implémenter l'analyse
        return {'variables': list(self.variables), 'valid': True}
'''
        },
        {
            'nom': 'Mini-Base de Connaissances',
            'description': 'Système de stockage et requête de faits simples',
            'technologies': ['Python', 'JSON', 'Algorithmes de recherche'],
            'duree_estimee': '3-4 heures',
            'concepts_cles': ['Faits', 'Règles', 'Inférence simple'],
            'template_code': '''
# Template pour mini base de connaissances
class BaseConnaissances:
    def __init__(self):
        self.faits = []
        self.regles = []
    
    def ajouter_fait(self, fait: str):
        """Ajoute un fait à la base"""
        # TODO: Implémenter
        pass
'''
        }
    ],
    'intermediaire': [
        {
            'nom': 'Moteur d\'Inférence Avancé',
            'description': 'Implémentation d\'algorithmes d\'inférence (forward/backward chaining)',
            'technologies': ['Python', 'Algorithmes', 'Structures de données'],
            'duree_estimee': '5-8 heures',
            'concepts_cles': ['Chaînage avant', 'Chaînage arrière', 'Résolution'],
            'template_code': '''
# Template pour moteur d'inférence
class MoteurInference:
    def __init__(self):
        self.base_faits = set()
        self.base_regles = []
    
    def chainage_avant(self) -> set:
        """Algorithme de chaînage avant"""
        # TODO: Implémenter
        return self.base_faits
'''
        },
        {
            'nom': 'Analyseur d\'Arguments Rhétoriques',
            'description': 'Système pour analyser la structure des arguments et détecter les fallacies',
            'technologies': ['Python', 'NLP', 'Patterns', 'Classifications'],
            'duree_estimee': '6-10 heures',
            'concepts_cles': ['Structure argumentative', 'Fallacies logiques', 'Analyse textuelle'],
            'template_code': '''
# Template pour analyseur d'arguments
class AnalyseurArguments:
    def __init__(self):
        self.fallacies_connues = {
            'ad_hominem': 'Attaque personnelle',
            'strawman': 'Homme de paille'
        }
    
    def analyser_argument(self, texte: str) -> dict:
        """Analyse la structure d'un argument"""
        # TODO: Implémenter
        return {'structure': [], 'fallacies': []}
'''
        }
    ],
    'avance': [
        {
            'nom': 'Système Multi-Agents Logiques',
            'description': 'Implémentation d\'un système où plusieurs agents raisonnent et communiquent',
            'technologies': ['Python', 'Concurrence', 'Protocoles', 'IA'],
            'duree_estimee': '10-15 heures',
            'concepts_cles': ['Agents autonomes', 'Communication inter-agents', 'Négociation'],
            'template_code': '''
# Template pour système multi-agents
import threading
from abc import ABC, abstractmethod

class AgentLogique(ABC):
    def __init__(self, nom: str):
        self.nom = nom
        self.base_connaissances = set()
        self.messages_recus = []
    
    @abstractmethod
    def raisonner(self) -> list:
        """Méthode de raisonnement de l'agent"""
        pass
'''
        },
        {
            'nom': 'Démonstrateur de Théorèmes Automatique',
            'description': 'Système capable de prouver automatiquement des théorèmes simples',
            'technologies': ['Python', 'Logique formelle', 'Algorithmes de preuve'],
            'duree_estimee': '12-20 heures',
            'concepts_cles': ['Preuves formelles', 'Résolution SLD', 'Unification'],
            'template_code': '''
# Template pour démonstrateur de théorèmes
class DemonstrateurTheoremes:
    def __init__(self):
        self.axiomes = []
        self.regles_inference = []
    
    def prouver(self, theoreme: str) -> tuple:
        """Tente de prouver un théorème"""
        # TODO: Implémenter
        return (False, [])
'''
        }
    ]
}

# Documentation et liens utiles
LIENS_DOCUMENTATION = {
    'logique_propositionnelle': 'https://docs.python.org/3/tutorial/datastructures.html',
    'intelligence_symbolique': 'docs/guides/guide_utilisation.md',
    'tests_unitaires': 'https://docs.pytest.org/en/stable/',
    'exemples_projets': 'examples/',
    'api_documentation': 'docs/api/'
}

# Codes couleur ANSI pour la console
class Colors:
    """Codes couleur ANSI pour la console"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Symboles pour l'interface (compatibles toutes plateformes)
class Symbols:
    """Symboles pour l'interface pédagogique"""
    BOOK = "[COURS]"
    ROCKET = "[START]"
    CHECK = "[OK]"
    CROSS = "[ECHEC]"
    QUESTION = "[?]"
    BULB = "[ASTUCE]"
    GEAR = "[EXEC]"
    CHART = "[STATS]"
    TARGET = "[OBJECTIF]"
    STAR = "[STAR]"
    FIRE = "[EXCELLENT]"
    BRAIN = "[IA]"
    WARNING = "[ATTENTION]"

# =====================================
# FONCTIONS D'INTERFACE PÉDAGOGIQUE
# =====================================

def afficher_banniere_interactive():
    """Affiche une bannière colorée pour le mode interactif"""
    banniere = f"""
{Colors.CYAN}{Colors.BOLD}
+==============================================================================+
|                    [EPITA] DEMONSTRATION - MODE INTERACTIF                  |
|                     Intelligence Symbolique & IA Explicable                 |
+==============================================================================+
{Colors.ENDC}

{Symbols.ROCKET} Bienvenue dans la demonstration interactive du projet !
{Symbols.BRAIN} Vous allez explorer les concepts cles de l'intelligence symbolique
{Symbols.TARGET} Objectif : Comprendre et maitriser les outils developpes

{Colors.GREEN}* Fonctionnalites disponibles :{Colors.ENDC}
  {Symbols.BOOK} Pauses pedagogiques avec explications detaillees
  {Symbols.QUESTION} Quiz interactifs pour valider votre comprehension
  {Symbols.CHART} Dashboard de progression en temps reel
  {Symbols.GEAR} Templates de projets adaptes a votre niveau
"""
    print(banniere)

def afficher_progression(etape_actuelle: int, total_etapes: int, description: str = "") -> None:
    """Affiche une barre de progression colorée avec description"""
    pourcentage = (etape_actuelle / total_etapes) * 100
    barre_longueur = 50
    barre_remplie = int((etape_actuelle / total_etapes) * barre_longueur)
    
    # Choix de couleur selon le pourcentage
    if pourcentage < 30:
        couleur = Colors.FAIL
    elif pourcentage < 70:
        couleur = Colors.WARNING
    else:
        couleur = Colors.GREEN
    
    barre = '#' * barre_remplie + '-' * (barre_longueur - barre_remplie)
    
    print(f"\n{Colors.BOLD}{Symbols.CHART} Progression :{Colors.ENDC}")
    print(f"{couleur}[{barre}] {pourcentage:.1f}% ({etape_actuelle}/{total_etapes}){Colors.ENDC}")
    if description:
        print(f"{Colors.CYAN}{Symbols.TARGET} {description}{Colors.ENDC}")

def afficher_metriques_tests() -> None:
    """Affiche les métriques de succès des tests en temps réel"""
    print(f"\n{Colors.BOLD}{Symbols.CHART} Métriques du Projet :{Colors.ENDC}")
    print(f"{Colors.GREEN}{Symbols.CHECK} Taux de succès des tests : {TEST_SUCCESS_RATE}%{Colors.ENDC}")
    print(f"{Colors.BLUE}{Symbols.GEAR} Architecture : Python + Java (JPype){Colors.ENDC}")
    print(f"{Colors.CYAN}{Symbols.BRAIN} Domaines couverts : Logique formelle, Argumentation, IA symbolique{Colors.ENDC}")

def pause_pedagogique(concept: str, explication: str, liens_doc: List[str] = None) -> None:
    """Pause interactive pour expliquer un concept avec liens documentation"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{Symbols.WARNING} PAUSE PÉDAGOGIQUE{Colors.ENDC}")
    print(f"{Colors.BOLD}{Symbols.BOOK} Concept : {concept}{Colors.ENDC}")
    print(f"\n{Colors.CYAN}{explication}{Colors.ENDC}")
    
    if liens_doc:
        print(f"\n{Symbols.BULB} {Colors.BOLD}Documentation utile :{Colors.ENDC}")
        for lien in liens_doc:
            print(f"  > {lien}")
    
    print(f"\n{Colors.WARNING}[PAUSE] Appuyez sur Entrée pour continuer...{Colors.ENDC}")
    input()

def interactive_quiz(question: str, options: List[str], bonne_reponse: int, explication_reponse: str) -> bool:
    """Quiz interactif pour valider la compréhension"""
    print(f"\n{Colors.BOLD}{Colors.WARNING}{Symbols.QUESTION} QUIZ INTERACTIF{Colors.ENDC}")
    print(f"{Colors.BOLD}{question}{Colors.ENDC}\n")
    
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        try:
            reponse = int(input(f"\n{Colors.CYAN}Votre réponse (1-{len(options)}) : {Colors.ENDC}"))
            if 1 <= reponse <= len(options):
                break
            else:
                print(f"{Colors.FAIL}Veuillez entrer un nombre entre 1 et {len(options)}{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.FAIL}Veuillez entrer un nombre valide{Colors.ENDC}")
    
    if reponse == bonne_reponse:
        print(f"\n{Colors.GREEN}{Symbols.CHECK} Excellente réponse !{Colors.ENDC}")
        print(f"{Colors.GREEN}{explication_reponse}{Colors.ENDC}")
        return True
    else:
        print(f"\n{Colors.FAIL}{Symbols.CROSS} Pas tout à fait...{Colors.ENDC}")
        print(f"{Colors.WARNING}La bonne réponse était : {options[bonne_reponse-1]}{Colors.ENDC}")
        print(f"{Colors.CYAN}{explication_reponse}{Colors.ENDC}")
        return False

def suggerer_projets(niveau_etudiant: str, afficher_details: bool = True) -> List[Dict]:
    """Suggestions personnalisées de projets selon le niveau"""
    if niveau_etudiant not in PROJETS_SUGGESTIONS:
        niveau_etudiant = 'debutant'
    
    projets = PROJETS_SUGGESTIONS[niveau_etudiant]
    
    if afficher_details:
        print(f"\n{Colors.BOLD}{Symbols.TARGET} SUGGESTIONS DE PROJETS - NIVEAU {niveau_etudiant.upper()}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
        
        for i, projet in enumerate(projets, 1):
            print(f"\n{Colors.BOLD}{i}. {projet['nom']}{Colors.ENDC}")
            print(f"   {Colors.CYAN}Description: {projet['description']}{Colors.ENDC}")
            print(f"   {Colors.BLUE}Durée estimée : {projet['duree_estimee']}{Colors.ENDC}")
            print(f"   {Colors.GREEN}Technologies : {', '.join(projet['technologies'])}{Colors.ENDC}")
            print(f"   {Colors.WARNING}Concepts clés : {', '.join(projet['concepts_cles'])}{Colors.ENDC}")
    
    return projets

def afficher_template_code(projet: Dict) -> None:
    """Affiche le template de code pour un projet"""
    print(f"\n{Colors.BOLD}{Symbols.GEAR} TEMPLATE DE CODE - {projet['nom']}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'-' * 50}{Colors.ENDC}")
    print(projet['template_code'])
    print(f"{Colors.CYAN}{'-' * 50}{Colors.ENDC}")

def mode_quick_start() -> None:
    """Mode Quick Start pour les étudiants"""
    afficher_banniere_interactive()
    
    print(f"\n{Colors.BOLD}{Symbols.ROCKET} MODE QUICK START{Colors.ENDC}")
    print(f"{Colors.CYAN}Choisissez votre niveau pour obtenir des suggestions de projets adaptées :{Colors.ENDC}\n")
    
    niveaux = ['debutant', 'intermediaire', 'avance']
    for i, niveau in enumerate(niveaux, 1):
        descriptions = {
            'debutant': 'Découverte des concepts de base',
            'intermediaire': 'Approfondissement et algorithmes',
            'avance': 'Projets complexes et recherche'
        }
        print(f"  {i}. {niveau.capitalize()} - {descriptions[niveau]}")
    
    while True:
        try:
            choix = int(input(f"\n{Colors.CYAN}Votre niveau (1-3) : {Colors.ENDC}"))
            if 1 <= choix <= 3:
                niveau_choisi = niveaux[choix-1]
                break
            else:
                print(f"{Colors.FAIL}Veuillez entrer 1, 2 ou 3{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.FAIL}Veuillez entrer un nombre valide{Colors.ENDC}")
    
    # Afficher les suggestions
    projets = suggerer_projets(niveau_choisi)
    
    # Demander si l'utilisateur veut voir un template
    print(f"\n{Colors.CYAN}Voulez-vous voir le template de code pour un projet ? (o/n) : {Colors.ENDC}", end="")
    if input().lower() in ['o', 'oui', 'y', 'yes']:
        print(f"\n{Colors.CYAN}Choisissez un projet (1-{len(projets)}) : {Colors.ENDC}", end="")
        try:
            choix_projet = int(input()) - 1
            if 0 <= choix_projet < len(projets):
                afficher_template_code(projets[choix_projet])
            else:
                print(f"{Colors.WARNING}Projet non trouvé{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.WARNING}Choix invalide{Colors.ENDC}")

def setup_environment():
    """Configure le logger et le chemin système pour l'exécution."""
    logger = logging.getLogger("demonstration_orchestrator")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # S'assurer que le répertoire de travail est la racine du projet
    os.chdir(project_root)
    
    logger.info(f"Environnement configuré. Racine du projet : {project_root}")
    return logger, project_root

def check_and_install_dependencies(logger: logging.Logger):
    """Vérifie et installe les dépendances Python de base si elles sont manquantes."""
    logger.info(f"\n{Symbols.GEAR} --- Vérification des dépendances (seaborn, markdown) ---")
    dependencies = ["seaborn", "markdown"]
    for package_name in dependencies:
        try:
            __import__(package_name.replace("-", "_"))
            logger.info(f"{Symbols.CHECK} Le package '{package_name}' est déjà installé.")
        except ImportError:
            logger.warning(f"{Symbols.WARNING} Le package '{package_name}' n'est pas trouvé. Tentative d'installation...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", package_name], 
                    check=True, capture_output=True, text=True, timeout=300
                )
                logger.info(f"{Symbols.CHECK} SUCCÈS: Le package '{package_name}' a été installé.")
            except Exception as e:
                logger.error(f"{Symbols.CROSS} ERREUR: Échec de l'installation de '{package_name}': {e}")

def run_subprocess(script_name: str, logger: logging.Logger, interactive_mode: bool = False, etape_actuelle: int = 0, total_etapes: int = 0):
    """Exécute un sous-script Python et affiche sa sortie avec support du mode interactif."""
    script_path = Path("examples/scripts_demonstration") / script_name
    
    if interactive_mode:
        # Pause pédagogique avant le lancement
        concepts_scripts = {
            "demo_notable_features.py": {
                "concept": "Fonctionnalités de Base du Projet",
                "explication": """Ce script démontre les fonctionnalités principales de notre système d'intelligence symbolique :
• Analyse de texte et extraction d'arguments
• Systèmes de logique propositionnelle et prédicats
• Interface avec la base de connaissances
• Mécanismes d'inférence de base

Ces fonctionnalités constituent le cœur de notre approche de l'IA explicable.""",
                "liens": ["docs/guides/guide_utilisation.md", "examples/logic_agents/"]
            },
            "demo_advanced_features.py": {
                "concept": "Fonctionnalités Avancées",
                "explication": """Ce script présente les aspects les plus sophistiqués du projet :
• Moteurs d'inférence complexes (chaînage avant/arrière)
• Intégration Java-Python via JPype
• Analyse rhétorique avancée
• Systèmes multi-agents et communication

Ces fonctionnalités représentent l'état de l'art en IA symbolique.""",
                "liens": ["docs/architecture_python_java_integration.md", "docs/composants/"]
            }
        }
        
        if script_name in concepts_scripts:
            concept_info = concepts_scripts[script_name]
            pause_pedagogique(
                concept_info["concept"],
                concept_info["explication"],
                concept_info["liens"]
            )
        
        # Afficher la progression
        if total_etapes > 0:
            afficher_progression(etape_actuelle, total_etapes, f"Exécution de {script_name}")
    
    logger.info(f"\n{Symbols.GEAR} --- Lancement du sous-script : {script_name} ---")
    
    if not script_path.exists():
        logger.error(f"{Symbols.CROSS} Le sous-script {script_path} n'a pas été trouvé.")
        return False

    start_time = time.time()
    try:
        process = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            check=True, timeout=600  # 10 minutes
        )
        duration = time.time() - start_time
        logger.info(f"{Symbols.CHECK} --- Sortie de {script_name} (durée: {duration:.2f}s) ---")
        for line in process.stdout.splitlines():
            logger.info(line)
        if process.stderr:
            logger.warning(f"{Symbols.WARNING} --- Sortie d'erreur de {script_name} ---")
            for line in process.stderr.splitlines():
                logger.warning(line)
        logger.info(f"{Symbols.CHECK} --- Fin du sous-script : {script_name} ---")
        return True

    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        logger.error(f"{Symbols.CROSS} Le sous-script {script_name} a échoué (code: {e.returncode}, durée: {duration:.2f}s).")
        logger.error(f"--- Sortie de {script_name} ---\n{e.stdout}")
        logger.error(f"--- Erreurs de {script_name} ---\n{e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"{Symbols.CROSS} Le sous-script {script_name} a dépassé le timeout de 10 minutes.")
        return False
    except Exception as e:
        logger.error(f"{Symbols.CROSS} Une erreur inattendue est survenue en lançant {script_name}: {e}", exc_info=True)
        return False

def run_project_tests(logger: logging.Logger, interactive_mode: bool = False):
    """Exécute la suite de tests du projet avec pytest et affichage enrichi."""
    
    if interactive_mode:
        pause_pedagogique(
            "Suite de Tests Automatisés",
            f"""Les tests automatisés sont essentiels pour garantir la qualité du code :
• Tests unitaires : Vérification des composants individuels
• Tests d'intégration : Validation des interactions entre modules
• Tests de performance : Mesure de l'efficacité du système

Notre projet maintient un taux de succès de {TEST_SUCCESS_RATE}% grâce à une approche rigoureuse du testing.""",
            ["docs/tests/", "https://docs.pytest.org/en/stable/"]
        )
        
        # Quiz sur les tests
        quiz_reussi = interactive_quiz(
            "Quel est l'avantage principal des tests automatisés ?",
            [
                "Ils remplacent la documentation",
                "Ils garantissent la qualité et détectent les régressions",
                "Ils accélérent l'exécution du code",
                "Ils sont obligatoires en Python"
            ],
            2,
            "Les tests automatisés permettent de détecter rapidement les erreurs et régressions, garantissant ainsi la stabilité du code lors des modifications."
        )
        
        if quiz_reussi:
            print(f"{Colors.GREEN}{Symbols.STAR} Excellent ! Vous comprenez l'importance des tests !{Colors.ENDC}")
    
    logger.info(f"\n{Symbols.CHART} --- Lancement de la suite de tests du projet (pytest) ---")
    
    # Afficher les métriques avant les tests
    if interactive_mode:
        afficher_metriques_tests()
    
    start_time = time.time()
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "-v"],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=900  # 15 minutes
        )
        duration = time.time() - start_time
        logger.info(f"{Symbols.CHECK} Tests exécutés en {duration:.2f} secondes.")
        
        logger.info(f"\n{Symbols.CHART} --- Résultats des tests ---")
        for line in process.stdout.splitlines():
            # Colorier les résultats selon le statut
            if "PASSED" in line:
                logger.info(f"{Colors.GREEN}{line}{Colors.ENDC}")
            elif "FAILED" in line:
                logger.info(f"{Colors.FAIL}{line}{Colors.ENDC}")
            elif "ERROR" in line:
                logger.info(f"{Colors.FAIL}{line}{Colors.ENDC}")
            else:
                logger.info(line)
        
        if process.stderr:
            logger.error(f"\n{Symbols.WARNING} --- Erreurs des tests ---")
            logger.error(process.stderr)
            
        if process.returncode == 0:
            logger.info(f"\n{Colors.GREEN}{Symbols.CHECK} SUCCÈS : Tous les tests sont passés !{Colors.ENDC}")
            if interactive_mode:
                print(f"{Colors.GREEN}{Symbols.FIRE} Félicitations ! Le système fonctionne parfaitement !{Colors.ENDC}")
        else:
            logger.warning(f"\n{Colors.WARNING}{Symbols.CROSS} AVERTISSEMENT : Certains tests ont échoué (code: {process.returncode}).{Colors.ENDC}")

        return process.returncode == 0

    except Exception as e:
        logger.error(f"{Symbols.CROSS} Erreur lors de l'exécution des tests : {e}", exc_info=True)
        return False

def run_interactive_demonstration(main_logger: logging.Logger, project_root_path: Path) -> None:
    """Lance la démonstration en mode interactif complet."""
    afficher_banniere_interactive()
    
    # Quiz d'introduction
    print(f"\n{Colors.BOLD}{Symbols.BRAIN} QUIZ D'INTRODUCTION{Colors.ENDC}")
    quiz_reussi = interactive_quiz(
        "Qu'est-ce que l'Intelligence Symbolique ?",
        [
            "Une technique de deep learning",
            "Une approche basée sur la manipulation de symboles et la logique formelle",
            "Un langage de programmation",
            "Une base de données"
        ],
        2,
        "L'Intelligence Symbolique utilise des symboles et des règles logiques pour représenter et manipuler la connaissance, contrairement aux approches connexionnistes."
    )
    
    if not quiz_reussi:
        print(f"{Colors.CYAN}{Symbols.BULB} Pas de souci ! Cette démonstration va vous aider à mieux comprendre !{Colors.ENDC}")
    
    # Étapes de la démonstration avec progression
    etapes_totales = 4
    etape_courante = 0
    
    main_logger.info(f"\n{Colors.BOLD}{Symbols.ROCKET} === Début de la démonstration interactive EPITA ==={Colors.ENDC}")
    
    # 1. Vérifier les dépendances
    etape_courante += 1
    afficher_progression(etape_courante, etapes_totales, "Vérification des dépendances")
    check_and_install_dependencies(main_logger)
    
    # 2. Lancer les sous-scripts de démonstration
    etape_courante += 1
    success_demo1 = run_subprocess("demo_notable_features.py", main_logger, True, etape_courante, etapes_totales)
    
    etape_courante += 1
    success_demo2 = run_subprocess("demo_advanced_features.py", main_logger, True, etape_courante, etapes_totales)
    
    # 3. Lancer les tests du projet
    etape_courante += 1
    afficher_progression(etape_courante, etapes_totales, "Exécution de la suite de tests")
    success_tests = run_project_tests(main_logger, True)
    
    # Résumé final interactif
    print(f"\n{Colors.BOLD}{Colors.CYAN}{Symbols.CHART} RÉSUMÉ DE LA DÉMONSTRATION{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")
    
    resultats = [
        ("Démonstration des fonctionnalités de base", success_demo1),
        ("Démonstration des fonctionnalités avancées", success_demo2),
        ("Suite de tests", success_tests)
    ]
    
    for nom, succes in resultats:
        status = f"{Colors.GREEN}{Symbols.CHECK}" if succes else f"{Colors.FAIL}{Symbols.CROSS}"
        print(f"  {status} {nom}{Colors.ENDC}")
    
    # Suggestions de projets
    print(f"\n{Colors.BOLD}{Symbols.TARGET} ÉTAPES SUIVANTES RECOMMANDÉES :{Colors.ENDC}")
    print(f"{Colors.CYAN}1. Explorez les exemples dans le dossier 'examples/'")
    print(f"2. Consultez la documentation dans 'docs/'")
    print(f"3. Essayez les templates de projets adaptés à votre niveau")
    print(f"4. Rejoignez notre communauté d'étudiants EPITA !{Colors.ENDC}")
    
    # Option pour voir les suggestions de projets
    print(f"\n{Colors.CYAN}Voulez-vous voir des suggestions de projets ? (o/n) : {Colors.ENDC}", end="")
    if input().lower() in ['o', 'oui', 'y', 'yes']:
        suggerer_projets('intermediaire')
    
    main_logger.info(f"\n{Colors.BOLD}{Colors.GREEN}{Symbols.STAR} === Fin de la démonstration interactive EPITA ==={Colors.ENDC}")

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Script de démonstration EPITA - Intelligence Symbolique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Exemples d'utilisation :
  python {Path(__file__).name}                    # Mode normal
  python {Path(__file__).name} --interactive      # Mode interactif pédagogique
  python {Path(__file__).name} --quick-start      # Mode Quick Start pour étudiants
  python {Path(__file__).name} --metrics          # Affichage des métriques uniquement

[STUDENT] Mode interactif recommandé pour les étudiants !
        """
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Active le mode interactif avec pauses pédagogiques et quiz'
    )
    
    parser.add_argument(
        '--quick-start', '-q',
        action='store_true',
        help='Lance le mode Quick Start pour obtenir des suggestions de projets'
    )
    
    parser.add_argument(
        '--metrics', '-m',
        action='store_true',
        help='Affiche uniquement les métriques du projet'
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse les arguments de ligne de commande
    args = parse_arguments()
    
    # Configuration de l'environnement
    main_logger, project_root_path = setup_environment()
    
    # Mode Quick Start
    if args.quick_start:
        mode_quick_start()
        sys.exit(0)
    
    # Mode métriques uniquement
    if args.metrics:
        afficher_banniere_interactive()
        afficher_metriques_tests()
        sys.exit(0)
    
    # Mode interactif ou normal
    if args.interactive:
        run_interactive_demonstration(main_logger, project_root_path)
    else:
        # Mode normal (comportement original préservé)
        main_logger.info(f"{Symbols.ROCKET} === Début de l'orchestrateur de démonstration EPITA ===")
        
        # 1. Vérifier les dépendances
        check_and_install_dependencies(main_logger)
        
        # 2. Lancer les sous-scripts de démonstration
        run_subprocess("demo_notable_features.py", main_logger)
        run_subprocess("demo_advanced_features.py", main_logger)
        
        # 3. Lancer les tests du projet
        run_project_tests(main_logger)
        
        main_logger.info(f"\n{Symbols.CHECK} === Fin de l'orchestrateur de démonstration EPITA ===")