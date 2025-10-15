#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour pydantic pour les tests.
Ce mock permet d'exécuter les tests sans avoir besoin d'installer pydantic.
"""

import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Callable,
    Type,
    TypeVar,
    get_type_hints,
)
import inspect
import copy
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PydanticMock")

# Version
__version__ = "1.10.8"

# Type variable pour les annotations génériques
T = TypeVar("T")


# Exceptions
class ValidationError(Exception):
    """Exception levée lors d'une erreur de validation."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"Validation error: {errors}")


class ConfigError(Exception):
    """Exception levée lors d'une erreur de configuration."""

    pass


# Classes de base
class BaseModel:
    """Classe de base pour les modèles Pydantic."""

    class Config:
        """Configuration par défaut pour les modèles."""

        extra = "ignore"  # ignore, allow, forbid
        validate_assignment = True
        validate_all = False
        orm_mode = False
        allow_population_by_field_name = False
        arbitrary_types_allowed = False

    def __init__(self, **data):
        """Initialise le modèle avec les données fournies."""
        # Récupérer les annotations de type
        annotations = get_type_hints(self.__class__)

        # Valider et assigner les valeurs
        for field_name, field_type in annotations.items():
            if field_name in data:
                # Valider la valeur
                value = data[field_name]
                try:
                    # Validation simple
                    if isinstance(field_type, type) and not isinstance(
                        value, field_type
                    ):
                        # Tentative de conversion
                        try:
                            value = field_type(value)
                        except (ValueError, TypeError):
                            raise ValidationError(
                                [
                                    {
                                        "loc": (field_name,),
                                        "msg": f"value is not a valid {field_type.__name__}",
                                        "type": "type_error",
                                    }
                                ]
                            )
                except Exception as e:
                    raise ValidationError(
                        [{"loc": (field_name,), "msg": str(e), "type": "value_error"}]
                    )

                # Assigner la valeur
                setattr(self, field_name, value)
            else:
                # Champ manquant
                # Vérifier s'il s'agit d'un champ optionnel
                if getattr(field_type, "__origin__", None) is Union and type(
                    None
                ) in getattr(field_type, "__args__", []):
                    # Champ optionnel, assigner None
                    setattr(self, field_name, None)
                else:
                    # Champ requis manquant
                    raise ValidationError(
                        [
                            {
                                "loc": (field_name,),
                                "msg": "field required",
                                "type": "value_error.missing",
                            }
                        ]
                    )

        # Traiter les champs supplémentaires
        if hasattr(self.Config, "extra") and self.Config.extra == "allow":
            for field_name, value in data.items():
                if field_name not in annotations:
                    setattr(self, field_name, value)

    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convertit le modèle en dictionnaire."""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                if isinstance(value, BaseModel):
                    result[key] = value.dict(**kwargs)
                else:
                    result[key] = value
        return result

    def json(self, **kwargs) -> str:
        """Convertit le modèle en JSON."""
        return json.dumps(self.dict(**kwargs))

    def copy(self, **kwargs) -> "BaseModel":
        """Crée une copie du modèle."""
        data = self.dict()
        data.update(kwargs)
        return self.__class__(**data)

    @classmethod
    def parse_obj(cls: Type[T], obj: Dict[str, Any]) -> T:
        """Crée un modèle à partir d'un dictionnaire."""
        return cls(**obj)

    @classmethod
    def parse_raw(cls: Type[T], b: str, **kwargs) -> T:
        """Crée un modèle à partir d'une chaîne JSON."""
        obj = json.loads(b)
        return cls.model_validate(obj)

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        """Génère le schéma JSON du modèle."""
        schema = {"title": cls.__name__, "type": "object", "properties": {}}

        # Récupérer les annotations de type
        annotations = get_type_hints(cls)

        # Générer les propriétés du schéma
        for field_name, field_type in annotations.items():
            # Type de base
            if field_type is str:
                schema["properties"][field_name] = {"type": "string"}
            elif field_type is int:
                schema["properties"][field_name] = {"type": "integer"}
            elif field_type is float:
                schema["properties"][field_name] = {"type": "number"}
            elif field_type is bool:
                schema["properties"][field_name] = {"type": "boolean"}
            elif field_type is list or getattr(field_type, "__origin__", None) is list:
                schema["properties"][field_name] = {"type": "array"}
            elif field_type is dict or getattr(field_type, "__origin__", None) is dict:
                schema["properties"][field_name] = {"type": "object"}
            else:
                schema["properties"][field_name] = {"type": "object"}

        return schema


# Fonctions de validation
def validator(*fields, **kwargs):
    """Décorateur pour ajouter des validateurs aux champs."""

    def decorator(func):
        func._validator_fields = fields
        func._validator_kwargs = kwargs
        return func

    return decorator


# Fonctions utilitaires
def create_model(model_name: str, **field_definitions) -> Type[BaseModel]:
    """Crée dynamiquement un modèle Pydantic."""
    fields = {}
    annotations = {}

    for field_name, field_def in field_definitions.items():
        if isinstance(field_def, tuple):
            field_type, field_default = field_def
            fields[field_name] = field_default
            annotations[field_name] = field_type
        else:
            annotations[field_name] = field_def

    model_dict = {"__annotations__": annotations, **fields}

    return type(model_name, (BaseModel,), model_dict)


# Types spéciaux
class Field:
    """Définition d'un champ avec des métadonnées."""

    def __init__(self, default=..., **kwargs):
        self.default = default
        self.metadata = kwargs


# Log de chargement
logger.info("Module pydantic_mock chargé")
