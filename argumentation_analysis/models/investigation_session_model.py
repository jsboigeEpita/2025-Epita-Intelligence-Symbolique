"""
Modèle de session d'investigation avec intégration JTMS.
Gère le cycle de vie complet d'une investigation avec checkpoints et historique.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid


class SessionStatus(Enum):
    """États possibles d'une session d'investigation"""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class InvestigationType(Enum):
    """Types d'investigation supportés"""

    CRIMINAL_CASE = "criminal_case"
    FRAUD_DETECTION = "fraud_detection"
    CLUEDO_GAME = "cluedo_game"
    LOGICAL_PUZZLE = "logical_puzzle"
    HYPOTHESIS_TESTING = "hypothesis_testing"
    EVIDENCE_ANALYSIS = "evidence_analysis"


class AgentRole(Enum):
    """Rôles des agents dans l'investigation"""

    INVESTIGATOR = "investigator"  # Formule hypothèses (Sherlock)
    VALIDATOR = "validator"  # Valide et critique (Watson)
    COORDINATOR = "coordinator"  # Coordonne la session
    OBSERVER = "observer"  # Observe sans participer
    EXPERT = "expert"  # Expert domaine spécifique


@dataclass
class SessionCheckpoint:
    """Point de sauvegarde d'une session d'investigation"""

    checkpoint_id: str
    session_id: str
    timestamp: datetime
    checkpoint_name: str
    description: str = ""

    # État des agents
    agents_state: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # État JTMS
    beliefs_snapshot: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    justifications_snapshot: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    consistency_state: Dict[str, Any] = field(default_factory=dict)

    # Métadonnées de session
    session_metadata: Dict[str, Any] = field(default_factory=dict)

    # Statistiques au moment du checkpoint
    statistics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Génère un ID unique si non fourni"""
        if not self.checkpoint_id:
            self.checkpoint_id = (
                f"checkpoint_{uuid.uuid4().hex[:8]}_{int(self.timestamp.timestamp())}"
            )

    def get_size_estimate(self) -> int:
        """Estime la taille du checkpoint en bytes"""
        try:
            data = self.to_dict()
            return len(json.dumps(data, default=str))
        except:
            return 0

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "checkpoint_name": self.checkpoint_name,
            "description": self.description,
            "agents_state": self.agents_state,
            "beliefs_snapshot": self.beliefs_snapshot,
            "justifications_snapshot": self.justifications_snapshot,
            "consistency_state": self.consistency_state,
            "session_metadata": self.session_metadata,
            "statistics": self.statistics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionCheckpoint":
        """Création depuis un dictionnaire"""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            checkpoint_name=data["checkpoint_name"],
            description=data.get("description", ""),
            agents_state=data.get("agents_state", {}),
            beliefs_snapshot=data.get("beliefs_snapshot", {}),
            justifications_snapshot=data.get("justifications_snapshot", {}),
            consistency_state=data.get("consistency_state", {}),
            session_metadata=data.get("session_metadata", {}),
            statistics=data.get("statistics", {}),
        )


@dataclass
class SessionSummary:
    """Résumé d'une session d'investigation"""

    session_id: str
    investigation_type: InvestigationType
    status: SessionStatus
    start_time: datetime
    end_time: Optional[datetime] = None

    # Participants
    participating_agents: Dict[str, AgentRole] = field(default_factory=dict)
    lead_investigator: Optional[str] = None

    # Résultats
    investigation_outcome: Optional[Dict[str, Any]] = None
    final_solution: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None

    # Statistiques d'activité
    total_beliefs_created: int = 0
    total_justifications_added: int = 0
    total_conflicts_resolved: int = 0
    total_synchronizations: int = 0

    # Métriques de performance
    average_confidence: float = 0.0
    consistency_maintained: bool = True
    collaboration_efficiency: float = 0.0  # 0-1 score

    # Investigation specifics
    evidence_processed: List[str] = field(default_factory=list)
    hypotheses_tested: List[str] = field(default_factory=list)
    validation_cycles: int = 0

    @property
    def duration(self) -> Optional[timedelta]:
        """Durée de la session"""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def duration_seconds(self) -> float:
        """Durée en secondes"""
        if self.duration:
            return self.duration.total_seconds()
        return 0.0

    def calculate_success_metrics(self) -> Dict[str, float]:
        """Calcule les métriques de succès"""
        metrics = {
            "completion_rate": 1.0 if self.status == SessionStatus.COMPLETED else 0.0,
            "confidence_score": self.confidence_score or 0.0,
            "collaboration_efficiency": self.collaboration_efficiency,
            "consistency_maintained": 1.0 if self.consistency_maintained else 0.0,
            "evidence_utilization": len(self.evidence_processed)
            / max(1, len(self.evidence_processed)),
            "hypothesis_testing_rate": self.hypotheses_tested
            and len(self.hypotheses_tested) / max(1, self.validation_cycles),
        }

        # Score global (moyenne pondérée)
        weights = {
            "completion_rate": 0.3,
            "confidence_score": 0.25,
            "collaboration_efficiency": 0.2,
            "consistency_maintained": 0.15,
            "evidence_utilization": 0.05,
            "hypothesis_testing_rate": 0.05,
        }

        overall_score = sum(
            metrics[metric] * weights.get(metric, 0) for metric in metrics
        )
        metrics["overall_success_score"] = overall_score

        return metrics

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "session_id": self.session_id,
            "investigation_type": self.investigation_type.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "participating_agents": {
                agent: role.value for agent, role in self.participating_agents.items()
            },
            "lead_investigator": self.lead_investigator,
            "investigation_outcome": self.investigation_outcome,
            "final_solution": self.final_solution,
            "confidence_score": self.confidence_score,
            "total_beliefs_created": self.total_beliefs_created,
            "total_justifications_added": self.total_justifications_added,
            "total_conflicts_resolved": self.total_conflicts_resolved,
            "total_synchronizations": self.total_synchronizations,
            "average_confidence": self.average_confidence,
            "consistency_maintained": self.consistency_maintained,
            "collaboration_efficiency": self.collaboration_efficiency,
            "evidence_processed": self.evidence_processed,
            "hypotheses_tested": self.hypotheses_tested,
            "validation_cycles": self.validation_cycles,
            "duration_seconds": self.duration_seconds,
            "success_metrics": self.calculate_success_metrics(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionSummary":
        """Création depuis un dictionnaire"""
        participating_agents = {
            agent: AgentRole(role)
            for agent, role in data.get("participating_agents", {}).items()
        }

        return cls(
            session_id=data["session_id"],
            investigation_type=InvestigationType(data["investigation_type"]),
            status=SessionStatus(data["status"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=(
                datetime.fromisoformat(data["end_time"])
                if data.get("end_time")
                else None
            ),
            participating_agents=participating_agents,
            lead_investigator=data.get("lead_investigator"),
            investigation_outcome=data.get("investigation_outcome"),
            final_solution=data.get("final_solution"),
            confidence_score=data.get("confidence_score"),
            total_beliefs_created=data.get("total_beliefs_created", 0),
            total_justifications_added=data.get("total_justifications_added", 0),
            total_conflicts_resolved=data.get("total_conflicts_resolved", 0),
            total_synchronizations=data.get("total_synchronizations", 0),
            average_confidence=data.get("average_confidence", 0.0),
            consistency_maintained=data.get("consistency_maintained", True),
            collaboration_efficiency=data.get("collaboration_efficiency", 0.0),
            evidence_processed=data.get("evidence_processed", []),
            hypotheses_tested=data.get("hypotheses_tested", []),
            validation_cycles=data.get("validation_cycles", 0),
        )


@dataclass
class InvestigationSessionModel:
    """
    Modèle principal de session d'investigation avec JTMS intégré.
    Gère le cycle de vie complet d'une investigation collaborative.
    """

    session_id: str
    investigation_type: InvestigationType
    title: str
    description: str = ""

    # État de la session
    status: SessionStatus = SessionStatus.INITIALIZING
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Configuration
    max_duration: Optional[timedelta] = None
    auto_checkpoint_interval: timedelta = field(
        default_factory=lambda: timedelta(minutes=10)
    )
    max_checkpoints: int = 50

    # Agents participants
    registered_agents: Dict[str, AgentRole] = field(default_factory=dict)
    active_agents: Set[str] = field(default_factory=set)
    lead_investigator: Optional[str] = None

    # Contexte d'investigation
    investigation_context: Dict[str, Any] = field(default_factory=dict)
    available_evidence: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    investigation_goals: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

    # État JTMS et croyances
    session_beliefs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    shared_justifications: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    global_consistency_state: Dict[str, Any] = field(default_factory=dict)

    # Historique et checkpoints
    checkpoints: List[SessionCheckpoint] = field(default_factory=list)
    last_checkpoint_time: Optional[datetime] = None

    # Résultats et solutions
    investigation_phases: List[Dict[str, Any]] = field(default_factory=list)
    current_phase: str = "initialization"
    hypotheses_under_test: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validated_conclusions: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Métriques et statistiques
    session_statistics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Initialisation post-création"""
        if not self.session_id:
            self.session_id = f"investigation_{uuid.uuid4().hex[:12]}_{int(self.start_time.timestamp())}"

        self._initialize_session_statistics()
        self.global_consistency_state = {
            "is_consistent": True,
            "last_check": self.start_time,
            "conflict_count": 0,
            "resolution_count": 0,
        }

    def _initialize_session_statistics(self):
        """Initialise les statistiques de session"""
        self.session_statistics = {
            "beliefs_created": 0,
            "beliefs_modified": 0,
            "beliefs_validated": 0,
            "beliefs_invalidated": 0,
            "justifications_added": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "synchronizations_performed": 0,
            "checkpoints_created": 0,
            "agent_interactions": 0,
            "evidence_analyzed": 0,
            "hypotheses_formulated": 0,
            "validation_cycles": 0,
        }

    # === GESTION DES AGENTS ===

    def register_agent(self, agent_id: str, role: AgentRole) -> bool:
        """Enregistre un agent dans la session"""
        if agent_id not in self.registered_agents:
            self.registered_agents[agent_id] = role

            # Définir investigateur principal si c'est le premier investigateur
            if role == AgentRole.INVESTIGATOR and not self.lead_investigator:
                self.lead_investigator = agent_id

            return True
        return False

    def activate_agent(self, agent_id: str) -> bool:
        """Active un agent enregistré"""
        if agent_id in self.registered_agents:
            self.active_agents.add(agent_id)
            return True
        return False

    def deactivate_agent(self, agent_id: str) -> bool:
        """Désactive un agent"""
        if agent_id in self.active_agents:
            self.active_agents.remove(agent_id)
            return True
        return False

    def get_active_investigators(self) -> List[str]:
        """Retourne les investigateurs actifs"""
        return [
            agent_id
            for agent_id in self.active_agents
            if self.registered_agents.get(agent_id) == AgentRole.INVESTIGATOR
        ]

    def get_active_validators(self) -> List[str]:
        """Retourne les validateurs actifs"""
        return [
            agent_id
            for agent_id in self.active_agents
            if self.registered_agents.get(agent_id) == AgentRole.VALIDATOR
        ]

    # === GESTION DES PHASES ===

    def start_session(self) -> bool:
        """Démarre la session d'investigation"""
        if self.status == SessionStatus.INITIALIZING:
            self.status = SessionStatus.ACTIVE
            self.start_time = datetime.now()

            # Créer checkpoint initial
            self.create_checkpoint(
                "session_start", "Début de la session d'investigation"
            )

            # Phase d'initialisation
            self.start_phase("initialization", "Initialisation de l'investigation")

            return True
        return False

    def start_phase(
        self, phase_name: str, description: str = "", phase_data: Dict[str, Any] = None
    ) -> str:
        """Démarre une nouvelle phase d'investigation"""
        phase_id = f"phase_{len(self.investigation_phases)}_{phase_name}"

        phase_info = {
            "phase_id": phase_id,
            "phase_name": phase_name,
            "description": description,
            "start_time": datetime.now(),
            "end_time": None,
            "status": "active",
            "participating_agents": list(self.active_agents),
            "phase_data": phase_data or {},
            "results": {},
            "statistics": {
                "beliefs_in_phase": 0,
                "conflicts_in_phase": 0,
                "validations_in_phase": 0,
            },
        }

        self.investigation_phases.append(phase_info)
        self.current_phase = phase_name

        return phase_id

    def end_phase(self, phase_results: Dict[str, Any] = None) -> bool:
        """Termine la phase actuelle"""
        if self.investigation_phases:
            current_phase_info = self.investigation_phases[-1]
            if current_phase_info["status"] == "active":
                current_phase_info["end_time"] = datetime.now()
                current_phase_info["status"] = "completed"

                if phase_results:
                    current_phase_info["results"] = phase_results

                return True
        return False

    def get_current_phase_info(self) -> Optional[Dict[str, Any]]:
        """Retourne les informations de la phase actuelle"""
        if self.investigation_phases:
            return self.investigation_phases[-1]
        return None

    # === GESTION DES CROYANCES ===

    def add_session_belief(
        self, belief_id: str, belief_data: Dict[str, Any], agent_id: str
    ) -> bool:
        """Ajoute une croyance au niveau session"""
        if belief_id not in self.session_beliefs:
            self.session_beliefs[belief_id] = {
                **belief_data,
                "session_id": self.session_id,
                "created_by": agent_id,
                "created_at": datetime.now().isoformat(),
                "shared_with": [],
                "session_scope": True,
            }

            self.session_statistics["beliefs_created"] += 1
            self._update_phase_statistics("beliefs_in_phase", 1)

            return True
        return False

    def update_session_belief(
        self, belief_id: str, updates: Dict[str, Any], agent_id: str
    ) -> bool:
        """Met à jour une croyance de session"""
        if belief_id in self.session_beliefs:
            self.session_beliefs[belief_id].update(updates)
            self.session_beliefs[belief_id][
                "last_modified"
            ] = datetime.now().isoformat()
            self.session_beliefs[belief_id]["last_modified_by"] = agent_id

            self.session_statistics["beliefs_modified"] += 1
            return True
        return False

    def share_belief_with_agents(
        self, belief_id: str, target_agents: List[str]
    ) -> bool:
        """Partage une croyance avec des agents spécifiques"""
        if belief_id in self.session_beliefs:
            shared_with = self.session_beliefs[belief_id].get("shared_with", [])

            for agent_id in target_agents:
                if agent_id not in shared_with:
                    shared_with.append(agent_id)

            self.session_beliefs[belief_id]["shared_with"] = shared_with
            return True
        return False

    # === GESTION DES HYPOTHÈSES ===

    def add_hypothesis(
        self, hypothesis_id: str, hypothesis_data: Dict[str, Any], formulated_by: str
    ) -> bool:
        """Ajoute une hypothèse à tester"""
        if hypothesis_id not in self.hypotheses_under_test:
            self.hypotheses_under_test[hypothesis_id] = {
                **hypothesis_data,
                "hypothesis_id": hypothesis_id,
                "formulated_by": formulated_by,
                "formulated_at": datetime.now().isoformat(),
                "status": "under_test",
                "validation_attempts": [],
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "confidence_evolution": [],
            }

            self.session_statistics["hypotheses_formulated"] += 1
            return True
        return False

    def validate_hypothesis(
        self, hypothesis_id: str, validation_result: Dict[str, Any], validated_by: str
    ) -> bool:
        """Valide une hypothèse"""
        if hypothesis_id in self.hypotheses_under_test:
            hypothesis = self.hypotheses_under_test[hypothesis_id]

            validation_entry = {
                **validation_result,
                "validated_by": validated_by,
                "validation_timestamp": datetime.now().isoformat(),
            }

            hypothesis["validation_attempts"].append(validation_entry)

            # Mettre à jour le statut selon le résultat
            if validation_result.get("is_valid", False):
                hypothesis["status"] = "validated"

                # Déplacer vers les conclusions validées
                self.validated_conclusions[hypothesis_id] = hypothesis
                del self.hypotheses_under_test[hypothesis_id]

                self.session_statistics["beliefs_validated"] += 1
            elif validation_result.get("is_valid") is False:
                hypothesis["status"] = "invalidated"
                self.session_statistics["beliefs_invalidated"] += 1

            self.session_statistics["validation_cycles"] += 1
            self._update_phase_statistics("validations_in_phase", 1)

            return True
        return False

    # === GESTION DES ÉVIDENCES ===

    def add_evidence(self, evidence_id: str, evidence_data: Dict[str, Any]) -> bool:
        """Ajoute une évidence disponible"""
        if evidence_id not in self.available_evidence:
            self.available_evidence[evidence_id] = {
                **evidence_data,
                "evidence_id": evidence_id,
                "added_at": datetime.now().isoformat(),
                "analyzed_by": [],
                "related_hypotheses": [],
                "analysis_results": {},
            }

            self.session_statistics["evidence_analyzed"] += 1
            return True
        return False

    def link_evidence_to_hypothesis(
        self, evidence_id: str, hypothesis_id: str, relationship: str = "supports"
    ) -> bool:
        """Lie une évidence à une hypothèse"""
        if (
            evidence_id in self.available_evidence
            and hypothesis_id in self.hypotheses_under_test
        ):
            # Mettre à jour l'évidence
            if (
                hypothesis_id
                not in self.available_evidence[evidence_id]["related_hypotheses"]
            ):
                self.available_evidence[evidence_id]["related_hypotheses"].append(
                    hypothesis_id
                )

            # Mettre à jour l'hypothèse
            hypothesis = self.hypotheses_under_test[hypothesis_id]
            if relationship == "supports":
                if evidence_id not in hypothesis["supporting_evidence"]:
                    hypothesis["supporting_evidence"].append(evidence_id)
            elif relationship == "contradicts":
                if evidence_id not in hypothesis["contradicting_evidence"]:
                    hypothesis["contradicting_evidence"].append(evidence_id)

            return True
        return False

    # === GESTION DES CHECKPOINTS ===

    def should_create_checkpoint(self) -> bool:
        """Détermine s'il faut créer un checkpoint automatique"""
        if not self.last_checkpoint_time:
            return True

        time_since_last = datetime.now() - self.last_checkpoint_time
        return time_since_last >= self.auto_checkpoint_interval

    def create_checkpoint(
        self, name: str, description: str = "", force: bool = False
    ) -> Optional[SessionCheckpoint]:
        """Crée un checkpoint de la session"""
        if not force and len(self.checkpoints) >= self.max_checkpoints:
            # Supprimer les plus anciens
            self.checkpoints = self.checkpoints[-(self.max_checkpoints // 2) :]

        checkpoint = SessionCheckpoint(
            checkpoint_id="",  # Sera généré automatiquement
            session_id=self.session_id,
            timestamp=datetime.now(),
            checkpoint_name=name,
            description=description,
            session_metadata={
                "status": self.status.value,
                "current_phase": self.current_phase,
                "active_agents": list(self.active_agents),
                "investigation_type": self.investigation_type.value,
            },
            beliefs_snapshot=dict(self.session_beliefs),
            justifications_snapshot=dict(self.shared_justifications),
            consistency_state=dict(self.global_consistency_state),
            statistics=dict(self.session_statistics),
        )

        self.checkpoints.append(checkpoint)
        self.last_checkpoint_time = checkpoint.timestamp
        self.session_statistics["checkpoints_created"] += 1

        return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restaure un checkpoint"""
        for checkpoint in self.checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                # Restaurer l'état
                self.session_beliefs = dict(checkpoint.beliefs_snapshot)
                self.shared_justifications = dict(checkpoint.justifications_snapshot)
                self.global_consistency_state = dict(checkpoint.consistency_state)

                # Restaurer métadonnées
                metadata = checkpoint.session_metadata
                self.status = SessionStatus(metadata.get("status", "active"))
                self.current_phase = metadata.get("current_phase", "unknown")
                self.active_agents = set(metadata.get("active_agents", []))

                return True
        return False

    # === MÉTRIQUES ET STATISTIQUES ===

    def _update_phase_statistics(self, metric: str, increment: int = 1):
        """Met à jour les statistiques de la phase actuelle"""
        if self.investigation_phases:
            current_phase = self.investigation_phases[-1]
            if current_phase["status"] == "active":
                stats = current_phase.get("statistics", {})
                stats[metric] = stats.get(metric, 0) + increment
                current_phase["statistics"] = stats

    def calculate_session_metrics(self) -> Dict[str, float]:
        """Calcule les métriques de performance de la session"""
        if not self.start_time:
            return {}

        duration = (self.end_time or datetime.now()) - self.start_time
        duration_hours = duration.total_seconds() / 3600

        # Métriques de base
        metrics = {
            "session_duration_hours": duration_hours,
            "beliefs_per_hour": self.session_statistics["beliefs_created"]
            / max(0.1, duration_hours),
            "validation_rate": (
                self.session_statistics["beliefs_validated"]
                / max(1, self.session_statistics["beliefs_created"])
            ),
            "conflict_resolution_rate": (
                self.session_statistics["conflicts_resolved"]
                / max(1, self.session_statistics["conflicts_detected"])
            ),
            "agent_collaboration_score": len(self.active_agents)
            / max(1, len(self.registered_agents)),
            "evidence_utilization": len(self.available_evidence)
            / max(1, self.session_statistics["evidence_analyzed"]),
            "hypothesis_success_rate": (
                len(self.validated_conclusions)
                / max(1, self.session_statistics["hypotheses_formulated"])
            ),
        }

        # Score de performance global
        performance_weights = {
            "validation_rate": 0.25,
            "conflict_resolution_rate": 0.2,
            "agent_collaboration_score": 0.15,
            "hypothesis_success_rate": 0.2,
            "evidence_utilization": 0.1,
            "beliefs_per_hour": 0.1,  # Normaliser entre 0-1
        }

        normalized_beliefs_per_hour = min(
            1.0, metrics["beliefs_per_hour"] / 10.0
        )  # Assume 10/h max

        overall_score = (
            metrics["validation_rate"] * performance_weights["validation_rate"]
            + metrics["conflict_resolution_rate"]
            * performance_weights["conflict_resolution_rate"]
            + metrics["agent_collaboration_score"]
            * performance_weights["agent_collaboration_score"]
            + metrics["hypothesis_success_rate"]
            * performance_weights["hypothesis_success_rate"]
            + metrics["evidence_utilization"]
            * performance_weights["evidence_utilization"]
            + normalized_beliefs_per_hour * performance_weights["beliefs_per_hour"]
        )

        metrics["overall_performance_score"] = overall_score

        return metrics

    def update_consistency_state(self, consistency_report: Dict[str, Any]):
        """Met à jour l'état de cohérence globale"""
        self.global_consistency_state.update(
            {
                **consistency_report,
                "last_check": datetime.now(),
                "check_count": self.global_consistency_state.get("check_count", 0) + 1,
            }
        )

        # Mettre à jour les statistiques
        if not consistency_report.get("is_consistent", True):
            conflicts = consistency_report.get("conflicts", [])
            self.session_statistics["conflicts_detected"] += len(conflicts)
            self._update_phase_statistics("conflicts_in_phase", len(conflicts))

    # === FINALISATION ===

    def complete_session(self, final_results: Dict[str, Any] = None) -> SessionSummary:
        """Finalise la session et génère le résumé"""
        self.end_time = datetime.now()
        self.status = SessionStatus.COMPLETED

        # Terminer la phase actuelle
        self.end_phase(final_results)

        # Checkpoint final
        self.create_checkpoint("session_completed", "Fin de la session d'investigation")

        # Calculer métriques finales
        final_metrics = self.calculate_session_metrics()
        self.performance_metrics.update(final_metrics)

        # Créer le résumé
        summary = SessionSummary(
            session_id=self.session_id,
            investigation_type=self.investigation_type,
            status=self.status,
            start_time=self.start_time,
            end_time=self.end_time,
            participating_agents=dict(self.registered_agents),
            lead_investigator=self.lead_investigator,
            investigation_outcome=final_results,
            final_solution=final_results.get("solution") if final_results else None,
            confidence_score=final_results.get("confidence") if final_results else None,
            total_beliefs_created=self.session_statistics["beliefs_created"],
            total_justifications_added=self.session_statistics["justifications_added"],
            total_conflicts_resolved=self.session_statistics["conflicts_resolved"],
            total_synchronizations=self.session_statistics[
                "synchronizations_performed"
            ],
            average_confidence=final_metrics.get("validation_rate", 0.0),
            consistency_maintained=self.global_consistency_state.get(
                "is_consistent", True
            ),
            collaboration_efficiency=final_metrics.get(
                "agent_collaboration_score", 0.0
            ),
            evidence_processed=list(self.available_evidence.keys()),
            hypotheses_tested=list(self.hypotheses_under_test.keys())
            + list(self.validated_conclusions.keys()),
            validation_cycles=self.session_statistics["validation_cycles"],
        )

        return summary

    def to_dict(self, include_checkpoints: bool = False) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        result = {
            "session_id": self.session_id,
            "investigation_type": self.investigation_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "max_duration": (
                self.max_duration.total_seconds() if self.max_duration else None
            ),
            "auto_checkpoint_interval": self.auto_checkpoint_interval.total_seconds(),
            "max_checkpoints": self.max_checkpoints,
            "registered_agents": {
                agent: role.value for agent, role in self.registered_agents.items()
            },
            "active_agents": list(self.active_agents),
            "lead_investigator": self.lead_investigator,
            "investigation_context": self.investigation_context,
            "available_evidence": self.available_evidence,
            "investigation_goals": self.investigation_goals,
            "constraints": self.constraints,
            "session_beliefs": self.session_beliefs,
            "shared_justifications": self.shared_justifications,
            "global_consistency_state": self.global_consistency_state,
            "last_checkpoint_time": (
                self.last_checkpoint_time.isoformat()
                if self.last_checkpoint_time
                else None
            ),
            "investigation_phases": self.investigation_phases,
            "current_phase": self.current_phase,
            "hypotheses_under_test": self.hypotheses_under_test,
            "validated_conclusions": self.validated_conclusions,
            "session_statistics": self.session_statistics,
            "performance_metrics": self.performance_metrics,
        }

        if include_checkpoints:
            result["checkpoints"] = [cp.to_dict() for cp in self.checkpoints]

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationSessionModel":
        """Création depuis un dictionnaire"""
        # Reconstruction des énumérations
        investigation_type = InvestigationType(data["investigation_type"])
        status = SessionStatus(data["status"])

        registered_agents = {
            agent: AgentRole(role)
            for agent, role in data.get("registered_agents", {}).items()
        }

        # Reconstruction des dates
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = (
            datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
        )
        last_checkpoint_time = (
            datetime.fromisoformat(data["last_checkpoint_time"])
            if data.get("last_checkpoint_time")
            else None
        )

        # Création de l'instance
        session = cls(
            session_id=data["session_id"],
            investigation_type=investigation_type,
            title=data["title"],
            description=data.get("description", ""),
            status=status,
            start_time=start_time,
            end_time=end_time,
            max_duration=(
                timedelta(seconds=data["max_duration"])
                if data.get("max_duration")
                else None
            ),
            auto_checkpoint_interval=timedelta(
                seconds=data.get("auto_checkpoint_interval", 600)
            ),
            max_checkpoints=data.get("max_checkpoints", 50),
            registered_agents=registered_agents,
            active_agents=set(data.get("active_agents", [])),
            lead_investigator=data.get("lead_investigator"),
            investigation_context=data.get("investigation_context", {}),
            available_evidence=data.get("available_evidence", {}),
            investigation_goals=data.get("investigation_goals", []),
            constraints=data.get("constraints", {}),
            session_beliefs=data.get("session_beliefs", {}),
            shared_justifications=data.get("shared_justifications", {}),
            global_consistency_state=data.get("global_consistency_state", {}),
            last_checkpoint_time=last_checkpoint_time,
            investigation_phases=data.get("investigation_phases", []),
            current_phase=data.get("current_phase", "initialization"),
            hypotheses_under_test=data.get("hypotheses_under_test", {}),
            validated_conclusions=data.get("validated_conclusions", {}),
            session_statistics=data.get("session_statistics", {}),
            performance_metrics=data.get("performance_metrics", {}),
        )

        # Reconstruction des checkpoints si présents
        if "checkpoints" in data:
            session.checkpoints = [
                SessionCheckpoint.from_dict(cp_data) for cp_data in data["checkpoints"]
            ]

        return session
