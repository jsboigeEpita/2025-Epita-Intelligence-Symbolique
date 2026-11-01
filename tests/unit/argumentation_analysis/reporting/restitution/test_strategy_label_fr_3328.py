"""#3328 leg 2 — the strategy data channel prints a known label, never free English.

``counter_arguments[].strategy`` is free agent text. Measured on this seat's
stored states: 3739 labels across 183 states, of which **1** carries an enum
value (``CounterArgumentType``/``RhetoricalStrategy``) and 89 carry the English
word "rebuttal" — e.g. « Burden of rebuttal », the exact label the coordinator
read in 20 of 35 dossiers. Before this fix, every reader surface printed that
raw text: the dossier line said ``strategy=Burden of rebuttal``, Act II
rendered « Contre-argument (Burden of rebuttal) », Act III wrote
« Pour contrer arg_1 (Burden of rebuttal) ».

The repair maps a KNOWN enum value to its French name and prints nothing for
free text — an unmapped label renders as an absence, not as English prose on a
French reader surface.

Every fixture here is synthetic: opaque ids (arg_1, ca_1) and invented filler
text. Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.counter_argument.definitions import (
    strategy_label_fr,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _strategy_suffix,
)

#: A measured free-text label from this seat's stored states — quoted, never
#: invented here. The word "rebuttal" is what 89 of 3739 labels carry.
_FREE_EN = "Burden of rebuttal"


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={"arg_1": "claim alpha asserted early"},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores={},
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _counter(strategy: str) -> list:
    return [
        {
            "id": "ca_1",
            "strategy": strategy,
            "score": 0.5,
            "counter_content": "invented filler alpha",
            "target_arg_id": "arg_1",
        }
    ]


def _dossier_line(briefing: str) -> str:
    lines = [
        ln
        for ln in briefing.splitlines()
        if ln.startswith("[artifact:counter_arguments.ca_1]")
    ]
    assert lines, "the dossier must carry the counter line"
    return lines[0]


# ============================================================================
# The shared mapping — what a label may become
# ============================================================================


class TestStrategyLabelFr:
    def test_every_known_value_has_a_french_name(self):
        known = {
            "direct_refutation": "réfutation directe",
            "counter_example": "contre-exemple",
            "alternative_explanation": "explication alternative",
            "premise_challenge": "contestation des prémisses",
            "reductio_ad_absurdum": "raisonnement par l'absurde",
            "socratic_questioning": "questionnement socratique",
            "analogical_counter": "contre-analogie",
            "authority_appeal": "appel à l'autorité",
            "statistical_evidence": "preuve statistique",
        }
        for raw, fr in known.items():
            assert strategy_label_fr(raw) == fr, raw

    def test_free_text_maps_to_the_empty_string(self):
        """3738 of 3739 measured labels: the mapping must yield absence, not
        the raw label and not a guessed translation."""
        assert strategy_label_fr(_FREE_EN) == ""
        assert strategy_label_fr("une stratégie libre en français") == ""

    def test_none_and_blank_stay_absent(self):
        assert strategy_label_fr("") == ""
        assert strategy_label_fr("   ") == ""

    def test_a_padded_enum_value_still_maps(self):
        assert strategy_label_fr("  direct_refutation  ") == "réfutation directe"


# ============================================================================
# The dossier line — the writer's input (deep_synthesis_agent)
# ============================================================================


class TestTheDossierLine:
    def _line(self, strategy: str) -> str:
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(counter_arguments=_counter(strategy))
        )
        return _dossier_line(briefing)

    def test_free_english_never_reaches_the_line(self):
        line = self._line(_FREE_EN)
        assert "Burden" not in line, (
            f"free agent text reached the dossier line: {line!r}"
        )

    def test_an_unmapped_strategy_renders_no_segment(self):
        line = self._line(_FREE_EN)
        assert "strategy=" not in line, (
            f"an unmapped label printed a strategy segment: {line!r}"
        )

    def test_the_evidence_itself_survives(self):
        """Anti-pendulum: dropping the label is not dropping the counter."""
        line = self._line(_FREE_EN)
        assert "invented filler alpha" in line
        assert "target=arg_1" in line
        assert "score=0.5" in line

    def test_a_known_value_prints_its_french_name(self):
        line = self._line("direct_refutation")
        assert "strategy=réfutation directe" in line
        assert "direct_refutation" not in line


# ============================================================================
# The Act II render — « Contre-argument (…) : … »
# ============================================================================


class TestTheActTwoRender:
    def _prompt(self, strategy: str) -> str:
        return build_act2_prompt(
            build_act2_evidence(_state(counter_arguments=_counter(strategy)))
        )

    def test_free_english_never_reaches_the_render(self):
        prompt = self._prompt(_FREE_EN)
        assert "Burden" not in prompt, "free agent text reached the Act II render"

    def test_the_counter_line_itself_still_renders(self):
        """Anti-pendulum: the counter stays evidence, only the label goes."""
        prompt = self._prompt(_FREE_EN)
        assert "Contre-argument" in prompt
        assert "invented filler alpha" in prompt

    def test_a_known_value_prints_its_french_name(self):
        prompt = self._prompt("counter_example")
        assert "Contre-argument (contre-exemple)" in prompt


# ============================================================================
# The Act III suffix — « Pour contrer arg_1 (…) : … »
# ============================================================================


class TestTheActThreeSuffix:
    def test_free_english_renders_no_parenthetical(self):
        assert _strategy_suffix(_FREE_EN) == ""

    def test_a_known_value_renders_its_french_name(self):
        assert _strategy_suffix("authority_appeal") == " (appel à l'autorité)"

    def test_empty_stays_an_absence(self):
        """#1668 control: an empty strategy renders as nothing, not ()."""
        assert _strategy_suffix("") == ""
        assert _strategy_suffix("   ") == ""
