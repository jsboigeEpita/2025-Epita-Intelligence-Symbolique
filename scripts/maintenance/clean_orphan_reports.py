import os
import re
from pathlib import Path

def clean_orphan_reports():
    """
    Deletes narrative reports that are based on commit ranges beyond the actual git history.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    reports_dir = project_root / "docs" / "audit" / "synthesis_reports"
    
    # This should be determined dynamically, but for this specific cleanup, 
    # we know the last valid commit number.
    last_real_commit = 2872 

    if not reports_dir.exists():
        print(f"Error: Reports directory {reports_dir} not found.")
        return

    print(f"Scanning reports directory: {reports_dir}")
    
    # Regex for report filenames like 'rapport_commits_START-END.md'
    report_pattern = re.compile(r"rapport_commits_(\d+)-(\d+)\.md")
    
    files_to_delete = []

    for filename in os.listdir(reports_dir):
        match = report_pattern.match(filename)
        if match:
            end_commit = int(match.group(2))
            if end_commit > last_real_commit:
                files_to_delete.append(filename)

    if not files_to_delete:
        print("No orphan report files found.")
        return

    print(f"Found {len(files_to_delete)} orphan report files to delete.")

    for filename in files_to_delete:
        file_path = reports_dir / filename
        try:
            os.remove(file_path)
            print(f"Deleted: {filename}")
        except OSError as e:
            print(f"Error deleting {filename}: {e}")
            
    print("\nOrphan report cleanup finished.")

if __name__ == "__main__":
    clean_orphan_reports()