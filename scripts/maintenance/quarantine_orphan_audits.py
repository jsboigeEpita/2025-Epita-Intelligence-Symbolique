import os
import re
from pathlib import Path

def quarantine_miscounted_audits():
    """
    Identifies audit files with a sequential number higher than the total number of commits.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    audit_dir = project_root / "docs" / "commits_audit"
    quarantine_dir = project_root / "docs" / "commits_audit_quarantine_bymiscounting"

    # We know this from 'git rev-list --count HEAD'
    last_real_commit_number = 2872

    if not audit_dir.exists():
        print(f"Error: Audit directory {audit_dir} not found.")
        return

    quarantine_dir.mkdir(exist_ok=True)
    
    # Regex to extract sequential number from filenames like 'NNNN_...json'
    filename_pattern = re.compile(r"(\d+)_.*\.json")
    
    files_to_quarantine = []
    
    print(f"Scanning audit directory for miscounted files: {audit_dir}")
    for filename in os.listdir(audit_dir):
        match = filename_pattern.match(filename)
        if match:
            commit_number = int(match.group(1))
            if commit_number > last_real_commit_number:
                files_to_quarantine.append(filename)

    if not files_to_quarantine:
        print("No miscounted audit files found.")
        return

    print(f"Found {len(files_to_quarantine)} miscounted audit files to quarantine.")
    
    for filename in files_to_quarantine:
        source_path = audit_dir / filename
        destination_path = quarantine_dir / filename
        try:
            os.rename(source_path, destination_path)
            print(f"Moved: {filename}")
        except OSError as e:
            print(f"Error moving {filename}: {e}")

    print("\nMiscounted files quarantine process finished.")

if __name__ == "__main__":
    quarantine_miscounted_audits()