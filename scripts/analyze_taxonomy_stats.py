# scripts/analyze_taxonomy_stats.py
import sys
import csv
import argparse
from pathlib import Path
from collections import defaultdict


def analyze_taxonomy_stats(file_path: str):
    """
    Analyse un fichier de taxonomie CSV pour générer des statistiques de remplissage
    pour chaque colonne, regroupées par langue supposée.
    """
    print(f"--- Analyse statistique de la taxonomie : {file_path} ---")
    sys.stdout.flush()

    if not Path(file_path).exists():
        print(f"ERREUR: Le fichier n'existe pas: {file_path}")
        sys.stdout.flush()
        return

    taxonomy_data = []
    fieldnames = []
    try:
        with open(file_path, mode="r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            print("... Lecture du fichier CSV ...")
            sys.stdout.flush()
            fieldnames = reader.fieldnames
            taxonomy_data = list(reader)
            print(f"... {len(taxonomy_data)} lignes lues ...")
            sys.stdout.flush()
    except Exception as e:
        print(f"ERREUR: Impossible de lire le fichier CSV: {e}")
        sys.stdout.flush()
        return

    if not taxonomy_data or not fieldnames:
        print(
            "ERREUR: Aucune donnée ou aucun en-tête trouvé dans le fichier de taxonomie."
        )
        sys.stdout.flush()
        return

    total_rows = len(taxonomy_data)
    non_empty_counts = defaultdict(int)

    for row in taxonomy_data:
        for field in fieldnames:
            if row.get(field) and row.get(field).strip():
                non_empty_counts[field] += 1

    # Regrouper par langue supposée
    stats_by_lang = defaultdict(list)
    other_fields = []

    lang_suffixes = ["_fr", "_en", "_es", "_ru", "_de", "_it", "_pt", "_zh"]

    for field in fieldnames:
        found_lang = False
        for suffix in lang_suffixes:
            if field.endswith(suffix):
                lang = suffix[1:].upper()
                stats_by_lang[lang].append(field)
                found_lang = True
                break
        if not found_lang:
            other_fields.append(field)

    print(f"\n--- 📊 RAPPORT STATISTIQUE (sur {total_rows} noeuds) ---")

    print("\n--- Champs non spécifiques à une langue ---")
    sorted_other_fields = sorted(
        other_fields, key=lambda f: non_empty_counts.get(f, 0), reverse=True
    )
    for field in sorted_other_fields:
        count = non_empty_counts.get(field, 0)
        percentage = (count / total_rows) * 100
        print(f"  - {field:<25} : {count:>5} / {total_rows} ({percentage:6.2f}%)")

    sorted_langs = sorted(stats_by_lang.keys())
    for lang in sorted_langs:
        print(f"\n--- Langue: {lang} ---")
        sorted_lang_fields = sorted(
            stats_by_lang[lang], key=lambda f: non_empty_counts.get(f, 0), reverse=True
        )
        for field in sorted_lang_fields:
            count = non_empty_counts.get(field, 0)
            percentage = (count / total_rows) * 100
            print(f"  - {field:<25} : {count:>5} / {total_rows} ({percentage:6.2f}%)")

    print("\n--- FIN DU RAPPORT ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyseur statistique de fichier de taxonomie CSV."
    )
    parser.add_argument(
        "--taxonomy-file",
        type=str,
        default="argumentation_analysis/data/argumentum_fallacies_taxonomy.csv",
        help="Chemin vers le fichier de taxonomie CSV à analyser.",
    )
    args = parser.parse_args()

    print("--- Démarrage de l'analyse ---")
    sys.stdout.flush()
    analyze_taxonomy_stats(args.taxonomy_file)
    print("--- Fin de l'analyse ---")
    sys.stdout.flush()
