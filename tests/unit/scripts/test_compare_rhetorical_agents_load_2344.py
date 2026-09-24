"""#2344 — the comparison CLI says why it stops: a load failure is not "no result".

``load_results_from_json`` returned ``[]`` for a missing file, malformed JSON
or a JSON that is not a list, and the CLI answered each of them, and a
legitimately empty results file, with the same "no result could be loaded".
The loader now raises; the CLI names the cause, and keeps its own message
for a file that holds an empty list.
"""

import json
import logging
import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "reporting"
    / "compare_rhetorical_agents.py"
)


def _run(monkeypatch, base: Path, advanced: Path, out: Path):
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "-b", str(base), "-a", str(advanced), "-o", str(out)],
    )
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    return stop.value.code


def test_missing_base_file_is_named_as_a_load_failure(tmp_path, monkeypatch, caplog):
    advanced = tmp_path / "advanced.json"
    advanced.write_text(json.dumps([{"source_name": "s"}]), encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        code = _run(monkeypatch, tmp_path / "absent.json", advanced, tmp_path / "o")
    assert code == 1
    assert "Chargement impossible" in caplog.text
    assert "absent.json" in caplog.text


def test_empty_base_file_is_named_as_empty(tmp_path, monkeypatch, caplog):
    base = tmp_path / "base.json"
    base.write_text("[]", encoding="utf-8")
    advanced = tmp_path / "advanced.json"
    advanced.write_text(json.dumps([{"source_name": "s"}]), encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        code = _run(monkeypatch, base, advanced, tmp_path / "o")
    assert code == 1
    assert "ne contient aucun résultat" in caplog.text
    assert "Chargement impossible" not in caplog.text
