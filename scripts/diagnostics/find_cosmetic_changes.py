import subprocess
import sys

def get_modified_files():
    """Returns a list of modified files from git."""
    result = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True, check=True)
    return result.stdout.strip().split('\n')

def has_functional_changes(file_path):
    """
    Checks if a file has changes other than whitespace.
    Returns True if functional changes are detected, False otherwise.
    """
    try:
        process = subprocess.run(
            ['git', 'diff', '--ignore-all-space', '--ignore-blank-lines', '-U0', file_path],
            capture_output=True, text=True, check=True
        )
        # If the diff is empty, there are no functional changes
        return process.stdout.strip() != ''
    except subprocess.CalledProcessError as e:
        print(f"Error checking file {file_path}: {e}", file=sys.stderr)
        return True # Assume functional changes on error

def main():
    """
    Main function to classify modified files into cosmetic and functional changes.
    """
    modified_files = get_modified_files()
    
    cosmetic_only = []
    functional_changes = []

    for file in modified_files:
        if file:
            print(f"Analyzing {file}...")
            if has_functional_changes(file):
                functional_changes.append(file)
            else:
                cosmetic_only.append(file)
    
    print("\n--- Analysis Complete ---")
    print(f"\nFiles with only cosmetic changes ({len(cosmetic_only)}):")
    for file in cosmetic_only:
        print(f"  - {file}")
        
    print(f"\nFiles with potential functional changes ({len(functional_changes)}):")
    for file in functional_changes:
        print(f"  - {file}")

    # You could add logic here to automatically revert cosmetic changes,
    # but for now, we just report.
    # For example:
    # if input("Revert cosmetic changes? (y/n): ").lower() == 'y':
    #     for file in cosmetic_only:
    #         subprocess.run(['git', 'checkout', '--', file])

if __name__ == "__main__":
    main()