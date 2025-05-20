#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester l'agent informel sur un texte contenant des sophismes complexes
"""

import os
import sys
import asyncio
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin de recherche des modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

async def main():
    """Fonction principale pour tester l'agent informel"""
    from argumentation_analysis.run_orchestration import setup_logging, setup_environment, run_orchestration
    
    # Configuration du logging
    setup_logging(verbose=True)
    
    # Initialisation de l'environnement avec le singleton PyO3
    from argumentation_analysis.core.pyo3_singleton import initialize_pyo3
    initialize_pyo3()  # Initialiser l'environnement PyO3 avant tout
    
    llm_service = await setup_environment()
    if not llm_service:
        print("Échec de l'initialisation de l'environnement")
        return
    
    # Lecture du fichier de test (chercher dans plusieurs emplacements)
    test_file_paths = [
        Path("test_sophismes_complexes.txt"),  # Répertoire courant
        Path(__file__).parent / "test_sophismes_complexes.txt",  # Même répertoire que le script
        Path(__file__).parent.parent / "data" / "test_sophismes_complexes.txt",  # Répertoire data
    ]
    
    test_file = None
    for path in test_file_paths:
        if path.exists():
            test_file = path
            break
    
    if not test_file:
        print(f"Le fichier test_sophismes_complexes.txt n'existe pas dans les emplacements recherchés.")
        print(f"Emplacements vérifiés: {[str(p) for p in test_file_paths]}")
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