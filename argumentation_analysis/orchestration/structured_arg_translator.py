"""Text→structured translator for bipolar/ABA formalisms (TR-1 #1419 / FP-17 #1236).

The structured-argumentation reasoners read formalism-specific artifacts from
the pipeline ``context`` — ``supports`` for bipolar argumentation, ``contraries``
for ABA. Until now nothing populated those keys from real text, so the five
structured formalisms ran on auto-shaped synthetic input and were honestly
labelled ``absent_no_translator`` by
:func:`state_writers._record_structured_arg_status`.

This module wires the FIRST translator: an LLM that, given the already-extracted
arguments + the source text, derives genuine **support** relations (bipolar) and
**assumption↔contrary** pairs (ABA) *from the text*. It is invoked lazily inside
``_invoke_bipolar`` / ``_invoke_aba`` (:mod:`invoke_callables`) only when no
genuine structured input was supplied by the caller — so a caller that already
provides real artifacts is never overridden.

Anti-théâtre HARD (#1019)
-------------------------
Relations returned by the LLM are **validated against the real argument
inventory**. The arguments are handed to the LLM as an enumerated list
(``arg1``..``argN``) and it must cite relations *by id*. Any relation that
references an id not in the inventory, or is otherwise malformed, is dropped.
If after validation nothing remains, the translator returns a
``TranslationResult`` whose ``cause`` discriminates *why* (the LLM ran and
found no genuine relations · no API key configured · the call raised) — never a
fabricated evaluation ("soustraire le gap, pas contourner le garde"). The
caller propagates ``cause`` into the context so
``_record_structured_arg_status`` labels the axis with its true status
(``no_genuine_relations`` / ``translator_unconfigured`` / ``translator_failed``)
instead of the #1236-era ``absent_no_translator`` catch-all (#1608). The
honest-absent gate itself is never modified: this module only feeds it genuine
input + a discriminated cause.

Privacy HARD
------------
LLM user content is the source text (truncated) + argument labels — never
committed. Outputs (supports/contraries referencing opaque arg labels) live in
gitignored state artifacts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger("UnifiedPipeline")


class TranslatorUnconfigured(RuntimeError):
    """No LLM API key configured (#1608).

    Distinct from a runtime failure: the translator could not even attempt
    the work. Raised inside ``_llm_extract_relations`` and caught by each
    translator, which labels the axis ``translator_unconfigured`` rather than
    collapsing onto ``absent_no_translator``.
    """


# Discriminated causes for a structured-arg translation (#1608). The four
# values map 1:1 to the four statuses the recorder emits — a translator must
# never silently return an empty result without one of them.
CAUSE_EVALUATED = "evaluated"
CAUSE_TRANSLATOR_FAILED = "translator_failed"
CAUSE_NO_GENUINE_RELATIONS = "no_genuine_relations"
CAUSE_TRANSLATOR_UNCONFIGURED = "translator_unconfigured"


@dataclass
class TranslationResult:
    """Outcome of a structured-arg translation, carrying the discriminated cause.

    Replaces the bare ``[]`` / ``{}`` return that collapsed four distinct
    causes (translator raised · translator ran and found nothing · no API key
    · empty inventory) onto a single ``absent_no_translator`` label. The
    caller propagates ``cause`` into the pipeline context so
    :func:`state_writers._record_structured_arg_status` can label the axis
    honestly — *fail loud, not fail hard* (#1597): the run still completes,
    but the reason it ran degraded is now visible and attributed to its true
    cause, not the #1236-era "no translator" story.
    """

    relations: Any  # list | dict — the validated relations (empty when none)
    cause: str  # one of the CAUSE_* constants above
    error: str = ""  # exception type name, only when cause == translator_failed


# Cap the argument inventory handed to the LLM so prompt + response stay bounded
# (mirrors the [:40] cap in _extract_arguments_from_context, #708). Bipolar/ABA
# relations over a larger inventory would blow the JSON token ceiling without
# adding analytical value for a PoC.
_MAX_INVENTORY = 20


def _build_inventory(
    arguments: List[str],
) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    """Enumerate the real arguments as ``{id: text}`` + the LLM-facing list.

    Skips empty/whitespace entries. Returns ``(arg_by_id, listed)`` where
    ``arg_by_id`` maps ``arg1``..``argN`` → canonical text and ``listed`` is the
    JSON-serializable ``[{"id": "arg1", "text": "..."}]`` handed to the LLM.
    """
    cleaned = [a.strip() for a in arguments if isinstance(a, str) and a.strip()]
    cleaned = cleaned[:_MAX_INVENTORY]
    arg_by_id: Dict[str, str] = {f"arg{i + 1}": text for i, text in enumerate(cleaned)}
    listed = [{"id": k, "text": v} for k, v in arg_by_id.items()]
    return arg_by_id, listed


async def _llm_extract_relations(
    input_text: str, arguments: List[str], relation_kind: str
) -> Dict[str, Any]:
    """Call the LLM to extract ``relation_kind`` relations over the inventory.

    Mirrors the :func:`_invoke_fact_extraction` call shape (guarded completion,
    determinism params, JSON mode, ``_parse_json_from_llm``). Returns the parsed
    JSON dict (possibly empty). Raises on no-API-key / unrecoverable call failure
    so the caller can fall back to honest-absent.

    ``relation_kind`` is ``"supports"`` or ``"contraries"`` and drives the prompt
    + the expected JSON shape.
    """
    # Lazy import: invoke_callables imports this module lazily from the handlers,
    # so importing its helpers here is safe at call time (no module-load cycle).
    from argumentation_analysis.orchestration.invoke_callables import (
        _get_determinism_params,
        _get_openai_client,
        _guarded_chat_completion,
        _parse_json_from_llm,
    )

    arg_by_id, listed = _build_inventory(arguments)
    if not arg_by_id:
        logger.debug(
            "%s translator: empty argument inventory — nothing to relate.",
            relation_kind,
        )
        return {}

    client, model_id = _get_openai_client()
    if client is None:
        logger.info(
            "%s translator: no LLM API key configured — cannot translate.",
            relation_kind,
        )
        raise TranslatorUnconfigured("no LLM API key configured")

    inventory_json = ", ".join(
        f'{{"id":"{a["id"]}","text":"{a["text"][:140]}"}}' for a in listed
    )

    if relation_kind == "supports":
        task = (
            "Identify SUPPORT relations between these arguments: a support is a "
            "pair (source, target) where the source argument *reinforces or "
            "entails* the target argument's conclusion. Only relate arguments "
            "present in the inventory (cite by id)."
        )
        shape = (
            '{"supports": [{"source": "argN", "target": "argM", '
            '"rationale": "one short sentence"}]}'
        )
    elif relation_kind == "contraries":
        task = (
            "Identify ASSUMPTIONS and their CONTRARIES among these arguments: an "
            "assumption is a premise taken on faith (arguable), and its contrary "
            "is the sentence that would defeat it (often its negation). Only name "
            "assumptions present in the inventory (cite by id); the contrary is "
            "free-form text."
        )
        shape = (
            '{"contraries": [{"assumption": "argN", "contrary": "defeating sentence", '
            '"rationale": "one short sentence"}]}'
        )
    elif relation_kind == "aspic_rules":
        task = (
            "Identify DEFEASIBLE INFERENCE rules, CONTRADICTIONS, and UNDERCUTS "
            "among these arguments:\n"
            "- A RULE is (premises, conclusion) where the premise argument(s) "
            "defeasibly lead to — justify — the conclusion argument. Give each "
            "rule a short stable `name` so an undercut can reference it.\n"
            "- A CONTRADICTION is (attacker, target): the attacker argument "
            "gives a reason AGAINST the target argument (rebuts its conclusion "
            "or undermines its premise). Cite both by id.\n"
            "- An UNDERCUT is (attacker, target_rule): the attacker contests the "
            "RIGHT TO INFER of a rule you named above (not its premise or "
            "conclusion, but the inference itself). `target_rule` must be a name "
            "you gave to a rule in this same response.\n"
            "Cite every attacker/target/premise/conclusion by id present in the "
            "inventory. Report a relation ONLY when the text genuinely supports "
            "it — do NOT connect unrelated arguments."
        )
        shape = (
            '{"rules": [{"premises": ["argN"], "conclusion": "argM", '
            '"name": "rule_id", "rationale": "one short sentence"}], '
            '"contradictions": [{"attacker": "argN", "target": "argM", '
            '"rationale": "one short sentence"}], '
            '"undercuts": [{"attacker": "argN", "target_rule": "rule_id", '
            '"rationale": "one short sentence"}]}'
        )
    elif relation_kind == "setaf_attacks":
        task = (
            "Identify SET (collective) ATTACKS among these arguments: a SetAF "
            "attack is a SET of arguments that JOINTLY defeat a target argument "
            "— no single attacker defeats it alone, but together they do (a "
            "joint attack). Report an ordinary pairwise attack as a singleton "
            "attacker set. Cite every attacker AND the target by id; every id "
            "must be present in the inventory. Report an attack ONLY when the "
            "text genuinely presents the attackers as undermining the target — "
            "do NOT connect unrelated arguments."
        )
        shape = (
            '{"attacks": [{"attackers": ["argN"], "target": "argM", '
            '"rationale": "one short sentence"}]}'
        )
    elif relation_kind == "weighted_attacks":
        task = (
            "Identify WEIGHTED ATTACKS among these arguments: a weighted attack "
            "is a pair (source, target) where the source argument attacks the "
            "target, together with a WEIGHT in [0.0, 1.0] expressing how strongly "
            "the source defeats the target (1.0 = total defeat, 0.0 = negligible). "
            "Cite source AND target by id; every id must be present in the "
            "inventory. Report an attack ONLY when the text genuinely presents "
            "the source as undermining the target — do NOT connect unrelated "
            "arguments."
        )
        shape = (
            '{"attacks": [{"source": "argN", "target": "argM", "weight": 0.8, '
            '"rationale": "one short sentence"}]}'
        )
    else:
        raise ValueError(f"unknown relation_kind: {relation_kind!r}")

    system_content = (
        "You are an expert in formal argumentation theory. "
        + task
        + " If no genuine relations of this kind exist in the text, return an empty "
        "list — do NOT invent relations. "
        "Respond with ONLY a JSON object of this shape:\n" + shape
    )
    user_content = (
        f"Source text (excerpt):\n{input_text[:3000]}\n\n"
        f"Arguments (id → text):\n[{inventory_json}]\n\n"
        f"Return the {relation_kind} JSON."
    )

    det_params = _get_determinism_params()
    llm_kwargs: Dict[str, Any] = dict(det_params)
    llm_kwargs["response_format"] = {"type": "json_object"}
    response = await _guarded_chat_completion(
        client,
        model=model_id,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        **llm_kwargs,
    )
    raw = response.choices[0].message.content or ""
    data = _parse_json_from_llm(raw)
    return data


def _validate_supports(
    data: Dict[str, Any], arg_by_id: Dict[str, str]
) -> List[List[str]]:
    """Validate LLM support pairs against the real inventory.

    Drops any pair whose source/target id is unknown or equal (self-support is
    meaningless). Re-maps ids → canonical argument text so the bipolar framework
    connects real nodes. Dedup preserves first-seen order.
    """
    raw = data.get("supports", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    seen: set[Tuple[str, str]] = set()
    out: List[List[str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        src_id = str(item.get("source", "")).strip()
        tgt_id = str(item.get("target", "")).strip()
        if src_id not in arg_by_id or tgt_id not in arg_by_id:
            continue  # fabricated / malformed → dropped (anti-théâtre)
        if src_id == tgt_id:
            continue  # self-support is not a genuine relation
        src, tgt = arg_by_id[src_id], arg_by_id[tgt_id]
        key = (src, tgt)
        if key in seen:
            continue
        seen.add(key)
        out.append([src, tgt])
    return out


def _validate_contraries(
    data: Dict[str, Any], arg_by_id: Dict[str, str]
) -> Dict[str, str]:
    """Validate LLM assumption↔contrary pairs against the real inventory.

    Drops any pair whose assumption id is unknown. Re-maps the assumption id →
    canonical argument text. The contrary stays as the LLM's defeating sentence.
    Last-write-wins on duplicate assumptions.
    """
    raw = data.get("contraries", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return {}
    out: Dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        asump_id = str(item.get("assumption", "")).strip()
        contrary = str(item.get("contrary", "")).strip()
        if asump_id not in arg_by_id or not contrary:
            continue  # fabricated / malformed → dropped (anti-théâtre)
        out[arg_by_id[asump_id]] = contrary
    return out


def _sanitize_rule_name(raw: Any) -> str:
    """Reduce a free-form rule name to a stable, collision-safe identifier.

    Rule names are Tweety ``Proposition`` names when negated (the undercut path,
    #1678) — they must be ``[A-Za-z0-9_]``. We prefix ``def_`` so a rule name
    never collides with an argument atom (``arg_*``) or a strict-rule head. The
    mapping is lossy by design: PL labels are opaque.
    """
    import re as _re

    cleaned = _re.sub(r"[^A-Za-z0-9_]+", "_", str(raw)).strip("_").lower()
    if not cleaned:
        return "def_rule"
    return f"def_{cleaned}"[:48]


def _validate_aspic_rules(
    data: Dict[str, Any],
    arg_by_id: Dict[str, str],
    atom_fn: Callable[..., str],
) -> List[Dict[str, Any]]:
    """Validate LLM defeasible-rule proposals against the real inventory.

    A genuine defeasible rule links real arguments: the conclusion id **and every
    premise id** must be in the inventory (a rule citing any absent id is a
    fabricated relation → the whole rule is dropped, anti-théâtre #1019), and at
    least one premise must remain after removing any premise equal to the
    conclusion (a rule concluding one of its own premises is vacuous).

    Ids are mapped to canonical argument text, then to stable PL atoms via
    ``atom_fn``. All argument atoms share the ``arg`` prefix so that an argument
    used as a conclusion of one rule and as a premise of another maps to the SAME
    atom — genuine ASPIC+ rule chaining. Returns handler-shaped
    ``{head, body, name}`` dicts. Dedup on ``(head, frozenset(body))``.

    A caller-supplied ``name`` (#1678) is preserved (sanitized) so the LLM can
    target a rule by its own name in an undercut; otherwise a stable
    ``def_rule_N`` is assigned. Names are guaranteed unique.
    """
    raw = data.get("rules", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    seen: set[Tuple[str, frozenset[str]]] = set()
    used_names: set[str] = set()
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        premises = item.get("premises", [])
        if isinstance(premises, str):
            premises = [premises]
        if not isinstance(premises, list):
            continue
        concl_id = str(item.get("conclusion", "")).strip()
        prem_ids = [str(p).strip() for p in premises]
        # Every cited id must be real — a rule citing any unknown id is dropped
        # wholesale (never salvaged into a partly-fabricated rule).
        if concl_id not in arg_by_id:
            continue
        if not prem_ids or any(pid not in arg_by_id for pid in prem_ids):
            continue
        prem_ids = [pid for pid in prem_ids if pid != concl_id]
        if not prem_ids:
            continue  # only premise was the conclusion itself → vacuous
        head_atom = atom_fn(arg_by_id[concl_id], prefix="arg")
        body_atoms: List[str] = []
        body_seen: set[str] = set()
        for pid in prem_ids:
            a = atom_fn(arg_by_id[pid], prefix="arg")
            if a not in body_seen:
                body_seen.add(a)
                body_atoms.append(a)
        key = (head_atom, frozenset(body_atoms))
        if key in seen:
            continue
        seen.add(key)
        # #1678: preserve a caller-supplied name (sanitized + unique) so an
        # undercut can target it; else a stable positional name.
        name = _unique_rule_name(
            (
                _sanitize_rule_name(item.get("name"))
                if item.get("name")
                else f"def_rule_{len(out) + 1}"
            ),
            used_names,
        )
        used_names.add(name)
        out.append({"head": head_atom, "body": body_atoms, "name": name})
    return out


def _unique_rule_name(base: str, used: set[str]) -> str:
    """Return ``base`` made unique against ``used`` (suffix _2, _3, …)."""
    if base not in used:
        return base
    i = 2
    while f"{base}_{i}" in used:
        i += 1
    return f"{base}_{i}"


def _validate_aspic_contradictions(
    data: Dict[str, Any],
    arg_by_id: Dict[str, str],
    atom_fn: Callable[..., str],
    used_names: set[str],
) -> List[Dict[str, Any]]:
    """Validate LLM contradiction proposals into negated-head defeasible rules.

    #1678: a contradiction ``{attacker, target}`` says *the attacker argument
    provides a reason against the target argument*. It is rendered as a
    defeasible rule whose conclusion is ``Negation(atome(target))`` and whose
    body is ``[atome(attacker)]``. The handler qualifies the scope (rebut if the
    negated atom is a conclusion elsewhere, undermine if it is a premise)
    structurally — never from keywords.

    Both ids must be in the inventory; any absent id drops the whole relation
    (anti-théâtre #1019). A self-contradiction (attacker == target) is vacuous
    and dropped.
    """
    raw = data.get("contradictions", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        atk_id = str(item.get("attacker", "")).strip()
        tgt_id = str(item.get("target", "")).strip()
        if atk_id not in arg_by_id or tgt_id not in arg_by_id:
            continue  # fabricated id → dropped
        if atk_id == tgt_id:
            continue  # self-contradiction → vacuous
        head_atom = atom_fn(arg_by_id[tgt_id], prefix="arg")
        body_atom = atom_fn(arg_by_id[atk_id], prefix="arg")
        name = _unique_rule_name("def_con", used_names)
        used_names.add(name)
        out.append(
            {
                "head": head_atom,
                "body": [body_atom],
                "name": name,
                "head_negated": True,
            }
        )
    return out


def _validate_aspic_undercuts(
    data: Dict[str, Any],
    arg_by_id: Dict[str, str],
    atom_fn: Callable[..., str],
    valid_rule_names: set[str],
    used_names: set[str],
) -> List[Dict[str, Any]]:
    """Validate LLM undercut proposals into negated-rule-name defeasible rules.

    #1678: an undercut ``{attacker, target_rule}`` contests the RIGHT TO INFER
    of a rule (the asymmetric attack unique to ASPIC+). It is rendered as a
    defeasible rule whose conclusion is ``Negation(Proposition(target_rule))``
    and whose body is ``[atome(attacker)]``. ``target_rule`` must be the name of
    a rule the LLM itself supplied and that survived validation (sanitized
    identically on both sides so the match is exact); any other name drops the
    relation (anti-théâtre #1019).
    """
    raw = data.get("undercuts", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        atk_id = str(item.get("attacker", "")).strip()
        tgt_rule = str(item.get("target_rule", "")).strip()
        if atk_id not in arg_by_id:
            continue
        # The target must be a rule the LLM named AND that survived validation.
        # Sanitize identically to _validate_aspic_rules so the names match.
        sanitized = _sanitize_rule_name(tgt_rule) if tgt_rule else ""
        if not sanitized or sanitized not in valid_rule_names:
            continue  # references a rule that does not exist → dropped
        body_atom = atom_fn(arg_by_id[atk_id], prefix="arg")
        name = _unique_rule_name("def_unc", used_names)
        used_names.add(name)
        out.append(
            {
                "head": sanitized,
                "body": [body_atom],
                "name": name,
                "head_negated": True,
            }
        )
    return out


def _validate_setaf_attacks(
    data: Dict[str, Any], arg_by_id: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Validate LLM SetAF joint-attack proposals against the real inventory.

    A SetAF (Set Argumentation Framework) attack is collective: a SET of
    arguments jointly attacks a target. The target id AND every attacker id must
    be in the inventory — a joint-attack citing any absent id is dropped
    wholesale (never salvaged into a partly-fabricated attack, anti-théâtre
    #1019). The target is removed from the attacker set (self-attack is
    vacuous), and the attack is dropped if no attacker remains. Ids are re-mapped
    to canonical argument text so the framework connects real nodes. Returns
    handler-shaped ``{attackers, target}`` dicts. Dedup on
    ``(frozenset(attackers), target)``.
    """
    raw = data.get("attacks", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    seen: set[Tuple[frozenset[str], str]] = set()
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        attackers = item.get("attackers", [])
        if isinstance(attackers, str):
            attackers = [attackers]
        if not isinstance(attackers, list):
            continue
        tgt_id = str(item.get("target", "")).strip()
        atk_ids = [str(a).strip() for a in attackers]
        # Target and every attacker must be real — any unknown id drops the
        # whole joint-attack (never a partly-fabricated attacker set).
        if tgt_id not in arg_by_id:
            continue
        if not atk_ids or any(aid not in arg_by_id for aid in atk_ids):
            continue
        atk_ids = [aid for aid in atk_ids if aid != tgt_id]
        if not atk_ids:
            continue  # only attacker was the target itself → vacuous self-attack
        # Dedup attacker ids within the set (preserve first-seen order).
        uniq_ids: List[str] = []
        id_seen: set[str] = set()
        for aid in atk_ids:
            if aid not in id_seen:
                id_seen.add(aid)
                uniq_ids.append(aid)
        atk_texts = [arg_by_id[aid] for aid in uniq_ids]
        tgt_text = arg_by_id[tgt_id]
        key = (frozenset(atk_texts), tgt_text)
        if key in seen:
            continue
        seen.add(key)
        out.append({"attackers": atk_texts, "target": tgt_text})
    return out


def _validate_weighted_attacks(
    data: Dict[str, Any], arg_by_id: Dict[str, str]
) -> List[Tuple[str, str, float]]:
    """Validate LLM weighted-attack proposals against the real inventory.

    A weighted attack is a ``(source, target, weight)`` triple: the source and
    target ids must both be in the inventory and distinct (self-attack is not
    genuine), and the weight must be a number in ``[0, 1]``. A triple citing any
    unknown id is dropped (anti-théâtre #1019); a non-numeric weight is dropped
    (no fabricated confidence). Weights outside ``[0, 1]`` are CLAMPED — the
    attack relation is genuine, only the magnitude needs sanitising to the valid
    range. Ids are re-mapped to canonical argument text. Returns
    ``(source_text, target_text, weight)`` tuples. Dedup on ``(source, target)``
    keeps the first weight seen.
    """
    raw = data.get("attacks", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    seen: set[Tuple[str, str]] = set()
    out: List[Tuple[str, str, float]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        src_id = str(item.get("source", "")).strip()
        tgt_id = str(item.get("target", "")).strip()
        if src_id not in arg_by_id or tgt_id not in arg_by_id:
            continue  # fabricated / malformed → dropped (anti-théâtre)
        if src_id == tgt_id:
            continue  # self-attack is not a genuine relation
        try:
            w = float(item.get("weight", 0.5))
        except (TypeError, ValueError):
            continue  # non-numeric weight → dropped (no fabricated confidence)
        # Clamp to the valid [0, 1] range — the relation is genuine, the
        # magnitude is sanitised rather than invented or discarded.
        w = max(0.0, min(1.0, w))
        src, tgt = arg_by_id[src_id], arg_by_id[tgt_id]
        key = (src, tgt)
        if key in seen:
            continue
        seen.add(key)
        out.append((src, tgt, w))
    return out


async def translate_to_bipolar_supports(
    input_text: str, arguments: List[str]
) -> TranslationResult:
    """Derive genuine bipolar support relations from the text + arguments.

    Returns a ``TranslationResult`` whose ``relations`` is a list of
    ``[source, target]`` pairs (canonical argument texts), validated against
    the real inventory. The ``cause`` discriminates why the axis is absent
    when ``relations`` is empty: ``no_genuine_relations`` (ran, found none —
    an analytical result), ``translator_unconfigured`` (no API key), or
    ``translator_failed`` (the call raised — ``error`` carries the type).
    Anti-théâtre #1019 / #1608: the caller labels the axis from ``cause``,
    never fabricating supports.
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)
    try:
        data = await _llm_extract_relations(input_text, arguments, "supports")
    except TranslatorUnconfigured:
        return TranslationResult(relations=[], cause=CAUSE_TRANSLATOR_UNCONFIGURED)
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.warning(
            "Bipolar supports translator failed (%s) — staying absent.",
            type(e).__name__,
        )
        return TranslationResult(
            relations=[], cause=CAUSE_TRANSLATOR_FAILED, error=type(e).__name__
        )
    supports = _validate_supports(data, arg_by_id)
    if supports:
        logger.info(
            "Bipolar translator: derived %d genuine support relation(s) from text.",
            len(supports),
        )
        return TranslationResult(relations=supports, cause=CAUSE_EVALUATED)
    return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)


async def translate_to_aba_contraries(
    input_text: str, arguments: List[str]
) -> TranslationResult:
    """Derive genuine ABA assumption↔contrary pairs from the text + arguments.

    Returns a ``TranslationResult`` whose ``relations`` is an
    ``{assumption_text: contrary_sentence}`` dict validated against the real
    inventory. See :func:`translate_to_bipolar_supports` for the ``cause``
    contract (#1608).
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return TranslationResult(relations={}, cause=CAUSE_NO_GENUINE_RELATIONS)
    try:
        data = await _llm_extract_relations(input_text, arguments, "contraries")
    except TranslatorUnconfigured:
        return TranslationResult(relations={}, cause=CAUSE_TRANSLATOR_UNCONFIGURED)
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.warning(
            "ABA contraries translator failed (%s) — staying absent.",
            type(e).__name__,
        )
        return TranslationResult(
            relations={}, cause=CAUSE_TRANSLATOR_FAILED, error=type(e).__name__
        )
    contraries = _validate_contraries(data, arg_by_id)
    if contraries:
        logger.info(
            "ABA translator: derived %d genuine contrary pair(s) from text.",
            len(contraries),
        )
        return TranslationResult(relations=contraries, cause=CAUSE_EVALUATED)
    return TranslationResult(relations={}, cause=CAUSE_NO_GENUINE_RELATIONS)


async def translate_to_aspic_rules(
    input_text: str, arguments: List[str]
) -> TranslationResult:
    """Derive genuine ASPIC+ defeasible inference rules from the text + arguments.

    Returns a ``TranslationResult`` whose ``relations`` is a list of
    handler-shaped ``{head, body, name}`` rule dicts with PL-atom
    heads/bodies, validated against the real inventory. See
    :func:`translate_to_bipolar_supports` for the ``cause`` contract (#1608).

    Only **defeasible** rules are derived: natural-language argumentation is
    defeasible, and strict rules / preference orderings are not reliably
    extractable from prose (they stay auto-shaped, honestly not a genuine strict
    layer). Feeding genuine defeasible rules is sufficient to flip the
    honest-absent gate to ``evaluated`` — ``_STRUCTURED_ARG_INPUT_KEYS[
    'aspic_plus_reasoning']`` accepts ``defeasible_rules``. The gate itself is
    never modified.
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)
    try:
        data = await _llm_extract_relations(input_text, arguments, "aspic_rules")
    except TranslatorUnconfigured:
        return TranslationResult(relations=[], cause=CAUSE_TRANSLATOR_UNCONFIGURED)
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.warning(
            "ASPIC+ rules translator failed (%s) — staying absent.",
            type(e).__name__,
        )
        return TranslationResult(
            relations=[], cause=CAUSE_TRANSLATOR_FAILED, error=type(e).__name__
        )
    # _pl_atom lives in invoke_callables (lazy import — no module-load cycle).
    from argumentation_analysis.orchestration.invoke_callables import _pl_atom

    rules = _validate_aspic_rules(data, arg_by_id, _pl_atom)
    # #1678: the contradictions + undercuts channels. Contradictions render as
    # negated-head rules (rebut/undermine, qualified structurally by the
    # handler); undercuts render as negated-rule-name rules. Undercuts may only
    # target rules that survived validation (ids/names validated identically),
    # so they run AFTER rules. All three share the used-names namespace.
    used_names = {r["name"] for r in rules}
    contradictions = _validate_aspic_contradictions(
        data, arg_by_id, _pl_atom, used_names
    )
    undercuts = _validate_aspic_undercuts(
        data, arg_by_id, _pl_atom, set(used_names), used_names
    )
    # #1649 diagnostics (coord R783): on real corpus the handler emits 0 attack
    # even though this translator ran (status "evaluated", axioms_count>0 ⇒
    # #1679 leaf-atom derivation fired). The axis is alive end-to-end but
    # produces no attack because no ``head_negated`` rule reaches the handler.
    # This counter distinguishes the two remaining hypotheses WITHOUT further
    # code — a corpus run's log answers it:
    #   - raw>0, kept=0  ⇒ the LLM DID emit contradictions/undercuts, all
    #     SILENTLY DROPPED at validation (fabricated id / self / non-existent
    #     rule → bare ``continue`` in _validate_aspic_*).
    #   - raw=0          ⇒ the LLM emitted NONE (a prompt/LLM question, not
    #     plumbing).
    # Surfaced as a warning so it is visible even when base rules make
    # ``relations`` non-empty and the info log below hides the drop.
    _raw_contradictions = (
        len(data.get("contradictions", []) or []) if isinstance(data, dict) else 0
    )
    _raw_undercuts = (
        len(data.get("undercuts", []) or []) if isinstance(data, dict) else 0
    )
    if _raw_contradictions or _raw_undercuts:
        logger.warning(
            "ASPIC+ #1649 diagnostics: LLM proposed %d contradiction(s) "
            "(kept %d, dropped %d) and %d undercut(s) (kept %d, dropped %d). "
            "Drops = fabricated/self ids or non-existent rule names "
            "(anti-#1019 validation). If kept==0, no head_negated rule reaches "
            "the handler ⇒ 0 attack.",
            _raw_contradictions,
            len(contradictions),
            _raw_contradictions - len(contradictions),
            _raw_undercuts,
            len(undercuts),
            _raw_undercuts - len(undercuts),
        )
    relations = rules + contradictions + undercuts
    if relations:
        logger.info(
            "ASPIC+ translator: derived %d rule(s) (%d base, %d contradiction(s), "
            "%d undercut(s)) from text.",
            len(relations),
            len(rules),
            len(contradictions),
            len(undercuts),
        )
        return TranslationResult(relations=relations, cause=CAUSE_EVALUATED)
    return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)


async def translate_to_setaf_attacks(
    input_text: str, arguments: List[str]
) -> TranslationResult:
    """Derive genuine SetAF joint attacks from the text + arguments.

    Returns a ``TranslationResult`` whose ``relations`` is a list of
    handler-shaped ``{attackers, target}`` joint-attack dicts (canonical
    argument texts), validated against the real inventory. See
    :func:`translate_to_bipolar_supports` for the ``cause`` contract (#1608).
    The gate ``_STRUCTURED_ARG_INPUT_KEYS['setaf_reasoning']`` accepts
    ``set_attacks``; the gate itself is never modified.
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)
    try:
        data = await _llm_extract_relations(input_text, arguments, "setaf_attacks")
    except TranslatorUnconfigured:
        return TranslationResult(relations=[], cause=CAUSE_TRANSLATOR_UNCONFIGURED)
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.warning(
            "SetAF attacks translator failed (%s) — staying absent.",
            type(e).__name__,
        )
        return TranslationResult(
            relations=[], cause=CAUSE_TRANSLATOR_FAILED, error=type(e).__name__
        )
    attacks = _validate_setaf_attacks(data, arg_by_id)
    if attacks:
        logger.info(
            "SetAF translator: derived %d genuine joint attack(s) from text.",
            len(attacks),
        )
        return TranslationResult(relations=attacks, cause=CAUSE_EVALUATED)
    return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)


async def translate_to_weighted_attacks(
    input_text: str, arguments: List[str]
) -> TranslationResult:
    """Derive genuine weighted attacks from the text + arguments.

    Returns a ``TranslationResult`` whose ``relations`` is a list of
    ``(source, target, weight)`` triples (canonical argument texts, weight
    clamped to ``[0, 1]``), validated against the real inventory. See
    :func:`translate_to_bipolar_supports` for the ``cause`` contract (#1608).
    The gate ``_STRUCTURED_ARG_INPUT_KEYS['weighted_argumentation']`` accepts
    ``weighted_attacks``; the gate itself is never modified.
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)
    try:
        data = await _llm_extract_relations(input_text, arguments, "weighted_attacks")
    except TranslatorUnconfigured:
        return TranslationResult(relations=[], cause=CAUSE_TRANSLATOR_UNCONFIGURED)
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.warning(
            "Weighted attacks translator failed (%s) — staying absent.",
            type(e).__name__,
        )
        return TranslationResult(
            relations=[], cause=CAUSE_TRANSLATOR_FAILED, error=type(e).__name__
        )
    attacks = _validate_weighted_attacks(data, arg_by_id)
    if attacks:
        logger.info(
            "Weighted translator: derived %d genuine weighted attack(s) from text.",
            len(attacks),
        )
        return TranslationResult(relations=attacks, cause=CAUSE_EVALUATED)
    return TranslationResult(relations=[], cause=CAUSE_NO_GENUINE_RELATIONS)


__all__ = [
    "translate_to_bipolar_supports",
    "translate_to_aba_contraries",
    "translate_to_aspic_rules",
    "translate_to_setaf_attacks",
    "translate_to_weighted_attacks",
    "TranslationResult",
    "TranslatorUnconfigured",
    "CAUSE_EVALUATED",
    "CAUSE_TRANSLATOR_FAILED",
    "CAUSE_NO_GENUINE_RELATIONS",
    "CAUSE_TRANSLATOR_UNCONFIGURED",
    "_build_inventory",
    "_validate_supports",
    "_validate_contraries",
    "_validate_aspic_rules",
    "_validate_aspic_contradictions",
    "_validate_aspic_undercuts",
    "_sanitize_rule_name",
    "_unique_rule_name",
    "_validate_setaf_attacks",
    "_validate_weighted_attacks",
]
