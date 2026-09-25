#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Composants de base pour l'analyse informelle des arguments.

Ce module définit l'architecture logicielle pour l'interaction avec une
taxonomie de sophismes au sein de l'écosystème Semantic Kernel.

Il contient trois éléments principaux :
1.  `InformalAnalysisPlugin` : Un plugin natif pour Semantic Kernel qui expose
    des fonctions pour charger, interroger et explorer une taxonomie de
    sophismes stockée dans un fichier CSV.
2.  `setup_informal_kernel` : Une fonction de configuration qui enregistre
    le plugin natif et les fonctions sémantiques associées dans une instance
    de `Kernel`.
3.  `INFORMAL_AGENT_INSTRUCTIONS` : Un template de prompt système conçu pour
    un agent LLM, lui expliquant comment utiliser les outils fournis par ce
    module pour réaliser des tâches d'analyse rhétorique.
"""

import os
import sys
import json
import logging
import pandas as pd
import requests
import semantic_kernel as sk
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelArguments
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
    OpenAIChatPromptExecutionSettings,
)
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Dict, List, Any, Optional
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_function import KernelFunction
from semantic_kernel.functions.kernel_function_metadata import KernelFunctionMetadata
from semantic_kernel.functions.kernel_parameter_metadata import KernelParameterMetadata

# Import de l'utilitaire de lazy loading pour la taxonomie
from argumentation_analysis.core.utils.file_loaders import load_csv_file
from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path
from argumentation_analysis.utils.taxonomy_tree import taxonomy_parent_paths
from argumentation_analysis.utils.taxonomy_local_overrides import purge_dataframe
from argumentation_analysis.paths import DATA_DIR

logger = logging.getLogger("InformalDefinitions")

# Import des prompts (V3 - Tool Use)
from .prompts import (
    prompt_identify_args_v8,
    prompt_analyze_fallacies_v3_tool_use,
    prompt_justify_fallacy_attribution_v1,
)

# --- Modèles Pydantic pour une sortie structurée ---


class IdentifiedFallacy(BaseModel):
    """Modèle de données pour un seul sophisme identifié."""

    nom: str = Field(
        ...,
        description="Le nom du sophisme, doit correspondre EXACTEMENT à un nom de la taxonomie fournie.",
    )
    justification: str = Field(
        ...,
        description="Citation exacte du texte et explication détaillée de pourquoi c'est un sophisme.",
    )


class FallacyAnalysisResult(BaseModel):
    """Modèle de données pour le résultat complet de l'analyse de sophismes."""

    sophismes: List[IdentifiedFallacy] = Field(
        ..., description="Liste de tous les sophismes identifiés dans le texte."
    )


# --- Recherche d'un sophisme par son nom (#2412) ---

#: Colonnes qui portent un nom de sophisme, dans l'ordre où un nom est rapporté.
NAME_COLUMNS = ("nom_vulgarisé", "text_fr", "Latin")

#: Nombre maximal de candidats rapportés quand un nom ne désigne pas un seul nœud.
MAX_NAME_CANDIDATES = 10


def _cell_text(row: pd.Series, column: str) -> str:
    """Texte d'une cellule, ``""`` si la colonne manque ou si la cellule est vide.

    ``row.get(col, default)`` ne rend le défaut que si la colonne est absente :
    une cellule vide rend ``NaN``, qui part tel quel dans le JSON (#2412).
    """
    value = row.get(column)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def reported_fallacy_name(row: pd.Series, default: str = "") -> str:
    """Le nom sous lequel un nœud est rapporté : vulgarisé, sinon ``text_fr``."""
    for column in ("nom_vulgarisé", "text_fr"):
        text = _cell_text(row, column)
        if text:
            return text
    return default


def rows_matching_fallacy_name(df: pd.DataFrame, fallacy_name: str) -> pd.DataFrame:
    """Les lignes qu'un nom de sophisme désigne (#2412).

    La requête est lue **littéralement**, jamais comme une regex : un nom qui
    porte des parenthèses doit se retrouver lui-même. Un nom **exact** (casse
    ignorée, sur l'une des colonnes de nom) l'emporte sur une sous-chaîne ; la
    sous-chaîne reste le repli, puisque le prompt de l'agent cherche aussi par
    mots-clés. Plusieurs lignes rendues = un nom qui ne désigne pas un nœud.
    """
    query = str(fallacy_name or "").strip().casefold()
    if not query:
        return df.iloc[0:0]
    exact = pd.Series(False, index=df.index)
    contains = pd.Series(False, index=df.index)
    for column in NAME_COLUMNS:
        if column not in df.columns:
            continue
        values = df[column].fillna("").astype(str).str.strip().str.casefold()
        exact |= values == query
        contains |= values.str.contains(query, regex=False)
    return df[exact] if exact.any() else df[contains]


def node_summary(row: pd.Series) -> Dict[str, Any]:
    """Le résumé d'un nœud que l'explorateur et les détails renvoient.

    Les cellules vides rendent ``""`` : ``row.get(col, "")`` rendait ``NaN``,
    et le JSON de l'outil n'était plus du JSON strict.
    """
    return {
        "pk": int(row.name),
        # Clé de sortie `nom_vulgarise` (contrat, non accentuée) ≠ colonne CSV
        # `nom_vulgarisé` (accentuée) : les confondre est le défaut de 0b77c3e50 (#2196).
        "nom_vulgarise": _cell_text(row, "nom_vulgarisé"),
        "description_courte": _cell_text(row, "text_fr"),
        "famille": _cell_text(row, "Famille"),
    }


def child_rows(df: pd.DataFrame, pk: Any, path: Any, depth: Any):
    """Les enfants d'un nœud, et de quoi dire si un enfant en a lui-même.

    Rend ``(children, has_children)`` ; ``has_children(child_row)`` rend
    ``None`` quand la relation lue ne permet pas de le dire. L'explorateur et
    les détails lisaient chacun leur copie de cette cascade (#2345).
    """
    if "FK_Parent" in df.columns:
        keys = set(df["FK_Parent"].dropna())
        return df[df["FK_Parent"] == pk], lambda child: child.name in keys
    if "parent_pk" in df.columns:
        keys = set(df["parent_pk"].dropna())
        return df[df["parent_pk"] == pk], lambda child: child.name in keys
    if "path" in df.columns and path:
        parents = taxonomy_parent_paths(df)
        keys = set(parents.dropna())
        return df[parents == str(path)], lambda child: (
            str(child.get("path", "")) in keys
        )
    if "depth" in df.columns and pd.notna(depth):
        path_str = str(path) if pd.notna(path) else ""
        children = df[
            (df["depth"] == int(depth) + 1)
            & (
                df["path"]
                .astype(str)
                .str.startswith(path_str + ("." if path_str else ""), na=False)
            )
        ]
        return children, lambda child: None
    return df.iloc[0:0], lambda child: None


# --- Classe InformalAnalysisPlugin (Refonte Hybride) ---
class InformalAnalysisPlugin:
    """
    Plugin natif pour Semantic Kernel dédié à l'analyse de sophismes.
    """

    def __init__(
        self, kernel: Optional[Kernel] = None, taxonomy_file_path: Optional[str] = None
    ):
        """
        Initialise le plugin hybride.

        ``kernel`` is stored but never read by this class — the taxonomy-only
        entry points (``TaxonomySophismDetector`` / ``get_global_detector``)
        construct the plugin for its CSV accessor alone, so it is optional.
        """
        self.kernel = kernel
        self._logger = logging.getLogger("InformalAnalysisPlugin")
        self._logger.info(
            f"Initialisation du plugin d'analyse des sophismes (hybride)..."
        )

        self.DEFAULT_TAXONOMY_PATH = (
            Path(DATA_DIR) / "argumentum_fallacies_taxonomy.csv"
        )
        if taxonomy_file_path:
            self._current_taxonomy_path = Path(taxonomy_file_path)
        else:
            self._current_taxonomy_path = get_taxonomy_path()
        self._logger.info(
            f"Chemin de taxonomie utilisé : {self._current_taxonomy_path}"
        )

        self._taxonomy_df_cache = None

    def _internal_load_and_prepare_dataframe(self) -> pd.DataFrame:
        """
        Charge et prépare le DataFrame de la taxonomie.
        """
        self._logger.info(
            f"Chargement et préparation du DataFrame de taxonomie depuis: {self._current_taxonomy_path}..."
        )

        try:
            df = load_csv_file(self._current_taxonomy_path)
            if df is None:
                raise Exception(
                    f"Impossible de charger la taxonomie depuis {self._current_taxonomy_path}"
                )

            # #2036: local editorial-note purges — the vendored CSV stays a
            # byte-faithful upstream mirror, fixes live in code.
            purge_dataframe(df)

            self._logger.info(
                f"Taxonomie chargée : {len(df)} entrées. Standardisation des types de clés..."
            )

            key_columns = ["PK", "FK_Parent", "parent_pk"]

            # #2344: every reader goes through ``df.loc[pk]``. A key the loader
            # cannot index (null, non-numeric, duplicated) stops the load here,
            # instead of an error log and a frame that fails in the first lookup.
            if "PK" not in df.columns:
                raise ValueError(
                    "Colonne 'PK' non trouvée : l'index de la taxonomie ne peut être défini."
                )
            for col in key_columns:
                if col not in df.columns:
                    continue
                df[col] = pd.to_numeric(df[col], errors="coerce")
                if col == "PK":
                    n_null = int(df[col].isnull().sum())
                    if n_null:
                        raise ValueError(
                            f"La colonne clé primaire 'PK' porte {n_null} valeur(s) "
                            "nulle(s) ou non numérique(s) : la taxonomie ne peut être indexée."
                        )
                    df[col] = df[col].astype(int)
                    self._logger.info(
                        f"Colonne '{col}' traitée, type final: {df[col].dtype}."
                    )
                else:
                    if not df[col].isnull().any():
                        df[col] = df[col].astype(int)
                    self._logger.info(
                        f"Colonne '{col}' (clé étrangère) traitée, type final: {df[col].dtype}."
                    )

            duplicated = sorted(set(df.loc[df["PK"].duplicated(), "PK"]))
            if duplicated:
                raise ValueError(
                    f"La colonne clé primaire 'PK' porte des doublons : {duplicated[:10]}"
                    " — ``df.loc[pk]`` rendrait plusieurs lignes."
                )
            df.set_index("PK", inplace=True)
            self._logger.info(
                f"Index 'PK' défini avec succès. Type de l'index: {df.index.dtype}."
            )

            return df
        except Exception as e:
            self._logger.error(
                f"Erreur majeure lors du chargement/préparation de la taxonomie: {e}"
            )
            raise

    def _get_taxonomy_dataframe(self) -> pd.DataFrame:
        """
        Accède au DataFrame de la taxonomie avec mise en cache.
        """
        if self._taxonomy_df_cache is None:
            self._taxonomy_df_cache = self._internal_load_and_prepare_dataframe()
        return self._taxonomy_df_cache.copy()

    def _internal_explore_hierarchy(
        self, current_pk: int, df: pd.DataFrame, max_children: int = 15
    ) -> Dict[str, Any]:
        self._logger.debug(
            f"DEBUG: Entering _internal_explore_hierarchy with pk={current_pk}"
        )
        result = {"current_node": None, "children": [], "error": None}

        if df is None:
            result["error"] = "Taxonomie sophismes non disponible."
            self._logger.debug(
                "DEBUG: Exiting _internal_explore_hierarchy (df is None)"
            )
            return result

        if "depth" in df.columns and not pd.api.types.is_numeric_dtype(df["depth"]):
            df["depth"] = pd.to_numeric(df["depth"], errors="coerce")

        current_node_df = (
            df.loc[df.index == current_pk] if current_pk in df.index else pd.DataFrame()
        )
        if len(current_node_df) == 0:
            result["error"] = f"PK {current_pk} non trouvée dans la taxonomie."
            return result

        current_row = current_node_df.iloc[0]
        current_path = current_row.get("path", "")

        result["current_node"] = {
            "pk": int(current_row.name),
            "path": current_path,
            "depth": (
                int(current_row["depth"]) if pd.notna(current_row.get("depth")) else 0
            ),
            "Name": _cell_text(current_row, "Name"),
            **{k: v for k, v in node_summary(current_row).items() if k != "pk"},
        }

        children_df, has_children = child_rows(
            df, current_pk, current_path, current_row.get("depth")
        )

        children_count = len(children_df)

        if children_count > 0:
            if max_children > 0 and children_count > max_children:
                children_df = children_df.head(max_children)
                result["children_truncated"] = True
                result["total_children"] = children_count

            for _, child_row in children_df.iterrows():
                child_info = node_summary(child_row)
                child_info["has_children"] = has_children(child_row)
                result["children"].append(child_info)

        self._logger.debug(
            f"DEBUG: Exiting _internal_explore_hierarchy with pk={current_pk}"
        )
        return result

    def _internal_get_node_details(self, pk: int, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Logique interne pour récupérer les détails complets d'un nœud.
        """
        self._logger.debug(f"DEBUG: Entering _internal_get_node_details with pk={pk}")
        result = {"pk": pk, "error": None}

        if df is None:
            result["error"] = "Taxonomie sophismes non disponible."
            self._logger.debug(
                f"DEBUG: Exiting _internal_get_node_details (df is None) for pk={pk}"
            )
            return result

        if "PK" in df.columns and not pd.api.types.is_numeric_dtype(df["PK"]):
            df["PK"] = pd.to_numeric(df["PK"], errors="coerce")
        if "depth" in df.columns and not pd.api.types.is_numeric_dtype(df["depth"]):
            df["depth"] = pd.to_numeric(df["depth"], errors="coerce")

        node_df = df.loc[df.index == pk]
        if len(node_df) == 0:
            result["error"] = f"PK {pk} non trouvée dans la taxonomie."
            return result
        row = node_df.iloc[0]
        for col in row.index:
            if pd.notna(row[col]):
                if hasattr(row[col], "item"):
                    result[col] = row[col].item()
                else:
                    result[col] = row[col]

        parent_df = pd.DataFrame()
        parent_pk_val = None
        if "FK_Parent" in df.columns and pd.notna(row.get("FK_Parent")):
            parent_pk_val = row.get("FK_Parent")
        elif "parent_pk" in df.columns and pd.notna(row.get("parent_pk")):
            parent_pk_val = row.get("parent_pk")

        if parent_pk_val is not None:
            try:
                parent_pk_int = int(parent_pk_val)
                parent_df = df.loc[df.index == parent_pk_int]
            except ValueError:
                self._logger.warning(
                    f"Valeur FK_Parent/parent_pk non entière pour le nœud {pk}: {parent_pk_val}"
                )

        elif "path" in df.columns:
            parent_path = taxonomy_parent_paths(df).loc[pk]
            if parent_path is not None:
                parent_df = df[df["path"].astype(str) == parent_path]

        if len(parent_df) > 0:
            parent_row = parent_df.iloc[0]
            result["parent"] = node_summary(parent_row)

        child_nodes_for_details, _ = child_rows(
            df, pk, row.get("path", ""), row.get("depth", None)
        )

        if len(child_nodes_for_details) > 0:
            result["children"] = []
            for _, child_row_detail in child_nodes_for_details.iterrows():
                result["children"].append(node_summary(child_row_detail))

        self._logger.debug(f"DEBUG: Exiting _internal_get_node_details for pk={pk}")
        return result

    def get_taxonomy_summary_for_prompt(self) -> str:
        """Charge la taxonomie et la formate pour l'injection dans un prompt."""
        try:
            df = self._get_taxonomy_dataframe()
            return "\n".join(
                f"- {row.get('nom_vulgarisé', 'N/A')}: {row.get('text_fr', 'N/A')}"
                for _, row in df.iterrows()
            )
        except Exception as e:
            self._logger.error(
                f"Impossible de charger ou formater la taxonomie pour le prompt : {e}"
            )
            return "Erreur: taxonomie non disponible."

    def _validate_and_enrich_result(self, result: FallacyAnalysisResult):
        self._logger.debug("Validation et enrichissement du résultat de l'analyse...")
        pass

    @kernel_function(
        description="Explore la hiérarchie des sophismes à partir d'un nœud donné (par sa PK en chaîne).",
        name="explore_fallacy_hierarchy",
    )
    def explore_fallacy_hierarchy(
        self, current_pk_str: str, max_children: int = 15
    ) -> str:
        self._logger.info(
            f"Exploration hiérarchie sophismes depuis PK {current_pk_str}..."
        )

        try:
            current_pk = int(current_pk_str)
        except ValueError:
            self._logger.error(f"PK invalide: {current_pk_str}")
            return json.dumps({"error": f"PK invalide: {current_pk_str}"})

        df = self._get_taxonomy_dataframe()
        if df is None:
            self._logger.error(
                "Taxonomie sophismes non disponible (DataFrame est None)."
            )
            return json.dumps({"error": "Taxonomie sophismes non disponible."})

        result = self._internal_explore_hierarchy(current_pk, df, max_children)
        if result.get("error"):
            self._logger.warning(
                f" -> Erreur exploration PK {current_pk}: {result['error']}"
            )
        else:
            self._logger.info(
                f" -> Hiérarchie explorée depuis PK {current_pk}: {len(result.get('children', []))} enfants."
            )

        try:
            return json.dumps(result, indent=2, ensure_ascii=False, default=str)
        except Exception as e_json:
            self._logger.error(
                f"Erreur sérialisation JSON hiérarchie PK {current_pk}: {e_json}"
            )
            result_error = {
                "error": f"Erreur sérialisation JSON: {str(e_json)}",
                "current_pk": current_pk,
            }
            return json.dumps(result_error)

    @kernel_function(
        description="Obtient les détails d'un sophisme spécifique par sa PK (fournie en chaîne).",
        name="get_fallacy_details",
    )
    def get_fallacy_details(self, fallacy_pk_str: str) -> str:
        self._logger.info(f"Récupération détails sophisme PK {fallacy_pk_str}...")

        result_error = {"error": None}

        try:
            fallacy_pk = int(fallacy_pk_str)
        except ValueError:
            self._logger.error(f"PK invalide: {fallacy_pk_str}")
            result_error["error"] = f"PK invalide: {fallacy_pk_str}"
            return json.dumps(result_error)

        df = self._get_taxonomy_dataframe()
        if df is None:
            self._logger.error(
                "Taxonomie sophismes non disponible (DataFrame est None)."
            )
            return json.dumps(
                {
                    "pk_requested": fallacy_pk,
                    "error": "Taxonomie sophismes non disponible.",
                }
            )

        details = self._internal_get_node_details(fallacy_pk, df)
        if details.get("error"):
            self._logger.warning(
                f" -> Erreur récupération détails PK {fallacy_pk}: {details['error']}"
            )
        else:
            self._logger.info(f" -> Détails récupérés pour PK {fallacy_pk}.")
        try:
            return json.dumps(details, indent=2, ensure_ascii=False, default=str)
        except Exception as e_json:
            self._logger.error(
                f"Erreur sérialisation JSON détails PK {fallacy_pk}: {e_json}"
            )
            result_error["error"] = f"Erreur sérialisation JSON: {str(e_json)}"
            result_error["pk_requested"] = fallacy_pk
            return json.dumps(result_error)

    @kernel_function(
        description="Recherche la définition d'un sophisme par son nom.",
        name="find_fallacy_definition",
    )
    def find_fallacy_definition(self, fallacy_name: str) -> str:
        self._logger.info(
            f"Recherche de la définition pour le sophisme: '{fallacy_name}'"
        )
        return self._lookup_by_name(
            fallacy_name,
            column="desc_fr",
            key="definition",
            missing="Définition non disponible.",
            not_found=f"Définition non trouvée pour '{fallacy_name}'.",
        )

    def _lookup_by_name(
        self, fallacy_name: str, column: str, key: str, missing: str, not_found: str
    ) -> str:
        """La recherche par nom partagée par la définition et l'exemple (#2412).

        Un seul nœud trouvé : son ``pk``, son nom et la valeur de ``column``.
        Plusieurs : les candidats (``pk`` + nom, plafonnés), jamais un premier
        arbitraire — l'agent précise ensuite via ``get_fallacy_details(pk)``.
        """
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"error": "Taxonomie non disponible."})

        found = rows_matching_fallacy_name(df, fallacy_name)
        if found.empty:
            self._logger.warning(f"Aucun sophisme trouvé pour '{fallacy_name}'.")
            return json.dumps({"error": not_found})

        if len(found) > 1:
            self._logger.info(
                f"'{fallacy_name}' désigne {len(found)} nœuds : candidats rapportés."
            )
            candidates = [
                {"pk": int(pk), "fallacy_name": reported_fallacy_name(row)}
                for pk, row in found.head(MAX_NAME_CANDIDATES).iterrows()
            ]
            return json.dumps(
                {
                    "query": fallacy_name,
                    "ambiguous": True,
                    "match_count": len(found),
                    "candidates": candidates,
                    "message": (
                        f"'{fallacy_name}' désigne {len(found)} sophismes ; "
                        "préciser avec get_fallacy_details(pk)."
                    ),
                },
                ensure_ascii=False,
            )

        pk_found = int(found.index[0])
        row = found.iloc[0]
        name_found = reported_fallacy_name(row, default=fallacy_name)
        self._logger.info(f"Trouvé '{name_found}' (PK: {pk_found}).")
        return json.dumps(
            {
                "fallacy_name": name_found,
                "pk": pk_found,
                key: _cell_text(row, column) or missing,
            },
            ensure_ascii=False,
        )

    @kernel_function(
        description="Liste les grandes catégories de sophismes (basées sur la colonne 'Famille').",
        name="list_fallacy_categories",
    )
    def list_fallacy_categories(self) -> str:
        self._logger.info("Listage des catégories de sophismes...")
        try:
            df = self._get_taxonomy_dataframe()
        except ValueError as e:
            self._logger.error(
                f"Erreur de chargement de la taxonomie lors du listage des catégories: {e}"
            )
            return json.dumps({"error": f"Erreur de chargement de la taxonomie: {e}"})

        if df is None:
            return json.dumps(
                {"error": "Taxonomie non disponible (DataFrame est None)."}
            )

        if "Famille" in df.columns:
            categories = df["Famille"].dropna().unique().tolist()
            if categories:
                self._logger.info(f"{len(categories)} catégories trouvées.")
                return json.dumps({"categories": categories}, default=str)
            else:
                self._logger.info(
                    "Colonne 'Famille' présente mais vide ou que des NaN."
                )
                return json.dumps(
                    {
                        "categories": [],
                        "message": "Aucune catégorie définie dans la colonne 'Famille'.",
                    }
                )
        else:
            self._logger.warning("Colonne 'Famille' non trouvée dans la taxonomie.")
            return json.dumps(
                {
                    "categories": [],
                    "error": "Colonne 'Famille' pour les catégories non trouvée dans la taxonomie.",
                }
            )

    @kernel_function(
        description="Liste les sophismes appartenant à une catégorie donnée.",
        name="list_fallacies_in_category",
    )
    def list_fallacies_in_category(self, category_name: str) -> str:
        self._logger.info(f"Listage des sophismes dans la catégorie: '{category_name}'")
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"error": "Taxonomie non disponible."})

        if "Famille" not in df.columns:
            self._logger.warning(
                "Colonne 'Famille' non trouvée pour lister les sophismes par catégorie."
            )
            return json.dumps(
                {
                    "category": category_name,
                    "fallacies": [],
                    "error": "Colonne 'Famille' pour les catégories non trouvée.",
                }
            )

        fallacies_in_cat_df = df[df["Famille"] == category_name]

        if not fallacies_in_cat_df.empty:
            result_list = []
            for index, row in fallacies_in_cat_df.iterrows():
                pk_val = index
                name_val = reported_fallacy_name(row, default="Nom non disponible")
                result_list.append({"pk": int(pk_val), "nom_vulgarise": name_val})
            self._logger.info(
                f"{len(result_list)} sophismes trouvés dans la catégorie '{category_name}'."
            )
            return json.dumps(
                {"category": category_name, "fallacies": result_list}, default=str
            )
        else:
            self._logger.warning(
                f"Aucun sophisme trouvé pour la catégorie '{category_name}' ou catégorie inexistante."
            )
            return json.dumps(
                {
                    "category": category_name,
                    "fallacies": [],
                    "message": f"Aucun sophisme trouvé pour la catégorie '{category_name}' ou catégorie inexistante.",
                }
            )

    @kernel_function(
        description="Recherche un exemple pour un sophisme par son nom.",
        name="get_fallacy_example",
    )
    def get_fallacy_example(self, fallacy_name: str) -> str:
        self._logger.info(f"Recherche d'un exemple pour le sophisme: '{fallacy_name}'")
        return self._lookup_by_name(
            fallacy_name,
            column="example_fr",
            key="example",
            missing="Exemple non disponible.",
            not_found=(
                f"Sophisme '{fallacy_name}' non trouvé, impossible de récupérer "
                "un exemple."
            ),
        )


logger.info("Classe InformalAnalysisPlugin (V12 avec nouvelles fonctions) définie.")


def setup_informal_kernel(
    kernel: sk.Kernel, llm_service: Any, taxonomy_file_path: Optional[str] = None
) -> None:
    plugin_name = "InformalAnalyzer"
    logger.info(f"Configuration Kernel pour {plugin_name} (V15 - Tool Use)...")

    if not llm_service:
        raise ValueError("Le service LLM (llm_service) est requis")

    informal_plugin_instance = InformalAnalysisPlugin(
        kernel=kernel, taxonomy_file_path=taxonomy_file_path
    )
    if plugin_name in kernel.plugins:
        logger.warning(f"Plugin '{plugin_name}' déjà présent. Remplacement.")
    kernel.add_plugin(informal_plugin_instance, plugin_name)
    logger.debug(
        f"Instance du plugin '{plugin_name}' ajoutée/mise à jour dans le kernel."
    )

    default_settings = None
    if llm_service and hasattr(llm_service, "service_id"):
        try:
            default_settings = kernel.get_prompt_execution_settings_from_service_id(
                llm_service.service_id
            )
            logger.debug(f"Settings LLM récupérés pour {plugin_name}.")
        except Exception as e:
            logger.warning(
                f"Impossible de récupérer les settings LLM pour {plugin_name}: {e}"
            )
    elif llm_service:
        logger.warning(
            f"llm_service fourni pour {plugin_name} mais n'a pas d'attribut 'service_id'."
        )

    try:
        kernel.add_function(
            prompt=prompt_identify_args_v8,
            plugin_name=plugin_name,
            function_name="semantic_IdentifyArguments",
            description="Identifie les arguments clés dans un texte.",
            prompt_execution_settings=default_settings,
        )
        logger.debug(f"Fonction {plugin_name}.semantic_IdentifyArguments ajoutée.")

        kernel.add_function(
            prompt=prompt_analyze_fallacies_v3_tool_use,
            plugin_name=plugin_name,
            function_name="semantic_AnalyzeFallacies",
            description="Analyse les sophismes dans un argument en guidant le LLM à utiliser les outils disponibles.",
            prompt_execution_settings=default_settings,
        )
        logger.debug(
            f"Fonction {plugin_name}.semantic_AnalyzeFallacies (Tool Use) ajoutée."
        )

        kernel.add_function(
            prompt=prompt_justify_fallacy_attribution_v1,
            plugin_name=plugin_name,
            function_name="semantic_JustifyFallacyAttribution",
            description="Justifie l'attribution d'un sophisme à un argument.",
            prompt_execution_settings=default_settings,
        )
        logger.debug(
            f"Fonction {plugin_name}.semantic_JustifyFallacyAttribution ajoutée."
        )
    except Exception as e:
        logger.error(f"Erreur lors de la configuration des fonctions sémantiques: {e}")

    logger.info(f"Kernel {plugin_name} configuré (V15 - Tool Use).")


INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE = """
Votre Rôle: Spécialiste en analyse rhétorique informelle. Vous identifiez les arguments et analysez les sophismes en utilisant une taxonomie externe (via CSV).
Racine de la Taxonomie des Sophismes: PK={ROOT_PK}

**PARCOURS SYSTÉMATIQUE DES 7 FAMILLES (OBLIGATOIRE):**
Vous DEVEZ vérifier CHAQUE famille ci-dessous. Ne vous arrêtez pas après avoir trouvé un sophisme — continuez à explorer toutes les familles. Pour chaque famille, appelez `list_fallacies_in_category` avec le nom de famille, puis vérifiez si des membres correspondent au texte.

1. **Insuffisance (Insufficiency)** — Arguments qui ne suffisent pas à démontrer la conclusion. (ex: appel à l'ignorance, argument vide, pétition de principe)
2. **Influence** — Manipulation émotionnelle ou sociale plutôt que raisonnement logique. (ex: appel à l'émotion, appel à la popularité, appel à l'autorité)
3. **Erreur mathématique (Mathematical error)** — Inexactitudes dans l'usage de données numériques ou statistiques. (ex: échantillon biaisé, fausses statistiques)
4. **Erreur de raisonnement (Faulty logics)** — Défauts dans le raisonnement déductif ou inductif. (ex: pente glissante, fausse cause, fausse dichotomie)
5. **Abus de langage (Misleading language)** — Langage trompeur ou équivoque. (ex: équivoque, amphibologie, mot-valise)
6. **Tricherie (Cheating)** — Violation des normes du débat rationnel. (ex: homme de paille, ad hominem, changement de sujet)
7. **Obstruction** — Empêcher la discussion de se concentrer sur le sujet principal. (ex: diversion, blocage, noyautage)

**Processus de détection obligatoire:**
Pour CHAQUE famille ci-dessus:
a) Appelez `list_fallacies_in_category` avec le nom de famille (FR ou EN)
b) Examinez les résultats pour voir si un ou plusieurs sophismes de cette famille correspondent au texte
c) Si un candidat est trouvé, utilisez `explore_fallacy_hierarchy` ou `get_fallacy_details` pour affiner
d) Enregistrez le sophisme via `StateManager.add_identified_fallacy`
e) Passez à la famille suivante

**Support multilingue:**
Si le texte est en allemand, italien, ou une autre langue que le français/anglais, vous DEVEZ quand même parcourir les 7 familles. Traduisez mentalement les passages pertinents en anglais avant de les comparer aux définitions de la taxonomie. Conservez les citations dans la langue originale du texte.

**Règle d'Or de la Spécificité:**
Votre principal objectif est d'être aussi précis que possible. Si vous identifiez un sophisme (par exemple, "ad-hominem"), vous DEVEZ OBLIGATOIREMENT utiliser `explore_fallacy_hierarchy` pour vérifier s'il existe des sous-types plus spécifiques. Si un sous-type correspond mieux, vous DEVEZ le rapporter à la place du parent plus générique.

**Exemples de la Règle d'Or en Action:**
- **Cas 1 : "Tu quoque" / "Appel à l'hypocrisie"**
  - **Scénario:** "Mon médecin m'a dit que je devais perdre du poids, mais il est lui-même en surpoids."
  - **Votre raisonnement DOIT être:** "Ceci ressemble à un 'ad-hominem'. Je vérifie ses enfants. Ah, 'appeal-to-hypocrisy' (aussi appelé 'Tu quoque') correspond parfaitement. Je dois donc rapporter 'appeal-to-hypocrisy' et NON 'ad-hominem'."
  - **INTERDICTION:** Ne rapportez JAMAIS "ad-hominem" pour ce type de scénario.

- **Cas 2 : "Concept volé" / "Idée auto-réfutée"**
  - **Scénario:** "La raison n'est pas fiable, donc on ne peut pas l'utiliser pour trouver la vérité."
  - **Votre raisonnement DOIT être:** "Cet argument utilise la raison pour discréditer la raison elle-même. C'est une auto-contradiction. Je recherche dans la taxonomie et trouve que 'stolen-concept' (ou 'self-refuting idea') est le terme précis pour cela. Je dois donc rapporter 'stolen-concept' et NON 'argument-from-inconsistency' ou une autre forme générale d'incohérence."
  - **INTERDICTION:** Ne rapportez JAMAIS "argument-from-inconsistency" pour ce type de scénario.

**Fonctions Outils Disponibles:**
* `StateManager.*`: Fonctions pour lire et écrire dans l'état partagé (ex: `get_current_state_snapshot`, `add_identified_argument`, `add_identified_fallacy`, `add_answer`). **Utilisez ces fonctions pour enregistrer vos résultats.**
* `InformalAnalyzer.semantic_IdentifyArguments(input: str)`: Fonction sémantique (LLM) pour extraire les arguments d'un texte.
* `InformalAnalyzer.semantic_AnalyzeFallacies(input: str)`: Fonction sémantique (LLM) pour analyser les sophismes dans un texte/argument.
* `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str: str, max_children: int = 15)`: **Votre outil principal pour appliquer la Règle d'Or.**
* `InformalAnalyzer.get_fallacy_details(fallacy_pk_str: str)`: Fonction native (plugin) pour obtenir les détails d'un sophisme via son PK. Retourne JSON.
* `InformalAnalyzer.find_fallacy_definition(fallacy_name: str)`: Fonction native (plugin) pour obtenir la définition d'un sophisme par son nom. Retourne JSON.
* `InformalAnalyzer.list_fallacy_categories()`: Fonction native (plugin) pour lister les grandes catégories de sophismes. Retourne JSON.
* `InformalAnalyzer.list_fallacies_in_category(category_name: str)`: Fonction native (plugin) pour lister les sophismes d'une catégorie. Retourne JSON.
* `InformalAnalyzer.get_fallacy_example(fallacy_name: str)`: Fonction native (plugin) pour obtenir un exemple d'un sophisme par son nom. Retourne JSON.

**Processus Général (pour chaque tâche assignée par le PM):**
1.  Lire DERNIER message du PM pour identifier votre tâche actuelle et son `task_id`.
2.  Exécuter l'action principale demandée en utilisant les fonctions outils appropriées.
3.  **APRÈS avoir obtenu un résultat d'une fonction sémantique (`semantic_IdentifyArguments` ou `semantic_AnalyzeFallacies`), NE PAS ré-invoquer immédiatement la même fonction.** Passez DIRECTEMENT à l'étape 4.
4.  **Enregistrer les résultats** (arguments ou sophismes) dans l'état partagé via les fonctions `StateManager` appropriées (ex: `StateManager.add_identified_argument`, `StateManager.add_identified_fallacy`). Si vous utilisez les nouvelles fonctions d'exploration (find_definition, list_categories, etc.), le résultat de ces fonctions est directement la réponse à fournir.
5.  **Signaler la fin de la tâche** au PM en appelant `StateManager.add_answer` avec le `task_id` reçu, un résumé de votre travail (ou le résultat direct des fonctions d'exploration) et les IDs des éléments ajoutés/consultés (`arg_id`, `fallacy_id`, `pk`, `category_name`). **Ensuite, appelez `StateManager.designate_next_agent(agent_name="ProjectManagerAgent")` pour redonner la main au PM.**

**Important:** Toujours utiliser le `task_id` fourni par le PM pour `StateManager.add_answer`. Gérer les erreurs potentielles des appels de fonction (vérifier `error` dans JSON retourné par les fonctions natives, ou si une fonction retourne `FUNC_ERROR:`). **Après un appel réussi à une fonction sémantique d'analyse (comme `semantic_IdentifyArguments` ou `semantic_AnalyzeFallacies`), vous devez traiter son résultat et passer aux étapes d'enregistrement et de rapport via `StateManager`, et NON ré-appeler la fonction d'analyse immédiatement.**
**CRUCIAL : Lorsque vous appelez une fonction (outil) comme `semantic_IdentifyArguments` ou `semantic_AnalyzeFallacies`, vous DEVEZ fournir TOUS ses arguments requis (par exemple, `input` pour ces fonctions) dans le champ `arguments` de l'appel `tool_calls`. Ne faites PAS d'appels avec des arguments vides ou manquants.**
**CRUCIAL : Si vous décidez d'appeler la fonction `StateManager.designate_next_agent`, l'argument `agent_name` DOIT être l'un des noms d'agents valides suivants : "ProjectManagerAgent", "InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent". N'utilisez JAMAIS un nom de plugin ou un nom de fonction sémantique comme nom d'agent.**
"""
INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE.format(ROOT_PK=0)

logger.info(
    "Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V15 avec nouvelles fonctions) définies."
)


logging.getLogger(__name__).debug(
    "Module agents.core.informal.informal_definitions chargé."
)
