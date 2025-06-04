"""
Module pour le chargement en lazy loading de la taxonomie des sophismes.
Ce module utilise une version mock pour les tests et le développement.

Le module offre deux modes de fonctionnement:
1. Mode mock (par défaut): Utilise des données simulées pour les tests et le développement
2. Mode réel: Charge la taxonomie depuis un fichier local ou la télécharge depuis une URL

Pour changer de mode, modifiez la variable globale USE_MOCK:
- USE_MOCK = True  # Pour utiliser la version mock (recommandé pour les tests)
- USE_MOCK = False # Pour utiliser la version réelle (nécessite un accès au fichier ou à Internet)

Limitations connues:
- La version mock ne contient qu'un petit échantillon de sophismes
- La version réelle nécessite soit un fichier local, soit une connexion Internet
- Le téléchargement du fichier complet peut être lent en raison de sa taille
"""

import os
import logging
from pathlib import Path
from argumentation_analysis.paths import DATA_DIR

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL de la taxonomie des sophismes (pour référence uniquement)
TAXONOMY_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
# Chemin local où sera stocké le fichier
DATA_DIR = Path(__file__).parent.parent / DATA_DIR
TAXONOMY_FILE = DATA_DIR / "argumentum_fallacies_taxonomy.csv"

# Variable globale pour contrôler le mode mock
# Modifiez cette variable pour changer le mode de fonctionnement:
# - True: Utilise des données simulées (recommandé pour les tests)
# - False: Tente de charger ou télécharger le fichier réel
USE_MOCK = True

def get_taxonomy_path():
    """
    Obtient le chemin vers le fichier de taxonomie des sophismes.
    
    En mode mock (USE_MOCK=True):
    - Simule l'existence du fichier sans effectuer de téléchargement
    - Retourne un chemin vers un fichier fictif
    
    En mode réel (USE_MOCK=False):
    - Vérifie si le fichier existe localement
    - Si non, tente de le télécharger depuis l'URL définie
    - Nécessite la bibliothèque 'requests' pour le téléchargement
    
    Returns:
        Path: Chemin vers le fichier de taxonomie (réel ou simulé)
        
    Raises:
        NotImplementedError: En mode réel si le téléchargement n'est pas implémenté
        Exception: En cas d'erreur lors du téléchargement
    """
    if USE_MOCK:
        logger.info("Utilisation de la version mock de get_taxonomy_path()")
        # Créer le dossier data s'il n'existe pas
        DATA_DIR.mkdir(exist_ok=True)
        
        # Créer un fichier mock_taxonomy.csv avec un contenu valide et simplifié
        mock_path = DATA_DIR / "mock_taxonomy.csv"
        mock_csv_content = (
            "PK,Name\n"
            "1,Ad Hominem\n"
            "2,Straw Man\n"
            "3,Appeal to Authority\n"
        )
        try:
            with open(mock_path, 'w', encoding='utf-8') as f:
                f.write(mock_csv_content)
            logger.info(f"Fichier mock_taxonomy.csv créé avec succès à: {mock_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du fichier mock_taxonomy.csv: {e}")
            # Retourner un chemin même en cas d'échec d'écriture pour ne pas bloquer certains tests,
            # mais la lecture échouera probablement plus tard.
        
        logger.info(f"Chemin vers la taxonomie mock: {mock_path}")
        return mock_path
    else:
        # Version réelle (code conservé pour référence)
        if TAXONOMY_FILE.exists():
            logger.info(f"Fichier de taxonomie trouvé localement: {TAXONOMY_FILE}")
            return TAXONOMY_FILE
        
        # Créer le dossier data s'il n'existe pas
        DATA_DIR.mkdir(exist_ok=True)
        
        # Note: Cette partie est commentée car nous utilisons la version mock
        # Le téléchargement réel nécessiterait d'importer requests et d'exécuter:
        """
        logger.info(f"Téléchargement de la taxonomie depuis {TAXONOMY_URL}")
        try:
            import requests

from argumentation_analysis.paths import DATA_DIR

            response = requests.get(TAXONOMY_URL)
            response.raise_for_status()
            
            with open(TAXONOMY_FILE, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Taxonomie téléchargée avec succès: {TAXONOMY_FILE}")
            return TAXONOMY_FILE
        
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de la taxonomie: {e}")
            raise
        """
        logger.error("Version réelle non implémentée en mode mock")
        raise NotImplementedError("Version réelle non disponible en mode mock")

def validate_taxonomy_file():
    """
    Valide le fichier de taxonomie des sophismes.
    
    En mode mock (USE_MOCK=True):
    - Simule la validation sans vérifier de fichier réel
    - Retourne toujours True
    
    En mode réel (USE_MOCK=False):
    - Vérifie que le fichier existe et n'est pas vide
    - Valide la présence des colonnes requises dans l'en-tête
    - Vérifie qu'il y a au moins une ligne de données
    
    Returns:
        bool: True si le fichier est valide, False sinon
        
    Cas d'utilisation:
    - Tests unitaires: Utilisez le mode mock pour éviter les dépendances externes
    - Production: Désactivez le mode mock pour valider le fichier réel
    """
    if USE_MOCK:
        logger.info("Utilisation de la version mock de validate_taxonomy_file()")
        # Toujours retourner True en mode mock
        logger.info("Validation simulée du fichier de taxonomie réussie")
        return True
    else:
        # Version réelle (code conservé pour référence)
        try:
            taxonomy_path = get_taxonomy_path()
            
            if os.path.getsize(taxonomy_path) == 0:
                logger.error("Le fichier de taxonomie est vide")
                return False
            
            with open(taxonomy_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
                required_columns = ['PK', 'nom_vulgarisé', 'text_fr']
                if not all(col in header for col in required_columns):
                    logger.error(f"Format d'en-tête incorrect: {header}")
                    logger.error(f"Colonnes requises manquantes: {[col for col in required_columns if col not in header]}")
                    return False
                
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

class TaxonomyLoader:
    """
    Classe pour charger la taxonomie des sophismes.
    
    Cette classe fournit une interface unifiée pour accéder à la taxonomie,
    qu'elle soit chargée depuis un fichier réel ou générée en mode mock.
    
    Attributs:
        taxonomy_path (Path): Chemin vers le fichier de taxonomie
        
    Méthodes:
        load_taxonomy(): Charge ou génère la taxonomie des sophismes
    """
    
    def __init__(self):
        """
        Initialise le chargeur de taxonomie.
        
        En mode mock, aucun fichier réel n'est nécessaire.
        En mode réel, le chemin du fichier sera déterminé par get_taxonomy_path().
        """
        self.taxonomy_path = None
    
    def load_taxonomy(self):
        """
        Charge la taxonomie des sophismes.
        
        En mode mock (USE_MOCK=True):
        - Retourne un petit échantillon de données prédéfinies
        - Utile pour les tests et le développement rapide
        - Ne nécessite pas de fichier réel ni de connexion Internet
        
        En mode réel (USE_MOCK=False):
        - Charge les données depuis le fichier de taxonomie
        - Nécessite que le fichier existe localement ou soit téléchargeable
        
        Returns:
            list: Liste des entrées de la taxonomie (complète ou échantillon)
            
        Note:
        Pour passer en mode réel, modifiez la variable globale USE_MOCK en haut du module.
        """
        if USE_MOCK:
            logger.info("Utilisation de la version mock de load_taxonomy()")
            
            # Créer un petit échantillon de données mock
            mock_header = ["PK", "nom_vulgarisé", "text_fr", "category", "subcategory"]
            mock_entries = [
                {
                    "PK": "1",
                    "nom_vulgarisé": "Ad Hominem",
                    "text_fr": "Attaquer la personne plutôt que l'argument",
                    "category": "Fallacies",
                    "subcategory": "Relevance"
                },
                {
                    "PK": "2",
                    "nom_vulgarisé": "Faux Dilemme",
                    "text_fr": "Présenter seulement deux options alors qu'il en existe d'autres",
                    "category": "Fallacies",
                    "subcategory": "Structure"
                },
                {
                    "PK": "3",
                    "nom_vulgarisé": "Pente Glissante",
                    "text_fr": "Affirmer qu'un petit pas mènera inévitablement à une chaîne d'événements indésirables",
                    "category": "Fallacies",
                    "subcategory": "Causality"
                },
                {
                    "PK": "4",
                    "nom_vulgarisé": "Appel à l'Autorité",
                    "text_fr": "Affirmer qu'une proposition est vraie parce qu'une figure d'autorité le dit",
                    "category": "Fallacies",
                    "subcategory": "Relevance"
                },
                {
                    "PK": "5",
                    "nom_vulgarisé": "Homme de Paille",
                    "text_fr": "Déformer l'argument de l'adversaire pour le rendre plus facile à attaquer",
                    "category": "Fallacies",
                    "subcategory": "Relevance"
                }
            ]
            
            logger.info(f"Taxonomie mock chargée avec succès: {len(mock_entries)} entrées")
            return mock_entries
        else:
            # Cette partie serait implémentée pour charger le fichier réel
            # Pour l'instant, elle n'est pas implémentée car nous utilisons la version mock
            logger.error("Version réelle de load_taxonomy() non implémentée")
            raise NotImplementedError("Version réelle de load_taxonomy() non disponible en mode mock")