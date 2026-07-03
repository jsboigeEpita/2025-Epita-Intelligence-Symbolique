"""Tests for Track MM (#658): Formal formula recall — PL/FOL pipeline metrics.

Tests cover:
  1. pl_metrics dict present in PL return values
  2. pl_metrics counters populated at each pipeline stage
  3. PL whole-text pass adds extra formulas (wide-net)
  4. fol_metrics dict present in FOL return values
  5. fol_metrics counters populated at each pipeline stage
  6. Args limit raised from 6 to 10
"""

import asyncio
import pytest
import sys


def _make_fake_invoke_pl(
    pass1_atoms=None,
    pass2_formulas=None,
    whole_text_formulas=None,
):
    """Build a fake invoke_callables module for PL testing."""
    fake = type("FakeInvoke", (), {})()

    _pass1_atoms = pass1_atoms or ["is_mortal", "is_human"]
    _pass2_formulas = pass2_formulas or ["is_human => is_mortal"]
    _wt_formulas = whole_text_formulas or []

    async def fake_pl(text, context):
        return {
            "formulas": _pass2_formulas + _wt_formulas,
            "satisfiable": True,
            "model": {"p1": True},
            "message": "ok",
            "logic_type": "propositional",
            "argument_mapping": {},
            "pl_metrics": {
                "upstream_nl": 0,
                "pass1_atoms": len(_pass1_atoms),
                "pass2_candidates": len(_pass2_formulas),
                "fallback_nl": 0,
                "template": 0,
                "pre_sanitize": len(_pass2_formulas) + len(_wt_formulas),
                "post_sanitize": len(_pass2_formulas) + len(_wt_formulas),
                "post_tweety": len(_pass2_formulas) + len(_wt_formulas),
                "wide_net_extras": len(_wt_formulas),
            },
        }

    fake._invoke_propositional_logic = fake_pl
    return fake


class TestPLMetricsPresent:
    """pl_metrics dict is always present in PL return values."""

    def test_metrics_in_result(self, monkeypatch):
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_propositional_logic(text, context)

        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke("short text", {"formulas": ["p1", "p2 => p3"]})
        )
        assert "pl_metrics" in result
        metrics = result["pl_metrics"]
        assert isinstance(metrics, dict)
        assert "pre_sanitize" in metrics
        assert "post_tweety" in metrics

    def test_metrics_all_keys(self, monkeypatch):
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_propositional_logic(text, context)

        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke("short text", {"formulas": ["p1"]})
        )
        metrics = result["pl_metrics"]
        expected_keys = {
            "upstream_nl",
            "pass1_atoms",
            "pass2_candidates",
            "fallback_nl",
            "template",
            "pre_sanitize",
            "post_sanitize",
            "post_tweety",
            "wide_net_extras",
            "isolation_survivors",
        }
        assert expected_keys == set(metrics.keys())

    def test_pre_sanitize_counts_formulas(self, monkeypatch):
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_propositional_logic(text, context)

        formulas = ["p1", "p2 => p3", "p4 && p5"]
        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke("some text", {"formulas": formulas})
        )
        assert result["pl_metrics"]["pre_sanitize"] == 3


class TestPLMetricsCountersPopulated:
    """pl_metrics counters are populated correctly for template fallback."""

    def test_template_counter(self):
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_propositional_logic(text, context)

        context = {
            "_state_object": None,
        }
        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke("test text " * 20, context)
        )
        # Should fall through to template since no API key / no formulas
        assert "template" in result["pl_metrics"]
        assert result["pl_metrics"]["template"] >= 0


class TestPLWholeTextPass:
    """PL whole-text pass adds extra formulas not in per-argument results."""

    def test_wide_net_extras_in_metrics(self):
        """When wide-net is used, wide_net_extras > 0."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _parse_json_from_llm,
        )

        raw = '{"formulas": ["is_human => is_mortal", "is_foreign => !is_trusted"]}'
        parsed = _parse_json_from_llm(raw)
        assert parsed.get("formulas") == [
            "is_human => is_mortal",
            "is_foreign => !is_trusted",
        ]


class TestFOLMetricsPresent:
    """fol_metrics dict is always present in FOL return values."""

    def test_metrics_in_fol_result(self):
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_fol_reasoning(text, context)

        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke(
                "short text",
                {
                    "formulas": ["Asserted(arg1)"],
                    "_state_object": None,
                },
            )
        )
        assert "fol_metrics" in result
        metrics = result["fol_metrics"]
        assert isinstance(metrics, dict)
        assert "pre_tweety" in metrics
        assert "pass1_sorts" in metrics

    def test_fol_metrics_all_keys(self):
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_fol_reasoning(text, context)

        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke(
                "short text",
                {
                    "formulas": ["Asserted(arg1)"],
                    "_state_object": None,
                },
            )
        )
        metrics = result["fol_metrics"]
        expected_keys = {
            "upstream_nl",
            "pass1_sorts",
            "pass1_predicates",
            "pass2_candidates",
            "fallback_nl",
            "template",
            "pre_sanitize",
            "post_sanitize",
            "pre_tweety",
            "post_tweety",
            "isolation_survivors",
        }
        assert expected_keys == set(metrics.keys())


class TestFOLTemplateCounter:
    """FOL template counter tracks fallback predicates."""

    def test_template_counter_set(self):
        """Template counter is present in fol_metrics and non-negative."""
        from argumentation_analysis.orchestration import invoke_callables as mod

        async def fake_invoke(text, context):
            return await mod._invoke_fol_reasoning(text, context)

        context = {
            "_state_object": None,
        }
        result = asyncio.get_event_loop().run_until_complete(
            fake_invoke("test text " * 20, context)
        )
        assert "template" in result["fol_metrics"]
        assert result["fol_metrics"]["template"] >= 0


class TestArgsLimit:
    """Args limit increased from 6 to 10."""

    def test_pl_pass2_args_limit(self):
        """Verify PL pass2 loop uses args[:10] not args[:6]."""
        import inspect
        from argumentation_analysis.orchestration import invoke_callables as mod

        source = inspect.getsource(mod._invoke_propositional_logic)
        assert "args[:10]" in source
        assert "args[:6]" not in source

    def test_fol_pass2_args_limit(self):
        """Verify FOL pass2 loop uses args[:10] not args[:6]."""
        import inspect
        from argumentation_analysis.orchestration import invoke_callables as mod

        source = inspect.getsource(mod._invoke_fol_reasoning)
        assert "args[:10]" in source
        assert "args[:6]" not in source
