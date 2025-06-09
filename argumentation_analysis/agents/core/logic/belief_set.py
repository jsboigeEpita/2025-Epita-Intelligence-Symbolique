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

        :param content: Le contenu textuel représentant l'ensemble de croyances
                        dans la logique spécifique.
        :type content: str
        """
        self._content = content
    
    @property
    def content(self) -> str:
        """
        Retourne le contenu brut de l'ensemble de croyances.

        :return: Le contenu de l'ensemble de croyances.
        :rtype: str
        """
        return self._content
    
    @property
    @abstractmethod
    def logic_type(self) -> str:
        """
        Retourne le type de logique de cet ensemble de croyances (par exemple, "propositional").

        Cette propriété doit être implémentée par les sous-classes.

        :return: Le type de logique.
        :rtype: str
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance `BeliefSet` en un dictionnaire.

        :return: Un dictionnaire contenant le type de logique et le contenu.
        :rtype: Dict[str, Any]
        """
        return {
            "logic_type": self.logic_type,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['BeliefSet']:
        """
        Crée une instance d'une sous-classe concrète de `BeliefSet` à partir d'un dictionnaire.

        La sous-classe est déterminée par la valeur de la clé "logic_type" dans `data`.

        :param data: Dictionnaire contenant les clés "logic_type" et "content".
        :type data: Dict[str, Any]
        :return: Une instance de `PropositionalBeliefSet`, `FirstOrderBeliefSet`,
                 ou `ModalBeliefSet`, ou None si `logic_type` n'est pas supporté.
        :rtype: Optional[BeliefSet]
        """
        if data is None:
            return None
            
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
        Retourne le type de logique pour cet ensemble de croyances.

        :return: "propositional"
        :rtype: str
        """
        return "propositional"


class FirstOrderBeliefSet(BeliefSet):
    """
    Classe pour représenter un ensemble de croyances en logique du premier ordre.
    """
    
    @property
    def logic_type(self) -> str:
        """
        Retourne le type de logique pour cet ensemble de croyances.

        :return: "first_order"
        :rtype: str
        """
        return "first_order"


class ModalBeliefSet(BeliefSet):
    """
    Classe pour représenter un ensemble de croyances en logique modale.
    """
    
    @property
    def logic_type(self) -> str:
        """
        Retourne le type de logique pour cet ensemble de croyances.

        :return: "modal"
        :rtype: str
        """
        return "modal"