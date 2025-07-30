#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UnifiedSourceSelector - Interface CLI pour la sélection unifiée de sources.

Ce module fournit une interface CLI simplifiée qui délègue vers le composant core
argumentation_analysis.core.source_management pour la logique métier.

Refactorisé pour utiliser l'architecture core réutilisable.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Ajout du répertoire racine du projet au chemin
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import du composant core refactorisé
from argumentation_analysis.core.source_management import (
    InteractiveSourceSelector,
    create_unified_source_manager,
    UnifiedSourceType
)

logger = logging.getLogger("UnifiedSourceSelector")

class UnifiedSourceSelector:
    """
    Wrapper CLI pour le composant core source_management.
    
    Interface simplifiée qui délègue vers InteractiveSourceSelector
    pour la logique métier.
    """
    
    def __init__(self, passphrase: str = None, auto_passphrase: bool = True):
        """
        Initialise le sélecteur de sources.
        
        Args:
            passphrase: Phrase secrète pour déchiffrement (optionnel)
            auto_passphrase: Si True, récupère automatiquement depuis l'environnement
        """
        self._core_selector = InteractiveSourceSelector(
            passphrase=passphrase,
            auto_passphrase=auto_passphrase
        )
        
    def select_source_interactive(self) -> Tuple[str, str, str]:
        """
        Interface interactive pour sélectionner une source.
        
        Returns:
            Tuple[str, str, str]: (selected_text, description, source_type)
        """
        return self._core_selector.select_source_interactive()
    
    def load_source_batch(self,
                         source_type: str,
                         enc_file: str = None,
                         text_file: str = None,
                         source_index: int = 0,
                         free_text: str = None) -> Tuple[str, str, str]:
        """
        Charge une source en mode batch (non-interactif).
        
        Args:
            source_type: "simple", "complex", "enc_file", "text_file", "free_text"
            enc_file: Chemin vers fichier .enc (si source_type="enc_file")
            text_file: Chemin vers fichier texte (si source_type="text_file")
            source_index: Index de la source à sélectionner (pour complex)
            free_text: Contenu texte libre (si source_type="free_text")
            
        Returns:
            Tuple[str, str, str]: (selected_text, description, source_type)
        """
        return self._core_selector.load_source_batch(
            source_type=source_type,
            enc_file=enc_file,
            text_file=text_file,
            source_index=source_index,
            free_text=free_text
        )
    
    def list_available_sources(self) -> Dict[str, List[str]]:
        """
        Liste toutes les sources disponibles sans les charger complètement.
        
        Returns:
            Dict contenant les listes de sources par type
        """
        return self._core_selector.list_available_sources()