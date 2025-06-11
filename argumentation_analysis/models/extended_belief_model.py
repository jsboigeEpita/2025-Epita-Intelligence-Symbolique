"""
Modèle étendu de croyance pour l'intégration JTMS.
Enrichit les croyances basiques avec métadonnées d'investigation et traçabilité.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import json

class BeliefType(Enum):
    """Types de croyances dans le système d'investigation"""
    FACT = "fact"                    # Fait établi
    HYPOTHESIS = "hypothesis"        # Hypothèse à valider
    EVIDENCE = "evidence"           # Preuve ou indice
    DEDUCTION = "deduction"         # Conclusion logique
    ASSUMPTION = "assumption"       # Supposition
    CONSTRAINT = "constraint"       # Contrainte du système
    VALIDATION = "validation"       # Résultat de validation
    CRITIQUE = "critique"           # Critique d'une autre croyance

class ConfidenceLevel(Enum):
    """Niveaux de confiance standardisés"""
    VERY_LOW = (0.0, 0.2)
    LOW = (0.2, 0.4)
    MEDIUM = (0.4, 0.6)
    HIGH = (0.6, 0.8)
    VERY_HIGH = (0.8, 1.0)
    
    def contains(self, confidence: float) -> bool:
        """Vérifie si une confiance appartient à ce niveau"""
        min_val, max_val = self.value
        return min_val <= confidence < max_val

class EvidenceQuality(Enum):
    """Qualité de l'évidence supportant une croyance"""
    UNRELIABLE = "unreliable"        # Non fiable
    CIRCUMSTANTIAL = "circumstantial" # Circonstancielle
    CORROBORATED = "corroborated"    # Corroborée
    VERIFIED = "verified"            # Vérifiée
    PROVEN = "proven"                # Prouvée

@dataclass
class ModificationHistory:
    """Historique des modifications d'une croyance"""
    timestamp: datetime
    modification_type: str  # created, updated, invalidated, validated, merged
    agent_id: str
    previous_confidence: Optional[float] = None
    new_confidence: Optional[float] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "modification_type": self.modification_type,
            "agent_id": self.agent_id,
            "previous_confidence": self.previous_confidence,
            "new_confidence": self.new_confidence,
            "reason": self.reason,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModificationHistory':
        """Création depuis un dictionnaire"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            modification_type=data["modification_type"],
            agent_id=data["agent_id"],
            previous_confidence=data.get("previous_confidence"),
            new_confidence=data.get("new_confidence"),
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {})
        )

@dataclass
class BeliefMetadata:
    """Métadonnées enrichies pour une croyance"""
    belief_type: BeliefType
    source_agent: str
    creation_timestamp: datetime
    last_modified: datetime
    confidence_level: ConfidenceLevel
    evidence_quality: EvidenceQuality
    
    # Investigation specifics
    investigation_context: Dict[str, Any] = field(default_factory=dict)
    related_evidence: List[str] = field(default_factory=list)
    supporting_beliefs: List[str] = field(default_factory=list)
    contradicting_beliefs: List[str] = field(default_factory=list)
    
    # Validation et critique
    validation_status: str = "pending"  # pending, validated, invalidated, under_review
    validation_agent: Optional[str] = None
    validation_confidence: Optional[float] = None
    critique_notes: List[str] = field(default_factory=list)
    
    # Traçabilité JTMS
    justification_chain: List[str] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    truth_maintenance_status: str = "active"  # active, suspended, invalidated
    
    # Communication inter-agents
    shared_with_agents: List[str] = field(default_factory=list)
    sync_status: Dict[str, str] = field(default_factory=dict)  # agent_id -> sync_status
    conflict_resolutions: List[str] = field(default_factory=list)
    
    def update_confidence_level(self, new_confidence: float):
        """Met à jour le niveau de confiance"""
        for level in ConfidenceLevel:
            if level.contains(new_confidence):
                self.confidence_level = level
                break
        self.last_modified = datetime.now()
    
    def add_related_evidence(self, evidence_id: str):
        """Ajoute une évidence liée"""
        if evidence_id not in self.related_evidence:
            self.related_evidence.append(evidence_id)
            self.last_modified = datetime.now()
    
    def add_supporting_belief(self, belief_id: str):
        """Ajoute une croyance supportante"""
        if belief_id not in self.supporting_beliefs:
            self.supporting_beliefs.append(belief_id)
            self.last_modified = datetime.now()
    
    def add_contradicting_belief(self, belief_id: str):
        """Ajoute une croyance contradictoire"""
        if belief_id not in self.contradicting_beliefs:
            self.contradicting_beliefs.append(belief_id)
            self.last_modified = datetime.now()
    
    def set_validation_result(self, agent_id: str, status: str, confidence: float = None):
        """Définit le résultat de validation"""
        self.validation_status = status
        self.validation_agent = agent_id
        self.validation_confidence = confidence
        self.last_modified = datetime.now()
    
    def add_critique(self, critique: str):
        """Ajoute une note de critique"""
        self.critique_notes.append(critique)
        self.last_modified = datetime.now()
    
    def share_with_agent(self, agent_id: str, sync_status: str = "pending"):
        """Marque comme partagé avec un agent"""
        if agent_id not in self.shared_with_agents:
            self.shared_with_agents.append(agent_id)
        self.sync_status[agent_id] = sync_status
        self.last_modified = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "belief_type": self.belief_type.value,
            "source_agent": self.source_agent,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "confidence_level": self.confidence_level.name,
            "evidence_quality": self.evidence_quality.value,
            "investigation_context": self.investigation_context,
            "related_evidence": self.related_evidence,
            "supporting_beliefs": self.supporting_beliefs,
            "contradicting_beliefs": self.contradicting_beliefs,
            "validation_status": self.validation_status,
            "validation_agent": self.validation_agent,
            "validation_confidence": self.validation_confidence,
            "critique_notes": self.critique_notes,
            "justification_chain": self.justification_chain,
            "dependency_graph": self.dependency_graph,
            "truth_maintenance_status": self.truth_maintenance_status,
            "shared_with_agents": self.shared_with_agents,
            "sync_status": self.sync_status,
            "conflict_resolutions": self.conflict_resolutions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeliefMetadata':
        """Création depuis un dictionnaire"""
        return cls(
            belief_type=BeliefType(data["belief_type"]),
            source_agent=data["source_agent"],
            creation_timestamp=datetime.fromisoformat(data["creation_timestamp"]),
            last_modified=datetime.fromisoformat(data["last_modified"]),
            confidence_level=ConfidenceLevel[data["confidence_level"]],
            evidence_quality=EvidenceQuality(data["evidence_quality"]),
            investigation_context=data.get("investigation_context", {}),
            related_evidence=data.get("related_evidence", []),
            supporting_beliefs=data.get("supporting_beliefs", []),
            contradicting_beliefs=data.get("contradicting_beliefs", []),
            validation_status=data.get("validation_status", "pending"),
            validation_agent=data.get("validation_agent"),
            validation_confidence=data.get("validation_confidence"),
            critique_notes=data.get("critique_notes", []),
            justification_chain=data.get("justification_chain", []),
            dependency_graph=data.get("dependency_graph", {}),
            truth_maintenance_status=data.get("truth_maintenance_status", "active"),
            shared_with_agents=data.get("shared_with_agents", []),
            sync_status=data.get("sync_status", {}),
            conflict_resolutions=data.get("conflict_resolutions", [])
        )

@dataclass
class ExtendedBeliefModel:
    """
    Modèle étendu de croyance intégrant JTMS et métadonnées d'investigation.
    Extension de la classe Belief basique du JTMS.
    """
    belief_id: str
    belief_name: str
    content: str
    confidence: float
    valid: Optional[bool] = None
    
    # Métadonnées étendues
    metadata: BeliefMetadata = None
    modification_history: List[ModificationHistory] = field(default_factory=list)
    
    # Relations JTMS
    justifications: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)
    
    # États computationnels
    is_derived: bool = False
    derivation_rule: Optional[str] = None
    computation_trace: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialisation post-création"""
        if self.metadata is None:
            # Créer métadonnées par défaut
            self.metadata = BeliefMetadata(
                belief_type=BeliefType.FACT,
                source_agent="unknown",
                creation_timestamp=datetime.now(),
                last_modified=datetime.now(),
                confidence_level=self._get_confidence_level(self.confidence),
                evidence_quality=EvidenceQuality.CIRCUMSTANTIAL
            )
        
        # Enregistrer création dans l'historique
        self.record_modification("created", self.metadata.source_agent, "Croyance créée")
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Détermine le niveau de confiance"""
        for level in ConfidenceLevel:
            if level.contains(confidence):
                return level
        return ConfidenceLevel.MEDIUM
    
    def update_confidence(self, new_confidence: float, agent_id: str, reason: str = ""):
        """Met à jour la confiance avec traçabilité"""
        old_confidence = self.confidence
        self.confidence = new_confidence
        
        # Mettre à jour métadonnées
        self.metadata.update_confidence_level(new_confidence)
        
        # Enregistrer modification
        self.record_modification(
            "updated", agent_id, reason,
            previous_confidence=old_confidence,
            new_confidence=new_confidence
        )
    
    def validate(self, agent_id: str, validation_confidence: float = None, notes: str = ""):
        """Valide la croyance"""
        self.valid = True
        self.metadata.set_validation_result(agent_id, "validated", validation_confidence)
        
        if notes:
            self.metadata.add_critique(f"Validation: {notes}")
        
        self.record_modification("validated", agent_id, notes)
    
    def invalidate(self, agent_id: str, reason: str = ""):
        """Invalide la croyance"""
        self.valid = False
        self.metadata.set_validation_result(agent_id, "invalidated")
        self.metadata.truth_maintenance_status = "invalidated"
        
        self.record_modification("invalidated", agent_id, reason)
    
    def add_justification(self, justification_id: str, agent_id: str):
        """Ajoute une justification"""
        if justification_id not in self.justifications:
            self.justifications.append(justification_id)
            self.metadata.justification_chain.append(justification_id)
            
            self.record_modification("justification_added", agent_id, 
                                   f"Justification ajoutée: {justification_id}")
    
    def add_dependency(self, belief_id: str, agent_id: str):
        """Ajoute une dépendance vers une autre croyance"""
        if belief_id not in self.depends_on:
            self.depends_on.append(belief_id)
            
            # Mettre à jour le graphe de dépendances
            if "depends_on" not in self.metadata.dependency_graph:
                self.metadata.dependency_graph["depends_on"] = []
            self.metadata.dependency_graph["depends_on"].append(belief_id)
            
            self.record_modification("dependency_added", agent_id, 
                                   f"Dépendance ajoutée: {belief_id}")
    
    def add_support(self, belief_id: str, agent_id: str):
        """Ajoute une croyance que celle-ci supporte"""
        if belief_id not in self.supports:
            self.supports.append(belief_id)
            
            # Mettre à jour le graphe de dépendances
            if "supports" not in self.metadata.dependency_graph:
                self.metadata.dependency_graph["supports"] = []
            self.metadata.dependency_graph["supports"].append(belief_id)
            
            self.record_modification("support_added", agent_id, 
                                   f"Support ajouté: {belief_id}")
    
    def derive_from_rule(self, rule_name: str, source_beliefs: List[str], agent_id: str):
        """Marque comme dérivée d'une règle"""
        self.is_derived = True
        self.derivation_rule = rule_name
        self.depends_on.extend([b for b in source_beliefs if b not in self.depends_on])
        
        derivation_info = f"Dérivée par règle {rule_name} depuis {source_beliefs}"
        self.computation_trace.append(derivation_info)
        
        self.record_modification("derived", agent_id, derivation_info)
    
    def record_modification(self, modification_type: str, agent_id: str, reason: str = "",
                          previous_confidence: float = None, new_confidence: float = None,
                          metadata: Dict[str, Any] = None):
        """Enregistre une modification dans l'historique"""
        modification = ModificationHistory(
            timestamp=datetime.now(),
            modification_type=modification_type,
            agent_id=agent_id,
            previous_confidence=previous_confidence,
            new_confidence=new_confidence,
            reason=reason,
            metadata=metadata or {}
        )
        
        self.modification_history.append(modification)
        self.metadata.last_modified = datetime.now()
    
    def get_modification_summary(self) -> Dict[str, Any]:
        """Résumé des modifications"""
        if not self.modification_history:
            return {"total_modifications": 0}
        
        summary = {
            "total_modifications": len(self.modification_history),
            "creation_date": self.modification_history[0].timestamp.isoformat(),
            "last_modification": self.modification_history[-1].timestamp.isoformat(),
            "modification_types": {},
            "involved_agents": set(),
            "confidence_evolution": []
        }
        
        for mod in self.modification_history:
            # Compter types de modifications
            mod_type = mod.modification_type
            summary["modification_types"][mod_type] = summary["modification_types"].get(mod_type, 0) + 1
            
            # Agents impliqués
            summary["involved_agents"].add(mod.agent_id)
            
            # Évolution de confiance
            if mod.new_confidence is not None:
                summary["confidence_evolution"].append({
                    "timestamp": mod.timestamp.isoformat(),
                    "confidence": mod.new_confidence,
                    "agent": mod.agent_id
                })
        
        summary["involved_agents"] = list(summary["involved_agents"])
        return summary
    
    def is_consistent_with(self, other_belief: 'ExtendedBeliefModel') -> Dict[str, Any]:
        """Vérifie la cohérence avec une autre croyance"""
        consistency_report = {
            "is_consistent": True,
            "conflict_type": None,
            "conflict_details": {},
            "confidence_difference": abs(self.confidence - other_belief.confidence),
            "validation_consistency": None
        }
        
        # Vérifier contradictions directes
        if (self.belief_name.startswith("not_") and other_belief.belief_name == self.belief_name[4:]) or \
           (other_belief.belief_name.startswith("not_") and self.belief_name == other_belief.belief_name[4:]):
            consistency_report["is_consistent"] = False
            consistency_report["conflict_type"] = "direct_contradiction"
            consistency_report["conflict_details"] = {
                "belief1": self.belief_name,
                "belief2": other_belief.belief_name
            }
        
        # Vérifier cohérence de validation
        if self.valid is not None and other_belief.valid is not None:
            if self.belief_name == other_belief.belief_name and self.valid != other_belief.valid:
                consistency_report["is_consistent"] = False
                consistency_report["conflict_type"] = "validation_conflict"
                consistency_report["validation_consistency"] = False
            else:
                consistency_report["validation_consistency"] = True
        
        # Vérifier différences de confiance importantes
        if consistency_report["confidence_difference"] > 0.5:
            if consistency_report["is_consistent"]:
                consistency_report["conflict_type"] = "confidence_conflict"
            consistency_report["conflict_details"]["high_confidence_difference"] = True
        
        return consistency_report
    
    def to_dict(self, include_history: bool = True) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        result = {
            "belief_id": self.belief_id,
            "belief_name": self.belief_name,
            "content": self.content,
            "confidence": self.confidence,
            "valid": self.valid,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "justifications": self.justifications,
            "depends_on": self.depends_on,
            "supports": self.supports,
            "is_derived": self.is_derived,
            "derivation_rule": self.derivation_rule,
            "computation_trace": self.computation_trace
        }
        
        if include_history:
            result["modification_history"] = [mod.to_dict() for mod in self.modification_history]
            result["modification_summary"] = self.get_modification_summary()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtendedBeliefModel':
        """Création depuis un dictionnaire"""
        # Reconstruction des métadonnées
        metadata = None
        if data.get("metadata"):
            metadata = BeliefMetadata.from_dict(data["metadata"])
        
        # Reconstruction de l'historique
        modification_history = []
        if data.get("modification_history"):
            modification_history = [
                ModificationHistory.from_dict(mod_data) 
                for mod_data in data["modification_history"]
            ]
        
        # Création de l'instance
        belief = cls(
            belief_id=data["belief_id"],
            belief_name=data["belief_name"],
            content=data["content"],
            confidence=data["confidence"],
            valid=data.get("valid"),
            metadata=metadata,
            modification_history=modification_history,
            justifications=data.get("justifications", []),
            depends_on=data.get("depends_on", []),
            supports=data.get("supports", []),
            is_derived=data.get("is_derived", False),
            derivation_rule=data.get("derivation_rule"),
            computation_trace=data.get("computation_trace", [])
        )
        
        return belief
    
    def __str__(self) -> str:
        """Représentation textuelle"""
        status = "✅" if self.valid else "❌" if self.valid is False else "⏳"
        confidence_bar = "█" * int(self.confidence * 10) + "░" * (10 - int(self.confidence * 10))
        
        return (f"{status} {self.belief_name} "
                f"[{confidence_bar}] {self.confidence:.2f} "
                f"({self.metadata.belief_type.value if self.metadata else 'unknown'})")
    
    def __repr__(self) -> str:
        """Représentation détaillée"""
        return (f"ExtendedBeliefModel(id='{self.belief_id}', "
                f"name='{self.belief_name}', confidence={self.confidence}, "
                f"valid={self.valid}, type='{self.metadata.belief_type.value if self.metadata else 'unknown'}')")