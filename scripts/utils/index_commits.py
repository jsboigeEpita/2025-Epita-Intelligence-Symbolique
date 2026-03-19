import json
import os

def index_commits_in_json(file_path):
    """
    Reads a JSON file containing a list of commits, adds a sequential 'index'
    to each commit object, and overwrites the file with the updated data.

    Args:
        file_path (str): The path to the JSON file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            commits = json.load(f)

        for i, commit in enumerate(commits):
            commit['index'] = i + 1

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(commits, f, indent=4, ensure_ascii=False)

        print(f"Successfully added 'index' to {len(commits)} commits in {file_path}")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # Construct the full path to the JSON file relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to go up from scripts/utils to the root, then down to docs/audit/synthesis_reports
    json_file = os.path.join(script_dir, '..', '..', 'docs', 'audit', 'synthesis_reports', 'aggregated_commits_1_a_215.json')
    
    # Normalize the path to handle '..' correctly
    normalized_path = os.path.normpath(json_file)
    
    index_commits_in_json(normalized_path)