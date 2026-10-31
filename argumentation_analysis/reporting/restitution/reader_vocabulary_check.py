r"""Deterministic post-render vocabulary check of the reader surface (#1914, c. 1+7).

Third consumer of the rendered body, beside
:func:`~.factual_consistency_check.check_factual_consistency` (formal-verdict
theatre) and :func:`~.surplus_grounding_check.check_surplus_grounding`
(ungrounded surplus claims). This one holds the two criteria of the issue
that share one shape — a vocabulary that must LEAVE the reader surface
while SURVIVING in the folded appendix (criterion 6 requires exactly that
survival):

* **criterion 1** — reader-facing acts carry no issue numbers, internal
  spec references, raw Python/JSON dictionaries or gate self-diagnostics;
* **criterion 7** — raw specialist badges cannot leak into the acts while
  remaining present in the appendix.

## The measured map this builds on (see the issue, dispatch R1030)

One family parameterized by token classes, NOT one instrument per
criterion. Each class below is a DISCOVERED gap — the occupied ground
stays where it is: the readability gate keeps its machinery family
(``acceptés [`` brackets, ``extension X :`` enumerations, ``word(s)``
morphology, ``→``, dotted taxonomy codes, scored bare refs), the eight
producer guards keep guarding the prompt, and the folded gate block is
already held by ``test_reader_surface_gate_block_1914``.

The check scans the **body only** — the assembled acts, never the folded
appendix. That boundary IS the ± pair's appendix half: the same tokens
that FAIL on the reader surface are contractual material inside the fold
(specialist inventories, counters, taxonomy IDs, protocol details — the
issue's Appendix section). A detector widened to bite the appendix would
have turned the contract around.

## Token classes

* ``#\d{3,4}`` issue numbers — unambiguous, FAIL at first hit;
* standalone ``P1``/``P2``/``P3`` verdict-hierarchy labels — the prompt's
  own instruction vocabulary copied into prose, FAIL at first hit (#3225);
* ``social-choice`` / ``social_choice`` — the governance engine's name for
  the vote, however spelled; the reader-facing vote is « le vote de la
  délibération », FAIL at first hit (#3238);
* snake_case virtue identifiers (``refutation_constructive``,
  ``redondance_faible``, « clarte »…) — the quality engine's 8 spellings
  whose French display differs; the verdict names each virtue in the
  reader's French, FAIL at first hit (#3244);
* a « … » span carrying the code-written verdict shape (« Le discours
  tient sur … k/m arguments évalués … ») — the pre-calculated verdict's
  own delimiters copied into the render; the shape is pinned to the
  builder's lead plus its machine figures, so a quoted corpus line never
  matches, FAIL at first hit (#3319);
* « confiance »/« confidence » + a 0,x decimal on one line — the
  detector's raw evidence figure copied into prose (« confiance de
  détection de 0,6 »); the standing travels in words only (provisoire /
  moyenne / ferme), FAIL at first hit (#3248);
* ``spec §`` / ``§\d`` internal spec pointers — unambiguous, FAIL;
* serialized dict literals ``{"key": …}`` — unambiguous in French prose,
  FAIL;
* gate self-diagnostic echoes (« gate lisibilité », « non truqué »,
  « contrôles structurels », self-check) — the block is folded; an echo
  in an act is the LLM reciting the machinery, FAIL;
* score-less specialist badges (« Verdict FOL : théorie inconsistante »,
  « PL : 3 inférences inconsistantes ») — the line-lead axis token + colon
  shape. WARN at 1–2 (residual), FAIL at ≥3 (manifest enumeration) — same
  banding as the gate's bare-ref and taxonomy-code families. A WOVEN
  sentence (« le solveur Tweety confirme… ») does not match: the shape,
  not the framework mention, is the defect (the #2046 scope guard).
"""

from __future__ import annotations

import re
from typing import List

from .fr_accord import accord
from .readability_gate import GateVerdict

# --- the token classes ---------------------------------------------------------

# #NNNN issue numbers. The lookbehind keeps identifiers (``arg_#1``) and the
# heading fence (``###`` followed by a space) out; 3-4 digits matches this
# repo's issue range without matching colours (#FFF) or short refs (#12).
_ISSUE_NUMBER_RE = re.compile(r"(?<![0-9A-Za-z_])#\d{3,4}\b")

# #3225 — the verdict-hierarchy labels the Act III prompt instructs by
# (« les P1 d'abord »): the writer copies prompt tokens, and the reader
# cannot resolve the label (which P1? defined where?). Standalone tokens
# only — ``P10`` and ``arg_P1`` belong to other vocabularies and stay out,
# and the appendix's premise numbering is out of scope with the fold.
_HIERARCHY_LABEL_RE = re.compile(r"(?<![0-9A-Za-z_])P[123](?![0-9A-Za-z_])")

# #3238 — the governance machinery's own name for the vote:
# ``governance_origin`` used to return « le vote social-choice » as the
# origin label of a ``vote_aggregate`` winner, and the writer copied the
# prompt token (R1110c: « Le vote social-choice désigne lui aussi cette
# réponse… »). Both spellings are machinery on the reader surface — the
# hyphenated label and the internal snake_case method name
# (``method = "social_choice"``, measured ×15 on the stored corpus). The
# method name stays in the state and on the prompt's data side by design
# (both acts' consignes forbid copying it by name); this class holds the
# reader surface. Letter-bounded both sides, the P[123] precedent — the
# French words that share letters (« climat social », « le choix ») never
# match: the regex needs the English « choice » right after the join.
_METHOD_TOKEN_RE = re.compile(
    r"(?<![0-9A-Za-z_-])social[-_]choice(?![0-9A-Za-z_-])", re.IGNORECASE
)

# #3244 — the quality engine's virtue identifiers. The pre-calculated
# verdict used to interpolate them raw (« Le discours tient sur … ;
# refutation_constructive (…) ; redondance_faible (…) », R1111a; « clarte »,
# R1110b) and the writer is instructed to copy that sentence verbatim. The
# 8 spellings whose display name differs: the 6 snake_case compounds and
# the 2 accent-stripped singles. ``pertinence`` is excluded by construction
# — its display name IS the French word, so flagging it would be a false
# positive by definition. Letter-bounded both sides: the accented display
# words (« clarté », « exhaustivité », measured on 59 of 144 stored bodies)
# never match, and internal key shapes (``argument_quality_scores``) stay
# out. The data side keeps the ids by design (#3238 precedent).
_VIRTUE_ID_RE = re.compile(
    r"(?<![0-9A-Za-z_])(?:refutation_constructive|redondance_faible|"
    r"analogie_pertinente|fiabilite_sources|presence_sources|"
    r"structure_logique|clarte|exhaustivite)(?![0-9A-Za-z_])"
)

# #3319 — the pre-calculated verdict's own delimiters on the reader
# surface. The producer used to interpolate the verdict between « » and
# the writer, instructed to copy the sentence, copied the quotes with it
# (2 renders on the coordinator's saved corpus, R1129 dispatch). The
# shape is pinned to what only the builder writes: the opening «, the
# sentence lead ``discourse_virtue_sentence`` composes (« Le discours
# tient sur ») and its machine figures (``k/m arguments évalués``) — a
# corpus sentence cannot carry them, so nothing a speaker said can match.
# A quoted corpus line (« Le discours est dense. ») lacks the shape and
# stays out. Zero carriers on this seat's 1016 stored reader texts; the
# population witness turns the measurement into the property (#3244
# precedent — the carriers live on the coordinator's corpus).
_QUOTED_VERDICT_RE = re.compile(
    r"«\s*Le discours tient sur[^»]*?\d+\s*/\s*\d+\s+arguments\s+évalués[^»]*?»"
)

# #3248 — the detector's raw decimal confidence, evidence vocabulary copied
# onto the reader surface: the fallacy evidence lines print the figure
# (« confiance du détecteur : 0,4 », fallacy_attribution.detector_confidence_
# note) and the R1113a writer copied it into the narrative (« avec une
# confiance de détection de 0,6 à 0,7 ») while the same render said the
# standing in words three pages earlier — both vocabularies live in one
# render and the reader cannot weigh a « 0,6 ». BOTH tokens must sit on the
# same line: « confiance » with no figure is the #3231 ladder doing its
# job, and a bare decimal belongs to other families. The ladder words
# (provisoire, moyenne, ferme) never carry a 0,x — they cannot match.
_CONFIDENCE_WORD_RE = re.compile(r"confiance|confidence", re.IGNORECASE)
_DECIMAL_ZERO_RE = re.compile(r"\b0[.,]\d")

# Internal spec pointers, both spellings the fixed surfaces carried.
_SPEC_REF_RE = re.compile(r"\bspec\s*§|§\s*\d")

# A serialized dict opening: quoted key + colon. Nothing legitimate in
# French narrative prose matches this shape.
_DICT_LITERAL_RE = re.compile(r"\{\s*[\"'][\w.\- ]+[\"']\s*:")

# Gate self-diagnostic vocabulary. The verdict block itself is folded
# (#2086); these tokens surviving in an ACT are the LLM echoing the
# machinery it was told stays behind the curtain.
_GATE_ECHO_TOKENS = (
    "gate lisibilité",
    "non truqué",
    "contrôles structurels",
    "self-check",
    "autocontr",
)

# A raw specialist badge: the line LEADS with the axis/solver token
# (optionally after a list bullet or the word « verdict »), then a colon.
# « Verdict FOL : théorie inconsistante » — the exact shape the R1029
# probe measured invisible to the scored bare-ref detector, at any dose.
# A woven sentence never matches: the axis has to lead the line for this
# to be an enumeration entry, not prose.
_BARE_BADGE_RE = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:verdict\s+)?(?:pl|fol|modal|modale|tweety|dung|aspic)\s*[:：]\s*\S",
    re.IGNORECASE | re.MULTILINE,
)

_BADGE_WARN_THRESHOLD = 2  # 1–2 residual badges → WARN (gate-family precedent)
_BADGE_FAIL_THRESHOLD = 3  # ≥3 → FAIL (manifest enumeration)


def _lines(body: str) -> List[str]:
    return [line for line in body.splitlines() if line.strip()]


def check_reader_vocabulary(body: str) -> GateVerdict:
    """Deterministic post-render check of the reader-surface vocabulary.

    Args:
        body: the rendered narrative body (the 3 acts, excluding the folded
            appendix) — the surface the criteria govern. The appendix is
            deliberately out of scope: its carrying these tokens is the
            contract (criterion 6), not a violation.

    Returns:
        A :class:`~.readability_gate.GateVerdict` — ``FAIL`` when an
        unambiguous internal token (issue number, spec pointer, dict
        literal, gate echo) reaches the reader surface, or when bare
        specialist badges enumerate (≥3); ``WARN`` for 1–2 residual
        badges; ``PASS`` on a clean surface. Reasons are per-class,
        counted, with a first-hit preview — auditable, mergeable.
    """
    reasons: List[str] = []
    worst = "PASS"

    issue_hits = list(_ISSUE_NUMBER_RE.finditer(body))
    if issue_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(issue_hits), 'numéro d', 'numéros d')}"
            f"'issue sur la surface lecteur (ex : "
            f"{issue_hits[0].group(0)}). Les références "
            f"d'issue n'appartiennent pas au récit."
        )

    hierarchy_hits = list(_HIERARCHY_LABEL_RE.finditer(body))
    if hierarchy_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#3225) — "
            f"{accord(len(hierarchy_hits), 'étiquette de hiérarchie P', 'étiquettes de hiérarchie P')} "
            f"sur la surface lecteur (ex : {hierarchy_hits[0].group(0)}). "
            f"P1/P2/P3 sont le vocabulaire du prompt : le récit traduit la "
            f"hiérarchie, il ne la recopie pas."
        )

    method_hits = list(_METHOD_TOKEN_RE.finditer(body))
    if method_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#3238) — "
            f"{accord(len(method_hits), 'nom interne de la méthode de vote', 'noms internes de la méthode de vote')} "
            f"sur la surface lecteur (ex : « {method_hits[0].group(0)} »). "
            f"Le vote se nomme en français (« le vote de la délibération ») ; "
            f"« social-choice »/« social_choice » est le vocabulaire du "
            f"moteur, pas du récit."
        )

    virtue_hits = list(_VIRTUE_ID_RE.finditer(body))
    if virtue_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#3244) — "
            f"{accord(len(virtue_hits), 'identifiant interne de vertu', 'identifiants internes de vertu')} "
            f"sur la surface lecteur (ex : « {virtue_hits[0].group(0)} »). "
            f"Chaque vertu se nomme en français dans le récit (« réfutation "
            f"constructive », « faible redondance », « clarté »…) ; "
            f"l'identifiant snake_case est le vocabulaire du moteur qualité."
        )

    quoted_verdict_hits = list(_QUOTED_VERDICT_RE.finditer(body))
    if quoted_verdict_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#3319) — "
            f"{accord(len(quoted_verdict_hits), 'verdict pré-calculé imprimé entre guillemets', 'verdicts pré-calculés imprimés entre guillemets')} "
            f"sur la surface lecteur (ex : « "
            f"{quoted_verdict_hits[0].group(0)[:80]}… »). Le verdict "
            f"pré-calculé se recopie mot pour mot, délimiteurs exclus : "
            f"les guillemets sont ceux du prompt, pas du récit."
        )

    spec_hits = list(_SPEC_REF_RE.finditer(body))
    if spec_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(spec_hits), 'référence de spec interne', 'références de spec internes')} "
            f"sur la surface lecteur (ex : "
            f"{spec_hits[0].group(0)}). Le récit cite ses "
            f"preuves, pas la spécification qui l'a produit."
        )

    dict_hits = list(_DICT_LITERAL_RE.finditer(body))
    if dict_hits:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(dict_hits), 'dictionnaire brut sérialisé', 'dictionnaires bruts sérialisés')} "
            f"dans le récit (ex : « "
            f"{dict_hits[0].group(0)}… »). Les données "
            f"appartiennent à l'annexe repliée."
        )

    gate_echoes = [
        line.strip()
        for line in _lines(body)
        if any(token in line.lower() for token in _GATE_ECHO_TOKENS)
    ]
    if gate_echoes:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#1914, c.1) — "
            f"{accord(len(gate_echoes), 'écho du diagnostic de gate', 'échos du diagnostic de gate')} "
            f"dans le récit (ex : « {gate_echoes[0][:100]} »). Le gate "
            f"parle dans le pli, jamais dans l'acte."
        )

    confidence_lines = [
        line.strip()
        for line in _lines(body)
        if _CONFIDENCE_WORD_RE.search(line) and _DECIMAL_ZERO_RE.search(line)
    ]
    if confidence_lines:
        worst = "FAIL"
        reasons.append(
            f"Vocabulaire interne (#3248) — "
            f"{accord(len(confidence_lines), 'ligne portant la confiance chiffrée du détecteur', 'lignes portant la confiance chiffrée du détecteur')} "
            f"sur la surface lecteur (ex : « {confidence_lines[0][:100]} »). "
            f"Le standing d'une détection se dit en mots (provisoire, "
            f"moyenne, ferme) ; le chiffre du détecteur reste du côté des "
            f"preuves."
        )

    badges = [line.strip() for line in _lines(body) if _BARE_BADGE_RE.match(line)]
    if len(badges) >= _BADGE_FAIL_THRESHOLD:
        worst = "FAIL"
    elif badges and worst == "PASS":
        worst = "WARN"
    if badges:
        reasons.append(
            f"Badge de spécialiste brut (#1914, c.7) — "
            f"{accord(len(badges), 'ligne mène par le nom d', 'lignes mènent par le nom d')}"
            f"'axe puis deux-points (ex : « {badges[0][:100]} »). Le "
            f"verdict formel se tisse dans la prose, il ne s'énumère pas ; "
            f"l'inventaire exhaustif vit en annexe."
        )

    if not reasons:
        return GateVerdict(band="PASS")
    return GateVerdict(band=worst, reasons=reasons)
