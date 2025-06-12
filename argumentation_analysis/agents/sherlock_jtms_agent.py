"""
Agent Sherlock enrichi avec JTMS pour formulation d'hypothèses et déductions.
Selon les spécifications du RAPPORT_ARCHITECTURE_INTEGRATION_JTMS.md - AXE A
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import semantic_kernel as sk
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments

from .jtms_agent_base import JTMSAgentBase, ExtendedBelief
from .core.pm.sherlock_enquete_agent import SherlockEnqueteAgent

class HypothesisTracker:
    """Gestionnaire des hypothèses avec traçabilité JTMS"""
    
    def __init__(self, jtms_session):
        self.jtms_session = jtms_session
        self.hypothesis_counter = 0
        self.active_hypotheses = {}
        self.hypothesis_networks = {}
        
    def create_hypothesis(self, description: str, context: Dict = None,
                         confidence: float = 0.5, agent_source: str = "unknown") -> str:
        """Crée une nouvelle hypothèse avec ID unique"""
        self.hypothesis_counter += 1
        hypothesis_id = f"hypothesis_{self.hypothesis_counter}"
        
        # Croyance JTMS pour l'hypothèse
        hypothesis_belief = self.jtms_session.add_belief(
            hypothesis_id,
            context={
                "type": "hypothesis",
                "description": description,
                "creation_method": "sherlock_deduction",
                **(context or {})
            },
            confidence=confidence,
            agent_source=agent_source
        )
        
        self.active_hypotheses[hypothesis_id] = {
            "id": hypothesis_id,
            "description": description,
            "confidence": confidence,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "status": "active",
            "created_at": datetime.now()
        }
        
        return hypothesis_id
    
    def link_evidence_to_hypothesis(self, hypothesis_id: str, evidence_id: str, 
                                   support_type: str = "positive") -> None:
        """Lie une évidence à une hypothèse via justification JTMS"""
        if hypothesis_id not in self.active_hypotheses:
            raise ValueError(f"Hypothèse inconnue: {hypothesis_id}")
        
        if support_type == "positive":
            # Évidence positive soutient l'hypothèse
            self.jtms_session.add_justification([evidence_id], [], hypothesis_id)
            self.active_hypotheses[hypothesis_id]["supporting_evidence"].append(evidence_id)
        else:
            # Évidence négative contredit l'hypothèse
            self.jtms_session.add_justification([], [evidence_id], f"not_{hypothesis_id}")
            self.active_hypotheses[hypothesis_id]["contradicting_evidence"].append(evidence_id)
    
    def evaluate_hypothesis_strength(self, hypothesis_id: str) -> Dict:
        """Évalue la force d'une hypothèse basée sur ses justifications"""
        if hypothesis_id not in self.active_hypotheses:
            return {"error": "Hypothèse inconnue"}
        
        hypothesis_data = self.active_hypotheses[hypothesis_id]
        supporting_count = len(hypothesis_data["supporting_evidence"])
        contradicting_count = len(hypothesis_data["contradicting_evidence"])
        
        # Score basé sur le ratio support/contradiction
        if supporting_count + contradicting_count == 0:
            strength_score = hypothesis_data["confidence"]
        else:
            strength_score = supporting_count / (supporting_count + contradicting_count)
        
        # Vérifier le statut JTMS
        belief_valid = self.jtms_session.jtms.beliefs.get(hypothesis_id, {}).valid
        
        return {
            "hypothesis_id": hypothesis_id,
            "strength_score": strength_score,
            "supporting_evidence_count": supporting_count,
            "contradicting_evidence_count": contradicting_count,
            "jtms_validity": belief_valid,
            "status": "strong" if strength_score > 0.7 else "weak" if strength_score < 0.3 else "moderate"
        }

class EvidenceManager:
    """Gestionnaire des évidences avec classification automatique"""
    
    def __init__(self, jtms_session):
        self.jtms_session = jtms_session
        self.evidence_counter = 0
        self.evidence_catalog = {}
        
    def add_evidence(self, evidence_data: Dict) -> str:
        """Ajoute une nouvelle évidence au système"""
        self.evidence_counter += 1
        evidence_id = f"evidence_{self.evidence_counter}"
        
        evidence_type = evidence_data.get("type", "unknown")
        reliability = evidence_data.get("reliability", 0.5)
        description = evidence_data.get("description", "")
        
        # Croyance JTMS pour l'évidence
        evidence_belief = self.jtms_session.add_belief(
            evidence_id,
            context={
                "type": "evidence",
                "evidence_type": evidence_type,
                "description": description,
                "reliability": reliability,
                "source": evidence_data.get("source", "unknown")
            },
            confidence=reliability
        )
        
        self.evidence_catalog[evidence_id] = {
            "id": evidence_id,
            "type": evidence_type,
            "description": description,
            "reliability": reliability,
            "added_at": datetime.now(),
            "linked_hypotheses": []
        }
        
        return evidence_id
    
    def get_supporting_evidence(self, min_reliability: float = 0.3) -> List[str]:
        """Récupère les évidences fiables pour justifications"""
        return [
            evidence_id for evidence_id, data in self.evidence_catalog.items()
            if data["reliability"] >= min_reliability
        ]
    
    def classify_evidence_relevance(self, evidence_id: str, context: str) -> str:
        """Classifie la pertinence d'une évidence dans un contexte donné"""
        if evidence_id not in self.evidence_catalog:
            return "unknown"
        
        evidence = self.evidence_catalog[evidence_id]
        
        # Classification simple basée sur mots-clés
        context_lower = context.lower()
        description_lower = evidence["description"].lower()
        
        # Recherche de correspondances
        common_words = set(context_lower.split()) & set(description_lower.split())
        relevance_score = len(common_words) / max(len(context_lower.split()), 1)
        
        if relevance_score > 0.5:
            return "highly_relevant"
        elif relevance_score > 0.2:
            return "moderately_relevant"
        else:
            return "low_relevance"

class SherlockJTMSAgent(JTMSAgentBase):
    """
    Agent Sherlock enrichi avec JTMS pour formulation d'hypothèses et déductions.
    Spécialisé dans la collecte d'indices et génération d'hypothèses avec traçabilité.
    """
    
    def __init__(self, kernel: Kernel, agent_name: str = "Sherlock_JTMS", 
                 system_prompt: Optional[str] = None, **kwargs):
        super().__init__(kernel, agent_name, strict_mode=False)
        
        # Intégration avec l'agent Sherlock existant
        self._base_sherlock = SherlockEnqueteAgent(kernel, agent_name, system_prompt)
        
        # Gestionnaires spécialisés JTMS
        self._hypothesis_tracker = HypothesisTracker(self._jtms_session)
        self._evidence_manager = EvidenceManager(self._jtms_session)
        
        # Configuration spécifique Sherlock
        self._deduction_style = "intuitive_logical"
        self._max_concurrent_hypotheses = 5
        
        self._logger.info(f"SherlockJTMSAgent initialisé avec JTMS intégré")
    
    # === MÉTHODES SPÉCIALISÉES SHERLOCK ===
    
    async def formulate_hypothesis(self, context: str, evidence_ids: List[str] = None) -> Dict:
        """Formule une hypothèse basée sur le contexte et l'enregistre dans JTMS"""
        self._logger.info(f"Formulation d'hypothèse pour contexte: {context[:100]}...")
        
        try:
            # Générer hypothèse via l'agent Sherlock de base
            base_hypothesis = await self._base_sherlock.process_message(
                f"Formulez une hypothèse pour cette situation: {context}"
            )
            
            # Créer hypothèse dans le tracker JTMS
            hypothesis_id = self._hypothesis_tracker.create_hypothesis(
                description=base_hypothesis,
                context={"source_context": context},
                confidence=0.7,  # Confiance initiale de Sherlock
                agent_source=self.agent_name
            )
            
            # Lier les évidences si fournies
            if evidence_ids:
                for evidence_id in evidence_ids:
                    if evidence_id in self._evidence_manager.evidence_catalog:
                        self._hypothesis_tracker.link_evidence_to_hypothesis(
                            hypothesis_id, evidence_id, "positive"
                        )
            
            # Générer justification JTMS
            justification_chain = self.explain_belief(hypothesis_id)
            
            # Calculer confiance basée sur évidences
            hypothesis_strength = self._hypothesis_tracker.evaluate_hypothesis_strength(hypothesis_id)
            
            result = {
                "hypothesis_id": hypothesis_id,
                "hypothesis": base_hypothesis,
                "confidence": hypothesis_strength["strength_score"],
                "justification_chain": justification_chain,
                "supporting_evidence": evidence_ids or [],
                "jtms_validity": hypothesis_strength["jtms_validity"],
                "creation_timestamp": datetime.now().isoformat()
            }
            
            self._logger.info(f"Hypothèse créée: {hypothesis_id} (confiance: {hypothesis_strength['strength_score']:.2f})")
            return result
            
        except Exception as e:
            self._logger.error(f"Erreur formulation hypothèse: {e}")
            return {"error": str(e), "context": context}
    
    async def analyze_clues(self, clues: List[Dict]) -> Dict:
        """Analyse des indices avec classification et intégration JTMS"""
        self._logger.info(f"Analyse de {len(clues)} indices")
        
        analysis_results = {
            "processed_clues": [],
            "new_evidence_ids": [],
            "relevance_scores": {},
            "generated_hypotheses": [],
            "jtms_inferences": []
        }
        
        try:
            for i, clue in enumerate(clues):
                clue_id = f"clue_{i}_{int(datetime.now().timestamp())}"
                
                # Convertir indice en évidence JTMS
                evidence_id = self._evidence_manager.add_evidence({
                    "type": clue.get("type", "physical_evidence"),
                    "description": clue.get("description", ""),
                    "reliability": clue.get("reliability", 0.6),
                    "source": clue.get("source", "investigation")
                })
                
                analysis_results["new_evidence_ids"].append(evidence_id)
                
                # Classifier la pertinence
                context = clue.get("context", "")
                relevance = self._evidence_manager.classify_evidence_relevance(evidence_id, context)
                analysis_results["relevance_scores"][evidence_id] = relevance
                
                # Si indice très pertinent, générer hypothèse
                if relevance == "highly_relevant":
                    hypothesis_result = await self.formulate_hypothesis(
                        f"Indice: {clue.get('description', '')}",
                        [evidence_id]
                    )
                    analysis_results["generated_hypotheses"].append(hypothesis_result)
                
                analysis_results["processed_clues"].append({
                    "clue_id": clue_id,
                    "evidence_id": evidence_id,
                    "relevance": relevance,
                    "integrated_jtms": True
                })
            
            # Inférences automatiques JTMS
            self._trigger_automatic_inferences()
            analysis_results["jtms_inferences"] = self._get_recent_inferences()
            
            self._logger.info(f"Analyse terminée: {len(analysis_results['new_evidence_ids'])} évidences, "
                             f"{len(analysis_results['generated_hypotheses'])} hypothèses")
            
            return analysis_results
            
        except Exception as e:
            self._logger.error(f"Erreur analyse indices: {e}")
            return {"error": str(e), "clues_count": len(clues)}
    
    async def deduce_solution(self, investigation_context: Dict) -> Dict:
        """Déduction de solution basée sur toutes les hypothèses et évidences"""
        self._logger.info("Déduction de solution finale")
        
        try:
            # Évaluer toutes les hypothèses actives
            hypothesis_evaluations = []
            for hypothesis_id in self._hypothesis_tracker.active_hypotheses:
                evaluation = self._hypothesis_tracker.evaluate_hypothesis_strength(hypothesis_id)
                hypothesis_evaluations.append(evaluation)
            
            # Trier par force décroissante
            hypothesis_evaluations.sort(key=lambda x: x["strength_score"], reverse=True)
            
            # Prendre la meilleure hypothèse comme base de solution
            if hypothesis_evaluations:
                best_hypothesis = hypothesis_evaluations[0]
                
                # Générer solution détaillée via Sherlock de base
                solution_prompt = f"""
                Basé sur l'hypothèse principale: {self._hypothesis_tracker.active_hypotheses[best_hypothesis['hypothesis_id']]['description']}
                Avec {best_hypothesis['supporting_evidence_count']} évidences de support.
                Contexte: {investigation_context}
                
                Proposez une solution finale détaillée.
                """
                
                detailed_solution = await self._base_sherlock.process_message(solution_prompt)
                
                # Vérification de cohérence JTMS
                consistency_check = self.check_consistency()
                
                solution_result = {
                    "primary_hypothesis": best_hypothesis,
                    "detailed_solution": detailed_solution,
                    "confidence_score": best_hypothesis["strength_score"],
                    "supporting_evidence_count": best_hypothesis["supporting_evidence_count"],
                    "jtms_consistency": consistency_check["is_consistent"],
                    "alternative_hypotheses": hypothesis_evaluations[1:3],  # Top 2 alternatives
                    "deduction_timestamp": datetime.now().isoformat(),
                    "total_inferences": self._jtms_session.total_inferences
                }
                
                self._logger.info(f"Solution déduite avec confiance {best_hypothesis['strength_score']:.2f}")
                return solution_result
            else:
                return {
                    "error": "Aucune hypothèse disponible pour déduction",
                    "context": investigation_context
                }
                
        except Exception as e:
            self._logger.error(f"Erreur déduction solution: {e}")
            return {"error": str(e)}
    
    async def validate_hypothesis_against_evidence(self, hypothesis_id: str, 
                                                  new_evidence: Dict) -> Dict:
        """Valide une hypothèse contre une nouvelle évidence"""
        self._logger.info(f"Validation hypothèse {hypothesis_id} contre nouvelle évidence")
        
        try:
            if hypothesis_id not in self._hypothesis_tracker.active_hypotheses:
                return {"error": f"Hypothèse {hypothesis_id} inconnue"}
            
            # Ajouter nouvelle évidence
            evidence_id = self._evidence_manager.add_evidence(new_evidence)
            
            # Évaluer compatibilité avec hypothèse
            hypothesis_desc = self._hypothesis_tracker.active_hypotheses[hypothesis_id]["description"]
            evidence_desc = new_evidence.get("description", "")
            
            # Classification de support/contradiction (simplifié)
            compatibility_score = self._calculate_compatibility(hypothesis_desc, evidence_desc)
            
            if compatibility_score > 0.6:
                # Évidence supporte l'hypothèse
                self._hypothesis_tracker.link_evidence_to_hypothesis(
                    hypothesis_id, evidence_id, "positive"
                )
                validation_result = "supports"
            elif compatibility_score < 0.4:
                # Évidence contredit l'hypothèse
                self._hypothesis_tracker.link_evidence_to_hypothesis(
                    hypothesis_id, evidence_id, "negative"
                )
                validation_result = "contradicts"
            else:
                # Évidence neutre
                validation_result = "neutral"
            
            # Réévaluer force de l'hypothèse
            updated_strength = self._hypothesis_tracker.evaluate_hypothesis_strength(hypothesis_id)
            
            return {
                "hypothesis_id": hypothesis_id,
                "evidence_id": evidence_id,
                "validation_result": validation_result,
                "compatibility_score": compatibility_score,
                "updated_strength": updated_strength,
                "jtms_updated": True
            }
            
        except Exception as e:
            self._logger.error(f"Erreur validation hypothèse: {e}")
            return {"error": str(e)}
    
    async def update_with_evidence(self, evidence: Dict) -> Dict:
        """Met à jour JTMS avec nouvelles évidences et propage les changements"""
        self._logger.info("Mise à jour avec nouvelle évidence")
        
        try:
            # Ajouter évidence au système
            evidence_id = self._evidence_manager.add_evidence(evidence)
            
            # Trouver hypothèses affectées
            affected_hypotheses = []
            for hypothesis_id in self._hypothesis_tracker.active_hypotheses:
                validation = await self.validate_hypothesis_against_evidence(hypothesis_id, evidence)
                if validation.get("validation_result") != "neutral":
                    affected_hypotheses.append(validation)
            
            # Propagation automatique JTMS
            self._trigger_automatic_inferences()
            
            # Détecter nouvelles inférences
            new_inferences = self._get_recent_inferences()
            
            return {
                "evidence_added": evidence_id,
                "affected_hypotheses": affected_hypotheses,
                "new_inferences": new_inferences,
                "total_beliefs": len(self._jtms_session.extended_beliefs),
                "update_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self._logger.error(f"Erreur mise à jour évidence: {e}")
            return {"error": str(e)}
    
    async def generate_investigation_leads(self, current_state: Dict) -> List[Dict]:
        """Génère des pistes d'investigation basées sur l'état JTMS actuel"""
        self._logger.info("Génération de pistes d'investigation")
        
        try:
            leads = []
            
            # Analyser les hypothèses faibles pour suggestions d'amélioration
            for hypothesis_id in self._hypothesis_tracker.active_hypotheses:
                strength = self._hypothesis_tracker.evaluate_hypothesis_strength(hypothesis_id)
                
                if strength["strength_score"] < 0.5:
                    leads.append({
                        "type": "strengthen_hypothesis",
                        "hypothesis_id": hypothesis_id,
                        "current_strength": strength["strength_score"],
                        "suggestion": f"Rechercher plus d'évidences pour {hypothesis_id}",
                        "priority": "medium"
                    })
            
            # Identifier les croyances non justifiées
            unjustified_beliefs = [
                name for name, belief in self._jtms_session.extended_beliefs.items()
                if not belief.justifications and belief.valid is None
            ]
            
            for belief_name in unjustified_beliefs[:3]:  # Limiter à 3
                leads.append({
                    "type": "justify_belief",
                    "belief_name": belief_name,
                    "suggestion": f"Trouver justification pour {belief_name}",
                    "priority": "high"
                })
            
            # Détecter contradictions potentielles à résoudre
            consistency_check = self.check_consistency()
            for conflict in consistency_check.get("conflicts", []):
                leads.append({
                    "type": "resolve_conflict",
                    "conflicting_beliefs": conflict["beliefs"],
                    "suggestion": f"Résoudre contradiction entre {conflict['beliefs']}",
                    "priority": "critical"
                })
            
            self._logger.info(f"Générées {len(leads)} pistes d'investigation")
            return leads
            
        except Exception as e:
            self._logger.error(f"Erreur génération pistes: {e}")
            return []
    
    # === IMPLÉMENTATION DES MÉTHODES ABSTRAITES ===
    
    async def process_jtms_inference(self, context: str) -> Dict:
        """Traitement spécialisé Sherlock pour inférences JTMS"""
        return await self.formulate_hypothesis(context)
    
    async def validate_reasoning_chain(self, chain: List[Dict]) -> Dict:
        """Validation de chaînes de raisonnement selon la logique de Sherlock"""
        validation_results = []
        
        for step in chain:
            if "hypothesis" in step:
                # Valider hypothèse
                hypothesis_id = step.get("hypothesis_id")
                if hypothesis_id in self._hypothesis_tracker.active_hypotheses:
                    strength = self._hypothesis_tracker.evaluate_hypothesis_strength(hypothesis_id)
                    validation_results.append({
                        "step": step,
                        "valid": strength["strength_score"] > 0.5,
                        "strength": strength["strength_score"]
                    })
                else:
                    validation_results.append({
                        "step": step,
                        "valid": False,
                        "error": "Hypothèse inconnue"
                    })
            else:
                # Valider étape logique générale
                validation_results.append({
                    "step": step,
                    "valid": True,  # Validation basique
                    "note": "Étape logique acceptée"
                })
        
        overall_valid = all(result["valid"] for result in validation_results)
        
        return {
            "chain_valid": overall_valid,
            "step_results": validation_results,
            "confidence": sum(r.get("strength", 0.5) for r in validation_results) / len(validation_results)
        }
    
    # === MÉTHODES UTILITAIRES ===
    
    def _trigger_automatic_inferences(self):
        """Déclenche les inférences automatiques JTMS"""
        # Propage les changements dans le système JTMS
        for belief in self._jtms_session.jtms.beliefs.values():
            belief.compute_truth_statement()
    
    def _get_recent_inferences(self, limit: int = 5) -> List[Dict]:
        """Récupère les inférences récentes"""
        return self._get_recent_modifications(limit)
    
    def _calculate_compatibility(self, hypothesis_desc: str, evidence_desc: str) -> float:
        """Calcule score de compatibilité entre hypothèse et évidence"""
        # Implémentation simplifiée basée sur mots-clés communs
        hyp_words = set(hypothesis_desc.lower().split())
        ev_words = set(evidence_desc.lower().split())
        
        if not hyp_words or not ev_words:
            return 0.5
        
        intersection = hyp_words & ev_words
        union = hyp_words | ev_words
        
        return len(intersection) / len(union) if union else 0.5
    
    def get_investigation_summary(self) -> Dict:
        """Résumé complet de l'état de l'investigation"""
        return {
            "agent_name": self._agent_name,
            "session_id": self._session_id,
            "active_hypotheses": len(self._hypothesis_tracker.active_hypotheses),
            "total_evidence": len(self._evidence_manager.evidence_catalog),
            "jtms_statistics": self.get_session_statistics(),
            "strongest_hypothesis": self._get_strongest_hypothesis(),
            "investigation_leads": len(self._get_recent_modifications())
        }
    
    def _get_strongest_hypothesis(self) -> Optional[Dict]:
        """Récupère l'hypothèse la plus forte"""
        if not self._hypothesis_tracker.active_hypotheses:
            return None
        
        best_strength = 0
        best_hypothesis = None
        
        for hypothesis_id in self._hypothesis_tracker.active_hypotheses:
            strength = self._hypothesis_tracker.evaluate_hypothesis_strength(hypothesis_id)
            if strength["strength_score"] > best_strength:
                best_strength = strength["strength_score"]
                best_hypothesis = {
                    "hypothesis_id": hypothesis_id,
                    "strength": strength["strength_score"],
                    "description": self._hypothesis_tracker.active_hypotheses[hypothesis_id]["description"]
                }
        
        return best_hypothesis