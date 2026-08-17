"""#1737 step 2 — acceptance run for the computed reading-head selection.

The coordinator's acceptance contract (R817): the selector is judged by the
#1770 head-nature instrument, whose features it does NOT use (independence
proven in tests/unit/argumentation_analysis/core/test_reading_window.py —
the two functions disagree on crafted inputs in both directions, so this
acceptance CAN fail).

Checks, per corpus and per production window (1500/2000/3000/4000):
- corpus_B (head = TOC, defect carrier): verdict at the SELECTED head must
  be ``prose``.
- corpus_A / corpus_C (heads already prose): selection must be offset 0 —
  a corpus that already reads prose keeps reading the same span — and the
  verdict stays ``prose``.
- The instrument's two calibration points still pass (B@0 = metadata,
  C@10400 = prose) — threshold drift would show there first.
- probe2: the whole run is executed twice and must hash identically.

Privacy HARD: in-memory dataset, opaque corpus IDs, numeric features and
offsets only; artifact under gitignored evaluation/results/real_analysis/.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/measure_1737_head_selection.py [--probe2]
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent.parent)

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from measure_1737_head_nature import (  # noqa: E402
    CORPUS_SRC_IDX,
    classify_head,
    head_features,
    load_corpus_text,
)
from argumentation_analysis.core.reading_window import select_reading_head  # noqa: E402

# The four distinct windows the anchored reading sites actually use.
WINDOWS = [1500, 2000, 3000, 4000]
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")


def run_once() -> dict:
    texts = {label: load_corpus_text(label) for label in CORPUS_SRC_IDX}
    report = {"calibration": [], "selections": []}

    for label, offset, expected in (("B", 0, "metadata"), ("C", 10400, "prose")):
        head = texts[label][offset : offset + 3000]
        got = classify_head(head_features(head))
        report["calibration"].append(
            {
                "corpus": f"corpus_{label}",
                "at": offset,
                "verdict": got,
                "expected": expected,
                "ok": got == expected,
            }
        )

    for label, text in texts.items():
        head0_verdict = classify_head(head_features(text[:3000]))
        for window in WINDOWS:
            sel = select_reading_head(text, window)
            window_text = text[sel.offset : sel.offset + window]
            feats = head_features(window_text)
            verdict = classify_head(feats)
            report["selections"].append(
                {
                    "corpus": f"corpus_{label}",
                    "window": window,
                    "selected_offset": sel.offset,
                    "status": sel.status,
                    "verdict_at_selection": verdict,
                    "head0_verdict_w3000": head0_verdict,
                    # acceptance verdicts only need the features, kept for audit
                    "avg_sentence_len": feats["avg_sentence_len"],
                    "alpha_ratio": feats["alpha_ratio"],
                    "sentences_per_kchar": feats["sentences_per_kchar"],
                    "year_tokens_per_kchar": feats["year_tokens_per_kchar"],
                    "list_marker_lines_pct": feats["list_marker_lines_pct"],
                    "top5gram_repetition_pct": feats["top5gram_repetition_pct"],
                }
            )
    return report


def check_acceptance(report: dict) -> bool:
    ok = all(c["ok"] for c in report["calibration"])
    for row in report["selections"]:
        if row["corpus"] == "corpus_B":
            ok = ok and row["verdict_at_selection"] == "prose"
        else:
            ok = ok and row["selected_offset"] == 0
            ok = ok and row["verdict_at_selection"] == "prose"
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe2", action="store_true")
    a = ap.parse_args()

    report = run_once()
    run_hash = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]

    if a.probe2:
        report2 = run_once()
        hash2 = hashlib.sha256(
            json.dumps(report2, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        print(f"probe1 hash: {run_hash}")
        print(f"probe2 hash: {hash2}")
        if run_hash != hash2:
            print("NON-DETERMINISM DETECTED — do not compare anything (R814)")
            sys.exit(1)

    accepted = check_acceptance(report)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RESULTS_DIR / f"measure_1737_head_selection_{ts}.json"
    with open(artifact, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated": ts,
                "rows_sha256_16": run_hash,
                "probe2": bool(a.probe2),
                "accepted": accepted,
                **report,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n=== #1737 step-2 acceptance (hash {run_hash}) ===")
    for c in report["calibration"]:
        print(
            f"calibration {c['corpus']}@{c['at']}: {c['verdict']} "
            f"(expected {c['expected']}) ok={c['ok']}"
        )
    for row in report["selections"]:
        print(
            f"{row['corpus']} w={row['window']}: offset={row['selected_offset']:>6} "
            f"status={row['status']:<28} verdict={row['verdict_at_selection']}"
        )
    print(f"ACCEPTED: {accepted}")
    print(f"artifact: {artifact}")
    if not accepted:
        sys.exit(1)


if __name__ == "__main__":
    main()
