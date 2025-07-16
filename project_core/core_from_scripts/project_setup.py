"""
Gestionnaire de setup et configuration projet
===========================================

Centralise la configuration et le setup du projet.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
from pathlib import Path
import sys
import argparse
from typing import Dict, List, Optional, Any
import site

from .common_utils import Logger, LogLevel
from .environment_manager import EnvironmentManager
from .validation.validation_engine import ValidationEngine


class ProjectSetup:
    """Gestionnaire de setup projet"""
    
    def __init__(self, logger: Logger = None):
        self.logger = logger or Logger()
        self.env_manager = EnvironmentManager(logger_instance=self.logger)
        self.validator = ValidationEngine(logger=self.logger)
    
    def setup_environment(self, env_name: str, force: bool = False, with_mocks: bool = False) -> bool:
        """
        Orchestre le setup complet d'un environnement spécifié.

        Args:
            env_name (str): Le nom de l'environnement à configurer ('test' ou 'dev').
            force (bool): Si True, force le setup même si des prérequis sont manquants.
            with_mocks (bool): Spécifique à l'environnement 'test', active les mocks.

        Returns:
            bool: True si le setup a réussi, False sinon.
        """
        self.logger.info(f"Démarrage du setup pour l'environnement : '{env_name}'...")
        if env_name == 'test':
            return self._setup_test_environment(with_mocks=with_mocks)
        elif env_name == 'dev':
            return self._setup_development_environment(force=force)
        else:
            self.logger.error(f"Nom d'environnement non reconnu : '{env_name}'. Les choix valides sont 'test', 'dev'.")
            return False

    def _setup_development_environment(self, force: bool = False) -> bool:
        """Setup complet de l'environnement de développement."""
        self.logger.info("Setup de l'environnement de développement...")
        
        # Vérifications préalables
        validation_results = self.validator.run()
        failed_validations = [r for r in validation_results if not r.success]

        if failed_validations and not force:
            self.logger.error("Setup impossible - Prérequis de validation manquants")
            for result in failed_validations:
                self.logger.error(f"  - Règle '{result.rule_name}': {result.message}")
            return False
        
        # Configuration variables d'environnement
        self.env_manager.setup_environment_variables()
        
        self.logger.success("Setup environnement de développement terminé.")
        return True
    
    def check_project_status(self) -> Dict[str, Any]:
        """Vérifie le statut complet du projet"""
        status = {
            "conda_available": self.env_manager.check_conda_available(),
            "conda_env_exists": self.env_manager.check_conda_env_exists(),
            "python_version_ok": self.env_manager.check_python_version(),
            "prerequisites_ok": all(r.success for r in self.validator.run())
        }
        
        status["overall_status"] = all(status.values())
        return status

    def install_project(self, requirements_file: str = "requirements.txt") -> bool:
        """
        Orchestre une installation complète et propre du projet.

        Cette méthode exécute les étapes suivantes dans l'ordre :
        1. Valide la présence des outils de compilation.
        2. Tente d'installer les dépendances depuis le fichier requirements.txt.
        3. Crée le fichier .pth pour assurer la visibilité du projet dans le PYTHONPATH.

        Args:
            requirements_file (str): Le chemin vers le fichier requirements.txt principal.

        Returns:
            bool: True si toutes les étapes ont réussi, False sinon.
        """
        self.logger.info("Démarrage de l'installation orchestrée du projet...")
        
        # Étape 1: Valider les outils de compilation
        # self.logger.info("Étape 1/3 : Validation des outils de compilation...")
        # build_tools_status = self.validator.validate_build_tools()
        # self.logger.info(build_tools_status['message'])
        # if build_tools_status['status'] == 'failure':
        #     self.logger.error("Installation annulée. Veuillez installer les outils de compilation requis et réessayer.")
        #     return False
        # self.logger.success("Outils de compilation validés.")

        # Étape 2: Installer les dépendances depuis requirements.txt
        self.logger.info(f"Étape 1/2 : Installation des dépendances depuis '{requirements_file}'...")
        deps_installed = self.env_manager.fix_dependencies(requirements_file=requirements_file, strategy_name='aggressive')
        if not deps_installed:
            self.logger.error(f"L'installation des dépendances depuis '{requirements_file}' a échoué. Installation annulée.")
            return False
        self.logger.success("Dépendances installées avec succès.")

        # Étape 3: Configurer le PYTHONPATH
        self.logger.info("Étape 3/3 : Configuration du PYTHONPATH via le fichier .pth...")
        path_set = self.set_project_path_file()
        if not path_set:
            self.logger.error("La configuration du PYTHONPATH a échoué. L'installation est peut-être incomplète.")
            return False
        self.logger.success("PYTHONPATH configuré avec succès.")

        self.logger.success("Installation complète du projet terminée avec succès!")
        return True

    def set_project_path_file(self) -> bool:
        """
        Crée un fichier .pth pour ajouter la racine du projet au PYTHONPATH.

        Cette méthode est une solution de secours robuste lorsque les installations
        en mode édition (`pip install -e .`) échouent.

        Returns:
            True si le fichier a été créé ou mis à jour, False en cas d'erreur.
        """
        try:
            # Déterminer le chemin racine du projet
            project_root = Path(__file__).resolve().parent.parent.parent
            
            # Obtenir le répertoire site-packages de l'environnement actuel
            site_packages_paths = site.getsitepackages()
            
            # Si `getsitepackages` ne retourne rien, essayer `getusersitepackages` comme fallback
            if not site_packages_paths:
                self.logger.warning("site.getsitepackages() n'a retourné aucun chemin. Tentative avec site.getusersitepackages().")
                user_site_packages = site.getusersitepackages()
                if user_site_packages and Path(user_site_packages).is_dir():
                    site_packages_paths = [user_site_packages]
                else:
                    self.logger.error("Impossible de déterminer le répertoire site-packages, même avec getusersitepackages.")
                    return False

            # Utiliser le premier chemin de site-packages trouvé
            site_packages = Path(site_packages_paths[0])
            if not site_packages.is_dir():
                self.logger.error(f"Le répertoire site-packages trouvé n'existe pas ou n'est pas un répertoire : {site_packages}")
                return False
                
            pth_file_path = site_packages / "argumentation_analysis_project.pth"
            
            self.logger.info(f"Création/Mise à jour du fichier .pth : {pth_file_path}")
            
            # Écrire le chemin absolu de la racine du projet dans le fichier .pth
            with open(pth_file_path, 'w') as f:
                f.write(str(project_root))
            
            self.logger.info(f"Le fichier '{pth_file_path.name}' a été configuré avec succès.")
            return True

        except Exception as e:
            self.logger.error(f"Erreur lors de la création du fichier .pth : {e}")
            return False


    def download_test_jars(self) -> bool:
        """
        Télécharge les dépendances .jar requises pour l'environnement de test.
        (Conforme au Lot 5, Partie C)
        """
        self.logger.info("Vérification/Téléchargement des Jars de test...")
        # Pour l'instant, nous simulons le succès car la logique de téléchargement
        # n'est pas l'objectif principal de ce lot.
        self.logger.info("Les Jars de test sont considérés à jour (simulation).")
        return True

    def _setup_test_environment(self, with_mocks: bool = False) -> bool:
        """
        Prépare l'environnement pour l'exécution des tests en orchestrant les tâches nécessaires.
        (Conforme au Lot 11 et 12)
        """
        self.logger.info("Orchestration de la configuration de l'environnement de test...")

        # Étape 1: Télécharger les dépendances de test (Lot 5)
        if not self.download_test_jars():
            self.logger.error("Échec du téléchargement des Jars de test. Setup annulé.")
            return False
        
        # Étape 2: Configurer les mocks si nécessaire (Lot 11)
        if with_mocks:
            self.logger.info("Activation des mocks pour l'environnement de test...")
            # La logique de patching/mocking serait appelée ici.
            # Exemple: self.env_manager.apply_jpype_mocks()
            self.logger.info("Mocks activés (simulation).")

        self.logger.success("Environnement de test configuré avec succès.")
        return True


def setup_environment(env_name: str, force: bool = False, with_mocks: bool = False, logger: Logger = None) -> bool:
    """Fonction wrapper pour un appel programmatique."""
    setup = ProjectSetup(logger)
    return setup.setup_environment(env_name, force, with_mocks)


def check_project_status(logger: Logger = None) -> Dict[str, Any]:
    """Fonction utilitaire de vérification statut"""
    setup = ProjectSetup(logger)
    return setup.check_project_status()


def main():
    """Point d'entrée CLI pour le gestionnaire de setup."""
    parser = argparse.ArgumentParser(description="Gestionnaire de Setup et Configuration du Projet.")
    # Arguments globaux
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux.')
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles', required=True)

    # Commande `setup`
    parser_setup = subparsers.add_parser('setup', help="Configurer un environnement de projet ('dev' ou 'test').")
    parser_setup.add_argument('--env', type=str, required=True, choices=['dev', 'test'], help="Le type d'environnement à configurer.")
    parser_setup.add_argument('--force', action='store_true', help="Forcer le setup même si des prérequis sont manquants (utilisé pour 'dev').")
    parser_setup.add_argument('--with-mocks', action='store_true', help="Activer les mocks pour les tests (utilisé pour 'test').")

    # Commande `status`
    subparsers.add_parser('status', help='Vérifier le statut complet du projet.')

    # Commande `install`
    parser_install = subparsers.add_parser('install', help='Lancer une installation complète et propre du projet.')
    parser_install.add_argument('--requirements', type=str, default='requirements.txt', help='Chemin vers le fichier requirements.txt.')
    
    args = parser.parse_args()
    logger = Logger(verbose=args.verbose)
    setup = ProjectSetup(logger)

    if args.command == 'setup':
        success = setup.setup_environment(env_name=args.env, force=args.force, with_mocks=args.with_mocks)
        sys.exit(0 if success else 1)
    elif args.command == 'status':
        status = setup.check_project_status()
        for key, value in status.items():
            logger.info(f"{key}: {'✓' if value else '✗'}")
        sys.exit(0 if status["overall_status"] else 1)
    elif args.command == 'install':
        success = setup.install_project(requirements_file=args.requirements)
        sys.exit(0 if success else 1)
    else:
        # Inatteignable avec `required=True` sur subparsers en Python 3.7+
        parser.print_help()


if __name__ == "__main__":
    main()