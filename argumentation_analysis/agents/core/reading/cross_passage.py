"""#3432 (ask 6b) — one claim contradicted by another passage, far away.

Cycle 3b of the panel (#3374) measured that the render states the thesis but
never examines it: among the judge's persistent M1-on-thesis items is an
**internal inconsistency between distant passages** — a claim another passage
of the same document contradicts, which no line of the analysis names. A
zero-shot *notices* such a tension; a formal lens **decides** it (#1644 step
D: point the lens at the passages that carry the thesis).

**The KB comes from the defining moves, not from the opening's units.** The
propositional phase formalises a stratified selection of the *extracted*
units: a pillar the extractor did not overlap never reaches that selection,
and the thesis the first reading names is not an extraction unit either.
This module is the other KB: the thesis, the mechanism and the pillars the
first reading named (#3442), each kept with its OWN verified quote and
offset — the document's characters, never a paraphrase (#3389's citation
rule, already applied by the first reading).

**The lens decides; a prompt never does.** One translation call, on a FREE
vocabulary (#2960's lesson: reusing atoms across independently translated
passages conjoins two meanings under one ``p`` and yields a mechanical UNSAT
pinned on the wrong formulas). The central batch is translated in ONE call
so its propositions mean the same thing on both sides of a contradiction —
the point of the check, since a separately-translated theory could never be
inconsistent for the right reason. Distant slots, those the selector would
never batch with the thesis, are also translated per slot, and every
candidate pair that carries a position is decided by SAT.

* ``status="inconsistent"`` — the central theory is UNSAT **or** a pair is:
  the render gets the two slots, each with its quote and its offset, and the
  minimal core the solver implicated. Only a solver verdict writes this.
* ``status="checked"`` — the central theory is SAT and no pair decided
  UNSAT: the honest « no inconsistency established » of the control
  document, never « the document is consistent » (a SAT theory of free
  propositions is the common case).
* ``status="undecided"`` — the reasoner answered None (degraded, JVM down,
  unparseable theory): an absence (#1941), stated, never a False.
* ``status="unreachable"`` — no reading, no quote, no translation, no LLM:
  the check was not reached, and the render says exactly which part failed.

No second opinion: the quotes and offsets are copied from the recorded
moves; a formula that will not parse is dropped and COUNTED; a pair whose
member has no position is not a finding a reader can locate, so it is not
reported as one (it still counts toward the coverage the record names).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

from argumentation_analysis.agents.core.reading.first_reading import defining_moves

logger = logging.getLogger("CrossPassageConsistency")

#: The slots that carry the thesis — the KB's population, in reading order.
CROSS_PASSAGE_SLOTS: Tuple[str, ...] = ("thesis", "mechanism", "pillar")

#: How far a translation batch may run: the central theory is one call, so a
#: long panel document's slots stay bounded. Declared, not tuned per call.
CROSS_PASSAGE_BATCH_CAP = 6

#: The per-slot quotes the solver keeps, verbatim, never re-anchored here.
#: A slot with no quote carries no evidence: it is counted, not translated.

_TRANSLATION_RULES = (
    "You are an expert in propositional logic. Translate each numbered "
    "passage below into propositional formulas.\n\n"
    "Rules:\n"
    "- Output ONLY a JSON object with one key per passage id, each mapping "
    "to a list of formula strings.\n"
    "- Operators: ! (not), && (and), || (or), => (implies), <=> (iff).\n"
    "- Proposition names are lowercase words or snake_case (e.g. "
    "policy_applied); never reuse one name for two different claims.\n"
    "- Each passage is translated on its own: keep its explicit claims and "
    "its negations. Do NOT add anything the passage does not say, do NOT "
    "resolve any contradiction you notice — the solver decides that.\n"
    "- Do not invent relations between passages that they do not state.\n"
)


def _parse_json_object(content: str) -> Dict[str, Any]:
    """The model's JSON, fenced or not; unreadable answers raise nothing."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text) if text else {}
    except (json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _slot_entries(state: Any) -> List[Dict[str, Any]]:
    """The thesis/mechanism/pillar moves, as named entries for the solver.

    Each entry carries the slot, a stable id, the kind, the recorded quote
    (verbatim, already citation-checked by the first reading) and its
    offset. A move without a slot (a local move) is not part of the KB; a
    slot with no quote is named in ``untranslated`` by the caller, never
    silently skipped.
    """
    entries: List[Dict[str, Any]] = []
    for index, move in enumerate(defining_moves(state)):
        slot = str(move.get("slot") or "")
        if slot not in CROSS_PASSAGE_SLOTS:
            continue
        quote = str(move.get("quote") or "")
        offset = move.get("offset")
        if not isinstance(offset, int) or isinstance(offset, bool):
            offset = None
        entries.append(
            {
                "id": f"s{index + 1}",
                "slot": slot,
                "kind": str(move.get("kind") or ""),
                "quote": quote,
                "offset": offset,
            }
        )
    return entries


def _translation_prompt(batch: Sequence[Dict[str, Any]]) -> str:
    """One call, one theory: the batch's propositions mean the same thing
    on both sides of a contradiction — the whole point of the check."""
    passages = "\n\n".join(
        f"Passage {entry['id']}:\n{entry['quote']}" for entry in batch
    )
    return _TRANSLATION_RULES + "\n" + passages


def _distance_pair(
    left: Dict[str, Any], right: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
    """Two positioned entries and their gap in characters."""
    left_start = int(left["offset"])
    right_start = int(right["offset"])
    gap = abs(right_start - left_start)
    return (left, right, gap)


def _positioned_pairs(
    entries: Sequence[Dict[str, Any]],
) -> List[Tuple[Dict[str, Any], Dict[str, Any], int]]:
    """Every pair that carries a position on both sides, farthest first.

    A pair whose member has no position is not a finding a reader can
    locate: the report needs both quotes AND both positions, so the check
    only decides pairs the render could name. The unpositioned entries stay
    in the central theory (their claims still count against the batch).
    """
    positioned = [e for e in entries if e["offset"] is not None and e["quote"]]
    pairs = [
        _distance_pair(positioned[i], positioned[j])
        for i in range(len(positioned))
        for j in range(i + 1, len(positioned))
    ]
    pairs.sort(key=lambda item: item[2], reverse=True)
    return pairs


def _finding(
    left: Dict[str, Any], right: Dict[str, Any], *, origin: str
) -> Dict[str, Any]:
    """The reader-facing pair: two slots, two verbatim quotes, two offsets.

    The quotes are the recorded moves' own characters — this module never
    re-writes, re-anchors or paraphrases them, so the render can run them
    through the citation rule and find them in the document.
    """
    return {
        "left": {k: left[k] for k in ("id", "slot", "kind", "quote", "offset")},
        "right": {k: right[k] for k in ("id", "slot", "kind", "quote", "offset")},
        "gap": abs(int(right["offset"]) - int(left["offset"])),
        "origin": origin,
    }


async def _decide(bridge: Any, formulas: Sequence[str]) -> Optional[bool]:
    """The lens's tri-state verdict on a theory: False is UNSAT, None is
    an absence (degraded reasoner, unparseable belief set). Never a bool()
    fold — #1634's tri-state is the whole point of the control case."""
    if not formulas:
        return None
    try:
        verdict, _msg = await asyncio.to_thread(
            bridge.check_consistency, "\n".join(formulas), "propositional"
        )
    except Exception as exc:  # the reasoner is absent or died mid-call
        logger.warning("CrossPassageConsistency: solver unavailable (%s)", exc)
        return None
    return verdict if isinstance(verdict, bool) else None


async def build_cross_passage_consistency(
    state: Any,
    llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
    bridge: Any = None,
) -> Dict[str, Any]:
    """Decide whether the thesis's own passages contradict one another.

    The lens is the wired propositional reasoner (TweetyBridge SAT), called
    over a theory built from the FIRST READING's slots — never from the
    extraction window. ``bridge`` is injectable for the offline witness;
    production leaves it None and the wired bridge is built here.
    """
    payload: Dict[str, Any] = {
        "status": "unreachable",
        "reason": "",
        "checked": 0,
        "dropped_formulas": 0,
        "unquoted_slots": [],
        "pairs_decided": 0,
        "findings": [],
        "basis": "cross_passage_consistency",
    }
    entries = _slot_entries(state)
    if not entries:
        payload["reason"] = "no_first_reading_slots"
        return payload

    quoted = [e for e in entries if e["quote"]]
    payload["unquoted_slots"] = [e["slot"] for e in entries if not e["quote"]]
    if not quoted:
        payload["reason"] = "no_verbatim_quote_on_any_slot"
        return payload

    central = quoted[:CROSS_PASSAGE_BATCH_CAP]

    if llm_callable is None:
        payload["reason"] = "no_llm_translation_route"
        return payload

    try:
        central_answer = await llm_callable(_translation_prompt(central))
    except Exception as exc:
        payload["reason"] = f"translation_failed: {type(exc).__name__}"
        return payload
    parsed = _parse_json_object(central_answer)
    central_formulas: List[str] = []
    for entry in central:
        raw = parsed.get(entry["id"])
        if isinstance(raw, list):
            central_formulas.extend(str(f).strip() for f in raw if str(f).strip())
    payload["dropped_formulas"] += sum(
        1
        for entry in central
        if not isinstance(parsed.get(entry["id"]), list) or not parsed.get(entry["id"])
    )
    if not central_formulas:
        payload["reason"] = "translation_produced_no_formula"
        return payload

    if bridge is None:
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )

        bridge = TweetyBridge()

    # 1. The central theory, one verdict over the whole batch. A SAT theory
    #    is the honest « no inconsistency established »; a None is the named
    #    absence, never a False (#1941).
    central_verdict = await _decide(bridge, central_formulas)
    payload["checked"] = len(central_formulas)
    if central_verdict is None:
        payload["status"] = "undecided"
        payload["reason"] = "the_reasoner_did_not_decide_the_central_theory"
        return payload

    # 2. The positioned pairs, farthest first. A pair is decided on its own
    #    members' formulas ONLY — the same per-slot translation on both
    #    sides, so a pair is never UNSAT on an unrelated batch formula. The
    #    first UNSAT pair is the finding, and the render can locate both
    #    passages. A pair with no formula on one side is not decidable:
    #    counted as skipped, never invented.
    slot_formulas = await _translate_per_slot(quoted, llm_callable)
    payload["checked"] += sum(len(fs) for fs in slot_formulas.values())
    findings: List[Dict[str, Any]] = []
    decided = 0
    for left, right, _gap in _positioned_pairs(quoted):
        left_formulas = slot_formulas.get(left["id"], [])
        right_formulas = slot_formulas.get(right["id"], [])
        if not left_formulas or not right_formulas:
            continue
        verdict = await _decide(bridge, left_formulas + right_formulas)
        decided += 1
        if verdict is False:
            findings.append(_finding(left, right, origin="positioned_pair"))
            break
    payload["pairs_decided"] = decided
    payload["findings"] = findings
    payload["status"] = (
        "inconsistent"
        if findings
        else ("inconsistent" if central_verdict is False else "checked")
    )
    if central_verdict is False and not findings:
        # The theory is UNSAT but no POSITIONED pair decides it: the render
        # names the theory's verdict with no located pair — the honest
        # absence of a citation, never a fabricated one (#1941).
        payload["reason"] = "unsat_theory_without_a_decided_positioned_pair"
    return payload


def _slot_label(entry: Dict[str, Any]) -> str:
    """The French name of a slot, for the reader-facing block."""
    if entry["slot"] == "thesis":
        return "la thèse"
    if entry["slot"] == "mechanism":
        return "le mécanisme"
    return "un pilier de la thèse"


def cross_passage_note(state: Any) -> str:
    """The one reader-facing block of the check (#3432 ask 6b, #1941).

    Two states, never a third: a decided record renders its verdict — the
    two verbatim quotes with their character positions when the lens
    implicated a pair, or the plain « no inconsistency established » of a
    SAT theory — and an undecided or unreachable record renders its named
    absence. The quotes are the moves' own characters (already citation-
    checked by the first reading), printed between « » with their position
    stated in characters, so the reader can find both passages.

    Empty on a state that carries no record at all (bare doubles): the
    prompt then omits the section rather than putting a producer's
    vocabulary where none ran — the #3395 rule.
    """
    record = getattr(state, "cross_passage_consistency", None)
    if isinstance(state, dict):
        record = state.get("cross_passage_consistency")
    if not isinstance(record, dict):
        return ""
    status = str(record.get("status") or "")
    if status not in ("inconsistent", "checked", "undecided", "unreachable"):
        return ""
    lines: List[str] = [
        "[COHÉRENCE ENTRE PASSAGES ÉLOIGNÉS — contrôle par le raisonneur "
        "propositionnel]"
    ]
    if status == "inconsistent":
        for finding in record.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            left = finding.get("left") or {}
            right = finding.get("right") or {}
            if not (isinstance(left, dict) and isinstance(right, dict)):
                continue
            gap = finding.get("gap")
            lines.append(
                "Le solveur établit une contradiction entre deux passages "
                f"à {gap} caractères d'écart :"
            )
            for entry in (left, right):
                quote = str(entry.get("quote") or "")
                offset = entry.get("offset")
                if quote and isinstance(offset, int):
                    lines.append(
                        f"  — {_slot_label(entry)} « {quote} » " f"(position {offset})"
                    )
                else:
                    lines.append(f"  — {_slot_label(entry)} : citation non localisable")
            lines.append(
                "Aucune ligne du texte ne dit laquelle des deux positions "
                "l'emporte : le contrôle ne tranche pas, il constate."
            )
        if len(lines) == 1:
            # An inconsistent record with no readable finding: the verdict
            # exists, the located pair does not — stated, not decorated.
            lines.append(
                "Le solveur établit une contradiction dans la théorie, sans "
                f"qu'aucune paire localisable ne la porte ({record.get('reason') or 'sans paire décidée'})."
            )
    elif status == "checked":
        lines.append(
            "Contrôle atteint : le solveur n'établit aucune contradiction "
            f"entre les passages porteurs de la thèse ({record.get('checked') or 0} "
            "formules vérifiées)."
        )
    else:
        reason = str(record.get("reason") or "")
        suffix = f" ({reason})" if reason else ""
        word = "non tranche" if status == "undecided" else "non atteint"
        lines.append(f"Contrôle {word}{suffix} : aucune incohérence rapportée.")
    return "\n".join(lines)


async def _translate_per_slot(
    entries: Sequence[Dict[str, Any]],
    llm_callable: Callable[[str], Awaitable[str]],
) -> Dict[str, List[str]]:
    """Each slot's own formulas, one call per slot.

    A pair is decided on these formulas, so a pair's UNSAT is a statement
    about its two passages alone — not about the batch. One call per slot
    keeps each passage's atoms within its own vocabulary (#2960), and the
    pair verdict stays meaningful because BOTH sides are translated with
    the same free-vocabulary rule. A slot with no formula is simply absent
    from the map: its pairs are skipped, never decided.
    """
    per_slot: Dict[str, List[str]] = {}
    for entry in entries:
        try:
            answer = await llm_callable(_translation_prompt([entry]))
        except Exception:
            continue
        raw = _parse_json_object(answer).get(entry["id"])
        formulas = (
            [str(f).strip() for f in raw if str(f).strip()]
            if isinstance(raw, list)
            else []
        )
        if formulas:
            per_slot[entry["id"]] = formulas
    return per_slot


__all__ = [
    "CROSS_PASSAGE_SLOTS",
    "build_cross_passage_consistency",
    "cross_passage_note",
]
