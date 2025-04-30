#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Définitions pour l'agent Informel.

Ce module contient:
1. La classe InformalAnalysisPlugin pour l'analyse des sophismes
2. La fonction setup_informal_kernel pour configurer le kernel
3. Les instructions système pour l'agent Informel
"""

import os
import sys
import json
import logging
import pandas as pd
import semantic_kernel as sk
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("InformalDefinitions")

# Import des prompts
from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1

# --- Classe InformalAnalysisPlugin (V12) ---
class InformalAnalysisPlugin:
    """
    Plugin pour l'analyse des sophismes dans les arguments.
    
    Ce plugin fournit des fonctions pour:
    1. Explorer la hiérarchie des sophismes
    2. Obtenir les détails d'un sophisme spécifique
    """
    
    def __init__(self):
        """
        Initialise le plugin d'analyse des sophismes.
        """
        self._logger = logging.getLogger("InformalAnalysisPlugin")
        self._logger.info("Initialisation du plugin d'analyse des sophismes (V12)...")
        
        # Constantes pour le CSV
        self.FALLACY_CSV_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
        self.DATA_DIR = Path("data")
        self.FALLACY_CSV_LOCAL_PATH = self.DATA_DIR / "argumentum_fallacies_taxonomy.csv"
        
        # Créer le répertoire de données si nécessaire
        self.DATA_DIR.mkdir(exist_ok=True)
        
        # Charger la taxonomie
        self._taxonomy_df = self._load_taxonomy()
    
    def _load_taxonomy(self) -> Optional[pd.DataFrame]:
        """
        Charge la taxonomie des sophismes depuis le fichier CSV.
        """
        self._logger.info("Chargement de la taxonomie des sophismes...")
        
        if not self.FALLACY_CSV_LOCAL_PATH.exists():
            self._logger.error(f"Fichier CSV de taxonomie non trouvé: {self.FALLACY_CSV_LOCAL_PATH}")
            return None
        
        try:
            df = pd.read_csv(self.FALLACY_CSV_LOCAL_PATH, encoding='utf-8')
            self._logger.info(f"Taxonomie chargée avec succès: {len(df)} sophismes.")
            return df
        except Exception as e:
            self._logger.error(f"Erreur lors du chargement de la taxonomie: {e}")
            return None
    
    def _internal_explore_hierarchy(self, current_pk: int, df: pd.DataFrame, max_children: int = 15) -> Dict[str, Any]:
        """
        Explore la hiérarchie des sophismes à partir d'un nœud donné.
        """
        result = {
            "current_node": None,
            "children": [],
            "error": None
        }
        
        if df is None:
            result["error"] = "Taxonomie sophismes non disponible."
            return result
        
        # Convertir les colonnes numériques
        if 'PK' in df.columns:
            df['PK'] = pd.to_numeric(df['PK'], errors='coerce')
        if 'depth' in df.columns:
            df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
        
        # Trouver le nœud courant
        current_node = df[df['PK'] == current_pk]
        if len(current_node) == 0:
            result["error"] = f"PK {current_pk} non trouvée dans la taxonomie."
            return result
        
        # Extraire les informations du nœud courant
        current_row = current_node.iloc[0]
        current_path = current_row.get('path', '')
        
        result["current_node"] = {
            "pk": int(current_row['PK']),
            "path": current_path,
            "depth": int(current_row['depth']) if pd.notna(current_row.get('depth')) else 0,
            "nom_vulgarisé": current_row.get('nom_vulgarisé', ''),
            "text_fr": current_row.get('text_fr', ''),
            "text_en": current_row.get('text_en', '')
        }
        
        # Trouver les enfants (nœuds dont le chemin commence par le chemin actuel suivi d'un point)
        if current_path:
            # Pour les nœuds avec un chemin, chercher les enfants directs
            children = df[df['path'].str.startswith(current_path + '.', na=False) &
                         ~df['path'].str.contains('\\..*\\.', na=False, regex=True)]
        else:
            # Pour le nœud racine (PK=0), chercher les nœuds de premier niveau
            children = df[df['depth'] == 1]
        children_count = len(children)
        
        if children_count > 0:
            # Limiter le nombre d'enfants si nécessaire
            if max_children > 0 and children_count > max_children:
                children = children.head(max_children)
                result["children_truncated"] = True
                result["total_children"] = children_count
            
            # Extraire les informations des enfants
            for _, child in children.iterrows():
                child_info = {
                    "pk": int(child['PK']),
                    "nom_vulgarisé": child.get('nom_vulgarisé', ''),
                    "text_fr": child.get('text_fr', ''),
                    "has_children": len(df[df['path'].str.startswith(child.get('path', '') + '.', na=False)]) > 0
                }
                result["children"].append(child_info)
        
        return result
    
    def _internal_get_node_details(self, pk: int, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Obtient les détails d'un nœud spécifique.
        """
        result = {
            "pk": pk,
            "error": None
        }
        
        if df is None:
            result["error"] = "Taxonomie sophismes non disponible."
            return result
        
        # Convertir les colonnes numériques
        if 'PK' in df.columns:
            df['PK'] = pd.to_numeric(df['PK'], errors='coerce')
        if 'depth' in df.columns:
            df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
        
        # Trouver le nœud
        node = df[df['PK'] == pk]
        if len(node) == 0:
            result["error"] = f"PK {pk} non trouvée dans la taxonomie."
            return result
        
        # Extraire les informations du nœud
        row = node.iloc[0]
        for col in row.index:
            if pd.notna(row[col]):
                result[col] = row[col]
        
        # Trouver le parent à partir du chemin
        path = row.get('path', '')
        if path and '.' in path:
            parent_path = path.rsplit('.', 1)[0]
            parent = df[df['path'] == parent_path]
            if len(parent) > 0:
                parent_row = parent.iloc[0]
                result["parent"] = {
                    "pk": int(parent_row['PK']),
                    "nom_vulgarisé": parent_row.get('nom_vulgarisé', ''),
                    "text_fr": parent_row.get('text_fr', '')
                }
        
        # Trouver les enfants (nœuds dont le chemin commence par le chemin actuel suivi d'un point)
        if path:
            # Pour les nœuds avec un chemin, chercher les enfants directs
            children = df[df['path'].str.startswith(path + '.', na=False) &
                         ~df['path'].str.contains('\\..*\\.', na=False, regex=True)]
        else:
            # Pour le nœud racine (PK=0), chercher les nœuds de premier niveau
            children = df[df['depth'] == 1]
        if len(children) > 0:
            result["children"] = []
            for _, child in children.iterrows():
                child_info = {
                    "pk": int(child['PK']),
                    "nom_vulgarisé": child.get('nom_vulgarisé', ''),
                    "text_fr": child.get('text_fr', '')
                }
                result["children"].append(child_info)
        
        return result
    
    def explore_fallacy_hierarchy(self, current_pk_str: str, max_children: int = 15) -> str:
        """
        Explore la hiérarchie des sophismes à partir d'un nœud donné.
        
        Args:
            current_pk_str: PK du nœud à explorer (en string)
            max_children: Nombre maximum d'enfants à retourner
        
        Returns:
            JSON avec le nœud courant et ses enfants
        """
        self._logger.info(f"Exploration hiérarchie sophismes depuis PK {current_pk_str}...")
        
        try:
            current_pk = int(current_pk_str)
        except ValueError:
            self._logger.error(f"PK invalide: {current_pk_str}")
            return json.dumps({"error": f"PK invalide: {current_pk_str}"})
        
        df = self._taxonomy_df
        if df is None:
            self._logger.error("Taxonomie sophismes non disponible.")
            return json.dumps({"error": "Taxonomie sophismes non disponible."})
        
        result = self._internal_explore_hierarchy(current_pk, df, max_children)
        if result.get("error"):
            self._logger.warning(f" -> Erreur exploration PK {current_pk}: {result['error']}")
        else:
            self._logger.info(f" -> Hiérarchie explorée depuis PK {current_pk}: {len(result['children'])} enfants.")
        
        try:
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e_json:
            self._logger.error(f"Erreur sérialisation JSON hiérarchie PK {current_pk}: {e_json}")
            result_error = {"error": f"Erreur sérialisation JSON: {e_json}", "current_pk": current_pk}
            return json.dumps(result_error)
    
    def get_fallacy_details(self, fallacy_pk_str: str) -> str:
        """
        Obtient les détails d'un sophisme spécifique.
        
        Args:
            fallacy_pk_str: PK du sophisme (en string)
        
        Returns:
            JSON avec les détails du sophisme
        """
        self._logger.info(f"Récupération détails sophisme PK {fallacy_pk_str}...")
        
        result_error = {"error": None}
        
        try:
            fallacy_pk = int(fallacy_pk_str)
        except ValueError:
            self._logger.error(f"PK invalide: {fallacy_pk_str}")
            result_error["error"] = f"PK invalide: {fallacy_pk_str}"
            return json.dumps(result_error)
        
        df = self._taxonomy_df
        if df is None:
            self._logger.error("Taxonomie sophismes non disponible.")
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
        # Ajouter la fonction d'identification des arguments
        kernel.add_function(
            prompt=prompt_identify_args_v8,
            plugin_name=plugin_name,
            function_name="semantic_IdentifyArguments",
            description="Identifie les arguments clés dans un texte.",
            prompt_execution_settings=default_settings
        )
        logger.debug(f"Fonction {plugin_name}.semantic_IdentifyArguments ajoutée/mise à jour.")

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
    except Exception as e:
        logger.error(f"Erreur lors de la configuration des fonctions sémantiques: {e}")

    # Les fonctions natives sont automatiquement enregistrées lors de l'ajout du plugin
    # Vérifions simplement qu'elles sont bien présentes
    native_facades = ["explore_fallacy_hierarchy", "get_fallacy_details"]
    if plugin_name in kernel.plugins:
        for func_name in native_facades:
            if hasattr(informal_plugin_instance, func_name):
                logger.debug(f"Fonction native {plugin_name}.{func_name} disponible dans l'instance.")
            else:
                logger.error(f"ERREUR CRITIQUE: Fonction {func_name} non trouvée dans l'instance du plugin!")
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

INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE.format(ROOT_PK=0)

logger.info("Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V14) définies.")