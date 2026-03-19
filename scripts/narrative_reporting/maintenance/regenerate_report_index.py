import os
import json
import re
import argparse

def find_relevant_files(directory, start_commit, end_commit):
    relevant_files = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            match = re.match(r"(\d+)_", filename)
            if match:
                commit_num = int(match.group(1))
                if start_commit <= commit_num <= end_commit:
                    relevant_files.append(os.path.join(directory, filename))
    return relevant_files

def generate_index(files, start_commit, report_content=""):
    index_content = "### Index des Fichiers Sources\n\n"
    
    files.sort()
    
    chapters = {}
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                commit_number = int(os.path.basename(file_path).split('_')[0])
                
                # Generic grouping logic
                chapter_start = ((commit_number - start_commit) // 20) * 20 + start_commit
                chapter_end = chapter_start + 19
                
                # Search for the full chapter title in the report content
                title_pattern = r"^#\s+(Chapitre .*?\(Commits {}-{}\)).*".format(chapter_start, chapter_end)
                title_match = re.search(title_pattern, report_content, re.MULTILINE | re.IGNORECASE)

                if title_match:
                    chapter_title = title_match.group(1).strip()
                else:
                    chapter_title = f"Commits {chapter_start}-{chapter_end}"

                if chapter_title not in chapters:
                    chapters[chapter_title] = []

                chapters[chapter_title].append(f"- `{os.path.join(file_path)}`")

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Skipping file {file_path} due to error: {e}")
                continue

    def sort_key(title):
        # Extraire le premier numéro de commit pour un tri fiable
        match = re.search(r'\(Commits (\d+)-\d+\)', title)
        if not match:
            match = re.search(r'Commits (\d+)-\d+', title)
        if match:
            return int(match.group(1))
        return -1  # Fallbackpour les titres sans numéro de commit

    sorted_chapter_titles = sorted(chapters.keys(), key=sort_key)

    for i, title in enumerate(sorted_chapter_titles, 1):
        # Extraire les numéros de commit du titre pour le nouveau format
        match = re.search(r'Commits (\d+)-(\d+)', title)
        if match:
            start = match.group(1)
            end = match.group(2)
            new_title = f"Chapitre {i}: commits {start}-{end}"
            index_content += f"### {new_title}\n\n"
        else:
            # Fallback pour les titres qui ne correspondent pas
            index_content += f"### Chapitre {i}: {title}\n\n"

        unique_files = sorted(list(set(chapters[title])))
        index_content += "\n".join(unique_files)
        index_content += "\n\n"
        
    return index_content.strip()

def main():
    parser = argparse.ArgumentParser(description="Regenerate the index of an audit report while preserving the narrative.")
    parser.add_argument("--report-path", required=True, help="Path to the report file to update.")
    parser.add_argument("--backup-path", required=True, help="Path to the backup file to restore narrative from.")
    parser.add_argument("--audit-dir", default="docs/commits_audit", help="Directory containing the audit JSON files.")
    parser.add_argument("--start-commit", type=int, required=True, help="Start commit number.")
    parser.add_argument("--end-commit", type=int, required=True, help="End commit number.")
    parser.add_argument("--narrative-marker", default="# Chapitre 1", help="The text marker indicating the start of the narrative section.")

    args = parser.parse_args()

    # Restore original narrative content
    narrative_content = ""
    backup_content = ""
    try:
        with open(args.backup_path, 'r', encoding='utf-8') as f:
            backup_content = f.read()

        narrative_start_index = backup_content.find(args.narrative_marker)

        if narrative_start_index != -1:
            narrative_content = backup_content[narrative_start_index:]
            print(f"Narrative content successfully restored from '{args.backup_path}'.")
        else:
            print(f"Error: Narrative start marker '{args.narrative_marker}' not found in backup file '{args.backup_path}'.")

    except FileNotFoundError:
        print(f"Error: Backup file not found at '{args.backup_path}'. Cannot restore narrative.")

    # Generate the new index using the backup content to find titles
    relevant_files = find_relevant_files(args.audit_dir, args.start_commit, args.end_commit)
    new_index_content = generate_index(relevant_files, args.start_commit, backup_content)

    # Write the new content to the file
    final_content = new_index_content + "\n" + narrative_content
    with open(args.report_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Report '{args.report_path}' has been regenerated with a new index and restored narrative.")


if __name__ == "__main__":
    main()