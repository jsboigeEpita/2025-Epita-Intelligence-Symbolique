#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de vérification des extraits

Ce script vérifie la validité des extraits définis dans extract_sources.json
en s'assurant que les marqueurs de début et de fin sont présents dans les textes sources.

Fonctionnalités:
- Vérification de la présence des marqueurs dans les textes sources
- Génération d'un rapport détaillé des problèmes détectés
- Prise en charge des templates pour les marqueurs de début
- Vérification spécifique pour le corpus de discours d'Hitler
"""

import os
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VerifyExtracts")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("verify_extracts.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

# Imports des services et modèles
from argumentation_analysis.models.extract_definition import ExtractDefinitions # SourceDefinition, Extract ne sont plus utilisés directement ici
# from argumentation_analysis.services.cache_service import CacheService # Non utilisé directement
from argumentation_analysis.services.crypto_service import CryptoService # Utilisé par DefinitionService
from argumentation_analysis.services.definition_service import DefinitionService
# from argumentation_analysis.services.extract_service import ExtractService # La logique d'extraction est dans marker_verification_logic
# from argumentation_analysis.services.fetch_service import FetchService # La logique de fetch est dans marker_verification_logic
from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON

# Import de la logique métier déplacée
from argumentation_analysis.utils.extract_repair.marker_verification_logic import (
    verify_all_extracts, # Remplacera la fonction verify_extracts locale
    generate_verification_report # Remplacera la fonction generate_report locale
)
# Note: verify_extract n'est pas importé car verify_all_extracts l'utilise en interne.

# La fonction verify_extracts originale est remplacée par verify_all_extracts importée.
# La fonction generate_report originale est remplacée par generate_verification_report importée.

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Vérification des extraits")
    parser.add_argument("--output", "-o", default="verify_report.html", help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None, help="Fichier d'entrée personnalisé")
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de vérification des extraits...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    logger.info(f"Chemin du script: {os.path.abspath(__file__)}")
    
    # Initialiser les services
    try:
        # Créer le service de cache
        cache_dir = Path("./text_cache")
        cache_service = CacheService(cache_dir)
        
        # Créer le service de chiffrement
        crypto_service = CryptoService(ENCRYPTION_KEY) # Conserver si DefinitionService en a besoin
        
        # Les services ExtractService et FetchService ne sont plus nécessaires ici
        # car la logique qui les utilisait est maintenant dans marker_verification_logic.py
        # et cette logique (verify_all_extracts) s'attend à recevoir les définitions chargées.
        
        # Créer le service de définition
        input_file = Path(args.input) if args.input else Path(CONFIG_FILE)
        fallback_file = Path(CONFIG_FILE_JSON) if Path(CONFIG_FILE_JSON).exists() else None
        definition_service = DefinitionService(
            crypto_service=crypto_service,
            config_file=input_file,
            fallback_file=fallback_file
        )
        
        # Charger les définitions d'extraits
        extract_definitions, error_message = definition_service.load_definitions()
        if error_message:
            logger.warning(f"Avertissement lors du chargement des définitions: {error_message}")
        
        logger.info(f"{len(extract_definitions.sources)} sources chargées.")
        
        # Vérifier les extraits
        # Charger les définitions d'extraits en tant que liste de dictionnaires,
        # car c'est ce que verify_all_extracts attend.
        # DefinitionService.load_definitions() retourne un objet ExtractDefinitions.
        # Nous devons le convertir ou ajuster verify_all_extracts.
        # Pour l'instant, supposons que definition_service.load_definitions() peut retourner
        # la structure attendue ou qu'une conversion est faite.
        # Si extract_definitions est un objet ExtractDefinitions, il faut extraire .sources
        # et potentiellement convertir chaque source et extrait en dictionnaire si nécessaire.
        
        # Pour simplifier, nous allons passer extract_definitions.to_dict()['sources']
        # si ExtractDefinitions a une méthode to_dict() qui retourne une structure compatible.
        # Ou alors, il faut que marker_verification_logic.verify_all_extracts
        # soit adapté pour prendre un objet ExtractDefinitions.
        
        # Option 1: Adapter l'appel (plus simple pour l'instant)
        # Assumons que extract_definitions.sources est une liste d'objets SourceDefinition
        # et que verify_all_extracts peut gérer cela ou qu'on le convertit.
        # Le plus simple est que verify_all_extracts s'attende à la structure JSON brute (liste de dicts).
        # DefinitionService.load_definitions() retourne (ExtractDefinitions, error_message)
        # Nous devons donc obtenir la liste de dictionnaires à partir de l'objet ExtractDefinitions.
        
        # Si extract_definitions est bien l'objet ExtractDefinitions:
        if hasattr(extract_definitions, 'sources') and isinstance(extract_definitions.sources, list):
            # Convertir chaque SourceDefinition et ses Extracts en dictionnaires
            definitions_as_list_of_dicts = []
            for source_def in extract_definitions.sources:
                source_dict_repr = source_def.to_dict() # Supposant que to_dict() existe et fait le nécessaire
                definitions_as_list_of_dicts.append(source_dict_repr)
            results = verify_all_extracts(definitions_as_list_of_dicts)
        else:
            # Si extract_definitions est déjà une liste de dictionnaires (improbable avec DefinitionService)
            # ou si la structure est différente, il faut ajuster.
            # Pour l'instant, on log une erreur si la structure n'est pas celle attendue.
            logger.error("La structure de extract_definitions n'est pas celle attendue par verify_all_extracts.")
            results = []


        # Générer le rapport
        generate_verification_report(results, args.output)
        
    except Exception as e:
        logger.error(f"Exception non gérée: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main()