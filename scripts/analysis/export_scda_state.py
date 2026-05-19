#!/usr/bin/env python
"""CLI to export SCDA analysis state into multiple formats.

Usage:
    python scripts/analysis/export_scda_state.py --state results/state.json --format json --out outputs/
    python scripts/analysis/export_scda_state.py --state results/state.json --format all --out outputs/
"""

import argparse
import json
import sys
from pathlib import Path


def _load_state(state_path: str):
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _DictStateProxy(data)


class _DictStateProxy:
    """Minimal state-like object wrapping a dict for MultiFormatExporter."""

    def __init__(self, data: dict):
        self._data = data

    def get_state_snapshot(self, summarize: bool = False):
        return self._data


def main():
    parser = argparse.ArgumentParser(description="Export SCDA state into multiple formats")
    parser.add_argument("--state", required=True, help="Path to state JSON file")
    parser.add_argument(
        "--format",
        required=True,
        choices=["json", "xml", "md", "csv", "html", "rich", "all"],
        help="Output format (or 'all' for every format)",
    )
    parser.add_argument("--out", default=".", help="Output directory")
    args = parser.parse_args()

    state = _load_state(args.state)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from argumentation_analysis.reporting.multi_format_exporter import MultiFormatExporter

    exporter = MultiFormatExporter(state)

    fmt = args.format
    formats = ["json", "xml", "md", "csv", "html", "rich"] if fmt == "all" else [fmt]
    written = []

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

    for p in written:
        print(f"  {p}")
    print(f"Exported {len(written)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
