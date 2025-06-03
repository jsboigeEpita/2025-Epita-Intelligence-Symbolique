"""
Modèle pour les résultats d'extraction.

Ce module contient la classe ExtractResult qui représente le résultat d'une opération
d'extraction de texte, avec des informations sur le statut, les marqueurs et le texte extrait.
"""

from typing import Dict, Any, Optional


class ExtractResult:
    """Classe représentant le résultat d'une extraction."""
    
    def __init__(
        self,
        source_name: str,
        extract_name: str,
        status: str,
        message: str,
        start_marker: str = "",
        end_marker: str = "",
        template_start: str = "",
        explanation: str = "",
        extracted_text: str = ""
    ):
        """
        Initialise un résultat d'extraction.
        
        Args:
            source_name: Nom de la source
            extract_name: Nom de l'extrait
            status: Statut de l'extraction (valid, rejected, error)
            message: Message explicatif
            start_marker: Marqueur de début
            end_marker: Marqueur de fin
            template_start: Template pour le marqueur de début
            explanation: Explication de l'extraction
            extracted_text: Texte extrait
        """
        self.source_name = source_name
        self.extract_name = extract_name
        self.status = status
        self.message = message
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.template_start = template_start
        self.explanation = explanation
        self.extracted_text = extracted_text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "source_name": self.source_name,
            "extract_name": self.extract_name,
            "status": self.status,
            "message": self.message,
            "start_marker": self.start_marker,
            "end_marker": self.end_marker,
            "template_start": self.template_start,
            "explanation": self.explanation,
            "extracted_text": self.extracted_text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractResult':
        """Crée un résultat à partir d'un dictionnaire."""
        return cls(
            source_name=data.get("source_name", ""),
            extract_name=data.get("extract_name", ""),
            status=data.get("status", ""),
            message=data.get("message", ""),
            start_marker=data.get("start_marker", ""),
            end_marker=data.get("end_marker", ""),
            template_start=data.get("template_start", ""),
            explanation=data.get("explanation", ""),
            extracted_text=data.get("extracted_text", "")
        )
    
    def is_valid(self) -> bool:
        """Vérifie si l'extraction est valide."""
        return self.status == "valid"
    
    def is_error(self) -> bool:
        """Vérifie si l'extraction a échoué."""
        return self.status == "error"
    
    def is_rejected(self) -> bool:
        """Vérifie si l'extraction a été rejetée."""
        return self.status == "rejected"
    
    def __str__(self) -> str:
        """Représentation sous forme de chaîne."""
        return f"ExtractResult({self.status}): {self.message}"