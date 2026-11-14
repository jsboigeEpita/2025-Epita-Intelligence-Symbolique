"""Acte III generator — actionable conclusion (the reader's payoff).

Epic #1134 (Restitution) / Track R4 #1138. LLM-conducted, woven per spec §4.
Consumed by the R6 renderer to populate ``RestitutionActs.act3_conclusion``.

Design (spec §1.3 + §3 + §4 + §7, issue #1138, dispatch coord R428/R429):
  - The conclusion hands back something *usable*. Three beats:
    1. **Synthèse honnête** — the verdict, **gated** on the non-triviality gates
       G1–G4 (#1008 §3) and on the verdict band (computed here, adapted from
       #1008 §2 — see ``_compute_verdict_band``). No over-claim.
    2. **Appréciations** — strengths **and** weaknesses of the discourse (both,
       honestly, woven from the quality axis and the fallacy/formal findings).
    3. **Que faire de l'analyse** — actionable: how to **counter** the arguments
       (the generated counter-arguments), the **weak points to target** (the
       structuring fallacies + the inferences Tweety invalidates + the attacks
       Dung isolates as defeated), and **what to expect next** (the probable
       follow-on moves — closing the loop on the Acte I game-theoretic framing).
  - Every framework citation gets a narrative anchor (passes the §4 gate — this
    module self-checks its own output with ``ReadabilityGate``).
  - **LLM-conducted**: the conclusion VARIES by corpus (no template #1108/#405).
    Fail-loud when no LLM is injected — empty string + explicit status; the
    renderer reports the gap honestly (anti-pendule #1019/#369).

Verdict band — honest adaptation of #1008 §2 to the restitution context:
  #1008 §2.1 frames the bands as "pipeline vs external analyst" (MATCH+ count
  over 10 yardstick dimensions). The restitution report has *no external
  analyst to compare against* (spec §3: "what this discourse is, honestly").
  We therefore compute the band from the **real analytical coverage** of the
  run — how many analytical axes produced non-trivial content — so the band
  governs *how strongly the discourse may be characterised*, never a fabricated
  comparison. This is the scorer the spec §2 table attributes to
  ``_compute_verdict()`` ("computed, not a state key").

Privacy HARD: opaque IDs only (``arg_N``, fallacy families are taxonomy
constants). The prompt carries the OPAQUE_ID_DIRECTIVE (FB-34). Corpus-derived
fields (fallacy justifications, counter-content) are **truncated** before
entering the prompt; the LLM is told to paraphrase, never echo verbatim — the
final R6 scrub (spec §6) is the downstream guard. (#1620: "synthesis snippets"
used to be listed here and never were one — no synthesis text has ever entered
this prompt; the ``_SYNTHESIS_CAP`` that would have capped it was declared in
the same commit as the claim and never used. Both removed rather than
implemented, since nothing in the prose needs them.)

Testability: ``build_act3_evidence`` is deterministic (no LLM/JVM/API); the LLM
is an injectable async callable ``Callable[[str], Awaitable[str]]`` (FB-29/38
injectable-LLM pattern), so unit tests pass a stub and need no kernel.

Mirrors the R3 act-plugin pattern (``act2_narrative_plugin``) — same 3 infra
files, append-only.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .figure_scales import score_with_scale  # #3394
from .arena_record import (  # #3073: shared arena record with act1
    ArenaRecord,
    build_arena_record,
    format_arena_line,
)
from .speaker_record import (  # #3082: shared speaker record with act1/act2
    SPEAKER_NAMING_RULE,
    SpeakerRecord,
    build_speaker_record,
    format_speaker_line,
)
from .reading_record import (  # #2850 lot 6: recorded reading bounds
    READING_BASIS_RULE,
    BoundRemoval,
    bound_removal_motif,
    format_reader_bounds_passage,
    remove_restated_bounds,
    ReadingRecord,
    build_reading_record,
    format_reading_block,
)
from .dung_reader import (  # #1908: shared meaning with act2
    REJECTED_MEANS,
    appendix_ref,
    appendix_refs_in,
    citable_appendix_refs,
)
from .native_dung import (  # #1912: single shared decoder — see native_dung.py
    decode_native_dung,
    native_semantics_label,
    select_primary_native,
)
from .conclusion_salience import ConclusionSalience, assess_conclusion_salience
from .cited_units import (  # #2965 (Acte III slice) — same budget as Act II
    CITED_UNIT_TEXT_CAP,
    act2_joined_unit_ids,
    cited_unit_ids,
    divergent_winner_texts,
    render_governance_lead,
    render_divergence_clause,
    truncate_at_boundary,
    truncate_head_and_tail,  # #3231 — the producer's final sentence survives the cap
)
from .unit_labels import (  # #3296 — per-act label table + legend
    LEGEND_REFERENT_CAP,
    label_writer_prompt,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    strategy_label_fr,  # #3328 leg 2: enum value -> FR name, free text -> ""
)
from argumentation_analysis.core.fallacy_attribution import (  # #3180
    confidence_of,  # #3231
    detector_confidence_note,  # #3231
    DETECTION_STANDING_RULE,  # #3248
    is_reported_move,
    is_speaker_move,
    move_author_label_of,
    reported_position_qualifier,  # #3513 — one qualifier reader, every surface
    taxonomy_definition_note,  # #3394
)
from argumentation_analysis.orchestration.fol_cause import (  # #3237
    FORMAL_CAUSE_NAMING_RULE,
)
from argumentation_analysis.utils.taxonomy_loader import (  # #3224
    fallacy_taxonomy_label,
)
from .act1_framing_plugin import reader_metadata_view  # #3311
from .fr_accord import accord
from .global_projection import (
    GlobalFinding,
    _MAX_CONVERGENCE_FINDINGS,
    _MAX_GATE_FINDINGS,
    project_global_findings,
)
from .llm_weaving import LlmCallable, WeaveOutcome, weave
from .quote_fidelity import sanitize_act_quotes
from .readability_gate import GateVerdict, ReadabilityGate
from .virtuous_identification import VirtuousModeAssessment, detect_virtuous_mode
from argumentation_analysis.agents.core.governance.coalition_play import (
    coalition_note,  # #3386
)
from argumentation_analysis.agents.core.reading import first_reading_note  # #3395

logger = logging.getLogger(__name__)

# Truncation caps for corpus-derived fields entering the prompt (privacy +
# prompt-budget discipline). The LLM is told to paraphrase, not echo.
_JUSTIFICATION_CAP = 200
# #3231 — bounds the FINAL sentence the cut re-appends (same contract as Act
# II's tail cap: a detector states its hedge at the end of its justification).
_JUSTIFICATION_TAIL_CAP = 200
_COUNTER_CAP = 200
# #1622 — how many counter-strategies the prompt ENUMERATES. Distinct from
# ``_COUNTER_CAP`` above (that one truncates each snippet's *text*). Named so the
# truncation notice below is computed from the same constant that produces the
# truncation: a literal ``[:8]`` and a hard-coded "8" in the notice can drift
# apart silently. Do NOT raise it — 16 would have the identical defect at 17;
# the fix is to *say* the list is partial, not to show more of it.
_COUNTER_LIST_CAP = 8
# SV (#1182): caps for governance/debate evidence (privacy + prompt budget).
_DEBATE_CAP = 200
_DEBATE_MAX_EXCHANGES = 4
#: #3158 (second instance) — a debate reply is an objection an agent produced;
#: nothing verified it, and its VERDICT is the reply's, never the report's.
#: The tag rides on the line that delivers the reply, where the rule it serves
#: applies: Act III restated a reply's « c'est un faux dilemme » as its own
#: finding, on a unit no detector had recorded anything for.
_DEBATE_PROVENANCE_TAG = (
    "[réplique produite par un agent de débat, jamais vérifiée : si tu en "
    "reprends le verdict, attribue-le au débat (« dans le débat, la réplique "
    "objecte que… »), et ne le présente jamais comme une détection]"
)
# #2845 — the source metadata entering the prompt. Same cap as Acte I's
# `_META_CAP`: both acts quote the same recorded fields, so they must truncate
# them alike (a divergence here would be a silent second contract).
_META_CAP = 160
# Epic #1258 / Track 4 #1262 — real claim excerpts for the reader-oriented
# conclusion. A reader re-links the verdict to the discourse from a few claims,
# not all. The per-text cap is #2974's CITED_UNIT_TEXT_CAP (imported above):
# the old 240-char cut kept 31 % of the governance winner (#2965); only the
# count of excerpts stays a local constant.
_MAX_CLAIM_EXCERPTS = 5
# #3193 (rework) — the anchor-excerpt count cap. It equals the projection's
# own bound (``_MAX_CONVERGENCE_FINDINGS + _MAX_GATE_FINDINGS``, imported
# above): in practice it never drops an anchor, but the renderer ENFORCES the
# bound the #2908 census row states instead of trusting the projection's.
_MAX_ANCHOR_EXCERPTS = _MAX_CONVERGENCE_FINDINGS + _MAX_GATE_FINDINGS
# #3214 — the joined-excerpt count cap (units Act II weighs that a map edge
# joins to a citation). The anchor cap above it mirrors the projection's own
# bound; this one has no upstream bound to mirror — the join's population is
# graph adjacency, which grows with the map — so the cap is stated here and
# the renderer counts its drops (``joined_excerpts_total`` → notice), never
# silently. Per-text budget stays CITED_UNIT_TEXT_CAP like every other
# cited-unit surface.
_MAX_JOINED_EXCERPTS = 8
# #1605 — the honest-absence ledger entering the prompt. The reason strings are
# code-authored (no corpus content), but they are capped like everything else so
# a future longer wording cannot silently eat the prompt budget.
_ABSENCE_REASON_CAP = 300

# #1667 — the PRESENCE side of the same axes. Before this, a structured-argu-
# mentation axis reached the conclusion ONLY through the absence ledger above:
# the prose had a vocabulary for the axis that FAILED and none for the axis that
# SUCCEEDED. Reanimating a module therefore REMOVED its single trace from the
# narrative. These caps bound what a successful axis may spend of the prompt.
_SUPPORT_NODE_CAP = 140
_SUPPORT_PAIR_CAP = 3
# #1645 — the distinctive insight (support cycle = circular authority) gets at
# most this many named groups in the prose. Smaller than _SUPPORT_PAIR_CAP: a
# cycle is a stronger, more specific statement than a support pair.
_SUPPORT_CYCLE_CAP = 2
# #1645 PR2 — articulation points (sole-supporter) cap, same rationale.
_ARTICULATION_CAP = 2
# #1646 — minimal-retraction insight: at most this many distinct rupture
# beliefs named in the prose (the cardinality is the headline; the beliefs are
# the evidence). Small, same rationale as the cycle/articulation caps.
_RETRACTION_CAP = 3
_ASPIC_MEMBER_CAP = 120
_ASPIC_MEMBERS_SHOWN = 4
# #1649 — ASPIC+'s singular contribution is attack SCOPE (undercut has no
# equivalent anywhere in the stack). The prose names the scope DISTRIBUTION
# only (undercut/rebut/undermine counts = vocabulary markers), never the raw
# ``attacks[*].target`` atoms: ``_pl_atom`` keeps up to 24 leading chars of
# source text, so those atoms are source-derived and must stay out of the
# prose (privacy HARD, coord R781 — "marqueurs de vocabulaire, texte caviardé").
# Ordered so the most singular scope (undercut) leads the sentence.
_ASPIC_ATTACK_SCOPES = ("undercut", "rebut", "undermine", "unresolved")
_ASPIC_SCOPE_GLOSS: Dict[str, str] = {
    "undercut": (
        "l'inférence elle-même est contestée à la racice (règle attaquée "
        "nommément) — l'apport singulier d'ASPIC+, sans équivalent dans la stack"
    ),
    "rebut": "la conclusion d'un autre enchaînement est contredite",
    "undermine": "la prémisse d'un autre enchaînement est attaquée",
    "unresolved": "une attaque n'a pu être qualifiée structurellement",
}

# #1667 axes 3/5 (ABA / SETAF / pondéré) — the three structured-argumentation
# axes whose container lives on ``dung_frameworks[*].formalism_specific`` (there
# is no first-level ``aba_results`` / ``setaf_results`` / ``weighted_results`` —
# the #1667 dispatch measured it: the sidecar the #1648 writers attach is the
# ONLY place these axes store their distinctive data). Caps bound what a
# successful axis spends of the prompt, same discipline as _SUPPORT_*_CAP.
_FORMALISM_NODE_CAP = 120  # truncate corpus-derived atoms (privacy HARD, #1702)
_ABA_CONTRARY_PAIR_CAP = 3  # max assumption↔contrary pairs named in prose
_SETAF_JOINT_ATTACK_CAP = 3  # max collective-attack coalitions named
# #3162 item 2 — the reading rule the Act III briefing carries ONLY when a
# SETAF line is qualified « (position rapportée) ». It states the direction of
# the defeat (the reported position's camp loses, the attacker is not weakened)
# and forbids inferring a side from an unqualified line. Conditional by
# construction: no qualifier, no rule.
_SETAF_REPORTED_POSITION_RULE = (
    "- ATTAQUE D'UNE POSITION RAPPORTÉE : quand une ligne du bloc CE QUE LES\n"
    "  CADRES STRUCTURÉS ÉTABLISSENT porte « (position rapportée) », la cible\n"
    "  est une position que le texte rapporte, cite ou combat — pas celle du\n"
    "  locuteur. Qu'une coalition la renverse est une défaite de ce camp-là :\n"
    "  ce n'est jamais une faiblesse de l'attaquant. N'écris pas que l'édifice\n"
    "  du locuteur se tient mal parce qu'une position rapportée tombe. Une\n"
    "  ligne sans ce qualificatif ne dit à qui est la position : n'en infère\n"
    "  aucun camp.\n"
)
_WEIGHTED_DIST_ATTACK_CAP = 8  # max attacks sampled for the weight distribution
# #2952 sites 1a-3 (DeLP / EAF / ADF) — same prompt-budget discipline as above.
_DELP_VERDICT_CAP = 3  # max named dialectical verdicts (warranted/defeated)
_EAF_DIVERGENCE_CAP = 3  # max named agent-pair belief divergences
_ADF_UNDECIDED_CAP = 3  # max named three-valued undecided statements
# #2952 site 3 — assignments inside a Tweety ``str(interp)`` rendering
# (``"{p=T,q=U}"``). Defensive by design: a format change fails the match and
# the projector falls back to the non-unicity figure, never fabricates.
_ADF_ASSIGNMENT_RE = re.compile(r"([A-Za-z0-9_.\-]+)\s*=\s*([TtFfUu])\b")

# #1605 — reader-facing French names for the structured-argumentation axes. The
# prose forbids raw snake_case identifiers (they are opaque to the non-technical
# reader this narrative addresses), so a capability key never reaches the
# narrative as-is. A capability absent from this map degrades to its
# underscore-stripped key rather than being dropped: an unnamed absence must
# still be said.
_ABSENT_DIMENSION_LABELS: Dict[str, str] = {
    "aspic_plus_reasoning": "l'argumentation défaisable (règles strictes et révisables)",
    "aba_reasoning": "l'argumentation par hypothèses et contraires",
    "setaf_reasoning": "les attaques collectives (plusieurs arguments attaquant ensemble)",
    "weighted_argumentation": "la force pondérée des attaques",
    "bipolar_argumentation": "les relations de soutien entre arguments",
    "belief_revision": "la révision des croyances (le point de rupture minimal)",
    # #3547 — the JTMS axis. As a key of this map, an executor-level death
    # of the ``belief_maintenance`` phase now reaches the absence ledger
    # (#3087's contract: the keys ARE the membership table) — before this
    # entry a timed-out jtms phase left no ledger entry whatever.
    "belief_maintenance": "la maintenance des croyances (ce qui tomberait sans une prémisse)",
    # #2952 — the three axes wired into Acte III by the sidecar/native
    # projectors.
    # #3087 — this map's KEYS are the absence-ledger membership table: the
    # executor-failure father (``state_writers._absence_ledger_axes``)
    # derives the axes it covers from exactly these keys, so an entry added
    # here declares an axis whose executor-level death is covered — there is
    # no second hand-kept list. An entry still does not by itself file an
    # absence: the ledger iterates ``structured_arg_status`` (writers only);
    # and both label consumers call ``.get``, so an UNlabelled axis degrades
    # to its underscore-stripped key rather than disappearing.
    "delp_reasoning": "la décision dialectique sur requêtes défaisables",
    "eaf_reasoning": "les croyances épistémiques par agent",
    "adf_reasoning": "l'acceptation à trois valeurs des énoncés",
    # #3131 — the local tier. Its skip/error statuses are collected from
    # ``state.local_llm_results`` by ``_collect_local_llm_dimension`` below;
    # and as a key of this map the executor-failure father (``state_writers.
    # _absence_ledger_axes``) covers a phase-level death automatically —
    # there is no second list to keep.
    "local_llm": "le palier local d'analyse (modèle servi sur place)",
}

# Verdict bands (adapted from #1008 §2.1 to the restitution coverage model).
_BAND_EXCEEDED = "EXCEEDED"
_BAND_MATCH = "MATCH"
_BAND_PARTIAL = "PARTIAL"
_BAND_BELOW = "BELOW"

# The analytical axes whose non-trivial coverage earns the verdict band. Each is
# real-in-state; we never fabricate an axis (G4).
_AXIS_FALLACIES = "fallacies"
_AXIS_QUALITY = "quality"
_AXIS_COUNTERS = "counter_arguments"
_AXIS_FORMAL_PL = "formal_pl"
_AXIS_FORMAL_FOL = "formal_fol"
_AXIS_DUNG = "dung"

# #1986 — encompassment is deliberately NOT a seventh axis here (the DoD's
# written-justification branch). This band counts axes of analytical
# coverage that the pipeline writes into state; the encompassment detector
# (evaluation/encompassment.py) is a per-document rhetorical verdict with
# no state writer yet. Adding a 7th axis would also silently recalibrate
# _EXCEEDED_MIN_AXES / _MATCH_MIN_AXES / _PARTIAL_MIN_AXES for every
# future run — a threshold decision to take deliberately, with its own
# before/after measurement, once the instrument is validated on the #1970
# witnesses (20a53f0c / 2cdc11ee) — not a side effect of building it.

# Thresholds mapping coverage count → band (anti-pendule: transparent, fixed).
# EXCEEDED needs formal depth (PL or FOL) AND quality (a characterised discourse)
# on top of broad coverage — the "depth surpassing" spirit of #1008 §2.1.
_EXCEEDED_MIN_AXES = 5
_MATCH_MIN_AXES = 4
_PARTIAL_MIN_AXES = 2

# Single definition of the axis set, shared by the band computation and the
# claim gate below. Two lists would drift, and the gate's whole job is to be
# exactly as wide as the band's notion of coverage.
_ALL_AXES: Tuple[str, ...] = (
    _AXIS_FALLACIES,
    _AXIS_QUALITY,
    _AXIS_COUNTERS,
    _AXIS_FORMAL_PL,
    _AXIS_FORMAL_FOL,
    _AXIS_DUNG,
)

# Formula prefixes written by a formalism into ANOTHER formalism's container
# (#1605). See _is_guest_formal_entry for why the host axis must not credit them.
_GUEST_FORMULA_MARKERS: Tuple[str, ...] = ("dl:", "cl(", "qbf:")

# --- #1605: the blocking half of the conclusion gate -------------------------
#
# _band_claim_ceiling tells the LLM how strongly it may characterise the
# discourse. That is a *prompt* instruction, and nothing verified afterwards
# that the produced prose respected it. This gate is the deterministic half:
# after the conclusion is woven, an assertion resting on an axis that produced
# nothing is removed and the removal is said out loud.
#
# Per-axis, deliberately, and NOT band-based: the band counts axes against fixed
# thresholds, so a run can lose an entire formalism and keep the same band
# (measured — losing formal_fol takes 6 axes to 5, still EXCEEDED). A count
# cannot express "this particular claim has no support".

_AXIS_LABELS_FR: Dict[str, str] = {
    _AXIS_FALLACIES: "les sophismes",
    _AXIS_QUALITY: "la qualité argumentative",
    _AXIS_COUNTERS: "les contre-arguments",
    _AXIS_FORMAL_PL: "la logique propositionnelle",
    _AXIS_FORMAL_FOL: "la logique du premier ordre",
    _AXIS_DUNG: "l'argumentation abstraite (Dung)",
}

# Phrases by which a French conclusion asserts an axis. Kept narrow: a marker
# that also occurs in ordinary prose would block honest sentences.
_AXIS_CLAIM_MARKERS: Dict[str, Tuple[str, ...]] = {
    _AXIS_FALLACIES: ("sophisme", "fallacieu", "paralogisme"),
    _AXIS_QUALITY: ("qualité argumentative", "score de qualité", "vertu argumentative"),
    _AXIS_COUNTERS: ("contre-argument", "contre-argumentation"),
    _AXIS_FORMAL_PL: (
        "logique propositionnelle",
        "satisfiabilité",
        "solveur sat",
    ),
    _AXIS_FORMAL_FOL: (
        "logique du premier ordre",
        "premier ordre",
        "eprover",
        "prover9",
        "quantificateur",
    ),
    _AXIS_DUNG: (
        "sémantique de dung",
        "argumentation abstraite",
        "extension fondée",
        "extension admissible",
        "extension préférée",
    ),
}

# A sentence carrying one of these is *stating the absence*, not claiming the
# axis — exactly what #1609 asks the conclusion to do. Blocking it would punish
# the honest wording. The gate is biased toward NOT blocking.
_ABSENCE_MARKERS: Tuple[str, ...] = (
    "aucun",
    "aucune",
    "n'a pas",
    "n'ont pas",
    "ne permet",
    "ne peut",
    "n'est pas",
    "ne sont pas",
    "faute de",
    "absence",
    "non évalu",
    "pas de ",
    "sans ",
    "indisponible",
    "n'a produit",
    "hors de portée",
)

# Sentence splitter that preserves each chunk's leading whitespace, so removing
# a sentence leaves the rest of the line spaced as the LLM wrote it.
_SENTENCE_RE = re.compile(r"\s*[^.!?\n]+[.!?]*")


# --- evidence dataclasses ----------------------------------------------------


@dataclass
class StructuringWeakPoint:
    """A weak point the reader can target — a fallacy or a formal rejection.

    ``source`` is one of ``"fallacy"`` / ``"pl"`` / ``"fol"`` / ``"dung"`` so the
    LLM can anchor the citation to the framework that produced it (spec §4).
    """

    source: str
    label: str  # human-readable: fallacy family/type, or a formal verdict line
    target_arg_id: str
    detail: str = ""
    # #3231 — for a fallacy-sourced point: the detector's own confidence in
    # the detection, None when it measured none (#3029: unmeasured is None,
    # never a default). Printed on the line, weighed by the consigne.
    confidence: Optional[float] = None
    # #3394 — the taxonomy's one-line definition for the label, "" when the
    # node did not resolve (a definition is looked up, never borrowed). It
    # rides the label's FIRST mention among the weaknesses lines.
    definition: str = ""


@dataclass
class CounterStrategy:
    """A counter-argument the reader can use to push back."""

    strategy: str
    target_arg_id: str
    snippet: str
    # G6 (#1180): the validation verdict (ValidationResult shape) so the
    # narrative can cite counter-argument *validity*, not just existence.
    # None when the evaluator did not run (honest absence, not fabricated).
    is_valid_attack: Optional[bool] = None
    counter_succeeds: Optional[bool] = None


@dataclass
class GovernanceVerdict:
    """A governance voting decision (SV #1182), verified-in-state.

    ``scores`` maps opaque option IDs → Copeland/influence score. Privacy: the
    keys are opaque (no party/option names).
    """

    method: str
    winner: str
    scores: Dict[str, float] = field(default_factory=dict)
    # #2969: a divergent vote records every distinct winner — presenting one
    # "leading argument" when the methods disagreed erases the divergence.
    winners: List[str] = field(default_factory=list)
    # #2965 / R1078: the winner's ORIGIN — "vote_aggregate" (a formal vote),
    # "llm_resolution" (a model-recommended STRATEGY, not a ranked unit),
    # "conflict_resolution" (a mediation TYPE), or "unresolved"/None
    # (unrecorded). Both Act III branches used to say
    # "vote social-choice" unconditionally; this is what they frame on now.
    winner_provenance: Optional[str] = None
    method_provenance: Optional[str] = None
    # #3001 (a′) — HOW SOLID the vote was: per-option support across the
    # deciding methods, the count of deciding methods, and the tier that
    # decided (condorcet → majority → plurality, #2300). Rendered
    # QUALITATIVELY by cited_units.qualitative_support_band (#1914 — never
    # a counter); vote-origin records only, honest absence otherwise.
    support_by_option: Dict[str, int] = field(default_factory=dict)
    n_methods_decided: Optional[int] = None
    winner_basis: Optional[str] = None
    # #3394 cycle 2 — the NAMES behind the counts (which deciding methods
    # chose each option): the render names the vote it invokes.
    methods_by_option: Dict[str, List[str]] = field(default_factory=dict)
    # #3394 (tranche R1145) — the two consensus protocols' verdicts, named
    # apart: not scrutins, never in the support population; the band names
    # their count (« plus deux protocoles de consensus »).
    consensus_protocols: Dict[str, str] = field(default_factory=dict)
    # #3386 — the coalition play's block, producer-rendered like Acte II's
    # (``coalition_play.coalition_note``): a bloc that moved the outcome
    # and/or the declared profile's pivot. Empty when nothing changed.
    coalition_note: str = ""


@dataclass
class DebateExchange:
    """One adversarial-debate exchange (SV #1182). G8 (#1184): scheme-grounded.

    ``scheme``/``critical_question`` carried when the deterministic classifier
    matched (None otherwise — honest, not fabricated). SV reader contract
    (point/rebuttal) preserved.
    """

    point: str
    rebuttal: str
    scheme: Optional[str] = None
    critical_question: Optional[str] = None


@dataclass
class QualityStrength:
    """A virtue where the discourse scores well (a strength to acknowledge).

    #3137: a strength carries its population — ``args_at_top`` (k) arguments
    at the top band, of ``args_evaluated`` (m) arguments whose scores carry
    the virtue, of ``units_total`` (N) units in the discourse. Without these
    counts the writer read ``meilleur score du discours : 1.0`` and turned
    one top-band argument of 8 into a property of the whole discourse.
    """

    virtue: str
    score: float
    args_at_top: int
    args_evaluated: int
    units_total: int


@dataclass
class AbsentDimension:
    """An analytical dimension the run did NOT genuinely evaluate (#1605).

    Built from ``state.structured_arg_status`` — the honest-absence ledger that
    #1236 populates and that, until now, no restitution module read. A run may
    complete all its phases and still have lost an axis (the translator raised,
    or found nothing genuine); the conclusion must be able to say so.

    ``label`` is the reader-facing French name: the prose forbids raw snake_case
    identifiers, so the capability key never reaches the narrative as-is.
    """

    capability: str
    label: str
    status: str
    reason: str


@dataclass(frozen=True)
class StructuredArgFinding:
    """What a structured-argumentation axis ESTABLISHED, when it succeeded (#1667).

    The symmetric counterpart of :class:`AbsentDimension`. ``statement`` is not a
    count and not a status word: it is what THIS formalism says and no other axis
    says — the support relation for bipolar, the surviving rule-derivations for
    ASPIC+. A count here would reproduce ``appendix.py``'s ``"disponible"`` one
    hop further along: the witness moved, no decider created (anti-pendule
    #1667).
    """

    capability: str
    label: str
    statement: str


@dataclass(frozen=True)
class BlockedClaim:
    """A sentence the gate removed because its axis produced nothing (#1605).

    Carries the offending sentence so a reviewer can audit what was withheld —
    a gate whose decisions are not inspectable is indistinguishable from prose
    that simply never made the claim.
    """

    axis: str
    label: str
    sentence: str


@dataclass
class VerdictBand:
    """The computed verdict band + the honest coverage that earned it.

    Adapted from #1008 §2.1 to the restitution coverage model (no external
    analyst): the band governs how strongly the discourse may be characterised.
    """

    band: str
    nontrivial_axes: List[str] = field(default_factory=list)
    missing_axes: List[str] = field(default_factory=list)
    axes_count: int = 0


@dataclass
class Act3Evidence:
    """Deterministic evidence bundle for the Acte III conclusion.

    ``gates`` carries the G1–G4 statuses (#1008 §3.2) so the orchestrator can
    emit the honest fallback wording when the conclusion must not render.
    """

    args_total: int = 0
    fallacies_total: int = 0
    # #3180 — the fallacies the text REPORTS (a move by another party), kept
    # apart from the speaker's count so the conclusion can still say they were
    # found without filing them as this discourse's weaknesses.
    reported_fallacies_total: int = 0
    # #3429 — the third parties the text actually NAMES for those reported
    # moves. Empty means the text named none, and the block must then say so
    # instead of pointing the conductor at a party that does not exist.
    reported_fallacies_labels: List[str] = field(default_factory=list)
    counters_total: int = 0
    quality_axis_available: bool = False
    quality_strengths: List[QualityStrength] = field(default_factory=list)
    weak_points: List[StructuringWeakPoint] = field(default_factory=list)
    counter_strategies: List[CounterStrategy] = field(default_factory=list)
    verdict: Optional[VerdictBand] = None
    gates: Dict[str, bool] = field(default_factory=dict)
    # SV (#1182): governance verdict + debate exchanges, surfaced so the
    # conclusion can cite collective deliberation. None/empty when the phases
    # produced no non-trivial output (honest absence, not fabricated).
    governance_verdict: Optional[GovernanceVerdict] = None
    debate_exchanges: List[DebateExchange] = field(default_factory=list)
    # DERIVED virtuous flag (spec §5.1) — drives virtue-first titling when the
    # state characterises the text as virtuous (zero fallacies + non-trivial
    # quality/formal axis). None until build_act3_evidence populates it.
    virtuous_mode: Optional[VirtuousModeAssessment] = None
    # Epic #1258 / Track 1 #1259 — when True, build_act3_prompt DROPS the
    # opaque-ID directive so the readable conclusion names the real stakes.
    deanonymized: bool = True
    # Epic #1258 / Track 4 #1262, re-keyed by #2965 (Acte III slice) — real
    # claim text from ``state.identified_arguments``, as ``(unit_id, capped
    # text)`` pairs. The prior contract was the first N texts in insertion
    # order: on the measured run, the 14 units Act III cites were none of
    # them (issue #2965). The selection now follows the citations — see
    # ``build_act3_evidence`` — and each text is capped by
    # ``CITED_UNIT_TEXT_CAP`` (#2974's allocation), not the 240-char excerpt
    # cut that kept 31 % of the governance winner.
    claim_excerpts: List[Tuple[str, str]] = field(default_factory=list)
    # #2850 lot 4 — the population ``claim_excerpts`` was cut from: the
    # cited units plus the dict's remaining ones, distinct. The writer-prompt
    # notice fires from the gap between what is listed and what exists, never
    # from the cap alone — the ``counters_total`` precedent (#1622), so a run
    # below the cap stays silent (no false alarm).
    claim_excerpts_total: int = 0
    # #3156 — the anchor text of every unit a global finding cites, keyed by
    # opaque id and capped like every other cited text. The `[convergence]`
    # line printed `arg_66` / `arg_79` as bare ids while asking the writer to
    # name the passages, so the writer bound them to the one nearby unit it
    # could describe (arg_30 — neither convergent, and with no quality score).
    # The same lesson as #2965: the referent travels on the line that asks.
    anchor_excerpts: Dict[str, str] = field(default_factory=dict)
    # #3193 (rework) — distinct unit cites left without an anchor because the
    # count cap fired. Stated on the rendered block, never silent (a drop the
    # reader cannot see is a silent drop, #1019). Zero in practice: the cap
    # equals the projection's own bound.
    anchors_dropped: int = 0
    # #3214 — the units Act II WEIGHS that an argument-map attack edge joins
    # to a unit Act III already cites, as ``(unit_id, relation, capped text)``
    # triples. Act III's own populations (winner, salience, findings,
    # ``cited_unit_ids``) never carried them, so the conclusion could deny in
    # good faith a reply Act II had weighed a page earlier. The relation names
    # the cited neighbor (``attaque arg_1`` / ``attaqué par arg_1``) — an
    # excerpt with no join is orphan text the writer cannot place (#2965's
    # lesson: the referent travels on the line that asks).
    joined_excerpts: List[Tuple[str, str, str]] = field(default_factory=list)
    # #3214 — the whole joined population the cap cut ``joined_excerpts``
    # from. The prompt notice fires from the gap between what is listed and
    # what the join found, never from the cap alone (#1622/#2850 idiom).
    joined_excerpts_total: int = 0
    # #2965 (Acte III slice) — the governance winner's own text, capped.
    # The writer does not join an id to its unit across a long prompt
    # (measured on the saved state: wrong unit 4 of 5 samples, R1071), so
    # the governance line carries the referent itself. Empty when the
    # winner has no joinable text — the line then keeps its role-only
    # wording (honest absence, not a fabricated description).
    governance_winner_text: str = ""
    # #2989 rework — the DIVERGENT winners' texts, in ``winners`` order as
    # ``(winner_id, text)`` pairs (text ``""`` when not localizable). The
    # divergence clause names each winner by what it says; an id stays only
    # for a winner with no text (#2965/#2980 — the writer does not join an
    # id to its unit across a long prompt).
    governance_divergent_texts: List[Tuple[str, str]] = field(default_factory=list)
    # #3308 — for every unit Act III cites as a VOTE WINNER (the leading
    # winner and each divergent one), what the fallacy pass established about
    # ITS defects. R1127a: the writer was told nothing, saw no fallacy listed
    # on a divergent winner, and concluded « les unités citées ne portent pas
    # de défaut net » about units the pass had never examined — an absence of
    # examination read as an absence of defect (#2966/#1019, the #2976 defect
    # Act II already repairs). Four honest states, never conflated: examined
    # and clean, examined with N localized defects, NOT examined, and no
    # coverage record at all (#2966: absence of the record is not coverage).
    examination_by_unit: Dict[str, str] = field(default_factory=dict)
    # #1605 — dimensions the run did NOT genuinely evaluate, read from
    # ``state.structured_arg_status``. Empty on a healthy run. Non-empty here is
    # not a defect of the pipeline: it is the one thing the conclusion was
    # structurally unable to say before this field existed.
    absent_dimensions: List[AbsentDimension] = field(default_factory=list)
    # #1667 — the symmetric PRESENCE channel. ``absent_dimensions`` above was the
    # ONLY path from a structured-argumentation axis to this conclusion, and it
    # opens on failure. An axis that worked was therefore mute here, and making a
    # module work again removed its single trace from the prose. Empty when no
    # axis established anything — never a status word, never a count.
    structured_findings: List[StructuredArgFinding] = field(default_factory=list)
    # #1911 — the GLOBAL synthesis channel. Bounded structured findings
    # (cross-axis convergences + deep-synthesis value gates) derived from
    # lower-level state, never the synthesis prose and never a boolean (the
    # two dead ends #1620 documented). Every finding cites its anchors, so
    # the conclusion can weigh convergence as confidence, not as inventory.
    global_findings: List[GlobalFinding] = field(default_factory=list)
    # #1914 (Acte III slice) — the salience ranking (P1 decisif → P3
    # accompanying) + the zero-shot surplus split. None until
    # build_act3_evidence populates it (mirrors virtuous_mode).
    salience: Optional[ConclusionSalience] = None
    # #1914 (Acte I slice) — the interpretive question the framing closed
    # on, READ back from the state (written by both orchestration lanes
    # after Acte I). Empty when Acte I posed none — honest absence; the
    # prompt then forbids a retroactive question instead of fabricating one.
    interpretive_question: str = ""
    # #3432 (ask 3) — the points the framing ANNOUNCED as needing to be
    # settled, READ back from the state (written by both orchestration lanes
    # after Acte I). Empty when the framing announced none — honest absence,
    # and the prompt then forbids inventing a retroactive one. A non-empty
    # list binds the conclusion: each announced point is either settled with
    # its verdict, or explicitly reported as not reached.
    announced_checks: List[str] = field(default_factory=list)
    # #3432 (ask 2) — what the thesis LEAVES OUT, as the personas read it
    # (#3377): one named field per persona, labelled model knowledge by the
    # persona's dict-level ``basis`` and by the block that renders it here.
    # A reading, not a move: no quote, no span, and an empty string is the
    # honest "none named" — the prompt then forbids inventing one.
    historical_blind_spot: str = ""
    strategic_blind_spot: str = ""
    # #2845 — the source metadata as the run recorded them
    # (``state.source_metadata``). The prompt has always asked the writer to
    # name the speaker "via les métadonnées" while the bundle carried none, so
    # the writer harvested a name from the extracts — and on a reply, the only
    # person named in the extracts is the INTERLOCUTOR the speaker answers.
    # Measured on a campaign dump: the conclusion credited the thesis to the
    # questioner. Same field, same cap and same honest-absence branch as Acte I,
    # which is the act that has always carried it.
    metadata: Dict[str, str] = field(default_factory=dict)
    # #3073 — l'arène : l'enregistrement partagé avec l'Acte I (valeur +
    # provenance). L'Acte III ne lisait que ``source_metadata`` et disait donc
    # « l'arène n'est pas documentée » là où l'Acte I imprimait l'inférence de
    # l'extracteur sous un titre « vérifié ». Même ligne, même étiquette.
    arena: ArenaRecord = field(default_factory=ArenaRecord)
    # #3082 — le locuteur : le même partage, étendu aux trois actes. La
    # métadonnée n'est qu'un des deux producteurs — le stakeholder « speaker »
    # de l'extracteur est l'autre — et le nommage se lie à l'enregistrement,
    # plus au bloc MÉTADONNÉES seul.
    speaker: SpeakerRecord = field(default_factory=SpeakerRecord)
    # #2850 lot 6 — the run's recorded bounded readings (#1737 table): the
    # basis the Acts never spoke, quoted here beside the speaker so the
    # reader learns the bounds of the readings the verdicts rest on.
    readings: ReadingRecord = field(default_factory=ReadingRecord)
    # #3395 (acts slice) — the first reading's labelled block, rendered by its
    # ONE producer (``first_reading_note``): the text's defining moves with
    # their verbatim quotes, or the stated absence — the conclusion may neither
    # invent a centre nor read a failed read as a silence. Empty when the state
    # carries no record at all (bare doubles): the prompt then omits the
    # section instead of putting a producer's vocabulary where none ran.
    first_reading: str = ""
    # #3296 — every unit's capped text, keyed by opaque id: the referent
    # source for the per-act label table's legend. The ids stay in the
    # evidence layer; the writer's prompt alone reads them as letters.
    unit_texts: Dict[str, str] = field(default_factory=dict)


@dataclass
class Act3Result:
    """Outcome of :func:`build_act3_conclusion`.

    ``status`` is one of ``"woven"`` (LLM produced a conclusion), ``"unavailable"``
    (no LLM injected or LLM failed — fail-loud, #1108), ``"empty_state"`` (G1
    failed — no substrate), ``"gates_failed"`` (G1–G4 blocked the gated
    synthesis — honest fallback wording). ``gate_verdict`` is the honest §4
    self-check.
    """

    narrative: str
    status: str
    gate_verdict: Optional[GateVerdict] = None
    degraded: Dict[str, str] = field(default_factory=dict)
    # True when the conclusion was conducted in virtuous mode (spec §5) — the
    # headline titles on the measured virtues, not on the absence of fallacies.
    is_virtuous: bool = False


# --- deterministic evidence builder (no LLM) ---------------------------------


def _truncate(text: Any, cap: int) -> str:
    """Coerce to str and cap length (privacy + prompt budget)."""
    if not text:
        return ""
    s = str(text).strip()
    return s if len(s) <= cap else s[:cap].rstrip() + " […]"


def _pl_verdict(result: Dict[str, Any]) -> Optional[bool]:
    """Read a PL analysis verdict as a strict bool, or None when unverified.

    Canonical PL key is ``satisfiable`` (shared_state.add_propositional_analysis_result,
    #1151 Finding C); ``consistent`` is the legacy/FOL-shared key kept as a
    fallback. Preserves the strict ``True``/``False``/``None`` semantics so an
    unverified theory is never conflated with an inconsistent one (#1019) — do
    NOT collapse to ``bool()``.
    """
    sat = result.get("satisfiable")
    if sat is None:
        sat = result.get("consistent")
    return sat if isinstance(sat, bool) else None


def _fol_verdict(result: Dict[str, Any]) -> Optional[bool]:
    """Read a FOL verdict (``consistent``) as a strict bool, or None when undecided."""
    consistent = result.get("consistent")
    return consistent if isinstance(consistent, bool) else None


def _is_guest_formal_entry(result: Dict[str, Any]) -> bool:
    """True when a record in a formal container was written by ANOTHER formalism.

    #1605: the formal containers are shared. ``fol_analysis_results`` also
    receives Description Logic verdicts (``state_writers._write_dl_to_state``
    renders them as ``formulas=["DL: <message>"]``), and
    ``propositional_analysis_results`` receives Conditional-Logic (``CL(...)``)
    and QBF ones. Sharing a container is a storage decision and is fine; letting
    a GUEST verdict credit the HOST axis is not — measured on 2 of 3 real
    corpora, the ``formal_fol`` axis was carried solely by a DL prose entry on
    runs where the real FOL theory failed to parse, so the conclusion was
    granted first-order support that no first-order solver ever produced.

    Conservative on purpose: only an entry whose formulas are *all* guest
    markers is treated as a guest, so a real theory that happens to mention a
    marker keeps its credit.
    """
    formulas = result.get("formulas")
    if not isinstance(formulas, list) or not formulas:
        return False
    return all(
        isinstance(f, str) and f.strip().lower().startswith(_GUEST_FORMULA_MARKERS)
        for f in formulas
    )


def _pl_inconsistent(state: Any) -> int:
    """Count PL inferences the Tweety solver found inconsistent (real-in-state).

    Uses ``_pl_verdict`` (canonical ``satisfiable`` key) so the PL axis is read
    the same way as the FOL axis and the virtuous-mode detector — #1151 C.
    """
    pl = getattr(state, "propositional_analysis_results", None)
    if not isinstance(pl, list):
        return 0
    return sum(
        1
        for r in pl
        if isinstance(r, dict)
        and not _is_guest_formal_entry(r)
        and _pl_verdict(r) is False
    )


def _pl_verified(state: Any) -> int:
    """Count PL theories the Tweety solver verified (any verdict, real-in-state).

    D1c (#1167): a CONSISTENT PL theory (``satisfiable is True``) is a real
    formal result, not a non-event — the solver ran and confirmed the
    discourse's propositional structure holds. The formal axis must credit it
    as non-trivial so a coherent text (no inconsistency) still surfaces a
    formal finding (satisfiable IS a result). Counts True AND False verdicts;
    unverified (None) theories are excluded — #1019 (never ``bool()`` a formal
    verdict: None ≠ False).
    """
    pl = getattr(state, "propositional_analysis_results", None)
    if not isinstance(pl, list):
        return 0
    return sum(
        1
        for r in pl
        if isinstance(r, dict)
        and not _is_guest_formal_entry(r)
        and _pl_verdict(r) is not None
    )


def _fol_inconsistent(state: Any) -> int:
    """Count FOL theories the Tweety solver found inconsistent (real-in-state)."""
    fol = getattr(state, "fol_analysis_results", None)
    if not isinstance(fol, list):
        return 0
    return sum(
        1
        for r in fol
        if isinstance(r, dict)
        and not _is_guest_formal_entry(r)
        and r.get("consistent") is False
    )


def _fol_stated_causes(state: Any) -> List[str]:
    """The causes each INCONSISTENT FOL theory stated (#3107), in entry order.

    Read from ``consistency_cause`` — computed by the writer from the formulas
    and their source units. Empty when no theory stated one: an artefact from
    before the field existed, or a run whose cause could not be established.
    Never inferred here — a cause this reader invented would be exactly the
    defect the field repairs.
    """
    fol = getattr(state, "fol_analysis_results", None)
    if not isinstance(fol, list):
        return []
    # Lazy on purpose (#2352): the orchestration package ``__init__`` imports
    # a module that rewrites ``os.environ`` from the root .env at import time
    # — this renderer must not drag it in module order.
    from argumentation_analysis.orchestration.fol_cause import cause_phrase

    causes = []
    for r in fol:
        if not isinstance(r, dict) or r.get("consistent") is not False:
            continue
        if not isinstance(r.get("consistency_cause"), dict):
            continue
        if not r["consistency_cause"].get("cause"):
            continue
        causes.append(cause_phrase(r["consistency_cause"]))
    return causes


def _pl_stated_causes(state: Any) -> List[str]:
    """The causes each UNSAT propositional theory stated (#3122), in entry order.

    The PL twin of :func:`_fol_stated_causes`, reading the same
    ``consistency_cause`` field the #3122 writer attaches (a minimal
    unsatisfiable core classified by the shared fol_cause vocabulary).
    Guest entries (CL/SAT/QBF sidecars) carry no cause and never did.
    Never inferred here — a cause this reader invented would be exactly the
    defect the field repairs.
    """
    pl = getattr(state, "propositional_analysis_results", None)
    if not isinstance(pl, list):
        return []
    # Lazy on purpose (#2352): the orchestration package ``__init__`` imports
    # a module that rewrites ``os.environ`` from the root .env at import time
    # — this renderer must not drag it in module order.
    from argumentation_analysis.orchestration.fol_cause import cause_phrase

    causes = []
    for r in pl:
        if not isinstance(r, dict) or _is_guest_formal_entry(r):
            continue
        if _pl_verdict(r) is not False:
            continue
        if not isinstance(r.get("consistency_cause"), dict):
            continue
        if not r["consistency_cause"].get("cause"):
            continue
        causes.append(cause_phrase(r["consistency_cause"]))
    return causes


def _fol_verified(state: Any) -> int:
    """Count FOL theories the Tweety solver verified (any verdict, real-in-state).

    D1c (#1167): a CONSISTENT FOL theory (``consistent is True``) is a real
    formal result — credit it so a coherent text surfaces a formal finding.
    Counts True AND False verdicts; excludes unverified (None) — #1019.
    """
    fol = getattr(state, "fol_analysis_results", None)
    if not isinstance(fol, list):
        return 0
    return sum(
        1
        for r in fol
        if isinstance(r, dict)
        and not _is_guest_formal_entry(r)
        and (r.get("consistent") is True or r.get("consistent") is False)
    )


# #1912: the local ``_dung_rejected_by_arg`` resolver is DELETED. This was
# the duplicated copy whose comment said "kept local for file-disjointness".
# Both acts share the single decoder in ``restitution.native_dung`` — only
# verification_* entries contribute Dung rejections; the old generic loop read
# sidecar shapes as native acceptance and fabricated 221 false rejections on
# the real corpus (#1894 forensic). Do not resurrect a local copy: extend
# native_dung.py instead.


def _collect_weak_points(
    fallacies: Dict[str, Any],
    dung_rejected: Dict[str, str],
    pl_inc: int,
    fol_inc: int,
    fol_causes: Optional[List[str]] = None,
    pl_causes: Optional[List[str]] = None,
    citable_refs: Optional[Set[str]] = None,
    primary_semantics: Optional[str] = None,
    state: Any = None,
) -> List[StructuringWeakPoint]:
    """Collect the structuring weak points the reader can target (real-in-state).

    Each weak point is bound to (a) a located argument and (b) the concrete
    verdict that flagged it — the spec §4 weaving anchors. We surface the
    fallacies that *target* an argument, plus the formal rejections. Never
    fabricate a weak point (G4, anti-pendule #1019/#369).
    """
    points: List[StructuringWeakPoint] = []
    for _fid, fdata in fallacies.items():
        if not isinstance(fdata, dict):
            continue
        # #3180 — a reported move is another party's, not this discourse's
        # weak point: it cannot be targeted as the speaker's failure.
        if not is_speaker_move(fdata):
            continue
        tid = fdata.get("target_argument_id") or ""
        if not tid:
            continue
        family = str(fdata.get("family", "inconnu"))
        ftype = str(fdata.get("type", "inconnu"))
        points.append(
            StructuringWeakPoint(
                source="fallacy",
                # #3224 — the label names the taxonomy branch, not only the
                # leaf and the root: the reader can then read an absence
                # claim against the category the evidence detected under.
                label=fallacy_taxonomy_label(ftype, family, fdata.get("taxonomy_path")),
                target_arg_id=str(tid),
                detail=truncate_head_and_tail(
                    fdata.get("justification", ""),
                    _JUSTIFICATION_CAP,
                    _JUSTIFICATION_TAIL_CAP,
                ),
                # #3231 — the detector's own standing travels with the point:
                # the conclusion's consigne weighs it as Act II does.
                confidence=confidence_of(fdata),
                # #3394 — the label carries the taxonomy's own definition on
                # its first mention: the reader is a non-specialist, and
                # « sophisme métonymique » alone teaches nothing.
                definition=taxonomy_definition_note(fdata),
            )
        )
    for arg_id, semantics in dung_rejected.items():
        # #3394 cycle 2 — the annex ref rides the point ONLY when the annex
        # will print it (citable_appendix_refs, the appendix's own
        # derivation); otherwise the point states its result in place. And
        # when this rejection's semantics is not the one Act II's primary
        # verdict spoke under, the line SAYS the two readings — the cycle-2
        # census measured the same proposition sent to Annexe Dung[preferred]
        # in Act II and Annexe Dung[multi] in Act III with the difference
        # never said.
        _ref = appendix_ref(semantics)
        if _ref and (citable_refs is None or _ref in citable_refs):
            _detail = f"{_ref} — {REJECTED_MEANS}"
        else:
            _detail = (
                f"{REJECTED_MEANS} — conséquence énoncée en place "
                f"(aucune annexe imprimée pour la sémantique {semantics})"
            )
        if primary_semantics and semantics != primary_semantics:
            _detail += (
                " — le verdict principal (Acte II) est énoncé sous la "
                f"sémantique {primary_semantics}"
            )
        points.append(
            StructuringWeakPoint(
                source="dung",
                # #3513 — the rejection line says whose position fell: a
                # REPORTED position the graph rejects is that camp's defeat
                # (the speaker may even be the attacker), never a weakened
                # support of the analysed text. The shared qualifier reads the
                # raw provenance; an unstated author changes nothing.
                label=(
                    f"argument rejeté par le cadre de Dung (sémantique {semantics})"
                    + (
                        reported_position_qualifier(state, str(arg_id))
                        if state is not None
                        else ""
                    )
                ),
                target_arg_id=str(arg_id),
                # #1908: the accepted/rejected meaning is shared with Act II —
                # one helper (dung_reader), so the acts cannot diverge.
                # #1914 résidu b: the same graph finding bears the same stable
                # ref in both acts — the rejection's proof is the machinery
                # the annexe folds under that ref.
                detail=_detail,
            )
        )
    if pl_inc:
        # #3122 — the cause the writer stated, when one was stated. Without
        # it this label said only "inconsistent", and the conclusion read a
        # bare UNSAT as the discourse's own incoherence — the PL twin of the
        # misreading #3107 removed from the FOL leg.
        pl_cause_text = " ; ".join(pl_causes or [])
        points.append(
            StructuringWeakPoint(
                source="pl",
                label=(
                    f"{accord(pl_inc, 'inférence propositionnelle inconsistante', 'inférences propositionnelles inconsistantes')} "
                    f"(solveur Tweety"
                    + (f" — {pl_cause_text}" if pl_cause_text else "")
                    + ")"
                ),
                target_arg_id="—",
            )
        )
    if fol_inc:
        # #3107 — the cause the writer stated, when one was stated. Without
        # it this label said only "inconsistent", and the conclusion supplied
        # the rest: on a two-speaker document it read as one speaker's
        # reasoning invalidated, pinned on quantifier scope by the synthesis.
        cause_text = " ; ".join(fol_causes or [])
        points.append(
            StructuringWeakPoint(
                source="fol",
                label=(
                    f"{accord(fol_inc, 'théorie du premier ordre inconsistante', 'théories du premier ordre inconsistantes')} "
                    f"(solveur Tweety"
                    + (f" — {cause_text}" if cause_text else "")
                    + ")"
                ),
                target_arg_id="—",
            )
        )
    return points


def _collect_quality_strengths(
    quality: Dict[str, Any], units_total: int
) -> List[QualityStrength]:
    """Surface the virtues where the discourse genuinely holds (honest strengths).

    #1907 cross-act residue: with no threshold, the top-N of a weak set
    reached the conductor under a slot labelled ``[CE QUI TIENT — forces]``
    while Act II said of the same axis that it does not discriminate (real
    run: best score of the discourse 0.5, clarity floor 0.2). A force is
    therefore a virtue that reached the quality instrument's TOP band on at
    least one argument — the canonical scale is ``{0.0, 0.2, 0.5, 1.0}``
    (``_snap_to_scale``, shared by the lexical and agentic detectors), where
    0.5 is the instrument's own "partiel" wording: a partial is not "ce qui
    tient". Values >= 1.0 from non-canonical writers still qualify.

    #3137: the strength keeps the max score (best tenue on that virtue) AND
    its population — k arguments at the top band, of m evaluated (whose
    scores carry the virtue), of N units. One top-band argument of 8 is not
    "the discourse's best score": the counts flow to the writer, who owns
    the generalisation rule. When no virtue qualifies, the empty list flows
    into the prompt's pre-existing honest-absence wording — the axis stays
    *measured* (Act II may still weave virtues as character); what empties
    is praise, not measurement.
    """
    _STRENGTH_MIN_SCORE = 1.0
    best: Dict[str, float] = {}
    at_top: Dict[str, int] = {}
    evaluated: Dict[str, int] = {}
    for _arg, qs in quality.items():
        if not isinstance(qs, dict):
            continue
        # Canonical writer key is ``scores`` (shared_state.add_quality_score,
        # #1150/#1151); ``scores_par_vertu`` is the legacy key kept as a
        # fallback for any external source. Same {virtue: float} mapping.
        spv = qs.get("scores")
        if not isinstance(spv, dict):
            spv = qs.get("scores_par_vertu")
        if not isinstance(spv, dict):
            continue
        for vname, vval in spv.items():
            vname_s = str(vname)
            if not isinstance(vval, (int, float)):
                continue
            evaluated[vname_s] = evaluated.get(vname_s, 0) + 1
            if float(vval) >= _STRENGTH_MIN_SCORE:
                best[vname_s] = max(best.get(vname_s, 0.0), float(vval))
                at_top[vname_s] = at_top.get(vname_s, 0) + 1
    return [
        QualityStrength(
            virtue=k,
            score=v,
            args_at_top=at_top[k],
            args_evaluated=evaluated[k],
            units_total=units_total,
        )
        for k, v in sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    ]


# The bar at which a virtue may be said OF the discourse (3/4 of the evaluated
# arguments). #3137 shipped it as a rule FOR THE WRITER; R1107's first
# post-#3143 render broke it (clarté at 4/8 said « generally clear », no base).
# A rule the writer can break is not a guarantee — the producer now states the
# discourse-level sentence itself and the writer copies it (#3159).
_DISCOURSE_BAR = 0.75

# #3244 — the reader-facing name of each virtue, for the verdict sentence
# ONLY. The sentence is code-written and copied verbatim (« reprends-le tel
# quel »), so the identifier it interpolated reached the reader (R1111a:
# « refutation_constructive », « redondance_faible »; R1110b: « clarte »).
# The state's identifiers are NOT renamed — ``VERTUES``, the quality plugin
# and every reader keyed by them keep the ids; the strengths list below in
# the prompt keeps them too (the data side, the ``social_choice`` precedent
# #3238). An id missing here falls through as itself and reddens the
# totality witness (the mapping reads the producer's own ``VERTUES``).
VIRTUE_DISPLAY_FR = {
    "clarte": "clarté",
    "pertinence": "pertinence",
    "presence_sources": "présence de sources",
    "refutation_constructive": "réfutation constructive",
    "structure_logique": "structure logique",
    "analogie_pertinente": "analogie pertinente",
    "fiabilite_sources": "fiabilité des sources",
    "exhaustivite": "exhaustivité",
    "redondance_faible": "faible redondance",
}


def _passed_strengths(strengths: List[QualityStrength]) -> List[QualityStrength]:
    """The strengths that reach the discourse bar (#3159)."""
    return [
        s
        for s in strengths
        if s.args_evaluated and (s.args_at_top / s.args_evaluated) >= _DISCOURSE_BAR
    ]


def _named_passed_virtues(strengths: List[QualityStrength]) -> str:
    """The virtues that reach the bar, each with its measured base (#3159).

    Empty when none does — the caller then speaks the honest absence instead.
    """
    passed = _passed_strengths(strengths)
    # #3394 — the count says what it counts: « 7/8 » alone never named its
    # bar, and the reader could not tell a thin base from a strong one. The
    # bar that admits a virtue to the discourse statement (3/4 of the
    # arguments the quality pass evaluated) rides the clause itself.
    # « k/m arguments évalués » stays contiguous — ``_VERDICT_BASE_RE``
    # (the woven-restatement removal) is anchored on that exact shape.
    bar = f"{Fraction(str(_DISCOURSE_BAR)).limit_denominator(4)}"
    return " ; ".join(
        f"{VIRTUE_DISPLAY_FR.get(s.virtue, s.virtue)} "
        f"({s.args_at_top}/{s.args_evaluated} arguments évalués "
        f"— barre : {bar} des arguments évalués, {s.units_total} unités)"
        for s in passed
    )


def discourse_virtue_sentence(strengths: List[QualityStrength]) -> str:
    """The discourse-level virtue statement, pre-composed (#3159).

    Names every virtue that reaches the bar with its measured base (k/m
    arguments evaluated, N units), and says plainly when none does — the
    honest absence replaces the rule, it does not soften it. Each virtue is
    named by its reader-facing French (#3244, ``VIRTUE_DISPLAY_FR``), so no
    identifier rides it.

    #3335 (#3182 shape) — the sentence is no longer handed over for the
    writer to copy. Three paid passes out of three paraphrased it and dropped
    its base (« Le discours a de vraies qualités : il réfute… »), the last of
    them adding « surtout » and « souvent », which nothing measures: an
    instruction with no post-generation check is not a guarantee (#3134
    lesson). The passing branch now returns the READER sentence, and the
    pipeline grafts it under :data:`VERDICT_HEADING` after the prose. The
    absent branch keeps its instruction — there is nothing to print when no
    virtue reaches the bar, and the writer still has to attribute each virtue
    to the arguments that carry it, with its base.
    """
    named = _named_passed_virtues(strengths)
    if not named:
        return (
            "VERDICT PRÉ-CALCULÉ : aucune vertu n'atteint 3/4 des arguments "
            "évalués — aucune ne se dit DU DISCOURS. Attribue chaque vertu aux "
            "arguments qui la portent, avec sa base."
        )
    return f"Le discours tient sur {named}. Aucune autre vertu ne se dit du discours."


def discourse_virtue_reader_sentence(strengths: List[QualityStrength]) -> str:
    """The verdict sentence the pipeline prints itself, or ``""`` (#3335).

    Empty when no virtue reaches the bar: the absent case has no reader
    sentence — its prompt keeps the coding instruction, and no passage is
    grafted (the DoD's positive control).
    """
    named = _named_passed_virtues(strengths)
    if not named:
        return ""
    return f"Le discours tient sur {named}. Aucune autre vertu ne se dit du discours."


#: Reader-facing heading of the grafted verdict, #3335 — same shape as the
#: coverage passage's (#3159): the provenance is part of the heading, so the
#: reader knows the figures are the pipeline's, not the prose's. No issue
#: number on a reader surface (#3225).
VERDICT_HEADING = "Verdict sur les vertus (chiffres du pipeline)"

#: The pipeline sentence's closing clause, AS PROSE REPRODUCES IT (#3335).
#: All three paid passes kept a variant of it — « Aucune autre vertu ne s'en
#: dit. », « pas d'autre vertu établie. » — because it is the one part of the
#: handed-over sentence the writer could restate without inventing anything.
#: It anchors the woven verdict: the sentences just before it, in the same
#: paragraph, are what the grafted sentence replaces.
_VERDICT_RESTRICTION_RE = re.compile(
    r"\baucune\s+autre\s+vertu\b|\bpas\s+d['’]autre\s+vertu\b"
    r"|\baucune\s+vertu\s+d['’]autre\b",
    re.IGNORECASE,
)


#: How prose writes each virtue the quality pass measures (#3335). Only the
#: virtues that actually reached the bar are looked up, so an act discussing
#: « les sources » when no source virtue passed is never touched. The forms
#: are the ones the three paid renders used (« il réfute », « se répète
#: guère », « reste pertinent »), not the display labels.
_VIRTUE_PROSE_RE: Dict[str, Any] = {
    "clarte": re.compile(r"\bclair\w*|\bclart[ée]\b", re.IGNORECASE),
    "pertinence": re.compile(r"\bpertinen\w*", re.IGNORECASE),
    "presence_sources": re.compile(r"\bsources?\b", re.IGNORECASE),
    "refutation_constructive": re.compile(r"\br[ée]fut\w*", re.IGNORECASE),
    "structure_logique": re.compile(
        r"\bstructure\s+logique|\bstructurel\w*", re.IGNORECASE
    ),
    "analogie_pertinente": re.compile(r"\banalog\w*", re.IGNORECASE),
    "fiabilite_sources": re.compile(r"\bfiabilit\w*", re.IGNORECASE),
    "exhaustivite": re.compile(r"\bexhausti\w*", re.IGNORECASE),
    "redondance_faible": re.compile(r"\bredondan\w*|\br[ée]p[ée]t\w*", re.IGNORECASE),
}

#: The measured base the pipeline owns (#3335): « (7/8 arguments évalués,
#: 89 unités) ». A woven sentence carrying it verbatim is the writer copying
#: the handed sentence — removed like the paraphrase, the graft carries it.
_VERDICT_BASE_RE = re.compile(
    r"\d+\s*/\s*\d+\s+arguments?\s+[ée]valu[ée]s?", re.IGNORECASE
)

#: #3348 — the discourse as grammatical subject, sentence-initial: « Le
#: discours a un vrai caractère de clarté… ». The verdict speaks OF the
#: discourse, and a restatement of it keeps that subject; « que faire »
#: beats and per-argument sentences start differently by construction.
_DISCOURSE_SUBJECT_RE = re.compile(r"^(?:le|ce)\s+discours\b", re.IGNORECASE)


def restated_verdict_sentences(text: str, passed_virtues: Iterable[str]) -> List[str]:
    """The woven sentences that restate the virtue verdict (#3335, #3348).

    Two independent anchors. The first is the pipeline sentence's closing
    clause (« aucune autre vertu … »), extended BACKWARDS over the sentences
    of the same paragraph that name a virtue which reached the bar or
    reproduce the measured base. The second (#3348) is the clause-less
    restatement R1133a wove: the discourse as grammatical subject, naming
    every virtue that crossed the bar AND no virtue the bar rejected — a
    restatement can only copy what the verdict names, and a sentence
    asserting a rejected virtue commits the claim gate's defect, not this
    one's, so the rest of its sentence is not this removal's to delete
    (census on the stored states: the one literal-class match named « clair »
    with clarté below the bar — out of class, kept).

    Bounded on purpose in both anchors: the clause walk never leaves its
    paragraph, the sentence-level anchor never walks at all, and a sentence
    of the « que faire » beat — different subject, or fewer virtues — is
    never touched. The pipeline's own grafted passage is not food either:
    its paragraph is skipped, so the removal stays safe on a final render.
    A false positive here would delete content, which is the unsafe side of
    the trade; the anchors are what keep it off.

    ``passed_virtues`` is the set of virtue keys that crossed the bar: the
    vocabulary looked for is bounded by what the verdict actually names.
    """
    passed = [v for v in passed_virtues if v in _VIRTUE_PROSE_RE]
    wanted = [_VIRTUE_PROSE_RE[v] for v in passed]
    if not wanted:
        return []
    rejected = [_VIRTUE_PROSE_RE[k] for k in _VIRTUE_PROSE_RE if k not in set(passed)]
    caught: List[str] = []
    for paragraph in re.split(r"\n\s*\n", text or ""):
        if paragraph.lstrip().startswith(f"**{VERDICT_HEADING}**"):
            # The pipeline's own grafted passage (#3335) — never food.
            continue
        sentences = [s.strip() for s in _SENTENCE_RE.findall(paragraph) if s.strip()]
        for index in range(len(sentences) - 1, -1, -1):
            sentence = sentences[index]
            if not _VERDICT_RESTRICTION_RE.search(sentence):
                continue
            caught.append(sentence)
            back = index - 1
            while back >= 0:
                candidate = sentences[back]
                if candidate.lstrip().startswith("#"):
                    break
                names_virtue = any(rx.search(candidate) for rx in wanted)
                states_base = bool(_VERDICT_BASE_RE.search(candidate))
                if not (names_virtue or states_base):
                    break
                caught.append(candidate)
                back -= 1
            break
        for sentence in sentences:
            # #3348 — the clause-less restatement: discourse subject, every
            # passed virtue named, no rejected one.
            if sentence in caught:
                continue
            if not _DISCOURSE_SUBJECT_RE.match(sentence):
                continue
            if not all(rx.search(sentence) for rx in wanted):
                continue
            if any(rx.search(sentence) for rx in rejected):
                continue
            caught.append(sentence)
    return caught


def format_verdict_passage(sentence: str) -> str:
    """The verdict passage the act grafts after its prose (#3335).

    Empty when the state names no virtue above the bar: no measured verdict →
    no sentence, never a fabricated one.
    """
    if not (sentence or "").strip():
        return ""
    return f"**{VERDICT_HEADING}**\n{sentence.strip()}"


def _collect_governance(state: Any) -> Optional[GovernanceVerdict]:
    """Collect the governance voting verdict (SV #1182).

    Reads ``state.governance_decisions``; surfaces the LAST non-trivial decision.
    Fail-loud: ``None`` when empty or winner is a placeholder ("N/A"/empty) —
    no fabricated verdict (#1019). Privacy: option keys stay opaque.
    """
    decisions = getattr(state, "governance_decisions", []) or []
    if not isinstance(decisions, list):
        return None
    chosen: Optional[GovernanceVerdict] = None
    for d in decisions:
        if not isinstance(d, dict):
            continue
        method = str(d.get("method", "")).strip()
        winner = str(d.get("winner", "")).strip()
        if not method or not winner or winner == "N/A":
            continue
        raw_scores = d.get("scores", {}) or {}
        scores: Dict[str, float] = {}
        if isinstance(raw_scores, dict):
            for k, v in raw_scores.items():
                try:
                    scores[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        # #3001 (a′) — the support population (vote records only; honest
        # absence when the record carries none).
        raw_support = d.get("support_by_option", {}) or {}
        support_by_option: Dict[str, int] = {}
        if isinstance(raw_support, dict):
            for k, v in raw_support.items():
                if isinstance(v, int) and v > 0:
                    support_by_option[str(k)] = v
        n_raw = d.get("n_methods_decided")
        n_methods_decided = n_raw if isinstance(n_raw, int) and n_raw > 0 else None
        wb_raw = d.get("winner_basis")
        winner_basis = (
            str(wb_raw).strip()
            if isinstance(wb_raw, str) and str(wb_raw).strip()
            else None
        )
        # #3394 cycle 2 — the methods' names per option (honest absence when
        # the record carries none).
        raw_methods = d.get("methods_by_option", {}) or {}
        methods_by_option: Dict[str, List[str]] = {}
        if isinstance(raw_methods, dict):
            for k, names in raw_methods.items():
                if isinstance(names, list):
                    kept = [str(n) for n in names if isinstance(n, str) and n.strip()]
                    if kept:
                        methods_by_option[str(k)] = kept
        # #3394 (tranche R1145) — the protocols, named apart (honest absence
        # when the record carries none: no protocol clause invented).
        raw_protocols = d.get("consensus_protocols", {}) or {}
        consensus_protocols: Dict[str, str] = {}
        if isinstance(raw_protocols, dict):
            for k, v in raw_protocols.items():
                if isinstance(v, str) and v.strip():
                    consensus_protocols[str(k)] = v
        chosen = GovernanceVerdict(
            method=method,
            winner=winner,
            scores=scores,
            winners=[
                str(w)
                for w in (d.get("winners") or [])
                if isinstance(w, str) and w.strip()
            ],
            # #2965 / R1077 — the origin the conclusion must frame on (#2969).
            winner_provenance=(
                str(d["winner_provenance"]).strip()
                if isinstance(d.get("winner_provenance"), str)
                and str(d["winner_provenance"]).strip()
                else None
            ),
            method_provenance=(
                str(d["method_provenance"]).strip()
                if isinstance(d.get("method_provenance"), str)
                and str(d["method_provenance"]).strip()
                else None
            ),
            # #3001 — the qualitative robustness band's inputs.
            support_by_option=support_by_option,
            n_methods_decided=n_methods_decided,
            winner_basis=winner_basis,
            # #3394 cycle 2 — the names behind the counts.
            methods_by_option=methods_by_option,
            # #3394 (tranche R1145) — the protocols, named apart.
            consensus_protocols=consensus_protocols,
            # #3386 — the producer-rendered coalition block ("" when the
            # play changed nothing).
            coalition_note=coalition_note(d),
        )
    return chosen


def _collect_absent_dimensions(state: Any) -> List[AbsentDimension]:
    """Collect the dimensions the run did not genuinely evaluate (#1605).

    Reads ``state.structured_arg_status``, the honest-absence ledger written by
    ``state_writers._record_structured_arg_status``. Measured on three real
    corpora: A lost 4 axes of 5, B lost none, C lost 2 — and the conclusion read
    identically in all three, because nothing here reached the restitution.

    Only genuinely-degraded entries are surfaced. An ``evaluated`` capability is
    not an absence, and an axis that simply found nothing to report is NOT a
    degradation (anti-pendule: an honest absence correctly labelled is a success
    of the matrix, not a failure of the pipeline).

    #2344: the ledger covers the structured-argumentation axes only. The formal
    PL/FOL axes that ran without deciding anything join the list through
    :func:`_collect_undecided_formal_axes`.
    """
    ledger = getattr(state, "structured_arg_status", None) or {}
    out: List[AbsentDimension] = []
    if isinstance(ledger, dict):
        for capability, info in ledger.items():
            if not isinstance(info, dict) or not info.get("degraded"):
                continue
            cap = str(capability)
            out.append(
                AbsentDimension(
                    capability=cap,
                    label=_ABSENT_DIMENSION_LABELS.get(cap, cap.replace("_", " ")),
                    status=str(info.get("status", "")).strip(),
                    reason=_truncate(info.get("reason", ""), _ABSENCE_REASON_CAP),
                )
            )
    out.extend(_collect_undecided_formal_axes(state))
    out.extend(_collect_local_llm_dimension(state))
    return sorted(out, key=lambda d: d.label)


def _collect_local_llm_dimension(state: Any) -> List[AbsentDimension]:
    """#3131 — the local tier's skip/error, as a lost dimension.

    ``state.local_llm_results`` carries the phase's own statuses since #3113:
    ``skipped: not_configured``, ``skipped: endpoint_unavailable``, ``error``.
    The tier is a dimension the run did not evaluate when any of them is the
    last word, and the conclusion's scope must say so, the same as any
    structured axis that never ran. A completed record is not an absence
    (the tier spoke — its reading line, not this ledger, carries it); an
    empty list is not one either (the phase was never in this workflow —
    silence, like every unrecorded site).

    The reason mirrors the family contract — the producer's own message for
    an error (capped like every ledger reason), a code-authored French
    sentence for the two skips, whose cause is a configuration fact the
    record already names.
    """
    records = getattr(state, "local_llm_results", None)
    if not isinstance(records, list) or not records:
        return []
    last = records[-1]
    if not isinstance(last, dict):
        return []
    status = str(last.get("status", "") or "")
    if status == "completed":
        return []
    if status == "skipped: not_configured":
        reason = "aucun endpoint local configuré — le palier n'a pas été sollicité"
    elif status == "skipped: endpoint_unavailable":
        reason = "l'endpoint local était injoignable au moment de la phase"
    else:
        reason = _truncate(
            str(last.get("error", "") or "") or "erreur d'appel", _ABSENCE_REASON_CAP
        )
    return [
        AbsentDimension(
            capability="local_llm",
            label=_ABSENT_DIMENSION_LABELS.get("local_llm", "local llm"),
            status=status,
            reason=reason,
        )
    ]


def _collect_undecided_formal_axes(state: Any) -> List[AbsentDimension]:
    """The formal axes whose every result came back undecided (#2344).

    ``_pl_verified``/``_fol_verified`` count decided verdicts only, which is
    right for the band. But they made an axis that ran and broke read exactly
    like an axis that never ran: results in the state, none decided (the
    translation produced nothing, the parser rejected everything, the solver
    raised or is not installed). Measured: same prompt, same conclusion, same
    ``degraded``. Such an axis was not evaluated, and the absence channel says
    so, with the producer's own message as the reason.

    An axis with at least one decided result is not lost: the conclusion stands
    on its decided results, and the appendix counts the undecided ones
    (``degradees``). An axis with no result at all is not lost either: it did
    not run, so nothing broke.
    """
    out: List[AbsentDimension] = []
    for axis, container, verdict in (
        (_AXIS_FORMAL_PL, "propositional_analysis_results", _pl_verdict),
        (_AXIS_FORMAL_FOL, "fol_analysis_results", _fol_verdict),
    ):
        results = getattr(state, container, None)
        if not isinstance(results, list):
            continue
        host = [
            r for r in results if isinstance(r, dict) and not _is_guest_formal_entry(r)
        ]
        if not host or any(verdict(r) is not None for r in host):
            continue
        cause = next((str(r["message"]).strip() for r in host if r.get("message")), "")
        reason = f"{accord(len(host), 'résultat', 'résultats')} sans verdict décidé"
        out.append(
            AbsentDimension(
                capability=axis,
                label=_AXIS_LABELS_FR[axis],
                status="undecided",
                reason=_truncate(
                    f"{reason} : {cause}" if cause else f"{reason}.",
                    _ABSENCE_REASON_CAP,
                ),
            )
        )
    return out


def _axis_label(capability: str) -> str:
    """Reader-facing French name of a structured-argumentation axis.

    Shares :data:`_ABSENT_DIMENSION_LABELS` with the absence ledger on purpose:
    the French name of an axis does not depend on whether it succeeded. Only the
    sentence built around it does.
    """
    return _ABSENT_DIMENSION_LABELS.get(capability, capability.replace("_", " "))


def _cycle_phrase(nodes: List[str]) -> str:
    """French prose naming a support-cycle group as circular authority (#1645).

    ``nodes`` is a sorted list of opaque argument identifiers locked in a
    mutual-support cycle (a non-trivial SCC of the support digraph). The
    phrasing distinguishes the 2-cycle (the canonical « se soutiennent
    mutuellement »), longer cycles, and the degenerate self-support. The verdict
    « autorité circulaire » is appended so the structural figure is NAMED, not
    merely described — this is the projection no attack-only axis or LLM fallacy
    detector can produce.
    """
    if len(nodes) == 1:
        return (
            f"« {nodes[0]} » se soutient lui-même, sans ancrage externe "
            f"(autorité circulaire)"
        )
    if len(nodes) == 2:
        return (
            f"« {nodes[0]} » et « {nodes[1]} » se soutiennent mutuellement, "
            f"sans ancrage externe (autorité circulaire)"
        )
    joined = ", ".join(f"« {n} »" for n in nodes)
    return f"{joined} forment un cycle de soutien sans ancrage externe (autorité circulaire)"


def _player_for_point(
    state: Any, node_id: str, dependent_ids: Sequence[str]
) -> Optional[str]:
    """The strategist's player whose case rests on this articulation point (#3544).

    The players carry a located quote (``offset`` + text); the units carry
    their located source quotes through ``argument_provenance``. A player's
    case DEPENDS on the point when the player's quoted ground overlaps the
    node itself (they quote the aside) or one of its dependents (they quote
    the claim only the aside supports) — both are the figure the sentence
    states, and on the panel the dependent side is the one that fires (2 of
    44 points on the node, 7 of 44 on a dependent). Players are read in the
    strategist's own order (salience, the #3386 convention) and the first
    overlap wins; a player without a located quote claims no ground, and a
    point without provenance names no player. The sentence then names that
    player, or no player at all when none is recorded — never an invented
    attribution.
    """
    provenance = getattr(state, "argument_provenance", None)
    if not isinstance(provenance, dict):
        return None

    def _span(unit_id: str) -> Optional[Tuple[int, int]]:
        entry = provenance.get(unit_id)
        if not isinstance(entry, dict):
            return None
        offset = entry.get("offset")
        quote = str(entry.get("source_quote") or "")
        if not isinstance(offset, int) or isinstance(offset, bool) or not quote:
            return None
        return (offset, offset + len(quote))

    spans = [
        s for s in (_span(uid) for uid in [node_id, *dependent_ids]) if s is not None
    ]
    if not spans:
        return None
    read = getattr(state, "strategic_read", None)
    players = read.get("players") if isinstance(read, dict) else None
    for player in players or []:
        if not isinstance(player, dict):
            continue
        offset = player.get("offset")
        quote = str(player.get("quote") or "")
        name = str(player.get("name") or "").strip()
        if not isinstance(offset, int) or isinstance(offset, bool):
            continue
        if not quote or not name:
            continue
        end = offset + len(quote)
        if any(s[0] < end and offset < s[1] for s in spans):
            return name
    return None


def _articulation_phrase(
    node: str, dependents: List[str], player: Optional[str] = None
) -> str:
    """French prose naming a sole-supporter articulation point (#1645 PR2).

    The figure: an argument that is the ONLY backer of one or more others, so
    removing it would collapse their support — the "remark presented as
    incidental that structurally carries the weight" (issue B-insight-3).
    Naming the figure (``point d'articulation``) is the projection no other
    axis produces; the dependent count conveys how much rests on it.

    #3544 — the node and its dependents arrive as TEXT (resolved through the
    entry's ``argument_labels`` by the caller), and ``player`` names whose
    case depends on the point when the strategist's players carry the
    ground; ``None`` names no player.
    """
    node_t = _truncate(node, _SUPPORT_NODE_CAP)
    deps_t = [_truncate(d, _SUPPORT_NODE_CAP) for d in dependents if d]
    figure = (
        f"point d'articulation dont le cas de {player} dépend"
        if player
        else "point d'articulation"
    )
    if len(deps_t) == 1:
        return (
            f"« {node_t} » est le seul appui de « {deps_t[0]} » : le retirer "
            f"lui ferait perdre tout soutien ({figure})"
        )
    listed = ", ".join(f"« {d} »" for d in deps_t)
    return (
        f"« {node_t} » est le seul appui de {len(deps_t)} arguments ({listed}) : "
        f"le retirer ferait s'effondrer leur soutien ({figure})"
    )


def _bipolar_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the SUPPORT relation — what bipolar argumentation alone says.

    Dung frameworks carry attacks only; ``supports`` is the relation no other
    axis in the pipeline computes. Its two distinctive structural properties,
    both NAMED here (not recopied) when populated (#1645):
    1. **support cycles** (circular authority) — arguments backing each other
       with no external anchor;
    2. **articulation points** — an argument that is the SOLE support of one or
       more others, so removing it collapses their support.
    Both are invisible to attack-only frameworks and to LLM fallacy detection.
    When neither is present, the support pairs are projected descriptively as a
    fallback.

    Returns ``None`` when no well-formed pair AND no cycle/articulation exists
    (fail-loud #1019: an empty support set is an honest absence, never a
    fabricated sentence).
    """
    entries = getattr(state, "bipolar_results", None) or []
    if not isinstance(entries, list):
        return None

    # Priority insight (#1645 section A): support cycles = circular authority.
    # NAME it — this is the projection no other axis can produce. A cycle is a
    # structural fact the text does not contain, so naming it is not a recopy
    # (anti-pendulum C: "si le texte le dit, on mesure une recopie").
    # #3544 — the cycle's nodes render as TEXT through the entry's labels,
    # exactly like the articulation phrase below (ids give the writer nothing
    # to describe — the #3156 lesson).
    cycle_parts: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_labels = entry.get("argument_labels")
        labels = entry_labels if isinstance(entry_labels, dict) else {}
        for group in entry.get("support_cycles") or []:
            if not isinstance(group, list):
                continue
            nodes = [
                _truncate(
                    _resolve_unit_label(labels, str(n).strip()), _SUPPORT_NODE_CAP
                )
                for n in group
                if str(n).strip()
            ]
            if nodes:
                cycle_parts.append(_cycle_phrase(nodes))
                if len(cycle_parts) >= _SUPPORT_CYCLE_CAP:
                    break
        if len(cycle_parts) >= _SUPPORT_CYCLE_CAP:
            break
    if cycle_parts:
        return StructuredArgFinding(
            capability="bipolar_argumentation",
            label=_axis_label("bipolar_argumentation"),
            statement=" ; ".join(cycle_parts),
        )

    # Second insight (#1645 PR2, B-insight-3): articulation points = sole
    # supporter. NAME the figure ("point d'articulation") — the gap between
    # structural weight and displayed importance. Same anti-recopy rationale.
    # #3544 — the node and its dependents render as TEXT through the entry's
    # ``argument_labels`` (falling back to the id when no label exists), and
    # the phrase names the player whose case carries the point when the
    # strategist's players locate the ground.
    articulation_parts: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_labels = entry.get("argument_labels")
        labels = entry_labels if isinstance(entry_labels, dict) else {}
        for ap in entry.get("articulation_points") or []:
            if not isinstance(ap, dict):
                continue
            node_id = str(ap.get("node", "")).strip()
            if not node_id:
                continue
            deps_raw = ap.get("dependents") or []
            dep_ids = [str(d).strip() for d in deps_raw if str(d).strip()]
            deps = [_resolve_unit_label(labels, d) for d in dep_ids]
            if deps:
                articulation_parts.append(
                    _articulation_phrase(
                        _resolve_unit_label(labels, node_id),
                        deps,
                        _player_for_point(state, node_id, dep_ids),
                    )
                )
                if len(articulation_parts) >= _ARTICULATION_CAP:
                    break
        if len(articulation_parts) >= _ARTICULATION_CAP:
            break
    if articulation_parts:
        return StructuredArgFinding(
            capability="bipolar_argumentation",
            label=_axis_label("bipolar_argumentation"),
            statement=" ; ".join(articulation_parts),
        )

    # Fallback (no cycle, no articulation): descriptive projection of the pairs.
    pairs: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        supports = entry.get("supports") or []
        if not isinstance(supports, list):
            continue
        for pair in supports:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            source = _truncate(str(pair[0]).strip(), _SUPPORT_NODE_CAP)
            target = _truncate(str(pair[1]).strip(), _SUPPORT_NODE_CAP)
            if not source or not target:
                continue
            pairs.append(f"« {source} » appuie « {target} »")
            if len(pairs) >= _SUPPORT_PAIR_CAP:
                break
        if len(pairs) >= _SUPPORT_PAIR_CAP:
            break
    if not pairs:
        return None
    return StructuredArgFinding(
        capability="bipolar_argumentation",
        label=_axis_label("bipolar_argumentation"),
        statement="; ".join(pairs),
    )


def _jtms_counterfactual_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the counterfactual the JTMS pass measured on a copy (#3547).

    Today the pipeline retracts a belief only when a fallacy targets it — the
    retraction chain names what DID fall. This axis names the other direction,
    which no other axis computes: which premises CARRY weight they never
    display, in the sense that withdrawing one would drop other beliefs' only
    justification. The records carry text (never a bare id — the #3156
    lesson) and unit ids for the persona lookup; a withdrawal record is
    rendered as the issue's canonical sentence: premise named, falls named,
    the rest holding. The persona names the strategist's player whose case
    rests on the ground, when the players locate it (#3544's convention).

    Returns ``None`` when no withdrawal drops anything (an honest absence —
    no premise carries that weight), never a fabricated sentence.
    """
    entries = getattr(state, "jtms_counterfactual_withdrawals", None) or []
    if not isinstance(entries, list):
        return None
    parts: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or len(parts) >= _ARTICULATION_CAP:
            continue
        premise = _truncate(str(entry.get("text") or "").strip(), _SUPPORT_NODE_CAP)
        if not premise:
            continue
        fall_texts = [
            _truncate(str(f.get("text") or "").strip(), _SUPPORT_NODE_CAP)
            for f in entry.get("falls") or []
            if isinstance(f, dict) and str(f.get("text") or "").strip()
        ]
        if not fall_texts:
            continue
        listed = " et ".join(f"« {t} »" for t in fall_texts)
        verb = (
            "perd sa seule justification"
            if len(fall_texts) == 1
            else "perdent leur seule justification"
        )
        sentence = f"si « {premise} » est retiré, {listed} {verb} ; le reste tient"
        premise_id = entry.get("premise_unit_id")
        fall_ids = [
            str(f.get("unit_id"))
            for f in entry.get("falls") or []
            if isinstance(f, dict) and f.get("unit_id")
        ]
        if isinstance(premise_id, str) and premise_id:
            player = _player_for_point(state, premise_id, fall_ids)
            if player:
                sentence += f" (le cas de {player} repose sur cet appui)"
        parts.append(sentence)
    if not parts:
        return None
    return StructuredArgFinding(
        capability="belief_maintenance",
        label=_axis_label("belief_maintenance"),
        statement=" ; ".join(parts),
    )


def _aspic_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project what ASPIC+ alone establishes, in priority order (#1649).

    An ASPIC+ argument is a derivation *through rules*, so what this axis brings
    that no other does is naming HOW derivations conflict — the attack SCOPE
    (undercut = the inference link itself contested; rebut = a conclusion
    contradicted; undermine = a premise attacked). Undercut has no equivalent
    anywhere in the stack; that is the singular contribution (#1649).

    Emission is gated, in priority order, each gate measured firsthand:

    1. **Qualified attacks** (``aspic_results[*].attacks``, #1649). The producer
       (#1678 handler ``_qualify_attacks`` + #1679 translator emitting
       ``head_negated`` rules) fires real attacks only when genuine contraries
       are supplied — a ``Negation(Proposition(head))``, not a head string
       carrying ``"!"`` (the latter is absorbed into the identifier, measured 0
       attack), and only when the generated Dung framework actually materialised
       an edge (``dung_attacks > 0`` gate). An empty ``attacks`` list is the
       honest "ran, no attack", never a dropped field (#1681 writer carries it).
       The statement names the scope DISTRIBUTION only — never the raw target
       atoms (source-derived via ``_pl_atom``, privacy HARD).
    2. **Contested sets** (fallback, pre-#1649 finding). At least two distinct
       non-empty extensions: what some extensions keep and others drop. A single
       all-inclusive extension arbitrated nothing; reporting it would hand the
       conclusion a formally-authorised statement with no discriminating content
       (#1631).

    Nothing to say on either → ``None`` (honest absence, never a status word).
    """
    entries = getattr(state, "aspic_results", None) or []
    if not isinstance(entries, list):
        return None
    contested: List[str] = []
    # #1649: aggregate qualified attack scopes across entries. The producer
    # (#1678 handler + #1679 translator) emits ``attacks[*].scope`` in
    # {undercut, rebut, undermine, unresolved}, gated on ``dung_attacks > 0``
    # so an empty list is the honest "ran, no attack" (never a dropped field).
    # Undercut is the singular contribution — no other axis names it.
    scope_counts: Dict[str, int] = {s: 0 for s in _ASPIC_ATTACK_SCOPES}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for atk in entry.get("attacks") or []:
            if not isinstance(atk, dict):
                continue
            scope = str(atk.get("scope", "unresolved"))
            if scope not in scope_counts:
                scope = "unresolved"
            scope_counts[scope] += 1
        extensions = entry.get("extensions") or []
        if not isinstance(extensions, list):
            continue
        distinct: List[frozenset[str]] = []
        for ext in extensions:
            if not isinstance(ext, (list, tuple)):
                continue
            members = frozenset(
                _truncate(str(m).strip(), _ASPIC_MEMBER_CAP)
                for m in ext
                if str(m).strip()
            )
            if members and members not in distinct:
                distinct.append(members)
        # One extension (or one repeated) = nothing was arbitrated.
        if len(distinct) < 2:
            continue
        union = frozenset().union(*distinct)
        intersection = frozenset.intersection(*distinct)
        entry_contested = sorted(union - intersection)
        if len(entry_contested) > len(contested):
            contested = entry_contested
    # #1649: attack scope is ASPIC+'s singular contribution and strictly more
    # specific than contested sets (which Dung preferred-semantics also yields),
    # so it leads the finding when the producer fired real attacks. Falls back
    # to contested sets, then to None — preserving the existing honest-absence
    # gate. Anti-#1019 (coord R782): the rendered statement CHANGES when
    # ``attacks`` changes; an empty/absent list yields no scope statement.
    if sum(scope_counts.values()) > 0:
        return StructuredArgFinding(
            capability="aspic_plus_reasoning",
            label=_axis_label("aspic_plus_reasoning"),
            statement=_aspic_attack_statement(scope_counts),
        )
    if not contested:
        return None
    shown = contested[:_ASPIC_MEMBERS_SHOWN]
    tail = (
        ""
        if len(contested) <= _ASPIC_MEMBERS_SHOWN
        else f" (et {accord(len(contested) - len(shown), 'autre', 'autres')})"
    )
    return StructuredArgFinding(
        capability="aspic_plus_reasoning",
        label=_axis_label("aspic_plus_reasoning"),
        statement=(
            "des enchaînements de raisonnement s'excluent mutuellement — "
            "le corpus ne permet pas de les tenir tous ensemble : "
            + " | ".join(shown)
            + tail
        ),
    )


def _iter_formalism_specific(state: Any, leaf: str) -> List[Any]:
    """Collect every non-empty ``leaf`` value across all dung_frameworks sidecars.

    #1667 axes 3/5 (ABA / SETAF / pondéré) store their distinctive data on the
    strictly-additive ``dung_frameworks[df_id].formalism_specific`` sidecar the
    #1648 writers attach — there is NO first-level ``aba_results`` /
    ``setaf_results`` / ``weighted_results`` (the dispatch measured it; the
    #1702 triage table established it writer-by-writer). This helper is the one
    reader of that sidecar across the three projectors — *one channel, not one
    reader per axis* (the eight-half-fixes lesson of #1633 restated at five
    sites). Each projector decides on its own what its axis has to say; this
    only hands it the sidecar leaves, defensively typed.
    """
    frameworks = getattr(state, "dung_frameworks", None)
    if not isinstance(frameworks, dict):
        return []
    out: List[Any] = []
    for entry in frameworks.values():
        if not isinstance(entry, dict):
            continue
        sidecar = entry.get("formalism_specific")
        if not isinstance(sidecar, dict):
            continue
        val = sidecar.get(leaf)
        if val:
            out.append(val)
    return out


def _iter_native_extension(state: Any, key: str) -> List[Any]:
    """Collect every non-empty ``key`` value across all dung_frameworks extensions.

    #2952 native counterpart of :func:`_iter_formalism_specific` — one channel
    for the ``extensions`` leaves the #1648/#2063 writers attach (DeLP's
    ``delp_query_results``, ADF's ``adf_models``), not one reader per axis.
    ``native_dung.extension_lists`` deliberately yields ``None`` on these
    entries (they are not acceptance-extension lists), so each of these keys
    has exactly one reader: this one. Defensively typed like its sibling.
    """
    frameworks = getattr(state, "dung_frameworks", None)
    if not isinstance(frameworks, dict):
        return []
    out: List[Any] = []
    for entry in frameworks.values():
        if not isinstance(entry, dict):
            continue
        exts = entry.get("extensions")
        if not isinstance(exts, dict):
            continue
        val = exts.get(key)
        if val:
            out.append(val)
    return out


def _aba_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the ASSUMPTION↔CONTRARY relation — what ABA alone says (#1667).

    ABA's distinctive data is the ``contraries`` mapping (assumption → its
    contrary), which lives on ``formalism_specific.contraries`` (#1648 Wave-2
    sidecar, writer ``_write_aba_to_state``). The relation an assumption holds
    *and* its contrary names what each side would have to give up — no other
    axis in the pipeline carries it (Dung is attack-only; ASPIC+ is rule-scope).

    The statement NAMES the contrary relation (truncated atoms — the sidecar is
    the surface #1702 scrubbed, so its atoms are corpus-derived via ``_pl_atom``
    and stay truncated here, same privacy bar as ``_aspic_finding``'s contested
    members). Not a count: ``3 résultats ABA`` would reproduce ``appendix.py``'s
    ``"disponible"`` one hop further — the witness moved, no decider created
    (anti-pendule #1667). Returns ``None`` when no contrary pair is populated
    (fail-loud #1019: an empty mapping is an honest absence, never fabricated).
    """
    pairs: List[str] = []
    for contraries in _iter_formalism_specific(state, "contraries"):
        if not isinstance(contraries, dict):
            continue
        for assumption, contrary in contraries.items():
            a = _truncate(str(assumption).strip(), _FORMALISM_NODE_CAP)
            c = _truncate(str(contrary).strip(), _FORMALISM_NODE_CAP)
            if a and c:
                # #3513 — the contraries are keyed by unit id (#3014), so the
                # shared qualifier resolves them exactly as it resolves a
                # SETAF target: a contrary of a REPORTED position names whose
                # camp the relation touches, never a guess.
                side = reported_position_qualifier(state, str(assumption).strip())
                pairs.append(f"« {a} »{side} a pour contraire « {c} »")
                if len(pairs) >= _ABA_CONTRARY_PAIR_CAP:
                    break
        if len(pairs) >= _ABA_CONTRARY_PAIR_CAP:
            break
    if not pairs:
        return None
    tail = "" if len(pairs) < _ABA_CONTRARY_PAIR_CAP else " (extrait partiel)"
    return StructuredArgFinding(
        capability="aba_reasoning",
        label=_axis_label("aba_reasoning"),
        statement=(
            "le cadre ABA pose des relations de contrariété entre hypothèses : "
            + " ; ".join(pairs)
            + tail
        ),
    )


def _setaf_coalitions_by_target(
    set_attacks: List[Any],
) -> Dict[str, List["frozenset[str]"]]:
    """#3162 — every attack ONE frame records, indexed by its target.

    Irreducibility is a property of a frame, not of a coalition in isolation:
    the same members may attack an atom here without attacking it there. The
    index is read per frame, exactly as ``_iter_formalism_specific`` yields it.
    """
    index: Dict[str, List["frozenset[str]"]] = {}
    for atk in set_attacks:
        if not isinstance(atk, dict):
            continue
        attackers = atk.get("attackers")
        target = atk.get("target")
        if not isinstance(attackers, list) or not isinstance(target, str):
            continue
        target_atom = target.strip()
        coalition = frozenset(str(a).strip() for a in attackers if str(a).strip())
        if target_atom and coalition:
            index.setdefault(target_atom, []).append(coalition)
    return index


_SETAF_REPORTED_QUALIFIER = "(position rapportée)"

#: #3513 — SETAF, Dung and ABA verdict lines read ONE qualifier function
#: (``reported_position_qualifier``), which lives beside the closed vocabulary
#: it reads. The local alias above is kept for the existing #3162 witnesses;
#: the function itself is the single reader.


def _setaf_target_side(state: Any, target: str) -> str:
    """#3162 item 2 — kept as the SETAF call shape; the read is shared.

    #3513 — the body moved to ``fallacy_attribution.reported_position_qualifier``
    so the Dung and ABA surfaces read the same raw provenance the same way.
    """
    return reported_position_qualifier(state, target)


def _setaf_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the COLLECTIVE attack — what SETAF alone says (#1667).

    SETAF's distinctive data is the ``set_attacks`` list
    (``{attackers: [atom, ...], target: atom}``), on
    ``formalism_specific.set_attacks`` (#1648 Wave-2 sidecar, writer
    ``_write_setaf_to_state``). The singularity is the **joint** attack: a
    *coalition* of arguments that defeats a target no member defeats alone —
    which binary (Dung) attacks cannot express. A unary set-attack (one
    attacker) IS a Dung attack and carries nothing SETAF-specific, so it is
    deliberately not projected here (honest absence, #1019: SETAF that emits
    only binary attacks added nothing the Dung projection did not already say).

    The statement NAMES the joint coalitions (truncated atoms — privacy HARD,
    same bar as ABA/ASPIC+). Not a count. Returns ``None`` when no joint attack
    is populated.
    """
    joint: List[str] = []
    for set_attacks in _iter_formalism_specific(state, "set_attacks"):
        if not isinstance(set_attacks, list):
            continue
        # #3162 — the frame's own attacks, so irreducibility is READ. The
        # docstring always stated the condition ("a target no member defeats
        # alone"); the code never tested it, so a coalition that is a superset
        # of an existing attack was still called irreducible and the prompt
        # carried a formal claim the frame refutes. Same frame only: the same
        # members attacking an atom elsewhere say nothing about this one.
        frame_index = _setaf_coalitions_by_target(set_attacks)
        for atk in set_attacks:
            if not isinstance(atk, dict):
                continue
            attackers = atk.get("attackers")
            target = atk.get("target")
            if not isinstance(attackers, list) or len(attackers) < 2:
                continue  # unary = a Dung attack, nothing SETAF-specific
            t = _truncate(str(target).strip(), _FORMALISM_NODE_CAP)
            if not t:
                continue
            named = [
                _truncate(str(a).strip(), _FORMALISM_NODE_CAP)
                for a in attackers
                if str(a).strip()
            ]
            named = [n for n in named if n]
            if len(named) < 2 or not t:
                continue
            # #3162 — reducible when a PROPER subset of the coalition already
            # attacks the same target in this frame (unary or smaller
            # coalition). The empty set is never stored, so ``<`` is enough.
            members = frozenset(str(a).strip() for a in attackers if str(a).strip())
            proper_subset = any(
                other < members for other in frame_index.get(str(target).strip(), [])
            )
            if proper_subset:
                continue
            listed = ", ".join(f"« {n} »" for n in named)
            # #3162 item 2 — whose position the TARGET is, when the state says
            # (raw provenance, same-target lookup; absent = no side claimed).
            side = _setaf_target_side(state, str(target).strip())
            joint.append(
                f"une coalition de {len(named)} arguments ({listed}) renverse "
                f"« {t} »{side} qu'aucun ne renverse seul"
            )
            if len(joint) >= _SETAF_JOINT_ATTACK_CAP:
                break
        if len(joint) >= _SETAF_JOINT_ATTACK_CAP:
            break
    if not joint:
        return None
    return StructuredArgFinding(
        capability="setaf_reasoning",
        label=_axis_label("setaf_reasoning"),
        statement=(
            "le cadre SETAF qualifie des attaques collectives irréductibles à "
            "des attaques binaires : " + " ; ".join(joint)
        ),
    )


def _weighted_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the WEIGHT distribution — what weighted AF alone says (#1667).

    Weighted AF's distinctive data is the numeric ``weight`` on each attack
    (``{source, target, weight}`` + optional ``weight_statistics``), on
    ``formalism_specific.attack_weights`` (#1648 Wave-2 sidecar, writer
    ``_write_weighted_to_state``). The singularity is that attacks carry
    *unequal force* — a binary attack graph treats all edges alike, so naming
    the weight distribution (range, mean) is the projection no other axis
    produces.

    Privacy: only numeric weights reach the prose (the source/target atoms are
    corpus-derived and stay out, like the aspic scope statement renders counts
    not targets). Not a count of attacks. Returns ``None`` when no weighted
    attack is populated.
    """
    weights: List[float] = []
    stats_from_sidecar: Optional[Dict[str, float]] = None
    for sidecar_val in _iter_formalism_specific(state, "attack_weights"):
        if not isinstance(sidecar_val, list):
            continue
        for atk in sidecar_val:
            if not isinstance(atk, dict):
                continue
            w = atk.get("weight")
            if isinstance(w, (int, float)):
                weights.append(float(w))
    # weight_statistics is a sibling leaf on the same sidecar; read it directly
    # (the helper iterates one leaf, so scan the sidecars once more for stats).
    for sidecar_val in _iter_formalism_specific(state, "weight_statistics"):
        if isinstance(sidecar_val, dict) and sidecar_val:
            stats_from_sidecar = sidecar_val  # keep the last non-empty
            break
    if not weights:
        return None
    # Prefer the producer's aggregate; fall back to computing from the sample.
    if stats_from_sidecar and all(
        isinstance(stats_from_sidecar.get(k), (int, float))
        for k in ("min_weight", "max_weight", "avg_weight")
    ):
        lo = float(stats_from_sidecar["min_weight"])
        hi = float(stats_from_sidecar["max_weight"])
        avg = float(stats_from_sidecar["avg_weight"])
    else:
        lo = min(weights)
        hi = max(weights)
        avg = sum(weights) / len(weights)
    shown = weights[:_WEIGHTED_DIST_ATTACK_CAP]
    flat = ", ".join(f"{w:.2f}" for w in shown)
    tail = "" if len(weights) <= _WEIGHTED_DIST_ATTACK_CAP else f" (sur {len(weights)})"
    return StructuredArgFinding(
        capability="weighted_argumentation",
        label=_axis_label("weighted_argumentation"),
        statement=(
            f"le cadre pondéré gradue "
            f"{accord(len(weights), 'attaque', 'attaques')} selon leur "
            f"force (poids de {lo:.2f} à {hi:.2f}, moyenne {avg:.2f}) : "
            f"{flat}{tail}"
        ),
    )


# #2963 review (coordinator, c.6023555773) — the DeLP criterion is a
# CONSTANT on the production path (nothing poses the leaf;
# ``invoke_callables.py:5749`` reads the default), so a standalone projector
# on it would print the same sentence on every run — a tally dressed as a
# finding. It is folded below, as a qualifier that appears ONLY when the
# verdicts do. The labels never echo the raw snake_case token.
_DELP_CRITERION_QUALIFIERS = {
    "generalized_specificity": "selon un critère de spécificité",
    "specificity": "selon un critère de spécificité",
    "weakness": "selon un critère de faiblesse",
}
_DELP_CRITERION_FALLBACK = "selon son critère de comparaison déclaré"


def _delp_criterion_qualifier(state: Any) -> str:
    """The comparison criterion as a prose qualifier (#2952 site 1a, folded).

    Returns ``""`` when no criterion leaf is populated — the caller then
    states the verdicts without qualifying the method. The raw criterion
    token never reaches the prose: DeLP's sidecar is the surface #1702
    opacifies, and a snake_case token is not a French qualifier.
    """
    criteria = [
        c
        for c in _iter_formalism_specific(state, "criterion")
        if isinstance(c, str) and c.strip()
    ]
    if not criteria:
        return ""
    token = criteria[0].strip()
    qualifier = _DELP_CRITERION_QUALIFIERS.get(token, _DELP_CRITERION_FALLBACK)
    sizes = [
        s
        for s in _iter_formalism_specific(state, "program_size")
        if isinstance(s, int) and s > 0
    ]
    amplitude = f", sur un programme de {sizes[0]} lignes" if sizes else ""
    return f"{qualifier}{amplitude}"


def _delp_verdicts_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the dialectical VERDICTS — what DeLP decided (#2952 site 1b).

    DeLP's native leaf ``extensions["delp_query_results"]`` (writer
    ``_write_delp_to_state``, handler ``delp_handler.analyze_delp``) carries
    one verdict per query: YES (the argument is *warranted* — it survives
    every dialectical attack), NO (*defeated*), UNDECIDED (both camps hold),
    UNKNOWN (a functional error, never projected). The singular fact is the
    DECISION itself — no other axis in the pipeline decides per-query: Dung
    decides per-framework, PL per-formula. The statement names the first
    warranted and defeated queries (truncated atoms — the sidecar is the
    surface #1702 scrubs, privacy HARD) and counts the undecided remainder;
    ``message`` payloads never reach the prose (they carry handler diagnostics).

    #2963 review: the comparison criterion (site 1a) rides here as a
    QUALIFIER — it only appears when a verdict does, and it never prints the
    raw token. Control: criterion alone (no YES, no NO) yields no finding.

    Returns ``None`` when nothing was decided (no YES and no NO): an all-
    UNDECIDED or empty run is an honest absence, never a fabricated verdict.
    """
    warranted: List[str] = []
    defeated: List[str] = []
    undecided_atoms: List[str] = []
    for results in _iter_native_extension(state, "delp_query_results"):
        if not isinstance(results, list):
            continue
        for r in results:
            if not isinstance(r, dict):
                continue
            q = _truncate(str(r.get("query", "")).strip(), _FORMALISM_NODE_CAP)
            answer = str(r.get("answer", "")).strip().upper()
            if not q:
                continue
            if answer == "YES":
                warranted.append(q)
            elif answer == "NO":
                defeated.append(q)
            elif answer == "UNDECIDED":
                undecided_atoms.append(q)

    def _first(items: List[str]) -> List[str]:
        return items[:_DELP_VERDICT_CAP]

    if not warranted and not defeated:
        return None
    parts: List[str] = []
    if warranted:
        named = ", ".join(f"« {q} »" for q in _first(warranted))
        parts.append(
            f"{accord(len(warranted), 'requête ressort garantie', 'requêtes ressortent garanties')}"
            f" ({named})"
        )
    if defeated:
        named = ", ".join(f"« {q} »" for q in _first(defeated))
        parts.append(
            f"{accord(len(defeated), 'requête est renversée', 'requêtes sont renversées')}"
            f" ({named})"
        )
    undecided = ""
    if undecided_atoms:
        first = undecided_atoms[0]
        rest = len(undecided_atoms) - 1
        if rest <= 0:
            undecided = f" ; « {first} » resterait indécise — aucun camp ne l'emporte"
        else:
            undecided = (
                f" ; « {first} » et {rest} "
                + accord(rest, "autre resteraient", "autres resteraient")
                + " indécises — aucun camp ne l'emporte"
            )
    over = ""
    total = len(warranted) + len(defeated) + len(undecided_atoms)
    if total > _DELP_VERDICT_CAP:
        over = f" (sur {total} requêtes)"
    # #2963 — the comparison criterion (former site 1a) qualifies the verdicts
    # instead of standing alone: alone it is a constant of the production path
    # and would print the same sentence on every run.
    qualifier = _delp_criterion_qualifier(state)
    head = "la dialectique défaisable a tranché"
    if qualifier:
        head += f" {qualifier}"
    return StructuredArgFinding(
        capability="delp_reasoning",
        label=_axis_label("delp_reasoning"),
        statement=(head + " : " + " et ".join(parts) + undecided + over),
    )


def _eaf_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the DIVERGENT epistemic beliefs — what EAF alone sees (#2952 site 2).

    EAF's sidecar (writer ``_write_eaf_to_state``) preserves the per-agent
    belief map ``epistemic_beliefs`` (``Dict[agent, List[arg]]``). The
    singular fact is the DIVERGENCE: an argument one agent holds as believed
    while another does not — the multi-agent disagreement no attack-only
    framework can express (Dung says who defeats whom, never who believes
    what). Like SETAF's unary attack (a Dung attack in disguise), agents in
    full agreement carry nothing EAF-specific: the projector stays silent
    (honest absence, #1019). Agent names and atoms are corpus-derived and are
    truncated at the same bar as ABA/SETAF (privacy HARD, #1702).

    Returns ``None`` when fewer than two agents populated beliefs, or when
    every pair of agents agrees on every argument.
    """
    divergent: List[str] = []
    for beliefs in _iter_formalism_specific(state, "epistemic_beliefs"):
        if not isinstance(beliefs, dict):
            continue
        held: List[tuple[str, set[str]]] = []
        for agent, args in beliefs.items():
            if not isinstance(args, list):
                continue
            name = _truncate(str(agent).strip(), _FORMALISM_NODE_CAP)
            atoms = {
                _truncate(str(a).strip(), _FORMALISM_NODE_CAP)
                for a in args
                if str(a).strip()
            }
            if name:
                held.append((name, atoms))
        for i, (agent_a, atoms_a) in enumerate(held):
            for agent_b, atoms_b in held[i + 1 :]:
                # Two agents who each believe nothing agree (on the empty set);
                # ONE who believes something the other does not is exactly the
                # divergence this axis exists to name — an empty belief list on
                # one side is a party to the disagreement, not an absence.
                if not atoms_a and not atoms_b:
                    continue
                only_a = sorted(atoms_a - atoms_b)
                only_b = sorted(atoms_b - atoms_a)
                if only_a:
                    divergent.append(
                        f"« {agent_a} » tient « {only_a[0]} » pour acquis "
                        f"quand « {agent_b} » ne l'admet pas"
                    )
                elif only_b:
                    divergent.append(
                        f"« {agent_b} » tient « {only_b[0]} » pour acquis "
                        f"quand « {agent_a} » ne l'admet pas"
                    )
                if len(divergent) >= _EAF_DIVERGENCE_CAP:
                    break
            if len(divergent) >= _EAF_DIVERGENCE_CAP:
                break
        if len(divergent) >= _EAF_DIVERGENCE_CAP:
            break
    if not divergent:
        return None
    tail = "" if len(divergent) < _EAF_DIVERGENCE_CAP else " (extrait partiel)"
    return StructuredArgFinding(
        capability="eaf_reasoning",
        label=_axis_label("eaf_reasoning"),
        statement=(
            "les croyances épistémiques divergent entre agents : "
            + " ; ".join(divergent)
            + tail
        ),
    )


def _adf_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project the THREE-VALUED undecided statements — what ADF alone says (#2952 site 3).

    ADF's native leaf ``extensions["adf_models"]`` (writer
    ``_write_adf_to_state``, #2063) carries the reasoner's interpretations as
    strings (``"{p=T,q=U}"`` — T/F/U per statement). The singular fact is the
    UNDECIDED value: a statement neither established nor overturned, which a
    two-valued acceptance cannot name. When the format does not parse, the
    projector falls back to the NON-UNICITY figure (several distinct
    interpretations = the acceptance is not arbitrated to one world), never
    fabricating assignments it could not read.

    #2063 provenance combination: the writer also attaches a ``degraded`` flag
    on the sidecar. Per the #2844 discipline (an axis filed degraded is named
    by the absence channel and nowhere else), a degraded ADF run produces NO
    finding here even when interpretations are populated — the two readers of
    one state stay in agreement by construction. Statements are corpus-derived
    and truncated (privacy HARD, #1702); the ``note``/``statistics`` provenance
    leaves never reach the prose.

    Returns ``None`` when nothing was decided (empty models), when the run is
    degraded, or when every statement is two-valued in a single world (an
    honest absence: plain acceptance, nothing ADF-specific to say).
    """
    for flag in _iter_formalism_specific(state, "degraded"):
        if flag is True:
            return None
    models: List[str] = []
    for batch in _iter_native_extension(state, "adf_models"):
        if not isinstance(batch, list):
            continue
        for interp in batch:
            text = str(interp).strip()
            if text:
                models.append(text)
    if not models:
        return None
    undecided: List[str] = []
    for interp in models:
        for atom, value in _ADF_ASSIGNMENT_RE.findall(interp):
            if value.upper() == "U":
                atom = _truncate(atom.strip(), _FORMALISM_NODE_CAP)
                if atom and atom not in undecided:
                    undecided.append(atom)
                if len(undecided) >= _ADF_UNDECIDED_CAP:
                    break
        if len(undecided) >= _ADF_UNDECIDED_CAP:
            break
    if undecided:
        named = ", ".join(f"« {a} »" for a in undecided)
        tail = "" if len(undecided) < _ADF_UNDECIDED_CAP else " (extrait partiel)"
        return StructuredArgFinding(
            capability="adf_reasoning",
            label=_axis_label("adf_reasoning"),
            statement=(
                "le cadre d'acceptation conditionnelle laisse des énoncés "
                "indécis — ni établis, ni renversés : " + named + tail
            ),
        )
    distinct = set(models)
    if len(distinct) < 2:
        return None
    return StructuredArgFinding(
        capability="adf_reasoning",
        label=_axis_label("adf_reasoning"),
        statement=(
            "le cadre d'acceptation conditionnelle n'arbitre pas à un monde "
            f"unique : {len(distinct)} interprétations distinctes coexistent"
        ),
    )


def _resolve_unit_label(labels: Dict[str, str], key: str) -> str:
    """Render a retraction option name as text when it names a unit (#3014).

    The pipeline's retraction options carry unit ids (``arg_N``) with the
    unit texts in the entry's ``argument_labels``; a fallacy-negation clause
    names ``¬arg_N``. The conversational lane and pre-#3014 entries name texts
    already — an unknown key passes through verbatim, so the prose keeps
    naming the belief either way.
    """
    if key in labels:
        return labels[key]
    if key.startswith("¬") and key[1:] in labels:
        return f"¬{labels[key[1:]]}"
    return key


def _retraction_pair_belief(label: Any) -> str:
    """The belief a retraction label retracts — ``¬x`` and ``x`` are one pair."""
    text = str(label).strip()
    return text[1:] if text.startswith("¬") else text


def _product_of_disjoint_pairs(options: List[Any], card: int) -> int:
    """How many independent belief / ¬belief pairs the options select across.

    Returns the pair count when **every** stored option picks exactly one side
    of each of ``card`` disjoint pairs — the option set is then a sub-cube of
    ``2 ** card`` built by the fallacy negations, and its multiplicity is
    arithmetic, not structure. Returns 0 when the options overlap (a belief
    shared by several conflicts makes the union larger than the cardinality)
    or when the shape cannot be read.

    #3150 — the R1106 render sold « 32 retraits de cardinal 5 … plusieurs
    mondes consistants incompatibles, également minimaux » as a structural
    finding. The 5 pairs are the five fallacy targets; the 32 is 2⁵. Nothing
    about the discourse is learned from that number.

    A single pair is **not** collapsed: with one clash the two retractions ARE
    the clash (insight B-2 of #1646 — drop the belief or drop its negation),
    and there is no combinatorial product to mistake for structure. The
    defect this guards is the product of SEVERAL independent conflicts.
    """
    if not isinstance(options, list) or len(options) < 2 or card < 2:
        return 0
    pairs: set[str] = set()
    for option in options:
        if not isinstance(option, list) or not option:
            return 0
        beliefs = [_retraction_pair_belief(label) for label in option]
        if any(not belief for belief in beliefs):
            return 0
        if len(set(beliefs)) != len(beliefs) or len(beliefs) != card:
            return 0
        pairs.update(beliefs)
    return len(pairs) if len(pairs) == card else 0


def _belief_revision_finding(state: Any) -> Optional[StructuredArgFinding]:
    """Project what belief revision alone establishes: the minimal retraction.

    The axis's singular contribution (#1646 section A) is the **minimal
    retraction** — the smallest set of beliefs whose removal restores
    consistency. It is a global cardinality property no other axis produces: the
    PL solver says UNSAT but not what to give up, and a contradiction detector
    never asks what SURVIVES. NAMING the cardinality + the belief(s) to give up
    (insight B-1) is the projection; when several retractions of the same
    minimal cardinality restore consistency, NONE is the minimal one — the base
    splits into incompatible but equally-minimal worlds (insight B-2, the figure
    a single revised world cannot express); when the retraction touches only a
    clashing belief and leaves the rest intact, the contradiction is INERT
    (insight B-3) — the figure that goes against the rhetorical reflex that any
    contradiction must bear on the thesis.

    Returns None when the base is consistent (cardinality 0, honest absence), or
    the insight degraded (cardinality -1 / missing — fail-loud #1019: never
    fabricate a retraction the computation did not produce).
    """
    entries = getattr(state, "belief_revision_results", None) or []
    if not isinstance(entries, list):
        return None

    # Pick the entry with the smallest cardinality >= 1 (the sharpest rupture).
    # cardinal-1 is the canonical figure "one belief restores consistency"; if
    # any entry reaches it, stop — no deeper search needed.
    best_mr: Optional[Dict[str, Any]] = None
    best_labels: Dict[str, str] = {}
    best_original: Any = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        mr = entry.get("minimal_retraction")
        if not isinstance(mr, dict):
            continue
        card = mr.get("cardinality")
        if not isinstance(card, int) or card < 1:
            continue
        if best_mr is None or card < best_mr.get("cardinality", card + 1):
            best_mr = mr
            best_original = entry.get("original")
            entry_labels = entry.get("argument_labels")
            best_labels = entry_labels if isinstance(entry_labels, dict) else {}
            if card == 1:
                break
    if best_mr is None:
        return None

    card = best_mr["cardinality"]
    options = best_mr.get("options") or []
    # Real-run bases yield combinatorially many equally-minimal retractions,
    # so the producer caps the stored list and carries the exact count. Prefer
    # the true multiplicity (insight B-2 names it); fall back to counting the
    # stored list for pre-repair entries that carry no total.
    options_total = best_mr.get("options_total")
    n_options = (
        options_total
        if isinstance(options_total, int) and options_total >= 1
        else sum(1 for opt in options if isinstance(opt, list))
    )
    # Flatten the distinct beliefs across all minimal options (the rupture
    # candidates the reader names as evidence).
    named: List[str] = []
    seen: set[str] = set()
    for opt in options:
        if not isinstance(opt, list):
            continue
        for label in opt:
            key = str(label).strip()
            if not key:
                continue
            # #3014: an id-keyed option renders the unit's TEXT when the
            # entry carries the label map — the prose names beliefs, not ids.
            rendered = _resolve_unit_label(best_labels, key)
            if rendered not in seen:
                seen.add(rendered)
                named.append(_truncate(rendered, _SUPPORT_NODE_CAP))
                if len(named) >= _RETRACTION_CAP:
                    break
        if len(named) >= _RETRACTION_CAP:
            break

    base_size = best_mr.get("base_size", 0)
    touched = best_mr.get("touched_count", 0)
    untouched = (
        base_size - touched
        if isinstance(base_size, int) and isinstance(touched, int)
        else 0
    )

    # B-1 names the cardinality + the rupture belief(s); B-2 takes precedence
    # when several retractions of the SAME minimal cardinality restore
    # consistency — none is *the* minimal one, and the base splits into
    # incompatible but equally-minimal consistent worlds. That non-unicity is
    # the figure no LLM produces (a single revised world is all a revision
    # operator, or a prose paraphrase, can express), so it is named first when
    # the computation surfaced more than one option.
    #
    # #3150 — UNLESS the options are the cross-product of independent
    # belief / ¬belief pairs. Then the multiplicity is 2 ** (number of fallacy
    # negations): arithmetic wearing the costume of a structural figure. Naming
    # it as « plusieurs mondes » invites the reader to read a property of the
    # discourse where the state only multiplied its own negations.
    pairs = _product_of_disjoint_pairs(options, card)
    if n_options >= 2 and pairs:
        lead = (
            f"pas de rétractation minimale unique — {n_options} retraits de "
            f"cardinal {card} restaurent également la cohérence, mais ce "
            f"nombre est un produit : chaque retrait prend un côté de chacune "
            f"des {pairs} paires croyance / négation indépendantes que les "
            "sophismes ont créées, il n'ajoute aucune structure au propos"
        )
    elif n_options >= 2:
        lead = (
            f"pas de rétractation minimale unique — {n_options} retraits de "
            f"cardinal {card} restaurent également la cohérence : plusieurs "
            "mondes consistants incompatibles, également minimaux"
        )
    elif card == 1:
        lead = "une seule proposition suffit à restaurer la cohérence si on l'abandonne"
    else:
        lead = (
            f"la rétractation minimale est de cardinal {card} — il faut renoncer "
            f"à au moins {accord(card, 'engagement', 'engagements')} pour que le "
            f"reste tienne"
        )
    parts: List[str] = [lead]
    # #3150 — the base, always. The R1106 render never said over WHAT the
    # revision reasoned, so its « cette contradiction » was free to latch onto
    # the nearest formal verdict it had just discussed. The revision ran on the
    # extraction window's units plus one negation per targeted fallacy: that is
    # a PROPAGATION of the fallacy signal, and the reader must not receive it
    # as a second, independent corroboration.
    n_units = len(best_original) if isinstance(best_original, list) else None
    n_population = len(getattr(state, "identified_arguments", None) or {}) or None
    n_negations = (
        base_size - n_units
        if isinstance(base_size, int) and n_units is not None and base_size >= n_units
        else None
    )
    if n_units is not None:
        socle = f"le socle examiné est de {n_units} engagement(s)" + (
            f" sur {n_population} unités lues" if n_population else ""
        )
        if n_negations:
            socle += (
                f", augmenté des {accord(n_negations, 'négation', 'négations')} "
                "que les détections de sophismes ajoutent à leurs cibles — le "
                "conflit rejoué prolonge le signal de sophisme, il ne le "
                "corrobore pas"
            )
        parts.append(socle)
    if named:
        parts.append("le point de rupture porte sur : " + " | ".join(named))
    # B-3: the contradiction is confined — some beliefs survive every retraction.
    # #3150: it names WHICH contradiction (the one these negations build), so
    # the sentence can never be read as a statement about the PL/FOL verdict.
    if untouched > 0:
        survit = "survit intact" if untouched == 1 else "survivent intacts"
        subject = (
            "la contradiction née de ces négations"
            if n_negations
            else "la contradiction ainsi construite"
        )
        parts.append(
            f"{subject} est confinée — "
            f"{accord(untouched, 'engagement', 'engagements')} {survit} : "
            "une contradiction réelle mais inerte, qui n'entraîne pas "
            "la thèse"
        )
    return StructuredArgFinding(
        capability="belief_revision",
        label=_axis_label("belief_revision"),
        statement=" ; ".join(parts),
    )


def _aspic_attack_statement(scope_counts: Dict[str, int]) -> str:
    """Render the ASPIC+ attack-scope finding (#1649).

    Names the scope DISTRIBUTION only (counts + vocabulary gloss), never the
    raw ``attacks[*].target`` atoms — those are source-derived via ``_pl_atom``
    (24 leading chars of text) and stay out of the prose (privacy HARD). The
    most singular scope (undercut) leads the sentence; absent scopes are
    omitted so the statement reflects exactly what the producer qualified.
    """
    parts: List[str] = []
    for scope in _ASPIC_ATTACK_SCOPES:
        count = scope_counts.get(scope, 0)
        if count <= 0:
            continue
        parts.append(f"{count} « {scope} » ({_ASPIC_SCOPE_GLOSS[scope]})")
    if not parts:
        # Defensive: callers gate on sum>0, but never trust the gate alone.
        return ""
    return (
        "le cadre ASPIC+ qualifie des attaques qui fragmentent le raisonnement "
        "selon leur portée : " + " ; ".join(parts) + "."
    )


def _degraded_capabilities(state: Any) -> Set[str]:
    """The axes the honest-absence ledger files as degraded (#2844).

    ``state.structured_arg_status`` is the one ledger ``state_writers.
    _record_structured_arg_status`` fills, and :func:`_collect_absent_dimensions`
    already reads it to name the lost axes. This is the same read, for the
    presence side: an axis whose framework returned only empty result sets is
    filed ``evaluated_empty`` / degraded there (#1671: it "contributed no
    analysis and must not be counted as capable"), while its *input* — the
    weighted sidecar, the degenerate SetAF graph — can still carry data a
    projector would turn into a statement. Counting that statement as
    established surplus made the two readers of one run contradict each other.
    """
    ledger = getattr(state, "structured_arg_status", None) or {}
    if not isinstance(ledger, dict):
        return set()
    return {
        str(capability)
        for capability, info in ledger.items()
        if isinstance(info, dict) and info.get("degraded")
    }


def _collect_structured_arg_findings(state: Any) -> List[StructuredArgFinding]:
    """Collect the structured-argumentation axes that produced something (#1667).

    One channel, not one reader per axis (the eight-half-fixes lesson of #1633).
    Each projector decides on its own whether its axis has a singular statement
    to make; an axis with nothing to say produces nothing rather than a status
    word.

    #2844: a projector reads the axis's INPUT, which can survive the axis's
    own failure — the weighted sidecar is written before the framework runs,
    so weights exist on a run the framework answered with empty sets only.
    The ledger is the run's own record of that, and the surplus channel now
    honours it: an axis filed degraded is named by the absence channel and
    nowhere else, so the two readers of one state agree by construction.
    """
    degraded = _degraded_capabilities(state)
    out: List[StructuredArgFinding] = []
    for projector in (
        _aspic_finding,
        _bipolar_finding,
        # #3547 — the JTMS counterfactual: premises whose withdrawal would
        # drop other beliefs' only justification. Same contract — ``None``
        # when no premise carries that weight.
        _jtms_counterfactual_finding,
        _belief_revision_finding,
        # #1667 axes 3/5 — the three axes whose container is the
        # ``formalism_specific`` sidecar (no first-level ``*_results`` exists).
        # Each reads the sidecar via ``_iter_formalism_specific`` and returns
        # ``None`` when its axis has nothing singular to say (honest absence).
        _aba_finding,
        _setaf_finding,
        _weighted_finding,
        # #2952 — DeLP (native verdicts; the sidecar criterion rides as a
        # qualifier, #2963), EAF (sidecar), ADF (native + #2063 provenance):
        # the three axes whose writers were planted without a consumer. Same
        # contract: one projector per site, ``None`` when the site's singular
        # fact is absent, degraded ADF yields to the absence channel (#2844).
        _delp_verdicts_finding,
        _eaf_finding,
        _adf_finding,
    ):
        finding = projector(state)
        if finding is None or finding.capability in degraded:
            continue
        out.append(finding)
    return sorted(out, key=lambda f: f.label)


def _collect_debate(state: Any) -> List[DebateExchange]:
    """Collect adversarial-debate exchanges (SV #1182). Gap β G8: can be sparse.

    Reads ``state.debate_transcripts``; surfaces ONLY non-empty exchanges
    (fail-loud: empty point+rebuttal would read as fabricated matter, #1019).
    """
    transcripts = getattr(state, "debate_transcripts", []) or []
    if not isinstance(transcripts, list):
        return []
    out: List[DebateExchange] = []
    for t in transcripts:
        if not isinstance(t, dict):
            continue
        exchanges = t.get("exchanges", []) or []
        if not isinstance(exchanges, list):
            continue
        for ex in exchanges:
            if not isinstance(ex, dict):
                continue
            point = _truncate(ex.get("point", ""), _DEBATE_CAP)
            rebuttal = _truncate(ex.get("rebuttal", ""), _DEBATE_CAP)
            if not point and not rebuttal:
                continue
            # G8 (#1184): carry scheme grounding (None when no match — honest).
            scheme_raw = ex.get("scheme")
            scheme = (
                str(scheme_raw).strip()
                if isinstance(scheme_raw, str) and scheme_raw.strip()
                else None
            )
            cq_raw = ex.get("critical_question")
            critical_question = (
                str(cq_raw).strip()
                if isinstance(cq_raw, str) and cq_raw.strip()
                else None
            )
            out.append(
                DebateExchange(
                    point=point,
                    rebuttal=rebuttal,
                    scheme=scheme,
                    critical_question=critical_question,
                )
            )
            if len(out) >= _DEBATE_MAX_EXCHANGES:
                return out
    return out


def _compute_verdict_band(
    axes_nontrivial: List[str],
) -> VerdictBand:
    """Compute the verdict band from the real analytical coverage.

    Honest adaptation of #1008 §2.1: the restitution report has no external
    analyst to compare against, so the band governs *how strongly the discourse
    may be characterised* based on how many analytical axes produced non-trivial
    content. The thresholds are transparent and fixed (anti-pendule: no curve).

    EXCEEDED needs formal depth (PL or FOL) AND the quality axis (a
    characterised discourse) on top of broad coverage — the "depth surpassing"
    spirit of #1008 §2.1, read as analytical depth rather than comparison.
    """
    present = set(axes_nontrivial)
    missing = [a for a in _ALL_AXES if a not in present]
    n = len(axes_nontrivial)
    has_formal_depth = _AXIS_FORMAL_PL in present or _AXIS_FORMAL_FOL in present
    has_quality = _AXIS_QUALITY in present

    if n >= _EXCEEDED_MIN_AXES and has_formal_depth and has_quality:
        band = _BAND_EXCEEDED
    elif n >= _MATCH_MIN_AXES:
        band = _BAND_MATCH
    elif n >= _PARTIAL_MIN_AXES:
        band = _BAND_PARTIAL
    else:
        band = _BAND_BELOW

    return VerdictBand(
        band=band,
        nontrivial_axes=list(axes_nontrivial),
        missing_axes=missing,
        axes_count=n,
    )


def _vote_winner_examination(
    state: Any,
    winner_ids: List[str],
    fallacies: Any,
) -> Dict[str, str]:
    """#3308 — per cited vote winner, what the fallacy pass established.

    Four states, kept distinct (the whole point of the family #2966 opened):

    * **examined, nothing found** — the pass looked at this unit and localized
      no fallacy, so « aucun défaut localisé » is a measured statement;
    * **examined, N found** — the count of the speaker's own localized
      detections on the unit;
    * **never examined** — the pass never submitted the unit, so its silence
      establishes nothing. This is the state R1127a was missing: the writer
      read it, correctly but unsoundly, as « no defect »;
    * **no coverage record** — the run predates #2966 or does not record.
      ``_fallacy_examined_ids`` returns ``None`` there, and the honest answer
      names the missing record rather than claiming a verdict either way.

    The label travels on the SAME line as the referent (#2965): the writer
    must not have to join a status to a unit across a long prompt.
    """
    from .virtuous_identification import _fallacy_examined_ids

    examined = _fallacy_examined_ids(state)
    found: Dict[str, int] = {}
    if isinstance(fallacies, dict):
        for data in fallacies.values():
            if not isinstance(data, dict) or not is_speaker_move(data):
                continue
            target = str(data.get("target_argument_id") or "").strip()
            if target:
                found[target] = found.get(target, 0) + 1

    labels: Dict[str, str] = {}
    for raw_id in winner_ids:
        unit_id = str(raw_id or "").strip()
        if not unit_id:
            continue
        if examined is None:
            label = (
                "couverture de la détection de sophismes non enregistrée sur "
                "ce run — aucune conclusion sur ses défauts n'a été établie"
            )
        elif unit_id not in examined:
            label = (
                "unité NON examinée par la détection de sophismes — son "
                "absence de défaut n'a PAS été établie, et son silence ne "
                "prouve rien"
            )
        elif found.get(unit_id):
            n = found[unit_id]
            label = f"examinée, {n} défaut{'s' if n > 1 else ''} " "localisé" + (
                "s" if n > 1 else ""
            )
        else:
            label = "examinée, aucun défaut localisé"
        labels[unit_id] = label
    return labels


def build_act3_evidence(state: Any) -> Act3Evidence:
    """Build the deterministic Acte III evidence bundle from a shared state.

    No LLM, no JVM — pure state extraction. Privacy: corpus-derived fields are
    truncated; IDs stay opaque. The verdict band and the G1–G4 gate statuses are
    computed here (deterministic) so the orchestrator can gate the synthesis
    honestly.
    """
    # #2845 — the recorded source metadata, truncated like everything else
    # (privacy HARD + prompt budget). Mirrors build_act1_evidence.
    # #3311 — through the same reader-label view as Acte I: no raw key
    # reaches this prompt either.
    metadata = getattr(state, "source_metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata_view = reader_metadata_view(metadata)

    args = getattr(state, "identified_arguments", {}) or {}
    fallacies = getattr(state, "identified_fallacies", {}) or {}
    quality = getattr(state, "argument_quality_scores", {}) or {}
    counters = getattr(state, "counter_arguments", []) or []

    if not isinstance(args, dict):
        args = {}
    if not isinstance(fallacies, dict):
        fallacies = {}
    if not isinstance(quality, dict):
        quality = {}
    if not isinstance(counters, list):
        counters = []

    args_total = len(args)
    # #3180 — only the speaker's own localized detections count. A reported
    # move is surfaced apart (``reported_fallacies_total``), never as this
    # discourse's weakness.
    fallacies_total = sum(
        1
        for _f, d in fallacies.items()
        if isinstance(d, dict)
        and (d.get("target_argument_id") or "")
        and is_speaker_move(d)
    )
    reported_fallacies_total = sum(
        1
        for _f, d in fallacies.items()
        if isinstance(d, dict)
        and (d.get("target_argument_id") or "")
        and is_reported_move(d)
    )
    # #3429 — which third parties the text names, if any. Distinct and in
    # state order: the block quotes them, it never invents one.
    reported_fallacies_labels: List[str] = []
    for _f, d in fallacies.items():
        if not isinstance(d, dict) or not (d.get("target_argument_id") or ""):
            continue
        if not is_reported_move(d):
            continue
        _label = move_author_label_of(d).strip()
        if _label and _label not in reported_fallacies_labels:
            reported_fallacies_labels.append(_label)
    quality_axis_available = bool(quality)
    counters_total = sum(
        1
        for c in counters
        if isinstance(c, dict) and (c.get("target_arg_id") or c.get("counter_content"))
    )
    pl_inc = _pl_inconsistent(state)
    fol_inc = _fol_inconsistent(state)
    # D1c (#1167): a verified-consistent theory is a real formal result too —
    # the formal axis credits ANY verified verdict (satisfiable/consistent True
    # OR False), so a coherent text surfaces a non-trivial formal finding.
    pl_verified = _pl_verified(state)
    fol_verified = _fol_verified(state)
    dung_rejected = decode_native_dung(state).rejected_by_arg
    # #3394 cycle 2 — the refs the annex will print, and the semantics Act
    # II's primary verdict spoke under: the weak points gate their refs on
    # the first and name any divergence from the second.
    _citable_dung_refs = citable_appendix_refs(state)
    _primary_fw = select_primary_native(getattr(state, "dung_frameworks", {}) or {})
    _primary_dung_semantics = (
        native_semantics_label(_primary_fw) if _primary_fw is not None else None
    )

    # Non-trivial axes (real-in-state content), in a stable display order.
    axes_nontrivial: List[str] = []
    if fallacies_total:
        axes_nontrivial.append(_AXIS_FALLACIES)
    if quality_axis_available:
        axes_nontrivial.append(_AXIS_QUALITY)
    if counters_total:
        axes_nontrivial.append(_AXIS_COUNTERS)
    if pl_verified:
        axes_nontrivial.append(_AXIS_FORMAL_PL)
    if fol_verified:
        axes_nontrivial.append(_AXIS_FORMAL_FOL)
    if dung_rejected:
        axes_nontrivial.append(_AXIS_DUNG)

    # #3107 — the causes the FOL writer stated, read from the same entries
    # ``_fol_inconsistent`` counts. Empty when none was stated.
    fol_causes = _fol_stated_causes(state)
    # #3122 — same for the PL leg, read from the entries ``_pl_inconsistent``
    # counts (guest sidecars never carry a cause).
    pl_causes = _pl_stated_causes(state)
    weak_points = _collect_weak_points(
        fallacies,
        dung_rejected,
        pl_inc,
        fol_inc,
        fol_causes,
        pl_causes,
        citable_refs=_citable_dung_refs,
        primary_semantics=_primary_dung_semantics,
        state=state,
    )
    counter_strategies: List[CounterStrategy] = []
    for ca in counters:
        if not isinstance(ca, dict):
            continue
        tid = ca.get("target_arg_id") or ""
        content = ca.get("counter_content") or ""
        if not (tid or content):
            continue
        # G6 (#1180): surface the validation verdict (absent → None, honest).
        validation = ca.get("validation")
        is_valid = None
        succeeds = None
        if isinstance(validation, dict):
            _iv = validation.get("is_valid_attack")
            _cs = validation.get("counter_succeeds")
            if isinstance(_iv, bool):
                is_valid = _iv
            if isinstance(_cs, bool):
                succeeds = _cs
        counter_strategies.append(
            CounterStrategy(
                strategy=str(ca.get("strategy", "")),
                target_arg_id=str(tid),
                snippet=_truncate(content, _COUNTER_CAP),
                is_valid_attack=is_valid,
                counter_succeeds=succeeds,
            )
        )

    quality_strengths = _collect_quality_strengths(quality, args_total)

    # #1620 — ``narrative_synthesis_available`` was read here and dropped. It is
    # gone by subtraction, not relocated: measured on three real artifacts, the
    # Acte III prose asserts *nothing* about a narrative synthesis (0 mentions
    # in 3447 / 3742 / 3560 chars of conclusion) even where the state carries a
    # 5053-char one, so the flag guarded no claim. The availability signal the
    # reader does get comes from ``appendix.py`` (``synthese_narrative``), which
    # computes it from the state directly — a working reader, not this one.
    #
    # #1911 is "its own issue" below — and it took the third branch neither
    # dead end anticipated: not the text, not a boolean, but the bounded
    # STRUCTURED projection (convergences + value gates), derived from
    # lower-level state so every claim stays traceable.
    global_findings = project_global_findings(state)

    # SV (#1182): surface governance verdict + debate exchanges (debranched
    # capabilities — same fix shape as G6 for counter-arg validity). The
    # verdict is collected BEFORE the salience call below: #1914 / R1080
    # grafts the deliberation preference into the ranking from the SAME
    # collected object — one reader of the ``governance_decisions`` leaf,
    # never two (#1633).
    governance_verdict = _collect_governance(state)

    # #1914 (Acte III slice) — the salience ranking + zero-shot surplus,
    # derived from the components above (one reader per state leaf, #1633):
    # the role classifier reads the state, the structured/global findings
    # are passed in already-derived, and so is the governance verdict.
    structured = _collect_structured_arg_findings(state)
    salience = assess_conclusion_salience(
        state,
        structured_findings=structured,
        global_findings=global_findings,
        counters_total=counters_total,
        governance_verdict=governance_verdict,
    )

    debate_exchanges = _collect_debate(state)

    # G1–G4 (#1008 §3.2). G3 passes once a band is computable (always, given the
    # deterministic scorer); G4 is structural (we only surface real-in-state
    # fields). The orchestrator emits the honest fallback when any gate fails.
    gates: Dict[str, bool] = {
        "G1_arguments_extracted": args_total > 0,
        "G2_one_dimension_nontrivial": len(axes_nontrivial) >= 1,
        "G3_verdict_computed": True,
        "G4_no_fabrication": True,
    }

    verdict = _compute_verdict_band(axes_nontrivial)
    virtuous_mode = detect_virtuous_mode(state)

    # #2965 (Acte III slice) — the excerpts follow the citations, not the
    # dict head. On the measured run Act III cited 14 units (governance
    # winner, ranked salience, weak-point and counter targets) and received
    # the text of none of them: its only five excerpts were the first five
    # units in insertion order, the opening of the document, which it cites
    # nowhere. Order here is salience order — the winner first (it is what
    # the conclusion presents as the discourse's answer), then the
    # ranked-salience anchors, then the remaining citation populations from
    # ``cited_unit_ids`` (#2974: fallacy targets, counter targets, winner).
    # Each text is capped by ``CITED_UNIT_TEXT_CAP`` — the same budget Act
    # II allocates to the units it asks its writer to discuss.
    cited_args: List[str] = []

    def _cite(unit_id: Any) -> None:
        u = str(unit_id or "").strip()
        if u and u in args and u not in cited_args:
            cited_args.append(u)

    if governance_verdict is not None:
        _cite(governance_verdict.winner)
    if salience is not None:
        for item in salience.ranked:
            for anchor in item.cites:
                _cite(anchor)
    # #3156 — the units a global convergence names are cited units. The R1107
    # render put arg_66 / arg_79 on a `[convergence]` line as bare ids while
    # the writer had to name « two passages »: it bound them to arg_30, the one
    # nearby unit whose text it had. Citing them first puts their text in
    # ``anchor_excerpts`` below and, when the budget allows, in the claims list.
    for finding in global_findings:
        for cite in finding.cites:
            _cite(cite)
    for unit_id in sorted(cited_unit_ids(state)):
        _cite(unit_id)
    # #3214 — the units Act II weighs, joined to a citation above by an
    # argument-map edge (attack, or support since the rework — #1645's
    # relation, measured wired into ``bipolar_results``). Act III's
    # populations are the ones the
    # conclusion asks ABOUT; Act II weighs every unit, and the reply it
    # weighed (an attack edge in the graph) reached Act III only if some
    # citation population happened to include it — on the measured state it
    # did not, and Act III denied the reply in good faith. The join is a
    # citation population of its OWN (not a reordering of the claims list,
    # which keeps its selection above untouched): narrow by construction —
    # only a weighed unit an edge joins to an ALREADY-CITED unit, either
    # direction, native frameworks only (#1912 sidecars stay unread).
    joined_units = act2_joined_unit_ids(state, cited_args)
    joined_excerpts: List[Tuple[str, str, str]] = [
        (
            unit_id,
            relation,
            truncate_at_boundary(args[unit_id], CITED_UNIT_TEXT_CAP),
        )
        for unit_id, relation in joined_units[:_MAX_JOINED_EXCERPTS]
        if str(args[unit_id] or "").strip()
    ]
    # #2850 lot 4 — one population, one cap. The dict used to be a SECOND,
    # silent cap (``list(args)[:_MAX_CLAIM_EXCERPTS]``): the fill draws after
    # the citations and can only consume ``_MAX_CLAIM_EXCERPTS - len(cited)``
    # entries, at most that many of the head's five are already cited, so
    # the selected set and its order are IDENTICAL — what changes is that
    # the population is now the whole dict and is named
    # (``claim_excerpts_total``), which the prompt notice below reads.
    citable_args = list(cited_args)
    for unit_id in args:
        if unit_id not in citable_args:
            citable_args.append(unit_id)
    selected_args = citable_args[:_MAX_CLAIM_EXCERPTS]
    claim_excerpts: List[Tuple[str, str]] = [
        (u, truncate_at_boundary(args[u], CITED_UNIT_TEXT_CAP))
        for u in selected_args
        if str(args[u] or "").strip()
    ]

    # #2965 (Acte III slice) — the winner's referent travels on the
    # governance line itself; see the field's comment.
    governance_winner_text = ""
    if governance_verdict is not None and governance_verdict.winner in args:
        governance_winner_text = truncate_at_boundary(
            args[governance_verdict.winner], CITED_UNIT_TEXT_CAP
        )

    # #2989 rework — the same resolution for EVERY distinct winner, so the
    # divergence clause can name what each one argues instead of printing
    # two raw ids.
    governance_divergent_texts = (
        divergent_winner_texts(governance_verdict.winners, args)
        if governance_verdict is not None
        else []
    )

    # #3308 — the examination status of every unit cited as a vote winner.
    # R1127a read the pass's silence on a divergent winner as « pas de défaut
    # net »; the status travels on the same line as the referent (#2965).
    cited_winner_ids: List[str] = []
    if governance_verdict is not None:
        cited_winner_ids.append(str(governance_verdict.winner))
        cited_winner_ids.extend(str(w) for w, _text in governance_divergent_texts)
    examination_by_unit = _vote_winner_examination(state, cited_winner_ids, fallacies)

    # #3156 — the anchor of every unit a global finding cites, keyed by opaque
    # id. The convergence line carried ids only; the writer, asked to name the
    # passages, bound them to the one nearby unit whose text it had (arg_30,
    # which carries no quality score and is not one of the converging units).
    # « Joinable » is not « joined »: the referent travels ON the line.
    # #3193 (rework) — the COUNT of anchors is bounded here too, not only the
    # per-text cap: ``global_findings`` is itself capped by the projection
    # (``_MAX_CONVERGENCE_FINDINGS + _MAX_GATE_FINDINGS``), so this loop can
    # never exceed that in practice — but the #2908 census row must state a
    # bound the CODE enforces, not one the projection happens to guarantee
    # today. The cap mirrors the claims block: a drop is counted and stated,
    # never silent.
    anchor_excerpts: Dict[str, str] = {}
    dropped_anchor_ids: Set[str] = set()
    for finding in global_findings:
        for cite in finding.cites:
            cite_id = str(cite).strip()
            if not cite_id:
                continue
            # Only a cite the units table holds as text is an anchor: method
            # names (« contre-argument »…) and gate ids are never anchored,
            # so they consume no cap slot and count no drop (#3193 rework,
            # coordinator comment 6362949622 — the former counter announced
            # 7 omissions where one unit cite was left bare).
            text = args.get(cite_id)
            if not (isinstance(text, str) and text.strip()):
                continue
            if cite_id in anchor_excerpts or cite_id in dropped_anchor_ids:
                continue  # a unit repeated across findings drops once, not per finding
            if len(anchor_excerpts) >= _MAX_ANCHOR_EXCERPTS:
                dropped_anchor_ids.add(cite_id)
                continue
            anchor_excerpts[cite_id] = truncate_at_boundary(text, CITED_UNIT_TEXT_CAP)

    return Act3Evidence(
        args_total=args_total,
        fallacies_total=fallacies_total,
        reported_fallacies_total=reported_fallacies_total,
        reported_fallacies_labels=reported_fallacies_labels,
        counters_total=counters_total,
        quality_axis_available=quality_axis_available,
        quality_strengths=quality_strengths,
        weak_points=weak_points,
        counter_strategies=counter_strategies,
        verdict=verdict,
        gates=gates,
        virtuous_mode=virtuous_mode,
        governance_verdict=governance_verdict,
        debate_exchanges=debate_exchanges,
        deanonymized=bool(getattr(state, "deanonymized", True)),
        claim_excerpts=claim_excerpts,
        claim_excerpts_total=len(citable_args),
        anchor_excerpts=anchor_excerpts,
        anchors_dropped=len(dropped_anchor_ids),
        # #3296 — the per-act label table's referent source (same field as
        # Act II): every identified unit's capped text, keyed by opaque id.
        unit_texts={
            str(arg_id): truncate_at_boundary(str(text), LEGEND_REFERENT_CAP)
            for arg_id, text in args.items()
        },
        joined_excerpts=joined_excerpts,
        joined_excerpts_total=len(joined_units),
        governance_winner_text=governance_winner_text,
        governance_divergent_texts=governance_divergent_texts,
        examination_by_unit=examination_by_unit,
        absent_dimensions=_collect_absent_dimensions(state),
        structured_findings=structured,
        global_findings=global_findings,
        salience=salience,
        interpretive_question=str(
            getattr(state, "interpretive_question", "") or ""
        ).strip(),
        announced_checks=[
            str(check).strip()
            for check in (getattr(state, "announced_checks", None) or [])
            if str(check).strip()
        ],
        # #3432 (ask 2) — the personas' blind spots, read from the same state
        # dicts Acte I renders (#3377): no new state attribute, the field is a
        # named part of each persona's read. Strip-and-keep only — capping
        # happened at the producer (BLIND_SPOT_CAP), a reader that re-capped
        # would say a different sentence from the one recorded.
        historical_blind_spot=str(
            (getattr(state, "historical_context", {}) or {}).get("blind_spot", "") or ""
        ).strip(),
        strategic_blind_spot=str(
            (getattr(state, "strategic_read", {}) or {}).get("blind_spot", "") or ""
        ).strip(),
        metadata=metadata_view,
        arena=build_arena_record(state),
        speaker=build_speaker_record(state),
        readings=build_reading_record(state),
        # #3395 (acts slice) — the one producer renders the block; the act
        # never re-words the moves in its own vocabulary.
        first_reading=first_reading_note(state),
    )


# --- the conducted prompt (spec §4 weaving rule, no template) ----------------

_OPAQUE_ID_DIRECTIVE = (
    # #3296 — FB-34 is a privacy rule: it forbids the source's NAME, and it
    # used to also order the machine id (« Désigne chaque argument par son ID
    # opaque (arg_1, arg_2…) »). The order contradicted the readability gate
    # (#2980), which counts every printed ``arg_N`` as jargon, and the order
    # won: 5 of 41 renders carried raw ids. The clause is REMOVED, the ban
    # kept (arbitration R1126). Designation moves to the per-act label table
    # with its legend (#2896/#2965) — nothing is added here in its place.
    "DISCIPLINE D'IDENTIFIANTS OPAQUES (FB-34) — OBLIGATOIRE :\n"
    "- Ne désigne JAMAIS un argument par un nom de source, d'auteur, de lieu\n"
    "  ou de date.\n"
    "- Ne reproduis JAMAIS de passage verbatim du texte source : paraphrase la\n"
    "  conclusion en une phrase qui dit quelque chose.\n"
    "- Les familles de sophismes (ad hominem, ad verecundiam…) sont des\n"
    "  constantes de taxonomie : tu peux les nommer comme ancrage."
)

_WEAVING_RULE = (
    "RÈGLE DE TISSAGE (spec §4) — le contrat anti-énumération :\n"
    "- CHAQUE citation d'un cadre (Tweety, Dung, taxonomie, vertus) DOIT être\n"
    "  ancrée narrativement : liée à (a) un argument localisé ET (b) le verdict\n"
    "  concret que ce cadre a produit.\n"
    "- INTERDIT : une ligne « nom + score isolé », ex. « ad verecundiam (0.8) ».\n"
    "  Ne produis JAMAIS de score entre parenthèses isolé comme (0.8) ou\n"
    "  « score 0.8 ». Les vertus sont le CARACTÈRE du discours, pas un tableau\n"
    "  de scores.\n"
    "- INTERDIT : numéroter en « Sophisme 1: » / « Argument 2: ». Donne aux\n"
    "  blocs des titres THÉMATIQUES en ### (ex. « Ce qui tient », « Ce qui\n"
    "  dérape et comment le contrer », « Les coups suivants probables »).\n"
    "- Le verdict formel appuie un battement narratif ; ce n'est jamais une\n"
    "  sous-section isolée."
)

_FAIL_LOUD_INSTRUCTION = (
    "HONNÊTETÉ (anti-pendule #1019/#369) :\n"
    "- La bande de verdict ci-dessous gouverne la force de ta caractérisation.\n"
    "  Ne formule JAMAIS un claim au-delà de ce que la bande autorise.\n"
    "- Si un axe est manquant (liste fournie), DIS-LE explicitement (« l'axe\n"
    "  qualité n'est pas concluable sur ce run »), ne le simule JAMAIS.\n"
    "- Si aucun point faible n'est localisé (texte vertueux), titre sur les\n"
    "  forces — la robustesse formelle, la tenue des schemes. Ne fabrique pas\n"
    "  de sophisme pour remplir un bloc."
)


def _band_claim_ceiling(band: str) -> str:
    """The allowed-claim ceiling per band (adapted from #1008 §2.2).

    Restitution framing (#1008 absorbed, spec §3): the band governs *how
    strongly the discourse may be characterised* — narrative, not a scorecard.
    """
    if band == _BAND_EXCEEDED:
        # #3163 — the band counts AXES THAT PRODUCED NON-TRIVIAL CONTENT, which
        # is breadth, never extent. The old text turned that count into an
        # extent claim (« elle couvrait largement les dimensions »), and the
        # same prompt carried reading bounds where no axis read more than 15 of
        # 90 units (R1107c, doc_A): the writer put « broad coverage » next to
        # the bounds in one closing paragraph. The ceiling now says what the
        # band measures. The count is derived from the thresholds, never
        # hard-coded: the band is EXCEEDED from _EXCEEDED_MIN_AXES axes, and
        # five of the six five-axis shapes of _ALL_AXES are EXCEEDED (R1108
        # review), so a fixed « six » would tell the writer that six axes
        # spoke when five did — a figure the record contradicts (#3159 class).
        return (
            f"Tu peux caractériser l'analyse comme APPROFONDIE et multi-axes : "
            f"au moins {_EXCEEDED_MIN_AXES} des {len(_ALL_AXES)} axes ont "
            f"produit un résultat non-trivial (dont la profondeur formelle "
            f"vérifiée et le profil de qualité), et ces verdicts vont au-delà "
            f"d'une lecture de surface. La bande compte des AXES qui ont "
            f"parlé, pas l'étendue lue : chaque axe n'a examiné qu'une partie "
            f"des unités — les bornes de lecture du présent prompt disent "
            f"laquelle. Cite les axes non-triviaux qui justifient la bande, "
            f"sans étendre le propos au-delà de ces bornes."
        )
    if band == _BAND_MATCH:
        return (
            "Tu peux caractériser l'analyse comme COMPLÈTE : les axes "
            "principaux du discours ont rendu un verdict (la bande compte des "
            "axes, pas l'étendue lue). Nomme les axes touchés et ceux qui "
            "restent non-concluables, honnêtement."
        )
    if band == _BAND_PARTIAL:
        return (
            "Caractérise l'analyse comme PARTIELLE : elle touche certaines "
            "dimensions mais en manque de clés. Diagnostic honnête : nomme ce "
            "qui est couvert et ce qui manque (axes listés)."
        )
    # BELOW
    return (
        "Caractérise l'analyse comme MINIMALE : la couverture analytique est "
        "réduite. Donne la liste honnête des axes non-concluables. Ne rejette "
        "pas la responsabilité sur des facteurs externes (timeout, DLL) sans "
        "reconnaître la responsabilité du pipeline dans la dégradation gracieuse."
    )


def _strategy_suffix(strategy: str) -> str:
    """Render a counter-argument's observed strategy as a parenthetical suffix.

    #1668 conclusion-side: ``strategy`` is free text. #3328 leg 2: only a
    KNOWN enum value renders (its French name, :func:`strategy_label_fr`) —
    free text renders as nothing, like an empty strategy, never as dangling
    empty parens (which read as a labelled-but-empty slot, the #1019 shape)
    and never as free English on this French surface.
    """
    s = strategy_label_fr(strategy)
    return f" ({s})" if s else ""


def _assemble_act3_prompt(evidence: Act3Evidence) -> str:
    """Build the §4-compliant LLM-conducted prompt for the Acte III conclusion.

    The prompt varies with the evidence (hence with the corpus) — it is not a
    static template (#1108/#405). It hands the LLM the gated verdict ceiling,
    the real strengths/weaknesses, and the actionable material (counters +
    structuring weak points), and instructs it to weave the three beats.

    Returns the prompt with its raw ``arg_N`` ids still in place — the
    relabel seam (#3296) is applied by :func:`build_act3_prompt`, so the
    bounded retry (#3343/#3358) can append its correction blocks to THIS
    text and route everything through the same seam in one pass: one
    letter table, one legend, no id the writer ever sees.
    """
    verdict = evidence.verdict

    # --- Synthèse honnête (gated) ---
    if verdict is not None:
        axes_present = ", ".join(verdict.nontrivial_axes) or "aucun axe non-trivial"
        axes_missing = ", ".join(verdict.missing_axes) or "aucun"
        synthesis_block = (
            f"Bande de verdict : {verdict.band} "
            f"(couverture analytique : "
            f"{accord(verdict.axes_count, 'axe non-trivial', 'axes non-triviaux')} "
            f"sur 6).\n"
            f"  Axes touchés : {axes_present}.\n"
            f"  Axes manquants / non-concluables : {axes_missing}.\n"
            f"  Plafond de claim autorisé : {_band_claim_ceiling(verdict.band)}"
        )
    else:
        synthesis_block = "Bande de verdict : NON CALCULABLE (gates G1–G4 non passés)."

    # --- Mode vertueux (spec §5) — titre sur les vertus quand l'état le dit ---
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if is_virtuous:
        virtuous_section = (
            "MODE VIRTUEUX (spec §5) — DÉCISION DE TITRE :\n"
            "Le TITRE de l'Acte III porte sur ce qui TIENT : les vertus mesurées,\n"
            "la robustesse formelle, la tenue des schemes. Le pipeline n'a localisé\n"
            "AUCUN sophisme sur ce texte — ce n'est pas un manque à combler, c'est\n"
            "le résultat honnête. Ne fabrique JAMAIS de sophisme ni de point faible\n"
            "pour remplir un battement (anti-pendule #1019/#369). Si un battement\n"
            "manque de matière faiblesse, titre sur la force qui le justifie.\n"
            f"Dérivation du flag : {vm.reasoning if vm is not None else ''}\n\n"
        )
        consigne_virtue = (
            "- MODE VIRTUEUX : ouvre la synthèse en caractérisant le discours par\n"
            "  ses vertus (ce qui tient). L'appréciation mène avec les forces ; les\n"
            "  faiblesses (si aucune localisée) s'effacent honnêtement. Le « que\n"
            "  faire » devient « comment s'appuyer sur ce qui tient / le préserver »\n"
            "  plutôt que « comment contrer ».\n"
        )
    else:
        virtuous_section = ""
        consigne_virtue = ""

    # --- Appréciations (forces + faiblesses) ---
    if evidence.quality_strengths:
        strengths_lines = "\n".join(
            # #3394 — the score arrives with its scale and direction
            # (« 0,9 sur 1,0 — plus haut = meilleur »), never bare: the old
            # line read « 1.0 sur 1 des 8 arguments évalués », where « sur »
            # carried the scale and the count in one word.
            f"  - {s.virtue} : score {score_with_scale(s.score, 1.0, decimals=1)} ; "
            f"vertu atteinte sur {s.args_at_top} des {s.args_evaluated} "
            f"arguments évalués — {s.units_total} unités"
            for s in evidence.quality_strengths[:6]
        )
        # #3159 — the generalisation was a RULE aimed at the writer (#3137) and
        # the first post-#3143 render broke it. The rule is gone.
        # #3335 (#3182 shape) — nor does the writer COPY the verdict any more:
        # three paid passes out of three paraphrased it and lost its base, the
        # last adding quantifiers nothing measures. The pipeline grafts the
        # sentence under ``VERDICT_HEADING`` after the prose, and the prompt
        # says so — the note names the heading, the writer restates none of
        # it. The absent branch keeps its coding instruction: when no virtue
        # reaches the bar there is no reader sentence to print.
        _verdict_sentence = discourse_virtue_reader_sentence(evidence.quality_strengths)
        if _verdict_sentence:
            strengths_lines += (
                "\n  "
                + _verdict_sentence
                + f" (chiffres du pipeline — rendu sous « {VERDICT_HEADING} » "
                "après ta prose : ne le reformule pas.)"
            )
        else:
            strengths_lines += "\n  " + discourse_virtue_sentence(
                evidence.quality_strengths
            )
    else:
        strengths_lines = (
            "  (axe qualité non concluable — aucune vertu caractérisée à "
            "acknowledger)"
        )
    if evidence.weak_points:
        # #3394 — the definition rides the label's FIRST mention only: the
        # reader learns what the label means once, and a repeated definition
        # on every line would bury the document-grounded detail.
        _defined_labels = set()
        _weak_lines = []
        for wp in evidence.weak_points[:8]:
            # #3231 — only a fallacy point carries a detector's confidence
            # (a Dung/PL/FOL verdict is a computation, not a measurement —
            # it has no confidence to print); among them, unmeasured is
            # printed as unmeasured, never filled in (#3029).
            line = (
                f"  - [{wp.source}] {wp.label} sur {wp.target_arg_id}"
                + (f" : {wp.detail}" if wp.detail else "")
                + (
                    f" — {detector_confidence_note(wp.confidence)}"
                    if wp.source == "fallacy"
                    else ""
                )
            )
            if wp.definition and wp.label not in _defined_labels:
                _defined_labels.add(wp.label)
                line += f" ({wp.definition})"
            _weak_lines.append(line)
        weaknesses_lines = "\n".join(_weak_lines)
    else:
        weaknesses_lines = (
            "  (aucun point faible localisé — texte vertueux : titre sur la "
            "robustesse formelle et la tenue des schemes)"
        )
    # #3180 — reported detections are not weaknesses, but they were found: say
    # so with their third-party author rather than silently dropping them.
    reported_block = ""
    if evidence.reported_fallacies_total:
        _n_rep = evidence.reported_fallacies_total
        # #3429 — no label, no attribution: an unlabelled ``reported`` must
        # not be handed to « the quoted voices » (the panel read exactly that
        # out of the bare « le texte les dénonce ou les cite »).
        _labels = list(evidence.reported_fallacies_labels or ())
        if _labels:
            _who = "le texte nomme le tiers : " + ", ".join(
                f"« {label} »" for label in _labels
            )
        else:
            _who = "le texte ne nomme aucun tiers : ne les attribue à aucune voix citée"
        reported_block = (
            "[SOPHISMES RAPPORTÉS — geste d'un tiers, non commis par le "
            "locuteur]\n"
            f"  {accord(_n_rep, 'sophisme rapporté', 'sophismes rapportés')} : "
            f"le texte les dénonce ou les cite ; {_who}. Ils ne sont PAS des "
            "faiblesses du locuteur et n'entrent dans aucun compte de cette "
            "conclusion.\n\n"
        )

    # #1914 résidu b — same citation contract as Act II, on the weak-point
    # lines that carry a ref. Conditional: no ref, no rule (never instruct
    # the conductor about a citation that has nothing to cite), and the
    # example interpolates a REAL ref (a bracketed placeholder would pollute
    # the ref namespace a conductor scans).
    annex_ref_rule = ""
    _wp_refs = [
        r for wp in evidence.weak_points for r in appendix_refs_in(wp.detail or "")
    ]
    if _wp_refs:
        annex_ref_rule = (
            "RÉFÉRENCES D'ANNEXE (la preuve repliée) — quand un point faible "
            "porte une référence d'annexe Dung (entre crochets) :\n"
            f"- Tu PEUX la citer TELLE QUELLE, entre parenthèses, sur le "
            f"battement qui mobilise ce point faible : "
            f"« … (voir {_wp_refs[0]}) ».\n"
            "- Cite une référence SEULEMENT sur le battement concerné ; "
            "jamais sans lui, jamais inventée ni modifiée : copie-la "
            "exactement depuis le bloc ci-dessus.\n"
            "- Une référence ne change PAS le rôle hiérarchique du point "
            "faible (P1 / tension / accompagnement) : la HIÉRARCHIE DU "
            "VERDICT gouverne ; la référence n'indique qu'où la preuve est "
            "repliée.\n\n"
        )

    # --- Que faire (actionnable) ---
    # #1668 conclusion-side: ``strategy`` is free text (an observed rhetorical
    # move), surfaced in parentheses only when present — an empty strategy
    # renders as an absence, not as dangling empty parens (which read as a
    # labelled-but-empty slot).
    shown_counters = evidence.counter_strategies[:_COUNTER_LIST_CAP]
    if shown_counters:
        counters_lines = "\n".join(
            f"  - Pour contrer {cs.target_arg_id}{_strategy_suffix(cs.strategy)} : {cs.snippet}"
            for cs in shown_counters
        )
    else:
        counters_lines = "  (aucun contre-argument généré — recommandations de contre limitées aux exceptions de scheme)"
    # #1622 — the enumeration above is capped, and it is the ONLY place the
    # prompt lists counter-arguments. Measured on 8 real artifacts, 8/8 carried
    # more than the cap (11 to 56), so the conclusion routinely wrote its
    # actionable section from as little as 14 % of the material while nothing
    # told it a remainder existed. ``counters_total`` already reached the
    # evidence bundle; only its *magnitude* had no reader (the boolean did, at
    # the axis test). The notice fires from the gap between what is shown and
    # what exists — not from the cap alone — so it stays honest if the two ever
    # diverge, and stays silent (no false alarm) on a run below the cap.
    _omitted_counters = evidence.counters_total - len(shown_counters)
    if _omitted_counters > 0:
        counters_lines += (
            f"\n  (liste tronquée : {len(shown_counters)} contre-arguments "
            f"listés sur {evidence.counters_total} au total, "
            f"{_omitted_counters} non énumérés ici. N'écris pas, et ne laisse "
            f"pas entendre, que cette liste est exhaustive.)"
        )

    target_lines = (
        "\n".join(
            f"  - {wp.label} sur {wp.target_arg_id} (ancre : {wp.source})"
            for wp in evidence.weak_points
            if wp.source in ("fallacy", "pl", "fol", "dung")
        )
        or "  (aucun point faible structurel localisé)"
    )

    # Epic #1258 / Track 4 #1262, re-keyed by #2965 — real claim text so a
    # reader can re-link the verdict to what was actually said. Each line is
    # keyed by its opaque id: the weaknesses and counter blocks above cite
    # those same ids, and the join is local (a few lines apart), which the
    # measured run showed the writer does make. The texts arrive already
    # capped at ``CITED_UNIT_TEXT_CAP`` — re-cutting them here would
    # reintroduce the 240-char cut that kept 31 % of the winner.
    if evidence.claim_excerpts:
        claims_block = "\n".join(
            f"  - {unit_id} : {text}"
            for unit_id, text in evidence.claim_excerpts[:_MAX_CLAIM_EXCERPTS]
        )
    else:
        claims_block = "  (aucune revendication extraite — G1 non passé)"
    # #2850 lot 4 — same idiom as the counters notice above (#1622): the
    # excerpt list is capped and is the ONLY place the writer sees claim
    # text, so it must say it is capped or the conclusion writes as if the
    # five units were the whole inventory. Fires from the gap between what
    # is listed and what the selection could have listed, never from the cap
    # alone — a run below the cap stays silent. Counts only: no source text.
    _omitted_excerpts = evidence.claim_excerpts_total - len(evidence.claim_excerpts)
    if _omitted_excerpts > 0:
        claims_block += (
            f"\n  (liste tronquée : {len(evidence.claim_excerpts)} revendications "
            f"listées sur {evidence.claim_excerpts_total} citables au total, "
            f"{_omitted_excerpts} non énumérées ici. N'écris pas, et ne laisse "
            f"pas entendre, que cette liste est exhaustive.)"
        )

    # #3214 — the units Act II weighs, joined to the citations above by a
    # map edge. Same idioms as the claims block: texts arrive already capped
    # at ``CITED_UNIT_TEXT_CAP``, the count cap's drops are stated (never
    # silent), and an empty join is RENDERED — an empty section and a missing
    # section read the same to the writer (#1667).
    if evidence.joined_excerpts:
        joined_block = "\n".join(
            f"  - {unit_id} ({relation}) : {text}"
            for unit_id, relation, text in evidence.joined_excerpts
        )
    else:
        joined_block = (
            "  (aucune unité pesée par l'Acte II ne rejoint les citations "
            "par une arête du graphe)"
        )
    _omitted_joined = evidence.joined_excerpts_total - len(evidence.joined_excerpts)
    if _omitted_joined > 0:
        joined_block += (
            f"\n  (liste tronquée : {len(evidence.joined_excerpts)} unités "
            f"jointes listées sur {evidence.joined_excerpts_total} jointes au "
            f"total, {_omitted_joined} non énumérées ici. N'écris pas, et ne "
            f"laisse pas entendre, que cette liste est exhaustive.)"
        )

    what_next_block = (
        "  Comment se faire son avis : aide le lecteur à relier le verdict à ce "
        "qu'il a entendu ou lu du discours. Le « que faire » n'est PAS une "
        "préparation de débat (comment contrer, quels coups jouer) — c'est un "
        "apprentissage critique : quels passages le lecteur doit recevoir avec "
        "prudence, lesquels tiennent, et pourquoi, pour qu'il forme son propre "
        "jugement. Les faiblesses localisées ci-dessus sont les points de "
        "prudence, pas des cibles à abattre."
    )

    # --- SV (#1182): délibération collective (governance + debate) ---
    deliberation_lines: List[str] = []
    gv = evidence.governance_verdict
    if gv is not None:
        # #2965 / R1077 — the origin is `winner_provenance` (#2969), never
        # `extraction_method`: both branches said "vote social-choice"
        # whatever produced the verdict, so an LLM resolution read as a vote.
        # R1078 — the GOUVERNANCE line is ONE shared renderer (cited_units,
        # same as Acte II): the fallback producers write a STRATEGY
        # (`compromise`) and a MEDIATION TYPE (`collaborative`) into
        # `winner`, not a ranked unit — presenting those as « l'argument
        # arrivé en tête » was the R1078 blocker on PR #3000.
        gov_warning, gov_lead = render_governance_lead(
            gv.method,
            gv.winner,
            evidence.governance_winner_text,
            gv.winner_provenance,
            gv.method_provenance,
            tail="(options opaques, FB-34.)",
            # #3001 (a′) — the robustness band's inputs (vote only).
            support_by_option=gv.support_by_option,
            methods_by_option=gv.methods_by_option,
            n_methods_decided=gv.n_methods_decided,
            winner_basis=gv.winner_basis,
            # #3394 (tranche R1145) — the protocols, named apart from the
            # vote's fraction.
            n_consensus_protocols=len(gv.consensus_protocols) or None,
            # #3308 — what the fallacy pass established about THIS winner.
            examination=evidence.examination_by_unit.get(str(gv.winner).strip(), ""),
        )
        # #2969 / #2989 rework: a divergent vote is part of the verdict —
        # name every distinct winner by WHAT IT SAYS, never reduce the
        # conclusion to one "leading argument" the methods never agreed on,
        # and never hand the writer two bare ids (#2965/#2980). An id stays
        # only for a winner whose text could not be localized. #3001: each
        # winner's qualitative support travels beside its text.
        divergence = render_divergence_clause(
            evidence.governance_divergent_texts,
            support_by_option=gv.support_by_option,
            methods_by_option=gv.methods_by_option,
            n_methods_decided=gv.n_methods_decided,
            # #3308 — each divergent winner's examination status, on its line.
            examination_by_unit=evidence.examination_by_unit,
        )
        if divergence:
            gov_lead += divergence
        if gov_warning:
            deliberation_lines.append(gov_warning)
        deliberation_lines.append(gov_lead)
        # #3386 — the coalition play's facts, beside the verdict (same as
        # Acte II): producer-rendered, no prompt rule added.
        if gv.coalition_note:
            deliberation_lines.append(f"  {gv.coalition_note}")
    if evidence.debate_exchanges:
        for i, ex in enumerate(evidence.debate_exchanges, start=1):
            scheme_anchor = ""
            if ex.scheme:
                scheme_anchor = f" [scheme : {ex.scheme}"
                if ex.critical_question:
                    scheme_anchor += f" — question critique : {ex.critical_question}"
                scheme_anchor += "]"
            deliberation_lines.append(
                f"  - DÉBAT (échange {i}) : position « {ex.point} » / "
                f"réplique « {ex.rebuttal} »{scheme_anchor}. "
                f"{_DEBATE_PROVENANCE_TAG}"
            )
    deliberation_block = (
        "\n".join(deliberation_lines)
        if deliberation_lines
        else "  (aucune délibération governance/débat non-triviale — ne la fabrique pas)"
    )

    # #1605 — what the run did NOT genuinely evaluate. Measured on three real
    # corpora: the conclusion read the same whether 0, 2 or 4 axes of 5 had been
    # lost, because this ledger reached no restitution module. The block is
    # rendered in both states (present / empty) so the LLM sees an explicit
    # "nothing was lost" rather than the ambiguity of a missing section.
    if evidence.absent_dimensions:
        absence_block = "\n".join(
            f"  - {d.label} : NON ÉVALUÉE ({d.status}). {d.reason}"
            for d in evidence.absent_dimensions
        )
    else:
        absence_block = (
            "  (aucune dimension perdue — toutes les analyses structurées ont "
            "abouti sur ce corpus)"
        )

    # #3162 item 2 — the reading rule follows the qualifier it governs. A
    # line qualified « (position rapportée) » says the unit is a position the
    # text reports/cites; the writer inverted exactly that into "the
    # speaker's case stands poorly". #3513 — the qualifier now rides Dung and
    # ABA lines too, so the rule follows it on EVERY surface: any structured
    # finding statement or any weak-point label carrying it brings the rule.
    # Conditional on the qualifier: a briefing with no such line gets no rule
    # (never instruct the writer about a side nothing stated, and never claim
    # a side a line did not carry).
    setaf_side_rule = ""
    if any(
        _SETAF_REPORTED_QUALIFIER in f.statement for f in evidence.structured_findings
    ) or any(
        _SETAF_REPORTED_QUALIFIER in (wp.label or "") for wp in evidence.weak_points
    ):
        setaf_side_rule = _SETAF_REPORTED_POSITION_RULE

    # #1667 — the symmetric presence side. Rendered in both states, exactly like
    # the absence block above: an empty section and a missing section read the
    # same to the LLM, and this channel exists precisely because a silence was
    # being read as a verdict.
    if evidence.structured_findings:
        presence_block = "\n".join(
            f"  - {f.label} : {f.statement}" for f in evidence.structured_findings
        )
    else:
        presence_block = (
            "  (aucun cadre d'argumentation structurée n'a établi de relation "
            "exploitable sur ce corpus — ne fabrique aucun résultat formel)"
        )

    # #1911 — the global synthesis's structured findings. Empty section and
    # missing section read the same to the LLM, so this renders in both states
    # like the presence/absence blocks above.
    if evidence.global_findings:
        # #3156 — each anchor carries its unit's text, and says when the same
        # text is ALSO listed among the claims. Bare ids are what let the
        # writer rebind a convergence to whichever passage it could describe.
        excerpted_ids = {unit_id for unit_id, _ in evidence.claim_excerpts}

        def _anchored(finding: Any) -> str:
            rendered: List[str] = []
            for cite in finding.cites:
                cite_id = str(cite)
                text = evidence.anchor_excerpts.get(cite_id)
                if not text:
                    rendered.append(cite_id)
                    continue
                marker = (
                    " (déjà listé parmi les revendications)"
                    if cite_id in excerpted_ids
                    else ""
                )
                rendered.append(f"{cite_id} — « {text} »{marker}")
            return ", ".join(rendered)

        global_block = "\n".join(
            f"  - [{f.kind}] {f.statement} (ancres : {_anchored(f)})"
            for f in evidence.global_findings
        )
        # #3193 (rework) — a dropped anchor loses its excerpt; the reader must
        # be told the line lost referents, not guess it (zero in practice: the
        # cap equals the projection's own bound). #3296 — the ids themselves
        # no longer print anywhere (the seam relabels them), so the notice
        # says the anchor is not designated, not that it stays "bare".
        if evidence.anchors_dropped:
            global_block += (
                f"\n  - ({evidence.anchors_dropped} ancre(s) omise(s) au plafond "
                "— ces unités ne sont désignées nulle part dans ce bloc)"
            )
    else:
        global_block = (
            "  (aucune convergence inter-axes ni gate de synthèse ne se dégage "
            "— n'en fabrique aucune)"
        )

    # #1914 (Acte I slice) — the question the framing closed on. Rendered in
    # BOTH states (#1941 discipline: a silence must never be misread) — when
    # Acte I posed no question, the honest-absence wording renders and the
    # consigne forbids inventing a retroactive one.
    if evidence.interpretive_question:
        question_block = (
            f"  {evidence.interpretive_question}\n"
            "  (posée par la mise en situation — cette conclusion doit y "
            "répondre)"
        )
    else:
        question_block = (
            "  (aucune question interprétative n'a été posée en Acte I — "
            "n'en fabrique pas une rétroactive)"
        )

    # #3432 (ask 3) — the points the framing announced as needing to be
    # settled. Rendered in BOTH states (#1941 discipline: a silence must never
    # be misread) — when the framing announced none, the honest-absence
    # wording renders and the consigne forbids inventing one. Before this
    # block, only the closing question rode here: a point announced in Acte
    # I's prose reached no later act, so nothing ever closed it (the panel's
    # `5075cd82` announced a false dilemma as a point to test and no act
    # settled it).
    if evidence.announced_checks:
        checks_block = "\n".join(f"  - {check}" for check in evidence.announced_checks)
        checks_block += (
            "\n  (annoncés par la mise en situation — chacun doit être CLOS "
            "par cette conclusion)"
        )
    else:
        checks_block = (
            "  (la mise en situation n'a annoncé aucun point à trancher — "
            "n'en fabrique pas un rétroactif)"
        )

    # #3432 (ask 2) — what the thesis leaves out, per the personas (#3377).
    # Rendered in BOTH states (#1941 discipline): when a persona named no
    # blind spot, the honest-absence line renders for that persona — an empty
    # block would let the writer fill the gap with the text's own content,
    # which is exactly the confusion the model_knowledge label exists to
    # prevent. Each line carries its persona: the reader must be able to tell
    # a historian's omission from a strategist's.
    blind_spot_lines = []
    if evidence.historical_blind_spot:
        blind_spot_lines.append(f"  - l'historien : {evidence.historical_blind_spot}")
    else:
        blind_spot_lines.append(
            "  - l'historien : (aucune tache aveugle nommée sur ce run — "
            "n'en invente pas une)"
        )
    if evidence.strategic_blind_spot:
        blind_spot_lines.append(f"  - le stratège : {evidence.strategic_blind_spot}")
    else:
        blind_spot_lines.append(
            "  - le stratège : (aucune tache aveugle nommée sur ce run — "
            "n'en invente pas une)"
        )
    blind_spot_block = "\n".join(blind_spot_lines)

    # #1914 (Acte III slice) — the salience hierarchy. The structure carries
    # the ranking; the consigne binds the verdict beat to it. Renders in
    # both states so a silence is never read as a verdict.
    sal = evidence.salience
    if sal is not None and sal.ranked:
        hierarchy_block = "\n".join(
            f"  - P{item.weight} [{item.kind}] {item.statement} "
            f"(ancres : {', '.join(item.cites)})"
            for item in sal.ranked
        )
    else:
        hierarchy_block = (
            "  (aucun résultat ne porte le verdict par lui-même — les labels "
            "et compteurs restent du contexte, pas des findings)"
        )
    if sal is not None and sal.surplus.established:
        surplus_established = "\n".join(
            f"  - {s.statement} (ancres : {', '.join(s.cites)})"
            for s in sal.surplus.established
        )
    else:
        surplus_established = (
            "  - RIEN au-delà d'une lecture attentive : aucun résultat de ce "
            "run n'établit ce qu'une lecture unique ne peut pas. Les "
            "compteurs et labels disponibles NE SONT PAS un surplus "
            "interprétatif."
        )
    if sal is not None and sal.surplus.procedural_only:
        surplus_procedural = "\n".join(
            f"  - {line}" for line in sal.surplus.procedural_only
        )
    else:
        surplus_procedural = (
            "  (aucune matière purement procédurale à écarter nommément)"
        )
    surplus_block = (
        "  ÉTABLI (ce qu'une lecture simple ne peut pas produire) :\n"
        f"{surplus_established}\n"
        "  PUREMENT PROCÉDURAL (contexte, jamais un surplus) :\n"
        f"{surplus_procedural}"
    )

    # #2845 — the metadata block Acte I has always carried. The prompt's own
    # instruction asks the writer to name the speaker "via les métadonnées";
    # without this block that instruction is unsatisfiable on every run, and the
    # writer resolves it against the extracts — where a reply names only the
    # interlocutor.
    if evidence.metadata:
        meta_block = "\n".join(f"  - {k} : {v}" for k, v in evidence.metadata.items())
    else:
        meta_block = (
            "  (aucune métadonnée renseignée — le locuteur et l'arène ne sont "
            "pas documentés par ce run ; pour chacun, voir les blocs LOCUTEUR "
            "et ARÈNE DISCURSIVE ci-dessous, qui disent d'où vient chaque "
            "valeur — un locuteur INFÉRÉ du texte n'est pas une métadonnée)"
        )

    opaque_block = f"{_OPAQUE_ID_DIRECTIVE}\n\n" if not evidence.deanonymized else ""

    # #2850 lot 6 — the recorded reading bounds (empty when nothing was
    # recorded: the rule's absent case then forbids inventing one).
    reading_block = format_reading_block(evidence.readings)
    if reading_block:
        reading_block += "\n\n"

    # #3395 (acts slice) — the first reading's block, beside the reading
    # bounds: what the one whole-document read found the TEXT doing, before
    # any lens ran. Empty on a state that carries no record (omitted whole).
    first_reading_block = (
        f"{evidence.first_reading}\n\n" if evidence.first_reading else ""
    )

    prompt = (
        "Tu es l'auteur de l'ACTE III d'un rapport de restitution argumentative\n"
        "— la CONCLUSION ORIENTÉE LECTEUR : un lecteur qui a vu ou lu le discours\n"
        "doit pouvoir s'y retrouver, relier le verdict à ce qui a été dit, et se\n"
        "faire son propre avis. Va chercher le lecteur dans sa connaissance du\n"
        "contexte et des locuteurs. Trois battements en prose :\n"
        "1. Ce que le discours dit vraiment : nomme le locuteur et l'arène (d'après\n"
        "   les blocs de données ci-dessus, chacun avec sa provenance étiquetée),\n"
        "   et CITE ce qui a réellement été dit (les\n"
        "   revendications extraites ci-dessous) — le lecteur doit reconnaître\n"
        "   le discours qu'il a entendu.\n"
        "2. Ce qui tient et ce qui ne tient pas : un verdict en langage clair sur\n"
        "   chaque revendication, pour un lecteur formant son jugement — pas un\n"
        "   catalogue de labels techniques. Les sophismes/contre-arguments sont\n"
        "   nommés par ce qu'ils signifient pour le lecteur.\n"
        "3. Comment se faire son avis : ce que le lecteur doit recevoir avec\n"
        "   prudence, ce qui est solide, et pourquoi. La machinerie formelle\n"
        "   (solveur, cadre de Dung) est un APPUI lisible, jamais un titre.\n\n"
        f"{opaque_block}"
        f"{_WEAVING_RULE}\n\n"
        f"{_FAIL_LOUD_INSTRUCTION}\n\n"
        f"{virtuous_section}"
        # #3073 (cross-review) — même requalification que l'Acte I : le titre
        # disait « vérifiées » alors que l'arène peut être INFÉRÉE du texte et
        # les revendications extraites sont une lecture de modèle. Chaque bloc
        # porte sa provenance ; le titre n'en promet plus une seule.
        "DONNÉES DU STATE — provenance étiquetée bloc à bloc "
        "(ne citer que ces données ; « métadonnée enregistrée » = lue à la "
        "source du corpus ; « inférée du texte » = lecture de modèle, jamais "
        "une donnée vérifiée) :\n\n"
        f"[MÉTADONNÉES DE LA SOURCE — l'origine du discours, telle qu'enregistrée]"
        f"\n{meta_block}\n\n"
        # #3082 — le locuteur vient du MÊME enregistrement que celui des
        # Actes I et II (valeur + provenance) : trois actes, une valeur, une
        # étiquette. Le bloc MÉTADONNÉES reste « telle qu'enregistrée » —
        # c'est le registre brut ; l'enregistrement partagé est ici, et il
        # sait aussi dire « inféré du texte ».
        f"[LOCUTEUR — provenance de la valeur]\n"
        f"  {format_speaker_line(evidence.speaker)}\n\n"
        f"{first_reading_block}"
        f"{reading_block}"
        # #3073 — l'arène vient du MÊME enregistrement que celui de l'Acte I
        # (valeur + provenance) : deux actes, une valeur, une étiquette. Elle
        # sort du bloc « telle qu'enregistrée » — une inférence du texte n'y a
        # pas sa place (c'était la moitié Acte III de la contradiction).
        f"[ARÈNE DISCURSIVE — provenance de la valeur]\n"
        f"  {format_arena_line(evidence.arena)}\n\n"
        f"[CE QUI A ÉTÉ DIT — revendications extraites]\n{claims_block}\n\n"
        # #3214 — the join follows the citations: units the Act II analysis
        # weighed and the map links to them, so the conclusion cannot deny in
        # good faith what Act II weighed a page earlier. Context, not a new
        # inventory (the cap and its notice say so).
        "[REVENDICATIONS PESÉES PAR L'ACTE II — jointes aux citations par le "
        f"graphe d'arguments]\n"
        "  Unités que l'Acte II a pesées et qu'une arête du graphe (attaque\n"
        "  ou soutien) relie à une citation ci-dessus : contexte de la\n"
        "  conclusion, pas un inventaire supplémentaire à énumérer.\n"
        f"{joined_block}\n\n"
        f"[VERDICT GATED — plafond de claim honnête]\n{synthesis_block}\n\n"
        f"[CE QUI TIENT — forces (qualité)]\n{strengths_lines}\n\n"
        f"[CE QUI NE TIENT PAS — faiblesses localisées]\n{weaknesses_lines}\n\n"
        f"{reported_block}"
        f"{annex_ref_rule}"
        f"[CONTRE-POINTS — ce qui affaiblit les revendications]\n{counters_lines}\n\n"
        f"[POINTS DE PRUDENCE — ancrages structurels]\n{target_lines}\n\n"
        f"[DÉLIBÉRATION COLLECTIVE — governance + débat]\n{deliberation_block}\n\n"
        f"[CE QUE LES CADRES STRUCTURÉS ÉTABLISSENT]\n{presence_block}\n\n"
        f"[CONVERGENCES GLOBALES — synthèse inter-axes, ancrées]\n{global_block}\n\n"
        f"[LA QUESTION DE L'ACTE I — celle que la conclusion doit trancher]\n{question_block}\n\n"
        f"[POINTS À TRANCHER — ceux que la mise en situation a annoncés]\n{checks_block}\n\n"
        f"[CE QUE LA THÈSE LAISSE DE CÔTÉ — lecture des personas, "
        f"connaissance du modèle]\n{blind_spot_block}\n\n"
        f"[HIÉRARCHIE DU VERDICT — ce qui porte la conclusion]\n{hierarchy_block}\n\n"
        f"[SURPLUS MULTI-AGENTS — au-delà d'une lecture simple]\n{surplus_block}\n\n"
        f"[DIMENSIONS NON ÉVALUÉES — à dire, jamais à taire]\n{absence_block}\n\n"
        f"{what_next_block}\n\n"
        "CONSIGNE DE RÉDACTION :\n"
        f"{consigne_virtue}"
        "- Rédige 3 paragraphes thématiques (un par battement), en prose lisible,\n"
        "  pas une liste de champs. Titres thématiques en ###.\n"
        "- OUVRE en nommant le locuteur d'après le bloc LOCUTEUR et l'arène\n"
        "  d'après le bloc ARÈNE DISCURSIVE ci-dessus — chacun avec sa\n"
        "  provenance étiquetée : une valeur INFÉRÉE du texte se dit comme\n"
        "  telle, jamais comme vérifiée — et en citant la (les) revendication(s)\n"
        "  centrale(s) du discours — le lecteur doit raccrocher à ce qu'il a\n"
        "  entendu. Reformule fidèlement, ne galvaude pas le propos.\n"
        "- UN NOM DE PERSONNE CITÉ DANS LES REVENDICATIONS EST UN INTERLOCUTEUR\n"
        "  (celui à qui le discours répond), JAMAIS le locuteur : ne lui attribue\n"
        "  aucune position.\n"
        # #3082 — la clause « Si le bloc métadonnées ne renseigne pas le
        # locuteur, DIS-LE et n'en nomme aucun » disait l'intention, pas la
        # phrase : le writer la recopiait comme règle au lecteur. La règle
        # partagée (celle des Actes I et II) donne maintenant la phrase à
        # écrire, tel quel.
        f"{SPEAKER_NAMING_RULE}\n"
        f"{READING_BASIS_RULE}\n"
        f"{setaf_side_rule}"
        # #3237 — the cause rule is now the shared constant from fol_cause
        # (the vocabulary's one home): Act II misstated a recorded cause
        # because only this act carried the rule. Same words, one father.
        "- Le verdict formel (Tweety/Dung) est un APPUI, jamais un titre. "
        f"{FORMAL_CAUSE_NAMING_RULE} « l'analyse formelle confirme la cohérence de ce\n"
        "  raisonnement » (théorie consistante — un résultat aussi) et « le cadre\n"
        "  d'argumentation isole cette revendication comme rejetée » restent\n"
        "  disponibles — toujours au service du jugement du lecteur, jamais en\n"
        "  sous-section isolée.\n"
        "- Respecte STRICTEMENT le plafond de claim de la bande : ne formule rien\n"
        "  au-delà de ce qu'elle autorise.\n"
        # #3158 (second instance) — le canal débat rendait un VERDICT de
        # réplique comme une détection du rapport, sur une unité où aucun
        # détecteur n'avait rien enregistré.
        "- Une réplique de débat (ligne DÉBAT, marquée « jamais vérifiée ») reste\n"
        "  attribuée : si tu en reprends le verdict, écris « dans le débat, la\n"
        "  réplique objecte que… ». Tu ne le présentes JAMAIS comme une détection.\n"
        "- Un NOM DE SOPHISME dans ta prose est une détection : tu ne le nommes que\n"
        "  sur une unité où un sophisme est réellement enregistré (bloc des\n"
        "  procédés relevés). Si aucune détection ne couvre l'unité, tu ne lui en\n"
        "  prêtes aucun — même quand une réplique de débat l'affirme. Et le\n"
        # #3231 — même contrat de standing qu'Acte II : la force d'une détection
        # est celle que son détecteur lui a donnée (confiance imprimée sur la
        # ligne, réserve écrite en fin de justification). #3369 : l'échelle
        # existe, mais elle est imprimée — le mot à côté de la décimale, le
        # rédacteur le reprend, il ne le retrace pas.
        "  standing du nommé suit son détecteur : une détection à confiance\n"
        "  basse, ou que sa justification tient pour provisoire, se cite comme\n"
        "  une lecture provisoire — jamais comme une faute établie. "
        # #3248 — même échelle, même constante que l'Acte II (le geste
        # #3237 : une échelle, un père) : le chiffre du détecteur est un
        # vocabulaire de preuve, jamais du récit.
        f"{DETECTION_STANDING_RULE}\n"
        "- JARGON INTERNE INTERDIT dans la prose : ne recopie JAMAIS un\n"
        "  identifiant technique brut — token snake_case (agent_1, social_choice,\n"
        "  modal_kb…), nom d'agent numéroté, ou nom de méthode/modèle interne.\n"
        "  Ils sont opaques pour le lecteur non-technicien à qui ce récit\n"
        "  s'adresse. Décris-les par leur RÔLE en français courant (« l'argument\n"
        "  arrivé en tête », « la méthode de vote employée »). L'opacité des\n"
        "  sources (FB-34) reste préservée : décrire par rôle ne\n"
        "  déanonymise aucune source.\n"
        "- La conclusion doit VARIER selon le contenu réel ci-dessus : pas de\n"
        "  prose générique recyclable.\n"
        "- Si le bloc CE QUE LES CADRES STRUCTURÉS ÉTABLISSENT porte une relation,\n"
        "  SERS-T'EN dans le deuxième battement : elle dit comment les propos du\n"
        "  locuteur se tiennent ENTRE EUX (ce qui s'appuie sur quoi, quel\n"
        "  enchaînement résiste), ce qu'aucune autre analyse du rapport ne dit.\n"
        "  Rends-la en français courant, au service du jugement du lecteur, sans\n"
        "  la nommer par son formalisme et sans en faire un titre. Si le bloc dit\n"
        "  qu'aucun cadre n'a rien établi, n'invente aucun résultat formel : cette\n"
        "  absence-là se tait, elle relève du bloc suivant.\n"
        "- Si le bloc CONVERGENCES GLOBALES porte des convergences, SERS-T'EN\n"
        "  comme DEGRÉ DE CONFIANCE du verdict dans le deuxième battement :\n"
        "  quand plusieurs méthodes indépendantes s'accordent sur un même\n"
        "  argument, dis-le au lecteur en français courant (ce qui frappe, c'est\n"
        "  que tout converge vers le même point faible) — sans énumérer les\n"
        "  méthodes par leur nom technique. Si le bloc dit qu'aucune convergence\n"
        "  ne se dégage, n'invente aucune unanimité.\n"
        "- HIÉRARCHIE : fonde le deuxième battement sur la HIÉRARCHIE DU VERDICT\n"
        "  ci-dessus, dans cet ordre — les P1 (points décisifs) d'abord,\n"
        "  puis les tensions, puis\n"
        "  l'accompagnement. Un item [preference] est la préférence de la\n"
        "  délibération collective — le coup que son vote a placé en tête :\n"
        "  rends-le comme tel (un choix de la délibération, jamais une force\n"
        "  établie par un solveur) et jamais au-dessus d'un P1. Un label hors\n"
        "  hiérarchie est du contexte : il peut illustrer, jamais porter le\n"
        "  verdict. Ne rejoue pas chaque label au même niveau.\n"
        "- QUESTION : si le bloc LA QUESTION DE L'ACTE I porte une question,\n"
        "  le DEUXIÈME battement y répond EXPLICITEMENT : tranche-la au moyen\n"
        "  de la hiérarchie du verdict (les points décisifs, P1, d'abord),\n"
        "  puis dis franchement ce\n"
        "  qui reste ouvert. Une conclusion qui ne répond pas à la question\n"
        "  posée en Acte I manque son objet. Si le bloc dit qu'aucune question\n"
        "  n'a été posée, n'en formule pas une rétroactive.\n"
        "- POINTS À TRANCHER : le bloc POINTS À TRANCHER liste les points que\n"
        "  la mise en situation a annoncés. Chacun est CLOS, nommément : soit\n"
        "  tu dis ce que l'analyse établit sur lui (son verdict, appuyé sur la\n"
        "  hiérarchie du verdict), soit tu dis franchement qu'il n'a pas été\n"
        "  atteint — et alors tu ne laisses pas croire qu'il l'a été. Un point\n"
        "  annoncé puis passé sous silence est le défaut que ce bloc répare.\n"
        "  Si le bloc dit qu'aucun point n'a été annoncé, n'en invente aucun.\n"
        # #3432 (ask 2) — the blind-spot block is model knowledge riding the
        # personas' read (#3377): the consigne binds the writer to the same
        # label the state carries, so the omission can never read as the
        # text's own content — nor as something the pipeline extracted.
        "- CE QUE LA THÈSE LAISSE DE CÔTÉ : ce bloc est la lecture des personas\n"
        "  (l'historien, le stratège), étiquetée CONNAISSANCE DU MODÈLE — un\n"
        "  angle de vue que le modèle apporte, jamais un contenu du texte.\n"
        "  Présente-le comme tel si tu t'en sers (« ce que l'analyse éclaire\n"
        "  par contraste »), sans citer le texte à l'appui et sans le\n"
        "  présenter comme une extraction. Une ligne « aucune tache aveugle\n"
        "  nommée » est une absence honnête : n'invente pas d'omission.\n"
        "- QUESTION — PORTÉE D'UNE ABSENCE : une absence que tu constates ne\n"
        "  porte JAMAIS sur le texte, toujours sur ce que l'analyse en a\n"
        "  porté. Dis ce que les unités analysées n'établissent pas (« les\n"
        "  revendications citées ici n'en portent pas la trace nette »),\n"
        "  jamais que le texte ne le montre ou ne le contient pas. Tu n'as lu\n"
        "  que ces unités : une absence dans l'analyse n'est pas une absence\n"
        "  dans le texte.\n"
        "- QUATRE ORDRES DE JUGEMENT, jamais confondus : (1) VÉRITÉ FACTUELLE —\n"
        "  aucun axe de ce run ne l'établit : ne formule jamais qu'un propos est\n"
        "  factuellement vrai ou faux ; (2) ACCEPTABILITÉ ARGUMENTATIVE — ce que\n"
        "  les verdicts formels et la qualité mesurée établissent ; (3)\n"
        "  EFFICACITÉ RHÉTORIQUE — ce que les procédés accomplissent sur\n"
        "  l'auditoire ; (4) PRÉFÉRENCE DE SOLVEUR/MODÈLE — les choix de\n"
        "  sémantique ou de méthode de vote : présente-les comme des choix\n"
        "  d'outil, jamais comme des vérités du discours.\n"
        "- SURPLUS : si le bloc SURPLUS MULTI-AGENTS dit que RIEN n'est établi\n"
        "  au-delà d'une lecture attentive, ne revendique AUCUN apport du\n"
        "  pipeline au-delà de ce qu'une lecture soignée donne. Le lecteur doit\n"
        "  pouvoir distinguer ce que l'analyse multi-agents a CHANGÉ dans\n"
        "  l'interprétation de ce qu'elle a seulement compté.\n"
        "- Si le bloc DIMENSIONS NON ÉVALUÉES en liste, DIS-LE au lecteur dans le\n"
        "  troisième battement, en une phrase et en français courant : quel angle\n"
        "  d'analyse n'a pas abouti sur ce texte, et donc ce que ce verdict ne\n"
        "  couvre pas. Le lecteur doit pouvoir situer la portée de ce qu'il lit.\n"
        "  N'en fais ni un titre ni un paragraphe : une absence dite est une\n"
        "  précision honnête, pas un aveu de faiblesse — et l'analyse conduite\n"
        "  garde toute sa valeur. Si le bloc dit qu'aucune dimension n'a été\n"
        "  perdue, n'invente aucune réserve.\n"
        "- Rédige en français, markdown léger. 300-600 mots selon la richesse.\n"
    )
    # #3296 — the ids stay in the assembled text: the seam
    # (``build_act3_prompt``) relabels every arg_N the data blocks supplied
    # (claims, joined units, weaknesses/counters/targets, salience
    # statements AND their cites — the id is built INTO the statement,
    # conclusion_salience) so the writer's view carries the per-act letter
    # table with its legend. Method cites (FOL, qualite…) are not arg ids
    # and stay.
    return prompt


def build_act3_prompt(evidence: Act3Evidence) -> str:
    """The writer's view of the Acte III prompt — assembled, then relabelled.

    The #3296 seam: one pass of ``label_writer_prompt`` over the assembled
    text, so every ``arg_N`` from every block leaves the writer's view and
    the legend carries each letter's referent. The retry builds on the
    ASSEMBLED text and applies this same seam — never a correction block
    that bypasses it.
    """
    return label_writer_prompt(_assemble_act3_prompt(evidence), evidence.unit_texts)


# --- #1605: the scope limitation the narrative must carry --------------------

# Distinctive French words tying a prose sentence to a specific lost axis. A
# generic hedge ("certaines analyses n'ont pas abouti") must NOT count as having
# named the absence — the reader has to know WHICH angle is missing.
_ABSENCE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "aspic_plus_reasoning": ("défaisable", "revisable", "révisable", "règles strictes"),
    "aba_reasoning": ("hypothès", "contraire"),
    "setaf_reasoning": ("collectiv", "conjoint", "ensemble"),
    "weighted_argumentation": ("pondér", "poids", "force des attaques"),
    "bipolar_argumentation": ("soutien", "appui mutuel"),
    _AXIS_FORMAL_PL: ("propositionnel", "satisfiab"),
    _AXIS_FORMAL_FOL: ("premier ordre", "prédicat"),
}

# Domain-generic capability tokens that must never count as naming an axis —
# every restitution sentence talks about "argumentation".
_CAP_TOKEN_STOP_LIST = frozenset({"argumentation", "reasoning", "analysis"})

# Phrases that mark a scope limitation being stated. Presence is necessary but
# NOT sufficient: it must co-occur with a keyword of an actually-lost axis.
# #2032 cross-review (corpus B): « n'a pas produit de résultat exploitable »
# and « reste non concluable » are ordinary French limitation phrasings the
# original table lacked — the gate returned False before the cue layer (which
# would have matched « pondér ») ever ran.
_SCOPE_LIMIT_MARKERS: Tuple[str, ...] = (
    "n'a pas abouti",
    "n'a pas pu",
    "n'a pas permis",
    "n'a pas produit",
    "non concluable",
    "non évalué",
    "pas été évalué",
    "pas été conduite",
    "pas été menée",
    "ne couvre pas",
    "hors de portée",
    "faute de",
)


def _narrative_states_scope_limit(
    narrative: str, absent: List[AbsentDimension]
) -> bool:
    """True only when the narrative visibly ties a limitation to a lost axis.

    Deliberately strict, and biased toward returning ``False``: a false negative
    costs a redundant sentence, a false positive costs exactly the defect this
    guards against — a conclusion that reads identically whether the run lost 0
    or 4 analytical axes (measured on three real corpora, #1605).

    #2032: an axis the prose names by its LABEL counts as named. The label is
    the French name the prompt itself instructs the LLM to use, so a compliant
    closing sentence (« les relations de soutien… ne sont pas couvertes ») must
    not trigger the fallback. The keyword table alone missed axes it does not
    list (belief_revision) and paraphrases of listed ones — a false negative
    that served the reader the same caveat three times.
    """
    # #2032, the measured root cause: French LLM prose writes the
    # typographic apostrophe (U+2019 « n'a pas abouti ») while the marker
    # table stores the straight one (U+0027) — no marker ever matched, the
    # detector returned False on prose that HAD named the axis, and the
    # reader got the deterministic scope note anyway. Normalise before
    # matching.
    low = narrative.lower().replace("’", "'")
    if not any(m in low for m in _SCOPE_LIMIT_MARKERS):
        return False
    for dim in absent:
        label = dim.label.lower()
        # The label's core (before any parenthetical gloss) — prose names the
        # axis by its name, not by the full label with its gloss.
        label_core = label.split(" (")[0]
        # Distinctive capability tokens (≥6 chars, domain-generic words
        # excluded), truncated to their 6-char stem so the stem crosses the
        # French/English spelling boundary: "bipolar"[:6] = "bipola" also
        # matches "bipolaire". A technical paraphrase names the axis as
        # surely as the label does.
        cap_tokens = tuple(
            t[:6]
            for t in dim.capability.lower().split("_")
            if len(t) >= 6 and t not in _CAP_TOKEN_STOP_LIST
        )
        cues = (
            _ABSENCE_KEYWORDS.get(dim.capability, ()) + (label, label_core) + cap_tokens
        )
        if any(w in low for w in cues):
            return True
    return False


def _scope_note(absent: List[AbsentDimension]) -> str:
    """The deterministic scope paragraph appended when the LLM stayed silent.

    Not a fallback template for the conclusion (#1108 forbids that): the
    conclusion itself is LLM-conducted or absent. This is the one factual
    sentence the run *knows* and the reader cannot infer — appended, never
    substituted.
    """
    labels = [d.label for d in absent]
    if len(labels) == 1:
        listing = labels[0]
        opening = "Un angle d'analyse n'a pas abouti sur ce texte"
        coverage = "cette dimension"
    else:
        listing = ", ".join(labels[:-1]) + f" et {labels[-1]}"
        opening = "Plusieurs angles d'analyse n'ont pas abouti sur ce texte"
        coverage = "ces dimensions"
    return (
        "### Portée de cette analyse\n\n"
        f"{opening} : {listing}. Ce verdict ne couvre donc pas {coverage} — ce "
        "qui précède garde sa valeur sur les angles effectivement conduits."
    )


def _states_absence(lowered_sentence: str) -> bool:
    """True when the sentence names the axis in order to say it produced nothing."""
    return any(m in lowered_sentence for m in _ABSENCE_MARKERS)


def _gate_unsupported_claims(
    narrative: str, nontrivial_axes: List[str]
) -> Tuple[str, List[BlockedClaim]]:
    """Remove assertions resting on an axis that produced nothing.

    The blocking half of the #1605 conclusion gate. ``_band_claim_ceiling``
    *instructs* the LLM; this *enforces*, after the fact, on the produced prose.
    A sentence is blocked when it names an absent axis without stating that the
    axis is absent — the honest wording (#1609) must survive untouched, so the
    absence markers act as an exemption rather than the claim markers acting as
    a trigger on their own.

    Fail loud, not fail hard: the offending sentence is dropped and the drop is
    reported through ``degraded``; the rest of the conclusion is preserved. A
    reader must never receive an unsupported claim, and must never silently lose
    a whole conclusion either.
    """
    absent = [a for a in _ALL_AXES if a not in set(nontrivial_axes)]
    if not absent or not narrative:
        return narrative, []

    blocked: List[BlockedClaim] = []
    out_lines: List[str] = []
    for line in narrative.splitlines():
        chunks = _SENTENCE_RE.findall(line)
        if not chunks:
            out_lines.append(line)
            continue
        kept: List[str] = []
        for chunk in chunks:
            lowered = chunk.lower()
            hit = next(
                (
                    axis
                    for axis in absent
                    if any(m in lowered for m in _AXIS_CLAIM_MARKERS[axis])
                ),
                None,
            )
            if hit is not None and not _states_absence(lowered):
                blocked.append(
                    BlockedClaim(
                        axis=hit, label=_AXIS_LABELS_FR[hit], sentence=chunk.strip()
                    )
                )
                continue
            kept.append(chunk)
        out_lines.append("".join(kept).rstrip())

    if not blocked:
        return narrative, []
    # Removing sentences can leave runs of blank lines where a paragraph was,
    # and can empty a section outright — a bare heading with nothing under it
    # is an artefact of the gate, not something the reader should receive.
    return _drop_empty_headings("\n".join(out_lines)), blocked


def _heading_depth(line: str) -> int:
    """Markdown depth of a heading line, or 0 when the line is not a heading."""
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return 0
    return len(stripped) - len(stripped.lstrip("#"))


def _drop_empty_headings(text: str) -> str:
    """Remove headings whose whole subtree is empty, and collapse the gaps.

    Emptiness is a property of the SUBTREE, not of the lines immediately
    below. A heading that carries its content in subsections has nothing
    directly under it, and a rule that only looked ahead to the next heading
    would delete it while keeping its children — mangling the hierarchy of a
    document the gate never touched. The narrative here is free-form markdown
    conducted by the LLM (``weave_act3_conclusion``), so nested headings are
    ordinary input, not a corner case.

    Walks backwards so children are decided before their parents: a heading
    survives if it has own content OR if any of its descendants survived.
    """
    lines = text.split("\n")
    dropped: set[int] = set()
    # Depths of surviving headings already decided BELOW the current line and
    # not yet absorbed by a shallower heading — i.e. the current candidate's
    # descendants once we reach it.
    surviving_below: List[int] = []
    for i in range(len(lines) - 1, -1, -1):
        depth = _heading_depth(lines[i])
        if depth == 0:
            continue
        has_own_content = False
        for nxt in lines[i + 1 :]:
            if _heading_depth(nxt):
                break
            if nxt.strip():
                has_own_content = True
                break
        has_surviving_descendant = any(d > depth for d in surviving_below)
        # Everything deeper than this heading belongs to its subtree; it is
        # now accounted for and must not count for anything further up.
        surviving_below = [d for d in surviving_below if d <= depth]
        if has_own_content or has_surviving_descendant:
            surviving_below.append(depth)
        else:
            dropped.add(i)
    kept = [line for i, line in enumerate(lines) if i not in dropped]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def _blocked_claim_note(
    blocked: List[BlockedClaim], *, nothing_survived: bool = False
) -> str:
    """The paragraph that replaces what was removed — the removal must be said.

    ``nothing_survived`` is not cosmetic. The structured ``degraded`` dict does
    NOT survive the state round-trip (``_write_act3_conclusion_to_state`` stores
    only the narrative; see the provenance note in ``pipeline_adapter``), so the
    narrative is the ONLY surface that reaches the reader. If every sentence was
    removed, the emptiness has to be stated *here* or it is not stated at all.
    """
    labels = sorted({b.label for b in blocked})
    if len(labels) == 1:
        listing = labels[0]
        subject = "une dimension que cette analyse n'a pas pu établir"
    else:
        listing = ", ".join(labels[:-1]) + f" et {labels[-1]}"
        subject = "des dimensions que cette analyse n'a pas pu établir"
    if nothing_survived:
        return (
            "### Aucune conclusion soutenable\n\n"
            "**Il ne reste aucune conclusion.** L'intégralité de la conclusion "
            f"conduite reposait sur {subject} : {listing}. Tout a été retiré : "
            "il ne s'agit pas d'une conclusion écourtée mais d'une conclusion "
            "dont aucune affirmation n'avait de support dans l'état de "
            "l'analyse. Le lecteur ne doit rien en inférer."
        )
    return (
        "### Affirmation retirée\n\n"
        f"La conclusion conduite s'appuyait sur {subject} : {listing}. "
        f"{'Cette phrase a été retirée' if len(blocked) == 1 else 'Ces phrases ont été retirées'} "
        "plutôt que nuancée : sans résultat dans l'état, l'affirmation n'avait "
        "aucun support à nuancer."
    )


# --- LLM-conducted weaving (fail-loud) ---------------------------------------


async def weave_act3_conclusion(
    evidence: Act3Evidence, llm_callable: LlmCallable
) -> WeaveOutcome:
    """Conduct the Acte III conclusion via the LLM (fail-loud, #1108).

    The outcome carries the LLM-produced markdown, or the observed reason there
    is none — the call raised, or the LLM produced nothing (#2345); the caller
    records it with the explicit ``unavailable`` status. No template fallback —
    anti-pendule #1019/#369.
    """
    return await weave(build_act3_prompt(evidence), llm_callable, "Acte III")


def build_act3_retry_prompt(
    evidence: Act3Evidence,
    flagged: List[str],
    virtue_flagged: Optional[List[str]] = None,
    virtue_table: str = "",
    letter_flagged: Optional[List[str]] = None,
) -> str:
    """The bounded ONE writer retry (#3343) — the writer rewrites its own prose.

    Same shape as Act II's: the base prompt is the one the writer already
    received (same data blocks, same rules, same relabelling #3296), and the
    correction block only NAMES what the #3297 check found and what a
    superlative must carry to stand.

    Act III's licence is different — its measured ranking is the salience
    hierarchy, so a sentence naming a P1 unit legitimately rests on it
    (criterion 4 of the reader contract REQUIRES a ranking marker here, so
    « le plus » backed by P1 is licensed, never banned). The correction says
    that too: the point is to stand on the ranking, not to stop ranking.

    #3358 — a second motive rides the SAME bounded call: virtue
    misattribution. The two correction blocks concatenate (each names what
    its own check found), and the virtue block carries the per-unit table
    the base prompt never had — the data gap that let the writer localise
    the discourse's measured virtues on a passage the measure never read.
    One call for both motives, never two.

    Both blocks are appended to the ASSEMBLED text and the whole goes
    through the #3296 relabel seam in ONE pass — the table's ids reach the
    writer as the same per-act letters the rest of the prompt uses, with
    the legend carrying each referent (#3303: never an order to print an
    id; #3296: never a raw id in the writer's view). The correction speaks
    the legend's own vocabulary — designate a unit by what it says, or
    lift the claim to the discourse level — never « nomme-la ».
    """
    prompt = _assemble_act3_prompt(evidence)
    if flagged:
        quoted = "\n".join(f"- {sentence}" for sentence in flagged[:5])
        prompt += (
            f"\n\nCORRECTION DEMANDÉE — ta conclusion ci-dessus contient "
            f"{len(flagged)} phrase(s) qui portent un superlatif sur TOUT le "
            "rapport (« le plus… du dispositif », « … du discours », « … du run ») "
            "sans classement mesuré pour l'adosser. Le classement mesuré de cet "
            "acte est la hiérarchie de saillance fournie plus haut : seules les "
            "unités qu'elle classe en tête peuvent porter un « le plus ». Phrases "
            f"repérées :\n{quoted}\n\n"
            "Réécris la conclusion EN ENTIER — même structure, mêmes beats, mêmes "
            "données, même longueur. Pour chaque superlatif, choisis : soit il "
            "nomme l'unité que la hiérarchie classe en tête et son rang, soit il "
            "porte sur la population réellement évaluée et la nomme, soit il cite "
            "la base du classement. Sinon, ne l'écris pas : dis la même chose sans "
            "superlatif. Ne commente pas cette consigne et ne cite pas les phrases "
            "repérées : rends la conclusion complète, prête à lire.\n"
        )
    if virtue_flagged:
        virtue_quoted = "\n".join(f"- {sentence}" for sentence in virtue_flagged[:5])
        prompt += (
            f"\n\nCORRECTION DEMANDÉE — ta conclusion ci-dessus contient "
            f"{len(virtue_flagged)} phrase(s) qui localisent une vertu mesurée "
            "sur des passages. Une vertu mesurée ne peut être localisée que sur "
            "une unité qui l'obtient au niveau maximal du tableau ci-dessous. "
            f"Phrases repérées :\n{virtue_quoted}\n"
            "Tableau mesuré (vertus retenues : unités qui les tiennent au niveau "
            f"maximal) :\n{virtue_table}\n\n"
            "Réécris la conclusion EN ENTIER — même structure, mêmes beats, mêmes "
            "données, même longueur. Pour chaque phrase repérée, choisis : soit la "
            "vertu est localisée sur une unité du tableau qui la tient, désignée "
            "par ce qu'elle dit — comme le reste de ta prose ; la légende des "
            "désignations en donne le texte —, soit dis la même chose au niveau "
            "du discours, sans localiser la vertu mesurée : le conseil au "
            "lecteur reste. Ne commente pas cette consigne et ne cite pas les "
            "phrases repérées : rends la conclusion complète, prête à lire.\n"
        )
    if letter_flagged:
        # #3393 (item 7) — Act III's own #3367 block: the wording is Act II's,
        # the surface is the conclusion. The block never orders a designation
        # by id or letter (#3303/#3296) — it restates the designation rule the
        # legend already carries.
        letter_quoted = "\n".join(f"- {sentence}" for sentence in letter_flagged[:5])
        header = (
            "CORRECTION DEMANDÉE"
            if not (flagged or virtue_flagged)
            else "AUTRE CORRECTION DEMANDÉE"
        )
        prompt += (
            f"\n\n{header} — ta conclusion ci-dessus imprime {len(letter_flagged)} "
            "phrase(s) où une lettre de désignation (α, β, …) paraît dans la "
            "conclusion. Une lettre est un raccourci d'atelier : le lecteur n'a "
            "pas la légende des désignations et ne peut rien en résoudre. "
            f"Phrases repérées :\n{letter_quoted}\n\n"
            "Réécris la conclusion EN ENTIER — même structure, mêmes beats, "
            "mêmes données, même longueur. Pour chaque lettre imprimée, "
            "désigne l'unité par ce qu'elle dit — comme le reste de ta prose ; "
            "la légende des désignations en donne le texte —, ou dis la même "
            "chose au niveau du discours. N'imprime jamais la lettre seule ni "
            "un identifiant interne. Ne commente pas cette consigne et ne cite "
            "pas les phrases repérées : rends la conclusion complète, prête à "
            "lire.\n"
        )
    return label_writer_prompt(prompt, evidence.unit_texts)


async def weave_act3_conclusion_retry(
    evidence: Act3Evidence,
    llm_callable: LlmCallable,
    flagged: List[str],
    virtue_flagged: Optional[List[str]] = None,
    virtue_table: str = "",
    letter_flagged: Optional[List[str]] = None,
) -> WeaveOutcome:
    """The bounded ONE retry (#3343), under the same fail-loud contract."""
    return await weave(
        build_act3_retry_prompt(
            evidence,
            flagged,
            virtue_flagged=virtue_flagged,
            virtue_table=virtue_table,
            letter_flagged=letter_flagged,
        ),
        llm_callable,
        "Acte III (relance)",
    )


# --- orchestrator ------------------------------------------------------------


@dataclass(frozen=True)
class _DressedAct3:
    """One Act III draft after every deterministic pass + the #3297 read.

    The bounded retry (#3343) dresses a second draft EXACTLY like the first —
    comparing two texts is only honest when both went through the same passes,
    and the check must judge the text the reader would receive (post claim
    gate, pre bounds passage).
    """

    text: str
    bound_removal: BoundRemoval
    verdict_removed: int
    absent_scope_appended: bool
    blocked: List[Any]
    nothing_survived: bool
    superlative_note: str
    superlative_sentences: List[str]
    virtue_note: str
    virtue_sentences: List[str]
    # #3393 (item 7) — Act III joins Act II's #3367 read: a printed Greek
    # letter is a workshop handle the reader cannot resolve (#3317), and the
    # panel's conclusion printed « Pour γ, … » with no legend in sight.
    letter_sentences: List[str]


def _dress_act3_prose(
    narrative: str, state: Any, evidence: Act3Evidence
) -> _DressedAct3:
    """Launder one Act III draft: bounds, verdict, scope note, claim gate, #3297.

    Silent by design — the caller logs the retained draft, so a discarded
    first draft leaves no repair trace claiming work the reader never got.
    """
    # #3134/#3310 — a woven sentence that restates a numeric bound is
    # withdrawn before anything else touches the text: the reader's bounds are
    # the record's passage grafted below, where each number sits under its own
    # site label. The R1105b render fused three fallacy lines into one
    # "initial detection" carrying the descent's 500; which model paraphrases
    # the record cannot stay a bound the pipeline guarantees. Pipeline event:
    # logged, never a reader note (#2032).
    _bound_removal = remove_restated_bounds(narrative)
    narrative = _bound_removal.text

    # #3335 (#3182 shape) — the virtue verdict is the pipeline's sentence, not
    # the prose's. Three paid passes out of three paraphrased the sentence the
    # prompt handed over and dropped its measured base; the last added « de
    # vraies qualités », « surtout », « souvent ». An instruction with no
    # post-generation check is not a guarantee, so a woven restatement — the
    # paraphrase or the verbatim copy — is removed here, BEFORE the claim gate
    # (the gate's « aucune conclusion soutenable » branch is decided on the
    # writer's prose, never on a passage or a paraphrase the pipeline owns) and
    # inside the dress, so the retry's second draft is laundered exactly like
    # the first. The pipeline's passage itself is grafted by the caller, after
    # every gate that judges prose. Nothing happens on the absent branch: no
    # virtue reached the bar, so there is no reader sentence (the DoD's
    # control).
    _verdict_removed = 0
    _verdict_sentence = discourse_virtue_reader_sentence(evidence.quality_strengths)
    # #3358 — the passed-virtue keys serve two readers of this dress: the
    # verdict-restatement detector below and the virtue-attribution check
    # that closes the dress.
    _passed_keys = [s.virtue for s in _passed_strengths(evidence.quality_strengths)]
    if _verdict_sentence:
        _verdict_removal = remove_restated_bounds(
            narrative,
            detector=lambda body: restated_verdict_sentences(body, _passed_keys),
            number_free=lambda _sentence: None,
        )
        narrative = _verdict_removal.text
        _verdict_removed = _verdict_removal.removed
        if _verdict_removal.removed:
            # A beat whose whole prose WAS the verdict would otherwise keep a
            # heading over nothing. Only on this branch: an untouched
            # narrative keeps whatever structure the writer gave it.
            narrative = _drop_empty_headings(narrative)

    # #1605 — the conclusion must carry what the run failed to evaluate. The
    # scope paragraph is appended when the woven prose did not tie a
    # limitation to a lost axis. Deterministic on purpose: the guarantee
    # cannot depend on the LLM having complied with the prompt directive.
    absent_scope_appended = False
    if evidence.absent_dimensions and not _narrative_states_scope_limit(
        narrative, evidence.absent_dimensions
    ):
        narrative = (
            narrative.rstrip() + "\n\n" + _scope_note(evidence.absent_dimensions)
        )
        absent_scope_appended = True

    # #1605 — the blocking half. Runs BEFORE the §4 self-check so the gate
    # reads the text the reader will actually receive. The band's claim
    # ceiling is a prompt instruction; this is the enforcement.
    blocked: List[Any] = []
    nothing_survived = False
    if evidence.verdict is not None:
        narrative, blocked = _gate_unsupported_claims(
            narrative, evidence.verdict.nontrivial_axes
        )
        if blocked:
            survivor = narrative.rstrip()
            # When nothing survives, the note IS the whole deliverable and must
            # say so in the prose: the structured ``degraded`` dict below is
            # dropped by the state round-trip, so it cannot carry that fact.
            nothing_survived = not survivor
            narrative = (survivor + "\n\n" if survivor else "") + _blocked_claim_note(
                blocked, nothing_survived=nothing_survived
            )

    # #3297 — a whole-scope superlative needs a measured ranking to stand on,
    # and Act III's own ranking is the salience hierarchy. A sentence naming
    # a unit the assessment ranks first (P1, weight 1) rests on it; everything
    # else whole-scope is unbacked. The check runs POST claim-gate (a removed
    # claim cannot be flagged) and PRE bounds-passage (the record's numbers
    # are code, not the writer's claim) — same placement logic as Act II.
    # Criterion 4 of the reader contract REQUIRES a ranking marker in Act III,
    # so « le plus » backed by P1 is licensed, never banned (anti-pendulum).
    from .whole_scope_superlative_check import (
        whole_scope_superlative_note,
        whole_scope_superlative_sentences,
    )

    _p1_ids = (
        [
            cite
            for item in evidence.salience.ranked
            if item.weight == 1
            for cite in item.cites
            if re.fullmatch(r"arg_\d+", cite)
        ]
        if evidence.salience is not None
        else []
    )
    _superlative_note = whole_scope_superlative_note(
        narrative, licensed_ids=_p1_ids, act_label="Acte III"
    )
    _flagged = (
        whole_scope_superlative_sentences(narrative, licensed_ids=_p1_ids)
        if _superlative_note
        else []
    )

    # #3358 — a measured virtue is localised only on a unit the measure
    # scored at the top band. The « que faire » beat advises passages; when
    # it justifies the advice by the discourse's measured virtues (« car
    # c'est là que le discours est clair »), the passages must hold them —
    # the recorded pass credited them to two passages, one of which the
    # quality pass never read. Same placement logic as #3297: post
    # claim-gate (a removed claim cannot be flagged), pre grafts (the
    # verdict passage and bounds are the pipeline's, not prose). The
    # vocabulary is the #3335 mapping bounded by the passed set — injected
    # by the caller's plugin, never duplicated. The units the sentence
    # designates resolve by id (synthetic) or by CONTENT against the unit
    # texts the act was handed — the acceptance path production prose can
    # actually reach (measured: the stored acts carry 0 arg_N).
    from .virtue_attribution_check import (
        flatten_unit_scores,
        unbacked_localisation_sentences,
        virtue_localisation_note,
    )

    _unit_scores = flatten_unit_scores(
        getattr(state, "argument_quality_scores", {}) or {}
    )
    _virtue_flagged = unbacked_localisation_sentences(
        narrative,
        _VIRTUE_PROSE_RE,
        _passed_keys,
        _unit_scores,
        unit_texts=evidence.unit_texts,
    )
    # #3393 (item 7) — the writer's own Greek handles must leave the prose:
    # a printed letter is a designation the reader cannot resolve (#3317 —
    # fixed for Act II by #3367, this is the same read for the conclusion).
    # The sentences feed the bounded retry's correction; no deterministic
    # strip — the fix is the writer's rewrite, not a behind-the-reader edit
    # (#3317's own calibration).
    from .readability_gate import greek_label_sentences

    _letters = greek_label_sentences(narrative)
    return _DressedAct3(
        text=narrative,
        bound_removal=_bound_removal,
        verdict_removed=_verdict_removed,
        absent_scope_appended=absent_scope_appended,
        blocked=list(blocked),
        nothing_survived=nothing_survived,
        superlative_note=_superlative_note,
        superlative_sentences=_flagged,
        virtue_note=virtue_localisation_note(len(_virtue_flagged), "Acte III"),
        virtue_sentences=_virtue_flagged,
        letter_sentences=_letters,
    )


async def build_act3_conclusion(
    state: Any, llm_callable: Optional[LlmCallable] = None
) -> Act3Result:
    """Build the Acte III actionable conclusion for ``state``.

    Deterministic evidence is always built (including the gated verdict band and
    the G1–G4 statuses). The conclusion is LLM-conducted only when
    ``llm_callable`` is provided; otherwise the result is fail-loud
    (``status="unavailable"``, empty narrative) — the renderer reports the gap
    honestly, never a template (#1108).

    G1–G4 (#1008 §3.2) gate the *gated synthesis* beat: on any gate failure the
    LLM is still conducted for the *appreciations* and *que-faire* beats (those
    do not require a comparative verdict), but the synthesis beat carries the
    honest fallback wording. A §4 self-check (``ReadabilityGate``) is attached
    to every woven result so the verdict is auditable; it never fabricates a
    pass.
    """
    evidence = build_act3_evidence(state)

    gates = evidence.gates
    failed_gates = [g for g, ok in gates.items() if not ok]

    if not gates["G1_arguments_extracted"]:
        # No substrate at all — the whole conclusion is fail-loud.
        return Act3Result(
            narrative="",
            status="empty_state",
            degraded={
                "act3_conclusion": (
                    "Aucun argument extrait — l'Acte III n'a pas de substrat à "
                    "conclure (G1 échoué : identified_arguments vide)."
                )
            },
        )

    if llm_callable is None:
        return Act3Result(
            narrative="",
            status="unavailable",
            degraded={
                "act3_conclusion": (
                    "Conclusion non conduite — aucun LLM injecté pour l'Acte III "
                    "(fail-loud, #1108)."
                )
            },
        )

    # If a gate beyond G1 failed, flag it: the synthesis beat must carry the
    # honest fallback, but we still conduct the LLM for the other beats and
    # attach the gate status so nothing is silently weakened.
    gate_note = ""
    if failed_gates:
        gate_note = (
            f"Gates G1–G4 : {', '.join(failed_gates)} "
            f"{accord(len(failed_gates), 'non passé', 'non passés')}. La synthèse "
            "doit porter le wording de repli honnête (#1008 §3.3) — pas de "
            "verdict comparatif."
        )
        # Re-flag the verdict as ungated so the prompt's synthesis beat degrades.
        evidence.verdict = None

    outcome = await weave_act3_conclusion(evidence, llm_callable)
    if not outcome.narrative:
        return Act3Result(
            narrative="",
            status="unavailable",
            degraded={
                "act3_conclusion": (
                    f"Conclusion indisponible — {outcome.failure} "
                    "(fail-loud, #1108)."
                )
            },
        )
    _dressed = _dress_act3_prose(outcome.narrative, state, evidence)

    # #3343 — the bounded ONE retry (#3159's rule was not enough: nothing read
    # the act, so the writer could break it in silence). Asked ONCE, with its
    # own flagged sentences and the measured hierarchy; the check still only
    # records, and if the rewrite is not better the first draft is kept. The
    # gesture is measured here, not assumed: on the stored states Act III
    # fires 16 of 48 and its P1 licence suppresses none of them — the act
    # needs the retry at least as much as Act II does.
    # #3358 — the trigger now carries two motives: the whole-scope
    # superlative (#3297) and the unbacked virtue localisation. Still ONE
    # bounded call — the correction blocks concatenate — and the second
    # draft is kept only when the SUMMED cost drops: flags of BOTH checks
    # plus the readability designation leaks (#2980 ids + #3317 letters,
    # ``designation_leak_count``). A rewrite that fixes its own motive
    # while printing ids or letters — the very jargon the gate forbids —
    # leaves the reader worse off, and the comparison has to see it. Each
    # motive is recorded when its own check fired on the first draft, with
    # the retained draft's counts.
    _retry_motif = ""
    _virtue_retry_motif = ""
    _first_superlative = _dressed.superlative_sentences
    _first_virtue = _dressed.virtue_sentences
    # #3393 (item 7) — the letters ride the SAME bounded call as the two
    # existing motives: one call, three correction blocks, and the summed
    # cost comparison already sees a printed letter (a designation leak,
    # #2980/#3317) through ``designation_leak_count``.
    _first_letters = _dressed.letter_sentences
    if _dressed.superlative_note or _dressed.virtue_note or _first_letters:
        from .readability_gate import designation_leak_count
        from .virtue_attribution_check import (
            flatten_unit_scores,
            held_virtues_table,
            virtue_localisation_retry_motif,
        )
        from .whole_scope_superlative_check import superlative_retry_motif

        _retry_keys = [s.virtue for s in _passed_strengths(evidence.quality_strengths)]
        _retry_unit_scores = flatten_unit_scores(
            getattr(state, "argument_quality_scores", {}) or {}
        )
        _retry = await weave_act3_conclusion_retry(
            evidence,
            llm_callable,
            _first_superlative,
            virtue_flagged=_first_virtue,
            virtue_table=held_virtues_table(
                _retry_keys, _retry_unit_scores, display=VIRTUE_DISPLAY_FR
            ),
            letter_flagged=_first_letters,
        )
        if _retry.narrative:
            _second = _dress_act3_prose(_retry.narrative, state, evidence)
            _before_total = (
                len(_first_superlative)
                + len(_first_virtue)
                + len(_first_letters)
                + designation_leak_count(_dressed.text)
            )
            _after_total = (
                len(_second.superlative_sentences)
                + len(_second.virtue_sentences)
                + len(_second.letter_sentences)
                + designation_leak_count(_second.text)
            )
            if _after_total < _before_total:
                _dressed = _second
            if _first_superlative:
                _retry_motif = superlative_retry_motif(
                    "Acte III",
                    len(_first_superlative),
                    len(_dressed.superlative_sentences),
                )
            if _first_virtue:
                _virtue_retry_motif = virtue_localisation_retry_motif(
                    "Acte III", len(_first_virtue), len(_dressed.virtue_sentences)
                )
        else:
            if _first_superlative:
                _retry_motif = superlative_retry_motif(
                    "Acte III", len(_first_superlative), failure=_retry.failure
                )
            if _first_virtue:
                _virtue_retry_motif = virtue_localisation_retry_motif(
                    "Acte III", len(_first_virtue), failure=_retry.failure
                )
        logger.info(
            "Acte III bounded writer retry (#3343/#3358): %s | %s | lettres: %d | "
            "first draft: %s",
            _retry_motif or "(pas de superlatif)",
            _virtue_retry_motif or "(pas de vertu mal localisée)",
            len(_first_letters),
            "; ".join(
                s[:90]
                for s in (_first_superlative + _first_virtue + _first_letters)[:3]
            ),
        )

    narrative = _dressed.text
    # #3389 — the retained draft's « … » spans are compared with the document
    # while it is still in memory, on the WRITER'S prose: the absent-axis
    # paragraph and the record's bounds are grafted below, and their wording is
    # the pipeline's, not a citation claim (#3310's rule for the same seam). An
    # exact quote passes byte-identical; an altered quote or a translation
    # printed as the document's words loses its guillemets and reads as the
    # paraphrase it is.
    narrative, _quote_motif = sanitize_act_quotes(narrative, state, "Acte III")
    _bound_removal = _dressed.bound_removal
    if _bound_removal.removed or _bound_removal.withdrawn:
        logger.info(
            "act3 woven bound restatement: %d sentence(s) removed, %d bound(s) "
            "withdrawn in place (record passage carries the figures): %s",
            _bound_removal.removed,
            _bound_removal.withdrawn,
            bound_removal_motif(_bound_removal),
        )

    # #3335 — the verdict restatement removal happened inside the dress (both
    # drafts are laundered the same way); the retained draft's count is the
    # one the auditor reads.
    _verdict_sentence = discourse_virtue_reader_sentence(evidence.quality_strengths)
    _verdict_removed = _dressed.verdict_removed
    if _verdict_removed:
        logger.info(
            "act3 woven virtue-verdict restatement: %d sentence(s) removed "
            "(the pipeline's verdict carries the base)",
            _verdict_removed,
        )

    # #1605 — the conclusion must carry what the run failed to evaluate. The
    # ledger is recorded unconditionally (it is a fact about the run), and the
    # scope paragraph is appended when the woven prose did not tie a limitation
    # to a lost axis. Deterministic on purpose: the guarantee cannot depend on
    # the LLM having complied with the prompt directive.
    degraded: Dict[str, str] = {}
    # #3310 — the prose was CHANGED here, and an auditor must be able to find
    # it: act, motive, count, never the sentence (#3249). Filed under the
    # #2046 fabrication-note keys, so it is archived in the appendix and never
    # reaches the reader as a repair note.
    _bound_motif = bound_removal_motif(_bound_removal)
    if _bound_motif:
        degraded["act3_bound_restatement"] = _bound_motif
    # #3389 — a « … » span was not the document's words: label, counts, never
    # a span (#3249). Filed under the #2046 fabrication-note keys with the
    # other acts' seam, so it is archived in the appendix.
    if _quote_motif:
        degraded["act3_quote_fidelity"] = _quote_motif
    if _verdict_removed:
        degraded["act3_verdict_restatement"] = (
            f"{_verdict_removed} phrase(s) restatant le verdict de vertus "
            "retirée(s) du récit — le verdict du lecteur est celui du pipeline, "
            "avec sa base mesurée."
        )
    if evidence.absent_dimensions:
        labels = ", ".join(d.label for d in evidence.absent_dimensions)
        degraded["act3_absent_dimensions"] = (
            f"{accord(len(evidence.absent_dimensions), 'dimension non évaluée', 'dimensions non évaluées')} sur "
            f"ce corpus : {labels}."
        )
        if _dressed.absent_scope_appended:
            # #2032: this is a pipeline event, not reader information — every
            # key of ``degraded`` reaches the reader as a blockquote note, and
            # a repair note telling the reader the renderer repaired something
            # is machine voice. Logged (the trace surface), never rendered.
            logger.info(
                "act3 scope note appended deterministically: the conducted "
                "prose named no limitation for the lost axes %s",
                labels,
            )

    # #1605 — the blocking half, applied inside the dress so the §4 self-check
    # reads the text the reader will actually receive. The band's claim
    # ceiling is a prompt instruction; this is the enforcement. The motive is
    # rebuilt from the retained draft's own blocked set.
    if _dressed.blocked:
        degraded["act3_claim_blocked"] = (
            f"{accord(len(_dressed.blocked), 'affirmation retirée', 'affirmations retirées')}, "
            "sans support dans l'état : "
            + "; ".join(
                f"{b.label} — « {_truncate(b.sentence, 90)} »" for b in _dressed.blocked
            )
        )
        if _dressed.nothing_survived:
            degraded["act3_claim_blocked_all"] = (
                "Aucune phrase de la conclusion n'a survécu au gate : toutes "
                "reposaient sur des dimensions sans résultat dans l'état. "
                "Le livrable ne porte que l'avis de retrait."
            )

    # #3297 — the motive of the whole-scope superlative, on the retained
    # draft. The degraded motif is a code literal (``restitution_acts_degraded``
    # is a closed producer vocabulary as far as the sanitizer is concerned,
    # #3249); the excerpt goes to the trace.
    _superlative_note = _dressed.superlative_note
    if _superlative_note:
        logger.warning(
            "Acte III whole-scope superlative (retained draft): %s | %s",
            _superlative_note,
            "; ".join(s[:90] for s in _dressed.superlative_sentences[:3]),
        )
        degraded["act3_whole_scope_superlative"] = _superlative_note
    # #3343 — the retry rewrote (or tried to rewrite) the act: act, counts and
    # which draft was kept, never a sentence (#3249). Archived with the other
    # fabrication notes (#2046), never a reader note.
    if _retry_motif:
        degraded["act3_superlative_retry"] = _retry_motif
    # #3358 — the unbacked-localisation read of the retained draft (the
    # reader sees the sentence; the report says the localisation has no
    # measured unit at its back — the same contract as the whole-scope
    # superlative note). The note names exactly what was judged, so it can
    # only ever fire on a sentence the check READ: a unit the table
    # contradicts, or a designation nothing resolves. And the retry
    # motive, archived with the fabrication notes (#2046 twins).
    # Counts only, never a sentence (#3249); the excerpts go to the trace.
    if _dressed.virtue_note:
        logger.warning(
            "Acte III unbacked virtue localisation (retained draft): %s | %s",
            _dressed.virtue_note,
            "; ".join(s[:90] for s in _dressed.virtue_sentences[:3]),
        )
        degraded["act3_virtue_localisation_unbacked"] = _dressed.virtue_note
    if _virtue_retry_motif:
        degraded["act3_virtue_localisation_retry"] = _virtue_retry_motif

    # #3335 — the pipeline's verdict is grafted HERE, not where it was
    # computed: the claim gate above judges the WRITER's prose, and a passage
    # appended before it would make the narrative non-empty, silencing the
    # « aucune conclusion soutenable » branch that tells the reader every
    # conducted claim was withdrawn (measured: the gate went mute). The
    # sentence is code-written, carries its own measured base, and states no
    # claim about an absent axis, so no gate applies to it — it is rendered
    # after the ones that judge the prose.
    if _verdict_sentence:
        narrative = (
            narrative.rstrip() + "\n\n" + format_verdict_passage(_verdict_sentence)
        )

    # #3134 — the record's own bounds close the act, after the prose: the
    # numbers the reader receives come from the record, not from the model.
    # Grafted BEFORE the §4 self-check so the gate reads the text the reader
    # receives. Empty passage when nothing was recorded (the rule's absent
    # case forbids inventing a bound; the passage stays absent too).
    _bounds_passage = format_reader_bounds_passage(evidence.readings)
    if _bounds_passage:
        narrative = narrative.rstrip() + "\n\n" + _bounds_passage

    # §4 self-check (honest, never grades on a curve).
    gate = ReadabilityGate()
    verdict = gate.check_body(narrative)
    if verdict.band != "PASS":
        degraded["act3_conclusion_gate"] = (
            f"Autocontrôle de lisibilité = {verdict.band}: "
            + "; ".join(verdict.reasons[:3])
        )
    if gate_note:
        degraded["act3_conclusion_gates"] = gate_note
    if not evidence.quality_axis_available:
        degraded["act3_conclusion"] = (
            "Axe qualité non concluable ici (argument_quality_scores "
            "indisponible) — appréciations limitées aux faiblesses, fail-loud."
        )
    vm = evidence.virtuous_mode
    # Positive outcome — reported by ``is_virtuous``, never filed under
    # ``degraded`` (see the note in ``act1_framing_plugin``): #1608 turned
    # ``degraded`` into a verdict, so a virtue left here marked the act as
    # degraded and stripped it from ``capabilities_used``. The branch below
    # stays gated on NOT-virtuous, which is what the ``elif`` expressed.
    is_virtuous = vm is not None and vm.is_virtuous
    if not is_virtuous and not evidence.weak_points:
        # Defensive: no weak points AND not flagged virtuous (an empty-ish run
        # that still passed G1). Honest note — not a positive virtuous claim,
        # since no non-trivial axis qualified the text as virtuous.
        #
        # Key is ``act3_conclusion_thin``, NOT ``act3_conclusion`` (#1615): the
        # latter is already written above when the quality axis is unavailable,
        # and both conditions hold together on a thin run — measured through the
        # real builder, the generic motif here silently replaced the precise
        # "axe qualité non concluable" one, so the reader was told the wrong
        # reason for the degradation. Distinct keys, both motifs survive.
        degraded["act3_conclusion_thin"] = (
            "Aucun point faible localisé et aucun axe vertueux non-trivial — "
            "la conclusion titre sur les forces disponibles sans claim vertueux "
            "non dérivé (fail-loud)."
        )

    return Act3Result(
        narrative=narrative,
        status="woven",
        gate_verdict=verdict,
        degraded=degraded,
        is_virtuous=is_virtuous,
    )
