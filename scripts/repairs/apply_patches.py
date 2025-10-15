import os
import subprocess
import sys

PATCHES_DIR = "patches"


def apply_patch(patch_file_path):
    """
    Applies a single patch file using 'git apply'.
    """
    if not os.path.exists(patch_file_path):
        print(f"Patch file not found: {patch_file_path}", file=sys.stderr)
        return False

    print(f"Applying patch: {os.path.basename(patch_file_path)}...")
    try:
        # Using --reject is safer as it won't stop on failures,
        # but create .rej files for manual inspection.
        subprocess.run(
            ["git", "apply", "--reject", "--ignore-whitespace", patch_file_path],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error applying patch {patch_file_path}:", file=sys.stderr)
        print(f"STDOUT: {e.stdout}", file=sys.stderr)
        print(f"STDERR: {e.stderr}", file=sys.stderr)
        print(
            "Changes may have been saved to a .rej file. Manual review needed.",
            file=sys.stderr,
        )
        return False


def main():
    """
    Main function to find all .patch files and apply them.
    """
    if not os.path.isdir(PATCHES_DIR):
        print(f"Error: Patches directory '{PATCHES_DIR}' not found.", file=sys.stderr)
        sys.exit(1)

    patch_files = [f for f in os.listdir(PATCHES_DIR) if f.endswith(".patch")]

    if not patch_files:
        print("No .patch files found to apply.")
        return

    print(f"--- Starting to Apply {len(patch_files)} Patches ---")

    success_count = 0
    fail_count = 0

    for patch_file in sorted(patch_files):
        full_path = os.path.join(PATCHES_DIR, patch_file)
        if apply_patch(full_path):
            success_count += 1
        else:
            fail_count += 1

    print("\n--- Patch Application Complete ---")
    print(f"Successfully applied {success_count} patches.")
    if fail_count > 0:
        print(
            f"Failed to apply {fail_count} patches cleanly. Please check for .rej files and review the logs."
        )


if __name__ == "__main__":
    main()
