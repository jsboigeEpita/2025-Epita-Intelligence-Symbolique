import argparse
import json
import os
from pathlib import Path
import sys
import re

# Ajout du chemin pour l'importation du module de maintenance
sys.path.append(str(Path(__file__).resolve().parent.parent))
from maintenance.regenerate_report_index import find_relevant_files

def get_report_files(reports_dir, current_report_start_commit):
    """
    Trouve le rapport actuel et les rapports précédents.
    """
    previous_reports = []
    current_report = None
    
    for filename in sorted(os.listdir(reports_dir)):
        match = re.match(r"rapport_commits_(\d+)-(\d+)\.md", filename)
        if match:
            start_commit = int(match.group(1))
            if start_commit < current_report_start_commit:
                previous_reports.append(os.path.join(reports_dir, filename))
            elif start_commit == current_report_start_commit:
                current_report = os.path.join(reports_dir, filename)
                
    return previous_reports, current_report

def main():
    parser = argparse.ArgumentParser(description="Gather context for a specific audit report chapter.")
    parser.add_argument("--report-start-commit", type=int, required=True, help="The starting commit number of the report series (e.g., 416).")
    parser.add_argument("--chapter-number", type=int, required=True, help="The chapter number to analyze (1-based).")
    parser.add_argument("--audit-dir", default="docs/commits_audit", help="Directory containing the audit JSON files.")
    parser.add_argument("--reports-dir", default="docs/audit/synthesis_reports", help="Directory containing the synthesis report files.")

    args = parser.parse_args()

    # 1. Trouver les fichiers de rapport pertinents
    previous_reports, current_report_path = get_report_files(args.reports_dir, args.report_start_commit)

    print("--- PREVIOUS REPORTS ---")
    if previous_reports:
        for report_path in previous_reports:
            print(f"\n### Content of {report_path} ###\n")
            with open(report_path, 'r', encoding='utf-8') as f:
                print(f.read())
    else:
        print("No previous reports found.")
    print("\n--- END OF PREVIOUS REPORTS ---\n")

    print("--- CURRENT REPORT ---")
    if current_report_path:
        print(f"\n### Content of {current_report_path} ###\n")
        with open(current_report_path, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print(f"Error: Could not find the current report for start commit {args.report_start_commit}.")
        return
    print("\n--- END OF CURRENT REPORT ---\n")


    # 2. Calculer la plage de commits pour le chapitre
    # La logique de chapitrage est de 20 commits par chapitre.
    start_commit_chapter = args.report_start_commit + (args.chapter_number - 1) * 20
    end_commit_chapter = start_commit_chapter + 19

    print(f"--- CONCATENATED JSON FOR CHAPTER {args.chapter_number} (COMMITS {start_commit_chapter}-{end_commit_chapter}) ---")
    
    # 3. Trouver et concaténer les fichiers JSON
    relevant_files = find_relevant_files(args.audit_dir, start_commit_chapter, end_commit_chapter)
    
    if not relevant_files:
        print(f"No JSON files found for commits {start_commit_chapter}-{end_commit_chapter}.")
        return

    concatenated_content = ""
    for file_path in sorted(relevant_files):
        concatenated_content += f"\n\n--- Start of {os.path.basename(file_path)} ---\n\n"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # On utilise json.load puis json.dumps pour formater proprement le JSON
                data = json.load(f)
                concatenated_content += json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            concatenated_content += f"Error reading or parsing file: {e}"
    
    print(concatenated_content)
    print(f"\n--- END OF CONCATENATED JSON ---")


if __name__ == "__main__":
    main()