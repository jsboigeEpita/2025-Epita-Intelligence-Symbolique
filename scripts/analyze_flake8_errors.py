# -*- coding: utf-8 -*-
"""
Script d'analyse du rapport flake8 pour la mission D-CI-06 Phase 6.

Ce script parse le fichier flake8_report.txt, génère des statistiques
détaillées sur la distribution des erreurs et identifie les "hotspots"
(fichiers avec un grand nombre d'erreurs).

Fonctionnalités :
- Compte le nombre total d'erreurs.
- Calcule la distribution des erreurs par code (ex: E128, F401).
- Calcule la distribution des erreurs par répertoire.
- Identifie les fichiers avec plus de 100 erreurs.
- Exporte les résultats dans un fichier JSON structuré pour analyse ultérieure.

Usage :
    python scripts/analyze_flake8_errors.py

Le script lira 'flake8_report.txt' à la racine du projet et produira
'reports/flake8_analysis_phase6_1.json'.
"""
import json
import os
from collections import Counter
from datetime import datetime

# Constantes
REPORT_FILE = 'flake8_report.txt'
OUTPUT_JSON = 'reports/flake8_analysis_phase6_1.json'
HOTSPOT_THRESHOLD = 100

def analyze_flake8_report(report_path):
    """
    Analyse un rapport flake8 et retourne des statistiques détaillées.

    Args:
        report_path (str): Chemin vers le fichier flake8_report.txt.

    Returns:
        dict: Un dictionnaire contenant les statistiques d'analyse.
              Retourne None si le fichier n'est pas trouvé.
    """
    if not os.path.exists(report_path):
        print(f"Erreur : Le fichier '{report_path}' n'a pas été trouvé.")
        return None

    error_codes = Counter()
    errors_by_file = Counter()
    errors_by_directory = Counter()
    total_errors = 0

    with open(report_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_errors += 1
            parts = line.strip().split(':')
            if len(parts) >= 4:
                file_path = parts[0].strip()
                try:
                    error_code = parts[3].strip().split(' ')[0]
                    error_codes[error_code] += 1
                    errors_by_file[file_path] += 1

                    # Analyse par répertoire
                    dir_path = os.path.dirname(file_path)
                    # Normaliser le chemin pour Windows/Unix
                    dir_path = dir_path.replace('.\\', '').replace('./', '')
                    # Regrouper les sous-répertoires dans leur parent de premier niveau
                    parts = dir_path.split(os.sep) if dir_path else []
                    if not parts or parts[0] in ['.', '']:
                        top_level_dir = "root"
                    else:
                        top_level_dir = parts[0]
                    errors_by_directory[top_level_dir] += 1

                except IndexError:
                    print(f"Avertissement : Ligne mal formée ignorée : {line.strip()}")

    # Calcul des pourcentages
    by_code_percent = {code: {"count": count, "percentage": round((count / total_errors) * 100, 2)}
                       for code, count in error_codes.items()}

    by_directory_percent = {directory: {"count": count, "percentage": round((count / total_errors) * 100, 2)}
                            for directory, count in errors_by_directory.items()}

    # Identification des hotspots
    hotspots = [{"file": file, "errors": count}
                for file, count in errors_by_file.items() if count > HOTSPOT_THRESHOLD]
    hotspots.sort(key=lambda x: x['errors'], reverse=True)

    return {
        "baseline_date": datetime.utcnow().isoformat() + "Z",
        "total_errors": total_errors,
        "by_code": dict(sorted(by_code_percent.items(), key=lambda item: item[1]['count'], reverse=True)),
        "by_directory": dict(sorted(by_directory_percent.items(), key=lambda item: item[1]['count'], reverse=True)),
        "hotspots": hotspots
    }

def save_analysis_to_json(analysis_data, output_path):
    """
    Sauvegarde les données d'analyse dans un fichier JSON.

    Args:
        analysis_data (dict): Les données à sauvegarder.
        output_path (str): Le chemin du fichier JSON de sortie.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Répertoire '{output_dir}' créé.")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    print(f"Analyse sauvegardée dans '{output_path}'")


def main():
    """
    Fonction principale du script.
    """
    print("Début de l'analyse du rapport flake8...")
    analysis_results = analyze_flake8_report(REPORT_FILE)

    if analysis_results:
        print(f"Analyse terminée. Total d'erreurs trouvées : {analysis_results['total_errors']}")
        save_analysis_to_json(analysis_results, OUTPUT_JSON)

        print("\nTop 10 des codes d'erreur :")
        for i, (code, data) in enumerate(analysis_results['by_code'].items()):
            if i >= 10:
                break
            print(f"  {code}: {data['count']} erreurs ({data['percentage']}%)")

        print("\nTop 5 des répertoires avec le plus d'erreurs :")
        for i, (directory, data) in enumerate(analysis_results['by_directory'].items()):
            if i >= 5:
                break
            print(f"  {directory}: {data['count']} erreurs ({data['percentage']}%)")

        print(f"\nNombre de hotspots (fichiers > {HOTSPOT_THRESHOLD} erreurs) : {len(analysis_results['hotspots'])}")

if __name__ == "__main__":
    main()