from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ValidationResult:
    """Résultat de validation avec métadonnées détaillées"""

    belief_name: str
    is_valid: bool
    confidence_score: float
    validation_method: str
    issues_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    formal_proof: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConflictResolution:
    """Résolution de conflit entre croyances contradictoires"""

    conflict_id: str
    conflicting_beliefs: List[str]
    resolution_strategy: str
    chosen_belief: Optional[str]
    reasoning: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
