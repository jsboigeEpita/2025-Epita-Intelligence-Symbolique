# tests/unit/argumentation_analysis/orchestration/test_degraded_ledger_1749.py
"""#1749 — the THIRD capability state must survive the reader hop.

The pipeline renders three capability states — ``used`` / ``degraded`` /
``missing``. The comparison harness read only two, so a capability that RAN
and returned nothing (``degraded=True``) appeared in neither list: a reader
counted "14 used / 0 missing" and concluded full coverage on a run that was
wrong by exactly one capability.

The producer is CORRECT and says so: ``_collect_degraded_capabilities``
(``unified_pipeline.py:55-99``) removes degraded capabilities from
``capabilities_used`` *deliberately* — "so a degraded capability surfaces as
degraded, NOT as ``used`` (anti-theater #1019)" — and emits the third list
alongside. The loss is at the READER hop, which is why these tests pin the
TRAVERSAL (producer dict -> ``ModeResult`` -> report) and never the presence
of the field at the producer (already covered by ``test_unified_pipeline.py``).

Measured shapes (R810, on ``main``), which decide who may claim a ledger:

===========================  =====  ========  =======
runner                       used   degraded  missing
===========================  =====  ========  =======
pipeline                     yes    yes       yes
conversational               yes    yes       yes
hierarchical_bridge          no     no        no
hierarchical_delegation      no     no        no
conversation_deterministic   no     no        no
===========================  =====  ========  =======

Hence the ``None`` vs ``[]`` convention (same as CG #1540): ``None`` = "this
mode emits no ledger" -> ``n/a``; ``[]`` = "ledger emitted, nothing degraded"
-> ``0``. An absent ledger is not an empty one.

JVM/LLM-free: the orchestrators are patched at their definition site.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_PROJECT_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compare_orchestration_modes as harness  # noqa: E402


def _drive_pipeline(producer_result: dict) -> harness.ModeResult:
    """Push a producer dict through the REAL pipeline runner (hop 1)."""

    async def fake_run(**kwargs):
        return producer_result

    async def _go():
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline"
            ".run_unified_analysis",
            side_effect=fake_run,
        ):
            return await harness.run_pipeline_mode("text", "corpus_A", "standard")

    return asyncio.run(_go())


def _drive_conversational(producer_result: dict) -> harness.ModeResult:
    """Push a producer dict through the REAL conversational runner (hop 1)."""

    async def fake_run(**kwargs):
        return producer_result

    async def _go():
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            ".run_conversational_analysis",
            side_effect=fake_run,
        ):
            return await harness.run_conversational_mode("text", "corpus_A")

    return asyncio.run(_go())


class TestDegradedLedgerTraversesTheReaderHop:
    """A capability that ran degraded must be NAMED, end to end.

    These are the tests that go red before the fix. Each one pins a distinct
    hop, so a partial fix cannot make all of them green.
    """

    def test_producer_declared_degradation_reaches_the_artefact(self) -> None:
        """The whole traversal, with NO reference to the new field.

        This is the control that proves the DEFECT rather than the newness of
        a field: every other test here names ``capabilities_degraded`` on
        ``ModeResult``, so before the fix they fail on a missing kwarg — which
        demonstrates only that the attribute does not exist yet. This one feeds
        the runner a producer dict of exactly the shape ``unified_pipeline``
        already emits today, runs the real reader chain (runner ->
        ``ModeResult`` -> report), and requires the capability's NAME to come
        out the far end.

        ⚠ It deliberately does NOT compare two reports for inequality. That
        was the first draft, and it was an assertion that cannot fail:
        ``generate_report`` stamps ``Generated: {datetime.now().isoformat()}``
        (``:1701``), so two reports built from *identical* input are already
        unequal — measured. Such a control is green for any inputs whatsoever.
        """
        report = harness.generate_report(
            [
                _drive_pipeline(
                    {
                        "summary": {"completed": 15, "total": 15},
                        "state_snapshot": {"fallacy_count": 10},
                        "capabilities_used": ["hierarchical_fallacy_detection"],
                        "capabilities_degraded": ["neural_fallacy_detection"],
                        "capabilities_missing": [],
                    }
                )
            ]
        )
        assert "neural_fallacy_detection" in report, (
            "#1749: the producer declared a capability as degraded and the "
            "artefact never mentions it. A reader counts 1 used / 0 missing "
            "and concludes full coverage on a run that was wrong by exactly "
            "one capability — the instrument that exists to detect this defect "
            "elsewhere is blind to it in its own output."
        )

    def test_pipeline_runner_carries_the_degraded_ledger(self) -> None:
        """Hop 1a: producer dict -> ``ModeResult`` (pipeline)."""
        result = _drive_pipeline(
            {
                "summary": {"completed": 15, "total": 15},
                "state_snapshot": {"fallacy_count": 10, "argument_count": 4},
                "capabilities_used": ["hierarchical_fallacy_detection"],
                "capabilities_degraded": ["neural_fallacy_detection"],
                "capabilities_missing": [],
            }
        )
        assert result.capabilities_degraded == ["neural_fallacy_detection"], (
            "#1749: the pipeline runner dropped ``capabilities_degraded``. A "
            "capability that RAN and returned nothing is in neither ``used`` "
            "nor ``missing`` — dropping the third list makes it invisible, and "
            "the report then claims full coverage on a truncated ledger."
        )

    def test_conversational_runner_carries_the_degraded_ledger(self) -> None:
        """Hop 1b: producer dict -> ``ModeResult`` (conversational).

        The defect blinds BOTH ledger-emitting modes, so both runners need the
        control — fixing only the pipeline would leave the conversational row
        silently truncated.
        """
        result = _drive_conversational(
            {
                "phases": ["a", "b"],
                "state_snapshot": {},
                "conversation_log": [],
                "capabilities_used": ["fact_extraction"],
                "capabilities_degraded": ["formal_translation"],
                "capabilities_missing": [],
            }
        )
        assert result.capabilities_degraded == ["formal_translation"], (
            "#1749: the conversational runner dropped ``capabilities_degraded`` "
            f"(got {result.capabilities_degraded!r})."
        )

    def test_report_names_the_degraded_capability(self) -> None:
        """Hop 2: ``ModeResult`` -> report. The DoD's literal requirement.

        Not "a degraded count appears" — the NAME must appear, because the
        corrective action differs per capability (configure an endpoint vs
        wire a provider).
        """
        report = harness.generate_report(
            [
                harness.ModeResult(
                    mode="pipeline_standard",
                    corpus_id="corpus_A",
                    success=True,
                    duration_seconds=1.0,
                    phases_completed=15,
                    phases_total=15,
                    capabilities_used=["hierarchical_fallacy_detection"],
                    capabilities_degraded=["neural_fallacy_detection"],
                    capabilities_missing=[],
                    scope_of_work="pipeline",
                ),
            ]
        )
        assert "neural_fallacy_detection" in report, (
            "#1749: the degraded capability is not named anywhere in the "
            "report. It ran and produced nothing; a reader of this artefact "
            "cannot see that."
        )

    def test_report_shows_the_three_states_together(self) -> None:
        """The third list is rendered BESIDE the other two, same visibility.

        "14 used / 1 degraded / 0 missing" is readable; "14 used / 0 missing"
        with a footnote is not — that is how the state got lost in the first
        place.
        """
        report = harness.generate_report(
            [
                harness.ModeResult(
                    mode="pipeline_standard",
                    corpus_id="corpus_A",
                    success=True,
                    duration_seconds=1.0,
                    phases_completed=15,
                    phases_total=15,
                    capabilities_used=["a", "b"],
                    capabilities_degraded=["c"],
                    capabilities_missing=[],
                    scope_of_work="pipeline",
                ),
            ]
        )
        assert "2 used / 1 degraded / 0 missing" in report, (
            "#1749: the three capability states are not rendered together as a "
            "single ledger line. Found instead:\n"
            + "\n".join(ln for ln in report.splitlines() if "used" in ln)
        )


class TestAbsentLedgerIsNotAnEmptyLedger:
    """DoD item 3 — a mode that emits NO ledger renders ``n/a``, never ``0``.

    Same convention as CG #1540 / #1740: a value read from an absent field is
    indistinguishable from a measured zero unless the two render differently.
    ``hierarchical_bridge`` / ``hierarchical_delegation`` /
    ``conversation_deterministic`` emit none of the three keys (measured on
    their return dicts), so "0 degraded" would be a fabricated measurement.
    """

    def test_a_mode_with_no_ledger_renders_n_a(self) -> None:
        report = harness.generate_report(
            [
                harness.ModeResult(
                    mode="hierarchical_delegation",
                    corpus_id="corpus_A",
                    success=True,
                    duration_seconds=1.0,
                    phases_completed=4,
                    phases_total=5,
                    scope_of_work="delegation",
                ),
            ]
        )
        ledger_lines = [ln for ln in report.splitlines() if "capabilities" in ln]
        assert any("n/a" in ln for ln in ledger_lines), (
            "#1749 DoD-3: a mode emitting no capability ledger must render "
            "``n/a``, not a fabricated ``0 degraded``. Ledger lines found:\n"
            + "\n".join(ledger_lines)
        )
        assert not any(
            "0 degraded" in ln for ln in ledger_lines
        ), "#1749 DoD-3: ``0 degraded`` asserts a measurement never made here."

    def test_an_emitted_empty_ledger_renders_zero(self) -> None:
        """The counterpart control: ``[]`` really does mean "none degraded".

        Without this, "fix" could mean rendering ``n/a`` everywhere, which
        destroys the distinction rather than restoring it.
        """
        report = harness.generate_report(
            [
                harness.ModeResult(
                    mode="pipeline_standard",
                    corpus_id="corpus_A",
                    success=True,
                    duration_seconds=1.0,
                    phases_completed=15,
                    phases_total=15,
                    capabilities_used=["a"],
                    capabilities_degraded=[],
                    capabilities_missing=[],
                    scope_of_work="pipeline",
                ),
            ]
        )
        assert "1 used / 0 degraded / 0 missing" in report, (
            "#1749: an EMITTED empty ledger must read ``0 degraded`` — the "
            "mode looked and found none. Collapsing it to ``n/a`` loses the "
            "very distinction this issue restores."
        )


class TestTheThreeStatesStayDistinct:
    """Anti-pendule, transcribed as controls rather than prose.

    These stay GREEN before and after the fix. Without them, "correcting"
    #1749 could mean folding the third state into one of the other two — which
    is exactly the defect, with a different sign.
    """

    def test_degraded_is_not_folded_into_used(self) -> None:
        """Anti-pendule 1: a degraded capability must NOT count as used.

        The producer removes it from ``used`` on purpose (#1019). Putting it
        back would make the harness report theatre as coverage.
        """
        result = _drive_pipeline(
            {
                "summary": {"completed": 15, "total": 15},
                "state_snapshot": {},
                "capabilities_used": ["a"],
                "capabilities_degraded": ["degraded_one"],
                "capabilities_missing": [],
            }
        )
        assert "degraded_one" not in result.capabilities_used, (
            "#1749 anti-pendule: a degraded capability was folded back into "
            "``capabilities_used``. The producer excludes it deliberately."
        )

    def test_degraded_is_not_folded_into_missing(self) -> None:
        """Anti-pendule 2: "ran and returned nothing" != "no provider".

        The two call for opposite corrections (configure the environment vs
        wire a provider), so merging them destroys the actionable content.
        """
        result = _drive_pipeline(
            {
                "summary": {"completed": 15, "total": 15},
                "state_snapshot": {},
                "capabilities_used": ["a"],
                "capabilities_degraded": ["degraded_one"],
                "capabilities_missing": ["absent_one"],
            }
        )
        assert result.capabilities_missing == ["absent_one"], (
            "#1749 anti-pendule: the degraded capability leaked into "
            f"``capabilities_missing`` (got {result.capabilities_missing!r})."
        )
        assert "absent_one" not in (result.capabilities_degraded or []), (
            "#1749 anti-pendule: a missing capability leaked into the degraded "
            "ledger."
        )

    def test_a_producer_that_stops_emitting_degrades_to_n_a_not_zero(self) -> None:
        """The safe side, at the runner hop.

        If the producer ever stops emitting the key, the runner must land on
        ``None`` ("no ledger") rather than a ``[]`` default that would assert
        "looked, found none" — the phantom-key defect this file exists for.
        """
        result = _drive_pipeline(
            {
                "summary": {"completed": 15, "total": 15},
                "state_snapshot": {},
                "capabilities_used": ["a"],
                "capabilities_missing": [],
            }
        )
        assert result.capabilities_degraded is None, (
            "#1749: an absent ``capabilities_degraded`` key must yield None "
            "(renders ``n/a``), never a ``[]`` default that fabricates "
            f"'looked, found none'. Got {result.capabilities_degraded!r}."
        )
