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
If after validation nothing remains, the formalism stays
``absent_no_translator`` — an honest absence, never a fabricated evaluation
("soustraire le gap, pas contourner le garde"). The honest-absent gate in
``_record_structured_arg_status`` is never modified: this module only feeds it
genuine input.

Privacy HARD
------------
LLM user content is the source text (truncated) + argument labels — never
committed. Outputs (supports/contraries referencing opaque arg labels) live in
gitignored state artifacts.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger("UnifiedPipeline")

# Cap the argument inventory handed to the LLM so prompt + response stay bounded
# (mirrors the [:40] cap in _extract_arguments_from_context, #708). Bipolar/ABA
# relations over a larger inventory would blow the JSON token ceiling without
# adding analytical value for a PoC.
_MAX_INVENTORY = 20


def _build_inventory(arguments: List[str]) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
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
            "%s translator: no LLM API key configured — staying absent_no_translator.",
            relation_kind,
        )
        return {}

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
            "Identify DEFEASIBLE INFERENCE rules among these arguments: a rule is "
            "(premises, conclusion) where the premise argument(s) defeasibly lead "
            "to — justify — the conclusion argument. Cite premises AND conclusion "
            "by id; every id must be present in the inventory. Report a rule ONLY "
            "when the text genuinely presents the premises as reasons for the "
            "conclusion — do NOT connect unrelated arguments."
        )
        shape = (
            '{"rules": [{"premises": ["argN"], "conclusion": "argM", '
            '"rationale": "one short sentence"}]}'
        )
    else:
        raise ValueError(f"unknown relation_kind: {relation_kind!r}")

    system_content = (
        "You are an expert in formal argumentation theory. "
        + task
        + " If no genuine relations of this kind exist in the text, return an empty "
        "list — do NOT invent relations. "
        "Respond with ONLY a JSON object of this shape:\n"
        + shape
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
    """
    raw = data.get("rules", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    seen: set[Tuple[str, frozenset[str]]] = set()
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
        out.append(
            {"head": head_atom, "body": body_atoms, "name": f"def_rule_{len(out) + 1}"}
        )
    return out


async def translate_to_bipolar_supports(
    input_text: str, arguments: List[str]
) -> List[List[str]]:
    """Derive genuine bipolar support relations from the text + arguments.

    Returns a list of ``[source, target]`` pairs (canonical argument texts),
    validated against the real inventory. Empty list when the LLM finds no
    genuine supports OR no API key is configured — the caller then stays
    ``absent_no_translator`` (honest absence, anti-théâtre #1019).
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return []
    try:
        data = await _llm_extract_relations(input_text, arguments, "supports")
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.info(
            "Bipolar supports translator failed (%s) — staying absent_no_translator.",
            e,
        )
        return []
    supports = _validate_supports(data, arg_by_id)
    if supports:
        logger.info(
            "Bipolar translator: derived %d genuine support relation(s) from text.",
            len(supports),
        )
    return supports


async def translate_to_aba_contraries(
    input_text: str, arguments: List[str]
) -> Dict[str, str]:
    """Derive genuine ABA assumption↔contrary pairs from the text + arguments.

    Returns ``{assumption_text: contrary_sentence}`` validated against the real
    inventory. Empty dict when the LLM finds no genuine contraries OR no API key
    is configured — the caller then stays ``absent_no_translator``.
    """
    arg_by_id, _ = _build_inventory(arguments)
    if not arg_by_id:
        return {}
    try:
        data = await _llm_extract_relations(input_text, arguments, "contraries")
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.info(
            "ABA contraries translator failed (%s) — staying absent_no_translator.",
            e,
        )
        return {}
    contraries = _validate_contraries(data, arg_by_id)
    if contraries:
        logger.info(
            "ABA translator: derived %d genuine contrary pair(s) from text.",
            len(contraries),
        )
    return contraries


async def translate_to_aspic_rules(
    input_text: str, arguments: List[str]
) -> List[Dict[str, Any]]:
    """Derive genuine ASPIC+ defeasible inference rules from the text + arguments.

    Returns a list of handler-shaped ``{head, body, name}`` rule dicts with
    PL-atom heads/bodies, validated against the real inventory. Empty list when
    the LLM finds no genuine rules OR no API key is configured — the caller then
    stays ``absent_no_translator`` (honest absence, anti-théâtre #1019).

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
        return []
    try:
        data = await _llm_extract_relations(input_text, arguments, "aspic_rules")
    except Exception as e:  # network / parse / budget — never fatal to the run
        logger.info(
            "ASPIC+ rules translator failed (%s) — staying absent_no_translator.",
            e,
        )
        return []
    # _pl_atom lives in invoke_callables (lazy import — no module-load cycle).
    from argumentation_analysis.orchestration.invoke_callables import _pl_atom

    rules = _validate_aspic_rules(data, arg_by_id, _pl_atom)
    if rules:
        logger.info(
            "ASPIC+ translator: derived %d genuine defeasible rule(s) from text.",
            len(rules),
        )
    return rules


__all__ = [
    "translate_to_bipolar_supports",
    "translate_to_aba_contraries",
    "translate_to_aspic_rules",
    "_build_inventory",
    "_validate_supports",
    "_validate_contraries",
    "_validate_aspic_rules",
]
