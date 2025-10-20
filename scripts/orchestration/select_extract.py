#!/usr/bin/env python
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
            all_extracts.append(
                {
                    "source": source.get("source_name", "Unknown"),
                    "extract": extract.get("extract_name", "Unknown"),
                    "start": extract.get("start_marker", "")[:50],
                }
            )

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
