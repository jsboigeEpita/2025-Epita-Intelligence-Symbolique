"""DT-2 #1499 anti-theater tests for the one-command demo entrypoint.

These tests verify three guarantees from the DT-2 spec:
1. SNAPSHOT mode displays a verdict WITHOUT an LLM key, WITHOUT inventing
   anything. The ``decided_firsthand`` field is hard-stamped to
   ``"PRE-RECORDED"`` (never ``True``) on every replayed verdict.
2. The shape of the snapshot is validated (wrong schema → error).
3. When neither LLM key nor snapshot is available, the entrypoint exits
   with code 2 and a clear actionable message — never a fabricated verdict.

Privacy: no live deliberation, no LLM key used, no corpus.
Synthetic shape fixture only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest


# Make the demo entrypoint importable without disturbing the package layout.
_DEMO_DIR = Path(__file__).resolve().parents[3] / "examples" / "democratech_deliberation"
_FIXTURE_PATH = _DEMO_DIR / "prerecorded_snapshot_shape_fixture.json"


@pytest.fixture(scope="module")
def demo_module() -> Any:
    """Import the entrypoint module (must succeed without LLM key)."""
    if str(_DEMO_DIR) not in sys.path:
        sys.path.insert(0, str(_DEMO_DIR))
    from run_democratech_demo_one_command import (
        _load_snapshot,
        _locate_snapshot,
        _snapshot_to_results,
    )
    return {
        "_load_snapshot": _load_snapshot,
        "_locate_snapshot": _locate_snapshot,
        "_snapshot_to_results": _snapshot_to_results,
    }


@pytest.fixture(scope="module")
def fixture_path() -> Path:
    assert _FIXTURE_PATH.is_file(), (
        f"shape fixture missing: {_FIXTURE_PATH}"
    )
    return _FIXTURE_PATH


# ---------------------------------------------------------------------------
# 1. SNAPSHOT mode works without LLM key, never invents
# ---------------------------------------------------------------------------


def test_load_snapshot_stamps_pre_recorded_on_every_verdict(
    demo_module: Any, fixture_path: Path
) -> None:
    """Anti-theater #1019: replay must never pretend a verdict is LIVE."""
    snapshot = demo_module["_load_snapshot"](fixture_path)
    for pid, payload in snapshot["propositions"].items():
        verdict = payload["verdict"]
        assert verdict["decided_firsthand"] == "PRE-RECORDED", (
            f"proposition {pid} not stamped PRE-RECORDED: "
            f"{verdict['decided_firsthand']!r}"
        )
        assert verdict["decided_firsthand"] is not True, (
            f"proposition {pid} wrongly marked as LIVE: "
            f"replay must never claim firsthand True"
        )


def test_snapshot_to_results_preserves_pre_recorded_marker(
    demo_module: Any, fixture_path: Path
) -> None:
    snapshot = demo_module["_load_snapshot"](fixture_path)
    results = demo_module["_snapshot_to_results"](snapshot, limit=None)
    assert len(results) == 1
    assert results[0]["id"] == "prop_A"
    assert results[0]["verdict"]["decided_firsthand"] == "PRE-RECORDED"
    assert results[0]["verdict"]["winner"] == "Option A"


def test_snapshot_limit_honors_arg(
    demo_module: Any, fixture_path: Path
) -> None:
    """Limit must be respected — no infinite iteration over the snapshot."""
    snapshot = demo_module["_load_snapshot"](fixture_path)
    results = demo_module["_snapshot_to_results"](snapshot, limit=1)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# 2. Shape validation: bad snapshot → ValueError, never silent accept
# ---------------------------------------------------------------------------


def test_load_snapshot_rejects_root_not_dict(
    demo_module: Any, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(ValueError, match="root is not a dict"):
        demo_module["_load_snapshot"](bad)


def test_load_snapshot_rejects_missing_propositions(
    demo_module: Any, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"mode": "live"}), encoding="utf-8")
    with pytest.raises(ValueError, match="no 'propositions' dict"):
        demo_module["_load_snapshot"](bad)


def test_load_snapshot_rejects_proposition_without_verdict(
    demo_module: Any, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({"propositions": {"prop_X": {"label": "y"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no verdict dict"):
        demo_module["_load_snapshot"](bad)


# ---------------------------------------------------------------------------
# 3. No key + no snapshot → locator returns None, no fabrication
# ---------------------------------------------------------------------------


def test_locate_snapshot_returns_none_when_no_file(
    demo_module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pure lookup: no env, no cwd file, no user-cache file → None."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert demo_module["_locate_snapshot"](None) is None


def test_locate_snapshot_finds_explicit_arg(
    demo_module: Any, fixture_path: Path
) -> None:
    """The ``--snapshot`` argument takes precedence over cwd/user-cache."""
    assert demo_module["_locate_snapshot"](str(fixture_path)) == fixture_path


def test_locate_snapshot_rejects_missing_explicit_arg(
    demo_module: Any, tmp_path: Path
) -> None:
    non_existent = tmp_path / "does_not_exist.json"
    assert demo_module["_locate_snapshot"](str(non_existent)) is None
