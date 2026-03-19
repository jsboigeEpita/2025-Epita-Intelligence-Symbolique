import argparse
import json
import os
from pathlib import Path
from regenerate_report_index import find_relevant_files, generate_index

def generate_report_skeleton(start_commit, end_commit, output_dir):
    """
    Génère un squelette de rapport d'audit Markdown pour une plage de commits.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    output_filename = f"rapport_commits_{start_commit}-{end_commit}.md"
    report_file_path = output_path / output_filename

    if report_file_path.exists():
        print(f"Le fichier de rapport {report_file_path} existe déjà. Opération ignorée.")
        return

    source_dir = 'docs/commits_audit'
    relevant_files = find_relevant_files(source_dir, start_commit, end_commit)
    
    # Générer seulement l'index des fichiers, sans chapitres d'analyse
    index_content = generate_index(relevant_files, start_commit)

    with open(report_file_path, 'w', encoding='utf-8') as f:
        f.write(f"# Archéologie Narrative des Commits {start_commit}-{end_commit}\n\n")
        f.write("## Index des Fichiers et Chapitres\n\n")
        f.write(index_content)
        f.write("\n---\n\n")
        f.write("## Narration et Analyse des Commits\n\n")
        f.write("*(Cette section est laissée vide intentionnellement pour être remplie plus tard.)*\n")

    print(f"Le rapport squelette a été généré : {report_file_path}")

def main():
    """
    Point d'entrée principal du script.
    Génère des squelettes de rapport pour des plages de commits.
    """
    START_COMMIT = 416
    END_COMMIT = 3205
    CHUNK_SIZE = 200
    OUTPUT_DIR = 'docs/audit/synthesis_reports'

    for start in range(START_COMMIT, END_COMMIT + 1, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE - 1, END_COMMIT)
        print(f"Génération du rapport pour la plage de commits {start}-{end}...")
        generate_report_skeleton(start, end, OUTPUT_DIR)

    print("\nTous les rapports squelettes ont été générés.")

if __name__ == "__main__":
    main()