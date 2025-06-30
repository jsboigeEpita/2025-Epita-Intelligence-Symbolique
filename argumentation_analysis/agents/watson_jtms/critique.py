import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

# Supposons que JTMSAgentBase et d'autres dépendances nécessaires soient accessibles
# ou seront gérées ultérieurement. Pour l'instant, nous nous concentrons sur le déplacement de la logique.
# from ..jtms_agent_base import JTMSAgentBase, ExtendedBelief # Exemple
# from ..core.logic.watson_logic_assistant import WatsonLogicAssistant, TweetyBridge # Exemple

# Placeholder pour les classes qui seraient normalement importées
class JTMSAgentBase: # Placeholder
    def __init__(self, kernel, agent_name, strict_mode=False):
        self._logger = logging.getLogger(agent_name)
        self._jtms_session = None # Placeholder
        self._agent_name = agent_name
        self._conflict_resolutions = []
        self.validation_history = {}
        self.critique_patterns = {}
        self._validation_style = "rigorous_formal"
        self._consensus_threshold = 0.7
        # Mock des méthodes/attributs nécessaires pour que le code copié ne lève pas d'erreur immédiatement
        self._base_watson = None 
        self._formal_validator = None
        self._consistency_checker = None
        self.export_session_state = lambda: {}


    def add_belief(self, name, context, confidence): # Placeholder
        pass

    def _extract_logical_structure(self, text): # Placeholder
        return {}

    async def _analyze_hypothesis_consistency(self, hypothesis_data, sherlock_session_state): # Placeholder
        return {"consistent": True, "conflicts": []}

    def _analyze_hypothesis_strengths_weaknesses(self, hypothesis_data): # Placeholder
        return {"strengths": [], "critical_issues": []}

    def _calculate_overall_assessment(self, critique_results): # Placeholder
        return {"assessment": "pending", "confidence": 0.0}
    
    async def validate_reasoning_chain(self, chain: List[Dict]) -> Dict: # Placeholder
        return {
            "valid": True,
            "cumulative_confidence": 0.0,
            "step_validations": []
        }

    def _calculate_text_similarity(self, text1, text2): # Placeholder
        return 0.0
        
    def get_session_statistics(self): # Placeholder
        return {}

@dataclass
class ConflictResolution: # Placeholder
    conflict_id: str
    resolution_strategy: str
    chosen_belief: Optional[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


class CritiqueEngine:
    def __init__(self, agent_context: JTMSAgentBase):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._agent_context = agent_context # Pour accéder aux attributs/méthodes de l'agent original si nécessaire

    async def critique_hypothesis(self, hypothesis_data: Dict, sherlock_session_state: Dict = None) -> Dict:
        """Critique rigoureuse d'une hypothèse avec analyse formelle"""
        self._logger.info(f"Critique de l'hypothèse: {hypothesis_data.get('hypothesis_id', 'unknown')}")
        
        try:
            hypothesis_id = hypothesis_data.get("hypothesis_id")
            hypothesis_text = hypothesis_data.get("hypothesis", "")
            
            # Créer croyance locale pour analyse
            local_belief_name = f"critique_{hypothesis_id}_{int(datetime.now().timestamp())}"
            self._agent_context.add_belief(
                local_belief_name,
                context={
                    "type": "hypothesis_critique",
                    "original_hypothesis": hypothesis_text,
                    "source_agent": "sherlock"
                },
                confidence=0.5  # Neutre pour commencer
            )
            
            critique_results = {
                "hypothesis_id": hypothesis_id,
                "critique_belief_id": local_belief_name,
                "logical_analysis": {},
                "consistency_check": {},
                "formal_validation": {},
                "critical_issues": [],
                "strengths": [],
                "overall_assessment": "pending"
            }
            
            # Analyse logique via Watson de base
            # Note: _base_watson et _extract_logical_structure sont sur _agent_context
            if self._agent_context._base_watson:
                 logical_analysis = await self._agent_context._base_watson.process_message(
                     f"Analysez rigoureusement cette hypothèse: {hypothesis_text}"
                 )
                 critique_results["logical_analysis"] = {
                     "watson_analysis": logical_analysis,
                     "formal_structure": self._agent_context._extract_logical_structure(hypothesis_text)
                 }
            
            # Vérification de cohérence si état Sherlock fourni
            if sherlock_session_state:
                consistency_analysis = await self._agent_context._analyze_hypothesis_consistency(
                    hypothesis_data, sherlock_session_state
                )
                critique_results["consistency_check"] = consistency_analysis
                
                # Identifier problèmes potentiels
                if not consistency_analysis.get("consistent", True):
                    critique_results["critical_issues"].extend(
                        consistency_analysis.get("conflicts", [])
                    )
            
            # Validation formelle de la structure
            # Note: _formal_validator est sur _agent_context
            if self._agent_context._formal_validator:
                formal_validation = await self._agent_context._formal_validator.prove_belief(local_belief_name)
                critique_results["formal_validation"] = formal_validation
            
            # Analyse des forces et faiblesses
            strengths_weaknesses = self._agent_context._analyze_hypothesis_strengths_weaknesses(hypothesis_data)
            critique_results.update(strengths_weaknesses)
            
            # Évaluation globale
            overall_score = self._agent_context._calculate_overall_assessment(critique_results)
            critique_results["overall_assessment"] = overall_score["assessment"]
            critique_results["confidence_score"] = overall_score["confidence"]
            
            self._logger.info(f"Critique terminée: {overall_score['assessment']} "
                             f"(confiance: {overall_score['confidence']:.2f})")
            
            return critique_results
            
        except Exception as e:
            self._logger.error(f"Erreur critique hypothèse: {e}")
            return {"error": str(e), "hypothesis_id": hypothesis_data.get("hypothesis_id")}

    async def critique_reasoning_chain(self, chain_id: str, reasoning_chain: List[Dict]) -> Dict:
        """Critique une chaîne de raisonnement complète"""
        self._logger.info(f"Critique de la chaîne de raisonnement: {chain_id}")
        
        try:
            # Utiliser la validation existante comme base
            # Note: validate_reasoning_chain est sur _agent_context
            validation_result = await self._agent_context.validate_reasoning_chain(reasoning_chain)
            
            critique_result = {
                "chain_id": chain_id,
                "overall_valid": validation_result["valid"],
                "chain_confidence": validation_result["cumulative_confidence"],
                "step_critiques": [],
                "logical_fallacies": [],
                "logical_issues": [], 
                "missing_evidence": [], 
                "alternative_explanations": [], 
                "improvement_suggestions": [],
                "critique_summary": "",
                "revised_confidence": validation_result["cumulative_confidence"] * 0.9, 
                "timestamp": datetime.now().isoformat()
            }
            
            # Analyser chaque étape pour des fallacies
            for i, step_validation in enumerate(validation_result["step_validations"]):
                step_critique = {
                    "step_index": i,
                    "valid": step_validation["valid"],
                    "confidence": step_validation["confidence"],
                    "fallacies_detected": [],
                    "suggestions": []
                }
                
                if not step_validation["valid"]:
                    step_critique["fallacies_detected"].append("weak_premises")
                    step_critique["suggestions"].append("Renforcer les prémisses")
                
                critique_result["step_critiques"].append(step_critique)
            
            # Générer résumé
            valid_steps = sum(1 for s in critique_result["step_critiques"] if s["valid"])
            total_steps = len(critique_result["step_critiques"])
            
            if valid_steps == total_steps:
                critique_result["critique_summary"] = "Chaîne de raisonnement solide"
            else:
                critique_result["critique_summary"] = f"Chaîne partiellement valide: {valid_steps}/{total_steps} étapes valides"
            
            return critique_result
            
        except Exception as e:
            self._logger.error(f"Erreur critique chaîne {chain_id}: {e}")
            return {
                "chain_id": chain_id,
                "error": str(e),
                "overall_valid": False
            }

    async def challenge_assumption(self, assumption_id: str, assumption_data: Dict) -> Dict:
        """Challenge/conteste une assumption avec analyse critique"""
        self._logger.info(f"Challenge de l'assumption: {assumption_id}")
        
        try:
            challenge_result = {
                "assumption_id": assumption_id,
                "challenge_id": f"challenge_{assumption_id}_{int(datetime.now().timestamp())}",
                "assumption_text": assumption_data.get("assumption", ""),
                "challenge_valid": False,
                "challenge_strength": 0.0,
                "counter_arguments": [],
                "alternative_explanations": [],
                "supporting_evidence_gaps": [],
                "logical_vulnerabilities": [],
                "challenge_summary": "",
                "timestamp": datetime.now().isoformat()
            }
            
            assumption_text = assumption_data.get("assumption", "")
            confidence = assumption_data.get("confidence", 0.5)
            
            # Analyser les vulnérabilités logiques
            if confidence < 0.6:
                challenge_result["logical_vulnerabilities"].append("Low initial confidence")
                challenge_result["challenge_strength"] += 0.3
            
            supporting_evidence = assumption_data.get("supporting_evidence", [])
            if len(supporting_evidence) < 2:
                challenge_result["supporting_evidence_gaps"].append("Insufficient supporting evidence")
                challenge_result["challenge_strength"] += 0.4
            
            # Générer contre-arguments
            challenge_result["counter_arguments"].append({
                "argument": f"Alternative interpretation of evidence for: {assumption_text}",
                "strength": 0.6,
                "type": "alternative_interpretation"
            })
            
            # Générer explications alternatives
            challenge_result["alternative_explanations"].append({
                "explanation": f"Alternative explanation to: {assumption_text}",
                "plausibility": 0.5,
                "evidence_required": "Additional investigation needed"
            })
            
            challenge_result["alternative_scenarios"] = [{ 
                "scenario": f"Alternative scenario for: {assumption_text}",
                "probability": 0.3,
                "impact": "medium"
            }]
            
            # Déterminer si le challenge est valide
            challenge_result["challenge_valid"] = challenge_result["challenge_strength"] > 0.5
            
            # Résumé du challenge
            if challenge_result["challenge_valid"]:
                challenge_result["challenge_summary"] = f"Challenge valide (force: {challenge_result['challenge_strength']:.2f})"
            else:
                challenge_result["challenge_summary"] = "Challenge faible - assumption probablement solide"
            
            challenge_result["confidence_impact"] = -challenge_result["challenge_strength"] * 0.5
            
            return challenge_result
            
        except Exception as e:
            self._logger.error(f"Erreur challenge assumption {assumption_id}: {e}")
            return {
                "assumption_id": assumption_id,
                "error": str(e),
                "challenge_valid": False
            }

    async def identify_logical_fallacies(self, reasoning_id: str, reasoning_text: str) -> Dict:
        """Identifie les fallacies logiques dans un raisonnement"""
        self._logger.info(f"Identification de fallacies logiques pour: {reasoning_id}")
        
        try:
            fallacy_result = {
                "reasoning_id": reasoning_id,
                "reasoning_text": reasoning_text,
                "fallacies_detected": [],
                "fallacies_found": [], 
                "fallacy_count": 0,
                "severity_assessment": "low",
                "reasoning_quality": "acceptable",
                "improvement_suggestions": [],
                "timestamp": datetime.now().isoformat()
            }
            
            text_lower = reasoning_text.lower()
            
            # Détecter les fallacies communes
            if any(word in text_lower for word in ["stupide", "idiot", "incompétent"]):
                fallacy_result["fallacies_detected"].append({
                    "type": "ad_hominem",
                    "description": "Attaque personnelle au lieu d'argumenter sur le fond",
                    "severity": "medium",
                    "location": "Multiple occurrences detected"
                })
            
            if "soit" in text_lower and "soit" in text_lower.count("soit") > 1 : # Basic check
                fallacy_result["fallacies_detected"].append({
                    "type": "false_dilemma",
                    "description": "Présentation de seulement deux alternatives quand d'autres existent",
                    "severity": "medium",
                    "location": "Either/or construction detected"
                })
            
            if any(phrase in text_lower for phrase in ["tout le monde sait", "il est évident", "c'est évident"]):
                fallacy_result["fallacies_detected"].append({
                    "type": "appeal_to_authority",
                    "description": "Appel à une autorité non qualifiée ou consensus présumé",
                    "severity": "low",
                    "location": "Authority claim without qualification"
                })
            
            if any(word in text_lower for word in ["toujours", "jamais", "tous", "aucun"]) and len(reasoning_text.split()) < 50:
                fallacy_result["fallacies_detected"].append({
                    "type": "hasty_generalization",
                    "description": "Généralisation basée sur des exemples insuffisants",
                    "severity": "medium",
                    "location": "Absolute terms in short reasoning"
                })
            
            if "après" in text_lower and ("donc" in text_lower or "alors" in text_lower):
                fallacy_result["fallacies_detected"].append({
                    "type": "post_hoc",
                    "description": "Confusion entre corrélation et causalité",
                    "severity": "high",
                    "location": "Temporal sequence interpreted as causation"
                })
            
            fallacy_result["fallacy_count"] = len(fallacy_result["fallacies_detected"])
            fallacy_result["fallacies_found"] = fallacy_result["fallacies_detected"] 
            
            if fallacy_result["fallacy_count"] == 0:
                fallacy_result["severity_assessment"] = "none"
                fallacy_result["reasoning_quality"] = "good"
            elif fallacy_result["fallacy_count"] <= 2:
                fallacy_result["severity_assessment"] = "low"
                fallacy_result["reasoning_quality"] = "acceptable"
            elif fallacy_result["fallacy_count"] <= 4:
                fallacy_result["severity_assessment"] = "medium"
                fallacy_result["reasoning_quality"] = "questionable"
            else:
                fallacy_result["severity_assessment"] = "high"
                fallacy_result["reasoning_quality"] = "poor"
            
            if fallacy_result["fallacy_count"] > 0:
                fallacy_result["improvement_suggestions"].append("Réviser les arguments pour éliminer les fallacies identifiées")
                fallacy_result["improvement_suggestions"].append("Renforcer avec des preuves factuelles")
                fallacy_result["improvement_suggestions"].append("Éviter les généralisations absolues")
            
            # Note: critique_patterns est sur _agent_context
            self._agent_context.critique_patterns[reasoning_id] = {
                "fallacy_count": fallacy_result["fallacy_count"],
                "quality": fallacy_result["reasoning_quality"],
                "timestamp": datetime.now().isoformat()
            }
            
            fallacy_result["severity_scores"] = [f.get("severity", "low") for f in fallacy_result["fallacies_detected"]]
            fallacy_result["corrections_suggested"] = fallacy_result["improvement_suggestions"]
            
            return fallacy_result
            
        except Exception as e:
            self._logger.error(f"Erreur identification fallacies {reasoning_id}: {e}")
            return {
                "reasoning_id": reasoning_id,
                "error": str(e),
                "fallacies_detected": [],
                "fallacy_count": 0
            }

    def export_critique_state(self) -> Dict:
        """Exporte l'état des critiques et patterns identifiés"""
        try:
            # Note: Accès aux attributs via _agent_context
            critique_state = {
                "agent_name": self._agent_context._agent_name,
                "agent_type": "watson_validator",
                "session_id": self._agent_context._jtms_session.session_id if self._agent_context._jtms_session else "unknown_session",
                "validation_history": self._agent_context.validation_history,
                "critique_patterns": self._agent_context.critique_patterns,
                "conflict_resolutions": [
                    {
                        "conflict_id": res.conflict_id,
                        "strategy": res.resolution_strategy,
                        "chosen_belief": res.chosen_belief,
                        "confidence": res.confidence,
                        "timestamp": res.timestamp.isoformat()
                    } for res in self._agent_context._conflict_resolutions
                ],
                "validation_style": self._agent_context._validation_style,
                "consensus_threshold": self._agent_context._consensus_threshold,
                "jtms_session_state": self._agent_context.export_session_state(),
                "session_state": {
                    "active": True,
                    "last_activity": datetime.now().isoformat(),
                    "validation_count": len(self._agent_context.validation_history)
                },
                "export_timestamp": datetime.now().isoformat()
            }
            
            return critique_state
            
        except Exception as e:
            self._logger.error(f"Erreur export état critique: {e}")
            return {
                "error": str(e),
                "agent_name": self._agent_context._agent_name
            }