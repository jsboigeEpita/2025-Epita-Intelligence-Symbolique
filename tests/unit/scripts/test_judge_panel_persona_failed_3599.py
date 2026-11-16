"""#3599 — a persona read that failed upstream is named on the arm's row.

At c15 the strategist read was a ``parse_error`` on four of the nine
argumentative documents: those four renders were written WITHOUT the
strategist's input (Act I's players, Act III's resting player and blind
spot), and both families' ``TABLE.md`` scored those arms healthy — no row
carried « bras pipeline dégradé » and the summary named none of them.

The witness, one per clause of the issue:

- ``arm_health`` NAMES the failed persona read (``persona_failed``) — on
  ``main`` it names nothing, because the rule only knew an empty act AND a
  degradation report, or a dead signature;
- the row shows it on its OWN cell, and the table summary counts and names
  the documents;
- it is NOT a refusal: ``DEGRADED_ARM_REFUSAL_THRESHOLD`` is unchanged, the
  pass runs, the judge is called, and the table states that a change on such
  a document is read with its failed input;
- the writer keeps ``degraded`` / ``degraded_reason`` when the payload sets
  them (conditionally, like #3597's ``attempts``/``parse_failure``), and
  writes NO key when the payload does not.

No network, no dataset, no key: the endpoint resolver and the document
loader are replaced, every call goes through the injected ``judge_call``.
**Zero paid call, zero corpus read.** Synthetic values only.
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
from argumentation_analysis.orchestration import state_writers as sw  # noqa: E402

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

# A persona read that RAN and FAILED: the strategist's reply was malformed
# twice, so the state carries the discriminated status. The other personas
# read fine, and the coverage review never ran on this document.
STRATEGIST_FAILED = {
    "players": [],
    "options": [],
    "preferences": {},
    "blind_spot": "",
    "reading": "",
    "game": {},
    "status": "parse_error",
    "basis": "model_knowledge",
    "attempts": 2,
    "parse_failure": {"message": "Expecting ':' delimiter", "position": 17},
}
HISTORIAN_OK = {
    "situation": "Une situation synthetique.",
    "blind_spot": "",
    "items": [],
    "status": "ok",
    "basis": "model_knowledge",
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _state_payload(persona=None):
    """A state dump: the three acts rendered, plus an optional persona read."""
    st = dict(ACTS_RENDERED)
    if persona is not None:
        st.update(persona)
    return {"state": st}


def make_world(tmp_path: Path, failed_docs=("bbbb2222",)):
    """A tiny stand-in campaign: one document whose strategist read failed."""
    states_dir = tmp_path / "states"
    signatures = tmp_path / "signatures"
    zeroshots = tmp_path / "zeroshots"
    for doc_id in PANEL:
        persona = {"historical_context": HISTORIAN_OK}
        if doc_id in failed_docs:
            persona["strategic_read"] = STRATEGIST_FAILED
        _write_json(
            states_dir / f"state_full_{doc_id}.json",
            _state_payload(persona),
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
# The rule — pure, no run
# ---------------------------------------------------------------------------


class TestTheRuleNamesTheFailedPersona:
    def test_a_failed_persona_read_is_named(self):
        health = jp.arm_health(
            _state_payload(
                {
                    "strategic_read": STRATEGIST_FAILED,
                    "historical_context": HISTORIAN_OK,
                }
            )
        )
        assert health["persona_failed"] == ["strategist"]

    def test_a_rendered_arm_with_a_failed_read_is_still_not_a_degraded_arm(self):
        """Ask 2 — NOT a refusal: the threshold is unchanged, and the flag
        lives on its own signal, never inside ``pipeline_degraded``."""
        health = jp.arm_health(_state_payload({"strategic_read": STRATEGIST_FAILED}))
        assert health["pipeline_degraded"] is False
        assert health["persona_failed"] == ["strategist"]

    def test_the_threshold_is_unchanged(self):
        assert jp.DEGRADED_ARM_REFUSAL_THRESHOLD == 2

    def test_a_successful_read_names_nothing(self):
        health = jp.arm_health(
            _state_payload(
                {
                    "strategic_read": dict(STRATEGIST_FAILED, status="ok"),
                    "historical_context": HISTORIAN_OK,
                }
            )
        )
        assert health["persona_failed"] == []

    def test_an_honest_empty_is_not_a_failure(self):
        """``no_llm`` is a document with no LLM read by design — never a
        failure, and never named."""
        health = jp.arm_health(
            _state_payload(
                {
                    "strategic_read": {"status": "no_llm", "players": []},
                    "historical_context": {"status": "no_llm", "items": []},
                }
            )
        )
        assert health["persona_failed"] == []

    def test_a_failed_historian_is_named_too(self):
        health = jp.arm_health(
            _state_payload({"historical_context": {"status": "llm_error"}})
        )
        assert health["persona_failed"] == ["historian"]

    def test_two_failed_reads_are_both_named(self):
        health = jp.arm_health(
            _state_payload(
                {
                    "strategic_read": STRATEGIST_FAILED,
                    "historical_context": {"status": "llm_error"},
                }
            )
        )
        assert health["persona_failed"] == ["strategist", "historian"]

    def test_a_failed_first_reading_is_named(self):
        """The census: the first reading records a status and has the same
        failed vocabulary — it is read by the check, not only the two named
        personas."""
        health = jp.arm_health(
            _state_payload({"defining_moves": {"status": "parse_error", "moves": []}})
        )
        assert health["persona_failed"] == ["first_reading"]

    def test_a_failed_coverage_review_is_named(self):
        health = jp.arm_health(
            _state_payload({"coverage_review": {"status": "llm_error"}})
        )
        assert health["persona_failed"] == ["coverage_review"]

    def test_cross_passage_statuses_are_not_persona_failures(self):
        """Census, second half: ``cross_passage_consistency`` persists a
        status but its vocabulary has no failed PERSONA read — ``undecided``
        is a silent reasoner, ``unreachable`` a check not reached. Not read,
        and never named."""
        for status in ("checked", "inconsistent", "undecided", "unreachable"):
            health = jp.arm_health(
                _state_payload({"cross_passage_consistency": {"status": status}})
            )
            assert health["persona_failed"] == []

    def test_the_state_is_unwrapped_like_the_fiche_does(self):
        inner = _state_payload({"strategic_read": STRATEGIST_FAILED})["state"]
        assert jp.arm_health({"state": inner}) == jp.arm_health(inner)

    def test_a_missing_read_names_nothing(self):
        health = jp.arm_health(_state_payload())
        assert health["persona_failed"] == []


# ---------------------------------------------------------------------------
# The row and the summary
# ---------------------------------------------------------------------------


class TestTheRowAndTheSummary:
    def test_the_row_carries_the_flag_and_the_record_names_the_read(self, tmp_path):
        world = make_world(tmp_path)
        assert _run(world, FakeJudge()) == 0
        record = _record(world, "bbbb2222")
        assert record["persona_failed"] == ["strategist"]
        for healthy in ("aaaa1111", "cccc3333"):
            assert _record(world, healthy)["persona_failed"] == []

    def test_the_row_shows_it_on_its_own_cell(self, tmp_path):
        world = make_world(tmp_path)
        _run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "| doc | verdict | persona en échec |" in table

        def cells(doc_id):
            line = next(
                line
                for line in table.splitlines()
                if line.startswith(f"| `{doc_id}` |")
            )
            # The pipe-split cells: [empty, doc, verdict, persona, ID, ...].
            return [cell.strip() for cell in line.split("|")]

        # The mark is on cell 3, its own column — never merged into the verdict.
        assert cells("bbbb2222")[3] == "**en échec : `strategist`**"
        for healthy in ("aaaa1111", "cccc3333"):
            assert cells(healthy)[3] == "—"

    def test_the_summary_counts_and_names_the_documents(self, tmp_path):
        world = make_world(tmp_path)
        _run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "**persona en échec** : **1** document(s)" in table
        assert "`bbbb2222`" in table
        assert "**strategist** : `bbbb2222`" in table

    def test_the_table_states_that_a_change_is_read_with_the_failed_input(
        self, tmp_path
    ):
        world = make_world(tmp_path)
        _run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "avec son entrée manquante" in table
        assert "DEGRADED_ARM_REFUSAL_THRESHOLD` est inchangé" in table

    def test_a_healthy_panel_names_no_persona(self, tmp_path):
        world = make_world(tmp_path, failed_docs=())
        _run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "**persona en échec** :" not in table

    def test_the_pass_is_not_refused(self, tmp_path):
        """Ask 2 — the pass runs and the judge is called: a render with a
        missing input is still the pipeline's render."""
        world = make_world(tmp_path, failed_docs=PANEL)
        judge = FakeJudge()
        assert _run(world, judge) == 0
        assert len(judge.calls) == len(PANEL)

    def test_the_consensus_row_and_its_table_carry_the_flag(self):
        def _pass(failed):
            return {
                "opaque_id": "doc_X",
                "positions": {"pipeline": 1, "zeroshot": 2},
                "identification_ok": True,
                "state": "PIPELINE_SUPPLIES",
                "reported_state": "PIPELINE_SUPPLIES",
                "kept": [],
                "dropped": [],
                "costs": {"pipeline": 0.01, "zeroshot": 0.001},
                "judge_cost": 0.1,
                "persona_failed": ["strategist"] if failed else [],
            }

        row = jp.consensus_row(
            [_pass(True), _pass(True), _pass(True)], ["p1", "p2", "p3"]
        )
        assert row["persona_failed"] == ["strategist"]
        table = jp.render_table(
            [row],
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
        assert "**en échec : `strategist`**" in table

    def test_a_clean_consensus_names_no_persona(self):
        row = {
            "opaque_id": "doc_X",
            "positions": {"pipeline": 1, "zeroshot": 2},
            "identification_ok": True,
            "state": "PARITY",
            "reported_state": "PARITY",
            "kept": [],
            "dropped": [],
            "costs": {"pipeline": 0.01, "zeroshot": 0.001},
            "judge_cost": 0.1,
        }
        consensus = jp.consensus_row([row, dict(row), dict(row)], ["p1", "p2", "p3"])
        assert consensus["persona_failed"] == []


# ---------------------------------------------------------------------------
# The writers — the marker reaches the state
# ---------------------------------------------------------------------------


class TestTheWritersKeepTheMarker:
    def test_a_failed_strategist_read_keeps_the_keys(self):
        state = {}
        sw._write_strategic_read_to_state(
            {
                "players": [],
                "options": [],
                "preferences": {},
                "reading": "",
                "game": {},
                "status": "parse_error",
                "degraded": True,
                "degraded_reason": "strategist parse_error: bad reply",
            },
            state,
            {},
        )
        payload = state["strategic_read"]
        assert payload["degraded"] is True
        assert payload["degraded_reason"] == "strategist parse_error: bad reply"
        assert payload["status"] == "parse_error"

    def test_a_successful_strategist_read_writes_no_marker(self):
        state = {}
        sw._write_strategic_read_to_state(
            {"players": [], "status": "ok"},
            state,
            {},
        )
        payload = state["strategic_read"]
        assert "degraded" not in payload
        assert "degraded_reason" not in payload

    def test_a_failed_historian_read_keeps_the_keys(self):
        state = {}
        sw._write_historical_context_to_state(
            {
                "situation": "",
                "items": [],
                "status": "llm_error",
                "degraded": True,
                "degraded_reason": "historian llm_error: timeout",
            },
            state,
            {},
        )
        payload = state["historical_context"]
        assert payload["degraded"] is True
        assert payload["degraded_reason"] == "historian llm_error: timeout"

    def test_a_successful_historian_read_writes_no_marker(self):
        state = {}
        sw._write_historical_context_to_state(
            {"situation": "Une situation.", "items": [], "status": "ok"},
            state,
            {},
        )
        payload = state["historical_context"]
        assert "degraded" not in payload
        assert "degraded_reason" not in payload

    def test_the_marker_reaches_the_health_rule(self):
        """The two halves meet: a state written by the writer is named by
        ``arm_health`` — the marker is not dead weight."""
        state = {}
        sw._write_strategic_read_to_state(
            {
                "players": [],
                "status": "parse_error",
                "degraded": True,
                "degraded_reason": "strategist parse_error: bad reply",
            },
            state,
            {},
        )
        health = jp.arm_health({"state": {**ACTS_RENDERED, **state}})
        assert health["persona_failed"] == ["strategist"]
