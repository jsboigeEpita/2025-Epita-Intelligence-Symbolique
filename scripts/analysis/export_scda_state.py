#!/usr/bin/env python
"""CLI to export SCDA analysis state into multiple formats.

Usage:
    python scripts/analysis/export_scda_state.py --state results/state.json --format json
    python scripts/analysis/export_scda_state.py --state results/state.json --format all --out outputs/tmp

L'export passe par la **même** décontamination que le bundle
(`argumentation_analysis.evaluation.state_export_scrub`) : les champs de texte
brut sont retirés et les entités remplacées. Le répertoire de sortie par défaut,
`outputs/scda_export/`, est gitignoré en bloc (`.gitignore:171`) — un export
lancé sans `--out` ne peut donc pas déposer de texte brut dans un répertoire
suivi par git.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

#: Répertoire de sortie par défaut. `outputs/` est gitignoré en bloc
#: (`.gitignore:171`), et c'est déjà là que vivent les états SCDA que le
#: bundle relit (`outputs/scda_audit/`).
DEFAULT_OUT_DIR = "outputs/scda_export"


def _load_state(state_path: str) -> Dict[str, Any]:
    with open(state_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return data


class _DictStateProxy:
    """Minimal state-like object wrapping a dict for MultiFormatExporter."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def get_state_snapshot(self, summarize: bool = False) -> Dict[str, Any]:
        return self._data


def _scrub_state(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """La frontière privacy, partagée avec `generate_spectacular_bundle.py`.

    `MultiFormatExporter` est brut par conception : il ne décontamine rien. La
    frontière vit chez l'appelant, et les deux appelants appellent désormais la
    même fonction.
    """
    from argumentation_analysis.evaluation.state_export_scrub import (
        _scrub_state_for_export,
    )

    return _scrub_state_for_export(state_data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export SCDA state into multiple formats")
    parser.add_argument("--state", required=True, help="Path to state JSON file")
    parser.add_argument(
        "--format",
        required=True,
        choices=["json", "xml", "md", "csv", "html", "rich", "all"],
        help="Output format (or 'all' for every format)",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR}, gitignored)",
    )
    return parser


def export_state(state_path: str, fmt: str, out_dir: Path) -> List[Path]:
    """Écrit l'état **décontaminé** dans `out_dir` ; rend les chemins écrits."""
    state = _DictStateProxy(_scrub_state(_load_state(state_path)))
    out_dir.mkdir(parents=True, exist_ok=True)

    from argumentation_analysis.reporting.multi_format_exporter import MultiFormatExporter

    exporter = MultiFormatExporter(state)

    formats = ["json", "xml", "md", "csv", "html", "rich"] if fmt == "all" else [fmt]
    written: List[Path] = []

    for f in formats:
        try:
            if f == "json":
                path = out_dir / "state.json"
                path.write_text(exporter.to_json(pretty=True), encoding="utf-8")
                written.append(path)
            elif f == "xml":
                path = out_dir / "state.xml"
                path.write_text(exporter.to_xml(), encoding="utf-8")
                written.append(path)
            elif f == "md":
                path = out_dir / "state.md"
                path.write_text(exporter.to_markdown(), encoding="utf-8")
                written.append(path)
            elif f == "csv":
                csv_files = exporter.to_csv_bundle(out_dir)
                written.extend(csv_files)
            elif f == "html":
                path = out_dir / "state.html"
                path.write_text(exporter.to_html(), encoding="utf-8")
                written.append(path)
            elif f == "rich":
                path = out_dir / "state_terminal.txt"
                path.write_text(exporter.to_rich_terminal(), encoding="utf-8")
                written.append(path)
        except Exception as e:
            print(f"ERROR exporting {f}: {e}", file=sys.stderr)

    return written


def main() -> None:
    args = build_parser().parse_args()
    written = export_state(args.state, args.format, Path(args.out))

    for p in written:
        print(f"  {p}")
    print(f"Exported {len(written)} file(s) to {args.out}")


if __name__ == "__main__":
    main()
