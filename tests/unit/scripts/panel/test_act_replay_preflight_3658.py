"""#3658 item 46c — the act replay's keyless input and destination preflight.

``scripts/panel/replay_acts.py`` re-runs Acts I-III on a harvested cycle and
pays one model call per act and per document. Before the first call — before
any model client exists — the preflight answers from the files alone: does the
cycle hold the panel its own harvest recorded, does each state carry the
signature it was written with, is the destination a fresh place of its own.
It reads; it never writes.

Stub seat, no key, no client, no corpus: every fixture below is invented.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import act_replay_preflight as ap  # noqa: E402
from tests.support.tree_walk import iter_files  # noqa: E402

DOCS = ("doc_x1", "doc_x2")
MARK_ACT = "INVENTED-ACT-7f3a"
MARK_NAME = "INVENTED-NAME-91c0"

#: The import graph a keyless preflight must not touch — a model client, the
#: native runtime the pipeline drags with it, and the project package itself.
FORBIDDEN = (
    "semantic_kernel",
    "openai",
    "anthropic",
    "jpype",
    "torch",
    "transformers",
    "httpx",
    "requests",
    "argumentation_analysis",
)

CHILD = """
import builtins, runpy, sys
FORBIDDEN = %r
_real = builtins.__import__


def _guard(name, *args, **kwargs):
    if name.split(".")[0] in FORBIDDEN:
        raise ImportError("forbidden import: " + name.split(".")[0])
    return _real(name, *args, **kwargs)


builtins.__import__ = _guard
script = sys.argv[1]
sys.argv = [script] + sys.argv[2:]
runpy.run_path(script, run_name="__main__")
"""

_KEYLIKE = re.compile(r"KEY|TOKEN|SECRET|PASSPHRASE|PASSWORD|CREDENTIAL", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Invented fixtures
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _state(doc: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {"raw_text": f"An invented source, for {doc}."}
    for act in ap.ACTS:
        state[act] = f"{MARK_ACT} {doc} {act}."
    state["llm_usage"] = {"act1_framing": {"calls": 1, "cost_usd": 0.01}}
    return state


def _signature(doc: str, state: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {k: v for k, v in state.items() if k != "raw_text"}
    for act in ap.ACTS:
        text = sanitized.get(act)
        if isinstance(text, str):
            sanitized[act] = {"length": len(text), "stripped": True}
    return {
        "opaque_id": doc,
        "outcome": {"status": "ok"},
        "state": sanitized,
        "llm_usage": state["llm_usage"],
        "metadata": {"speaker": MARK_NAME},
    }


def _cycle(
    root: Path,
    docs: Sequence[str] = DOCS,
    *,
    copied: Optional[int] = None,
    missing: int = 0,
    stale: int = 0,
    panel_size: Optional[int] = None,
) -> Path:
    cycle = Path(root) / "panel_cycles" / "invented"
    for doc in docs:
        state = _state(doc)
        _write_json(cycle / "states" / f"state_full_{doc}.json", state)
        _write_json(
            cycle / "signatures" / f"signature_{doc}.json", _signature(doc, state)
        )
    _write_json(
        cycle / "pipeline.json",
        {
            "rc": 0,
            "harvest": {
                "copied": len(docs) if copied is None else copied,
                "missing": missing,
                "stale": stale,
            },
        },
    )
    _write_json(
        cycle / "cycle.json",
        {"panel_size": len(docs) if panel_size is None else panel_size},
    )
    return cycle


def _state_path(cycle: Path, doc: str) -> Path:
    return cycle / "states" / f"state_full_{doc}.json"


def _sig_path(cycle: Path, doc: str) -> Path:
    return cycle / "signatures" / f"signature_{doc}.json"


def _edit(path: Path, change: Callable[[Dict[str, Any]], None]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    change(payload)
    _write_json(path, payload)


def _kinds(verdict: ap.Verdict) -> List[str]:
    return [problem.kind for problem in verdict.problems]


def _details(verdict: ap.Verdict) -> List[str]:
    return [problem.detail for problem in verdict.problems]


def _fresh(tmp_path: Path) -> Path:
    return tmp_path / "replay_out"


def _snapshot(cycle: Path) -> Tuple[List[str], Dict[str, str]]:
    """The fixture's tree, byte for byte: every file under the fixture's root
    with its sha256, and the directory entries of the tree the fixture built —
    an empty directory has no file to show. The files come through
    ``iter_files``, the walker ``tests/`` shares (#2607); nothing here walks a
    tree of its own."""
    root = cycle.parents[1]
    entries: List[str] = []
    digests: Dict[str, str] = {}
    for path in sorted(iter_files(root, pattern="*")):
        rel = path.relative_to(root).as_posix()
        entries.append(rel)
        digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    directories = [
        root,
        cycle.parents[0],
        cycle,
        cycle / ap.STATES_DIR,
        cycle / ap.SIGNATURES_DIR,
    ]
    for directory in directories:
        entries.extend(
            path.relative_to(root).as_posix() + "/"
            for path in directory.iterdir()
            if path.is_dir()
        )
    return sorted(entries), digests


def _keyless_env() -> Dict[str, str]:
    """This process's environment minus every variable that could carry a credential."""
    return {k: v for k, v in os.environ.items() if not _KEYLIKE.search(k)}


# ---------------------------------------------------------------------------
# 1. Panel membership
# ---------------------------------------------------------------------------


def test_a_whole_cycle_passes_and_counts_its_pairs(tmp_path: Path) -> None:
    verdict = ap.preflight(_cycle(tmp_path), _fresh(tmp_path))

    assert verdict.ok, verdict.problems
    assert verdict.panel == DOCS
    assert verdict.pairs_ok == len(DOCS)
    assert verdict.membership == ap.MEMBERSHIP_RECORD
    report = verdict.as_dict()
    assert report["ok"] is True
    assert report["counts"] == {}
    assert report["panel_size"] == len(DOCS)


def test_a_panel_the_caller_names_is_checked_as_a_set(tmp_path: Path) -> None:
    verdict = ap.preflight(_cycle(tmp_path), _fresh(tmp_path), panel=list(DOCS))

    assert verdict.ok, verdict.problems
    assert verdict.membership == ap.MEMBERSHIP_SET


@pytest.mark.parametrize(
    "drop, prefix",
    [("states", "state_full_"), ("signatures", "signature_")],
)
def test_a_panel_document_without_one_of_its_files_is_named(
    tmp_path: Path, drop: str, prefix: str
) -> None:
    cycle = _cycle(tmp_path)
    (cycle / drop / f"{prefix}doc_x2.json").unlink()

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.MISSING_PAIR]
    assert verdict.problems[0].doc == "doc_x2"
    assert verdict.pairs_ok == 1
    assert not verdict.ok


@pytest.mark.parametrize(
    "folder, prefix",
    [("states", "state_full_"), ("signatures", "signature_")],
)
def test_a_file_the_panel_does_not_name_is_a_stray(
    tmp_path: Path, folder: str, prefix: str
) -> None:
    cycle = _cycle(tmp_path)
    _write_json(cycle / folder / f"{prefix}doc_x9.json", {})

    verdict = ap.preflight(cycle, _fresh(tmp_path), panel=list(DOCS))

    # Three independent witnesses of one fact: the panel does not name it,
    # and the harvest's own count — like the panel size the cycle records —
    # no longer matches what the directory holds.
    assert _kinds(verdict) == [
        ap.STRAY_PAIR,
        ap.HARVEST_COUNT_MISMATCH,
        ap.HARVEST_COUNT_MISMATCH,
    ]
    assert verdict.problems[0].doc == "doc_x9"
    assert _details(verdict)[1:] == ["copied=2 present=3", "panel_size=2 present=3"]


def test_a_panel_document_the_cycle_lacks_is_named_twice(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)

    verdict = ap.preflight(
        cycle, _fresh(tmp_path), panel=["doc_x1", "doc_x2", "doc_x9"]
    )

    assert verdict.counts() == {ap.MISSING_PAIR: 2}
    assert [p.doc for p in verdict.problems] == ["doc_x9", "doc_x9"]


@pytest.mark.parametrize("missing, stale", [(1, 0), (0, 1)])
def test_an_incomplete_harvest_refuses_the_cycle(
    tmp_path: Path, missing: int, stale: int
) -> None:
    cycle = _cycle(tmp_path, copied=len(DOCS) - 1, missing=missing, stale=stale)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert ap.HARVEST_INCOMPLETE in _kinds(verdict)
    assert not verdict.ok


def test_the_harvest_counts_must_match_the_pairs_present(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    _edit(cycle / "pipeline.json", lambda r: r["harvest"].update(copied=3))

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.HARVEST_COUNT_MISMATCH]
    assert _details(verdict) == ["copied=3 present=2"]


def test_the_panel_size_the_cycle_records_must_match_too(tmp_path: Path) -> None:
    verdict = ap.preflight(_cycle(tmp_path, panel_size=3), _fresh(tmp_path))

    assert _kinds(verdict) == [ap.HARVEST_COUNT_MISMATCH]
    assert _details(verdict) == ["panel_size=3 present=2"]


def test_a_cycle_without_its_harvest_record_is_refused(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    (cycle / "pipeline.json").unlink()

    alone = ap.preflight(cycle, _fresh(tmp_path))
    assert _kinds(alone) == [ap.RECORD_MISSING]
    assert alone.problems[0].detail == "pipeline.json"
    assert alone.membership == ap.MEMBERSHIP_NONE

    # A named panel says which documents to check. It is no witness that the
    # pairs were harvested by this run rather than left by an earlier one —
    # the record is, and the cycle is refused until it can be read.
    named = ap.preflight(cycle, _fresh(tmp_path), panel=list(DOCS))
    assert _kinds(named) == [ap.RECORD_MISSING]
    assert not named.ok
    assert named.membership == ap.MEMBERSHIP_SET


def test_a_cycle_without_its_cycle_record_is_refused(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    (cycle / "cycle.json").unlink()

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_MISSING]
    assert verdict.problems[0].detail == "cycle.json"
    assert verdict.membership == ap.MEMBERSHIP_RECORD


@pytest.mark.parametrize("name", ["pipeline.json", "cycle.json"])
def test_a_record_that_is_a_directory_is_named_unreadable(
    tmp_path: Path, name: str
) -> None:
    cycle = _cycle(tmp_path)
    (cycle / name).unlink()
    (cycle / name).mkdir()

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_UNREADABLE]
    assert verdict.problems[0].detail == f"{name}: not a file"


def test_an_empty_harvest_record_compares_nothing_and_is_refused(
    tmp_path: Path,
) -> None:
    cycle = _cycle(tmp_path)
    _edit(cycle / "pipeline.json", lambda r: r.update(harvest={}))

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_MALFORMED] * 3
    assert _details(verdict) == [
        "pipeline.json: no copied count",
        "pipeline.json: no missing count",
        "pipeline.json: no stale count",
    ]
    assert verdict.membership == ap.MEMBERSHIP_NONE


@pytest.mark.parametrize(
    "change, detail",
    [
        (lambda r: r.pop("harvest"), "pipeline.json: no harvest object"),
        (lambda r: r.update(harvest=[]), "pipeline.json: no harvest object"),
        (lambda r: r["harvest"].pop("stale"), "pipeline.json: no stale count"),
        (lambda r: r["harvest"].update(copied="2"), "pipeline.json: no copied count"),
        (
            lambda r: r["harvest"].update(missing=False),
            "pipeline.json: no missing count",
        ),
    ],
)
def test_a_harvest_record_the_contract_would_not_write_is_refused(
    tmp_path: Path, change: Callable[[Dict[str, Any]], None], detail: str
) -> None:
    cycle = _cycle(tmp_path)
    _edit(cycle / "pipeline.json", change)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_MALFORMED]
    assert verdict.problems[0].detail == detail


def test_a_cycle_record_without_a_panel_size_is_refused(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    _edit(cycle / "cycle.json", lambda r: r.pop("panel_size"))

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_MALFORMED]
    assert verdict.problems[0].detail == "cycle.json: no panel_size count"


def test_an_unreadable_harvest_record_is_named_not_guessed(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    (cycle / "pipeline.json").write_text("{not json", encoding="utf-8")

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_UNREADABLE]
    assert verdict.problems[0].detail == "pipeline.json: JSONDecodeError"
    assert verdict.membership == ap.MEMBERSHIP_NONE


def test_an_unreadable_cycle_record_is_named_too(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    (cycle / "cycle.json").write_text("{not json", encoding="utf-8")

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.RECORD_UNREADABLE]
    assert verdict.problems[0].detail == "cycle.json: JSONDecodeError"


@pytest.mark.parametrize(
    "folder, kind",
    [
        ("states", ap.STATES_DIR_MISSING),
        ("signatures", ap.SIGNATURES_DIR_MISSING),
    ],
)
def test_a_missing_input_directory_is_named_first(
    tmp_path: Path, folder: str, kind: str
) -> None:
    cycle = _cycle(tmp_path)
    for path in sorted((cycle / folder).iterdir()):
        path.unlink()
    (cycle / folder).rmdir()

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict)[0] == kind
    assert not verdict.ok


# ---------------------------------------------------------------------------
# 2. Matching readable pairs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", ["{not json", "[1, 2, 3]", '"a string"'])
def test_an_unreadable_or_non_object_state_is_named_not_guessed(
    tmp_path: Path, payload: str
) -> None:
    cycle = _cycle(tmp_path)
    _state_path(cycle, "doc_x1").write_text(payload, encoding="utf-8")

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.UNREADABLE_STATE]
    assert verdict.problems[0].doc == "doc_x1"
    assert verdict.pairs_ok == 1


def test_an_unreadable_signature_is_named_and_never_read(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    _sig_path(cycle, "doc_x2").write_text("", encoding="utf-8")

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.UNREADABLE_SIGNATURE]
    assert verdict.problems[0].doc == "doc_x2"


@pytest.mark.parametrize("damage", ["another document's", "no opaque_id"])
def test_a_signature_whose_opaque_id_is_not_the_documents_is_refused(
    tmp_path: Path, damage: str
) -> None:
    cycle = _cycle(tmp_path)
    other = json.loads(_sig_path(cycle, "doc_x2").read_text(encoding="utf-8"))
    if damage == "no opaque_id":
        other.pop("opaque_id")
    _write_json(_sig_path(cycle, "doc_x1"), other)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert ap.FOREIGN_SIGNATURE in _kinds(verdict)
    assert verdict.problems[0].doc == "doc_x1"
    assert verdict.problems[0].detail == "its opaque_id does not name this document"
    assert not verdict.ok


def test_a_signature_from_another_run_is_refused(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    _edit(
        _sig_path(cycle, "doc_x1"),
        lambda s: s["llm_usage"].update({"cost_usd": 9.99}),
    )

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.PAIR_MISMATCH]
    assert _details(verdict) == ["llm_usage"]


def test_an_act_length_the_signature_records_must_match_the_state(
    tmp_path: Path,
) -> None:
    cycle = _cycle(tmp_path)

    def shorten(sig: Dict[str, Any]) -> None:
        sig["state"]["act1_framing"]["length"] += 1

    _edit(_sig_path(cycle, "doc_x1"), shorten)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.PAIR_MISMATCH]
    assert _details(verdict) == ["act1_framing length"]


@pytest.mark.parametrize("agree", [True, False])
def test_an_act_the_signature_records_as_text_is_compared_as_text(
    tmp_path: Path, agree: bool
) -> None:
    cycle = _cycle(tmp_path)
    text = _state("doc_x1")["act2_narrative"]

    def verbatim(sig: Dict[str, Any]) -> None:
        sig["state"]["act2_narrative"] = text if agree else text + " different"

    _edit(_sig_path(cycle, "doc_x1"), verbatim)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    if agree:
        assert verdict.ok, verdict.problems
    else:
        assert _kinds(verdict) == [ap.PAIR_MISMATCH]
        assert _details(verdict) == ["act2_narrative text"]


def test_an_act_the_state_holds_and_the_signature_omits_is_refused(
    tmp_path: Path,
) -> None:
    cycle = _cycle(tmp_path)
    _edit(_sig_path(cycle, "doc_x1"), lambda s: s["state"].pop("act3_conclusion"))

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.PAIR_MISMATCH]
    assert _details(verdict) == ["act3_conclusion not recorded"]


def test_a_length_without_the_sanitisers_marker_is_not_a_record(
    tmp_path: Path,
) -> None:
    # The sanitiser never writes a length alone. A record of another shape is
    # not the witness the replay compares against, so it is refused by name
    # rather than read as one.
    cycle = _cycle(tmp_path)
    length = len(_state("doc_x1")["act1_framing"])
    _edit(
        _sig_path(cycle, "doc_x1"),
        lambda s: s["state"].update({"act1_framing": {"length": length}}),
    )

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.PAIR_MISMATCH]
    assert _details(verdict) == ["act1_framing not recorded"]


def test_a_signature_written_before_the_usage_was_recorded_still_passes(
    tmp_path: Path,
) -> None:
    # A signature older than #2849 carries no ``llm_usage``. That witness is
    # then absent, which is not a mismatch: the three acts still witness the
    # pair.
    cycle = _cycle(tmp_path)
    _edit(_sig_path(cycle, "doc_x1"), lambda s: s.pop("llm_usage"))

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert verdict.ok, verdict.problems
    assert verdict.pairs_ok == len(DOCS)


@pytest.mark.parametrize("recorded", [0, 5])
def test_an_empty_act_still_compares_as_a_length_of_zero(
    tmp_path: Path, recorded: int
) -> None:
    # A cut phase leaves an empty act, and the sanitiser records it like any
    # other text — so an empty act is compared, never skipped.
    cycle = _cycle(tmp_path)
    _edit(_state_path(cycle, "doc_x1"), lambda s: s.update({"act1_framing": ""}))

    def claim(sig: Dict[str, Any]) -> None:
        sig["state"]["act1_framing"] = {"length": recorded, "stripped": True}

    _edit(_sig_path(cycle, "doc_x1"), claim)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    if recorded == 0:
        assert verdict.ok, verdict.problems
    else:
        assert _kinds(verdict) == [ap.PAIR_MISMATCH]
        assert _details(verdict) == ["act1_framing length"]


def _hold_no_act(container: Dict[str, Any], act: str, how: str) -> None:
    if how == "none":
        container[act] = None
    else:
        container.pop(act)


@pytest.mark.parametrize("how", ["none", "absent"])
def test_a_state_that_holds_no_act_refuses_a_signature_that_records_one(
    tmp_path: Path, how: str
) -> None:
    # Both files are written from one state: a signature that still records
    # an act was not written from the state beside it.
    cycle = _cycle(tmp_path)
    _edit(
        _state_path(cycle, "doc_x1"), lambda s: _hold_no_act(s, "act2_narrative", how)
    )

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.PAIR_MISMATCH]
    assert _details(verdict) == ["act2_narrative recorded, not held"]
    assert verdict.pairs_ok == 1


@pytest.mark.parametrize("how", ["none", "absent"])
def test_a_state_that_holds_no_act_agrees_with_a_signature_that_records_none(
    tmp_path: Path, how: str
) -> None:
    cycle = _cycle(tmp_path)
    _edit(
        _state_path(cycle, "doc_x1"), lambda s: _hold_no_act(s, "act2_narrative", how)
    )
    _edit(
        _sig_path(cycle, "doc_x1"),
        lambda s: _hold_no_act(s["state"], "act2_narrative", how),
    )

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert verdict.ok, verdict.problems


@pytest.mark.parametrize("value", [["two", "words"], {"a": "dict"}, 17, True])
def test_an_act_that_is_not_text_is_refused_whatever_the_signature_says(
    tmp_path: Path, value: Any
) -> None:
    # The sanitiser traverses a value whose type it does not classify intact,
    # so the two files can agree on an act that no replay could read as text.
    cycle = _cycle(tmp_path)
    _edit(_state_path(cycle, "doc_x1"), lambda s: s.update({"act3_conclusion": value}))
    _edit(
        _sig_path(cycle, "doc_x1"),
        lambda s: s["state"].update({"act3_conclusion": value}),
    )

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert _kinds(verdict) == [ap.PAIR_MISMATCH]
    assert _details(verdict) == ["act3_conclusion is not text"]
    assert verdict.pairs_ok == 1


def test_only_the_three_acts_the_replay_reruns_are_compared(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)

    def wrong_other_field(sig: Dict[str, Any]) -> None:
        sig["state"]["narrative_synthesis"] = {"length": 1, "stripped": True}

    _edit(_sig_path(cycle, "doc_x1"), wrong_other_field)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert verdict.ok, verdict.problems


def test_the_length_record_the_preflight_reads_is_the_one_the_sanitiser_writes(
    tmp_path: Path,
) -> None:
    # The length witness is keyed to the sanitiser's output. This pins the
    # key: an act reduced to anything else would turn every real cycle into
    # a refusal that names the wrong cause.
    from argumentation_analysis.evaluation.sanitize_state import sanitize_state

    raw: Dict[str, Any] = {
        "act1_framing": MARK_ACT,
        "act2_narrative": "",
        "act3_conclusion": None,
    }

    assert sanitize_state(dict(raw)) == {
        "act1_framing": {"length": len(MARK_ACT), "stripped": True},
        "act2_narrative": {"length": 0, "stripped": True},
        "act3_conclusion": None,
    }

    cycle = _cycle(tmp_path)
    for doc in DOCS:
        state = json.loads(_state_path(cycle, doc).read_text(encoding="utf-8"))
        signature = json.loads(_sig_path(cycle, doc).read_text(encoding="utf-8"))
        signature["state"] = sanitize_state(state)
        _write_json(_sig_path(cycle, doc), signature)

    verdict = ap.preflight(cycle, _fresh(tmp_path))

    assert verdict.ok, verdict.problems
    assert verdict.pairs_ok == len(DOCS)


# ---------------------------------------------------------------------------
# 3. A destination of its own
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("as_dir", [True, False])
def test_an_existing_destination_collides_even_when_empty(
    tmp_path: Path, as_dir: bool
) -> None:
    cycle = _cycle(tmp_path)
    destination = _fresh(tmp_path)
    if as_dir:
        destination.mkdir()
    else:
        destination.write_text("", encoding="utf-8")

    verdict = ap.preflight(cycle, destination)

    assert _kinds(verdict) == [ap.DESTINATION_EXISTS]


@pytest.mark.parametrize("folder", ["states", "signatures"])
def test_a_destination_inside_an_input_directory_collides(
    tmp_path: Path, folder: str
) -> None:
    cycle = _cycle(tmp_path)

    verdict = ap.preflight(cycle, cycle / folder / "replay_out")

    assert _kinds(verdict) == [ap.DESTINATION_COLLIDES]


def test_the_cycle_directory_itself_is_no_destination(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)

    verdict = ap.preflight(cycle, cycle)

    assert _kinds(verdict) == [ap.DESTINATION_EXISTS, ap.DESTINATION_COLLIDES]


def test_a_fresh_subdirectory_of_the_cycle_is_a_destination_of_its_own(
    tmp_path: Path,
) -> None:
    cycle = _cycle(tmp_path)

    verdict = ap.preflight(cycle, cycle / "act_replay_out")

    assert verdict.ok, verdict.problems


def test_a_destination_git_would_track_is_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "ignored").mkdir(parents=True)
    (repo / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    cycle = _cycle(repo / "ignored" / "cycle")

    refused = ap.preflight(cycle, repo / "tracked_out", repo_root=repo)
    assert _kinds(refused) == [ap.DESTINATION_TRACKED]

    accepted = ap.preflight(cycle, repo / "ignored" / "out", repo_root=repo)
    assert accepted.ok, accepted.problems


# ---------------------------------------------------------------------------
# 4. The instrument's own properties
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("break_it", [None, "signature", "destination"])
def test_no_verdict_writes_anything(tmp_path: Path, break_it: Optional[str]) -> None:
    cycle = _cycle(tmp_path)
    destination = _fresh(tmp_path)
    if break_it == "signature":
        _sig_path(cycle, "doc_x1").unlink()
    if break_it == "destination":
        destination.mkdir()
    before = _snapshot(cycle)

    verdict = ap.preflight(cycle, destination)

    assert _snapshot(cycle) == before
    assert verdict.ok is (break_it is None)
    if break_it is None:
        assert not destination.exists()


def _overwrite_a_state(cycle: Path) -> None:
    _state_path(cycle, "doc_x1").write_text("{}", encoding="utf-8")


def _write_a_nested_file(cycle: Path) -> None:
    deeper = cycle / ap.STATES_DIR / "deeper"
    deeper.mkdir()
    (deeper / "stray.json").write_text("{}", encoding="utf-8")


def _create_an_empty_directory(cycle: Path) -> None:
    (cycle / ap.SIGNATURES_DIR / "empty").mkdir()


def _create_a_directory_at_the_root(cycle: Path) -> None:
    (cycle.parents[1] / "new").mkdir()


@pytest.mark.parametrize(
    "change",
    [
        _overwrite_a_state,
        _write_a_nested_file,
        _create_an_empty_directory,
        _create_a_directory_at_the_root,
    ],
    ids=[
        "an overwritten state",
        "a new nested file",
        "a new empty directory",
        "a new directory at the root",
    ],
)
def test_the_snapshot_sees_every_kind_of_write(
    tmp_path: Path, change: Callable[[Path], None]
) -> None:
    """The instrument's own sensitivity: each write the preflight must not make
    changes what the snapshot returns."""
    cycle = _cycle(tmp_path)
    before = _snapshot(cycle)

    change(cycle)

    assert _snapshot(cycle) != before


def test_the_report_names_witnesses_never_values(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path, docs=DOCS + ("doc_x3",))

    def break_every_witness(sig: Dict[str, Any]) -> None:
        sig["opaque_id"] = "doc_x9"
        sig["llm_usage"]["cost_usd"] = 9.99
        sig["state"]["act1_framing"]["length"] += 1
        sig["state"]["act2_narrative"] = "different text"
        sig["state"].pop("act3_conclusion")

    _edit(_sig_path(cycle, "doc_x1"), break_every_witness)
    _state_path(cycle, "doc_x2").write_text("{not json", encoding="utf-8")

    def break_the_act_types(state: Dict[str, Any]) -> None:
        state["act1_framing"] = [MARK_ACT]
        state["act2_narrative"] = None

    _edit(_state_path(cycle, "doc_x3"), break_the_act_types)

    verdict = ap.preflight(cycle, _fresh(tmp_path))
    text = json.dumps(verdict.as_dict(), ensure_ascii=False)

    assert not verdict.ok
    assert MARK_ACT not in text
    assert MARK_NAME not in text
    assert "An invented source" not in text
    assert set(verdict.counts()) <= {
        ap.FOREIGN_SIGNATURE,
        ap.PAIR_MISMATCH,
        ap.UNREADABLE_STATE,
    }
    assert _details(verdict)[-2:] == [
        "act1_framing is not text",
        "act2_narrative recorded, not held",
    ]


def _cli() -> Path:
    return REPO_ROOT / "scripts" / "panel" / "act_replay_preflight.py"


def _run_cli(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(_cli()), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )


def test_the_cli_prints_one_json_object_and_exits_by_its_verdict(
    tmp_path: Path,
) -> None:
    cycle = _cycle(tmp_path)

    passing = _run_cli("--cycle-dir", str(cycle), "--dest", str(_fresh(tmp_path)))
    assert passing.returncode == 0, passing.stderr
    assert json.loads(passing.stdout)["ok"] is True

    collided = _fresh(tmp_path)
    collided.mkdir()
    failing = _run_cli("--cycle-dir", str(cycle), "--dest", str(collided))
    assert failing.returncode == 1
    report = json.loads(failing.stdout)
    assert report["ok"] is False
    assert report["counts"] == {ap.DESTINATION_EXISTS: 1}


def test_the_cli_refuses_an_empty_panel_rather_than_checking_nothing(
    tmp_path: Path,
) -> None:
    cycle = _cycle(tmp_path)

    run = _run_cli(
        "--cycle-dir", str(cycle), "--dest", str(_fresh(tmp_path)), "--panel", ""
    )

    assert run.returncode == 2
    assert "empty" in run.stderr
    assert run.stdout == ""


def _keyless_child(script: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-c", CHILD % (FORBIDDEN,), str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_keyless_env(),
        timeout=180,
    )


def test_the_preflight_needs_no_key_and_no_model_client(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)

    run = _keyless_child(
        _cli(), "--cycle-dir", str(cycle), "--dest", str(_fresh(tmp_path))
    )

    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["ok"] is True


def test_the_import_guard_fires_on_a_script_that_imports_a_client(
    tmp_path: Path,
) -> None:
    probe = tmp_path / "probe_imports_client.py"
    probe.write_text("import json\nimport openai\n", encoding="utf-8")

    run = _keyless_child(probe)

    assert run.returncode != 0
    assert "forbidden import: openai" in run.stderr
