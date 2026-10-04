"""Deterministic post-render checks of the reader contract on the acts
(#1914, criteria 2, 3 and 4 — dispatch R1059, rework R1060).

The producer side of these three criteria is held at the prompt + evidence
level (the derivation consigne, the device-function consigne, the salience
ranker — pinned by ``test_formal_derivation_channel_1914``,
``test_rhetorical_device_channel_1914`` and ``test_conclusion_salience_1914``).
The card (c.5969933470) measured the shared gap: NO test reads a rendered
act, and the coordinator's paid render of 01/10 showed the exact defect
(fallacy labels piling instead of naming what a reader recognizes).

These three controls are the mechanical half of the closure. Each is a PURE
function ``act text -> findings`` (with positions), in the family of
:func:`~.surplus_grounding_check.check_surplus_grounding` and
:func:`~.reader_vocabulary_check.check_reader_vocabulary`, with one
contractual difference (dispatch R1059): **the findings are diagnostics for
the folded appendix — the control never modifies an act and never fails a
render.** The prose is a model output: one degrades in the state, one does
not raise. There is therefore NO ``GateVerdict`` here — findings ride into
the appendix as their own audit section.

R1060 rework (review c.5974319482): the first calibration read saturation as
a property of the pre-tranche corpus; measured on a post-tranche render the
instrument itself saturated (~2/13 true). Every lexicon entry below is now
TAKEN FROM THE PRODUCER and cited where it is used — the Act II/III consignes
(``act2_narrative_plugin`` / ``act3_conclusion_plugin``), the ranker cap
(:mod:`.conclusion_salience`), the Dung frame vocabulary
(:mod:`.dung_reader`) and the nine quality virtues
(:mod:`...agents.core.quality.quality_evaluator`) — never fitted to the
calibration corpus. The structural guards (negation scope, judgment step,
withdrawal, discourse-quote introduction, meta-axis enumeration, heading
lines) remove the false-positive classes the review named. One residual
class is documented, not solved: a function stated with a FREE verb outside
any lexicon (« associent », « laisse », « transforme ») — see
``_FUNCTION_RE``; criterion 3 ships as a measured-weak diagnostic for that
shape, and the calibration says so.

What each control reads:

* **criterion 2** — a sentence citing a formal result (solver name, axis
  badge, refutation/inconsistency verdict — the QUALITY VIRTUES are not
  citations) must carry, in the SAME sentence, what was tested and what it
  changes. The honest absence (« contenu testé non disponible », « compteur
  seul ») is compliant: naming the missing derivation is the contract, not
  a violation.
* **criterion 3** — a sentence carrying a device/fallacy label cue without
  any function marker: the piling-labels shape the paid render measured.
  The consigne's second step (judging whether the device weakens the
  reasoning) and the honest withdrawal of labels are compliant — a sentence
  that judges or withdraws is not a pile.
* **criterion 4** — the Act III ranked shape: a ranking marker must be
  present (the consigne's own order vocabulary — « les P1 d'abord », «
  l'argument arrivé en tête », « dans cet ordre »), and label-cue mentions
  must not exceed the ranker's own structural cap (5,
  :func:`.conclusion_salience` — a cap taken from the producer, never tuned
  against the calibration corpus).

A body with NO act heading yields one explicit ``not_evaluated`` finding
(criterion 0): a zero must say whether it was evaluated (R1060, silent
zeros).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

# -- finding -----------------------------------------------------------------


@dataclass(frozen=True)
class ContractFinding:
    """One reader-contract observation on a rendered act — a diagnostic for
    the appendix, never a render failure."""

    criterion: int  # 2, 3, 4 — or 0 (envelope: not-evaluated, not a defect)
    kind: str  # machine-readable shape, e.g. "formal_citation_without_change"
    act: str  # "Acte II" / "Acte III" (the act the sentence lives in)
    line: int  # 1-based line in the rendered body
    excerpt: str  # <= 120 chars of the offending sentence, audit-side only
    note: str  # what the finding means, in reader language


# -- act splitting -----------------------------------------------------------

# Case-insensitive: a real seat render writes « ## ACTE I — » (uppercase).
# The label is canonicalised to « Acte N » whatever the source casing.
_ACT_HEADING_RE = re.compile(r"^## Acte (I|II|III)\b.*$", re.MULTILINE | re.IGNORECASE)


def _split_acts(body: str) -> List[Tuple[str, str, int]]:
    """(``Acte N``, act text, 0-based body line of the heading) triples, in
    document order, case-insensitive on the heading. The preamble before
    Acte I is dropped (it is not an act). The heading's own line offset
    makes every finding's line number absolute in the rendered body."""
    matches = list(_ACT_HEADING_RE.finditer(body))
    acts: List[Tuple[str, str, int]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        first_line = body.count("\n", 0, start)
        acts.append((f"Acte {m.group(1).upper()}", body[start:end], first_line))
    return acts


# -- sentences ---------------------------------------------------------------

# A French sentence ends at . ! ? … (a colon introduces the elaboration of
# the SAME sentence — « ... : ce que ça change » is one sentence).
_SENTENCE_END_RE = re.compile(r"[.!?…]")

# French LLM prose writes the typographic apostrophe (U+2019); markers store
# the straight one — normalise before matching (#2032 lesson).
_APOSTROPHE = ("’", "'")


def _sentences_with_lines(act_text: str, act_offset: int) -> List[Tuple[str, int]]:
    """(sentence, 1-based body line of its first char) for every sentence in
    the act. ``act_offset`` is the 0-based line of the act's first line.
    Markdown heading lines (``###`` subsection titles) are NOT prose — a
    heading naming a movement (« ### Le mouvement « sophisme d'origine » »)
    is structure, not a piling sentence (R1060)."""
    out: List[Tuple[str, int]] = []
    for rel_line, raw in enumerate(act_text.splitlines()):
        if raw.lstrip().startswith("#"):
            continue
        line = raw.replace(*_APOSTROPHE)
        for part in _SENTENCE_END_RE.split(line):
            stripped = part.strip()
            if stripped:
                out.append((stripped, act_offset + rel_line + 1))
    return out


def _excerpt(sentence: str) -> str:
    return sentence if len(sentence) <= 120 else sentence[:117] + "…"


# -- shared guards (R1060 false-positive classes) ------------------------------

# The nine quality virtues (``agents/core/quality/quality_evaluator.py``)
# are NOT formal citations: « réfutation constructive » (and its snake_case
# leak ``refutation_constructive``) is a virtue name, not a Tweety verdict.
# Both spellings are neutralised before the citation match.
_VIRTUE_TOKEN_RE = re.compile(
    r"refutation_constructive|r[ée]futation constructive"
    r"|analogie_pertinente|analogie pertinente"
    r"|presence_sources|pr[ée]sence de sources"
    r"|fiabilite_sources|fiabilit[ée] de[s]? sources"
    r"|structure_logique|structure logique"
    r"|redondance_faible|redondance faible"
    r"|\bclart[ée]\b|\bpertinence\b|\bexhaustivit[ée]\b",
    re.IGNORECASE,
)

# The pipeline's own analysis dimensions, as the appendix axis table names
# them (English keys) and the acts name them in French. A sentence
# enumerating several of them is describing the ANALYSIS, not labelling the
# discourse (R1060 meta class: « l'analyse croise sophismes, qualité,
# contre-arguments »). Solver names are deliberately absent — a derivation
# sentence cites one solver, and must stay under the controls.
_AXIS_NAME_RES = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"sophismes?\b|fallacies\b|fallacie",
        r"qualit[ée]\b|quality\b",
        r"contre-arguments?\b|counter_?arguments?\b",
        r"gouvernance\b|governance\b",
        r"d[ée]bats?\b|debate\b",
        r"extraction\b",
        r"synth[èe]se\b|synthesis\b",
        r"indexation\b",
        r"fact.?check",
        r"v[ée]rifications? formelles?\b|formal_",
        r"logique (?:propositionnelle|modale|formelle)",
        r"\bjtms\b",
    )
]

# Analysis-actor words: with >= 2 axis names they confirm the meta reading.
_ANALYSIS_ACTOR_RE = re.compile(
    r"l'analyse|analyse couvre|ce rapport|la restitution|les axes|dimensions"
    r"|en regard|la machinerie|le diagnostic|ce diagnostic|l'[ée]valuation"
    r"|ce run|m[ée]thodes ind[ée]pendantes",
    re.IGNORECASE,
)


def _is_meta_sentence(norm: str) -> bool:
    """True when the sentence enumerates the analysis's own dimensions
    rather than labelling the discourse. >= 3 distinct axis names is meta
    on its own; 2 needs an analysis-actor word."""
    names = sum(1 for rx in _AXIS_NAME_RES if rx.search(norm))
    if names >= 3:
        return True
    return names >= 2 and bool(_ANALYSIS_ACTOR_RE.search(norm))


# -- criterion 2: formal citation without derivation --------------------------

# A sentence CITES a formal result through a solver name, an axis badge or a
# formal verdict word. The bracket forms are the raw badge shapes the real
# renders carry (« [pl] 3 inférence(s) PL consistantes — ancrage : solveur
# Tweety »). Runs on the virtue-stripped sentence (see _VIRTUE_TOKEN_RE).
_FORMAL_CITATION_RE = re.compile(
    r"\[\s*(?:pl|fol|modal)\s*\]|\bsolveurs?\b|tweety|spass|\bdung\b|aspic"
    r"|\br[ée]fut(?:ée?|ion)\b|inconsistante?\b|\br[ée]fut[ée]es?\b",
    re.IGNORECASE,
)

# The derivation halves. The BADGE's counting shapes (« 3 inférence(s) », «
# 1 théorie(s) FOL », « 2 vérifiée(s) » — produced by formal_derivation.py)
# are stripped BEFORE the tested match: a count is not a tested proposition.
# What survives in PROSE is a tested marker: « inférence », « théorie »,
# « argument », « revendication » and « position » — the Act III consigne's
# own derivation formula is « le cadre d'argumentation isole cette
# REVENDICATION comme rejetée », the Dung frame's arguments are POSITION
# texts (dung_reader: « chaque position »), and an enumerated arg_N is the
# tested unit (consigne: « N retenus sur M unités argumentatives
# identifiées »).
_BADGE_COUNT_RE = re.compile(
    r"\d+\s+inf[ée]rences?\(s\)|inf[ée]rence\(s\)|\d+\s+th[ée]ories?\(s\)"
    r"|th[ée]orie\(s\)|\d+\s+v[ée]rifi[ée]e?s?\(s\)|v[ée]rifi[ée]e?\(s\)"
    r"|\d+\s+retenue?s?\(s\)|retenu\(s\)|\d+\s+rejet[ée]e?s?\(s\)|rejet[ée]e?\(s\)"
    r"|\d+\s+relations? d'attaque",
    re.IGNORECASE,
)
_TESTED_RE = re.compile(
    r"test[ée]|\b[àa] l'[ée]preuve\b|proposition|clause|pr[ée]dicat|atome"
    r"|formule|revendication|position\b|\barg_\d+\b|inf[ée]rence|th[ée]orie"
    r"|\barguments?\b|affirmation|assertion",
    re.IGNORECASE,
)
# The change half, extended with the consigne's own derivation wording: «
# isole ... comme rejetée » / isolated-as-defeated is what the formal frame
# CHANGES for the judgment (act3 consigne formula, cited above), « ce qui
# AFFAIBLIT les revendications » is the Act III consigne's own name for its
# counter-points block, and « l'analyse formelle CONFIRME la cohérence de ce
# raisonnement » is its consistency-verdict formula.
_CHANGE_RE = re.compile(
    r"chang|fragilis|remet en cause|oblige|reconsid|[ée]pend\b|montre|r[ée]v[èe]le"
    r"|signifi|impliqu|entra[îi]n|renfor[çc]|condamn|[ée]tablit|juge|affaibl"
    r"|confirm|isol(?:e|ent|[ée]e?s?) comme|comme (?:rejet[ée]e?s?|d[ée]faillantes?)"
    r"|\brejet[ée]e?s?\b|\bd[ée]faillante?s?\b",
    re.IGNORECASE,
)

# The honest-absence wording the Act II evidence itself carries for a
# placeholder-only record — naming the missing derivation is compliant.
_HONTEST_ABSENCE_RE = re.compile(r"non disponible|compteur seul", re.IGNORECASE)


def _formal_findings(acts: List[Tuple[str, str, int]]) -> List[ContractFinding]:
    findings: List[ContractFinding] = []
    for label, text, first_line in acts:
        if label == "Acte I":
            continue  # situation act: no formal citation is expected there
        for sentence, line in _sentences_with_lines(text, first_line):
            norm = sentence.lower()
            if not _FORMAL_CITATION_RE.search(_VIRTUE_TOKEN_RE.sub(" ", norm)):
                continue
            if _is_meta_sentence(norm):
                continue
            if _HONTEST_ABSENCE_RE.search(norm):
                continue
            has_tested = bool(_TESTED_RE.search(_BADGE_COUNT_RE.sub(" ", norm)))
            has_change = bool(_CHANGE_RE.search(norm))
            if has_tested and has_change:
                continue
            kind = (
                "formal_citation_without_derivation"
                if not has_tested and not has_change
                else (
                    "formal_citation_without_tested"
                    if not has_tested
                    else "formal_citation_without_change"
                )
            )
            missing = (
                "ni ce qui a été testé ni ce que ça change"
                if not has_tested and not has_change
                else (
                    "ce qui a été testé"
                    if not has_tested
                    else "ce que ça change pour le jugement"
                )
            )
            findings.append(
                ContractFinding(
                    criterion=2,
                    kind=kind,
                    act=label,
                    line=line,
                    excerpt=_excerpt(sentence),
                    note=f"citation formelle sans {missing} dans la même phrase "
                    f"(critère 2 — le lecteur reçoit un badge, pas une dérivation)",
                )
            )
    return findings


# -- criterion 3: label without function --------------------------------------

# A sentence carries a LABEL cue (the defect taxonomy vocabulary) or piles
# quoted LABELS; a FUNCTION marker is what the device accomplishes. The
# function lexicon is the Act II consigne's own wording: « dis d'abord CE
# QU'IL ACCOMPLIT dans le discours — ce que le locuteur CHERCHE À OBTENIR
# par lui ; la justification le porte le plus souvent (« VISANT À… », «
# POUR LÉGITIMER… ») » (#2060).
_LABEL_CUE_RE = re.compile(
    r"sophisme|proc[ée]d[ée]|figure de style|fallacie|paralogisme",
    re.IGNORECASE,
)
_FUNCTION_RE = re.compile(
    r"accomplit|visant|vise [àa]|cherche [àa] obtenir|afin de|en vue de"
    r"|de sorte [àa]|l[ée]gitim|cr[ée]e|cr[ée]dibilis|installe|instaur"
    r"|permet de|rassure|s[ée]duit|endoctrin|d[ée]responsabilis|fonction",
    re.IGNORECASE,
)

# The consigne's SECOND step is itself a function-bearing shape: « PUIS JUGE
# s'il FRAGILISE le raisonnement : ... une figure (ce qui fait avancer le
# discours) avec une faute (ce qui le CASSE) » — a sentence that judges,
# withdraws or denies establishment is compliant (R1060: judgment-of-device
# and withdrawal classes). Honest withdrawal: « ne sont pas établies ».
_JUDGMENT_RE = re.compile(
    r"\bjuge\b|jug[ée]e?|fragilis|casse|adouc|suffit pas|suffisent pas"
    r"|pas suffisan|ne tient pas|tiennent pas|pas [ée]tabli|non [ée]tabli"
    r"|d[ée]montre|ne prouve|peu d'appui|sans appui|pas des preuves"
    r"|pas une preuve|pas des preuves juridiques|garde son verdict"
    r"|[ée]tablit une faute|ne d[ée]montre",
    re.IGNORECASE,
)

# Negation scope (R1060: « sans procédé identifiable » / « sans tomber dans
# un sophisme localisé » / « ne déclenchent pas de sophisme »): a cue under
# a negation DENIES a device — it is not a label.
_NEGATION_BEFORE_RE = re.compile(
    r"(?:\bsans\b|\baucun(?:e)?\b|\bpas de\b|\bni \b|\bnul\b|\bexempt\b)"
    r"[^.!?»]{0,45}$"
    r"|\bne\b[^.!?»]{0,35}\b(?:pas|jamais|plus|rien)\b[^.!?»]{0,45}$",
    re.IGNORECASE,
)


def _cue_is_negated(norm: str, cue: "re.Match[str]") -> bool:
    return bool(_NEGATION_BEFORE_RE.search(norm, 0, cue.start()))


# A quoted segment counts toward the piling shape only when it is a DEVICE
# LABEL. Quotes introduced by a discourse verb are CITATIONS OF WHAT WAS
# SAID (Act II consigne: « L'argument ... AFFIRME QUE » ; Act III: « CITE ce
# qui a réellement été dit ») — the discourse quoting the acts are asked to
# weave. The introduction window is the 60 chars before the opening «.
# A sentence whose SUBJECT is the discourse itself (le discours présente,
# l'argument prétend, le texte oppose) is citing discourse throughout: none
# of its quotes count toward a label pile.
_DISCOURSE_INTRO_RE = re.compile(
    r"affirme|soutient|pr[ée]tend|d[ée]clare|pr[ée]sente|annonc|cite|cit[ée]e?"
    r"|revendication|proclamation|remarque|termes?|mot\b|slogan|appel[ée]e?"
    r"|nomm[ée]e?|surnomm|sous-titre|titre",
    re.IGNORECASE,
)
_DISCOURSE_SUBJECT_RE = re.compile(
    r"le discours|le locuteur|l'orateur|l'auteur\b|le texte\b|l'argument \w+"
    r"|l'affirmation selon|les formulations|les propositions|les all[ée]gations",
    re.IGNORECASE,
)
_QUOTED_SEGMENT_RE = re.compile(r"«\s*([^»]{2,60})\s*»")

# Reader guidance (Act III consigne, third beat: « ce que le lecteur doit
# recevoir avec prudence, ce qui est solide »): a sentence addressing the
# reader with an imperative prudence verb is the asked-for guidance shape,
# not a label pile.
_READER_IMPERATIVE_RE = re.compile(
    r"\b(recevez|prenez|demandez|contr[ôo]lez|v[ée]rifiez|jugez|attendez"
    r"|m[ée]fiez|gardez|comparez|m[ée]rite)\b",
    re.IGNORECASE,
)


def _label_quotes(sentence: str) -> int:
    """Quoted segments that are device labels (not discourse citations)."""
    if _DISCOURSE_SUBJECT_RE.search(sentence):
        return 0
    n = 0
    for m in _QUOTED_SEGMENT_RE.finditer(sentence):
        window = sentence[max(0, m.start() - 60) : m.start()]
        if not _DISCOURSE_INTRO_RE.search(window):
            n += 1
    return n


def _label_findings(acts: List[Tuple[str, str, int]]) -> List[ContractFinding]:
    findings: List[ContractFinding] = []
    for label, text, first_line in acts:
        if label == "Acte I":
            continue
        for sentence, line in _sentences_with_lines(text, first_line):
            norm = sentence.lower()
            cue = _LABEL_CUE_RE.search(norm)
            quoted = _label_quotes(sentence)
            if not cue and quoted < 2:
                continue
            if cue is not None and _cue_is_negated(norm, cue):
                continue  # the cue is denied, not asserted
            if _FUNCTION_RE.search(norm):
                continue
            if _JUDGMENT_RE.search(norm):
                continue  # consigne step 2 or honest withdrawal
            if _READER_IMPERATIVE_RE.search(norm):
                continue  # Act III beat 3: the asked-for reader guidance
            if _is_meta_sentence(norm):
                continue
            findings.append(
                ContractFinding(
                    criterion=3,
                    kind="label_without_function",
                    act=label,
                    line=line,
                    excerpt=_excerpt(sentence),
                    note="étiquette de procédé/sophisme sans ce qu'il accomplit "
                    "dans la même phrase (critère 3 — une étiquette ne dit pas "
                    "ce qu'un lecteur reconnaît)",
                )
            )
    return findings


# -- criterion 4: Act III ranked shape ----------------------------------------

# A ranking marker: the producer's own hierarchy vocabulary — P1/P2/P3 from
# conclusion_salience — and the Act III consigne's ORDER wording: « fonde le
# deuxième battement sur la HIÉRARCHIE DU VERDICT ci-dessus, dans cet ordre
# — les P1 D'ABORD » and, for the reader rendering of a P1, « l'argument
# ARRIVÉ EN TÊTE ». A P1-first hierarchy is naturally written as a
# superlative (« le plus sérieux »), which the review named as ranking too.
_RANKED_MARKER_RE = re.compile(
    r"\bP[123]\b|d[ée]cisif|d[ée]terminant|priorit|hi[ée]rarch|l'essentiel"
    r"|en premier|par ordre d'importance|d'abord|en t[êe]te|dans cet ordre"
    r"|\ble plus\b|\bla plus\b",
    re.IGNORECASE,
)

# The label-replay ceiling is the ranker's own structural cap — never tuned
# against the calibration corpus (dispatch R1059, anti-pendulum).
_RANKED_CAP = 5


def _ranked_findings(acts: List[Tuple[str, str, int]]) -> List[ContractFinding]:
    act3 = next(((l, t, o) for l, t, o in acts if l == "Acte III"), None)
    if act3 is None:
        return []  # honest skip: no Act III to judge (missing act is the
        # renderer's own loud degradation, not this check's business)
    label, text, first_line = act3
    findings: List[ContractFinding] = []
    sentences = _sentences_with_lines(text, first_line)
    if not any(_RANKED_MARKER_RE.search(s.lower()) for s, _ in sentences):
        findings.append(
            ContractFinding(
                criterion=4,
                kind="no_ranked_marker",
                act="Acte III",
                line=first_line + 1,
                excerpt="(acte entier)",
                note="aucun marqueur de hiérarchie courte dans l'Acte III "
                "(critère 4 — la priorisation doit se voir, pas se deviner)",
            )
        )
    label_sentences = sum(
        1
        for s, _ in sentences
        if _LABEL_CUE_RE.search(s.lower()) or _label_quotes(s) >= 2
    )
    if label_sentences > _RANKED_CAP:
        findings.append(
            ContractFinding(
                criterion=4,
                kind="label_replay",
                act="Acte III",
                line=first_line + 1,
                excerpt=f"{label_sentences} phrases à étiquette dans l'Acte III",
                note=f"{label_sentences} phrases portent une étiquette — au-delà "
                f"de la limite structurelle du classement ({_RANKED_CAP}, le cap "
                "du rangeur) : rejeu d'inventaire plutôt que hiérarchie "
                "(critère 4)",
            )
        )
    return findings


# -- runner -------------------------------------------------------------------


def check_act_reader_contract(body: str) -> List[ContractFinding]:
    """Run the three criteria-2/3/4 controls on a rendered body.

    Args:
        body: the rendered narrative body (the 3 acts with their ``## Acte``
            headings, any casing — the renderer's ``body`` BEFORE the folded
            appendix).

    Returns:
        Findings, each with its criterion, act, line and a short excerpt —
        diagnostics for the folded appendix. NEVER a verdict: this function
        observes, it does not judge the render (dispatch R1059). A body
        without any act heading returns ONE criterion-0 envelope finding —
        a zero must say whether it was evaluated (R1060).
    """
    # A full document (acts + folded appendix) may be handed in — the fold
    # and everything after it are appendix material, never act prose. The
    # renderer's own body carries no fold; this cut is defensive for callers
    # passing whole documents (the calibration producer does).
    acts = _split_acts(body.split("<details>")[0])
    if not acts:
        return [
            ContractFinding(
                criterion=0,
                kind="not_evaluated_no_act_heading",
                act="—",
                line=1,
                excerpt="(aucun titre d'acte)",
                note="non évalué : aucun titre d'acte dans le corps rendu — "
                "les contrôles des critères 2-4 ne s'appliquent pas",
            )
        ]
    return _formal_findings(acts) + _label_findings(acts) + _ranked_findings(acts)
