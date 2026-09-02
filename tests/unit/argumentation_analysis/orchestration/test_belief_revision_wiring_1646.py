"""#1646 incr 3 — belief-revision producer/reader wiring (minimal-retraction).

The singular insight of belief revision (#1646 section A) is the **minimal
retraction** — the smallest set of beliefs whose removal restores consistency.
Incr 1 (``minimal_retractions``, MCS over python-sat) and incr 2
(``build_belief_base``, derives a genuinely-inconsistent CNF base from
fallacies) are merged as pure JVM-free functions. Incr 3 wires them end-to-end,
mirroring the bipolar pattern (#1645): the producer computes the insight
JVM-free and survives the honest-degraded path → the state writer carries it →
the Act III reader NAMES it → the privacy scrub opacifies the named beliefs.

Kill-set B (the reader-side naming promised by the incr-1/2 test header). The
insight algorithm itself stays pinned in ``test_belief_revision_insight_1646``.

Three producer states, never two (mirror ``test_bipolar_honest_degraded_1645``):
  - JVM absent ⇒ honest-absent: a degraded dict WITH the minimal-retraction
    insight (computed JVM-free), the phase continues. The insight no longer dies
    on the degraded path — the whole point of computing it JVM-free.
  - JVM up + handler/analysis raises ⇒ fail loud with the real cause.
  - JVM up success ⇒ the insight is attached to the Levi result.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch):
    """#1973: ``opaque_id`` has no default salt any more and raises without one.

    Every source this module feeds the scrubber is fabricated (see the module
    docstring), so a salt protects nothing here — it is pinned at the perimeter
    of the synthetic fixtures rather than provisioned as a CI secret. Two
    reasons, in that order: a repository secret makes the dependency invisible
    (green in CI, red on a fresh clone), and a root-scope ``autouse`` would
    disarm the #1973 fail-loud guard for the whole test environment, letting a
    future production path that forgets the salt pass green. Scoped to this
    module, the guard keeps its teeth everywhere else and
    ``test_opaque_id.py`` keeps asserting the raise.
    """
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1973")


_BRIDGE_BR = (
    "argumentation_analysis.agents.core.logic.belief_revision_handler."
    "BeliefRevisionHandler"
)
_JVM_STARTED = "argumentation_analysis.core.jvm_setup.is_jvm_started"


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _ctx() -> dict:
    """A context with 3 extracted arguments and ONE fallacy on arg_1.

    arg_1 ↔ arguments[0]. The fallacy negates it, so the belief base gains a
    ``[-1]`` clause alongside ``[1]`` — a real clash, cardinality 1 (insight
    B-1). Opaque synthetic claims (privacy).
    """
    return {
        "phase_extract_output": {
            "arguments": ["claim_alpha", "claim_beta", "claim_gamma"]
        },
        "phase_hierarchical_fallacy_output": {
            "fallacies": [{"type": "ad_hominem", "target_argument": "arg_1"}]
        },
    }


# ---------------------------------------------------------------------------
# State 1 — JVM absent ⇒ honest-absent degraded dict WITH the insight
# ---------------------------------------------------------------------------


class TestJvmAbsentIsHonestAbsentWithInsight:
    """JVM down: the producer returns a degraded dict (does NOT raise) AND the
    minimal-retraction insight — computed JVM-free — still reaches the state.
    Pre-fix the handler raised ``RuntimeError`` unconditionally, so the insight
    never survived the degraded path (the #1645/#1670 architecture defect)."""

    def test_returns_dict_not_raises(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        with patch(_BRIDGE_BR, side_effect=RuntimeError("no JVM")), patch(
            _JVM_STARTED, return_value=False
        ):
            result = _run(_invoke_belief_revision("text", _ctx()))

        assert isinstance(result, dict)
        assert result.get("degraded") is True
        assert result.get("absent_reason") == "jvm_not_started"

    def test_insight_survives_degraded_path_and_names_real_clash(self):
        """The minimal-retraction insight is computed JVM-free, so it is present
        in the degraded dict and reflects the planted fallacy (cardinality 1).
        This is the core #1646 wiring: the insight does not die on the path
        where the handler never runs."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        with patch(_BRIDGE_BR, side_effect=RuntimeError("no JVM")), patch(
            _JVM_STARTED, return_value=False
        ):
            result = _run(_invoke_belief_revision("text", _ctx()))

        mr = result["minimal_retraction"]
        assert mr["degraded"] is False  # the INSIGHT computed (jpype importable)
        assert mr["cardinality"] == 1  # the fallacy created a real clash
        # B-2: one fallacy on arg_1 yields ≥2 cardinal-1 retractions (drop the
        # belief OR drop its negation) — the non-unicity the reader names. The
        # multiplicity reaches the state, not just the cardinality.
        assert len(mr["options"]) >= 2
        # The retraction options name the clashing belief (alpha) or its negation.
        flat = {label for opt in mr["options"] for label in opt}
        assert any("alpha" in label for label in flat)

    def test_absent_dict_preserves_real_signal_not_relabeled(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        with patch(_BRIDGE_BR, side_effect=RuntimeError("no JVM")), patch(
            _JVM_STARTED, return_value=False
        ):
            result = _run(_invoke_belief_revision("text", _ctx()))

        assert "no JVM" in result.get("error", "")
        assert result.get("revised") == []  # tri-state: not computed under Levi


# ---------------------------------------------------------------------------
# State 2 — JVM up + handler failure ⇒ fail loud with the real cause
# ---------------------------------------------------------------------------


class TestJvmUpHandlerFailureFailsLoudRealCause:
    """JVM up but the handler/analysis raises ⇒ the failure is ours, not the
    environment's. Fail loud with the real cause (preserved via ``from e``),
    never relabeled 'install a JVM' (the #1634 fabrication)."""

    def test_raises_with_real_cause_not_relabeled(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        real_cause = TypeError("bad belief shape in revise")
        mock_handler = MagicMock()
        mock_handler.revise.side_effect = real_cause
        with patch(_BRIDGE_BR, return_value=mock_handler), patch(
            _JVM_STARTED, return_value=True
        ):
            with pytest.raises(RuntimeError) as exc_info:
                _run(_invoke_belief_revision("text", _ctx()))

        msg = str(exc_info.value)
        assert "TypeError" in msg
        assert "bad belief shape in revise" in msg
        # No environment relabel — the JVM is up.
        assert "JVM/Tweety required" not in msg
        assert "Install JVM" not in msg
        assert exc_info.value.__cause__ is real_cause


# ---------------------------------------------------------------------------
# State 3 — JVM up success ⇒ the insight is attached to the Levi result
# ---------------------------------------------------------------------------


class TestJvmUpAttachesInsight:
    """On the JVM-up path the Levi handler runs AND the minimal-retraction
    insight is attached to its result dict, so it reaches the state writer."""

    def test_jvm_up_result_carries_minimal_retraction(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        mock_handler = MagicMock()
        mock_handler.revise.return_value = {
            "method": "dalal",
            "original": ["a"],
            "revised": ["b"],
        }
        with patch(_BRIDGE_BR, return_value=mock_handler), patch(
            _JVM_STARTED, return_value=True
        ):
            result = _run(_invoke_belief_revision("text", _ctx()))

        assert result["method"] == "dalal"  # the Levi result survived
        mr = result["minimal_retraction"]
        assert mr["cardinality"] == 1  # the insight was attached too
        assert mr["degraded"] is False


# ---------------------------------------------------------------------------
# ImportError degrade of the insight (pysat / logic-cascade absent)
# ---------------------------------------------------------------------------


class TestInsightImportErrorDegradesHonestly:
    """If the insight computation itself is unavailable (missing pysat, or the
    logic/__init__ jpype cascade #1697), the producer degrades the INSIGHT
    honestly (cardinality -1) rather than the phase — the pipeline still
    returns a result. Monkeypatching the call-site attribute (not sys.modules)
    keeps the test hermetic — the R772 lesson."""

    def test_pysat_absent_degrades_insight_to_neg1(self, monkeypatch):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )
        import argumentation_analysis.agents.core.logic.belief_revision_insight as ins

        def _boom(_base):
            raise ImportError("simulated pysat absent")

        monkeypatch.setattr(ins, "minimal_retractions", _boom)
        with patch(_BRIDGE_BR, side_effect=RuntimeError("no JVM")), patch(
            _JVM_STARTED, return_value=False
        ):
            result = _run(_invoke_belief_revision("text", _ctx()))

        # The phase still returns (degraded dict); the insight itself degraded.
        assert result["degraded"] is True
        mr = result["minimal_retraction"]
        assert mr["degraded"] is True
        assert mr["cardinality"] == -1
        assert mr["options"] == []


# ---------------------------------------------------------------------------
# Bridge — the insight flows producer output → state entry
# ---------------------------------------------------------------------------


class TestBridgePersistsInsight:
    def test_writer_passes_minimal_retraction_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_belief_revision_to_state,
        )

        output = {
            "method": "dalal",
            "original": ["a"],
            "revised": ["b"],
            "minimal_retraction": {
                "cardinality": 1,
                "options": [["claim_alpha"]],
                "base_size": 4,
                "touched_count": 1,
                "degraded": False,
            },
        }
        state = MagicMock()
        _write_belief_revision_to_state(output, state, {})

        state.add_belief_revision_result.assert_called_once()
        # minimal_retraction is the 4th positional arg (mirrors add_bipolar_result
        # style — support_cycles/articulation_points are positional too).
        persisted_mr = state.add_belief_revision_result.call_args.args[3]
        assert persisted_mr["cardinality"] == 1

    def test_writer_passes_none_when_insight_absent(self):
        """A producer output without the insight (e.g. a pre-insight caller)
        stores None — honest, the reader then produces nothing."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_belief_revision_to_state,
        )

        state = MagicMock()
        _write_belief_revision_to_state(
            {"method": "dalal", "original": [], "revised": []}, state, {}
        )
        persisted_mr = state.add_belief_revision_result.call_args.args[3]
        assert persisted_mr is None


# ---------------------------------------------------------------------------
# Reader — the Act III prose NAMES the minimal retraction
# ---------------------------------------------------------------------------


def _state_with(mr):
    return SimpleNamespace(belief_revision_results=[{"minimal_retraction": mr}])


class TestBeliefRevisionFinding:
    def test_cardinality_one_unique_names_rupture_belief(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        # B-1: a SINGLE minimal retraction of cardinal 1 — one belief restores
        # consistency, and the reader NAMES it as the unique point of rupture.
        state = _state_with(
            {
                "cardinality": 1,
                "options": [["claim_alpha"]],
                "base_size": 4,
                "touched_count": 1,
                "degraded": False,
            }
        )
        finding = _belief_revision_finding(state)
        assert finding is not None
        assert finding.capability == "belief_revision"
        assert "une seule proposition" in finding.statement
        assert "alpha" in finding.statement  # the rupture belief is NAMED

    def test_non_unique_retraction_names_incompatibility(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        # B-2: TWO retractions of cardinal 1 restore consistency (alpha or its
        # negation). None is *the* minimal one — the base splits into two
        # incompatible but equally-minimal consistent worlds. This is the figure
        # no LLM produces (a single revised world is all a revision operator can
        # express), so it must reach the rendered conclusion by name. DoD #1646.
        state = _state_with(
            {
                "cardinality": 1,
                "options": [["claim_alpha"], ["¬claim_alpha"]],
                "base_size": 4,
                "touched_count": 2,
                "degraded": False,
            }
        )
        finding = _belief_revision_finding(state)
        assert finding is not None
        # The non-unicity is the headline, not folded into a generic rupture list.
        assert "pas de rétractation minimale unique" in finding.statement
        assert "incompatibles" in finding.statement
        assert "également minimaux" in finding.statement
        # The cardinality still appears (both options are cardinal 1).
        assert "cardinal 1" in finding.statement

    def test_cardinality_two_names_cardinal(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        state = _state_with(
            {
                "cardinality": 2,
                "options": [["claim_alpha", "claim_beta"]],
                "base_size": 5,
                "touched_count": 2,
                "degraded": False,
            }
        )
        finding = _belief_revision_finding(state)
        assert finding is not None
        assert "cardinal 2" in finding.statement

    def test_inert_contradiction_named_when_beliefs_survive(self):
        """B-3: when the retraction touches fewer beliefs than the base holds,
        the untouched beliefs survive — the contradiction is real but inert."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        # base of 4, only 1 ever touched → 3 survive → inert signal fires.
        state = _state_with(
            {
                "cardinality": 1,
                "options": [["claim_alpha"]],
                "base_size": 4,
                "touched_count": 1,
                "degraded": False,
            }
        )
        finding = _belief_revision_finding(state)
        assert finding is not None
        assert "inerte" in finding.statement or "confinée" in finding.statement

    def test_consistent_base_no_finding(self):
        """cardinality 0 (consistent base) ⇒ no finding (honest absence, #1019)."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        state = _state_with(
            {"cardinality": 0, "options": [[]], "base_size": 3, "touched_count": 0}
        )
        assert _belief_revision_finding(state) is None

    def test_degraded_insight_no_finding(self):
        """cardinality -1 (insight unavailable) ⇒ no finding (never fabricate)."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        state = _state_with(
            {"cardinality": -1, "options": [], "base_size": 0, "touched_count": 0}
        )
        assert _belief_revision_finding(state) is None

    def test_missing_insight_no_finding(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        state = SimpleNamespace(belief_revision_results=[{"method": "dalal"}])
        assert _belief_revision_finding(state) is None


# ---------------------------------------------------------------------------
# Privacy — the named belief labels are opacified on export
# ---------------------------------------------------------------------------


class TestSanitizeOpacifiesOptions:
    def test_options_opacified_counts_intact(self):
        from argumentation_analysis.evaluation.sanitize_state import sanitize_state

        state = {
            "belief_revision_results": [
                {
                    "method": "dalal",
                    "original": ["claim_alpha"],
                    "revised": ["claim_beta"],
                    "minimal_retraction": {
                        "cardinality": 1,
                        "options": [["claim_alpha"], ["¬claim_alpha"]],
                        "base_size": 4,
                        "touched_count": 2,
                        "degraded": False,
                    },
                }
            ]
        }
        out = sanitize_state(state)
        mr = out["belief_revision_results"][0]["minimal_retraction"]
        # The ints survive untouched (the structural signal).
        assert mr["cardinality"] == 1
        assert mr["base_size"] == 4
        assert mr["touched_count"] == 2
        # The named belief labels are opacified (no source prose leaks).
        flat = {label for opt in mr["options"] for label in opt}
        assert all("claim_alpha" not in label for label in flat)
        # ... and the topology survived (still 2 singleton options).
        assert len(mr["options"]) == 2
        assert all(len(opt) == 1 for opt in mr["options"])

    def test_options_opacified_roundtrip_structure(self):
        """A nested option (cardinality-2 retraction) opacifies each leaf but
        keeps the arity, so the reader-side structure survives export."""
        from argumentation_analysis.evaluation.sanitize_state import sanitize_state

        state = {
            "belief_revision_results": [
                {
                    "method": "dalal",
                    "original": [],
                    "revised": [],
                    "minimal_retraction": {
                        "cardinality": 2,
                        "options": [["claim_alpha", "claim_beta"]],
                        "base_size": 5,
                        "touched_count": 2,
                        "degraded": False,
                    },
                }
            ]
        }
        out = sanitize_state(state)
        opt = out["belief_revision_results"][0]["minimal_retraction"]["options"]
        assert len(opt) == 1 and len(opt[0]) == 2  # arity preserved
        assert all("claim_" not in leaf for leaf in opt[0])  # content opacified
