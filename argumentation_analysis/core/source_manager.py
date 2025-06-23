#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DEPRECATED: Module de gestion des sources.

Ce module est OBSOLETE et conservé pour compatibilité ascendante uniquement.
Veuillez utiliser le module `argumentation_analysis.core.source_management` qui
fournit une interface unifiée et étendue.

Ce fichier sera supprimé dans une future version.
"""

import warnings
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple

warnings.warn(
    "Le module 'source_manager' est obsolète. Utilisez 'source_management' à la place.",
    DeprecationWarning,
    stacklevel=2
)

# --- Définitions de classes vides pour la compatibilité des imports ---

class SourceType(Enum):
    """Types de sources (obsolète)."""
    SIMPLE = "simple"
    COMPLEX = "complex"

@dataclass
class SourceConfig:
    """Configuration de source (obsolète)."""
    source_type: SourceType
    passphrase: Optional[str] = None
    anonymize_logs: bool = True
    auto_cleanup: bool = True

class SourceManager:
    """Gestionnaire de sources (obsolète)."""
    
    def __init__(self, config: SourceConfig):
        warnings.warn(
            "La classe 'SourceManager' est obsolète. Utilisez 'UnifiedSourceManager' "
            "du module 'source_management'.",
            DeprecationWarning,
            stacklevel=2
        )
        self.config = config

    def load_sources(self) -> Tuple[None, str]:
        """Méthode obsolète."""
        return None, "SourceManager est obsolète."

    def select_text_for_analysis(self, extract_definitions) -> Tuple[str, str]:
        """Méthode obsolète."""
        return "SourceManager est obsolète.", "obsolete"
        
    def cleanup_sensitive_data(self):
        """Méthode obsolète."""
        pass

def create_source_manager(source_type: str, **kwargs) -> SourceManager:
    """Factory function obsolète."""
    warnings.warn(
        "La fonction 'create_source_manager' est obsolète. Utilisez 'create_unified_source_manager' "
        "du module 'source_management'.",
        DeprecationWarning,
        stacklevel=2
    )
    return SourceManager(SourceConfig(source_type=SourceType(source_type)))