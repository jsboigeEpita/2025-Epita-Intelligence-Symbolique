# argumentation_analysis/agents/core/logic/tweety_bridge.py
"""
Interface avec TweetyProject via JPype.
"""

import logging
from typing import Tuple, Optional, Any, Dict

import jpype
from semantic_kernel.functions import kernel_function

# Configuration du logger
logger = logging.getLogger("Orchestration.TweetyBridge")

class TweetyBridge:
    """
    Interface avec TweetyProject via JPype.
    
    Cette classe fournit une interface unifiée pour interagir avec TweetyProject
    pour différents types de logiques (propositionnelle, premier ordre, modale).
    """
    
    def __init__(self):
        """
        Initialise l'interface TweetyBridge.
        """
        self._logger = logger
        self._jvm_ok = False
        
        # Classes Java pour la logique propositionnelle
        self._PlParser = None
        self._SatReasoner = None
        self._PlFormula = None
        
        # Classes Java pour la logique du premier ordre
        self._FolParser = None
        self._FolReasoner = None
        self._FolFormula = None
        
        # Classes Java pour la logique modale
        self._ModalParser = None
        self._ModalReasoner = None
        self._ModalFormula = None
        
        # Instances des parsers et raisonneurs
        self._pl_parser_instance = None
        self._pl_reasoner_instance = None
        self._fol_parser_instance = None
        self._fol_reasoner_instance = None
        self._modal_parser_instance = None
        self._modal_reasoner_instance = None
        
        # Tenter l'initialisation des composants JVM
        if jpype.isJVMStarted():
            self._initialize_jvm_components()
        else:
            self._logger.warning("JVM non démarrée à l'initialisation de TweetyBridge. Composants non chargés.")
            self._jvm_ok = False # S'assurer que _jvm_ok est False
    
    def is_jvm_ready(self) -> bool:
        """
        Vérifie si la JVM est prête.
        
        Returns:
            True si la JVM est démarrée, False sinon
        """
        return jpype.isJVMStarted() and self._jvm_ok
    
    def _initialize_jvm_components(self) -> None:
        """
        Initialise les composants JVM pour TweetyProject.
        """
        # Vérifier si la JVM est démarrée
        if not jpype.isJVMStarted():
            self._logger.critical("Tentative d'initialisation alors que la JVM n'est PAS démarrée!")
            self._jvm_ok = False
            return
        
        self._logger.info("JVM démarrée. Tentative de chargement des classes Tweety...")
        
        try:
            # Initialiser les composants pour la logique propositionnelle
            self._initialize_pl_components()
            
            # Initialiser les composants pour la logique du premier ordre
            self._initialize_fol_components()
            
            # Initialiser les composants pour la logique modale
            self._initialize_modal_components()
            
            # Si tout réussit
            self._jvm_ok = True
            self._logger.info("✅ Classes et instances Java Tweety chargées avec succès.")
        except Exception as e:
            self._logger.critical(f"❌ Erreur chargement classes/instances Tweety: {e}", exc_info=True)
            self._jvm_ok = False
    
    def _initialize_pl_components(self) -> None:
        """
        Initialise les composants pour la logique propositionnelle.
        """
        try:
            # Charger les classes
            self._PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
            self._SatReasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner")
            self._PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
            
            # Créer les instances
            self._pl_parser_instance = self._PlParser()
            self._pl_reasoner_instance = self._SatReasoner()
            
            self._logger.info("✅ Composants pour la logique propositionnelle initialisés.")
        
        except Exception as e:
            self._logger.error(f"❌ Erreur initialisation composants logique propositionnelle: {e}", exc_info=True)
            raise
    
    def _initialize_fol_components(self) -> None:
        """
        Initialise les composants pour la logique du premier ordre.
        """
        try:
            # Charger les classes
            self._FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
            self._FolReasoner = jpype.JClass("org.tweetyproject.logics.fol.reasoner.FolReasoner") # Pour type hinting
            self._SimpleFolReasoner = jpype.JClass("org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner") # Classe concrète
            self._FolFormula = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolFormula")
            
            # Créer les instances
            self._fol_parser_instance = self._FolParser()
            self._fol_reasoner_instance = self._SimpleFolReasoner() # Utiliser la classe concrète
            
            self._logger.info("✅ Composants pour la logique du premier ordre initialisés.")
        
        except Exception as e:
            self._logger.error(f"❌ Erreur initialisation composants logique du premier ordre: {e}", exc_info=True)
            # Ne pas lever d'exception pour permettre l'initialisation partielle
            self._logger.warning("La logique du premier ordre ne sera pas disponible.")
    
    def _initialize_modal_components(self) -> None:
        """
        Initialise les composants pour la logique modale.
        """
        try:
            # Charger les classes
            self._ModalParser = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser") # Nom corrigé
            self._AbstractModalReasoner = jpype.JClass("org.tweetyproject.logics.ml.reasoner.AbstractMlReasoner") # Pour type hinting
            self._SimpleModalReasoner = jpype.JClass("org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner") # Classe concrète
            self._ModalFormula = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalFormula")
            
            # Créer les instances
            self._modal_parser_instance = self._ModalParser()
            self._modal_reasoner_instance = self._SimpleModalReasoner() # Utiliser la classe concrète
            
            self._logger.info("✅ Composants pour la logique modale initialisés.")
        
        except Exception as e:
            self._logger.error(f"❌ Erreur initialisation composants logique modale: {e}", exc_info=True)
            # Ne pas lever d'exception pour permettre l'initialisation partielle
            self._logger.warning("La logique modale ne sera pas disponible.")
    
    # --- Méthodes pour la logique propositionnelle ---
    
    def validate_formula(self, formula_string: str) -> Tuple[bool, str]:
        """
        Valide une formule de logique propositionnelle.
        
        Args:
            formula_string: La formule à valider
            
        Returns:
            Un tuple (is_valid, message)
        """
        if not self._jvm_ok or not self._pl_parser_instance:
            return False, "JVM ou parser non prêt"
        
        try:
            self._pl_parser_instance.parseFormula(formula_string)
            return True, "Formule valide"
        
        except jpype.JException as e_java:
            return False, f"Erreur de syntaxe: {e_java.getMessage()}"
        
        except Exception as e:
            return False, f"Erreur: {str(e)}"
    
    def validate_belief_set(self, belief_set_string: str) -> Tuple[bool, str]:
        """
        Valide un ensemble de croyances de logique propositionnelle.
        
        Args:
            belief_set_string: L'ensemble de croyances à valider
            
        Returns:
            Un tuple (is_valid, message)
        """
        if not self._jvm_ok or not self._pl_parser_instance:
            return False, "JVM ou parser non prêt"
        
        try:
            belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n")
            parsed_bs = self._pl_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            # Vérifier si l'ensemble de croyances est vide
            bs_str_repr = str(parsed_bs).strip()
            if not bs_str_repr or all(line.strip().startswith("#") for line in bs_str_repr.splitlines() if line.strip()):
                return False, "Ensemble de croyances vide ou ne contenant que des commentaires"
            
            return True, "Ensemble de croyances valide"
        
        except jpype.JException as e_java:
            error_msg = f"Erreur de syntaxe: {e_java.getMessage()}"
            
            # Ajouter contexte sur la ligne potentielle causant l'erreur si possible
            # Utiliser getMessage() qui est la méthode standard et mockée
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_msg += f" (Probablement près de la ligne {line_info})"
                except Exception:
                    pass # Ignorer si l'extraction de la ligne échoue
            
            return False, error_msg
        
        except Exception as e:
            return False, f"Erreur: {str(e)}"
    
    @kernel_function(
        description="Exécute une requête en Logique Propositionnelle (syntaxe Tweety: !,||,=>,<=>,^^) sur un Belief Set fourni.",
        name="execute_pl_query"
    )
    def execute_pl_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Exécute une requête en logique propositionnelle.
        
        Args:
            belief_set_content: Le contenu de l'ensemble de croyances
            query_string: La requête à exécuter
            
        Returns:
            Le résultat formaté de la requête
        """
        self._logger.info(f"Appel execute_pl_query: Query='{query_string}' sur BS ('{belief_set_content[:60]}...')")
        
        if not self._jvm_ok:
            self._logger.error("execute_pl_query: JVM non prête.")
            return "FUNC_ERROR: JVM non prête ou composants Tweety non chargés."
        
        try:
            # Parser l'ensemble de croyances
            belief_set_obj = self._parse_pl_belief_set(belief_set_content)
            if belief_set_obj is None:
                return "FUNC_ERROR: Échec parsing Belief Set. Vérifiez syntaxe."
            
            # Parser la formule
            formula_obj = self._parse_pl_formula(query_string)
            if formula_obj is None:
                return f"FUNC_ERROR: Échec parsing requête '{query_string}'. Vérifiez syntaxe."
            
            # Exécuter la requête
            result_bool = self._execute_pl_query_internal(belief_set_obj, formula_obj)
            
            # Formater le résultat
            if result_bool is None:
                result_str = f"Tweety Result: Unknown for query '{query_string}'."
                self._logger.warning(f"Requête '{query_string}' -> indéterminé (None).")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: Query '{query_string}' is {result_label}."
                self._logger.info(f" -> Résultat formaté requête '{query_string}': {result_label}")
            
            return result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
    
    def _parse_pl_formula(self, formula_string: str) -> Optional[Any]:
        """
        Parse une formule de logique propositionnelle.
        
        Args:
            formula_string: La formule à parser
            
        Returns:
            L'objet formule parsé ou None en cas d'erreur
        """
        if not self._jvm_ok or not self._pl_parser_instance:
            self._logger.error(f"Parse formula: JVM/Parser non prêt ('{formula_string[:60]}...').")
            return None
        
        try:
            self._logger.debug(f"Parsing formule: '{formula_string}'")
            return self._pl_parser_instance.parseFormula(formula_string)
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing formule '{formula_string}': {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            raise RuntimeError(f"Erreur Parsing Formule: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python parsing formule '{formula_string}': {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Parsing Formule: {e}") from e
    
    def _parse_pl_belief_set(self, belief_set_string: str) -> Optional[Any]:
        """
        Parse un ensemble de croyances de logique propositionnelle.
        
        Args:
            belief_set_string: L'ensemble de croyances à parser
            
        Returns:
            L'objet ensemble de croyances parsé ou None en cas d'erreur
        """
        if not self._jvm_ok or not self._pl_parser_instance:
            self._logger.error(f"Parse BS: JVM/Parser non prêt (BS: '{belief_set_string[:60]}...').")
            return None
        
        try:
            belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n")
            self._logger.debug(f"Parsing belief set (nettoyé): '{belief_set_string_cleaned[:100]}...'. Longueur: {len(belief_set_string_cleaned)}")
            parsed_bs = self._pl_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            # Vérifier si l'ensemble de croyances est vide
            bs_str_repr = str(parsed_bs).strip()
            if not bs_str_repr or all(line.strip().startswith("#") for line in bs_str_repr.splitlines() if line.strip()):
                self._logger.warning(f" -> BS parsé semble vide ou ne contient que des commentaires: '{bs_str_repr[:100]}...'")
            else:
                self._logger.debug(f" -> BS parsé (type: {type(parsed_bs)}, size: {parsed_bs.size()}, repr: '{bs_str_repr[:100]}...')")
            
            return parsed_bs
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing BS (extrait: '{belief_set_string[:60]}...'): {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            
            # Ajouter contexte sur la ligne potentielle causant l'erreur si possible
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_context = f" (Probablement près de la ligne {line_info} du belief set)"
                    error_msg += error_context
                except Exception:
                    pass # Ignorer si l'extraction de la ligne échoue
            
            raise RuntimeError(f"Erreur Parsing Belief Set: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python parsing BS: {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Parsing Belief Set: {e}") from e
    
    def _execute_pl_query_internal(self, belief_set_obj: Any, formula_obj: Any) -> Optional[bool]:
        """
        Exécute une requête de logique propositionnelle.
        
        Args:
            belief_set_obj: L'objet ensemble de croyances
            formula_obj: L'objet formule
            
        Returns:
            Le résultat de la requête (True, False ou None si indéterminé)
        """
        if not self._jvm_ok or not self._pl_reasoner_instance or not self._PlFormula:
            self._logger.error("Execute query: JVM/Reasoner/Formula non prêt.")
            return None
        
        try:
            # Vérifier si formula_obj est bien une instance de PlFormula
            if not jpype.JObject(formula_obj, self._PlFormula):
                raise TypeError(f"Objet requête n'est pas un PlFormula (type: {type(formula_obj)})")
            
            # Vérifier si belief_set_obj est valide
            if belief_set_obj is None:
                raise ValueError("Objet Belief Set est None.")
            
            formula_str = str(formula_obj)
            self._logger.debug(f"Exécution requête '{formula_str}' avec raisonneur '{self._pl_reasoner_instance.getClass().getName()}'...")
            
            # Exécuter la requête
            result_java_boolean = self._pl_reasoner_instance.query(belief_set_obj, formula_obj)
            self._logger.debug(f" -> Résultat brut Java pour '{formula_str}': {result_java_boolean}")
            
            # Conversion et retour
            if result_java_boolean is None:
                self._logger.warning(f"Requête Tweety pour '{formula_str}' a retourné null (indéterminé?).")
                return None
            else:
                result_python_bool = bool(result_java_boolean)
                self._logger.info(f" -> Résultat requête Python pour '{formula_str}': {result_python_bool}")
                return result_python_bool
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java exécution requête '{str(formula_obj)}': {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            raise RuntimeError(f"Erreur Exécution Requête Tweety: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python exécution requête '{str(formula_obj)}': {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Exécution Requête: {e}") from e
            
            self._logger.info("✅ Composants pour la logique modale initialisés.")
        
# --- Méthodes pour la logique du premier ordre ---
    
    def validate_fol_formula(self, formula_string: str) -> Tuple[bool, str]:
        """
        Valide une formule de logique du premier ordre.
        
        Args:
            formula_string: La formule à valider
            
        Returns:
            Un tuple (is_valid, message)
        """
        if not self._jvm_ok or not self._fol_parser_instance:
            return False, "JVM ou parser FOL non prêt"
        
        try:
            self._fol_parser_instance.parseFormula(formula_string)
            return True, "Formule FOL valide"
        
        except jpype.JException as e_java:
            return False, f"Erreur de syntaxe FOL: {e_java.getMessage()}"
        
        except Exception as e:
            return False, f"Erreur FOL: {str(e)}"
    
    def validate_fol_belief_set(self, belief_set_string: str) -> Tuple[bool, str]:
        """
        Valide un ensemble de croyances de logique du premier ordre.
        
        Args:
            belief_set_string: L'ensemble de croyances à valider
            
        Returns:
            Un tuple (is_valid, message)
        """
        if not self._jvm_ok or not self._fol_parser_instance:
            return False, "JVM ou parser FOL non prêt"
        
        try:
            belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n")
            parsed_bs = self._fol_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            # Vérifier si l'ensemble de croyances est vide
            bs_str_repr = str(parsed_bs).strip()
            if not bs_str_repr or all(line.strip().startswith("#") for line in bs_str_repr.splitlines() if line.strip()):
                return False, "Ensemble de croyances FOL vide ou ne contenant que des commentaires"
            
            return True, "Ensemble de croyances FOL valide"
        
        except jpype.JException as e_java:
            error_msg = f"Erreur de syntaxe FOL: {e_java.getMessage()}"
            
            # Ajouter contexte sur la ligne potentielle causant l'erreur si possible
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_msg += f" (Probablement près de la ligne {line_info})"
                except Exception:
                    pass # Ignorer si l'extraction de la ligne échoue
            
            return False, error_msg
        
        except Exception as e:
            return False, f"Erreur FOL: {str(e)}"
    
    @kernel_function(
        description="Exécute une requête en Logique du Premier Ordre sur un Belief Set fourni.",
        name="execute_fol_query"
    )
    def execute_fol_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Exécute une requête en logique du premier ordre.
        
        Args:
            belief_set_content: Le contenu de l'ensemble de croyances
            query_string: La requête à exécuter
            
        Returns:
            Le résultat formaté de la requête
        """
        self._logger.info(f"Appel execute_fol_query: Query='{query_string}' sur BS ('{belief_set_content[:60]}...')")
        
        if not self._jvm_ok or not self._fol_parser_instance or not self._fol_reasoner_instance:
            self._logger.error("execute_fol_query: JVM ou composants FOL non prêts.")
            return "FUNC_ERROR: JVM non prête ou composants FOL non chargés."
        
        try:
            # Parser l'ensemble de croyances
            belief_set_obj = self._parse_fol_belief_set(belief_set_content)
            if belief_set_obj is None:
                return "FUNC_ERROR: Échec parsing Belief Set FOL. Vérifiez syntaxe."
            
            # Parser la formule
            formula_obj = self._parse_fol_formula(query_string)
            if formula_obj is None:
                return f"FUNC_ERROR: Échec parsing requête FOL '{query_string}'. Vérifiez syntaxe."
            
            # Exécuter la requête
            result_bool = self._execute_fol_query_internal(belief_set_obj, formula_obj)
            
            # Formater le résultat
            if result_bool is None:
                result_str = f"Tweety Result: Unknown for FOL query '{query_string}'."
                self._logger.warning(f"Requête FOL '{query_string}' -> indéterminé (None).")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: FOL Query '{query_string}' is {result_label}."
                self._logger.info(f" -> Résultat formaté requête FOL '{query_string}': {result_label}")
            
            return result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête FOL: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
    
    def _parse_fol_formula(self, formula_string: str) -> Optional[Any]:
        """
        Parse une formule de logique du premier ordre.
        
        Args:
            formula_string: La formule à parser
            
        Returns:
            L'objet formule parsé ou None en cas d'erreur
        """
        if not self._jvm_ok or not self._fol_parser_instance:
            self._logger.error(f"Parse FOL formula: JVM/Parser non prêt ('{formula_string[:60]}...').")
            return None
        
        try:
            self._logger.debug(f"Parsing formule FOL: '{formula_string}'")
            return self._fol_parser_instance.parseFormula(formula_string)
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing formule FOL '{formula_string}': {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            raise RuntimeError(f"Erreur Parsing Formule FOL: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python parsing formule FOL '{formula_string}': {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Parsing Formule FOL: {e}") from e
    
    def _parse_fol_belief_set(self, belief_set_string: str) -> Optional[Any]:
        """
        Parse un ensemble de croyances de logique du premier ordre.
        
        Args:
            belief_set_string: L'ensemble de croyances à parser
            
        Returns:
            L'objet ensemble de croyances parsé ou None en cas d'erreur
        """
        if not self._jvm_ok or not self._fol_parser_instance:
            self._logger.error(f"Parse FOL BS: JVM/Parser non prêt (BS: '{belief_set_string[:60]}...').")
            return None
        
        try:
            belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n")
            self._logger.debug(f"Parsing FOL belief set (nettoyé): '{belief_set_string_cleaned[:100]}...'. Longueur: {len(belief_set_string_cleaned)}")
            parsed_bs = self._fol_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            # Vérifier si l'ensemble de croyances est vide
            bs_str_repr = str(parsed_bs).strip()
            if not bs_str_repr or all(line.strip().startswith("#") for line in bs_str_repr.splitlines() if line.strip()):
                self._logger.warning(f" -> BS FOL parsé semble vide ou ne contient que des commentaires: '{bs_str_repr[:100]}...'")
            else:
                self._logger.debug(f" -> BS FOL parsé (type: {type(parsed_bs)}, size: {parsed_bs.size()}, repr: '{bs_str_repr[:100]}...')")
            
            return parsed_bs
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing BS FOL (extrait: '{belief_set_string[:60]}...'): {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            
            # Ajouter contexte sur la ligne potentielle causant l'erreur si possible
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_context = f" (Probablement près de la ligne {line_info} du belief set)"
                    error_msg += error_context
                except Exception:
                    pass # Ignorer si l'extraction de la ligne échoue
            
            raise RuntimeError(f"Erreur Parsing Belief Set FOL: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python parsing BS FOL: {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Parsing Belief Set FOL: {e}") from e
    
    def _execute_fol_query_internal(self, belief_set_obj: Any, formula_obj: Any) -> Optional[bool]:
        """
        Exécute une requête de logique du premier ordre.
        
        Args:
            belief_set_obj: L'objet ensemble de croyances
            formula_obj: L'objet formule
            
        Returns:
            Le résultat de la requête (True, False ou None si indéterminé)
        """
        if not self._jvm_ok or not self._fol_reasoner_instance or not self._FolFormula:
            self._logger.error("Execute FOL query: JVM/Reasoner/Formula non prêt.")
            return None
        
        try:
            # Vérifier si formula_obj est bien une instance de FolFormula
            if not jpype.JObject(formula_obj, self._FolFormula):
                raise TypeError(f"Objet requête n'est pas un FolFormula (type: {type(formula_obj)})")
            
            # Vérifier si belief_set_obj est valide
            if belief_set_obj is None:
                raise ValueError("Objet Belief Set FOL est None.")
            
            formula_str = str(formula_obj)
            self._logger.debug(f"Exécution requête FOL '{formula_str}' avec raisonneur '{self._fol_reasoner_instance.getClass().getName()}'...")
            
            # Exécuter la requête
            result_java_boolean = self._fol_reasoner_instance.query(belief_set_obj, formula_obj)
            self._logger.debug(f" -> Résultat brut Java pour FOL '{formula_str}': {result_java_boolean}")
            
            # Conversion et retour
            if result_java_boolean is None:
                self._logger.warning(f"Requête FOL Tweety pour '{formula_str}' a retourné null (indéterminé?).")
                return None
            else:
                result_python_bool = bool(result_java_boolean)
                self._logger.info(f" -> Résultat requête FOL Python pour '{formula_str}': {result_python_bool}")
                return result_python_bool
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java exécution requête FOL '{str(formula_obj)}': {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            raise RuntimeError(f"Erreur Exécution Requête FOL Tweety: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python exécution requête FOL '{str(formula_obj)}': {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Exécution Requête FOL: {e}") from e
    
    # --- Méthodes pour la logique modale ---
    
    def validate_modal_formula(self, formula_string: str) -> Tuple[bool, str]:
        """
        Valide une formule de logique modale.
        
        Args:
            formula_string: La formule à valider
            
        Returns:
            Un tuple (is_valid, message)
        """
        if not self._jvm_ok or not self._modal_parser_instance:
            return False, "JVM ou parser Modal non prêt"
        
        try:
            self._modal_parser_instance.parseFormula(formula_string)
            return True, "Formule modale valide"
        
        except jpype.JException as e_java:
            return False, f"Erreur de syntaxe modale: {e_java.getMessage()}"
        
        except Exception as e:
            return False, f"Erreur modale: {str(e)}"
    
    def validate_modal_belief_set(self, belief_set_string: str) -> Tuple[bool, str]:
        """
        Valide un ensemble de croyances de logique modale.
        
        Args:
            belief_set_string: L'ensemble de croyances à valider
            
        Returns:
            Un tuple (is_valid, message)
        """
        if not self._jvm_ok or not self._modal_parser_instance:
            return False, "JVM ou parser Modal non prêt"
        
        try:
            belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n")
            parsed_bs = self._modal_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            # Vérifier si l'ensemble de croyances est vide
            bs_str_repr = str(parsed_bs).strip()
            if not bs_str_repr or all(line.strip().startswith("#") for line in bs_str_repr.splitlines() if line.strip()):
                return False, "Ensemble de croyances modal vide ou ne contenant que des commentaires"
            
            return True, "Ensemble de croyances modal valide"
        
        except jpype.JException as e_java:
            error_msg = f"Erreur de syntaxe modale: {e_java.getMessage()}"
            
            # Ajouter contexte sur la ligne potentielle causant l'erreur si possible
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_msg += f" (Probablement près de la ligne {line_info})"
                except Exception:
                    pass # Ignorer si l'extraction de la ligne échoue
            
            return False, error_msg
        
        except Exception as e:
            return False, f"Erreur modale: {str(e)}"
    
    @kernel_function(
        description="Exécute une requête en Logique Modale sur un Belief Set fourni.",
        name="execute_modal_query"
    )
    def execute_modal_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Exécute une requête en logique modale.
        
        Args:
            belief_set_content: Le contenu de l'ensemble de croyances
            query_string: La requête à exécuter
            
        Returns:
            Le résultat formaté de la requête
        """
        self._logger.info(f"Appel execute_modal_query: Query='{query_string}' sur BS ('{belief_set_content[:60]}...')")
        
        if not self._jvm_ok or not self._modal_parser_instance or not self._modal_reasoner_instance:
            self._logger.error("execute_modal_query: JVM ou composants Modal non prêts.")
            return "FUNC_ERROR: JVM non prête ou composants Modal non chargés."
        
        try:
            # Parser l'ensemble de croyances
            belief_set_obj = self._parse_modal_belief_set(belief_set_content)
            if belief_set_obj is None:
                return "FUNC_ERROR: Échec parsing Belief Set Modal. Vérifiez syntaxe."
            
            # Parser la formule
            formula_obj = self._parse_modal_formula(query_string)
            if formula_obj is None:
                return f"FUNC_ERROR: Échec parsing requête modale '{query_string}'. Vérifiez syntaxe."
            
            # Exécuter la requête
            result_bool = self._execute_modal_query_internal(belief_set_obj, formula_obj)
            
            # Formater le résultat
            if result_bool is None:
                result_str = f"Tweety Result: Unknown for Modal query '{query_string}'."
                self._logger.warning(f"Requête modale '{query_string}' -> indéterminé (None).")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: Modal Query '{query_string}' is {result_label}."
                self._logger.info(f" -> Résultat formaté requête modale '{query_string}': {result_label}")
            
            return result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête modale: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
    
    def _parse_modal_formula(self, formula_string: str) -> Optional[Any]:
        """
        Parse une formule de logique modale.
        
        Args:
            formula_string: La formule à parser
            
        Returns:
            L'objet formule parsé ou None en cas d'erreur
        """
        if not self._jvm_ok or not self._modal_parser_instance:
            self._logger.error(f"Parse Modal formula: JVM/Parser non prêt ('{formula_string[:60]}...').")
            return None
        
        try:
            self._logger.debug(f"Parsing formule modale: '{formula_string}'")
            return self._modal_parser_instance.parseFormula(formula_string)
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing formule modale '{formula_string}': {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            raise RuntimeError(f"Erreur Parsing Formule modale: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python parsing formule modale '{formula_string}': {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Parsing Formule modale: {e}") from e
    
    def _parse_modal_belief_set(self, belief_set_string: str) -> Optional[Any]:
        """
        Parse un ensemble de croyances de logique modale.
        
        Args:
            belief_set_string: L'ensemble de croyances à parser
            
        Returns:
            L'objet ensemble de croyances parsé ou None en cas d'erreur
        """
        if not self._jvm_ok or not self._modal_parser_instance:
            self._logger.error(f"Parse Modal BS: JVM/Parser non prêt (BS: '{belief_set_string[:60]}...').")
            return None
        
        try:
            belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n")
            self._logger.debug(f"Parsing Modal belief set (nettoyé): '{belief_set_string_cleaned[:100]}...'. Longueur: {len(belief_set_string_cleaned)}")
            parsed_bs = self._modal_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            # Vérifier si l'ensemble de croyances est vide
            bs_str_repr = str(parsed_bs).strip()
            if not bs_str_repr or all(line.strip().startswith("#") for line in bs_str_repr.splitlines() if line.strip()):
                self._logger.warning(f" -> BS Modal parsé semble vide ou ne contient que des commentaires: '{bs_str_repr[:100]}...'")
            else:
                self._logger.debug(f" -> BS Modal parsé (type: {type(parsed_bs)}, size: {parsed_bs.size()}, repr: '{bs_str_repr[:100]}...')")
            
            return parsed_bs
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing BS Modal (extrait: '{belief_set_string[:60]}...'): {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            
            # Ajouter contexte sur la ligne potentielle causant l'erreur si possible
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_context = f" (Probablement près de la ligne {line_info} du belief set)"
                    error_msg += error_context
                except Exception:
                    pass # Ignorer si l'extraction de la ligne échoue
            
            raise RuntimeError(f"Erreur Parsing Belief Set Modal: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python parsing BS Modal: {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Parsing Belief Set Modal: {e}") from e
    
    def _execute_modal_query_internal(self, belief_set_obj: Any, formula_obj: Any) -> Optional[bool]:
        """
        Exécute une requête de logique modale.
        
        Args:
            belief_set_obj: L'objet ensemble de croyances
            formula_obj: L'objet formule
            
        Returns:
            Le résultat de la requête (True, False ou None si indéterminé)
        """
        if not self._jvm_ok or not self._modal_reasoner_instance or not self._ModalFormula:
            self._logger.error("Execute Modal query: JVM/Reasoner/Formula non prêt.")
            return None
        
        try:
            # Vérifier si formula_obj est bien une instance de ModalFormula
            if not jpype.JObject(formula_obj, self._ModalFormula):
                raise TypeError(f"Objet requête n'est pas un ModalFormula (type: {type(formula_obj)})")
            
            # Vérifier si belief_set_obj est valide
            if belief_set_obj is None:
                raise ValueError("Objet Belief Set Modal est None.")
            
            formula_str = str(formula_obj)
            self._logger.debug(f"Exécution requête modale '{formula_str}' avec raisonneur '{self._modal_reasoner_instance.getClass().getName()}'...")
            
            # Exécuter la requête
            result_java_boolean = self._modal_reasoner_instance.query(belief_set_obj, formula_obj)
            self._logger.debug(f" -> Résultat brut Java pour Modal '{formula_str}': {result_java_boolean}")
            
            # Conversion et retour
            if result_java_boolean is None:
                self._logger.warning(f"Requête Modal Tweety pour '{formula_str}' a retourné null (indéterminé?).")
                return None
            else:
                result_python_bool = bool(result_java_boolean)
                self._logger.info(f" -> Résultat requête Modal Python pour '{formula_str}': {result_python_bool}")
                return result_python_bool
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java exécution requête modale '{str(formula_obj)}': {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            raise RuntimeError(f"Erreur Exécution Requête Modal Tweety: {e_java.getMessage()}") from e_java
        
        except Exception as e:
            self._logger.error(f"Erreur Python exécution requête modale '{str(formula_obj)}': {e}", exc_info=True)
            raise RuntimeError(f"Erreur Python Exécution Requête Modal: {e}") from e
        except Exception as e:
            self._logger.error(f"❌ Erreur initialisation composants logique modale: {e}", exc_info=True)
            # Ne pas lever d'exception pour permettre l'initialisation partielle
            self._logger.warning("La logique modale ne sera pas disponible.")