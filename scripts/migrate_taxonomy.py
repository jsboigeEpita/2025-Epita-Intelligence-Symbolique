# scripts/migrate_taxonomy.py
import pandas as pd
import json
import os
import numpy as np


def build_tree(df, parent_id=None):
    """Construit récursivement l'arbre à partir du DataFrame."""
    tree = []

    # Gère le cas où parent_id est None (éléments racines)
    if parent_id is None:
        children_df = df[df["Parent"].isnull()]
    else:
        children_df = df[df["Parent"] == parent_id]

    for _, row in children_df.iterrows():
        node = {
            "id": row["ID"],
            "name": row["Name"],
            "description": row["Description"],
            "children": build_tree(df, row["ID"]),
        }
        tree.append(node)
    return tree


def convert_csv_to_json(csv_path, json_path):
    """
    Convertit le fichier CSV de taxonomie en un fichier JSON hiérarchique.
    """
    # Charge le CSV, en s'assurant que 'path' est une chaîne de caractères
    df_raw = pd.read_csv(csv_path, dtype={"path": str})

    # Sélectionne et renomme les colonnes nécessaires
    df = df_raw[["PK", "path", "nom_vulgarisé", "desc_fr"]].copy()
    df.rename(
        columns={
            "PK": "ID",
            "path": "PathStr",
            "nom_vulgarisé": "Name",
            "desc_fr": "Description",
        },
        inplace=True,
    )

    # Remplace les NaN (par ex. dans les descriptions) par des chaînes vides
    df["Description"] = df["Description"].fillna("")
    df["Name"] = df["Name"].fillna("Sans nom")

    # Crée un mapping du PathStr vers l'ID pour une recherche rapide
    path_to_id_map = pd.Series(df.ID.values, index=df.PathStr).to_dict()

    def get_parent_id(path_str):
        """Dérive l'ID du parent à partir de la chaîne de chemin."""
        if not isinstance(path_str, str) or "." not in path_str:
            return None  # C'est un nœud de premier niveau
        parent_path = ".".join(path_str.split(".")[:-1])
        return path_to_id_map.get(parent_path)

    df["Parent"] = df["PathStr"].apply(get_parent_id)

    # Construction de la structure arborescente finale
    tree_data = {
        "id": "fallacy_root",
        "name": "Fallacy Taxonomy",
        "description": "Root of the fallacy taxonomy.",
        "children": build_tree(df),
    }

    # Sauvegarde la taxonomie hiérarchique en JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tree_data, f, indent=2, ensure_ascii=False)

    print(f"Taxonomy successfully converted to {json_path}")


if __name__ == "__main__":
    # Construit des chemins robustes indépendamment de l'endroit où le script est exécuté
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CSV_PATH = os.path.join(
        BASE_DIR, "argumentation_analysis", "data", "taxonomy_full.csv"
    )
    JSON_PATH = os.path.join(
        BASE_DIR, "argumentation_analysis", "data", "taxonomy_full.json"
    )

    print(f"Converting {CSV_PATH} to {JSON_PATH}...")
    convert_csv_to_json(CSV_PATH, JSON_PATH)
