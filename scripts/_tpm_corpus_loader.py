"""TPM-2 #1491 — Corpus loader (in-memory only, opaque IDs, privacy HARD).

Loads real-corpus ``extract_definitions`` from the Fernet-encrypted dataset
for trajectory analysis (TPM-2 #1491). The loader is a SEPARATE module
to keep ``scripts/extract_belief_trajectories.py`` synthetic-only — the
script never references the encrypted dataset path directly.

PRIVACY HARD contract:
- In-memory decrypt only (``load_extract_definitions``). NO plaintext disk.
- Opaque IDs on every surface (``prop_<8hex>``).
- Source name carried ONLY in the internal ``_source_label`` field for
  pipeline grouping (never persisted by this loader or its caller).
- The dataset path / passphrase are read from env (``TEXT_CONFIG_PASSPHRASE``)
  and never logged.
- Caller must NOT persist the returned text or any raw verbatim.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_corpus_definitions(corpus_id: str) -> List[Dict[str, Any]]:
    """Load the A/B/C subset of the encrypted corpus, decrypted in-memory.

    Returns a list of dicts with keys ``id``, ``source_name``, ``text``.
    The caller MUST NOT persist the plaintext fields to disk.
    """
    corpus_id = corpus_id.upper()
    if corpus_id not in ("A", "B", "C"):
        raise ValueError(f"Unknown corpus id: {corpus_id} (expected A/B/C)")

    repo_root = Path(__file__).resolve().parent.parent
    enc_path = (
        repo_root / "argumentation_analysis" / "data"
        / "extract_sources.json.gz.enc"
    )
    if not enc_path.exists():
        raise FileNotFoundError(
            f"Encrypted corpus not found at {enc_path}. "
            "Re-clone the repo or restore the encrypted dataset."
        )

    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        raise EnvironmentError(
            "TEXT_CONFIG_PASSPHRASE not set in env. "
            "Copy .env.example to .env and set the passphrase to decrypt the corpus."
        )

    # Late imports — keep this module's import graph small for the test path.
    from argumentation_analysis.core.utils.crypto_utils import (
        load_encryption_key,
    )
    from argumentation_analysis.core.io_manager import load_extract_definitions

    # `load_encryption_key` resolves the passphrase (arg > settings.passphrase)
    # and derives a Fernet-compatible b64url-encoded key (bytes). The runtime
    # accepts both ``str`` and ``bytes`` via ``decrypt_data_with_fernet``'s
    # ``Union[str, bytes]`` annotation, so we pass the bytes through directly.
    key = load_encryption_key(passphrase)
    all_defs = load_extract_definitions(
        config_file=enc_path,
        b64_derived_key=key,
        raise_on_decrypt_error=True,
    )

    # Deterministic 3-way partition by source name + id (alphabetical).
    sorted_defs = sorted(
        all_defs,
        key=lambda d: (d.get("source_name", ""), d.get("id", "")),
    )
    n = len(sorted_defs)
    if n == 0:
        raise ValueError("Encrypted corpus decrypted to 0 definitions.")
    third = n // 3
    if corpus_id == "A":
        return sorted_defs[:third] if third > 0 else sorted_defs[:1]
    if corpus_id == "B":
        return sorted_defs[third : 2 * third] if third > 0 else sorted_defs
    # C
    return sorted_defs[2 * third :] if third > 0 else sorted_defs[-1:]


def load_corpus_propositions(corpus_id: str) -> Dict[str, Dict[str, str]]:
    """Adapt real-corpus definitions to the {prop_id: meta} shape.

    Each definition → one proposition. The ``id`` is OPAQUE on every
    persistent surface (``prop_<8hex>``). The ``text`` is the only field
    the pipeline consumes (it is not written by the extractor).
    """
    defs = load_corpus_definitions(corpus_id)
    out: Dict[str, Dict[str, str]] = {}
    for d in defs:
        raw_id = str(d.get("id", ""))
        if not raw_id:
            continue
        # The encrypted dataset stores the document under ``full_text`` (the
        # extracts also carry ``extract_text``); it has no bare ``text`` key.
        # Map onto the single ``text`` field the pipeline consumes. This maps
        # into the IN-MEMORY dict only — the extractor persists LIGHT
        # aggregates, never the text (privacy HARD #1491).
        text = str(d.get("full_text", "") or d.get("text", "")).strip()
        if not text:
            continue
        opaque = "prop_" + hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:8]
        out[opaque] = {
            "text": text,
            # ``label`` is read by the run loop and PERSISTED as ``corpus_label``
            # in tpm.json — it MUST stay opaque for the real corpus. The real
            # source name lives only in ``_source_label`` (internal grouping,
            # never persisted by the extractor). Privacy HARD #1491.
            "label": f"corpus{corpus_id.upper()} · {opaque}",
            "_source_label": str(d.get("source_name", "unknown"))[:32],
        }
    if not out:
        raise ValueError(
            f"Corpus {corpus_id} produced 0 propositions after filtering "
            "(empty/non-extractable texts)."
        )
    return out
