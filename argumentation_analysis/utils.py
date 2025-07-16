import os

def load_taxonomy_branches(directory: str) -> dict:
    """Loads all taxonomy definitions from a directory."""
    branches = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".txt"):
                path = os.path.join(root, file)
                # Create a "path-like" name for the branch, relative to the base directory
                branch_name = os.path.relpath(path, directory).replace("\\", "/")
                with open(path, 'r', encoding='utf-8') as f:
                    branches[branch_name] = f.read().strip()
    return branches