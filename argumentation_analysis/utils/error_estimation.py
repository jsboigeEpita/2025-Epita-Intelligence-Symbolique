#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire pour l'estimation des taux d'erreur (faux positifs/négatifs).
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def estimate_false_positives_negatives_rates(
    base_results: List[Dict[str, Any]],
    advanced_results: List[Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    """
    Estime les taux de faux positifs et faux négatifs en comparant les analyses de base et avancées.
    Cette fonction suppose que les résultats avancés sont plus proches de la vérité terrain.

    Args:
        base_results (List[Dict[str, Any]]): Liste des résultats d'analyse de base.
        advanced_results (List[Dict[str, Any]]): Liste des résultats d'analyse avancée.

    Returns:
        Dict[str, Dict[str, float]]: Dictionnaire des taux de faux positifs/négatifs estimés par agent/type.
    """
    error_rates: Dict[str, Dict[str, float]] = {
        "base_contextual": {"false_positive_rate": 0.0, "false_negative_rate": 0.0, "processed_extracts": 0},
        "advanced_contextual": {"false_positive_rate": 0.0, "false_negative_rate": 0.0, "processed_extracts": 0}, # FP basé sur confiance, FN non estimé ici
        "advanced_complex": {"false_positive_rate": 0.0, "false_negative_rate": 0.0, "processed_extracts": 0} # FP basé sur gravité, FN non estimé ici
    }
    
    def create_result_dict(results_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        res_dict = {}
        for r in results_list:
            s_name = r.get('source_name', 'UnknownSource')
            e_name = r.get('extract_name', 'UnknownExtract_' + str(datetime.now().timestamp()))
            res_dict[f"{s_name}:{e_name}"] = r
        return res_dict

    base_dict = create_result_dict(base_results)
    advanced_dict = create_result_dict(advanced_results)
    
    common_extract_keys = set(base_dict.keys()) & set(advanced_dict.keys())
    
    if not common_extract_keys:
        logger.warning("Aucun extrait commun trouvé entre les résultats de base et avancés. Impossible d'estimer les taux d'erreur comparatifs.")
        return {k: {"false_positive_rate": 0.0, "false_negative_rate": 0.0} for k in error_rates if k != "base_contextual" and k != "advanced_contextual" and k != "advanced_complex"}


    fp_sum_base_contextual = 0.0
    fn_sum_base_contextual = 0.0
    fp_sum_advanced_contextual = 0.0
    fp_sum_advanced_complex = 0.0

    for key in common_extract_keys:
        base_res = base_dict[key]
        adv_res = advanced_dict[key]
        
        base_analyses = base_res.get("analyses", {})
        adv_analyses = adv_res.get("analyses", {})

        base_contextual_data = base_analyses.get("contextual_fallacies", {})
        adv_contextual_data = adv_analyses.get("contextual_fallacies", {})

        base_fallacy_types = []
        if isinstance(base_contextual_data, dict):
            for arg_r in base_contextual_data.get("argument_results", []):
                if isinstance(arg_r, dict):
                    for fall in arg_r.get("detected_fallacies", []):
                        if isinstance(fall, dict) and fall.get("fallacy_type"):
                            base_fallacy_types.append(fall["fallacy_type"])
        
        adv_fallacy_types_contextual = []
        if isinstance(adv_contextual_data, dict):
            for fall in adv_contextual_data.get("contextual_fallacies", []): 
                 if isinstance(fall, dict) and fall.get("fallacy_type"):
                    adv_fallacy_types_contextual.append(fall["fallacy_type"])

        if base_fallacy_types or adv_fallacy_types_contextual: 
            fp_base = len([f for f in base_fallacy_types if f not in adv_fallacy_types_contextual])
            fn_base = len([f for f in adv_fallacy_types_contextual if f not in base_fallacy_types])
            
            fp_sum_base_contextual += fp_base / len(base_fallacy_types) if base_fallacy_types else 0
            fn_sum_base_contextual += fn_base / len(adv_fallacy_types_contextual) if adv_fallacy_types_contextual else 0
            error_rates["base_contextual"]["processed_extracts"] += 1

        adv_contextual_fp_count = 0
        if isinstance(adv_contextual_data, dict): 
            adv_contextual_fallacies_list = adv_contextual_data.get("contextual_fallacies", [])
            if adv_contextual_fallacies_list:
                for fall_eval in adv_contextual_fallacies_list:
                    if isinstance(fall_eval, dict) and fall_eval.get("confidence", 1.0) < 0.5: 
                        adv_contextual_fp_count += 1
                fp_sum_advanced_contextual += adv_contextual_fp_count / len(adv_contextual_fallacies_list)
                error_rates["advanced_contextual"]["processed_extracts"] += 1
        
        adv_complex_data = adv_analyses.get("complex_fallacies", {})
        if isinstance(adv_complex_data, dict):
            composite_severity_data = adv_complex_data.get("composite_severity", {})
            severity_level_str = composite_severity_data.get("severity_level", "") if isinstance(composite_severity_data, dict) else ""
            
            current_fp_adv_complex = 0.0
            if severity_level_str == "Faible": current_fp_adv_complex = 0.2
            elif severity_level_str == "Modéré": current_fp_adv_complex = 0.1
            elif severity_level_str: current_fp_adv_complex = 0.05 
            
            fp_sum_advanced_complex += current_fp_adv_complex 
            error_rates["advanced_complex"]["processed_extracts"] += 1

    for agent_type in ["base_contextual", "advanced_contextual", "advanced_complex"]:
        num_processed = error_rates[agent_type]["processed_extracts"]
        if num_processed > 0:
            if agent_type == "base_contextual":
                error_rates[agent_type]["false_positive_rate"] = fp_sum_base_contextual / num_processed
                error_rates[agent_type]["false_negative_rate"] = fn_sum_base_contextual / num_processed
            elif agent_type == "advanced_contextual":
                error_rates[agent_type]["false_positive_rate"] = fp_sum_advanced_contextual / num_processed
            elif agent_type == "advanced_complex":
                error_rates[agent_type]["false_positive_rate"] = fp_sum_advanced_complex / num_processed
        del error_rates[agent_type]["processed_extracts"] 

    logger.info(f"Estimation des taux d'erreur terminée. Extraits communs traités: {len(common_extract_keys)}")
    # S'assurer que toutes les clés attendues sont présentes même si aucun extrait n'a été traité
    final_error_rates = {}
    for agent_key in ["base_contextual", "advanced_contextual", "advanced_complex"]:
        final_error_rates[agent_key] = {
            "false_positive_rate": error_rates.get(agent_key, {}).get("false_positive_rate", 0.0),
            "false_negative_rate": error_rates.get(agent_key, {}).get("false_negative_rate", 0.0)
        }
    return final_error_rates