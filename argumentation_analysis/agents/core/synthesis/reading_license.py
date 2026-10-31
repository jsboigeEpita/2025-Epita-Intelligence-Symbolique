"""#3123 — what a synthesis may conclude from the artifacts it was handed.

Two misreadings were measured in the R1104 render, and both are an inference
the input never licensed:

* **breadth as robustness** — the grounded extension covered most of the
  arguments and the text called the argumentation robust, while the evaluated
  graph carried fewer attacks than arguments (edges were submitted and dropped
  before the frame was built). Breadth there measures the frame's sparsity,
  not the discourse's resistance to challenge.
* **someone else's inconsistency as the discourse's** — a theory was
  unsatisfiable between source units (``between_sources``) and the synthesis
  concluded that the discourse itself was incoherent, though no single voice
  was shown to contradict itself.
* **a check that decided nothing, sold as strength** (R1105b, Sonnet pass) —
  the FOL leg returned ``consistent`` without answering a single query; Act II
  of the same render said exactly that ("ran without distinguishing anything,
  and that is neither a strength nor a weakness") and the synthesis still
  called the discourse robust "at the level of formal consistency". A decided
  consistency with no inference behind it licenses no robustness claim; an
  entry that DID answer queries may still be cited as strength.

This module is the deterministic, non-LLM check over a PRODUCED text. It
flags; it never rewrites — the defect is the inference, and the sentence is
where a reader can see it. Every detector is a narrow phrase pattern, never a
bag of tokens, so a sentence that already carries its qualifier is not
flagged, and a negated robustness statement ("n'est pas robuste") is not a
claim at all.

No state writer is changed here: the caller stores the result beside the
value gates it already persists.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from argumentation_analysis.core.fallacy_attribution import is_reported_move  # #3180
from argumentation_analysis.utils.taxonomy_loader import (  # #3224
    DISTINCTIVE_NODE_DF_MAX,
    taxonomy_token_df,
)
from argumentation_analysis.utils.taxonomy_loader import taxonomy_chain

#: A robustness word. Read together with :data:`_BREADTH_MARKERS`: alone it is
#: an ordinary adjective, and only the *combination* makes the claim.
_ROBUSTNESS_MARKERS = re.compile(
    r"(robust\w*|robustesse|solide(?:ment)?|solidité|résiste\w*|résilien\w*|"
    r"bien étay\w*|consolid\w*)",
    re.IGNORECASE,
)

#: A breadth word. ``extension`` alone names a computed object; combined with a
#: robustness word it becomes "the extension is broad, therefore the discourse
#: is robust" — the inference #3123 removes.
_BREADTH_MARKERS = re.compile(
    r"(extension\w*|grounded|groundée\w*|couvre\w*|étendue|large\w*|"
    r"breadth|broad\w*|comprehensive)",
    re.IGNORECASE,
)

#: A discourse-level subject: the sentence speaks about the discourse as a
#: whole (or about a speaker's commitments), not about a source unit. The
#: possessive forms below are the #3123/R1105c Act II shape — "the case the
#: speaker builds does not hold together" charges a recorded cause to the
#: speaker just as the explicit subjects do.
_DISCOURSE_SUBJECTS = re.compile(
    r"(le discours|l['’]ensemble des engagements|les engagements du discours|"
    r"les engagements (?:du|d['’]un) locuteur|s[ea]s engagements|"
    r"la position (?:est|s['’]avère|se révèle|reste)|"
    r"(?:le|la) (?:cas|thèse|these|démonstration|demonstration|argumentation|"
    r"raisonnement|argumentaire|défense|defense|fil|développement|"
    r"developpement) (?:que|qu['’]|de |du |d['’])|"
    r"the discourse|the speaker['’]s commitments|the commitments)",
    re.IGNORECASE,
)

#: An incoherence predicate.
_INCOHERENCE_MARKERS = re.compile(
    r"(incohér\w*|inconsisten\w*|contradictoire\w*|contradiction|"
    r"se contredis\w*|se contredit|"
    r"ne tient pas|does not hold|is inconsistent|is incoherent)",
    re.IGNORECASE,
)

#: The qualifiers the writer's own phrase carries (#3107/#3122, #3199). A
#: sentence that already names the conflict site is stating the cause, not
#: misreading it.
_QUALIFIERS = re.compile(
    r"(entre unités sources|entre voix|auto[- ]contradiction|"
    r"lot de traduction|cause non établie|sans unité source|"
    r"between (?:source )?units|between voices|translation batch|"
    r"cause not established)",
    re.IGNORECASE,
)

#: A formal-consistency word. Combined with a robustness word it claims the
#: FOL leg as strength; whether that is licensed depends on what the leg
#: decided (see :func:`_fol_decisions`).
_FORMAL_CONSISTENCY_MARKERS = re.compile(
    r"(coh[ée]rence formelle|consistance formelle|vérification formelle|"
    r"formal consistency|formal(ly)? (?:consistent|sound|verification|check)|"
    r"formellement|test formel)",
    re.IGNORECASE,
)

_NEGATION = re.compile(
    # #3298 — « X et non Y » denies Y: the contrastive « et/mais/ou non » is
    # the French counterpart of #3287's English ``not``. It rides the same
    # 32-character window as the other French tokens, so a denial sitting in
    # another clause licenses nothing (the #3288 scope rules).
    #
    # #3318 — the bare comma-contrastive denial « X, non Y », the form the
    # writers use most: 501 raw occurrences on the stored states against 0
    # « non seulement » and 0 « non sans », and on the coordinator's census
    # every ``breadth_as_robustness`` flag of the five most recent paid
    # passes was this shape denying the inference the check accused it of.
    # It rides the same 32-character window — the #3288 scope rules stay
    # unwidened — and replaying the whole licence on the stored states
    # (496 texts) with and without it moves no flag in either direction.
    # The lookahead keeps the two non-denial « non » forms out: « non
    # seulement » asserts what follows (#3287's ``not only``), and « non
    # sans » says "with" — a window carrying ``sans`` is already licensed
    # by the ``sans`` token above, which this alternative must not extend.
    r"\b(ne|n['’]|pas|jamais|sans|aucun\w*|(?:et|mais|ou)\s+non)\b"
    r"|,\s*non\b(?!\s+(?:seulement|sans)\b)",
    re.IGNORECASE,
)

#: #3287 — the English denials, kept SEPARATE from ``_NEGATION`` on purpose.
#: The French tokens are read through the 32-character window of
#: :func:`_is_negated`; English ones are read only when they are adjacent to
#: the marker they deny. The reason is the measured false positive: the R1124
#: render wrote "this breadth reflects sparse attack coverage, not a robust
#: discourse", which the French-only pattern could not see, and the obvious
#: repair (add ``not`` to the pattern above) would silence a genuinely
#: affirmative clause as soon as another clause carried a negation inside its
#: 32 characters. ``not only`` / ``not merely`` assert what follows, so they
#: deny nothing where they sit.
_EN_NEGATION = re.compile(
    r"(?:\bnot\b(?!\s+(?:only|merely|just|simply)\b)|\bnever\b|n['’]t|"
    r"\bno\s+longer\b|\bhardly\b|\bbarely\b|\bfar\s+from\b|\brather\s+than\b|"
    r"\binstead\s+of\b|\banything\s+but\b)",
    re.IGNORECASE,
)

#: What may separate an English denial from the marker it denies: a few words
#: of the same noun phrase ("not a", "does not establish a"), never a
#: punctuation mark. A clause break ends the denial's scope.
_EN_NEGATION_TAIL = re.compile(r"[^.;:,!?]{0,28}")

#: A coordination inside the gap joins two claims: "not sparse but a robust
#: discourse" asserts the robustness, so the ``not`` must not license it.
_EN_CONJUNCTION = re.compile(
    r"\b(?:and|but|yet|or|nor|while|whereas|although|though)\b", re.IGNORECASE
)

#: #3150 — a containment word. « la contradiction reste confinée » is a claim
#: about a contradiction's EXTENT, and it is only licensed for a contradiction
#: the state actually reasoned over.
_CONTAINMENT_MARKERS = re.compile(
    r"(confin\w*|circonscri\w*|cantonné\w*|cantonn\w*|"
    r"reste localis\w*|restent localis\w*)",
    re.IGNORECASE,
)

#: The words that name WHERE a contradiction comes from and over what base it
#: was computed. A sentence carrying one of these states its own binding, so it
#: is not making the unlicensed leap this check looks for.
_REVISION_BASE_MARKERS = re.compile(
    r"(sophisme\w*|négation\w*|negation\w*|socle)", re.IGNORECASE
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# --- #3198 — an absence in the analysis is not an absence in the text ------
#
# The R1109 doc_A render wrote « le texte ne montre pas de réponse à [terme] »
# while Act II weighed that very reply on two units. The writer had read only
# the units the pipeline carried; the absence it observed was in THEM. Nothing
# in the report licensed the step from « these units do not carry it » to « the
# text does not say it », and the no-derivation rule is easier to check on the
# output than to guarantee on the input: whatever the evidence carries, a
# lexical match across a question and its units cannot be exact.
#
# Read as presence verbs on the TEXT as subject. « le texte n'établit pas de
# lien causal » denies a PROPERTY of the text and is not this claim; so does
# the evidence-scoped hedge (« les revendications citées ici n'en portent pas
# la trace »), which names what was analysed rather than the text.
_TEXT_ABSENCE_RE = re.compile(
    r"\ble\s+texte\s+ne\s+"
    r"(?:montre|contient|présente|apporte|offre|donne|fournit|dit|répond)\s+pas"
    r"|\ble\s+texte\s+ne\s+"
    r"(?:donne|apporte|offre|contient|présente)\s+aucun\w*"
    r"|\baucun\w*\s+(?:réponse|trace|mention)\b[^.]{0,60}?\bdans\s+le\s+texte"
    r"|\bthe\s+text\s+(?:does\s+not|doesn['’]t|never)\s+"
    r"(?:show|contain|present|provide|give|answer|say)"
    r"|\bno\s+(?:answer|mention|trace)\b[^.]{0,60}?\bin\s+the\s+text\b",
    re.IGNORECASE,
)


def _text_absence_flags(sentence: str) -> List[Dict[str, Any]]:
    """#3198 — a sentence that places the absence in the TEXT, not the analysis."""
    match = _TEXT_ABSENCE_RE.search(sentence or "")
    if match is None:
        return []
    return [
        {
            "kind": "text_absence_claim",
            "sentence": sentence,
            "measured": {"span": match.group(0)},
        }
    ]


# --- #3224 — an absence the act's own evidence contradicts -----------------
#
# The R1110 render answered the question's causal half in the negative
# (« Les unités analysées n'y montrent pas de glissement de causalité »)
# while ``identified_fallacies`` held a speaker-attributed detection under the
# taxonomy branch « Causalité douteuse » (4.1). #3213 moved that kind of claim
# from the text to the analysis — the right SCOPE, still a false claim. What
# falsifies it is not the text but the act's own record: a sentence that
# denies a category, in words that name a node a speaker detection sits
# under. The match is French against French — the node's content tokens
# against the sentence's — so the question's own vocabulary (« causalité »)
# reaches the branch name without quoting it. Root names stay out: the six
# roots are too coarse (« Erreur de raisonnement ») for one shared word to
# name the category.
#
# Measured on the seven stored local renders before settling the rule: a
# loose marker (« aucun », « ne … pas » anywhere, English negation) raised 14
# flags, all false — « aucun » inside a quoted corpus fragment, « never » in
# an English counter, a reasoning-path dump quoting the node's own name. The
# claim the check targets has a shape those do not: the ANALYSIS as subject,
# its presence verb NEGATED, or an explicit « aucun … relevé / détecté ».
# The coordinator's replay on the four stored doc_A states then raised one
# more false flag, of a second class: the R1110b sentence « Un sophisme
# détecté n'a aucun argument cible identifié » matched the node
# « Sophisme psychogénétique » on « sophisme » — the CLASS word itself, not a
# category name. The marker was right and the token was wrong: a node token
# now carries a category only when it is distinctive WITHIN the taxonomy
# (document frequency over the 1 408 node names — see
# ``DISTINCTIVE_NODE_DF_MAX``), the same lesson as #3215: a generic word is
# not a join.
_ANALYSIS_ABSENCE_RE = re.compile(
    # the analysis as subject, its presence verb negated
    r"\b(?:unit[ée]s?|analys\w+|analyse|rapport|corpus|d[ée]tections?)\b"
    r"[^.]{0,60}?\b(?:ne|n'y|n'en)\s*(?:y\s+)?"
    r"(?:montre|montrent|rel[èe]ve|rel[èe]vent|pr[ée]sente|pr[ée]sentent|"
    r"identifie|identifient|d[ée]tecte|d[ée]tectent|rep[èe]re|rep[èe]rent|"
    r"comporte|comportent|contient|contiennent|appara[îi]t|apparaissent)\w*"
    r"\s+pas\b"
    # or an explicit absence of detection
    r"|\baucun\w*\b[^.]{0,40}?\b(?:relev[ée]|d[ée]tect[ée]|identifi[ée]|"
    r"rep[ée]r[ée]|observ[ée]|document[ée])\w*\b"
    r"|\bpas\s+de\b[^.]{0,40}?\b(?:relev[ée]|d[ée]tect[ée]|identifi[ée]|"
    r"rep[ée]r[ée]|observ[ée])\w*\b",
    re.IGNORECASE,
)


def _speaker_detection_nodes(state: Any) -> List[Tuple[str, str, str, "set[str]"]]:
    """(#fallacy_id, taxonomy_path, node_name, its distinctive tokens) for the
    branch and leaf nodes of each SPEAKER-attributed detection.

    #3180: a detection whose ``move_author`` is ``reported`` is another
    party's move — the speaker commits nothing, so it cannot contradict an
    absence claim about the discourse. The one father ``is_reported_move``
    decides, exactly as the evidence sites do. A detection with no resolvable
    taxonomy path names no node.

    #3224 — a node token must be DISTINCTIVE within the taxonomy to carry a
    category: its document frequency over the vendored node names stays at
    or below ``DISTINCTIVE_NODE_DF_MAX``. The R1110b render flagged
    « aucun … identifié » on the node « Sophisme psychogénétique » through
    « sophisme » alone (df 76) — a class word one ordinary sentence away,
    not a category name; « causalité » (df 5) carried the true positive.
    A node whose every token fails the bar names nothing here.
    """
    fallacies = getattr(state, "identified_fallacies", None)
    if not isinstance(fallacies, dict):
        return []
    out: List[Tuple[str, str, str, "set[str]"]] = []
    for fid, fdata in fallacies.items():
        if not isinstance(fdata, dict):
            continue
        if is_reported_move(fdata):
            continue
        raw = str(fdata.get("taxonomy_path", ""))
        chain = taxonomy_chain(raw)
        if not chain:
            continue
        for node in chain[1:]:
            tokens = {
                t
                for t in _distinctive(_weave_tokens(node))
                if (df := taxonomy_token_df(t)) is not None
                and df <= DISTINCTIVE_NODE_DF_MAX
            }
            if tokens:
                out.append((str(fid), raw, node, tokens))
    return out


def _contradicted_absence_flags(
    sentence: str,
    nodes: List[Tuple[str, str, str, "set[str]"]],
) -> List[Dict[str, Any]]:
    """#3224 — an absence claim naming a node a speaker detection sits under."""
    if _ANALYSIS_ABSENCE_RE.search(sentence or "") is None:
        return []
    sentence_tokens = _weave_tokens(sentence)
    hits: List[Dict[str, Any]] = []
    for fid, path, node, tokens in nodes:
        shared = tokens & sentence_tokens
        if shared:
            hits.append(
                {
                    "fallacy_id": fid,
                    "node": node,
                    "taxonomy_path": path,
                    "shared_tokens": sorted(shared),
                }
            )
    if not hits:
        return []
    return [
        {
            "kind": "absence_contradicted_by_detection",
            "sentence": sentence,
            "measured": {"nodes": hits},
        }
    ]


# --- #3157 — a membership claim must be true of the frame it cites ---------
#
# The R1107 render wrote « arg_13, arg_17 and arg_100 sit inside the grounded
# extension [artifact:dung_frameworks.dung_4] ». That frame's nodes are
# arg_1 … arg_40 — arg_100 is not one of them (it is the deliberation winner,
# with its own quality score) — so the sentence merged a membership claim onto
# a frame that never held the unit, against the very artifact it cited. No gate
# read that kind of claim: VG-1 counts citations, VG-2 only asks that the cited
# field is populated.

#: The artifact key names the EXACT frame the sentence cites, so the check
#: reads that frame — never "some frame in the state".
_DUNG_CITATION_RE = re.compile(r"\[artifact:dung_frameworks\.([A-Za-z0-9_.\-]+)\]")

#: A unit id. The digits are captured so ``arg_1`` cannot match inside
#: ``arg_100``.
_UNIT_ID_RE = re.compile(r"\barg_(\d+)\b")

#: An INSIDE-membership assertion, as narrow phrases. None of them matches
#: through a negation ("is not in", "n'est pas dans"): a sentence that puts a
#: unit OUTSIDE an extension asserts no membership, and a non-node is
#: trivially outside — there is nothing to verify and nothing to flag.
_MEMBERSHIP_INSIDE = re.compile(
    r"(?:"
    r"\b(?:sit|sits|sitting|stand|stands|lie|lies)\s+(?:inside|within|in)\b|"
    r"\b(?:is|are)\s+(?:inside|within)\b|"
    r"\b(?:inside|within)\s+the\b|"
    r"\bmembers?\s+of\b|"
    r"\bappartien\w*|"
    r"\b(?:font|fait)\s+partie\b|"
    r"\bmembres?\b|"
    r"\b(?:sont|est|figurent?|se trouvent?|siègent?)\s+(?:dans|au sein)\b"
    r")",
    re.IGNORECASE,
)

# #3157, extension half (R1109 remainder) — the frame half above reads the
# NODES; the extension half reads a NAMED extension of the cited frame. A
# unit said to be inside (or outside) « the grounded extension » is checked
# against that extension: a node the extension does not hold makes the inside
# claim false, a member the sentence puts outside makes the outside claim
# false. Membership alone decides — after #3174 « outside the grounded
# extension » covers ``out`` and ``undec`` alike, so an outside claim on an
# undecided unit is true and never flagged.

#: The semantics an inside/outside claim can name — the three the readers of
#: #2672 display. A sentence naming none of them leaves the claim to the
#: frame half; the check does not guess a semantics.
_NAMED_SEMANTICS: "Tuple[Tuple[str, re.Pattern[str]], ...]" = (
    ("grounded", re.compile(r"\bgrounded\b|\bancr[ée]e?s?\b|\bfond[ée]e?s?\b", re.I)),
    (
        "preferred",
        re.compile(r"\bpr[ée]f[ée]r[ée]e?s?\b|\bpreferred\b", re.IGNORECASE),
    ),
    ("stable", re.compile(r"\bstables?\b", re.IGNORECASE)),
)

#: An OUTSIDE-membership assertion — the mirror of ``_MEMBERSHIP_INSIDE``.
#: An outside claim is falsified only by membership: a unit the named
#: extension holds.
_MEMBERSHIP_OUTSIDE = re.compile(
    r"(?:"
    r"\b(?:lie|lies|lying|sit|sits|sitting|stand|stands)\s+outside\b|"
    r"\b(?:is|are)\s+outside\b|"
    r"\boutside\s+the\b|"
    r"\bhors\s+de\s+l['’]extension\b|"
    r"\bn['’](?:est|sont)\s+pas\s+dans\s+l['’]extension\b|"
    r"\bn['’]appartien\w*\s+pas\s+à\s+l['’]extension\b"
    r")",
    re.IGNORECASE,
)

# --- #3151 — the weave must keep the evidence's own bindings -------------
#
# The R1106 Act II render moved a counter-argument (and its supporting
# material) from the unit it targets onto the deliberation winner — both sit
# in the same "soutiens" movement, and the reader got a counter against the
# passage the report itself calls the strongest. The binding was correct in
# the evidence (counters are indexed by ``target_arg_id`` and listed under
# their own bullet); it was lost in the WEAVE. The detectors below read the
# same bundle the writer received — distinctive tokens of each counter's
# content and of each unit's description, both measured AGAINST THE OTHERS
# (a token names something only when no other counter/unit carries it) — and
# flag the loss. They never rewrite; the sentence is where the reader sees it.

#: Function words a distinctive-token pass must ignore: a stopword names
#: nothing, and counting it would make two unrelated texts "cite" each other.
#: The last two blocks (#3215) are not function words but the REPORT's own
#: generic vocabulary — « revendication », « conclusion », « argument »,
#: « also », « only » — which names nothing either, because every text of a
#: report about arguments carries it. Measured on the six stored renders: they
#: carried every `counter_on_wrong_unit` flag the token pass raised.
_WEAVE_STOPWORDS = frozenset("""
    le la les un une des du de d l et ou mais donc or ni car que qui quoi
    dont à au aux ce cet cette ces son sa ses leur leurs il elle ils elles
    on nous vous je tu me te se lui y en est sont était étaient être avoir
    ai as ont a eu plus moins très trop peu tout tous toute toutes même
    aussi alors ainsi lors par pour avec sans sous sur entre vers chez dans
    ne pas jamais aucun aucune celui celle ceux
    the a an and or but of to in on for with without at by from as is are
    was were be been being this that these those it its his her their our
    your not no nor
    deux trois quand apres après avant faire fait mieux puis contre argument
    arguments revendication revendications conclusion conclusions analyse
    discours paragraphe passage passages texte rapport section corpus graphe
    cadre rejet rejets assertion thèse
    also more than just only even some such when what which would could
    should there then they them very much many make made does done like well
    """.split())

#: A content word: ≥ 4 letters — shorter words are too common to be
#: distinctive.
_WEAVE_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]{4,}")

#: #3215 — a DISTINCTIVE token is ≥ 5 letters. Measured on the six stored
#: renders: at 4 letters the "distinctive" sets carried « deux » and « puis »,
#: and 22 of 22 `counter_on_wrong_unit` flags rested on such words (0 of them
#: on the counter's own subject). The bar applies where distinctiveness is
#: BUILT (the unit and counter indexes), so the tokenizer's other readers are
#: untouched.
_DISTINCTIVE_MIN_LEN = 5

#: #3215 — a counter is CITED in a paragraph on at least this many of its
#: distinctive tokens...
_CITE_MIN_TOKENS = 2

#: #3215 — ... and on at least this SHARE of them. Two matches out of eleven
#: is a coincidence of common words, not a citation: the R1109 render's flags
#: were built on exactly that shape.
_CITE_MIN_SHARE = 1.0 / 3.0

#: #3215 — a unit is BOUND in a paragraph on at least this many distinctive
#: tokens. A single shared word places nothing, and one word was enough for
#: the paragraph to count as "about" a unit before this bar.
_BOUND_MIN_TOKENS = 2


def _distinctive(tokens: "set[str]") -> "set[str]":
    """The tokens long enough to be distinctive (#3215)."""
    return {t for t in tokens if len(t) >= _DISTINCTIVE_MIN_LEN}


def _cited_in(distinctive: "set[str]", tokens: "set[str]") -> bool:
    """Does this paragraph carry a real citation of the counter (#3215)?

    Two distinctive tokens AND at least a third of the counter's distinctive
    set: the render must carry something only that counter carries, at a
    share no generic vocabulary reaches by accident.
    """
    matched = distinctive & tokens
    return len(matched) >= _CITE_MIN_TOKENS and len(matched) >= _CITE_MIN_SHARE * len(
        distinctive
    )


#: The holding threshold — the same ≥ 0.75 rule the Act II evidence line
#: uses, so the check and the evidence never disagree.
_HOLD_THRESHOLD = 0.75

#: « Seuls / only » — an exhaustive claim over a list.
_ONLY_MARKER = re.compile(r"\b(?:seul(?:e)?|seuls|only)\b", re.IGNORECASE)

#: A superlative over a counter (« le contre-argument le plus fort » /
#: « the highest-scoring counter »).
_SUPERLATIVE_MARKERS = re.compile(
    r"\b(meilleur\w*|plus (?:fort|élevé|haut|noté)|mieux noté\w*|"
    r"highest(?:[- ]scoring)?|top)\b",
    re.IGNORECASE,
)
_COUNTER_WORD = re.compile(r"contre[- ]arguments?|counter[- ]arguments?", re.IGNORECASE)

#: The natural French/English spellings of the nine quality virtues, so a
#: « seuls » sentence can be read against the unit's measured scores. Narrow
#: phrases, one pattern per virtue — never a bag of tokens.
_VIRTUE_PATTERNS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("clarte", re.compile(r"clart[ée]", re.IGNORECASE)),
    ("pertinence", re.compile(r"pertinen\w*", re.IGNORECASE)),
    (
        "presence_sources",
        re.compile(r"pr[ée]sences? de sources?|sources? pr[ée]sent\w*", re.IGNORECASE),
    ),
    (
        "refutation_constructive",
        re.compile(r"r[ée]futations? constructives?", re.IGNORECASE),
    ),
    ("structure_logique", re.compile(r"structures? logiques?", re.IGNORECASE)),
    ("analogie_pertinente", re.compile(r"analogies? pertinente?s?", re.IGNORECASE)),
    ("fiabilite_sources", re.compile(r"fiabilit[ée](?: des sources?)?", re.IGNORECASE)),
    ("exhaustivite", re.compile(r"exhaustivit[ée]", re.IGNORECASE)),
    (
        "redondance_faible",
        re.compile(
            r"redondances? faibl\w*|faible redondance|refus de la redite",
            re.IGNORECASE,
        ),
    ),
)

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")

#: #3298 — a citation anchor as the briefing emits it. Its interior is the
#: state's key vocabulary (``identified_fallacies``, ``arg_16``), never the
#: prose's: on the R1125a render the word ``identified`` from inside the
#: anchors was the ONLY token binding a unit the sentence never named.
_ANCHOR_RE = re.compile(r"\[artifact:[^\]]*\]")


def _weave_tokens(text: str) -> "set[str]":
    """The content tokens of a text, lowercased, stopwords dropped.

    #3298 — anchor interiors are stripped first: the tokens inside an
    ``[artifact:…]`` citation are the state's key vocabulary, not the
    prose's, and on the R1125a render they bound a unit the sentence never
    named. The unit an anchor names is read where the sentence names it —
    see :func:`_units_named_through_anchors` — never through its characters.
    """
    stripped = _ANCHOR_RE.sub(" ", text or "")
    return {t.lower() for t in _WEAVE_TOKEN_RE.findall(stripped)} - _WEAVE_STOPWORDS


def _index_counters(state: Any) -> List[Tuple[str, str, "set[str]"]]:
    """Counters with a target binding, each with the tokens no OTHER counter
    carries — the tokens that make a citation attributable (#3151)."""
    entries = [
        e
        for e in (getattr(state, "counter_arguments", []) or [])
        if isinstance(e, dict)
        and e.get("target_arg_id")
        and isinstance(e.get("counter_content"), str)
        and e["counter_content"].strip()
    ]
    token_sets = [_weave_tokens(e["counter_content"]) for e in entries]
    out: List[Tuple[str, str, "set[str]"]] = []
    for index, entry in enumerate(entries):
        others: "set[str]" = set()
        for j, tokens in enumerate(token_sets):
            if j != index:
                others |= tokens
        # #3215 — distinctiveness starts at five letters: « deux » and « puis »
        # are shared by unrelated texts and made « cited » true by accident.
        distinctive = _distinctive(token_sets[index] - others)
        if len(distinctive) >= 2:
            out.append(
                (str(entry.get("id", "?")), str(entry["target_arg_id"]), distinctive)
            )
    return out


# --- #3158: a counter-argument's factual claim is the counter-argument's ---
#
# Act II restated a *prior trend* in the report's own voice and used it as the
# refutation of a post hoc — a trend no source in the state asserts. It is
# asserted by a counter-argument: an LLM-generated objection that cites
# nothing. The report adopted an unverified external fact and the reader
# cannot tell it from a checked fact (#3158).
#
# The producer tags the claim; a writer can ignore a tag. This is the check
# that sees the change of voice in the produced text: a paragraph restating
# that claim with no attribution is flagged.
#
# What counts as « asserts a fact » is read deterministically, never guessed:
# a number, a claim delegated to an authority, a general statement of fact, or
# a dated trend (a year, a direction over time). A counter that only reframes
# the question (« autrement dit, la question est de savoir… ») asserts nothing
# about the world — it carries no tag and earns no flag (the issue's control).
#
# BOTH languages: the counter generator writes French or English depending on
# the run, and a French-only vocabulary left the very instance the issue was
# filed for untagged — ca_31, an English dated trend, on the doc_B state.
_FACT_ASSERTION_MARKERS = re.compile(
    r"\d+\s*%"
    r"|\d+\s*(?:fois|millions?|milliards?|points?|pour ?cent|times|percent)"
    r"|\b(?:études?|recherches?|données|statistiques|sondages?|travaux"
    r"|experts?|scientifiques?|économistes?|historiens?|chercheurs?"
    r"|mesures?|observations?"
    r"|studies|study|research|data|statistics|surveys?|evidence|findings"
    r"|scientists?|economists?|historians?|researchers?"
    r"|measurements?)\b"
    r"|\bil est (?:établi|prouvé|avéré|reconnu|démontré|mesuré|documenté)\b"
    r"|\bon (?:sait|observe|constate|mesure|trouve)\b"
    r"|\b(?:en réalité|de fait|empiriquement|dans les faits|historiquement)\b"
    r"|\b(?:it is|it's) (?:established|proven|documented|well known)\b"
    r"|\b(?:in fact|empirically|historically|research shows|data shows)\b"
    r"|\b(?:19|20)\d{2}\b"
    r"|\b(?:trends?|tendances?|declin\w*|increas\w*|decreas\w*"
    r"|rising|falling|grew|growing|doubled|tripled"
    r"|baisse|hausse|croissance|recul)\b"
    r"|\bover the (?:past|last) \w+\b",
    re.IGNORECASE,
)

#: What keeps a restatement attributed. Narrow on purpose: the point is the
#: voice, and a report that says whose claim it is has done what the consigne
#: asks. Pronouns are included so the attribution may lead the next sentence
#: (« Un contre-argument objecte. Selon lui, les études … »).
_ATTRIBUTION_MARKERS = re.compile(
    r"contre-argument\w*"
    r"|\bobjections?\b|\bobjecte(?:nt)?\b|\bobjecter\b"
    r"|\bcontradict(?:eur|eurs|rice|rices)\b"
    r"|\bcontre-discours\b|\brépliques?\b"
    r"|\bselon (?:lui|elle|eux|elles|le contre|la contre|un contre"
    r"|une objection)\b"
    r"|\bd'après (?:lui|elle|eux|elles)\b"
    r"|\bla partie adverse\b",
    re.IGNORECASE,
)


def counter_asserts_a_fact(text: str) -> bool:
    """#3158 — does this counter-argument assert something about the world?

    Shared by the producer (does the line need a provenance tag?) and by the
    check (is an unattributed restatement a defect?), so the two can never
    disagree about which objections carry a claim.
    """
    return bool(_FACT_ASSERTION_MARKERS.search(text or ""))


def _fact_asserting_counters(state: Any) -> List[Tuple[str, "set[str]"]]:
    """The fact-asserting counters, with the tokens a restatement of THAT
    claim carries — tokens no OTHER counter carries.

    Same distinctive-token construction as :func:`_index_counters`: a word
    every objection shares cannot place a sentence, so only a claim this
    counter and no other one makes can be recognised as a restatement.
    """
    entries = [
        e
        for e in (getattr(state, "counter_arguments", []) or [])
        if isinstance(e, dict)
        and e.get("target_arg_id")
        and isinstance(e.get("counter_content"), str)
        and e["counter_content"].strip()
    ]
    token_sets = [_weave_tokens(e["counter_content"]) for e in entries]
    out: List[Tuple[str, "set[str]"]] = []
    for index, entry in enumerate(entries):
        if not counter_asserts_a_fact(entry["counter_content"]):
            continue
        others: "set[str]" = set()
        for j, tokens in enumerate(token_sets):
            if j != index:
                others |= tokens
        distinctive = token_sets[index] - others
        if len(distinctive) >= 2:
            out.append((str(entry.get("id", "?")), distinctive))
    return out


def _unattributed_claim_flags(
    paragraphs: List[str],
    fact_counters: List[Tuple[str, "set[str]"]],
    max_flags: int,
) -> List[Dict[str, Any]]:
    """#3158 — sentences that restate a counter's factual claim in the
    report's own voice."""
    flags: List[Dict[str, Any]] = []
    for paragraph in paragraphs:
        if len(flags) >= max_flags:
            break
        attributed_in_previous_sentence = False
        for sentence in _sentences(paragraph):
            if len(flags) >= max_flags:
                return flags
            tokens = _weave_tokens(sentence)
            restated = [
                counter_id
                for counter_id, distinctive in fact_counters
                if len(distinctive & tokens) >= 2
            ]
            attributes = _ATTRIBUTION_MARKERS.search(sentence) is not None
            if restated and not attributes and not attributed_in_previous_sentence:
                flags.append(
                    {
                        "kind": "counter_claim_in_own_voice",
                        "sentence": sentence,
                        # ids only — the tokens are corpus-derived
                        "measured": {"counters": restated},
                    }
                )
            attributed_in_previous_sentence = attributes
    return flags


# --- #3158 (second instance): a fallacy NAME is a detection, not a judgement --
#
# Through the debate channel Act III restated a reply's verdict as the report's
# own finding: « le dilemme sur les résolutions […] est lui-même un faux
# dilemme », while none of the 28 ``identified_fallacies`` named that unit. A
# fallacy name in the report's voice reads as a DETECTION, and the detectors
# recorded nothing there; the deep synthesis of the same render cites that unit
# among the claims that fare better, so the report contradicted itself.
#
# Only names a detector classification can be checked against belong here: the
# two-word-and-longer labels the taxonomy produces. « C'est un sophisme » names
# no class, so it is not a detection the state could fail to carry, and it does
# not fire.
_FALLACY_NAME_RE = re.compile(
    r"\b(?:faux dilemmes?|fausses? dichotomies?|hommes? de paille|épouvantails?"
    r"|pentes? glissantes?|généralisations? (?:hâtives?|abusives?)"
    r"|appels? à l'autorité|appels? à l'émotion|appels? au peuple"
    r"|appels? à l'ignorance|ad hominem|post hoc|pétitions? de principe"
    r"|cercles? vicieux|fausses? analogies?|fausses? causes?|whataboutism\w*"
    r"|non[- ]sequitur)\b",
    re.IGNORECASE,
)


def _units_with_fallacy_record(state: Any) -> "set[str]":
    """The units a detector actually recorded a fallacy on.

    The key is ``target_argument_id``: ``SharedState.add_fallacy`` writes it
    (``shared_state.py``), and the paid states carry it on 30/31, 28/29 and
    29/30 records. ``target_arg_id`` is the COUNTER key — reading it here made
    ``recorded`` always empty and flagged every name on a recorded unit.
    """
    out: "set[str]" = set()
    records = getattr(state, "identified_fallacies", None)
    entries = records.values() if isinstance(records, dict) else records or []
    for data in entries:
        if isinstance(data, dict) and data.get("target_argument_id"):
            out.add(str(data["target_argument_id"]))
    return out


#: #3298 — the two anchors that NAME a unit: directly
#: (``[artifact:identified_arguments.arg_16]`` — the key is the unit's id) or
#: through a fallacy record (``[artifact:identified_fallacies.fallacy_16]``
#: cites a detection, whose ``target_argument_id`` is the unit it sits on).
_UNIT_ANCHOR_RE = re.compile(r"\[artifact:identified_arguments\.(arg_\d+)\]")
_FALLACY_ANCHOR_RE = re.compile(
    r"\[artifact:identified_fallacies\.([A-Za-z0-9_.\-]+)\]"
)

#: #3316 — a clause boundary, read only OUTSIDE anchors: an anchor's own
#: dots (``identified_fallacies`` **.** ``fallacy_2``) are not punctuation.
#: The measured trap: a plain ``[.,;:!?]`` search cut the span at the record
#: key's dot, and the backing anchor became invisible — the first
#: measurement of the backing rule removed nothing because of it.
_CLAUSE_PUNCTUATION = re.compile(r"[.,;:!?]")


def _units_named_through_anchors(sentence: str, state: Any) -> "set[str]":
    """#3298 — the units a sentence names THROUGH its citations.

    After #3307 the prose no longer prints bare keys: a unit is cited as
    ``[artifact:identified_arguments.arg_16]`` (the anchor's key is the
    unit's id) or through a fallacy record — the anchor cites the detection,
    and the detection's ``target_argument_id`` names the unit it was
    recorded on. Both name a unit exactly as an explicit ``arg_N`` in the
    prose does; an anchor citing anything else names no unit here.
    """
    units: "set[str]" = set(_UNIT_ANCHOR_RE.findall(sentence))
    records = getattr(state, "identified_fallacies", None)
    if isinstance(records, dict):
        for key in _FALLACY_ANCHOR_RE.findall(sentence):
            data = records.get(key)
            if isinstance(data, dict) and data.get("target_argument_id"):
                units.add(str(data["target_argument_id"]))
    return units


def _name_backed_by_anchor(sentence: str, match: "re.Match[str]", records: Any) -> bool:
    """#3316 — True when the name ``match`` is followed, within its clause,
    by an ``identified_fallacies`` anchor whose record exists.

    The name is then backed by that record, and the check does not look for
    other units in the sentence — the false positive this rule kills is a
    name whose sentence carries a word that coincidentally binds a
    record-less unit through its description (the ``speaker`` /
    ``opponent`` class, measured on the stored states: 4 distinct false
    positives removed, zero true positives lost; subtracting taxonomy
    vocabulary instead removed nothing — the binding tokens are ordinary
    words, not label vocabulary). A clause boundary never sits inside an
    anchor: the anchor's own dots are not punctuation.
    """
    if not isinstance(records, dict):
        return False
    tail = sentence[match.end() :]
    anchor_spans = [(a.start(), a.end()) for a in _ANCHOR_RE.finditer(tail)]
    stop = len(tail)
    for boundary in _CLAUSE_PUNCTUATION.finditer(tail):
        if any(start <= boundary.start() < end for start, end in anchor_spans):
            continue
        stop = boundary.start()
        break
    for key in _FALLACY_ANCHOR_RE.findall(tail[:stop]):
        data = records.get(key)
        if isinstance(data, dict) and data.get("target_argument_id"):
            return True
    return False


def _unbacked_fallacy_name_flags(
    paragraphs: List[str],
    state: Any,
    units_indexed: Dict[str, "set[str]"],
    max_flags: int,
) -> List[Dict[str, Any]]:
    """#3158 — a fallacy name in the report's voice on a unit no detector
    recorded one for.

    Five ways a sentence may legitimately carry a name, and none is flagged: it
    names no unit (then it is not a claim about a unit), it is negated (« ne
    relève aucun faux dilemme »), it attributes the name to the objection that
    made it, the unit carries a fallacy record, or — #3316 — the name itself
    is backed by a record anchor in its own clause, whatever other word of the
    sentence coincidentally binds a record-less unit.

    #3298 — how a sentence NAMES a unit: an explicit ``arg_N`` in the prose,
    through the anchors that cite a unit or a fallacy record (#3307's
    channel), or by its description's distinctive tokens — never through
    tokens from inside an anchor.
    """
    if not units_indexed:
        return []
    recorded = _units_with_fallacy_record(state)
    records = getattr(state, "identified_fallacies", None)
    flags: List[Dict[str, Any]] = []
    for paragraph in paragraphs:
        if len(flags) >= max_flags:
            break
        for sentence in _sentences(paragraph):
            if len(flags) >= max_flags:
                return flags
            # #3298 — a unit is named where the sentence NAMES it: an
            # explicit ``arg_N`` in the prose (anchors stripped, so an
            # anchor's key is never read as prose), through the anchors that
            # cite a unit or a fallacy record (#3307's channel — the prose
            # prints no bare key any more), or by its description's
            # distinctive tokens. Gone: tokens from INSIDE an anchor binding
            # a unit — on the R1125a render the anchors' own word
            # ``identified`` bound arg_47 while the sentence, right, named
            # arg_16 … arg_63 explicitly.
            prose = _ANCHOR_RE.sub(" ", sentence)
            tokens = _weave_tokens(prose)
            explicit_ids = {f"arg_{d}" for d in _UNIT_ID_RE.findall(prose)}
            named_units = sorted(
                (explicit_ids | _units_named_through_anchors(sentence, state))
                | {
                    unit
                    for unit, distinctive in units_indexed.items()
                    if distinctive & tokens
                }
            )
            if not named_units:
                continue
            match = _FALLACY_NAME_RE.search(sentence)
            if match is None or _is_negated(sentence, match.start()):
                continue
            if _ATTRIBUTION_MARKERS.search(sentence) is not None:
                continue
            if _name_backed_by_anchor(sentence, match, records):
                continue
            unbacked = [unit for unit in named_units if unit not in recorded]
            if unbacked:
                flags.append(
                    {
                        "kind": "fallacy_name_without_record",
                        "sentence": sentence,
                        "measured": {"name": match.group(0), "units": unbacked},
                    }
                )
    return flags


#: #3308 — an assertion that a unit carries NO defect. The family #2966
#: named: a zero never evaluated, read as an evaluated zero (#1019). The
#: R1127a sentence was « les unités citées ne portent pas de défaut net ».
_NO_DEFECT_CLAIM_RE = re.compile(
    r"\b(?:"
    r"(?:ne |n')(?:portent?|présentent?|comportent?|ont?|a)\s+"
    r"(?:pas|aucun)\s+(?:de\s+|d')?(?:défaut|faute|sophisme)"
    r"|sans\s+(?:aucun\s+)?(?:défaut|faute)"
    r"|(?:aucun|pas de)\s+(?:défaut|faute)\s+(?:net|nettes?|localisé|localisée)"
    r"|exempt(?:e?s)?\s+de\s+(?:défaut|faute)"
    r")\b",
    re.IGNORECASE,
)


def _no_defect_claim_flags(
    paragraphs: List[str],
    state: Any,
    units_indexed: Dict[str, "set[str]"],
    max_flags: int,
) -> List[Dict[str, Any]]:
    """#3308 — « pas de défaut » said of a unit the fallacy pass never examined.

    Act III concluded, of a divergent vote winner, that « les unités citées ne
    portent pas de défaut net »; neither winner was in the pass's coverage
    record (k = 10 of N = 89), so the claim rested on the pass's SILENCE. That
    is #2966's family — an absence of examination told as an absence of defect
    (#1019) — and the same defect #2976 repaired in Act II's narrative.

    The claim is a sentence; the units it is about are the ones its PARAGRAPH
    designates, read exactly as :func:`_unbacked_fallacy_name_flags` reads
    them (explicit ``arg_N`` in the prose, the #3307 anchors, or a unit's
    distinctive description tokens). A paragraph that names no unit makes no
    claim about a unit and is never flagged.

    A unit is only flaggable when the coverage record EXISTS and excludes it.
    ``_fallacy_examined_ids`` returns ``None`` for a state older than #2966:
    absence of the record is not evidence of non-examination, so the licence
    degrades to honest silence rather than inventing a verdict (#2966).
    """
    if not units_indexed:
        return []
    from argumentation_analysis.reporting.restitution.virtuous_identification import (
        _fallacy_examined_ids,
    )

    examined = _fallacy_examined_ids(state)
    if examined is None:
        return []
    flags: List[Dict[str, Any]] = []
    for paragraph in paragraphs:
        if len(flags) >= max_flags:
            break
        if _NO_DEFECT_CLAIM_RE.search(paragraph) is None:
            continue
        prose = _ANCHOR_RE.sub(" ", paragraph)
        tokens = _weave_tokens(prose)
        named_units = sorted(
            (
                {f"arg_{d}" for d in _UNIT_ID_RE.findall(prose)}
                | _units_named_through_anchors(paragraph, state)
            )
            | {
                unit
                for unit, distinctive in units_indexed.items()
                if distinctive & tokens
            }
        )
        if not named_units:
            continue
        unexamined = [unit for unit in named_units if unit not in examined]
        if not unexamined:
            continue
        flags.append(
            {
                "kind": "no_defect_claim_on_unexamined_unit",
                "sentence": paragraph.strip(),
                "measured": {
                    "units": unexamined,
                    "examined": sorted(named_units),
                },
            }
        )
    return flags


def _index_units(state: Any) -> Dict[str, "set[str]"]:
    """Per-unit distinctive description tokens — what places a paragraph.

    The value IS the description: ``UnifiedAnalysisState.add_argument``
    (``shared_state.py``) writes ``identified_arguments[arg_id] = description``
    — the only writer — so every real state carries a ``str`` (measured on
    all 12 paid states of R1101–R1109). Reading a ``["description"]`` key
    made this index empty on every real run, and every check gated on
    ``units_indexed`` inert (#3202).
    """
    args = getattr(state, "identified_arguments", None)
    if not isinstance(args, dict):
        return {}
    entries: List[Tuple[str, "set[str]"]] = []
    for arg_id, description in args.items():
        if isinstance(description, str) and description.strip():
            entries.append((str(arg_id), _weave_tokens(description)))
    out: Dict[str, "set[str]"] = {}
    for index, (arg_id, tokens) in enumerate(entries):
        others: "set[str]" = set()
        for j, (_, other) in enumerate(entries):
            if j != index:
                others |= other
        # #3215 — the same five-letter bar as the counter index: a 4-letter
        # word placed nothing reliably on the measured renders.
        distinctive = _distinctive(tokens - others)
        if distinctive:
            out[arg_id] = distinctive
    return out


def _holding_virtues(state: Any, arg_id: str) -> "set[str]":
    """The virtues the unit's measured scores hold (≥ the evidence's 0.75)."""
    quality = getattr(state, "argument_quality_scores", None)
    if not isinstance(quality, dict):
        return set()
    entry = quality.get(arg_id)
    if not isinstance(entry, dict):
        return set()
    scores = entry.get("scores")
    if not isinstance(scores, dict):
        return set()
    return {
        str(virtue)
        for virtue, score in scores.items()
        if isinstance(score, (int, float)) and score >= _HOLD_THRESHOLD
    }


def _counter_scores(state: Any) -> List[Tuple[str, float]]:
    """The (id, score) pairs the run recorded on its counters."""
    out: List[Tuple[str, float]] = []
    for entry in getattr(state, "counter_arguments", []) or []:
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        if isinstance(score, (int, float)):
            out.append((str(entry.get("id", "?")), float(score)))
    return out


def _weave_flags(
    paragraphs: List[str],
    state: Any,
    counters_indexed: List[Tuple[str, str, "set[str]"]],
    units_indexed: Dict[str, "set[str]"],
    counter_scores: List[Tuple[str, float]],
    max_flags: int,
) -> List[Dict[str, Any]]:
    """The #3151 binding flags: counter on the wrong unit's paragraph, «
    seuls » dropping a holding virtue, superlative over a tied maximum."""
    flags: List[Dict[str, Any]] = []
    top = max((score for _, score in counter_scores), default=None)
    tied = (
        sorted(cid for cid, score in counter_scores if score == top)
        if top is not None and sum(1 for _, s in counter_scores if s == top) >= 2
        else []
    )
    for paragraph in paragraphs:
        if len(flags) >= max_flags:
            break
        tokens = _weave_tokens(paragraph)
        present_units = sorted(u for u, dist in units_indexed.items() if dist & tokens)
        # -- a counter cited in a paragraph that BINDS another unit (#3215) --
        # The pre-fix rule flagged whenever the target was not "present", and
        # presence was one shared token: on the R1109 render the units are in
        # the source language while the prose is French, so the target was
        # never present and every cited counter flagged (32/32 false; 22/22 on
        # the six stored renders measured here). Binding now needs two
        # distinctive tokens, the citation needs a real share, and the flag no
        # longer asks where the TARGET is — that half is what no lexical join
        # can see across languages.
        bound_units = [
            u
            for u, dist in units_indexed.items()
            if len(dist & tokens) >= _BOUND_MIN_TOKENS
        ]
        if bound_units:
            for counter_id, target, distinctive in counters_indexed:
                if not _cited_in(distinctive, tokens):
                    continue
                if target in bound_units:
                    continue  # its own unit's paragraph: where it belongs
                flags.append(
                    {
                        "kind": "counter_on_wrong_unit",
                        "sentence": paragraph.strip(),
                        "measured": {
                            "counter": counter_id,
                            "target_arg_id": target,
                            "paragraph_units": sorted(bound_units),
                        },
                    }
                )
                if len(flags) >= max_flags:
                    return flags
        for sentence in _sentences(paragraph):
            if len(flags) >= max_flags:
                return flags
            # -- « seuls X et Y » while a holding virtue is dropped ---------
            if (
                present_units
                and len(present_units) == 1
                and _ONLY_MARKER.search(sentence)
            ):
                named = {
                    virtue
                    for virtue, pattern in _VIRTUE_PATTERNS
                    if pattern.search(sentence)
                }
                if named:
                    holding = _holding_virtues(state, present_units[0])
                    dropped = holding - named
                    if dropped:
                        flags.append(
                            {
                                "kind": "only_virtues_drops_a_holding_one",
                                "sentence": sentence,
                                "measured": {
                                    "unit": present_units[0],
                                    "holding": sorted(holding),
                                    "dropped": sorted(dropped),
                                },
                            }
                        )
                        continue
            # -- a superlative that reads a tie as a unique maximum ---------
            if (
                tied
                and _SUPERLATIVE_MARKERS.search(sentence)
                and _COUNTER_WORD.search(sentence)
            ):
                flags.append(
                    {
                        "kind": "superlative_over_tied_counters",
                        "sentence": sentence,
                        "measured": {"max": top, "tied": tied},
                    }
                )
    return flags


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def _english_negates(window: str) -> bool:
    """True when an English denial sits ADJACENT to the end of ``window``.

    Adjacency, not the window, is what bounds the English scope (#3287): the
    nearest denial must reach the marker through the same noun phrase — no
    punctuation, no coordination — so another clause's ``not`` cannot license
    a claim this one asserts.
    """
    last = None
    for match in _EN_NEGATION.finditer(window):
        last = match
    if last is None:
        return False
    tail = window[last.end() :]
    if _EN_CONJUNCTION.search(tail):
        return False
    return bool(_EN_NEGATION_TAIL.fullmatch(tail))


def _is_negated(sentence: str, start: int) -> bool:
    """True when a negation sits just before ``start`` ("n'est pas robuste").

    A 32-character window keeps the test cheap and local: a negation further
    away belongs to another clause, and treating it as one would silence real
    claims that follow a negative aside. English denials are the exception
    (#3287): they are read only when adjacent to the marker, because the same
    window carries them across clauses far more easily than French syntax does
    — see :func:`_english_negates`.
    """
    window = sentence[max(0, start - 32) : start]
    return bool(_NEGATION.search(window)) or _english_negates(window)


def _dung_measurements(state: Any) -> List[Dict[str, Any]]:
    """The measured attack density of every Dung framework the state holds."""
    measurements: List[Dict[str, Any]] = []
    entries = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(entries, dict):
        return measurements
    for framework, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        arguments = entry.get("arguments") or []
        attacks = entry.get("attacks") or []
        if not isinstance(arguments, list) or not arguments:
            continue
        measurements.append(
            {
                "framework": framework,
                "arguments": len(arguments),
                "attacks": len(attacks) if isinstance(attacks, list) else 0,
                "density": (
                    len(attacks) / len(arguments) if isinstance(attacks, list) else 0.0
                ),
                "attacks_submitted": entry.get("attacks_submitted"),
                "attacks_retained": entry.get("attacks_retained"),
            }
        )
    return measurements


def _formal_causes(state: Any) -> List[str]:
    """The cause classes the run actually recorded, FOL and PL alike."""
    causes: List[str] = []
    for attribute in ("fol_analysis_results", "propositional_analysis_results"):
        for result in getattr(state, attribute, []) or []:
            if not isinstance(result, dict):
                continue
            cause = result.get("consistency_cause")
            if isinstance(cause, dict) and cause.get("cause"):
                causes.append(str(cause["cause"]))
    return causes


def _revision_base_units(state: Any) -> Optional["set[str]"]:
    """The units the belief revision actually revised (#3150).

    ``belief_revision_results[*]["original"]`` is the base the minimal
    retraction was computed over — the extraction window's units, which on a
    real run is a PREFIX of the population. ``None`` means no revision ran (or
    none recorded its base), so there is nothing to bind a containment claim
    to and the check stays silent rather than guessing.
    """
    entries = getattr(state, "belief_revision_results", None)
    if not isinstance(entries, list) or not entries:
        return None
    base: "set[str]" = set()
    recorded = False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        original = entry.get("original")
        if isinstance(original, list) and original:
            recorded = True
            base.update(str(unit) for unit in original if isinstance(unit, str))
    return base if recorded else None


def _formal_contradiction_units(state: Any) -> "set[str]":
    """The source units a DECIDED formal contradiction names (#3150).

    A ``satisfiable`` of ``False`` (PL) or a ``consistent`` of ``False`` (FOL)
    is a decided contradiction; the units behind it come from the recorded
    cause's pairs when it names any, else from the ``formula_sources`` aligned
    with the recorded core's indices. An undecided record contributes nothing.
    """
    units: "set[str]" = set()
    for attribute, verdict_key in (
        ("propositional_analysis_results", "satisfiable"),
        ("fol_analysis_results", "consistent"),
    ):
        for result in getattr(state, attribute, None) or []:
            if not isinstance(result, dict) or result.get(verdict_key) is not False:
                continue
            cause = result.get("consistency_cause")
            if isinstance(cause, dict):
                for pair in cause.get("pairs") or []:
                    if not isinstance(pair, dict):
                        continue
                    for side in pair.get("sources") or []:
                        if isinstance(side, list):
                            units.update(unit for unit in side if isinstance(unit, str))
            core = cause.get("core") if isinstance(cause, dict) else None
            formulas = result.get("formulas")
            sources = result.get("formula_sources")
            if (
                isinstance(core, dict)
                and isinstance(core.get("indices"), list)
                and isinstance(formulas, list)
                and isinstance(sources, list)
            ):
                for index in core["indices"]:
                    if isinstance(index, int) and 0 <= index < len(sources):
                        side = sources[index]
                        if isinstance(side, list):
                            units.update(unit for unit in side if isinstance(unit, str))
    return units


def _fol_decisions(state: Any) -> Dict[str, int]:
    """What the FOL leg actually decided (#3123, R1105b instance).

    ``vacuous_consistent`` counts entries that returned ``consistent`` without
    answering a single inference — a decided consistency that distinguished
    nothing. ``decisive`` counts entries that answered queries or decided an
    inconsistency; as long as one exists, citing formal strength is licensed
    (the positive control).
    """
    vacuous = 0
    decisive = 0
    for result in getattr(state, "fol_analysis_results", []) or []:
        if not isinstance(result, dict):
            continue
        if result.get("consistent") is True and not (result.get("inferences") or []):
            vacuous += 1
        elif result.get("inferences") or result.get("consistent") is False:
            decisive += 1
    return {"vacuous_consistent": vacuous, "decisive": decisive}


def _dung_frames_with_nodes(state: Any) -> Dict[str, "set[str]"]:
    """#3157 — the node set of every Dung frame the run actually built.

    A frame with no ``arguments`` list (the formalism sidecars the state also
    holds — ``delp_analysis`` and friends) validates no membership at all, so
    it is left out rather than read as "this frame holds nothing".
    """
    frames: Dict[str, "set[str]"] = {}
    entries = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(entries, dict):
        return frames
    for frame_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        nodes = {str(node) for node in (entry.get("arguments") or []) if str(node)}
        if nodes:
            frames[str(frame_id)] = nodes
    return frames


#: Contrast clause boundaries — a compound sentence flips the claim's
#: direction mid-sentence (« inside ..., while ... outside it »). Each unit
#: belongs to the marker of ITS OWN clause, never to the sentence's (#3204
#: rework: reading the units sentence-wide made every true compound sentence
#: raise both flags at once).
_CLAUSE_BOUNDARY = re.compile(
    r",\s*(?:while|whereas|but|mais|alors\s+que|tandis\s+que|yet)\b|;",
    re.IGNORECASE,
)


def _clauses(sentence: str) -> "List[str]":
    """The contrast clauses of a sentence — the whole sentence when it has
    no boundary (a single claim, the common case)."""
    parts = _CLAUSE_BOUNDARY.split(sentence)
    return [part for part in (p.strip() for p in parts) if part]


def _bound_units(sentence: str) -> "Tuple[set[str], set[str]]":
    """Per marker kind, the units whose clause carries exactly that marker.

    A clause naming both markers (``inside and outside ... respectively``)
    names no single claim the check can read, and a clause naming neither
    makes no membership assertion: the units of both stay unbound — silent,
    the check does not guess which side of a contrast a unit sits on.
    """
    inside_units: "set[str]" = set()
    outside_units: "set[str]" = set()
    for clause in _clauses(sentence):
        has_inside = _MEMBERSHIP_INSIDE.search(clause) is not None
        has_outside = _MEMBERSHIP_OUTSIDE.search(clause) is not None
        if has_inside == has_outside:  # both markers, or neither: unbindable
            continue
        units = {f"arg_{digits}" for digits in _UNIT_ID_RE.findall(clause)}
        if has_inside:
            inside_units |= units
        else:
            outside_units |= units
    return inside_units, outside_units


def _extension_membership_flags(
    sentence: str, frames: Dict[str, "set[str]"]
) -> List[Dict[str, Any]]:
    """#3157 — a unit said to sit INSIDE a cited frame must be a node of it.

    Only the units bound to an INSIDE clause are read: a unit whose clause
    puts it outside is trivially outside when the frame never held it —
    there is nothing to verify (#3204 rework)."""
    cited = _DUNG_CITATION_RE.findall(sentence)
    if not cited:
        return []
    units, _outside_units = _bound_units(sentence)
    if not units:
        return []
    flags: List[Dict[str, Any]] = []
    for frame_id in cited:
        nodes = frames.get(frame_id)
        if not nodes:
            continue
        off_frame = sorted(units - nodes)
        if off_frame:
            flags.append(
                {
                    "kind": "extension_membership_off_frame",
                    "sentence": sentence.strip(),
                    "measured": {
                        "frame": frame_id,
                        "off_frame_units": off_frame,
                        "frame_nodes": len(nodes),
                    },
                }
            )
    return flags


def _named_extensions_by_frame(
    state: Any,
) -> Dict[str, Dict[str, "List[List[str]]"]]:
    """#3157 extension half — the per-semantics extensions of every frame the
    run actually built, through the shared decoder.

    ``extension_lists`` is the per-frame primitive ``dung_reading`` itself
    calls; the merged view would read "some frame in the state", which the
    cited-frame rule forbids. Frames whose extensions were never computed,
    and the formalism sidecars, contribute nothing — a claim naming their
    semantics stays silent rather than reading as "the extension is empty".
    """
    from argumentation_analysis.reporting.restitution.native_dung import (
        extension_lists,
    )

    found: Dict[str, Dict[str, List[List[str]]]] = {}
    entries = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(entries, dict):
        return found
    for frame_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        if not (entry.get("arguments") or []):
            continue
        lists = extension_lists(entry)
        if lists:
            found[str(frame_id)] = lists
    return found


def _extension_claim_flags(
    sentence: str,
    frames: Dict[str, "set[str]"],
    extensions_by_frame: Dict[str, Dict[str, "List[List[str]]"]],
) -> List[Dict[str, Any]]:
    """#3157 extension half — a unit said to sit inside (or outside) a NAMED
    extension of the cited frame is checked against THAT extension.

    The frame half flags units the cited frame never held; this half flags
    units the frame holds but the named extension does not (a false inside
    claim, ``extension_membership_off_extension``), or the named extension
    holds while the sentence puts it outside (a false outside claim,
    ``extension_membership_false_outside``). A sentence naming no semantics,
    or a frame that did not compute the one it names, stays silent — the
    check does not guess. Membership alone decides, never the #3174
    rejection rule: an outside claim on an undecided unit is true.

    Two bindings the rework (#3204) tightened:

    - each unit is read against the marker of ITS OWN clause — a compound
      « arg_1 sits inside ..., while arg_2 lies outside it » carries two
      claims, and reading the units sentence-wide flagged both halves of
      every TRUE compound sentence;
    - a semantics can compute several extensions (two preferred): an inside
      claim is false only when NO extension holds the unit (the union),
      an outside claim only when EVERY extension does (the intersection) —
      « outside the preferred extension » must be true of one extension to
      be reportable, false only of them all.
    """
    cited = _DUNG_CITATION_RE.findall(sentence)
    if not cited:
        return []
    named = [sem for sem, pattern in _NAMED_SEMANTICS if pattern.search(sentence)]
    if not named:
        return []  # no semantics named: the frame half owns the claim
    # The semantics stays sentence-wide: the second clause says « outside
    # IT », and the it is the extension the first clause named.
    inside_units, outside_units = _bound_units(sentence)
    if not (inside_units or outside_units):
        return []
    flags: List[Dict[str, Any]] = []
    for frame_id in cited:
        nodes = frames.get(frame_id)
        if not nodes:
            continue  # off-frame units are the frame half's finding
        lists = extensions_by_frame.get(frame_id) or {}
        for sem in named:
            extensions = lists.get(sem)
            if extensions is None:
                continue  # the frame did not compute the semantics it names
            members_any: "set[str]" = set()
            for one in extensions:
                members_any.update(one)
            members_every: "set[str]" = (
                set.intersection(*(set(one) for one in extensions))
                if extensions
                else set()
            )
            if inside_units:
                wrong = sorted(
                    u for u in inside_units if u in nodes and u not in members_any
                )
                if wrong:
                    flags.append(
                        {
                            "kind": "extension_membership_off_extension",
                            "sentence": sentence.strip(),
                            "measured": {
                                "frame": frame_id,
                                "semantics": sem,
                                "units_not_in_extension": wrong,
                                "extension_members": sorted(members_any),
                            },
                        }
                    )
            if outside_units:
                wrong = sorted(u for u in outside_units if u in members_every)
                if wrong:
                    flags.append(
                        {
                            "kind": "extension_membership_false_outside",
                            "sentence": sentence.strip(),
                            "measured": {
                                "frame": frame_id,
                                "semantics": sem,
                                "units_in_extension": wrong,
                                "extension_members": sorted(members_every),
                            },
                        }
                    )
    return flags


def check_reading_license(
    text: str,
    state: Any,
    *,
    dense_threshold: float = 1.0,
    max_flags: int = 12,
) -> Dict[str, Any]:
    """Flag where a produced synthesis reads a qualifier as a conclusion.

    ``dense_threshold`` is the attack-density below which breadth is not
    robustness (one attack per argument). It is the same constant the briefing
    rule states, so the reader and the check never disagree.

    Returns ``{"flags": [...], "checked": {...}, "threshold": ...}``. An empty
    text yields no flag — nothing was produced, and an absent synthesis is
    already reported by its status, not by this check.
    """
    sentences = _sentences(text or "")
    measurements = _dung_measurements(state)
    causes = _formal_causes(state)
    fol_decisions = _fol_decisions(state)
    self_contradiction = "self_contradiction" in causes
    sparse_everywhere = bool(measurements) and all(
        m["density"] < dense_threshold for m in measurements
    )
    # #3151 — the weave-binding index: what the writer received, and where
    # each piece was bound when the evidence handed it over.
    counters_indexed = _index_counters(state)
    fact_counters = _fact_asserting_counters(state)
    units_indexed = _index_units(state)
    counter_scores = _counter_scores(state)
    # #3157 — the cited frame's own node sets, so a membership claim is read
    # against the frame the sentence names; and the same frames' extensions
    # per semantics (extension half, R1109), so an inside/outside claim is
    # read against the extension the sentence names.
    frames = _dung_frames_with_nodes(state)
    named_extensions = _named_extensions_by_frame(state)
    # #3150 — what the revision actually revised, and what the formal
    # contradiction actually names. Both are read once: the sentence loop only
    # compares them.
    base_units = _revision_base_units(state)
    formal_units = _formal_contradiction_units(state)
    # #3224 — the taxonomy nodes the act's own speaker detections sit under,
    # so an absence claim is read against the record's categories.
    detection_nodes = _speaker_detection_nodes(state)
    # The flags carry the sentence as produced — no slice: a cut could only
    # hide the qualifier the reader needs, and it never protected a verdict
    # (detection reads the whole sentence; #2850 asked what the cut was for,
    # and the answer was nothing).

    flags: List[Dict[str, Any]] = []
    for sentence in sentences:
        if len(flags) >= max_flags:
            break

        # -- a membership claim on a frame that never held the unit (#3157),
        # -- or on a named extension that does not hold it (R1109 half) --
        membership_flags = _extension_membership_flags(sentence, frames)
        claim_flags = _extension_claim_flags(sentence, frames, named_extensions)
        if membership_flags or claim_flags:
            flags.extend(membership_flags)
            flags.extend(claim_flags)
            continue

        # -- an absence in the analysis sold as an absence in the text (#3198) --
        # Like every branch of this loop, the ``continue`` means one flag per
        # sentence: a sentence that puts an absence in the text is not ALSO
        # tested by the later branches, and vice versa.
        text_absence_flags = _text_absence_flags(sentence)
        if text_absence_flags:
            flags.extend(text_absence_flags)
            continue

        # -- an absence the act's own detections contradict (#3224) --------
        contradicted = _contradicted_absence_flags(sentence, detection_nodes)
        if contradicted:
            flags.extend(contradicted)
            continue

        # -- breadth sold as robustness -------------------------------------
        robustness = _ROBUSTNESS_MARKERS.search(sentence)
        if (
            robustness is not None
            and _BREADTH_MARKERS.search(sentence) is not None
            and not _is_negated(sentence, robustness.start())
            and sparse_everywhere
        ):
            flags.append(
                {
                    "kind": "breadth_as_robustness",
                    "sentence": sentence,
                    "measured": {
                        "threshold": dense_threshold,
                        "frameworks": measurements,
                    },
                }
            )
            continue

        # -- a check that decided nothing, sold as strength (R1105b) --------
        if (
            robustness is not None
            and _FORMAL_CONSISTENCY_MARKERS.search(sentence) is not None
            and not _is_negated(sentence, robustness.start())
            and fol_decisions["vacuous_consistent"] > 0
            and fol_decisions["decisive"] == 0
        ):
            flags.append(
                {
                    "kind": "vacuous_consistency_as_strength",
                    "sentence": sentence,
                    "measured": {"fol": fol_decisions},
                }
            )
            continue

        # -- « la contradiction reste confinée », with no base in sight -----
        # #3150: the revision base is a PREFIX of the population, and its
        # conflicts are the fallacy negations. A containment sentence is only
        # about that base; when the formal contradiction's own units lie
        # entirely OUTSIDE it, the revision cannot have measured their extent —
        # yet the render credits it with the containment. The sentence escapes
        # the flag only by naming its base (socle / négations / sophismes),
        # which is what makes the claim licensed rather than borrowed.
        containment = _CONTAINMENT_MARKERS.search(sentence)
        if (
            containment is not None
            and base_units is not None
            and formal_units
            and not (formal_units & base_units)
            and _INCOHERENCE_MARKERS.search(sentence) is not None
            and _REVISION_BASE_MARKERS.search(sentence) is None
            and not _is_negated(sentence, containment.start())
        ):
            flags.append(
                {
                    "kind": "containment_outside_revision_base",
                    "sentence": sentence,
                    "measured": {
                        "revision_base_units": len(base_units),
                        "contradiction_units": sorted(formal_units),
                        "overlap": sorted(formal_units & base_units),
                    },
                }
            )
            continue

        # -- a cause misread as the discourse's ------------------------------
        if (
            _DISCOURSE_SUBJECTS.search(sentence) is not None
            and _INCOHERENCE_MARKERS.search(sentence) is not None
            and _QUALIFIERS.search(sentence) is None
            and not self_contradiction
        ):
            flags.append(
                {
                    "kind": "discourse_incoherence",
                    "sentence": sentence,
                    "measured": {"recorded_causes": causes},
                }
            )

    # #3151 — the binding flags ride after the sentence flags, within the
    # same max_flags budget: they read paragraphs, not sentences.
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text or "") if p.strip()]
    flags.extend(
        _weave_flags(
            paragraphs,
            state,
            counters_indexed,
            units_indexed,
            counter_scores,
            max_flags - len(flags),
        )
    )
    # #3158 — the change of voice rides after the binding flags, same budget:
    # it reads sentences, but only the paragraphs that carry an objection.
    flags.extend(
        _unattributed_claim_flags(paragraphs, fact_counters, max_flags - len(flags))
    )
    # #3158 (second instance) — a fallacy NAME stated as a finding must sit on
    # a unit a detector recorded one for.
    flags.extend(
        _unbacked_fallacy_name_flags(
            paragraphs, state, units_indexed, max_flags - len(flags)
        )
    )
    # #3308 — « pas de défaut » said of a unit the pass never examined. The
    # same family as the flag above, one turn further: not a NAME the state
    # does not hold, but an ABSENCE sold as a measured verdict.
    flags.extend(
        _no_defect_claim_flags(paragraphs, state, units_indexed, max_flags - len(flags))
    )

    # #3215 — how many units the render binds on the sound bar, over the same
    # paragraphs the weave checks read. Counted here, once, so the trace and
    # the flag cannot disagree on what "bound" means.
    _paragraph_tokens = [_weave_tokens(p) for p in paragraphs]
    bound_unit_count = sum(
        1
        for dist in units_indexed.values()
        if any(len(dist & toks) >= _BOUND_MIN_TOKENS for toks in _paragraph_tokens)
    )

    return {
        "flags": flags,
        "checked": {
            "sentences": len(sentences),
            "dung_frameworks": len(measurements),
            "recorded_causes": causes,
            "self_contradiction_recorded": self_contradiction,
            "fol_decisions": fol_decisions,
            "counters_with_target": len(counters_indexed),
            "counters_asserting_a_fact": len(fact_counters),
            "units_indexed": len(units_indexed),
            # #3215 — a check that stays silent must not read as a clean one.
            # This is how many units the render BINDS on the sound bar (two
            # distinctive tokens): 0 means the join could not hold on this
            # text (typically a prose in another language than the units),
            # not that every counter sits on its own unit.
            "units_bound_two_tokens": bound_unit_count,
            "dung_frames_with_nodes": len(frames),
            "named_extension_frames": len(named_extensions),
            "revision_base_units": len(base_units) if base_units is not None else 0,
            "contradiction_units": len(formal_units),
            "speaker_detection_nodes": len(detection_nodes),
        },
        "threshold": dense_threshold,
    }


def summarise_flags(report: Optional[Dict[str, Any]]) -> str:
    """One line a log or a gate verdict can print — never the text itself."""
    if not isinstance(report, dict):
        return ""
    flags = report.get("flags") or []
    if not flags:
        return ""
    kinds = sorted({str(f.get("kind")) for f in flags})
    return f"{len(flags)} reading-license flag(s): {', '.join(kinds)}"
