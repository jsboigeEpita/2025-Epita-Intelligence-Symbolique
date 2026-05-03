#!/usr/bin/env python3
"""Add an extract to the encrypted dataset.

Usage:
    python scripts/dataset/add_extract.py \
        --source-name "Speaker Name" \
        --extract-text-file /path/to/plaintext.txt \
        --metadata "discourse_type=populist,era=2025,regime_type=democracy"

Workflow:
    1. Load encrypted dataset in memory
    2. Read plaintext from user-supplied file (never committed)
    3. Append extract with metadata
    4. Re-encrypt and save
    5. Print opaque ID for use in PRs/dashboards

Privacy: the plaintext file is never persisted under a tracked path.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Repo root = 3 levels up from this script.
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "argumentation_analysis" / "data"
ENCRYPTED_PATH = DATA_DIR / "extract_sources.json.gz.enc"


def _is_tracked(file_path: Path) -> bool:
    """Return True if *file_path* is tracked by git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(file_path)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _parse_metadata(raw: str) -> dict[str, str]:
    """Parse 'key=val,key2=val2' into a dict."""
    meta: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            meta[k.strip()] = v.strip()
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add an extract to the encrypted dataset."
    )
    parser.add_argument(
        "--source-name", required=True, help="Display name of the source."
    )
    parser.add_argument(
        "--extract-text-file",
        required=True,
        type=Path,
        help="Path to a local plaintext file (never committed).",
    )
    parser.add_argument(
        "--metadata",
        default="",
        help="Comma-separated key=value pairs (e.g. 'discourse_type=populist,era=2025').",
    )
    args = parser.parse_args(argv)

    text_file = args.extract_text_file.resolve()

    # --- Privacy guard ---
    if _is_tracked(text_file):
        print(
            f"ERROR: {text_file} is tracked by git. "
            "Provide a plaintext file outside the repo or gitignored.",
            file=sys.stderr,
        )
        return 1

    if not text_file.exists():
        print(f"ERROR: file not found: {text_file}", file=sys.stderr)
        return 1

    plaintext = text_file.read_text(encoding="utf-8").strip()
    if not plaintext:
        print("ERROR: empty plaintext file.", file=sys.stderr)
        return 1

    # --- Load encrypted dataset ---
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")

    import os

    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        print("ERROR: TEXT_CONFIG_PASSPHRASE not set in .env", file=sys.stderr)
        return 1

    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import (
        load_extract_definitions,
        save_extract_definitions,
    )

    key = derive_encryption_key(passphrase)
    if not key:
        print("ERROR: failed to derive encryption key.", file=sys.stderr)
        return 1

    b64_key = key.decode("utf-8")

    definitions = load_extract_definitions(
        config_file=ENCRYPTED_PATH,
        b64_derived_key=b64_key,
        raise_on_decrypt_error=True,
    )

    # --- Build new extract entry ---
    metadata = _parse_metadata(args.metadata) if args.metadata else {}
    new_extract = {
        "source_name": args.source_name,
        "source_type": metadata.get("source_type", "text"),
        "schema": "v1",
        "host_parts": metadata.get("host_parts", "local").split(","),
        "path": metadata.get("path", ""),
        "extracts": [
            {
                "full_text": plaintext,
                "num_extract": 1,
                "metadata": metadata,
            }
        ],
    }

    definitions.append(new_extract)

    # --- Save re-encrypted ---
    ok = save_extract_definitions(
        extract_definitions=definitions,
        config_file=ENCRYPTED_PATH,
        b64_derived_key=b64_key,
        embed_full_text=True,
        text_retriever=lambda x: plaintext,
    )
    if not ok:
        print("ERROR: failed to save encrypted dataset.", file=sys.stderr)
        return 1

    # --- Print opaque ID ---
    from argumentation_analysis.evaluation.opaque_id import opaque_id

    oid = opaque_id(args.source_name)
    print(f"OK — extract added. opaque_id: {oid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
