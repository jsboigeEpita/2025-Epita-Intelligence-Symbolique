"""#2927 — Section 4's fallacy count must not sum two detection classes blind.

Since #3027, ``_build_fallacy_diagnoses`` appends the self-hosted neural
detector's whole-text claims (no span, no argument anchor, key = a free-text
label) after the anchored hierarchical diagnoses (one per ``taxonomy_pk``).
The Section 4 headline rendered ``Fallacies: {len(report.fallacy_diagnoses)}``,
so a type named by both detectors was held twice, and neither the families
line nor the top-3 exemplars said which class a line came from.

The R1064 headline is "the distinct fallacy types the text exhibits". The two
channels share no reliable type-level key — the only common mapper,
``_fallacy_family``, is family-granular and heuristic (its own docstring says
it *re-derives* a family from free text) — so the honest repair is to SPLIT
the count, not to fuse it. These tests pin:

- the born-red witness: both channels non-empty, one family named by both —
  the count line carries the split, the families line separates anchored
  from claimed, and a top-3 neural entry says it is unanchored;
- the empty-neural-channel regression (every real run today): the Section 4
  lines stay byte-identical to the previous single-channel rendering;
- the producer marks the channel on the entry itself.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

from semantic_kernel import Kernel

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    ArgumentMapEntry,
    DeepSynthesisReport,
    FallacyDiagnosis,
)


def _report_with(diagnoses):
    """A minimal report whose Section 4 renders the given diagnoses."""
    report = DeepSynthesisReport()
    report.argument_map = [
        ArgumentMapEntry(
            arg_id="arg_1",
            description="Speaker_A asserts a causal chain without support.",
        )
    ]
    report.fallacy_diagnoses = diagnoses
    return report


def _anchored(fid, family, path):
    return FallacyDiagnosis(
        fallacy_id=fid,
        family=family,
        taxonomy_path=path,
        textual_span="a quoted span",
        commentary=f"{fid}: an anchored hierarchical justification, long enough.",
        impacted_args=["arg_1"],
    )


def _neural_claim(fid, label, family):
    return FallacyDiagnosis(
        fallacy_id=fid,
        family=family,
        taxonomy_path=f"fallacy/{family}/{label}",
        textual_span="",
        commentary=f"self_hosted_llm whole-text detection (confidence 0.90)",
        impacted_args=[],
        unanchored_claim=True,
    )


class TestSection4CountSplitsChannels2927:
    """#2927 — the count line splits anchored vs unanchored, never blind-sums."""

    @staticmethod
    def _run(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @classmethod
    def _prompt_for(cls, report):
        kernel = create_autospec(Kernel, instance=True)
        kernel.get_prompt_execution_settings_from_service_id = MagicMock(
            return_value=MagicMock()
        )
        invoke_capture = AsyncMock(return_value="## 1. C\n## 6. L")
        kernel.invoke_prompt = invoke_capture
        stub = SimpleNamespace(_llm_service_id="default", kernel=kernel)
        cls._run(DeepSynthesisAgent._llm_synthesis(stub, report))
        call_kwargs = invoke_capture.call_args
        return call_kwargs[1]["prompt"] if call_kwargs[1] else ""

    def test_both_channels_the_count_line_splits_and_never_blind_sums(self):
        """Born-red witness: a family named by BOTH detectors (Ad Hominem).

        The old line printed ``Fallacies: 3.`` — the sum of two classes, with
        Ad Hominem held twice. The repaired line must state the split.
        """
        report = _report_with(
            [
                _anchored("f1", "Ad Hominem", "fallacy/ad_hominem/abusive"),
                _anchored("f2", "Slippery Slope", "fallacy/slippery/generic"),
                _neural_claim("nn_1", "ad hominem", "Ad Hominem"),
            ]
        )
        prompt = self._prompt_for(report)
        assert "Fallacies: 3 (2 anchored + 1 unanchored neural claims)." in prompt
        # The families line separates the classes instead of fusing them.
        assert "Key fallacy families: Ad Hominem, Slippery Slope (anchored); " in prompt
        assert "Ad Hominem (unanchored claims)." in prompt
        # A top-3 exemplar from the neural channel says what it is.
        assert (
            "Fallacy: Ad Hominem (fallacy/Ad Hominem/ad hominem) "
            "[unanchored claim]:" in prompt
        )

    def test_empty_neural_channel_renders_the_legacy_lines(self):
        """Regression: with no claims, the Section 4 lines are byte-identical
        to the previous single-channel rendering (the case on every real run
        while #2130 answers 401)."""
        report = _report_with(
            [
                _anchored("f1", "Ad Hominem", "fallacy/ad_hominem/abusive"),
                _anchored("f2", "Slippery Slope", "fallacy/slippery/generic"),
            ]
        )
        prompt = self._prompt_for(report)
        assert "Fallacies: 2. " in prompt
        assert "unanchored neural claims" not in prompt
        assert "[unanchored claim]" not in prompt
        assert "(anchored)" not in prompt

    def test_only_claims_no_anchored(self):
        """Edge: a neural-only report still splits honestly — the anchored
        set renders 'none', the claims carry their own families."""
        report = _report_with([_neural_claim("nn_1", "faux dilemme", "presumption")])
        prompt = self._prompt_for(report)
        assert "Fallacies: 1 (0 anchored + 1 unanchored neural claims)." in prompt
        assert (
            "Key fallacy families: none (anchored); presumption (unanchored claims)."
            in prompt
        )


class TestProducerMarksTheChannel2927:
    """``_build_fallacy_diagnoses`` carries the channel on each entry."""

    def test_build_fallacy_diagnoses_marks_the_channels(self):
        state = UnifiedAnalysisState("A short discourse.")
        state.identified_fallacies = {
            "fallacy_1": {
                "type": "ad hominem",
                "justification": "attacks the person, not the thesis",
                "family": "Ad Hominem",
                "taxonomy_path": "fallacy/ad_hominem/abusive",
                "target_argument_id": "arg_1",
            }
        }
        state.neural_fallacy_scores = [
            {"id": "nn_1", "label": "ad hominem", "confidence": 0.9}
        ]
        entries = DeepSynthesisAgent._build_fallacy_diagnoses(state)
        assert [e.unanchored_claim for e in entries] == [False, True]
        # The default keeps every pre-existing constructor a hierarchical one.
        assert (
            FallacyDiagnosis(
                fallacy_id="x",
                family="f",
                taxonomy_path="p",
                textual_span="s",
                commentary="c",
            ).unanchored_claim
            is False
        )
