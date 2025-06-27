"""
Moteur de validation et vérification système
==========================================

Centralise les validations de prérequis et vérifications système en se basant sur un système de règles.

Auteur: Intelligence Symbolique EPITA
Date: 27/06/2025
"""

import os
import abc
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass

from ..common_utils import Logger
from ..environment_manager import EnvironmentManager


@dataclass
class ValidationResult:
    """Résultat d'une validation"""
    success: bool
    message: str
    rule_name: str
    details: Optional[Dict[str, Any]] = None


class ValidationRule(abc.ABC):
    """Classe de base abstraite pour une règle de validation."""
    
    def __init__(self, engine: 'ValidationEngine'):
        self.engine = engine
        self.logger = engine.logger
        self.project_root = engine.project_root

    @property
    def name(self) -> str:
        """Nom de la règle, utilisé pour les logs."""
        return self.__class__.__name__

    @abc.abstractmethod
    def validate(self) -> ValidationResult:
        """Exécute la logique de validation et retourne un résultat."""
        pass


class ValidationEngine:
    """Moteur principal de validation qui exécute des règles."""
    
    def __init__(self, logger: Logger = None):
        self.logger = logger or Logger()
        self.env_manager = EnvironmentManager(self.logger)
        self.project_root = self.env_manager.project_root
        self.rules: List[ValidationRule] = []
        self._load_rules()

    def _load_rules(self):
        """Charge et instancie toutes les règles de validation."""
        # Pour l'instant, nous chargeons manuellement.
        # Plus tard, cela pourrait être dynamique.
        from .rules.config_rules import ConfigValidationRule
        
        rule_classes: List[Type[ValidationRule]] = [
            ConfigValidationRule,
        ]
        
        for rule_class in rule_classes:
            self.rules.append(rule_class(self))
        self.logger.info(f"{len(self.rules)} règles de validation chargées.")

    def run(self) -> List[ValidationResult]:
        """Exécute toutes les règles de validation chargées."""
        self.logger.info("Démarrage du moteur de validation...")
        results = []
        for rule in self.rules:
            self.logger.debug(f"Exécution de la règle: {rule.name}")
            result = rule.validate()
            results.append(result)
            if not result.success:
                self.logger.warning(f"Règle '{rule.name}' échouée: {result.message}")
        
        self.logger.info("Moteur de validation terminé.")
        return results
