#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour activer le mock JPype.

Ce script importe et appelle la fonction setup_jpype_mock depuis
project_core.dev_utils.mock_utils pour configurer l'environnement
avec un JPype mocké.
"""

import os
import sys
import logging

# Configuration du logger pour ce script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_project_root_to_path():
    """Ajoute le répertoire racine du projet au sys.path."""
    try:
        # Chemin vers le répertoire racine du projet (en supposant que ce script est dans scripts/setup/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            logger.info(f"Répertoire racine du projet ajouté au PYTHONPATH : {project_root}")
        else:
            logger.info(f"Le répertoire racine du projet est déjà dans le PYTHONPATH : {project_root}")
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du répertoire racine au PYTHONPATH: {e}")
        # Quitter si le chemin ne peut pas être configuré, car l'import échouera.
        sys.exit(1)

def main():
    """
    Fonction principale pour activer le mock JPype.
    """
    logger.info("Début de la configuration du mock JPype via le script lanceur.")
    
    add_project_root_to_path()

    try:
        # Importer la fonction depuis son nouvel emplacement
        from project_core.dev_utils.mock_utils import setup_jpype_mock
        logger.info("Fonction setup_jpype_mock importée avec succès.")
        
        # Appeler la fonction pour activer le mock
        # Vous pouvez passer un chemin personnalisé ici si nécessaire, par exemple :
        # setup_jpype_mock(mock_jvm_path="/mon/chemin/jvm/mock")
        setup_jpype_mock()
        
        logger.info("Le mock JPype a été activé.")
        
        # Test simple pour vérifier si jpype est mocké (optionnel)
        try:
            import jpype
            from unittest import mock
            if isinstance(jpype.startJVM, mock.Mock):
                logger.info("Vérification : jpype.startJVM est bien un mock.")
            else:
                logger.warning("Vérification : jpype.startJVM ne semble pas être un mock.")
        except ImportError:
            logger.error("Vérification : Impossible d'importer jpype après l'activation du mock.")
        except Exception as e_check:
            logger.error(f"Vérification : Erreur lors de la vérification du mock jpype : {e_check}")

    except ImportError as e_import:
        logger.error(f"Erreur d'importation : {e_import}. Assurez-vous que project_core est dans le PYTHONPATH.")
        logger.error("Vérifiez que le fichier project_core/dev_utils/mock_utils.py existe et est correct.")
    except Exception as e:
        logger.error(f"Une erreur inattendue s'est produite lors de l'activation du mock JPype : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()