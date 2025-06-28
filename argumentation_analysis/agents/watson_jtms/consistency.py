import logging
from typing import Dict, List, Optional, Any, Tuple # Ajout basé sur l'utilisation potentielle future et les types dans les méthodes

# Note: JTMSAgentBase et ExtendedBelief ne sont pas directement utilisés DANS CETTE CLASSE
# mais pourraient être nécessaires pour le typage de jtms_session si on voulait être plus strict.
# Pour l'instant, on garde les imports minimaux pour la classe elle-même.

class ConsistencyChecker:
    """Vérificateur de cohérence avec analyse formelle"""
    
    def __init__(self, jtms_session): # jtms_session est attendu comme un objet ayant .jtms.beliefs et .extended_beliefs
        self.jtms_session = jtms_session
        self.conflict_counter = 0
        self.resolution_history = []
        
    def check_global_consistency(self) -> Dict:
        """Vérification complète de cohérence du système"""
        consistency_report = {
            "is_consistent": True,
            "conflicts_detected": [],
            "logical_contradictions": [],
            "non_monotonic_loops": [],
            "unresolved_conflicts": [],
            "confidence_score": 1.0
        }
        
        # Détection des contradictions directes
        direct_conflicts = self._detect_direct_contradictions()
        consistency_report["conflicts_detected"].extend(direct_conflicts)
        
        # Détection des contradictions logiques
        logical_conflicts = self._detect_logical_contradictions()
        consistency_report["logical_contradictions"].extend(logical_conflicts)
        
        # Vérification des boucles non-monotoniques
        # Assumant que jtms_session.jtms.update_non_monotonic_befielfs() existe et est appelé ailleurs
        # ou que cette logique doit être adaptée si elle est spécifique à ce contexte.
        # Pour l'instant, on garde la logique telle quelle.
        if hasattr(self.jtms_session, 'jtms') and hasattr(self.jtms_session.jtms, 'update_non_monotonic_befielfs'):
             self.jtms_session.jtms.update_non_monotonic_befielfs()
        
        non_monotonic = []
        if hasattr(self.jtms_session, 'jtms') and hasattr(self.jtms_session.jtms, 'beliefs'):
            non_monotonic = [
                name for name, belief in self.jtms_session.jtms.beliefs.items()
                if hasattr(belief, 'non_monotonic') and belief.non_monotonic
            ]
        consistency_report["non_monotonic_loops"] = non_monotonic
        
        # Calcul du score de cohérence global
        total_issues = (len(direct_conflicts) + len(logical_conflicts) + len(non_monotonic))
        
        total_beliefs = 0
        if hasattr(self.jtms_session, 'extended_beliefs'):
            total_beliefs = len(self.jtms_session.extended_beliefs)
        
        if total_beliefs > 0:
            consistency_report["confidence_score"] = max(0, 1 - (total_issues / total_beliefs))
        
        consistency_report["is_consistent"] = total_issues == 0
        
        return consistency_report
    
    def _detect_direct_contradictions(self) -> List[Dict]:
        """Détecte les contradictions directes (A et non-A)"""
        conflicts = []
        processed_pairs = set()
        
        if not hasattr(self.jtms_session, 'extended_beliefs'):
            return conflicts

        for belief_name, belief in self.jtms_session.extended_beliefs.items():
            # Recherche de négation directe
            if belief_name.startswith("not_"):
                positive_name = belief_name[4:]
            else:
                positive_name = belief_name
                # belief_name_neg = f"not_{belief_name}" # Non utilisé directement ici

            # Vérifier si les deux existent et sont valides
            if positive_name in self.jtms_session.extended_beliefs:
                belief_neg_name = f"not_{positive_name}"
                
                pair_key = tuple(sorted([positive_name, belief_neg_name]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                if belief_neg_name in self.jtms_session.extended_beliefs:
                    pos_belief = self.jtms_session.extended_beliefs[positive_name]
                    neg_belief = self.jtms_session.extended_beliefs[belief_neg_name]
                    
                    if hasattr(pos_belief, 'valid') and pos_belief.valid and \
                       hasattr(neg_belief, 'valid') and neg_belief.valid:
                        conflicts.append({
                            "type": "direct_contradiction",
                            "beliefs": [positive_name, belief_neg_name],
                            "agents": [getattr(pos_belief, 'agent_source', 'unknown'), getattr(neg_belief, 'agent_source', 'unknown')],
                            "confidences": [getattr(pos_belief, 'confidence', 0.0), getattr(neg_belief, 'confidence', 0.0)]
                        })
        
        return conflicts
    
    def _detect_logical_contradictions(self) -> List[Dict]:
        """Détecte les contradictions logiques via chaînes d'inférence"""
        logical_conflicts = []
        
        if not hasattr(self.jtms_session, 'extended_beliefs'):
            return logical_conflicts

        # Analyse des chaînes de justification pour cycles contradictoires
        for belief_name, belief in self.jtms_session.extended_beliefs.items():
            if hasattr(belief, 'justifications') and belief.justifications:
                for justification in belief.justifications:
                    if not hasattr(justification, 'in_list') or not hasattr(justification, 'out_list'):
                        continue

                    # Vérifier si les prémisses contiennent des contradictions
                    in_beliefs = [str(b) for b in justification.in_list]
                    out_beliefs = [str(b) for b in justification.out_list]
                    
                    # Contradiction si même croyance en in et out
                    common_beliefs = set(in_beliefs) & set(out_beliefs)
                    if common_beliefs:
                        logical_conflicts.append({
                            "type": "justification_contradiction",
                            "belief": belief_name,
                            "contradictory_premises": list(common_beliefs),
                            "justification": {
                                "in_list": in_beliefs,
                                "out_list": out_beliefs
                            }
                        })
        
        return logical_conflicts