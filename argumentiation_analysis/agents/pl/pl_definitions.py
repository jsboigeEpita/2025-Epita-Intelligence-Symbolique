# agents/pl/pl_definitions.py
import logging
import jpype # Garder l'import pour isinstance et JException
from typing import List, Optional, Any, Dict
import time
from semantic_kernel.functions import kernel_function
import semantic_kernel as sk

# Importer les prompts
from .prompts import prompt_text_to_pl_v8, prompt_gen_pl_queries_v8, prompt_interpret_pl_v8

# Loggers
logger = logging.getLogger("Orchestration.AgentPL.Defs")
plugin_logger = logging.getLogger("Orchestration.PLAnalyzerPlugin")
setup_logger = logging.getLogger("Orchestration.AgentPL.Setup")

# --- Configuration Logger Plugin ---
if not plugin_logger.handlers and not plugin_logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); plugin_logger.addHandler(handler); plugin_logger.setLevel(logging.INFO)

# --- Plugin Spécifique PLAnalyzer (V10.1 - Sans dépendance globale jvm_ready) ---
class PropositionalLogicPlugin:
    """
    Plugin SK pour l'analyse en logique propositionnelle via Tweety/JPype.
    Contient la logique d'interaction Java et expose une fonction native au kernel.
    """
    _logger: logging.Logger
    _jvm_ok: bool # Indique si l'initialisation des composants Java a réussi
    _PlParser: Optional[Any] = None
    _SatReasoner: Optional[Any] = None
    _PlFormula: Optional[Any] = None
    _parser_instance: Optional[Any] = None
    _reasoner_instance: Optional[Any] = None

    def __init__(self):
        self._logger = plugin_logger
        self._jvm_ok = False # Initialisé à False
        self._logger.info("Instance PropositionalLogicPlugin créée. Tentative init composants JVM...")
        self._initialize_jvm_components() # Tente l'initialisation

    def _initialize_jvm_components(self):
        """Tente de charger les classes/instances Tweety si JVM démarrée."""
        # Ne dépend plus de `jvm_ready` global ici
        if not jpype.isJVMStarted():
            self._logger.critical("Tentative d'init Plugin PL alors que la JVM n'est PAS démarrée ! Fonctions natives échoueront.")
            self._jvm_ok = False
            return

        # La JVM est démarrée, on essaie de charger les classes
        self._logger.info("JVM démarrée. Tentative de chargement des classes Tweety...")
        try:
            # Tenter de charger les classes
            self._PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
            self._SatReasoner = jpype.JClass("org.tweetyproject.logics.pl.reasoner.SatReasoner")
            self._PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")
            # Tenter de créer les instances
            self._parser_instance = self._PlParser()
            self._reasoner_instance = self._SatReasoner()
            # Si tout réussit :
            self._jvm_ok = True
            self._logger.info("✅ Classes et instances Java Tweety chargées avec succès.")
        except Exception as e:
            self._logger.critical(f"❌ Erreur chargement classes/instances Tweety (JVM démarrée): {e}", exc_info=True)
            self._jvm_ok = False # Échec de l'initialisation

    def _internal_parse_formula(self, formula_string: str) -> Optional[Any]:
         if not self._jvm_ok or not self._parser_instance:
             self._logger.error(f"Parse formula: JVM/Parser non prêt ('{formula_string[:60]}...').")
             return None
         try:
             self._logger.debug(f"Parsing formule: '{formula_string}'")
             return self._parser_instance.parseFormula(formula_string)
         except jpype.JException as e_java:
             error_msg = f"Erreur Java parsing formule '{formula_string}': {e_java.getClass().getName()}: {e_java.getMessage()}"
             self._logger.error(error_msg)
             raise RuntimeError(f"Erreur Parsing Formule: {e_java.getMessage()}") from e_java
         except Exception as e:
             self._logger.error(f"Erreur Python parsing formule '{formula_string}': {e}", exc_info=True)
             raise RuntimeError(f"Erreur Python Parsing Formule: {e}") from e

    def _internal_parse_belief_set(self, belief_set_string: str) -> Optional[Any]:
         if not self._jvm_ok or not self._parser_instance:
             self._logger.error(f"Parse BS: JVM/Parser non prêt (BS: '{belief_set_string[:60]}...').")
             return None
         try:
             belief_set_string_cleaned = belief_set_string.replace("\\\\n", "\\n") # Correction double backslash
             self._logger.debug(f"Parsing belief set (nettoyé): '{belief_set_string_cleaned[:100]}...'. Longueur: {len(belief_set_string_cleaned)}")
             parsed_bs = self._parser_instance.parseBeliefBase(belief_set_string_cleaned)
             # Utiliser str() pour obtenir une représentation et vérifier si elle est vide ou contient juste des commentaires
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
             if hasattr(e_java, 'message') and 'line ' in e_java.message():
                 try:
                     line_info = e_java.message().split('line ')[1].split(',')[0]
                     error_context = f" (Probablement près de la ligne {line_info} du belief set)"
                     error_msg += error_context
                 except Exception: pass # Ne pas planter si l'extraction échoue
             raise RuntimeError(f"Erreur Parsing Belief Set: {e_java.getMessage()}") from e_java
         except Exception as e:
             self._logger.error(f"Erreur Python parsing BS: {e}", exc_info=True)
             raise RuntimeError(f"Erreur Python Parsing Belief Set: {e}") from e

    def _internal_execute_query(self, belief_set_obj: Any, formula_obj: Any) -> Optional[bool]:
        if not self._jvm_ok or not self._reasoner_instance or not self._PlFormula:
            self._logger.error("Execute query: JVM/Reasoner/Formula non prêt.")
            return None
        try:
            # Vérifier si formula_obj est bien une instance de PlFormula chargée
            if not jpype.JObject(formula_obj, self._PlFormula):
                 raise TypeError(f"Objet requête n'est pas un PlFormula (type: {type(formula_obj)})")

            # Vérifier si belief_set_obj est valide (au moins qu'il n'est pas None)
            if belief_set_obj is None:
                raise ValueError("Objet Belief Set est None.")

            formula_str = str(formula_obj) # Pour logging
            self._logger.debug(f"Exécution requête '{formula_str}' avec raisonneur '{self._reasoner_instance.getClass().getName()}'...")

            # Exécuter la requête
            result_java_boolean = self._reasoner_instance.query(belief_set_obj, formula_obj)
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


    @kernel_function(
        description="Exécute une requête en Logique Propositionnelle (syntaxe Tweety: !,||,=>,<=>,^^) sur un Belief Set fourni. Retourne le résultat (ACCEPTED, REJECTED, Unknown, ou FUNC_ERROR).",
        name="execute_pl_query"
    )
    def execute_pl_query(self, belief_set_content: str, query_string: str) -> str:
        # ... (Code execute_pl_query inchangé) ...
        self._logger.info(f"Appel execute_pl_query: Query='{query_string}' sur BS ('{belief_set_content[:60]}...')")
        if not self._jvm_ok:
            self._logger.error("execute_pl_query: JVM non prête.")
            return "FUNC_ERROR: JVM non prête ou composants Tweety non chargés."
        try:
            belief_set_obj = self._internal_parse_belief_set(belief_set_content)
            if belief_set_obj is None: return "FUNC_ERROR: Échec parsing Belief Set. Vérifiez syntaxe."
            formula_obj = self._internal_parse_formula(query_string)
            if formula_obj is None: return f"FUNC_ERROR: Échec parsing requête '{query_string}'. Vérifiez syntaxe."
            result_bool: Optional[bool] = self._internal_execute_query(belief_set_obj, formula_obj)
            if result_bool is None:
                result_str = f"Tweety Result: Unknown for query '{query_string}'."
                self._logger.warning(f"Requête '{query_string}' -> indéterminé (None).")
            else:
                result_label = "ACCEPTED (True)" if result_bool else "REJECTED (False)"
                result_str = f"Tweety Result: Query '{query_string}' is {result_label}."
                self._logger.info(f" -> Résultat formaté requête '{query_string}': {result_label}")
            return result_str
        except RuntimeError as e_runtime:
             self._logger.error(f"Erreur exécution (parsing/query): {e_runtime}")
             return f"FUNC_ERROR: {e_runtime}"
        except Exception as e_py:
            error_msg = f"Erreur Python inattendue dans execute_pl_query: {e_py}"
            self._logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"


logger.info("Classe PropositionalLogicPlugin (V10.1) définie.")


# --- Fonction pour configurer le Kernel spécifique à l'agent PL (V10.1) ---
def setup_pl_kernel(kernel: sk.Kernel, llm_service):
    """
    Configure le kernel pour le PropositionalLogicAgent.
    Ajoute une instance du PropositionalLogicPlugin et les fonctions sémantiques.
    """
    plugin_name = "PLAnalyzer" # Doit être DÉFINI ICI
    logger.info(f"Configuration Kernel pour {plugin_name} (V10.1 - Correction Indentation)...")

    # Vérifier si la JVM est prête AVANT d'instancier/ajouter le plugin
    if not jpype.isJVMStarted():
        setup_logger.error(f"❌ ERREUR: Tentative de setup PL Kernel alors que la JVM n'est PAS démarrée. Plugin {plugin_name} ne sera PAS ajouté.")
        return # Ne pas continuer si la JVM n'est pas prête

    # Instanciation du plugin À L'INTÉRIEUR de la fonction
    pl_plugin_instance = PropositionalLogicPlugin()
    
    # Vérifier si l'initialisation interne du plugin a réussi
    if not pl_plugin_instance._jvm_ok:
         setup_logger.error(f"❌ ERREUR: Échec de l'initialisation des composants Java dans {plugin_name}. Plugin ne sera PAS complètement fonctionnel.")
         # On pourrait choisir de ne pas ajouter le plugin du tout ici,
         # mais on le laisse pour que les fonctions sémantiques soient là.
         # La fonction native retournera FUNC_ERROR car _jvm_ok est False.

    # Ajout du plugin au kernel passé en argument
    if plugin_name in kernel.plugins: logger.warning(f"Plugin '{plugin_name}' déjà présent. Remplacement.")
    kernel.add_plugin(pl_plugin_instance, plugin_name=plugin_name)
    logger.debug(f"Instance du plugin '{plugin_name}' ajoutée/mise à jour.")

    # Configuration des settings LLM
    default_settings = None
    if llm_service:
        try: default_settings = kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id); logger.debug(f"Settings LLM récupérés pour {plugin_name}.")
        except Exception as e: logger.warning(f"Impossible de récupérer settings LLM pour {plugin_name}: {e}")

    # Ajout des fonctions sémantiques au kernel
    semantic_functions = [
        ("semantic_TextToPLBeliefSet", prompt_text_to_pl_v8, "Traduit texte en Belief Set PL (syntaxe Tweety ! || => <=> ^^)."),
        ("semantic_GeneratePLQueries", prompt_gen_pl_queries_v8, "Génère requêtes PL pertinentes (syntaxe Tweety ! || => <=> ^^)."),
        ("semantic_InterpretPLResult", prompt_interpret_pl_v8, "Interprète résultat requête PL Tweety formaté.")
    ]
    for func_name, prompt, description in semantic_functions:
        try:
            kernel.add_function(prompt=prompt, plugin_name=plugin_name, function_name=func_name, description=description, prompt_execution_settings=default_settings)
            logger.debug(f"Fonction sémantique {plugin_name}.{func_name} ajoutée/mise à jour.")
        except ValueError as ve: logger.warning(f"Problème ajout/MàJ {plugin_name}.{func_name}: {ve}")

    # Vérification de la fonction native (façade)
    native_facade = "execute_pl_query"
    if plugin_name in kernel.plugins:
        if native_facade not in kernel.plugins[plugin_name]:
            logger.error(f"ERREUR CRITIQUE: Fonction native {plugin_name}.{native_facade} non enregistrée!")
        else:
            logger.debug(f"Fonction native {plugin_name}.{native_facade} trouvée.")
    else:
        logger.error(f"ERREUR CRITIQUE: Plugin {plugin_name} non trouvé après ajout!")

    logger.info(f"Kernel {plugin_name} configuré (V10.1).")

# --- Instructions Système ---
# (Provenant de la cellule [ID: f7943ca6] du notebook 'Argument_Analysis_Agentic-2-pl_agent.ipynb')
PL_AGENT_INSTRUCTIONS_V10 = """
Votre Rôle: Spécialiste en logique propositionnelle utilisant Tweety. Vous devez générer et interpréter des formules logiques en respectant **STRICTEMENT** la syntaxe Tweety.

**Syntaxe Tweety PlParser Requise (BNF) :**
```bnf
FORMULASET ::== FORMULA ( "\\n" FORMULA )*
FORMULA ::== PROPOSITION | "(" FORMULA ")" | FORMULA ">>" FORMULA |
             FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA |
             FORMULA "^^" FORMULA | "!" FORMULA | "+" | "-"
PROPOSITION is a sequence of characters excluding |,&,!,(),=,<,> and whitespace.
IMPORTANT: N'utilisez PAS l'opérateur >> (cause des erreurs). Utilisez !, ||, =>, <=>, ^^. Formules séparées par \\n dans les Belief Sets. Propositions courtes et sans espaces (ex: renewable_essential).

Fonctions Outils Disponibles:

    StateManager.*: Pour lire/écrire dans l'état (get_current_state_snapshot, add_belief_set, log_query_result, add_answer).
    PLAnalyzer.semantic_TextToPLBeliefSet(input: str): Fonction sémantique pour traduire texte en Belief Set PL.
    PLAnalyzer.semantic_GeneratePLQueries(input: str, belief_set: str): Fonction sémantique pour générer des requêtes PL.
    PLAnalyzer.semantic_InterpretPLResult(input: str, belief_set: str, queries: str, tweety_result: str): Fonction sémantique pour interpréter les résultats.
    PLAnalyzer.execute_pl_query(belief_set_content: str, query_string: str): Fonction native pour exécuter une requête PL via Tweety. Retourne le résultat formaté (ACCEPTED/REJECTED/Unknown/FUNC_ERROR). Nécessite une JVM prête.


Processus OBLIGATOIRE à chaque tour:

    CONSULTER L'ÉTAT: Appelez StateManager.get_current_state_snapshot(summarize=True).
    IDENTIFIER VOTRE TÂCHE: Lisez DERNIER message PM (ID tâche, description). Extrayez task_id.
    EXÉCUTER LA TÂCHE:
        Si Tâche = "Traduire ... en Belief Set PL":
        a.  Récupérer le texte source (arguments/texte brut) depuis l'état ou le message du PM.
        b.  Appelez PLAnalyzer.semantic_TextToPLBeliefSet(input=[Texte source]). Validez mentalement la syntaxe de la sortie (Belief Set string) selon la BNF.
        c.  Si la syntaxe semble OK, appelez StateManager.add_belief_set(logic_type="Propositional", content="[Belief Set string généré]"). Notez bs_id. Si l'appel retourne FUNC_ERROR:, signalez l'erreur.
        d.  Préparez réponse texte indiquant succès et bs_id (ou l'erreur).
        e.  Appelez StateManager.add_answer(task_id="[ID reçu]", author_agent="PropositionalLogicAgent", answer_text="...", source_ids=[bs_id si succès]).
        Si Tâche = "Exécuter ... Requêtes PL" (avec belief_set_id):
        a.  Récupérez le belief_set_content correspondant au belief_set_id depuis l'état (StateManager.get_current_state_snapshot(summarize=False) -> belief_sets). Si impossible (ID non trouvé), signalez erreur via add_answer et stoppez.
        b.  Récupérez le raw_text depuis l'état pour le contexte.
        c.  Appelez PLAnalyzer.semantic_GeneratePLQueries(input=raw_text, belief_set=belief_set_content). Validez mentalement la syntaxe des requêtes générées.
        d.  Initialisez formatted_results_list (pour l'interprétation) et log_ids_list. Pour CHAQUE requête q valide générée:
        i.  Appelez PLAnalyzer.execute_pl_query(belief_set_content=belief_set_content, query_string=q).
        ii. Notez le result_str retourné. Ajoutez-le à formatted_results_list. Si result_str commence par FUNC_ERROR:, loggez l'erreur mais continuez si possible avec les autres requêtes.
        iii.Appelez StateManager.log_query_result(belief_set_id=belief_set_id, query=q, raw_result=result_str). Notez le log_id. Ajoutez log_id à log_ids_list.
        e.  Si AU MOINS UNE requête a été tentée: Concaténez tous les result_str dans aggregated_results_str (séparés par newline \\n). Concaténez les requêtes valides testées dans queries_str.
        f.  Appelez PLAnalyzer.semantic_InterpretPLResult(input=raw_text, belief_set=belief_set_content, queries=queries_str, tweety_result=aggregated_results_str). Notez l'interpretation.
        g.  Préparez réponse texte (l'interpretation). Inclure un avertissement si des erreurs (FUNC_ERROR:) ont été rencontrées pendant l'exécution des requêtes.
        h.  Appelez StateManager.add_answer(task_id="[ID reçu]", author_agent="PropositionalLogicAgent", answer_text=interpretation, source_ids=[belief_set_id] + log_ids_list).
        Si Tâche Inconnue/Erreur Préliminaire: Indiquez-le et appelez StateManager.add_answer(task_id=\\\"[ID reçu]\\\", ...) avec le message d'erreur.


Important: Utilisez TOUJOURS task_id reçu pour add_answer. La syntaxe Tweety est STRICTE. Gérez les FUNC_ERROR: retournés par les outils. Vérifiez que la JVM est prête avant d'appeler execute_pl_query (normalement géré par le plugin, mais soyez conscient).
"""
PL_AGENT_INSTRUCTIONS = PL_AGENT_INSTRUCTIONS_V10
logger.info("Instructions Système PL_AGENT_INSTRUCTIONS (V10) définies.")

# Log de chargement
logging.getLogger(__name__).debug("Module agents.pl.pl_definitions chargé.")