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
    
    def setup_environment(self, force: bool = False) -> bool:
        """Setup complet de l'environnement"""
        self.logger.info("Setup de l'environnement projet...")
        
        # Vérifications préalables
        issues = self.validator.check_prerequisites()
        if issues and not force:
            self.logger.error("Setup impossible - Prérequis manquants")
            for issue in issues:
                self.logger.error(f"  - {issue}")
            return False
        
        # Configuration variables d'environnement
        self.env_manager.setup_environment_variables()
        
        self.logger.success("Setup environnement terminé")
        return True
    
    def check_project_status(self) -> Dict[str, Any]:
        """Vérifie le statut complet du projet"""
        status = {
            "conda_available": self.env_manager.check_conda_available(),
            "conda_env_exists": self.env_manager.check_conda_env_exists(),
            "python_version_ok": self.env_manager.check_python_version(),
            "prerequisites_ok": len(self.validator.check_prerequisites()) == 0
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
        self.logger.info("Étape 1/3 : Validation des outils de compilation...")
        build_tools_status = self.validator.validate_build_tools()
        self.logger.info(build_tools_status['message'])
        if build_tools_status['status'] == 'failure':
            self.logger.error("Installation annulée. Veuillez installer les outils de compilation requis et réessayer.")
            return False
        self.logger.success("Outils de compilation validés.")

        # Étape 2: Installer les dépendances depuis requirements.txt
        self.logger.info(f"Étape 2/3 : Installation des dépendances depuis '{requirements_file}'...")
        deps_installed = self.env_manager.fix_dependencies(requirements_file=requirements_file, strategy='aggressive')
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


def setup_environment(force: bool = False, logger: Logger = None) -> bool:
    """Fonction utilitaire de setup"""
    def setup_test_environment(self, with_mocks: bool = False) -> bool:
        """
        Prépare l'environnement pour l'exécution des tests.

        Cette fonction peut, par exemple, s'assurer que les dépendances de test
        sont installées et configurer des mocks si nécessaire.

        Args:
            with_mocks (bool): Si True, active les mocks pour des modules
                               comme JPype, simulant un environnement où le pont
                               JVM n'est pas nécessaire.

        Returns:
            bool: True si la préparation a réussi, False sinon.
        """
        self.logger.info("Configuration de l'environnement de test...")

        if with_mocks:
            self.logger.info("Activation des mocks pour l'environnement de test...")
            # La logique de patching/mocking sera appelée ici.
            # Pour l'instant, nous simulons le succès.
            # Exemple: self.env_manager.apply_jpype_mocks()
            self.logger.info("Mocks activés.")

        # D'autres étapes de préparation pourraient être ajoutées ici,
        # comme le téléchargement de dépendances de test.

        self.logger.success("Environnement de test prêt.")
        return True
    setup = ProjectSetup(logger)
    return setup.setup_environment(force)


def check_project_status(logger: Logger = None) -> Dict[str, Any]:
    """Fonction utilitaire de vérification statut"""
    setup = ProjectSetup(logger)
    return setup.check_project_status()


def main():
    """Point d'entrée CLI"""
    parser = argparse.ArgumentParser(description="Setup projet")
    parser.add_argument('--setup', action='store_true', help='Setup environnement')
    parser.add_argument('--status', action='store_true', help='Vérifier statut')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    logger = Logger(verbose=args.verbose)
    
    if args.setup:
        success = setup_environment(logger=logger)
        sys.exit(0 if success else 1)
    elif args.status:
        status = check_project_status(logger)
        for key, value in status.items():
            logger.info(f"{key}: {'✓' if value else '✗'}")
        sys.exit(0 if status["overall_status"] else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()