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

**The lens decides; a prompt never does.** Every translation batch is ONE
call on a FREE vocabulary (#2960's lesson: two independently translated
passages name their atoms independently, so their union is trivially SAT —
nothing is ever located — or UNSAT by a name collision — a fabricated
contradiction). A positioned pair is decided on that ONE call's per-entry
formulas, so a pair's UNSAT is a statement about its two passages. The
pair search runs only when a batch theory is UNSAT, and only to LOCATE its
core: the farthest pair whose union is UNSAT while each member is SAT on
its own. A slot that contradicts itself alone is a single-passage case,
named as such — never printed as a pair. Every batch carries the thesis,
so no pair ever spans two calls; pairs that would are counted, never
guessed.

* ``status="inconsistent"`` — a batch theory is UNSAT: the render gets the
  located pair (two slots, each with its quote and its offset) when the
  core is two passages, or the named single-passage case / the theory's
  verdict when no located pair carries it. Only a solver verdict writes
  this.
* ``status="checked"`` — every batch theory is SAT: the honest « no
  inconsistency established » of the control document, never « the document
  is consistent » (a SAT theory of free propositions is the common case).
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

#: How many quoted slots one translation batch may carry. Every batch holds
#: the thesis plus up to this many minus one others: declared, not tuned.
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
    in the batch theory (their claims still count against the batch).
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

    One vocabulary per batch (#2960): every batch is ONE translation call,
    and a positioned pair is decided on that call's OWN per-entry formulas.
    The pair search runs only when a batch theory is UNSAT — a pair subset
    of a SAT theory is SAT — and only to locate the core: the farthest pair
    whose union is UNSAT while each member alone is SAT. A slot that is
    UNSAT on its own is named as a single-passage case, never one side of a
    pair. Every batch carries the thesis; a pair never spans two batches.
    """
    payload: Dict[str, Any] = {
        "status": "unreachable",
        "reason": "",
        "checked": 0,
        "dropped_formulas": 0,
        "unquoted_slots": [],
        "pairs_decided": 0,
        "findings": [],
        "single_passage_unsat": [],
        "cross_batch_pairs_not_decided": 0,
        "batches": 0,
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

    if llm_callable is None:
        payload["reason"] = "no_llm_translation_route"
        return payload

    # Thesis-anchored batches: every batch carries the thesis (or the first
    # quoted slot when no thesis is quoted), so no pair ever spans two
    # calls, and every quoted slot joins exactly one batch beside it.
    anchor = next((e for e in quoted if e["slot"] == "thesis"), quoted[0])
    others = [e for e in quoted if e is not anchor]
    stride = CROSS_PASSAGE_BATCH_CAP - 1
    batches = [
        [anchor] + others[i : i + stride] for i in range(0, len(others), stride)
    ] or [[anchor]]
    payload["batches"] = len(batches)

    if bridge is None:
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )

        bridge = TweetyBridge()

    findings: List[Dict[str, Any]] = []
    decided_pairs = 0
    saw_unsat = False
    saw_undecided = False
    for batch in batches:
        try:
            answer = await llm_callable(_translation_prompt(batch))
        except Exception as exc:
            payload["reason"] = f"translation_failed: {type(exc).__name__}"
            return payload
        parsed = _parse_json_object(answer)
        formulas_by_id: Dict[str, List[str]] = {}
        batch_formulas: List[str] = []
        for entry in batch:
            raw = parsed.get(entry["id"])
            if isinstance(raw, list) and raw:
                entry_formulas = [str(f).strip() for f in raw if str(f).strip()]
                if entry_formulas:
                    formulas_by_id[entry["id"]] = entry_formulas
                    batch_formulas.extend(entry_formulas)
                    continue
            payload["dropped_formulas"] += 1
        if not batch_formulas:
            payload["reason"] = "translation_produced_no_formula"
            return payload

        # One verdict over the whole batch: its formulas share one
        # vocabulary, so an UNSAT is a statement about the passages, never
        # about two translations' name collisions.
        verdict = await _decide(bridge, batch_formulas)
        payload["checked"] += len(batch_formulas)
        if verdict is None:
            saw_undecided = True
            continue
        if verdict is True:
            # A pair subset of a SAT theory is SAT: the search runs only
            # when the theory is UNSAT, and only to LOCATE its core.
            continue

        saw_unsat = True
        # A slot whose own formulas are UNSAT contradicts ITSELF: that is a
        # single-passage case, named here, never one side of a pair.
        solo_verdicts = {}
        for entry in batch:
            entry_formulas = formulas_by_id.get(entry["id"])
            if not entry_formulas:
                continue
            solo_verdicts[entry["id"]] = await _decide(bridge, entry_formulas)
            if solo_verdicts[entry["id"]] is False:
                if entry["id"] not in payload["single_passage_unsat"]:
                    payload["single_passage_unsat"].append(entry["id"])
        for left, right, _gap in _positioned_pairs(batch):
            if (
                solo_verdicts.get(left["id"]) is not True
                or solo_verdicts.get(right["id"]) is not True
            ):
                continue
            left_formulas = formulas_by_id.get(left["id"])
            right_formulas = formulas_by_id.get(right["id"])
            if not left_formulas or not right_formulas:
                continue
            decided_pairs += 1
            if await _decide(bridge, left_formulas + right_formulas) is False:
                findings.append(_finding(left, right, origin="positioned_pair"))
                break  # farthest first: one located core per batch

    # Pairs spanning two batches were never decided — one vocabulary per
    # call is the whole point (#2960). Counted, named, never guessed.
    batch_index = {
        entry["id"]: index
        for index, batch in enumerate(batches)
        for entry in batch
        if entry is not anchor
    }
    cross_batch = 0
    for left, right, _gap in _positioned_pairs(quoted):
        if left is anchor or right is anchor:
            continue  # the anchor shares every batch
        if batch_index.get(left["id"]) != batch_index.get(right["id"]):
            cross_batch += 1
    payload["cross_batch_pairs_not_decided"] = cross_batch

    payload["pairs_decided"] = decided_pairs
    payload["findings"] = findings
    if findings or saw_unsat:
        payload["status"] = "inconsistent"
        if not findings:
            if payload["single_passage_unsat"]:
                payload["reason"] = (
                    "unsat_theory_including_single_passage: "
                    + ",".join(payload["single_passage_unsat"])
                )
            else:
                # The theory is UNSAT but no POSITIONED pair decides it: the
                # render names the theory's verdict with no located pair —
                # the honest absence of a citation, never a fabricated one
                # (#1941).
                payload["reason"] = "unsat_theory_without_a_decided_positioned_pair"
    elif saw_undecided:
        payload["status"] = "undecided"
        payload["reason"] = "the_reasoner_did_not_decide_a_batch_theory"
    else:
        payload["status"] = "checked"
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
            single = record.get("single_passage_unsat") or []
            if single:
                lines.append(
                    "Le solveur établit une contradiction interne à un seul "
                    "passage ("
                    + ", ".join(str(s) for s in single)
                    + ") ; aucune paire de passages éloignés n'a été établie."
                )
            else:
                # An inconsistent record with no readable finding: the
                # verdict exists, the located pair does not — stated, not
                # decorated.
                lines.append(
                    "Le solveur établit une contradiction dans la théorie, sans "
                    f"qu'aucune paire localisable ne la porte ({record.get('reason') or 'sans paire décidée'})."
                )
    elif status == "checked":
        line = (
            "Contrôle atteint : le solveur n'établit aucune contradiction "
            f"entre les passages porteurs de la thèse ({record.get('checked') or 0} "
            "formules vérifiées)."
        )
        lines.append(line)
    else:
        reason = str(record.get("reason") or "")
        suffix = f" ({reason})" if reason else ""
        word = "non tranche" if status == "undecided" else "non atteint"
        lines.append(f"Contrôle {word}{suffix} : aucune incohérence rapportée.")
    skipped = record.get("cross_batch_pairs_not_decided") or 0
    if skipped:
        lines.append(
            f"{skipped} paire(s) réparties entre deux lots de traduction "
            "restent non décidées."
        )
    dropped = record.get("dropped_formulas") or 0
    if dropped:
        lines.append(f"{dropped} passage(s) sans traduction exploitable.")
    return "\n".join(lines)


__all__ = [
    "CROSS_PASSAGE_SLOTS",
    "build_cross_passage_consistency",
    "cross_passage_note",
]
