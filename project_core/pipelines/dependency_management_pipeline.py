#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ce module fournit un pipeline pour la gestion et l'installation des dépendances Python
d'un projet à partir d'un fichier de requirements.

Il utilise pip pour installer les paquets listés dans le fichier spécifié,
permettant des options telles que la réinstallation forcée et la transmission
d'options pip personnalisées. Le module est conçu pour être utilisé comme partie
d'un processus de configuration ou de déploiement automatisé.
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Supposons que ces utilitaires existent et sont importables.
# Si les chemins sont incorrects, ils devront être ajustés.
try:
    from project_core.utils.logging_utils import setup_logging
except ImportError:
    # Fallback si setup_logging n'est pas trouvé, pour permettre au code de se charger
    # Dans un vrai scénario, cette dépendance doit être résolue.
    print("Attention: project_core.utils.logging_utils.setup_logging non trouvé. Utilisation du logging standard.")
    def setup_logging(level="INFO"):
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        )

try:
    from project_core.utils.system_utils import run_shell_command
except ImportError:
    # Fallback si run_shell_command n'est pas trouvé
    print("Attention: project_core.utils.system_utils.run_shell_command non trouvé. Les installations échoueront.")
    def run_shell_command(command: str, work_dir: str = None, timeout: int = 60) -> Tuple[int, str, str]:
        return -1, "", f"Erreur: run_shell_command non implémenté/importé. Commande: {command}"

logger = logging.getLogger(__name__)

def run_dependency_installation_pipeline(
    requirements_file_path: str,
    force_reinstall: bool = False,
    log_level: str = "INFO",
    pip_options: List[str] = None
) -> bool:
    """
    Exécute le pipeline d'installation des dépendances Python à partir d'un fichier
    de type requirements.txt.

    Ce pipeline lit un fichier spécifiant les dépendances, puis tente d'installer
    chaque dépendance en utilisant pip. Il offre des options pour forcer la
    réinstallation et pour ajouter des arguments personnalisés à la commande pip.

    :param requirements_file_path: Chemin vers le fichier requirements (ex: "requirements.txt").
    :type requirements_file_path: str
    :param force_reinstall: Si True, force la réinstallation des paquets en ajoutant
                            l'option `--force-reinstall` à la commande pip.
                            Utile pour s'assurer que les paquets sont réinstallés
                            même s'ils sont déjà présents.
    :type force_reinstall: bool
    :param log_level: Niveau de verbosité du logging pour le pipeline.
                      Exemples: "INFO", "DEBUG", "WARNING".
    :type log_level: str
    :param pip_options: Liste d'options supplémentaires à passer directement à la
                        commande `pip install`. Par exemple, `["--no-cache-dir"]`.
    :type pip_options: List[str], optional
    :return: True si toutes les dépendances listées ont été installées avec succès,
             False si au moins une installation a échoué ou si le fichier
             requirements n'a pas pu être lu.
    :rtype: bool
    :raises FileNotFoundError: Si le fichier `requirements_file_path` n'est pas trouvé
                              (géré en interne, retourne False).
    :raises Exception: Pour d'autres erreurs potentielles lors de la lecture du fichier
                       requirements (géré en interne, retourne False).
    """
    setup_logging(log_level)
    logger.info(f"Démarrage du pipeline d'installation des dépendances depuis: {requirements_file_path}")

    if pip_options is None:
        pip_options = []

    req_file = Path(requirements_file_path)
    # Vérification de l'existence du fichier requirements
    if not req_file.is_file():
        logger.error(f"Le fichier requirements '{requirements_file_path}' n'a pas été trouvé.")
        return False # Conforme à :raises FileNotFoundError (implicitement)

    all_successful = True # Indicateur du succès global de l'installation

    # Lecture du fichier requirements
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            dependencies = f.readlines()
    except Exception as e: # Capture générique pour les erreurs de lecture
        logger.error(f"Erreur lors de la lecture du fichier '{requirements_file_path}': {e}")
        return False # Conforme à :raises Exception (implicitement)

    # Traitement de chaque dépendance
    for dep_line in dependencies:
        package_spec = dep_line.strip()
        # Ignorer les lignes vides ou les commentaires dans le fichier requirements
        if not package_spec or package_spec.startswith('#'):
            continue

        # Construction de la commande pip
        command_parts = [
            Path(sys.executable).name,  # Assure l'utilisation de l'interpréteur Python courant
            "-m",
            "pip",
            "install",
            package_spec # La dépendance spécifique, ex: "requests==2.25.1" ou "numpy"
        ]

        # Ajout de l'option de réinstallation forcée si demandée
        if force_reinstall:
            command_parts.append("--force-reinstall")
        
        # Ajout des options pip supplémentaires si fournies
        if pip_options:
            command_parts.extend(pip_options)

        command = " ".join(command_parts)
        
        logger.info(f"Tentative d'installation de '{package_spec}' avec la commande: '{command}'")
        
        # Exécution de la commande d'installation
        return_code, stdout_str, stderr_str = run_shell_command(command)
        
        # Vérification du résultat de l'installation
        if return_code == 0:
            logger.info(f"Installation de '{package_spec}' réussie.")
            if stdout_str: # Affichage des messages de sortie standard (souvent informatifs)
                logger.debug(f"Sortie pip (stdout) pour {package_spec}:\n{stdout_str}")
            if stderr_str: # Affichage des messages d'erreur standard (peuvent être des warnings)
                logger.debug(f"Sortie pip (stderr) pour {package_spec}:\n{stderr_str}")
        else:
            all_successful = False # Marquer l'échec si une dépendance ne s'installe pas
            logger.error(f"Erreur lors de l'installation de '{package_spec}'. Code de retour: {return_code}")
            if stdout_str:
                logger.error(f"Sortie pip (stdout) pour {package_spec} (erreur):\n{stdout_str}")
            if stderr_str:
                logger.error(f"Sortie pip (stderr) pour {package_spec} (erreur):\n{stderr_str}")
    
    # Message final basé sur le succès global
    if all_successful:
        logger.info("Toutes les dépendances listées dans le fichier requirements ont été traitées avec succès.")
    else:
        logger.warning("Au moins une dépendance n'a pas pu être installée correctement. Veuillez vérifier les logs.")
        
    return all_successful

if __name__ == '__main__':
    # Exemple d'utilisation (pourrait être exécuté directement pour des tests)
    # Créez un dummy_requirements.txt pour tester
    # exemple_req_file = Path(__file__).parent / "dummy_requirements.txt"
    # with open(exemple_req_file, "w") as f:
    #     f.write("requests==2.25.1\n")
    #     f.write("# Ceci est un commentaire\n")
    #     f.write("numpy\n")

    # print(f"Test du pipeline avec {exemple_req_file}")
    # success = run_dependency_installation_pipeline(str(exemple_req_file), force_reinstall=True, log_level="DEBUG")
    # print(f"Résultat du test du pipeline: {'Succès' if success else 'Échec'}")
    # exemple_req_file.unlink() # Nettoyage
    
    # Pour un test réel, vous devez avoir un fichier requirements.txt
    # et les utilitaires project_core.utils.* disponibles.
    logger.info("Ce module est destiné à être importé et utilisé via sa fonction run_dependency_installation_pipeline.")
    logger.info("Pour un test direct, décommentez et adaptez la section __main__.")