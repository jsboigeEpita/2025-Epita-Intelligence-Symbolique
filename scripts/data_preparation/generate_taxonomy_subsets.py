import os
import pandas as pd
import sys
from pathlib import Path

# Ajouter le chemin du projet au sys.path pour permettre les importations relatives
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from argumentation_analysis.core.utils.file_loaders import load_csv_file


def load_and_prepare_taxonomy(file_path: str) -> pd.DataFrame:
    """
    Charge et prépare le DataFrame de la taxonomie à partir d'un fichier CSV.
    - Charge le CSV en utilisant la fonction partagée `load_csv_file`.
    - Assure que 'PK' est une colonne d'entiers et la définit comme index.
    - Assure que 'depth' et les colonnes de clés parentes sont numériques.
    """
    print(f"Chargement et préparation de la taxonomie depuis : {file_path}")
    df = load_csv_file(file_path)
    if df is None:
        raise ValueError(f"Impossible de charger le fichier de taxonomie : {file_path}")

    # Préparation des colonnes clés
    key_columns = ["PK", "FK_Parent", "parent_pk", "depth"]
    for col in key_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # La colonne PK ne doit pas avoir de NaN
    if "PK" in df.columns and df["PK"].isnull().any():
        raise ValueError(
            "La colonne 'PK' contient des valeurs nulles, ce qui est interdit."
        )

    # Convertir PK en entier et le définir comme index
    if "PK" in df.columns:
        df["PK"] = df["PK"].astype(int)
        df.set_index("PK", inplace=True)
    else:
        raise ValueError(
            "La colonne 'PK' est manquante et ne peut être définie comme index."
        )

    print(f"Taxonomie chargée avec {len(df)} entrées.")
    return df


def get_direct_children(
    df: pd.DataFrame, parent_path: str, parent_depth: int
) -> pd.DataFrame:
    """
    Récupère les enfants directs d'un nœud parent à partir de son chemin et de sa profondeur.
    """
    if not parent_path or pd.isna(parent_depth):
        return pd.DataFrame()

    child_path_prefix = str(parent_path) + "."
    expected_child_depth = parent_depth + 1

    # Filtrer les enfants potentiels par le début du chemin et la profondeur exacte
    potential_children = df[
        df["path"].str.startswith(child_path_prefix, na=False)
        & (df["depth"] == expected_child_depth)
    ]
    return potential_children


def generate_taxonomy_subsets(base_path: str, output_dir: str):
    """
    Génère et sauvegarde trois sous-ensembles de la taxonomie des sophismes.
    """
    full_taxonomy_path = os.path.join(base_path, "argumentum_fallacies_taxonomy.csv")

    # 1. Charger la taxonomie complète
    full_df = load_and_prepare_taxonomy(full_taxonomy_path)

    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # --- Génération de taxonomy_full.csv ---
    full_output_path = os.path.join(output_dir, "taxonomy_full.csv")
    full_df.to_csv(full_output_path, index=True)
    print(f"Taxonomie complète sauvegardée dans : {full_output_path}")

    # --- Génération de taxonomy_small.csv ---
    # Contient les nœuds de profondeur 0 ou 1
    small_df = full_df[full_df["depth"].isin([0, 1])]
    small_output_path = os.path.join(output_dir, "taxonomy_small.csv")
    small_df.to_csv(small_output_path, index=True)
    print(f"Taxonomie 'small' sauvegardée dans : {small_output_path}")

    # --- Génération de taxonomy_medium.csv ---
    # Contient les branches principales plus leurs enfants directs
    medium_pks = set(small_df.index)
    for pk, parent_row in small_df.iterrows():
        parent_path = parent_row.get("path")
        parent_depth = parent_row.get("depth")
        children_df = get_direct_children(full_df, parent_path, parent_depth)
        medium_pks.update(children_df.index.tolist())

    medium_df = full_df.loc[list(medium_pks)].sort_index()
    medium_output_path = os.path.join(output_dir, "taxonomy_medium.csv")
    medium_df.to_csv(medium_output_path, index=True)
    print(f"Taxonomie 'medium' sauvegardée dans : {medium_output_path}")


if __name__ == "__main__":
    data_dir = os.path.join(project_root, "argumentation_analysis", "data")
    generate_taxonomy_subsets(base_path=data_dir, output_dir=data_dir)
