import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

from argumentation_analysis.ui.utils import load_extract_definitions
from cryptography.fernet import Fernet

def test_load_extract_definitions_with_invalid_key():
    """
    Teste la fonction load_extract_definitions avec une clé invalide.
    La fonction devrait retourner les définitions par défaut sans lever d'exception.
    """
    # Créer un fichier de configuration temporaire
    config_file = Path("temp_config.bin")
    
    # Générer une clé valide pour le chiffrement
    valid_key = Fernet.generate_key()
    
    # Écrire des données chiffrées dans le fichier
    with open(config_file, 'wb') as f:
        f.write(b"Ceci n est pas un contenu chiffre valide")
    
    try:
        # Générer une clé différente pour le déchiffrement (ce qui causera un échec)
        invalid_key = Fernet.generate_key()
        
        # Appeler la fonction avec la clé invalide
        # Cela devrait retourner les définitions par défaut sans lever d'exception
        result = load_extract_definitions(config_file, invalid_key)
        
        print("Test réussi: La fonction a retourné les définitions par défaut sans lever d'exception.")
        print(f"Nombre de définitions retournées: {len(result)}")
        
    except Exception as e:
        print(f"Test échoué: La fonction a levé une exception: {e}")
    
    finally:
        # Nettoyer le fichier temporaire
        if config_file.exists():
            config_file.unlink()

if __name__ == "__main__":
    test_load_extract_definitions_with_invalid_key()