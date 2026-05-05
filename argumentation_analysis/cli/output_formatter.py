"""
Rich CLI output formatter for spectacular analysis results.

Renders UnifiedAnalysisState sections with colors, indentation, and
cross-references between sections (e.g., "see Section 3.2").

Usage:
    from argumentation_analysis.cli.output_formatter import (
        render_spectacular_result,
        render_state_snapshot,
    )

    # From run_orchestration.py --rich-output
    render_spectacular_result(result)

Sections: Extraction / Formal Logic / Fallacies / JTMS / ATMS / Dung /
Counter-arguments / Debate / Quality / Narrative (#364).
"""

import json
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Section numbering for cross-references
SECTIONS = [
    (1, "Extraction"),
    (2, "Formal Logic"),
    (3, "Fallacies"),
    (4, "JTMS"),
    (5, "ATMS"),
    (6, "Dung"),
    (7, "Counter-arguments"),
    (8, "Debate"),
    (9, "Quality"),
    (10, "Narrative"),
]


def _section_ref(section_num: int) -> str:
    """Generate a cross-reference string like 'see Section 3'."""
    for num, name in SECTIONS:
        if num == section_num:
            return f"see Section {num} ({name})"
    return f"see Section {section_num}"


def _truncate(text: str, max_len: int = 100) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _count_non_empty(data: Dict[str, Any]) -> int:
    return sum(1 for v in data.values() if v and v not in ([], {}, "", None, 0))


def render_spectacular_result(result: Dict[str, Any], console: Optional[Any] = None):
    """Render a full spectacular analysis result with rich formatting.

    Args:
        result: Analysis result dict from run_unified_analysis or
            run_conversational_analysis.
        console: Optional Rich Console instance. Auto-created if not provided.
    """
    if HAS_RICH and console is None:
        console = Console()

    if not HAS_RICH or console is None:
        _render_plain(result)
        return

    state_snapshot = result.get("state_snapshot", {})
    summary = result.get("summary", {})

    # Header
    workflow = result.get("workflow_name", "unknown")
    completed = summary.get("completed", 0)
    total = summary.get("total", 0)
    total_fields = len(state_snapshot)
    non_empty = _count_non_empty(state_snapshot)
    coverage = non_empty / total_fields * 100 if total_fields else 0

    console.print(
        Panel(
            f"[bold]Workflow:[/bold] {workflow}\n"
            f"[bold]Phases:[/bold] {completed}/{total} completed\n"
            f"[bold]State coverage:[/bold] {non_empty}/{total_fields} fields ({coverage:.0f}%)",
            title="[bold cyan]Spectacular Rhetorical Analysis[/bold cyan]",
            border_style="cyan",
        )
    )

    # Sections
    _render_extraction(console, state_snapshot)
    _render_formal_logic(console, state_snapshot)
    _render_fallacies(console, state_snapshot)
    _render_jtms(console, state_snapshot)
    _render_dung(console, state_snapshot)
    _render_counter_arguments(console, state_snapshot)
    _render_debate(console, state_snapshot)
    _render_quality(console, state_snapshot)
    _render_narrative(console, state_snapshot, result)

    # Footer
    caps = result.get("capabilities_used", [])
    if caps:
        console.print(f"\n[dim]Capabilities: {', '.join(caps)}[/dim]")


def _render_extraction(console, state: Dict[str, Any]):
    args = state.get("identified_arguments", {})
    extracts = state.get("extracts", [])
    if not args and not extracts:
        return

    console.print(f"\n[bold]1. Extraction[/bold] ({_section_ref(1)})")
    if args:
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="dim")
        table.add_column("Argument")
        for aid, desc in list(args.items())[:10]:
            table.add_row(aid, _truncate(str(desc)))
        console.print(table)
    if extracts:
        console.print(f"  {len(extracts)} factual claims extracted")


def _render_formal_logic(console, state: Dict[str, Any]):
    fol = state.get("fol_analysis_results", [])
    pl = state.get("propositional_analysis_results", [])
    modal = state.get("modal_analysis_results", [])
    nl = state.get("nl_to_logic_translations", [])
    if not fol and not pl and not modal and not nl:
        return

    console.print(f"\n[bold]2. Formal Logic[/bold] ({_section_ref(2)})")
    if nl:
        console.print(f"  {len(nl)} NL-to-logic translations")
    if fol:
        for entry in fol[:5]:
            formula = entry.get("formula", "?")
            console.print(f"  [yellow]FOL[/yellow] {formula}")
    if pl:
        for entry in pl[:5]:
            formula = entry.get("formula", "?")
            console.print(f"  [green]PL[/green] {formula}")
    if modal:
        for entry in modal[:5]:
            formula = entry.get("formula", "?")
            console.print(f"  [blue]Modal[/blue] {formula}")


def _render_fallacies(console, state: Dict[str, Any]):
    fallacies = state.get("identified_fallacies", {})
    neural = state.get("neural_fallacy_scores", [])
    if not fallacies and not neural:
        return

    console.print(f"\n[bold]3. Fallacies[/bold] ({_section_ref(3)})")
    if fallacies:
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="dim")
        table.add_column("Type", style="red")
        table.add_column("Justification")
        for fid, data in list(fallacies.items())[:10]:
            ftype = data.get("type", "?") if isinstance(data, dict) else "?"
            just = (
                data.get("justification", "") if isinstance(data, dict) else str(data)
            )
            table.add_row(fid, ftype, _truncate(just, 60))
        console.print(table)
    if neural:
        console.print(
            f"  {len(neural)} neural detection scores "
            f"({_section_ref(9)} for quality impact)"
        )


def _render_jtms(console, state: Dict[str, Any]):
    beliefs = state.get("jtms_beliefs", {})
    if not beliefs:
        return

    console.print(f"\n[bold]4. JTMS[/bold] ({_section_ref(4)})")
    status_styles = {"IN": "green", "OUT": "red", "UNDECIDED": "yellow"}
    for bid, bdata in list(beliefs.items())[:10]:
        if isinstance(bdata, dict):
            status = bdata.get("status", "?")
            style = status_styles.get(status, "white")
            conf = bdata.get("confidence", "?")
            line = f"  [{style}]{status}[/{style}] {bid}"
            if conf != "?":
                line += f" (conf={conf})"
            if not bdata.get("valid", True):
                line += " [dim](retracted)[/dim]"
            console.print(line)
        else:
            console.print(f"  {bid}: {bdata}")


def _render_dung(console, state: Dict[str, Any]):
    frameworks = state.get("dung_frameworks", {})
    if not frameworks:
        return

    console.print(f"\n[bold]6. Dung[/bold] ({_section_ref(6)})")
    for fname, fdata in list(frameworks.items())[:5]:
        if isinstance(fdata, dict):
            exts = fdata.get("extensions", {})
            if exts:
                grounded = exts.get("grounded", [])
                console.print(
                    f"  {fname}: grounded={{{', '.join(str(a) for a in grounded)}}}"
                )
            else:
                console.print(f"  {fname}")


def _render_counter_arguments(console, state: Dict[str, Any]):
    counters = state.get("counter_arguments", [])
    if not counters:
        return

    console.print(f"\n[bold]7. Counter-arguments[/bold] ({_section_ref(7)})")
    for ca in counters[:5]:
        strategy = ca.get("strategy", "?")
        content = _truncate(
            str(ca.get("counter_content", ca.get("original_argument", "")))
        )
        console.print(f"  [{strategy}] {content}")


def _render_debate(console, state: Dict[str, Any]):
    debates = state.get("debate_transcripts", [])
    gov = state.get("governance_decisions", [])
    if not debates and not gov:
        return

    console.print(f"\n[bold]8. Debate[/bold] ({_section_ref(8)})")
    if debates:
        console.print(f"  {len(debates)} debate rounds")
    if gov:
        for g in gov[:3]:
            method = g.get("method", "?")
            result_text = g.get("result", "")
            console.print(f"  Governance ({method}): {_truncate(str(result_text))}")


def _render_quality(console, state: Dict[str, Any]):
    scores = state.get("argument_quality_scores", {})
    if not scores:
        return

    console.print(f"\n[bold]9. Quality[/bold] ({_section_ref(9)})")
    for arg_id, quality in list(scores.items())[:5]:
        if isinstance(quality, dict):
            overall = quality.get("overall", "?")
            console.print(f"  {arg_id}: {overall}")
            # Cross-ref to fallacies
            console.print(
                f"    [dim](cross-ref: {_section_ref(3)} for fallacy impact)[/dim]"
            )


def _render_narrative(console, state: Dict[str, Any], result: Dict[str, Any]):
    conclusion = state.get("final_conclusion")
    if not conclusion:
        return

    console.print(f"\n[bold]10. Narrative[/bold] ({_section_ref(10)})")
    console.print(Panel(str(conclusion), border_style="green"))

    # Cross-references
    refs = []
    if state.get("identified_fallacies"):
        refs.append(_section_ref(3))
    if state.get("jtms_beliefs"):
        refs.append(_section_ref(4))
    if state.get("dung_frameworks"):
        refs.append(_section_ref(6))
    if refs:
        console.print(f"  [dim]Supporting evidence: {'; '.join(refs)}[/dim]")


def _render_plain(result: Dict[str, Any]):
    """Fallback plain-text renderer when Rich is not available."""
    state = result.get("state_snapshot", {})
    summary = result.get("summary", {})
    workflow = result.get("workflow_name", "unknown")
    print(f"\n{'='*60}")
    print(f" Spectacular Analysis — {workflow}")
    print(f"{'='*60}")
    print(f"  Phases: {summary.get('completed', 0)}/{summary.get('total', 0)}")
    print(f"  Fields: {_count_non_empty(state)}/{len(state)}")

    for key, value in state.items():
        if value and value not in ([], {}, "", None, 0):
            print(f"\n  [{key}]")
            if isinstance(value, dict):
                for k, v in list(value.items())[:5]:
                    print(f"    {k}: {_truncate(str(v))}")
            elif isinstance(value, list):
                for item in value[:5]:
                    print(f"    {_truncate(str(item))}")
            else:
                print(f"    {_truncate(str(value))}")


def render_state_snapshot(state: Any, console: Optional[Any] = None):
    """Convenience: render just a state object (not a full result).

    Args:
        state: UnifiedAnalysisState or RhetoricalAnalysisState instance.
        console: Optional Rich Console.
    """
    try:
        snapshot = state.get_state_snapshot(summarize=False)
    except Exception:
        snapshot = {}

    render_spectacular_result(
        {"state_snapshot": snapshot, "summary": {"completed": 0, "total": 0}},
        console=console,
    )
