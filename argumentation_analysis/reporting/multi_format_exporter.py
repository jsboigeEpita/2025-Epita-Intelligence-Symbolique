"""Multi-format spectacular export for UnifiedAnalysisState.

Exports the rich shared state into 6 formats: JSON, XML, Markdown, CSV
bundle, HTML, and Rich terminal output.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

_DIMENSION_LABELS = {
    "identified_arguments": "Arguments",
    "identified_fallacies": "Fallacies",
    "extracts": "Extracts",
    "counter_arguments": "Counter-Arguments",
    "argument_quality_scores": "Quality Scores",
    "jtms_beliefs": "JTMS Beliefs",
    "dung_frameworks": "Dung Frameworks",
    "governance_decisions": "Governance Decisions",
    "debate_transcripts": "Debate Transcripts",
    "neural_fallacy_scores": "Neural Fallacy Scores",
    "ranking_results": "Ranking Results",
    "aspic_results": "ASPIC Results",
    "belief_revision_results": "Belief Revision Results",
    "dialogue_results": "Dialogue Results",
    "probabilistic_results": "Probabilistic Results",
    "bipolar_results": "Bipolar Results",
    "fol_analysis_results": "FOL Analysis",
    "propositional_analysis_results": "PL Analysis",
    "modal_analysis_results": "Modal Analysis",
    "formal_synthesis_reports": "Formal Synthesis",
    "workflow_results": "Workflow Results",
    "atomic_propositions": "Atomic Propositions",
    "fol_shared_signature": "FOL Shared Signature",
    "final_conclusion": "Final Conclusion",
}


def _safe_str(val: Any, max_len: int = 200) -> str:
    s = str(val)
    return s if len(s) <= max_len else s[:max_len] + "..."


def _count_items(data: Any) -> int:
    if isinstance(data, (list, dict)):
        return len(data)
    if data is None:
        return 0
    return 1


class MultiFormatExporter:
    """Export UnifiedAnalysisState into multiple formats."""

    def __init__(self, state: Any):
        self._state = state
        self._snapshot: Optional[Dict[str, Any]] = None
        self._summary: Optional[Dict[str, Any]] = None

    @property
    def snapshot(self) -> Dict[str, Any]:
        if self._snapshot is None:
            self._snapshot = self._state.get_state_snapshot(summarize=False)
        return self._snapshot

    @property
    def summary(self) -> Dict[str, Any]:
        if self._summary is None:
            self._summary = self._state.get_state_snapshot(summarize=True)
        return self._summary

    def _reset_cache(self) -> None:
        self._snapshot = None
        self._summary = None

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def to_json(self, pretty: bool = True) -> str:
        indent = 2 if pretty else None
        return json.dumps(self.snapshot, indent=indent, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # XML
    # ------------------------------------------------------------------

    def to_xml(self) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<analysis_state>',
            f'  <generated_at>{datetime.now(timezone.utc).isoformat()}</generated_at>',
        ]
        lines.extend(self._xml_sections(self.snapshot))
        lines.append('</analysis_state>')
        return "\n".join(lines)

    def _xml_sections(self, data: Dict[str, Any], indent: int = 1) -> List[str]:
        lines: List[str] = []
        pad = "  " * indent
        for key, value in data.items():
            tag = key.replace("_", "-")
            label = _DIMENSION_LABELS.get(key, key)
            count = _count_items(value)
            if isinstance(value, dict) and count > 0:
                lines.append(f'{pad}<{tag} count="{count}" label="{label}">')
                for k, v in value.items():
                    inner_tag = "entry" if isinstance(v, dict) else "item"
                    if isinstance(v, dict):
                        lines.append(f'{pad}  <{inner_tag} id="{_xml_escape(k)}">')
                        for sk, sv in v.items():
                            lines.append(
                                f"{pad}    <{sk.replace('_', '-')}>{_xml_escape(_safe_str(sv, 500))}</{sk.replace('_', '-')}>"
                            )
                        lines.append(f"{pad}  </{inner_tag}>")
                    else:
                        lines.append(
                            f'{pad}  <{inner_tag} key="{_xml_escape(k)}">{_xml_escape(_safe_str(v))}</{inner_tag}>'
                        )
                lines.append(f"{pad}</{tag}>")
            elif isinstance(value, list) and count > 0:
                lines.append(f'{pad}<{tag} count="{count}" label="{label}">')
                for item in value[:100]:
                    if isinstance(item, dict):
                        lines.append(f"{pad}  <entry>")
                        for sk, sv in item.items():
                            lines.append(
                                f"{pad}    <{sk.replace('_', '-')}>{_xml_escape(_safe_str(sv, 500))}</{sk.replace('_', '-')}>"
                            )
                        lines.append(f"{pad}  </entry>")
                    else:
                        lines.append(f"{pad}  <item>{_xml_escape(_safe_str(item))}</item>")
                lines.append(f"{pad}</{tag}>")
            elif value is not None:
                lines.append(
                    f"{pad}<{tag} label=\"{label}\">{_xml_escape(_safe_str(value))}</{tag}>"
                )
        return lines

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    def to_markdown(self, sections: Optional[Sequence[str]] = None) -> str:
        lines: List[str] = [
            "# SCDA State Export",
            "",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]
        data = self.snapshot
        target_keys = sections if sections else list(data.keys())
        for key in target_keys:
            if key not in data:
                continue
            label = _DIMENSION_LABELS.get(key, key.replace("_", " ").title())
            value = data[key]
            count = _count_items(value)
            lines.append(f"## {label} ({count})")
            lines.append("")
            if isinstance(value, dict) and count > 0:
                for k, v in value.items():
                    if isinstance(v, dict):
                        lines.append(f"### {k}")
                        for sk, sv in v.items():
                            lines.append(f"- **{sk}:** {_safe_str(sv, 300)}")
                        lines.append("")
                    else:
                        lines.append(f"- **{k}:** {_safe_str(v, 300)}")
                lines.append("")
            elif isinstance(value, list) and count > 0:
                for i, item in enumerate(value[:50]):
                    if isinstance(item, dict):
                        lines.append(f"{i+1}. " + " | ".join(
                            f"**{sk}:** {_safe_str(sv, 100)}" for sk, sv in list(item.items())[:5]
                        ))
                    else:
                        lines.append(f"{i+1}. {_safe_str(item)}")
                if count > 50:
                    lines.append(f"... and {count - 50} more")
                lines.append("")
            elif value is not None:
                lines.append(f"```")
                lines.append(_safe_str(value, 2000))
                lines.append("```")
                lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # CSV bundle
    # ------------------------------------------------------------------

    def to_csv_bundle(self, out_dir: str | Path) -> List[Path]:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        data = self.snapshot
        written: List[Path] = []

        csv_specs = {
            "args.csv": ("identified_arguments", _dict_items_to_rows),
            "fallacies.csv": ("identified_fallacies", _dict_items_to_rows),
            "quality.csv": ("argument_quality_scores", _dict_items_to_rows),
            "counter_args.csv": ("counter_arguments", _list_items_to_rows),
            "debate.csv": ("debate_transcripts", _list_items_to_rows),
            "governance_votes.csv": ("governance_decisions", _list_items_to_rows),
        }

        for filename, (key, converter) in csv_specs.items():
            items = data.get(key)
            if not items:
                continue
            rows = converter(items)
            if not rows:
                continue
            path = out_dir / filename
            fieldnames = list(rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            written.append(path)

        return written

    # ------------------------------------------------------------------
    # HTML
    # ------------------------------------------------------------------

    def to_html(self, template: str = "spectacular") -> str:
        data = self.snapshot
        sections_html: List[str] = []

        for key, value in data.items():
            label = _DIMENSION_LABELS.get(key, key.replace("_", " ").title())
            count = _count_items(value)
            content = self._html_section_content(key, value)
            sections_html.append(
                f'<details><summary><strong>{label}</strong> ({count})</summary>'
                f'<div class="section-content">{content}</div></details>'
            )

        return "\n".join([
            "<!DOCTYPE html>",
            "<html lang='en'><head>",
            "<meta charset='UTF-8'>",
            "<title>SCDA Spectacular Export</title>",
            _HTML_STYLE,
            "</head><body>",
            "<h1>SCDA Spectacular State Export</h1>",
            f"<p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>",
            "<div class='summary-grid'>",
            self._html_summary_grid(data),
            "</div>",
            "<hr>",
            "\n".join(sections_html),
            "</body></html>",
        ])

    def _html_section_content(self, key: str, value: Any) -> str:
        if isinstance(value, dict):
            rows = []
            for k, v in value.items():
                if isinstance(v, dict):
                    inner = "".join(
                        f"<li><strong>{_html_escape(sk)}:</strong> {_html_escape(_safe_str(sv, 200))}</li>"
                        for sk, sv in v.items()
                    )
                    rows.append(f"<tr><td>{_html_escape(k)}</td><td><ul>{inner}</ul></td></tr>")
                else:
                    rows.append(f"<tr><td>{_html_escape(k)}</td><td>{_html_escape(_safe_str(v, 200))}</td></tr>")
            if rows:
                return "<table>" + "".join(rows) + "</table>"
            return "<p>(empty)</p>"
        if isinstance(value, list):
            if not value:
                return "<p>(empty)</p>"
            if isinstance(value[0], dict):
                rows = []
                for item in value[:50]:
                    cells = "".join(
                        f"<td>{_html_escape(_safe_str(v, 100))}</td>" for v in list(item.values())[:5]
                    )
                    rows.append(f"<tr>{cells}</tr>")
                header = "".join(
                    f"<th>{_html_escape(k)}</th>" for k in list(value[0].keys())[:5]
                )
                return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
            items = "".join(f"<li>{_html_escape(_safe_str(item))}</li>" for item in value[:50])
            return f"<ul>{items}</ul>"
        return f"<pre>{_html_escape(_safe_str(value, 1000))}</pre>"

    def _html_summary_grid(self, data: Dict[str, Any]) -> str:
        cards: List[str] = []
        for key, label in _DIMENSION_LABELS.items():
            val = data.get(key)
            if val is None:
                continue
            count = _count_items(val)
            cards.append(
                f'<div class="card"><span class="card-count">{count}</span>'
                f'<span class="card-label">{label}</span></div>'
            )
        return "\n".join(cards)

    # ------------------------------------------------------------------
    # Rich terminal
    # ------------------------------------------------------------------

    def to_rich_terminal(self) -> str:
        try:
            from argumentation_analysis.cli.output_formatter import render_state_snapshot

            buf = io.StringIO()
            from rich.console import Console
            console = Console(file=buf, width=120)
            render_state_snapshot(self._state, console=console)
            return buf.getvalue()
        except ImportError:
            logger.debug("Rich not available, falling back to plain text")
            return self.to_markdown()


# ======================================================================
# Helpers
# ======================================================================

def _xml_escape(text: Any) -> str:
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _html_escape(text: Any) -> str:
    import html
    return html.escape(str(text))


def _dict_items_to_rows(data: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for key, value in data.items():
        if isinstance(value, dict):
            row = {"id": key}
            for sk, sv in value.items():
                row[sk] = _safe_str(sv, 500)
            rows.append(row)
        else:
            rows.append({"id": key, "value": _safe_str(value, 500)})
    return rows


def _list_items_to_rows(data: List[Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in data:
        if isinstance(item, dict):
            row = {}
            for k, v in item.items():
                row[k] = _safe_str(v, 500)
            rows.append(row)
        else:
            rows.append({"value": _safe_str(item, 500)})
    return rows


_HTML_STYLE = """<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 1200px; margin: 0 auto; padding: 20px; background: #f8f9fa; color: #333; }
h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
details { background: white; margin: 8px 0; border-radius: 6px; padding: 12px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
summary { cursor: pointer; font-size: 1.1em; padding: 4px 0; }
.section-content { padding: 10px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 0.9em; }
th { background: #f1f3f5; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                gap: 10px; margin: 15px 0; }
.card { background: white; border-radius: 6px; padding: 12px; text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.card-count { display: block; font-size: 1.8em; font-weight: bold; color: #3498db; }
.card-label { display: block; font-size: 0.8em; color: #666; margin-top: 4px; }
hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }
ul { padding-left: 20px; }
li { margin: 2px 0; }
pre { background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }
</style>"""
