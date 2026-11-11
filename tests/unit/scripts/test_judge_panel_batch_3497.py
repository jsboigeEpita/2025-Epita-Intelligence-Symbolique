"""#3497 — the Anthropic judge's passes through the Message Batches API.

Half price on input and output for passes that are not latency-bound (the
consensus is computed offline, #3423). The ask, one witness per clause:

- the batch request carries the SAME body as the synchronous call — one
  payload producer, equality measured, transport fields apart;
- an item that errors, cancels or expires in the batch is a FAILED document,
  counted and named — never an empty verdict, never a silent skip;
- the batch pass flows through the same rows, table and health gates as a
  synchronous pass, with ``route: anthropic-batch`` in the provenance;
- without the flag, nothing changes — same route, same command, the
  per-document judge_call path;
- the cost applies the batch price; a non-Anthropic judge with the flag is
  refused before any call;
- polling is bounded, a single waiter, on the REAL status field
  (``processing_status``: in_progress | canceling | ended).

**Fakes on the real wire** (the avenant, after the first paid batch ran 2
min 13 s and the script timed out on a field the API never sends): each
results line is ``{"custom_id", "result": {"type", …}}`` with the Message
nested at ``result.message``; an ``errored`` line carries the
``ErrorResponse`` at ``result.error.error``; ``canceled``/``expired`` are
per-request result types, NOT batch statuses. Two mutations must redden:
reading ``status`` again, and reading ``result.content``.

No network, no dataset, no key: the batch transport, the endpoint resolver
and the document loader are replaced. **Zero paid call, zero corpus read.**
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
from tests.unit.scripts.test_judge_panel_3375 import (  # noqa: E402
    DOCUMENT_TEXT,
    PANEL,
    FakeJudge,
    _answer,
    _argv,
    _with_panel_file,
    make_world,
)

ENDPOINT = {
    "api_key": "not-a-key",
    "base_url": "https://example.invalid/v1",
    "model_id": "claude-sonnet-5-5",
    "family": "anthropic",
    "host": "example.invalid",
    "route": "anthropic-batch",
    "temperature": None,
}


@pytest.fixture(autouse=True)
def _synthetic_world(monkeypatch):
    """Route and corpus replaced: no witness needs a key or the dataset.

    The resolver answers by model name so the non-Anthropic refusal witness
    passes the family gate (``assert_judge_differs``) and hits the flag's own
    check.
    """

    def fake_resolve(model):
        family = "anthropic" if model.startswith("claude-") else "google"
        return {
            "api_key": "not-a-key",
            "base_url": "https://example.invalid/v1",
            "model_id": model,
            "family": family,
            "host": "example.invalid",
            "route": "test",
        }

    monkeypatch.setattr(jp, "resolve_judge_endpoint", fake_resolve)
    monkeypatch.setattr(
        jp, "load_document_texts", lambda panel: {d: DOCUMENT_TEXT for d in panel}
    )


class FakeBatch:
    """Answers every document from the same table the sync FakeJudge uses."""

    def __init__(self, records=None, elapsed=123.4):
        self.calls = []
        self._records = records
        self._elapsed = elapsed

    async def __call__(
        self, endpoint, prompts, timeout=600, batch_timeout=3600, batch_id=None
    ):
        self.calls.append((endpoint["route"], sorted(prompts), batch_id))
        if self._records is not None:
            return dict(self._records), self._elapsed
        return (
            {
                doc_id: {
                    "status_code": 200,
                    "answer": _answer(),
                    "prompt_tokens": 2000,
                    "completion_tokens": 400,
                    "usage": {},
                    "answered_model": endpoint["model_id"],
                    "stop_reason": "end_turn",
                }
                for doc_id in prompts
            },
            self._elapsed,
        )


def _sync_record(answer=None):
    return {
        "status_code": 200,
        "answer": answer or _answer(),
        "prompt_tokens": 2000,
        "completion_tokens": 400,
        "usage": {},
    }


def _succeeded_line(custom_id, answer=None):
    """The REAL wire shape: the Message object nested at ``result.message``."""
    return {
        "custom_id": custom_id,
        "result": {
            "type": "succeeded",
            "message": {
                "id": f"msg_{custom_id}",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-5-5",
                "content": [{"type": "text", "text": answer or _answer()}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 2000, "output_tokens": 400},
            },
        },
    }


def _errored_line(custom_id):
    """The documented ErrorResponse: details at ``result.error.error``."""
    return {
        "custom_id": custom_id,
        "result": {
            "type": "errored",
            "error": {
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "prompt is too long",
                },
                "request_id": "req_01X",
            },
        },
    }


# ---------------------------------------------------------------------------
# Same request content: one producer, measured equality
# ---------------------------------------------------------------------------


class TestTheRequestBodies:
    def test_the_batch_params_are_the_sync_body(self):
        """One payload producer: batch params == the synchronous body."""
        prompt = "Juge ce document."
        sync_body = jp.anthropic_judge_payload(ENDPOINT, prompt)
        request = jp.build_anthropic_batch_request(ENDPOINT, {"aaaa1111": prompt})
        assert len(request["requests"]) == 1
        entry = request["requests"][0]
        # Transport fields carry the routing; everything else is the body the
        # synchronous call posts.
        assert set(entry) == {"custom_id", "params"}
        assert entry["custom_id"] == "aaaa1111"
        assert entry["params"] == sync_body
        assert sync_body["model"] == ENDPOINT["model_id"]
        assert sync_body["max_tokens"] == jp.JUDGE_MAX_TOKENS
        assert sync_body["messages"] == [{"role": "user", "content": prompt}]

    def test_a_temperature_rides_both_routes_or_neither(self):
        """#3423: the sampling temperature rides the endpoint, on both wires."""
        warm = {**ENDPOINT, "temperature": 0.2}
        assert jp.anthropic_judge_payload(warm, "p")["temperature"] == 0.2
        request = jp.build_anthropic_batch_request(warm, {"aaaa1111": "p"})
        assert request["requests"][0]["params"]["temperature"] == 0.2
        assert "temperature" not in jp.anthropic_judge_payload(ENDPOINT, "p")


# ---------------------------------------------------------------------------
# An error is a failed document, counted and named
# ---------------------------------------------------------------------------


class TestTheBatchResults:
    def test_a_succeeded_line_maps_to_the_sync_record_shape(self):
        record = jp.batch_item_record(_succeeded_line("aaaa1111"))
        assert record["status_code"] == 200
        assert record["prompt_tokens"] == 2000
        assert record["completion_tokens"] == 400
        assert record["answered_model"] == "claude-sonnet-5-5"
        assert record["stop_reason"] == "end_turn"
        assert json.loads(record["answer"])["state"] == "PIPELINE_SUPPLIES"

    def test_an_errored_line_is_a_named_failed_document(self):
        record = jp.batch_item_record(_errored_line("aaaa1111"))
        assert record["status_code"] != 200
        assert record.get("answer") in (None, "")
        assert "invalid_request_error" in record["error_body_head"]
        assert "too long" in record["error_body_head"]

    def test_canceled_and_expired_lines_are_named_failed_documents(self):
        for item_type in ("canceled", "expired"):
            line = {"custom_id": "aaaa1111", "result": {"type": item_type}}
            record = jp.batch_item_record(line)
            assert record["status_code"] != 200
            assert record.get("answer") in (None, "")
            assert item_type in record["error_body_head"]

    def test_the_poll_timeout_names_the_resume_flag(self):
        timed_out = jp.batch_terminal_failure(
            PANEL, "poll_timeout", "msgbatch_123", after_seconds=90
        )
        assert all(r["status_code"] != 200 for r in timed_out.values())
        assert all("90" in r["error_body_head"] for r in timed_out.values())
        assert all(
            "--batch-id msgbatch_123" in r["error_body_head"]
            for r in timed_out.values()
        )


# ---------------------------------------------------------------------------
# The full pass: same rows, same gates, batch provenance
# ---------------------------------------------------------------------------


class TestTheBatchPass:
    def _run(self, tmp_path, batch, extra=("--anthropic-batch",)):
        world = _with_panel_file(make_world(tmp_path))
        argv = _argv(world, extra=extra)
        rc = asyncio.run(jp.run(argv, judge_batch_call=batch))
        out = world["out"]
        meta = json.loads((out / jp.META_FILENAME).read_text(encoding="utf-8"))
        rows = {
            doc_id: json.loads((out / f"{doc_id}.json").read_text(encoding="utf-8"))
            for doc_id in PANEL
        }
        return rc, meta, rows

    def test_the_batch_pass_produces_the_same_rows_as_the_sync_pass(self, tmp_path):
        """Same answers in, same verdict rows out — only the route differs."""
        rc_b, meta_b, rows_b = self._run(tmp_path / "b", FakeBatch())
        world_s = _with_panel_file(make_world(tmp_path / "s"))
        judge = FakeJudge()
        rc_s = asyncio.run(jp.run(_argv(world_s), judge_call=judge))
        assert rc_b == rc_s == 0
        assert judge.calls  # the sync path did go through judge_call
        for doc_id in PANEL:
            row_s = json.loads(
                (world_s["out"] / f"{doc_id}.json").read_text(encoding="utf-8")
            )
            # The verdict fields are identical: the same answer through the
            # batch wire lands in the same row the synchronous wire builds.
            for field in ("state", "kept", "dropped"):
                assert rows_b[doc_id][field] == row_s[field], field
        # Provenance: the route and the replayable command say the batch.
        assert meta_b["judge_route"] == "anthropic-batch"
        assert "--anthropic-batch" in meta_b["command"]

    def test_without_the_flag_nothing_changes(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        judge = FakeJudge()
        batch = FakeBatch()
        rc = asyncio.run(jp.run(_argv(world), judge_call=judge, judge_batch_call=batch))
        assert rc == 0
        assert len(judge.calls) == len(PANEL)
        assert batch.calls == []  # the batch wire is never touched
        meta = json.loads((world["out"] / jp.META_FILENAME).read_text(encoding="utf-8"))
        assert "--anthropic-batch" not in meta["command"]
        assert meta["judge_route"] != "anthropic-batch"

    def test_a_failed_batch_item_exits_two_and_names_the_document(self, tmp_path):
        records = {doc_id: _sync_record() for doc_id in PANEL}
        records["bbbb2222"] = {
            "status_code": 0,
            "error_body_head": "batch item errored (overloaded): try later",
        }
        rc, meta, rows = self._run(tmp_path, FakeBatch(records=records))
        assert rc == 2
        assert rows["bbbb2222"]["state"] == "UNPARSED"
        assert "overloaded" in rows["bbbb2222"]["error_body_head"]

    def test_the_batch_cost_is_half_the_synchronous_price(self, tmp_path):
        from argumentation_analysis.services.model_prices import price_tokens

        rc_b, _meta_b, rows_b = self._run(tmp_path / "b", FakeBatch())
        world_s = _with_panel_file(make_world(tmp_path / "s"))
        rc_s = asyncio.run(jp.run(_argv(world_s), judge_call=FakeJudge()))
        assert rc_b == rc_s == 0
        sync_price = price_tokens("claude-sonnet-5-5", 2000, 400)
        if sync_price is None:
            pytest.skip("claude-sonnet-5-5 unpriced in the table")
        doc = PANEL[0]
        assert rows_b[doc]["judge_cost"] == pytest.approx(sync_price * 0.5)
        row_s = json.loads((world_s["out"] / f"{doc}.json").read_text(encoding="utf-8"))
        assert row_s["judge_cost"] == pytest.approx(sync_price)

    def test_the_flag_refuses_a_non_anthropic_judge(self, tmp_path):
        """Loud, before any call: the batch API is Anthropic-native."""
        world = _with_panel_file(make_world(tmp_path))
        batch = FakeBatch()
        with pytest.raises(SystemExit):
            asyncio.run(
                jp.run(
                    _argv(
                        world,
                        judge_model="gemini-4-argon",
                        extra=("--anthropic-batch",),
                    ),
                    judge_batch_call=batch,
                )
            )
        assert batch.calls == []

    def test_the_batch_elapsed_reaches_every_row_and_meta(self, tmp_path):
        """The avenant's elapsed defect: a second assignment overwrote the
        batch's wall time with ≈ 0.0 per row, and META said nothing."""
        rc, meta, rows = self._run(tmp_path, FakeBatch(elapsed=123.4))
        assert rc == 0
        for doc_id in PANEL:
            assert rows[doc_id]["elapsed_seconds"] == 123.4
        assert meta["batch_elapsed_seconds"] == 123.4

    def test_without_the_flag_the_per_document_timing_is_unchanged(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        rc = asyncio.run(jp.run(_argv(world), judge_call=FakeJudge()))
        assert rc == 0
        meta = json.loads((world["out"] / jp.META_FILENAME).read_text(encoding="utf-8"))
        assert "batch_elapsed_seconds" not in meta
        assert "resumed_batch_id" not in meta
        for doc_id in PANEL:
            row = json.loads(
                (world["out"] / f"{doc_id}.json").read_text(encoding="utf-8")
            )
            assert (
                row["elapsed_seconds"] < 123.0
            )  # measured per document, not the batch's

    def test_resume_by_batch_id_skips_the_submit_and_marks_meta(self, tmp_path):
        batch = FakeBatch(elapsed=42.0)
        rc, meta, rows = self._run(
            tmp_path, batch, extra=("--batch-id", "msgbatch_paid123")
        )
        assert rc == 0
        # --batch-id alone routes the batch wire, with the id passed through.
        assert batch.calls == [("anthropic-batch", sorted(PANEL), "msgbatch_paid123")]
        assert meta["resumed_batch_id"] == "msgbatch_paid123"
        assert "--batch-id msgbatch_paid123" in meta["command"]
        assert meta["batch_elapsed_seconds"] == 42.0
        for doc_id in PANEL:
            assert rows[doc_id]["elapsed_seconds"] == 42.0

    def test_a_batch_carrying_a_foreign_custom_id_is_refused_loudly(self):
        """A resumed batch that is not THIS panel's: a loud ValueError, no
        verdicts mapped onto this run — the witness runs the real wire."""
        transport = FakeTransport(
            statuses=["ended"],
            results_lines=[_succeeded_line("zzzz9999")],
        )
        with pytest.raises(ValueError, match="outside the"):
            asyncio.run(
                jp.call_judge_batch(
                    ENDPOINT,
                    {"aaaa1111": "p1"},
                    batch_timeout=60,
                    poll_seconds=0,
                    _transport=transport,
                    batch_id="msgbatch_other",
                )
            )
        # Resume: nothing was submitted for the foreign batch.
        assert transport.posts == 0


# ---------------------------------------------------------------------------
# The waiter: bounded, single, every terminal state
# ---------------------------------------------------------------------------


class FakeTransport:
    """Posts once, then answers a scripted processing_status sequence, then
    results — on the REAL wire shape (the avenant): the status object
    carries ``processing_status`` and ``request_counts``; results lines are
    nested (``result.type`` / ``result.message``)."""

    def __init__(self, statuses, results_lines=None, submit_status=200):
        self._statuses = list(statuses)
        self._results = results_lines or []
        self._submit_status = submit_status
        self.posts = 0
        self.gets = 0

    async def post(self, url, json=None, headers=None, timeout=None):
        self.posts += 1
        return FakeResponse(self._submit_status, {"id": "msgbatch_123"})

    async def get(self, url, headers=None, timeout=None):
        self.gets += 1
        if url.endswith("/results"):
            return FakeResponse(200, "\n".join(json_dumps(l) for l in self._results))
        status = self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
        return FakeResponse(
            200,
            {
                "id": "msgbatch_123",
                "type": "message_batch",
                "processing_status": status,
                "request_counts": {
                    "processing": 0,
                    "succeeded": 1,
                    "errored": 0,
                    "canceled": 0,
                    "expired": 0,
                },
            },
        )


def json_dumps(obj):
    return json.dumps(obj)


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    @property
    def text(self):
        return self._body if isinstance(self._body, str) else json.dumps(self._body)

    def json(self):
        return json.loads(self.text) if isinstance(self._body, str) else self._body


class TestTheWaiter:
    PROMPTS = {"aaaa1111": "p1", "bbbb2222": "p2"}

    def test_ended_retrieves_the_results(self):
        transport = FakeTransport(
            statuses=["in_progress", "ended"],
            results_lines=[
                _succeeded_line("aaaa1111"),
                _errored_line("bbbb2222"),
            ],
        )
        records, elapsed = asyncio.run(
            jp.call_judge_batch(
                ENDPOINT,
                self.PROMPTS,
                batch_timeout=60,
                poll_seconds=0,
                _transport=transport,
            )
        )
        assert records["aaaa1111"]["status_code"] == 200
        assert records["aaaa1111"]["answered_model"] == "claude-sonnet-5-5"
        assert records["bbbb2222"]["status_code"] != 200
        assert "invalid_request_error" in records["bbbb2222"]["error_body_head"]
        assert elapsed >= 0
        # A single submit, and the poll loop is bounded by the status count.
        assert transport.posts == 1

    def test_expired_and_canceled_lines_are_named_in_their_records(self):
        """canceled/expired are per-request result TYPES, not batch statuses:
        the batch still ends, and its cancelled/expired requests are named."""
        transport = FakeTransport(
            statuses=["ended"],
            results_lines=[
                {"custom_id": "aaaa1111", "result": {"type": "expired"}},
                {"custom_id": "bbbb2222", "result": {"type": "canceled"}},
            ],
        )
        records, _ = asyncio.run(
            jp.call_judge_batch(
                ENDPOINT,
                self.PROMPTS,
                batch_timeout=60,
                poll_seconds=0,
                _transport=transport,
            )
        )
        assert records["aaaa1111"]["status_code"] != 200
        assert "expired" in records["aaaa1111"]["error_body_head"]
        assert records["bbbb2222"]["status_code"] != 200
        assert "canceled" in records["bbbb2222"]["error_body_head"]

    def test_canceling_keeps_waiting(self):
        transport = FakeTransport(
            statuses=["canceling", "ended"],
            results_lines=[_succeeded_line("aaaa1111"), _succeeded_line("bbbb2222")],
        )
        records, _ = asyncio.run(
            jp.call_judge_batch(
                ENDPOINT,
                self.PROMPTS,
                batch_timeout=60,
                poll_seconds=0,
                _transport=transport,
            )
        )
        assert all(r["status_code"] == 200 for r in records.values())

    def test_the_waiters_own_timeout_is_bounded_and_reported(self):
        transport = FakeTransport(statuses=["in_progress"])
        records, _ = asyncio.run(
            jp.call_judge_batch(
                ENDPOINT,
                self.PROMPTS,
                batch_timeout=5,
                poll_seconds=0,
                _transport=transport,
            )
        )
        assert all(r["status_code"] != 200 for r in records.values())
        assert all("poll timeout" in r["error_body_head"] for r in records.values())
        assert all("--batch-id" in r["error_body_head"] for r in records.values())
        # Bounded: the loop stopped even though the batch never ended.
        assert transport.gets <= 12

    def test_resume_polls_and_retrieves_without_a_submit(self):
        transport = FakeTransport(
            statuses=["in_progress", "ended"],
            results_lines=[_succeeded_line("aaaa1111"), _succeeded_line("bbbb2222")],
        )
        records, _ = asyncio.run(
            jp.call_judge_batch(
                ENDPOINT,
                self.PROMPTS,
                batch_timeout=60,
                poll_seconds=0,
                _transport=transport,
                batch_id="msgbatch_paid123",
            )
        )
        assert transport.posts == 0  # no submit: the batch was already paid
        assert all(r["status_code"] == 200 for r in records.values())

    def test_a_foreign_custom_id_on_resume_is_a_loud_refusal(self):
        transport = FakeTransport(
            statuses=["ended"],
            results_lines=[_succeeded_line("zzzz9999")],
        )
        with pytest.raises(ValueError, match="outside the"):
            asyncio.run(
                jp.call_judge_batch(
                    ENDPOINT,
                    self.PROMPTS,
                    batch_timeout=60,
                    poll_seconds=0,
                    _transport=transport,
                    batch_id="msgbatch_other",
                )
            )
        assert transport.posts == 0
