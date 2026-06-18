"""R5 corpus scan — qualify virtuous-text candidates in the encrypted dataset.

Epic #1134 (Restitution) / Track R5 (#1159). Answers the owner's standing
question — *« le dataset en contient, peut-être pas assez »* — empirically and
honestly, by running the **volet-1 lexical candidate screen** (`identify`,
merged in R5 volet-1) over the real encrypted corpus.

Privacy HARD (CLAUDE.md dataset-privacy):
  - The dataset is loaded **encrypted-in-memory** via ``load_extract_definitions``
    + the derived key (``derive_encryption_key``), the same loader the rest of
    the codebase uses. It is never persisted decrypted.
  - Outputs carry **opaque IDs only** (``src_N_ext_M``). No ``source_name``,
    no path, no host, no ``raw_text`` / ``extract_text`` / ``full_text`` value.
  - The detailed inventory (which carries opaque IDs + metrics) is written
    under ``argumentation_analysis/evaluation/results/`` — gitignored by default
    (CLAUDE.md rule 3). Only an **opaque aggregate summary** (counts + rarity
    verdict + opaque candidate IDs, zero source names) is emitted as
    committable.

Anti-pendule (#1019/#369): the lexical screen is a recall-oriented candidate
generator, NOT a classifier. Its PRECISION is unknown without a pipeline run —
a text scoring ``density 0.0`` can be structurally fallacious (non sequitur,
circularity) or simply in an unmatched language/register. **This scan never
asserts a candidate is virtuous.** The DERIVED virtuous flag (spec §5.1,
``detect_virtuous_mode``) requires a pipeline run and is a separate, gated
step (po-2025's #1160 capstone). If the candidate pool is thin, this scan
**fails loud** on the rarity (manque documenté) — it does NOT lower the virtue
threshold to "find" entries.

Determinism: 0 LLM, 0 JVM, 0 API — pure lexical counts over in-memory text.

Usage::

    conda run -n projet-is --no-capture-output python scripts/scan_virtuous_corpus.py
    conda run -n projet-is --no-capture-output python scripts/scan_virtuous_corpus.py \\
        --min-chars 2000 --max-chars 50000 --max-density 0.2

Exits non-zero when the candidate pool is THIN (rarity fail-loud), so CI / a
caller cannot mistake a thin pool for success.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Resolve the repo root from this script's location (scripts/) so the tool runs
# from anywhere with the conda env active.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger("scan_virtuous_corpus")

_DATASET_PATH = _REPO_ROOT / "argumentation_analysis" / "data" / "extract_sources.json.gz.enc"
_RESULTS_DIR = _REPO_ROOT / "argumentation_analysis" / "evaluation" / "results"
_DETAIL_OUT = _RESULTS_DIR / "r5_virtuous_scan_inventory.md"
_AGGREGATE_OUT = _RESULTS_DIR / "r5_virtuous_scan_aggregate.json"

# The aggregate summary is the COMMITTABLE artifact. It carries opaque IDs only.
# The repo's .gitignore ignores evaluation/results/ wholesale, so we also drop a
# copy next to this script's notion of a committable location is NOT done here —
# the reviewer commits the aggregate JSON by path-exemption if they want it
# tracked (it is opaque by construction, so safe to track; but the default-ignored
# path is the privacy-safe choice). See README of this script's PR for the
# one-line `.gitignore` exemption if the aggregate is to be tracked.

_PASSPHRASE_ENV = "TEXT_CONFIG_PASSPHRASE"


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (the project's conda env does not auto-load .env).

    Reads ``KEY=value`` lines, ignoring comments/blanks. The passphrase lives in
    ``.env`` (gitignored); we load it explicitly rather than requiring the
    caller to export it. Never raises — a missing key surfaces as a clear error
    downstream (``derive_encryption_key`` needs the passphrase).
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError as exc:  # noqa: BLE001 — non-fatal: env may be set another way
        logger.warning("Could not read %s (%s); relying on exported env", path, exc)


def _load_dataset() -> List[Dict[str, Any]]:
    """Load + decrypt the corpus in memory. Returns the definitions list.

    Mirrors ``scripts/repro_soutenance_ee.load_corpus_c``: derive the key from
    the passphrase, hand it to ``load_extract_definitions``. The dataset never
    touches disk decrypted.
    """
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
    from argumentation_analysis.core.io_manager import load_extract_definitions

    passphrase = os.environ.get(_PASSPHRASE_ENV, "")
    if not passphrase:
        raise SystemExit(
            f"ABORT: {_PASSPHRASE_ENV} is not set. Load .env or export it before "
            "running this scan."
        )
    key = derive_encryption_key(passphrase)
    if not key:
        raise SystemExit(
            f"ABORT: key derivation from {_PASSPHRASE_ENV} returned None "
            "(empty passphrase?)."
        )
    if not _DATASET_PATH.exists():
        raise SystemExit(f"ABORT: encrypted dataset not found at {_DATASET_PATH}")
    # derive_encryption_key returns base64url bytes; load_extract_definitions is
    # annotated as ``Optional[str]`` but forwards to decrypt_data_with_fernet
    # which accepts ``Union[str, bytes]`` (io_manager.py:23 vs crypto_utils:153).
    # Decode to satisfy the str annotation while staying runtime-correct.
    defs = load_extract_definitions(_DATASET_PATH, key.decode("utf-8"))
    if not defs:
        raise SystemExit(
            "ABORT: load_extract_definitions returned an empty list — "
            "decryption failed or dataset is empty."
        )
    return defs


def _build_aggregate(inv: Any, *, min_chars: int, max_chars: int, max_density: float) -> Dict[str, Any]:
    """Build the opaque, committable aggregate summary from the inventory.

    Carries counts + the rarity verdict + the opaque candidate IDs. Zero source
    names, zero corpus text. The ``rarity`` fail-loud verdict is the headline.
    """
    return {
        "track": "R5 volet-1 corpus scan",
        "epic": "#1134",
        "issue": "#1159",
        "rarity_verdict": inv.rarity,
        "candidate_count": inv.candidate_count,
        "candidate_opaque_ids": [c.opaque_id for c in inv.candidates],
        "candidate_top_metrics": [
            {
                "opaque_id": c.opaque_id,
                "chars": c.char_count,
                "signal_total": c.signal_total,
                "signal_density_per_1k": c.signal_density,
            }
            for c in inv.candidates
        ],
        "corpus": {
            "sources": inv.total_sources,
            "extracts_total": inv.total_extracts,
            "extracts_with_text": inv.text_extracts,
            "extracts_metadata_only": inv.metadata_only_extracts,
            "size_brackets": dict(inv.size_brackets),
        },
        "screen": {
            "min_chars": min_chars,
            "max_chars": max_chars,
            "max_density_per_1k": max_density,
            "excluded_too_short": inv.excluded_too_short,
            "excluded_too_long": inv.excluded_too_long,
            "excluded_high_signal": inv.excluded_high_signal,
        },
        "caveat": (
            "CANDIDATE list (lexical screen, recall-oriented). The DERIVED "
            "virtuous flag needs a pipeline run (spec §5.1, detect_virtuous_mode) "
            "— unconfirmed here. A density-0 candidate can be structurally "
            "fallacious or in an unmatched language/register. Do not assert "
            "virtue without the run."
        ),
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan the encrypted corpus for virtuous-text candidates (opaque)."
    )
    parser.add_argument(
        "--min-chars", type=int, default=2000,
        help="min chars for a candidate (default 2000, ~300-400 words).",
    )
    parser.add_argument(
        "--max-chars", type=int, default=50000,
        help="max chars for a candidate (default 50000; larger = book).",
    )
    parser.add_argument(
        "--max-density", type=float, default=0.2,
        help="max lexical-signal density per 1k chars for a candidate (default 0.2).",
    )
    parser.add_argument(
        "--fail-loud-thin", action="store_true", default=True,
        help="exit non-zero when the pool is THIN (rarity fail-loud). Default on.",
    )
    parser.add_argument(
        "--no-fail-loud-thin", dest="fail_loud_thin", action="store_false",
        help="do NOT exit non-zero on a THIN pool (still report it).",
    )
    args = parser.parse_args(argv)

    _load_dotenv(_REPO_ROOT / ".env")
    defs = _load_dataset()

    from argumentation_analysis.reporting.restitution.virtuous_identification import (
        identify,
        render_inventory_report,
    )

    inv = identify(
        defs,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        max_density=args.max_density,
    )

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    detail_md = render_inventory_report(inv)
    _DETAIL_OUT.write_text(detail_md, encoding="utf-8")
    aggregate = _build_aggregate(
        inv,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        max_density=args.max_density,
    )
    _AGGREGATE_OUT.write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Console: opaque summary only (no source names, no prose). The detail lives
    # in the gitignored artifact.
    print(f"[scan] sources={inv.total_sources} extracts={inv.total_extracts} "
          f"(with_text={inv.text_extracts})")
    print(f"[scan] candidates={inv.candidate_count}  rarity={inv.rarity}")
    print(f"[scan] excluded short={inv.excluded_too_short} "
          f"long={inv.excluded_too_long} high_signal={inv.excluded_high_signal}")
    print(f"[scan] detail (gitignored): {_DETAIL_OUT}")
    print(f"[scan] aggregate (opaque, committable): {_AGGREGATE_OUT}")

    if args.fail_loud_thin and inv.rarity == "THIN":
        print(
            "[scan] FAIL-LOUD: candidate pool is THIN (≤2). The corpus barely "
            "supports a virtuous track — documented gap, not padded. Exit 2."
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
