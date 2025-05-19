#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester l'agent informel sur un texte contenant des sophismes complexes
"""

import os
import sys
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

async def main():
    """Fonction principale pour tester l'agent informel"""
    from argumentation_analysis.run_orchestration import setup_logging, setup_environment, run_orchestration
    
    # Configuration du logging
    setup_logging(verbose=True)
    
    # Initialisation de l'environnement
    llm_service = await setup_environment()
    if not llm_service:
        print("Échec de l'initialisation de l'environnement")
        return
    
    # Lecture du fichier de test
    test_file = Path("test_sophismes_complexes.txt")
    if not test_file.exists():
        print(f"Le fichier {test_file} n'existe pas.")
        return
    
    with open(test_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    print(f"Texte chargé depuis {test_file} ({len(text_content)} caractères)")
    
    # Exécution de l'orchestration avec l'agent informel uniquement
    await run_orchestration(
        text_content=text_content,
        llm_service=llm_service,
        agents=["informal"],
        verbose=True
    )
    
    print("Test de l'agent informel terminé")

if __name__ == "__main__":
    asyncio.run(main())