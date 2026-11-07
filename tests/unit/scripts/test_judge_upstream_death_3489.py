"""#3489 — the arm's health also reads the signature: a run that DIED
upstream (``outcome.status == "failed"``) is a broken arm toward refusal,
whatever the state dump says.

The c4 run: the provider key died mid-run; most documents ended with
``outcome.status = "failed"`` and empty acts, but NO
``restitution_acts_degraded`` — the run died before any render attempt, so
the report never existed. The conjunctive rule (#3458) read those documents
as "no acts by design", the count stayed under the refusal threshold, and
the judge graded broken documents as clean baseline wins.

The decision the issue asks to state, not slip in silently (#3468 renders a
cut run's recorded material): ``partial_timeout`` / ``partial_error`` are
LEGIBLE partials — the cut is named and the recorded material rides to the
judge — so they do NOT count toward refusal. The panel sweep's own
vocabulary (``ok`` / ``partial``) is equally out: ``partial`` there means a
budget-cut run whose material #3468 renders. ``failed`` is the death record;
the death record is the only new signal.

No network, no dataset, no key: the endpoint resolver and the document
loader are replaced, every call goes through the injected ``judge_call``.
**Zero paid call, zero corpus read.**
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset import judge_panel as jp  # noqa: E402

ZEROSHOT_TEXT = (
    "Le document defend la these beta en s'appuyant sur un exemple date, et "
    "ne discute jamais la semantique preferee."
)
DOCUMENT_TEXT = (
    "Discours synthetique de test. La these centrale affirme que la mesure "
    "de 1998 a reduit le deficit de moitie, et le texte appuie cette "
    "affirmation sur trois chiffres dates."
)

PANEL = ["aaaa1111", "bbbb2222", "cccc3333"]
SEED = 3375

ACTS_RENDERED = {
    "act1_framing": "Acte I rendu sur ce document.",
    "act2_narrative": "Acte II rendu sur ce document.",
    "act3_conclusion": "Acte III rendu sur ce document.",
}
DEGRADED_REPORT = {"act1_framing": {"status": "degraded", "detail": "writer gap"}}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _state_payload(empty_acts=(), report=None, drop_acts=()):
    """A state dump: acts rendered unless emptied, the report optional.

    ``drop_acts`` removes the keys entirely — the shape of a state written
    before the act phases ever ran, which is what an upstream death leaves.
    """
    st = dict(ACTS_RENDERED)
    for key in empty_acts:
        st[key] = ""
    for key in drop_acts:
        st.pop(key, None)
    if report is not None:
        st["restitution_acts_degraded"] = report
    return {"state": st}


def _c4_state():
    """The c4 death shape: no act key ever written, no report either."""
    return {"drop_acts": ACTS_RENDERED.keys()}


def _failed_signature(reason="provider refused the call mid-run"):
    """The c4 signature: the run's own outcome says the run died."""
    return {"outcome": {"status": "failed", "reason": reason}}


def make_world(tmp_path: Path, states=None, signatures=None):
    """A tiny stand-in campaign: both arms, per-document state shapes.

    ``states`` maps doc_id → ``_state_payload`` kwargs; ``signatures`` maps
    doc_id → fields merged into that document's signature (the writer's
    ``outcome`` / ``document_classification`` ride here). A doc absent from
    either map gets the healthy default.
    """
    shapes = states or {}
    sig_overrides = signatures or {}
    states_dir = tmp_path / "states"
    signatures_dir = tmp_path / "signatures"
    zeroshots = tmp_path / "zeroshots"
    for doc_id in PANEL:
        _write_json(
            states_dir / f"state_full_{doc_id}.json",
            _state_payload(**shapes.get(doc_id, {})),
        )
        _write_json(
            signatures_dir / f"signature_{doc_id}.json",
            {
                "opaque_id": doc_id,
                "llm_usage": {
                    "phase_1": {"prompt_tokens": 1200, "completion_tokens": 300}
                },
                **sig_overrides.get(doc_id, {}),
            },
        )
        _write_json(
            zeroshots / f"{doc_id}.json",
            {
                "opaque_id": doc_id,
                "provenance": {"model": "gpt-5.6-luna", "git_head": "deadbeef"},
                "usage": {"prompt_tokens": 900, "completion_tokens": 250},
                "answer": ZEROSHOT_TEXT,
            },
        )
    panel_file = tmp_path / "panel.txt"
    panel_file.write_text("\n".join(PANEL) + "\n", encoding="utf-8")
    return {
        "states": states_dir,
        "signatures": signatures_dir,
        "zeroshots": zeroshots,
        "out": tmp_path / "out",
        "panel_file": panel_file,
    }


class FakeJudge:
    """Counts its calls and answers from a fixed table — never the network."""

    def __init__(self):
        self.calls = []

    async def __call__(self, endpoint, prompt, timeout=600):
        self.calls.append(prompt)
        return {
            "status_code": 200,
            "answer": json.dumps(
                {
                    "identification": "1",
                    "state": "PIPELINE_SUPPLIES",
                    "items": [],
                    "style_notes": [],
                    "conclusion": "Le surplus est formel.",
                },
                ensure_ascii=False,
            ),
            "prompt_tokens": 2000,
            "completion_tokens": 400,
            "usage": {},
        }


def _argv(world, extra=()):
    return [
        "--judge-model",
        "claude-sonnet-5-5",
        "--panel-file",
        str(world["panel_file"]),
        "--seed",
        str(SEED),
        "--states-dir",
        str(world["states"]),
        "--signatures-dir",
        str(world["signatures"]),
        "--zeroshot-dir",
        str(world["zeroshots"]),
        "--out-dir",
        str(world["out"]),
        *extra,
    ]


def _run(world, judge, extra=()):
    return asyncio.run(jp.run(_argv(world, extra), judge_call=judge))


def _record(world, doc_id):
    return json.loads((world["out"] / f"{doc_id}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_named_route(monkeypatch):
    monkeypatch.setattr(
        jp,
        "resolve_judge_endpoint",
        lambda model: {
            "api_key": "not-a-key",
            "base_url": "https://example.invalid/v1",
            "model_id": model,
            "family": "anthropic",
            "host": "example.invalid",
            "route": "test",
        },
    )


@pytest.fixture(autouse=True)
def _synthetic_documents(monkeypatch):
    monkeypatch.setattr(
        jp,
        "load_document_texts",
        lambda panel: {doc_id: DOCUMENT_TEXT for doc_id in panel},
    )


# ---------------------------------------------------------------------------
# The rule itself — pure, no run
# ---------------------------------------------------------------------------


class TestTheUpstreamDeathRule:
    def test_a_failed_status_is_a_broken_arm_with_no_report(self):
        """The c4 blindness, closed: the run's own death record flags the
        arm even though the state carries no degradation report (the run
        died before any render attempt — the report never existed)."""
        health = jp.arm_health(_state_payload(**_c4_state()), _failed_signature())
        assert health["pipeline_degraded"] is True

    def test_a_failed_status_flags_whatever_the_acts_say(self):
        """The signature is the record: a run that says failed is a broken
        arm even if some acts rendered before the death."""
        health = jp.arm_health(_state_payload(), _failed_signature())
        assert health["pipeline_degraded"] is True

    def test_a_non_argumentative_classification_stays_by_design(self):
        health = jp.arm_health(
            _state_payload(**_c4_state()),
            {
                "outcome": {"status": "failed"},
                "document_classification": "non_argumentative",
            },
        )
        assert health["pipeline_degraded"] is False

    def test_a_partial_timeout_is_a_legible_partial_not_a_death(self):
        """#3468 renders a cut run's recorded material and names the cut: a
        partial timeout is judged on what the run did record."""
        health = jp.arm_health(
            _state_payload(**_c4_state()),
            {"outcome": {"status": "partial_timeout", "reason": "timeout after 180s"}},
        )
        assert health["pipeline_degraded"] is False

    def test_a_partial_error_is_a_legible_partial_not_a_death(self):
        health = jp.arm_health(
            _state_payload(**_c4_state()),
            {"outcome": {"status": "partial_error", "reason": "phase refused"}},
        )
        assert health["pipeline_degraded"] is False

    def test_the_sweep_partial_vocabulary_is_not_a_death_either(self):
        """The panel sweep writes ok/partial — ``partial`` there is a budget
        cut whose material #3468 renders, never an upstream death."""
        health = jp.arm_health(
            _state_payload(**_c4_state()),
            {"outcome": {"status": "partial", "reason": "budget cut with material"}},
        )
        assert health["pipeline_degraded"] is False

    def test_without_a_signature_the_rule_stays_conjunctive(self):
        """The door closes only when the signature is handed over: a caller
        reading the state alone keeps the #3458 behaviour exactly."""
        health = jp.arm_health(_state_payload(**_c4_state()))
        assert health["pipeline_degraded"] is False

    def test_the_health_names_the_upstream_death(self):
        dead = jp.arm_health(_state_payload(**_c4_state()), _failed_signature())
        alive = jp.arm_health(
            _state_payload(**_c4_state()),
            {"outcome": {"status": "partial_timeout"}},
        )
        assert dead["upstream_failed"] is True
        assert alive["upstream_failed"] is False


# ---------------------------------------------------------------------------
# The real c4 shape is refused before the first paid call
# ---------------------------------------------------------------------------


class TestTheRealC4ShapeIsRefused:
    def _c4_world(self, tmp_path, dead=("bbbb2222", "cccc3333")):
        return make_world(
            tmp_path,
            states={doc_id: _c4_state() for doc_id in dead},
            signatures={doc_id: _failed_signature() for doc_id in dead},
        )

    def test_two_failed_signatures_refuse_before_the_first_paid_call(
        self, tmp_path, capsys
    ):
        world = self._c4_world(tmp_path)
        judge = FakeJudge()
        rc = _run(world, judge)
        out = capsys.readouterr().out
        assert rc == 3, "the refusal is a distinct non-zero exit, not a WARN"
        assert "`bbbb2222`" in out and "`cccc3333`" in out, "the opaque ids are named"
        assert "before the first paid call" in out

    def test_the_refusal_names_the_signature_status(self, tmp_path, capsys):
        """The refusal message names the status alongside the acts/report
        reason: a reader must tell an upstream death from a broken render."""
        world = self._c4_world(tmp_path)
        _run(world, FakeJudge())
        out = capsys.readouterr().out
        assert "failed" in out
        assert "upstream" in out

    def test_the_fake_judge_is_never_invoked_on_the_refusal(self, tmp_path):
        world = self._c4_world(tmp_path)
        judge = FakeJudge()
        _run(world, judge)
        assert judge.calls == [], "the refusal happens BEFORE any judge call"

    def test_the_refusal_writes_no_table(self, tmp_path):
        world = self._c4_world(tmp_path)
        _run(world, FakeJudge())
        assert not (world["out"] / "TABLE.md").exists()
        assert not (world["out"] / "bbbb2222.json").exists()


# ---------------------------------------------------------------------------
# Below the threshold: judged, and the record names the death
# ---------------------------------------------------------------------------


class TestOneFailedDocumentIsJudgedAndFlagged:
    def test_the_pass_runs_and_the_record_names_the_death(self, tmp_path):
        world = make_world(
            tmp_path,
            states={"bbbb2222": _c4_state()},
            signatures={"bbbb2222": _failed_signature()},
        )
        judge = FakeJudge()
        assert _run(world, judge) == 0
        assert len(judge.calls) == len(PANEL), "one dead doc does not stop the pass"
        record = _record(world, "bbbb2222")
        assert record["pipeline_degraded"] is True
        assert record["pipeline_upstream_failed"] is True
        assert _record(world, "aaaa1111")["pipeline_degraded"] is False


# ---------------------------------------------------------------------------
# The refusal tells the two reasons apart
# ---------------------------------------------------------------------------


class TestTheRefusalTellsTheTwoReasonsApart:
    def test_a_mixed_panel_names_both_reasons(self, tmp_path, capsys):
        """One broken render (#3458's shape) and one upstream death (#3489's
        shape) in the same panel: each id carries its own reason."""
        world = make_world(
            tmp_path,
            states={
                "bbbb2222": {
                    "empty_acts": ("act1_framing",),
                    "report": DEGRADED_REPORT,
                },
                "cccc3333": _c4_state(),
            },
            signatures={"cccc3333": _failed_signature()},
        )
        rc = _run(world, FakeJudge())
        out = capsys.readouterr().out
        assert rc == 3
        assert "an empty act AND a non-empty restitution_acts_degraded" in out
        assert "signature status: failed" in out


# ---------------------------------------------------------------------------
# The override still applies — explicit, and the records keep the flag
# ---------------------------------------------------------------------------


class TestTheOverrideStillApplies:
    def test_allow_degraded_arm_judges_the_dead_ones_anyway(self, tmp_path, capsys):
        world = make_world(
            tmp_path,
            states={"bbbb2222": _c4_state(), "cccc3333": _c4_state()},
            signatures={
                "bbbb2222": _failed_signature(),
                "cccc3333": _failed_signature(),
            },
        )
        judge = FakeJudge()
        rc = _run(world, judge, extra=["--allow-degraded-arm"])
        out = capsys.readouterr().out
        assert rc == 0
        assert len(judge.calls) == len(PANEL)
        assert "--allow-degraded-arm" in out, "the override's use is printed"
        for doc_id in ("bbbb2222", "cccc3333"):
            record = _record(world, doc_id)
            assert record["pipeline_degraded"] is True
            assert record["pipeline_upstream_failed"] is True


# ---------------------------------------------------------------------------
# The consensus carries the death with the row
# ---------------------------------------------------------------------------


class TestTheConsensusCarriesTheDeath:
    def _pass(self, doc="d1", upstream=None):
        row = {
            "opaque_id": doc,
            "positions": {"pipeline": 1, "zeroshot": 2},
            "identification_ok": True,
            "state": "PIPELINE_SUPPLIES",
            "reported_state": "PIPELINE_SUPPLIES",
            "kept": [],
            "dropped": [],
            "costs": {"pipeline": 0.01, "zeroshot": 0.001},
            "judge_cost": 0.1,
            "pipeline_degraded": upstream is not None,
            "pipeline_empty_acts": ["act1_framing"] if upstream is not None else [],
        }
        if upstream is not None:
            row["pipeline_upstream_failed"] = upstream
        return row

    def test_the_consensus_row_carries_the_death_of_its_passes(self):
        row = jp.consensus_row(
            [self._pass(upstream=True) for _ in range(3)],
            ["p1", "p2", "p3"],
        )
        assert row["pipeline_degraded"] is True
        assert row["pipeline_upstream_failed"] is True

    def test_a_consensus_of_clean_passes_stays_clean(self):
        row = jp.consensus_row([self._pass() for _ in range(3)], ["p1", "p2", "p3"])
        assert row["pipeline_degraded"] is False
        assert row["pipeline_upstream_failed"] is False
