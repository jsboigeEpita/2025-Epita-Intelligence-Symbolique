"""The narrative-synthesis plugin's surviving surface, and the prose prompt.

#3266 retired the ``narrate_convergence`` kernel function (Track CC #636): it
had no production caller through the mounted path — ``_PLUGIN_REGISTRY`` builds
``NarrativeSynthesisPlugin`` with no argument, so ``_kernel`` was always
``None`` and every call returned the template behind a log line. The arbitrated
decision was to retire rather than wire, because wiring would have created a
second competing LLM surface with a silent fallback next to
``DeepSynthesisAgent.grounded_transversal_synthesis`` (fail-loud, #3264).

What this module holds is what still has a subject:

* ``_build_prose_prompt`` — **kept**, and not as a courtesy: it is the prompt a
  live path uses, ``DeepSynthesisAgent._llm_convergence_prose``
  (``deep_synthesis_agent.py:352``, #644). Deleting it would have made that
  import fail inside a broad ``except`` and silently degraded production to
  the template — green CI, quieter output.
* the two template kernel functions of the plugin, which the factory mounts.

The tests that exercised ``narrate_convergence`` itself (fallback, mocked
kernel, real-LLM integration) went with it.
"""

import json

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    NarrativeSynthesisPlugin,
    _build_prose_prompt,
    build_convergent_synthesis,
)


def _convergent_state() -> UnifiedAnalysisState:
    """State with arg_1 flagged by 3 independent methods (convergence score=3)."""
    state = UnifiedAnalysisState("Test discourse for LLM prose narration.")
    state.add_argument("A weak argument susceptible to multiple analytical methods.")
    # arg_2 is a silent, not-weak quality entry (per #1923 shape: 9 virtues,
    # sum 5.4 = fraction 0.6) — it spans the weak bar so the #1942 non-vacuity
    # gate lets "qualite faible" discriminate on arg_1.
    state.add_argument("A solid argument with measured strengths.")
    # Signal 1: fallacy targeting arg_1
    state.add_fallacy("straw_man", "Distortion of original position.", "arg_1")
    # Signal 2: low quality score (fraction 0.25)
    state.add_quality_score("arg_1", {f"vertu_{i}": 0.25 for i in range(9)}, 2.25)
    # Silent span: not-weak signal that opens the gate
    state.add_quality_score("arg_2", {f"vertu_{i}": 0.6 for i in range(9)}, 5.4)
    # Signal 3: counter-argument with target_arg_id
    state.add_counter_argument(
        "A weak argument susceptible to multiple analytical methods.",
        "This argument misrepresents the opposing view.",
        "reductio",
        0.8,
        "arg_1",
    )
    return state


class TestBuildProsePrompt:
    """_build_prose_prompt embeds grounded evidence in the prompt."""

    def test_contains_arg_id(self):
        """#3296: the convergence block names the unit by its per-act letter
        (the legend binds it) — the machine id no longer reaches the writer."""
        import re

        synthesis = build_convergent_synthesis(_convergent_state())
        prompt = _build_prose_prompt(synthesis)
        assert re.search(r"[α-ω]", prompt), "the unit is named by no letter"
        assert not re.search(r"arg_\d+", prompt)

    def test_contains_method_names(self):
        synthesis = build_convergent_synthesis(_convergent_state())
        prompt = _build_prose_prompt(synthesis)
        assert "sophisme" in prompt
        assert "qualite faible" in prompt

    def test_contains_structural_conclusion(self):
        """#3296: the conclusion rides the prompt verbatim, except that a
        unit id inside it rides as the same letter the evidence block uses —
        walk the fragments in order and the ids as letters."""
        import re

        synthesis = build_convergent_synthesis(_convergent_state())
        prompt = _build_prose_prompt(synthesis)
        pos = 0
        for part in re.split(r"(arg_\d+)", synthesis["conclusion"]):
            if not part:
                continue
            if re.fullmatch(r"arg_\d+", part):
                m = re.compile(r"[α-ω]+").search(prompt, pos)
                assert m, "the conclusion's unit reference is not a letter"
                pos = m.end()
            else:
                idx = prompt.find(part, pos)
                assert idx >= 0, f"conclusion fragment lost: {part!r}"
                pos = idx + len(part)

    def test_no_convergence_shows_placeholder(self):
        state = UnifiedAnalysisState("test")
        state.add_argument("strong arg")
        synthesis = build_convergent_synthesis(state)
        assert not synthesis["convergent_verdicts"]
        assert "no convergent" in _build_prose_prompt(synthesis).lower()

    def test_returns_str(self):
        synthesis = build_convergent_synthesis(_convergent_state())
        assert isinstance(_build_prose_prompt(synthesis), str)


class TestPluginSurface:
    """The class the factory mounts: two template functions, no constructor."""

    def test_construction_takes_no_argument(self):
        """#3266: the kernel parameter existed only for the retired prose layer.

        The mounted path never passed one, so the parameter was the thing that
        made the layer unreachable while looking wired.
        """
        plugin = NarrativeSynthesisPlugin()
        assert not hasattr(plugin, "_kernel")
        assert not hasattr(plugin, "narrate_convergence")

    def test_synthesize_still_works(self):
        result = NarrativeSynthesisPlugin().synthesize(state_json="{}")
        assert result, "synthesize produced an empty result"

    def test_convergent_synthesize_still_works(self):
        data = json.loads(NarrativeSynthesisPlugin().convergent_synthesize("{}"))
        assert "narrative" in data
        assert "convergent_verdicts" in data


@pytest.mark.parametrize("name", ["narrate_convergence"])
def test_the_retired_function_is_gone(name):
    """Guard against a silent re-introduction of the retired surface."""
    assert not hasattr(NarrativeSynthesisPlugin, name)
