"""Encompassment axis detector (#1986) — the reader for the #1970 witnesses.

#1982 established that no executable path produces an encompassment verdict
(the three probed items all came back "n'a pas pu évaluer"). #1986 option 1
(settled by user arbitration) builds the instrument. This module is it.

SPEC — what "englobement" designates, in observable criteria
------------------------------------------------------------
L'englobement est un geste rhétorique totalisant : le locuteur absorbe
l'auditoire dans un corps unique dont il devient la voix, pour rendre une
conclusion inévitable. Quatre critères observables, applicables par un
second lecteur sans l'auteur :

C1 — apostrophe au collectif : le texte s'adresse à un « vous » pluriel
     constitué en masse (troupe, peuple, nation, fidèles, camarades), via
     des actes de parole directs — exhortation, injonction, promesse.
     Un interlocuteur singulier ou un public abstrait ne compte pas ;
     l'adresse administrative à des administrés est un « vous » pluriel
     sans totalisation et ne compte pas non plus.
C2 — « nous » fusionnel : un « nous » dont l'extension englobe à la fois
     l'énonciateur et l'auditoire, porté par un destin partagé (verbes de
     mouvement, de devenir, de destin). Le « nous » délibératif (nous qui
     raisonnons ensemble, nous = les auteurs) et le « nous » de l'offre
     (nous = l'entreprise, vous = les clients — le nous EXCLUT l'auditoire)
     ne comptent pas.
C3 — extrusion d'un ennemi : un « eux » extérieur au nous, construit avec
     une valence négative, dont l'exclusion consolide le nous. L'ennemi
     peut être un groupe humain, une force ou une menace figurée.
C4 — clôture eschatologique : le mouvement se ferme sur un horizon
     TERMINAL — victoire finale, jugement, fin d'un monde, avenir radieux,
     « pour toujours ». Un objectif proximate et réversible ( céder,
     signer, gagner un match) n'est pas une clôture eschatologique.

Firing rule (deterministic, computed in code from the criteria — the LLM
never emits the verdict, only the per-criterion judgments):

    fired  ⟺  C1 ∧ C2 ∧ (C3 ∨ C4)

C1∧C2 are the constitutive pair (absorb the audience, speak as the merged
body); the totalising closure is C3 OR C4. The disjunction is what makes
the #1970 witness ``20a53f0c`` (control_inversion: mass address, fused
"we", eschatological close, REFUSES enemy extrusion) a LIVE probe rather
than a negative defined by construction — per #1970, firing on it means
the detector reads form, which is defensible.

Three-state contract (#1977): ``state`` is
  True  — fired,
  False — evaluated and rejected (the rule ran and failed),
  None  — could not evaluate: a criterion the rule needs is undecidable
          (LLM returned null for C1, C2, or for both C3 and C4), the text
          is empty/too short, or the rubric output is unparseable.
A negative is NEVER fabricated where the axis did not turn.

Anti-pendules (#1986, binding):
  - not a keyword detector: the LLM judges STRUCTURE per criterion and
    must quote the span that carries it; the prompt explicitly says the
    lexeme "nous"/"ennemi" without the structure does not count (dev
    corpus item ``neg_deliberatif_01`` is the live control);
  - not a recycled ``_detect_escalation_patterns`` (escalation of
    fallacy severity per paragraph is a neighbouring, distinct notion);
  - validation is against the hand-annotated dev corpus
    (``tests/fixtures/encompassment/dev_corpus_1986.json``), never by
    agreement with another LLM judge on the same items.

LLM dependency is injectable (``LLMCallable = Callable[[str], str]``,
FB-29/38 pattern, mirrors ``agents/core/quality/agentic_virtue_detectors.py``).
No LLM wired ⟶ ``EncompassmentError`` raised — never a synthetic verdict.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

logger = logging.getLogger("encompassment")

# Reusable LLM callable contract: prompt string in, completion string out.
LLMCallable = Callable[[str], str]

CRITERIA = ("c1", "c2", "c3", "c4")

# Evidence quotes are corpus-derived when this runs on the encrypted
# dataset, so they are capped like every other corpus-derived field
# (privacy HARD — they stay in-process / under gitignored results/).
_QUOTE_CAP = 200
# Below this the text cannot carry the four criteria as a structure.
_MIN_TEXT_CHARS = 10


class EncompassmentError(RuntimeError):
    """Raised when the detector cannot run at all (no LLM callable wired).

    Fail-loud: the caller must see the missing dependency rather than
    receive a synthetic None/False "as if measured" — a None verdict is a
    measurement outcome (rubric undecidable), not a substitute for the
    instrument being absent.
    """


@dataclass(frozen=True)
class EncompassmentVerdict:
    """Three-state verdict + the per-criteria material it rests on.

    ``state``: True=fired, False=evaluated-rejected, None=could-not-
    evaluate (see module SPEC for the contract).
    ``criteria``: per-criterion judgment, True/False/None (None =
    undecidable on this text).
    ``evidence``: the quoted span carrying each criterion (may be empty
    for null/false criteria).
    ``reason``: populated when state is None — WHY it could not evaluate.
    """

    state: Optional[bool]
    criteria: Dict[str, Optional[bool]] = field(default_factory=dict)
    evidence: Dict[str, str] = field(default_factory=dict)
    note: str = ""
    reason: str = ""

    @property
    def fired(self) -> bool:
        return self.state is True


def verdict_from_criteria(criteria: Dict[str, Optional[bool]]) -> Optional[bool]:
    """Deterministic firing rule: C1 ∧ C2 ∧ (C3 ∨ C4), None-safe.

    Returns None when the rule cannot be evaluated (C1 or C2 or both C3/C4
    undecidable) — the #1977 boundary between "not evaluated" and
    "evaluated-rejected".
    """
    c1 = criteria.get("c1")
    c2 = criteria.get("c2")
    c3 = criteria.get("c3")
    c4 = criteria.get("c4")
    if c1 is None or c2 is None or (c3 is None and c4 is None):
        return None
    return bool(c1 and c2 and (c3 or c4))


_RUBRIC_PROMPT = """Tu évalues un texte sur l'axe de l'englobement rhétorique (geste totalisant : le locuteur absorbe l'auditoire dans un corps unique dont il devient la voix).

Définition en quatre critères OBSERVABLES. Juge la STRUCTURE, jamais le lexique seul : la présence du mot « nous » ou « ennemi » sans la structure ne vaut pas true ; inversement, une structure portée sans ces mots vaut true.

c1 — apostrophe au collectif : le texte s'adresse à un « vous » pluriel constitué en masse (troupe, peuple, nation, fidèles, camarades) via des actes de parole directs (exhortation, injonction, promesse). Un interlocuteur singulier, un public abstrait, ou une adresse administrative sans totalisation : false.
c2 — « nous » fusionnel : un « nous » englobant à la fois l'énonciateur et l'auditoire, porté par un destin partagé. Le « nous » délibératif (nous qui raisonnons) et le « nous » de l'offre (nous = l'entreprise, vous = les clients) : false.
c3 — extrusion d'un ennemi : un « eux » extérieur au nous, à valence négative, dont l'exclusion consolide le nous.
c4 — clôture eschatologique : le mouvement se ferme sur un horizon TERMINAL (victoire finale, jugement, fin d'un monde, « pour toujours »). Un objectif proximate et réversible : false.

Pour chaque critère : true / false / null (null = ce texte ne permet pas de juger ce critère). Chaque valeur non-null s'appuie sur une citation textuelle du passage qui la porte (max 40 mots) ; null exige une justification d'une phrase.

Texte lacunaire ou tronqué (marques « [lacune] », coupures, phrases inachevées) : renvoie null pour tout critère que les coupures empêchent d'établir — ne devine jamais le passage manquant. Un critère n'est true que si le texte fourni le montre ; s'il ne reste qu'un fragment nominal (« et nous, soldats... ») sans acte d'adresse et sans destin, c1 et c2 sont null, pas true.

Réponds par un UNIQUE objet JSON STRICT, rien d'autre (pas de texte avant/après) :
{"c1": true|false|null, "c2": true|false|null, "c3": true|false|null, "c4": true|false|null, "q1": "...", "q2": "...", "q3": "...", "q4": "...", "note": "..."}

Texte à évaluer :
<<<
{text}
>>>"""


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json_object(raw: str) -> str:
    """Isolate the JSON object from a raw completion (fences, prose around)."""
    fenced = _FENCE_RE.search(raw)
    candidate = fenced.group(1) if fenced else raw
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in output: {raw[:120]!r}")
    return candidate[start : end + 1]


def _parse_rubric_output(raw: str) -> Dict[str, object]:
    """Strict parse-or-reject of the rubric JSON.

    Every c1..c4 key must be present and be a bool or null; quote keys are
    optional strings. A half-formed rubric is not a rubric — the caller
    turns the ValueError into a None verdict with the reason.
    """
    data = json.loads(_extract_json_object(raw))
    if not isinstance(data, dict):
        raise ValueError(f"rubric output is not a JSON object: {type(data).__name__}")
    for key in CRITERIA:
        if key not in data:
            raise ValueError(f"rubric output missing criterion {key!r}")
        if data[key] not in (True, False, None):
            raise ValueError(
                f"criterion {key!r} must be true/false/null, got {data[key]!r}"
            )
    for key in ("q1", "q2", "q3", "q4", "note"):
        if key in data and not isinstance(data[key], str):
            raise ValueError(f"{key!r} must be a string, got {data[key]!r}")
    return data


def assess_encompassment(text: str, llm: LLMCallable) -> EncompassmentVerdict:
    """Evaluate ``text`` on the encompassment axis (three-state, #1977).

    The LLM judges the four criteria (with quoted evidence); the firing
    rule is computed here, deterministically, from those judgments.
    """
    if llm is None:
        raise EncompassmentError(
            "Encompassment detector has no LLM callable. Pass llm= (tests "
            "inject a stub; production wires the OpenRouter/OpenAI client). "
            "Fail-loud per #1986 — not returning a synthetic verdict."
        )
    stripped = (text or "").strip()
    if len(stripped) < _MIN_TEXT_CHARS:
        return EncompassmentVerdict(
            state=None,
            criteria={},
            evidence={},
            reason=f"text too short to carry the four criteria ({len(stripped)} chars)",
        )
    raw = llm(_RUBRIC_PROMPT.replace("{text}", stripped))
    try:
        data = _parse_rubric_output(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        return EncompassmentVerdict(
            state=None,
            criteria={},
            evidence={},
            reason=f"rubric output unparseable: {exc}",
        )
    criteria: Dict[str, Optional[bool]] = {
        key: data[key] for key in CRITERIA  # type: ignore[misc]
    }
    evidence = {
        f"q{i + 1}": str(data.get(f"q{i + 1}", ""))[:_QUOTE_CAP] for i in range(4)
    }
    state = verdict_from_criteria(criteria)
    reason = ""
    if state is None:
        undecidable = [k for k in CRITERIA if criteria[k] is None]
        reason = "rule needs an undecidable criterion: " + ", ".join(undecidable)
    return EncompassmentVerdict(
        state=state,
        criteria=criteria,
        evidence=evidence,
        note=str(data.get("note", ""))[:_QUOTE_CAP],
        reason=reason,
    )
