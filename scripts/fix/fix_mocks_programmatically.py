import argumentation_analysis.core.environment
import re
import argparse
import os
import sys

# Patterns de remplacement fournis par l'utilisateur
PATTERNS = {
    r'Mock\(SemanticKernel\)': 'UnifiedConfig().get_kernel_with_gpt4o_mini()',
    r'mock_\w+_agent': 'OrchestrationServiceManager',
    # Attention avec ce pattern, il faut s'assurer qu'il ne capture pas trop de choses.
    # Le .* peut être gourmand. S'il y a des problèmes, il faudra l'affiner.
    # Exemple: r'@patch\(("|\').*llm("|\')\)'
    r'@patch.*llm': '@pytest.mark.no_mocks\n@pytest.mark.requires_api_key',
    r'MagicMock\(\).*kernel': 'await UnifiedConfig().get_kernel_with_gpt4o_mini()'
}

def fix_mocks_in_file(filepath, patterns_to_use):
    """
    Applique les remplacements de mocks dans un fichier donné.

    Args:
        filepath (str): Chemin vers le fichier à modifier.
        patterns_to_use (dict): Dictionnaire des patterns regex et de leurs remplacements.

    Returns:
        tuple: (bool, list)
            - bool: True si des modifications ont été apportées, False sinon.
            - list: Liste des modifications apportées (chaînes de caractères).
    """
    modifications_log = []
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        modifications_log.append(f"ERREUR: Impossible de lire le fichier {filepath}: {e}")
        return False, modifications_log

    original_content = content
    current_content = content
    
    file_changed_overall = False

    for idx, (pattern, replacement) in enumerate(patterns_to_use.items()):
        new_content_lines = []
        lines = current_content.splitlines(True) # Conserve les fins de ligne
        pattern_made_change_in_file = False
        
        for i, line_content in enumerate(lines):
            # Appliquer re.subn pour obtenir le nombre de remplacements
            processed_line, num_replacements = re.subn(pattern, replacement, line_content)
            if num_replacements > 0:
                modifications_log.append(f"  Fichier: {filepath} - Ligne {i+1}: Remplacement du pattern #{idx+1} ('{pattern}')")
                pattern_made_change_in_file = True
                file_changed_overall = True
            new_content_lines.append(processed_line)
        
        if pattern_made_change_in_file:
            current_content = "".join(new_content_lines)

    if file_changed_overall:
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(current_content)
            modifications_log.insert(0, f"SUCCÈS: Fichier modifié : {filepath}")
            return True, modifications_log
        except Exception as e:
            modifications_log.append(f"ERREUR: Impossible d'écrire les modifications dans {filepath}: {e}")
            # Idéalement, il faudrait une stratégie de rollback ici si nécessaire.
            return False, modifications_log
    else:
        modifications_log.append(f"INFO: Aucune modification nécessaire pour : {filepath} avec les patterns fournis.")
        return False, modifications_log

def main():
    parser = argparse.ArgumentParser(
        description="Nettoie les mocks problématiques dans les fichiers de test Python de manière programmatique.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--files', nargs='+', help="Liste des fichiers Python à traiter.")
    group.add_argument('--directory', help="Répertoire à scanner récursivement pour les fichiers .py.")
    parser.add_argument(
        '--report-file',
        default='reports/fix_mocks_report.txt',
        help="Fichier pour enregistrer le rapport détaillé des modifications (par défaut: reports/fix_mocks_report.txt)."
    )
    
    args = parser.parse_args()

    files_to_process = []
    if args.directory:
        if not os.path.isdir(args.directory):
            print(f"ERREUR: Le répertoire spécifié n'existe pas : {args.directory}", file=sys.stderr)
            sys.exit(1)
        for root, _, files in os.walk(args.directory):
            for file_name in files:
                if file_name.endswith(".py"):
                    files_to_process.append(os.path.join(root, file_name))
        if not files_to_process:
            print(f"INFO: Aucun fichier .py trouvé dans le répertoire : {args.directory}")
            sys.exit(0)
    else:
        files_to_process = args.files
    
    all_modifications_summary = []
    total_files_processed = 0
    total_files_successfully_modified = 0
    
    report_dir = os.path.dirname(args.report_file)
    if report_dir and not os.path.exists(report_dir):
        try:
            os.makedirs(report_dir)
            print(f"INFO: Répertoire de rapport créé : {report_dir}")
        except OSError as e:
            print(f"ERREUR: Impossible de créer le répertoire de rapport {report_dir}: {e}", file=sys.stderr)
            # Continuer sans enregistrer dans un fichier si le répertoire ne peut être créé
            args.report_file = None 

    print(f"INFO: Début du traitement de {len(files_to_process)} fichier(s).")

    for filepath in files_to_process:
        if os.path.isfile(filepath):
            print(f"INFO: Traitement du fichier : {filepath}...")
            total_files_processed += 1
            modified, file_mods_log = fix_mocks_in_file(filepath, PATTERNS)
            if modified:
                total_files_successfully_modified += 1
            all_modifications_summary.extend(file_mods_log)
            all_modifications_summary.append("-" * 40) # Séparateur pour la lisibilité
        else:
            not_found_msg = f"ERREUR: Fichier non trouvé ou n'est pas un fichier standard : {filepath}"
            print(not_found_msg, file=sys.stderr)
            all_modifications_summary.append(not_found_msg)
            all_modifications_summary.append("-" * 40)

    summary_header = (
        f"Rapport final du nettoyage des mocks :\n"
        f"---------------------------------------\n"
        f"Fichiers traités au total : {total_files_processed}\n"
        f"Fichiers modifiés avec succès : {total_files_successfully_modified}\n"
        f"Fichiers avec erreurs ou non trouvés : {total_files_processed - total_files_successfully_modified}\n"
        f"---------------------------------------\n\n"
        f"Détails des opérations :\n"
    )
    report_content = summary_header + "\n".join(all_modifications_summary)

    if args.report_file:
        try:
            with open(args.report_file, 'w', encoding='utf-8') as r_file:
                r_file.write(report_content)
            print(f"\nINFO: Rapport détaillé des modifications enregistré dans : {args.report_file}")
        except Exception as e:
            print(f"\nERREUR: Impossible d'enregistrer le rapport détaillé dans {args.report_file}: {e}", file=sys.stderr)
            print("\n------ CONTENU DU RAPPORT (non sauvegardé) ------")
            print(report_content)
            print("------ FIN DU CONTENU DU RAPPORT ------")
    else:
        print("\n------ RAPPORT DES MODIFICATIONS ------")
        print(report_content)
        print("------ FIN DU RAPPORT ------")


    print(f"\nINFO: Terminé. {total_files_successfully_modified} fichier(s) sur {total_files_processed} ont été modifié(s) avec succès.")

if __name__ == "__main__":
    main()