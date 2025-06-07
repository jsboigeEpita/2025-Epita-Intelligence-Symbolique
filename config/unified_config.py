#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration unifiée pour le système d'analyse argumentative.

Ce module centralise toute la configuration du système, incluant les paramètres
pour les agents, les outils d'analyse, et les configurations spécifiques aux tests.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration par défaut
DEFAULT_CONFIG = {
    "system": {
        "name": "argumentation_analysis",
        "version": "1.0.0",
        "debug": False,
        "log_level": "INFO"
    },
    
    "agents": {
        "fol_logic": {
            "enabled": True,
            "jvm_enabled": False,  # JVM désactivée par défaut pour éviter les conflits
            "timeout": 30,
            "max_retries": 3
        },
        "complex_fallacy": {
            "enabled": True,
            "confidence_threshold": 0.5,
            "max_fallacies": 10
        },
        "contextual_fallacy": {
            "enabled": True,
            "context_analysis": True,
            "default_context": "général"
        }
    },
    
    "tools": {
        "text_processing": {
            "max_text_length": 10000,
            "chunk_size": 500,
            "encoding": "utf-8"
        },
        "analysis": {
            "enable_caching": True,
            "cache_ttl": 3600,
            "parallel_processing": False
        }
    },
    
    "testing": {
        "mock_mode": False,
        "test_data_path": "tests/data",
        "mock_responses": True,
        "skip_integration": False
    },
    
    "paths": {
        "project_root": None,  # Sera défini dynamiquement
        "data_dir": "data",
        "logs_dir": "logs",
        "temp_dir": "temp"
    }
}


class UnifiedConfig:
    """
    Classe de configuration unifiée pour le système d'analyse argumentative.
    """
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        """
        Initialise la configuration unifiée.
        
        Args:
            config_override: Configuration optionnelle pour surcharger les valeurs par défaut
        """
        self._config = DEFAULT_CONFIG.copy()
        
        # Définir le répertoire racine du projet
        self._set_project_root()
        
        # Appliquer les surcharges de configuration
        if config_override:
            self._apply_override(config_override)
        
        # Charger les variables d'environnement
        self._load_environment_variables()
    
    def _set_project_root(self):
        """Définit le répertoire racine du projet."""
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        self._config["paths"]["project_root"] = str(project_root)
    
    def _apply_override(self, override: Dict[str, Any]):
        """
        Applique les surcharges de configuration.
        
        Args:
            override: Dictionnaire de surcharges
        """
        def deep_update(base_dict: Dict, override_dict: Dict):
            """Met à jour récursivement les dictionnaires imbriqués."""
            for key, value in override_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self._config, override)
    
    def _load_environment_variables(self):
        """Charge les variables d'environnement pertinentes."""
        env_mappings = {
            "ARGUMENTATION_DEBUG": ("system", "debug"),
            "ARGUMENTATION_LOG_LEVEL": ("system", "log_level"),
            "ARGUMENTATION_MOCK_MODE": ("testing", "mock_mode"),
            "ARGUMENTATION_JVM_ENABLED": ("agents", "fol_logic", "jvm_enabled"),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convertir les valeurs booléennes
                if env_value.lower() in ('true', '1', 'yes', 'on'):
                    env_value = True
                elif env_value.lower() in ('false', '0', 'no', 'off'):
                    env_value = False
                
                # Appliquer la valeur à la configuration
                current = self._config
                for key in config_path[:-1]:
                    current = current[key]
                current[config_path[-1]] = env_value
    
    def get(self, *keys) -> Any:
        """
        Récupère une valeur de configuration.
        
        Args:
            *keys: Clés imbriquées pour accéder à la valeur
            
        Returns:
            Valeur de configuration ou None si non trouvée
            
        Example:
            config.get("agents", "fol_logic", "enabled")
        """
        current = self._config
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return None
    
    def set(self, value: Any, *keys):
        """
        Définit une valeur de configuration.
        
        Args:
            value: Valeur à définir
            *keys: Clés imbriquées pour définir la valeur
            
        Example:
            config.set(True, "agents", "fol_logic", "enabled")
        """
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def is_enabled(self, component: str, subcomponent: Optional[str] = None) -> bool:
        """
        Vérifie si un composant est activé.
        
        Args:
            component: Nom du composant
            subcomponent: Nom du sous-composant (optionnel)
            
        Returns:
            True si le composant est activé, False sinon
        """
        if subcomponent:
            return self.get(component, subcomponent, "enabled") or False
        else:
            return self.get(component, "enabled") or False
    
    def get_paths(self) -> Dict[str, str]:
        """
        Retourne tous les chemins configurés.
        
        Returns:
            Dictionnaire des chemins
        """
        return self._config["paths"].copy()
    
    def get_project_root(self) -> str:
        """
        Retourne le répertoire racine du projet.
        
        Returns:
            Chemin vers le répertoire racine
        """
        return self._config["paths"]["project_root"]
    
    def is_testing_mode(self) -> bool:
        """
        Vérifie si le système est en mode test.
        
        Returns:
            True si en mode test, False sinon
        """
        return self.get("testing", "mock_mode") or False
    
    def is_jvm_enabled(self) -> bool:
        """
        Vérifie si JVM est activée pour FOL Logic.
        
        Returns:
            True si JVM est activée, False sinon
        """
        return self.get("agents", "fol_logic", "jvm_enabled") or False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Retourne la configuration complète sous forme de dictionnaire.
        
        Returns:
            Configuration complète
        """
        return self._config.copy()


# Instance globale de configuration
_global_config = None


def get_config(config_override: Optional[Dict[str, Any]] = None) -> UnifiedConfig:
    """
    Retourne l'instance globale de configuration.
    
    Args:
        config_override: Configuration optionnelle pour surcharger les valeurs par défaut
        
    Returns:
        Instance de UnifiedConfig
    """
    global _global_config
    if _global_config is None or config_override is not None:
        _global_config = UnifiedConfig(config_override)
    return _global_config


def reset_config():
    """Remet à zéro la configuration globale."""
    global _global_config
    _global_config = None


# Fonctions utilitaires pour les tests
def get_test_config() -> UnifiedConfig:
    """
    Retourne une configuration spécialement adaptée aux tests.
    
    Returns:
        Configuration de test
    """
    test_override = {
        "testing": {
            "mock_mode": True,
            "mock_responses": True,
            "skip_integration": True
        },
        "agents": {
            "fol_logic": {
                "jvm_enabled": False,  # JVM désactivée pour les tests
                "timeout": 5
            }
        },
        "system": {
            "debug": True,
            "log_level": "DEBUG"
        }
    }
    return UnifiedConfig(test_override)


def get_production_config() -> UnifiedConfig:
    """
    Retourne une configuration pour la production.
    
    Returns:
        Configuration de production
    """
    production_override = {
        "testing": {
            "mock_mode": False,
            "mock_responses": False,
            "skip_integration": False
        },
        "agents": {
            "fol_logic": {
                "jvm_enabled": True,  # JVM activée en production
                "timeout": 60
            }
        },
        "system": {
            "debug": False,
            "log_level": "INFO"
        }
    }
    return UnifiedConfig(production_override)


if __name__ == "__main__":
    # Test de la configuration
    config = get_config()
    print(f"Configuration du système: {config.get('system')}")
    print(f"JVM activée: {config.is_jvm_enabled()}")
    print(f"Mode test: {config.is_testing_mode()}")
    print(f"Agent FOL activé: {config.is_enabled('agents', 'fol_logic')}")