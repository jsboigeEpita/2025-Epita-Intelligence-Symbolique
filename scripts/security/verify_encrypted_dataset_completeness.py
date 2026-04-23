# -*- coding: utf-8 -*-
"""
Verify that the encrypted canonical dataset contains all extracts from the
plaintext JSON files before deleting them from HEAD.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/security/verify_encrypted_dataset_completeness.py

Reads TEXT_CONFIG_PASSPHRASE from .env.
Exits 0 if encrypted dataset is a superset of plaintext; non-zero otherwise.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from argumentation_analysis.core.io_manager import load_extract_definitions  # noqa: E402
from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key  # noqa: E402


ENCRYPTED_PATH = ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
PLAINTEXT_PATHS = [
    ROOT / "Arg_Semantic_Index" / "sources" / "original_sources.json",
    ROOT / "Arg_Semantic_Index" / "sources" / "final_processed_config_unencrypted.json",
]


def load_plaintext(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_signature(source: dict) -> tuple:
    """Stable key for cross-file matching: name + extract count."""
    return (
        source.get("source_name", ""),
        len(source.get("extracts", []) or []),
    )


def extract_names(source: dict) -> set[str]:
    return {e.get("extract_name", "") for e in (source.get("extracts") or [])}


def main() -> int:
    load_dotenv(ROOT / ".env")
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        print("[FAIL] TEXT_CONFIG_PASSPHRASE not found in .env")
        return 2

    key = derive_encryption_key(passphrase)
    if not key:
        print("[FAIL] Could not derive encryption key from passphrase")
        return 2

    print(f"[INFO] Decrypting {ENCRYPTED_PATH.name}...")
    encrypted_defs = load_extract_definitions(
        config_file=ENCRYPTED_PATH,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )
    print(f"[INFO] Encrypted dataset: {len(encrypted_defs)} sources")

    enc_sigs = {extract_signature(s) for s in encrypted_defs}
    enc_names_per_source = {s.get("source_name", ""): extract_names(s) for s in encrypted_defs}

    all_ok = True

    for plaintext_path in PLAINTEXT_PATHS:
        if not plaintext_path.exists():
            print(f"[SKIP] {plaintext_path.name} not found")
            continue
        plain = load_plaintext(plaintext_path)
        print(f"\n[INFO] Checking {plaintext_path.name}: {len(plain)} sources")

        missing_sources = []
        partial_sources = []

        for src in plain:
            name = src.get("source_name", "")
            p_extracts = extract_names(src)
            e_extracts = enc_names_per_source.get(name)
            if e_extracts is None:
                missing_sources.append(name)
            else:
                missing_extracts = p_extracts - e_extracts
                if missing_extracts:
                    partial_sources.append((name, sorted(missing_extracts)))

        if missing_sources:
            print(f"  [FAIL] {len(missing_sources)} sources absent from encrypted dataset:")
            for n in missing_sources:
                print(f"    - {n!r}")
            all_ok = False
        if partial_sources:
            print(f"  [WARN] {len(partial_sources)} sources present but with missing extracts:")
            for name, missing in partial_sources:
                print(f"    - {name!r}: missing {missing}")
            # Treat as failure so we don't accidentally lose data
            all_ok = False
        if not missing_sources and not partial_sources:
            print(f"  [OK] All {len(plain)} sources + extracts present in encrypted dataset")

    print()
    if all_ok:
        print("[OK] Encrypted dataset is a superset of plaintext files. Safe to delete plaintext.")
        return 0
    else:
        print("[FAIL] Encrypted dataset is MISSING content. Do NOT delete plaintext files.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
