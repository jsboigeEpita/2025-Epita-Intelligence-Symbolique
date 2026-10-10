"""#2967 — the units a writer is asked to DISCUSS reach it whole.

A fixed 220-character head cut showed the Act II narrative and the
deep-synthesis briefing the *setup* of a long unit and dropped what it
*concludes*: on the 06/10 authorized pass, the governance winner kept 31 %
of its text and its operative clause (past character 340) never reached any
writer (#1914).

The budget becomes an ALLOCATION: cited units (the ones a writer is asked
to discuss — attack targets, counter-argument targets, the governance
winner) get their full text up to ``CITED_UNIT_TEXT_CAP``; every other unit
keeps the short cap, so the prompt does not grow with N.

Calibration of the cap (doc_A, 94 units, measured by the coordinator on
the saved state — no saved state lives on a worker seat): median 422,
71/94 longer than 220 (the 75th percentile sits above 220), longest 2 142.
The exact p90 is pending (asked of the coordinator); 2 000 covers the
issue's witness (a cited 700-character unit, whole) with wide margin and
stays under the observed max.

This module carries no heavy imports on purpose: ``deep_synthesis_agent``
imports it, and it must not pull the narrative plugins in.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

# Budget for a CITED unit's text — see the module docstring for the
# calibration and what remains pending.
CITED_UNIT_TEXT_CAP = 2000

# Visible cut marker — the same convention the Act II plugin already used,
# so a reader of either surface meets one marker, and no cut is silent
# (#2967 Expected 3: the briefing used to cut with a bare slice).
CUT_MARKER = " […]"

# A sentence boundary is only used when it preserves at least this share of
# the budget — otherwise a lone early period would throw away almost the
# whole budget to honour the boundary.
_MIN_BOUNDARY_SHARE = 0.5

_SENTENCE_ENDS = (".", "!", "?", "…")


def truncate_at_boundary(text: Any, cap: int, marker: str = CUT_MARKER) -> str:
    """Cap length, cutting at a boundary — never mid-word (#2967 Expected 4).

    Preference order: the last sentence boundary inside the head (if it
    keeps at least half the budget), then the last word boundary, then a
    hard cut when the head carries no boundary at all. Every cut carries
    the visible marker; text within the cap is returned untouched.
    """
    if not text:
        return ""
    s = str(text).strip()
    if len(s) <= cap:
        return s
    head = s[:cap]
    sent = max(head.rfind(end) for end in _SENTENCE_ENDS)
    if sent >= int(cap * _MIN_BOUNDARY_SHARE):
        # keep the sentence delimiter — cutting AT it must not swallow it
        return head[: sent + 1].rstrip() + marker
    word = head.rfind(" ")
    if word > 0:
        return head[:word].rstrip() + marker
    return head.rstrip() + marker


def governance_winner_id(state: Any) -> Optional[str]:
    """The last non-trivial governance decision's winner.

    Mirrors act2's ``_collect_governance`` for the single question "who
    wins" (same trivial guard: a winner needs a method, a value, and not
    the placeholder). Kept here so consumers that must not import the
    narrative plugins (the deep-synthesis briefing) read the same answer.
    """
    decisions = getattr(state, "governance_decisions", None)
    if not isinstance(decisions, list):
        return None
    winner: Optional[str] = None
    for d in decisions:
        if not isinstance(d, dict):
            continue
        method = str(d.get("method", "")).strip()
        w = str(d.get("winner", "")).strip()
        if not method or not w or w == "N/A":
            continue
        winner = w
    return winner


def divergent_winner_texts(
    winners: Sequence[str],
    unit_texts: Mapping[str, Any],
    cap: int = CITED_UNIT_TEXT_CAP,
) -> List[Tuple[str, str]]:
    """``(winner_id, text)`` for each divergent winner, text ``""`` untracked.

    Why the pair travels instead of the bare id (#2965/#2980): the R1071
    replays measured that a writer does not join an id to its unit across a
    long prompt — a divergence line carrying only ``arg_16``, ``arg_23``
    leaves it two bad choices (copy the raw id, and the readability gate
    flags the render; or say "the methods disagree" without saying what
    each winner argues, the role-only form that measured 1/5 attribution).
    Resolution mirrors ``governance_winner_text``: the unit's text through
    ``truncate_at_boundary``; a winner absent from the map keeps ``""`` so
    its id can stay on the line.
    """
    pairs: List[Tuple[str, str]] = []
    for w in winners:
        wid = str(w).strip()
        if not wid:
            continue
        text = unit_texts.get(wid) if isinstance(unit_texts, Mapping) else None
        pairs.append((wid, truncate_at_boundary(text, cap) if text else ""))
    return pairs


def render_divergence_clause(
    winner_texts: Sequence[Tuple[str, str]],
    cap: int = CITED_UNIT_TEXT_CAP,
    support_by_option: Optional[Mapping[str, int]] = None,
    n_methods_decided: Optional[int] = None,
) -> str:
    """The divergent-vote clause: each winner by its TEXT, an id only when no
    text was localized (#2965/#2980 — « ne recopie NI un identifiant
    technique brut »). Empty string when fewer than two winners: the clause
    is earned by the record, never unconditional.

    #3001 (a′) — each winner's QUALITATIVE support band travels next to its
    text (#2989): in a divergence the aggregate number says nothing about
    which winner is solid, and the band stays qualitative (#1914 — never a
    counter). Absent population → no band (honest absence).

    The renderer bounds its OWN text (#2908 census, rework 3): the census
    reads an interpolation of a doc-text name with no bound as a
    whole-document read — it cannot see that ``divergent_winner_texts``
    already capped the pair, and a future caller may hand this renderer raw
    unit text. Each surface carries its own bound; ``truncate_at_boundary``
    is idempotent, so a pair already cut upstream is returned untouched.
    """
    if len(winner_texts) < 2:
        return ""
    parts = []
    for wid, text in winner_texts:
        if text:
            fragment = f"celui qui dit : « {truncate_at_boundary(text, cap)} »"
        else:
            fragment = f"l'option d'identifiant « {wid} » (texte non localisé)"
        band = qualitative_support_band(
            support_by_option.get(wid) if support_by_option else None,
            n_methods_decided,
        )
        if band:
            fragment += f" — soutenu {band}"
        parts.append(fragment)
    joined = " et ".join(parts)
    return (
        f" Le vote DIVERGE entre les méthodes : {joined} sortent gagnants selon "
        "la méthode consultée — la conclusion doit le dire (nomme ce que "
        "défend chacun), pas le réduire à un gagnant unique."
    )


GOVERNANCE_MODEL_WARNING = (
    "ATTENTION : ce verdict governance est une RECOMMANDATION DE STRATÉGIE "
    "(issue d'un seul appel LLM, pas d'une délibération multi-agent réelle, "
    "pas un classement d'arguments). Présente-la comme une stratégie de "
    "résolution recommandée par le modèle, PAS comme une caution de "
    "légitimité procédurale indépendante."
)


def governance_origin(
    winner_provenance: Any,
    method_provenance: Any = None,
) -> Tuple[str, Optional[str], str, str]:
    """How a governance winner was designated, and the warning it earns.

    The origin is ``winner_provenance`` — written by
    ``state_writers._write_governance_to_state`` (#2969) — **never**
    ``extraction_method``. Since GE-4 #1462 an LLM assessment can run *and* a
    formal vote decide the winner: ``extraction_method == "llm"`` says only
    that an assessment happened, so framing the verdict on it made Act II tell
    the reader a vote was a model ranking (R1077 paid pass on ``doc_A``,
    ``llm`` + ``vote_aggregate`` — the wording was false).

    Returns ``(warning, origin, note, kind)``. ``kind`` says WHAT THE ORIGIN'S
    PRODUCER WRITES INTO ``winner`` — measured on the real producers (R1078
    review of #3000): the two fallback paths do not write a ranked unit at
    all, and framing their winners as ranked arguments was the R1078 blocker.

    * ``vote_aggregate`` → no warning, ``"le vote social-choice"`` (a
      model-recommended *method* is carried in ``note``, not the verdict);
      ``kind="vote"`` — ``winner`` is a ranked unit id;
    * ``llm_resolution`` → the model-recommendation warning; ``kind=
      "llm_strategy"`` — the writer stores the LLM's
      ``recommended_resolution`` (``"compromise"``/…), a STRATEGY, not an
      argument;
    * ``conflict_resolution`` → no warning, ``kind="mediation"`` — the writer
      stores the mediation's ``resolution_type`` (``"collaborative"``/…),
      an outcome TYPE, not a unit;
    * unrecorded/unknown → ``origin`` is ``None``, ``kind="unrecorded"``: the
      caller states the origin is unrecorded and does NOT guess it
      (anti-#1019 — absence is not a vote, and a vote is not an absence).
    """
    provenance = (
        winner_provenance.strip()
        if isinstance(winner_provenance, str) and winner_provenance.strip()
        else ""
    )
    if provenance == "vote_aggregate":
        note = (
            "méthode de vote recommandée par le modèle"
            if method_provenance == "llm_recommendation"
            else ""
        )
        return "", "le vote social-choice", note, "vote"
    if provenance == "llm_resolution":
        return (
            GOVERNANCE_MODEL_WARNING,
            "une recommandation de stratégie du modèle",
            "",
            "llm_strategy",
        )
    if provenance == "conflict_resolution":
        return "", "une médiation de conflit", "", "mediation"
    return "", None, "", "unrecorded"


def qualitative_support_band(
    support: Optional[int],
    n_methods_decided: Optional[int],
    winner_basis: Optional[str] = None,
) -> Optional[str]:
    """The QUALITATIVE band of a vote's support (#3001 a′ — never a counter).

    The R1077 census found the support population was dropped before the
    record: "11 methods out of 12" and "the plurality fallback tier only"
    are two different verdicts the Acts rendered with the same sentence.
    This band is the bounded rendering the coordinator's arbitration asks
    for: three bands, no digits (#1914 — a raw counter or a badge would hand
    the writer a number to copy instead of a fact to phrase).

    The bands derive from the DEFINITION (R1080 rework): "majorité" is
    spoken only when 2s > n — strictly more than half of the deciding
    methods — so a tie (2s == n) and any support below half render the
    honest no-majority band (« par une partie seulement des méthodes »).
    The pre-rework else branch said « une majorité étroite » for every
    support below 2/3, which the coordinator's enumeration measured as 108
    affirmative false majorities on the grid n 1..12 — including every
    divergent vote's weakest winner.

    The broad-majority test deliberately precedes the plurality branch
    (cross-review #3006): this is a band of SUPPORT, and a fallback-tier
    winner carried by at least 2/3 of the deciding methods reads as broad
    support. ``winner_basis`` names the deciding tier only in the
    "de justesse" bands, where the narrowness of the decision is the fact
    being rendered — and the plurality branch never borrows the word
    "majorité": the fallback tier can decide while the winner holds no
    majority at all.

    ``None`` when the population is absent (no band without a measured
    support — honest absence, anti-#1019).
    """
    if not n_methods_decided or support is None or support <= 0:
        return None
    n = n_methods_decided
    s = support
    if s >= n:
        return "à l'unanimité des méthodes qui ont décidé"
    if 3 * s >= 2 * n:
        return "par une large majorité des méthodes"
    if winner_basis == "plurality":
        if 2 * s > n:
            return (
                "de justesse, par une majorité étroite des méthodes, au "
                "palier de repli"
            )
        return (
            "de justesse, au palier de repli — aucune option ne s'était "
            "clairement imposée parmi les méthodes"
        )
    if 2 * s > n:
        return "de justesse, par une majorité étroite des méthodes"
    return "par une partie seulement des méthodes"


def render_governance_lead(
    method: str,
    winner: str,
    winner_text: str,
    winner_provenance: Any,
    method_provenance: Any = None,
    tail: str = "",
    support_by_option: Optional[Mapping[str, int]] = None,
    n_methods_decided: Optional[int] = None,
    winner_basis: Optional[str] = None,
) -> Tuple[str, str]:
    """The GOUVERNANCE line of both Acts' prompts — one renderer, no drift.

    Both Acts used to build this line independently (R1077: Act III said
    "vote social-choice" whatever the origin; R1078: both dressed a strategy
    as « l'argument arrivé en tête »). The framing keys on the origin AND on
    the KIND of value the origin's producer writes into ``winner`` (see
    :func:`governance_origin`): a strategy is named as a strategy, a mediation
    type as a mediation — the ranked-argument framing is reserved for the
    kinds whose ``winner`` IS a unit id (``vote``, ``unrecorded``).

    #3001 (a′) — for ``kind == "vote"`` ONLY, the lead carries a bounded
    robustness clause: the winner's qualitative support band (see
    :func:`qualitative_support_band`), with the instruction to keep it
    qualitative. It grafts onto the ``kind`` framing of #3000 and never
    fires for a fallback origin, whose winner is not a unit at all.

    Returns ``(warning, lead)`` — the caller appends the divergence clause
    (#2989, votes only) to the lead, then the warning and the lead to its
    deliberation lines.
    """
    warning, origin, note, kind = governance_origin(
        winner_provenance, method_provenance
    )
    if kind == "llm_strategy":
        lead = (
            f"  - GOUVERNANCE : sous la méthode interne « {method} », "
            f"l'évaluation d'un modèle RECOMMANDE la stratégie de résolution "
            f"« {winner} » — une STRATÉGIE recommandée, PAS un argument "
            "classé : ne la présente jamais comme « l'argument arrivé en "
            "tête » ni comme un vote. "
        )
    elif kind == "mediation":
        lead = (
            f"  - GOUVERNANCE : les conflits ont été résolus par une "
            f"MÉDIATION de type « {winner} » — une résolution de conflit, "
            "PAS un vote et pas un argument classé. "
        )
    elif winner_text:
        desig_arg = (
            f"désigné par {origin}{' (' + note + ')' if note else ''}"
            if origin is not None
            else "retenu par la gouvernance (origine non enregistrée)"
        )
        lead = (
            f"  - GOUVERNANCE : sous la méthode interne « {method} », "
            f"l'argument {desig_arg} est celui qui dit : « {winner_text} ». "
            "Présente-le par ce qu'il dit (paraphrase fidèle), ne recopie NI "
            "un identifiant technique brut NI le nom de méthode snake_case. "
        )
    else:
        desig_option = (
            f"désignée par {origin}{' (' + note + ')' if note else ''}"
            if origin is not None
            else "retenue par la gouvernance (origine non enregistrée)"
        )
        lead = (
            f"  - GOUVERNANCE : sous la méthode interne « {method} », "
            f"l'option d'identifiant interne « {winner} » a été "
            f"{desig_option}. DÉCRIS cette option par son RÔLE dans la "
            "prose (p.ex. « l'argument arrivé en tête »), ne recopie PAS "
            "l'identifiant technique brut ni le nom de méthode snake_case. "
        )
    if kind == "vote":
        band = qualitative_support_band(
            support_by_option.get(str(winner).strip()) if support_by_option else None,
            n_methods_decided,
            winner_basis,
        )
        if band:
            lead += (
                f"Le soutien de ce verdict : {band}. Rends ce soutien de "
                "façon QUALITATIVE (comme cette phrase le fait) — jamais "
                "sous forme de compteur ni de badge."
            )
    return warning, lead + tail


def cited_unit_ids(state: Any) -> Set[str]:
    """Ids of the units a writer is asked to DISCUSS (#2967 Expected 2).

    Three populations, all opaque ``arg_N`` ids already in the state:
    attack targets (a fallacy names its ``target_argument_id``),
    counter-argument targets (``target_arg_id``), and the governance
    winner. On doc_A the ranked-salience items overlap these three
    populations (issue #2965's measured table); #2965's Act III slice
    extends this set when it wires the excerpts to the citations.
    """
    ids: Set[str] = set()
    fallacies = getattr(state, "identified_fallacies", None)
    if isinstance(fallacies, dict):
        for fdata in fallacies.values():
            if isinstance(fdata, dict):
                tid = str(fdata.get("target_argument_id") or "").strip()
                if tid:
                    ids.add(tid)
    counters = getattr(state, "counter_arguments", None)
    if isinstance(counters, list):
        for ca in counters:
            if isinstance(ca, dict):
                tid = str(ca.get("target_arg_id") or "").strip()
                if tid:
                    ids.add(tid)
    winner = governance_winner_id(state)
    if winner:
        ids.add(winner)
    return ids
