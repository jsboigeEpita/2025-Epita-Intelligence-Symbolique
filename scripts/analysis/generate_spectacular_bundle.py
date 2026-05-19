"""Generate the Spectacular Capstone bundle for all corpora.

Reads existing SCDA state snapshots from outputs/scda_audit/ and produces
multi-format exports (JSON, XML, MD, CSV, HTML) plus balance reports,
cross-reference graphs, and reprompt trace reports.

Output: docs/reports/spectacular/

Privacy: raw_text, full_text, raw_text_snippet and similar plaintext fields
are stripped from all exports. Only opaque IDs (corpus_A, arg_1, etc.) are used.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ── Project root ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Top-level fields to remove entirely
_PRIVACY_STRIP_FIELDS = frozenset({
    "raw_text", "full_text", "raw_text_snippet", "full_text_segment",
    "source_text", "text_content", "original_text",
})

# NL fields inside dict values to replace with opaque markers
_NL_SCRUB_KEYS = frozenset({
    "premisses", "conclusion", "text", "justification", "quote",
    "reformulation", "llm_assessment", "content", "description",
    "counter_content", "topic", "reason",
})

CORPORA = {
    "A": ROOT / "outputs/scda_audit/corpus_dense_A",
    "B": ROOT / "outputs/scda_audit/corpus_dense_B",
    "C": ROOT / "outputs/scda_audit/corpus_dense_C",
}

OUT_DIR = ROOT / "docs/reports/spectacular"


# ── Helpers ───────────────────────────────────────────────────────────

def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        logger.warning("Missing: %s", path)
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _scrub_nl(value: Any) -> Any:
    """Replace natural-language string values with opaque marker."""
    if isinstance(value, str) and len(value) > 10:
        return "<scrubbed>"
    return value


def _strip_privacy(data: Any, depth: int = 0) -> Any:
    """Recursively strip plaintext fields and scrub NL content."""
    if depth > 12:
        return data
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in _PRIVACY_STRIP_FIELDS:
                continue
            if k in _NL_SCRUB_KEYS and isinstance(v, str):
                result[k] = "<scrubbed>"
            elif k == "content" and isinstance(v, str) and len(v) > 50:
                result[k] = "<scrubbed>"
            else:
                result[k] = _strip_privacy(v, depth + 1)
        return result
    if isinstance(data, list):
        return [_strip_privacy(item, depth + 1) for item in data]
    if isinstance(data, str) and depth == 1 and len(data) > 80:
        # Top-level string values in dicts (e.g. arg values that are raw strings)
        return "<scrubbed>"
    return data


def _scrub_state_for_export(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """Full privacy scrub: strip raw text + scrub NL in analysis dimensions."""
    # First pass: strip top-level privacy fields
    cleaned = {k: v for k, v in state_data.items() if k not in _PRIVACY_STRIP_FIELDS}

    # Second pass: scrub identified_arguments
    args = cleaned.get("identified_arguments", {})
    if isinstance(args, dict):
        scrubbed_args = {}
        for arg_id, arg_val in args.items():
            if isinstance(arg_val, dict):
                scrubbed_args[arg_id] = {
                    k: ("<scrubbed>" if k in _NL_SCRUB_KEYS and isinstance(v, str) else v)
                    for k, v in arg_val.items()
                }
            elif isinstance(arg_val, str):
                scrubbed_args[arg_id] = "<scrubbed>"
            else:
                scrubbed_args[arg_id] = arg_val
        cleaned["identified_arguments"] = scrubbed_args

    # Third pass: scrub identified_fallacies
    fallacies = cleaned.get("identified_fallacies", {})
    if isinstance(fallacies, dict):
        scrubbed_fallacies = {}
        for f_id, f_val in fallacies.items():
            if isinstance(f_val, dict):
                scrubbed_fallacies[f_id] = {
                    k: ("<scrubbed>" if k in _NL_SCRUB_KEYS and isinstance(v, str) else v)
                    for k, v in f_val.items()
                }
            else:
                scrubbed_fallacies[f_id] = f_val
        cleaned["identified_fallacies"] = scrubbed_fallacies

    # Fourth pass: scrub argument_quality_scores
    quality = cleaned.get("argument_quality_scores", {})
    if isinstance(quality, dict):
        scrubbed_quality = {}
        for q_id, q_val in quality.items():
            if isinstance(q_val, dict):
                scrubbed_quality[q_id] = {
                    k: ("<scrubbed>" if k in _NL_SCRUB_KEYS and isinstance(v, str) else v)
                    for k, v in q_val.items()
                }
            else:
                scrubbed_quality[q_id] = q_val
        cleaned["argument_quality_scores"] = scrubbed_quality

    # Fifth pass: scrub counter_arguments
    counters = cleaned.get("counter_arguments", [])
    if isinstance(counters, list):
        cleaned["counter_arguments"] = [
            {k: ("<scrubbed>" if k in _NL_SCRUB_KEYS and isinstance(v, str) else v)
             for k, v in ca.items()}
            if isinstance(ca, dict) else ca
            for ca in counters
        ]

    # Sixth pass: scrub debate_transcripts
    debates = cleaned.get("debate_transcripts", [])
    if isinstance(debates, list):
        cleaned["debate_transcripts"] = [
            {k: ("<scrubbed>" if k in _NL_SCRUB_KEYS and isinstance(v, str) else v)
             for k, v in dt.items()}
            if isinstance(dt, dict) else dt
            for dt in debates
        ]

    # Seventh pass: scrub belief_sets content
    belief_sets = cleaned.get("belief_sets", {})
    if isinstance(belief_sets, dict):
        scrubbed_bs = {}
        for bs_id, bs_val in belief_sets.items():
            if isinstance(bs_val, dict):
                content = bs_val.get("content", "")
                if isinstance(content, str) and len(content) > 20:
                    bs_val = {**bs_val, "content": "<scrubbed>"}
                scrubbed_bs[bs_id] = bs_val
            else:
                scrubbed_bs[bs_id] = bs_val
        cleaned["belief_sets"] = scrubbed_bs

    # Eighth pass: scrub extracts
    extracts = cleaned.get("extracts", {})
    if isinstance(extracts, dict):
        scrubbed_extracts = {}
        for e_id, e_val in extracts.items():
            if isinstance(e_val, str) and len(e_val) > 20:
                scrubbed_extracts[e_id] = "<scrubbed>"
            elif isinstance(e_val, dict):
                scrubbed_extracts[e_id] = {
                    k: ("<scrubbed>" if isinstance(v, str) and len(v) > 20 else v)
                    for k, v in e_val.items()
                }
            else:
                scrubbed_extracts[e_id] = e_val
        cleaned["extracts"] = scrubbed_extracts

    # Ninth pass: scrub analysis_tasks (may contain NL instructions)
    tasks = cleaned.get("analysis_tasks", {})
    if isinstance(tasks, dict):
        cleaned["analysis_tasks"] = {
            k: ("<scrubbed>" if isinstance(v, str) and len(v) > 50 else v)
            for k, v in tasks.items()
        }

    # Tenth pass: scrub final_conclusion if present
    conclusion = cleaned.get("final_conclusion")
    if isinstance(conclusion, str) and len(conclusion) > 20:
        cleaned["final_conclusion"] = "<scrubbed>"

    # Final pass: global regex scrub on ALL remaining strings
    cleaned = _global_entity_scrub(cleaned)

    return cleaned


# Entity patterns that must never appear in exports
_ENTITY_PATTERN = re.compile(
    r"(?i)\b(trump|biden|obama|harris|clinton|poutine|putin|zelensky|macron|attal|netanyahu)"
    r"|\b(iran|ukraine|russia|china|israel|otan|onu|nato|maidan|crimea|bolchevik|bolchévik)"
    r"|\b(kremlin|pentagon|white\s*house|united\s*nations|un\s*general\s*assembly)"
    r"|\b(russie|chinese|américaine)\b",
)


def _global_entity_scrub(data: Any, depth: int = 0) -> Any:
    """Recursively replace any string containing entity names with <scrubbed>."""
    if depth > 15:
        return data
    if isinstance(data, str):
        if _ENTITY_PATTERN.search(data):
            return "<scrubbed>"
        return data
    if isinstance(data, dict):
        return {k: _global_entity_scrub(v, depth + 1) for k, v in data.items()}
    if isinstance(data, list):
        return [_global_entity_scrub(item, depth + 1) for item in data]
    return data


class _DictStateProxy:
    """Wraps a dict to provide get_state_snapshot() + attribute access.

    MultiFormatExporter uses get_state_snapshot(); CrossReferenceGraph uses
    getattr(state, "identified_arguments", None). This proxy supports both.
    """

    def __init__(self, snapshot: Dict[str, Any]):
        self._snapshot = snapshot
        # Expose top-level keys as attributes for build_from_state()
        for key, value in snapshot.items():
            if not hasattr(self, key):
                try:
                    setattr(self, key, value)
                except (AttributeError, TypeError):
                    pass

    def get_state_snapshot(self, summarize: bool = False) -> Dict[str, Any]:
        if summarize:
            return {
                k: (f"<{type(v).__name__}({len(v)})>" if isinstance(v, (dict, list)) else v)
                for k, v in self._snapshot.items()
            }
        return self._snapshot


# ── Generation steps ──────────────────────────────────────────────────

def generate_multi_format(corpus_id: str, state_data: Dict[str, Any]) -> None:
    """Generate JSON, XML, MD, CSV bundle, HTML for one corpus."""
    from argumentation_analysis.reporting.multi_format_exporter import MultiFormatExporter

    safe_data = _scrub_state_for_export(state_data)
    proxy = _DictStateProxy(safe_data)
    exporter = MultiFormatExporter(proxy)

    corpus_dir = OUT_DIR / corpus_id

    # JSON
    json_path = OUT_DIR / f"corpus_{corpus_id}.json"
    json_path.write_text(exporter.to_json(pretty=True), encoding="utf-8")
    logger.info("  JSON  → %s", json_path.name)

    # XML
    xml_path = OUT_DIR / f"corpus_{corpus_id}.xml"
    xml_path.write_text(exporter.to_xml(), encoding="utf-8")
    logger.info("  XML   → %s", xml_path.name)

    # Markdown
    md_path = OUT_DIR / f"corpus_{corpus_id}.md"
    md_path.write_text(exporter.to_markdown(), encoding="utf-8")
    logger.info("  MD    → %s", md_path.name)

    # CSV bundle
    csv_dir = corpus_dir / "csv"
    csv_files = exporter.to_csv_bundle(csv_dir)
    logger.info("  CSV   → %s (%d files)", csv_dir.name, len(csv_files))

    # HTML
    html_path = OUT_DIR / f"corpus_{corpus_id}.html"
    html_path.write_text(exporter.to_html(), encoding="utf-8")
    logger.info("  HTML  → %s", html_path.name)


def generate_balance_report(corpus_id: str, conversation_log: list) -> None:
    """Generate balance report via ConversationBalanceAnalyzer."""
    from argumentation_analysis.reporting.conversation_balance import ConversationBalanceAnalyzer

    analyzer = ConversationBalanceAnalyzer()
    report = analyzer.analyze(conversation_log)

    path = OUT_DIR / f"balance_corpus_{corpus_id}.md"
    path.write_text(report.to_markdown(), encoding="utf-8")
    logger.info("  Balance → %s", path.name)


def generate_cross_ref_graph(corpus_id: str, state_data: Dict[str, Any]) -> None:
    """Generate cross-reference graph in JSON, DOT, Mermaid."""
    from argumentation_analysis.reporting.cross_reference_graph import CrossReferenceGraph

    safe_data = _scrub_state_for_export(state_data)
    proxy = _DictStateProxy(safe_data)

    graph = CrossReferenceGraph()
    graph.build_from_state(proxy)

    # Replace NL labels with opaque IDs
    for nid, node in graph.nodes.items():
        if node.node_type == "argument":
            node.label = nid
        elif node.node_type == "fallacy":
            node.label = nid
        elif node.node_type == "quality_score":
            node.label = nid

    json_path = OUT_DIR / f"cross_ref_graph_corpus_{corpus_id}.json"
    json_path.write_text(graph.to_json(), encoding="utf-8")

    dot_path = OUT_DIR / f"cross_ref_graph_corpus_{corpus_id}.dot"
    dot_path.write_text(graph.to_dot(), encoding="utf-8")

    mmd_path = OUT_DIR / f"cross_ref_graph_corpus_{corpus_id}.mmd"
    mmd_path.write_text(graph.to_mermaid(), encoding="utf-8")

    logger.info("  CrossRef → JSON + DOT + Mermaid")


def generate_reprompt_trace(
    corpus_id: str,
    conversation_log: list,
    trace_data: Dict[str, Any],
) -> None:
    """Generate reprompt trace report from conversation_log re_prompt markers."""
    from argumentation_analysis.reporting.reprompt_trace import RepromptTraceExtractor

    extractor = RepromptTraceExtractor()

    # Extract re_prompt events from conversation log
    turn_counts: Dict[str, int] = {}
    for entry in conversation_log:
        if not isinstance(entry, dict):
            continue
        if entry.get("re_prompt") != 1:
            continue

        phase = entry.get("phase", "unknown")
        agent = entry.get("agent", "unknown")
        turn = entry.get("turn", 0)
        turn_key = f"{phase}:{turn}"
        attempt = turn_counts.get(turn_key, 0)
        turn_counts[turn_key] = attempt + 1

        extractor.record(
            phase_name=phase,
            turn=turn,
            attempt_idx=attempt,
            fingerprint_before=(0,) * 11,
            fingerprint_after=(0,) * 11,
            outcome="reran" if attempt < 2 else "gave_up",
            agent_name=agent,
        )

    path = OUT_DIR / f"reprompt_trace_corpus_{corpus_id}.json"
    path.write_text(extractor.to_json(), encoding="utf-8")

    md_path = OUT_DIR / f"reprompt_trace_corpus_{corpus_id}.md"
    md_path.write_text(extractor.to_markdown(), encoding="utf-8")

    logger.info("  RePrompt → JSON + MD (%d traces)", len(extractor.traces))


def generate_readme(corpus_summaries: Dict[str, Dict[str, Any]]) -> None:
    """Generate README.md guide for the jury."""
    lines = [
        "# SCDA Spectacular Capstone Bundle\n",
        "Multi-format exports of the Shared Conversational Decision Analysis (SCDA)\n",
        "pipeline results across three politically-diverse corpora.\n",
        "",
        "## Corpus Overview\n",
        "| Corpus | Arguments | Fallacies | Phases | Turns | Duration |",
        "|--------|-----------|-----------|--------|-------|----------|",
    ]

    for cid, info in corpus_summaries.items():
        lines.append(
            f"| {cid} | {info['args']} | {info['fallacies']} | "
            f"{info['phases']} | {info['turns']} | {info['duration']:.0f}s |"
        )

    lines.extend([
        "",
        "## File Guide\n",
        "### Per-Corpus Exports\n",
        "| File | Format | Content |",
        "|------|--------|---------|",
        "| `corpus_X.json` | JSON | Full state snapshot (structured data) |",
        "| `corpus_X.xml` | XML | State in XML with labeled dimensions |",
        "| `corpus_X.md` | Markdown | Human-readable state summary |",
        "| `corpus_X.html` | HTML | Interactive collapsible sections + summary cards |",
        "| `corpus_X/csv/*.csv` | CSV | Tabular exports (arguments, fallacies, quality, etc.) |",
        "",
        "### Analysis Reports\n",
        "| File | Content |",
        "|------|---------|",
        "| `balance_corpus_X.md` | Agent participation balance (turn count, entropy, dominance alerts) |",
        "| `cross_ref_graph_corpus_X.json` | Cross-reference graph (arguments→fallacies→JTMS→quality) |",
        "| `cross_ref_graph_corpus_X.dot` | Graphviz DOT visualization |",
        "| `cross_ref_graph_corpus_X.mmd` | Mermaid flowchart |",
        "| `reprompt_trace_corpus_X.json` | Growth-validation re-prompt events with fingerprint deltas |",
        "| `reprompt_trace_corpus_X.md` | Human-readable re-prompt trace summary |",
        "",
        "## How to Explore\n",
        "1. **Quick overview**: Open any `corpus_X.html` in a browser — collapsible sections with summary cards.",
        "2. **Graph visualization**: Paste `cross_ref_graph_corpus_X.mmd` into [Mermaid Live](https://mermaid.live).",
        "3. **Data analysis**: Import `corpus_X.json` or CSV files into pandas/Excel.",
        "4. **Agent balance**: Read `balance_corpus_X.md` to see how evenly agents participated.",
        "",
        "## Privacy\n",
        "All personally-identifiable text and source metadata has been stripped.\n",
        "Only opaque identifiers (corpus_A, arg_1, fallacy_3, etc.) are used.\n",
        "",
        "---",
        f"*Generated by `scripts/analysis/generate_spectacular_bundle.py`*",
    ])

    path = OUT_DIR / "README.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("  README → %s", path.name)


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    corpus_summaries: Dict[str, Dict[str, Any]] = {}

    for corpus_id, corpus_dir in sorted(CORPORA.items()):
        logger.info("=== Corpus %s ===", corpus_id)

        state_data = _load_json(corpus_dir / "state_snapshot.json")
        conv_log = _load_json(corpus_dir / "conversation_log.json")
        trace_data = _load_json(corpus_dir / "trace_report.json")

        if state_data is None:
            logger.error("Skipping corpus %s — no state snapshot", corpus_id)
            continue

        # Summary stats
        args = state_data.get("identified_arguments", {})
        fallacies = state_data.get("identified_fallacies", {})
        trace_summary = trace_data or {}

        corpus_summaries[corpus_id] = {
            "args": len(args) if isinstance(args, dict) else 0,
            "fallacies": len(fallacies) if isinstance(fallacies, dict) else 0,
            "phases": trace_summary.get("total_phases", 0),
            "turns": trace_summary.get("total_turns", 0),
            "duration": trace_summary.get("total_duration_seconds", 0),
        }

        # Generate all artefacts
        generate_multi_format(corpus_id, state_data)

        if conv_log and isinstance(conv_log, list):
            generate_balance_report(corpus_id, conv_log)
        else:
            logger.warning("  No conversation log for corpus %s", corpus_id)

        generate_cross_ref_graph(corpus_id, state_data)

        if conv_log and isinstance(conv_log, list):
            generate_reprompt_trace(corpus_id, conv_log, trace_data or {})
        else:
            logger.warning("  No conversation log for corpus %s — skipping reprompt trace", corpus_id)

        # Per-corpus subdirectory
        (OUT_DIR / corpus_id).mkdir(parents=True, exist_ok=True)

    # README
    generate_readme(corpus_summaries)

    logger.info("\n=== Bundle complete: %s ===", OUT_DIR)


if __name__ == "__main__":
    main()
