#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour récupérer directement le discours du Kremlin et le mettre en cache.
"""

import os
import sys
import hashlib
import requests
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))  # Ajouter le répertoire parent

# Charger les variables d'environnement
load_dotenv(override=True)

# Définir les constantes
CACHE_DIR = parent_dir / "text_cache"
CACHE_DIR.mkdir(exist_ok=True, parents=True)

def get_cache_filepath(url):
    """Génère le chemin du fichier cache pour une URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return CACHE_DIR / f"{url_hash}.txt"

def load_from_cache(url):
    """Charge le contenu textuel depuis le cache si disponible."""
    filepath = get_cache_filepath(url)
    if filepath.exists():
        try:
            print(f"   -> Lecture depuis cache : {filepath.name}")
            return filepath.read_text(encoding='utf-8')
        except Exception as e:
            print(f"   -> Erreur lecture cache {filepath.name}: {e}")
            return None
    print(f"Cache miss pour URL: {url}")
    return None

def save_to_cache(url, text):
    """Sauvegarde le contenu textuel dans le cache."""
    if not text:
        print("   -> Texte vide, non sauvegardé.")
        return
    filepath = get_cache_filepath(url)
    try:
        # S'assurer que le dossier cache existe
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding='utf-8')
        print(f"   -> Texte sauvegardé : {filepath.name}")
    except Exception as e:
        print(f"   -> Erreur sauvegarde cache {filepath.name}: {e}")

def fetch_direct_text(url, timeout=60):
    """Récupère contenu texte brut d'URL, utilise cache fichier."""
    print(f"-> Téléchargement direct depuis : {url}...")
    headers = {'User-Agent': 'ArgumentAnalysisApp/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        texte_brut = response.content.decode('utf-8', errors='ignore')
        print(f"   -> Contenu direct récupéré (longueur {len(texte_brut)}).")
        save_to_cache(url, texte_brut)
        return texte_brut
    except requests.exceptions.RequestException as e:
        print(f"Erreur téléchargement direct ({url}): {e}")
        raise ConnectionError(f"Erreur téléchargement direct ({url}): {e}") from e

def main():
    """Fonction principale."""
    print("\n=== Récupération du discours du Kremlin ===\n")
    
    # URL du discours du Kremlin
    kremlin_url = "http://en.kremlin.ru/events/president/transcripts/67828"
    
    # Vérifier si le texte est déjà dans le cache
    cache_path = get_cache_filepath(kremlin_url)
    cached_text = load_from_cache(kremlin_url)
    
    if cached_text is not None:
        print(f"✅ Discours du Kremlin déjà en cache : {cache_path}")
        print(f"   Longueur : {len(cached_text)} caractères")
        print(f"   Hash de l'URL : {cache_path.name}")
        return
    
    # Récupérer le discours du Kremlin
    print(f"⏳ Récupération du discours du Kremlin depuis {kremlin_url}...")
    try:
        kremlin_text = fetch_direct_text(kremlin_url)
        
        if kremlin_text:
            print(f"✅ Discours du Kremlin récupéré ({len(kremlin_text)} caractères)")
            print(f"   Sauvegardé dans : {cache_path}")
            print(f"   Hash de l'URL : {cache_path.name}")
            
            # Créer un fichier spécifique pour le test d'orchestration
            specific_cache_path = CACHE_DIR / "4cf2d4853745719f6504a54610237738ad016de4f64176c3e8f5218f8fd2c01b.txt"
            specific_cache_path.write_text(kremlin_text, encoding='utf-8')
            print(f"✅ Copie créée pour le test d'orchestration : {specific_cache_path.name}")
        else:
            print("❌ Impossible de récupérer le discours du Kremlin.")
    except Exception as e:
        print(f"❌ Erreur lors de la récupération du discours du Kremlin : {e}")

if __name__ == "__main__":
    # Exécuter la fonction principale
    main()
    
    print("\n=== Récupération terminée ===\n")