"""S6-B #1506 — Tier faible-charge (fables) scaffold validator.

S6-B is the **design phase** of the encrypted-extracts port for CoursIA
strate-6. Per the issue body, **port réel APRÈS acceptation du grounding**
(S6-A1 acceptance on PR #1516). This script is the **validation scaffold**
on the *weak-load tier* (fables/mythes, public-domain, opaque ids).

It does **NOT** perform the port. It validates that the existing encryption
pipeline
(`argumentation_analysis.core.io_manager` +
 `argumentation_analysis.core.utils.crypto_utils`) round-trips a tiny,
self-contained, fables-tier payload through:

1. **plaintext → encrypted blob on disk** (`save_extract_definitions`)
2. **encrypted blob on disk → plaintext in memory** (`load_extract_definitions`)
3. **invariants check** (schema, opaque ids, 0 raw_text field leaks)

Privacy HARD: the scaffold writes a small encrypted blob
(`fables_tier.json.gz.enc`) under `argumentation_analysis/data/` — same
directory as the canonical encrypted corpus. It NEVER writes plaintext to
disk (the in-memory payload is discarded at function return). The script
self-destructs the plaintext blob at the end if `--cleanup-plain` is passed.

Why fables tier first: per the issue body, "fables/mythes d'abord (tier
faible-charge)". Fables are public-domain La Fontaine (Fables, 1668-1694)
and Aesop (6th century BC) — zero political sensitivity, zero contemporary
figures, exactly the weak-load smoke we need to prove the encryption
pipeline before the real port.

Anti-pendule: the scaffold does NOT pre-build the port. It validates the
existing IO + crypto chain. The real port waits for S6-A1 acceptance.

Usage:
    # In-memory only (no disk write of plaintext):
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/coursia_s6b/validate_fables_tier.py --dry-run

    # Full round-trip on the canonical encrypted dataset location:
    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/coursia_s6b/validate_fables_tier.py

Output:
    - ``argumentation_analysis/data/fables_tier.json.gz.enc`` (encrypted blob)
    - JSON summary to stdout (opaque ids only)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from argumentation_analysis.core.io_manager import (  # noqa: E402
    load_extract_definitions,
    save_extract_definitions,
)
from argumentation_analysis.core.utils.crypto_utils import (  # noqa: E402
    derive_encryption_key,
)

S6B_BLOB_NAME = "fables_tier.json.gz.enc"
S6B_BLOB_PATH = REPO_ROOT / "argumentation_analysis" / "data" / S6B_BLOB_NAME

logger = logging.getLogger("coursia_s6b")
# Do NOT attach a StreamHandler: root logger already configures one in
# __main__. Attaching one here doubles every line.
logger.setLevel(logging.INFO)
logger.propagate = True


# ---------------------------------------------------------------------------
# Tier faible-charge : fables domaine public (La Fontaine, Aesop).
# Contenus délibérément courts (1-2 phrases chacun), IDs opaques `fable_*`.
# Privacy HARD : aucun nom d'auteur, aucune date, aucun contenu polémique.
# Le champ `text` est *seulement* généré en mémoire (jamais persisté en clair
# sauf dans le blob chiffré).
# ---------------------------------------------------------------------------

_FABLES_TIER: List[Dict[str, Any]] = [
    {
        # `source_name` is the validator's primary opaque-id field. We use the
        # same `id` form (prefixed `fable_*`) for consistency on this surface.
        "source_name": "fable_tier_corpus_a",
        "source_type": "fables_public_domain",
        "schema": "extract_definition_v1",
        # `host_parts` MUST be a list (real-corpora use a structured list of
        # URL segments). For the local fables blob we use an opaque placeholder.
        "host_parts": ["fables_tier", "corpus_a"],
        "path": "argumentation_analysis/data/fables_tier.json.gz.enc",
        "id": "fable_tier_corpus_a",
        "title_placeholder": "fable_domain_public_corpus_a",
        "extracts": [
            {
                "extract_name": "fable_001_ext_0",
                "start_marker": "fable_001_debut",
                "end_marker": "fable_001_fin",
                "host_parts": ["fables_tier", "fable_001_ext_0"],
                "path": "/dev/null/fables_tier/fable_001_ext_0",
                "text": (
                    "Corpus fables-tier : placeholder court généré in-memory. "
                    "Contenu public-domain, zero sensibilité politique. "
                    "Domaine public ; exemple : La Fontaine, Fables, 1668."
                ),
            }
        ],
    },
    {
        "source_name": "fable_tier_corpus_b",
        "source_type": "fables_public_domain",
        "schema": "extract_definition_v1",
        "host_parts": ["fables_tier", "corpus_b"],
        "path": "argumentation_analysis/data/fables_tier.json.gz.enc",
        "id": "fable_tier_corpus_b",
        "title_placeholder": "fable_domain_public_corpus_b",
        "extracts": [
            {
                "extract_name": "fable_002_ext_0",
                "start_marker": "fable_002_debut",
                "end_marker": "fable_002_fin",
                "host_parts": ["fables_tier", "fable_002_ext_0"],
                "path": "/dev/null/fables_tier/fable_002_ext_0",
                "text": (
                    "Corpus fables-tier : placeholder court généré in-memory. "
                    "Contenu public-domain, zero sensibilité politique."
                ),
            }
        ],
    },
    {
        "source_name": "fable_tier_corpus_c",
        "source_type": "fables_public_domain",
        "schema": "extract_definition_v1",
        "host_parts": ["fables_tier", "corpus_c"],
        "path": "argumentation_analysis/data/fables_tier.json.gz.enc",
        "id": "fable_tier_corpus_c",
        "title_placeholder": "fable_domain_public_corpus_c",
        "extracts": [
            {
                "extract_name": "fable_003_ext_0",
                "start_marker": "fable_003_debut",
                "end_marker": "fable_003_fin",
                "host_parts": ["fables_tier", "fable_003_ext_0"],
                "path": "/dev/null/fables_tier/fable_003_ext_0",
                "text": (
                    "Corpus fables-tier : placeholder court généré in-memory. "
                    "Contenu public-domain, zero sensibilité politique."
                ),
            }
        ],
    },
]


def _strip_text_fields(defs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy with all `text` / `full_text` fields popped.

    Privacy HARD: the in-memory payload returned to the caller must NEVER
    carry plaintext field names. The encrypted blob keeps them (encrypted),
    but every artifact emitted by this validator must be opaque-id-only.
    """
    cleaned: List[Dict[str, Any]] = []
    for d in defs:
        d_clean = {k: v for k, v in d.items() if k not in ("text", "full_text")}
        d_clean["extracts"] = [
            {k: v for k, v in ext.items() if k not in ("text", "full_text")}
            for ext in d.get("extracts", [])
        ]
        cleaned.append(d_clean)
    return cleaned


def _summary(defs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Opaque-id-only summary for the [DONE] report."""
    return {
        "n_sources": len(defs),
        "n_extracts_total": sum(len(d.get("extracts", [])) for d in defs),
        "ids": [d.get("id") for d in defs],
        "blob_path": str(S6B_BLOB_PATH.relative_to(REPO_ROOT)),
        "blob_name": S6B_BLOB_NAME,
        "tier": "fables_public_domain_weak_load",
    }


def _round_trip(passphrase: str) -> Dict[str, Any]:
    """Validate the existing IO + crypto chain end-to-end on the fables tier.

    Steps (anti-pendule: reuse existing functions, do NOT re-implement):
      1. **Strip plaintext fields in memory** before save (the encrypted blob
         carries opaque-id metadata only — the real text stays in the source
         document, fetched on-demand via ``text_retriever``). The
         ``save_extract_definitions`` flag ``embed_full_text`` controls
         ``full_text`` only, not ``text``; the right fix is to strip at the
         source.
      2. ``save_extract_definitions`` writes an encrypted blob to disk.
      3. ``load_extract_definitions`` reads it back, decrypts, validates.
      4. Schema + opaque-id + no-`text`-in-loaded-extract invariants verified.
    """
    key = derive_encryption_key(passphrase)
    if not key:
        raise RuntimeError("derive_encryption_key returned None (empty passphrase?)")
    # ``derive_encryption_key`` returns base64url-encoded bytes; ``load_extract_definitions``
    # expects ``str | None`` per its signature.
    key_str: str = key.decode("ascii")

    # ---- 1a. strip plaintext fields in memory (privacy HARD) ----
    payload_to_save = _strip_text_fields(_FABLES_TIER)

    # ---- 1b. write encrypted blob ----
    S6B_BLOB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ok = save_extract_definitions(
        extract_definitions=payload_to_save,
        config_file=S6B_BLOB_PATH,
        b64_derived_key=key_str,
        embed_full_text=False,
        config=None,
        text_retriever=None,
    )
    if not ok:
        raise RuntimeError(f"save_extract_definitions failed for {S6B_BLOB_PATH}")

    # ---- 2. read encrypted blob back ----
    loaded = load_extract_definitions(
        config_file=S6B_BLOB_PATH,
        b64_derived_key=key_str,
        app_config=None,
        raise_on_decrypt_error=True,
        fallback_definitions=None,
    )

    # ---- 3. invariants ----
    # 3a. schema: list of dicts with required keys (per io_manager L97-106)
    assert isinstance(loaded, list), f"expected list, got {type(loaded).__name__}"
    for d in loaded:
        assert isinstance(d, dict)
        for required_key in (
            "source_name",
            "source_type",
            "schema",
            "host_parts",
            "path",
            "extracts",
        ):
            assert required_key in d, (
                f"missing key {required_key!r} in {d.get('source_name')!r}"
            )

    # 3b. opaque-id only: every source_name starts with `fable_tier_`
    for d in loaded:
        sn = d.get("source_name", "")
        assert sn.startswith("fable_tier_"), (
            f"non-fable source_name leaked: {sn!r}"
        )

    # 3c. NO plaintext leak: stripped before save, so loaded extracts must
    # not carry `text` / `full_text`.
    for d in loaded:
        for ext in d.get("extracts", []):
            assert "text" not in ext, "plaintext `text` leaked in loaded extract"
            assert "full_text" not in ext, (
                "plaintext `full_text` leaked in loaded extract"
            )

    return _summary(loaded)


def _dry_run() -> int:
    """Print the contract + invariants without touching disk."""
    logger.info("S6-B #1506 — fables-tier scaffold dry-run")
    logger.info("Tier: fables_public_domain_weak_load (La Fontaine, Aesop)")
    logger.info("Blob (would-write): %s", S6B_BLOB_PATH.relative_to(REPO_ROOT))
    logger.info("Source name on this surface: opaque (fable_*)")
    logger.info("Round-trip steps:")
    logger.info("  1. save_extract_definitions (existing IO) -> encrypted blob")
    logger.info("  2. load_extract_definitions (existing IO) -> in-memory dict")
    logger.info("  3. invariants: schema + opaque-ids + no plaintext leak")
    logger.info(
        "Port réel différé : en attente acceptation S6-A1 #1516 (PR ouverte)."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "S6-B #1506 — fables-tier scaffold validator "
            "(design phase, NO real port)"
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the contract + invariants without touching disk.",
    )
    parser.add_argument(
        "--cleanup-blob",
        action="store_true",
        help=(
            "After the round-trip + invariants check, delete the encrypted "
            "blob. Use to keep the fables-tier scaffold invisible from HEAD "
            "after local validation."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
    )
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.dry_run:
        return _dry_run()

    load_dotenv(REPO_ROOT / ".env")
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logger.error("TEXT_CONFIG_PASSPHRASE not found in .env")
        return 2

    summary = _round_trip(passphrase)
    logger.info("Round-trip OK: %s", json.dumps(summary, ensure_ascii=False))

    if args.cleanup_blob:
        try:
            S6B_BLOB_PATH.unlink()
            logger.info("Encrypted blob removed (--cleanup-blob).")
        except FileNotFoundError:
            logger.warning("Encrypted blob already absent.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())