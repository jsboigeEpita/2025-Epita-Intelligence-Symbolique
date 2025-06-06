# argumentation_analysis/agents/core/logic/tweety_bridge.py
"""
Interface avec TweetyProject via JPype pour l'exécution de requêtes logiques.

Ce module fournit la classe `TweetyBridge` qui sert d'interface Python
pour interagir avec les bibliothèques Java de TweetyProject. Elle permet
de parser des formules et des ensembles de croyances, de valider leur syntaxe,
et d'exécuter des requêtes pour la logique propositionnelle, la logique du
premier ordre, et la logique modale. L'interaction avec Java est gérée
par la bibliothèque JPype.
"""

import logging
from typing import Tuple, Optional, Any, Dict, List

import jpype
# from argumentation_analysis.core.jvm_setup import initialize_jvm # Remplacé par TweetyInitializer
# from argumentation_analysis.paths import LIBS_DIR # Remplacé par TweetyInitializer
from semantic_kernel.functions import kernel_function

from .tweety_initializer import TweetyInitializer
from .pl_handler import PLHandler
from .fol_handler import FOLHandler
from .modal_handler import ModalHandler

# Configuration du logger
logger = logging.getLogger("Orchestration.TweetyBridge")

class TweetyBridge:
    """
    Interface avec TweetyProject via JPype pour différents types de logiques.

    Cette classe encapsule la communication avec TweetyProject, permettant
    l'analyse syntaxique, la validation et le raisonnement sur des bases de
    croyances en logique propositionnelle (PL), logique du premier ordre (FOL),
    et logique modale (ML). Elle utilise les handlers dédiés (PLHandler,
    FOLHandler, ModalHandler) qui s'appuient sur TweetyInitializer pour la
    gestion de la JVM et des composants Java de TweetyProject.

    Attributes:
        _logger (logging.Logger): Logger pour cette classe.
        _jvm_ok (bool): Indique si les handlers Python sont prêts.
        _initializer (TweetyInitializer): Instance du gestionnaire d'initialisation Tweety.
        _pl_handler (PLHandler): Handler pour la logique propositionnelle.
        _fol_handler (FOLHandler): Handler pour la logique du premier ordre.
        _modal_handler (ModalHandler): Handler pour la logique modale.
    """
    
    def __init__(self):
        """
        Initialise l'interface TweetyBridge et ses handlers.

        S'appuie sur TweetyInitializer pour la gestion de la JVM et des
        composants Java sous-jacents.
        """
        self._logger = logger
        self._logger.info("TWEETY_BRIDGE: __init__ - Début (Refactored)")
        self._jvm_ok = False # Sera mis à True si tous les handlers s'initialisent correctement

        # Initialiser TweetyInitializer (qui gère la JVM et les composants Java)
        # TweetyInitializer est instancié ici.
        self._initializer = TweetyInitializer(self) # TweetyInitializer prend l'instance de TweetyBridge
        if not self._initializer.is_jvm_started(): # Utiliser la méthode correcte de TweetyInitializer
            self._logger.info("TWEETY_BRIDGE: __init__ - JVM non prête, tentative d'initialisation via TweetyInitializer...")
            # TweetyInitializer._start_jvm() est appelé dans son __init__ si nécessaire.
            # Il faut s'assurer que les composants spécifiques sont prêts.
            # self._initializer.start_jvm_and_initialize() # Cette méthode n'existe pas sur TweetyInitializer
            # L'appel à _start_jvm est fait dans __init__ de TweetyInitializer.
            # Il faut ensuite s'assurer que les composants sont initialisés.
            if not self._initializer.is_jvm_started(): # Vérifier à nouveau après l'init de TweetyInitializer
                self._logger.error("TWEETY_BRIDGE: __init__ - Échec critique de l'initialisation de la JVM via TweetyInitializer.")
                raise RuntimeError("TweetyBridge ne peut pas fonctionner sans une JVM initialisée.")
        else:
            self._logger.info("TWEETY_BRIDGE: __init__ - JVM déjà prête ou initialisée par TweetyInitializer.")

        # S'assurer que les composants spécifiques sont initialisés (PL, FOL, Modal)
        # Ces appels sont idempotents dans TweetyInitializer s'ils ont déjà été faits.
        self._initializer.initialize_pl_components()
        self._initializer.initialize_fol_components()
        self._initializer.initialize_modal_components()

        # Initialiser les handlers spécifiques
        try:
            self._pl_handler = PLHandler(self._initializer)
            self._fol_handler = FOLHandler(self._initializer)
            self._modal_handler = ModalHandler(self._initializer)
            self._jvm_ok = True # Indique que les handlers Python sont prêts
            self._logger.info("TWEETY_BRIDGE: __init__ - Handlers PL, FOL, Modal initialisés avec succès.")
        except RuntimeError as e:
            self._logger.error(f"TWEETY_BRIDGE: __init__ - Erreur lors de l'initialisation des handlers: {e}", exc_info=True)
            self._jvm_ok = False # Marquer comme non prêt si un handler échoue
            # Il est important de lever l'exception ici pour signaler que TweetyBridge n'est pas fonctionnel.
            raise RuntimeError(f"Échec de l'initialisation d'un handler dans TweetyBridge: {e}") from e
        
        self._logger.info(f"TWEETY_BRIDGE: __init__ - Fin (Refactored). _jvm_ok: {self._jvm_ok}")
    
    def is_jvm_ready(self) -> bool:
        """
        Vérifie si la JVM, TweetyInitializer et les handlers Python sont prêts.

        :return: True si tout est initialisé correctement, False sinon.
        :rtype: bool
        """
        # Vérifie que l'initializer est là, que la JVM est prête via l'initializer,
        # et que les handlers Python ont été instanciés (indiqué par self._jvm_ok dans __init__).
        return (
            self._initializer is not None and
            self._initializer.is_jvm_started() and # Utiliser la méthode correcte de TweetyInitializer
            hasattr(self, '_pl_handler') and self._pl_handler is not None and
            hasattr(self, '_fol_handler') and self._fol_handler is not None and
            hasattr(self, '_modal_handler') and self._modal_handler is not None and
            self._jvm_ok # Ce flag interne à TweetyBridge indique si les handlers Python sont OK
        )

    # Les méthodes _initialize_jvm_components, _initialize_pl_components,
    # _initialize_fol_components, et _initialize_modal_components
    # sont maintenant gérées par TweetyInitializer et appelées depuis __init__.
    # Elles peuvent être supprimées de TweetyBridge.

    # La méthode _remove_comments_and_empty_lines sera supprimée plus tard si elle n'est plus nécessaire.
    def _remove_comments_and_empty_lines(self, text: str) -> List[str]:
        """
        Supprime les lignes de commentaire (commençant par '%' pour Tweety) et les lignes vides.
        Sépare les formules sur la même ligne si elles sont délimitées par ';'.
        Les espaces en début/fin de ligne sont également supprimés pour chaque formule.
        Retourne une liste de chaînes de formules propres.
        """
        if text is None:
            return []
        
        text_with_actual_newlines = text.replace("\\n", "\n")
        raw_lines = text_with_actual_newlines.splitlines()
        final_formulas: List[str] = []
        
        for line_content in raw_lines:
            # 1. Enlever les commentaires de la ligne entière (Tweety utilise '%' pour les commentaires)
            line_no_comments = line_content.split('%')[0].strip()
            if not line_no_comments: # Si la ligne est vide ou ne contient qu'un commentaire
                continue

            # 2. Séparer les formules sur la ligne par des points-virgules.
            potential_formulas_on_line = line_no_comments.split(';')
            
            for pf_str in potential_formulas_on_line:
                formula_candidate = pf_str.strip()
                if formula_candidate: # S'assurer que la formule n'est pas vide après strip
                    final_formulas.append(formula_candidate)
                    
        self._logger.debug(f"_remove_comments_and_empty_lines: a retourné {len(final_formulas)} formules: {final_formulas}")
        return final_formulas

    # --- Méthodes pour la logique propositionnelle ---
    
    def validate_formula(self, formula_string: str) -> Tuple[bool, str]:
        """
        Valide la syntaxe d'une formule de logique propositionnelle.
        Délègue la validation au PLHandler.
        """
        if not self.is_jvm_ready() or not hasattr(self, '_pl_handler'):
            return False, "TweetyBridge ou PLHandler non prêt."
        
        self._logger.debug(f"TweetyBridge.validate_formula (PL) appelée pour: '{formula_string}'")
        try:
            # PLHandler.parse_pl_formula lève une ValueError en cas d'échec de parsing.
            # Si elle ne lève pas d'exception, la formule est syntaxiquement valide.
            self._pl_handler.parse_pl_formula(formula_string)
            self._logger.info(f"Formule PL '{formula_string}' validée avec succès par PLHandler.")
            return True, "Formule valide"
        except ValueError as e_val:
            self._logger.warning(f"Erreur de syntaxe PL pour '{formula_string}' détectée par PLHandler: {e_val}")
            return False, f"Erreur de syntaxe: {str(e_val)}"
        except Exception as e_generic:
            self._logger.error(f"Erreur inattendue lors de la validation PL de '{formula_string}': {e_generic}", exc_info=True)
            return False, f"Erreur inattendue: {str(e_generic)}"

    def validate_belief_set(self, belief_set_string: str) -> Tuple[bool, str]:
        """
        Valide la syntaxe d'un ensemble de croyances en logique propositionnelle.
        Délègue la validation au PLHandler.
        """
        if not self.is_jvm_ready() or not hasattr(self, '_pl_handler'):
            return False, "TweetyBridge ou PLHandler non prêt."

        self._logger.debug(f"TweetyBridge.validate_belief_set (PL) appelée pour BS: '{belief_set_string[:100]}...'")
        try:
            # PLHandler.pl_check_consistency parse implicitement le belief set.
            # Si le parsing échoue pour une formule, il devrait lever une ValueError.
            # Pour une simple validation syntaxique, on peut essayer de parser chaque formule.
            # Ou, si pl_check_consistency est robuste aux erreurs de parsing et les signale,
            # on pourrait l'utiliser. Pour l'instant, on simule le parsing.
            
            # PLHandler.pl_check_consistency va parser. Si une erreur survient, elle sera propagée.
            # Un ensemble vide ou avec commentaires seulement sera géré par le handler.
            # Si aucune exception n'est levée, on considère que la syntaxe est globalement ok.
            # Note: pl_check_consistency retourne un booléen pour la cohérence, pas pour la validité syntaxique.
            # Il faut une méthode dédiée dans PLHandler pour la validation syntaxique du BS.
            # En attendant, on peut essayer de parser chaque formule.

            # Solution temporaire : utiliser _remove_comments_and_empty_lines ici
            # et parser chaque formule via le handler.
            # Idéalement, PLHandler aurait une méthode validate_syntax_belief_set.
            cleaned_formulas = self._remove_comments_and_empty_lines(belief_set_string)
            if not cleaned_formulas:
                return False, "Ensemble de croyances vide ou ne contenant que des commentaires"

            for formula_str in cleaned_formulas:
                self._pl_handler.parse_pl_formula(formula_str) # Lèvera ValueError si invalide

            self._logger.info(f"Ensemble de croyances PL validé avec succès par PLHandler (parsing individuel).")
            return True, "Ensemble de croyances valide"
            
        except ValueError as e_val:
            self._logger.warning(f"Erreur de syntaxe dans le BS PL détectée par PLHandler: {e_val}")
            return False, f"Erreur de syntaxe: {str(e_val)}"
        except Exception as e_generic:
            self._logger.error(f"Erreur inattendue lors de la validation du BS PL: {e_generic}", exc_info=True)
            return False, f"Erreur inattendue: {str(e_generic)}"

    @kernel_function(
        description="Exécute une requête en Logique Propositionnelle (syntaxe Tweety: !,||,=>,<=>,^^) sur un Belief Set fourni.",
        name="execute_pl_query"
    )
    def perform_pl_query(self, belief_set_content: str, query_string: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête PL et retourne le résultat booléen brut et une chaîne de sortie.
        """
        self._logger.info(f"TweetyBridge.perform_pl_query: Query='{query_string}' sur BS: ('{belief_set_content[:60]}...')")
        if not self.is_jvm_ready() or not hasattr(self, '_pl_handler'):
            self._logger.error("TweetyBridge.perform_pl_query: TweetyBridge ou PLHandler non prêt.")
            return None, "Erreur: TweetyBridge ou PLHandler non prêt."

        try:
            result_bool = self._pl_handler.pl_query(belief_set_content, query_string)
            
            if result_bool is None:
                result_str = f"Tweety Result: Unknown for query '{query_string}'."
                self._logger.warning(f"Requête PL '{query_string}' -> indéterminé (None) via PLHandler.")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: Query '{query_string}' is {result_label}."
                self._logger.info(f"Résultat formaté requête PL '{query_string}' via PLHandler: {result_label}")
            
            return result_bool, result_str

        except ValueError as e_val:
            error_msg = f"Erreur lors de l'exécution de la requête PL via PLHandler: {str(e_val)}"
            self._logger.error(error_msg, exc_info=True)
            return None, f"ERREUR: {error_msg}"
        except Exception as e_generic:
            error_msg = f"Erreur inattendue lors de l'exécution de la requête PL: {str(e_generic)}"
            self._logger.error(error_msg, exc_info=True)
            return None, f"ERREUR: {error_msg}"

    def execute_pl_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Exécute une requête en logique propositionnelle sur un ensemble de croyances donné.
        Délègue l'exécution au PLHandler et retourne une chaîne formatée.
        """
        _, result_str = self.perform_pl_query(belief_set_content, query_string)
        return result_str

    # Les méthodes _parse_pl_formula, _parse_pl_belief_set, _execute_pl_query_internal
    # sont maintenant encapsulées dans PLHandler et peuvent être supprimées ici.
            
    # --- Méthodes pour la logique du premier ordre ---

    def validate_fol_formula(self, formula_string: str, signature_declarations_str: Optional[str] = None) -> Tuple[bool, str]:
        """
        Valide la syntaxe d'une formule de logique du premier ordre (FOL).
        Délègue la validation au FOLHandler.
        """
        if not self.is_jvm_ready() or not hasattr(self, '_fol_handler'):
            return False, "TweetyBridge ou FOLHandler non prêt."

        self._logger.debug(f"TweetyBridge.validate_fol_formula appelée pour: '{formula_string}'")
        try:
            # FOLHandler.parse_fol_formula lève une ValueError en cas d'échec.
            # Le paramètre signature_declarations_str est géré par le handler.
            self._fol_handler.parse_fol_formula(formula_string, signature_declarations_str)
            self._logger.info(f"Formule FOL '{formula_string}' validée avec succès par FOLHandler.")
            return True, "Formule FOL valide"
        except ValueError as e_val:
            self._logger.warning(f"Erreur de syntaxe FOL pour '{formula_string}' détectée par FOLHandler: {e_val}")
            return False, f"Erreur de syntaxe FOL: {str(e_val)}"
        except Exception as e_generic:
            self._logger.error(f"Erreur inattendue lors de la validation FOL de '{formula_string}': {e_generic}", exc_info=True)
            return False, f"Erreur FOL inattendue: {str(e_generic)}"

    def validate_fol_belief_set(self, belief_set_string: str, signature_declarations_str: Optional[str] = None) -> Tuple[bool, str]:
        """
        Valide la syntaxe d'un ensemble de croyances en logique du premier ordre (FOL).
        Délègue la validation au FOLHandler.
        """
        if not self.is_jvm_ready() or not hasattr(self, '_fol_handler'):
            return False, "TweetyBridge ou FOLHandler non prêt."

        self._logger.debug(f"TweetyBridge.validate_fol_belief_set appelée pour BS: '{belief_set_string[:100]}...'")
        try:
            # Similaire à PL, FOLHandler devrait avoir une méthode pour valider la syntaxe du BS.
            # En attendant, on parse chaque formule individuellement après nettoyage.
            # FOLHandler.fol_check_consistency parse aussi, mais son but est la cohérence.
            
            # Solution temporaire : utiliser _remove_comments_and_empty_lines ici
            # et parser chaque formule via le handler.
            cleaned_formulas = self._remove_comments_and_empty_lines(belief_set_string)
            if not cleaned_formulas:
                return False, "Ensemble de croyances FOL vide ou ne contenant que des commentaires"

            for formula_str in cleaned_formulas:
                self._fol_handler.parse_fol_formula(formula_str, signature_declarations_str) # Lèvera ValueError

            self._logger.info(f"Ensemble de croyances FOL validé avec succès par FOLHandler (parsing individuel).")
            return True, "Ensemble de croyances FOL valide"
            
        except ValueError as e_val:
            self._logger.warning(f"Erreur de syntaxe dans le BS FOL détectée par FOLHandler: {e_val}")
            return False, f"Erreur de syntaxe FOL: {str(e_val)}"
        except Exception as e_generic:
            self._logger.error(f"Erreur inattendue lors de la validation du BS FOL: {e_generic}", exc_info=True)
            return False, f"Erreur FOL inattendue: {str(e_generic)}"

    @kernel_function(
        description="Exécute une requête en Logique du Premier Ordre sur un Belief Set fourni. Peut inclure des déclarations de signature.",
        name="execute_fol_query"
    )
    def execute_fol_query(self, belief_set_content: str, query_string: str, signature_declarations_str: Optional[str] = None) -> str:
        """
        Exécute une requête en logique du premier ordre (FOL) sur un ensemble de croyances.
        Délègue l'exécution au FOLHandler.
        """
        self._logger.info(f"TweetyBridge.execute_fol_query: Query='{query_string}' sur BS: ('{belief_set_content[:60]}...'), Signature: '{str(signature_declarations_str)[:60]}...'")
        
        if not self.is_jvm_ready() or not hasattr(self, '_fol_handler'):
            self._logger.error("TweetyBridge.execute_fol_query: TweetyBridge ou FOLHandler non prêt.")
            return "FUNC_ERROR: TweetyBridge ou FOLHandler non prêt."
        
        try:
            result_bool = self._fol_handler.fol_query(belief_set_content, query_string, signature_declarations_str)
            
            if result_bool is None: # FOLHandler.fol_query peut retourner None si le raisonneur ne peut pas conclure
                result_str = f"Tweety Result: Unknown for FOL query '{query_string}'."
                self._logger.warning(f"Requête FOL '{query_string}' -> indéterminé (None) via FOLHandler.")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: FOL Query '{query_string}' is {result_label}."
                self._logger.info(f"Résultat formaté requête FOL '{query_string}' via FOLHandler: {result_label}")
            
            return result_str
            
        except ValueError as e_val: # Erreurs de parsing ou autres du handler
            error_msg = f"Erreur lors de l'exécution de la requête FOL via FOLHandler: {str(e_val)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
        except Exception as e_generic: # Erreurs inattendues
            error_msg = f"Erreur inattendue lors de l'exécution de la requête FOL: {str(e_generic)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"

    # Les méthodes _parse_fol_formula, _parse_fol_belief_set, _execute_fol_query_internal
    # sont maintenant encapsulées dans FOLHandler et peuvent être supprimées ici.
    
    # --- Méthodes pour la logique modale ---

    def validate_modal_formula(self, formula_string: str, modal_logic_str: str = "S4", signature_declarations_str: Optional[str] = None) -> Tuple[bool, str]:
        """
        Valide la syntaxe d'une formule de logique modale (ML).
        Délègue la validation au ModalHandler.
        """
        if not self.is_jvm_ready() or not hasattr(self, '_modal_handler'):
            return False, "TweetyBridge ou ModalHandler non prêt."

        self._logger.debug(f"TweetyBridge.validate_modal_formula appelée pour: '{formula_string}', Logic: {modal_logic_str}")
        try:
            # ModalHandler.parse_modal_formula lève une ValueError en cas d'échec.
            self._modal_handler.parse_modal_formula(formula_string, modal_logic_str) # signature_declarations_str n'est pas utilisé par parse_modal_formula
            self._logger.info(f"Formule Modale '{formula_string}' (Logic: {modal_logic_str}) validée avec succès par ModalHandler.")
            return True, "Formule Modale valide"
        except ValueError as e_val:
            self._logger.warning(f"Erreur de syntaxe Modale pour '{formula_string}' (Logic: {modal_logic_str}) détectée par ModalHandler: {e_val}")
            return False, f"Erreur de syntaxe Modale: {str(e_val)}"
        except Exception as e_generic:
            self._logger.error(f"Erreur inattendue lors de la validation Modale de '{formula_string}': {e_generic}", exc_info=True)
            return False, f"Erreur Modale inattendue: {str(e_generic)}"

    def validate_modal_belief_set(self, belief_set_string: str, modal_logic_str: str = "S4", signature_declarations_str: Optional[str] = None) -> Tuple[bool, str]:
        """
        Valide la syntaxe d'un ensemble de croyances en logique modale (ML).
        Délègue la validation au ModalHandler.
        """
        if not self.is_jvm_ready() or not hasattr(self, '_modal_handler'):
            return False, "TweetyBridge ou ModalHandler non prêt."

        self._logger.debug(f"TweetyBridge.validate_modal_belief_set appelée pour BS: '{belief_set_string[:100]}...', Logic: {modal_logic_str}")
        try:
            # Solution temporaire : utiliser _remove_comments_and_empty_lines ici
            # et parser chaque formule via le handler.
            cleaned_formulas = self._remove_comments_and_empty_lines(belief_set_string)
            if not cleaned_formulas:
                return False, "Ensemble de croyances Modal vide ou ne contenant que des commentaires"

            for formula_str in cleaned_formulas:
                self._modal_handler.parse_modal_formula(formula_str, modal_logic_str) # signature_declarations_str non pertinent pour le parsing simple de formule

            self._logger.info(f"Ensemble de croyances Modal (Logic: {modal_logic_str}) validé avec succès par ModalHandler (parsing individuel).")
            return True, "Ensemble de croyances Modal valide"
            
        except ValueError as e_val:
            self._logger.warning(f"Erreur de syntaxe dans le BS Modal (Logic: {modal_logic_str}) détectée par ModalHandler: {e_val}")
            return False, f"Erreur de syntaxe Modale: {str(e_val)}"
        except Exception as e_generic:
            self._logger.error(f"Erreur inattendue lors de la validation du BS Modal (Logic: {modal_logic_str}): {e_generic}", exc_info=True)
            return False, f"Erreur Modale inattendue: {str(e_generic)}"

    @kernel_function(
        description="Exécute une requête en Logique Modale sur un Belief Set fourni. Spécifier la logique modale (ex: S4, K) et optionnellement les déclarations de signature.",
        name="execute_modal_query"
    )
    def execute_modal_query(self, belief_set_content: str, query_string: str, modal_logic_str: str = "S4", signature_declarations_str: Optional[str] = None) -> str:
        """
        Exécute une requête en logique modale (ML) sur un ensemble de croyances.
        Délègue l'exécution au ModalHandler.
        """
        self._logger.info(f"TweetyBridge.execute_modal_query: Query='{query_string}' sur BS: ('{belief_set_content[:60]}...'), Logic: {modal_logic_str}, Signature: '{str(signature_declarations_str)[:60]}...'")
        
        if not self.is_jvm_ready() or not hasattr(self, '_modal_handler'):
            self._logger.error("TweetyBridge.execute_modal_query: TweetyBridge ou ModalHandler non prêt.")
            return "FUNC_ERROR: TweetyBridge ou ModalHandler non prêt."
        
        try:
            result_bool = self._modal_handler.modal_query(belief_set_content, query_string, modal_logic_str, signature_declarations_str)
            
            if result_bool is None: # ModalHandler.modal_query peut retourner None
                result_str = f"Tweety Result: Unknown for Modal query '{query_string}' (Logic: {modal_logic_str})."
                self._logger.warning(f"Requête Modale '{query_string}' (Logic: {modal_logic_str}) -> indéterminé (None) via ModalHandler.")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: Modal Query '{query_string}' (Logic: {modal_logic_str}) is {result_label}."
                self._logger.info(f"Résultat formaté requête Modale '{query_string}' (Logic: {modal_logic_str}) via ModalHandler: {result_label}")
            
            return result_str
            
        except ValueError as e_val:
            error_msg = f"Erreur lors de l'exécution de la requête Modale via ModalHandler: {str(e_val)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
        except Exception as e_generic:
            error_msg = f"Erreur inattendue lors de l'exécution de la requête Modale: {str(e_generic)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"

    # Les méthodes _parse_modal_formula, _parse_modal_belief_set, _execute_modal_query_internal
    # sont maintenant encapsulées dans ModalHandler et peuvent être supprimées ici.

# Fin des méthodes de la classe TweetyBridge