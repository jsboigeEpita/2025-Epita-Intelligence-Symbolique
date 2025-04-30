#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour récupérer le discours du Kremlin et le sauvegarder dans le cache.
"""

import os
import sys
import json
import hashlib
import requests
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Définir les chemins
current_dir = Path(__file__).parent
project_root = current_dir.parent
text_cache_dir = project_root / "text_cache"

# Créer le répertoire de cache s'il n'existe pas
text_cache_dir.mkdir(exist_ok=True, parents=True)

# URL du discours du Kremlin
kremlin_url = "http://en.kremlin.ru/events/president/transcripts/67828"

# Fonction pour calculer le hash de l'URL
def get_cache_filepath(url):
    """Génère le chemin du fichier cache pour une URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return text_cache_dir / f"{url_hash}.txt"

# Fonction pour récupérer le contenu d'une URL
def fetch_with_jina(url):
    """Récupère le contenu d'une URL via Jina Reader."""
    jina_url = f"https://r.jina.ai/{url}"
    print(f"Récupération via Jina : {jina_url}...")
    
    headers = {'Accept': 'text/markdown', 'User-Agent': 'ArgumentAnalysisApp/1.0'}
    
    try:
        response = requests.get(jina_url, headers=headers, timeout=90)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erreur Jina ({jina_url}): {e}")
        return None
    
    content = response.text
    md_start_marker = "Markdown Content:"
    md_start_index = content.find(md_start_marker)
    
    if md_start_index != -1:
        text = content[md_start_index + len(md_start_marker):].strip()
    else:
        text = content
    
    print(f"Contenu récupéré (longueur {len(text)}).")
    return text

# Récupérer le discours du Kremlin
print(f"Récupération du discours du Kremlin depuis {kremlin_url}...")
kremlin_text = fetch_with_jina(kremlin_url)

if kremlin_text:
    # Calculer le hash de l'URL
    cache_path = get_cache_filepath(kremlin_url)
    
    # Sauvegarder le texte dans le cache
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(kremlin_text)
    
    print(f"Discours du Kremlin sauvegardé dans {cache_path}")
    print(f"Hash de l'URL: {cache_path.name}")
else:
    print("Impossible de récupérer le discours du Kremlin.")