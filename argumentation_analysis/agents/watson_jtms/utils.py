from typing import Dict, List, Any
from datetime import datetime

# Ces imports pourraient être nécessaires pour certaines fonctions,
# je les ajoute par anticipation. Ils seront nettoyés plus tard si inutiles.
# from .jtms_agent_base import ExtendedBelief # Potentiellement pour _suggest_belief_strengthening
# from .watson_jtms_agent import ConflictResolution # Potentiellement pour _resolve_single_conflict

def _extract_logical_structure(hypothesis_text: str) -> Dict:
    """Extrait la structure logique d'un texte d'hypothèse"""
    structure = {
        "type": "unknown",
        "components": [],
        "logical_operators": [],
        "complexity": "simple"
    }
    
    # Analyse basique des mots-clés logiques
    text_lower = hypothesis_text.lower()
    if "si" in text_lower and "alors" in text_lower:
        structure["type"] = "conditional"
        structure["logical_operators"].append("implication")
    elif "et" in text_lower:
        structure["type"] = "conjunctive"
        structure["logical_operators"].append("conjunction")
    elif "ou" in text_lower:
        structure["type"] = "disjunctive"
        structure["logical_operators"].append("disjunction")
    else:
        structure["type"] = "atomic"
    
    return structure

async def _analyze_hypothesis_consistency(hypothesis_data: Dict, 
                                         sherlock_state: Dict,
                                         similarity_calculator_func) -> Dict: # Ajout d'un paramètre pour la fonction de similarité
    """Analyse la cohérence d'une hypothèse avec l'état Sherlock"""
    consistency_result = {
        "consistent": True,
        "conflicts": [],
        "supportive_beliefs": [],
        "contradictory_beliefs": []
    }
    
    hypothesis_text = hypothesis_data.get("hypothesis", "")
    sherlock_beliefs = sherlock_state.get("beliefs", {})
    
    # Recherche de croyances liées
    for belief_name, belief_data in sherlock_beliefs.items():
        belief_desc = belief_data.get("context", {}).get("description", "")
        
        # Analyse de similarité/contradiction (simplifiée)
        similarity = similarity_calculator_func(hypothesis_text, belief_desc) # Utilisation de la fonction passée
        
        if similarity > 0.7:
            consistency_result["supportive_beliefs"].append({
                "belief_name": belief_name,
                "similarity": similarity,
                "support_strength": "strong"
            })
        elif similarity < -0.3:  # Contradiction détectée
            consistency_result["contradictory_beliefs"].append({
                "belief_name": belief_name,
                "contradiction_level": abs(similarity),
                "conflict_type": "semantic"
            })
            consistency_result["consistent"] = False
    
    return consistency_result

def _analyze_hypothesis_strengths_weaknesses(hypothesis_data: Dict) -> Dict:
    """Analyse les forces et faiblesses d'une hypothèse"""
    analysis = {
        "strengths": [],
        "weaknesses": [],
        "critical_issues": []
    }
    
    confidence = hypothesis_data.get("confidence", 0.0)
    supporting_evidence = hypothesis_data.get("supporting_evidence", [])
    
    # Analyse des forces
    if confidence > 0.7:
        analysis["strengths"].append("Haute confiance initiale")
    if len(supporting_evidence) > 2:
        analysis["strengths"].append("Multiples évidences de support")
    
    # Analyse des faiblesses
    if confidence < 0.5:
        analysis["weaknesses"].append("Confiance insuffisante")
    if len(supporting_evidence) == 0:
        analysis["critical_issues"].append("Aucune évidence de support")
    
    return analysis

def _calculate_overall_assessment(critique_results: Dict) -> Dict:
    """Calcule l'évaluation globale d'une critique"""
    scores = []
    
    # Score de cohérence
    if critique_results["consistency_check"].get("consistent", True):
        scores.append(0.8)
    else:
        scores.append(0.2)
    
    # Score de validation formelle
    formal_valid = critique_results["formal_validation"].get("provable", False)
    formal_confidence = critique_results["formal_validation"].get("confidence", 0.0)
    scores.append(formal_confidence if formal_valid else 0.1)
    
    # Score basé sur les problèmes critiques
    critical_issues_count = len(critique_results["critical_issues"])
    issue_penalty = min(critical_issues_count * 0.2, 0.8)
    scores.append(max(0.1, 1.0 - issue_penalty))
    
    overall_score = sum(scores) / len(scores) if scores else 0.0 # Éviter division par zéro
    
    if overall_score > 0.7:
        assessment = "valid_strong"
    elif overall_score > 0.5:
        assessment = "valid_moderate"
    elif overall_score > 0.3:
        assessment = "questionable"
    else:
        assessment = "invalid"
    
    return {
        "assessment": assessment,
        "confidence": overall_score,
        "component_scores": scores
    }

async def _analyze_justification_gaps(belief_name: str, extended_beliefs: Dict) -> List[Dict]:
    """Analyse les lacunes dans les justifications d'une croyance"""
    gaps = []
    
    if belief_name not in extended_beliefs:
        return gaps
    
    belief = extended_beliefs[belief_name]
    
    # Si pas de justifications
    if not belief.justifications:
        gaps.append({
            "type": "missing_justification",
            "suggested_premise": f"evidence_for_{belief_name}",
            "rationale": "Croyance sans justification",
            "confidence": 0.8
        })
    
    # Si justifications faibles
    for i, justification in enumerate(belief.justifications):
        if len(justification.in_list) == 0:
            gaps.append({
                "type": "weak_justification",
                "suggested_premise": f"stronger_evidence_{i}",
                "rationale": "Justification sans prémisses positives",
                "confidence": 0.6
            })
    
    return gaps

async def _generate_contextual_alternatives(belief_name: str, context: Dict) -> List[Dict]:
    """Génère des alternatives basées sur le contexte"""
    alternatives = []
    
    context_type = context.get("type", "unknown")
    
    if context_type == "investigation":
        alternatives.append({
            "type": "alternative_hypothesis",
            "description": f"Hypothèse alternative à {belief_name}",
            "rationale": "Exploration d'alternatives dans le contexte d'enquête",
            "confidence": 0.5,
            "priority": "medium"
        })
    
    return alternatives

def _suggest_belief_strengthening(belief_name: str, extended_beliefs: Dict) -> List[Dict]:
    """Suggère des moyens de renforcer une croyance"""
    suggestions = []
    
    belief = extended_beliefs.get(belief_name)
    if belief and belief.confidence < 0.7:
        suggestions.append({
            "type": "strengthen_confidence",
            "description": f"Rechercher évidences additionnelles pour {belief_name}",
            "rationale": f"Confiance actuelle faible: {belief.confidence:.2f}",
            "confidence": 0.7,
            "priority": "high"
        })
    
    return suggestions

def _generate_contradictory_tests(belief_name: str) -> List[Dict]:
    """Génère des tests contradictoires pour tester la robustesse"""
    tests = []
    
    tests.append({
        "type": "contradictory_test",
        "description": f"Tester la négation: not_{belief_name}",
        "rationale": "Vérifier la robustesse face à la contradiction",
        "confidence": 0.4,
        "priority": "low"
    })
    
    return tests

async def _resolve_single_conflict(conflict: Dict, conflict_resolutions_count: int, extended_beliefs: Dict, ConflictResolutionClass) -> Any: # ConflictResolutionClass au lieu de ConflictResolution
    """Résout un conflit individuel"""
    conflict_id = f"conflict_{conflict_resolutions_count}_{int(datetime.now().timestamp())}"
    
    conflicting_beliefs = conflict.get("beliefs", [])
    
    # Stratégie de résolution basée sur la confiance
    if len(conflicting_beliefs) == 2:
        belief1_name, belief2_name = conflicting_beliefs
        
        belief1 = extended_beliefs.get(belief1_name)
        belief2 = extended_beliefs.get(belief2_name)
        
        if belief1 and belief2:
            if belief1.confidence > belief2.confidence:
                chosen_belief = belief1_name
                resolution_strategy = "confidence_based"
                reasoning = f"Choix basé sur confiance: {belief1.confidence:.2f} > {belief2.confidence:.2f}"
            elif belief2.confidence > belief1.confidence:
                chosen_belief = belief2_name
                resolution_strategy = "confidence_based"
                reasoning = f"Choix basé sur confiance: {belief2.confidence:.2f} > {belief1.confidence:.2f}"
            else:
                chosen_belief = None
                resolution_strategy = "manual_review_needed"
                reasoning = "Confiances égales - révision manuelle nécessaire"
        else:
            chosen_belief = None
            resolution_strategy = "error"
            reasoning = "Croyances conflictuelles introuvables"
    else:
        chosen_belief = None
        resolution_strategy = "complex_conflict"
        reasoning = f"Conflit complexe avec {len(conflicting_beliefs)} croyances"
    
    return ConflictResolutionClass( # Utilisation de ConflictResolutionClass
        conflict_id=conflict_id,
        conflicting_beliefs=conflicting_beliefs,
        resolution_strategy=resolution_strategy,
        chosen_belief=chosen_belief,
        reasoning=reasoning,
        confidence=0.7 if chosen_belief else 0.3
    )

async def _apply_conflict_resolutions(resolutions: List[Any], jtms_session): # Any au lieu de ConflictResolution
    """Applique les résolutions de conflit au système JTMS"""
    for resolution in resolutions:
        if resolution.chosen_belief and resolution.resolution_strategy == "confidence_based":
            # Invalider les croyances non choisies
            for belief_name in resolution.conflicting_beliefs:
                if belief_name != resolution.chosen_belief:
                    if belief_name in jtms_session.jtms.beliefs:
                        jtms_session.jtms.beliefs[belief_name].valid = False
                    if belief_name in jtms_session.extended_beliefs:
                        jtms_session.extended_beliefs[belief_name].record_modification(
                            "conflict_resolution",
                            {"resolved_by": resolution.conflict_id, "strategy": resolution.resolution_strategy}
                        )

async def _analyze_logical_soundness(beliefs: Dict) -> Dict:
    """Analyse la solidité logique d'un ensemble de croyances"""
    soundness_analysis = {
        "sound": True,
        "logical_errors": [],
        "inference_quality": "high",
        "circular_reasoning": []
    }
    
    # Recherche de raisonnement circulaire (simplifiée)
    belief_dependencies = {}
    for belief_name, belief_data in beliefs.items():
        dependencies = []
        for justification in belief_data.get("justifications", []):
            dependencies.extend(justification.get("in_list", []))
        belief_dependencies[belief_name] = dependencies
    
    # Détection de cycles simples
    for belief_name, deps in belief_dependencies.items():
        if belief_name in deps:
            soundness_analysis["circular_reasoning"].append(belief_name)
            soundness_analysis["sound"] = False
    
    return soundness_analysis

def _generate_validation_recommendations(validation_report: Dict) -> List[Dict]:
    """Génère des recommandations basées sur le rapport de validation"""
    recommendations = []
    
    # Recommandations basées sur les conflits
    conflicts_detected = validation_report["consistency_analysis"].get("conflicts_detected", []) # Correction: conflicts_detected est une liste
    if conflicts_detected: # Correction: vérifier si la liste n'est pas vide
        recommendations.append({
            "type": "resolve_conflicts",
            "priority": "critical",
            "description": f"Résoudre {len(conflicts_detected)} conflits détectés", # Correction: utiliser len()
            "action": "conflict_resolution"
        })
    
    # Recommandations basées sur les croyances non prouvables
    unproven_count = sum(
        1 for validation in validation_report["beliefs_validated"].values()
        if not validation["provable"]
    )
    if unproven_count > 0:
        recommendations.append({
            "type": "strengthen_proofs",
            "priority": "high",
            "description": f"Renforcer {unproven_count} croyances non prouvables",
            "action": "add_justifications"
        })
    
    return recommendations

def _assess_overall_validity(validation_report: Dict) -> Dict:
    """Évalue la validité globale du raisonnement"""
    scores = []
    
    # Score de cohérence
    consistency_score = 1.0 if validation_report["consistency_analysis"]["is_consistent"] else 0.0
    scores.append(consistency_score)
    
    # Score de preuves formelles
    proven_beliefs = sum(
        1 for validation in validation_report["beliefs_validated"].values()
        if validation["provable"]
    )
    total_beliefs = len(validation_report["beliefs_validated"])
    proof_score = proven_beliefs / total_beliefs if total_beliefs > 0 else 0.0
    scores.append(proof_score)
    
    # Score de solidité logique
    soundness_score = 1.0 if validation_report["logical_soundness"]["sound"] else 0.5
    scores.append(soundness_score)
    
    overall_score = sum(scores) / len(scores) if scores else 0.0 # Éviter division par zéro
    
    if overall_score > 0.8:
        status = "highly_valid"
    elif overall_score > 0.6:
        status = "moderately_valid"
    elif overall_score > 0.4:
        status = "questionable"
    else:
        status = "invalid"
    
    return {
        "status": status,
        "score": overall_score,
        "component_scores": {
            "consistency": consistency_score,
            "formal_proofs": proof_score,
            "logical_soundness": soundness_score
        }
    }

def _build_logical_chains(validated_beliefs: List[str], extended_beliefs: Dict) -> List[Dict]:
    """Construit les chaînes logiques entre croyances validées"""
    chains = []
    
    # Construction simplifiée des chaînes basée sur les justifications JTMS
    for belief_name in validated_beliefs:
        if belief_name in extended_beliefs:
            belief = extended_beliefs[belief_name]
            
            for justification in belief.justifications:
                chain = {
                    "conclusion": belief_name,
                    "premises": [str(b) for b in justification.in_list],
                    "negatives": [str(b) for b in justification.out_list],
                    "chain_type": "direct_justification",
                    "strength": belief.confidence
                }
                chains.append(chain)
    
    return chains

def _generate_final_assessment(synthesis_result: Dict) -> Dict:
    """Génère l'évaluation finale de la synthèse"""
    high_confidence_count = len(synthesis_result["high_confidence_conclusions"])
    total_count = len(synthesis_result["validated_beliefs"])
    
    quality_score = high_confidence_count / total_count if total_count > 0 else 0.0
    
    if quality_score > 0.7:
        assessment_level = "excellent"
    elif quality_score > 0.5:
        assessment_level = "good"
    elif quality_score > 0.3:
        assessment_level = "acceptable"
    else:
        assessment_level = "poor"
    
    return {
        "assessment_level": assessment_level,
        "quality_score": quality_score,
        "high_confidence_ratio": quality_score,
        "total_conclusions": total_count,
        "synthesis_quality": "rigorous_formal_analysis"
    }

def _validate_logical_step(premises: List[str], conclusion: str) -> bool:
    """Valide une étape logique basique"""
    # Validation simplifiée - dans une vraie implémentation, 
    # ceci utiliserait un moteur de logique formelle
    return len(premises) > 0 and conclusion is not None

def _calculate_text_similarity(text1: str, text2: str) -> float:
    """Calcule similarité entre deux textes (implémentation simplifiée)"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    # Jaccard similarity
    similarity = len(intersection) / len(union) if union else 0.0 # Éviter division par zéro
    
    # Détecter contradictions par mots-clés
    contradiction_keywords = {
        ("oui", "non"), ("vrai", "faux"), ("est", "n'est pas"),
        ("peut", "ne peut pas"), ("va", "ne va pas")
    }
    
    for word1_key, word2_key in contradiction_keywords: # Renommer les variables pour éviter conflit
        if word1_key in words1 and word2_key in words2:
            return -0.5  # Contradiction détectée
        if word2_key in words1 and word1_key in words2:
            return -0.5
    
    return similarity