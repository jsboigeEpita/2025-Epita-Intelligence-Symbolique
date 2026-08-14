# tests/unit/argumentation_analysis/orchestration/test_perimeter_aware_counts_1740.py
"""#1740 — a count whose PRODUCER never ran must not render as ``0``.

The comparison harness printed ``Fallacies: 0`` for ``pipeline_light``, whose
workflow carries **no fallacy capability at all**. That ``0`` meant "never
evaluated" and was numerically identical to "evaluated, found none" — the
#1019 family, inside the instrument that exists to detect it elsewhere.

The defect was NOT at the reader hop, where it had already been fixed three
times (#1528 item 3, #1540, #1560). Those fixes are correct: ``_fmt_count``
renders ``—`` for an absent key. They are also inert, because
``get_state_snapshot`` derives every count as ``len()`` over a *pre-declared*
container — so the key is never absent and the "absent → —" convention can
never fire on this field. The discriminator has to come from the **executed
perimeter** instead.

These tests are JVM/LLM-free: they build ``ModeResult`` objects directly and
introspect the real workflow builders.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_PROJECT_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compare_orchestration_modes as harness  # noqa: E402
from argumentation_analysis.orchestration.state_writers import (  # noqa: E402
    CAPABILITY_STATE_WRITERS,
)
from argumentation_analysis.orchestration.workflows import (  # noqa: E402
    build_light_workflow,
    build_standard_workflow,
)


def _result(mode: str, **kw) -> harness.ModeResult:
    """A minimal ModeResult; only the count/perimeter fields matter here."""
    base = dict(
        mode=mode,
        corpus_id="corpus_A",
        success=True,
        duration_seconds=1.0,
        phases_completed=1,
        phases_total=1,
    )
    base.update(kw)
    return harness.ModeResult(**base)


class TestTheDefectItself:
    """The exact row that started #1740."""

    def test_light_workflow_really_has_no_fallacy_capability(self) -> None:
        # Verify-before-assert: the premise is re-measured, never trusted.
        light_caps = {p.capability for p in build_light_workflow().phases}
        assert not (light_caps & harness._FALLACY_PRODUCING_CAPABILITIES)
        # ...and the contrast case does carry one, so the distinction is real.
        standard_caps = {p.capability for p in build_standard_workflow().phases}
        assert standard_caps & harness._FALLACY_PRODUCING_CAPABILITIES

    def test_pipeline_light_row_renders_na_not_zero(self) -> None:
        # The regression: a run that completed 3/3 phases, none of which can
        # produce a fallacy, must not report "0 fallacies found".
        row = _result(
            "pipeline_light",
            fallacy_count=0,
            argument_count=5,
            capabilities_used=[
                "fact_extraction",
                "argument_quality",
                "counter_argument_generation",
            ],
        )
        section = harness.generate_report([row])
        assert "| n/a |" in section, "fallacy count outside the perimeter must be n/a"
        assert "| 0 |" not in section, "a never-evaluated capability must not read 0"
        # The argument count IS in perimeter (fact_extraction ran) → real value.
        assert "| 5 |" in section


class TestThreeStatesNeverTwo:
    """``n/a`` / ``—`` / ``<int>`` must be mutually distinguishable."""

    def test_producer_ran_and_wrote_zero_still_reads_zero(self) -> None:
        # The state that MUST survive: a genuine, observed zero. If this
        # rendered n/a, the fix would have swung into the mirror-image defect.
        row = _result(
            "pipeline_standard",
            fallacy_count=0,
            capabilities_used=["fact_extraction", "neural_fallacy_detection"],
        )
        assert (
            harness._fmt_count_in_perimeter(
                row.fallacy_count,
                harness._FALLACY_PRODUCING_CAPABILITIES,
                row.capabilities_used,
            )
            == "0"
        )

    def test_producer_ran_but_nothing_written_reads_dash(self) -> None:
        assert (
            harness._fmt_count_in_perimeter(
                None,
                harness._FALLACY_PRODUCING_CAPABILITIES,
                ["neural_fallacy_detection"],
            )
            == "—"
        )

    def test_producer_absent_reads_na(self) -> None:
        assert (
            harness._fmt_count_in_perimeter(
                0, harness._FALLACY_PRODUCING_CAPABILITIES, ["fact_extraction"]
            )
            == "n/a"
        )

    def test_the_three_renderings_are_pairwise_distinct(self) -> None:
        caps = harness._FALLACY_PRODUCING_CAPABILITIES
        out_of_perimeter = harness._fmt_count_in_perimeter(0, caps, ["fact_extraction"])
        in_perimeter_unwritten = harness._fmt_count_in_perimeter(
            None, caps, ["neural_fallacy_detection"]
        )
        observed_zero = harness._fmt_count_in_perimeter(
            0, caps, ["neural_fallacy_detection"]
        )
        assert len({out_of_perimeter, in_perimeter_unwritten, observed_zero}) == 3


class TestUnknownPerimeterIsNotAnEmptyPerimeter:
    """The trap that would have made this fix a lie in the other direction."""

    def test_empty_capabilities_preserves_a_genuine_count(self) -> None:
        # conversation_deterministic reports NO perimeter and a real count of 2.
        # Treating "no perimeter reported" as "empty perimeter" would erase it.
        assert (
            harness._fmt_count_in_perimeter(
                2, harness._FALLACY_PRODUCING_CAPABILITIES, []
            )
            == "2"
        )

    def test_deterministic_row_keeps_its_count(self) -> None:
        row = _result("conversation_deterministic", fallacy_count=2, phases_completed=3)
        section = harness.generate_report([row])
        assert "| 2 |" in section
        # Cell form, not bare substring: the column legend also says "n/a".
        assert "| n/a |" not in section


class TestProducersPinnedAgainstTheRegistry:
    """The declared producer sets must not drift from the real capabilities."""

    def test_fallacy_producers_match_the_registry(self) -> None:
        # Derived, not hand-copied: whatever the registry calls a fallacy
        # capability is what the harness must treat as a fallacy producer.
        from_registry = {k for k in CAPABILITY_STATE_WRITERS if "fallacy" in k}
        assert from_registry == harness._FALLACY_PRODUCING_CAPABILITIES

    def test_argument_producer_is_a_real_registered_capability(self) -> None:
        assert harness._ARGUMENT_PRODUCING_CAPABILITIES <= set(CAPABILITY_STATE_WRITERS)


class TestDeprecatedAliasExcludedFromDefaultSweep:
    """The alias emitted rows indistinguishable from the real bridge."""

    def test_default_sweep_excludes_the_alias(self) -> None:
        assert "hierarchical" not in harness.default_modes()

    def test_alias_stays_dispatchable_on_demand(self) -> None:
        # Excluded from the default sweep, NOT removed — anyone who scripted
        # ``--modes hierarchical`` keeps working.
        assert "hierarchical" in harness.MODE_RUNNERS

    def test_default_sweep_has_no_duplicate_labels(self) -> None:
        # The baseline ran 24 instead of 21 because two keys produced rows
        # bearing the same label. Every default mode must be distinct.
        #
        # #1747: this used to read ``len(MODE_RUNNERS) - 1``, which encoded
        # "there is exactly ONE alias" as a magic constant — so the second
        # alias (``pipeline``, added for the same reason as ``hierarchical``)
        # turned a correct change into a red test. The property the assertion
        # means is that the default sweep is the runner set MINUS the aliases;
        # deriving it from ``_DEPRECATED_MODE_ALIASES`` states that property
        # and survives the next alias.
        modes = harness.default_modes()
        assert len(modes) == len(set(modes))
        assert len(modes) == len(harness.MODE_RUNNERS) - len(
            harness._DEPRECATED_MODE_ALIASES
        )
        assert (
            set(modes) == set(harness.MODE_RUNNERS) - harness._DEPRECATED_MODE_ALIASES
        )
