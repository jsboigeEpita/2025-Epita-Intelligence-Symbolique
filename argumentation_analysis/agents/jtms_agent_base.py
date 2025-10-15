"""
Module de base pour l'intégration JTMS avec les agents existants.
Selon les spécifications du RAPPORT_ARCHITECTURE_INTEGRATION_JTMS.md - AXE A
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from abc import ABC, abstractmethod

import semantic_kernel as sk
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions import KernelArguments

# Import du système JTMS existant
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../1.4.1-JTMS"))
from jtms import JTMS, Belief, Justification


class ExtendedBelief:
    """Croyance étendue avec métadonnées pour intégration agents"""

    def __init__(
        self,
        name: str,
        agent_source: str = "unknown",
        context: Dict[str, Any] = None,
        confidence: float = 0.0,
    ):
        self.name = name
        self.agent_source = agent_source
        self.context = context or {}
        self.confidence = confidence
        self.creation_timestamp = datetime.now()
        self.modification_history = []

        # Wrapping du Belief JTMS original
        self._jtms_belief = Belief(name)

    @property
    def valid(self):
        return self._jtms_belief.valid

    @property
    def non_monotonic(self):
        return self._jtms_belief.non_monotonic

    @property
    def justifications(self):
        return self._jtms_belief.justifications

    @property
    def implications(self):
        return self._jtms_belief.implications

    def add_justification(self, justification):
        """Ajoute justification avec traçabilité"""
        self._jtms_belief.add_justification(justification)
        self.record_modification(
            "add_justification",
            {
                "justification_id": id(justification),
                "premises": [str(b) for b in justification.in_list],
                "negatives": [str(b) for b in justification.out_list],
            },
        )

    def record_modification(self, action: str, details: Dict):
        """Enregistre modification pour traçabilité"""
        self.modification_history.append(
            {
                "action": action,
                "timestamp": datetime.now(),
                "details": details,
                "agent": self.agent_source,
            }
        )

    def to_dict(self) -> Dict:
        """Conversion en dictionnaire pour sérialisation"""
        return {
            "name": self.name,
            "agent_source": self.agent_source,
            "context": self.context,
            "confidence": self.confidence,
            "valid": self.valid,
            "non_monotonic": self.non_monotonic,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "modification_count": len(self.modification_history),
        }


class JTMSSession:
    """Session JTMS avec gestion d'état avancée pour agents"""

    def __init__(self, session_id: str, owner_agent: str, strict_mode: bool = False):
        self.session_id = session_id
        self.owner_agent = owner_agent
        self.created_at = datetime.now()
        self.last_modified = datetime.now()

        # Instance JTMS dédiée
        self.jtms = JTMS(strict=strict_mode)

        # Croyances étendues mappées
        self.extended_beliefs: Dict[str, ExtendedBelief] = {}

        # Statistiques de session
        self.total_inferences = 0
        self.consistency_checks = 0
        self.last_consistency_status = True

        # Versioning et checkpoints
        self.version = 1
        self.checkpoints = []

    def add_belief(
        self,
        name: str,
        agent_source: str,
        context: Dict = None,
        confidence: float = 0.0,
    ):
        """Ajoute croyance étendue à la session"""
        if name in self.extended_beliefs:
            # Mise à jour d'une croyance existante
            existing = self.extended_beliefs[name]
            existing.record_modification(
                "updated_by_agent",
                {
                    "new_agent": agent_source,
                    "new_context": context,
                    "new_confidence": confidence,
                },
            )
            if context:
                existing.context.update(context)
            existing.confidence = max(existing.confidence, confidence)
        else:
            # Nouvelle croyance
            extended_belief = ExtendedBelief(name, agent_source, context, confidence)
            self.extended_beliefs[name] = extended_belief
            self.jtms.add_belief(name)

        self.last_modified = datetime.now()
        return self.extended_beliefs[name]

    def add_justification(
        self,
        in_list: List[str],
        out_list: List[str],
        conclusion: str,
        agent_source: str = "unknown",
    ):
        """Ajoute justification avec traçabilité d'agent ET détection de contradiction."""
        # Assurer que toutes les croyances existent
        all_beliefs_in_rule = list(set(in_list + out_list + [conclusion]))
        for belief_name in all_beliefs_in_rule:
            if belief_name not in self.extended_beliefs:
                self.add_belief(belief_name, agent_source, {"auto_created": True})

        # Ajouter à JTMS
        self.jtms.add_justification(in_list, out_list, conclusion)

        # Stratégie de contradiction explicite :
        # Pour une règle A & ~B -> C, on crée une règle de conflit A & B & C -> _CONTRADICTION_
        # Simplifié : si la conclusion C est vraie et une prémisse négative B est vraie, c'est un conflit.
        if out_list:
            contradiction_belief = "_CONTRADICTION_"
            if contradiction_belief not in self.extended_beliefs:
                self.add_belief(contradiction_belief, "system", {"auto_created": True})

            for out_item in out_list:
                # Un conflit survient lorsque toutes les prémisses POSITIVES (in_list)
                # sont vraies EN MEME TEMPS qu'une prémisse NEGATIVE (out_item) est également vraie.
                # Donc, in_list ET out_item -> _CONTRADICTION_
                conflict_in_list = list(set(in_list + [out_item]))
                self.jtms.add_justification(conflict_in_list, [], contradiction_belief)

        # Traçabilité sur la croyance conclusion
        if conclusion in self.extended_beliefs:
            self.extended_beliefs[conclusion].record_modification(
                "justification_added",
                {
                    "in_list": in_list,
                    "out_list": out_list,
                    "agent_source": agent_source,
                },
            )

        self.total_inferences += 1
        self.last_modified = datetime.now()

    def set_fact(self, name: str, is_true: bool = True):
        """Déclare une croyance comme étant un fait (lui assigne une validité sans justification)."""
        if name not in self.jtms.beliefs:
            # Si on essaie de mettre un fait sur une croyance qui n'a pas été ajoutée,
            # on l'ajoute implicitement.
            self.add_belief(
                name, "system_fact", {"description": "Auto-added as a fact"}
            )

        self.jtms.set_belief_validity(name, is_true)
        # La propagation est gérée par set_belief_validity dans la lib JTMS
        self.last_modified = datetime.now()

    def explain_belief(self, belief_name: str) -> str:
        """Explication enrichie avec contexte agent"""
        if belief_name not in self.extended_beliefs:
            return f"Croyance '{belief_name}' inconnue dans cette session"

        # Explication JTMS de base
        base_explanation = self.jtms.explain_belief(belief_name)

        # Enrichissement avec métadonnées
        extended_belief = self.extended_beliefs[belief_name]
        enriched_explanation = f"""
=== EXPLICATION ENRICHIE JTMS ===
Croyance: {belief_name}
Agent source: {extended_belief.agent_source}
Confiance: {extended_belief.confidence:.2f}
Contexte: {json.dumps(extended_belief.context, ensure_ascii=False)}
Créée le: {extended_belief.creation_timestamp}
Modifications: {len(extended_belief.modification_history)}

=== JUSTIFICATIONS JTMS ===
{base_explanation}
"""
        return enriched_explanation

    def check_consistency(self) -> Dict:
        """Vérifie la cohérence en propageant les justifications et en détectant les contradictions."""
        self.consistency_checks += 1

        # Force la propagation des valeurs de vérité à travers le réseau de justifications.
        # C'est cette étape qui révèle les contradictions latentes.
        self.jtms.update_non_monotonic_befielfs()

        conflicts = []
        contradiction_belief_name = "_CONTRADICTION_"
        if (
            contradiction_belief_name in self.jtms.beliefs
            and self.jtms.beliefs[contradiction_belief_name].valid
        ):
            # La croyance _CONTRADICTION_ est valide, donc le système est incohérent.
            # Maintenant, trouver quelles justifications la supportent.
            contradiction_belief = self.jtms.beliefs[contradiction_belief_name]
            for justif in contradiction_belief.justifications:
                if all(self.jtms.beliefs[b.name].valid for b in justif.in_list):
                    conflicting_beliefs = [b.name for b in justif.in_list]
                    conflicts.append(
                        {
                            "type": "explicit_contradiction",
                            "beliefs": conflicting_beliefs,
                            "agents": list(
                                set(
                                    self.extended_beliefs[b].agent_source
                                    for b in conflicting_beliefs
                                    if b in self.extended_beliefs
                                )
                            ),
                        }
                    )

        # Détection de cycles non-monotoniques (qui est une forme d'incohérence/ambiguité)
        non_monotonic_beliefs = [
            name for name, belief in self.jtms.beliefs.items() if belief.non_monotonic
        ]

        is_consistent = not conflicts
        self.last_consistency_status = is_consistent

        return {
            "is_consistent": is_consistent,
            "conflicts": conflicts,
            "non_monotonic_beliefs": non_monotonic_beliefs,
            "total_beliefs": len(self.extended_beliefs),
            "total_justifications": sum(
                len(b.justifications) for b in self.jtms.beliefs.values()
            ),
            "check_timestamp": datetime.now().isoformat(),
        }

    def create_checkpoint(self, name: str) -> str:
        """Crée point de sauvegarde de l'état"""
        checkpoint_id = (
            f"checkpoint_{len(self.checkpoints)}_{int(datetime.now().timestamp())}"
        )

        state_snapshot = {
            "checkpoint_id": checkpoint_id,
            "name": name,
            "timestamp": datetime.now(),
            "version": self.version,
            "beliefs_count": len(self.extended_beliefs),
            "beliefs_state": {
                name: belief.to_dict() for name, belief in self.extended_beliefs.items()
            },
        }

        self.checkpoints.append(state_snapshot)
        return checkpoint_id

    def get_session_summary(self) -> Dict:
        """Résumé complet de la session"""
        return {
            "session_id": self.session_id,
            "owner_agent": self.owner_agent,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "version": self.version,
            "beliefs_count": len(self.extended_beliefs),
            "total_inferences": self.total_inferences,
            "consistency_checks": self.consistency_checks,
            "last_consistency_status": self.last_consistency_status,
            "checkpoints_count": len(self.checkpoints),
        }


class JTMSAgentBase(ABC):
    """
    Classe de base pour l'intégration JTMS avec les agents existants.
    Fournit l'interface standardisée pour la communication inter-agents.
    """

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str,
        session_id: str = None,
        strict_mode: bool = False,
    ):
        self._kernel = kernel
        self._agent_name = agent_name
        self._logger = logging.getLogger(f"jtms_agent.{agent_name}")

        # Session JTMS dédiée à cet agent
        self._session_id = (
            session_id or f"{agent_name}_{int(datetime.now().timestamp())}"
        )
        self._jtms_session = JTMSSession(self._session_id, agent_name, strict_mode)

        self._logger.info(
            f"JTMSAgentBase initialisé pour {agent_name} (session: {self._session_id})"
        )

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def jtms_session(self) -> JTMSSession:
        return self._jtms_session

    @property
    def agent_name(self) -> str:
        return self._agent_name

    # === MÉTHODES PRINCIPALES JTMS ===

    def add_belief(
        self, belief_name: str, context: Dict = None, confidence: float = 0.0
    ) -> ExtendedBelief:
        """Ajoute une croyance dans le JTMS de l'agent"""
        self._logger.info(f"Ajout croyance '{belief_name}' par {self._agent_name}")
        return self._jtms_session.add_belief(
            belief_name, self._agent_name, context, confidence
        )

    def add_justification(
        self, in_list: List[str], out_list: List[str], conclusion: str
    ) -> None:
        """Ajoute une justification dans le JTMS"""
        self._logger.info(
            f"Ajout justification: {in_list} ∧ ¬{out_list} → {conclusion}"
        )
        self._jtms_session.add_justification(
            in_list, out_list, conclusion, self._agent_name
        )

    def set_fact(self, belief_name: str, is_true: bool = True):
        """Déclare une croyance comme un fait dans le JTMS de l'agent."""
        self._logger.info(f"Déclaration du fait '{belief_name}' à {is_true}")
        self._jtms_session.set_fact(belief_name, is_true)

    def validate_justification(
        self, in_list: List[str], out_list: List[str], conclusion: str
    ) -> bool:
        """Valide qu'une justification est logiquement cohérente"""
        try:
            # Vérification que toutes les prémisses existent
            for belief_name in in_list + out_list:
                if belief_name not in self._jtms_session.extended_beliefs:
                    self._logger.warning(
                        f"Croyance '{belief_name}' inconnue pour validation"
                    )
                    return False

            # Vérification logique basique
            valid_premises = all(
                self._jtms_session.jtms.beliefs[name].valid
                for name in in_list
                if name in self._jtms_session.jtms.beliefs
            )

            invalid_negatives = all(
                not self._jtms_session.jtms.beliefs[name].valid
                for name in out_list
                if name in self._jtms_session.jtms.beliefs
            )

            return valid_premises and invalid_negatives

        except Exception as e:
            self._logger.error(f"Erreur validation justification: {e}")
            return False

    def explain_belief(self, belief_name: str) -> str:
        """Explique une croyance avec traçabilité complète"""
        return self._jtms_session.explain_belief(belief_name)

    def get_belief_confidence(self, belief_name: str) -> float:
        """Récupère le score de confiance d'une croyance"""
        if belief_name in self._jtms_session.extended_beliefs:
            return self._jtms_session.extended_beliefs[belief_name].confidence
        return 0.0

    def update_belief_confidence(self, belief_name: str, new_confidence: float) -> None:
        """Met à jour le score de confiance d'une croyance"""
        if belief_name in self._jtms_session.extended_beliefs:
            old_confidence = self._jtms_session.extended_beliefs[belief_name].confidence
            self._jtms_session.extended_beliefs[belief_name].confidence = new_confidence
            self._jtms_session.extended_beliefs[belief_name].record_modification(
                "confidence_updated",
                {"old_confidence": old_confidence, "new_confidence": new_confidence},
            )
            self._logger.info(
                f"Confiance mise à jour pour '{belief_name}': {old_confidence} → {new_confidence}"
            )

    def check_consistency(self) -> Dict:
        """Vérifie la cohérence du système de croyances"""
        self._logger.info(f"Vérification cohérence pour {self._agent_name}")
        return self._jtms_session.check_consistency()

    def create_checkpoint(self, checkpoint_name: str) -> str:
        """Crée un point de sauvegarde de l'état JTMS"""
        checkpoint_id = self._jtms_session.create_checkpoint(checkpoint_name)
        self._logger.info(f"Checkpoint créé: {checkpoint_id}")
        return checkpoint_id

    # === MÉTHODES DE COMMUNICATION INTER-AGENTS ===

    def export_session_state(self) -> Dict:
        """Exporte l'état JTMS pour communication inter-agents"""
        beliefs_export = {}
        for name, extended_belief in self._jtms_session.extended_beliefs.items():
            beliefs_export[name] = {
                "name": name,
                "valid": extended_belief.valid,
                "non_monotonic": extended_belief.non_monotonic,
                "agent_source": extended_belief.agent_source,
                "context": extended_belief.context,
                "confidence": extended_belief.confidence,
                "justifications": [
                    {
                        "in_list": [str(b) for b in j.in_list],
                        "out_list": [str(b) for b in j.out_list],
                        "conclusion": str(j.conclusion),
                    }
                    for j in extended_belief.justifications
                ],
            }

        return {
            "session_summary": self._jtms_session.get_session_summary(),
            "beliefs": beliefs_export,
            "export_timestamp": datetime.now().isoformat(),
        }

    def import_beliefs_from_agent(
        self, other_agent_state: Dict, conflict_resolution: str = "merge"
    ) -> Dict:
        """Importe les croyances d'un autre agent avec résolution de conflits"""
        import_report = {"imported_beliefs": [], "conflicts": [], "skipped": []}

        other_beliefs = other_agent_state.get("beliefs", {})

        for belief_name, belief_data in other_beliefs.items():
            try:
                if belief_name in self._jtms_session.extended_beliefs:
                    # Conflit détecté
                    existing = self._jtms_session.extended_beliefs[belief_name]
                    conflict = {
                        "belief_name": belief_name,
                        "local_agent": existing.agent_source,
                        "remote_agent": belief_data["agent_source"],
                        "local_confidence": existing.confidence,
                        "remote_confidence": belief_data["confidence"],
                    }
                    import_report["conflicts"].append(conflict)

                    if conflict_resolution == "merge":
                        # Prendre la confiance la plus élevée
                        if belief_data["confidence"] > existing.confidence:
                            self.update_belief_confidence(
                                belief_name, belief_data["confidence"]
                            )
                            existing.context.update(belief_data.get("context", {}))
                            import_report["imported_beliefs"].append(belief_name)
                    elif conflict_resolution == "skip":
                        import_report["skipped"].append(belief_name)
                        continue
                else:
                    # Nouvelle croyance - import direct
                    self.add_belief(
                        belief_name,
                        context={
                            **belief_data.get("context", {}),
                            "imported_from": belief_data["agent_source"],
                        },
                        confidence=belief_data["confidence"],
                    )
                    import_report["imported_beliefs"].append(belief_name)

            except Exception as e:
                self._logger.error(f"Erreur import croyance '{belief_name}': {e}")
                import_report["skipped"].append(belief_name)

        self._logger.info(
            f"Import terminé: {len(import_report['imported_beliefs'])} importées, "
            f"{len(import_report['conflicts'])} conflits, "
            f"{len(import_report['skipped'])} ignorées"
        )

        return import_report

    # === MÉTHODES ABSTRAITES POUR SPÉCIALISATION ===

    @abstractmethod
    async def process_jtms_inference(self, context: str) -> Dict:
        """Méthode abstraite pour traitement spécialisé selon l'agent"""
        pass

    @abstractmethod
    async def validate_reasoning_chain(self, chain: List[Dict]) -> Dict:
        """Méthode abstraite pour validation de chaînes de raisonnement"""
        pass

    # === MÉTHODES UTILITAIRES ===

    def get_all_beliefs(self) -> Dict[str, ExtendedBelief]:
        """Récupère toutes les croyances de l'agent"""
        return self._jtms_session.extended_beliefs.copy()

    def get_valid_beliefs(self) -> List[str]:
        """Récupère les noms des croyances valides"""
        return [
            name
            for name, belief in self._jtms_session.extended_beliefs.items()
            if belief.valid is True
        ]

    def get_session_statistics(self) -> Dict:
        """Statistiques détaillées de la session JTMS"""
        summary = self._jtms_session.get_session_summary()
        consistency = self.check_consistency()

        return {
            **summary,
            "consistency_status": consistency,
            "beliefs_by_confidence": self._get_beliefs_by_confidence_range(),
            "recent_modifications": self._get_recent_modifications(limit=5),
        }

    def _get_beliefs_by_confidence_range(self) -> Dict:
        """Répartition des croyances par niveau de confiance"""
        ranges = {"low": 0, "medium": 0, "high": 0, "very_high": 0}

        for belief in self._jtms_session.extended_beliefs.values():
            if belief.confidence < 0.25:
                ranges["low"] += 1
            elif belief.confidence < 0.5:
                ranges["medium"] += 1
            elif belief.confidence < 0.75:
                ranges["high"] += 1
            else:
                ranges["very_high"] += 1

        return ranges

    def _get_recent_modifications(self, limit: int = 5) -> List[Dict]:
        """Récupère les modifications récentes"""
        all_modifications = []

        for belief in self._jtms_session.extended_beliefs.values():
            for mod in belief.modification_history:
                all_modifications.append(
                    {
                        "belief_name": belief.name,
                        "action": mod["action"],
                        "timestamp": mod["timestamp"],
                        "agent": mod["agent"],
                        "details": mod["details"],
                    }
                )

        # Trier par timestamp décroissant et limiter
        all_modifications.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_modifications[:limit]
