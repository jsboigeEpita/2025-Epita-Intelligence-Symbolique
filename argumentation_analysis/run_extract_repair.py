#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer la réparation des bornes défectueuses dans les extraits

Ce script permet de lancer facilement le script de réparation des bornes défectueuses
depuis la racine du projet, après la réorganisation des fichiers.
"""

import os
import sys
import asyncio
from pathlib import Path

async def main():
    """Fonction principale pour lancer la réparation des bornes défectueuses.

    :raises ImportError: Si le module `repair_extract_markers` ne peut pas être importé.
    """
    # Importer le module depuis son nouvel emplacement
    try:
        from argumentation_analysis.utils.extract_repair.repair_extract_markers import main as repair_main
        print("✅ Module repair_extract_markers importé avec succès.")
        
        # Lancer le script de réparation
        await repair_main()
        print("\n✅ Script de réparation exécuté avec succès.")
    except ImportError as e:
        print(f"❌ Erreur lors de l'importation du module repair_extract_markers: {e}")
        print("Vérifiez que le fichier repair_extract_markers.py est présent dans le répertoire utils/extract_repair/.")
        raise
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du script de réparation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())