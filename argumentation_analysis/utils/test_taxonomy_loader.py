#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour l'utilitaire de lazy loading de la taxonomie des sophismes.
Ce script vérifie que le fichier de taxonomie peut être correctement téléchargé et validé.
"""

import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestTaxonomyLoader")

# Import de l'utilitaire de lazy loading
from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path, validate_taxonomy_file

def test_taxonomy_loader():
    """
    Teste l'utilitaire de lazy loading de la taxonomie des sophismes.
    """
    logger.info("Test de l'utilitaire de lazy loading de la taxonomie...")
    
    try:
        # Obtenir le chemin du fichier de taxonomie
        taxonomy_path = get_taxonomy_path()
        logger.info(f"Chemin du fichier de taxonomie: {taxonomy_path}")
        
        # Vérifier que le fichier existe
        assert os.path.exists(taxonomy_path), f"Le fichier de taxonomie n'existe pas: {taxonomy_path}"
        
        # Vérifier la taille du fichier
        file_size = os.path.getsize(taxonomy_path)
        logger.info(f"Taille du fichier de taxonomie: {file_size} octets")
        
        assert file_size > 0, "Le fichier de taxonomie est vide"
        
        # Valider le fichier
        is_valid = validate_taxonomy_file()
        logger.info(f"Validation du fichier de taxonomie: {is_valid}")
        
        assert is_valid is True, "La validation du fichier de taxonomie a échoué"
    
    except Exception as e:
        logger.error(f"Erreur lors du test de l'utilitaire de lazy loading: {e}")
        raise

if __name__ == "__main__":
    result = test_taxonomy_loader()
    print(f"\nRésultat du test: {'SUCCÈS' if result else 'ÉCHEC'}")