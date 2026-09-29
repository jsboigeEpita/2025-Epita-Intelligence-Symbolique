"""#2841 — guards for the zero-shot arm producer.

Each guard kills a measured anti-pattern of the existing instruments
(named in #2841's table):

1. ``text[:8000]`` — run_capstone_c1's baseline truncates the zero-shot
   input while the pipeline receives the full document;
2. ``_scrub_baseline`` — it kept only the answer's LENGTH: nothing was
   left to read side by side;
3. raw env model reads — the #2352 class: an arm that reads
   ``OPENAI_CHAT_MODEL_ID`` directly measures a model the resolver may
   substitute away (the #2827 lesson, requalified by measurement);
4. a divergent population — the two arms must run the SAME documents:
   the producer reuses ``expand_corpus``, never a re-implementation.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dataset import run_zeroshot_arm as arm


def _synthetic_definitions():
    """Two sources, three extracts — the shapes expand_corpus branches on:
    a single-extract source (id = src oid) and a multi-extract one
    (ids = src oid_extN)."""
    long_text = ("argument. " * 1300)[:9000]  # > 8000: the truncation witness
    return [
        {
            "source_name": "src_alpha",
            "full_text": "",
            "extracts": [{"extract_text": "texte court alpha."}],
        },
        {
            "source_name": "src_beta",
            "full_text": "",
            "extracts": [
                {"extract_text": long_text},
                {"extract_text": "texte court beta 2."},
            ],
        },
    ]


class TestFullTextGuard:
    """Kills the ``[:8000]`` cut: the prompt carries the WHOLE document."""

    def test_prompt_carries_the_full_text_past_8000_chars(self):
        text = ("mot. " * 2000)[:9000]
        prompt = arm.build_prompt(text)
        assert text[-50:] in prompt, (
            "the tail of a 9000-char document is missing from the prompt — "
            "the run_capstone_c1 [:8000] cut is back"
        )
        assert len(prompt) >= len(text)

    def test_prompt_is_the_capstone_analyst_prompt_verbatim(self):
        """Same starting point as mandated: imported from run_capstone_c1,
        not re-typed (a copy would drift)."""
        from scripts.run_capstone_c1 import ZEROSHOT_PROMPT

        assert arm.ZEROSHOT_PROMPT is ZEROSHOT_PROMPT


class TestFullAnswerGuard:
    """Kills the length-only scrub: the record keeps the WHOLE answer."""

    def test_call_zeroshot_keeps_the_answer_verbatim(self, monkeypatch):
        answer = "Analyse complète. " * 400  # long answer, 6800+ chars
        captured = {}

        class _FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": answer}, "finish_reason": "stop"}
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
                captured["url"] = url
                captured["payload"] = json
                return _FakeResponse()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
        record = {"k": "x"}
        import asyncio

        record = asyncio.run(
            arm.call_zeroshot(
                {"api_key": "k", "base_url": "https://gw.example/v1", "model_id": "m"},
                "doc",
                timeout=30,
            )
        )
        assert record["answer"] == answer, (
            "the answer is not kept verbatim — the _scrub_baseline "
            "length-only anti-pattern is back"
        )
        assert record["status_code"] == 200
        # No tools, no effort: a plain analyst call.
        assert "tools" not in captured["payload"]


class TestResolverProvenance:
    """The arm's model comes from the canonical resolver, never a raw env
    read (#2352/#2840)."""

    def test_endpoint_comes_from_resolve_chat_endpoint(self, monkeypatch):
        from argumentation_analysis.core import llm_service

        monkeypatch.setattr(
            llm_service,
            "resolve_chat_endpoint",
            lambda: ("key-x", "https://gw.example/v1", "sentinel-model"),
        )
        endpoint = arm.resolve_arm_endpoint()
        assert endpoint["model_id"] == "sentinel-model"
        assert endpoint["base_url"] == "https://gw.example/v1"

    def test_no_key_is_a_named_exit(self, monkeypatch):
        from argumentation_analysis.core import llm_service

        monkeypatch.setattr(llm_service, "resolve_chat_endpoint", lambda: ("", "", "m"))
        with pytest.raises(SystemExit, match="no API key resolved"):
            arm.resolve_arm_endpoint()


class TestSamePopulation:
    """The arm runs the pipeline arm's documents, via expand_corpus itself."""

    async def test_dry_run_ladder_matches_expand_corpus(self, monkeypatch, capsys):
        # CI has no .env: the salt must come from the test, so the ladder
        # comparison is decided by _synthetic_definitions alone (born red:
        # delenv reproduces CI's RuntimeError first; convention neighbour
        # tests/scripts/test_corpus_batch_coverage_1903.py:84).
        monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-2841")
        monkeypatch.setattr(arm, "load_definitions", _synthetic_definitions)
        rc = await arm.run_arm(["--dry-run", "--max-chars", "0"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "candidate documents: 3" in out

        from scripts.dataset.run_corpus_batch import expand_corpus

        docs, _, _ = expand_corpus(_synthetic_definitions(), 0)
        for doc in docs:
            assert doc["opaque_id"] in out, (
                f"{doc['opaque_id']} missing from the arm's ladder — the "
                "two arms would run different documents"
            )

    async def test_dry_run_makes_no_network_and_writes_nothing(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-2841")
        monkeypatch.setattr(arm, "load_definitions", _synthetic_definitions)
        monkeypatch.setattr(arm, "RESULTS_DIR", tmp_path / "zeroshot")
        called = []

        async def _no_call(*a, **k):
            called.append(1)
            raise AssertionError("dry-run must not call the network")

        monkeypatch.setattr(arm, "call_zeroshot", _no_call)
        rc = await arm.run_arm(["--dry-run"])
        assert rc == 0
        assert not called
        assert not (tmp_path / "zeroshot").exists()


class TestOutputDiscipline:
    """The answers land under the gitignored results tree, with the
    provenance header the render will cite (#2353)."""

    def test_results_dir_is_gitignored(self):
        import subprocess

        rc = subprocess.run(
            ["git", "check-ignore", str(arm.RESULTS_DIR)],
            capture_output=True,
            text=True,
            cwd=str(arm.REPO_ROOT),
        )
        assert rc.returncode == 0, (
            f"{arm.RESULTS_DIR} is not gitignored — answers of the corpus "
            "must never leave the machine via git"
        )

    def test_provenance_header_names_producer_and_command(self):
        header = arm.provenance_header("m", "https://gw.example/v1", 0)
        assert "run_zeroshot_arm.py" in header["producer"]
        assert "run_zeroshot_arm.py" in header["command"]
        assert header["max_chars"] == 0
        assert header["base_url_host"] == "gw.example"
