#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaires pour la gestion des fichiers.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configuration d'un logger pour ce module.
# Les applications utilisant ces utilitaires peuvent le reconfigurer.
logger = logging.getLogger(__name__)
if not logger.handlers:  # Évite d'ajouter plusieurs handlers si le module est rechargé
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def load_json_data(file_path: Path) -> Optional[List[Dict[str, Any]]]:
    """
    Charge des données depuis un fichier JSON.

    Args:
        file_path (Path): Chemin vers le fichier JSON.

    Returns:
        Optional[List[Dict[str, Any]]]: Liste de dictionnaires si le chargement réussit,
                                         None sinon.
    """
    logger.info(f"Chargement des données JSON depuis {file_path}")
    
    if not file_path.exists():
        logger.error(f"❌ Le fichier {file_path} n'existe pas.")
        return None
    
    if not file_path.is_file():
        logger.error(f"❌ Le chemin {file_path} n'est pas un fichier.")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.warning(f"⚠️ Les données dans {file_path} ne sont pas une liste JSON. Type trouvé: {type(data)}")
            # Selon le cas d'usage, on pourrait vouloir retourner data ou None/[]
            # Pour l'instant, on s'attend à une liste d'objets (dictionnaires)
            # Si ce n'est pas une liste, on considère que ce n'est pas le format attendu.
            # Cependant, pour être plus flexible, on pourrait retourner data et laisser l'appelant gérer.
            # Pour l'instant, on retourne None si ce n'est pas une liste.
            # Si le fichier JSON contient un seul objet au lieu d'une liste,
            # on pourrait vouloir le retourner encapsulé dans une liste: return [data]
            # Mais cela dépend des attentes des appelants.
            # Pour l'instant, on est strict sur le format attendu (liste de dictionnaires).
            # Si le fichier est vide ou contient `null`, json.load peut retourner None.
            if data is None:
                 logger.warning(f"Le fichier JSON {file_path} est vide ou contient 'null'.")
                 return [] # Retourner une liste vide pour un JSON null ou vide.

        logger.info(f"✅ {len(data) if isinstance(data, list) else 1} élément(s) chargé(s) avec succès depuis {file_path}.")
        return data # Retourne les données telles quelles, l'appelant vérifiera le type si besoin.
    except json.JSONDecodeError as e:
        logger.error(f"❌ Erreur de décodage JSON dans {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement de {file_path}: {e}")
        return None

# Exemple d'utilisation (peut être retiré ou mis sous if __name__ == "__main__")
# if __name__ == '__main__':
#     # Créer un fichier JSON de test
#     test_dir = Path("temp_test_json_data")
#     test_dir.mkdir(exist_ok=True)
#     test_file_path = test_dir / "test_data.json"
#     sample_data = [{"id": 1, "name": "Test"}, {"id": 2, "name": "Autre Test"}]
    
#     with open(test_file_path, 'w', encoding='utf-8') as f:
#         json.dump(sample_data, f, indent=2)
        
#     loaded_data = load_json_data(test_file_path)
    
#     if loaded_data:
#         logger.info(f"Données chargées avec succès: {loaded_data}")
#     else:
#         logger.error("Échec du chargement des données.")
    
#     # Nettoyer
#     # test_file_path.unlink()
#     # test_dir.rmdir()