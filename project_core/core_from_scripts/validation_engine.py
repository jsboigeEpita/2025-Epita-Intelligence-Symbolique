"""
Moteur de validation et vérification système
==========================================

Centralise les validations de prérequis et vérifications système.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import os
import sys
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .common_utils import Logger, LogLevel
from .environment_manager import EnvironmentManager


@dataclass
class ValidationResult:
    """Résultat d'une validation"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidationEngine:
    """Moteur principal de validation"""
    
    def __init__(self, logger: Logger = None):
        self.logger = logger or Logger()
        self.env_manager = EnvironmentManager(self.logger)
        self.project_root = self.env_manager.project_root
    
    def check_prerequisites(self, authentic: bool = False) -> List[str]:
        """Vérifie tous les prérequis système"""
        issues = []
        
        # Python et conda
        if not self.env_manager.check_python_version():
            issues.append("Version Python incompatible")
        
        if not self.env_manager.check_conda_available():
            issues.append("Conda non disponible")
        
        if not self.env_manager.check_conda_env_exists():
            issues.append("Environnement conda 'projet-is' manquant")
        
        # Fichiers essentiels
        essential_files = [
            "scripts/env/activate_project_env.ps1",
            "config/unified_config.py"
        ]
        
        for file_path in essential_files:
            if not os.path.exists(os.path.join(self.project_root, file_path)):
                issues.append(f"Fichier essentiel manquant: {file_path}")
        
        # Prérequis authentiques
        if authentic:
            if not os.getenv("OPENAI_API_KEY"):
                issues.append("Clé API OpenAI manquante")
            
            auth_files = ["libs/tweety.jar", "config/taxonomies"]
            for file_path in auth_files:
                if not os.path.exists(os.path.join(self.project_root, file_path)):
                    issues.append(f"Fichier authentique manquant: {file_path}")
        
        return issues
    
    def validate_system(self, mode: str = "basic") -> ValidationResult:
        """Validation complète du système"""
        self.logger.info(f"Validation système mode: {mode}")
        
        issues = self.check_prerequisites(authentic=(mode == "authentic"))
        
        if issues:
            self.logger.warning(f"{len(issues)} problèmes détectés")
            return ValidationResult(
                success=False,
                message=f"Validation échouée: {len(issues)} problèmes",
                details={"issues": issues}
            )
        
        self.logger.success("Validation système réussie")
        return ValidationResult(
            success=True,
            message="Système validé"
        )


def check_prerequisites(authentic: bool = False, logger: Logger = None) -> List[str]:
    """Fonction utilitaire de vérification"""
    engine = ValidationEngine(logger)
    return engine.check_prerequisites(authentic)


def validate_system(mode: str = "basic", logger: Logger = None) -> bool:
    """Fonction utilitaire de validation"""
    engine = ValidationEngine(logger)
    result = engine.validate_system(mode)
    return result.success