"""
Modèle pour les définitions d'extraits.

Ce module contient les classes qui représentent les définitions d'extraits
et leurs métadonnées, utilisées pour la gestion des sources et des extraits.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Extract:
    """Classe représentant un extrait de texte."""
    
    extract_name: str
    start_marker: str
    end_marker: str
    template_start: str = ""
    full_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'extrait en dictionnaire."""
        result = {
            "extract_name": self.extract_name,
            "start_marker": self.start_marker,
            "end_marker": self.end_marker,
            "full_text": self.full_text
        }
        
        if self.template_start:
            result["template_start"] = self.template_start
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Extract':
        """Crée un extrait à partir d'un dictionnaire."""
        return cls(
            extract_name=data.get("extract_name", ""),
            start_marker=data.get("start_marker", ""),
            end_marker=data.get("end_marker", ""),
            template_start=data.get("template_start", ""),
            full_text=data.get("full_text", "")
        )


@dataclass
class SourceDefinition:
    """Classe représentant une définition de source."""
    
    source_name: str
    source_type: str
    schema: str
    host_parts: List[str]
    path: str
    extracts: List[Extract] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la définition de source en dictionnaire."""
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "schema": self.schema,
            "host_parts": self.host_parts,
            "path": self.path,
            "extracts": [extract.to_dict() for extract in self.extracts]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceDefinition':
        """Crée une définition de source à partir d'un dictionnaire."""
        extracts_data = data.get("extracts", [])
        extracts = [Extract.from_dict(extract_data) for extract_data in extracts_data]
        
        return cls(
            source_name=data.get("source_name", ""),
            source_type=data.get("source_type", ""),
            schema=data.get("schema", ""),
            host_parts=data.get("host_parts", []),
            path=data.get("path", ""),
            extracts=extracts
        )
    
    def add_extract(self, extract: Extract) -> None:
        """Ajoute un extrait à la source."""
        self.extracts.append(extract)
    
    def get_extract_by_name(self, extract_name: str) -> Optional[Extract]:
        """Récupère un extrait par son nom."""
        for extract in self.extracts:
            if extract.extract_name == extract_name:
                return extract
        return None
    
    def get_extract_by_index(self, index: int) -> Optional[Extract]:
        """Récupère un extrait par son index."""
        if 0 <= index < len(self.extracts):
            return self.extracts[index]
        return None


class ExtractDefinitions:
    """Classe pour gérer l'ensemble des définitions d'extraits."""
    
    def __init__(self, sources: List[SourceDefinition] = None):
        """
        Initialise les définitions d'extraits.
        
        Args:
            sources: Liste des définitions de sources
        """
        self.sources = sources or []
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convertit les définitions en liste de dictionnaires."""
        return [source.to_dict() for source in self.sources]
    
    @classmethod
    def from_dict_list(cls, data: List[Dict[str, Any]]) -> 'ExtractDefinitions':
        """Crée des définitions à partir d'une liste de dictionnaires."""
        sources = [SourceDefinition.from_dict(source_data) for source_data in data]
        return cls(sources=sources)
    
    def add_source(self, source: SourceDefinition) -> None:
        """Ajoute une source aux définitions."""
        self.sources.append(source)
    
    def get_source_by_name(self, source_name: str) -> Optional[SourceDefinition]:
        """Récupère une source par son nom."""
        for source in self.sources:
            if source.source_name == source_name:
                return source
        return None
    
    def get_source_by_index(self, index: int) -> Optional[SourceDefinition]:
        """Récupère une source par son index."""
        if 0 <= index < len(self.sources):
            return self.sources[index]
        return None
    
    @classmethod
    def model_validate(cls, data):
        """Méthode de compatibilité pour Pydantic v1/v2"""
        if hasattr(cls, 'parse_obj'):
            return cls.parse_obj(data)
        elif isinstance(data, dict):
            return cls.from_dict_list(data.get('sources', []))
        elif isinstance(data, list):
            return cls.from_dict_list(data)
        else:
            return cls(**data if isinstance(data, dict) else {})