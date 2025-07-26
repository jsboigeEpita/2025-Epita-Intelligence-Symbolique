import os
import subprocess
import sys

PATCHES_DIR = "patches"
FUNCTIONAL_CHANGES_FILE = "functional_changes_confirmed.txt"

def create_patch_backup(file_path):
    """
    Creates a .patch file for a given file using 'git diff'.
    """
    if not os.path.exists(file_path):
        print(f"File not found, skipping patch: {file_path}", file=sys.stderr)
        return False
        
    # Ensure the path inside the patch is correctly formatted (posix-style)
    # Replace both possible path separators with an underscore for a flat structure
    patch_file_name = file_path.replace('/', '_').replace('\\', '_') + ".patch"
    patch_file_path = os.path.join(PATCHES_DIR, patch_file_name)

    try:
        print(f"Creating patch for {file_path}...")
        # Use git diff to capture the changes
        result = subprocess.run(
            ['git', 'diff', 'HEAD', '--', file_path],
            capture_output=True, text=True, check=True
        )
        
        with open(patch_file_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating patch for {file_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred for {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """
    Main function to read the list of functional changes and back them up as patch files.
    """
    if not os.path.exists(FUNCTIONAL_CHANGES_FILE):
        print(f"Error: {FUNCTIONAL_CHANGES_FILE} not found.", file=sys.stderr)
        print("Please run the AST analysis script first.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(PATCHES_DIR, exist_ok=True)

    with open(FUNCTIONAL_CHANGES_FILE, 'r') as f:
        files_to_patch = [line.strip() for line in f if line.strip()]

    print(f"--- Starting Backup of {len(files_to_patch)} Functional Change Files ---")
    
    success_count = 0
    fail_count = 0
    
    for file_path in files_to_patch:
        if create_patch_backup(file_path):
            success_count += 1
        else:
            fail_count += 1
            
    print("\n--- Backup Complete ---")
    print(f"Successfully created {success_count} patch files in '{PATCHES_DIR}'.")
    if fail_count > 0:
        print(f"Failed to create {fail_count} patch files. Please check the logs above.")

if __name__ == "__main__":
    main()