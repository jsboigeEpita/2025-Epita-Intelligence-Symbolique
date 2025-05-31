import logging
import sys
from unittest.mock import MagicMock
from itertools import chain, combinations

# Importations relatives (anticipées)
# JClass sera probablement importé depuis le module principal du mock jpype
# from ..jpype_mock import JClass
# MockJavaCollection et potentiellement MockJClassCore depuis jclass_core
from .jclass_core import MockJavaCollection, MockJClassCore 
# Pour éviter une dépendance circulaire immédiate avec jpype_mock pour JClass,
# on va supposer que JClass("java.util.HashSet") est passé ou accessible.
# Pour l'instant, on va le définir localement ou le passer en argument.

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[MOCK JPYPE TWEETY_REASONERS LOG] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

# --- Helper functions for argumentation semantics ---
# Ces fonctions étaient initialement dans MockJClass.__call__

def _get_args_from_theory(theory_mock):
    if hasattr(theory_mock, '_collections') and "nodes" in theory_mock._collections:
        return list(theory_mock._collections["nodes"])
    mock_logger.warning(f"[_get_args_from_theory] Pas de 'nodes' dans {theory_mock}")
    return []

def _get_attacks_from_theory(theory_mock):
    if hasattr(theory_mock, '_collections') and "attacks" in theory_mock._collections:
        return list(theory_mock._collections["attacks"])
    mock_logger.warning(f"[_get_attacks_from_theory] Pas de 'attacks' dans {theory_mock}")
    return []

def _check_attack_exists_helper(arg1_mock, arg2_mock, all_attacks_mocks):
    for attack_mock in all_attacks_mocks:
        if not (hasattr(attack_mock, 'getAttacker') and hasattr(attack_mock, 'getAttacked')):
            mock_logger.warning(f"[_check_attack_exists_helper] attack_mock n'a pas getAttacker/getAttacked: {attack_mock}")
            continue
        attacker = attack_mock.getAttacker()
        attacked = attack_mock.getAttacked()
        
        # S'assurer que attacker et attacked sont des mocks valides avec .equals()
        # et que arg1_mock et arg2_mock le sont aussi.
        if not (hasattr(attacker, 'equals') and callable(attacker.equals) and \
                hasattr(attacked, 'equals') and callable(attacked.equals) and \
                hasattr(arg1_mock, 'equals') and callable(arg1_mock.equals) and \
                hasattr(arg2_mock, 'equals') and callable(arg2_mock.equals)):
            mock_logger.warning(f"[_check_attack_exists_helper] Un des mocks (attacker, attacked, arg1, arg2) n'a pas .equals callable.")
            continue
            
        if attacker.equals(arg1_mock) and attacked.equals(arg2_mock):
            return True
    return False

def _is_conflict_free_set_helper(args_set_mocks, all_attacks_mocks):
    for arg_a_mock in args_set_mocks:
        for arg_b_mock in args_set_mocks: # Inclut l'auto-attaque
            if _check_attack_exists_helper(arg_a_mock, arg_b_mock, all_attacks_mocks):
                return False
    return True

def _get_attackers_of_arg_helper(target_arg_mock, all_args_mocks, all_attacks_mocks):
    attackers = set()
    for potential_attacker_mock in all_args_mocks:
        if _check_attack_exists_helper(potential_attacker_mock, target_arg_mock, all_attacks_mocks):
            attackers.add(potential_attacker_mock)
    return attackers

def _is_arg_defended_by_set_helper(target_arg_mock, defending_set_mocks, all_args_mocks, all_attacks_mocks):
    attackers_of_target = _get_attackers_of_arg_helper(target_arg_mock, all_args_mocks, all_attacks_mocks)
    if not attackers_of_target:
        return True
    
    for attacker_of_target_mock in attackers_of_target:
        is_attacker_counter_attacked = False
        for defender_from_set_mock in defending_set_mocks:
            if _check_attack_exists_helper(defender_from_set_mock, attacker_of_target_mock, all_attacks_mocks):
                is_attacker_counter_attacked = True
                break
        if not is_attacker_counter_attacked:
            return False
    return True

def _is_admissible_set_helper(args_set_mocks, all_args_mocks, all_attacks_mocks):
    if not _is_conflict_free_set_helper(args_set_mocks, all_attacks_mocks):
        return False
    for arg_in_set_mock in args_set_mocks:
        if not _is_arg_defended_by_set_helper(arg_in_set_mock, args_set_mocks, all_args_mocks, all_attacks_mocks):
            return False
    return True

# --- Configuration functions for specific reasoners ---

def configure_complete_reasoner_mock(reasoner_instance_mock, dung_theory_instance, JClass_provider):
    """
    Configure le mock pour CompleteReasoner.
    JClass_provider est une fonction (comme le JClass global) qui peut créer des JClass mocks.
    """
    mock_logger.debug(f"[CONFIGURE CompleteReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}")
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error("[CONFIGURE CompleteReasoner] _collections['models'] non trouvée sur l'instance du reasoner.")
        reasoner_instance_mock._collections["models"] = [] # Initialiser si manquant
        models_coll = reasoner_instance_mock._collections["models"]
    
    models_coll.clear() # Vider les modèles précédents

    # La logique originale créait des mocks d'arguments 'a' et 'b' en dur.
    # Idéalement, cela devrait être basé sur la dung_theory_instance.
    # Pour l'instant, on garde la logique simple du mock original pour la migration.
    
    mock_arg_a = MagicMock(name="MockArgument_a_from_complete")
    mock_arg_a.getName.return_value = "a"
    mock_arg_a.equals.side_effect = lambda other: hasattr(other, 'getName') and callable(other.getName) and other.getName() == "a"
    mock_arg_a.hashCode.side_effect = lambda: hash("a_complete")
    mock_arg_a.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
    mock_arg_a._constructor_args = (JClass_provider("java.lang.String")("a"),)


    mock_arg_b = MagicMock(name="MockArgument_b_from_complete")
    mock_arg_b.getName.return_value = "b"
    mock_arg_b.equals.side_effect = lambda other: hasattr(other, 'getName') and callable(other.getName) and other.getName() == "b"
    mock_arg_b.hashCode.side_effect = lambda: hash("b_complete")
    mock_arg_b.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
    mock_arg_b._constructor_args = (JClass_provider("java.lang.String")("b"),)

    HashSet = JClass_provider("java.util.HashSet")

    ext1 = HashSet()
    ext1.add(mock_arg_a)
    models_coll.append(ext1)

    ext2 = HashSet()
    ext2.add(mock_arg_b)
    models_coll.append(ext2)

    ext3 = HashSet() # Ensemble vide
    models_coll.append(ext3)
    
    mock_logger.info(f"[CONFIGURE CompleteReasoner] Ajout de {len(models_coll)} extensions mockées.")

def configure_stable_reasoner_mock(reasoner_instance_mock, dung_theory_instance, JClass_provider):
    mock_logger.debug(f"[CONFIGURE StableReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}")
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error("[CONFIGURE StableReasoner] _collections['models'] non trouvée.")
        reasoner_instance_mock._collections["models"] = []
        models_coll = reasoner_instance_mock._collections["models"]
    models_coll.clear()

    mock_arg_a = MagicMock(name="MockArgument_a_from_stable")
    mock_arg_a.getName.return_value = "a"
    mock_arg_a.equals.side_effect = lambda other: hasattr(other, 'getName') and callable(other.getName) and other.getName() == "a"
    mock_arg_a.hashCode.side_effect = lambda: hash("a_stable")
    mock_arg_a.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
    mock_arg_a._constructor_args = (JClass_provider("java.lang.String")("a"),)

    mock_arg_c = MagicMock(name="MockArgument_c_from_stable")
    mock_arg_c.getName.return_value = "c"
    mock_arg_c.equals.side_effect = lambda other: hasattr(other, 'getName') and callable(other.getName) and other.getName() == "c"
    mock_arg_c.hashCode.side_effect = lambda: hash("c_stable")
    mock_arg_c.class_name = "org.tweetyproject.arg.dung.syntax.Argument"
    mock_arg_c._constructor_args = (JClass_provider("java.lang.String")("c"),)

    HashSet = JClass_provider("java.util.HashSet")

    ext1 = HashSet()
    ext1.add(mock_arg_a)
    ext1.add(mock_arg_c)
    models_coll.append(ext1)
    
    mock_logger.info(f"[CONFIGURE StableReasoner] Ajout de {len(models_coll)} extensions mockées.")

def configure_preferred_reasoner_mock(reasoner_instance_mock, dung_theory_instance, JClass_provider):
    mock_logger.debug(f"[CONFIGURE PreferredReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}")
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error("[CONFIGURE PreferredReasoner] _collections['models'] non trouvée.")
        reasoner_instance_mock._collections["models"] = []
        models_coll = reasoner_instance_mock._collections["models"]
    models_coll.clear()

    if dung_theory_instance is None:
        mock_logger.warning("[CONFIGURE PreferredReasoner] Aucun argument (DungTheory) fourni.")
        HashSet = JClass_provider("java.util.HashSet")
        empty_set_wrapper = HashSet()
        models_coll.append(empty_set_wrapper)
        return

    if not hasattr(dung_theory_instance, 'class_name') or dung_theory_instance.class_name != "org.tweetyproject.arg.dung.syntax.DungTheory":
        mock_logger.warning(f"[CONFIGURE PreferredReasoner] Argument du constructeur n'est pas une DungTheory mockée: {dung_theory_instance}")
        HashSet = JClass_provider("java.util.HashSet")
        empty_set_wrapper = HashSet()
        models_coll.append(empty_set_wrapper)
        return

    theory_args_list = _get_args_from_theory(dung_theory_instance)
    theory_attacks_list = _get_attacks_from_theory(dung_theory_instance)
    
    mock_logger.debug(f"[CONFIGURE PreferredReasoner] Theory args: {[a.getName() for a in theory_args_list if hasattr(a, 'getName') and callable(a.getName)]}")
    mock_logger.debug(f"[CONFIGURE PreferredReasoner] Theory attacks: {len(theory_attacks_list)} attacks")

    admissible_sets_python = []
    s = theory_args_list
    powerset_tuples = chain.from_iterable(combinations(list(s), r) for r in range(len(s) + 1))

    for subset_tuple in powerset_tuples:
        current_set_mocks = set(subset_tuple)
        if _is_admissible_set_helper(current_set_mocks, theory_args_list, theory_attacks_list):
            admissible_sets_python.append(current_set_mocks)
    
    preferred_extensions_python = []
    if not admissible_sets_python:
        if not theory_args_list :
            preferred_extensions_python.append(set())
    else:
        for s1 in admissible_sets_python:
            is_maximal = True
            for s2 in admissible_sets_python:
                if s1 == s2: continue
                if s1.issubset(s2) and not s2.issubset(s1):
                    is_maximal = False
                    break
            if is_maximal:
                preferred_extensions_python.append(s1)
    
    mock_logger.info(f"[CONFIGURE PreferredReasoner] Found {len(preferred_extensions_python)} preferred extensions (Python sets).")

    HashSet = JClass_provider("java.util.HashSet")
    if not preferred_extensions_python: # Cas où il n'y a pas d'extensions préférées (ex: théorie vide ou cycle impair)
         java_set_mock = HashSet()
         models_coll.append(java_set_mock)
    else:
        for ext_set_mocks in preferred_extensions_python:
            java_set_mock = HashSet()
            for arg_mock in ext_set_mocks:
                java_set_mock.add(arg_mock)
            models_coll.append(java_set_mock)
    
    mock_logger.info(f"[CONFIGURE PreferredReasoner] Models collection populated with {len(models_coll)} preferred extensions.")


def configure_grounded_reasoner_mock(reasoner_instance_mock, dung_theory_instance, JClass_provider):
    mock_logger.debug(f"[CONFIGURE GroundedReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}")
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error("[CONFIGURE GroundedReasoner] _collections['models'] non trouvée.")
        reasoner_instance_mock._collections["models"] = []
        models_coll = reasoner_instance_mock._collections["models"]
    models_coll.clear()

    if dung_theory_instance is None:
        mock_logger.warning("[CONFIGURE GroundedReasoner] Aucun argument (DungTheory) fourni.")
        HashSet = JClass_provider("java.util.HashSet")
        empty_set_wrapper = HashSet()
        models_coll.append(empty_set_wrapper)
        if hasattr(reasoner_instance_mock, 'getModel'): # S'assurer que getModel est un mock
             reasoner_instance_mock.getModel.return_value = empty_set_wrapper
        return

    if not hasattr(dung_theory_instance, 'class_name') or dung_theory_instance.class_name != "org.tweetyproject.arg.dung.syntax.DungTheory":
        mock_logger.warning(f"[CONFIGURE GroundedReasoner] Argument du constructeur n'est pas une DungTheory mockée: {dung_theory_instance}")
        HashSet = JClass_provider("java.util.HashSet")
        empty_set_wrapper = HashSet()
        models_coll.append(empty_set_wrapper)
        if hasattr(reasoner_instance_mock, 'getModel'):
            reasoner_instance_mock.getModel.return_value = empty_set_wrapper
        return

    theory_args_list = _get_args_from_theory(dung_theory_instance)
    theory_attacks_list = _get_attacks_from_theory(dung_theory_instance)

    mock_logger.debug(f"[CONFIGURE GroundedReasoner] Theory args: {[a.getName() for a in theory_args_list if hasattr(a, 'getName') and callable(a.getName)]}")
    
    grounded_extension_mocks = set()
    if not theory_args_list:
        mock_logger.info("[CONFIGURE GroundedReasoner] Empty theory, grounded extension is empty set.")
    else:
        current_s = set()
        while True:
            previous_s = current_s.copy()
            next_s = set()
            for arg_candidate_mock in theory_args_list:
                if _is_arg_defended_by_set_helper(arg_candidate_mock, previous_s, theory_args_list, theory_attacks_list):
                    next_s.add(arg_candidate_mock)
            current_s = next_s
            if current_s == previous_s:
                break
        grounded_extension_mocks = current_s
    
    mock_logger.info(f"[CONFIGURE GroundedReasoner] Calculated grounded extension (Python set): {[a.getName() for a in grounded_extension_mocks if hasattr(a, 'getName') and callable(a.getName)]}")

    HashSet = JClass_provider("java.util.HashSet")
    java_set_mock = HashSet()
    for arg_mock in grounded_extension_mocks:
        java_set_mock.add(arg_mock)
    models_coll.append(java_set_mock)
    
    # S'assurer que getModel() pour GroundedReasoner retourne directement le HashSet calculé
    if hasattr(reasoner_instance_mock, 'getModel'):
        reasoner_instance_mock.getModel.return_value = java_set_mock
    
    mock_logger.info(f"[CONFIGURE GroundedReasoner] Models collection populated with 1 grounded extension (size: {java_set_mock.size()}). getModel will return this set directly.")

mock_logger.info("Module jpype_components.tweety_reasoners initialisé.")