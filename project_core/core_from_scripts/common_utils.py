"""
Utilitaires communs pour les scripts de projet
=============================================

Ce module fournit les fonctionnalités de base utilisées par tous les scripts :
- Logging avec couleurs et timestamps
- Gestion des messages d'erreur/succès/warning
- Utilitaires de formatage et parsing d'arguments
- Gestion sécurisée des sorties

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import os
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import platform


class LogLevel(Enum):
    """Niveaux de log disponibles"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ColorCodes:
    """Codes couleurs ANSI pour terminaux compatibles"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Couleurs de base
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Couleurs brillantes
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class Logger:
    """Logger centralisé avec support couleurs et formatage"""
    
    def __init__(self, use_colors: bool = None, verbose: bool = False):
        """
        Initialise le logger
        
        Args:
            use_colors: Utiliser les couleurs (auto-détecté si None)
            verbose: Mode verbeux pour plus de détails
        """
        self.verbose = verbose
        self.use_colors = use_colors if use_colors is not None else self._supports_color()
        self.color_map = {
            LogLevel.DEBUG: ColorCodes.CYAN,
            LogLevel.INFO: ColorCodes.WHITE,
            LogLevel.SUCCESS: ColorCodes.BRIGHT_GREEN,
            LogLevel.WARNING: ColorCodes.BRIGHT_YELLOW,
            LogLevel.ERROR: ColorCodes.BRIGHT_RED,
            LogLevel.CRITICAL: ColorCodes.RED + ColorCodes.BOLD
        }
    
    def _supports_color(self) -> bool:
        """Détecte si le terminal supporte les couleurs"""
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            os.getenv('TERM', '').lower() != 'dumb' and
            platform.system() != 'Windows'  # Windows PowerShell gérera les couleurs différemment
        )
    
    def _format_message(self, message: str, level: LogLevel) -> str:
        """Formate un message avec timestamp et niveau"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level.value}] {message}"
        
        if self.use_colors and level in self.color_map:
            color = self.color_map[level]
            formatted = f"{color}{formatted}{ColorCodes.RESET}"
        
        return formatted
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO):
        """Log un message avec le niveau spécifié"""
        if level == LogLevel.DEBUG and not self.verbose:
            return
        
        formatted = self._format_message(message, level)
        
        # Erreurs et critiques vers stderr
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            print(formatted, file=sys.stderr)
        else:
            print(formatted)
    
    def debug(self, message: str):
        """Log un message de debug"""
        self.log(message, LogLevel.DEBUG)
    
    def info(self, message: str):
        """Log un message d'information"""
        self.log(message, LogLevel.INFO)
    
    def success(self, message: str):
        """Log un message de succès"""
        self.log(message, LogLevel.SUCCESS)
    
    def warning(self, message: str):
        """Log un message d'avertissement"""
        self.log(message, LogLevel.WARNING)
    
    def error(self, message: str):
        """Log un message d'erreur"""
        self.log(message, LogLevel.ERROR)
    
    def critical(self, message: str):
        """Log un message critique"""
        self.log(message, LogLevel.CRITICAL)


class ColoredOutput:
    """Classe utilitaire pour affichage coloré simple"""
    
    @staticmethod
    def print_banner(title: str, char: str = "="):
        """Affiche une bannière stylée"""
        banner_line = char * max(60, len(title) + 4)
        print(f"\n{banner_line}")
        print(f"{char} {title.center(len(banner_line) - 4)} {char}")
        print(f"{banner_line}\n")
    
    @staticmethod
    def print_section(title: str):
        """Affiche un titre de section"""
        print(f"\n🔸 {title}")
        print("-" * (len(title) + 4))


def format_timestamp(dt: datetime = None) -> str:
    """Formate un timestamp pour les fichiers et logs"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y%m%d_%H%M%S")


def safe_exit(code: int, logger: Logger = None, message: str = None):
    """Sortie sécurisée avec logging optionnel"""
    if logger and message:
        if code == 0:
            logger.success(message)
        else:
            logger.error(message)
    
    sys.exit(code)


def parse_common_args() -> argparse.ArgumentParser:
    """Crée un parser d'arguments avec les options communes"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Options communes à tous les scripts
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mode verbeux pour plus de détails'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulation sans exécution réelle'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Désactiver les couleurs dans la sortie'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Fichier de sortie pour les rapports'
    )
    
    return parser


def load_json_config(config_path: str) -> Optional[Dict[str, Any]]:
    """Charge un fichier de configuration JSON"""
    try:
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    except (json.JSONDecodeError, IOError) as e:
        print(f"Erreur lors du chargement de {config_path}: {e}", file=sys.stderr)
        return None


def save_json_report(data: Dict[str, Any], output_path: str, logger: Logger = None) -> bool:
    """Sauvegarde un rapport en JSON"""
    try:
        # Ajout de métadonnées
        report = {
            "timestamp": datetime.now().isoformat(),
            "generated_by": "Intelligence Symbolique EPITA",
            "platform": platform.platform(),
            "python_version": sys.version,
            **data
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        if logger:
            logger.success(f"Rapport sauvegardé: {output_path}")
        
        return True
    
    except IOError as e:
        if logger:
            logger.error(f"Erreur sauvegarde rapport: {e}")
        return False


def validate_file_path(path: str, must_exist: bool = True) -> bool:
    """Valide qu'un chemin de fichier est correct"""
    if not path:
        return False
    
    if must_exist:
        return os.path.exists(path)
    else:
        # Vérifier que le répertoire parent existe
        parent_dir = os.path.dirname(path)
        return os.path.exists(parent_dir) if parent_dir else True


def get_project_root() -> str:
    """Retourne la racine du projet"""
    # Cherche le répertoire contenant setup_project_env.ps1
    current = os.getcwd()
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, "setup_project_env.ps1")):
            return current
        current = os.path.dirname(current)
    
    # Fallback vers le répertoire courant
    return os.getcwd()


def create_progress_indicator(total: int, prefix: str = "Progression"):
    """Crée un indicateur de progression simple"""
    def update_progress(current: int, suffix: str = ""):
        percent = (current / total) * 100
        bar_length = 50
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'\r{prefix}: |{bar}| {percent:.1f}% {suffix}', end='', flush=True)
        if current == total:
            print()  # Nouvelle ligne à la fin
    
    return update_progress


# Instance globale du logger pour utilisation simple
default_logger = Logger()

# Fonctions de commodité
def log_info(message: str):
    """Log d'information via le logger global"""
    default_logger.info(message)

def log_success(message: str):
    """Log de succès via le logger global"""
    default_logger.success(message)

def log_warning(message: str):
    """Log d'avertissement via le logger global"""
    default_logger.warning(message)

def log_error(message: str):
    """Log d'erreur via le logger global"""
    default_logger.error(message)

def log_debug(message: str):
    """Log de debug via le logger global"""
    default_logger.debug(message)


def print_colored(message: str, color: str = "white", bold: bool = False):
    """
    Affiche un message coloré dans le terminal
    
    Args:
        message: Message à afficher
        color: Couleur (red, green, yellow, blue, cyan, magenta, white)
        bold: Texte en gras
    """
    color_map = {
        'red': ColorCodes.RED,
        'green': ColorCodes.GREEN,
        'yellow': ColorCodes.YELLOW,
        'blue': ColorCodes.BLUE,
        'cyan': ColorCodes.CYAN,
        'magenta': ColorCodes.MAGENTA,
        'white': ColorCodes.WHITE,
        'bright_red': ColorCodes.BRIGHT_RED,
        'bright_green': ColorCodes.BRIGHT_GREEN,
        'bright_yellow': ColorCodes.BRIGHT_YELLOW,
        'bright_blue': ColorCodes.BRIGHT_BLUE,
        'bright_cyan': ColorCodes.BRIGHT_CYAN,
        'bright_magenta': ColorCodes.BRIGHT_MAGENTA,
        'bright_white': ColorCodes.BRIGHT_WHITE,
    }
    
    # Vérifier si les couleurs sont supportées
    supports_color = (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
        os.getenv('TERM', '').lower() != 'dumb'
    )
    
    if supports_color and color.lower() in color_map:
        color_code = color_map[color.lower()]
        bold_code = ColorCodes.BOLD if bold else ""
        formatted_message = f"{bold_code}{color_code}{message}{ColorCodes.RESET}"
    else:
        formatted_message = message
    
    # Gestion de l'encodage Unicode sur Windows
    try:
        print(formatted_message)
    except UnicodeEncodeError:
        # Fallback sans caractères Unicode problématiques
        safe_message = formatted_message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)


def setup_logging(verbose: bool = False, use_colors: bool = None) -> Logger:
    """
    Configure et retourne un logger pour le projet
    
    Args:
        verbose: Active le mode verbeux
        use_colors: Utilise les couleurs (auto-détecté si None)
    
    Returns:
        Instance configurée du logger
    """
    return Logger(use_colors=use_colors, verbose=verbose)


def validate_python_requirements() -> Dict[str, Any]:
    """
    Valide que les prérequis Python sont satisfaits
    
    Returns:
        Dictionnaire avec les résultats de validation
    """
    issues = []
    
    # Vérification version Python
    if sys.version_info < (3, 7):
        issues.append(f"Python 3.7+ requis, version actuelle: {sys.version}")
    
    # Vérification modules requis
    required_modules = ['json', 'os', 'sys', 'datetime', 'platform']
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            issues.append(f"Module Python requis manquant: {module}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'python_version': sys.version,
        'platform': platform.platform()
    }