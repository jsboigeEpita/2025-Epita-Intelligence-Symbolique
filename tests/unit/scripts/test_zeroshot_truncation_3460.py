"""#3460 — a zero-shot answer cut at the token cap is never counted as a
finished baseline.

Measured on panel B (#3374): 2 of 10 Sonnet answers stopped at
``finish_reason: "length"`` — exactly 16 000 completion tokens, the cap
hardcoded in ``build_payload``. Sonnet bills its hidden thinking as
completion tokens (#3096: ~44 % of a completion), so a cap sized for luna
cuts a thinking model's visible answer. The producer counted both as
``ok``, and the judge graded a baseline that was never finished — a bias
that always goes toward the pipeline.

The dispatch's DoD, one witness per clause:

- producer: a truncated answer is printed ``TRUNCATED``, counted apart from
  ``ok``, and the run exits non-zero; the cap becomes
  ``--max-completion-tokens`` (default 32 000+, room for a thinking model)
  recorded in the provenance header and reaching the payload;
- judge: the arm's recorded ``finish_reason`` is read — a truncated
  zero-shot document is flagged in its record and the verdict table, never
  counted as a plain pipeline win; a systemic truncation refuses before any
  paid call (the #3458 mechanism).

Synthetic records only, no corpus text: the loaders and the call are
replaced. **Zero paid call, zero corpus read.**
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
from scripts.dataset import run_zeroshot_arm as arm  # noqa: E402

# ---------------------------------------------------------------------------
# Synthetic arms for the judge side
# ---------------------------------------------------------------------------

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
ACTS_RENDERED = {
    "act1_framing": "Acte I rendu sur ce document.",
    "act2_narrative": "Acte II rendu sur ce document.",
    "act3_conclusion": "Acte III rendu sur ce document.",
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_world(tmp_path: Path, truncated=()):
    """A stand-in campaign; docs in ``truncated`` carry a zero-shot answer
    that stopped at the cap (``finish_reason: "length"``, #3460's measured
    shape — sibling of ``answer`` at the record's root)."""
    states = tmp_path / "states"
    signatures = tmp_path / "signatures"
    zeroshots = tmp_path / "zeroshots"
    for doc_id in PANEL:
        _write_json(
            states / f"state_full_{doc_id}.json", {"state": dict(ACTS_RENDERED)}
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
                # The arm's model NAME is inert here (only finish_reason
                # decides); gpt-5.6-luna keeps the judge's family check
                # honest — the real panel B ran the arm on Sonnet.
                "provenance": {"model": "gpt-5.6-luna", "git_head": "deadbeef"},
                "usage": {"prompt_tokens": 900, "completion_tokens": 250},
                "answer": ZEROSHOT_TEXT,
                **(
                    {"finish_reason": "length"}
                    if doc_id in truncated
                    else {"finish_reason": "stop"}
                ),
            },
        )
    panel_file = tmp_path / "panel.txt"
    panel_file.write_text("\n".join(PANEL) + "\n", encoding="utf-8")
    return {
        "states": states,
        "signatures": signatures,
        "zeroshots": zeroshots,
        "out": tmp_path / "out",
        "panel_file": panel_file,
    }


def _answer():
    return json.dumps(
        {
            "identification": "1",
            "state": "PIPELINE_SUPPLIES",
            "items": [],
            "style_notes": [],
            "conclusion": "Le surplus est formel.",
        },
        ensure_ascii=False,
    )


class FakeJudge:
    def __init__(self):
        self.calls = []

    async def __call__(self, endpoint, prompt, timeout=600):
        self.calls.append(prompt)
        return {
            "status_code": 200,
            "answer": _answer(),
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
# The producer — a cut answer is named, counted apart, and fails the run
# ---------------------------------------------------------------------------


def _synthetic_definitions():
    return [
        {
            "source_name": "src_gamma",
            "full_text": "",
            "extracts": [{"extract_text": "texte court gamma."}],
        },
        {
            "source_name": "src_delta",
            "full_text": "",
            "extracts": [{"extract_text": "texte court delta."}],
        },
    ]


def _wire_run(monkeypatch, tmp_path):
    """Wire the producer's surroundings for a run with zero corpus read:
    definitions, endpoint, output dir, env stamp. The CALL stays real —
    the caller replaces it (or the HTTP layer) as their witness needs."""
    # CI has no .env: the opaque-id salt must come from the test
    # (convention neighbour: test_run_zeroshot_arm_2841.py).
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3460")
    monkeypatch.setattr(arm, "load_definitions", _synthetic_definitions)
    monkeypatch.setattr(
        arm,
        "resolve_arm_endpoint",
        lambda: {"api_key": "k", "base_url": "https://gw.example/v1", "model_id": "m"},
    )
    monkeypatch.setattr(arm, "RESULTS_DIR", tmp_path / "zeroshot")
    monkeypatch.setattr(
        "argumentation_analysis.evaluation.env_manifest.render_environment_stamp",
        lambda manifest: "env-stamp",
    )


def _fake_arm(monkeypatch, tmp_path, records):
    """``_wire_run`` plus a fake ``call_zeroshot``: ``records`` maps the Nth
    call to its returned record."""
    _wire_run(monkeypatch, tmp_path)
    calls = []

    async def _call(endpoint, doc_text, timeout, max_completion_tokens=32000):
        calls.append(doc_text)
        return records[len(calls) - 1]

    monkeypatch.setattr(arm, "call_zeroshot", _call)
    return calls


class TestTheCapIsAFlag:
    def test_the_default_leaves_room_for_a_thinking_model(self):
        """#3096 measured ~44 % of a Sonnet completion is thinking; luna's
        largest was 11 781 and 16 000 cut Sonnet twice. The default must be
        at least twice that cap."""
        assert arm.DEFAULT_MAX_COMPLETION_TOKENS >= 32000
        payload = arm.build_payload("m", "doc text")
        assert payload["max_completion_tokens"] >= 32000

    def test_the_flag_reaches_the_payload(self, monkeypatch, tmp_path):
        captured = {}

        class _FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": "reponse."}, "finish_reason": "stop"}
                    ],
                    "usage": {"total_tokens": 42},
                }

        class _FakeClient:
            def __init__(self, timeout=None):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, headers=None):
                captured["payload"] = json
                return _FakeResponse()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
        _wire_run(monkeypatch, tmp_path)
        rc = asyncio.run(
            arm.run_arm(["--max-completion-tokens", "45000", "--max-chars", "0"])
        )
        assert rc == 0
        assert captured["payload"]["max_completion_tokens"] == 45000

    def test_the_cap_rides_in_the_provenance_header(self):
        header = arm.provenance_header(
            "m", "https://gw.example/v1", 0, max_completion_tokens=45000
        )
        assert header["max_completion_tokens"] == 45000
        assert "--max-completion-tokens 45000" in header["command"]

    def test_the_header_records_the_default_when_not_given(self):
        header = arm.provenance_header("m", "https://gw.example/v1", 0)
        assert header["max_completion_tokens"] == arm.DEFAULT_MAX_COMPLETION_TOKENS


class TestACutAnswerIsNotOk:
    def test_one_truncated_answer_is_named_counted_apart_and_fails_the_run(
        self, monkeypatch, tmp_path, capsys
    ):
        _fake_arm(
            monkeypatch,
            tmp_path,
            [
                {
                    "status_code": 200,
                    "answer": "premiere reponse complete.",
                    "finish_reason": "stop",
                    "usage": {"completion_tokens": 800},
                },
                {
                    "status_code": 200,
                    # #3460's measured shape: text IS present, the cap cut it
                    "answer": "reponse coupee avant sa conclusion...",
                    "finish_reason": "length",
                    "usage": {"completion_tokens": 16000},
                },
            ],
        )
        rc = asyncio.run(arm.run_arm(["--max-chars", "0"]))
        out = capsys.readouterr().out
        assert rc != 0, "a run with a truncated answer exits non-zero"
        assert "TRUNCATED" in out, "the truncated answer is printed TRUNCATED"
        assert "16000" in out, "the print names the cap it stopped at"
        assert "truncated: 1" in out, "truncated is counted apart from ok"
        assert "ok: 1" in out and "ok: 2" not in out
        records = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((tmp_path / "zeroshot").glob("*.json"))
        ]
        assert sum(1 for r in records if r.get("finish_reason") == "length") == 1

    def test_a_run_without_truncation_still_exits_zero(
        self, monkeypatch, tmp_path, capsys
    ):
        _fake_arm(
            monkeypatch,
            tmp_path,
            [
                {
                    "status_code": 200,
                    "answer": "premiere reponse complete.",
                    "finish_reason": "stop",
                    "usage": {"completion_tokens": 800},
                },
                {
                    "status_code": 200,
                    "answer": "seconde reponse complete.",
                    "finish_reason": "stop",
                    "usage": {"completion_tokens": 900},
                },
            ],
        )
        rc = asyncio.run(arm.run_arm(["--max-chars", "0"]))
        out = capsys.readouterr().out
        assert rc == 0
        assert "TRUNCATED" not in out
        assert "truncated: 0" in out
        assert "ok: 2" in out


# ---------------------------------------------------------------------------
# The judge — the arm's own finish_reason is read, not assumed
# ---------------------------------------------------------------------------


class TestTheJudgeFlagsTheTruncatedBaseline:
    def test_one_truncated_document_is_flagged_in_its_record(self, tmp_path):
        world = make_world(tmp_path, truncated=("bbbb2222",))
        judge = FakeJudge()
        assert _run(world, judge) == 0
        assert len(judge.calls) == len(
            PANEL
        ), "one truncated doc does not stop the pass"
        assert _record(world, "bbbb2222")["zeroshot_truncated"] is True
        assert _record(world, "aaaa1111")["zeroshot_truncated"] is False
        assert _record(world, "cccc3333")["zeroshot_truncated"] is False

    def test_the_table_carries_the_flag_and_never_a_plain_pipeline_win(self, tmp_path):
        world = make_world(tmp_path, truncated=("bbbb2222",))
        _run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "**zero-shot tronqué**" in table
        assert "`bbbb2222`" in table
        assert "jamais comptés comme une victoire simple du pipeline" in table

    def test_a_finished_baseline_carries_no_flag(self, tmp_path):
        world = make_world(tmp_path)
        assert _run(world, FakeJudge()) == 0
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        for doc_id in PANEL:
            assert _record(world, doc_id)["zeroshot_truncated"] is False
        assert "zero-shot tronqué" not in table


class TestASystemicallyTruncatedBaselineIsRefused:
    def test_two_truncated_documents_refuse_before_the_first_paid_call(
        self, tmp_path, capsys
    ):
        world = make_world(tmp_path, truncated=("bbbb2222", "cccc3333"))
        judge = FakeJudge()
        rc = _run(world, judge)
        out = capsys.readouterr().out
        assert rc == 3, "the refusal is a distinct non-zero exit, not a WARN"
        assert "`bbbb2222`" in out and "`cccc3333`" in out
        assert "before the first paid call" in out

    def test_the_fake_judge_is_never_invoked_on_the_refusal(self, tmp_path):
        world = make_world(tmp_path, truncated=("bbbb2222", "cccc3333"))
        judge = FakeJudge()
        _run(world, judge)
        assert judge.calls == []

    def test_the_override_judges_anyway_and_prints_its_use(self, tmp_path, capsys):
        world = make_world(tmp_path, truncated=("bbbb2222", "cccc3333"))
        judge = FakeJudge()
        rc = _run(world, judge, extra=["--allow-degraded-arm"])
        out = capsys.readouterr().out
        assert rc == 0
        assert len(judge.calls) == len(PANEL)
        assert "--allow-degraded-arm" in out
        assert _record(world, "bbbb2222")["zeroshot_truncated"] is True


class TestTheConsensusKeepsTheTruncationFlag:
    def _pass(self, doc="d1", truncated=None):
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
        if truncated is not None:
            row["zeroshot_truncated"] = truncated
        return row

    def test_the_consensus_row_carries_the_flag_of_its_passes(self):
        row = jp.consensus_row(
            [
                self._pass(truncated=True),
                self._pass(truncated=True),
                self._pass(truncated=True),
            ],
            ["p1", "p2", "p3"],
        )
        assert row["zeroshot_truncated"] is True

    def test_a_consensus_of_finished_passes_stays_unflagged(self):
        row = jp.consensus_row(
            [self._pass(), self._pass(), self._pass()], ["p1", "p2", "p3"]
        )
        assert row["zeroshot_truncated"] is False
