"""#3478 — the dry-run resolves the judge's route, and the third family is priced.

The first third-family run (#3465 ask 4) hit two seams the judge's own checks
did not cover: both panels' dry-runs exited 0 while the first paid pass died
at ``resolve_judge_endpoint`` (the canonical route resolves to an OpenAI model
and no named route exists for google — the #3402 seam class, already paid for
once), and ``gemini-4-argon`` was in no price row, so 12 passes costing 7.55 $
printed ``unpriced`` and every row recorded ``judge_cost: None``.

Witnessed here, zero paid call, zero corpus read (the document loader is
replaced, as in test_judge_panel_3375.py):

- the dry-run resolves the route through the REAL ``resolve_judge_endpoint``
  — doubles touch the environment only, never the resolver;
- a judge family with no route exits the dry-run non-zero, the same
  SystemExit the paid pass would hit before its first call;
- a resolvable route prints ``family=``, ``host=`` and ``route=``;
- ``price_tokens`` prices both the bare and the routed id (2 $/M in, 10 $/M
  out — the 12 recorded passes price 7.55 $), and the dry-run estimate stops
  saying ``unpriced``;
- a model still absent from the table stays ``unpriced``, never 0.0000 $
  (#1019 tri-state — pinned before, must survive the new row).
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

# --- synthetic arms (same shape as test_judge_panel_3375.py) ----------------

PIPELINE_TEXT = "Acte I — cadrage synthetique, sans nom reel."
ZEROSHOT_TEXT = "Le zero-shot defend une these beta, sans nom reel non plus."
DOCUMENT_TEXT = "Document synthetique de test, sans aucune donnee du corpus."
PANEL = ["aaaa1111", "bbbb2222", "cccc3333"]
SEED = 3378


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_world(tmp_path: Path, ids=PANEL, zeroshot_model="gpt-5.6-luna"):
    states = tmp_path / "states"
    signatures = tmp_path / "signatures"
    zeroshots = tmp_path / "zeroshots"
    for doc_id in ids:
        _write_json(
            states / f"state_full_{doc_id}.json",
            {"state": {"act1_framing": PIPELINE_TEXT}},
        )
        _write_json(
            signatures / f"signature_{doc_id}.json",
            {
                "opaque_id": doc_id,
                "llm_usage": {
                    "phase_1": {"prompt_tokens": 100, "completion_tokens": 20}
                },
            },
        )
        _write_json(
            zeroshots / f"{doc_id}.json",
            {
                "opaque_id": doc_id,
                "provenance": {"model": zeroshot_model, "git_head": "deadbeef"},
                "usage": {"prompt_tokens": 90, "completion_tokens": 25},
                "answer": ZEROSHOT_TEXT,
            },
        )
    panel_file = tmp_path / "panel.txt"
    panel_file.write_text("\n".join(ids) + "\n", encoding="utf-8")
    return {
        "panel_file": panel_file,
        "states": states,
        "signatures": signatures,
        "zeroshots": zeroshots,
        "out": tmp_path / "out",
    }


def _argv(world, judge_model="gemini-4-argon", extra=()):
    return [
        "--judge-model",
        judge_model,
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


class FakeJudge:
    """Counts its calls — a dry-run witness must never need a real key."""

    def __init__(self):
        self.calls = []

    async def __call__(self, endpoint, prompt, timeout=600):
        self.calls.append(prompt)
        return {"status_code": 200, "answer": "{}", "usage": {}}


@pytest.fixture(autouse=True)
def _synthetic_documents(monkeypatch):
    """No witness ever reads the corpus (privacy rule 5)."""
    monkeypatch.setattr(
        jp,
        "load_document_texts",
        lambda panel: {doc_id: DOCUMENT_TEXT for doc_id in panel},
    )


# --- environment doubles — the resolver itself is NEVER doubled -------------

_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_CHAT_MODEL_ID",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_CHAT_MODEL_ID",
    "ANTHROPIC_BASE_URL",
)


def _clear_routes(monkeypatch):
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)


def _openrouter_canonical(monkeypatch):
    """The canonical route resolves to the judge's own routed id."""
    _clear_routes(monkeypatch)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.example.test/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-a-key")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "google/gemini-4-argon")


def _openai_canonical(monkeypatch):
    """The canonical route resolves to an OpenAI model — no route for google."""
    _clear_routes(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test-not-a-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")


def _anthropic_canonical(monkeypatch):
    """The named Anthropic route — for a judge the table still does not price."""
    _clear_routes(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-key")
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-sonnet-5-5")


# ---------------------------------------------------------------------------
# 1 — the dry-run resolves the route
# ---------------------------------------------------------------------------


class TestTheDryRunResolvesTheRoute:
    def test_a_judge_family_without_a_route_exits_non_zero(
        self, tmp_path, monkeypatch, capsys
    ):
        _openai_canonical(monkeypatch)
        world = _make_world(tmp_path)

        with pytest.raises(SystemExit) as excinfo:
            asyncio.run(
                jp.run(
                    _argv(world, judge_model="gemini-4-argon", extra=("--dry-run",)),
                    judge_call=FakeJudge(),
                )
            )

        # A string message exits 1 at the top level — the same non-zero code
        # the paid pass would have taken at the same call.
        assert excinfo.value.code not in (0, None)
        assert "no named route exists for google" in str(excinfo.value)
        assert "no call made" not in capsys.readouterr().out

    def test_a_resolvable_route_is_printed_with_family_host_and_route(
        self, tmp_path, monkeypatch, capsys
    ):
        _openrouter_canonical(monkeypatch)
        world = _make_world(tmp_path)
        judge = FakeJudge()

        code = asyncio.run(
            jp.run(
                _argv(world, judge_model="gemini-4-argon", extra=("--dry-run",)),
                judge_call=judge,
            )
        )

        assert code == 0
        out = capsys.readouterr().out
        assert "family=google" in out
        assert "host=openrouter.example.test" in out
        assert "route=canonical" in out
        assert judge.calls == [], "the dry-run made a call"
        assert "no call made" in out


# ---------------------------------------------------------------------------
# 2 — the third-family judge is priced
# ---------------------------------------------------------------------------


class TestTheThirdFamilyIsPriced:
    def test_price_tokens_prices_both_ids(self):
        from argumentation_analysis.services.model_prices import (
            price_tokens,
            resolve_price_row,
        )

        for model_id in ("gemini-4-argon", "google/gemini-4-argon"):
            row = resolve_price_row(model_id, 0)
            assert row is not None, model_id
            assert row.input_per_mtok == 2.00
            assert row.output_per_mtok == 10.00
            assert row.read_on == "2026-11-06"
        assert price_tokens("gemini-4-argon", 1_000_000, 1_000_000) == 12.0
        assert price_tokens("google/gemini-4-argon", 1_000_000, 1_000_000) == 12.0

    def test_the_recorded_passes_price_to_the_measured_figure(self):
        """2 948 316 in / 165 991 out over 12 passes (#3465 ask 4): 7.55 $."""
        from argumentation_analysis.services.model_prices import price_tokens

        total = price_tokens("google/gemini-4-argon", 2_948_316, 165_991)

        assert total == pytest.approx(7.5565, abs=1e-3)

    def test_the_dry_run_estimate_stops_saying_unpriced(
        self, tmp_path, monkeypatch, capsys
    ):
        _openrouter_canonical(monkeypatch)
        world = _make_world(tmp_path)

        asyncio.run(
            jp.run(
                _argv(world, judge_model="gemini-4-argon", extra=("--dry-run",)),
                judge_call=FakeJudge(),
            )
        )

        out = capsys.readouterr().out
        assert "estimated judge cost:" in out
        assert "$" in out
        assert "unpriced" not in out

    def test_an_absent_model_stays_unpriced_never_zero(
        self, tmp_path, monkeypatch, capsys
    ):
        _anthropic_canonical(monkeypatch)
        world = _make_world(tmp_path)

        code = asyncio.run(
            jp.run(
                _argv(world, judge_model="claude-unpriced-9", extra=("--dry-run",)),
                judge_call=FakeJudge(),
            )
        )

        assert code == 0
        out = capsys.readouterr().out
        assert "unpriced" in out
        assert "0.0000 $" not in out
