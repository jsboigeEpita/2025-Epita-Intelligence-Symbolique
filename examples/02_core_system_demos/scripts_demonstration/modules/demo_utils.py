# -*- coding: utf-8 -*-
"""
Utilitaires communs pour les modules de démonstration EPITA
Architecture modulaire - Intelligence Symbolique
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from project_core.utils.shell import run_sync, run_in_activated_env, ShellCommandError

# Import de PyYAML avec fallback
try:
    import yaml
except ImportError:
    print("PyYAML non trouvé. Installation...")
    run_sync([sys.executable, "-m", "pip", "install", "PyYAML"], check_errors=True)
    import yaml


# Codes couleur ANSI pour la console
class Colors:
    """Codes couleur ANSI pour la console"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


# Symboles pour l'interface
class Symbols:
    """Symboles pour l'interface pédagogique"""

    BOOK = "[COURS]"
    ROCKET = "[START]"
    CHECK = "[OK]"
    CROSS = "[FAIL]"
    QUESTION = "[?]"
    BULB = "[ASTUCE]"
    GEAR = "[EXEC]"
    CHART = "[STATS]"
    TARGET = "[OBJECTIF]"
    STAR = "[STAR]"
    FIRE = "[EXCELLENT]"
    BRAIN = "[IA]"
    WARNING = "[ATTENTION]"


class DemoLogger:
    """Logger spécialisé pour les démonstrations"""

    def __init__(self, nom_module: str):
        self.logger = logging.getLogger(f"demo_{nom_module}")
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def success(self, message: str):
        self.logger.info(f"{Colors.GREEN}{message}{Colors.ENDC}")

    def header(self, message: str):
        self.logger.info(f"{Colors.BOLD}{Colors.CYAN}{message}{Colors.ENDC}")


def charger_config_categories() -> Dict[str, Any]:
    """Charge la configuration des catégories depuis le fichier YAML"""
    config_path = Path(__file__).parent.parent / "configs" / "demo_categories.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(
            f"{Colors.FAIL}Erreur lors du chargement de la configuration : {e}{Colors.ENDC}"
        )
        return {}


def afficher_progression(etape: int, total: int, description: str = "") -> None:
    """Affiche une barre de progression colorée"""
    pourcentage = (etape / total) * 100
    barre_longueur = 50
    barre_remplie = int((etape / total) * barre_longueur)

    if pourcentage < 30:
        couleur = Colors.FAIL
    elif pourcentage < 70:
        couleur = Colors.WARNING
    else:
        couleur = Colors.GREEN

    barre = "#" * barre_remplie + "-" * (barre_longueur - barre_remplie)

    print(f"\n{Colors.BOLD}{Symbols.CHART} Progression :{Colors.ENDC}")
    print(f"{couleur}[{barre}] {pourcentage:.1f}% ({etape}/{total}){Colors.ENDC}")
    if description:
        print(f"{Colors.CYAN}{Symbols.TARGET} {description}{Colors.ENDC}")


def executer_tests(
    pattern_tests: List[str], logger: DemoLogger, timeout: int = 300
) -> Tuple[bool, Dict[str, Any]]:
    """Exécute une liste de tests avec pytest et retourne les résultats"""
    logger.header(f"{Symbols.GEAR} Exécution des tests : {', '.join(pattern_tests)}")

    resultats = {"total": 0, "passed": 0, "failed": 0, "duration": 0, "details": []}

    start_time = time.time()

    try:
        # Construire la commande pour run_in_activated_env. On lance pytest en tant que module.
        cmd = ["-m", "pytest", "-v"] + pattern_tests

        process = run_in_activated_env(
            cmd, check_errors=False, timeout=timeout  # On gère les erreurs manuellement
        )

        resultats["duration"] = time.time() - start_time

        # Parser la sortie
        output_to_parse = process.stdout or ""
        for line in output_to_parse.splitlines():
            if "PASSED" in line:
                resultats["passed"] += 1
                resultats["total"] += 1
                logger.info(f"{Colors.GREEN}{line}{Colors.ENDC}")
            elif "FAILED" in line:
                resultats["failed"] += 1
                resultats["total"] += 1
                logger.info(f"{Colors.FAIL}{line}{Colors.ENDC}")
            elif "::" in line and ("test_" in line or "Test" in line):
                resultats["details"].append(line)

        if process.returncode == 0:
            logger.success(
                f"{Symbols.CHECK} Tests réussis : {resultats.get('passed', 0)}/{resultats.get('total', 0)}"
            )
            return True, resultats
        else:
            logger.error(
                f"{Symbols.CROSS} Tests échoués : {resultats.get('failed', 0)}/{resultats.get('total', 0)}"
            )
            if process.stderr:
                logger.error(f"Stderr: {process.stderr}")
            return False, resultats

    except ShellCommandError as e:
        logger.error(f"{Symbols.CROSS} Erreur Shell (Timeout ou autre) : {e}")
        return False, resultats
    except Exception as e:
        logger.error(f"{Symbols.CROSS} Erreur inattendue lors de l'exécution : {e}")
        return False, resultats


def afficher_stats_tests(resultats: Dict[str, Any]) -> None:
    """Affiche les statistiques des tests de façon colorée"""
    total = resultats.get("total", 0)
    passed = resultats.get("passed", 0)
    failed = resultats.get("failed", 0)
    duration = resultats.get("duration", 0)

    print(f"\n{Colors.BOLD}{Symbols.CHART} STATISTIQUES DES TESTS{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")

    if total > 0:
        taux_succes = (passed / total) * 100
        couleur_taux = (
            Colors.GREEN
            if taux_succes >= 90
            else Colors.WARNING
            if taux_succes >= 70
            else Colors.FAIL
        )

        print(f"{Colors.GREEN}{Symbols.CHECK} Tests réussis : {passed}{Colors.ENDC}")
        print(f"{Colors.FAIL}{Symbols.CROSS} Tests échoués : {failed}{Colors.ENDC}")
        print(f"{Colors.BLUE}{Symbols.GEAR} Total exécuté : {total}{Colors.ENDC}")
        print(
            f"{couleur_taux}{Symbols.STAR} Taux de succès : {taux_succes:.1f}%{Colors.ENDC}"
        )
        print(
            f"{Colors.CYAN}{Symbols.CHART} Durée d'exécution : {duration:.2f}s{Colors.ENDC}"
        )
    else:
        print(f"{Colors.WARNING}{Symbols.WARNING} Aucun test exécuté{Colors.ENDC}")


def afficher_menu_module(
    titre: str, description: str, fonctionnalites: List[str]
) -> None:
    """Affiche le menu d'un module de démonstration"""
    print(
        f"\n{Colors.BOLD}{Colors.HEADER}╔═══════════════════════════════════════════════════════════════════════╗{Colors.ENDC}"
    )
    print(f"{Colors.BOLD}{Colors.HEADER}║{titre:^70}║{Colors.ENDC}")
    print(
        f"{Colors.BOLD}{Colors.HEADER}╚═══════════════════════════════════════════════════════════════════════╝{Colors.ENDC}"
    )

    print(f"\n{Colors.CYAN}{Symbols.TARGET} {description}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Fonctionnalités disponibles :{Colors.ENDC}")
    for i, fonc in enumerate(fonctionnalites, 1):
        print(f"  {Colors.GREEN}{i}.{Colors.ENDC} {fonc}")


def pause_interactive(message: str = "Appuyez sur Entrée pour continuer...") -> None:
    """Pause interactive avec message personnalisé"""
    print(f"\n{Colors.WARNING}[PAUSE] {message}{Colors.ENDC}")
    input()


def confirmer_action(message: str) -> bool:
    """Demande confirmation à l'utilisateur"""
    reponse = input(f"\n{Colors.CYAN}{message} (o/n) : {Colors.ENDC}").lower()
    return reponse in ["o", "oui", "y", "yes"]


def afficher_erreur_module(nom_module: str, erreur: str) -> None:
    """Affiche une erreur de module de façon uniforme"""
    print(
        f"\n{Colors.FAIL}{Colors.BOLD}ERREUR - MODULE {nom_module.upper()}{Colors.ENDC}"
    )
    print(f"{Colors.FAIL}{Symbols.CROSS} {erreur}{Colors.ENDC}")


def valider_environnement() -> bool:
    """Valide que l'environnement est correctement configuré"""
    try:
        # Vérifier que nous sommes dans la racine du projet
        project_root = Path.cwd()
        required_dirs = ["examples", "tests", "project_core"]

        for dir_name in required_dirs:
            if not (project_root / dir_name).exists():
                print(f"{Colors.FAIL}Répertoire manquant : {dir_name}{Colors.ENDC}")
                return False

        return True
    except Exception as e:
        print(f"{Colors.FAIL}Erreur de validation environnement : {e}{Colors.ENDC}")
        return False
