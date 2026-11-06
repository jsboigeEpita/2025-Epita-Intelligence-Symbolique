"""#3458 — the judge reads the pipeline arm's health itself, and refuses a
systemically broken arm BEFORE the first paid call.

The dispatch's DoD, one witness per clause:

- degraded = an empty act key (``act1_framing`` / ``act2_narrative`` /
  ``act3_conclusion``) AND a non-empty ``restitution_acts_degraded`` — never
  either alone: a document with no acts by design carries neither, and the
  c2 cycle carries the report on documents whose acts rendered;
- the health rides in the per-document record, the verdict table and the
  consensus, so no reader mistakes a broken render for a pipeline loss/win;
- beyond a NAMED threshold (calibration: c2 = 1 doc passes, c3 = 9 refuses;
  threshold 2/10) the run REFUSES — non-zero exit, opaque ids, reason —
  before the first paid call, which here means the fake judge is never
  invoked;
- an explicit override may exist, and its use is printed.

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

PIPELINE_TEXT = (
    "Acte I — cadrage. Le graphe rejette la these alpha dans la semantique "
    "stable et l'accepte dans la semantique preferee ; aucun argument ne "
    "survit aux deux."
)
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

# The three act keys the health rule reads — all rendered on a healthy arm.
ACTS_RENDERED = {
    "act1_framing": "Acte I rendu sur ce document.",
    "act2_narrative": "Acte II rendu sur ce document.",
    "act3_conclusion": "Acte III rendu sur ce document.",
}
# What a mid-render break leaves in the state: the report names the act(s)
# that degraded. Non-empty is what the rule reads — the shape inside is the
# writer's, not the judge's.
DEGRADED_REPORT = {"act1_framing": {"status": "degraded", "detail": "writer gap"}}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _state_payload(empty_acts=(), report=None, drop_acts=()):
    """A state dump: acts rendered unless emptied, the report optional.

    ``drop_acts`` removes the keys entirely — the shape of a state written
    before the act phases ever ran (a document with no acts by design).
    """
    st = dict(ACTS_RENDERED)
    for key in empty_acts:
        st[key] = ""
    for key in drop_acts:
        st.pop(key, None)
    if report is not None:
        st["restitution_acts_degraded"] = report
    return {"state": st}


def make_world(tmp_path: Path, states=None):
    """A tiny stand-in campaign: both arms, per-document state shapes.

    ``states`` maps doc_id → the kwargs of ``_state_payload``; a doc absent
    from the map gets the healthy default (all acts rendered, no report).
    """
    shapes = states or {}
    states_dir = tmp_path / "states"
    signatures = tmp_path / "signatures"
    zeroshots = tmp_path / "zeroshots"
    for doc_id in PANEL:
        _write_json(
            states_dir / f"state_full_{doc_id}.json",
            _state_payload(**shapes.get(doc_id, {})),
        )
        _write_json(
            signatures / f"signature_{doc_id}.json",
            {
                "opaque_id": doc_id,
                "llm_usage": {
                    "phase_1": {"prompt_tokens": 1200, "completion_tokens": 300}
                },
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
        "signatures": signatures,
        "zeroshots": zeroshots,
        "out": tmp_path / "out",
        "panel_file": panel_file,
    }


def _answer(state="PIPELINE_SUPPLIES", items=None):
    return json.dumps(
        {
            "identification": "1",
            "state": state,
            "items": items or [],
            "style_notes": [],
            "conclusion": "Le surplus est formel.",
        },
        ensure_ascii=False,
    )


class FakeJudge:
    """Counts its calls and answers from a fixed table — never the network."""

    def __init__(self, answer=None):
        self.calls = []
        self._answer = answer or (lambda doc, prompt: _answer())

    async def __call__(self, endpoint, prompt, timeout=600):
        self.calls.append(prompt)
        return {
            "status_code": 200,
            "answer": self._answer(None, prompt),
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


class TestTheHealthRule:
    def test_an_empty_act_plus_a_report_is_degraded(self):
        health = jp.arm_health(
            _state_payload(empty_acts=("act1_framing",), report=DEGRADED_REPORT)
        )
        assert health["pipeline_degraded"] is True
        assert health["empty_acts"] == ["act1_framing"]

    def test_a_report_alone_is_not_the_signal(self):
        """Anti-pendulum: the c2 cycle carries ``restitution_acts_degraded``
        on documents whose acts RENDERED — that alone must not flag them."""
        health = jp.arm_health(_state_payload(report=DEGRADED_REPORT))
        assert health["pipeline_degraded"] is False
        assert health["empty_acts"] == []

    def test_an_empty_act_alone_is_not_the_signal(self):
        """A document with no acts by design carries neither half of the
        rule: empty acts, yes — but no degradation report either."""
        health = jp.arm_health(_state_payload(empty_acts=("act2_narrative",)))
        assert health["pipeline_degraded"] is False

    def test_absent_act_keys_read_as_empty_but_stay_healthy_without_a_report(self):
        health = jp.arm_health(_state_payload(drop_acts=ACTS_RENDERED.keys()))
        assert health["empty_acts"] == [
            "act1_framing",
            "act2_narrative",
            "act3_conclusion",
        ]
        assert health["pipeline_degraded"] is False

    def test_a_whitespace_act_counts_as_empty(self):
        health = jp.arm_health(
            _state_payload(empty_acts=("act3_conclusion",), report=DEGRADED_REPORT)
        )
        health_ws = jp.arm_health(
            {
                "state": {
                    **ACTS_RENDERED,
                    "act3_conclusion": "   ",
                    "restitution_acts_degraded": DEGRADED_REPORT,
                }
            }
        )
        assert health_ws["pipeline_degraded"] is True
        assert health_ws["empty_acts"] == health["empty_acts"]

    def test_the_state_is_unwrapped_like_the_fiche_does(self):
        inner = _state_payload(empty_acts=("act1_framing",), report=DEGRADED_REPORT)[
            "state"
        ]
        assert jp.arm_health({"state": inner}) == jp.arm_health(inner)

    def test_the_threshold_is_the_calibrated_two_of_ten(self):
        """c2 = 1 doc passes, c3 = 9 refuses — the boundary is 2, and it is
        a named constant, never a bare literal at the call site."""
        assert jp.DEGRADED_ARM_REFUSAL_THRESHOLD == 2


# ---------------------------------------------------------------------------
# A pass judges the arm it can read — c2: one degraded document
# ---------------------------------------------------------------------------


class TestOneDegradedDocumentIsJudgedAndFlagged:
    def test_the_pass_runs_and_the_record_carries_the_flag(self, tmp_path):
        world = make_world(
            tmp_path,
            states={
                "bbbb2222": {
                    "empty_acts": ("act1_framing",),
                    "report": DEGRADED_REPORT,
                }
            },
        )
        judge = FakeJudge()
        assert _run(world, judge) == 0
        assert len(judge.calls) == len(PANEL), "one degraded doc does not stop the pass"
        degraded = _record(world, "bbbb2222")
        assert degraded["pipeline_degraded"] is True
        assert degraded["pipeline_empty_acts"] == ["act1_framing"]
        for healthy in ("aaaa1111", "cccc3333"):
            assert _record(world, healthy)["pipeline_degraded"] is False

    def test_the_table_carries_the_flag_on_the_row_and_in_the_count(self, tmp_path):
        world = make_world(
            tmp_path,
            states={
                "bbbb2222": {
                    "empty_acts": ("act1_framing",),
                    "report": DEGRADED_REPORT,
                }
            },
        )
        _run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "**bras pipeline dégradé**" in table
        assert "`bbbb2222`" in table
        assert "jamais lus comme une victoire ou une défaite du pipeline" in table

    def test_a_healthy_panel_carries_no_flag_anywhere(self, tmp_path):
        world = make_world(tmp_path)
        judge = FakeJudge()
        assert _run(world, judge) == 0
        for doc_id in PANEL:
            assert _record(world, doc_id)["pipeline_degraded"] is False
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "dégradé" not in table

    def test_a_report_on_documents_whose_acts_rendered_flags_nothing(self, tmp_path):
        """End-to-end anti-pendulum: the c2 shape — the report rides on
        every document, the acts rendered on every document — passes clean."""
        world = make_world(
            tmp_path,
            states={doc_id: {"report": DEGRADED_REPORT} for doc_id in PANEL},
        )
        judge = FakeJudge()
        assert _run(world, judge) == 0
        assert len(judge.calls) == len(PANEL)
        for doc_id in PANEL:
            assert _record(world, doc_id)["pipeline_degraded"] is False

    def test_a_document_without_acts_by_design_is_not_degraded(self, tmp_path):
        world = make_world(
            tmp_path,
            states={"cccc3333": {"drop_acts": ACTS_RENDERED.keys()}},
        )
        assert _run(world, FakeJudge()) == 0
        assert _record(world, "cccc3333")["pipeline_degraded"] is False


# ---------------------------------------------------------------------------
# A systemically broken arm is refused — c3: the boundary is 2
# ---------------------------------------------------------------------------


class TestASystemicallyBrokenArmIsRefused:
    def test_two_degraded_documents_refuse_before_the_first_paid_call(
        self, tmp_path, capsys
    ):
        world = make_world(
            tmp_path,
            states={
                "bbbb2222": {
                    "empty_acts": ("act1_framing",),
                    "report": DEGRADED_REPORT,
                },
                "cccc3333": {
                    "empty_acts": ("act1_framing",),
                    "report": DEGRADED_REPORT,
                },
            },
        )
        judge = FakeJudge()
        rc = _run(world, judge)
        out = capsys.readouterr().out
        assert rc == 3, "the refusal is a distinct non-zero exit, not a WARN"
        assert "`bbbb2222`" in out and "`cccc3333`" in out, "the opaque ids are named"
        assert "before the first paid call" in out

    def test_the_fake_judge_is_never_invoked_on_the_refusal(self, tmp_path):
        degraded = {
            "empty_acts": ("act1_framing",),
            "report": DEGRADED_REPORT,
        }
        world = make_world(
            tmp_path, states={"bbbb2222": degraded, "cccc3333": degraded}
        )
        judge = FakeJudge()
        _run(world, judge)
        assert judge.calls == [], "the refusal happens BEFORE any judge call"

    def test_the_refusal_writes_no_table(self, tmp_path):
        degraded = {
            "empty_acts": ("act1_framing",),
            "report": DEGRADED_REPORT,
        }
        world = make_world(
            tmp_path, states={"bbbb2222": degraded, "cccc3333": degraded}
        )
        _run(world, FakeJudge())
        assert not (world["out"] / "TABLE.md").exists()
        assert not (world["out"] / "bbbb2222.json").exists()


# ---------------------------------------------------------------------------
# The override — explicit, and its use is printed
# ---------------------------------------------------------------------------


class TestTheOverrideIsExplicitAndPrinted:
    def test_the_override_judges_anyway_and_says_so(self, tmp_path, capsys):
        degraded = {
            "empty_acts": ("act1_framing",),
            "report": DEGRADED_REPORT,
        }
        world = make_world(
            tmp_path, states={"bbbb2222": degraded, "cccc3333": degraded}
        )
        judge = FakeJudge()
        rc = _run(world, judge, extra=["--allow-degraded-arm"])
        out = capsys.readouterr().out
        assert rc == 0
        assert len(judge.calls) == len(PANEL)
        assert "--allow-degraded-arm" in out, "the override's use is printed"
        assert _record(world, "bbbb2222")["pipeline_degraded"] is True
        assert _record(world, "cccc3333")["pipeline_degraded"] is True

    def test_the_override_rides_in_the_recorded_command(self, tmp_path):
        degraded = {
            "empty_acts": ("act1_framing",),
            "report": DEGRADED_REPORT,
        }
        world = make_world(
            tmp_path, states={"bbbb2222": degraded, "cccc3333": degraded}
        )
        _run(world, FakeJudge(), extra=["--allow-degraded-arm"])
        meta = json.loads((world["out"] / "META.json").read_text(encoding="utf-8"))
        assert "--allow-degraded-arm" in meta["command"]


# ---------------------------------------------------------------------------
# The consensus keeps the flag
# ---------------------------------------------------------------------------


class TestTheConsensusKeepsTheFlag:
    def _pass(self, doc="d1", degraded=None):
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
        }
        if degraded is not None:
            row["pipeline_degraded"] = degraded
            row["pipeline_empty_acts"] = ["act1_framing"] if degraded else []
        return row

    def test_the_consensus_row_carries_the_flag_of_its_passes(self):
        row = jp.consensus_row(
            [
                self._pass(degraded=True),
                self._pass(degraded=True),
                self._pass(degraded=True),
            ],
            ["p1", "p2", "p3"],
        )
        assert row["pipeline_degraded"] is True
        assert row["pipeline_empty_acts"] == ["act1_framing"]

    def test_a_consensus_of_clean_passes_stays_clean(self):
        row = jp.consensus_row(
            [self._pass(), self._pass(), self._pass()], ["p1", "p2", "p3"]
        )
        assert row["pipeline_degraded"] is False

    def test_the_consensus_table_line_is_flagged(self):
        rows = [self._pass(degraded=True)]
        table = jp.render_table(
            rows,
            {
                "judge_model": "claude-sonnet-5-5",
                "judge_family": "anthropic",
                "pipeline_model": "gpt-5.6-luna",
                "pipeline_family": "openai",
                "seed": SEED,
                "judge_temperature": None,
                "command": "cmd",
            },
        )
        assert "**bras pipeline dégradé**" in table
