#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour démontrer la sélection d'extraits du corpus chiffré.
Permet de choisir un extrait au hasard ou par son index.
"""

import os
import sys
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au sys.path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_corpus_selection():
    """
    Teste la sélection d'extraits depuis le corpus chiffré.
    """
    try:
        # 1. Import des modules nécessaires
        from argumentation_analysis.utils.debug_utils import display_extract_sources_details
        from scripts.data_processing.decrypt_extracts import decrypt_and_load_extracts
        from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key
        
        logger.info("=== Test de sélection d'extraits du corpus chiffré ===")
        
        # 2. Charger la clé de chiffrement
        encryption_key = os.getenv("TEXT_CONFIG_PASSPHRASE")
        if not encryption_key:
            logger.error("Variable d'environnement TEXT_CONFIG_PASSPHRASE requise")
            return
        
        # 3. Déchiffrer et charger les extraits
        logger.info("Déchiffrement du corpus...")
        extract_definitions, status_message = decrypt_and_load_extracts(encryption_key)
        
        if not extract_definitions:
            logger.error(f"Impossible de charger les extraits: {status_message}")
            return
        
        logger.info(f"✅ {len(extract_definitions)} sources chargées")
        
        # 4. Compter le nombre total d'extraits
        total_extracts = 0
        extract_index_map = {}  # Pour mapper les indices globaux aux extraits
        
        for source_idx, source in enumerate(extract_definitions):
            source_name = source.get("source_name", f"Source_{source_idx}")
            extracts = source.get("extracts", [])
            
            for extract_idx, extract in enumerate(extracts):
                extract_name = extract.get("extract_name", f"Extract_{extract_idx}")
                global_index = total_extracts
                extract_index_map[global_index] = {
                    "source_idx": source_idx,
                    "extract_idx": extract_idx,
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "source": source,
                    "extract": extract
                }
                total_extracts += 1
        
        logger.info(f"📊 Total d'extraits disponibles: {total_extracts}")
        
        # 5. Test de sélection aléatoire
        logger.info("\n--- 🎲 SÉLECTION ALÉATOIRE ---")
        if total_extracts > 0:
            random_index = random.randint(0, total_extracts - 1)
            random_extract_info = extract_index_map[random_index]
            
            logger.info(f"🎯 Extrait sélectionné aléatoirement (index {random_index}):")
            logger.info(f"   Source: {random_extract_info['source_name']}")
            logger.info(f"   Extrait: {random_extract_info['extract_name']}")
            
            # Afficher le début du contenu s'il existe
            extract = random_extract_info['extract']
            start_marker = extract.get('start_marker', '')
            end_marker = extract.get('end_marker', '')
            if start_marker:
                preview = start_marker[:100] + "..." if len(start_marker) > 100 else start_marker
                logger.info(f"   Début: {preview}")
        
        # 6. Test de sélection par index
        logger.info("\n--- 🔢 SÉLECTION PAR INDEX ---")
        test_indices = [0, total_extracts // 2, total_extracts - 1] if total_extracts > 0 else []
        
        for test_index in test_indices:
            if test_index < total_extracts:
                extract_info = extract_index_map[test_index]
                logger.info(f"📌 Index {test_index}:")
                logger.info(f"   Source: {extract_info['source_name']}")
                logger.info(f"   Extrait: {extract_info['extract_name']}")
        
        # 7. Afficher la liste des premières sources pour contexte
        logger.info("\n--- 📚 APERÇU DES SOURCES ---")
        display_extract_sources_details(
            extract_sources_data=extract_definitions[:3],  # Afficher seulement les 3 premières
            show_all=False
        )
        
        # 8. Proposer une commande de test interactive
        logger.info("\n--- 🛠 COMMANDES DE TEST ---")
        logger.info("Pour une inspection interactive, utilisez :")
        logger.info(f"  python scripts/data_processing/debug_inspect_extract_sources.py --all-french")
        logger.info(f"  python scripts/data_processing/debug_inspect_extract_sources.py --source-id=0")
        logger.info(f"  python scripts/data_processing/decrypt_extracts.py --verbose")
        
        return True
        
    except ImportError as e:
        logger.error(f"Erreur d'import: {e}")
        logger.error("Assurez-vous d'avoir activé l'environnement du projet")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False

def create_extract_selector_utility():
    """
    Crée un utilitaire simple pour sélectionner des extraits.
    """
    utility_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire simple pour sélectionner des extraits du corpus.
Usage: python select_extract.py [--random] [--index N] [--list]
"""

import argparse
import random
import sys
from pathlib import Path

# Ajouter le projet au sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    parser = argparse.ArgumentParser(description="Sélectionner un extrait du corpus")
    parser.add_argument("--random", action="store_true", help="Sélection aléatoire")
    parser.add_argument("--index", type=int, help="Sélection par index")
    parser.add_argument("--list", action="store_true", help="Lister tous les extraits")
    
    args = parser.parse_args()
    
    # Import des fonctions nécessaires
    from scripts.data_processing.decrypt_extracts import decrypt_and_load_extracts
    import os
    
    # Charger les extraits
    encryption_key = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not encryption_key:
        print("❌ Variable TEXT_CONFIG_PASSPHRASE requise")
        return 1
    
    extracts, status = decrypt_and_load_extracts(encryption_key)
    if not extracts:
        print(f"❌ {status}")
        return 1
    
    # Créer l'index des extraits
    all_extracts = []
    for source in extracts:
        for extract in source.get("extracts", []):
            all_extracts.append({
                "source": source.get("source_name", "Unknown"),
                "extract": extract.get("extract_name", "Unknown"),
                "start": extract.get("start_marker", "")[:50]
            })
    
    if args.list:
        print(f"📚 {len(all_extracts)} extraits disponibles:")
        for i, ext in enumerate(all_extracts):
            print(f"  {i:3d}: {ext['source']} → {ext['extract']}")
    elif args.random:
        if all_extracts:
            selected = random.choice(all_extracts)
            print(f"🎲 Sélection aléatoire:")
            print(f"   Source: {selected['source']}")
            print(f"   Extrait: {selected['extract']}")
    elif args.index is not None:
        if 0 <= args.index < len(all_extracts):
            selected = all_extracts[args.index]
            print(f"🔢 Index {args.index}:")
            print(f"   Source: {selected['source']}")
            print(f"   Extrait: {selected['extract']}")
        else:
            print(f"❌ Index {args.index} invalide (0-{len(all_extracts)-1})")
    else:
        print("Usage: python select_extract.py [--random] [--index N] [--list]")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    with open("select_extract.py", "w", encoding="utf-8") as f:
        f.write(utility_content)
    
    logger.info("✅ Utilitaire 'select_extract.py' créé")

if __name__ == "__main__":
    # Créer l'utilitaire simple
    create_extract_selector_utility()
    
    # Tester la sélection
    success = test_corpus_selection()
    
    if success:
        logger.info("\n✅ Test terminé avec succès!")
        logger.info("💡 Utilisez './activate_project_env.ps1' puis 'python select_extract.py --help'")
    else:
        logger.error("\n❌ Test échoué")
        sys.exit(1)