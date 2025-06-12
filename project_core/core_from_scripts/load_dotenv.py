#!/usr/bin/env python3
"""
Chargeur de fichier .env pour le projet
======================================

Module pour charger automatiquement le fichier .env du projet.
Fallback gracieux si python-dotenv n'est pas disponible.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
from pathlib import Path


def find_dotenv_file(start_path: str = None) -> str:
    """
    Trouve le fichier .env en remontant dans l'arborescence
    
    Args:
        start_path: Chemin de départ (défaut: répertoire du script)
    
    Returns:
        Chemin vers le fichier .env ou None
    """
    if start_path is None:
        if '__file__' in globals():
            start_path = Path(__file__).parent.parent.parent.absolute()
        else:
            start_path = Path.cwd()
    else:
        start_path = Path(start_path)
    
    # Recherche du .env en remontant
    current = start_path
    for _ in range(10):  # Limite la recherche
        dotenv_path = current / '.env'
        if dotenv_path.exists():
            return str(dotenv_path)
        
        parent = current.parent
        if parent == current:  # Racine atteinte
            break
        current = parent
    
    return None


def load_dotenv_simple(dotenv_path: str) -> bool:
    """
    Charge le fichier .env manuellement (fallback sans python-dotenv)
    
    Args:
        dotenv_path: Chemin vers le fichier .env
    
    Returns:
        True si chargé avec succès
    """
    try:
        with open(dotenv_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Ignorer commentaires et lignes vides
                if not line or line.startswith('#'):
                    continue
                
                # Parser KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Enlever guillemets si présents
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # Définir la variable d'environnement si pas déjà définie
                    if key and key not in os.environ:
                        os.environ[key] = value
        
        return True
        
    except Exception as e:
        print(f"[WARN] Erreur chargement .env simple: {e}")
        return False


def load_dotenv_advanced(dotenv_path: str) -> bool:
    """
    Charge le fichier .env avec python-dotenv si disponible
    
    Args:
        dotenv_path: Chemin vers le fichier .env
    
    Returns:
        True si chargé avec succès
    """
    try:
        from dotenv import load_dotenv
        return load_dotenv(dotenv_path, override=False)
    except ImportError:
        # Fallback vers le chargeur simple
        return load_dotenv_simple(dotenv_path)


def ensure_dotenv_loaded(start_path: str = None, silent: bool = True) -> bool:
    """
    S'assure que le fichier .env est chargé
    
    Args:
        start_path: Chemin de départ pour la recherche
        silent: Mode silencieux
    
    Returns:
        True si .env trouvé et chargé
    """
    # Chercher le fichier .env
    dotenv_path = find_dotenv_file(start_path)
    
    if not dotenv_path:
        if not silent:
            print("[WARN] Fichier .env non trouvé")
        return False
    
    # Charger le .env
    success = load_dotenv_advanced(dotenv_path)
    
    if success and not silent:
        print(f"[OK] Fichier .env chargé: {dotenv_path}")
    elif not success and not silent:
        print(f"[WARN] Échec chargement .env: {dotenv_path}")
    
    return success


# Auto-exécution à l'import
if __name__ != "__main__":
    # Le module est importé, chargement automatique
    ensure_dotenv_loaded()


if __name__ == "__main__":
    # Test direct
    print("[TEST] Chargeur .env")
    print("=" * 40)
    
    # Test de recherche
    dotenv_path = find_dotenv_file()
    if dotenv_path:
        print(f"[OK] .env trouvé: {dotenv_path}")
        
        # Test de chargement
        success = ensure_dotenv_loaded(silent=False)
        if success:
            print("[OK] .env chargé avec succès")
            
            # Afficher quelques variables
            test_vars = ['OPENAI_API_KEY', 'GLOBAL_LLM_SERVICE', 'PROJECT_ROOT']
            for var in test_vars:
                value = os.environ.get(var)
                if value:
                    # Masquer les clés sensibles
                    if 'KEY' in var and len(value) > 10:
                        display_value = value[:10] + "..."
                    else:
                        display_value = value
                    print(f"[VAR] {var}={display_value}")
        else:
            print("[ERROR] Échec chargement .env")
    else:
        print("[ERROR] .env non trouvé")