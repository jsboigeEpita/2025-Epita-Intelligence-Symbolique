#!/usr/bin/env python3
"""
Test de compatibilité pour les corrections d'imports semantic_kernel

Ce script teste que tous les imports problématiques ont été correctement
corrigés et que le module de compatibilité fonctionne.
"""

import sys
import traceback
from typing import List, Tuple

def test_import(module_path: str, description: str) -> Tuple[bool, str]:
    """
    Teste un import et retourne le résultat.
    
    Args:
        module_path: Chemin du module à importer
        description: Description du test
        
    Returns:
        Tuple (succès, message)
    """
    try:
        exec(f"import {module_path}")
        return True, f"[OK] {description}: Import réussi"
    except Exception as e:
        return False, f"[ERREUR] {description}: {str(e)}"

def test_specific_imports() -> List[Tuple[bool, str]]:
    """
    Teste des imports spécifiques depuis les modules corrigés.
    
    Returns:
        Liste des résultats de test
    """
    results = []
    
    # Test du module de compatibilité
    try:
        from semantic_kernel.agents import Agent, ChatCompletionAgent, AgentGroupChat
from argumentation_analysis.utils.semantic_kernel_compatibility import SelectionStrategy, TerminationStrategy