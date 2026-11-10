"""Acte II generator — dialectical narrative by argumentative movement.

Epic #1134 (Restitution) / Track R3 #1137. LLM-conducted, woven per spec §4.
Consumed by the R6 renderer to populate ``RestitutionActs.act2_narrative``.

Design (spec §1.2 + §4 + §7, dispatch coord R427):
  - Cut by argumentative **movement** (a cluster of arguments sharing a
    rhetorical fate — attacked by the same fallacy family, or the un-attacked
    "soutiens" that hold), **not** by analytical dimension.
  - Each movement beat weaves the argument + its virtues (quality, as
    *character*) + its dérapages (localized fallacies w/ descent + counter-args)
    + its formal tenue (PL/FOL/Dung cited as PROOF, never a standalone block).
  - Every framework citation gets a narrative anchor (passes the §4 gate — this
    module self-checks its own output with ``ReadabilityGate``).
  - **LLM-conducted**: the narrative VARIES by corpus (no template #1108/#405).
    Fail-loud when no LLM is injected — empty string + explicit status; the
    renderer reports the gap honestly (anti-pendule #1019/#369).

Privacy HARD: opaque IDs only (``arg_N``, fallacy families are taxonomy
constants). The prompt carries the OPAQUE_ID_DIRECTIVE (FB-34). Corpus-derived
fields (argument descriptions, fallacy justifications, counter-content) are
**truncated** before entering the prompt and the LLM is instructed to
**paraphrase the move, never echo verbatim text** — the final R6 scrub (spec
§6) is the downstream guard.

Testability: ``build_act2_evidence`` is deterministic (no LLM/JVM/API); the LLM
is an injectable async callable ``Callable[[str], Awaitable[str]]`` (FB-29/38
injectable-LLM pattern), so unit tests pass a stub and need no kernel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .figure_scales import (  # #3394 — a figure prints on its own scale
    _fr_number,
    penalised_sum_on_its_maximum,
    sum_on_its_maximum,
)
from .cited_units import (  # #2967: shared cited-unit budget + boundary cut
    CITED_UNIT_TEXT_CAP,
    cited_unit_ids,
    divergent_winner_texts,
    render_governance_lead,
    render_divergence_clause,
    truncate_at_boundary,
    truncate_head_and_tail,  # #3231 — the producer's final sentence survives the cap
)
from .unit_labels import (  # #3296 — per-act label table + legend
    LEGEND_REFERENT_CAP,
    RAW_UNIT_ID_RE,
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
    move_author_label_of,
    move_author_of,
)
from argumentation_analysis.utils.taxonomy_loader import (  # #3224
    fallacy_taxonomy_label,
)
from .dung_reader import (  # #1908: one shared meaning for act2 and act3
    ACCEPTED_MEANS,
    CREDULOUS_MEANS,
    EPISTEMIC_CAVEAT,
    REJECTED_MEANS,
    UNDECIDED_MEANS,
    UNAVAILABLE_STATUS,
    appendix_ref,
    appendix_refs_in,
    citable_appendix_refs,
    reader_consequence,
)
from .native_dung import (  # #1912: single shared decoder — see native_dung.py
    decode_accepted_members,
    decode_native_dung,
    grounded_labelling,
    native_semantics_label,
    rejected_from_framework,
    select_primary_native,
)
from .fr_accord import accord
from .formal_derivation import (
    ABSENT_CONFLICT_NOT_LOCALISED,
    read_tested_content,
)
from .speaker_record import (
    SPEAKER_NAMING_RULE,
    SpeakerRecord,
    build_speaker_record,
    format_speaker_line,
)
from .arena_record import (  # #3390 — the arena joins the speaker's record
    ArenaRecord,
    build_arena_record,
    format_arena_line,
    is_fiction_arena,
)
from .reading_record import (
    READING_BASIS_RULE,
    BoundRemoval,
    bound_removal_motif,
    remove_restated_bounds,
    ReadingRecord,
    build_reading_record,
    format_reading_block,
)
from .global_projection import GlobalFinding, project_global_findings
from .llm_weaving import LlmCallable, WeaveOutcome, weave
from .quote_fidelity import sanitize_act_quotes
from .specialist_roles import (
    ROLE_LABELS,
    ROLE_ORDER,
    RoleAssignment,
    classify_specialist_roles,
)
from .readability_gate import GateVerdict, ReadabilityGate
from argumentation_analysis.orchestration.fol_cause import (  # #3237: the cause rule too
    FORMAL_CAUSE_NAMING_RULE,
    cause_phrase,
)
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    select_for_budget,
)

from .text_sequence import MOVE_LABELS_FR, TextSequence, collect_text_sequence
from .virtuous_identification import VirtuousModeAssessment, detect_virtuous_mode
from argumentation_analysis.agents.core.governance.coalition_play import (
    coalition_note,  # #3386
)
from argumentation_analysis.agents.core.reading import first_reading_note  # #3395
from argumentation_analysis.agents.core.reading import cross_passage_note  # #3432
from argumentation_analysis.agents.core.reading import coverage_review_note  # #3492

logger = logging.getLogger(__name__)

# #2046 — the reader-facing lead for each finding kind. The bracket tag
# (``[pl]``…) is internal vocabulary the conducted LLM recited verbatim into
# prose (#2031's untreated brother channels); the readable name carries
# instead — translate, never delete the axis identity.
_KIND_READABLE = {
    "pl": "logique propositionnelle",
    "fol": "logique du premier ordre",
    "modal": "logique modale",
    "dung": "graphe de Dung (argumentation abstraite)",
    "convergence": "convergence inter-axes",
    "gate": "gate de synthèse",
}


def _first_stated_cause_kind(
    records: Any, verdict_reader: Callable[[Dict[str, Any]], Optional[bool]]
) -> str:
    """#3199 rework — the class of the first REFUTED record that stated one.

    One reader for the binding clause, in record order: the finding's units
    come from the recorded core, and the clause that names them must speak
    of the same conflict. Empty string when the run stated no cause — the
    clause then asserts nothing about the batch.

    KNOWN BOUND (#3199 review, named rather than silently carried): the units
    come from EVERY refuted record while this reads ONE class, so two refuted
    records of different classes would qualify the union with the first
    record's class. Not repaired here because the alternative — qualify only
    when all stated classes agree — would drop the qualifier exactly when the
    conflict is most mixed, and the unqualified clause charges the speaker
    again (the defect this issue repairs). Name the class, keep the honesty:
    the acts' own cause phrase (the #3107/#3122 readers) still names each
    record's class one by one.
    """
    if isinstance(records, list):
        for r in records:
            if not isinstance(r, dict) or verdict_reader(r) is not False:
                continue
            cause = r.get("consistency_cause")
            if isinstance(cause, dict) and cause.get("cause"):
                return str(cause["cause"])
    return ""


# Truncation caps for corpus-derived fields entering the prompt (privacy +
# prompt-budget discipline). The LLM is told to paraphrase, not echo.
_DESC_CAP = 220
_JUSTIFICATION_CAP = 200
# #3231 — the head keeps the reasoning, this cap bounds the FINAL sentence the
# cut re-appends: a detector states its hedge at the end of its justification,
# and the qualifier must survive the cap (same order of magnitude as the head).
_JUSTIFICATION_TAIL_CAP = 200
_COUNTER_CAP = 200
# SV (#1182): truncation + count caps for governance/debate evidence (privacy
# + prompt-budget discipline; the LLM paraphrases, never echoes).
_DEBATE_CAP = 220
_DEBATE_MAX_EXCHANGES = 6

# Fallacy families form the mouvement theme (taxonomy constants, not source
# content — safe to surface). The reserved theme for arguments no fallacy
# targets — the claims that hold.
_SOUTIENS_THEME = "soutiens"

# #2966 — « tient » est un VERDICT, il exige qu'un détecteur ait REGARDÉ.
# L'absence d'entrée de sophisme pour une unité ne dit rien tant qu'on ignore si
# l'unité était dans l'échantillon examiné. Deux thèmes réservés portent les deux
# façons dont ce verdict manque, et aucun n'est le mouvement des soutiens :
# l'unité hors de l'échantillon, et l'unité dont l'échantillon n'a pas été
# enregistré (état écrit avant le champ (#2966), rétro-compat honnête).
_NON_EXAMINE_THEME = "non examinés"
_ECHANTILLON_NON_ENREGISTRE = "échantillon non enregistré"

# Les thèmes qui ne sont pas des mouvements d'attaque : ils ferment le fil et
# n'entrent pas dans le tri alphabétique des familles.
_NON_ATTACK_THEMES = (
    _SOUTIENS_THEME,
    _NON_EXAMINE_THEME,
    _ECHANTILLON_NON_ENREGISTRE,
)

# Honest label for a fallacy the LLM named but that resolves to no taxonomy node
# (#1421-1). ``inconnu`` read as a bug; ``hors taxonomie`` says the truth — the
# LLM named a fallacy absent from our tree — without inventing a family.
_HORS_TAXONOMIE = "hors taxonomie"

# Lazy cache: lowercase fallacy name (``nom_vulgarisé`` / ``text_fr``) → ``Famille``
# from the taxonomy CSV. Used ONLY to reconcile LLM-named fallacies whose
# ``family`` arrived empty (defect #1421-1) — never to override an explicit one.
_TAXONOMY_NAME_TO_FAMILY: Optional[Dict[str, str]] = None


def _load_name_to_family() -> Dict[str, str]:
    """Lazy-load a name→family map from the taxonomy CSV (lightweight, no JVM).

    Maps every ``nom_vulgarisé`` and ``text_fr`` (lowercased) to its ``Famille``.
    Failure to load is non-fatal: the reconciler then falls back to
    ``hors taxonomie`` (honest absence), never a fabricated family (#1019).
    """
    global _TAXONOMY_NAME_TO_FAMILY
    if _TAXONOMY_NAME_TO_FAMILY is not None:
        return _TAXONOMY_NAME_TO_FAMILY
    mapping: Dict[str, str] = {}
    try:
        import csv

        csv_path = Path(__file__).resolve().parents[2] / "data" / "taxonomy_full.csv"
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    famille = (row.get("Famille") or "").strip()
                    if not famille:
                        continue
                    for key in ("nom_vulgarisé", "text_fr"):
                        name = (row.get(key) or "").strip().lower()
                        if name and name not in mapping:
                            mapping[name] = famille
    except Exception as exc:  # noqa: BLE001 — non-fatal, honest-absent fallback
        logger.debug("taxonomy name→family map unavailable: %s", exc)
    _TAXONOMY_NAME_TO_FAMILY = mapping
    return mapping


def _reconcile_family(fdata: Dict[str, Any]) -> str:
    """Resolve a fallacy's family, honest about gaps (#1421-1).

    Order: explicit non-empty ``family`` → name→taxonomy match on ``type`` →
    ``hors taxonomie``. Never invents a family; ``hors taxonomie`` labels the
    real gap (the LLM named a fallacy absent from our tree), unlike ``inconnu``
    which reads as a bug. Anti-pendulum #1019: the label is surfaced, not hidden.
    """
    fam = str(fdata.get("family", "") or "").strip()
    if fam and fam.lower() != "inconnu":
        return fam
    name = str(fdata.get("type", "") or "").strip().lower()
    if name:
        mapping = _load_name_to_family()
        # exact then substring: ``type`` may be « ad hominem circonstanciel »
        # while the CSV holds « ad hominem ».
        if name in mapping:
            return mapping[name]
        for csv_name, famille in mapping.items():
            if csv_name and (name in csv_name or csv_name in name):
                return famille
    return _HORS_TAXONOMIE


# --- evidence dataclasses ----------------------------------------------------


@dataclass
class FallacyEvidence:
    """One localized fallacy attacking an argument."""

    fallacy_id: str
    family: str
    type: str
    justification: str
    target_arg_id: str
    # #3180 — WHOSE move the fallacy is. ``speaker`` (the value an older
    # record implies, and the default) or ``reported``: the text reports or
    # denounces a move made by another party, named in
    # ``move_author_label``. A reported one is not one of the speaker's
    # dérapages — it belongs in the report's own line, never in a movement
    # built from the speaker's moves.
    move_author: str = "speaker"
    move_author_label: str = ""
    # #3224 — the detection's dotted address in the taxonomy, when the record
    # carries one: the printed label resolves it into the branch that names
    # the category. None keeps the two-level label, with no guess.
    taxonomy_path: Optional[str] = None
    # #3231 — the detector's own confidence in this detection, None when it
    # measured none (#3029: unmeasured is None, never a default value). The
    # Procédé line prints it and the consigne weighs it — a detection its
    # producer rates low, or calls tentative in its justification, is told as
    # a tentative reading, never as an established fault.
    confidence: Optional[float] = None


@dataclass
class CounterEvidence:
    """One counter-argument generated against an argument."""

    strategy: str
    target_arg_id: str
    snippet: str
    # G6 (#1180): validation verdict (ValidationResult shape) so the narrative
    # can cite counter-argument *validity*. None when the evaluator did not run.
    is_valid_attack: Optional[bool] = None
    counter_succeeds: Optional[bool] = None


# Total number of argumentative virtues the evaluator knows about. Used only
# to state instrument *coverage* ("2 of 9 were judgeable here"), never as the
# denominator of a grade (#1907).
_TOTAL_VIRTUES = 9

#: #3158 — the provenance tag every counter line carries (option (b), R1109).
#: It names the PROVENANCE, not a class: under (b) it rides on demands and
#: reframings too, and a label that said « affirmation factuelle » would tell
#: the writer something false about most of the lines it marks. The
#: attribution instruction lives once, in the consigne.
_UNSOURCED_CLAIM_TAG = "[objection d'un générateur — non vérifiée, non sourcée]"


@dataclass
class ArgEvidence:
    """Per-argument evidence woven into a movement beat."""

    arg_id: str
    description: str
    virtues: Dict[str, float] = field(default_factory=dict)
    quality_overall: Optional[float] = None
    quality_available: bool = False
    fallacies: List[FallacyEvidence] = field(default_factory=list)
    counter_args: List[CounterEvidence] = field(default_factory=list)
    dung_rejected: Optional[str] = None  # semantics label, if rejected
    # #2966 — l'unité était-elle dans l'échantillon soumis ? ``None`` = le run
    # n'a pas enregistré l'ensemble examiné (état d'avant le champ) : l'absence
    # de sophisme localisé n'est alors PAS un verdict, et rien ne peut être dit
    # « qui tient ». Séparer ce ``None`` du ``False`` est le point de l'issue :
    # « non examinée » et « ensemble inconnu » ne se racontent pas pareil.
    fallacy_examined: Optional[bool] = None
    quality_examined: Optional[bool] = None


@dataclass
class MovementEvidence:
    """A cluster of arguments sharing a rhetorical fate (the mouvement)."""

    movement_id: str
    theme: str  # family name (taxonomy constant) or "soutiens"
    arguments: List[ArgEvidence] = field(default_factory=list)


@dataclass
class FormalFinding:
    """A global formal-tenue anchor the LLM weaves as backing (verified-in-state)."""

    kind: str  # "pl" | "fol" | "dung"
    verdict: (
        str  # human-readable, e.g. "inconsistant (Tweety)", "rejet (Dung grounded)"
    )
    detail: str
    # #1914 (constat 1, Acte II) : the derivation material — a bounded
    # rendering of WHAT the axis actually tested, extracted from the record
    # formulas. None = the decided records carry no real formula (placeholder
    # counters) ; the weaving line then says so honestly instead of letting a
    # bare count read as a proof.
    tested: Optional[str] = None
    # #3146 : the source units a recorded core names. When the conflict site
    # is an unsplittable translation batch, the verdict binds to the batch's
    # units (and through them to their movements) — never to one unit the
    # state did not single out. Empty when no cause named units.
    units: List[str] = field(default_factory=list)
    # #3179 : WHICH absence ``tested is None`` stands for — an outage of the
    # record (placeholders / empty) or real formulas whose conflict does not
    # localise. The two were one ``None`` and one sentence that claimed the
    # content was absent while the state held it.
    tested_absence: Optional[str] = None
    # #3179 : how many real formulas the decided records carry — the count the
    # not-localised wording states instead of calling the content absent.
    tested_n_formulas: int = 0
    # #3199 rework — the stated class of the conflict, when the record named
    # one. The binding clause used to assert « le lot de traduction de ces
    # unités, pas une seule » whatever the cause: on an ``unattributed_side``
    # record only ONE flank carries units, so that sentence claimed a batch
    # that does not exist. The clause now reads this field.
    cause_kind: str = ""


@dataclass
class DungSolverTrace:
    """Concrete Dung computation trace (opaque IDs) for honest framing.

    Track D #1280 — the restitution used to say « Dung rejette X » ~15× while
    presenting the framework as an *external oracle*. In reality the attack
    graph is **built from the extracted arguments** (the pipeline's own attacks),
    so Dung only reorganises what the upstream extraction produced — it is not
    an independent corroboration. This trace surfaces the actual computation
    (graph size, accepted members, rejected args, a sample of the attack
    relations) so the narrative can frame it honestly: « le graphe construit à
    partir des arguments extraits donne… ». All IDs stay opaque (arg_N, never
    source text) — privacy HARD.
    """

    available: bool = False  # False when no verification_* framework was written
    semantics_label: str = ""  # e.g. "grounded", "preferred" — the primary one surfaced
    n_arguments: int = 0
    n_attacks: int = 0
    accepted_members: List[str] = field(
        default_factory=list
    )  # opaque arg_ids in the extension
    rejected_args: Dict[str, str] = field(
        default_factory=dict
    )  # arg_id -> semantics label
    sample_attacks: List[List[str]] = field(
        default_factory=list
    )  # up to N opaque [attacker, target] pairs
    # #1912: True when the primary native framework EXISTS but its extension
    # shape could not be decoded — no accepted/rejected verdict can be drawn.
    # Surfaced so the reader sees "non concluable", never "all rejected".
    non_concluable: bool = False
    # #3153: the arguments the primary frame's graph does NOT settle — a
    # mutual attack, or an argument attacked only by undecided ones. Neither
    # accepted nor rejected; the prose says the conflict is not settled.
    undecided_args: Dict[str, str] = field(
        default_factory=dict
    )  # arg_id -> semantics label
    # #3153: of those, the ones an accepted extension contains — « acceptés
    # par crédulité »: they survive in one coherent reading, without the
    # graph imposing that choice.
    credulously_accepted: Dict[str, str] = field(default_factory=dict)
    # #3014 body item 2: the population size the frame was built from BEFORE
    # its 40-node budget cap, as the entry records it — the reader names the
    # reduction ("40 retenus sur 94 identifiées") instead of re-deriving the
    # total from the state, which diverges when the frame came from a
    # fallback population the state's inventory does not hold. None on
    # pre-repair entries (the state bridge stays the fallback).
    population_total: Optional[int] = None


@dataclass
class GovernanceVerdict:
    """A governance decision (5 voting rules + 2 consensus protocols, plus
    social-choice functions — see governance_methods.py for the split),
    verified-in-state.

    SV (#1182): the spectacular pipeline runs a governance phase (the 7
    governance methods + social-choice functions like Copeland winner and
    consensus metrics) but it was invisible in the report — the same
    debranching G6 fixed for counter-argument validity. ``scores`` maps opaque
    option IDs → Copeland/influence score (privacy: opaque keys, never party names).

    Track E #1281 — ``extraction_method`` records whether an LLM assessment
    ran ("llm") or not ("heuristic"); ``None`` = not recorded. It does NOT say
    the assessment produced the verdict: since GE-4 #1462 the winner comes from
    the formal vote aggregation, and the LLM's ranking is at most a
    recommended method. Framing the verdict on this field made the narrative
    call a vote a model ranking (R1077 paid pass on ``doc_A``). The origin is
    ``winner_provenance`` (#2969), see ``governance_origin``.
    """

    method: str
    winner: str
    scores: Dict[str, float] = field(default_factory=dict)
    extraction_method: Optional[str] = None  # "llm" | "heuristic" | None
    # #2969: a divergent vote records every distinct winner — presenting one
    # "leading argument" when the methods disagreed (arg_16 vs arg_23 on
    # doc_A) erases the divergence the vote actually expressed.
    winners: List[str] = field(default_factory=list)
    # #2965 / R1078: the winner's ORIGIN — "vote_aggregate" (a formal vote),
    # "llm_resolution" (a model-recommended STRATEGY, not a ranked unit),
    # "conflict_resolution" (a mediation TYPE), or "unresolved"/None
    # (unrecorded). This is what the narrative frames on.
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
    # #3394 cycle 2 — the NAMES behind the counts: which deciding methods
    # chose each option. The cycle-0 band said « à l'unanimité des méthodes »
    # without naming one; the render now carries the names beside the count.
    methods_by_option: Dict[str, List[str]] = field(default_factory=dict)
    # #3394 (tranche R1145) — the two distributed-consensus protocols'
    # verdicts, named APART from the vote's support: they are not scrutins,
    # so they never enter ``support_by_option``/``n_methods_decided``; the
    # band names their count (« plus deux protocoles de consensus »).
    consensus_protocols: Dict[str, str] = field(default_factory=dict)
    # #3386 — the coalition play's block, rendered by the producer's own
    # function (``coalition_play.coalition_note``, the #3395 one-producer
    # pattern): a bloc that moved the outcome, and/or a pivot the #3385
    # engine found on the declared profile. Empty when the play changed
    # nothing — the deliberation passage is then byte-identical.
    coalition_note: str = ""


@dataclass
class DebateExchange:
    """One Walton-Krabbe adversarial-debate exchange (point vs rebuttal).

    SV (#1182): the debate phase produces key exchanges. NB (gap β G8): the
    schemes-engine (student ``ArgumentationEngine`` 10 schemes) was dropped in the
    #35 unification → exchanges can be sparse. We surface what exists honestly
    and never fabricate a rich debate (#1019). G8 is a separate follow-up.

    G8 (#1184) CLOSED: the 10-scheme engine is restored; each exchange now
    carries the Walton ``scheme`` it relies on + its ``critical_question`` when
    the deterministic classifier matched (None when no scheme fit — honest, not
    fabricated). The SV reader contract (point/rebuttal) is preserved.
    """

    point: str
    rebuttal: str
    scheme: Optional[str] = None
    critical_question: Optional[str] = None


@dataclass
class Act2Evidence:
    """Deterministic evidence bundle for the Acte II narrative."""

    movements: List[MovementEvidence] = field(default_factory=list)
    formal_findings: List[FormalFinding] = field(default_factory=list)
    quality_axis_available: bool = True
    # #3159 — the measured quality ranking and its base, computed by the
    # producer. R1107c's render promoted `arg_14` to « le mieux tenu de tout
    # le discours » while `arg_69` ranked above it, on 8 scored units of 90;
    # the writer derived a superlative the record contradicted.
    quality_ranking: str = ""
    # SV (#1182): governance voting verdict + adversarial-debate exchanges,
    # surfaced so the narrative can cite them. Empty/None when the phases did
    # not produce non-trivial output (honest absence, not fabricated).
    governance_verdict: Optional[GovernanceVerdict] = None
    # #2989 rework — the winner's referent travels on the governance line
    # (same rule as Acte III, #2965/#2980: the writer does not join an id to
    # its unit across a long prompt). Empty when no text is localizable —
    # the line keeps its id wording then (honest absence).
    governance_winner_text: str = ""
    # The DIVERGENT winners' texts, in ``winners`` order as
    # ``(winner_id, text)`` pairs — an id stays only for a winner with no
    # text.
    governance_divergent_texts: List[Tuple[str, str]] = field(default_factory=list)
    debate_exchanges: List[DebateExchange] = field(default_factory=list)
    args_total: int = 0
    # #3296 — the per-act label table's referent source: every identified
    # unit's capped text, keyed by opaque id. The legend binds each Greek
    # letter to its referent (the #2896/#2965 precedent, generalised to the
    # whole act); the ids themselves never reach the writer's prompt.
    unit_texts: Dict[str, str] = field(default_factory=dict)
    # #3180 — the SPEAKER's localised fallacies only. A detection whose
    # ``move_author`` is ``reported`` is carried in ``reported_fallacies`` and
    # never added here: the count is read as "what this discourse commits".
    fallacies_total: int = 0
    # #2966 — la couverture de la détection par argument, telle que le run l'a
    # enregistrée. ``fallacy_sample_recorded`` vient de l'état : ``False`` = la
    # couverture existe peut-être (k/N) mais pas l'ensemble des unités vues, et
    # le prompt le dit alors au lieu de laisser lire « tient ».
    fallacy_sample_recorded: bool = False
    fallacy_sample_size: int = 0
    quality_sample_size: int = 0
    # Note (a) (#1153): fallacies whose target_argument_id could not be
    # resolved to an identified argument. These cannot join a movement beat,
    # but they ARE counted (here) rather than silently dropped (#1019) — the
    # LLM/rapport surfaces them honestly as "non rattaché(s) à un argument
    # identifié". ``fallacies_total`` counts only the speaker's attributed ones.
    unattributed_fallacies: int = 0
    # #3180 — the fallacies the text REPORTS or denounces (a move by another
    # party), rather than commits. They form no movement and count in no
    # speaker tally; the prompt surfaces them with the party's label, and the
    # narrative says the speaker reports them. Empty when the run said nothing
    # about authorship — the attribution stays the speaker's, never invented.
    reported_fallacies: List[FallacyEvidence] = field(default_factory=list)
    # DERIVED virtuous flag (spec §5.1) — when the state characterises the text
    # as virtuous, the narrative leads with WHY THE ARGUMENTATION HOLDS (the
    # soutiens movement becomes the centrepiece; formal tenue is the proof).
    virtuous_mode: Optional[VirtuousModeAssessment] = None
    # Epic #1258 / Track 1 #1259 — when True, build_act2_prompt DROPS the
    # opaque-ID directive so the readable restitution names the real argument.
    deanonymized: bool = True
    # #1911 — the global synthesis channel: bounded structured findings
    # (cross-axis convergences + deep-synthesis value gates), each citing its
    # anchors. The narrative weighs them as confidence, never as inventory.
    global_findings: List[GlobalFinding] = field(default_factory=list)
    # #1914 (Acte II slice) — the evidential-role classification of specialist
    # results (decisif / corroborant / contradictoire / non-discriminant),
    # derived deterministically from lower-level state. The narrative's
    # citation hierarchy is carried by this structure, never asked of the LLM.
    role_assignments: List[RoleAssignment] = field(default_factory=list)
    # #2295 — the text-ordered sequence of argumentative moves (anchored
    # Walton-Krabbe moves read from the trace). None when the run carries
    # no anchored move (honest absence — the sequence is not fabricated).
    text_sequence: Optional[TextSequence] = None
    # #2848 — the source's character length, so the sequence block can say
    # « couvrant les positions a–b sur L caractères » (the truncation is said
    # where it is read, with the range it actually covers).
    source_length: int = 0
    # #3082 — le locuteur : l'enregistrement partagé (valeur + provenance)
    # que les Actes I et III lisent aussi. L'Acte II ne lisait AUCUN des deux
    # producteurs (ni la métadonnée, ni le stakeholder « speaker ») — il
    # portait sa règle de nommage sans la donnée sur laquelle elle tranche.
    speaker: SpeakerRecord = field(default_factory=SpeakerRecord)
    # #3390 — the arena, from the same single record Acts I and III read.
    arena: ArenaRecord = field(default_factory=ArenaRecord)
    # #2850 lot 6 — the run's recorded bounded readings (#1737 table), the
    # basis the "Acts silent" family never spoke: the trace named each
    # window since lot 4, the acts quoted none of them.
    readings: ReadingRecord = field(default_factory=ReadingRecord)
    # #3395 (acts slice) — the first reading's labelled block, rendered by its
    # ONE producer (``first_reading_note``): the text's defining moves with
    # their verbatim quotes, or the stated absence — the writer may neither
    # invent a centre nor read a failed read as a silence. Empty when the state
    # carries no record at all (bare doubles): the prompt then omits the
    # section instead of putting a producer's vocabulary where none ran.
    first_reading: str = ""
    # #3432 (ask 6b) — the cross-passage consistency block, rendered by its
    # ONE producer (``cross_passage_note``): the solver's verdict over the
    # thesis's own passages, with the two verbatim quotes and their
    # positions, or the named absence (#1941). Empty when the state carries
    # no record: the prompt omits the section.
    cross_passage: str = ""
    # #3492 — the coverage review's block, rendered by its ONE producer
    # (``coverage_review_note``): the supports or qualifiers of the thesis no
    # lens examined, each with its quote, its position and what its lens
    # answered — or the named absence of a lens for that class. EMPTY when the
    # review named nothing (every support was examined, or the pass never
    # reached the model): the prompt omits the section and stays byte-identical
    # to the pre-#3492 one (the issue's control).
    coverage_review: str = ""


@dataclass
class Act2Result:
    """Outcome of :func:`build_act2_narrative`.

    ``status`` is one of ``"woven"`` (LLM produced a narrative), ``"unavailable"``
    (no LLM injected or LLM failed — fail-loud, #1108), ``"empty_state"`` (no
    arguments to narrate). ``gate_verdict`` is the honest §4 self-check.
    """

    narrative: str
    status: str
    gate_verdict: Optional[GateVerdict] = None
    degraded: Dict[str, str] = field(default_factory=dict)
    # True when the narrative was conducted leading with why the argumentation
    # holds (spec §5) — the virtuous reading.
    is_virtuous: bool = False
    # #3123/R1105c — the reading-license check over the woven Act II text
    # (flags only; empty when nothing was woven). Act II receives the cause
    # phrases and can charge a recorded cause to the speaker just as the
    # synthesis did; the check covers the act, not only the synthesis.
    read_license: Dict[str, Any] = field(default_factory=dict)


# --- deterministic evidence builder (no LLM) ---------------------------------


def _truncate(text: Any, cap: int) -> str:
    """Coerce to str and cap length (privacy + prompt budget).

    #2967 Expected 4: a cut lands on a boundary — sentence first, word as
    fallback — never mid-word. The marker stays visible.
    """
    return truncate_at_boundary(text, cap)


# Cap on how many attack relations we surface in the trace / prompt. The full
# attack list can be long; a representative sample suffices to make the graph
# inspectable without blowing the prompt budget (privacy + budget discipline).
_TRACE_ATTACK_SAMPLE = 4

# #2295 — cap on rendered sequence moves (same budget discipline). The
# writer already caps at 12 entries; the renderer keeps the prompt lean.
_SEQUENCE_RENDER_CAP = 8


def _collect_dung_trace(state: Any) -> DungSolverTrace:
    """Collect the concrete Dung computation trace for honest framing (#1280).

    Reads ``state.dung_frameworks`` (written by ``state_writers`` as
    ``verification_{semantics}`` entries carrying ``arguments`` + ``attacks`` +
    ``extensions``). The attack graph is **built from the extracted arguments**,
    so this trace lets the restitution frame the result as « le graphe construit
    à partir des arguments extraits donne… » rather than as an external oracle.

    Picks the primary framework via the shared #1912 selector (preferred →
    grounded → first verification_*), decodes its extension with the shared
    decoder, and records graph size, accepted members, rejected args and a
    capped sample of attack pairs. #1912: a primary framework whose extension
    shape is undecodable yields ``non_concluable=True`` and NO verdict —
    never "accepted = ∅" (which would reject every argument). All IDs opaque
    (arg_N) — privacy HARD. Returns ``available=False`` when no verification
    framework was written (honest absence, not fabricated).
    """
    frameworks = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(frameworks, dict):
        return DungSolverTrace()
    primary = select_primary_native(frameworks)
    if primary is None:
        return DungSolverTrace()
    primary_sem = native_semantics_label(primary)

    fw_args = primary.get("arguments", []) or []
    fw_args = fw_args if isinstance(fw_args, list) else []
    fw_attacks = primary.get("attacks", []) or []
    fw_attacks = fw_attacks if isinstance(fw_attacks, list) else []
    # #3014 body item 2: the entry's own pre-cap population total, when the
    # producer recorded it (int-guarded — anything else keeps None and the
    # state bridge below).
    fw_total = primary.get("population_total")
    fw_total = fw_total if isinstance(fw_total, int) and fw_total >= 0 else None

    # Accepted extension members (opaque arg_ids) — None = shape unknown.
    decoded = decode_accepted_members(primary.get("extensions"))
    if decoded is None:
        sample_attacks = [
            [pair[0], pair[1]]
            for pair in fw_attacks
            if isinstance(pair, (list, tuple))
            and len(pair) >= 2
            and isinstance(pair[0], str)
            and isinstance(pair[1], str)
        ][:_TRACE_ATTACK_SAMPLE]
        return DungSolverTrace(
            available=True,
            semantics_label=primary_sem or "grounded",
            n_arguments=len(fw_args),
            n_attacks=len(fw_attacks),
            non_concluable=True,
            sample_attacks=sample_attacks,
            population_total=fw_total,
        )
    accepted: List[str] = sorted(decoded)

    # Rejected args from the SAME primary framework as the accepted members
    # (R868 rework): the trace announces one semantics label, so it must
    # carry that framework's verdict only — the pre-rework aggregate of ALL
    # verification_* measured rejected={arg_2: grounded} while preferred
    # accepted arg_2, a self-contradicting reader-facing trace with zero
    # sidecars. The multi-semantics union stays available as the distinct
    # aggregate output (Act III weak points, per-argument beats).
    rejected = rejected_from_framework(primary, decoded) or {}

    # #3153: the graph's OWN stand-off, from the same primary frame. The
    # labelling is a property of the attack graph, so it is well defined
    # whichever semantics the entry names; "out" is what ``rejected`` holds.
    _labelling = grounded_labelling(primary) or {}
    _sem = primary_sem or "grounded"
    undecided = {
        arg: _sem for arg, position in _labelling.items() if position == "undec"
    }
    credulous = {arg: lab for arg, lab in undecided.items() if arg in decoded}

    # #3325 — its own name: the early-return branch above binds
    # ``sample_attacks`` too, and re-binding it here is what the strict
    # check flagged. Same list, same order, same content at run time.
    sampled_attacks: List[List[str]] = []
    for pair in fw_attacks:
        if (
            isinstance(pair, (list, tuple))
            and len(pair) >= 2
            and isinstance(pair[0], str)
            and isinstance(pair[1], str)
        ):
            sampled_attacks.append([pair[0], pair[1]])
        if len(sampled_attacks) >= _TRACE_ATTACK_SAMPLE:
            break

    return DungSolverTrace(
        available=True,
        semantics_label=primary_sem or "grounded",
        n_arguments=len(fw_args),
        n_attacks=len(fw_attacks),
        accepted_members=accepted,
        rejected_args=rejected,
        undecided_args=undecided,
        credulously_accepted=credulous,
        sample_attacks=sampled_attacks,
        population_total=fw_total,
    )


def _dung_detail_with_citable_ref(
    semantics_label: str, citable: "set[str]", gloss: str
) -> str:
    """#3394 cycle 2 — the Dung finding's detail: the annex ref ONLY when the
    annex will print it; the result stated in place otherwise.

    The cycle-2 census measured renders citing ``Annexe Dung[...]`` anchors
    with no annex in the full text — same format, no target. The ref gates on
    ``citable_appendix_refs`` (the appendix's own derivation), so the two
    cannot drift; a ref that will not print never reaches the prompt, and the
    gloss plus the verdict above already state the result.
    """
    ref = appendix_ref(semantics_label)
    if ref and ref in citable:
        return (
            f"{ref} — composition exacte de "
            f"l'extension, identifiants et arêtes d'attaque ; {gloss}. "
            "Cite la conséquence ci-dessus, PAS la composition."
        )
    return (
        "conséquence énoncée ci-dessus — composition non jointe "
        f"(aucune annexe imprimée pour la sémantique {semantics_label}) ; "
        f"{gloss}. Cite la conséquence, jamais une composition absente."
    )


def _quality_axis_usable(quality: Any) -> bool:
    """§5 gate (#1153): is the quality axis *usable*, not merely present?

    The old gate ``bool(quality)`` stayed ``True`` for a non-empty dict whose
    entries were unusable (no overall, no per-virtue scores) — a silent bug that
    hid Finding A (#1151). This gate requires at least one scored entry to carry
    a usable ``overall`` OR a usable per-virtue map (under the canonical
    ``scores`` key or the legacy ``scores_par_vertu``).

    Calibrated, NOT over-strict (anti-pendule): a single usable entry suffices
    (we degrade the unusable ones per-entry, not the whole axis); we never
    require ALL virtues populated (some args are short/degraded with overall
    only). An empty/partial-but-empty axis returns ``False`` → the report
    fail-louds « non concluable » honestly.
    """
    if not isinstance(quality, dict) or not quality:
        return False
    for entry in quality.values():
        if not isinstance(entry, dict):
            continue
        ov = entry.get("overall")
        if isinstance(ov, (int, float)):
            return True
        spv = entry.get("scores")
        if not isinstance(spv, dict):
            spv = entry.get("scores_par_vertu")
        if isinstance(spv, dict) and spv:
            return True
    return False


def _tie_companions(ids: List[str]) -> str:
    """Name tied units the #3329 way: up to four names, then a count.

    Shared by every tie clause of ``quality_ranking_line`` (#3341 names the
    co-holders of the head; #3347 the co-holders of the winner's rank; #3356
    the holders of a tied head). One spelling, so the clauses cannot drift
    apart.
    """
    if len(ids) == 1:
        return ids[0]
    if len(ids) <= 4:
        return ", ".join(ids[:-1]) + " et " + ids[-1]
    # #3337 residual — at five co-holders the count is 1 and the noun
    # disagreed (« 1 autres »); count and noun agree.
    rest = len(ids) - 4
    return ", ".join(ids[:4]) + f" et {rest} autre{'s' if rest > 1 else ''}"


def quality_ranking_line(
    quality: Any, units_total: int, governance_winner: Optional[str] = None
) -> str:
    """The measured quality ranking, computed here so the writer copies it (#3159).

    R1107c's Act II called ``arg_14`` « le mieux tenu de tout le discours »
    while ``arg_69`` ranked above it and only 8 of 90 units were scored. The
    line carries the ranking AND its base, so a superlative over « the whole
    discourse » has nothing to stand on.

    #3337 — the measured-scope residual of the same conflation: paid pass
    R1131a crowned the vote winner « la mieux tenue du corpus mesuré » while
    the ranking handed to the writer puts another unit first (the winner 2nd,
    tied). The scope was licensed, the rank was never read. When the
    governance winner is NOT the measured top-1, the line now says the fact —
    the winner's rank, its score, the real leader — and what the vote does
    not say. When the winner IS the top-1 (or there is no vote, or the
    ``winner`` is a strategy the caller never passes), the line is
    byte-identical to what #3159 wrote.

    #3341 — "is the winner the top-1" is a question about SCORES, not about
    ids. Comparing the winner's id with ``scored[0][0]`` read the lexical
    order of the sort: with ``{arg_14: 5.0, arg_69: 5.0}`` the winner
    ``arg_14`` got the #3159 line while ``arg_69`` — the same fact — got
    « est 1ᵉ à égalité … ; arg_14 (5.0) est en tête », which is not an
    ordinal, calls an equal-score holder « en tête », and denies a crown the
    measurement does not deny. A shared maximum is one fact: the winner
    SHARES the head, said the #3329 way, and the co-holders are named.

    #3347 — both halves of the tie made visible. The listing cut at three
    fell inside the 4.0 tie of the recorded pass (arg_28 dropped, arg_22
    kept — an accident of alphabetical id order), and the off-top branch
    said « à égalité » without naming the co-holders, so Act II wrote
    « partage la deuxième place avec 1 co-détenteur sur 2 ». The cut now completes
    the boundary tie (bounded, counting its left-outs) and the off-top
    branch names its mates the same way the head branch does. No tie at
    the cut, untied off-top winners and sole top-1 winners keep the exact
    pre-#3347 line, byte for byte.

    #3356 — the last tie slot of the same branch: with a TIED head the
    closing clause read ``scored[0]``'s id and crowned one holder « en
    tête » — the alphabetical accident #3347 removed from the listing, one
    clause later. A shared head is named the one way the line names ties
    (#3341's helper); a sole top-1 keeps the exact pre-#3356 clause.
    """
    if not isinstance(quality, dict):
        return ""
    # #3394 — each collected score rides with the count of evaluated virtues
    # that is its own scale (#1942: ``overall`` is a SUM whose ceiling varies
    # by unit), and with its #289 penalty record when one applied. Nothing
    # prints bare anymore.
    #
    # #3394 follow-up (R1142), two rules on the same record:
    # - THE PENALTY IS SAID. 38 of 67 cycle-0 entries are
    #   ``original_score × (1 − penalty_factor)`` while the base clause
    #   called every figure a plain sum. A penalised entry now prints
    #   « 4,25 sur 6 après pénalité (6,00 avant) » — the reader sees which
    #   figure the penalty moved (same class as ask 5, render side).
    # - THE RANK COMPARES PARTS. The sort moved from the raw sum to the
    #   part of the ceiling each unit reaches (``overall / len(scores)``) —
    #   the reading ``add_quality_score``'s own contract documents. Measured
    #   on this seat's 10 cycle-0 state dumps, the two orders disagree on
    #   9/10 documents (table in the PR body): the sum order crowned
    #   whichever unit happened to have more evaluated virtues, not the
    #   better-held one. An entry with no ``scores`` map has no measurable
    #   part: it rides after the measured ones, by its sum (fixture-only
    #   shape — production pairs the two).
    scored: List[Tuple[str, float, int, bool, Optional[float]]] = []
    for arg_id, entry in quality.items():
        if not isinstance(entry, dict):
            continue
        overall = entry.get("overall")
        if isinstance(overall, (int, float)):
            scores = entry.get("scores")
            n_virtues = len(scores) if isinstance(scores, dict) and scores else 0
            penalty = entry.get("fallacy_penalty")
            penalised = False
            before: Optional[float] = None
            if isinstance(penalty, dict) and penalty.get("applied"):
                penalised = True
                raw_before = penalty.get("original_score")
                if isinstance(raw_before, (int, float)):
                    before = float(raw_before)
            scored.append((str(arg_id), float(overall), n_virtues, penalised, before))
    if not scored:
        return ""

    def _part(entry: Tuple[str, float, int, bool, Optional[float]]) -> Optional[float]:
        _a, overall, n, _p, _b = entry
        return overall / n if n else None

    def _tie_key(
        entry: Tuple[str, float, int, bool, Optional[float]],
    ) -> Tuple[int, float]:
        """What « same rank » means — the sort's key minus the id.

        Two entries tie when they reach the same PART of their ceiling.
        But ``None == None`` holds: two entries with no ``scores`` map
        (fixture-only shape — production pairs the two, #1942) would tie
        WHATEVER their sums, and a bare 4.0 would ride the co-holders of a
        bare 5.0 head. The key carries the group: bare entries tie on
        their sum, and never tie a measured one (different sort groups).
        """
        part = _part(entry)
        return (0, part) if part is not None else (1, entry[1])

    def _sort_key(
        entry: Tuple[str, float, int, bool, Optional[float]],
    ) -> Tuple[int, float, str]:
        return (_tie_key(entry)[0], -_tie_key(entry)[1], entry[0])

    scored.sort(key=_sort_key)

    def _scaled(
        arg_id: str,
        score: float,
        n_virtues: int,
        penalised: bool,
        before: Optional[float],
    ) -> str:
        if penalised:
            scaled = penalised_sum_on_its_maximum(score, before, n_virtues or None)
        else:
            scaled = sum_on_its_maximum(score, n_virtues or None)
        # An entry with no ``scores`` map has an unmeasurable ceiling: its id
        # rides the listing, its number does not (a bare sum is the #3394
        # defect; production pairs the two — ``add_quality_score``).
        return f"{arg_id} ({scaled})" if scaled else arg_id

    any_penalised = any(p for _a, _s, _n, p, _b in scored)
    penalty_clause = (
        " ; un score marqué « après pénalité » est cette somme après la "
        "pénalité de sophisme, la somme d'avant entre parenthèses"
        if any_penalised
        else ""
    )

    shown = scored[:3]
    overflow = ""
    if len(scored) > len(shown):
        # #3347 — the cut at three must never fall inside a tie. Keeping one
        # 4.0 and dropping another by alphabetical id order is an accident of
        # the sort, not a ranking: Act II then wrote « partage la deuxième
        # place avec [one of two co-holders] ». Every holder of the boundary
        # rank rides the listing (bounded: at most six shown), and beyond
        # that the left-outs are counted, never silently dropped. A cut
        # between two different ranks keeps the #3159 line, byte-identical.
        boundary_part = _part(shown[-1])
        tied_out = [e for e in scored[3:] if _tie_key(e) == _tie_key(shown[-1])]
        if tied_out:
            if len(tied_out) <= 3:
                shown = shown + tied_out
            else:
                # Plural by construction: this path starts at 4 left-outs
                # (fewer ride the listing above), so the count/noun
                # agreement the #3337 residual demands cannot break here.
                # #3394 — the group phrase carries the boundary rank on its
                # scale: the boundary sum when the left-outs share one
                # ceiling, the reached part otherwise (« 2,00 sur leur
                # maximum applicable » reads exactly under both). A bare
                # boundary (no ``scores`` map) prints no figure at all —
                # those sums ride nowhere, the group must not invent one.
                if boundary_part is None:
                    overflow = f" et {len(tied_out)} autres"
                else:
                    group_ns = {n for _a, _s, n, _p, _b in tied_out}
                    if len(group_ns) == 1 and 0 not in group_ns:
                        n_group = next(iter(group_ns))
                        group_value = _fr_number((boundary_part or 0.0) * n_group, 2)
                        group_scale = f" sur {n_group}"
                    else:
                        group_value = _fr_number(boundary_part or 0.0, 2)
                        group_scale = " sur leur maximum applicable"
                    group_pen = (
                        " après pénalité"
                        if all(p for _a, _s, _n, p, _b in tied_out)
                        else ""
                    )
                    overflow = (
                        f" et {len(tied_out)} autres à {group_value}"
                        f"{group_scale}{group_pen}"
                    )
    listed = (
        ", ".join(_scaled(arg_id, score, n, p, b) for arg_id, score, n, p, b in shown)
        + overflow
    )
    line = (
        f"Classement qualité (base : {len(scored)} unités évaluées sur "
        f"{units_total} ; chaque score est une somme de vertus, donnée sur "
        "le nombre de vertus évaluées de son unité ; le rang se lit sur la "
        "part du plafond atteinte, plus haut = meilleur"
        f"{penalty_clause}) : "
        f"{listed}. C'est le SEUL classement mesuré — aucun "
        "superlatif portant sur « tout le discours » n'a de base ici."
    )
    if not governance_winner:
        return line
    winner_entry = next(
        (e for e in scored if e[0] == governance_winner),
        None,
    )
    if winner_entry is None:
        # #3326 shape — the vote winner is a unit the quality pass never
        # scored: the vote ranks nothing in this measured set.
        return (
            f"{line} Le gagnant du vote, {governance_winner}, n'est pas dans "
            "ce classement mesuré : le vote ne dit pas qu'il est le mieux tenu."
        )
    winner_score, winner_n = winner_entry[1], winner_entry[2]
    top_score, top_n, top_pen, top_before = (
        scored[0][1],
        scored[0][2],
        scored[0][3],
        scored[0][4],
    )
    if _tie_key(winner_entry) == _tie_key(scored[0]):
        # #3341 — the winner is AT the maximum. Naming the other holders is
        # saying the crown is shared; the vote does not make it unique, and
        # the measurement does not deny it. Same ids order as the listing
        # above (`scored` is sorted by part then id).
        co_holders = sorted(
            arg_id
            for arg_id, _s, _n, _p, _b in scored
            if arg_id != governance_winner
            and _tie_key((arg_id, _s, _n, _p, _b)) == _tie_key(scored[0])
        )
        if not co_holders:
            # Sole top-1 — the #3159 line, byte-identical.
            return line
        winner_scale = (
            penalised_sum_on_its_maximum(
                winner_score, winner_entry[4], winner_n or None
            )
            if winner_entry[3]
            else sum_on_its_maximum(winner_score, winner_n or None)
        )
        winner_scale_str = f" ({winner_scale})" if winner_scale else ""
        return (
            f"{line} Le gagnant du vote, {governance_winner}, partage la tête "
            f"de ce classement{winner_scale_str} avec "
            f"{_tie_companions(co_holders)}."
        )
    # Rank of the winner's PART (first holder of it), and who shares it.
    winner_key = _tie_key(winner_entry)
    rank = 1 + next(i for i, e in enumerate(scored) if _tie_key(e) == winner_key)
    # #3347 — the off-top twin of the #3341 rule: saying « à égalité »
    # without naming the co-holders left the writer to fill the gap from the
    # only tie partner the truncated listing showed (1 of 2 on the recorded
    # pass). The mates are named the same way the head branch names its own.
    tie_mates = sorted(
        arg_id
        for arg_id, _s, _n, _p, _b in scored
        if arg_id != governance_winner
        and _tie_key((arg_id, _s, _n, _p, _b)) == winner_key
    )
    top_id = scored[0][0]
    # #3356 — the last tie slot of the line: « {top_id} est en tête » read the
    # sort's first holder as THE head. With a shared maximum it crowned one
    # holder by alphabetical accident — the same defect #3347 removed from the
    # listing, one clause later. A tied head is named the one way the line
    # already names ties (#3341's helper, its count/noun agreement inside); a
    # sole top-1 keeps the exact pre-#3356 clause, byte-identical. A head
    # group tied on PART with different ceilings prints no parenthetical —
    # each holder's own scale rides the listing above, and one member's
    # ceiling must not label another's.
    head_holders = sorted(
        arg_id
        for arg_id, _s, _n, _p, _b in scored
        if _tie_key((arg_id, _s, _n, _p, _b)) == _tie_key(scored[0])
    )
    head_ns = {n for a, _s, n, _p, _b in scored if a in head_holders}
    if len(head_holders) == 1:
        top_scale = (
            penalised_sum_on_its_maximum(top_score, top_before, top_n or None)
            if top_pen
            else sum_on_its_maximum(top_score, top_n or None)
        )
        top_scale_str = f" ({top_scale})" if top_scale else ""
        head_clause = f"{top_id}{top_scale_str} est en tête"
    else:
        if len(head_ns) == 1 and 0 not in head_ns:
            top_scale = (
                penalised_sum_on_its_maximum(top_score, top_before, top_n or None)
                if top_pen
                else sum_on_its_maximum(top_score, top_n or None)
            )
        else:
            top_scale = ""
        top_scale_str = f" ({top_scale})" if top_scale else ""
        head_clause = (
            f"{_tie_companions(head_holders)}{top_scale_str} " "partagent la tête"
        )
    winner_scale = (
        penalised_sum_on_its_maximum(winner_score, winner_entry[4], winner_n or None)
        if winner_entry[3]
        else sum_on_its_maximum(winner_score, winner_n or None)
    )
    winner_scale_str = f" ({winner_scale})" if winner_scale else ""
    return (
        f"{line} Le gagnant du vote, {governance_winner}, est {rank}ᵉ"
        f"{' à égalité' if tie_mates else ''} de ce classement"
        f"{winner_scale_str}"
        f"{' avec ' + _tie_companions(tie_mates) if tie_mates else ''}"
        f" ; {head_clause} : "
        "le vote ne dit pas qu'il est le mieux tenu."
    )


def _sampled_unit_ids(state: Any, phase: str) -> Optional[Set[str]]:
    """Les ids des unités qu'une phase a RÉELLEMENT soumises, ou ``None``.

    #2966 — ``record_analysis_coverage`` porte ``k``/``N`` depuis #2850/#2896 :
    combien d'unités ont été échantillonnées, jamais LESQUELLES. Sans les ids,
    aucun lecteur ne peut distinguer « examinée, propre » de « jamais
    examinée » (famille #1019), et Acte II rendait cette confusion comme un
    verdict — 84 unités « qui tiennent » alors que le détecteur en avait vu 10.

    ``None`` = le champ est absent : état écrit avant #2966, ou phase sans
    sélection. L'appelant doit alors dégrader vers « ensemble examiné non
    enregistré », jamais vers une tenue. Un ``set()`` (couverture enregistrée,
    zéro unité vue) est une information, pas une absence — les deux ne se
    confondent pas.
    """
    coverage = getattr(state, "analysis_coverage", None)
    if not isinstance(coverage, dict):
        return None
    entry = coverage.get(phase)
    if not isinstance(entry, dict):
        return None
    ids = entry.get("unit_ids")
    if not isinstance(ids, list):
        return None
    return {str(u) for u in ids}


def build_act2_evidence(state: Any) -> Act2Evidence:
    """Build the deterministic Acte II evidence bundle from a shared state.

    Groups ``identified_arguments`` into movements by the fallacy family that
    targets them (the family IS the movement theme); arguments no fallacy
    targets fall into the ``soutiens`` movement (the claims that hold). This
    realises the spec §1.2 *thèse → soutiens → dérapages* thread: each attacked
    movement is a dérapage, the un-attacked cluster is the soutien.

    No LLM, no JVM — pure state extraction. Privacy: corpus-derived fields are
    truncated; IDs stay opaque.
    """
    args = getattr(state, "identified_arguments", {}) or {}
    fallacies = getattr(state, "identified_fallacies", {}) or {}
    quality = getattr(state, "argument_quality_scores", {}) or {}
    counters = getattr(state, "counter_arguments", []) or []

    quality_axis_available = _quality_axis_usable(quality)
    # #3337 — the ranking line is computed below, after the governance verdict
    # is collected, so it can say the vote winner's rank when the winner is
    # not the measured top-1.
    if not isinstance(args, dict):
        args = {}
    if not isinstance(fallacies, dict):
        fallacies = {}
    if not isinstance(counters, list):
        counters = []

    # Index fallacies by target arg.
    fallacy_by_arg: Dict[str, List[FallacyEvidence]] = {}
    fallacies_total = 0
    unattributed_fallacies = 0  # Note (a) (#1153): traced, not dropped (#1019)
    # #3180 — a fallacy the text REPORTS (a move by another party) is not one
    # of the speaker's dérapages. It is indexed apart so it builds no movement
    # and enters no speaker tally; the prompt names it in its own block.
    reported_fallacies: List[FallacyEvidence] = []
    for _fid, fdata in fallacies.items():
        if not isinstance(fdata, dict):
            continue
        tid = fdata.get("target_argument_id") or ""
        if not tid:
            # Note (a): no resolved target — count it apart so the report can
            # surface it honestly instead of silently losing the detection.
            unattributed_fallacies += 1
            continue
        move_author = move_author_of(fdata)
        # Named "_ev" — a bare ``entry`` would collide (for mypy) with the
        # formal-findings loop below, whose variable carries another type.
        _ev = FallacyEvidence(
            fallacy_id=str(_fid),
            family=_reconcile_family(fdata),
            type=str(fdata.get("type", "inconnu")),
            justification=truncate_head_and_tail(
                fdata.get("justification", ""),
                _JUSTIFICATION_CAP,
                _JUSTIFICATION_TAIL_CAP,
            ),
            target_arg_id=str(tid),
            move_author=move_author,
            move_author_label=move_author_label_of(fdata),
            taxonomy_path=(
                str(fdata["taxonomy_path"])
                if isinstance(fdata.get("taxonomy_path"), str)
                and fdata["taxonomy_path"].strip()
                else None
            ),
            confidence=confidence_of(fdata),
        )
        if is_reported_move(_ev):
            reported_fallacies.append(_ev)
        else:
            # #3180 — only the speaker's own detections enter the tally.
            fallacies_total += 1
            fallacy_by_arg.setdefault(tid, []).append(_ev)

    # Index counters by target arg.
    counter_by_arg: Dict[str, List[CounterEvidence]] = {}
    for ca in counters:
        if not isinstance(ca, dict):
            continue
        tid = ca.get("target_arg_id") or ""
        if not tid:
            continue
        validation = ca.get("validation")
        is_valid_attack = None
        counter_succeeds = None
        if isinstance(validation, dict):
            iva = validation.get("is_valid_attack")
            if isinstance(iva, bool):
                is_valid_attack = iva
            cs = validation.get("counter_succeeds")
            if isinstance(cs, bool):
                counter_succeeds = cs
        counter_by_arg.setdefault(tid, []).append(
            CounterEvidence(
                strategy=str(ca.get("strategy", "")),
                target_arg_id=str(tid),
                snippet=_truncate(ca.get("counter_content", ""), _COUNTER_CAP),
                is_valid_attack=is_valid_attack,
                counter_succeeds=counter_succeeds,
            )
        )

    dung_rejected = decode_native_dung(state).rejected_by_arg

    # Assign each argument a movement key = primary fallacy family (sorted for
    # determinism) or, when no fallacy targets it, one of the two NON-VERDICT
    # themes (#2966). An argument may only be called a soutien that holds when
    # the fallacy detector actually EXAMINED it — the samples come from the
    # coverage the phases recorded, and ``None`` means the run did not record
    # which units it saw, so no unit can be called holding.
    fallacy_sample = _sampled_unit_ids(state, "fallacy_per_argument")
    quality_sample = _sampled_unit_ids(state, "quality")
    movement_key_by_arg: Dict[str, str] = {}
    for arg_id in args:
        flist = fallacy_by_arg.get(arg_id, [])
        if flist:
            families = sorted({f.family for f in flist if f.family})
            key = families[0] if families else _HORS_TAXONOMIE
        elif fallacy_sample is None:
            key = _ECHANTILLON_NON_ENREGISTRE
        elif str(arg_id) in fallacy_sample:
            key = _SOUTIENS_THEME
        else:
            key = _NON_EXAMINE_THEME
        movement_key_by_arg[arg_id] = key

    # Build movement evidence, ordering attack-movements first (alphabetical
    # theme) then the soutiens movement last — the claims that hold close the
    # thread.
    movements_by_key: Dict[str, MovementEvidence] = {}

    def _movement_for(key: str) -> MovementEvidence:
        if key not in movements_by_key:
            mid = (
                f"mvt_{_SOUTIENS_THEME}"
                if key == _SOUTIENS_THEME
                else f"mvt_{key}".replace(" ", "_")
            )
            movements_by_key[key] = MovementEvidence(movement_id=mid, theme=key)
        return movements_by_key[key]

    # #2967 — the budget is an ALLOCATION, not one global cap: a unit the
    # writer is asked to discuss (attack target, counter target, governance
    # winner) reaches it whole up to the cited budget; every other unit
    # keeps the short cap, so the prompt does not grow with N.
    cited = cited_unit_ids(state)
    for arg_id, desc in args.items():
        key = movement_key_by_arg[arg_id]
        mvt = _movement_for(key)
        qs = quality.get(arg_id) if isinstance(quality, dict) else None
        virtues: Dict[str, float] = {}
        q_overall: Optional[float] = None
        q_available = False
        if isinstance(qs, dict):
            q_available = True
            # Finding A (#1151/#1153): the writer add_quality_score stores
            # per-virtue scores under the canonical key ``scores``
            # (shared_state.py:536); read that first, then the legacy
            # ``scores_par_vertu`` key for any external source. Both shapes
            # carry the same {virtue: float} mapping.
            spv = qs.get("scores")
            if not isinstance(spv, dict):
                spv = qs.get("scores_par_vertu")
            if isinstance(spv, dict):
                for vname, vval in spv.items():
                    if isinstance(vval, (int, float)):
                        virtues[str(vname)] = float(vval)
            ov = qs.get("overall")
            if isinstance(ov, (int, float)):
                q_overall = float(ov)
        mvt.arguments.append(
            ArgEvidence(
                arg_id=str(arg_id),
                description=_truncate(
                    desc,
                    CITED_UNIT_TEXT_CAP if arg_id in cited else _DESC_CAP,
                ),
                virtues=virtues,
                quality_overall=q_overall,
                quality_available=q_available,
                fallacies=fallacy_by_arg.get(arg_id, []),
                counter_args=counter_by_arg.get(arg_id, []),
                dung_rejected=dung_rejected.get(str(arg_id)),
                fallacy_examined=(
                    None if fallacy_sample is None else str(arg_id) in fallacy_sample
                ),
                quality_examined=(
                    None if quality_sample is None else str(arg_id) in quality_sample
                ),
            )
        )

    attack_keys = sorted(k for k in movements_by_key if k not in _NON_ATTACK_THEMES)
    ordered: List[MovementEvidence] = [movements_by_key[k] for k in attack_keys]
    # Non-attack themes close the thread, in this order: the soutiens (the
    # claims that hold), then the units nothing was said about — never the
    # reverse, or a verdict would precede the coverage that qualifies it.
    for _trailing in _NON_ATTACK_THEMES:
        if _trailing in movements_by_key:
            ordered.append(movements_by_key[_trailing])

    formal_findings = _collect_formal_findings(state)
    virtuous_mode = detect_virtuous_mode(state)
    # SV (#1182): surface governance verdict + debate exchanges (debranched
    # capabilities — same fix shape as G6 for counter-arg validity).
    governance_verdict = _collect_governance(state)
    debate_exchanges = _collect_debate(state)

    # #2989 rework — resolve the winner's (and every divergent winner's)
    # text from the same unit map the movements read, so the governance
    # line names what each winner says instead of a raw id.
    governance_winner_text = ""
    if governance_verdict is not None and governance_verdict.winner in args:
        governance_winner_text = truncate_at_boundary(
            args[governance_verdict.winner], CITED_UNIT_TEXT_CAP
        )
    governance_divergent_texts = (
        divergent_winner_texts(governance_verdict.winners, args)
        if governance_verdict is not None
        else []
    )

    # #3337 — the ranking says the vote winner's rank when it is not the
    # measured top-1 (#3329: the fact on the line the writer copies). The
    # winner is passed ONLY when it names a unit (the same gate the cited
    # text uses) — a strategy "winner" is never ranked.
    vote_winner_for_ranking = (
        governance_verdict.winner
        if governance_verdict is not None and governance_verdict.winner in args
        else None
    )
    quality_ranking = quality_ranking_line(quality, len(args), vote_winner_for_ranking)

    return Act2Evidence(
        movements=ordered,
        formal_findings=formal_findings,
        quality_axis_available=quality_axis_available,
        quality_ranking=quality_ranking,
        args_total=len(args),
        unit_texts={
            str(arg_id): truncate_at_boundary(str(text), LEGEND_REFERENT_CAP)
            for arg_id, text in args.items()
        },
        fallacies_total=fallacies_total,
        fallacy_sample_recorded=fallacy_sample is not None,
        fallacy_sample_size=len(fallacy_sample) if fallacy_sample is not None else 0,
        quality_sample_size=len(quality_sample) if quality_sample is not None else 0,
        unattributed_fallacies=unattributed_fallacies,
        reported_fallacies=reported_fallacies,
        virtuous_mode=virtuous_mode,
        governance_verdict=governance_verdict,
        governance_winner_text=governance_winner_text,
        governance_divergent_texts=governance_divergent_texts,
        debate_exchanges=debate_exchanges,
        deanonymized=bool(getattr(state, "deanonymized", True)),
        global_findings=project_global_findings(state),
        role_assignments=classify_specialist_roles(state),
        text_sequence=collect_text_sequence(state),
        source_length=len(getattr(state, "raw_text", "") or ""),
        speaker=build_speaker_record(state),
        # #3390 — the arena record joins the speaker's: same single source
        # as Acts I and III (the #3073 gesture, completed), so a fiction
        # arena reaches Act II's writer instead of dying in the act that
        # named it.
        arena=build_arena_record(state),
        readings=build_reading_record(state),
        # #3395 (acts slice) — the one producer renders the block; the act
        # never re-words the moves in its own vocabulary.
        first_reading=first_reading_note(state),
        cross_passage=cross_passage_note(state),
        # #3492 — same single-producer rule: the act never re-words the review.
        coverage_review=coverage_review_note(state),
    )


def _collect_governance(state: Any) -> Optional[GovernanceVerdict]:
    """Collect the governance voting verdict (SV #1182, spec §1.2.4 social-choice).

    Reads ``state.governance_decisions`` (written by
    ``state_writers._write_governance_to_state``). Each entry carries the
    recommended voting ``method``, the ``winner`` (Copeland / recommended
    resolution), and per-option ``scores``. We surface the LAST decision (the
    terminal aggregation) — fail-loud: return ``None`` when the list is empty
    or carries no non-trivial winner/scores (no fabricated verdict, #1019).

    Privacy: option keys are kept as-is (opaque IDs from the pipeline). The
    writer already scrubs source names; we never echo raw option labels.
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
        raw_scores = d.get("scores", {}) or {}
        scores: Dict[str, float] = {}
        if isinstance(raw_scores, dict):
            for k, v in raw_scores.items():
                try:
                    scores[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        # Trivial / placeholder winners ("N/A", empty) carry no verdict.
        if not method or not winner or winner == "N/A":
            continue
        # `extraction_method` is carried for the record only: it says an LLM
        # assessment ran on the METHOD, not that it produced the verdict. The
        # prompt frames on the winner's origin, right below — never on this.
        em_raw = d.get("extraction_method")
        extraction_method = (
            str(em_raw).strip() if isinstance(em_raw, str) and em_raw.strip() else None
        )
        # #2965 / R1077 — the winner's origin (#2969): what the narrative
        # frames on, in place of the extraction_method proxy above.
        wp_raw = d.get("winner_provenance")
        winner_provenance = (
            str(wp_raw).strip() if isinstance(wp_raw, str) and wp_raw.strip() else None
        )
        mp_raw = d.get("method_provenance")
        method_provenance = (
            str(mp_raw).strip() if isinstance(mp_raw, str) and mp_raw.strip() else None
        )
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
        # the record carries none: pre-cycle-2 entries keep their count-only
        # band, byte-identical).
        raw_methods = d.get("methods_by_option", {}) or {}
        methods_by_option: Dict[str, List[str]] = {}
        if isinstance(raw_methods, dict):
            for k, names in raw_methods.items():
                if isinstance(names, list):
                    kept = [str(n) for n in names if isinstance(n, str) and n.strip()]
                    if kept:
                        methods_by_option[str(k)] = kept
        # #3394 (tranche R1145) — the protocols, named apart (honest absence
        # when the record carries none: pre-tranche entries keep their band
        # byte-identical, no protocol clause invented).
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
            extraction_method=extraction_method,
            winners=[
                str(w)
                for w in (d.get("winners") or [])
                if isinstance(w, str) and w.strip()
            ],
            winner_provenance=winner_provenance,
            method_provenance=method_provenance,
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


def _collect_debate(state: Any) -> List[DebateExchange]:
    """Collect adversarial-debate key exchanges (SV #1182, spec §1.2.4).

    Reads ``state.debate_transcripts`` (written by
    ``state_writers._write_debate_to_state``). Each transcript carries a list of
    ``exchanges`` (point + rebuttal). Gap β G8: the schemes-engine was dropped in
    #35 unification → exchanges can be sparse; we surface ONLY the real, non-empty
    ones and never invent exchanges (#1019). Capped to keep the prompt budget sane.
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
            # Fail-loud: skip empty exchanges (no point AND no rebuttal) — they
            # would read as fabricated debate matter (#1019).
            if not point and not rebuttal:
                continue
            # G8 (#1184): carry the scheme grounding (None when no scheme matched
            # — honest absence, not fabricated).
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


def _pl_verdict(result: Dict[str, Any]) -> Optional[bool]:
    """Resolve a PL analysis verdict from a stored result dict.

    Finding C (#1151/#1153): the canonical writer key is ``satisfiable``
    (shared_state.py:801); the legacy reader key is ``consistent``. Both map
    to the same satisfiability semantics here. Returns ``True``/``False`` for a
    settled verdict, or ``None`` when unverified (the entry carries neither key
    or an explicit None) — never collapses None to False (#1019).
    """
    sat = result.get("satisfiable")
    if sat is None:
        sat = result.get("consistent")
    return sat if isinstance(sat, bool) else None


def _collect_formal_findings(state: Any) -> List[FormalFinding]:
    """Collect verified-in-state formal verdicts as weaving anchors (spec §1.2.3).

    The LLM is told to bind each cited verdict to the movement it speaks about.
    We surface PL/FOL consistency + Dung rejection counts — never fabricate a
    verdict that is not in the state (DoD (c): cited formal verdicts are real).
    """
    findings: List[FormalFinding] = []

    pl = getattr(state, "propositional_analysis_results", None)
    if isinstance(pl, list):
        # Finding C (#1151/#1153): the writer add_propositional_analysis_result
        # stores the verdict under ``satisfiable`` (shared_state.py:801), NOT
        # ``consistent``. Read the canonical PL key first, then the legacy
        # ``consistent`` key (some external/older writers use it). Preserve the
        # strict ``is True``/``is False`` check — NEVER ``bool(sat)``: that
        # would conflate the unverified sentinel (None) with ``inconsistent``
        # (False), an #1019 silent-degradation.
        consistent = sum(
            1 for r in pl if isinstance(r, dict) and _pl_verdict(r) is True
        )
        inconsistent = sum(
            1 for r in pl if isinstance(r, dict) and _pl_verdict(r) is False
        )
        if consistent or inconsistent:
            # #3122 — the cause each UNSAT theory stated, in its own words,
            # the PL twin of the FOL block below. Empty when the run stated
            # none — never invented.
            pl_causes = [
                cause_phrase(r["consistency_cause"])
                for r in pl
                if isinstance(r, dict)
                and _pl_verdict(r) is False
                and isinstance(r.get("consistency_cause"), dict)
                and r["consistency_cause"].get("cause")
            ]
            # #3146 : one reader for content and units — the recorded core
            # decides both (the offline fallback names no units).
            # #3179 : the same reader says WHICH absence it hit, and how many
            # real formulas the records carry.
            pl_tested = read_tested_content(pl, _pl_verdict, refuted=bool(inconsistent))
            # #3199 rework — the binding clause speaks of the conflict the
            # record named, not of a translation batch by default.
            pl_cause_kind = _first_stated_cause_kind(pl, _pl_verdict)
            findings.append(
                FormalFinding(
                    kind="pl",
                    verdict=(
                        f"{accord(inconsistent, 'inférence PL inconsistante', 'inférences PL inconsistantes')} "
                        f"sur {accord(consistent + inconsistent, 'vérifiée', 'vérifiées')}"
                        if inconsistent
                        else f"{accord(consistent, 'inférence PL consistante', 'inférences PL consistantes')}"
                    ),
                    detail=(
                        "solveur Tweety (logique propositionnelle)"
                        + (" — " + " ; ".join(pl_causes) if pl_causes else "")
                    ),
                    # #1914 : the refuted records' formulas are the derivation
                    # (what failed) ; on an all-verified axis, a sample of what
                    # passed. Placeholder-only records → None → honest absence.
                    # #3146 : a recorded core also names its source units.
                    tested=pl_tested.text,
                    units=pl_tested.units,
                    tested_absence=pl_tested.absence,
                    tested_n_formulas=pl_tested.n_formulas,
                    cause_kind=pl_cause_kind,
                )
            )

    fol = getattr(state, "fol_analysis_results", None)
    if isinstance(fol, list):
        consistent = sum(
            1 for r in fol if isinstance(r, dict) and r.get("consistent") is True
        )
        inconsistent = sum(
            1 for r in fol if isinstance(r, dict) and r.get("consistent") is False
        )
        if consistent or inconsistent:
            # #3107 — the cause each inconsistent theory stated, in its own
            # words. Empty when the run stated none (an older artefact, or a
            # theory whose cause could not be established) — never invented.
            fol_causes = [
                cause_phrase(r["consistency_cause"])
                for r in fol
                if isinstance(r, dict)
                and r.get("consistent") is False
                and isinstance(r.get("consistency_cause"), dict)
                and r["consistency_cause"].get("cause")
            ]

            # #3146 : the FOL cause twin (#3107) carries the same core —
            # same single reader for content and units.
            # #3179 : and the same reader names the absence it hit.
            # #3199 rework — the tri-state reader is named once, so the
            # content reader and the cause reader cannot drift apart.
            def _fol_verdict(r: Any) -> Optional[bool]:
                v = r.get("consistent") if isinstance(r, dict) else None
                return v if isinstance(v, bool) else None

            fol_tested = read_tested_content(
                fol,
                _fol_verdict,
                refuted=bool(inconsistent),
            )
            findings.append(
                FormalFinding(
                    kind="fol",
                    verdict=(
                        f"{accord(inconsistent, 'théorie FOL inconsistante', 'théories FOL inconsistantes')} "
                        f"sur {accord(consistent + inconsistent, 'vérifiée', 'vérifiées')}"
                        if inconsistent
                        else f"{accord(consistent, 'théorie FOL consistante', 'théories FOL consistantes')}"
                    ),
                    detail=(
                        "solveur Tweety (logique du premier ordre)"
                        + (" — " + " ; ".join(fol_causes) if fol_causes else "")
                    ),
                    tested=fol_tested.text,
                    units=fol_tested.units,
                    tested_absence=fol_tested.absence,
                    tested_n_formulas=fol_tested.n_formulas,
                    cause_kind=_first_stated_cause_kind(fol, _fol_verdict),
                )
            )
        else:
            # Track B #1278: no decided FOL verdict — surface the honest
            # unavailability instead of silence. An entry with consistent=None
            # means the pipeline tried but could not decide. Two degraded
            # message conventions exist and BOTH must surface honest-absent:
            #   - "unavailable:<raison>" — caller-side gate (no translation /
            #     empty belief set, #1278).
            #   - "Degraded: ..." — solver-side degraded (parse-fail / reasoner
            #     unavailable, #1290 fol_handler fix). Without this branch a
            #     100%-parse-fail corpus would emit NO FOL finding at all — a
            #     silent omission (#1019) reintroduced by the very fix that
            #     stopped fabricating a False verdict.
            # The reader must see the axis is honestly absent, never a
            # "trivially consistent sur vide" fabrication (#1019).
            unavailable = [
                r
                for r in fol
                if isinstance(r, dict)
                and r.get("consistent") is None
                and isinstance(r.get("message"), str)
                and (
                    str(r.get("message")).startswith("unavailable:")
                    or str(r.get("message")).startswith("Degraded:")
                )
            ]
            if unavailable:
                findings.append(
                    FormalFinding(
                        kind="fol",
                        verdict=(
                            "FOL indisponible : aucune théorie du premier ordre "
                            "n'a pu être formalisée puis validée sur ce corpus"
                        ),
                        detail=(
                            "logique du premier ordre — la traduction NL→FOL n'a "
                            "produit aucune formule analysable (belief set vide ou "
                            "non parsable) ; axe honnêtement absent, non « consistant "
                            "sur vide » (#1278/#1019)"
                        ),
                    )
                )

    modal = getattr(state, "modal_analysis_results", None)
    if isinstance(modal, list):
        # Track C #1279: surface the modal verdict when decided, OR the honest
        # unavailability (no-translation / no-solver OOM) instead of silence —
        # mirroring the FOL block (#1278). ``valid`` is tri-state: True/False =
        # SPASS/SimpleMlReasoner decided; None = degraded.
        decided = [
            r for r in modal if isinstance(r, dict) and r.get("valid") in (True, False)
        ]
        if decided:
            sat = sum(1 for r in decided if r.get("valid") is True)
            unsat = sum(1 for r in decided if r.get("valid") is False)
            # #3146 : the modal leg has no cause writer — the shared reader
            # finds no core there and names no units, by construction.
            modal_tested = read_tested_content(
                modal,
                lambda r: (
                    r.get("valid") if isinstance(r.get("valid"), bool) else None
                ),
                refuted=bool(unsat),
            )
            findings.append(
                FormalFinding(
                    kind="modal",
                    verdict=(
                        f"{accord(unsat, 'théorie modale inconsistante', 'théories modales inconsistantes')} "
                        f"sur {accord(len(decided), 'vérifiée', 'vérifiées')}"
                        if unsat
                        else f"{accord(sat, 'théorie modale consistante', 'théories modales consistantes')}"
                    ),
                    detail="solveur modal (SPASS/Tweety)",
                    tested=modal_tested.text,
                    units=modal_tested.units,
                    tested_absence=modal_tested.absence,
                    tested_n_formulas=modal_tested.n_formulas,
                )
            )
        else:
            unavailable_modal = [
                r
                for r in modal
                if isinstance(r, dict)
                and r.get("valid") is None
                and isinstance(r.get("message"), str)
                and str(r.get("message")).startswith("unavailable:")
            ]
            if unavailable_modal:
                findings.append(
                    FormalFinding(
                        kind="modal",
                        verdict=(
                            "Modal indisponible : aucune théorie modale n'a pu "
                            "être formalisée puis validée sur ce corpus"
                        ),
                        detail=(
                            "logique modale — traduction NL→modal vide ou solveur "
                            "indisponible (OOM/absent) ; axe honnêtement absent, "
                            "non silencieusement dégradé (#1279/#1019)"
                        ),
                    )
                )

    dung_trace = _collect_dung_trace(state)
    # #3394 cycle 2 — the refs the appendix WILL print for this state: a
    # ref outside the set is an anchor with no target, and the finding
    # states its result in place instead of citing it.
    _citable = citable_appendix_refs(state)
    if dung_trace.available and dung_trace.non_concluable:
        # #1912: a native framework exists but its extension shape is
        # undecodable — say so. Never render "N rejected" from a shape the
        # decoder could not read (the accepted-empty fallacy).
        # #3050: when the label is the native ``unavailable`` STATUS (no
        # semantics was computed — compare mode's degraded entry), the prose
        # names the status in the reader's language and the appendix anchor
        # is DROPPED (appendix_ref returns ""): nothing was computed, so
        # there is no machinery to cite — never a phantom
        # ``Annexe Dung[unavailable]`` and never « sémantique unavailable ».
        _label = dung_trace.semantics_label
        if _label.strip().lower() == UNAVAILABLE_STATUS:
            _verdict = (
                "le graphe d'attaque construit sur les arguments extraits "
                "n'a pu être évalué : aucune sémantique n'a été calculée "
                "(cadre de Dung indisponible) — il ne fragilise ni ne "
                "valide aucun de ces mouvements"
            )
            _detail = (
                "machinerie non exécutée (solveur Dung indisponible) ; "
                f"{EPISTEMIC_CAVEAT} (#3050 : aucune sémantique calculée, "
                "aucune annexe à citer)"
            )
        else:
            _verdict = (
                f"le graphe d'attaque construit sur les arguments extraits "
                f"n'est pas concluable en sémantique "
                f"{_label} (forme d'extension non "
                "décodable) — aucun argument n'est fragilisé par ce "
                "verdict d'indécidabilité"
            )
            # #3394 cycle 2 — the protocol line cites the annex only when
            # the annex will print that ref; otherwise the verdict above
            # already states the result, and no dangling anchor rides it.
            _machinery = appendix_ref(_label)
            if _machinery and _machinery not in _citable:
                _machinery = (
                    "machinerie complète — protocole non joint "
                    f"(aucune annexe imprimée pour la sémantique {_label})"
                )
            else:
                _machinery = f"machinerie complète et protocole : {_machinery}"
            _detail = (
                f"{_machinery} ; "
                f"{EPISTEMIC_CAVEAT} (#1912 : ni accepté-vide ni inventé)"
            )
        findings.append(FormalFinding(kind="dung", verdict=_verdict, detail=_detail))
    elif dung_trace.available and dung_trace.rejected_args:
        # #1908: the prose COUNTS the rejections but never NAMES non-canonical
        # entries — the framework's ``arguments`` list can carry raw position
        # texts (measured on corpus B: English descriptions in the rejected
        # set), and the reader surface must never echo them. The appendix
        # carries the identifiers, canonicalised where possible.
        n_rej = len(dung_trace.rejected_args)
        # #1908 — the body carries the DIGESTED consequence (#1280 framing
        # kept: the graph reorganises the extracted arguments, it is not an
        # external oracle), the epistemic caveat at first mention, and the
        # appendix reference. No extension list, no serialized attack edges —
        # that machinery lives in the appendix now.
        # #2037: the Acte I inventory (identified_arguments) and the graph's
        # nodes are two populations — pass the total so the consequence can
        # NAME the reduction instead of reusing the inventory's syntagme
        # with the graph's number. #3014 body item 2: the ENTRY's own
        # pre-cap total wins when the producer recorded it — the state
        # bridge diverges exactly when the frame came from a fallback
        # population (extract output) the inventory does not hold, which is
        # when the cap bites silently.
        _inv = getattr(state, "identified_arguments", {}) or {}
        n_identified = (
            dung_trace.population_total
            if isinstance(dung_trace.population_total, int)
            and dung_trace.population_total > 0
            else (len(_inv) if isinstance(_inv, dict) else 0)
        )
        # #3153: the stand-off rides the SAME finding — a graph that settles
        # nothing against arg_4 but leaves three poles in conflict must say
        # both, never only the rejection (hiding the conflict is the pendulum
        # the issue forbids).
        _undec_id = len(dung_trace.undecided_args)
        verdict = (
            f"{reader_consequence(dung_trace.n_arguments, dung_trace.n_attacks, n_rej, dung_trace.semantics_label, n_identified=n_identified, n_undecided=_undec_id)}. "
            f"{EPISTEMIC_CAVEAT}."
        )
        _gloss = REJECTED_MEANS
        if _undec_id:
            _gloss = f"{_gloss}. {UNDECIDED_MEANS}"
            if dung_trace.credulously_accepted:
                _gloss = f"{_gloss}. {CREDULOUS_MEANS}"
        detail = _dung_detail_with_citable_ref(
            dung_trace.semantics_label, _citable, _gloss
        )
        findings.append(FormalFinding(kind="dung", verdict=verdict, detail=detail))
    elif dung_trace.available and (
        dung_trace.accepted_members or dung_trace.undecided_args
    ):
        # #1908: a decodable graph with zero rejections still deserves its
        # digested sentence — « every support survives » is a finding, not a
        # silence (the pre-fix code only spoke when something was rejected).
        # #2037: same inventory bridge as the rejection branch — entry total
        # first (#3014), state inventory as the pre-repair fallback.
        # #3153: an ALL-undecided frame (empty extension, self-attack) has no
        # accepted member and no rejection — it used to fall through with no
        # finding at all, silently erasing the stand-off.
        _inv = getattr(state, "identified_arguments", {}) or {}
        n_identified = (
            dung_trace.population_total
            if isinstance(dung_trace.population_total, int)
            and dung_trace.population_total > 0
            else (len(_inv) if isinstance(_inv, dict) else 0)
        )
        _undec_id = len(dung_trace.undecided_args)
        verdict = (
            f"{reader_consequence(dung_trace.n_arguments, dung_trace.n_attacks, 0, dung_trace.semantics_label, n_identified=n_identified, n_undecided=_undec_id)}. "
            f"{EPISTEMIC_CAVEAT}."
        )
        _gloss = ACCEPTED_MEANS if dung_trace.accepted_members else UNDECIDED_MEANS
        if _undec_id:
            _gloss = f"{_gloss}. {UNDECIDED_MEANS}"
            if dung_trace.credulously_accepted:
                _gloss = f"{_gloss}. {CREDULOUS_MEANS}"
        detail = _dung_detail_with_citable_ref(
            dung_trace.semantics_label, _citable, _gloss
        )
        findings.append(FormalFinding(kind="dung", verdict=verdict, detail=detail))

    return findings


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
    "- Ne reproduis JAMAIS de passage verbatim du texte source : paraphrase le\n"
    "  MOUVEMENT argumentatif en une phrase qui dit quelque chose.\n"
    "- Les familles de sophismes (ad hominem, ad verecundiam…) sont des\n"
    "  constantes de taxonomie : tu peux les nommer comme ancrage."
)

_WEAVING_RULE = (
    "RÈGLE DE TISSAGE (spec §4) — le contrat anti-énumération :\n"
    "- CHAQUE citation d'un cadre (Tweety, Dung, taxonomie, vertus) DOIT être\n"
    "  ancrée narrativement : liée à (a) un mouvement textuel localisé ET (b) le\n"
    "  verdict concret que ce cadre a produit.\n"
    "- INTERDIT : une ligne « nom + score isolé », ex. « ad verecundiam (0.8) ».\n"
    "  Ne produis JAMAIS de score entre parenthèses isolé comme (0.8) ou\n"
    "  « score 0.8 ». Les vertus sont le CARACTÈRE de l'argument, pas un tableau\n"
    "  de scores.\n"
    "- INTERDIT : numéroter en « Sophisme 1: » / « Argument 2: ». Donne aux\n"
    "  mouvements des titres THÉMATIQUES (ex. « Le mouvement ad hominem »,\n"
    "  « Les soutiens qui tiennent »).\n"
    "- Le verdict formel appuie un battement narratif ; ce n'est jamais une\n"
    "  sous-section isolée."
)


def _quality_scope_note(a: ArgEvidence, evidence: Act2Evidence) -> str:
    """Le motif d'absence de score, DIT à sa portée (#2966, Expected 3).

    « indisponible sur ce run » était imprimé pour toute unité sans score — y
    compris les 86 unités simplement hors de l'échantillon des 8 évaluées : la
    ligne imputait au run l'absence d'une unité. Quatre portées distinctes,
    jamais confondues, et la formulation de run reste RÉSERVÉE au cas où le run
    n'a réellement produit aucun score utilisable.
    """
    if not evidence.quality_axis_available:
        return "non concluable ici (argument_quality_scores indisponible sur ce run)."
    if a.quality_examined is False:
        scored = accord(
            evidence.quality_sample_size, "unité évaluée", "unités évaluées"
        )
        return f"non scorée ici (unité hors des {scored} sur ce run)."
    if a.quality_examined is None:
        return (
            "non concluable ici (l'ensemble des unités évaluées n'a pas été "
            "enregistré sur ce run)."
        )
    return "non scorée ici (unité soumise à l'évaluation, aucun score rendu)."


def build_act2_prompt(evidence: Act2Evidence) -> str:
    """Build the §4-compliant LLM-conducted prompt for the Acte II narrative.

    The prompt varies with the evidence (hence with the corpus) — it is not a
    static template (#1108/#405). It instructs the LLM to weave each movement
    and to cite only the verified formal verdicts provided.
    """
    # --- Mode vertueux (spec §5) — le récit mène avec pourquoi ça tient ---
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if is_virtuous:
        virtuous_section = (
            "MODE VIRTUEUX (spec §5) — LE RÉCIT MÈNE AVEC POURQUOI ÇA TIENT :\n"
            "Ce texte est caractérisé comme vertueux (zéro sophisme localisé +\n"
            "vertus mesurées). Le mouvement des soutiens est le CENTRE du récit,\n"
            "pas un résidu. Tisse d'abord ce qui tient : le caractère (vertus),\n"
            "la cohérence, et — si le solveur a validé des inférences — la tenue\n"
            "formelle comme PREUVE que l'argumentation ne dérape pas. Peu (aucun)\n"
            "contre-argument ne mord : c'est le résultat honnête, ne le présente\n"
            "pas comme un manque. Ne fabrique JAMAIS de dérapage pour équilibrer.\n"
            f"Dérivation du flag : {vm.reasoning if vm is not None else ''}\n\n"
        )
    else:
        virtuous_section = ""

    # --- movement data blocks (truncated, opaque) ---
    blocks: List[str] = []
    unexamined_total = 0
    for mvt in evidence.movements:
        is_soutiens = mvt.theme == _SOUTIENS_THEME
        if is_soutiens:
            # #2966 — vrai seulement depuis que ce mouvement ne contient que
            # des unités EXAMINÉES : la phrase était fausse pour les 84 unités
            # que le détecteur n'avait jamais vues.
            header = (
                f"MOUVEMENT « {mvt.theme} » — les soutiens qui tiennent "
                "(sophismes cherchés sur chacune, aucun localisé)"
            )
        elif mvt.theme == _NON_EXAMINE_THEME:
            unexamined_total += len(mvt.arguments)
            header = (
                f"MOUVEMENT « {mvt.theme} » — unités JAMAIS soumises à la "
                "détection de sophismes : aucun verdict n'a été rendu sur "
                "elles, ni « tient » ni « dérape »"
            )
        elif mvt.theme == _ECHANTILLON_NON_ENREGISTRE:
            unexamined_total += len(mvt.arguments)
            header = (
                f"MOUVEMENT « {mvt.theme} » — l'ensemble des unités examinées "
                "n'a pas été enregistré sur ce run : aucune de ces unités ne "
                "peut être dite « qui tient »"
            )
        else:
            header = (
                f"MOUVEMENT « {mvt.theme} » — "
                f"les arguments attaqués par la famille « {mvt.theme} »"
            )
        lines: List[str] = [header]
        for a in mvt.arguments:
            lines.append(f"  • {a.arg_id} : {a.description}")
            if a.quality_available:
                # #1907 — no grade in the reader narrative. ``a.virtues`` now
                # holds ONLY the dimensions that were actually evaluable on this
                # unit; the ones an isolated extract cannot carry (bibliography,
                # rebuttal, essay-level coverage) are absent rather than scored
                # zero. Reporting "x/10" over a fixed denominator turned that
                # instrument-reach artifact into a verdict on the speaker.
                evaluated = sorted(a.virtues.keys())
                tiennent = [k for k in evaluated if a.virtues[k] >= 0.75]
                faiblissent = [k for k in evaluated if a.virtues[k] <= 0.25]
                # #3165: no « Profil de vertus (caractère) » line — since
                # #1907 ``a.virtues`` holds the EVALUABLE dimensions, and that
                # list under a "what the unit is" label was identical on 7 of
                # 8 scored units (the instrument's reach, not the unit's
                # character). The observation line below carries the evaluated
                # set together with what holds and what fails.
                if evaluated:
                    n_eval = len(evaluated)
                    observation = (
                        f"      {accord(n_eval, 'dimension', 'dimensions')} sur "
                        f"{_TOTAL_VIRTUES} "
                        f"{'était jugeable' if n_eval == 1 else 'étaient jugeables'} "
                        f"sur cet extrait"
                    )
                    if tiennent:
                        observation += f" — tiennent : {', '.join(tiennent)}"
                    if faiblissent:
                        observation += f" ; ne tiennent pas : {', '.join(faiblissent)}"
                    observation += (
                        ". Les autres ne sont pas évaluables sur une unité de "
                        "cette taille et ne sont donc pas comptées contre "
                        "l'argument."
                    )
                    lines.append(observation)
            else:
                lines.append(f"      Axe qualité : {_quality_scope_note(a, evidence)}")
            for fl in a.fallacies:
                # #2031: the dotted taxonomy address never enters the evidence
                # — the reader gets the NAMES (type, root, branch since #3224);
                # an internal address fed to the conducted LLM leaks into prose.
                # #1914 (constat 4): the lead does not pre-judge — a joke, a
                # slogan and a dehumanizing metaphor all exited this mold
                # under the same attack word. The justification carries the
                # device's discursive function; the consigne asks the
                # conductor to name that function BEFORE judging fault.
                lines.append(
                    f"      Procédé : "
                    f"{fallacy_taxonomy_label(fl.type, fl.family, fl.taxonomy_path, quoted=True)} "
                    f"— {detector_confidence_note(fl.confidence)}. "
                    f"Justification : {fl.justification}"
                )
            for ca in a.counter_args:
                # #1668/#3328 leg 2: strategy is free text; only a KNOWN enum
                # value prints (its French name), anything else renders as an
                # absence — never (), never free English on this French
                # surface (« Burden of rebuttal », 89 of 3739 measured labels).
                _strat = strategy_label_fr(ca.strategy or "")
                _slot = f" ({_strat})" if _strat else ""
                # #3158 — EVERY counter line carries its provenance, not only
                # the ones a vocabulary calls "factual". A counter is an
                # objection a generator produced: nothing verified it, the
                # state records no source for it, whatever its wording. The
                # predicate (``asserts_fact``) was measured on doc_B and could
                # not separate « asserts a fact » from « demands evidence » —
                # 14 of 19 tags on methodological demands, 5 plain empirical
                # claims left untagged — so it no longer decides what the
                # writer is told. It lives on for the render check only
                # (:func:`check_reading_license`, flag ``counter_claim_in_own_voice``),
                # where a restatement of a reframing still earns no flag.
                _provenance = f" {_UNSOURCED_CLAIM_TAG}"
                lines.append(
                    f"      Contre-argument{_slot}{_provenance} : {ca.snippet}"
                )
            if a.dung_rejected:
                # Track D #1280 — frame honestly: the Dung graph is built from
                # the extracted arguments, so the verdict is a reorganisation of
                # upstream extraction, not an external corroboration.
                lines.append(
                    f"      Tenue formelle : le graphe de Dung bâti sur les "
                    f"arguments extraits ne retient pas {a.arg_id} dans "
                    f"l'extension acceptée (sémantique {a.dung_rejected})."
                )
        blocks.append("\n".join(lines))

    # --- #1621: detections the movement enumeration structurally cannot carry ---
    # Note (a) (#1153) added ``unattributed_fallacies`` so these would be
    # "surfaced honestly rather than silently dropped (#1019)" — and then nothing
    # read it. The promise lived only in the comment that made it.
    #
    # Why the enumeration above cannot stand in for this line: in
    # ``build_act2_evidence`` the ``continue`` fires BEFORE the insertion into
    # ``fallacy_by_arg``, so a fallacy with no resolvable target joins no
    # movement; and ``fallacies_total`` increments AFTER it, so it is absent from
    # the count too. Neither enumerated nor counted nor flagged — the exact
    # definition of the silent drop the field was created to prevent. Contrast
    # ``fallacies_total``, which IS recoverable here (the movement enumeration is
    # uncapped) and is therefore deliberately left unwired: transport where the
    # information already flows is #1019 read backwards.
    unattributed_block = ""
    if evidence.unattributed_fallacies:
        n_unattr = evidence.unattributed_fallacies
        il_fig = "Il ne figure" if n_unattr == 1 else "Ils ne figurent"
        est_compte = "n'est pas compté" if n_unattr == 1 else "ne sont pas comptés"
        unattributed_block = (
            f"DÉTECTIONS NON RATTACHÉES : "
            f"{accord(n_unattr, 'sophisme détecté', 'sophismes détectés')} "
            f"sans argument cible résolvable. {il_fig} "
            f"dans AUCUN mouvement ci-dessus et {est_compte} "
            f"dans les dérapages localisés. Si tu les évoques, dis-le "
            f"honnêtement — sans argument cible identifié — et "
            f"ne leur invente NI cible NI mouvement d'accueil.\n\n"
        )

    # --- #3180: the moves the text REPORTS, not the ones the speaker commits ---
    # A text that denounces a sophism commits no sophism by denouncing it. The
    # detection is real and worth surfacing, but attributing it to the speaker
    # turns a denunciation into a self-incrimination. These entries never reach
    # ``fallacy_by_arg`` (they build no movement) and never enter
    # ``fallacies_total``; they are named here with the party the text names.
    # Entries whose record carried no ``move_author`` keep the speaker
    # attribution and never land here — no party is invented.
    reported_block = ""
    if evidence.reported_fallacies:
        n_rep = len(evidence.reported_fallacies)
        rep_lines: List[str] = []
        # Named "rep" — a bare ``f`` would collide (for mypy) with the
        # formal-findings loop below, whose variable carries another type.
        for rep in evidence.reported_fallacies:
            party = rep.move_author_label.strip()
            chez = (
                f"chez « {party} »"
                if party
                else "chez un tiers que le texte ne nomme pas"
            )
            rep_lines.append(
                f"  • {fallacy_taxonomy_label(rep.type, rep.family, rep.taxonomy_path)} "
                f"{chez} — l'unité {rep.target_arg_id} en fait état"
            )
        # #3429 — an unlabelled ``reported`` must not become « the quoted
        # voices »: the panel read exactly that out of a block that told the
        # conductor to attribute to « the third party named below » when no
        # party was named at all. No label, no attribution.
        _named_parties = [
            rep.move_author_label.strip()
            for rep in evidence.reported_fallacies
            if rep.move_author_label.strip()
        ]
        _attribution_rule = (
            "et attribue-les au tiers nommé ci-dessous — ne les présente "
            "jamais comme les siens."
            if _named_parties
            else "le texte ne nomme aucun tiers : ne les attribue à aucune "
            "voix citée, ne nomme personne, et ne les présente jamais comme "
            "les siens."
        )
        reported_block = (
            "SOPHISMES RAPPORTÉS, NON COMMIS PAR LE LOCUTEUR : "
            f"{accord(n_rep, 'sophisme rapporté', 'sophismes rapportés')} "
            "(le texte les dénonce ou les cite, il ne les commet pas). "
            "Ils ne forment AUCUN mouvement ci-dessus et ne comptent PAS "
            "parmi les dérapages du locuteur : si tu les évoques, dis que le "
            f"locuteur les RAPPORTE, {_attribution_rule}\n"
            + "\n".join(rep_lines)
            + "\n\n"
        )

    # --- formal anchors (verified-in-state) ---
    # #1914 (constat 1) : an anchor without its tested content reads as a
    # badge — the reader cannot tell WHAT was tested. Each line now carries
    # the derivation material (or its honest absence); the consigne below
    # binds the conductor to weave testé → établi → conséquence.
    formal_block = "AUCUN verdict formel vérifié dans le state."
    if evidence.formal_findings:
        formal_lines = []
        for f in evidence.formal_findings:
            if f.kind in ("pl", "fol", "modal"):
                # the solver-count findings are the badge surface — they carry
                # the derivation (or its honest absence). Dung findings are
                # NOT counters: their verdict sentence already IS a
                # derivation (graph shape + consequence) — no marker there.
                if f.tested:
                    derivation = f"testé : {f.tested}"
                elif f.tested_absence == ABSENT_CONFLICT_NOT_LOCALISED:
                    # #3179 — the content IS in the state; what is missing is a
                    # localised conflict. Calling it "non disponible" told the
                    # reader the opposite of what the state holds. #2960 is
                    # untouched: no inference is singled out, so the decisive
                    # role still cannot fire against one.
                    derivation = (
                        "contenu testé présent "
                        f"({accord(f.tested_n_formulas, 'formule testée', 'formules testées')}) "
                        "mais conflit non localisé : aucune paire de formules ne "
                        "porte la contradiction — le verdict porte sur la théorie "
                        "entière, jamais sur une inférence désignée"
                    )
                else:
                    derivation = (
                        "contenu testé non disponible dans l'état (compteur seul)"
                    )
                # #3146 : the recorded core's source units — the verdict binds
                # to the batch's units (their movements), never « attached to
                # no move » for a conflict the state localises exactly.
                # #3199 rework: the qualifier follows the STATED cause. The
                # batch sentence is true only of ``batch_attribution``; on an
                # ``unattributed_side`` record only one flank carries units,
                # and any other class (or no stated cause) has no business
                # asserting a translation batch at all.
                binding_note = {
                    "batch_attribution": (
                        " (le lot de traduction de ces unités, pas une seule)"
                    ),
                    "unattributed_side": (
                        " (côté connu seulement — l'autre côté du conflit ne "
                        "porte aucune unité source)"
                    ),
                }.get(f.cause_kind, "")
                binding = (
                    f" — rattachement : unités {', '.join(f.units)}" f"{binding_note}"
                    if f.units
                    else ""
                )
                formal_lines.append(
                    f"  - {_KIND_READABLE.get(f.kind, f.kind)} : {f.verdict} — "
                    f"{derivation}{binding} — ancrage : {f.detail}"
                )
            else:
                formal_lines.append(
                    f"  - {_KIND_READABLE.get(f.kind, f.kind)} : {f.verdict} — "
                    f"ancrage : {f.detail}"
                )
        formal_block = "\n".join(formal_lines)

    # #1914 résidu b — the citation contract. The refs already ride the
    # anchor lines, but the anti-recopy rule dominated and no consigne ever
    # authorized citing one (measured: 0/49 acts cite the appendix). The
    # directive is the precise exception: the ref is the ONE anchor fragment
    # built to appear verbatim — everything else stays prose-woven. The
    # example interpolates a REAL ref from the block (never a placeholder:
    # a bracketed placeholder would pollute the ref namespace a conductor
    # stub — or a reader — scans).
    annex_ref_rule = ""
    _formal_refs = appendix_refs_in(formal_block)
    if _formal_refs:
        annex_ref_rule = (
            "RÉFÉRENCES D'ANNEXE (la preuve repliée) — quand une ancre TENUE "
            "FORMELLE porte une référence d'annexe Dung (entre crochets) :\n"
            f"- Tu PEUX citer cette référence TELLE QUELLE, entre "
            f"parenthèses, sur le battement qui mobilise cette ancre : "
            f"« … (voir {_formal_refs[0]}) ».\n"
            "- La référence est la SEULE partie de la ligne d'ancrage qui "
            "puisse être recopiée : le reste (solveur, composition, "
            "protocole) reste interdit de recopie — la preuve se tisse en "
            "prose, la référence ouvre le pli de l'annexe.\n"
            "- Cite une référence SEULEMENT sur le battement qui mobilise "
            "l'évidence correspondante ; jamais sans elle, jamais inventée "
            "ni modifiée : copie-la exactement depuis TENUE FORMELLE.\n"
            "- Une référence ne change PAS le rôle d'un résultat (décisif / "
            "corroborant / contradictoire / non discriminant) : la hiérarchie "
            "RÔLES gouverne ; la référence n'indique qu'où la preuve est "
            "repliée.\n\n"
        )

    # --- SV (#1182): délibération collective (governance + debate) ---
    # Both capabilities were completing in the 40 phases but invisible in the
    # report. We surface what exists — honestly sparse when the schemes-engine
    # gap (β G8) left debate thin. Each citation must bind to a narrative beat
    # (spec §4 anti-énumération); never a bare score/label line.
    # #2965 / R1077 — frame the verdict on its ORIGIN (`winner_provenance`,
    # #2969), never on `extraction_method`. An LLM assessment that ran is not
    # the verdict: on the R1077 paid pass (`doc_A`: llm + vote_aggregate) the
    # old rule told the reader a vote was a model ranking — false.
    # R1078 — the GOUVERNANCE line is ONE shared renderer (cited_units): the
    # fallback producers write a STRATEGY (`compromise`) and a MEDIATION TYPE
    # (`collaborative`) into `winner`, not a ranked unit — presenting those as
    # « l'argument arrivé en tête » was the R1078 blocker on this PR.
    deliberation_lines: List[str] = []
    gv = evidence.governance_verdict
    if gv is not None:
        gov_warning, gov_lead = render_governance_lead(
            gv.method,
            gv.winner,
            evidence.governance_winner_text,
            gv.winner_provenance,
            gv.method_provenance,
            tail="(noms d'options maintenus opaques — discipline FB-34.)",
            # #3001 (a′) — the robustness band's inputs (vote only).
            support_by_option=gv.support_by_option,
            methods_by_option=gv.methods_by_option,
            n_methods_decided=gv.n_methods_decided,
            winner_basis=gv.winner_basis,
            # #3394 (tranche R1145) — the protocols, named apart from the
            # vote's fraction.
            n_consensus_protocols=len(gv.consensus_protocols) or None,
        )
        # #2969 / #2989 rework: a divergent vote is part of the verdict —
        # name every distinct winner by WHAT IT SAYS (an id only when its
        # text is not localizable), never reduce it to one "leading
        # argument" the methods never agreed on. #3001: each winner's
        # qualitative support travels beside its text.
        divergence = render_divergence_clause(
            evidence.governance_divergent_texts,
            support_by_option=gv.support_by_option,
            methods_by_option=gv.methods_by_option,
            n_methods_decided=gv.n_methods_decided,
        )
        if divergence:
            gov_lead += divergence
        if gov_warning:
            deliberation_lines.append(gov_warning)
        deliberation_lines.append(gov_lead)
        # #3386 — the coalition play's facts, beside the verdict they
        # qualify: who moved their ballot and what it changed, and/or the
        # declared profile's pivot. Producer-rendered (no prompt rule added).
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
                f"réplique « {ex.rebuttal} »{scheme_anchor}."
            )
    deliberation_block = (
        "\n".join(deliberation_lines)
        if deliberation_lines
        else "  (aucune délibération governance/débat non-triviale dans le state — "
        "ne la fabrique pas, note l'absence honnêtement si tu l'évoques)"
    )

    quality_note = (
        "L'axe qualité est disponible : tisse les vertus comme CARACTÈRE."
        if evidence.quality_axis_available
        else "L'axe qualité est INDISPONIBLE sur ce run : note-le honnêtement, "
        "ne fabrique jamais de profil de vertus."
    )
    if evidence.quality_ranking:
        # #3159 — the ranking and its base travel with the note, so the writer
        # never has to derive « le mieux tenu » from a vote verdict.
        quality_note += "\n  " + evidence.quality_ranking

    opaque_block = f"{_OPAQUE_ID_DIRECTIVE}\n\n" if not evidence.deanonymized else ""

    # #1914 (Acte II slice) — the evidential-role hierarchy. The structure
    # carries the classification; the consigne below binds how each role may
    # be cited. Renders in both states so a silence is never read as a verdict.
    role_lines: List[str] = []
    for _role in ROLE_ORDER:
        for assignment in evidence.role_assignments:
            if assignment.role == _role:
                role_lines.append(
                    f"  - {ROLE_LABELS[_role]} — {assignment.statement} "
                    f"(ancres : {', '.join(assignment.cites)})"
                )
    roles_block = (
        "\n".join(role_lines)
        if role_lines
        else (
            "  (aucun résultat de spécialiste ne change le jugement, ne le "
            "corrobore ni ne le contredit sur ce corpus — n'invente aucun rôle)"
        )
    )

    # #1911 — the global synthesis channel; renders in both states so a silence
    # is never read as a verdict.
    global_block = (
        "\n".join(
            f"  - {_KIND_READABLE.get(f.kind, f.kind)} — {f.statement} "
            f"(ancres : {', '.join(f.cites)})"
            for f in evidence.global_findings
        )
        if evidence.global_findings
        else (
            "  (aucune convergence inter-axes ni gate de synthèse ne se dégage "
            "— n'en fabrique aucune)"
        )
    )

    # #2295 — the text sequence: the order the TEXT brings the moves,
    # restored from anchors (the execution clock cannot give it — it
    # orders by phase DAG). Renders in both orders' states so the verdict
    # is said, never implied by silence.
    seq_lines: List[str] = []
    seq_verdict = ""
    if evidence.text_sequence is not None:
        _seq = evidence.text_sequence
        # #2848 — SELECTION SPANS THE TEXT: the k moves handed to the narrated
        # thread are stratified over the anchored offsets (select_for_budget,
        # same gesture as #2850 slice A), not the first k in text order. The
        # budget (8) is unchanged; a bigger head sample would still be a head
        # sample.
        # Index-keyed ids: one arg can carry several moves (assert + retract),
        # so arg_ref is not unique — the position in the sequence is.
        _move_units = [
            SelectableUnit(unit_id=f"move_{i}", text="", offset=m.offset)
            for i, m in enumerate(_seq.moves)
        ]
        _move_selection = select_for_budget(
            _move_units,
            _SEQUENCE_RENDER_CAP,
            text_length=evidence.source_length or None,
        )
        _chosen_ids = {u.unit_id for u in _move_selection.selected}
        _chosen_moves = [
            m for i, m in enumerate(_seq.moves) if f"move_{i}" in _chosen_ids
        ]
        # #2896 (d): the thread's ACTORS are never raw ``arg_N`` ids. The
        # paid run's Act II printed « Plus loin, ``arg_40`` tente de… » —
        # the narrator received the machine id as an actor name and echoed
        # it verbatim into the prose. Each distinct arg_ref now gets a
        # stable letter (same letter = same argument across its moves, so
        # the assert-then-retract thread stays readable). Opaque ids stay
        # legitimate in the STRUCTURED data blocks (the Dung trace anchors,
        # #1280); this is the narrative thread, not a data block.
        for _i, m in enumerate(_chosen_moves, start=1):
            label = MOVE_LABELS_FR.get(m.move, m.move)
            if RAW_UNIT_ID_RE.fullmatch(m.arg_ref or ""):
                who = f"l'argument {m.arg_ref}"
            elif m.arg_ref:
                # a phase/axis reference, not a unit: calling it « l'argument
                # extract » would be a false designation, and the phase's raw
                # name is not corpus text the writer may narrate. The old
                # private legend hid these behind a letter that referred to
                # nothing; the honest render says so on the line itself
                # (#2965's lesson, applied at the line).
                who = "un coup non rattaché à un argument"
            else:
                who = "coup non référencé"
            seq_lines.append(f"  {_i}. {who} — {label} (offset {m.offset})")
        # #3296 — the thread no longer owns a private letter map. It kept one
        # since #2896 (d) + the #2965 legend because nothing else designated
        # the actors; the per-act label table now does, at the prompt's
        # assembly seam (unit_labels.py), with ONE legend for every block.
        # Two letter vocabularies in one prompt would collide — the thread's
        # α (its first actor) is not the table's α (the prompt's first id) —
        # so the thread renders the raw arg_ref and the seam relabels it,
        # same letter as every other block. The #2896 guard (no raw id in the
        # rendered prompt) is upheld by the seam, not by a second map.
        # #2848 — the truncation is SAID where it is read: k shown over N
        # anchored, covering a–b over the source's L characters.
        if len(_seq.moves) > len(_chosen_moves) and _chosen_moves:
            _a = min(m.offset for m in _chosen_moves)
            _b = max(m.offset + m.length for m in _chosen_moves)
            _k = len(_chosen_moves)
            _n = len(_seq.moves)
            _l = evidence.source_length
            seq_lines.append(
                f"  ({_k} coups montrés sur {_n} ancrés, couvrant les "
                f"positions {_a}–{_b} sur {_l} caractères)"
            )
        if _seq.order_differs is True:
            seq_verdict = (
                "  L'ordre du TEXTE diffère de l'ordre d'analyse : le récit "
                "suit l'ordre du texte, pas l'ordre des phases."
            )
        elif _seq.order_differs is False:
            seq_verdict = "  L'ordre d'analyse suit ici l'ordre du texte."
        else:
            seq_verdict = "  Un seul coup ancré — pas d'ordre à comparer."
    sequence_block = ""
    if seq_lines:
        sequence_block = (
            "SÉQUENCE DU TEXTE (coups argumentatifs ancrés, ordonnés par leur "
            "position dans le texte — à tisser comme fil chronologique du "
            "récit) :\n" + "\n".join(seq_lines) + "\n" + seq_verdict + "\n\n"
        )

    # #2966 — le FAIT de couverture, dit comme un fait : combien d'unités n'ont
    # pas été soumises. Sans lui, le lecteur du prompt voit un mouvement
    # « non examinés » sans savoir s'il tient à un échantillon ou à un défaut
    # d'enregistrement, et le writer doit savoir laquelle des deux raconter.
    coverage_note = ""
    if unexamined_total:
        if evidence.fallacy_sample_recorded:
            seen = accord(
                evidence.fallacy_sample_size, "unité examinée", "unités examinées"
            )
            coverage_note = (
                f"COUVERTURE — {accord(unexamined_total, 'unité', 'unités')} "
                f"n'ont PAS été soumises à la détection de sophismes sur ce run "
                f"({seen} sur {accord(evidence.args_total, 'extraite', 'extraites')}) : "
                "leur absence de sophisme est une absence d'examen, jamais une "
                "tenue démontrée. Nomme ce fait, ne le présente pas comme un "
                "résultat d'analyse.\n\n"
            )
        else:
            coverage_note = (
                "COUVERTURE — l'ensemble des unités soumises à la détection de "
                "sophismes n'a pas été enregistré sur ce run : aucune unité ne "
                "peut être présentée comme tenant, faute de savoir lesquelles "
                "ont été examinées.\n\n"
            )

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
    # #3432 (ask 6b) — the cross-passage consistency block, right after the
    # reading it builds on: a solver verdict is a PREUVE to weave, never an
    # inventory line. Empty when the state carries no record.
    cross_passage_block = (
        f"{evidence.cross_passage}\n\n" if evidence.cross_passage else ""
    )
    # #3492 — the coverage review's block: the supports or qualifiers of the
    # thesis no lens examined, and what the routed lens answered (or the honest
    # "nommé, non examiné" of a class with no wired lens). Empty when the
    # review named nothing: the prompt is then byte-identical to the pre-#3492
    # one.
    coverage_review_block = (
        f"{evidence.coverage_review}\n\n" if evidence.coverage_review else ""
    )

    prompt = (
        "Tu es l'auteur de l'ACTE II d'un rapport de restitution argumentative.\n"
        "Le récit suit le FIL ARGUMENTATIF (thèse → soutiens → dérapages), découpé\n"
        "par MOUVEMENT argumentatif, PAS par dimension analytique.\n\n"
        f"{opaque_block}"
        f"{_WEAVING_RULE}\n\n"
        f"{virtuous_section}"
        # #3081 — the #3073 class one act away: the blocks under this heading
        # are the specialists' readings of the text (extracted units, detected
        # procedures), not verified facts. The heading says what they are;
        # « ne citer que celles-ci » stays — it says what to cite, not what is
        # verified. TENUE FORMELLE below is different: solver verdicts keep
        # their « ancres vérifiées ».
        "DONNÉES DU STATE (ne citer que celles-ci — extraits et procédures "
        "détectées : lectures du texte par les spécialistes, jamais des "
        "données vérifiées) :\n\n"
        f"{chr(10).join(blocks)}\n\n"
        # #3082 — le locuteur vient du MÊME enregistrement que celui des
        # Actes I et III (valeur + provenance) : trois actes, une valeur, une
        # étiquette. Bloc à titre crocheté, auto-qualifié — il n'est PAS une
        # lecture du texte par un spécialiste, il ne vit donc pas sous le
        # titre DONNÉES DU STATE ci-dessus (dont la parenthétique qualifie
        # ses blocs comme extraits et procédures détectées).
        f"[LOCUTEUR — provenance de la valeur]\n"
        f"  {format_speaker_line(evidence.speaker)}\n"
        # #3390 — the arena line, same single formatter as Acts I and III;
        # and when the arena is a fiction, the one consequence stated once:
        # the characters argue, the author does not assert.
        f"  {format_arena_line(evidence.arena)}\n"
        + (
            "  ARÈNE DE FICTION : les gestes détectés sont ceux des "
            "PERSONNAGES — ne les attribue jamais à l'auteur.\n"
            if is_fiction_arena(evidence.arena)
            else ""
        )
        + f"\n{first_reading_block}"
        + f"{cross_passage_block}"
        + f"{coverage_review_block}"
        f"{reading_block}"
        f"{coverage_note}"
        f"{unattributed_block}"
        f"{reported_block}"
        f"TENUE FORMELLE (ancres vérifiées, à tisser comme PREUVE d'un battement) :\n"
        f"{formal_block}\n\n"
        f"{annex_ref_rule}"
        f"DÉLIBÉRATION COLLECTIVE (governance + débat, à tisser dans le récit — "
        f"le verdict de gouvernance ou un échange de débat peut appuyer un "
        f"battement, jamais une sous-section isolée) :\n"
        f"{deliberation_block}\n\n"
        f"{sequence_block}"
        f"RÔLES DES RÉSULTATS DE SPÉCIALISTES (hiérarchie de preuve dérivée de "
        f"l'état — ce que chaque résultat peut changer dans le jugement) :\n"
        f"{roles_block}\n\n"
        f"CONVERGENCES GLOBALES (synthèse inter-axes, ancrées — à tisser comme "
        f"DEGRÉ DE CONFIANCE d'un battement : quand plusieurs méthodes "
        f"indépendantes s'accordent sur un même argument, le récit le pèse en "
        f"français courant, sans énumérer les méthodes par leur nom technique) :\n"
        f"{global_block}\n\n"
        f"{quality_note}\n\n"
        "CONSIGNE DE RÉDACTION :\n"
        "- Pour chaque mouvement, écris un paragraphe qui tisse en UN battement : "
        "l'argument, son caractère (vertus) si l'axe est disponible, ses procédés "
        "relevés (procédé + examen approfondi + contre-argument), et sa tenue "
        "formelle citée comme preuve.\n"
        # #3082 — la règle de nommage que l'Acte III porte déjà, mot pour mot :
        # un seul contrat, une seule constante. L'Acte II récitait « le
        # locuteur » sans jamais lire la donnée qui dit qui il est.
        f"{SPEAKER_NAMING_RULE}\n"
        f"{READING_BASIS_RULE}\n"
        # #3237 — the cause rule Act III already carried, from the same
        # father (fol_cause): Act II receives the recorded causes on its
        # evidence lines; without the rule that binds the prose to them, it
        # misstates the cause (R1110c). Same constant, no second copy.
        f"- {FORMAL_CAUSE_NAMING_RULE}\n"
        # #3231 — le standing du verdict pèse ce que le détecteur a pesé : sa
        # confiance est imprimée sur chaque ligne Procédé et sa justification
        # va jusqu'à sa dernière phrase (c'est là qu'un détecteur écrit sa
        # réserve). Aucun seuil numérique : le standing suit les deux canaux
        # que le détecteur a lui-même écrits, le rédacteur les lit.
        "- Un procédé relevé n'est pas un défaut par nature. Pour chacun, dis "
        "d'abord CE QU'IL ACCOMPLIT dans le discours — ce que le locuteur "
        "cherche à obtenir par lui ; la justification le porte le plus souvent "
        "(« visant à… », « pour légitimer… ») : traduis-le en français courant, "
        "sans recopier ses guillemets. PUIS juge s'il fragilise le "
        "raisonnement : un procédé dont la justification établit une faute "
        "GARDE son verdict de sophisme, nommé comme tel — l'objectif n'est pas "
        "d'adoucir, c'est de ne pas confondre une figure (ce qui fait avancer "
        "le discours) avec une faute (ce qui le casse). Le standing du verdict "
        "est celui de son détecteur : chaque ligne Procédé porte sa confiance "
        "(« confiance du détecteur »), et sa justification va jusqu'à sa "
        "dernière phrase — c'est là qu'un détecteur écrit sa réserve. Une "
        "détection que le détecteur lui-même tient pour provisoire — confiance "
        "basse, ou réserve écrite dans sa justification — se raconte comme une "
        "lecture PROVISOIRE du procédé, jamais comme une faute établie. "
        # #3248 — l'échelle en mots et l'interdiction du chiffre, une seule
        # constante pour les deux actes (le geste #3237) : le writer copiait
        # la décimale de la ligne evidence (« une confiance de détection de
        # 0,6 », R1113a) — les mots #3234 et le chiffre vivaient ensemble.
        f"{DETECTION_STANDING_RULE} "
        "N'invente JAMAIS une "
        "fonction que la justification ne porte pas : si elle ne dit que la "
        "faute, dis la faute.\n"
        "- Le verdict formel (Tweety/Dung) appuie le battement. Le MOT du "
        "verdict se cite EXACTEMENT tel que fourni (si le verdict dit "
        "'consistantes', écris 'cohérent/consistant', JAMAIS 'inconsistant' ; "
        "INTERDIT de prétendre que Tweety confirme une 'inconsistance' si "
        "TENUE FORMELLE ne contient pas le mot 'inconsistant') — mais la "
        "LIGNE d'ancrage ne se recopie JAMAIS telle quelle dans le récit : "
        "pas de guillemets-recopie de « … — ancrage : solveur … », la preuve "
        "se tisse en prose.\n"
        "- Un verdict formel cité dans le récit est une DÉRIVATION, pas un "
        "badge : le lecteur doit recevoir CE QUI A ÉTÉ TESTÉ (le fragment "
        "« testé : … » de TENUE FORMELLE, traduit dans tes mots en français "
        "courant — jamais la formule brute ni les prédicats recopiés), "
        "CE QUI A ÉTÉ ÉTABLI (la tenue ou l'échec), et CE QUE ÇA CHANGE "
        "pour le jugement du mouvement concerné. "
        "Si l'ancrage porte « contenu testé non disponible », dis-le tel quel : "
        "un compteur sans contenu est une preuve procédurale, pas une "
        "dérivation — INTERDIT de lui inventer une formule ou un contenu. "
        "Si l'ancrage dit au contraire que le contenu est PRÉSENT mais que le "
        "conflit n'est pas localisé, dis le nombre de formules testées et "
        "l'absence de conflit localisé — et ne désigne AUCUNE inférence "
        "précise : le verdict porte sur la théorie entière.\n"
        "  Pour Dung : le graphe est BÂTI à partir des arguments retenus "
        "pour le graphe (pas un oracle externe) — cadre-le comme une "
        "réorganisation du matériau extrait, pas comme une vérification "
        "indépendante. Si tu cites la volumétrie du graphe, reprends le pont "
        "fourni dans TENUE FORMELLE (« N retenus sur M unités "
        "argumentatives identifiées ») ; n'écris JAMAIS « N arguments "
        "extraits » pour la population du graphe — ce syntagme désigne "
        "l'inventaire complet de l'Acte I.\n"
        "- La hiérarchie RÔLES gouverne la citation d'un résultat de "
        "spécialiste : un résultat décisif doit changer ce que le récit "
        "conclut sur sa cible ; un résultat corroborant appuie sans rien "
        "changer à lui seul ; un résultat contradictoire se dit comme une "
        "tension non résolue, jamais tranchée en silence ; un résultat non "
        "discriminant ne peut JAMAIS être cité comme une force ni une "
        "faiblesse — il a tourné sans rien distinguer.\n"
        "- Si un mouvement n'a ni sophisme ni verdict formel (les soutiens), "
        "dis ce qui le tient (le caractère, la cohérence).\n"
        # #3158 — le contre-argument est le canal de l'objection ; CHAQUE
        # ligne en porte la provenance (option (b), R1109).
        "- Toute ligne de contre-argument porte "
        f"« {_UNSOURCED_CLAIM_TAG} » : c'est une objection produite par un "
        "générateur, que rien n'a vérifiée. Rien de ce qu'elle avance n'est "
        "un fait du rapport : écris « un contre-argument objecte que… », "
        "jamais la thèse reprise comme un constat. Tu ne peux pas la "
        "vérifier — tu ne la signes donc pas.\n"
        "- JARGON INTERNE INTERDIT dans la prose : ne recopie JAMAIS un "
        "identifiant technique brut — token snake_case (agent_1, social_choice, "
        "modal_kb…), nom d'agent numéroté, ou nom de méthode/modèle interne. "
        "Ils sont opaques et illisibles pour le lecteur non-technicien à qui ce "
        "récit s'adresse. Décris-les par leur RÔLE en français courant "
        "(« l'argument arrivé en tête », « la méthode de vote employée »). "
        "L'opacité des sources (FB-34) reste préservée : décrire par rôle ne "
        "déanonymise aucune source.\n"
        "- Le récit doit VARIER selon le contenu réel ci-dessus : pas de prose\n"
        "  générique recyclable. Ce que tu écris découle des données.\n"
        "- Rédige en français, markdown léger (titres thématiques en ###). "
        "300-700 mots selon la richesse réelle.\n"
    )
    # #3296 — the seam: every arg_N the data blocks supplied (movement
    # bullets, Dung anchors, quality ranking, role/global cites, the thread)
    # leaves the writer's view here, relabelled by the per-act table with its
    # legend. The consignes carry no id (PR #3303), so nothing else changes.
    return label_writer_prompt(prompt, evidence.unit_texts)


# --- LLM-conducted weaving (fail-loud) ---------------------------------------


async def weave_act2_narrative(
    evidence: Act2Evidence, llm_callable: LlmCallable
) -> WeaveOutcome:
    """Conduct the Acte II narrative via the LLM (fail-loud, #1108).

    The outcome carries the LLM-produced markdown, or the observed reason there
    is none — the call raised, or the LLM produced nothing (#2345); the caller
    records it with the explicit ``unavailable`` status. No template fallback —
    anti-pendule #1019/#369.
    """
    return await weave(build_act2_prompt(evidence), llm_callable, "Acte II")


def build_act2_retry_prompt(
    evidence: Act2Evidence,
    flagged: List[str],
    letter_flagged: Optional[List[str]] = None,
) -> str:
    """The bounded ONE writer retry (#3343) — the writer rewrites its own prose.

    The base prompt is the one the writer already received: same data blocks,
    same rules, same relabelling (#3296). The correction blocks only NAME what
    the checks found — the #3297 superlative read, and since #3367 the #3317
    letter read — because the rules were already in the prompt and the writer
    broke them anyway (#3159 gave the licence, nothing read the act).

    Each correction block is self-contained and carries its own quoted
    sentences, capped at 5: a writer told what it did and nothing to stand on
    is a dice roll. The letter block never orders a designation by id or
    letter (#3303/#3296) — it restates the designation rule the legend
    already carries: the unit is designated by what it says, like the rest of
    the prose, or the same thing is said at discourse level.

    Bounded by construction: one call, never a loop. The checks still only
    record — a retry that changes nothing is a fact the report carries, not a
    reason to keep asking.
    """
    blocks: List[str] = []
    if flagged:
        quoted = "\n".join(f"- {sentence}" for sentence in flagged[:5])
        blocks.append(
            f"\n\nCORRECTION DEMANDÉE — ta rédaction ci-dessus contient "
            f"{len(flagged)} phrase(s) qui portent un superlatif sur TOUT le "
            "discours (« le plus… du dispositif », « … du discours », « … du "
            "run ») sans classement mesuré pour l'adosser. Le classement fourni "
            "plus haut est le SEUL mesuré : un superlatif ne peut pas le "
            f"dépasser. Phrases repérées :\n{quoted}\n\n"
            "Réécris le récit EN ENTIER — même structure, mêmes mouvements, "
            "mêmes données, même longueur. Pour chaque superlatif, choisis : "
            "soit il porte sur la population réellement évaluée et la nomme "
            "(« de l'ensemble évalué »), soit il cite la base du classement "
            "(« N unités évaluées sur M »), soit il porte sur un argument du "
            "classement avec son rang. Sinon, ne l'écris pas : dis la même "
            "chose sans superlatif. Ne commente pas cette consigne et ne cite "
            "pas les phrases repérées : rends le récit complet, prêt à lire.\n"
        )
    if letter_flagged:
        letter_quoted = "\n".join(f"- {sentence}" for sentence in letter_flagged[:5])
        header = "CORRECTION DEMANDÉE" if not flagged else "AUTRE CORRECTION DEMANDÉE"
        blocks.append(
            f"\n\n{header} — ta rédaction ci-dessus imprime {len(letter_flagged)} "
            "phrase(s) où une lettre de désignation (α, β, …) paraît dans le "
            "récit. Une lettre est un raccourci d'atelier : le lecteur n'a pas "
            "la légende des désignations et ne peut rien en résoudre. Phrases "
            f"repérées :\n{letter_quoted}\n\n"
            "Réécris le récit EN ENTIER — même structure, mêmes mouvements, "
            "mêmes données, même longueur. Pour chaque lettre imprimée, "
            "désigne l'unité par ce qu'elle dit — comme le reste de ta prose ; "
            "la légende des désignations en donne le texte —, ou dis la même "
            "chose au niveau du discours. N'imprime jamais la lettre seule ni "
            "un identifiant interne. Ne commente pas cette consigne et ne cite "
            "pas les phrases repérées : rends le récit complet, prêt à lire.\n"
        )
    return build_act2_prompt(evidence) + "".join(blocks)


async def weave_act2_narrative_retry(
    evidence: Act2Evidence,
    llm_callable: LlmCallable,
    flagged: List[str],
    letter_flagged: Optional[List[str]] = None,
) -> WeaveOutcome:
    """The bounded ONE retry (#3343/#3367), under the same fail-loud contract."""
    return await weave(
        build_act2_retry_prompt(evidence, flagged, letter_flagged),
        llm_callable,
        "Acte II (relance)",
    )


# --- orchestrator ------------------------------------------------------------


@dataclass(frozen=True)
class _DressedAct2:
    """One Act II draft after every deterministic pass + the #3297/#3317 reads.

    The bounded retry (#3343/#3367) dresses a second draft EXACTLY like the
    first — comparing two texts is only honest when both went through the same
    passes, and the checks must judge the text the reader would receive.
    """

    text: str
    bound_removal: BoundRemoval
    clash_removed: List[str]
    superlative_note: str
    superlative_sentences: List[str]
    letter_sentences: List[str]


def _dress_act2_prose(
    narrative: str, state: Any, evidence: Act2Evidence
) -> _DressedAct2:
    """Launder one draft: bounds withdrawal, voice-clash strip, #3297 read.

    Silent by design — the caller logs the retained draft, so a discarded
    first draft leaves no repair trace claiming work the reader never got.
    """
    # #3134/#3310 — a woven sentence that restates a numeric bound is
    # withdrawn before anything else touches the text: the reader's bounds are
    # the record's passage grafted below, where each number sits under its own
    # site label. ``remove_restated_bounds`` keeps the following anaphor's
    # antecedent — deleting the whole sentence took it away.
    _bound_removal = remove_restated_bounds(narrative)

    # #3237 — a woven sentence that ties a formal contradiction to voices
    # clashing, when every recorded cause says otherwise, is removed the same
    # way (#1605 shape): the act's evidence lines already carry the record's
    # own cause phrase, so nothing true is lost.
    from .formal_cause_check import strip_voice_clash_cause_sentences

    text, _removed_clash = strip_voice_clash_cause_sentences(_bound_removal.text, state)

    # #3297 — a whole-scope superlative needs a measured ranking to stand on.
    # The check runs on the MODEL PROSE, before the record's own bounds are
    # appended below: the bounds are the record's wording, not the writer's
    # claim, and the act must not be degraded for them.
    from .whole_scope_superlative_check import (
        whole_scope_superlative_note,
        whole_scope_superlative_sentences,
    )

    _superlative_note = whole_scope_superlative_note(
        text, ranking_line=evidence.quality_ranking, act_label="Acte II"
    )
    _flagged = (
        whole_scope_superlative_sentences(text, ranking_line=evidence.quality_ranking)
        if _superlative_note
        else []
    )

    # #3367 — the writer's own handles must stay in the prompt: a printed
    # letter is a designation the reader cannot resolve (#3317). The sentences
    # feed the bounded retry's correction; the gate (unchanged, after) still
    # carries the verdict. No deterministic strip — the fix is the writer's
    # rewrite, not a behind-the-reader edit (#3317's own calibration).
    from .readability_gate import greek_label_sentences

    _letters = greek_label_sentences(text)
    return _DressedAct2(
        text=text,
        bound_removal=_bound_removal,
        clash_removed=list(_removed_clash),
        superlative_note=_superlative_note,
        superlative_sentences=_flagged,
        letter_sentences=_letters,
    )


async def build_act2_narrative(
    state: Any, llm_callable: Optional[LlmCallable] = None
) -> Act2Result:
    """Build the Acte II dialectical narrative for ``state``.

    Deterministic evidence is always built. The narrative is LLM-conducted only
    when ``llm_callable`` is provided; otherwise the result is fail-loud
    (``status="unavailable"``, empty narrative) — the renderer reports the gap
    honestly, never a template (#1108).

    A §4 self-check (``ReadabilityGate``) is attached to every woven result so
    the verdict is auditable; it never fabricates a pass.
    """
    evidence = build_act2_evidence(state)

    if evidence.args_total == 0:
        return Act2Result(
            narrative="",
            status="empty_state",
            degraded={
                "act2_narrative": (
                    "Aucun argument extrait — l'Acte II n'a pas de substrat "
                    "argumentatif à narrer (identified_arguments vide)."
                )
            },
        )

    if llm_callable is None:
        return Act2Result(
            narrative="",
            status="unavailable",
            degraded={
                "act2_narrative": (
                    "Récit dialectique non conduit — aucun LLM injecté pour "
                    "l'Acte II (fail-loud, #1108)."
                )
            },
        )

    outcome = await weave_act2_narrative(evidence, llm_callable)
    if not outcome.narrative:
        return Act2Result(
            narrative="",
            status="unavailable",
            degraded={
                "act2_narrative": (
                    f"Récit dialectique indisponible — {outcome.failure} "
                    "(fail-loud, #1108)."
                )
            },
        )
    _dressed = _dress_act2_prose(outcome.narrative, state, evidence)

    # #3343/#3367 — the bounded ONE retry. #3159 gave the writer the ranking
    # and the rule, #3296 the legend and the designation rule; the #3297 and
    # #3317 checks read the act afterwards, and a rule the writer breaks is
    # still broken prose on the reader's page. So when either check fires, the
    # writer is asked ONCE — with its own flagged sentences — to rewrite the
    # act. The checks still only record: if the rewrite is not better on the
    # SUMMED count, the first draft is kept, and either way the report says
    # which draft the reader received. One call, never a loop — the letter
    # motive joins the same single retry, it does not open a second one.
    _retry_motif = ""
    _letter_retry_motif = ""
    _first_flagged = _dressed.superlative_sentences
    _first_letters = _dressed.letter_sentences
    if _dressed.superlative_note or _first_letters:
        from .readability_gate import designation_letter_retry_motif
        from .whole_scope_superlative_check import superlative_retry_motif

        _retry = await weave_act2_narrative_retry(
            evidence, llm_callable, _first_flagged, _first_letters
        )
        if _retry.narrative:
            _second = _dress_act2_prose(_retry.narrative, state, evidence)
            _before_total = len(_first_flagged) + len(_first_letters)
            _after_total = len(_second.superlative_sentences) + len(
                _second.letter_sentences
            )
            if _after_total < _before_total:
                _dressed = _second
            if _first_flagged:
                _retry_motif = superlative_retry_motif(
                    "Acte II", len(_first_flagged), len(_dressed.superlative_sentences)
                )
            if _first_letters:
                _letter_retry_motif = designation_letter_retry_motif(
                    "Acte II", len(_first_letters), len(_dressed.letter_sentences)
                )
        else:
            if _first_flagged:
                _retry_motif = superlative_retry_motif(
                    "Acte II", len(_first_flagged), failure=_retry.failure
                )
            if _first_letters:
                _letter_retry_motif = designation_letter_retry_motif(
                    "Acte II", len(_first_letters), failure=_retry.failure
                )
        # The excerpt of the FIRST draft stays on the trace: the retained
        # draft's own flags are logged below, and the motive is a code literal
        # with counts (#3249), never a quote.
        logger.info(
            "Acte II bounded writer retry (#3343/#3367): %s | %s | first " "draft: %s",
            _retry_motif or "(pas de superlatif)",
            _letter_retry_motif or "(pas de lettre imprimée)",
            "; ".join(s[:90] for s in (_first_flagged + _first_letters)[:3]),
        )

    narrative = _dressed.text
    # #3389 — the retained draft's « … » spans are compared with the document
    # here, on the WRITER'S prose and before the record's bounds are appended
    # below (same seam as the checks inside ``_dress_act2_prose``: the record's
    # wording is not the writer's). An exact quote passes byte-identical; an
    # altered quote or a translation printed as the document's words loses its
    # guillemets and reads as the paraphrase it is.
    narrative, _quote_motif = sanitize_act_quotes(narrative, state, "Acte II")
    # #3349 — the Dung annex ref must ride the sentence it proves (#1914
    # citation contract). The prompt carries the rule; this is the guarantee:
    # a ref on a sentence that names another formal axis and no graph
    # vocabulary moves to the paragraph's graph sentence, or is dropped.
    from .dung_ref_placement import (
        dung_ref_placement_motif,
        move_misplaced_dung_refs,
    )

    narrative, _dung_moved, _dung_dropped = move_misplaced_dung_refs(narrative)
    _dung_ref_motif = (
        dung_ref_placement_motif("Acte II", _dung_moved, _dung_dropped)
        if (_dung_moved or _dung_dropped)
        else ""
    )
    _bound_removal = _dressed.bound_removal
    if _bound_removal.removed or _bound_removal.withdrawn:
        logger.info(
            "act2 woven bound restatement: %d sentence(s) removed, %d bound(s) "
            "withdrawn in place (record passage carries the figures): %s",
            _bound_removal.removed,
            _bound_removal.withdrawn,
            bound_removal_motif(_bound_removal),
        )

    for _clash in _dressed.clash_removed:
        logger.info(
            "act2 woven voice-clash cause removed (record states otherwise): %s",
            _clash[:90],
        )

    _superlative_note = _dressed.superlative_note
    if _superlative_note:
        logger.warning(
            "Acte II whole-scope superlative (retained draft): %s | %s",
            _superlative_note,
            "; ".join(s[:90] for s in _dressed.superlative_sentences[:3]),
        )

    # #3393 — the record's bounds passage is grafted by Act III ONLY, once,
    # where it closes the whole report (same #3134 rationale, one print: a
    # reserve is said once, #3374). #3134 grafted it in BOTH acts and the
    # reader received it twice, word for word, on 9 of 9 panel renders.
    # Nothing else here reads the passage: the license check below judges
    # the WRITER's prose, and the bounds are code-written record lines.

    # #3123/R1105c — the reading-license check covers the act, not only the
    # synthesis: Act II receives the cause phrases and can charge a recorded
    # cause (a ``between_sources`` inconsistency) to the speaker, though it
    # licenses nothing about any one voice. Flags only — the check never
    # rewrites; the summary goes to the trace.
    from argumentation_analysis.agents.core.synthesis.reading_license import (
        check_reading_license,
        summarise_flags,
    )

    read_license = check_reading_license(narrative, state)
    if read_license["flags"]:
        logger.warning("Acte II reading-license: %s", summarise_flags(read_license))

    # §4 self-check (honest, never grades on a curve).
    gate = ReadabilityGate()
    verdict = gate.check_body(narrative)
    degraded: Dict[str, str] = {}
    if verdict.band != "PASS":
        degraded["act2_narrative_gate"] = (
            f"Autocontrôle de lisibilité = {verdict.band}: "
            + "; ".join(verdict.reasons[:3])
        )
    if not evidence.quality_axis_available:
        degraded["act2_narrative"] = (
            "Axe qualité non concluable ici (argument_quality_scores "
            "indisponible) — vertus tues, fail-loud."
        )
    # #3297 — the motive of the whole-scope superlative lands in the act's
    # degraded map, hence in ``restitution_acts_degraded``. The prose is NOT
    # rewritten: the reader sees the claim, the report carries the reason it
    # is unbacked.
    if _superlative_note:
        degraded["act2_whole_scope_superlative"] = _superlative_note
    # #3343 — the retry rewrote (or tried to rewrite) the act: act, counts and
    # which draft was kept, never a sentence (#3249). Filed under the #2046
    # fabrication-note keys, so it is archived in the appendix and never
    # reaches the reader as a repair note.
    if _retry_motif:
        degraded["act2_superlative_retry"] = _retry_motif
    # #3367 — same family, same contract: the letter retry repaired (or tried
    # to repair) the prose; it tells the reader nothing about the run, so it
    # is archived with the #2046 fabrication notes, never rendered.
    if _letter_retry_motif:
        degraded["act2_designation_letter_retry"] = _letter_retry_motif
    # #3349 — a Dung ref was moved (or dropped) here: act and counts, never a
    # sentence (#3249). Filed under the #2046 fabrication-note keys, so it is
    # archived in the appendix and never reaches the reader as a repair note.
    if _dung_ref_motif:
        degraded["act2_dung_ref_placement"] = _dung_ref_motif
    # #3310 — the prose was CHANGED here, and an auditor must be able to find
    # it: act, motive, count, never the sentence (#3249). Filed under the
    # #2046 fabrication-note keys, so it is archived in the appendix and never
    # reaches the reader as a repair note.
    _bound_motif = bound_removal_motif(_bound_removal)
    if _bound_motif:
        degraded["act2_bound_restatement"] = _bound_motif
    # #3389 — a « … » span was not the document's words: label, counts, never
    # a span (#3249). Filed with the other acts' seam under the #2046
    # fabrication-note keys, archived in the appendix.
    if _quote_motif:
        degraded["act2_quote_fidelity"] = _quote_motif
    vm = evidence.virtuous_mode
    # Positive outcome — reported by ``is_virtuous``, never filed under
    # ``degraded`` (see the note in ``act1_framing_plugin``): #1608 turned
    # ``degraded`` into a verdict, so a virtue left here marked the act as
    # degraded and stripped it from ``capabilities_used``.
    is_virtuous = vm is not None and vm.is_virtuous

    return Act2Result(
        narrative=narrative,
        status="woven",
        gate_verdict=verdict,
        degraded=degraded,
        is_virtuous=is_virtuous,
        read_license=read_license,
    )
