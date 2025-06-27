# -*- coding: utf-8 -*-
"""
Utilitaires pour l'analyse (parsing) de chaînes de caractères,
la conversion de formats de données simples, etc.
"""

import logging
import re
from typing import Dict, Pattern, Optional # Ajout de Optional

logger = logging.getLogger(__name__)

def parse_colon_separated_string_to_regex_dict(
    patterns_string: Optional[str],
    default_patterns: Optional[Dict[str, str]] = None,
    key_suffix: str = "_refs",
    escape_pattern: bool = True
) -> Dict[str, Pattern[str]]:
    """
    Convertit une chaîne de caractères contenant des motifs séparés par des ":"
    en un dictionnaire où les clés sont des noms dérivés des motifs et les valeurs
    sont des objets regex compilés.

    Par exemple, "config/:data/" devient:
    {
        "config_refs": re.compile(re.escape("config/")),
        "data_refs": re.compile(re.escape("data/"))
    }
    Si escape_pattern est False, les motifs sont compilés tels quels.

    Args:
        patterns_string (Optional[str]): La chaîne de caractères contenant les motifs
                                         séparés par des deux-points. Peut être None ou vide.
        default_patterns (Optional[Dict[str, str]]): Un dictionnaire de motifs par défaut
                                                     (nom_clé: motif_str) à utiliser si
                                                     patterns_string est vide ou ne produit
                                                     aucun motif valide.
        key_suffix (str): Suffixe à ajouter au nom du motif pour former la clé du dictionnaire.
        escape_pattern (bool): Si True, échappe le motif avant de le compiler en regex.
                               Si False, compile le motif tel quel (utile si le motif
                               est déjà une expression régulière valide).

    Returns:
        Dict[str, Pattern[str]]: Un dictionnaire de regex compilées.
                                 Retourne un dictionnaire basé sur default_patterns
                                 si patterns_string est invalide et default_patterns est fourni.
                                 Retourne un dictionnaire vide sinon.
    """
    compiled_patterns: Dict[str, Pattern[str]] = {}

    if patterns_string:
        pattern_names = patterns_string.split(':')
        for p_name in pattern_names:
            clean_p_name = p_name.strip()
            if clean_p_name: # S'assurer que le nom n'est pas vide après strip
                # La clé du dictionnaire sera "nom_du_motif_sans_slash_refs"
                # Le regex cherchera le motif original "nom_du_motif/"
                dict_key = f"{clean_p_name.replace('/', '')}{key_suffix}"
                pattern_to_compile = re.escape(clean_p_name) if escape_pattern else clean_p_name
                try:
                    compiled_patterns[dict_key] = re.compile(pattern_to_compile)
                    logger.debug(f"Motif '{clean_p_name}' compilé en regex pour la clé '{dict_key}'.")
                except re.error as e_re:
                    logger.error(f"Erreur de compilation regex pour le motif '{pattern_to_compile}' (original: '{clean_p_name}'): {e_re}")
    
    if not compiled_patterns and default_patterns:
        logger.info("Aucun motif valide fourni ou parsé, utilisation des motifs par défaut.")
        for name, pattern_str in default_patterns.items():
            pattern_to_compile_default = re.escape(pattern_str) if escape_pattern else pattern_str
            try:
                compiled_patterns[name] = re.compile(pattern_to_compile_default)
                logger.debug(f"Motif par défaut '{pattern_str}' compilé pour la clé '{name}'.")
            except re.error as e_re_default:
                 logger.error(f"Erreur de compilation regex pour le motif par défaut '{pattern_to_compile_default}' (original: '{pattern_str}'): {e_re_default}")
        return compiled_patterns

    if not compiled_patterns and not default_patterns:
        logger.warning("Aucun motif fourni et aucun motif par défaut. Retour d'un dictionnaire de regex vide.")
    
    return compiled_patterns