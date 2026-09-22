"""#2353 — tracked producer of the quality-phase render (metric mandate).

The user's metric mandate: the final judge is the perception of the text —
read the output, never a report about the output. #2337 satisfied it with a
real render (doc_B, first units, wired production path) whose producer never
entered the tree: the artifact lived on its author's seat only, so any other
seat could only believe the report. This script is that producer. It is
tracked; its OUTPUT stays gitignored (privacy rule 3) and it refuses to write
anywhere git would track.

Path exercised — the one production dispatch uses, ``setup_registry ->
find_for_capability(...) -> .invoke``, for both phases:

1. ``fact_extraction`` on the document text -> the units
   (``phase_extract_output``, the context key the executor writes);
2. ``argument_quality`` on those units, once per arm:

   - ``wired``: the phase exactly as production builds it (agentic callable
     when a route resolves — the phase's state output names the mode);
   - ``lexical``: same units, same invoke, the agentic factory forced to "no
     callable" — the phase's own named degraded path, as contrast arm.

Both arms read the SAME extraction, so what differs between them is the
wiring, not a second LLM draw of the units. The phase applies its own unit
cap; this script does not re-slice.

Every render opens with a provenance header (resolved route, effective model,
corpus label, HEAD sha + dirty flag, exact command, LLM requests per step,
SDK versions): two renders from two seats are comparable only through it.
LLM requests are counted by the repository's egress instrument
(``tests/llm_egress_counter.py``), not by a counter of this script's own.

Not the FB-29 harness: ``scripts/run_fb29_agentic_headtohead.py`` calls the
agentic detectors directly on a gitignored FB-25 artifact; this script
measures what the production PHASE builds.

Usage::

    conda run -n projet-is-roo-new --no-capture-output python \\
        scripts/analysis/render_quality_phase.py --doc B

Exit codes: 0 rendered as asked; 2 rendered, but the wired arm did not run
wired (no route) — the render says so at the top; 1 refused (no passphrase,
empty document, extraction failed, output path not gitignored).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import datetime as _dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PRODUCER = "scripts/analysis/render_quality_phase.py"
RESULTS_DIR = (
    REPO_ROOT / "argumentation_analysis/evaluation/results/2353_quality_render"
)
DATASET_PATH = REPO_ROOT / "argumentation_analysis/data/extract_sources.json.gz.enc"
ARMS = ("wired", "lexical")
FORCED_LEXICAL_ROUTE = "forced_lexical"


class RenderRefused(RuntimeError):
    """The producer cannot render honestly — the message names why."""


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def ensure_gitignored(path: Path) -> None:
    """Refuse an output path git would track: the render carries corpus text."""
    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    probe = subprocess.run(
        ["git", "check-ignore", "-q", rel],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if probe.returncode != 0:
        raise RenderRefused(
            f"output path is not gitignored ({rel}): the render carries corpus "
            "text and must never be committable (privacy rule 3)"
        )


@contextlib.contextmanager
def forced_lexical() -> Iterator[None]:
    """The contrast arm: the phase's agentic factory yields no callable.

    The phase then takes its own named degraded path and labels its state
    output ``degraded_forced_lexical`` — the arm is visible in the data, not
    only in this script.
    """
    import argumentation_analysis.orchestration.invoke_callables as ic

    original = ic._make_agentic_llm_callable
    ic._make_agentic_llm_callable = lambda: (None, FORCED_LEXICAL_ROUTE, "")
    try:
        yield
    finally:
        ic._make_agentic_llm_callable = original


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        return f"unavailable (git exit {out.returncode})"
    return out.stdout.strip()


def collect_provenance(label: str, source_index: int, command: str) -> Dict[str, Any]:
    from argumentation_analysis.core.llm_service import (
        classify_route,
        resolve_chat_endpoint,
    )

    api_key, base_url, model_id = resolve_chat_endpoint()
    versions: Dict[str, str] = {}
    for mod in ("openai", "semantic_kernel", "httpx"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception as exc:  # the header names the absence
            versions[mod] = f"unavailable ({type(exc).__name__})"
    return {
        "producer": PRODUCER,
        "command": command,
        "head": _git("rev-parse", "HEAD"),
        "tree_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "date_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus_label": label,
        "source_index": source_index,
        "route": classify_route(base_url) if api_key else "no_route",
        "model_resolved": model_id if api_key else "",
        "sdk_versions": versions,
    }


# ---------------------------------------------------------------------------
# Rendering (pure — tested offline)
# ---------------------------------------------------------------------------


def _unit_scores(output: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    scores = output.get("per_argument_scores") if isinstance(output, dict) else None
    return scores if isinstance(scores, dict) else {}


def unit_shape(units: List[Any]) -> Dict[str, Dict[str, int]]:
    """Word counts of what each unit carries — counts only, never the text.

    The quality phase judges ``arguments[i]["text"]``. Whether a virtue is
    even applicable is read from that text's length (#1907), so the shape of
    the unit decides what a render can show; two renders whose units differ
    in shape are not comparable on the structural virtues. ``source_quote``
    is what the extractor says it quoted from the document.
    """
    shape: Dict[str, Dict[str, int]] = {}
    for i, unit in enumerate(units):
        item = unit if isinstance(unit, dict) else {"text": str(unit)}
        shape[f"arg_{i + 1}"] = {
            "text_words": len(str(item.get("text") or "").split()),
            "source_quote_words": len(str(item.get("source_quote") or "").split()),
        }
    return shape


def discrimination_summary(arm_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Per arm: the note spread and, per virtue, how many units score above 0.

    The property #2353 asks to find again is qualitative: units become
    discernible from each other, and the structural virtues stop being
    uniformly null. A virtue scored on N units and non-zero on none is
    reported as ``uniformly_null`` — never averaged away.

    Absence is counted, never folded into the zeros (#1907): a unit where the
    virtue is ``not_applicable`` or ``unavailable`` carries no score, so
    ``uniformly_null`` rests on ``scored`` units only and the render always
    prints that denominator next to it. "Null on 1 unit, not applicable on 6"
    and "null on 7 units" are different findings.

    ``note_finale`` is summed over the applicable virtues only, so two units
    with different applicable maxima are not comparable on it; the
    ``ratio_*`` fields divide by ``note_max_applicable``.
    """
    summary: Dict[str, Any] = {}
    for arm, output in arm_outputs.items():
        units = _unit_scores(output)
        values = [
            u["note_finale"]
            for u in units.values()
            if isinstance(u, dict) and isinstance(u.get("note_finale"), (int, float))
        ]
        ratios = [
            u["note_finale"] / u["note_max_applicable"]
            for u in units.values()
            if isinstance(u, dict)
            and isinstance(u.get("note_finale"), (int, float))
            and isinstance(u.get("note_max_applicable"), (int, float))
            and u["note_max_applicable"] > 0
        ]
        virtues: Dict[str, Dict[str, Any]] = {}
        for unit in units.values():
            if not isinstance(unit, dict):
                continue
            scores = unit.get("scores_par_vertu") or {}
            statuses = unit.get("statuts_par_vertu") or {}
            # An n/a or unavailable virtue has NO key in ``scores_par_vertu``:
            # only its status names it. Walk both, or absence is invisible.
            for virtue in sorted(set(scores) | set(statuses)):
                v = virtues.setdefault(
                    virtue,
                    {"scored": 0, "non_zero": 0, "not_applicable": 0, "unavailable": 0},
                )
                score = scores.get(virtue)
                if isinstance(score, (int, float)):
                    v["scored"] += 1
                    v["non_zero"] += int(score > 0)
                    continue
                status = statuses.get(virtue)
                status = str(getattr(status, "value", status))
                if status in ("not_applicable", "unavailable"):
                    v[status] += 1
        for v in virtues.values():
            v["uniformly_null"] = v["scored"] > 0 and v["non_zero"] == 0
        summary[arm] = {
            "units": len(units),
            "note_min": min(values) if values else None,
            "note_max": max(values) if values else None,
            "distinct_notes": len({round(n, 3) for n in values}),
            "ratio_min": min(ratios) if ratios else None,
            "ratio_max": max(ratios) if ratios else None,
            "distinct_ratios": len({round(r, 3) for r in ratios}),
            "virtues": virtues,
        }
    return summary


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return "—" if value is None else str(value)


_HEADER_KEYS = (
    "producer",
    "command",
    "head",
    "tree_dirty",
    "date_utc",
    "corpus_label",
    "source_index",
    "route",
    "model_resolved",
)


def render_markdown(
    provenance: Dict[str, Any],
    extraction: Dict[str, Any],
    arms: Dict[str, Dict[str, Any]],
) -> str:
    """The reader surface: provenance first, then each unit read side by side."""
    outputs = {arm: data["output"] for arm, data in arms.items()}
    arm_names = list(arms)
    lines: List[str] = [f"# Quality phase render — {provenance['corpus_label']}", ""]

    wired = arms.get("wired")
    if wired is not None:
        mode = (wired["output"].get("agentic_wiring") or {}).get("mode")
        if mode != "wired":
            lines += [
                f"> ⚠ **The wired arm did not run wired** (mode `{mode}`): this "
                "render does not show the agentic layer.",
                "",
            ]

    lines += ["## Provenance", ""]
    for key in _HEADER_KEYS:
        lines.append(f"- **{key}**: `{provenance.get(key)}`")
    versions = provenance.get("sdk_versions", {})
    lines.append(
        "- **sdk_versions**: "
        + ", ".join(f"`{k} {v}`" for k, v in sorted(versions.items()))
    )
    lines.append(
        f"- **extraction**: status `{extraction.get('status')}`, "
        f"{extraction.get('argument_count')} units, "
        f"{extraction.get('llm_requests')} LLM requests, "
        f"{_fmt(extraction.get('wall_seconds'))} s"
    )
    shape = extraction.get("unit_shape") or {}
    if shape:
        text_words = [s["text_words"] for s in shape.values()]
        quote_words = [s["source_quote_words"] for s in shape.values()]
        lines.append(
            f"- **unit shape** (what the quality phase judges is `text`): "
            f"`text` {min(text_words)}–{max(text_words)} words, "
            f"`source_quote` present on "
            f"{sum(1 for q in quote_words if q)}/{len(quote_words)} units, "
            f"{min(quote_words)}–{max(quote_words)} words"
        )
    for arm, data in arms.items():
        wiring = data["output"].get("agentic_wiring") or {}
        degraded = wiring.get("units_degraded") or {}
        lines.append(
            f"- **arm `{arm}`**: mode `{wiring.get('mode')}`, model "
            f"`{wiring.get('model')}`, {wiring.get('units_evaluated')} units, "
            f"{len(degraded)} degraded, {data.get('llm_requests')} LLM requests, "
            f"{_fmt(data.get('wall_seconds'))} s"
        )
        for unit_id, reason in degraded.items():
            lines.append(f"  - degraded `{unit_id}`: {reason}")

    summary = discrimination_summary(outputs)
    lines += ["", "## Discrimination", ""]
    lines.append("| | " + " | ".join(arm_names) + " |")
    lines.append("|---|" + "---|" * len(arm_names))
    lines.append(
        "| note spread | "
        + " | ".join(
            f"{_fmt(summary[a]['note_min'])} ↔ {_fmt(summary[a]['note_max'])}"
            for a in arm_names
        )
        + " |"
    )
    lines.append(
        "| distinct notes | "
        + " | ".join(str(summary[a]["distinct_notes"]) for a in arm_names)
        + " |"
    )
    lines.append(
        "| note / applicable max | "
        + " | ".join(
            f"{_fmt(summary[a]['ratio_min'])} ↔ {_fmt(summary[a]['ratio_max'])}"
            f" ({summary[a]['distinct_ratios']} distinct)"
            for a in arm_names
        )
        + " |"
    )
    for virtue in sorted({v for a in arm_names for v in summary[a]["virtues"]}):
        cells = []
        for a in arm_names:
            v = summary[a]["virtues"].get(virtue)
            if v is None:
                cells.append("—")
            else:
                flag = " **null**" if v["uniformly_null"] else ""
                absent = "".join(
                    f" · {v[k]} {label}"
                    for k, label in (
                        ("not_applicable", "n/a"),
                        ("unavailable", "unavailable"),
                    )
                    if v.get(k)
                )
                cells.append(f"{v['non_zero']}/{v['scored']} > 0{flag}{absent}")
        lines.append(f"| {virtue} | " + " | ".join(cells) + " |")

    lines += ["", "## Units", ""]
    unit_ids: List[str] = []
    for output in outputs.values():
        for unit_id in _unit_scores(output):
            if unit_id not in unit_ids:
                unit_ids.append(unit_id)
    texts = extraction.get("unit_texts", {})
    for unit_id in unit_ids:
        lines += [f"### {unit_id}", ""]
        if unit_id in texts:
            lines += [f"> {texts[unit_id]}", ""]
        per_arm = {a: _unit_scores(outputs[a]).get(unit_id, {}) for a in arm_names}
        lines.append("| virtue | " + " | ".join(arm_names) + " |")
        lines.append("|---|" + "---|" * len(arm_names))
        lines.append(
            "| note | "
            + " | ".join(
                f"{_fmt(per_arm[a].get('note_finale'))} / "
                f"{_fmt(per_arm[a].get('note_max_applicable'))}"
                for a in arm_names
            )
            + " |"
        )
        virtues = sorted(
            {v for a in arm_names for v in (per_arm[a].get("statuts_par_vertu") or {})}
        )
        for virtue in virtues:
            cells = []
            for a in arm_names:
                status = (per_arm[a].get("statuts_par_vertu") or {}).get(virtue)
                score = (per_arm[a].get("scores_par_vertu") or {}).get(virtue)
                cells.append(f"{_fmt(score)} ({_fmt(status)})")
            lines.append(f"| {virtue} | " + " | ".join(cells) + " |")
        # What the wired arm SAW where it differs from the lexical reading:
        # the located exhibit is what makes a non-zero score readable.
        if "wired" in per_arm and "lexical" in per_arm:
            w_scores = per_arm["wired"].get("scores_par_vertu") or {}
            l_scores = per_arm["lexical"].get("scores_par_vertu") or {}
            details = per_arm["wired"].get("rapport_detaille") or {}
            differing = [v for v in w_scores if w_scores.get(v) != l_scores.get(v)]
            if differing:
                lines += ["", "Wired reading where it differs from lexical:", ""]
                for virtue in differing:
                    lines.append(f"- **{virtue}**: {details.get(virtue, '—')}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env")


def load_document(source_index: int) -> str:
    """The document text, decrypted in memory only (privacy rule 5)."""
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE", "")
    if not passphrase:
        raise RenderRefused("TEXT_CONFIG_PASSPHRASE is not set: no corpus to render")
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    definitions = load_extract_definitions(
        DATASET_PATH, derive_encryption_key(passphrase)
    )
    if not 0 <= source_index < len(definitions):
        raise RenderRefused(
            f"source index {source_index} outside the dataset "
            f"(0..{len(definitions) - 1})"
        )
    text = definitions[source_index].get("full_text", "") or ""
    if not text.strip():
        raise RenderRefused(f"source index {source_index} carries no text")
    return text


def resolve_phase_invoke(registry: Any, capability: str) -> Any:
    """The invoke production dispatch resolves — never a private import."""
    matches = registry.find_for_capability(capability)
    invokes = [m.invoke for m in matches if getattr(m, "invoke", None) is not None]
    if not invokes:
        raise RenderRefused(f"no production invoke registered for {capability!r}")
    return invokes[0]


async def run_render(
    label: str, source_index: int, arms: Tuple[str, ...], command: str
) -> Tuple[str, Dict[str, Any], int]:
    from argumentation_analysis.orchestration.registry_setup import setup_registry
    from tests.llm_egress_counter import LLMEgressCounter, llm_hosts_from_env

    provenance = collect_provenance(label, source_index, command)
    text = load_document(source_index)
    registry = setup_registry(include_optional=False)
    extract_invoke = resolve_phase_invoke(registry, "fact_extraction")
    quality_invoke = resolve_phase_invoke(registry, "argument_quality")

    counter = LLMEgressCounter(llm_hosts_from_env())
    counter.install()
    try:
        counter.current_test = "extract"
        t0 = time.monotonic()
        extract_output = await extract_invoke(text, {})
        extract_wall = time.monotonic() - t0
        status = extract_output.get("extraction_status")
        units = extract_output.get("arguments") or []
        if status != "ok" or not units:
            raise RenderRefused(
                f"extraction produced no units to render (status {status!r}, "
                f"{len(units)} units)"
            )
        arm_data: Dict[str, Dict[str, Any]] = {}
        for arm in arms:
            counter.current_test = arm
            context = {"phase_extract_output": extract_output}
            cm = forced_lexical() if arm == "lexical" else contextlib.nullcontext()
            t0 = time.monotonic()
            with cm:
                output = await quality_invoke(text, context)
            arm_data[arm] = {
                "output": output if isinstance(output, dict) else {},
                "wall_seconds": time.monotonic() - t0,
            }
    finally:
        counter.uninstall()

    per_step = counter.per_test()
    for arm in arm_data:
        arm_data[arm]["llm_requests"] = per_step.get(arm, 0)
    extraction = {
        "status": status,
        "argument_count": len(units),
        "llm_requests": per_step.get("extract", 0),
        "wall_seconds": extract_wall,
        "unit_texts": {
            f"arg_{i + 1}": (u.get("text") if isinstance(u, dict) else str(u))
            for i, u in enumerate(units)
        },
        "unit_shape": unit_shape(units),
    }
    markdown = render_markdown(provenance, extraction, arm_data)
    record = {
        "provenance": provenance,
        "extraction": {k: v for k, v in extraction.items() if k != "unit_texts"},
        "arms": arm_data,
        "discrimination": discrimination_summary(
            {arm: data["output"] for arm, data in arm_data.items()}
        ),
    }
    wired_mode = None
    if "wired" in arm_data:
        wired_mode = (arm_data["wired"]["output"].get("agentic_wiring") or {}).get(
            "mode"
        )
    exit_code = 2 if "wired" in arm_data and wired_mode != "wired" else 0
    return markdown, record, exit_code


def _resolve_doc(doc: Optional[str], source_index: Optional[int]) -> Tuple[str, int]:
    if source_index is not None:
        return f"src{source_index}", source_index
    # The FB/capstone family's opaque labels — one mapping, imported, not copied.
    from scripts.run_capstone_c1 import CORPUS_SRC_IDX

    return f"doc_{doc}", CORPUS_SRC_IDX[doc]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doc", choices=["A", "B", "C"], help="capstone opaque label")
    group.add_argument("--source-index", type=int, help="dataset index (label srcN)")
    parser.add_argument(
        "--arms",
        default=",".join(ARMS),
        help="comma list among wired,lexical (default both: the contrast)",
    )
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args(argv)

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    unknown = [a for a in arms if a not in ARMS]
    if unknown or not arms:
        parser.error(f"unknown arm(s) {unknown}; choose among {ARMS}")

    _load_env()
    label, source_index = _resolve_doc(args.doc, args.source_index)
    passed = list(argv) if argv is not None else sys.argv[1:]
    command = "python " + " ".join([PRODUCER, *passed])
    try:
        out_dir = args.out_dir.resolve()
        ensure_gitignored(out_dir / "probe.md")
        out_dir.mkdir(parents=True, exist_ok=True)
        markdown, record, exit_code = asyncio.run(
            run_render(label, source_index, arms, command)
        )
    except RenderRefused as exc:
        print(f"[#2353] REFUSED: {exc}", file=sys.stderr)
        return 1

    stamp = record["provenance"]["date_utc"].replace(":", "").replace("-", "")
    md_path = out_dir / f"{label}_{stamp}.md"
    json_path = out_dir / f"{label}_{stamp}.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Stdout carries aggregates only — it is the part that gets pasted.
    for arm, s in record["discrimination"].items():
        # Every null carries its denominator; a virtue absent on most units is
        # named as such, never left to read as a zero (#1907).
        nulls = sorted(
            f"{v} (scored {d['scored']}/{s['units']})"
            for v, d in s["virtues"].items()
            if d["uniformly_null"]
        )
        mostly_absent = sorted(
            v
            for v, d in s["virtues"].items()
            if d["not_applicable"] + d["unavailable"] > s["units"] / 2
        )
        wiring = record["arms"][arm]["output"].get("agentic_wiring") or {}
        print(
            f"[#2353] {label} arm={arm} mode={wiring.get('mode')} units={s['units']} "
            f"notes={_fmt(s['note_min'])}..{_fmt(s['note_max'])} "
            f"distinct={s['distinct_notes']} "
            f"ratio={_fmt(s['ratio_min'])}..{_fmt(s['ratio_max'])} "
            f"llm_requests={record['arms'][arm]['llm_requests']} "
            f"uniformly_null={nulls} absent_on_most_units={mostly_absent}"
        )
    print(f"[#2353] render: {md_path.relative_to(REPO_ROOT).as_posix()}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
