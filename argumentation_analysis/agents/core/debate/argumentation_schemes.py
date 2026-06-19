"""Dialogical argumentation schemes — Walton-style scheme table + classifier.

G8 (#1184, Epic #1165 enrichment). The trunk debate (``agents/core/debate/``)
had the protocol scaffold and a doc-string mention of "10 argumentation schemes"
(``__init__.py:16``), but NO active scheme matcher: ``FormalArgument.scheme``
(``protocols.py:75``) was never populated, and the LLM debate path
(``invoke_callables._invoke_debate_analysis``) produced ``key_exchanges`` with no
scheme grounding. This restored the engine dropped at the #35 unification
(β fidelity-audit gap G8).

Adapted FAITHFULLY (anti-pendule: restore, don't fabricate) from the student
deliverable ``1_2_7_argumentation_dialogique/local_db_arg/src/core/argumentation_engine.py``
→ ``_load_argumentation_schemes()`` (SANCTUARY, read-only reference). The 10
schemes and their ``strength`` values are the student's verbatim. The
``critical_questions`` are the CANONICAL Walton critical questions for each
scheme (canonical knowledge base, not fabricated) — the student engine had none;
adding them realises the Walton-Krabbe grounding the deliverable claimed.

``classify_scheme(text)`` is a DETERMINISTIC lexical matcher — no LLM, no JVM.
Fail-loud (#1019): it returns ``None`` when no scheme's keyword set fires, NEVER
a fabricated scheme label. If the genuine engine yields no match on a corpus,
that is the honest result.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArgumentationScheme:
    """One Walton-style argumentation scheme.

    ``strength`` is the student engine's default (a prior on scheme force, not a
    measured score). ``critical_questions`` are the canonical Walton questions a
    challenger asks to test the scheme — surfaced so a debate exchange can name
    the scheme AND the test that stresses it.
    """

    key: str
    label: str
    premises_pattern: List[str]
    conclusion_pattern: str
    strength: float
    critical_questions: List[str] = field(default_factory=list)


def _load_argumentation_schemes() -> Dict[str, ArgumentationScheme]:
    """Load the 10 argumentation schemes (restored from student deliverable).

    Faithful adaptation of ``argumentation_engine._load_argumentation_schemes``:
    same 10 keys, same ``strength`` values. Critical questions added from the
    canonical Walton corpus (the student engine carried none).
    """
    return {
        "modus_ponens": ArgumentationScheme(
            key="modus_ponens",
            label="Déduction (modus ponens)",
            premises_pattern=["P", "P → Q"],
            conclusion_pattern="Q",
            strength=1.0,
            critical_questions=[
                "La prémisse P est-elle effectivement établie ?",
                "L'implication P → Q est-elle valide (pas un sophisme conditionnel) ?",
            ],
        ),
        "expert_opinion": ArgumentationScheme(
            key="expert_opinion",
            label="Argument d'autorité (advice of an expert)",
            premises_pattern=[
                "Expert E says P",
                "E is expert in domain D",
                "P is in domain D",
            ],
            conclusion_pattern="P",
            strength=0.8,
            critical_questions=[
                "E est-elle réellement une source experte sur ce domaine ?",
                "L'avis de E est-il cohérent avec le consensus des autres experts ?",
                "Y a-t-il une preuve directe (au-delà du seul témoignage) ?",
            ],
        ),
        "analogy": ArgumentationScheme(
            key="analogy",
            label="Argument par analogie",
            premises_pattern=[
                "Case A has property X",
                "Case B is similar to A",
                "X is relevant",
            ],
            conclusion_pattern="Case B has property X",
            strength=0.6,
            critical_questions=[
                "En quoi les cas A et B sont-ils réellement similaires sur la dimension pertinente ?",
                "Existe-t-il une différence pertinente qui brise l'analogie ?",
            ],
        ),
        "cause_effect": ArgumentationScheme(
            key="cause_effect",
            label="Argument de cause à effet",
            premises_pattern=["A causes B", "A occurred"],
            conclusion_pattern="B will occur",
            strength=0.7,
            critical_questions=[
                "La relation causale A → B est-elle établie (et non une simple corrélation) ?",
                "Y a-t-il d'autres causes possibles de B ?",
            ],
        ),
        "consensus": ArgumentationScheme(
            key="consensus",
            label="Argument d'ad hominem consensuel (appeal to consensus)",
            premises_pattern=[
                "Majority of experts agree on P",
                "Experts are qualified",
                "No systematic bias",
            ],
            conclusion_pattern="P is likely true",
            strength=0.85,
            critical_questions=[
                "Le consensus est-il largement partagé (et non une minorité bruyante) ?",
                "Les experts sont-ils exempts de biais systématiques ?",
            ],
        ),
        "empirical_evidence": ArgumentationScheme(
            key="empirical_evidence",
            label="Argument empirique (from evidence)",
            premises_pattern=[
                "Data shows P",
                "Data is reliable",
                "Sample is representative",
            ],
            conclusion_pattern="P is supported by evidence",
            strength=0.9,
            critical_questions=[
                "Les données sont-elles fiables (collecte, mesure) ?",
                "L'échantillon est-il représentatif de la population visée ?",
            ],
        ),
        "economic_argument": ArgumentationScheme(
            key="economic_argument",
            label="Argument économique (cost-benefit)",
            premises_pattern=["Action A costs X", "Action A benefits Y", "Y > X"],
            conclusion_pattern="Action A is economically justified",
            strength=0.75,
            critical_questions=[
                "Le calcul coût/bénéfice inclut-il tous les coûts externes ?",
                "Les bénéfices Y sont-ils réellement supérieurs aux coûts X une fois actualisés ?",
            ],
        ),
        "precautionary_principle": ArgumentationScheme(
            key="precautionary_principle",
            label="Principe de précaution",
            premises_pattern=[
                "Risk R is possible",
                "R has severe consequences",
                "Prevention is possible",
            ],
            conclusion_pattern="Prevention should be taken",
            strength=0.7,
            critical_questions=[
                "Le risque R est-il suffisamment plausible (et non spéculatif) ?",
                "Le coût de la prévention est-il proportionné à la gravité de R ?",
            ],
        ),
        "moral_argument": ArgumentationScheme(
            key="moral_argument",
            label="Argument moral (from rights)",
            premises_pattern=[
                "Action A affects group G",
                "G has rights",
                "A violates rights",
            ],
            conclusion_pattern="Action A is morally wrong",
            strength=0.8,
            critical_questions=[
                "L'action A viole-t-elle réellement un droit de G ?",
                "Existe-t-il un droit concurrent qui justifierait A ?",
            ],
        ),
        "historical_precedent": ArgumentationScheme(
            key="historical_precedent",
            label="Argument à partir d'un précédent historique",
            premises_pattern=[
                "Situation S occurred before",
                "S led to outcome O",
                "Current situation similar to S",
            ],
            conclusion_pattern="Outcome O is likely",
            strength=0.65,
            critical_questions=[
                "La situation actuelle est-elle réellement analogue à S ?",
                "Les conditions causales de O en S sont-elles réunies aujourd'hui ?",
            ],
        ),
    }


# Keyword sets for the deterministic classifier. Each set is the lexical
# signature of its scheme (lowercased substrings). A scheme fires when ALL its
# keywords appear (AND within the text) — conservative, favours precision over
# recall so we don't mislabel. Tuned to FR + EN argumentative vocabulary.
_SCHEME_KEYWORDS: Dict[str, List[List[str]]] = {
    # Multiple alternative keyword-sets per scheme (any set firing ⇒ scheme).
    "expert_opinion": [
        ["expert", "domaine"],
        ["selon", "spécialiste"],
        ["autorité", "compétent"],
        ["source", "expert"],
    ],
    "analogy": [
        ["analogue", "similaire"],
        ["comme", "semblable"],
        ["à l'instar", "comparable"],
    ],
    "cause_effect": [
        ["cause", "effet"],
        ["entraîne", "conséquence"],
        ["provoque", "résultat"],
        ["donc", "parce que"],
    ],
    "consensus": [
        ["consensus", "experts"],
        ["majorité", "accord"],
        ["unanime", "scientifiques"],
    ],
    "empirical_evidence": [
        ["données", "représentatif"],
        ["étude", "mesure"],
        ["statistique", "échantillon"],
        ["résultat", "expérience"],
    ],
    "economic_argument": [
        ["coût", "bénéfice"],
        ["économique", "rentable"],
        ["investissement", "retour"],
    ],
    "precautionary_principle": [
        ["risque", "prévention"],
        ["principe de précaution"],
        ["danger", "éviter"],
    ],
    "moral_argument": [
        ["droit", "violation"],
        ["morale", "devoir"],
        ["éthique", "injuste"],
        ["droits", "atteinte"],
    ],
    "historical_precedent": [
        ["précédent", "historique"],
        ["déjà", "passé"],
        ["autrefois", "abouti"],
    ],
    "modus_ponens": [
        ["donc", "implique"],
        ["par conséquent", "si"],
    ],
}


def classify_scheme(text: str) -> Optional[ArgumentationScheme]:
    """Deterministically classify a text to its argumentation scheme.

    No LLM, no JVM — a lexical matcher over ``_SCHEME_KEYWORDS``. Returns the
    matching ``ArgumentationScheme`` (first scheme whose any keyword-set fires,
    in the table's canonical order — modus_ponens last as the weakest signal),
    or ``None`` when nothing matches.

    Fail-loud (#1019): ``None`` is an honest "no scheme matched", NEVER a
    fabricated label. Anti-pendule: this is a conservative classifier — it
    prefers returning None over mislabelling. If a corpus yields no match, the
    debate surfaces the exchange WITHOUT a scheme label rather than inventing one.
    """
    if not text:
        return None
    lowered = text.lower()
    schemes = _load_argumentation_schemes()
    # Canonical order: specific schemes first, modus_ponens (weakest lexical
    # signal — "donc" is everywhere) last so it only fires when nothing stronger
    # matches.
    order = [
        "expert_opinion",
        "empirical_evidence",
        "consensus",
        "analogy",
        "cause_effect",
        "economic_argument",
        "precautionary_principle",
        "moral_argument",
        "historical_precedent",
        "modus_ponens",
    ]
    for key in order:
        keyword_sets = _SCHEME_KEYWORDS.get(key, [])
        for kset in keyword_sets:
            if all(kw in lowered for kw in kset):
                scheme = schemes.get(key)
                if scheme is not None:
                    logger.debug(
                        "Scheme classified: %s (matched keywords %s)",
                        key,
                        kset,
                    )
                    return scheme
    return None


def schemes_as_prompt_context(limit: int = 10) -> str:
    """Render the scheme table as a knowledge-base block for the LLM prompt.

    Hands the LLM the real Walton schemes + their critical questions so a debate
    exchange can be scheme-grounded. Capped to keep the prompt budget sane.
    """
    schemes = _load_argumentation_schemes()
    lines: List[str] = []
    for i, key in enumerate(list(schemes.keys())[:limit], start=1):
        s = schemes[key]
        qs = " ; ".join(s.critical_questions[:2])
        lines.append(
            f"  {i}. « {s.label} » (force a priori {s.strength:.2f}) — questions "
            f"critiques de test : {qs}"
        )
    return "\n".join(lines)
