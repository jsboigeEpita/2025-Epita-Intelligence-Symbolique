import ast
import subprocess
import sys

def get_modified_files():
    """Returns a list of modified files from git."""
    result = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True, check=True)
    return [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]

def get_file_content_from_git(file_path, revision="HEAD"):
    """Gets the content of a file from a specific git revision."""
    try:
        result = subprocess.run(['git', 'show', f'{revision}:{file_path}'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        # File might be new, so it doesn't exist in HEAD
        return ""

def compare_ast(file_path):
    """
    Compares the AST of the current version of a file with its HEAD version.
    Returns 'functional' if ASTs differ, 'cosmetic' if they are the same,
    'error' if there's a syntax error, and 'new' for new files.
    """
    try:
        current_content = Path(file_path).read_text()
    except FileNotFoundError:
        print(f"File not found: {file_path}", file=sys.stderr)
        return 'error'
        
    original_content = get_file_content_from_git(file_path)

    if not original_content:
        return 'new'

    try:
        current_ast = ast.parse(current_content)
        original_ast = ast.parse(original_content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return 'error'

    current_dump = ast.dump(current_ast, annotate_fields=False)
    original_dump = ast.dump(original_ast, annotate_fields=False)

    if current_dump == original_dump:
        return 'cosmetic'
    else:
        return 'functional'

def main():
    modified_files = get_modified_files()
    
    functional_files = []
    cosmetic_files = []
    error_files = []
    new_files = []

    for file in modified_files:
        if file:
            print(f"Analyzing {file} with AST...")
            result = compare_ast(file)
            if result == 'functional':
                functional_files.append(file)
            elif result == 'cosmetic':
                cosmetic_files.append(file)
            elif result == 'new':
                new_files.append(file)
            else:
                error_files.append(file)
    
    print("\n--- AST Analysis Complete ---")

    with open("cosmetic_and_comments_only.txt", "w") as f:
        f.write("\n".join(cosmetic_files))
    print(f"\n({len(cosmetic_files)}) Files with cosmetic/comment changes only:")
    print("\n".join(f"  - {f}" for f in cosmetic_files))

    with open("functional_changes_confirmed.txt", "w") as f:
        f.write("\n".join(functional_files))
    print(f"\n({len(functional_files)}) Files with confirmed functional changes:")
    print("\n".join(f"  - {f}" for f in functional_files))

    if new_files:
        print(f"\n({len(new_files)}) New files (assumed functional):")
        print("\n".join(f"  - {f}" for f in new_files))
        # Add new files to functional list
        with open("functional_changes_confirmed.txt", "a") as f:
            f.write("\n" + "\n".join(new_files))


    if error_files:
        print(f"\n({len(error_files)}) Files with syntax errors (needs manual review):")
        print("\n".join(f"  - {f}" for f in error_files))

if __name__ == "__main__":
    from pathlib import Path
    main()
