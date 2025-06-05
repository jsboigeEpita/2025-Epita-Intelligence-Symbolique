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
        self._logger.info("TWEETY_BRIDGE: __init__ - Début")
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
        self._ModalReasoner = None # Renommé depuis _AbstractModalReasoner pour cohérence
        self._ModalFormula = None
        
        # Instances des parsers et raisonneurs
        self._pl_parser_instance = None
        self._pl_reasoner_instance = None
        self._fol_parser_instance = None
        self._fol_reasoner_instance = None
        self._modal_parser_instance = None
        self._modal_reasoner_instance = None
        
        # Tenter l'initialisation des composants JVM
        self._logger.info("TWEETY_BRIDGE: __init__ - Avant vérification/initialisation JVM.")
        if not jpype.isJVMStarted():
            self._logger.info("TWEETY_BRIDGE: __init__ - JVM non démarrée. Tentative d'initialisation...")
            # Utiliser le chemin par défaut pour LIBS_DIR tel que défini dans jvm_setup
            jvm_initialized_by_bridge = initialize_jvm(lib_dir_path=str(LIBS_DIR)) # Appel à initialize_jvm
            self._logger.info(f"TWEETY_BRIDGE: __init__ - initialize_jvm appelée, résultat: {jvm_initialized_by_bridge}, isJVMStarted: {jpype.isJVMStarted()}")
            if jvm_initialized_by_bridge and jpype.isJVMStarted():
                self._logger.info("TWEETY_BRIDGE: __init__ - JVM initialisée avec succès par TweetyBridge.")
                self._logger.info("TWEETY_BRIDGE: __init__ - Appel de _initialize_jvm_components après initialisation JVM.")
                self._initialize_jvm_components()
                self._logger.info("TWEETY_BRIDGE: __init__ - Retour de _initialize_jvm_components.")
            else:
                self._logger.error("TWEETY_BRIDGE: __init__ - Échec de l'initialisation de la JVM par TweetyBridge. Les composants Tweety ne seront pas chargés.")
                self._jvm_ok = False
        else:
            self._logger.info("TWEETY_BRIDGE: __init__ - JVM déjà démarrée. Initialisation des composants Tweety...")
            self._logger.info("TWEETY_BRIDGE: __init__ - Appel de _initialize_jvm_components (JVM déjà démarrée).")
            self._initialize_jvm_components()
            self._logger.info("TWEETY_BRIDGE: __init__ - Retour de _initialize_jvm_components (JVM déjà démarrée).")
        self._logger.info(f"TWEETY_BRIDGE: __init__ - Fin. _jvm_ok: {self._jvm_ok}")
    
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
        self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Début.")
        # Vérifier si la JVM est démarrée
        if not jpype.isJVMStarted():
            self._logger.critical("TWEETY_BRIDGE: _initialize_jvm_components - Tentative d'initialisation alors que la JVM n'est PAS démarrée!")
            self._jvm_ok = False
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Fin (JVM non démarrée).")
            return
        
        self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - JVM démarrée. Tentative de chargement des classes Tweety...")
        
        try:
            # Initialiser les composants pour la logique propositionnelle
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Appel de _initialize_pl_components.")
            self._initialize_pl_components()
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Retour de _initialize_pl_components.")
            
            # Initialiser les composants pour la logique du premier ordre
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Appel de _initialize_fol_components.")
            self._initialize_fol_components()
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Retour de _initialize_fol_components.")
            
            # Initialiser les composants pour la logique modale
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Appel de _initialize_modal_components.")
            self._initialize_modal_components()
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - Retour de _initialize_modal_components.")
            
            # Si tout réussit
            self._jvm_ok = True
            self._logger.info("TWEETY_BRIDGE: _initialize_jvm_components - ✅ Classes et instances Java Tweety chargées avec succès.")
        except Exception as e:
            self._logger.critical(f"TWEETY_BRIDGE: _initialize_jvm_components - ❌ Erreur chargement classes/instances Tweety: {e}", exc_info=True)
            self._jvm_ok = False
        self._logger.info(f"TWEETY_BRIDGE: _initialize_jvm_components - Fin. _jvm_ok: {self._jvm_ok}")
    
    def _initialize_pl_components(self) -> None:
        """
        Initialise les composants Java pour la logique propositionnelle.

        Charge les classes `PlParser`, `SatReasoner`, et `PlFormula` de TweetyProject
        et crée des instances du parser et du raisonneur.

        :raises Exception: Si une erreur survient lors du chargement des classes ou
                           de la création des instances.
        """
        self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Début.")
        try:
            # Charger les classes
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Chargement PlParser.")
            self._PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Chargement SatReasoner.")
            self._SatReasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner")
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Chargement PlFormula.")
            self._PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
            
            # Charger les classes SatSolver et Sat4jSolver pour configuration explicite
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Chargement SatSolver et Sat4jSolver pour configuration.")
            _SatSolver_class = jpype.JClass("org.tweetyproject.logics.pl.sat.SatSolver")
            _Sat4jSolver_class = jpype.JClass("org.tweetyproject.logics.pl.sat.Sat4jSolver")
            
            # Créer les instances
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Instanciation PlParser.")
            self._pl_parser_instance = self._PlParser()
            
            # Configurer explicitement Sat4jSolver comme solveur par défaut AVANT d'instancier SatReasoner.
            # Cela garantit que SatReasoner est initialisé avec le solveur par défaut correctement défini.
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Configuration explicite de Sat4jSolver comme solveur SAT par défaut (AVANT instanciation SatReasoner).")
            _SatSolver_class.setDefaultSolver(_Sat4jSolver_class())
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Sat4jSolver configuré comme défaut.")

            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Instanciation SatReasoner (APRÈS configuration solveur défaut).")
            self._pl_reasoner_instance = self._SatReasoner() # SatReasoner utilise le solveur par défaut
            self._logger.info(f"TWEETY_BRIDGE: _initialize_pl_components - Solveur SAT par défaut ACTIF: {_SatSolver_class.getDefaultSolver().getClass().getName()}")
            
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - ✅ Composants PL initialisés et Sat4jSolver configuré.")
        
        except Exception as e:
            self._logger.error(f"TWEETY_BRIDGE: _initialize_pl_components - ❌ Erreur: {e}", exc_info=True)
            raise
        finally:
            self._logger.info("TWEETY_BRIDGE: _initialize_pl_components - Fin.")
    
    def _initialize_fol_components(self) -> None:
        """
        Initialise les composants Java pour la logique du premier ordre (FOL).

        Charge les classes `FolParser`, `FolReasoner`, `SimpleFolReasoner`, et `FolFormula`
        de TweetyProject et crée des instances du parser et du raisonneur FOL.
        En cas d'erreur, un avertissement est loggué et la logique FOL ne sera pas disponible,
        mais l'initialisation des autres logiques peut continuer.
        """
        self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Début.")
        try:
            # Charger les classes
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Chargement FolParser.")
            self._FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Chargement FolReasoner.")
            self._FolReasoner = jpype.JClass("org.tweetyproject.logics.fol.reasoner.FolReasoner") # Pour type hinting
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Chargement SimpleFolReasoner.")
            self._SimpleFolReasoner = jpype.JClass("org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner") # Classe concrète
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Chargement FolFormula.")
            self._FolFormula = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolFormula")
            
            # Créer les instances
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Instanciation FolParser.")
            self._fol_parser_instance = self._FolParser()
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Instanciation SimpleFolReasoner.")
            self._fol_reasoner_instance = self._SimpleFolReasoner() # Utiliser la classe concrète
            
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - ✅ Composants FOL initialisés.")
        
        except Exception as e:
            self._logger.error(f"TWEETY_BRIDGE: _initialize_fol_components - ❌ Erreur: {e}", exc_info=True)
            # Ne pas lever d'exception pour permettre l'initialisation partielle
            self._logger.warning("TWEETY_BRIDGE: _initialize_fol_components - La logique du premier ordre ne sera pas disponible.")
        finally:
            self._logger.info("TWEETY_BRIDGE: _initialize_fol_components - Fin.")
    
    def _initialize_modal_components(self) -> None:
        """
        Initialise les composants Java pour la logique modale (ML).

        Charge les classes `MlParser`, `AbstractMlReasoner`, `SimpleMlReasoner`,
        et `ModalFormula` de TweetyProject et crée des instances du parser et du
        raisonneur modal. En cas d'erreur, un avertissement est loggué et la logique
        modale ne sera pas disponible, mais l'initialisation des autres logiques
        peut continuer.
        """
        self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Début.")
        try:
            # Charger les classes
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Chargement ModalParser.")
            self._ModalParser = jpype.JClass("org.tweetyproject.logics.ml.parser.MlParser") # Nom corrigé
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Chargement AbstractModalReasoner.")
            self._AbstractModalReasoner = jpype.JClass("org.tweetyproject.logics.ml.reasoner.AbstractMlReasoner") # Pour type hinting
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Chargement SimpleModalReasoner.")
            self._SimpleModalReasoner = jpype.JClass("org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner") # Classe concrète
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Chargement ModalFormula.")
            self._ModalFormula = jpype.JClass("org.tweetyproject.logics.ml.syntax.MlFormula")
            
            # Créer les instances
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Instanciation ModalParser.")
            self._modal_parser_instance = self._ModalParser()
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Instanciation SimpleModalReasoner.")
            self._modal_reasoner_instance = self._SimpleModalReasoner() # Utiliser la classe concrète
            
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - ✅ Composants Modaux initialisés.")
        
        except Exception as e:
            self._logger.error(f"TWEETY_BRIDGE: _initialize_modal_components - ❌ Erreur: {e}", exc_info=True)
            # Ne pas lever d'exception pour permettre l'initialisation partielle
            self._logger.warning("TWEETY_BRIDGE: _initialize_modal_components - La logique modale ne sera pas disponible.")
        finally:
            self._logger.info("TWEETY_BRIDGE: _initialize_modal_components - Fin.")

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

        self._logger.debug(f"validate_belief_set (PL): Input: '{belief_set_string[:100]}...'")
        cleaned_formulas_list = self._remove_comments_and_empty_lines(belief_set_string)

        if not cleaned_formulas_list:
            self._logger.info("validate_belief_set (PL): La liste de formules nettoyées est vide.")
            return False, "Ensemble de croyances vide ou ne contenant que des commentaires"

        try:
            # Tenter de parser pour valider la syntaxe de chaque formule.
            # _parse_pl_belief_set lèvera une RuntimeError si une formule est invalide.
            # Il retournera un PlBeliefSet (potentiellement vide si cleaned_formulas_list était vide,
            # mais ce cas est géré au-dessus).
            parsed_bs = self._parse_pl_belief_set(cleaned_formulas_list)
            
            if parsed_bs is None:
                 # Ce cas pourrait arriver si _jvm_ok devient False pendant l'appel à _parse_pl_belief_set,
                 # ou une autre condition inattendue dans _parse_pl_belief_set qui retourne None.
                 self._logger.error("validate_belief_set (PL): _parse_pl_belief_set a retourné None pour une liste non vide de formules.")
                 return False, "Erreur interne lors du parsing du Belief Set"

            # Si _parse_pl_belief_set a réussi (n'a pas levé d'exception et a retourné un objet PlBeliefSet),
            # et que cleaned_formulas_list n'était pas vide (vérifié au début),
            # alors l'ensemble est considéré syntaxiquement valide.
            # La taille de parsed_bs sera > 0 car cleaned_formulas_list n'était pas vide et le parsing a réussi.
            self._logger.info(f"validate_belief_set (PL): Ensemble de croyances valide, {parsed_bs.size()} formules parsées.")
            return True, "Ensemble de croyances valide"

        except RuntimeError as e_runtime:
            # Erreur de parsing d'une formule individuelle attrapée depuis _parse_pl_belief_set (via _parse_pl_formula)
            self._logger.warning(f"validate_belief_set (PL): Erreur de syntaxe détectée lors du parsing d'une formule: {str(e_runtime)}")
            # Le message de e_runtime est déjà formaté par _parse_pl_formula ou _parse_pl_belief_set
            return False, f"Erreur de syntaxe: {str(e_runtime)}"
        except jpype.JException as e_java:
            # Autres erreurs Java potentielles non attrapées par RuntimeError (ex: de .add() dans _parse_pl_belief_set si cela arrivait)
            self._logger.error(f"validate_belief_set (PL): Erreur Java inattendue lors de la validation: {e_java.getMessage()}", exc_info=True)
            return False, f"Erreur de syntaxe Java: {e_java.getMessage()}"
        except Exception as e_generic: # Autres exceptions Python
            self._logger.error(f"validate_belief_set (PL): Erreur générique inattendue lors de la validation: {str(e_generic)}", exc_info=True)
            return False, f"Erreur inattendue: {str(e_generic)}"
    
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
        self._logger.info(f"Appel execute_pl_query: Query='{query_string}' sur BS (brut): ('{belief_set_content[:60]}...')")
        
        if not self._jvm_ok:
            self._logger.error("execute_pl_query: JVM non prête.")
            return "FUNC_ERROR: JVM non prête ou composants Tweety non chargés."
        
        try:
            # Nettoyer et préparer la liste des formules de la base de croyances
            cleaned_formulas_list = self._remove_comments_and_empty_lines(belief_set_content)
            self._logger.debug(f"execute_pl_query: Liste de formules nettoyées (pour _parse_pl_belief_set): {cleaned_formulas_list}")
            
            # Note: Si cleaned_formulas_list est vide, _parse_pl_belief_set retournera un PlBeliefSet vide.
            # Ce comportement est conservé pour l'instant.
            if not cleaned_formulas_list:
                self._logger.warning("execute_pl_query: La liste de formules nettoyées est vide, un PlBeliefSet vide sera utilisé pour la requête.")

            # Parser l'ensemble de croyances
            belief_set_obj = self._parse_pl_belief_set(cleaned_formulas_list)
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
    
    def _parse_pl_belief_set(self, formula_list: List[str]) -> Optional[Any]:
        """
        Construit un objet PlBeliefSet Tweety à partir d'une liste de chaînes de formules.

        Chaque formule de la liste est parsée individuellement.

        :param formula_list: Liste des chaînes de formules à parser et ajouter.
        :type formula_list: List[str]
        :return: Un objet `PlBeliefSet` de TweetyProject.
                 Retourne un `PlBeliefSet` vide si la liste est vide.
                 Retourne `None` si la JVM ou le parser ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient pour une formule individuelle.
        """
        if not self._jvm_ok or not self._pl_parser_instance:
            self._logger.error(f"Parse PL BS from list: JVM/Parser non prêt. Liste: {formula_list[:5]}...")
            return None

        _PlBeliefSet_class = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlBeliefSet")
        java_belief_set = _PlBeliefSet_class()

        if not formula_list:
            self._logger.info("_parse_pl_belief_set: Reçu une liste de formules vide. Retourne un PlBeliefSet vide.")
            return java_belief_set

        self._logger.info(f"_parse_pl_belief_set: Construction manuelle du PlBeliefSet à partir de {len(formula_list)} formules.")
        for idx, formula_str in enumerate(formula_list):
            if not formula_str.strip(): # Ignorer les chaînes vides si présentes après nettoyage
                self._logger.debug(f"  Formule {idx} ignorée (vide).")
                continue
            try:
                # _parse_pl_formula gère déjà le logging d'erreur et lève RuntimeError
                formula_obj = self._parse_pl_formula(formula_str)
                if formula_obj:
                    java_belief_set.add(formula_obj)
                    self._logger.debug(f"  Formule {idx} ('{formula_str}') ajoutée. Nouvelle taille BS: {java_belief_set.size()}")
                else:
                    # Ce cas ne devrait pas arriver si _parse_pl_formula lève une exception en cas d'échec
                    self._logger.error(f"  _parse_pl_formula a retourné None pour '{formula_str}' sans lever d'exception. C'est inattendu.")
                    # Lever une exception pour signaler l'échec global du parsing du BS
                    raise RuntimeError(f"Échec inattendu du parsing de la formule individuelle '{formula_str}' (retour None)")
            except RuntimeError as e_formula_parse: # Attraper l'erreur de _parse_pl_formula
                self._logger.error(f"Erreur lors du parsing/ajout de la formule '{formula_str}' (index {idx}) au PlBeliefSet: {e_formula_parse}")
                raise RuntimeError(f"Erreur lors de la construction du Belief Set: {e_formula_parse}") from e_formula_parse
            except Exception as e_generic: # Attraper d'autres erreurs potentielles (ex: jpype.JException de .add)
                 self._logger.error(f"Erreur générique lors de l'ajout de la formule '{formula_str}' au PlBeliefSet: {e_generic}", exc_info=True)
                 raise RuntimeError(f"Erreur générique lors de la construction du Belief Set avec '{formula_str}': {e_generic}") from e_generic
        
        self._logger.info(f" -> BS PL construit manuellement (type: {java_belief_set.getClass().getName()}, size: {java_belief_set.size()}, repr: '{str(java_belief_set)[:100]}...')")
        return java_belief_set
    
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
            
            # Log ajouté pour inspecter les objets avant la requête
            self._logger.info(f"Querying PL with belief_set_obj: {str(belief_set_obj)} (Java class: {belief_set_obj.getClass().getName()}), formula_obj: {str(formula_obj)} (Java class: {formula_obj.getClass().getName()})") # DEBUG -> INFO
            
            # Inspecter le contenu détaillé du PlBeliefSet
            if belief_set_obj is not None:
                self._logger.info(f"TWEETY_BRIDGE: _execute_pl_query_internal - Contenu détaillé du PlBeliefSet (size {belief_set_obj.size()}):")
                try:
                    iterator = belief_set_obj.iterator()
                    idx = 0
                    while iterator.hasNext():
                        formula_in_set = iterator.next()
                        self._logger.info(f"  Formula {idx}: '{str(formula_in_set)}' (Class: {formula_in_set.getClass().getName()})")
                        idx += 1
                except Exception as e_iter:
                    self._logger.error(f"TWEETY_BRIDGE: _execute_pl_query_internal - Erreur lors de l'itération sur PlBeliefSet: {e_iter}")

            # Exécuter la requête
            result_java_boolean = self._pl_reasoner_instance.query(belief_set_obj, formula_obj)
            self._logger.info(f" -> Résultat brut Java pour '{formula_str}': {result_java_boolean}") # DEBUG -> INFO
            
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
            # Nettoyer la chaîne d'entrée en utilisant la méthode dédiée
            # Pour FOL, parseBeliefBase attend une chaîne unique, donc joindre la liste.
            cleaned_formulas_list = self._remove_comments_and_empty_lines(belief_set_string)
            belief_set_string_cleaned_for_fol = "\n".join(cleaned_formulas_list)

            self._logger.debug(f"validate_fol_belief_set: Original input string: '{belief_set_string[:60]}...'")
            self._logger.debug(f"validate_fol_belief_set: Cleaned string for FOL parsing: '{belief_set_string_cleaned_for_fol[:100]}...' (length: {len(belief_set_string_cleaned_for_fol)})")

            if not belief_set_string_cleaned_for_fol.strip(): # Vérifier si la chaîne jointe est vide après nettoyage
                 self._logger.info("validate_fol_belief_set: La chaîne de formules nettoyée et jointe est vide.")
                 return False, "Ensemble de croyances FOL vide ou ne contenant que des commentaires"

            # Essayer de parser avec Tweety
            parsed_bs = self._fol_parser_instance.parseBeliefBase(belief_set_string_cleaned_for_fol)
            current_size = parsed_bs.size() # Store size in local variable
            self._logger.debug(f"validate_fol_belief_set: Parsed belief set (Java object reference): {parsed_bs}")
            self._logger.debug(f"validate_fol_belief_set: String representation of parsed_bs: '{str(parsed_bs)[:100]}'")
            self._logger.debug(f"validate_fol_belief_set: Value of current_size (from parsed_bs.size()): {current_size} (type: {type(current_size)})")

            # Si parseBeliefBase réussit mais que la liste originale nettoyée était vide,
            # cela a déjà été géré. Si la liste n'était pas vide mais que current_size est 0,
            # cela signifie que le parsing a réussi mais n'a produit aucune formule (cas étrange mais possible).
            if current_size == 0 and cleaned_formulas_list: # Vérifier cleaned_formulas_list pour être sûr
                self._logger.warning(f"validate_fol_belief_set: parsed_bs.size() est 0 bien que cleaned_formulas_list ne soit pas vide. Considéré comme vide.")
                return False, "Ensemble de croyances FOL vide ou ne contenant que des commentaires"
            
            # Si current_size > 0, c'est valide.
            self._logger.debug(f"validate_fol_belief_set: Ensemble de croyances FOL valide, {current_size} formules.")
            return True, "Ensemble de croyances FOL valide"
        
        except jpype.JException as e_java:
            error_msg = f"Erreur de syntaxe FOL: {e_java.getMessage()}"
            
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_msg += f" (Probablement près de la ligne {line_info})"
                except Exception:
                    pass 
            
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
        self._logger.info(f"Appel execute_fol_query: Query='{query_string}' sur BS (brut): ('{belief_set_content[:60]}...')")
        
        if not self._jvm_ok or not self._fol_parser_instance or not self._fol_reasoner_instance:
            self._logger.error("execute_fol_query: JVM ou composants FOL non prêts.")
            return "FUNC_ERROR: JVM non prête ou composants FOL non chargés."
        
        try:
            # Nettoyer et préparer la chaîne de la base de croyances FOL
            cleaned_formulas_list = self._remove_comments_and_empty_lines(belief_set_content)
            belief_set_string_cleaned_for_fol = "\n".join(cleaned_formulas_list)
            self._logger.debug(f"execute_fol_query: Contenu BS FOL nettoyé (pour _parse_fol_belief_set): '{belief_set_string_cleaned_for_fol[:100]}...'")

            if not belief_set_string_cleaned_for_fol.strip():
                 self._logger.warning("execute_fol_query: La chaîne de formules nettoyée et jointe est vide, un FolBeliefSet vide sera utilisé.")
            
            # Parser l'ensemble de croyances
            belief_set_obj = self._parse_fol_belief_set(belief_set_string_cleaned_for_fol)
            if belief_set_obj is None: # Peut arriver si JVM/parser non prêt, ou erreur interne dans _parse_fol_belief_set
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
    
    def _parse_fol_belief_set(self, belief_set_string_cleaned: str) -> Optional[Any]:
        """
        Parse une chaîne de caractères (préalablement nettoyée) en un objet ensemble de croyances FOL (BeliefBase) Tweety.

        :param belief_set_string_cleaned: La chaîne représentant l'ensemble de croyances FOL,
                                          déjà traitée par _remove_comments_and_empty_lines et jointe.
        :type belief_set_string_cleaned: str
        :return: Un objet `FolBeliefSet` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser FOL ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
        """
        if not self._jvm_ok or not self._fol_parser_instance:
            self._logger.error(f"Parse FOL BS: JVM/Parser non prêt (BS nettoyé: '{belief_set_string_cleaned[:60]}...').")
            return None
        
        try:
            self._logger.debug(f"Parsing FOL belief set (reçu, déjà nettoyé et joint): '{belief_set_string_cleaned[:100]}...'. Longueur: {len(belief_set_string_cleaned)}")
            
            if not belief_set_string_cleaned.strip(): # Si la chaîne est vide après nettoyage et jointure
                self._logger.info("_parse_fol_belief_set: Chaîne vide fournie, retourne un FolBeliefSet vide.")
                _FolBeliefSet_class = jpype.JClass("org.tweetyproject.logics.fol.syntax.FolBeliefSet")
                return _FolBeliefSet_class()

            parsed_bs = self._fol_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            self._logger.debug(f" -> BS FOL parsé (type: {type(parsed_bs)}, size: {parsed_bs.size()}, repr: '{str(parsed_bs)[:100]}...')")
            
            return parsed_bs
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing BS FOL (extrait nettoyé: '{belief_set_string_cleaned[:60]}...'): {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_context = f" (Probablement près de la ligne {line_info} du belief set)"
                    error_msg += error_context
                except Exception:
                    pass 
            
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
            if not jpype.JObject(formula_obj, self._FolFormula):
                raise TypeError(f"Objet requête n'est pas un FolFormula (type: {type(formula_obj)})")
            
            if belief_set_obj is None:
                raise ValueError("Objet Belief Set FOL est None.")
            
            formula_str = str(formula_obj)
            self._logger.debug(f"Exécution requête FOL '{formula_str}' avec raisonneur '{self._fol_reasoner_instance.getClass().getName()}'...")
            
            result_java_boolean = self._fol_reasoner_instance.query(belief_set_obj, formula_obj)
            self._logger.debug(f" -> Résultat brut Java pour FOL '{formula_str}': {result_java_boolean}")
            
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
            # Nettoyer la chaîne d'entrée en utilisant la méthode dédiée
            # Pour Modal, parseBeliefBase attend une chaîne unique, donc joindre la liste.
            cleaned_formulas_list = self._remove_comments_and_empty_lines(belief_set_string)
            belief_set_string_cleaned_for_modal = "\n".join(cleaned_formulas_list)

            self._logger.debug(f"validate_modal_belief_set: Original input string: '{belief_set_string[:60]}...'")
            self._logger.debug(f"validate_modal_belief_set: Cleaned string for Modal parsing: '{belief_set_string_cleaned_for_modal[:100]}...' (length: {len(belief_set_string_cleaned_for_modal)})")

            if not belief_set_string_cleaned_for_modal.strip():
                 self._logger.info("validate_modal_belief_set: La chaîne de formules nettoyée et jointe est vide.")
                 return False, "Ensemble de croyances modal vide ou ne contenant que des commentaires"
            
            # Essayer de parser avec Tweety
            parsed_bs = self._modal_parser_instance.parseBeliefBase(belief_set_string_cleaned_for_modal)
            current_size = parsed_bs.size() 
            self._logger.debug(f"validate_modal_belief_set: Parsed belief set (Java object reference): {parsed_bs}")
            self._logger.debug(f"validate_modal_belief_set: String representation of parsed_bs: '{str(parsed_bs)[:100]}'")
            self._logger.debug(f"validate_modal_belief_set: Value of current_size (from parsed_bs.size()): {current_size} (type: {type(current_size)})")

            if current_size == 0 and cleaned_formulas_list:
                self._logger.warning(f"validate_modal_belief_set: parsed_bs.size() est 0 bien que cleaned_formulas_list ne soit pas vide. Considéré comme vide.")
                return False, "Ensemble de croyances modal vide ou ne contenant que des commentaires"
            
            self._logger.debug(f"validate_modal_belief_set: Ensemble de croyances modal valide, {current_size} formules.")
            return True, "Ensemble de croyances modal valide"
        
        except jpype.JException as e_java:
            error_msg = f"Erreur de syntaxe modale: {e_java.getMessage()}"
            
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_msg += f" (Probablement près de la ligne {line_info})"
                except Exception:
                    pass 
            
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
        self._logger.info(f"Appel execute_modal_query: Query='{query_string}' sur BS (brut): ('{belief_set_content[:60]}...')")
        
        if not self._jvm_ok or not self._modal_parser_instance or not self._modal_reasoner_instance:
            self._logger.error("execute_modal_query: JVM ou composants Modal non prêts.")
            return "FUNC_ERROR: JVM non prête ou composants Modal non chargés."
        
        try:
            # Nettoyer et préparer la chaîne de la base de croyances modale
            cleaned_formulas_list = self._remove_comments_and_empty_lines(belief_set_content)
            belief_set_string_cleaned_for_modal = "\n".join(cleaned_formulas_list)
            self._logger.debug(f"execute_modal_query: Contenu BS Modal nettoyé (pour _parse_modal_belief_set): '{belief_set_string_cleaned_for_modal[:100]}...'")

            if not belief_set_string_cleaned_for_modal.strip():
                self._logger.warning("execute_modal_query: La chaîne de formules nettoyée et jointe est vide, un ModalBeliefSet vide sera utilisé.")

            # Parser l'ensemble de croyances
            belief_set_obj = self._parse_modal_belief_set(belief_set_string_cleaned_for_modal)
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
    
    def _parse_modal_belief_set(self, belief_set_string_cleaned: str) -> Optional[Any]:
        """
        Parse une chaîne de caractères (préalablement nettoyée) en un objet ensemble de croyances modales (BeliefBase) Tweety.

        :param belief_set_string_cleaned: La chaîne représentant l'ensemble de croyances modales,
                                          déjà traitée par _remove_comments_and_empty_lines et jointe.
        :type belief_set_string_cleaned: str
        :return: Un objet `ModalBeliefSet` de TweetyProject si le parsing réussit,
                 `None` si la JVM ou le parser modal ne sont pas prêts.
        :rtype: Optional[Any]
        :raises RuntimeError: Si une erreur de parsing Java ou Python survient.
        """
        if not self._jvm_ok or not self._modal_parser_instance:
            self._logger.error(f"Parse Modal BS: JVM/Parser non prêt (BS nettoyé: '{belief_set_string_cleaned[:60]}...').")
            return None
        
        try:
            self._logger.debug(f"Parsing Modal belief set (reçu, déjà nettoyé et joint): '{belief_set_string_cleaned[:100]}...'. Longueur: {len(belief_set_string_cleaned)}")
            
            if not belief_set_string_cleaned.strip():
                self._logger.info("_parse_modal_belief_set: Chaîne vide fournie, retourne un ModalBeliefSet vide.")
                _ModalBeliefSet_class = jpype.JClass("org.tweetyproject.logics.ml.syntax.ModalBeliefSet")
                return _ModalBeliefSet_class()
                
            parsed_bs = self._modal_parser_instance.parseBeliefBase(belief_set_string_cleaned)
            
            self._logger.debug(f" -> BS Modal parsé (type: {type(parsed_bs)}, size: {parsed_bs.size()}, repr: '{str(parsed_bs)[:100]}...')")
            
            return parsed_bs
        
        except jpype.JException as e_java:
            error_msg = f"Erreur Java parsing BS Modal (extrait nettoyé: '{belief_set_string_cleaned[:60]}...'): {e_java.getClass().getName()}: {e_java.getMessage()}"
            self._logger.error(error_msg)
            
            java_error_message = e_java.getMessage()
            if java_error_message and 'line ' in java_error_message:
                try:
                    line_info = java_error_message.split('line ')[1].split(',')[0]
                    error_context = f" (Probablement près de la ligne {line_info} du belief set)"
                    error_msg += error_context
                except Exception:
                    pass 
            
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
            if not jpype.JObject(formula_obj, self._ModalFormula):
                raise TypeError(f"Objet requête n'est pas un ModalFormula (type: {type(formula_obj)})")
            
            if belief_set_obj is None:
                raise ValueError("Objet Belief Set Modal est None.")
            
            formula_str = str(formula_obj)
            self._logger.debug(f"Exécution requête modale '{formula_str}' avec raisonneur '{self._modal_reasoner_instance.getClass().getName()}'...")
            
            result_java_boolean = self._modal_reasoner_instance.query(belief_set_obj, formula_obj)
            self._logger.debug(f" -> Résultat brut Java pour Modal '{formula_str}': {result_java_boolean}")
            
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
# Fin des méthodes de la classe TweetyBridge