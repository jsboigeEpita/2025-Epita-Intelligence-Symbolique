"""
Script pour mettre à jour le fichier chiffré extract_sources.json.gz.enc
à partir du fichier JSON corrigé extract_sources_updated.json
"""

import json
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(str(Path(__file__).parent.parent))

# Importer les modules nécessaires
from argumentation_analysis.core.io_manager import save_extract_definitions
from argumentation_analysis.ui import config as ui_config

def update_encrypted_config():
    """
    Met à jour le fichier chiffré extract_sources.json.gz.enc
    à partir du fichier JSON corrigé extract_sources_updated.json
    """
    # Chemin vers le fichier JSON corrigé
    json_file_path = Path(__file__).parent / "extract_repair" / "docs" / "extract_sources_updated.json"
    
    # Vérifier si le fichier JSON corrigé existe
    if not json_file_path.exists():
        print(f"❌ Erreur: Le fichier JSON corrigé '{json_file_path}' n'existe pas.")
        return False
    
    # Vérifier si la clé de chiffrement est disponible
    if not ui_config.ENCRYPTION_KEY:
        print(f"❌ Erreur: La clé de chiffrement n'est pas disponible. Vérifiez la variable d'environnement '{ui_config.PASSPHRASE_VAR_NAME}'.")
        return False
    
    try:
        # Lire le contenu du fichier JSON corrigé
        with open(json_file_path, 'r', encoding='utf-8') as f:
            definitions = json.load(f)
        
        print(f"[OK] Fichier JSON corrigé '{json_file_path}' chargé avec succès.")
        print(f"   - {len(definitions)} sources trouvées.")
        
        # Sauvegarder les définitions dans le fichier chiffré
        success = save_extract_definitions(definitions, ui_config.CONFIG_FILE_ENC, ui_config.ENCRYPTION_KEY)
        
        if success:
            print(f"[OK] Fichier chiffré '{ui_config.CONFIG_FILE_ENC}' mis à jour avec succès.")
            return True
        else:
            print(f"❌ Erreur: Échec de la mise à jour du fichier chiffré '{ui_config.CONFIG_FILE_ENC}'.")
            return False
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Mise à jour du fichier chiffré extract_sources.json.gz.enc ===\n")
    
    # Vérifier si la variable d'environnement TEXT_CONFIG_PASSPHRASE est définie
    if not os.getenv(ui_config.PASSPHRASE_VAR_NAME):
        print(f"⚠️ La variable d'environnement '{ui_config.PASSPHRASE_VAR_NAME}' n'est pas définie.")
        print(f"   Veuillez la définir avant d'exécuter ce script.")
        sys.exit(1)
    
    # Mettre à jour le fichier chiffré
    success = update_encrypted_config()
    
    # Vérifier que le fichier chiffré a bien été mis à jour
    if success:
        print("\n=== Vérification du fichier chiffré ===\n")
        
        # Vérifier que le fichier chiffré existe
        if ui_config.CONFIG_FILE_ENC.exists():
            print(f"[OK] Le fichier chiffré '{ui_config.CONFIG_FILE_ENC}' existe.")
            print(f"   - Taille: {ui_config.CONFIG_FILE_ENC.stat().st_size} octets")
            print("\n[OK] Mise à jour réussie !")
        else:
            print(f"❌ Erreur: Le fichier chiffré '{ui_config.CONFIG_FILE_ENC}' n'existe pas.")
            print("\n❌ Échec de la mise à jour.")
    else:
        print("\n❌ Échec de la mise à jour.")
    
    sys.exit(0 if success else 1)