"""Real (NON-anonymized) spectacular analysis — for the data owner's local inspection.

Runs the full `spectacular` + `fallacy_tier:"full"` pipeline on ONE real corpus and
renders BOTH:
  - a full unscrubbed state snapshot (JSON, ground truth)
  - a readable Markdown digest with REAL names (arguments, located fallacies + taxonomy
    path, formal formulas + Tweety verdicts, quality virtues + exhibits, LLM synthesis)

Output lands under argumentation_analysis/evaluation/results/real_analysis/ which is
GITIGNORED (.gitignore line 70). This is the owner's local view — NEVER commit it,
NEVER post its content to dashboard / PR / chat. Opaque-ID discipline still governs
everything that reaches git; this artifact stays on disk.

Usage:
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_real_analysis.py --corpus A
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_real_analysis.py --corpus A --mode conversational

``--mode`` selects the orchestration path (#1668 item 5-bis):
  * ``pipeline`` (default) — sequential DAG via ``run_unified_analysis`` workflow
    ``spectacular``. The historic, unchanged behaviour.
  * ``conversational`` — SK AgentGroupChat multi-agent dialogue via
    ``run_conversational_analysis`` (``workflow_name="conversational"``). The
    runner surfaces ``execution_path`` (agent_group_chat / round_robin_fallback)
    and detects a silent fallback to pipeline (the conversational path raises
    inside ``run_unified_analysis`` and is swallowed back to ``standard``) by
    the absence of the conversational result keys — fail-loud, anti-#1019.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}
RESULTS_DIR = Path("argumentation_analysis/evaluation/results/real_analysis")
DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")

# Mode → run_unified_analysis workflow_name. The pipeline mode is the historic
# ``spectacular`` workflow; the conversational mode routes through
# ``run_conversational_analysis`` inside ``run_unified_analysis``. Kept as a
# standalone mapping so the routing is unit-testable without an API run.
MODE_TO_WORKFLOW: Dict[str, str] = {
    "pipeline": "spectacular",
    "conversational": "conversational",
}

# Result keys that distinguish a genuine conversational run from a pipeline
# fallback (run_unified_analysis swallows a conversational exception back to
# ``standard``). Used to detect the silent fallback — anti-#1019.
_CONV_RESULT_KEYS = ("conversation_log", "execution_path")


def is_conversational_fallback(mode: str, result: Any) -> bool:
    """Did a ``--mode conversational`` run silently fall back to the pipeline?

    ``run_unified_analysis`` swallows a conversational exception back to the
    ``standard`` workflow and returns a pipeline result. A mode-conversational
    run that returns a result without any conversational key
    (``conversation_log`` / ``execution_path``) is NOT a conversational verdict
    — the two call opposite paths, and reading the fallback as the mode asked
    for would measure the wrong voie (#1668 item 5-bis anti-#1019). Pure
    function (no I/O) so the detection is unit-testable without an API run.
    """
    if mode != "conversational":
        return False
    if not isinstance(result, dict):
        return True
    return not any(k in result for k in _CONV_RESULT_KEYS)


def load_corpus(label: str, max_chars: int = 60000) -> Dict[str, Any]:
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(DATASET_PATH, key)
    entry = defs[CORPUS_SRC_IDX[label]]
    text = entry.get("full_text", "") or ""
    meta = {
        k: v
        for k, v in entry.items()
        if k != "full_text" and not isinstance(v, (list, dict))
    }
    return {"text": text[:max_chars], "raw_len": len(text), "meta": meta}


def _md_section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body}\n"


def _fmt(v: Any, indent: int = 0) -> str:
    """Compact readable rendering of an arbitrary snapshot value."""
    pad = "  " * indent
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)) or v is None:
        return str(v)
    if isinstance(v, list):
        if not v:
            return "(vide)"
        return "\n".join(f"{pad}- {_fmt(x, indent + 1)}" for x in v[:50])
    if isinstance(v, dict):
        if not v:
            return "(vide)"
        lines = []
        for k, val in list(v.items())[:50]:
            rendered = _fmt(val, indent + 1)
            if "\n" in rendered:
                lines.append(f"{pad}**{k}**:\n{rendered}")
            else:
                lines.append(f"{pad}**{k}**: {rendered}")
        return "\n".join(lines)
    return str(v)


def render_markdown(
    snap: Dict[str, Any],
    corpus: Dict[str, Any],
    label: str,
    elapsed: float,
    summary: Dict[str, Any] | None = None,
    mode: str = "pipeline",
    execution_path: str | None = None,
    conversational_fallback: bool = False,
) -> str:
    md = [f"# Analyse réelle (non-anonymisée) — corpus {label}", ""]
    md.append(f"> Généré localement, chemin GITIGNORED. Ne pas committer / publier.")
    mode_line = f"> Mode: `{mode}` — {elapsed:.1f}s — corpus {corpus['raw_len']} chars (tronqué à {len(corpus['text'])})."
    if mode == "conversational":
        path_str = execution_path or "—"
        mode_line += f" — execution_path: `{path_str}`"
        if conversational_fallback:
            mode_line += " — ⚠ FALLBACK pipeline (voie conversationnelle non atteinte)"
    else:
        mode_line += " — workflow: `spectacular` + `fallacy_tier:full`"
    md.append(mode_line)
    md.append("")
    md.append("## Identité réelle du corpus (métadonnées source)")
    md.append("")
    md.append(_fmt(corpus["meta"]))

    # 0. Phase status — honest view of what actually ran
    if summary:
        done = summary.get("completed_phases", [])
        failed = summary.get("failed_phases", [])
        skipped = summary.get("skipped_phases", [])
        body = [
            f"- **Complétées ({len(done)})**: {', '.join(done) if done else '(aucune)'}",
            f"- **Échouées ({len(failed)})**: {', '.join(failed) if failed else '(aucune)'}",
            f"- **Sautées ({len(skipped)})**: {', '.join(skipped) if skipped else '(aucune)'}",
        ]
        md.append(
            _md_section("0. Statut des phases (transparence run)", "\n".join(body))
        )

    # 1. Arguments
    args = snap.get("identified_arguments", {})
    if isinstance(args, dict) and args:
        body = []
        for aid, a in list(args.items())[:60]:
            if isinstance(a, dict):
                desc = a.get("description") or a.get("text") or a.get("thesis") or ""
                body.append(f"- **{aid}** — {desc}")
            else:
                body.append(f"- **{aid}** — {a}")
        md.append(_md_section(f"1. Arguments extraits ({len(args)})", "\n".join(body)))

    # 2. Fallacies (located, real text + taxonomy)
    fals = snap.get("identified_fallacies", {})
    if isinstance(fals, dict) and fals:
        body = []
        for fid, f in list(fals.items())[:80]:
            if not isinstance(f, dict):
                body.append(f"- **{fid}** — {f}")
                continue
            ftype = f.get("fallacy_type", f.get("type", "?"))
            fam = f.get("family", "")
            path = f.get("taxonomy_path", "")
            just = f.get("justification", "")
            tgt = f.get("target_arg_id", "")
            head = f"- **{ftype}**"
            if fam:
                head += f" _(famille: {fam})_"
            if path:
                head += f" — taxo: `{path}`"
            if tgt:
                head += f" → {tgt}"
            body.append(head + (f"\n    {just}" if just else ""))
        md.append(
            _md_section(
                f"2. Sophismes localisés ({len(fals)}) — descente taxonomie",
                "\n".join(body),
            )
        )
    else:
        md.append(
            _md_section(
                "2. Sophismes localisés (0) — descente taxonomie",
                "_(aucun sophisme — vérifier le statut de la phase `hierarchical_fallacy` "
                "en section 0 ; 0 alors qu'elle est complétée = anomalie d'extraction amont)_",
            )
        )

    # 3. Formal reasoning
    for key, title in [
        (
            "propositional_analysis_results",
            "3a. Logique propositionnelle (PL) — vérifiée Tweety",
        ),
        ("fol_analysis_results", "3b. Logique du 1er ordre (FOL) — vérifiée Tweety"),
        ("modal_analysis_results", "3c. Logique modale — vérifiée Tweety"),
    ]:
        r = snap.get(key)
        if r:
            md.append(_md_section(title, _fmt(r)))

    # 4. Dung
    dung = snap.get("dung_frameworks", snap.get("dung_extensions"))
    if dung:
        md.append(
            _md_section("4. Argumentation abstraite (Dung) — extensions", _fmt(dung))
        )

    # 5. Quality virtues + exhibits
    q = snap.get("argument_quality_scores", snap.get("quality_evaluation"))
    if q:
        md.append(_md_section("5. Qualité — 9 vertus (+ exhibits agentiques)", _fmt(q)))

    # 6. Counter-arguments
    ca = snap.get("counter_arguments")
    if ca:
        md.append(_md_section("6. Contre-arguments (5 stratégies)", _fmt(ca)))

    # 7. Synthesis (the LLM prose — REAL). Keys vary by phase; render whatever exists,
    # honestly note the empties (the owner wants to see exactly what the run produced).
    synth_keys = [
        ("narrative_synthesis", "7a. Synthèse narrative (LLM)"),
        ("analysis_synthesis", "7b. Synthèse d'analyse (phase `synthesis`)"),
        ("deep_synthesis", "7c. Synthèse profonde (phase `deep_synthesis`)"),
        ("formal_synthesis_reports", "7d. Synthèse formelle (Tweety)"),
        ("final_conclusion", "7e. Conclusion finale"),
    ]
    seen = {k for k, _ in synth_keys}
    # catch any other synthesis-ish top-level key we didn't name explicitly
    for k in sorted(snap.keys()):
        if k not in seen and ("synth" in k.lower() or "conclus" in k.lower()):
            synth_keys.append((k, f"7z. {k}"))
    sec = []
    for key, title in synth_keys:
        v = snap.get(key)
        if v:
            sec.append(f"### {title}\n\n{_fmt(v)}")
        else:
            sec.append(
                f"### {title}\n\n_(vide — phase non exécutée ou sans sortie LLM ce run)_"
            )
    md.append(_md_section("7. Synthèses (prose LLM réelle)", "\n\n".join(sec)))

    # 8. JTMS / governance / debate
    for key, title in [
        ("jtms_beliefs", "8a. JTMS — croyances / justifications"),
        ("governance_decisions", "8b. Gouvernance — votes / consensus"),
        ("debate_transcripts", "8c. Débat adversarial"),
    ]:
        v = snap.get(key)
        if v:
            md.append(_md_section(title, _fmt(v)))

    return "\n".join(md)


async def main_async(label: str, mode: str = "pipeline") -> None:
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    if mode not in MODE_TO_WORKFLOW:
        raise ValueError(f"unknown mode '{mode}'; choose from {list(MODE_TO_WORKFLOW)}")
    workflow_name = MODE_TO_WORKFLOW[mode]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus(label)
    print(
        f"[REAL] corpus {label}: {corpus['raw_len']} chars (using {len(corpus['text'])})"
    )
    print(f"[REAL] meta: {corpus['meta']}")
    print(f"[REAL] mode: {mode} (workflow_name={workflow_name})")

    # NO shield_config: (a) the owner wants the REAL non-anonymized view, the shield
    # injects an opaque-ID directive; (b) shield_config switches the workflow name to
    # 'shielded_spectacular_analysis', which makes the `workflow_name == "spectacular"`
    # JPype-warmup guard FALSE -> JVM never warms -> the Tweety phases all fail. Plain
    # `spectacular` is what FB-37 ran (38 fallacies / 138 args). Subtraction, not counterweight.
    context = {"fallacy_tier": "full"}
    t0 = time.time()
    result = await run_unified_analysis(
        text=corpus["text"], workflow_name=workflow_name, context=context
    )
    elapsed = time.time() - t0
    print(f"[REAL] pipeline done in {elapsed:.1f}s")

    # Fail-loud on the silent conversational→pipeline fallback (#1668 item 5-bis
    # anti-#1019): run_unified_analysis swallows a conversational exception back
    # to ``standard``. A mode-conversational run that returns a pipeline result
    # (no conversation_log / execution_path) is NOT a conversational verdict —
    # the two call opposite paths, and reading the fallback as the mode asked
    # for would measure the wrong voie. The proof of presence is these keys.
    if is_conversational_fallback(mode, result):
        print(
            "[REAL] WARNING: --mode conversational requested but the result "
            "carries no conversational keys (conversation_log/execution_path) — "
            "run_unified_analysis fell back to the pipeline. The state below is "
            "a PIPELINE verdict, NOT a conversational one. Re-run after fixing "
            "the conversational path before measuring #1668 item 5-bis."
        )

    state = result.get("unified_state")
    snap = state.get_state_snapshot(summarize=False) if state is not None else {}

    # Full ground-truth JSON (unscrubbed — gitignored). Keep the mode in the
    # filename so the two voies do not overwrite each other when both are run.
    json_path = RESULTS_DIR / f"real_{label}_{mode}_state.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False, default=str)
    print(f"[REAL] full snapshot -> {json_path}")

    # Readable digest
    conv_fallback = is_conversational_fallback(mode, result)
    md = render_markdown(
        snap,
        corpus,
        label,
        elapsed,
        summary=result.get("summary"),
        mode=mode,
        execution_path=(
            result.get("execution_path") if isinstance(result, dict) else None
        ),
        conversational_fallback=conv_fallback,
    )
    md_path = RESULTS_DIR / f"real_{label}_{mode}_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[REAL] readable report -> {md_path}")
    print(f"[REAL] top-level snapshot keys: {sorted(snap.keys())}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--corpus", choices=["A", "B", "C"], default="A")
    parser.add_argument(
        "--mode",
        choices=list(MODE_TO_WORKFLOW),
        default="pipeline",
        help="orchestration path: pipeline (default, sequential DAG) or "
        "conversational (SK AgentGroupChat dialogue). The conversational mode "
        "is the voie the #1668 item 5-bis gate lives on.",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args.corpus, args.mode))


if __name__ == "__main__":
    main()
