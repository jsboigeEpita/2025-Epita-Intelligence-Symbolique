#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour créer un fichier chiffré de test avec des extraits d'exemple.

Ce script génère un corpus d'exemple chiffré pour tester le système de déchiffrement
et de listage d'extraits. Il simule la structure d'un vrai corpus politique sans
contenu sensible.

import argumentation_analysis.core.environment
Usage:
    python scripts/utils/create_test_encrypted_extracts.py [--passphrase PASSPHRASE]
"""

import os
import sys
import json
import gzip
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any

# Ajouter le chemin vers les modules du projet
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key, encrypt_data_with_fernet
    from argumentation_analysis.paths import DATA_DIR
except ImportError as e:
    print(f"Erreur d'import: {e}")
    print("Assurez-vous d'être dans le répertoire racine du projet")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_corpus_data() -> List[Dict[str, Any]]:
    """
    Crée un corpus de test avec des extraits d'exemple.
    
    Returns:
        List[Dict]: Données du corpus de test
    """
    test_corpus = [
        {
            "source_name": "Débat présidentiel - Climat",
            "source_type": "text",
            "schema": "political_debate",
            "host_parts": ["debate", "presidential", "climate"],
            "path": "/debates/presidential/climate_2024",
            "extracts": [
                {
                    "extract_name": "Argumentation sur la transition énergétique",
                    "start_marker": "La transition énergétique",
                    "end_marker": "des solutions concrètes.",
                    "full_text": (
                        "La transition énergétique est l'un des défis majeurs de notre époque. "
                        "Certains prétendent que nous devons abandonner immédiatement toutes les "
                        "énergies fossiles, mais c'est irréaliste et dangereux pour notre économie. "
                        "D'autres affirment que le changement climatique n'est qu'une mode passagère. "
                        "En réalité, nous devons adopter une approche équilibrée qui combine "
                        "développement économique et protection environnementale avec des solutions concrètes."
                    ),
                    "metadata": {
                        "speaker": "Candidat A",
                        "topic": "transition_energetique",
                        "date": "2024-03-15",
                        "duration_seconds": 120
                    }
                },
                {
                    "extract_name": "Rhétorique de l'urgence climatique",
                    "start_marker": "Mes chers concitoyens",
                    "end_marker": "agir maintenant.",
                    "full_text": (
                        "Mes chers concitoyens, nous sommes face à une urgence absolue. "
                        "La planète brûle pendant que nos adversaires nient la réalité. "
                        "Ils sont responsables de tous nos maux environnementaux. "
                        "Avec moi, vous choisirez l'avenir de vos enfants contre les intérêts "
                        "des lobbys pollueurs. Il n'y a pas d'alternative, nous devons agir maintenant."
                    ),
                    "metadata": {
                        "speaker": "Candidat B",
                        "topic": "urgence_climatique",
                        "date": "2024-03-15",
                        "duration_seconds": 90
                    }
                }
            ]
        },
        {
            "source_name": "Discours économique - Inflation",
            "source_type": "text", 
            "schema": "political_speech",
            "host_parts": ["speech", "economic", "inflation"],
            "path": "/speeches/economic/inflation_response",
            "extracts": [
                {
                    "extract_name": "Analyse des causes de l'inflation",
                    "start_marker": "L'inflation actuelle",
                    "end_marker": "politiques appropriées.",
                    "full_text": (
                        "L'inflation actuelle trouve ses origines dans plusieurs facteurs complexes. "
                        "Il serait simpliste d'accuser uniquement la politique monétaire ou les "
                        "dépenses publiques. Les chaînes d'approvisionnement perturbées, les tensions "
                        "géopolitiques et les changements de comportement post-pandémie jouent tous "
                        "un rôle. Une analyse rigoureuse est nécessaire pour adopter les politiques appropriées."
                    ),
                    "metadata": {
                        "speaker": "Économiste gouvernemental",
                        "topic": "analyse_inflation",
                        "date": "2024-02-10",
                        "duration_seconds": 150
                    }
                },
                {
                    "extract_name": "Accusation contre l'opposition",
                    "start_marker": "C'est la faute",
                    "end_marker": "vraies solutions.",
                    "full_text": (
                        "C'est la faute de l'opposition et de leurs politiques irresponsables du passé ! "
                        "Ils ont créé ce désastre économique et maintenant ils osent nous critiquer. "
                        "Tous les experts honnêtes reconnaissent que notre gouvernement hérite d'une "
                        "situation catastrophique. Seul notre parti peut apporter de vraies solutions."
                    ),
                    "metadata": {
                        "speaker": "Ministre de l'Économie",
                        "topic": "blame_opposition",
                        "date": "2024-02-12",
                        "duration_seconds": 75
                    }
                }
            ]
        },
        {
            "source_name": "Débat santé publique",
            "source_type": "text",
            "schema": "parliamentary_debate", 
            "host_parts": ["parliament", "health", "public"],
            "path": "/debates/parliament/health_system",
            "extracts": [
                {
                    "extract_name": "Réforme du système de santé",
                    "start_marker": "Notre système de santé",
                    "end_marker": "tous les citoyens.",
                    "full_text": (
                        "Notre système de santé nécessite des réformes profondes mais réfléchies. "
                        "Il ne s'agit pas de tout détruire ni de maintenir le statu quo. "
                        "Nous devons identifier les dysfonctionnements réels, écouter les professionnels "
                        "de santé, analyser les expériences internationales et proposer des solutions "
                        "graduelles qui amélioreront concrètement la prise en charge de tous les citoyens."
                    ),
                    "metadata": {
                        "speaker": "Rapporteur de la commission",
                        "topic": "reforme_sante",
                        "date": "2024-01-25",
                        "duration_seconds": 180
                    }
                },
                {
                    "extract_name": "Attaque ad hominem sur la santé",
                    "start_marker": "Le ministre de la santé",
                    "end_marker": "incompétence totale.",
                    "full_text": (
                        "Le ministre de la santé n'a jamais travaillé dans un hôpital de sa vie ! "
                        "Comment peut-il comprendre les vrais problèmes des soignants ? "
                        "Sa formation d'énarque ne lui donne aucune légitimité pour parler de médecine. "
                        "C'est un technocrate déconnecté qui montre une incompétence totale."
                    ),
                    "metadata": {
                        "speaker": "Député d'opposition",
                        "topic": "attaque_ministre",
                        "date": "2024-01-26",
                        "duration_seconds": 60
                    }
                }
            ]
        }
    ]
    
    return test_corpus

def create_encrypted_test_file(passphrase: str, output_path: Path) -> bool:
    """
    Crée un fichier chiffré de test.
    
    Args:
        passphrase: Phrase secrète pour le chiffrement
        output_path: Chemin du fichier de sortie
        
    Returns:
        bool: True si succès, False sinon
    """
    logger.info("Création du corpus de test...")
    
    try:
        # Générer les données de test
        test_data = create_test_corpus_data()
        
        # Convertir en JSON
        json_data = json.dumps(test_data, ensure_ascii=False, indent=2)
        logger.info(f"Corpus généré: {len(test_data)} sources")
        
        # Compresser
        compressed_data = gzip.compress(json_data.encode('utf-8'))
        logger.info(f"Données compressées: {len(compressed_data)} octets")
        
        # Chiffrer
        encryption_key = load_encryption_key(passphrase_arg=passphrase)
        if not encryption_key:
            logger.error("Impossible de dériver la clé de chiffrement")
            return False
        
        encrypted_data = encrypt_data_with_fernet(compressed_data, encryption_key)
        if not encrypted_data:
            logger.error("Échec du chiffrement")
            return False
        
        logger.info(f"Données chiffrées: {len(encrypted_data)} octets")
        
        # Sauvegarder
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        logger.info(f"Fichier chiffré créé: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du fichier chiffré: {e}")
        return False

def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Crée un fichier chiffré de test avec des extraits d'exemple"
    )
    
    parser.add_argument(
        "--passphrase",
        type=str,
        default="Propaganda",
        help="Phrase secrète pour le chiffrement (défaut: Propaganda)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Chemin de sortie (défaut: extract_sources.json.gz.enc dans DATA_DIR)"
    )
    
    args = parser.parse_args()
    
    # Déterminer le chemin de sortie
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = DATA_DIR / "extract_sources.json.gz.enc"
    
    # Créer une sauvegarde si le fichier existe
    if output_path.exists():
        backup_path = output_path.with_suffix('.enc.backup')
        logger.info(f"Sauvegarde du fichier existant: {backup_path}")
        output_path.rename(backup_path)
    
    # Créer le fichier chiffré de test
    success = create_encrypted_test_file(args.passphrase, output_path)
    
    if success:
        logger.info("Fichier de test créé avec succès !")
        logger.info(f"Vous pouvez maintenant tester avec:")
        logger.info(f"python scripts/utils/list_encrypted_extracts.py --passphrase '{args.passphrase}'")
        return 0
    else:
        logger.error("Échec de la création du fichier de test")
        return 1

if __name__ == "__main__":
    sys.exit(main())