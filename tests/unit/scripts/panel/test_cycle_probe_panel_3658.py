"""#3658 item 46g-3 (R1220 c) — the judges stage and a tag that is a probe.

A probe replays a named subset and its tag says so (``probe.covered`` /
``probe.left_out`` / ``probe.cycle_documents``). The judges stage used to read
such a tag as an ordinary cycle: with the whole panel it answered "N documents
have no harvested state", which cannot be told apart from a broken harvest, and
with the probe's own subset it graded the pass with nothing saying it was one.

Both halves are measured here, on a tag written by hand (no call, no judge):
the panel that is not the probe's is refused *as a probe*, and the matching one
is graded with its scope in the summary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from scripts.panel import run_cycle

HEAD = {"head": "a" * 40, "branch": "main", "dirty": False}
COVERED = ("doc_t1",)
LEFT_OUT = ("doc_t2",)


class _Credit:
    """Constant readings: this stage pays nothing, so no delta matters."""

    def __call__(self) -> Dict[str, Any]:
        return {"usage": 1.0, "limit": 100.0, "limit_remaining": 99.0}


def _tag(root: Path) -> Path:
    """A probe tag: one pair on disk, and the declaration in ``pipeline.json``."""
    tag = root / "panel_cycles" / "probe1"
    (tag / "states").mkdir(parents=True)
    (tag / "signatures").mkdir()
    for doc in COVERED:
        (tag / "states" / f"state_full_{doc}.json").write_text(
            "{}", encoding="utf-8"
        )
        (tag / "signatures" / f"signature_{doc}.json").write_text(
            "{}", encoding="utf-8"
        )
    # The zero-shot answers live beside the results root, not in the tag: the
    # matching-panel test has to clear the zero-shot gate before the stage it
    # exercises, and a document without one is refused there (rightly).
    zeroshot = root / "zeroshot"
    zeroshot.mkdir(exist_ok=True)
    for doc in COVERED:
        (zeroshot / f"{doc}.json").write_text(
            json.dumps({"answer": "a zero-shot answer stands in here"}), encoding="utf-8"
        )
    (tag / "pipeline.json").write_text(
        json.dumps(
            {
                "rc": 0,
                "head": "a" * 40,
                "head_after": "a" * 40,
                "harvest": {"copied": len(COVERED), "missing": 0, "stale": 0},
                "probe": {
                    "named": len(COVERED),
                    "covered": list(COVERED),
                    "left_out": list(LEFT_OUT),
                    "cycle_documents": len(COVERED) + len(LEFT_OUT),
                },
            }
        ),
        encoding="utf-8",
    )
    return tag


def _config(root: Path, tag: Path, panel: List[str], stage: str) -> run_cycle.Config:
    panel_file = root / "panel.txt"
    panel_file.write_text("\n".join(panel) + "\n", encoding="utf-8")
    zeroshot = root / "zeroshot"
    zeroshot.mkdir(exist_ok=True)
    return run_cycle.Config(
        tag=tag.name,
        panel_file=panel_file,
        zeroshot_dir=zeroshot,
        judges=(run_cycle.Judge(name="j1", model="invented-model"),),
        stage=stage,
        results_root=root,
    )


def _run(root: Path, tag: Path, panel: List[str], stage: str) -> Dict[str, Any]:
    return run_cycle.run_cycle(
        _config(root, tag, panel, stage),
        runner=lambda step: 0,
        credit=_Credit(),
        head=lambda: dict(HEAD),
    )


def test_a_panel_that_is_not_the_probe_is_refused_as_a_probe(tmp_path: Path) -> None:
    """The whole cycle's panel against a one-document probe: refused, and the
    refusal says *probe*, not "unharvested" — a reader must be able to tell a
    declared subset from a broken harvest."""
    tag = _tag(tmp_path)

    summary = _run(tmp_path, tag, list(COVERED) + list(LEFT_OUT), "judges")

    assert summary["exit_code"] == run_cycle.EXIT_STOPPED
    assert summary["stopped"].startswith("the tag declares itself a probe on 1 of 2")
    assert "doc_t1" in summary["stopped"]


def test_the_matching_panel_is_graded_with_the_probes_scope(tmp_path: Path) -> None:
    """The probe's own subset is what the tag holds, so the stage proceeds —
    and the summary carries the scope, so nobody reads that pass as the
    cycle's panel."""
    tag = _tag(tmp_path)

    summary = _run(tmp_path, tag, list(COVERED), "consensus")

    assert summary["probe"] == {
        "named": 1,
        "covered": ["doc_t1"],
        "left_out": ["doc_t2"],
        "cycle_documents": 2,
    }
