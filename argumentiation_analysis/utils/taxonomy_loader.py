"""
Module pour le chargement en lazy loading de la taxonomie des sophismes.
Ce module télécharge la taxonomie uniquement lorsqu'elle est sollicitée.
"""

import os
import requests
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL de la taxonomie des sophismes
TAXONOMY_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
# Chemin local où sera stocké le fichier
DATA_DIR = Path(__file__).parent.parent / "data"
TAXONOMY_FILE = DATA_DIR / "argumentum_fallacies_taxonomy.csv"

def get_taxonomy_path():
    """
    Vérifie si le fichier de taxonomie existe localement.
    S'il n'existe pas, le télécharge depuis l'URL GitHub.
    
    Returns:
        Path: Chemin vers le fichier de taxonomie
    """
    # Vérifier si le fichier existe déjà
    if TAXONOMY_FILE.exists():
        logger.info(f"Fichier de taxonomie trouvé localement: {TAXONOMY_FILE}")
        return TAXONOMY_FILE
    
    # Créer le dossier data s'il n'existe pas
    DATA_DIR.mkdir(exist_ok=True)
    
    # Télécharger le fichier
    logger.info(f"Téléchargement de la taxonomie depuis {TAXONOMY_URL}")
    try:
        response = requests.get(TAXONOMY_URL)
        response.raise_for_status()  # Lever une exception si la requête a échoué
        
        # Sauvegarder le contenu dans le fichier local
        with open(TAXONOMY_FILE, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Taxonomie téléchargée avec succès: {TAXONOMY_FILE}")
        return TAXONOMY_FILE
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors du téléchargement de la taxonomie: {e}")
        raise

def validate_taxonomy_file():
    """
    Vérifie que le fichier de taxonomie est correctement formaté.
    
    Returns:
        bool: True si le fichier est valide, False sinon
    """
    try:
        # S'assurer que le fichier existe
        taxonomy_path = get_taxonomy_path()
        
        # Vérifier que le fichier n'est pas vide
        if os.path.getsize(taxonomy_path) == 0:
            logger.error("Le fichier de taxonomie est vide")
            return False
        
        # Lire les premières lignes pour vérifier le format
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
            # Vérifier que l'en-tête contient les colonnes attendues pour la taxonomie Argumentum
            required_columns = ['PK', 'nom_vulgarisé', 'text_fr']
            if not all(col in header for col in required_columns):
                logger.error(f"Format d'en-tête incorrect: {header}")
                logger.error(f"Colonnes requises manquantes: {[col for col in required_columns if col not in header]}")
                return False
            
            # Vérifier qu'il y a au moins une ligne de données
            data_line = f.readline().strip()
            if not data_line:
                logger.error("Aucune donnée trouvée dans le fichier")
                return False
        
        logger.info("Validation du fichier de taxonomie réussie")
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la validation du fichier de taxonomie: {e}")
        return False

if __name__ == "__main__":
    # Test du module
    try:
        taxonomy_path = get_taxonomy_path()
        print(f"Chemin vers la taxonomie: {taxonomy_path}")
        
        is_valid = validate_taxonomy_file()
        print(f"Fichier valide: {is_valid}")
    except Exception as e:
        print(f"Erreur: {e}")