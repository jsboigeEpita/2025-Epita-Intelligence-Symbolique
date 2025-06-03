#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Définitions et composants pour l'analyse informelle des arguments.

Ce module fournit :
- `InformalAnalysisPlugin`: Un plugin Semantic Kernel contenant des fonctions natives
  pour interagir avec une taxonomie de sophismes (chargée à partir d'un fichier CSV).
  Ces fonctions permettent d'explorer la hiérarchie des sophismes et d'obtenir
  des détails sur des sophismes spécifiques. Il inclut également des fonctions
  pour rechercher des définitions, lister des catégories, lister des sophismes
  par catégorie et obtenir des exemples.
- `setup_informal_kernel`: Une fonction utilitaire pour configurer une instance de
  kernel Semantic Kernel avec le `InformalAnalysisPlugin` et les fonctions
  sémantiques nécessaires à l'agent d'analyse informelle.
- `INFORMAL_AGENT_INSTRUCTIONS`: Instructions système détaillées pour guider
  le comportement d'un agent LLM spécialisé dans l'analyse informelle,
  décrivant son rôle, les outils disponibles et les processus à suivre pour
  différentes tâches.

Le module gère également le chargement et la validation de la taxonomie des
sophismes utilisée par le plugin.
"""

import os
import sys
import json
import logging
import pandas as pd
import requests
import semantic_kernel as sk
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import de l'utilitaire de lazy loading pour la taxonomie
# Ajout du chemin pour l'importation
utils_path = str(Path(__file__).parent.parent.parent.parent / "utils")
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)
from taxonomy_loader import get_taxonomy_path, validate_taxonomy_file

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("InformalDefinitions")

# Import des prompts
from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1 # Nettoyage des imports dupliqués

from argumentation_analysis.paths import DATA_DIR


# --- Classe InformalAnalysisPlugin (V12 avec nouvelles fonctions) ---
class InformalAnalysisPlugin:
    """
    Plugin Semantic Kernel pour l'analyse informelle des sophismes.

    Ce plugin fournit des fonctions natives pour interagir avec une taxonomie
    de sophismes, typiquement chargée à partir d'un fichier CSV. Il permet
    d'explorer la structure hiérarchique de la taxonomie et de récupérer
    des informations détaillées sur des sophismes spécifiques par leur
    identifiant (PK).
    Il inclut également des fonctions pour rechercher des définitions, lister
    des catégories, lister des sophismes par catégorie et obtenir des exemples.

    Attributes:
        _logger (logging.Logger): Logger pour ce plugin.
        FALLACY_CSV_URL (str): URL distante du fichier CSV de la taxonomie (fallback).
        DATA_DIR (Path): Chemin vers le répertoire de données local.
        FALLACY_CSV_LOCAL_PATH (Path): Chemin local attendu pour le fichier CSV de la taxonomie.
        _taxonomy_df_cache (Optional[pd.DataFrame]): Cache pour le DataFrame de la taxonomie.
    """
    
    def __init__(self):
        """
        Initialise le plugin `InformalAnalysisPlugin`.

        Configure les chemins pour la taxonomie des sophismes et initialise le cache
        du DataFrame à None. Le DataFrame sera chargé paresseusement lors du premier accès.
        """
        self._logger = logging.getLogger("InformalAnalysisPlugin")
        self._logger.info("Initialisation du plugin d'analyse des sophismes (V12 avec nouvelles fonctions)...")
        
        # Constantes pour le CSV - Utilisation du chemin fourni par l'utilitaire de lazy loading
        self.FALLACY_CSV_URL = "https://raw.githubusercontent.com/ArgumentumGames/Argumentum/master/Cards/Fallacies/Argumentum%20Fallacies%20-%20Taxonomy.csv"
        self.DATA_DIR = Path(__file__).parent.parent.parent.parent / DATA_DIR
        self.FALLACY_CSV_LOCAL_PATH = self.DATA_DIR / "argumentum_fallacies_taxonomy.csv"
        
        # Cache pour le DataFrame de taxonomie
        self._taxonomy_df_cache = None
    
    def _internal_load_and_prepare_dataframe(self) -> pd.DataFrame:
        """
        Charge et prépare le DataFrame de taxonomie des sophismes à partir d'un fichier CSV.

        Utilise `taxonomy_loader.get_taxonomy_path()` pour obtenir le chemin du fichier
        et `taxonomy_loader.validate_taxonomy_file()` pour le valider avant chargement.
        L'index du DataFrame est défini sur la colonne 'PK' et converti en entier.

        :return: Un DataFrame pandas contenant la taxonomie des sophismes.
        :rtype: pd.DataFrame
        :raises Exception: Si le fichier de taxonomie n'est pas valide ou si une erreur
                           survient pendant le chargement ou la préparation.
        """
        self._logger.info("Chargement et préparation du DataFrame de taxonomie...")
        
        try:
            # Utiliser l'utilitaire de lazy loading pour obtenir le chemin du fichier
            taxonomy_path = get_taxonomy_path()
            self._logger.info(f"Fichier de taxonomie obtenu via lazy loading: {taxonomy_path}")
            
            # Vérifier que le fichier est valide
            if not validate_taxonomy_file():
                self._logger.error("Le fichier de taxonomie n'est pas valide")
                raise Exception("Le fichier de taxonomie n'est pas valide")
        
            # Charger le fichier CSV
            df = pd.read_csv(taxonomy_path, encoding='utf-8')
            self._logger.info(f"Taxonomie chargée avec succès: {len(df)} sophismes.")
            
            # Préparation du DataFrame
            if 'PK' in df.columns:
                df.set_index('PK', inplace=True)
                # S'assurer que l'index est de type entier, surtout pour les tests avec use_real_numpy
                if not pd.api.types.is_integer_dtype(df.index):
                    try:
                        # Tenter de convertir l'index en entier.
                        # Si l'index contient des valeurs non convertibles (ex: NaN, chaînes non numériques),
                        # cela pourrait échouer ou changer les valeurs. Pour le CSV de test, cela devrait être sûr.
                        df.index = pd.to_numeric(df.index, errors='coerce').fillna(0).astype(int)
                        self._logger.info("Index de la taxonomie converti en type entier après set_index.")
                    except Exception as e_astype:
                        self._logger.warning(f"Impossible de convertir l'index de la taxonomie en entier après set_index: {e_astype}")
            
            return df
        except Exception as e:
            self._logger.error(f"Erreur lors du chargement de la taxonomie: {e}")
            raise
    
    def _get_taxonomy_dataframe(self) -> pd.DataFrame:
        """
        Récupère le DataFrame de taxonomie des sophismes, en utilisant un cache interne.

        Si le DataFrame n'est pas déjà en cache (`self._taxonomy_df_cache`),
        il est chargé et préparé via `_internal_load_and_prepare_dataframe`.

        :return: Le DataFrame pandas de la taxonomie des sophismes.
        :rtype: pd.DataFrame
        """
        if self._taxonomy_df_cache is None:
            self._taxonomy_df_cache = self._internal_load_and_prepare_dataframe()
        return self._taxonomy_df_cache.copy() # Retourner une copie pour éviter les modifications accidentelles du cache
    
    def _internal_explore_hierarchy(self, current_pk: int, df: pd.DataFrame, max_children: int = 15) -> Dict[str, Any]:
        """
        Explore la hiérarchie des sophismes à partir d'un nœud parent donné (par sa PK).

        Construit un dictionnaire représentant le nœud courant et ses enfants directs,
        en se basant sur les colonnes 'FK_Parent', 'parent_pk', ou 'path' du DataFrame.

        :param current_pk: La clé primaire (PK) du nœud parent à partir duquel explorer.
        :type current_pk: int
        :param df: Le DataFrame pandas de la taxonomie des sophismes.
        :type df: pd.DataFrame
        :param max_children: Le nombre maximum d'enfants directs à retourner.
        :type max_children: int
        :return: Un dictionnaire contenant les informations du nœud courant (`current_node`),
                 une liste de ses enfants (`children`), et un champ `error` si un problème survient.
        :rtype: Dict[str, Any]
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
        if 'depth' in df.columns:
            df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
        
        # Trouver le nœud courant
        current_node_df = df.loc[[current_pk]] if current_pk in df.index else pd.DataFrame()
        if len(current_node_df) == 0:
            result["error"] = f"PK {current_pk} non trouvée dans la taxonomie."
            return result
        
        # Extraire les informations du nœud courant
        current_row = current_node_df.iloc[0]
        # Utiliser une valeur par défaut pour path si elle n'existe pas
        current_path = current_row.get('path', '') if hasattr(current_row, 'get') else ''
        
        result["current_node"] = {
            "pk": int(current_row.name),
            "path": current_path,
            "depth": int(current_row['depth']) if pd.notna(current_row.get('depth')) else 0,
            "nom_vulgarisé": current_row.get('nom_vulgarisé', ''),
            "text_fr": current_row.get('text_fr', ''),
            "text_en": current_row.get('text_en', '')
        }
        
        # Trouver les enfants
        children_df = pd.DataFrame() # Initialiser à un DataFrame vide
        if 'FK_Parent' in df.columns:
            # Si FK_Parent existe, l'utiliser pour trouver les enfants
            children_df = df[df['FK_Parent'] == current_pk]
        elif 'parent_pk' in df.columns:
            # Si parent_pk existe, l'utiliser pour trouver les enfants
            children_df = df[df['parent_pk'] == current_pk]
        elif 'path' in df.columns and current_path:
            # Si path existe, l'utiliser pour trouver les enfants
            # S'assurer que current_path se termine par un point pour éviter les correspondances partielles incorrectes
            # Exemple: si current_path est "1", on ne veut pas matcher "10.x"
            # On cherche les enfants directs, donc le path de l'enfant doit être current_path + ".quelquechose"
            # et ne pas contenir d'autres points après "quelquechose".
            # Exemple: si current_path = "1", on cherche "1.X" mais pas "1.X.Y"
            # Si current_path = "1.2", on cherche "1.2.X" mais pas "1.2.X.Y"
            
            # Construire le préfixe attendu pour les enfants directs
            child_path_prefix = str(current_path) + "."
            
            # Filtrer les enfants qui commencent par ce préfixe
            potential_children = df[df['path'].astype(str).str.startswith(child_path_prefix, na=False)]
            
            # Filtrer pour ne garder que les enfants directs (pas les petits-enfants, etc.)
            # Un enfant direct aura un path qui, une fois le préfixe retiré, ne contient plus de "."
            children_df = potential_children[~potential_children['path'].astype(str).str.slice(start=len(child_path_prefix)).str.contains('.', na=False, regex=False)]

        elif 'depth' in df.columns and pd.notna(current_row.get('depth')):
             # Si depth existe et que le nœud courant a une profondeur,
             # les enfants directs auront une profondeur de current_depth + 1
             # et leur path commencera par le path du parent.
            current_depth = int(current_row['depth'])
            # S'assurer que current_path est une chaîne pour la comparaison str.startswith
            current_path_str = str(current_path) if pd.notna(current_path) else ""

            # Filtrer par profondeur et par le début du path
            # (pour éviter de prendre des nœuds d'une autre branche ayant la même profondeur)
            children_df = df[
                (df['depth'] == current_depth + 1) &
                (df['path'].astype(str).str.startswith(current_path_str + ('.' if current_path_str else ''), na=False))
            ]
        
        children_count = len(children_df)
        
        if children_count > 0:
            # Limiter le nombre d'enfants si nécessaire
            if max_children > 0 and children_count > max_children:
                children_df = children_df.head(max_children)
                result["children_truncated"] = True
                result["total_children"] = children_count
            
            # Extraire les informations des enfants
            for _, child_row in children_df.iterrows():
                # Vérifier si l'enfant a lui-même des enfants
                # (simplifié, une vérification plus robuste serait nécessaire pour une UI complexe)
                # Pour cette fonction, on peut se baser sur la présence d'enfants dans le dataframe
                # en utilisant une logique similaire à celle ci-dessus.
                # Pour l'instant, on met False, car le but est de lister les enfants directs.
                child_info = {
                    "pk": int(child_row.name), # .name est l'index (PK)
                    "nom_vulgarisé": child_row.get('nom_vulgarisé', ''),
                    "text_fr": child_row.get('text_fr', ''),
                    "has_children": False # Simplifié. Pourrait être calculé si besoin.
                }
                result["children"].append(child_info)
        
        return result
    
    def _internal_get_children_details(self, pk: int, df: pd.DataFrame, max_children: int = 10) -> List[Dict[str, Any]]:
        """
        Obtient les détails (PK, nom, description, exemple) des enfants directs d'un nœud spécifique.

        :param pk: La clé primaire (PK) du nœud parent.
        :type pk: int
        :param df: Le DataFrame pandas de la taxonomie des sophismes.
        :type df: pd.DataFrame
        :param max_children: Le nombre maximum d'enfants à retourner.
        :type max_children: int
        :return: Une liste de dictionnaires, chaque dictionnaire représentant un enfant
                 avec ses détails. Retourne une liste vide si le DataFrame est None
                 ou si aucun enfant n'est trouvé.
        :rtype: List[Dict[str, Any]]
        """
        children_details_list = [] # Renommé pour éviter conflit avec variable 'children'
        
        if df is None:
            return children_details_list
        
        # Convertir les colonnes numériques si elles existent et ne sont pas déjà numériques
        if 'PK' in df.columns and not pd.api.types.is_numeric_dtype(df['PK']):
            df['PK'] = pd.to_numeric(df['PK'], errors='coerce')
        if 'FK_Parent' in df.columns and not pd.api.types.is_numeric_dtype(df['FK_Parent']):
            df['FK_Parent'] = pd.to_numeric(df['FK_Parent'], errors='coerce')
        
        # Trouver les enfants (nœuds dont le parent est le nœud courant)
        child_nodes_df = pd.DataFrame() # Initialiser
        if 'FK_Parent' in df.columns:
            child_nodes_df = df[df['FK_Parent'] == pk]
        elif 'parent_pk' in df.columns: # Fallback si FK_Parent n'existe pas
            child_nodes_df = df[df['parent_pk'] == pk]
        # Ajouter une logique basée sur 'path' et 'depth' si nécessaire, comme dans _internal_explore_hierarchy
        
        # Limiter le nombre d'enfants si nécessaire
        if max_children > 0 and len(child_nodes_df) > max_children:
            child_nodes_df = child_nodes_df.head(max_children)
        
        # Extraire les informations des enfants
        for _, child_row in child_nodes_df.iterrows():
            child_info = {
                "pk": int(child_row.name), # .name est l'index (PK)
                "text_fr": child_row.get('text_fr', ''),
                "nom_vulgarisé": child_row.get('nom_vulgarisé', ''),
                "description_fr": child_row.get('desc_fr', ''), # Utilisation de desc_fr
                "exemple_fr": child_row.get('example_fr', ''), # Utilisation de example_fr
                "error": None
            }
            children_details_list.append(child_info)
        
        return children_details_list
    
    def _internal_get_node_details(self, pk: int, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Obtient les détails complets d'un nœud spécifique de la taxonomie,
        y compris les informations sur son parent et ses enfants directs.

        :param pk: La clé primaire (PK) du nœud dont les détails sont demandés.
        :type pk: int
        :param df: Le DataFrame pandas de la taxonomie des sophismes.
        :type df: pd.DataFrame
        :return: Un dictionnaire contenant tous les attributs du nœud, ainsi que
                 des informations sur son parent et ses enfants. Contient un champ `error`
                 si le nœud n'est pas trouvé ou si la taxonomie n'est pas disponible.
        :rtype: Dict[str, Any]
        """
        result = {
            "pk": pk,
            "error": None
        }
        
        if df is None:
            result["error"] = "Taxonomie sophismes non disponible."
            return result
        
        # Convertir les colonnes numériques si elles existent et ne sont pas déjà numériques
        if 'PK' in df.columns and not pd.api.types.is_numeric_dtype(df['PK']):
            df['PK'] = pd.to_numeric(df['PK'], errors='coerce')
        if 'depth' in df.columns and not pd.api.types.is_numeric_dtype(df['depth']):
            df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
        
        # Trouver le nœud
        node_df = df.loc[[pk]] if pk in df.index else pd.DataFrame()
        if len(node_df) == 0:
            result["error"] = f"PK {pk} non trouvée dans la taxonomie."
            return result
        # Extraire les informations du nœud
        row = node_df.iloc[0]
        for col in row.index: # Utiliser row.index qui contient les noms des colonnes
            if pd.notna(row[col]):
                # Gérer la conversion pour numpy types si nécessaire pour la sérialisation JSON
                if hasattr(row[col], 'item'): # Typique pour les types numpy (int64, float64, etc.)
                    result[col] = row[col].item()
                else:
                    result[col] = row[col]
        
        # Trouver le parent
        parent_df = pd.DataFrame() # Initialiser
        parent_pk_val = None
        if 'FK_Parent' in df.columns and pd.notna(row.get('FK_Parent')):
            parent_pk_val = row.get('FK_Parent')
        elif 'parent_pk' in df.columns and pd.notna(row.get('parent_pk')): # Fallback
            parent_pk_val = row.get('parent_pk')
        
        if parent_pk_val is not None:
            try:
                parent_pk_int = int(parent_pk_val)
                parent_df = df.loc[[parent_pk_int]] if parent_pk_int in df.index else pd.DataFrame()
            except ValueError:
                self._logger.warning(f"Valeur FK_Parent/parent_pk non entière pour le nœud {pk}: {parent_pk_val}")

        elif 'path' in df.columns:
            # Sinon, essayer d'utiliser path
            path_val = row.get('path', '')
            if path_val and '.' in str(path_val): # S'assurer que path_val est une chaîne
                parent_path = str(path_val).rsplit('.', 1)[0]
                parent_df = df[df['path'] == parent_path]
        
        if len(parent_df) > 0:
            parent_row = parent_df.iloc[0]
            result["parent"] = {
                "pk": int(parent_row.name), # .name est l'index (PK)
                "nom_vulgarisé": parent_row.get('nom_vulgarisé', ''),
                "text_fr": parent_row.get('text_fr', '')
            }
        
        # Trouver les enfants (logique similaire à _internal_explore_hierarchy)
        # children_list = [] # Renommé pour éviter conflit
        # Pour être plus précis, on reprend la logique de _internal_explore_hierarchy pour les enfants directs
        
        child_nodes_for_details = pd.DataFrame()
        current_path_for_children = row.get('path', '')
        current_depth_for_children = row.get('depth', None)
        
        if 'FK_Parent' in df.columns:
            child_nodes_for_details = df[df['FK_Parent'] == pk]
        elif 'parent_pk' in df.columns:
            child_nodes_for_details = df[df['parent_pk'] == pk]
        elif 'path' in df.columns and current_path_for_children:
            child_path_prefix = str(current_path_for_children) + "."
            potential_children = df[df['path'].astype(str).str.startswith(child_path_prefix, na=False)]
            child_nodes_for_details = potential_children[~potential_children['path'].astype(str).str.slice(start=len(child_path_prefix)).str.contains('.', na=False, regex=False)]
        elif 'depth' in df.columns and pd.notna(current_depth_for_children):
            current_path_str_for_children = str(current_path_for_children) if pd.notna(current_path_for_children) else ""
            child_nodes_for_details = df[
                (df['depth'] == int(current_depth_for_children) + 1) &
                (df['path'].astype(str).str.startswith(current_path_str_for_children + ('.' if current_path_str_for_children else ''), na=False))
            ]

        if len(child_nodes_for_details) > 0:
            result["children"] = []
            for _, child_row_detail in child_nodes_for_details.iterrows():
                child_info_detail = {
                    "pk": int(child_row_detail.name),
                    "nom_vulgarisé": child_row_detail.get('nom_vulgarisé', ''),
                    "text_fr": child_row_detail.get('text_fr', '')
                }
                result["children"].append(child_info_detail)
        
        return result
    
    def explore_fallacy_hierarchy(self, current_pk_str: str, max_children: int = 15) -> str:
        """
        Explore la hiérarchie des sophismes à partir d'un nœud donné (par sa PK en chaîne).

        Wrapper autour de `_internal_explore_hierarchy` qui gère la conversion de `current_pk_str`
        en entier et la sérialisation du résultat en JSON.

        :param current_pk_str: La clé primaire (PK) du nœud à explorer, fournie en tant que chaîne.
        :type current_pk_str: str
        :param max_children: Le nombre maximum d'enfants directs à retourner.
        :type max_children: int
        :return: Une chaîne JSON représentant le nœud courant et ses enfants,
                 ou un JSON d'erreur en cas de problème.
        :rtype: str
        """
        self._logger.info(f"Exploration hiérarchie sophismes depuis PK {current_pk_str}...")
        
        try:
            current_pk = int(current_pk_str)
        except ValueError:
            self._logger.error(f"PK invalide: {current_pk_str}")
            return json.dumps({"error": f"PK invalide: {current_pk_str}"})
        
        df = self._get_taxonomy_dataframe()
        if df is None: # Vérifier si df est None après l'appel
            self._logger.error("Taxonomie sophismes non disponible (DataFrame est None).")
            return json.dumps({"error": "Taxonomie sophismes non disponible."})
        
        result = self._internal_explore_hierarchy(current_pk, df, max_children)
        if result.get("error"):
            self._logger.warning(f" -> Erreur exploration PK {current_pk}: {result['error']}")
        else:
            self._logger.info(f" -> Hiérarchie explorée depuis PK {current_pk}: {len(result.get('children', []))} enfants.")
        
        try:
            return json.dumps(result, indent=2, ensure_ascii=False, default=str) # Ajout de default=str pour types numpy
        except Exception as e_json:
            self._logger.error(f"Erreur sérialisation JSON hiérarchie PK {current_pk}: {e_json}")
            result_error = {"error": f"Erreur sérialisation JSON: {str(e_json)}", "current_pk": current_pk}
            return json.dumps(result_error)
    
    def get_fallacy_details(self, fallacy_pk_str: str) -> str:
        """
        Obtient les détails d'un sophisme spécifique par sa PK (fournie en chaîne).

        Wrapper autour de `_internal_get_node_details` qui gère la conversion de `fallacy_pk_str`
        en entier et la sérialisation du résultat en JSON.

        :param fallacy_pk_str: La clé primaire (PK) du sophisme, fournie en tant que chaîne.
        :type fallacy_pk_str: str
        :return: Une chaîne JSON contenant les détails du sophisme,
                 ou un JSON d'erreur en cas de problème.
        :rtype: str
        """
        self._logger.info(f"Récupération détails sophisme PK {fallacy_pk_str}...")
        
        result_error = {"error": None} # Initialiser avec une clé "error"
        
        try:
            fallacy_pk = int(fallacy_pk_str)
        except ValueError:
            self._logger.error(f"PK invalide: {fallacy_pk_str}")
            result_error["error"] = f"PK invalide: {fallacy_pk_str}"
            return json.dumps(result_error)
        
        df = self._get_taxonomy_dataframe()
        if df is None: # Vérifier si df est None
            self._logger.error("Taxonomie sophismes non disponible (DataFrame est None).")
            return json.dumps({"pk_requested": fallacy_pk, "error": "Taxonomie sophismes non disponible."})
        
        details = self._internal_get_node_details(fallacy_pk, df)
        if details.get("error"):
             self._logger.warning(f" -> Erreur récupération détails PK {fallacy_pk}: {details['error']}")
        else:
             self._logger.info(f" -> Détails récupérés pour PK {fallacy_pk}.")
        try:
            return json.dumps(details, indent=2, ensure_ascii=False, default=str) # Ajout de default=str
        except Exception as e_json:
            self._logger.error(f"Erreur sérialisation JSON détails PK {fallacy_pk}: {e_json}")
            result_error["error"] = f"Erreur sérialisation JSON: {str(e_json)}"
            result_error["pk_requested"] = fallacy_pk
            return json.dumps(result_error)

    # --- Nouvelles méthodes pour l'exploration de la taxonomie ---

    def find_fallacy_definition(self, fallacy_name: str) -> str:
        """
        Recherche la définition d'un sophisme par son nom.

        :param fallacy_name: Le nom du sophisme à rechercher (cas insensible).
        :type fallacy_name: str
        :return: Une chaîne JSON contenant la définition trouvée ou un message d'erreur.
        :rtype: str
        """
        self._logger.info(f"Recherche de la définition pour le sophisme: '{fallacy_name}'")
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"error": "Taxonomie non disponible."})

        # Recherche cas insensible dans 'nom_vulgarisé' et 'text_fr'
        # S'assurer que les colonnes existent et que les valeurs ne sont pas NaN avant d'appliquer .str
        condition_nom = pd.Series(False, index=df.index)
        if 'nom_vulgarisé' in df.columns:
            condition_nom = df['nom_vulgarisé'].fillna('').astype(str).str.contains(fallacy_name, case=False, na=False)
        
        condition_text_fr = pd.Series(False, index=df.index)
        if 'text_fr' in df.columns:
            condition_text_fr = df['text_fr'].fillna('').astype(str).str.contains(fallacy_name, case=False, na=False)
            
        found_fallacy = df[condition_nom | condition_text_fr]

        if not found_fallacy.empty:
            # Prendre la première occurrence si plusieurs
            definition = found_fallacy.iloc[0].get('desc_fr', "Définition non disponible.")
            pk_found = found_fallacy.iloc[0].name # PK est l'index
            self._logger.info(f"Définition trouvée pour '{fallacy_name}' (PK: {pk_found}).")
            return json.dumps({"fallacy_name": fallacy_name, "pk": int(pk_found), "definition_fr": definition}, default=str)
        else:
            self._logger.warning(f"Aucune définition trouvée pour '{fallacy_name}'.")
            return json.dumps({"error": f"Définition non trouvée pour '{fallacy_name}'."})

    def list_fallacy_categories(self) -> str:
        """
        Liste les grandes catégories de sophismes (basées sur la colonne 'Famille').

        :return: Une chaîne JSON contenant la liste des catégories ou un message d'erreur.
        :rtype: str
        """
        self._logger.info("Listage des catégories de sophismes...")
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"error": "Taxonomie non disponible."})

        if 'Famille' in df.columns:
            categories = df['Famille'].dropna().unique().tolist()
            self._logger.info(f"{len(categories)} catégories trouvées.")
            return json.dumps({"categories": categories}, default=str)
        else:
            self._logger.warning("Colonne 'Famille' non trouvée dans la taxonomie.")
            return json.dumps({"error": "Colonne 'Famille' pour les catégories non trouvée."})

    def list_fallacies_in_category(self, category_name: str) -> str:
        """
        Liste les sophismes appartenant à une catégorie donnée.

        :param category_name: Le nom de la catégorie à filtrer (cas sensible, basé sur 'Famille').
        :type category_name: str
        :return: Une chaîne JSON contenant la liste des sophismes (nom et PK)
                 dans la catégorie ou un message d'erreur.
        :rtype: str
        """
        self._logger.info(f"Listage des sophismes dans la catégorie: '{category_name}'")
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"error": "Taxonomie non disponible."})

        if 'Famille' not in df.columns:
            return json.dumps({"error": "Colonne 'Famille' pour les catégories non trouvée."})

        # Filtrer par catégorie (cas sensible pour correspondre aux valeurs exactes de 'Famille')
        fallacies_in_cat_df = df[df['Famille'] == category_name]

        if not fallacies_in_cat_df.empty:
            result_list = []
            for index, row in fallacies_in_cat_df.iterrows():
                result_list.append({
                    "pk": int(index), # index est la PK
                    "nom_vulgarisé": row.get('nom_vulgarisé', row.get('text_fr', 'Nom non disponible'))
                })
            self._logger.info(f"{len(result_list)} sophismes trouvés dans la catégorie '{category_name}'.")
            return json.dumps({"category": category_name, "fallacies": result_list}, default=str)
        else:
            self._logger.warning(f"Aucun sophisme trouvé pour la catégorie '{category_name}' ou catégorie inexistante.")
            return json.dumps({"error": f"Aucun sophisme trouvé pour la catégorie '{category_name}' ou catégorie inexistante."})

    def get_fallacy_example(self, fallacy_name: str) -> str:
        """
        Recherche un exemple pour un sophisme par son nom.

        :param fallacy_name: Le nom du sophisme à rechercher (cas insensible).
        :type fallacy_name: str
        :return: Une chaîne JSON contenant l'exemple trouvé ou un message d'erreur.
        :rtype: str
        """
        self._logger.info(f"Recherche d'un exemple pour le sophisme: '{fallacy_name}'")
        df = self._get_taxonomy_dataframe()
        if df is None:
            return json.dumps({"error": "Taxonomie non disponible."})

        condition_nom = pd.Series(False, index=df.index)
        if 'nom_vulgarisé' in df.columns:
            condition_nom = df['nom_vulgarisé'].fillna('').astype(str).str.contains(fallacy_name, case=False, na=False)
        
        condition_text_fr = pd.Series(False, index=df.index)
        if 'text_fr' in df.columns:
            condition_text_fr = df['text_fr'].fillna('').astype(str).str.contains(fallacy_name, case=False, na=False)
            
        found_fallacy = df[condition_nom | condition_text_fr]

        if not found_fallacy.empty:
            example = found_fallacy.iloc[0].get('example_fr', "Exemple non disponible.")
            pk_found = found_fallacy.iloc[0].name
            self._logger.info(f"Exemple trouvé pour '{fallacy_name}' (PK: {pk_found}).")
            return json.dumps({"fallacy_name": fallacy_name, "pk": int(pk_found), "example_fr": example}, default=str)
        else:
            self._logger.warning(f"Aucun exemple trouvé pour '{fallacy_name}'.")
            return json.dumps({"error": f"Exemple non trouvé pour '{fallacy_name}'."})

logger.info("Classe InformalAnalysisPlugin (V12 avec nouvelles fonctions) définie.")

# --- Fonction setup_informal_kernel (V13 - Simplifiée avec nouvelles fonctions) ---
def setup_informal_kernel(kernel: sk.Kernel, llm_service: Any) -> None:
    """
    Configure une instance de `semantic_kernel.Kernel` pour l'analyse informelle.

    Cette fonction enregistre `InformalAnalysisPlugin` (contenant des fonctions natives
    pour la taxonomie des sophismes) et plusieurs fonctions sémantiques (définies
    dans `.prompts`) dans le kernel fourni. Ces fonctions permettent d'identifier
    des arguments, d'analyser des sophismes et de justifier leur attribution.

    Le nom du plugin utilisé pour enregistrer à la fois le plugin natif et les
    fonctions sémantiques est "InformalAnalyzer".

    :param kernel: L'instance du `semantic_kernel.Kernel` à configurer.
    :type kernel: sk.Kernel
    :param llm_service: L'instance du service LLM (par exemple, une classe compatible
                        avec `OpenAIChatCompletion` de Semantic Kernel) qui sera utilisée
                        par les fonctions sémantiques. Doit avoir un attribut `service_id`.
    :type llm_service: Any
    :raises Exception: Peut propager des exceptions si l'enregistrement des fonctions
                       sémantiques échoue de manière critique (bien que certaines erreurs
                       soient actuellement logguées comme des avertissements).
    """
    plugin_name = "InformalAnalyzer"
    logger.info(f"Configuration Kernel pour {plugin_name} (V13 - Plugin autonome avec nouvelles fonctions)...")

    informal_plugin_instance = InformalAnalysisPlugin()

    if plugin_name in kernel.plugins:
        logger.warning(f"Plugin '{plugin_name}' déjà présent. Remplacement.")
    kernel.add_plugin(informal_plugin_instance, plugin_name)
    logger.debug(f"Instance du plugin '{plugin_name}' ajoutée/mise à jour dans le kernel.")

    default_settings = None
    if llm_service and hasattr(llm_service, 'service_id'): # Vérifier si llm_service et service_id existent
        try:
            default_settings = kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
            logger.debug(f"Settings LLM récupérés pour {plugin_name}.")
        except Exception as e:
            logger.warning(f"Impossible de récupérer les settings LLM pour {plugin_name}: {e}")
    elif llm_service:
        logger.warning(f"llm_service fourni pour {plugin_name} mais n'a pas d'attribut 'service_id'.")


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
    except Exception as e:
        logger.error(f"Erreur lors de la configuration des fonctions sémantiques: {e}")

    # Les fonctions natives sont automatiquement enregistrées lors de l'ajout du plugin
    # Vérifions simplement qu'elles sont bien présentes
    native_facades = [
        "explore_fallacy_hierarchy", "get_fallacy_details",
        "find_fallacy_definition", "list_fallacy_categories",
        "list_fallacies_in_category", "get_fallacy_example"
    ]
    if plugin_name in kernel.plugins:
        for func_name in native_facades:
            if hasattr(informal_plugin_instance, func_name):
                logger.debug(f"Fonction native {plugin_name}.{func_name} disponible dans l'instance.")
            else:
                logger.error(f"ERREUR CRITIQUE: Fonction {func_name} non trouvée dans l'instance du plugin!")
    else:
        logger.error(f"ERREUR CRITIQUE: Plugin {plugin_name} non trouvé après ajout!")
         
    logger.info(f"Kernel {plugin_name} configuré (V13 avec nouvelles fonctions natives).")

# --- Instructions Système ---
# (Provenant de la cellule [ID: 35fbe045] du notebook 'Argument_Analysis_Agentic-1-informal_agent.ipynb')
# Mise à jour pour inclure les nouvelles fonctions
INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE = """
Votre Rôle: Spécialiste en analyse rhétorique informelle. Vous identifiez les arguments et analysez les sophismes en utilisant une taxonomie externe (via CSV).
Racine de la Taxonomie des Sophismes: PK={ROOT_PK}

**Fonctions Outils Disponibles:**
* `StateManager.*`: Fonctions pour lire et écrire dans l'état partagé (ex: `get_current_state_snapshot`, `add_identified_argument`, `add_identified_fallacy`, `add_answer`). **Utilisez ces fonctions pour enregistrer vos résultats.**
* `InformalAnalyzer.semantic_IdentifyArguments(input: str)`: Fonction sémantique (LLM) pour extraire les arguments d'un texte.
* `InformalAnalyzer.semantic_AnalyzeFallacies(input: str)`: Fonction sémantique (LLM) pour analyser les sophismes dans un texte/argument.
* `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str: str, max_children: int = 15)`: Fonction native (plugin) pour explorer la taxonomie CSV. Retourne JSON avec nœud courant et enfants.
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

**Exemples de Tâches Spécifiques (Mise à jour):**

* **Tâche "Identifier les arguments":**
    1.  Récupérer le texte brut (`raw_text`) depuis l'état.
    2.  Appeler `InformalAnalyzer.semantic_IdentifyArguments(input=raw_text)`.
    3.  Pour chaque argument trouvé, appeler `StateManager.add_identified_argument`. Collecter `arg_ids`.
    4.  Appeler `StateManager.add_answer` (résumé, `arg_ids`). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Explorer taxonomie [depuis PK]":**
    1.  Déterminer PK de départ.
    2.  Appeler `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str="[PK]")`.
    3.  Analyser JSON. Formuler réponse textuelle (nœud, enfants, actions possibles).
    4.  Appeler `StateManager.add_answer` (réponse, PK exploré). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Obtenir détails sophisme [PK]":**
    1.  Appeler `InformalAnalyzer.get_fallacy_details(fallacy_pk_str="[PK]")`.
    2.  Analyser JSON. Formuler réponse textuelle (détails).
    3.  Appeler `StateManager.add_answer` (détails formatés, PK). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Trouver définition sophisme [nom]":**
    1.  Appeler `InformalAnalyzer.find_fallacy_definition(fallacy_name="[nom du sophisme]")`.
    2.  Analyser JSON. Extraire la définition.
    3.  Appeler `StateManager.add_answer` (définition trouvée ou message d'erreur, nom du sophisme). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Lister catégories sophismes":**
    1.  Appeler `InformalAnalyzer.list_fallacy_categories()`.
    2.  Analyser JSON. Extraire la liste des catégories.
    3.  Appeler `StateManager.add_answer` (liste des catégories ou message d'erreur). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Lister sophismes dans catégorie [nom_catégorie]":**
    1.  Appeler `InformalAnalyzer.list_fallacies_in_category(category_name="[nom_catégorie]")`.
    2.  Analyser JSON. Extraire la liste des sophismes (nom, PK).
    3.  Appeler `StateManager.add_answer` (liste des sophismes ou message d'erreur, nom de la catégorie). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Obtenir exemple sophisme [nom]":**
    1.  Appeler `InformalAnalyzer.get_fallacy_example(fallacy_name="[nom du sophisme]")`.
    2.  Analyser JSON. Extraire l'exemple.
    3.  Appeler `StateManager.add_answer` (exemple trouvé ou message d'erreur, nom du sophisme). **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Attribuer sophisme [PK] à argument [arg_id]":**
    1.  Utiliser `get_fallacy_details` ou `find_fallacy_definition` pour obtenir label et description.
    2.  Rédiger justification détaillée.
    3.  Appeler `StateManager.add_identified_fallacy`. Noter `fallacy_id`.
    4.  Appeler `StateManager.add_answer`. **Puis, désignez "ProjectManagerAgent".**

* **Tâche "Analyser sophismes dans argument [arg_id]" (ou texte général):**
    1.  Récupérer texte.
    2.  Récupérer `task_id`.
    3.  Appeler `InformalAnalyzer.semantic_AnalyzeFallacies(input=[texte])`.
    4.  Appeler `StateManager.add_answer` avec la réponse TEXTUELLE COMPLÈTE de `semantic_AnalyzeFallacies`.
    5.  Appeler `StateManager.designate_next_agent(agent_name="ProjectManagerAgent")`.

* **Si Tâche Inconnue/Pas Claire:** Signaler via `StateManager.add_answer`. **Puis, désignez "ProjectManagerAgent".**

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

**Important:** Toujours utiliser le `task_id` fourni par le PM pour `StateManager.add_answer`. Gérer les erreurs potentielles des appels de fonction (vérifier `error` dans JSON retourné par les fonctions natives, ou si une fonction retourne `FUNC_ERROR:`). **Après un appel réussi à une fonction sémantique d'analyse (comme `semantic_IdentifyArguments` ou `semantic_AnalyzeFallacies`), vous devez traiter son résultat et passer aux étapes d'enregistrement et de rapport via `StateManager`, et NON ré-appeler la fonction d'analyse immédiatement.**
**CRUCIAL : Lorsque vous appelez une fonction (outil) comme `semantic_IdentifyArguments` ou `semantic_AnalyzeFallacies`, vous DEVEZ fournir TOUS ses arguments requis (par exemple, `input` pour ces fonctions) dans le champ `arguments` de l'appel `tool_calls`. Ne faites PAS d'appels avec des arguments vides ou manquants.**
**CRUCIAL : Si vous décidez d'appeler la fonction `StateManager.designate_next_agent`, l'argument `agent_name` DOIT être l'un des noms d'agents valides suivants : "ProjectManagerAgent", "InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent". N'utilisez JAMAIS un nom de plugin ou un nom de fonction sémantique comme nom d'agent.**
"""
INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE.format(ROOT_PK=0)
"""
Instructions système finales pour l'agent d'analyse informelle.
Formatées à partir de `INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE` avec `ROOT_PK` défini à 0.
"""

logger.info("Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V15 avec nouvelles fonctions) définies.")

# Log de chargement
logging.getLogger(__name__).debug("Module agents.core.informal.informal_definitions chargé.")