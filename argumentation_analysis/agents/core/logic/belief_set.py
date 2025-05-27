# argumentation_analysis/agents/core/logic/belief_set.py
"""
Classes pour représenter les ensembles de croyances.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BeliefSet(ABC):
    """
    Classe abstraite de base pour représenter un ensemble de croyances.
    """
    
    def __init__(self, content: str):
        """
        Initialise un ensemble de croyances.
        
        Args:
            content: Le contenu de l'ensemble de croyances
        """
        self._content = content
    
    @property
    def content(self) -> str:
        """
        Retourne le contenu de l'ensemble de croyances.
        
        Returns:
            Le contenu de l'ensemble de croyances
        """
        return self._content
    
    @property
    @abstractmethod
    def logic_type(self) -> str:
        """
        Retourne le type de logique de l'ensemble de croyances.
        
        Returns:
            Le type de logique
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'ensemble de croyances en dictionnaire.
        
        Returns:
            Un dictionnaire représentant l'ensemble de croyances
        """
        return {
            "logic_type": self.logic_type,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['BeliefSet']:
        """
        Crée un ensemble de croyances à partir d'un dictionnaire.
        
        Args:
            data: Le dictionnaire contenant les données de l'ensemble de croyances
            
        Returns:
            Un ensemble de croyances ou None si le type de logique n'est pas supporté
        """
        logic_type = data.get("logic_type", "").lower()
        content = data.get("content", "")
        
        if logic_type == "propositional":
            return PropositionalBeliefSet(content)
        elif logic_type == "first_order":
            return FirstOrderBeliefSet(content)
        elif logic_type == "modal":
            return ModalBeliefSet(content)
        else:
            return None


class PropositionalBeliefSet(BeliefSet):
    """
    Classe pour représenter un ensemble de croyances en logique propositionnelle.
    """
    
    @property
    def logic_type(self) -> str:
        """
        Retourne le type de logique de l'ensemble de croyances.
        
        Returns:
            "propositional"
        """
        return "propositional"


class FirstOrderBeliefSet(BeliefSet):
    """
    Classe pour représenter un ensemble de croyances en logique du premier ordre.
    """
    
    @property
    def logic_type(self) -> str:
        """
        Retourne le type de logique de l'ensemble de croyances.
        
        Returns:
            "first_order"
        """
        return "first_order"


class ModalBeliefSet(BeliefSet):
    """
    Classe pour représenter un ensemble de croyances en logique modale.
    """
    
    @property
    def logic_type(self) -> str:
        """
        Retourne le type de logique de l'ensemble de croyances.
        
        Returns:
            "modal"
        """
        return "modal"