# scripts/analyze_taxonomy.py
import sys
import os
import csv
import argparse
from pathlib import Path

print("--- Script analyze_taxonomy.py starting ---")
sys.stdout.flush()

# Assurer que le chemin du projet est dans sys.path
print("... Configuring sys.path ...")
sys.stdout.flush()
try:
    current_file_path = Path(__file__).resolve()
    print(f"    - Current file path: {current_file_path}")
    project_root = next(
        (p for p in current_file_path.parents if (p / "pyproject.toml").exists()), None
    )
    print(f"    - Detected project root: {project_root}")
    if project_root and str(project_root) not in sys.path:
        print(f"    - Adding project root to sys.path: {project_root}")
        sys.path.insert(0, str(project_root))

    print("... Importing TaxonomyNavigator ...")
    sys.stdout.flush()
    from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

    print("--- TaxonomyNavigator imported successfully ---")
    sys.stdout.flush()

except (ImportError, FileNotFoundError) as e:
    print(f"Erreur: Impossible d'importer TaxonomyNavigator: {e}")
    sys.stdout.flush()
    sys.exit(1)


def analyze_taxonomy(file_path: str):
    """
    Analyse un fichier de taxonomie CSV pour trouver les noeuds avec des champs manquants.
    """
    print(f"--- Analyse de la taxonomie : {file_path} ---")
    sys.stdout.flush()

    if not Path(file_path).exists():
        print(f"ERREUR: Le fichier n'existe pas: {file_path}")
        sys.stdout.flush()
        return

    taxonomy_data = []
    try:
        with open(file_path, mode="r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                taxonomy_data.append(row)
    except Exception as e:
        print(f"ERREUR: Impossible de lire le fichier CSV: {e}")
        sys.stdout.flush()
        return

    if not taxonomy_data:
        print("ERREUR: Aucune donnée trouvée dans le fichier de taxonomie.")
        sys.stdout.flush()
        return

    navigator = TaxonomyNavigator(taxonomy_data=taxonomy_data)
    all_nodes = navigator.taxonomy_data

    missing_fields_report = {}
    fields_to_check = ["description_courte", "exemple", "ref_url", "text_fr"]

    for node in all_nodes:
        node_id = node.get("PK")
        missing_fields = []
        for field in fields_to_check:
            if not node.get(field) or not node.get(field).strip():
                missing_fields.append(field)

        if missing_fields:
            node_name = node.get("text_fr") or node.get("nom_vulgarise", "N/A")
            missing_fields_report[node_id] = {
                "name": node_name,
                "path": node.get("path"),
                "missing": missing_fields,
            }

    if not missing_fields_report:
        print("\n--- ✅ SUCCÈS ---")
        print(
            "Aucun champ manquant détecté pour les champs critiques dans les noeuds de la taxonomie."
        )
        sys.stdout.flush()
    else:
        print(
            f"\n--- 🚨 RAPPORT ({len(missing_fields_report)} noeuds avec des champs manquants) ---"
        )
        for node_id, details in missing_fields_report.items():
            print(
                f"  - Noeud ID: {node_id} (Path: {details['path']}, Nom: {details['name']})"
            )
            print(f"    Champs manquants: {', '.join(details['missing'])}")
        print("--- FIN DU RAPPORT ---")
        sys.stdout.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyseur de fichier de taxonomie CSV."
    )
    parser.add_argument(
        "--taxonomy-file",
        type=str,
        default="argumentation_analysis/data/argumentum_fallacies_taxonomy.csv",
        help="Chemin vers le fichier de taxonomie CSV à analyser.",
    )
    args = parser.parse_args()

    analyze_taxonomy(args.taxonomy_file)
    print("--- Script analyze_taxonomy.py finished ---")
    sys.stdout.flush()
