"""#3658 item 46c — the act replay's launcher: preflight first, then measurement.

``scripts/panel/replay_acts.py`` is the one command that decides whether a
replay may run, then produces the text a blind judge would read and compares
it with a reference rebuilt by the original code. Three claims are witnessed
here, each with the control that makes its zero mean something:

* the preflight answers **before** any text builder exists — a failing cycle
  imports neither the judge's entry point nor the pipeline runtime, and writes
  nothing; the same probe on a whole cycle shows both modules *do* load, so the
  first reading is not a guard that never fires;
* the replay path reproduces the harvest's render byte for byte on every
  record, and each recorded act alters it in the direction its branch states —
  ``acts``/``cut`` must move, ``non_argumentative``/``conversation_real``/
  ``hierarchical_delegation`` must not;
* the comparison can fail: an instrument that ignores the acts, or a reference
  that differs by one byte, is caught by the same run that passes otherwise.

Stub seat, no key, no client, no corpus: every fixture below is invented, and
no case pays a model call (``llm_requests`` is 0 on every path).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import act_replay_fidelity as w  # noqa: E402
from scripts.panel import replay_acts as ra  # noqa: E402

DOCS = ("doc_s1", "doc_s2")
MARK = "INVENTED-ACT-launcher-3658"

#: Read the child's ``sys.modules`` after the launcher ran: which of the text
#: builders exist in the process, and what the command answered.
CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
from scripts.panel import replay_acts as ra
rc = ra.main(sys.argv[2:])
wanted = ("scripts.dataset.judge_panel", "scripts.dataset.render_campaign_reading_folder",
          "scripts.dataset.run_corpus_batch", "argumentation_analysis")
print("CHILD " + json.dumps({
    "rc": rc,
    "loaded": sorted(name for name in wanted if name in sys.modules),
    "live_module": "scripts.panel.act_replay_live" in sys.modules,
}))
"""


# ---------------------------------------------------------------------------
# Invented fixtures
# ---------------------------------------------------------------------------


def _state(doc: str) -> Dict[str, Any]:
    state = dict(w.SYNTHETIC_STATE)
    state[w.ACTS[0]] = f"{MARK} cadre inventé pour {doc}."
    state["raw_text"] = f"Texte inventé du document {doc}, sans corpus."
    return state


def _write_cycle(
    root: Path,
    docs: Sequence[str] = DOCS,
    *,
    rc: int = 0,
    classification: Optional[str] = None,
) -> Path:
    """A harvested cycle as the harvest contract writes it: both folders, the
    two records the preflight compares, and the sanitised signature."""
    cycle = root / "cycle"
    (cycle / "states").mkdir(parents=True)
    (cycle / "signatures").mkdir(parents=True)
    for doc in docs:
        state = _state(doc)
        (cycle / "states" / f"state_full_{doc}.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
        recorded: Dict[str, Any] = {
            key: {"length": len(state.get(key) or ""), "stripped": True}
            for key in w.RENDER_INPUTS
        }
        recorded[w.QUESTION] = state.get(w.QUESTION)
        signature = {
            **w.SYNTHETIC_SIGNATURE,
            "opaque_id": doc,
            "document_classification": classification,
            "state": recorded,
        }
        (cycle / "signatures" / f"signature_{doc}.json").write_text(
            json.dumps(signature, ensure_ascii=False), encoding="utf-8"
        )
    (cycle / "cycle.json").write_text(
        json.dumps({"panel_size": len(docs)}), encoding="utf-8"
    )
    (cycle / "pipeline.json").write_text(
        json.dumps(
            {
                "rc": rc,
                "head": "a" * 40,
                "head_after": "a" * 40,
                "harvest": {"copied": len(docs), "missing": 0, "stale": 0},
            }
        ),
        encoding="utf-8",
    )
    return cycle


def _run_child(*argv: str) -> Dict[str, Any]:
    """The launcher in a fresh interpreter, and the modules it left behind."""
    done = subprocess.run(
        [sys.executable, "-c", CHILD, str(REPO_ROOT), *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    for line in done.stdout.splitlines():
        if line.startswith("CHILD "):
            return json.loads(line[len("CHILD ") :])
    raise AssertionError(
        f"the child printed no verdict (rc={done.returncode})\n"
        f"--- stdout\n{done.stdout[-3000:]}\n--- stderr\n{done.stderr[-3000:]}"
    )


# ---------------------------------------------------------------------------
# 1. The preflight answers before any text builder exists
# ---------------------------------------------------------------------------


def test_a_failing_preflight_imports_no_text_builder_and_writes_nothing(
    tmp_path: Path,
) -> None:
    cycle = _write_cycle(tmp_path)
    (cycle / "pipeline.json").unlink()  # the preflight's own record check
    dest = tmp_path / "dest"

    child = _run_child("--cycle-dir", str(cycle), "--dest", str(dest))

    assert child["rc"] == ra.EXIT_FAILED
    assert child["loaded"] == []
    assert not dest.exists()


def test_the_same_probe_does_import_the_builders_on_a_whole_cycle(
    tmp_path: Path,
) -> None:
    """The control for the test above: the guard is not vacuous.

    On a cycle that passes the preflight the judge's entry point and the
    pipeline runtime *are* loaded — so 'no module loaded' above is a reading
    of the preflight gate, not of an import that never happens at all.
    """
    cycle = _write_cycle(tmp_path)
    dest = tmp_path / "dest"

    child = _run_child("--cycle-dir", str(cycle), "--dest", str(dest))

    assert child["rc"] == ra.EXIT_OK
    assert "scripts.dataset.judge_panel" in child["loaded"]
    assert dest.is_dir()


def test_the_live_path_refuses_a_destination_that_is_not_a_tag(
    tmp_path: Path,
) -> None:
    """``--acts live`` runs, and stops before spending: a destination outside
    the cycles' folder is not a tag the judges stage could open."""
    cycle = _write_cycle(tmp_path)
    dest = tmp_path / "dest"

    child = _run_child(
        "--cycle-dir", str(cycle), "--dest", str(dest), "--acts", ra.LIVE
    )

    assert child["rc"] == ra.EXIT_USAGE
    assert child["live_module"] is True
    assert child["loaded"] == []
    assert not dest.exists()


def test_the_live_path_reaches_the_live_runner_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The routing witness: the launcher calls the live module's own ``main``,
    with the panel it parsed and the arguments it received."""
    from scripts.panel import act_replay_live as live

    cycle = _write_cycle(tmp_path)
    dest = tmp_path / "dest"
    seen: List[Any] = []

    def _recorded(*args: Any, **kwargs: Any) -> int:
        seen.append((args, kwargs))
        return 7

    monkeypatch.setattr(live, "main", _recorded)

    rc = ra.main(["--cycle-dir", str(cycle), "--dest", str(dest), "--acts", ra.LIVE])

    assert rc == 7
    args, kwargs = seen[0]
    assert args[0] == cycle and args[1] == dest
    assert args[2] is None and kwargs == {}
    assert args[3][-2:] == ["--acts", ra.LIVE]


# ---------------------------------------------------------------------------
# 2. The replay reproduces the render, and each act reaches it
# ---------------------------------------------------------------------------


def test_every_document_round_trips_and_its_acts_reach_the_render(
    tmp_path: Path,
) -> None:
    cycle = _write_cycle(tmp_path)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    assert report["ok"] is True, report["failures"]
    assert report["counts"]["documents"] == len(DOCS)
    assert report["counts"]["render_mismatches"] == 0
    assert report["counts"]["controls_ok"] == len(DOCS)
    assert report["counts"]["act_alterations_moved"] == 3 * len(DOCS)


def test_three_constructions_one_string(tmp_path: Path) -> None:
    cycle = _write_cycle(tmp_path)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    for entry in report["documents"]:
        assert entry["branch"] == w.BRANCH_ACTS
        assert entry["equal"] == {"judge_vs_replay": True, "fiche_vs_replay": True}
        assert entry["reference"]["sha256"] == entry["callers"]["replay"]["sha256"]
        assert entry["control"]["direction"] == ra.MUST_MOVE
        assert entry["control"]["did_not_move"] == []


def test_the_report_never_carries_the_act_text(tmp_path: Path) -> None:
    cycle = _write_cycle(tmp_path)
    dest = tmp_path / "dest"

    assert ra.main(["--cycle-dir", str(cycle), "--dest", str(dest)]) == ra.EXIT_OK

    written = (dest / ra.REPORT).read_text(encoding="utf-8")
    assert MARK not in written
    assert "Texte inventé du document" not in written
    report = json.loads(written)
    assert list(report)[0] == "provenance"
    assert report["provenance"]["llm_requests"] == 0
    instruments = report["provenance"]["code"]["instruments"]
    assert all(instruments[name] for name in instruments), instruments


# ---------------------------------------------------------------------------
# 2b. The report digests the cycle's inputs before and after the measurement
# ---------------------------------------------------------------------------


def _files_on_disk(cycle: Path) -> Dict[str, str]:
    """What the cycle holds, read independently of the launcher's own reader."""
    return {
        path.relative_to(cycle)
        .as_posix(): hashlib.sha256(path.read_bytes())
        .hexdigest()
        for path in cycle.rglob("*")
        if path.is_file()
    }


def _last_json_object(out: str) -> Dict[str, Any]:
    """The last JSON object printed on stdout, whatever else the imports said."""
    lines = out.splitlines()
    for start in range(len(lines) - 1, -1, -1):
        if lines[start] != "{":
            continue
        try:
            return json.loads("\n".join(lines[start:]))
        except ValueError:
            continue
    raise AssertionError(f"no JSON object on stdout:\n{out}")


def _writing_during_the_run(
    cycle: Path, monkeypatch: pytest.MonkeyPatch, write
) -> None:
    """Break, on purpose, the claim that the replay writes nothing: ``write``
    runs while the second document is measured."""
    real = ra.document

    def _then_writes(
        doc: str, state: Any, signature: Any, fidelity: Any
    ) -> Dict[str, Any]:
        if doc == DOCS[1]:
            write(cycle)
        return real(doc, state, signature, fidelity)

    monkeypatch.setattr(ra, "document", _then_writes)


def test_the_report_digests_every_input_file_before_and_after(tmp_path: Path) -> None:
    cycle = _write_cycle(tmp_path)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    on_disk = _files_on_disk(cycle)
    assert (
        len(on_disk) == 2 * len(DOCS) + 2
    )  # state + signature per document, two records
    assert report["cycle_inputs"] == {
        "files": len(on_disk),
        "unchanged": True,
        "drifted": [],
        "before": on_disk,
        "after": on_disk,
    }
    assert report["ok"] is True, report["failures"]


def test_a_file_rewritten_during_the_run_is_named_and_fails_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The witness: one byte written into the cycle it reads reddens — and the
    red is the cycle's, not a render's (the documents still round-trip)."""
    cycle = _write_cycle(tmp_path)
    touched = cycle / "states" / f"state_full_{DOCS[0]}.json"

    def _append(cycle: Path) -> None:
        touched.write_text(touched.read_text(encoding="utf-8") + " ", encoding="utf-8")

    _writing_during_the_run(cycle, monkeypatch, _append)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    inputs = report["cycle_inputs"]
    name = f"states/state_full_{DOCS[0]}.json"
    original = json.dumps(_state(DOCS[0]), ensure_ascii=False).encode("utf-8")
    assert report["failures"] == {}
    assert report["ok"] is False
    assert inputs["unchanged"] is False
    assert inputs["drifted"] == [name]
    assert set(inputs["before"]) == set(inputs["after"])
    assert inputs["before"][name] == hashlib.sha256(original).hexdigest()
    assert inputs["after"][name] == hashlib.sha256(original + b" ").hexdigest()


def test_a_file_added_into_the_cycle_during_the_run_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that was not there before is a write too, not a pass."""
    cycle = _write_cycle(tmp_path)

    def _add(cycle: Path) -> None:
        (cycle / "states" / "state_full_extra.json").write_text("{}", encoding="utf-8")

    _writing_during_the_run(cycle, monkeypatch, _add)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    assert report["ok"] is False
    assert report["cycle_inputs"]["drifted"] == ["states/state_full_extra.json"]
    assert (
        report["cycle_inputs"]["after"]["states/state_full_extra.json"]
        == hashlib.sha256(b"{}").hexdigest()
    )


def test_the_command_line_summary_names_what_drifted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 1, and the one-line summary says why without the whole map; the
    report on disk keeps the map."""
    cycle = _write_cycle(tmp_path)

    def _rewrite(cycle: Path) -> None:
        (cycle / "cycle.json").write_text("{}", encoding="utf-8")

    _writing_during_the_run(cycle, monkeypatch, _rewrite)
    dest = tmp_path / "dest"

    assert ra.main(["--cycle-dir", str(cycle), "--dest", str(dest)]) == ra.EXIT_FAILED

    out = capsys.readouterr().out
    summary = _last_json_object(out)
    assert summary["cycle_inputs"] == {
        "files": 2 * len(DOCS) + 2,
        "unchanged": False,
        "drifted": ["cycle.json"],
    }
    written = json.loads((dest / ra.REPORT).read_text(encoding="utf-8"))
    assert (
        written["cycle_inputs"]["before"]["cycle.json"]
        != written["cycle_inputs"]["after"]["cycle.json"]
    )


# ---------------------------------------------------------------------------
# 3. The comparison can fail — mutations of the launcher's own instrument
# ---------------------------------------------------------------------------


def test_an_instrument_that_ignores_the_acts_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutating the replay path to drop its ``acts`` argument must redden."""
    cycle = _write_cycle(tmp_path)
    monkeypatch.setattr(
        w,
        "replay_render",
        lambda state, signature, acts=None: w.judge_render(state, signature),
    )

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    assert report["ok"] is False
    assert report["counts"]["act_alterations_moved"] == 0
    assert all(
        "did not" in reason
        for reasons in report["failures"].values()
        for reason in reasons
    )


def test_a_reference_that_differs_by_a_byte_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cycle = _write_cycle(tmp_path)
    real = w.judge_render
    monkeypatch.setattr(
        w, "judge_render", lambda state, signature: real(state, signature) + " "
    )

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    assert report["ok"] is False
    assert report["counts"]["render_mismatches"] == len(DOCS)


def test_a_broken_record_does_not_cost_the_others_their_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cycle = _write_cycle(tmp_path)
    real = ra.document

    def _half(doc: str, state: Any, signature: Any, fidelity: Any) -> Dict[str, Any]:
        if doc == DOCS[1]:
            raise ValueError("invented failure")
        return real(doc, state, signature, fidelity)

    monkeypatch.setattr(ra, "document", _half)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    assert report["ok"] is False
    assert report["counts"]["documents_ok"] == 1
    assert report["failures"][DOCS[1]] == ["measurement failed (ValueError)"]
    assert DOCS[0] not in report["failures"]


# ---------------------------------------------------------------------------
# 4. The direction the control must hold comes from the branch
# ---------------------------------------------------------------------------


class _Shim:
    """The fidelity module, with a ``compare`` whose answer we choose."""

    def __init__(self, moves: bool) -> None:
        self.moves = moves

    def __getattr__(self, name: str) -> Any:
        return getattr(w, name)

    def compare(self, reference: str, rebuilt: str) -> Dict[str, Any]:
        return {
            "equal": not self.moves,
            "sections_differing": ["Acte I — cadrage"] if self.moves else [],
            "sections_only_in_reference": [],
            "sections_only_in_rebuilt": [],
        }

    def replay_render(self, state: Any, signature: Any, acts: Any = None) -> str:
        return "invented render"


@pytest.mark.parametrize(
    "branch, direction",
    [
        (w.BRANCH_ACTS, ra.MUST_MOVE),
        (w.BRANCH_CUT, ra.MUST_MOVE),
        (w.BRANCH_NON_ARGUMENTATIVE, ra.MUST_NOT_MOVE),
        (w.BRANCH_CONVERSATION_REAL, ra.MUST_NOT_MOVE),
        (w.BRANCH_HIERARCHICAL_DELEGATION, ra.MUST_NOT_MOVE),
    ],
)
def test_the_branch_states_the_direction(branch: str, direction: str) -> None:
    assert ra.direction_of(branch, w) == direction


def test_a_branch_without_a_stated_direction_fails_closed() -> None:
    """A control with no stated direction measures nothing, so it is a failure."""
    assert ra.direction_of("some_future_branch", w) is None

    control = ra.controls(
        {},
        {},
        "reference",
        {key: f"act for {key}" for key in w.ACTS},
        "some_future_branch",
        _Shim(moves=False),
    )

    assert control["ok"] is False
    assert control["direction"] is None


def test_a_non_argumentative_render_must_not_read_the_acts() -> None:
    """None of the three acts may move it — and if one does, that is the defect."""
    recorded = {key: f"act for {key}" for key in w.ACTS}

    held = ra.controls(
        {}, {}, "ref", recorded, w.BRANCH_NON_ARGUMENTATIVE, _Shim(False)
    )
    leaked = ra.controls(
        {}, {}, "ref", recorded, w.BRANCH_NON_ARGUMENTATIVE, _Shim(True)
    )

    assert held["ok"] is True and held["moved"] == []
    assert leaked["ok"] is False and leaked["moved"] == list(w.ACTS)


def test_an_acts_branch_that_loses_one_act_is_named() -> None:
    recorded = {key: f"act for {key}" for key in w.ACTS}

    control = ra.controls({}, {}, "ref", recorded, w.BRANCH_ACTS, _Shim(False))

    assert control["ok"] is False
    assert control["did_not_move"] == list(w.ACTS)


# ---------------------------------------------------------------------------
# 5. The cycle's own records are applied before any measurement
# ---------------------------------------------------------------------------


def test_a_cycle_whose_batch_failed_is_refused_before_measuring(tmp_path: Path) -> None:
    cycle = _write_cycle(tmp_path, rc=1)

    report = ra.replay(cycle, tmp_path / "dest", list(DOCS))

    assert report["ok"] is False
    assert report["stage"] == ra.STAGE_CYCLE
    assert "exit 1" in report["refused"]
    assert "documents" not in report


def test_a_refused_cycle_still_writes_the_named_reason(tmp_path: Path) -> None:
    """Past the preflight the destination is free and legitimate: a named
    refusal on disk is a record, not a leak."""
    cycle = _write_cycle(tmp_path, rc=1)
    dest = tmp_path / "dest"

    assert ra.main(["--cycle-dir", str(cycle), "--dest", str(dest)]) == ra.EXIT_FAILED

    report = json.loads((dest / ra.REPORT).read_text(encoding="utf-8"))
    assert report["stage"] == ra.STAGE_CYCLE
