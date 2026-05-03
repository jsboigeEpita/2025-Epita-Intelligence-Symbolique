#!/usr/bin/env python3
"""Enrichment workflow tasks for Discourse Pattern Mining (Issue #413).

Standalone CLI — no external task runner required.

Usage:
    python scripts/dataset/tasks.py pattern-add --source NAME --text PATH [--metadata KEY=VAL,...]
    python scripts/dataset/tasks.py pattern-rerun [--skip-existing]
    python scripts/dataset/tasks.py pattern-report
"""
import argparse
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "dataset"

ADD_SCRIPT = SCRIPTS_DIR / "add_extract.py"
BATCH_SCRIPT = SCRIPTS_DIR / "run_corpus_batch.py"
REPORT_SCRIPT = SCRIPTS_DIR / "build_pattern_report.py"


def _check_script(path: pathlib.Path, name: str) -> bool:
    if not path.is_file():
        print(f"ERROR: {name} not found at {path}", file=sys.stderr)
        print(f"  → This script is provided by a dependent issue (C.1–C.4).", file=sys.stderr)
        print(f"  → See docs/security/dataset_enrichment.md for the workflow.", file=sys.stderr)
        return False
    return True


def cmd_pattern_add(args):
    if not _check_script(ADD_SCRIPT, "add_extract.py"):
        return 1
    cmd = [sys.executable, str(ADD_SCRIPT),
           "--source-name", args.source,
           "--extract-text-file", args.text]
    if args.metadata:
        cmd.extend(["--metadata", args.metadata])
    return subprocess.call(cmd)


def cmd_pattern_rerun(args):
    if not _check_script(BATCH_SCRIPT, "run_corpus_batch.py"):
        return 1
    cmd = [sys.executable, str(BATCH_SCRIPT),
           "--workflow", "spectacular"]
    if args.skip_existing:
        cmd.append("--skip-existing")
    return subprocess.call(cmd)


def cmd_pattern_report(args):
    if not _check_script(REPORT_SCRIPT, "build_pattern_report.py"):
        return 1
    return subprocess.call([sys.executable, str(REPORT_SCRIPT)])


def main():
    parser = argparse.ArgumentParser(
        description="Discourse Pattern Mining — enrichment workflow tasks")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("pattern-add",
                           help="Add a new extract to the encrypted dataset")
    p_add.add_argument("--source", required=True,
                       help="Opaque source identifier (e.g. speech_id_X)")
    p_add.add_argument("--text", required=True,
                       help="Path to plaintext file (stays local, not committed)")
    p_add.add_argument("--metadata", default=None,
                       help="Comma-separated key=val pairs "
                            "(discourse_type=populist,era=2025)")

    p_rerun = sub.add_parser("pattern-rerun",
                             help="Re-run spectacular analysis on corpus")
    p_rerun.add_argument("--skip-existing", action="store_true",
                         help="Skip documents already processed")

    p_report = sub.add_parser("pattern-report",
                              help="Generate discourse pattern report + SVGs")

    args = parser.parse_args()
    dispatch = {
        "pattern-add": cmd_pattern_add,
        "pattern-rerun": cmd_pattern_rerun,
        "pattern-report": cmd_pattern_report,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
