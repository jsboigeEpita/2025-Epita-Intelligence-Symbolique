# agents/informal/informal_definitions.py
import logging
import json
import os
import pathlib
import requests
import time
from typing import Optional, Dict, Any, List
import pandas as pd # S'assurer que pandas est importé
from semantic_kernel.functions import kernel_function
import semantic_kernel as sk

# Importer les prompts
from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1

from argumentiation_analysis.paths import DATA_DIR


# Loggers
logger = logging.getLogger("Orchestration.AgentInformal.Defs")
plugin_logger = logging.getLogger("Orchestration.InformalAnalysisPlugin")
setup_logger = logging.getLogger("Orchestration.AgentInformal.Setup")

# --- Configuration Logger Plugin ---
if not plugin_logger.handlers and not plugin_logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); plugin_logger.addHandler(handler); plugin_logger.setLevel(logging.INFO)

# --- Constantes pour le CSV ---
FALLACY_CSV_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
# Utiliser un chemin relatif au fichier courant pour data/
DATA_DIR = pathlib.Path(__file__).parent.parent.parent / DATA_DIR # Remonte de informal/ et agents/ pour trouver data/
FALLACY_CSV_LOCAL_PATH = DATA_DIR / "argumentum_fallacies_taxonomy.csv"
ROOT_PK = 0

# --- Plugin Spécifique InformalAnalyzer (Refactorisé V12) ---
class InformalAnalysisPlugin:
    """
    Plugin SK pour l'identification d'arguments et l'exploration de la taxonomie des sophismes via CSV/Pandas.
    Utilise un caching simple pour le DataFrame.
    """
    _logger: logging.Logger
    _dataframe: Optional[pd.DataFrame]
    _taxonomy_load_attempted: bool
    _taxonomy_load_success: bool
    _last_load_time: float
    _cache_ttl_seconds: int

    def __init__(self):
        self._logger = plugin_logger
        self._dataframe = None
        self._taxonomy_load_attempted = False
        self._taxonomy_load_success = False
        self._last_load_time = 0
        self._cache_ttl_seconds = 3600 # Recharger toutes les heures max
        self._logger.info("Instance InformalAnalysisPlugin créée.")

    # --- Méthodes Internes ---
    def _internal_download_data(self, url: str, local_path: pathlib.Path) -> bool:
        # ... (Code _internal_download_data inchangé) ...
        if local_path.exists():
            self._logger.info(f"Fichier local trouvé: {local_path}")
            return True
        self._logger.info(f"Tentative de téléchargement de {url} vers {local_path}...")
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            headers = {'User-Agent': 'SemanticKernel-Python-Agent'}
            response = requests.get(url, timeout=60, headers=headers, allow_redirects=True, stream=True)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self._logger.info(f" -> Téléchargement de {local_path.name} terminé avec succès.")
            return True
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Erreur réseau/HTTP lors du téléchargement de {url}: {e}")
            return False
        except IOError as e:
            self._logger.error(f"Erreur d'écriture du fichier local {local_path}: {e}")
            return False
        except Exception as e:
            self._logger.error(f"Erreur inattendue pendant le téléchargement: {e}", exc_info=True)
            return False

    def _internal_load_and_prepare_dataframe(self) -> Optional[pd.DataFrame]:
         # ... (Code _internal_load_and_prepare_dataframe inchangé) ...
        if not self._internal_download_data(FALLACY_CSV_URL, FALLACY_CSV_LOCAL_PATH):
            return None
        try:
            self._logger.info(f"Lecture et préparation du DataFrame depuis: {FALLACY_CSV_LOCAL_PATH}...")
            df = pd.read_csv(FALLACY_CSV_LOCAL_PATH, encoding='utf-8')
            self._logger.debug(f"Colonnes brutes lues: {list(df.columns)}")
            if 'PK' not in df.columns:
                self._logger.error("Colonne 'PK' manquante.")
                return None
            df['PK'] = pd.to_numeric(df['PK'], errors='coerce')
            df.dropna(subset=['PK'], inplace=True)
            df['PK'] = df['PK'].astype(int)
            df.set_index('PK', inplace=True, verify_integrity=True)
            self._logger.debug(f"Index 'PK' défini. Lignes: {len(df)}")
            numeric_cols = ['depth']
            for col in numeric_cols:
                 if col in df.columns:
                     df[col] = pd.to_numeric(df[col], errors='coerce')
                     self._logger.debug(f"Colonne '{col}' convertie en numérique.")
            if df.empty:
                self._logger.warning("DataFrame vide après préparation.")
                return None
            df = df.where(pd.notnull(df), None) # Remplace NaN par None
            self._logger.info(f" -> DataFrame chargé et préparé ({len(df)} lignes).")
            return df
        except ValueError as ve:
            self._logger.error(f"Erreur préparation DataFrame (PKs dupliqués?): {ve}", exc_info=True)
            return None
        except Exception as e:
            self._logger.error(f"Erreur inattendue chargement/préparation DataFrame: {e}", exc_info=True)
            return None

    def _get_taxonomy_dataframe(self) -> Optional[pd.DataFrame]:
        # ... (Code _get_taxonomy_dataframe inchangé) ...
        current_time = time.time()
        if self._dataframe is not None and self._taxonomy_load_success and \
           (current_time - self._last_load_time) < self._cache_ttl_seconds:
            self._logger.debug("DataFrame taxonomie depuis cache.")
            return self._dataframe
        if not self._taxonomy_load_attempted or not self._taxonomy_load_success or \
           (current_time - self._last_load_time) >= self._cache_ttl_seconds:
            self._logger.info("Rechargement/Tentative chargement taxonomie CSV...")
            self._taxonomy_load_attempted = True
            self._dataframe = self._internal_load_and_prepare_dataframe()
            self._taxonomy_load_success = self._dataframe is not None
            self._last_load_time = current_time
            if not self._taxonomy_load_success:
                 self._logger.error("Échec chargement taxonomie.")
                 self._dataframe = None
            else:
                 self._logger.info("Taxonomie chargée/rechargée.")
        return self._dataframe

    def _internal_get_node_details(self, pk: int, df: pd.DataFrame) -> Dict[str, Any]:
        # ... (Code _internal_get_node_details inchangé) ...
        details = {"pk": pk, "error": None}
        if df is None:
            details["error"] = "DataFrame taxonomie non chargé."
            self._logger.warning(f"_internal_get_node_details: DF non chargé (PK: {pk}).")
            return details
        try:
            row_data = df.loc[pk]
            details.update(row_data.to_dict())
            self._logger.debug(f"Détails trouvés pour PK {pk}.")
        except KeyError:
            details["error"] = f"PK {pk} non trouvé."
            self._logger.warning(details["error"])
        except Exception as e:
            details["error"] = f"Erreur interne récupération détails PK {pk}."
            self._logger.error(f"{details['error']}: {e}", exc_info=True)
        return details

    def _internal_get_children_details(self, parent_pk: int, df: pd.DataFrame, max_children: int) -> List[Dict[str, Any]]:
        # ... (Code _internal_get_children_details inchangé) ...
        children_details = []
        if df is None:
            self._logger.warning(f"_internal_get_children_details: DF non chargé (Parent PK: {parent_pk}).")
            return children_details
        try:
            if 'FK_Parent' not in df.columns:
                 self._logger.error("Colonne 'FK_Parent' manquante.")
                 return children_details
            if parent_pk == ROOT_PK:
                 children_df = df[df['FK_Parent'].isnull() | (df['FK_Parent'] == ROOT_PK)]
            else:
                 children_df = df[df['FK_Parent'] == parent_pk]
            if not children_df.empty:
                children_df = children_df.sort_index().head(max_children)
                self._logger.debug(f"Trouvé {len(children_df)} enfants pour Parent PK {parent_pk} (max {max_children}).")
                for child_pk in children_df.index:
                    children_details.append(self._internal_get_node_details(child_pk, df))
            else:
                 self._logger.debug(f"Aucun enfant trouvé pour Parent PK {parent_pk}.")
        except Exception as e:
             self._logger.error(f"Erreur recherche enfants Parent PK {parent_pk}: {e}", exc_info=True)
        return children_details

    # --- Méthodes Façade (@kernel_function) ---
    @kernel_function(
        description=f"Explore la hiérarchie des sophismes à partir d'un PK donné (ex: {ROOT_PK} pour la racine). Retourne les détails JSON du nœud courant et de ses enfants directs.",
        name="explore_fallacy_hierarchy"
    )
    def explore_fallacy_hierarchy( self, current_pk_str: str, max_children: int = 15 ) -> str:
        # ... (Code explore_fallacy_hierarchy inchangé) ...
        self._logger.info(f"Appel explore_fallacy_hierarchy: PK='{current_pk_str}', max_children={max_children}")
        result_error = {"error": "Erreur inattendue."}
        try:
            current_pk = int(current_pk_str)
        except ValueError:
            error_msg = f"Format PK invalide: '{current_pk_str}'. Entier requis."
            self._logger.warning(error_msg)
            return json.dumps({"pk_requested": current_pk_str, "error": error_msg})
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"pk_requested": current_pk, "error": "Taxonomie sophismes non disponible."})
        current_node_details = self._internal_get_node_details(current_pk, df)
        children_details = self._internal_get_children_details(current_pk, df, max_children)
        result = { "current_node": current_node_details, "children": children_details }
        self._logger.info(f" -> Exploration PK {current_pk} terminée. Nœud trouvé: {current_node_details.get('error') is None}. Enfants: {len(children_details)}.")
        try:
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e_json:
            self._logger.error(f"Erreur sérialisation JSON exploration PK {current_pk}: {e_json}")
            result_error["error"] = f"Erreur sérialisation JSON: {e_json}"
            result_error["pk_requested"] = current_pk
            return json.dumps(result_error)

    @kernel_function(
        description="Récupère les détails complets (nom, description, exemple, etc.) d'un sophisme spécifique via son PK numérique depuis la taxonomie CSV.",
        name="get_fallacy_details"
    )
    def get_fallacy_details(self, fallacy_pk_str: str) -> str:
        # ... (Code get_fallacy_details inchangé) ...
        self._logger.info(f"Appel get_fallacy_details: PK='{fallacy_pk_str}'")
        result_error = {"error": "Erreur inattendue."}
        try:
            fallacy_pk = int(fallacy_pk_str)
        except ValueError:
            error_msg = f"Format PK invalide: '{fallacy_pk_str}'. Entier requis."
            self._logger.warning(error_msg)
            return json.dumps({"pk_requested": fallacy_pk_str, "error": error_msg})
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"pk_requested": fallacy_pk, "error": "Taxonomie sophismes non disponible."})
        details = self._internal_get_node_details(fallacy_pk, df)
        if details.get("error"):
             self._logger.warning(f" -> Erreur récupération détails PK {fallacy_pk}: {details['error']}")
        else:
             self._logger.info(f" -> Détails récupérés pour PK {fallacy_pk}.")
        try:
            return json.dumps(details, indent=2, ensure_ascii=False, default=str)
        except Exception as e_json:
            self._logger.error(f"Erreur sérialisation JSON détails PK {fallacy_pk}: {e_json}")
            result_error["error"] = f"Erreur sérialisation JSON: {e_json}"
            result_error["pk_requested"] = fallacy_pk
            return json.dumps(result_error)

logger.info("Classe InformalAnalysisPlugin (V12) définie.")

# --- Fonction setup_informal_kernel (V13 - Simplifiée) ---
def setup_informal_kernel(kernel: sk.Kernel, llm_service):
    """
    Configure le kernel pour l'InformalAnalysisAgent.
    Ajoute une instance du InformalAnalysisPlugin et la fonction sémantique.
    """
    plugin_name = "InformalAnalyzer"
    logger.info(f"Configuration Kernel pour {plugin_name} (V13 - Plugin autonome)...")

    informal_plugin_instance = InformalAnalysisPlugin()

    if plugin_name in kernel.plugins:
        logger.warning(f"Plugin '{plugin_name}' déjà présent. Remplacement.")
    kernel.add_plugin(informal_plugin_instance, plugin_name=plugin_name)
    logger.debug(f"Instance du plugin '{plugin_name}' ajoutée/mise à jour dans le kernel.")

    default_settings = None
    if llm_service:
        try:
            default_settings = kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
            logger.debug(f"Settings LLM récupérés pour {plugin_name}.")
        except Exception as e:
            logger.warning(f"Impossible de récupérer les settings LLM pour {plugin_name}: {e}")

    try:
        kernel.add_function(
            prompt=prompt_identify_args_v8,
            plugin_name=plugin_name,
            function_name="semantic_IdentifyArguments",
            description="Identifie les arguments clés dans un texte.",
            prompt_execution_settings=default_settings
        )
        logger.debug(f"Fonction {plugin_name}.semantic_IdentifyArguments ajoutée/mise à jour.")
    except ValueError as ve:
        logger.warning(f"Problème ajout/MàJ semantic_IdentifyArguments: {ve}")

        # Ajouter la fonction d'analyse des sophismes
        try:
            kernel.add_function(
                prompt=prompt_analyze_fallacies_v1,
                plugin_name=plugin_name,
                function_name="semantic_AnalyzeFallacies",
                description="Analyse les sophismes dans un argument.",
                prompt_execution_settings=default_settings
            )
            logger.debug(f"Fonction {plugin_name}.semantic_AnalyzeFallacies ajoutée/mise à jour.")
        except ValueError as ve:
            logger.warning(f"Problème ajout/MàJ semantic_AnalyzeFallacies: {ve}")
            
        # Ajouter la fonction de justification d'attribution
        try:
            kernel.add_function(
                prompt=prompt_justify_fallacy_attribution_v1,
                plugin_name=plugin_name,
                function_name="semantic_JustifyFallacyAttribution",
                description="Justifie l'attribution d'un sophisme à un argument.",
                prompt_execution_settings=default_settings
            )
            logger.debug(f"Fonction {plugin_name}.semantic_JustifyFallacyAttribution ajoutée/mise à jour.")
        except ValueError as ve:
            logger.warning(f"Problème ajout/MàJ semantic_JustifyFallacyAttribution: {ve}")

    native_facades = ["explore_fallacy_hierarchy", "get_fallacy_details"]
    if plugin_name in kernel.plugins:
        for func_name in native_facades:
             if func_name not in kernel.plugins[plugin_name]:
                 logger.error(f"ERREUR CRITIQUE: Fonction native {plugin_name}.{func_name} non enregistrée!")
             else:
                 logger.debug(f"Fonction native {plugin_name}.{func_name} trouvée.")
    else:
         logger.error(f"ERREUR CRITIQUE: Plugin {plugin_name} non trouvé après ajout!")
         
    logger.info(f"Kernel {plugin_name} configuré (V13).")

# --- Instructions Système ---
# (Provenant de la cellule [ID: 35fbe045] du notebook 'Argument_Analysis_Agentic-1-informal_agent.ipynb')
INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE = """
Votre Rôle: Spécialiste en analyse rhétorique informelle. Vous identifiez les arguments et analysez les sophismes en utilisant une taxonomie externe (via CSV).
Racine de la Taxonomie des Sophismes: PK={ROOT_PK}

**Fonctions Outils Disponibles:**
* `StateManager.*`: Fonctions pour lire et écrire dans l'état partagé (ex: `get_current_state_snapshot`, `add_identified_argument`, `add_identified_fallacy`, `add_answer`). **Utilisez ces fonctions pour enregistrer vos résultats.**
* `InformalAnalyzer.semantic_IdentifyArguments(input: str)`: Fonction sémantique (LLM) pour extraire les arguments d'un texte.
* `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str: str, max_children: int = 15)`: Fonction native (plugin) pour explorer la taxonomie CSV. Retourne JSON avec nœud courant et enfants.
* `InformalAnalyzer.get_fallacy_details(fallacy_pk_str: str)`: Fonction native (plugin) pour obtenir les détails d'un sophisme via son PK. Retourne JSON.

**Processus Général (pour chaque tâche assignée par le PM):**
1.  Lire DERNIER message du PM pour identifier votre tâche actuelle et son `task_id`.
2.  Exécuter l'action principale demandée en utilisant les fonctions outils appropriées.
3.  **Enregistrer les résultats** dans l'état partagé via les fonctions `StateManager`.
4.  **Signaler la fin de la tâche** au PM en appelant `StateManager.add_answer` avec le `task_id` reçu, un résumé de votre travail et les IDs des éléments ajoutés (`arg_id`, `fallacy_id`).

**Exemples de Tâches Spécifiques:**

* **Tâche "Identifier les arguments":**
    1.  Récupérer le texte brut (`raw_text`) depuis l'état (`StateManager.get_current_state_snapshot(summarize=False)`).
    2.  Appeler `InformalAnalyzer.semantic_IdentifyArguments(input=raw_text)`.
    3.  Pour chaque argument trouvé (chaque ligne de la réponse du LLM), appeler `StateManager.add_identified_argument(description=\"...\")`. Collecter les `arg_ids`.
    4.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec un résumé et la liste des `arg_ids`.

* **Tâche "Explorer taxonomie [depuis PK]":**
    1.  Déterminer le PK de départ (fourni dans la tâche ou `{ROOT_PK}`).
    2.  Appeler `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str=\"[PK en string]\")`.
    3.  Analyser le JSON retourné (vérifier `error`). Formuler une réponse textuelle résumant le nœud courant (`current_node`) et les enfants (`children`) avec leur PK et label (`nom_vulgarisé` ou `text_fr`). Proposer des actions (explorer enfant, voir détails, attribuer).
    4.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec la réponse textuelle et le PK exploré comme `source_ids`.

* **Tâche "Obtenir détails sophisme [PK]":**
    1.  Appeler `InformalAnalyzer.get_fallacy_details(fallacy_pk_str=\"[PK en string]\")`.
    2.  Analyser le JSON retourné (vérifier `error`). Formuler une réponse textuelle avec les détails pertinents (PK, labels, description, exemple, famille).
    3.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec les détails formatés et le PK comme `source_ids`.

* **Tâche "Attribuer sophisme [PK] à argument [arg_id]":**
    1.  Appeler `InformalAnalyzer.get_fallacy_details(fallacy_pk_str=\"[PK en string]\")` pour obtenir le label (priorité: `nom_vulgarisé`, sinon `text_fr`) et la description complète. Vérifier `error`. Si pas de label valide ou erreur, signaler dans la réponse `add_answer` et **ne pas attribuer**.
    2.  Récupérer le texte de l'argument ciblé depuis l'état partagé.
    3.  Rédiger une justification détaillée pour l'attribution qui:
       - Explique clairement en quoi l'argument correspond à ce type de sophisme
       - Cite des parties spécifiques de l'argument qui illustrent le sophisme
       - Fournit un exemple similaire pour clarifier (si pertinent)
       - Explique l'impact de ce sophisme sur la validité de l'argument
    4.  Si label OK, appeler `StateManager.add_identified_fallacy(fallacy_type=\"[label trouvé]\", justification=\"...\", target_argument_id=\"[arg_id]\")`. Noter le `fallacy_id`.
    5.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec confirmation (PK, label, arg_id, fallacy_id) ou message d'erreur si étape 1 échoue. Utiliser IDs pertinents (`fallacy_id`, `arg_id`) comme `source_ids`.

* **Tâche "Analyser sophismes dans argument [arg_id]":**
    1.  Récupérer le texte de l'argument depuis l'état partagé.
    2.  Explorer la taxonomie des sophismes en commençant par la racine (`{ROOT_PK}`).
    3.  Pour chaque catégorie pertinente de sophismes, explorer les sous-catégories.
    4.  Pour chaque sophisme potentiellement applicable:
       - Obtenir ses détails complets via `InformalAnalyzer.get_fallacy_details`
       - Évaluer si l'argument contient ce type de sophisme
       - Si oui, attribuer le sophisme avec une justification détaillée
    5.  Viser à identifier au moins 2-3 sophismes différents par argument quand c'est pertinent.
    6.  Appeler `StateManager.add_answer` avec un résumé des sophismes identifiés.

* **Si Tâche Inconnue/Pas Claire:** Signaler l'incompréhension via `StateManager.add_answer`.

**Directives pour l'Exploration de la Taxonomie:**
- Explorez systématiquement la taxonomie en profondeur, pas seulement les premiers niveaux.
- Utilisez une approche "top-down": commencez par les grandes catégories, puis explorez les sous-catégories pertinentes.
- Pour chaque argument, considérez au moins 3-5 branches différentes de la taxonomie.
- Ne vous limitez pas aux sophismes les plus évidents ou les plus connus.
- Documentez votre processus d'exploration dans vos réponses.

**Directives pour les Justifications:**
- Vos justifications doivent être détaillées (au moins 100 mots).
- Incluez toujours des citations spécifiques de l'argument qui illustrent le sophisme.
- Expliquez le mécanisme du sophisme et son impact sur la validité de l'argument.
- Quand c'est pertinent, fournissez un exemple similaire pour clarifier.
- Évitez les justifications vagues ou génériques.

**Important:** Toujours utiliser le `task_id` fourni par le PM pour `StateManager.add_answer`. Gérer les erreurs potentielles des appels de fonction (vérifier `error` dans JSON retourné par les fonctions natives, ou si une fonction retourne `FUNC_ERROR:`).
"""
INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE.format(
    ROOT_PK=ROOT_PK
)
logger.info("Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V14) définies.")

# Log de chargement
logging.getLogger(__name__).debug("Module agents.informal.informal_definitions chargé.")