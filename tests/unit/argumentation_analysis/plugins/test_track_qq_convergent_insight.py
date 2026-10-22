"""Tests for Track QQ (#667): Convergent insight paragraph.

Tests cover:
  1. _build_substantive_insight produces structured paragraph for >=3 methods
  2. build_convergent_synthesis uses substantive insight for >=3, standard for <3
  3. Insight is anchored in actual signals, not generic
  4. LLM prose prompt includes substantive conclusion instruction
"""

import pytest

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    _build_substantive_insight,
    build_convergent_synthesis,
    _build_prose_prompt,
)


def _make_state_with_convergence(verdicts: dict) -> object:
    """Create a mock state with compute_argument_convergence-style data."""

    class MockState:
        pass

    state = MockState()
    # build_convergent_synthesis calls compute_argument_convergence which reads
    # from state attributes. We patch via monkeypatch in tests that need it.
    state.identified_arguments = {}
    state.identified_fallacies = {}
    state.quality_scores = {}
    state.counter_arguments = {}
    state.jtms_beliefs = []
    state.dung_framework = {}
    state.belief_revision_results = {}
    return state


class TestBuildSubstantiveInsight:
    """_build_substantive_insight produces structured paragraph."""

    def test_basic_3_method_insight(self):
        result = _build_substantive_insight(
            "arg_1",
            3,
            [
                "detection rhetorique (Post hoc)",
                "score de qualite (0.32)",
                "argumentation abstraite (Dung/rejected)",
            ],
            [
                "la detection rhetorique a identifie un probleme (Post hoc)",
                "le scoring de qualite signale une faiblesse (0.32)",
                "l'analyse argumentative abstraite (Dung) rejette l'argument (rejected)",
            ],
            [],
        )
        assert "**Insight convergent sur arg_1**" in result
        assert "3 methodes independantes" in result
        assert "sur-determinee" in result
        assert "detection rhetorique" in result
        assert "score de qualite" in result
        assert "Dung" in result
        assert "insight emergent" in result

    def test_4_method_insight_cites_jtms_never_counts_it(self):
        # #3145: a 4-method insight lists four INDEPENDENT phrases; the JTMS
        # retraction rides in the cited tail — visible, labelled derived,
        # never among the concurring methods.
        result = _build_substantive_insight(
            "arg_3",
            4,
            [
                "detection rhetorique (Ad hominem)",
                "score de qualite (0.25)",
                "contre-argumentation",
                "argumentation abstraite (Dung/attacked)",
            ],
            [
                "la detection rhetorique a identifie un probleme (Ad hominem)",
                "le scoring de qualite signale une faiblesse (0.25)",
                "un contre-argument solide a ete oppose",
                "l'analyse argumentative abstraite (Dung) rejette l'argument (attacked)",
            ],
            [
                "le systeme de maintenance de verite (JTMS) a retracte la "
                "croyance associee — derive du sophisme, pas un temoin "
                "independant"
            ],
        )
        assert "4 methodes independantes" in result
        concur, _, tail = result.partition("Par ailleurs")
        assert "JTMS" not in concur
        assert "JTMS" in tail
        assert "retracte" in tail

    def test_includes_counter_argument(self):
        result = _build_substantive_insight(
            "arg_5",
            3,
            [
                "detection rhetorique (Non sequitur)",
                "contre-argumentation",
                "argumentation abstraite (Dung/defeated)",
            ],
            [
                "la detection rhetorique a identifie un probleme (Non sequitur)",
                "un contre-argument solide a ete oppose",
                "l'analyse argumentative abstraite (Dung) rejette l'argument (defeated)",
            ],
            [],
        )
        assert "contre-argument" in result

    def test_insight_not_generic(self):
        """Insight must reference actual signal details, not be a template."""
        result = _build_substantive_insight(
            "arg_1",
            3,
            [
                "detection rhetorique (Post hoc)",
                "score de qualite (0.32)",
                "argumentation abstraite (Dung/rejected)",
            ],
            [
                "la detection rhetorique a identifie un probleme (Post hoc)",
                "le scoring de qualite signale une faiblesse (0.32)",
                "l'analyse argumentative abstraite (Dung) rejette l'argument (rejected)",
            ],
            [],
        )
        # Must contain specific signal details
        assert "Post hoc" in result
        assert "0.32" in result
        assert "rejected" in result


class TestBuildConvergentSynthesisInsight:
    """build_convergent_synthesis uses substantive insight for >=3 methods."""

    def test_substantive_for_3plus(self, monkeypatch):
        """Verdicts with score >= 3 get substantive insight."""
        convergence_data = {
            "arg_1": {
                "score": 3,
                "signals": [
                    ("sophisme", "Post hoc"),
                    ("qualite faible", "0.3"),
                    ("rejet Dung", "rejected"),
                ],
                # #3145 shape: the synthesis reads the independent/cited
                # partition fail-loud — monkeypatched data carries it.
                "independent_signals": [
                    ("sophisme", "Post hoc"),
                    ("qualite faible", "0.3"),
                    ("rejet Dung", "rejected"),
                ],
                "cited_signals": [],
            },
        }
        monkeypatch.setattr(
            "argumentation_analysis.plugins.narrative_synthesis_plugin.compute_argument_convergence",
            lambda state: convergence_data,
        )
        state = _make_state_with_convergence({})
        result = build_convergent_synthesis(state)
        insights = result["emergent_insights"]
        assert len(insights) == 1
        assert "sur-determinee" in insights[0]

    def test_standard_for_2(self, monkeypatch):
        """Verdicts with score 2 get standard (non-substantive) insight."""
        convergence_data = {
            "arg_1": {
                "score": 2,
                "signals": [
                    ("sophisme", "Post hoc"),
                    ("qualite faible", "0.3"),
                ],
                "independent_signals": [
                    ("sophisme", "Post hoc"),
                    ("qualite faible", "0.3"),
                ],
                "cited_signals": [],
            },
        }
        monkeypatch.setattr(
            "argumentation_analysis.plugins.narrative_synthesis_plugin.compute_argument_convergence",
            lambda state: convergence_data,
        )
        state = _make_state_with_convergence({})
        result = build_convergent_synthesis(state)
        insights = result["emergent_insights"]
        assert len(insights) == 1
        assert "sur-determinee" not in insights[0]
        assert "Verdict convergent" in insights[0]

    def test_mixed_scores(self, monkeypatch):
        """Mix of >=3 and <3 produces appropriate insight types."""
        convergence_data = {
            "arg_1": {
                "score": 3,
                "signals": [
                    ("sophisme", "X"),
                    ("qualite faible", "0.3"),
                    ("rejet Dung", "r"),
                ],
                "independent_signals": [
                    ("sophisme", "X"),
                    ("qualite faible", "0.3"),
                    ("rejet Dung", "r"),
                ],
                "cited_signals": [],
            },
            "arg_2": {
                "score": 2,
                "signals": [
                    ("sophisme", "Y"),
                    ("qualite faible", "0.4"),
                ],
                "independent_signals": [
                    ("sophisme", "Y"),
                    ("qualite faible", "0.4"),
                ],
                "cited_signals": [],
            },
        }
        monkeypatch.setattr(
            "argumentation_analysis.plugins.narrative_synthesis_plugin.compute_argument_convergence",
            lambda state: convergence_data,
        )
        state = _make_state_with_convergence({})
        result = build_convergent_synthesis(state)
        insights = result["emergent_insights"]
        assert len(insights) == 2
        # First is substantive (score 3)
        assert "Insight convergent" in insights[0]
        assert "sur-determinee" in insights[0]
        # Second is standard (score 2)
        assert "Verdict convergent" in insights[1]


class TestProsePromptSubstantive:
    """LLM prose prompt includes substantive conclusion instruction."""

    def test_prompt_mentions_substantive(self):
        synthesis = {
            "convergent_verdicts": {
                "arg_1": {
                    "score": 3,
                    "signals": [("sophisme", "X"), ("qualite faible", "0.3")],
                },
            },
            "conclusion": "test",
        }
        prompt = _build_prose_prompt(synthesis)
        assert "SUBSTANTIVE CONCLUSION" in prompt
        assert "over-determined" in prompt

    def test_prompt_evidence_includes_3plus_methods(self):
        synthesis = {
            "convergent_verdicts": {
                "arg_1": {
                    "score": 3,
                    "signals": [
                        ("sophisme", "X"),
                        ("qualite faible", "0.3"),
                        ("rejet Dung", "r"),
                    ],
                },
            },
            "conclusion": "test",
        }
        prompt = _build_prose_prompt(synthesis)
        assert "3 methods" in prompt
