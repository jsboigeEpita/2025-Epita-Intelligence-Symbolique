"""State sanitizer — the UNIQUE export guard for analysis state snapshots.

Produces a privacy-safe dict suitable for commits, dashboards, PRs, and
reports. All quantitative aggregates (counts, scores, structures) are
preserved; only nominative natural-language content is removed or opacified.

Epic #1258 Track 3 (#1261): the de-anonymized pipeline (Track 1/2) lets real
names and readable logic symbols live in the working state and in the
gitignored local artefacts (``evaluation/results/``). This function is the
single chokepoint through which a state snapshot must pass before reaching
git, a dashboard, a PR, or an API: it is where nominative content is scrubbed
at the boundary. Anti-penduple: this is the *only* scrubber — the scattered
ones (``generate_spectacular_bundle._scrub_state_for_export``,
``appendix._strip_leak_keys``) are consolidation targets, not siblings.
"""

from __future__ import annotations

import copy
from typing import Any

from argumentation_analysis.evaluation.opaque_id import opaque_id

# Fields to remove entirely from the top-level state snapshot.
_STRIP_TOP_LEVEL = {
    "raw_text",
    "full_text",
    "full_text_segment",
    "raw_text_snippet",
    "source_name",
    "document_name",
    "author",
    "date_iso",
    "url",
}

# Fields to replace with opaque IDs (key -> opaque_id(value)).
_OPAQUE_REPLACE = {"source_id"}

# Dict-valued fields whose *values* are nominative strings keyed by generic
# structural labels (key kept, value -> opaque_id). Track 1 (#1259) threads
# real ``source_metadata`` = ``{genre, speaker_role, channel, title, ...}``
# into the working state; the values are nominative (a ``title`` is a source
# name per CLAUDE.md privacy) but the keys are structural. Opacifying the
# values preserves "which metadata was present" without leaking content.
_OPAQUE_DICT_VALUES = {"source_metadata"}

# Dict-valued fields whose entries are nominative *strings*
# (e.g. ``{arg_id: description}``). The string is replaced by a placeholder;
# non-string (structured) values are preserved untouched.
_TEXT_STRIP_DICTS = {"identified_arguments", "arguments"}

# Dict-of-dicts fields: top-level field -> sub-keys whose string values are
# nominative and must be dropped (the rest of each entry is preserved).
#   e.g. identified_fallacies = {fid: {type, justification, family, ...}}
#        belief_sets          = {bs_id: {logic_type, content}}
#        argument_quality_scores = {arg_id: {scores, overall, llm_assessment}}
# #1265 (Track 3 follow-up): ``llm_assessment`` is an LLM-written narrative
# that cites/paraphrases the real argument text (verify-the-verification,
# po-2023 finding) — pure narrative, 0 quantitative value, dropped.
_TEXT_STRIP_DICT_OF_DICTS = {
    "identified_fallacies": {"justification"},
    "belief_sets": {"content"},
    "argument_quality_scores": {"llm_assessment"},
}

# Dict-of-dicts fields whose *list sub-keys* carry nominative text entries
# (verified nominative firsthand, #1265): top-level field -> {sub_key}.
# Each list is reduced by opacifying every string entry via ``opaque_id``
# (non-strings left as-is). The list *structure* survives (length, topology)
# so downstream quantitative aggregates (argument/attack counts, Dung extension
# membership) are preserved — only the content is opacified.
#   e.g. dung_frameworks = {df_id: {name, arguments: [claim_text, ...],
#                                   attacks: [[text_a, text_b], ...]}}
# _extract_arguments_from_context (invoke_callables.py:2617) puts the real
# claim text into ``arguments``; ``attacks`` are pairs of those same texts.
_OPAQUE_LIST_SUBKEYS = {
    "dung_frameworks": {"arguments", "attacks"},
}

# List-of-dicts fields: top-level field -> sub-keys whose values are
# nominative text to drop (the rest of each item is preserved).
_TEXT_STRIP_LISTS = {
    "counter_arguments": {"counter_content", "generated_text", "original_argument"},
    "extracts": {"content"},
    "debate_transcripts": {"proponent_move", "opponent_move", "topic"},
    "transcription_segments": {"text", "speaker"},
    "neural_fallacy_scores": {"text_segment"},
    "analysis_trace": {"summary"},
    "nl_to_logic_translations": {"original_text"},
    "semantic_index_refs": {"query", "snippet"},
    "formal_synthesis_reports": {"summary"},
}

# List-of-dicts fields carrying a symbol-mapping sub-key: a ``Dict[str, str]``
# mapping an opaque atom (``p``, ``mp1``) to its NL meaning. Track 2 makes the
# NL meaning readable/potentially-nominative; the values are opacified with
# ``opaque_id`` so the mapping *structure* survives without leaking content.
_SYMBOL_MAPPING_LIST_FIELDS = {
    "nl_to_logic_translations": "variables",
}

# Fields that are purely narrative text -> replaced with length + marker.
_NARRATIVE_FIELDS = {
    "narrative_synthesis",
    "act1_framing",
    "act2_narrative",
    "act3_conclusion",
    "final_conclusion",
}

# A single struct-valued field whose list sub-keys carry nominative NL.
# Reduced to a counts-only summary (aggregates preserved, all NL removed).
# Each value is (list_subkey_to_count, ...).
_STRUCT_LIST_SCRUB = {
    "stakes_and_stakeholders": ("stakes", "stakeholders"),
}


def _strip_text_from_dict(data: dict[str, Any], text_keys: set[str]) -> dict[str, Any]:
    """Remove text-bearing keys from a dict, keep everything else."""
    return {k: v for k, v in data.items() if k not in text_keys}


def _strip_text_from_list(
    items: list[dict[str, Any]], text_keys: set[str]
) -> list[dict[str, Any]]:
    """Remove text-bearing keys from each dict in a list."""
    return [_strip_text_from_dict(item, text_keys) for item in items]


def _opacify_mapping(mapping: Any) -> Any:
    """Opacify the NL-meaning values of a ``Dict[str, str]`` symbol mapping.

    Atom keys (``p``, ``mp1``) are kept; only the human-readable values are
    passed through ``opaque_id``. Non-string/empty values are left as-is.
    """
    if not isinstance(mapping, dict):
        return mapping
    return {
        k: (opaque_id(v) if isinstance(v, str) and v else v) for k, v in mapping.items()
    }


def _opacify_list_values(value: Any) -> Any:
    """Recursively opacify the strings inside a (possibly nested) list.

    Used for Dung ``arguments`` (flat list of claim texts) and ``attacks``
    (list of [attacker, target] pairs = nested list). The list topology and
    arity survive; only the nominative strings are replaced by ``opaque_id``.
    Non-strings are left as-is.
    """
    if isinstance(value, str):
        return opaque_id(value) if value else value
    if isinstance(value, list):
        return [_opacify_list_values(item) for item in value]
    return value


def _scrub_struct(value: Any, list_keys: tuple[str, ...]) -> dict[str, Any]:
    """Reduce a stakes/stakeholders struct to a counts-only summary."""
    if not isinstance(value, dict):
        return {"stripped": True}
    summary: dict[str, Any] = {"stripped": True}
    for key in list_keys:
        lst = value.get(key)
        summary[f"{key}_count"] = len(lst) if isinstance(lst, list) else 0
    # Short categorical labels are reduced to presence flags: they may carry
    # discursive context, so we keep only the boolean, not the string.
    for str_key in ("rhetorical_register", "discursive_arena"):
        summary[f"has_{str_key}"] = bool(value.get(str_key))
    return summary


def sanitize_state(state: dict[str, Any] | Any) -> dict[str, Any]:
    """Strip nominative fields, keep all quantitative aggregates.

    Args:
        state: A state dict (typically from ``state_snapshot`` in a golden
               fixture) or a ``UnifiedAnalysisState`` instance.  If an object
               with a ``model_dump`` or ``dict`` method is passed, it will be
               serialized first.

    Returns:
        A new dict with all sensitive text removed, opaque IDs substituted,
        symbol mappings opacified, and all counts/scores/structures preserved.
    """
    # Handle Pydantic models or objects with serialization.
    if hasattr(state, "model_dump"):
        data = state.model_dump()
    elif hasattr(state, "dict"):
        data = state.dict()
    elif isinstance(state, dict):
        data = copy.deepcopy(state)
    else:
        data = dict(state)

    # 1. Strip top-level sensitive fields.
    for field in _STRIP_TOP_LEVEL:
        data.pop(field, None)

    # 2. Replace identifying fields with opaque IDs.
    for field in _OPAQUE_REPLACE:
        if field in data and isinstance(data[field], str):
            data[field] = opaque_id(data[field])

    # 2b. Opacify the nominative values of dict-valued identifier fields
    #     (source_metadata = {genre, speaker_role, channel, title, ...}).
    for field in _OPAQUE_DICT_VALUES:
        if field in data and isinstance(data[field], dict):
            data[field] = _opacify_mapping(data[field])

    # 3. Strip text from dict-valued fields whose entries are strings
    #    (identified_arguments, arguments).
    for field in _TEXT_STRIP_DICTS:
        if field in data and isinstance(data[field], dict):
            data[field] = {
                k: {"text_stripped": True} if isinstance(v, str) else v
                for k, v in data[field].items()
            }

    # 4. Strip nominative sub-keys from dict-of-dicts fields
    #    (identified_fallacies.justification, belief_sets.content,
    #    argument_quality_scores.llm_assessment).
    for field, text_keys in _TEXT_STRIP_DICT_OF_DICTS.items():
        if field in data and isinstance(data[field], dict):
            data[field] = {
                key: (
                    _strip_text_from_dict(val, text_keys)
                    if isinstance(val, dict)
                    else val
                )
                for key, val in data[field].items()
            }

    # 4b. Opacify the nominative list-valued sub-keys of dict-of-dicts fields
    #     (dung_frameworks.arguments = [claim_text, ...],
    #      dung_frameworks.attacks = [[text_a, text_b], ...]).
    #     The list structure survives (length + attack topology preserved) so
    #     downstream Dung aggregates are unaffected; only the claim texts are
    #     opacified (#1265, po-2023 firsthand verdict).
    for field, subkeys in _OPAQUE_LIST_SUBKEYS.items():
        if field in data and isinstance(data[field], dict):
            new_entries: dict[str, Any] = {}
            for key, val in data[field].items():
                if isinstance(val, dict):
                    new_entry = dict(val)
                    for sk in subkeys:
                        if sk in new_entry:
                            new_entry[sk] = _opacify_list_values(new_entry[sk])
                    new_entries[key] = new_entry
                else:
                    new_entries[key] = val
            data[field] = new_entries

    # 5. Strip nominative sub-keys from list-of-dicts fields.
    for field, text_keys in _TEXT_STRIP_LISTS.items():
        if field in data and isinstance(data[field], list) and text_keys:
            data[field] = _strip_text_from_list(data[field], text_keys)

    # 6. Opacify symbol-mapping sub-keys inside list-of-dicts fields
    #    (nl_to_logic_translations[*].variables).
    for field, subkey in _SYMBOL_MAPPING_LIST_FIELDS.items():
        if field in data and isinstance(data[field], list):
            for item in data[field]:
                if isinstance(item, dict) and subkey in item:
                    item[subkey] = _opacify_mapping(item[subkey])

    # 7. Replace narrative text with length info.
    for field in _NARRATIVE_FIELDS:
        if field in data and isinstance(data[field], str):
            original = data[field]
            data[field] = {
                "length": len(original),
                "stripped": True,
            }

    # 8. Reduce struct-valued NL fields to counts (stakes_and_stakeholders).
    for field, list_keys in _STRUCT_LIST_SCRUB.items():
        if field in data:
            data[field] = _scrub_struct(data[field], list_keys)

    return data
