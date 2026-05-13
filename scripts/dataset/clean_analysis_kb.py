#!/usr/bin/env python3
"""Clean analysis_kb output directories.

Removes all signature and state dump files produced by run_corpus_batch.py.
Safe to re-run — creates directories if they don't exist.

Usage:
    python scripts/dataset/clean_analysis_kb.py           # clean both
    python scripts/dataset/clean_analysis_kb.py --only signatures
    python scripts/dataset/clean_analysis_kb.py --only state_dumps
"""

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = REPO_ROOT / "analysis_kb"

SUBDIRS = {
    "signatures": KB_DIR / "signatures",
    "state_dumps": KB_DIR / "state_dumps",
}


def clean_dir(d: Path, label: str) -> int:
    if not d.exists():
        print(f"[{label}] directory does not exist, creating: {d}")
        d.mkdir(parents=True, exist_ok=True)
        return 0
    count = 0
    for f in d.iterdir():
        if f.is_file():
            f.unlink()
            count += 1
        elif f.is_dir():
            shutil.rmtree(f)
            count += 1
    print(f"[{label}] removed {count} items from {d}")
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clean analysis_kb output directories")
    parser.add_argument(
        "--only",
        choices=list(SUBDIRS.keys()),
        help="Clean only this subdirectory (default: both)",
    )
    args = parser.parse_args(argv)

    targets = [args.only] if args.only else list(SUBDIRS.keys())
    total = 0
    for name in targets:
        total += clean_dir(SUBDIRS[name], name)

    print(f"Done. {total} items removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
