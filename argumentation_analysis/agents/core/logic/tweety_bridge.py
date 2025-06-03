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
from typing import Tuple, Optional, Any, Dict

import jpype
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.paths import LIBS_DIR
from semantic_kernel.functions import kernel_function

# Configuration du logger
logger = logging.getLogger("Orchestration.TweetyBridge")

class TweetyBridge:
    """
    Interface avec TweetyProject via JPype pour différents types de logiques.

    Cette classe encapsule la communication avec TweetyProject, permettant
    l'analyse syntaxique, la validation et le raisonnement sur des bases de
    croyances en logique propositionnelle (PL), logique du premier ordre (FOL),
    et logique modale (ML). Elle gère le démarrage de la JVM et le chargement
    des classes Java nécessaires de TweetyProject.

    Attributes:
        _logger (logging.Logger): Logger pour cette classe.
        _jvm_ok (bool): Indique si la JVM et les composants Tweety sont prêts.
        _PlParser (jpype.JClass): Classe Java pour le parser de logique propositionnelle.
        _SatReasoner (jpype.JClass): Classe Java pour le raisonneur SAT (logique prop.).
        _PlFormula (jpype.JClass): Classe Java pour les formules de logique propositionnelle.
        _FolParser (jpype.JClass): Classe Java pour le parser de logique du premier ordre.
        _FolReasoner (jpype.JClass): Interface Java pour les raisonneurs FOL.
        _SimpleFolReasoner (jpype.JClass): Classe Java pour un raisonneur FOL simple.
        _FolFormula (jpype.JClass): Classe Java pour les formules de logique du premier ordre.
        _ModalParser (jpype.JClass): Classe Java pour le parser de logique modale.
        _AbstractModalReasoner (jpype.JClass): Classe Java abstraite pour les raisonneurs modaux.
        _SimpleModalReasoner (jpype.JClass): Classe Java pour un raisonneur modal simple.
        _ModalFormula (jpype.JClass): Classe Java pour les formules de logique modale.
        _pl_parser_instance (Any): Instance du parser de logique propositionnelle.
        _pl_reasoner_instance (Any): Instance du raisonneur de logique propositionnelle.
        _fol_parser_instance (Any): Instance du parser de logique du premier ordre.
        _fol_reasoner_instance (Any): Instance du raisonneur de logique du premier ordre.
        _modal_parser_instance (Any): Instance du parser de logique modale.
        _modal_reasoner_instance (Any): Instance du raisonneur de logique modale.
    """
    
    def __init__(self):
        """
        Initialise l'interface TweetyBridge.

        Tente de démarrer la JVM si elle n'est pas déjà démarrée et charge
        les classes Java nécessaires de TweetyProject.
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
        if not jpype.isJVMStarted():
            self._logger.info("JVM non démarrée. Tentative d'initialisation depuis TweetyBridge...")
            # Utiliser le chemin par défaut pour LIBS_DIR tel que défini dans jvm_setup
            jvm_initialized_by_bridge = initialize_jvm(lib_dir_path=str(LIBS_DIR))
            if jvm_initialized_by_bridge and jpype.isJVMStarted():
                self._logger.info("JVM initialisée avec succès par TweetyBridge.")
                self._initialize_jvm_components()
            else:
                self._logger.error("Échec de l'initialisation de la JVM par TweetyBridge. Les composants Tweety ne seront pas chargés.")
                self._jvm_ok = False
        else:
            self._logger.info("JVM déjà démarrée. Initialisation des composants Tweety...")
            self._initialize_jvm_components()
    
    def is_jvm_ready(self) -> bool:
        """
        Vérifie si la JVM et les composants Tweety sont prêts à l'emploi.

        :return: True si la JVM est démarrée et les composants Tweety initialisés, False sinon.
        :rtype: bool
        """
        return jpype.isJVMStarted() and self._jvm_ok
    
    def _initialize_jvm_components(self) -> None:
        """
        Initialise les composants JVM nécessaires pour interagir avec TweetyProject.

        Charge les classes Java pour les parsers et raisonneurs des différentes logiques
        supportées (PL, FOL, ML). Met à jour l'attribut `_jvm_ok`.
        Ne fait rien si la JVM n'est pas démarrée.
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
        Initialise les composants Java pour la logique propositionnelle.

        Charge les classes `PlParser`, `SatReasoner`, et `PlFormula` de TweetyProject
        et crée des instances du parser et du raisonneur.

        :raises Exception: Si une erreur survient lors du chargement des classes ou
                           de la création des instances.
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
        Initialise les composants Java pour la logique du premier ordre (FOL).

        Charge les classes `FolParser`, `FolReasoner`, `SimpleFolReasoner`, et `FolFormula`
        de TweetyProject et crée des instances du parser et du raisonneur FOL.
        En cas d'erreur, un avertissement est loggué et la logique FOL ne sera pas disponible,
        mais l'initialisation des autres logiques peut continuer.
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
        Initialise les composants Java pour la logique modale (ML).

        Charge les classes `MlParser`, `AbstractMlReasoner`, `SimpleMlReasoner`,
        et `ModalFormula` de TweetyProject et crée des instances du parser et du
        raisonneur modal. En cas d'erreur, un avertissement est loggué et la logique
        modale ne sera pas disponible, mais l'initialisation des autres logiques
        peut continuer.
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
        Valide la syntaxe d'une formule de logique propositionnelle.

        :param formula_string: La formule à valider.
        :type formula_string: str
        :return: Un tuple contenant un booléen indiquant si la formule est valide
                 et un message descriptif.
        :rtype: Tuple[bool, str]
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
        Valide la syntaxe d'un ensemble de croyances en logique propositionnelle.

        Nettoie les sauts de ligne échappés avant la validation.
        Vérifie également si l'ensemble de croyances est vide ou ne contient que des commentaires.

        :param belief_set_string: L'ensemble de croyances (chaque formule sur une nouvelle ligne).
        :type belief_set_string: str
        :return: Un tuple contenant un booléen indiquant si l'ensemble est valide
                 et un message descriptif, incluant potentiellement la ligne de l'erreur.
        :rtype: Tuple[bool, str]
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
        Exécute une requête en logique propositionnelle sur un ensemble de croyances donné.

        La fonction parse l'ensemble de croyances et la formule de requête, puis
        utilise le raisonneur SAT de TweetyProject pour déterminer si la requête
        est une conséquence logique de l'ensemble de croyances.

        :param belief_set_content: Le contenu de l'ensemble de croyances,
                                   avec les formules séparées par des sauts de ligne.
        :type belief_set_content: str
        :param query_string: La formule de logique propositionnelle à vérifier.
        :type query_string: str
        :return: Une chaîne de caractères formatée indiquant si la requête est
                 "ACCEPTED (True)", "REJECTED (False)", "Unknown", ou un message
                 d'erreur préfixé par "FUNC_ERROR:".
        :rtype: str
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
        Parse une chaîne de caractères en un objet formule de logique propositionnelle Tweety.

        :param formula_string: La chaîne représentant la formule.
        :type formula_string: str
        :return: Un objet `PlFormula` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
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
        Parse une chaîne de caractères en un objet ensemble de croyances (BeliefBase) Tweety.

        Nettoie les sauts de ligne échappés avant le parsing.

        :param belief_set_string: La chaîne représentant l'ensemble de croyances
                                  (formules séparées par des sauts de ligne).
        :type belief_set_string: str
        :return: Un objet `BeliefBase` (ou `PlBeliefSet`) de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
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
        Exécute une requête de logique propositionnelle en utilisant les objets Tweety parsés.

        Utilise le raisonneur SAT pour vérifier si la `formula_obj` est une conséquence
        logique de `belief_set_obj`.

        :param belief_set_obj: L'objet `BeliefBase` Tweety parsé.
        :type belief_set_obj: Any
        :param formula_obj: L'objet `PlFormula` Tweety parsé.
        :type formula_obj: Any
        :return: `True` si la formule est conséquence, `False` sinon, `None` si la JVM
                 n'est pas prête, si le raisonneur retourne `null` (indéterminé),
                 ou en cas d'erreur de type.
        :rtype: Optional[bool]
        :raises TypeError: Si `formula_obj` n'est pas une instance de `PlFormula`.
        :raises ValueError: Si `belief_set_obj` est `None`.
        :raises RuntimeError: Si une erreur d'exécution Java ou Python survient.
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
        Valide la syntaxe d'une formule de logique du premier ordre (FOL).

        :param formula_string: La formule FOL à valider.
        :type formula_string: str
        :return: Un tuple contenant un booléen indiquant si la formule est valide
                 et un message descriptif.
        :rtype: Tuple[bool, str]
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
        Valide la syntaxe d'un ensemble de croyances en logique du premier ordre (FOL).

        Nettoie les sauts de ligne échappés avant la validation.
        Vérifie également si l'ensemble de croyances est vide ou ne contient que des commentaires.

        :param belief_set_string: L'ensemble de croyances FOL (chaque formule sur une nouvelle ligne).
        :type belief_set_string: str
        :return: Un tuple contenant un booléen indiquant si l'ensemble est valide
                 et un message descriptif, incluant potentiellement la ligne de l'erreur.
        :rtype: Tuple[bool, str]
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
        Exécute une requête en logique du premier ordre (FOL) sur un ensemble de croyances.

        Parse l'ensemble de croyances et la formule de requête FOL, puis utilise
        le raisonneur FOL de TweetyProject.

        :param belief_set_content: Le contenu de l'ensemble de croyances FOL.
        :type belief_set_content: str
        :param query_string: La formule FOL à vérifier.
        :type query_string: str
        :return: Une chaîne de caractères formatée indiquant le résultat ou une erreur.
        :rtype: str
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
        Parse une chaîne de caractères en un objet formule de logique du premier ordre (FOL) Tweety.

        :param formula_string: La chaîne représentant la formule FOL.
        :type formula_string: str
        :return: Un objet `FolFormula` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser FOL ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
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
        Parse une chaîne de caractères en un objet ensemble de croyances FOL (BeliefBase) Tweety.

        Nettoie les sauts de ligne échappés avant le parsing.

        :param belief_set_string: La chaîne représentant l'ensemble de croyances FOL.
        :type belief_set_string: str
        :return: Un objet `FolBeliefSet` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser FOL ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
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
        Exécute une requête de logique du premier ordre (FOL) en utilisant les objets Tweety parsés.

        Utilise le raisonneur FOL pour vérifier si la `formula_obj` est une conséquence
        logique de `belief_set_obj`.

        :param belief_set_obj: L'objet `FolBeliefSet` Tweety parsé.
        :type belief_set_obj: Any
        :param formula_obj: L'objet `FolFormula` Tweety parsé.
        :type formula_obj: Any
        :return: `True` si la formule est conséquence, `False` sinon, `None` si la JVM
                 n'est pas prête, si le raisonneur retourne `null`, ou en cas d'erreur.
        :rtype: Optional[bool]
        :raises TypeError: Si `formula_obj` n'est pas une instance de `FolFormula`.
        :raises ValueError: Si `belief_set_obj` est `None`.
        :raises RuntimeError: Si une erreur d'exécution Java ou Python survient.
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
        Valide la syntaxe d'une formule de logique modale (ML).

        :param formula_string: La formule modale à valider.
        :type formula_string: str
        :return: Un tuple contenant un booléen indiquant si la formule est valide
                 et un message descriptif.
        :rtype: Tuple[bool, str]
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
        Valide la syntaxe d'un ensemble de croyances en logique modale (ML).

        Nettoie les sauts de ligne échappés avant la validation.
        Vérifie également si l'ensemble de croyances est vide ou ne contient que des commentaires.

        :param belief_set_string: L'ensemble de croyances modales (chaque formule sur une nouvelle ligne).
        :type belief_set_string: str
        :return: Un tuple contenant un booléen indiquant si l'ensemble est valide
                 et un message descriptif, incluant potentiellement la ligne de l'erreur.
        :rtype: Tuple[bool, str]
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
        Exécute une requête en logique modale (ML) sur un ensemble de croyances.

        Parse l'ensemble de croyances et la formule de requête modale, puis utilise
        le raisonneur modal de TweetyProject.

        :param belief_set_content: Le contenu de l'ensemble de croyances modales.
        :type belief_set_content: str
        :param query_string: La formule modale à vérifier.
        :type query_string: str
        :return: Une chaîne de caractères formatée indiquant le résultat ou une erreur.
        :rtype: str
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
        Parse une chaîne de caractères en un objet formule de logique modale (ML) Tweety.

        :param formula_string: La chaîne représentant la formule modale.
        :type formula_string: str
        :return: Un objet `ModalFormula` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser modal ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
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
        Parse une chaîne de caractères en un objet ensemble de croyances modales (BeliefBase) Tweety.

        Nettoie les sauts de ligne échappés avant le parsing.

        :param belief_set_string: La chaîne représentant l'ensemble de croyances modales.
        :type belief_set_string: str
        :return: Un objet `ModalBeliefSet` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser modal ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
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
        Exécute une requête de logique modale (ML) en utilisant les objets Tweety parsés.

        Utilise le raisonneur modal pour vérifier si la `formula_obj` est une conséquence
        logique de `belief_set_obj`.

        :param belief_set_obj: L'objet `ModalBeliefSet` Tweety parsé.
        :type belief_set_obj: Any
        :param formula_obj: L'objet `ModalFormula` Tweety parsé.
        :type formula_obj: Any
        :return: `True` si la formule est conséquence, `False` sinon, `None` si la JVM
                 n'est pas prête, si le raisonneur retourne `null`, ou en cas d'erreur.
        :rtype: Optional[bool]
        :raises TypeError: Si `formula_obj` n'est pas une instance de `ModalFormula`.
        :raises ValueError: Si `belief_set_obj` est `None`.
        :raises RuntimeError: Si une erreur d'exécution Java ou Python survient.
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