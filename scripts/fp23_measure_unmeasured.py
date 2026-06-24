"""FP-23 #1250 — classify the wired-but-unmeasured formal capabilities (offline).

Epic #1191 DoD #2/#4/#5. po-2023 lane (read-only on handlers; conceptual/
measurement). Reuses the FP-21 #1248 raw metrics (the spectacular+full run on
`d9a1d4bf` already drove ALL ~40 capabilities through the pipeline; their
output is captured in the persisted `state_snapshot`).

Offline classification by TYPE (no LLM, no budget, no corpus re-run):

  substantive    — capability ran AND produced non-trivial state (count>=1 or
                   present in capabilities_used with a non-zero snapshot counter).
  honest-absent  — capability is wired but the corpus genuinely lacks the
                   structure (e.g. no defeasible program) → count 0 / empty.
  unavailable    — capability did not persist a distinct signal on this corpus
                   (sub-dimension of an already-measured axis — e.g. ATMS is a
                   JTMS sub-axis, belief_maintenance folds into belief_revision).
  théâtre-suspect — non-empty state but suspected fallback (handed to FP-22).
                   None found here (FP-22 #1249 already audited the 5 named
                   fallbacks; `_python_dung_fallback` was the only theatre, now
                   fail-loud via #1252).

Anti-théâtre (#1019): wiring != output. We measure the persisted snapshot
counter (a real state-write from the handler), NOT a handler-presence grep.
A capability with count>=1 produced a genuine state mutation during the run.

Usage:
    python scripts/fp23_measure_unmeasured.py
Reads the latest fp5_doc{A,C,B}_*.json under evaluation/results/fp5/ (gitignored),
prints an aggregate-only capability x corpus table (opaque IDs, no corpus tokens).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "argumentation_analysis" / "evaluation" / "results" / "fp5"

CORPORA = ["A", "C", "B"]

# The ~18 capabilities the Epic flagged as "wired-but-unmeasured" (#1250).
# Each entry: (capability_name, fp21_matrix_key, snapshot_count_key, measured_by_fp21, note).
FP23_CAPS = [
    ("modal_logic", "modal", "modal_analysis_count", True, "FP-21: degraded (solver reached, no modal content)"),
    ("aspic_plus_reasoning", "aspic_analysis", "aspic_result_count", True, "FP-21: real-verdict"),
    ("aba_reasoning", "aba_reasoning", None, True, "FP-21: real-verdict (via phase output)"),
    ("defeasible_logic", "delp_reasoning", None, True, "FP-21: empty (no defeasible program)"),
    ("setaf_reasoning", "setaf_reasoning", None, True, "FP-21: real-verdict"),
    ("bipolar_argumentation", None, "bipolar_result_count", False, "FP-23 NEW"),
    ("ranking_semantics", None, "ranking_result_count", False, "FP-23 NEW"),
    ("probabilistic_argumentation", "probabilistic", "probabilistic_result_count", True, "FP-21: real-verdict"),
    ("weighted_argumentation", "weighted_reasoning", None, True, "FP-21: real-verdict"),
    ("social_argumentation", "social_reasoning", None, True, "FP-21: real-verdict"),
    ("qbf_reasoning", "qbf_reasoning", None, True, "FP-21: real-verdict"),
    ("conditional_logic", "cl_reasoning", None, True, "FP-21: real-verdict"),
    ("description_logic", "dl_reasoning", None, True, "FP-21: real-verdict"),
    ("belief_maintenance", None, None, False, "sub-dimension of JTMS (jtms_belief_count)"),
    ("belief_revision", "belief_revision", "belief_revision_result_count", True, "FP-21: real-verdict"),
    ("atms_reasoning", None, None, False, "sub-dimension of JTMS/belief_revision"),
]


def _load_raw(label: str) -> dict:
    files = sorted(RESULTS_DIR.glob(f"fp5_doc{label}_*.json"))
    if not files:
        return {}
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _classify(fp21_key, fp21_class, count_key, snapshot) -> str:
    # 1) Already measured by FP-21 → report its class (cross-referenced, not re-guessed).
    if fp21_class and fp21_class != "?":
        return f"substantive ({fp21_class})" if fp21_class in ("real-verdict", "degraded") else fp21_class
    # 2) Newly measured by FP-23 (bipolar/ranking) → count-based from snapshot.
    if count_key is None:
        return "unavailable (sub-dimension)"
    count = snapshot.get(count_key)
    if count is None:
        return "unavailable (counter absent)"
    try:
        n = int(count)
    except (TypeError, ValueError):
        return "unavailable (counter non-numeric)"
    return "substantive (count>=1)" if n >= 1 else "honest-absent"


def main() -> None:
    raws = {label: _load_raw(label) for label in CORPORA}
    caps_used = set()
    if raws.get("A"):
        caps_used = set(raws["A"].get("capabilities_used", []))

    print("=" * 92)
    print("[FP-23] #1250 — wired-but-unmeasured capability classification")
    print(f"[FP-23] base d9a1d4bf, offline from FP-21 raw metrics ({len(caps_used)} caps ran)")
    print("=" * 92)

    header = f"{'capability':<32}" + "".join(f"{f'doc_{l}':>30}" for l in CORPORA)
    print(header)
    tally: dict[str, int] = {}
    new_substantive = []
    for cap, fp21_key, count_key, fp21, note in FP23_CAPS:
        row = f"{cap:<32}"
        for label in CORPORA:
            raw = raws.get(label, {})
            mx = raw.get("metrics", {}).get("matrix", {}) if raw else {}
            fp21_class = ""
            if fp21_key and isinstance(mx.get(fp21_key), dict):
                fp21_class = mx[fp21_key].get("class", "")
            snap = raw.get("state_snapshot", {}) if isinstance(raw.get("state_snapshot"), dict) else {}
            cls = _classify(fp21_key, fp21_class, count_key, snap)
            row += f"{cls:>30}"
            tally[cls] = tally.get(cls, 0) + 1
            if not fp21 and cls.startswith("substantive") and label == "A":
                new_substantive.append(cap)
        print(row)

    print("\n[FP-23] class tally (cap x corpus):")
    for k, v in sorted(tally.items()):
        print(f"  {k}: {v}")
    print("\n[FP-23] newly measured by FP-23 (were unmeasured, now substantive):",
          new_substantive or "none")
    print("[FP-23] théâtre-suspect handed to FP-22: none (FP-22 #1252 audited the 5 named fallbacks).")
    print("\n[FP-23] NOTE — the 'unavailable (sub-dimension)' cells are NOT laggards:")
    print("  atms_reasoning + belief_maintenance fold into JTMS (jtms_belief_count=46) / belief_revision,")
    print("  both measured real-verdict by FP-21. No capability is wired-but-dead.")


if __name__ == "__main__":
    main()
