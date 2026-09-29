# -*- coding: utf-8 -*-
"""#2849 DoD 2 — the batch runner prints tokens per document and in total.

A dollar figure is printed only when the provider returned one; absence is
"not reported", never 0. Guards pin the three render functions of
``scripts/dataset/run_corpus_batch.py`` on synthetic usage dicts only (no
encrypted dataset, no LLM call).
"""

import importlib.util
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "dataset" / "run_corpus_batch.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("run_corpus_batch_2849", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRenderUsageLine:
    def test_tokens_and_phases_rendered(self):
        mod = _load_module()
        line = mod.render_usage_line(
            {
                "fact_extraction": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 200,
                    "calls": 3,
                },
                "fallacy": {"prompt_tokens": 500, "completion_tokens": 50, "calls": 2},
                "cost_usd": None,
            }
        )
        assert "1500 prompt" in line
        assert "250 completion" in line
        assert "5 call(s)" in line
        assert "2 phase(s)" in line
        assert "not reported" in line

    def test_dollar_rendered_only_when_reported(self):
        mod = _load_module()
        with_cost = mod.render_usage_line(
            {
                "p": {"prompt_tokens": 10, "completion_tokens": 1, "calls": 1},
                "cost_usd": 0.0123,
            }
        )
        without_cost = mod.render_usage_line(
            {
                "p": {"prompt_tokens": 10, "completion_tokens": 1, "calls": 1},
                "cost_usd": None,
            }
        )
        assert "$0.0123" in with_cost
        assert "0.0123" not in without_cost
        assert "not reported" in without_cost

    def test_absent_window_is_named_not_zeroed(self):
        mod = _load_module()
        line = mod.render_usage_line(None)
        assert "not measured" in line


class TestRenderUsageTotal:
    def test_total_sums_across_signatures_and_names_legacy(self):
        mod = _load_module()
        signatures = [
            {
                "llm_usage": {
                    "a": {"prompt_tokens": 100, "completion_tokens": 10, "calls": 1}
                }
            },
            {
                "llm_usage": {
                    "b": {"prompt_tokens": 50, "completion_tokens": 5, "calls": 1}
                }
            },
            # legacy signature from before #2849: no accounting field
            {"opaque_id": "legacy"},
        ]
        total = mod.render_usage_total(signatures)
        assert "150 prompt" in total
        assert "2 call(s)" in total
        assert "1 signature(s) without usage" in total

    def test_all_measured_total_has_no_legacy_tail(self):
        mod = _load_module()
        total = mod.render_usage_total(
            [
                {
                    "llm_usage": {
                        "a": {"prompt_tokens": 1, "completion_tokens": 1, "calls": 1}
                    }
                }
            ]
        )
        assert "without usage" not in total
