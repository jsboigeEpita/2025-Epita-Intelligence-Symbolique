#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'éditeur de marqueurs d'extraits

Ce script permet de lancer facilement l'éditeur de marqueurs d'extraits
depuis la racine du projet, après la réorganisation des fichiers.
"""

import os
import sys
from pathlib import Path

def main():
    """Fonction principale pour lancer l'éditeur de marqueurs.

    :raises ImportError: Si le module `extract_marker_editor` ne peut pas être importé.
    """
    # Importer le module depuis son nouvel emplacement
    try:
        from argumentation_analysis.ui.extract_editor.extract_marker_editor import main as editor_main
        print("[OK] Module extract_marker_editor importé avec succès.")
        
        # Lancer l'interface
        editor_main()
        print("\n[OK] Interface lancée avec succès.")
    except ImportError as e:
        print(f"❌ Erreur lors de l'importation du module extract_marker_editor: {e}")
        print("Vérifiez que le fichier extract_marker_editor.py est présent dans le répertoire ui/extract_editor/.")
        raise
    except Exception as e:
        print(f"❌ Erreur lors du lancement de l'interface: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()