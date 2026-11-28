"""#3658 item 46h — every explicit completion cap must fit the time its call has.

46f fixed the acts' ceiling by deriving it from the ATTEMPT deadline the
transport applies (80 s at the acts' 180 s budget), and 46h does the same for
the first reading. Neither fix says what should keep the next cap honest, and
the defect is structural rather than local: a cap is a promise about how long a
generation may run, and ``PhaseBudgetTransport`` gives a call far less than its
phase's budget.

So this is the population witness — the father, not one sibling. It takes the
census of completion caps **from the code** (every ``*_MAX_TOKENS`` constant in
``invoke_callables``), maps each to the workflow phases whose calls carry it,
and requires, for each pairing, that a call spending the whole cap still
finishes inside the deadline the transport really applies to that phase. The
deadline is measured on the production seam (``tests.support.attempt_deadline``),
never re-computed here.

What is IN the population: a cap the code names and a declared phase whose call
sends it. What is OUT, and named rather than skipped:

- the route's INGRESS default (measured 4 096). ``stakes`` sends no cap and
  inherits it; it is not a constant of ours, so it has no row — it is checked
  in ``test_a_phase_with_no_explicit_cap_is_named_not_measured`` so it cannot
  vanish silently.
- a call site no workflow phase reaches: the DAG never runs it, so it has no
  deadline to violate. The cap census below still forces every constant to have
  at least one row, which is what keeps a new cap from escaping.

Born red on ``main`` on two pairings: the first reading (24 576 tokens against
an 80 s attempt) and ``historian`` (the shared 8 192 against the 50 s attempt a
120 s budget composes).

Seat free: doubles only, zero network, zero paid call.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pytest

from argumentation_analysis.orchestration import invoke_callables as ic
from argumentation_analysis.orchestration import workflows as wf
from tests.support.attempt_deadline import (
    PROMPT_ALLOWANCE_SECONDS,
    RATE_TOKENS_PER_SECOND,
    effective_deadline,
)

#: cap constant -> the phases whose calls carry it. The site is named so a
#: reader can re-derive the pairing; the census assertion below reddens when a
#: new ``*_MAX_TOKENS`` appears in the module and is not listed here.
CAP_PHASES: Dict[str, Tuple[str, ...]] = {
    # ``_invoke_extraction`` and the window planner (``nl_extraction``).
    "_EXTRACTION_MAX_TOKENS": ("extract",),
    # The shared ceiling: every persona call with no cap of its own
    # (``_build_persona_callable``) and every ``structured_arg_translator``
    # call site (bipolar, ABA, ASPIC+, setaf, weighted, DeLP, probabilistic,
    # social, epistemic/EAF, and the Dung attack derivation).
    "_PHASE_MAX_TOKENS": (
        "historian",
        "cross_passage_consistency",
        "coverage_review",
        "strategist",
        "bipolar",
        "aba_reasoning",
        "aspic_analysis",
        "setaf_reasoning",
        "weighted_reasoning",
        "delp_reasoning",
        "probabilistic",
        "social_reasoning",
        "dung_extensions",
    ),
    # The three acts: their own ceiling (46b, re-derived on the deadline in 46f).
    "_ACT_MAX_TOKENS": ("act1_framing", "act2_narrative", "act3_conclusion"),
    # The first reading's own cap (46d, re-derived on the deadline in 46h).
    "_FIRST_READING_MAX_TOKENS": ("first_reading",),
}

#: The workflows the panel may run; a phase is given the TIGHTEST budget any
#: of them declares for it, since the same cap rides all of them.
WORKFLOW_BUILDERS = (
    "build_standard_workflow",
    "build_spectacular_workflow",
    "build_full_workflow",
    "build_formal_extended_workflow",
)


def _phase_budgets() -> Dict[str, Optional[float]]:
    """phase name -> smallest declared budget across the workflows.

    ``None`` in the value means no workflow declares a budget for it, which is
    a real deadline too (the client default) — not "unknown".
    """
    budgets: Dict[str, Optional[float]] = {}
    for builder in WORKFLOW_BUILDERS:
        factory = getattr(wf, builder, None)
        if factory is None:  # a renamed builder must not look like "no phase"
            continue
        for phase in factory().phases:
            declared = None if phase.timeout_seconds is None else float(
                phase.timeout_seconds
            )
            if phase.name not in budgets:
                budgets[phase.name] = declared
            elif declared is not None:
                current = budgets[phase.name]
                budgets[phase.name] = (
                    declared if current is None else min(current, declared)
                )
    return budgets


def _cap_census() -> set:
    """Every completion cap the module names, read from the module itself."""
    return {name for name in dir(ic) if name.endswith("_MAX_TOKENS")}


def test_the_census_is_read_from_the_code_and_covers_every_cap():
    """A new ``*_MAX_TOKENS`` must be placed in a phase before it ships: the
    witness is only a population if nothing can join it silently."""
    census = _cap_census()
    assert census, "no completion cap found — the census read nothing"
    unmapped = sorted(census - set(CAP_PHASES))
    stale = sorted(set(CAP_PHASES) - census)
    assert not unmapped, (
        f"completion cap(s) with no phase mapped: {unmapped}. Name the phase "
        "whose calls carry each one in CAP_PHASES; a cap with no phase found "
        "is named, never skipped"
    )
    assert not stale, (
        f"CAP_PHASES names cap(s) the code no longer defines: {stale}"
    )


def test_every_mapped_phase_exists_in_a_workflow():
    """A renamed phase would otherwise turn its row into a silent pass."""
    budgets = _phase_budgets()
    missing = sorted(
        phase
        for phases in CAP_PHASES.values()
        for phase in phases
        if phase not in budgets
    )
    assert not missing, (
        f"phase(s) named by the cap census are in no workflow: {missing}"
    )


@pytest.mark.parametrize(
    ("cap_name", "phase"),
    [
        (cap_name, phase)
        for cap_name, phases in sorted(CAP_PHASES.items())
        for phase in phases
    ],
)
def test_a_call_that_spends_the_whole_cap_fits_the_attempt_deadline(
    cap_name: str, phase: str
):
    """The pairing 46f applied to the acts and 46h to the reading, applied to
    the whole population: generation + prompt handling <= the deadline the
    transport applies to that phase's attempt.

    A call that cannot finish inside the deadline does not stop on ``length``
    — the attempt expires, tenacity re-issues it (billed and discarded), and
    the phase can end empty with nothing naming the cause.
    """
    cap = getattr(ic, cap_name)
    budget = _phase_budgets()[phase]
    deadline = effective_deadline(budget)

    generation = cap / RATE_TOKENS_PER_SECOND
    spent = generation + PROMPT_ALLOWANCE_SECONDS
    assert spent <= deadline, (
        f"{cap_name}={cap} rides the {phase!r} phase (budget {budget}s, so an "
        f"attempt deadline of {deadline:.1f}s). Spending the whole cap takes "
        f"{generation:.1f}s at {RATE_TOKENS_PER_SECOND:.0f} tok/s, and with "
        f"{PROMPT_ALLOWANCE_SECONDS:.0f}s of prompt handling that is "
        f"{spent:.1f}s — {spent - deadline:.1f}s past the deadline. Such a "
        "call cannot stop on 'length': it expires, is retried, is billed "
        "twice, and the phase may end empty and unreported. Lower the cap or "
        "raise the phase's budget — one lever, named in the PR"
    )


def test_a_phase_with_no_explicit_cap_is_named_not_measured():
    """The known out-of-population case, named so it cannot vanish silently:
    ``stakes`` sends no cap and inherits the route's 4 096 ingress default.

    4 096 tokens is ~20 s at the measured rate; its 120 s budget composes a
    50 s attempt, so it fits — but this is stated on purpose, not assumed, and
    the day ``stakes`` is given an explicit cap it joins the census above.
    """
    budgets = _phase_budgets()
    assert "stakes" in budgets, (
        "the 'stakes' phase is gone: either it was renamed (then update the "
        "note above) or it no longer runs"
    )
    ingress_default = 4_096
    spent = ingress_default / RATE_TOKENS_PER_SECOND + PROMPT_ALLOWANCE_SECONDS
    assert spent <= effective_deadline(budgets["stakes"])


def test_the_witness_is_not_vacuous():
    """Control: a population of one, or deadlines of zero, would pass the loop
    above for the wrong reason."""
    pairs = [(cap, phase) for cap, phases in CAP_PHASES.items() for phase in phases]
    assert len(pairs) >= 8, pairs
    assert len(CAP_PHASES) >= 4, sorted(CAP_PHASES)
    deadline = effective_deadline(_phase_budgets()["first_reading"])
    assert deadline > 0
    # the deadline BINDS: it is the composition, not the client's own timeout
    from argumentation_analysis.config.settings import settings

    assert deadline < settings.network.default_timeout, deadline
