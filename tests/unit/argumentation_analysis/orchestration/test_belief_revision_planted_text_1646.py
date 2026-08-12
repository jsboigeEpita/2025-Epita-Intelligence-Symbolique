"""#1646 incr 4 — planted-text paired-run differentiation (the empirical DoD).

Incr 1/2/3 (merged) pin the belief-revision insight as:

* a pure JVM-free function — ``minimal_retractions`` / ``build_belief_base``
  (kill-set A, ``test_belief_revision_insight_1646``);
* the producer → bridge → reader → privacy wiring with **hand-injected state**
  (kill-set B, ``test_belief_revision_wiring_1646``).

What those tests do NOT prove, and what this file does, is the DoD's empirical
claim (issue #1646):

* « Texte planté écrit, différenciation mesurée sur run apparié » — on a
  **planted text** whose inconsistency is real but non-trivial (it emerges from
  a fallacy undermining a headlined proposition, NOT from "A and ¬A" two
  sentences apart), the insight FIRES through the same JVM-free chain the wired
  pipeline runs, and the differentiation against the pre-#1646 baseline is
  MEASURED, not asserted a priori.
* « Le cas "contradiction inerte" (insight 3) est testé explicitement » — the
  B-3 inert signal is DISCRIMINATING (it distinguishes two planted texts that a
  pure UNSAT oracle reads identically), not just always-on.

The chain under test (the insight-specific path, JVM-free by construction — the
#1645 lesson, restated in ``belief_revision_insight.py``)::

    planted args + fallacy-negated index
        → build_belief_base          # the producer's base construction (incr 2)
        → minimal_retractions        # the MCS computation (incr 1)
        → producer-shaped mr dict    # named options + touched_count (incr 3)
        → _belief_revision_finding   # the Act III reader NAMES it (incr 3)

The **baseline** is what the chain had before #1646: ``build_belief_base(args,
[])`` produced an all-positive base (``_pl_atom`` laundered the fallacy back to
a positive atom — the D-forensic Lock 1), which is trivially SAT, so
``minimal_retractions`` returned cardinal 0 and the reader was silent. A PL/UNSAT
oracle, available pre-#1646, returned a bare boolean. The paired run contrasts
the two arms on the SAME planted text.

Opaque synthetic claims only (privacy HARD): no corpus text, no source-derived
atoms — the labels are structural placeholders. No JVM, no API key.

Out of scope for incr 4 (planted-text), stated honestly:
* DoD item F « Corpus réel » — real-corpus runs are data-gated on ai-01 (same
  path as #1668). The R781 D/E forensic showed real-run bases are all-positive
  until a fallacy targets a headlined proposition; the planted text simulates
  exactly that trigger without needing the corpus.
* B-1 *unique* retraction (reader lead « une seule proposition suffit… » with a
  single option) — ``build_belief_base`` represents a fallacy as {[i], [-i]},
  which always yields ≥ 2 cardinal-1 retractions (drop the belief OR its
  negation), so the honest planted-text figure is B-2 (non-unique) + B-3 (inert).
  Forcing a degenerate single-option base to trip B-1 would be the #1019
  anti-pattern; B-1-unique stays covered by the injected-state wiring test.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Sequence, Tuple

from argumentation_analysis.agents.core.logic.belief_revision_insight import (
    build_belief_base,
    minimal_retractions,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _belief_revision_finding,
)

# ---------------------------------------------------------------------------
# Chain harness — mirrors the producer shaping (invoke_callables l.4204-4217)
# so the test exercises the REAL dict the wired pipeline stores, not a hand
# -built surrogate.
# ---------------------------------------------------------------------------


def _sat_oracle(base: List[List[int]]) -> bool:
    """The pre-#1646 PL signal: a bare satisfiability boolean (Glucose3, the
    same oracle ``minimal_retractions`` uses). This is ALL a UNSAT check gives
    you — no named belief, no cardinality, no survivor count."""
    from pysat.solvers import Glucose3

    if not base:
        return True
    with Glucose3(bootstrap_with=base) as solver:
        return bool(solver.solve())


def _insight_chain(
    args: Sequence[str], negated_indices: Sequence[int]
) -> Tuple[List[List[int]], List[str], Dict[str, Any]]:
    """Run the full JVM-free insight chain on a planted argument set.

    Returns ``(base, names, mr_dict)`` where ``mr_dict`` is shaped exactly as the
    producer shapes it (``invoke_callables._invoke_belief_revision`` l.4204-4217):
    cardinality, NAMED options (so the reader can name the rupture), base_size,
    and touched_count (which drives the B-3 inert signal).
    """
    base, names = build_belief_base(args, negated_indices)
    card, options = minimal_retractions(base)
    named_options = [[names[i] for i in opt] for opt in options]
    touched = len({i for opt in options for i in opt})
    mr = {
        "cardinality": card,
        "options": named_options,
        "base_size": len(base),
        "touched_count": touched,
        "degraded": False,
    }
    return base, names, mr


def _reader_finding(mr: Dict[str, Any]) -> Any:
    """Wrap the insight dict as the reader sees it (one state entry) and run the
    Act III reader — proving the insight reaches the conclusion prose."""
    state = SimpleNamespace(belief_revision_results=[{"minimal_retraction": mr}])
    return _belief_revision_finding(state)


# A planted multi-commitment discourse. claim_T is the headlined founding
# proposition; claim_a/b/c are supporting engagements, each plausible in
# isolation. Opaque synthetic labels (privacy HARD — no corpus text).
_PLANTED_ARGS = ["claim_T", "claim_a", "claim_b", "claim_c"]
_THESIS_IDX = 0  # the fallacy undermines the headlined thesis


# ---------------------------------------------------------------------------
# DoD: « Texte planté écrit, différenciation mesurée sur run apparié »
# ---------------------------------------------------------------------------


class TestPlantedTextPairedRun:
    """The paired run: SAME planted text, the only difference between arms is
    whether the fallacy-negation is wired (incr 2's ``build_belief_base``). The
    differentiation is measured against the pre-#1646 baseline (all-positive
    base, trivially SAT, reader silent) and against the UNSAT boolean (which
    carries no named belief / cardinality / survivors)."""

    def test_planted_text_is_non_trivially_inconsistent(self) -> None:
        """DoD C: the inconsistency is NOT "A and ¬A" two phrases apart. The
        text's commitments, taken at face value, are CONSISTENT — no adjacent
        pair contradicts. The inconsistency is brought SOLELY by the fallacy
        negating the thesis (the speaker asserts claim_T; the fallacy establishes
        claim_T is not tenable). That is the non-trivial emergence the DoD asks
        for, and it is measurable: the no-fallacy base is SAT, the fallacy base
        is UNSAT, on the same commitments."""
        # Face-value commitments (pre-#1646): consistent.
        base_face_value, _, _ = _insight_chain(_PLANTED_ARGS, [])
        assert _sat_oracle(base_face_value) is True  # no surface contradiction

        # Fallacy undermines the thesis: the conjunction becomes inconsistent.
        base_with_fallacy, _, _ = _insight_chain(_PLANTED_ARGS, [_THESIS_IDX])
        assert _sat_oracle(base_with_fallacy) is False  # real clash, non-trivial

    def test_paired_run_differentiation_pre_vs_post(self) -> None:
        """The paired measurement. Arm A (pre-#1646, no fallacy-negation): the
        base is all-positive → cardinal 0 → reader SILENT (the insight is missed
        by construction — D-forensic Lock 1). Arm B (post-#1646, fallacy negates
        the thesis): cardinal 1 → reader NAMES the rupture. The differentiation
        is the #1646 contribution, measured on the same planted text."""
        # Arm A — pre-#1646 baseline.
        _, _, mr_pre = _insight_chain(_PLANTED_ARGS, [])
        finding_pre = _reader_finding(mr_pre)
        assert mr_pre["cardinality"] == 0  # trivially consistent base
        assert finding_pre is None  # the reader had nothing to say

        # Arm B — post-#1646 insight.
        _, names_post, mr_post = _insight_chain(_PLANTED_ARGS, [_THESIS_IDX])
        finding_post = _reader_finding(mr_post)
        assert mr_post["cardinality"] == 1  # one belief restores consistency
        assert finding_post is not None  # the insight now reaches the prose

        # The differentiation is strict: silent vs naming the rupture.
        assert finding_pre is None and finding_post is not None

    def test_insight_adds_info_the_unsat_boolean_cannot(self) -> None:
        """The pre-#1646 chain ALSO had a PL/UNSAT oracle: on the fallacy base
        it returns False ("inconsistent"). That boolean was available all along.
        The differentiation is NOT "the insight detects inconsistency" — it is
        that the insight adds WHAT to give up (a NAMED belief), HOW LITTLE
        suffices (a cardinality), and WHAT SURVIVES (a count) — none of which
        the boolean carries. Measured on the fallacy base."""
        base, _, mr = _insight_chain(_PLANTED_ARGS, [_THESIS_IDX])
        finding = _reader_finding(mr)

        # The UNSAT boolean the pre-#1646 chain already had.
        unsat_signal = _sat_oracle(base)
        assert unsat_signal is False  # "inconsistent" — that is all it says

        # The insight adds three things the boolean cannot express.
        assert finding is not None
        assert "claim_T" in finding.statement  # NAMED rupture belief
        assert "cardinal 1" in finding.statement  # HOW LITTLE suffices
        # WHAT SURVIVES (B-3 inert clause — see TestInertContradiction below).
        assert "survivent" in finding.statement

    def test_reader_names_headlined_proposition_as_rupture(self) -> None:
        """DoD B-1/B-2: the rupture the reader names is the HEADLINED thesis
        (``claim_T``), the proposition the speaker puts forward as founding —
        not a peripheral detail. ``build_belief_base`` represents the fallacy as
        {[T], [-T]}, so the reader emits the B-2 non-unique lead (drop T or drop
        ¬T, two incompatible consistent worlds) and names T as the rupture
        point."""
        _, _, mr = _insight_chain(_PLANTED_ARGS, [_THESIS_IDX])
        finding = _reader_finding(mr)
        assert finding is not None
        # B-2: the non-unicity is the headline (a fallacy always yields ≥ 2
        # cardinal-1 retractions — see module docstring for why B-1-unique is
        # out of scope for the planted text).
        assert "pas de rétractation minimale unique" in finding.statement
        # The headlined proposition is named as the rupture point.
        assert "claim_T" in finding.statement
        assert finding.capability == "belief_revision"


# ---------------------------------------------------------------------------
# DoD: « Le cas "contradiction inerte" (insight 3) est testé explicitement »
# ---------------------------------------------------------------------------


class TestInertContradictionIsDiscriminating:
    """B-3 (the most discriminating insight): a real contradiction whose minimal
    retraction leaves conclusions intact — inert. The discriminating proof is
    that the insight DISTINGUISHES two planted texts that a pure UNSAT oracle
    reads identically (both False). If B-3 fired on both (or neither), it would
    not be a discriminator — just noise. With ``build_belief_base``, a single
    fallacy touches exactly 2 clauses, so survivor count = (n_args + 1) − 2 =
    n_args − 1: a multi-commitment discourse has survivors (inert), a
    single-commitment discourse has none (non-inert). Both UNSAT; the insight
    tells them apart."""

    def test_multi_commitment_discourse_contradiction_is_inert(self) -> None:
        """Inert case: a 4-commitment discourse where the fallacy undermines one
        belief. The clash is real (UNSAT) but localized — 3 engagements survive
        every retraction, so the reader emits the B-3 inert clause. A pure UNSAT
        oracle returns the same boolean it returns for a thesis-fatal clash."""
        args = ["claim_T", "claim_a", "claim_b", "claim_c"]  # 4 commitments
        base, _, mr = _insight_chain(args, [_THESIS_IDX])
        finding = _reader_finding(mr)

        assert _sat_oracle(base) is False  # real contradiction
        assert mr["cardinality"] == 1
        # The B-3 discriminator fires: survivors > 0 → "confinée / inerte".
        assert mr["base_size"] - mr["touched_count"] == 3  # 3 survivors
        assert finding is not None
        assert "inerte" in finding.statement or "confinée" in finding.statement
        assert "3 engagement" in finding.statement  # the survivor count is named

    def test_single_commitment_discourse_contradiction_is_not_inert(self) -> None:
        """Non-inert control: a single-commitment discourse where the one belief
        IS the clash (fallacy undermines the only claim). Nothing survives — the
        contradiction bears on the whole base. The reader does NOT emit the B-3
        inert clause. A pure UNSAT oracle reads this IDENTICALLY to the inert
        case above (both False) — that is precisely what it cannot distinguish."""
        args = ["claim_solo"]  # 1 commitment
        base, _, mr = _insight_chain(args, [0])
        finding = _reader_finding(mr)

        assert _sat_oracle(base) is False  # real contradiction, same boolean
        assert mr["cardinality"] == 1
        assert mr["base_size"] - mr["touched_count"] == 0  # no survivors
        assert finding is not None
        # B-3 does NOT fire — the inert clause is absent.
        assert "inerte" not in finding.statement
        assert "confinée" not in finding.statement

    def test_b3_signal_tracks_survivors_not_cardinality(self) -> None:
        """The B-3 discrimination is driven by SURVIVORS (untouched beliefs),
        not by cardinality. Both cases above are cardinal 1; the inert clause
        fires in one and not the other. This pins the reader's B-3 logic to the
        ``base_size − touched_count > 0`` property (act3_conclusion_plugin
        l.1139), so a future change that ties inert-ness to cardinality alone
        would break here — guarding the discriminating figure."""
        multi_base, _, mr_multi = _insight_chain(
            ["claim_T", "claim_a", "claim_b", "claim_c"], [_THESIS_IDX]
        )
        solo_base, _, mr_solo = _insight_chain(["claim_solo"], [0])

        # Same boolean baseline, same cardinality — the insight differs.
        assert _sat_oracle(multi_base) is _sat_oracle(solo_base) is False
        assert mr_multi["cardinality"] == mr_solo["cardinality"] == 1

        f_multi = _reader_finding(mr_multi)
        f_solo = _reader_finding(mr_solo)
        multi_inert = "inerte" in f_multi.statement or "confinée" in f_multi.statement
        solo_inert = "inerte" in f_solo.statement or "confinée" in f_solo.statement
        # The discriminator: inert in the multi case, NOT in the solo case.
        assert multi_inert is True
        assert solo_inert is False


# ---------------------------------------------------------------------------
# End-to-end on a planted text: the insight dict the producer shapes reaches
# the reader unchanged (no loss between producer shaping and reader prose).
# ---------------------------------------------------------------------------


class TestPlantedTextProducerReaderRoundtrip:
    """The producer shapes the ``minimal_retraction`` dict (incr 3); the reader
    projects it to prose. On a planted text, the shaping → reader path must not
    drop the structural signal: the cardinality, the named rupture belief, and
    the survivor count all survive into the rendered conclusion. This is the
    « Le résultat atteint la prose de conclusion, pas seulement l'annexe » DoD
    item, measured through the real chain (not injected state)."""

    def test_planted_insight_reaches_conclusion_prose(self) -> None:
        _, names, mr = _insight_chain(_PLANTED_ARGS, [_THESIS_IDX])
        finding = _reader_finding(mr)

        # The reader consumed the producer-shaped dict and rendered a finding.
        assert finding is not None
        assert finding.capability == "belief_revision"
        # Cardinality survived into prose.
        assert "cardinal 1" in finding.statement
        # The NAMED rupture belief survived (not an opaque index).
        assert any(names[i] in finding.statement for i in range(len(names)))
        # The fallacy-negation clause label survived too (the ¬T side of the clash).
        assert "¬claim_T" in finding.statement

    def test_no_finding_when_planted_text_has_no_fallacy(self) -> None:
        """Honest absence (#1019): a planted text with no fallacy produces an
        all-positive base → cardinal 0 → the reader emits NOTHING (no fabricated
        retraction). This is the Arm-A baseline restated as a negative guarantee:
        the insight does not invent a rupture where the text is consistent."""
        _, _, mr = _insight_chain(_PLANTED_ARGS, [])
        assert mr["cardinality"] == 0
        assert _reader_finding(mr) is None
