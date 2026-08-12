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

Coverage is ALLOWLIST-DRIVEN, and that is a deliberate design: a catch-all
"scrub every long string" pass would erase the structural aggregates
(identifiers, methods, framework types, extension topologies) this function
promises to preserve. The consequence is equally deliberate to state: a
container absent from every table below traverses this function **intact**.
Adding a state container is therefore not neutral — it must be classified
here, and "it carries no natural language" is a claim to be verified against
its producer, not assumed from its name. #1664 measured the cost of leaving
that implicit: ``dung_frameworks`` was covered (#1265, #1271) while six
sibling containers carrying the *same* claim text under the *same* sub-key
were not, for the simple reason that they are declared ``List[Dict]`` and the
passes written for Dung gate on ``isinstance(..., dict)``.

Known and deliberately NOT covered, each for a stated reason:
  * ``workflow_results`` — a free-form dict with no imposed schema; scrubbing
    it needs a policy, not a table entry.
  * ``formal_synthesis_reports[*].phase_results.*.formulas`` — symbolic, but
    Track 2 makes symbols readable (which is why ``variables`` IS opacified);
    the producer has to be read before deciding.
  * ``extracts[*].name``, ``semantic_index_refs[*].document_id`` — declared as
    names, yet structural in every artefact measured so far, and used as join
    keys downstream. Opacifying them on suspicion would trade a hypothetical
    leak for a certain breakage.
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

# Dict-of-dicts whose entries carry a NESTED dict sub-key holding nominative
# list-valued leaves (#1271, po-2023 FB-39 follow-up to #1265): top-level field
# -> {nested_subkey -> {leaf_subkeys}}.
#   dung_frameworks[df_id]["extensions"] = {
#       "extensions":   [[claim_text, ...], ...],  # list of lists (the Dung
#                                                  #   extensions, each a set)
#       "count":        N,                         # structural — survives
#       "sizes":        [...],                     # structural — survives
#       "all_members":  [claim_text, ...],         # flat list (union of members)
#   }
# Tweety returns each extension as a set of the same ``arguments`` claim texts
# (invoke_callables.py:6188-6194); the writer stores them under ``extensions``
# (state_writers.py:903). Opacified recursively via ``_opacify_list_values``
# (handles both the nested list-of-lists and the flat ``all_members``) so set
# arity/topology survive — only the claim *content* is scrubbed. ``name`` is a
# structural label (verified non-nominative firsthand) and is left untouched.
_OPAQUE_NESTED_LIST_SUBKEYS = {
    "dung_frameworks": {"extensions": {"extensions", "all_members"}},
}

# Wave-2 ``formalism_specific`` sidecars on ``dung_frameworks`` entries (#1702).
# The six #1648 writers (ABA/SetAF/Weighted/EAF/DeLP, plus ADF which attaches no
# sidecar) attach a strictly-additive ``entry["formalism_specific"] = {...}`` dict
# to carry data the native Dung projection has no slot for. Each leaf was measured
# at its producer (the anti-pendule of #1702: "mesurer le producteur"), and the
# verdict split is nominative-source-atom vs closed-vocabulary/numeric-aggregate:
#
#   contraries        Dict[assumption_atom, contrary_atom]   — ABA l.968, BOTH
#                                                               keys+values source
#   set_attacks       List[{attackers:[atom], target:atom}]  — SetAF l.1482
#   attack_weights    List[{source, target, weight:float}]   — Weighted l.1541,
#                                                               weight KEPT (numeric)
#   epistemic_beliefs Dict[agent, List[arg_atom]]            — EAF l.1611
#   delp_arguments    str | List[str] (defeasible rule source over source
#                     predicates)                            — DeLP l.1658
#
# Deliberately NOT listed (survive untouched — closed vocab / pure numeric, the
# #1702 anti-pendule symmetrical to the scrubber's own l.156-163):
#   weight_statistics {min/max/avg_weight: float}            — Weighted l.1551
#   program_size      int                                     — DeLP l.1660
#   criterion         str (e.g. "generalized_specificity")   — DeLP l.1662, closed
#
# Parent 2 (``propositional_analysis_results[*].formalism_specific.qbf_quantifiers``)
# is ALSO not listed here and needs no scrub: the QBF writer docstring
# (state_writers.py:1683) measures its leaves as formal logical symbols
# (quantifier type + variable names like ``x``/``y``), not source-derived prose.
# "Covering both parents" (#1702 DoD) is therefore statuated by measurement on
# parent 2 (opaque by construction), not by a table entry.
#
# ``aspic_results.attacks`` (the other #1702 surface) is already covered by pass
# 5d via ``_OPAQUE_NESTED_ITEM_SUBKEYS`` (commit a9bcf516, #1649 follow-up).
#
# Leaf -> opacification mode:
#   "mapping"                 Dict keyed by a source atom -> opacify keys AND
#                             values (values may be a list of atoms).
#   ("dict_list", (fields,))  List[Dict] -> opacify the named string-leaves,
#                             keep the rest (e.g. the numeric ``weight``).
#   "atom_list"               A source-atom string OR list of them -> opacify.
_OPAQUE_FORMALISM_SPECIFIC = {
    "contraries": "mapping",
    "epistemic_beliefs": "mapping",
    "set_attacks": ("dict_list", ("attackers", "target")),
    "attack_weights": ("dict_list", ("source", "target")),
    "delp_arguments": "atom_list",
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

# LIST-of-dicts fields whose sub-keys carry the same nominative claim text that
# 4b/4c opacify for ``dung_frameworks`` (#1664): top-level field -> {sub_key}.
# Each sub-key is passed through ``_opacify_list_values``, which handles a bare
# string, a flat list and a nested list alike — so arity and topology survive
# and only the content is opacified, exactly as in 4b.
#
# Why these fields, measured rather than assumed: ``_extract_arguments_from_
# context`` (invoke_callables.py:3036) is the helper the 4b comment already
# cites as the one that "puts the real claim text into ``arguments``". It feeds
# 17 callables, not just Dung — ranking, probabilistic, bipolar, ASPIC+, belief
# revision and dialogue among them. Their writers store that list verbatim
# (shared_state.py:941-1032), so these carry claim text *by construction*:
#   bipolar_results[*].supports      = [[text_a, text_b], ...]  (cf. Dung attacks)
#   aspic_results[*].extensions      = [[text, ...], ...]       (cf. Dung extensions)
#   belief_revision_results[*].original/.revised = [text, ...]
#   dialogue_results[*].topic        = a claim text (the writer logs topic[:50])
#
# Anti-pendulum, also measured: the sibling label fields are NOT here.
# ``ranking_results.method``, ``aspic_results.reasoner_type``,
# ``bipolar_results.framework_type``, ``belief_revision_results.method`` are
# closed vocabularies at every producer, and the contract promises to preserve
# structural aggregates. Same verdict for ``dung_frameworks.name``: all ten
# call sites build it from a fixed vocabulary (``aba_preferred``,
# ``setaf_grounded``, ``social_af``, ``dung_arbitration``…), which confirms the
# #1271 firsthand reading — it stays untouched.
_OPAQUE_LIST_OF_DICTS_SUBKEYS = {
    "ranking_results": {"arguments"},
    "probabilistic_results": {"arguments"},
    "bipolar_results": {"arguments", "supports"},
    "aspic_results": {"extensions"},
    "belief_revision_results": {"original", "revised"},
    "dialogue_results": {"topic"},
}

# List-of-dicts fields with a dict sub-key whose *KEYS* are claim texts
# (#1664): top-level field -> {sub_key}. ``_invoke_probabilistic`` builds
# ``probs = {a: 0.5 for a in args}`` (invoke_callables.py:3896), so the
# acceptance map is indexed by the argument text itself. The keys are
# opacified and the numeric values kept, so the distribution survives intact.
_OPAQUE_LIST_OF_DICTS_MAPPING_KEYS = {
    "probabilistic_results": {"acceptance_probabilities"},
}

# List-of-dicts fields whose sub-key is ITSELF a list of dicts carrying
# nominative leaves (#1664): top-level field -> {sub_key -> {leaf_subkeys}}.
# One level deeper than pass 5.
#   dialogue_results[*].trace[*]      = {round, speaker, action, argument, target}
#       ``argument``/``target`` are claim texts (dialogue_handler.py:100-130);
#       ``speaker``/``action`` are closed vocabularies and survive.
#   debate_transcripts[*].exchanges[*] = {proponent_move, opponent_move, ...}
#       ``_TEXT_STRIP_LISTS`` already declares those two sub-keys, but the real
#       writer nests them one level down inside ``exchanges``
#       (shared_state.py:860-872), so the declaration never had a target. This
#       completes an intent already recorded rather than adding a new one.
_OPAQUE_NESTED_ITEM_SUBKEYS = {
    "dialogue_results": {"trace": {"argument", "target"}},
    "debate_transcripts": {"exchanges": {"proponent_move", "opponent_move"}},
    # #1649 privacy follow-up: aspic_results[*].attacks = the qualified attacks
    # surfaced top-level by the #1681 writer (and now read by the #1699 reader).
    # Each attack dict = {target, attacker_premises, scope, attacker_rule}.
    # ``target``/``attacker_premises`` are source-derived PL atoms — ``_pl_atom``
    # (invoke_callables.py) keeps up to 24 leading chars of the argument text,
    # so they ARE nominative → opacify. ``scope`` (undercut/rebut/undermine/
    # unresolved) and ``attacker_rule`` (def_con_N / def_unc_N) are structural
    # closed vocabularies at every producer (measured: handler _qualify_attacks,
    # translator _validate_aspic_*) → preserved, exactly as dung_frameworks.name
    # is. Uses the same opacify_list_values path as dialogue_results.trace.
    "aspic_results": {"attacks": {"target", "attacker_premises"}},
}

# List-of-dicts fields carrying a symbol-mapping sub-key: a ``Dict[str, str]``
# mapping an opaque atom (``p``, ``mp1``) to its NL meaning. Track 2 makes the
# NL meaning readable/potentially-nominative; the values are opacified with
# ``opaque_id`` so the mapping *structure* survives without leaking content.
_SYMBOL_MAPPING_LIST_FIELDS = {
    "nl_to_logic_translations": "variables",
}

# List-of-dicts fields whose sub-key is itself a DICT carrying nominative list
# leaves (#1646): top-level field -> {dict_subkey -> {leaf_subkeys}}. Unlike
# ``_OPAQUE_NESTED_ITEM_SUBKEYS`` (5d), the sub-key is a single dict, not a list
# of dicts — so the leaves hang directly off it.
#   belief_revision_results[*].minimal_retraction.options = [[belief, ...], ...]
#       ``options`` is a list-of-lists of belief labels (the argument text that
#       names the rupture point). The list topology + arity survive (how many
#       retraction options, how many beliefs each); only the nominative strings
#       are opacified. The sibling ``cardinality``/``base_size``/``touched_count``
#       are ints and are intentionally NOT listed, so they survive untouched.
_OPAQUE_DEEP_DICT_LEAVES: dict[str, dict[str, set[str]]] = {
    "belief_revision_results": {"minimal_retraction": {"options"}},
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


def _scrub_formalism_specific(sidecar: Any) -> Any:
    """Opacify the nominative leaves of a ``formalism_specific`` sidecar (#1702).

    The Wave-2 sidecar is a heterogeneous dict whose leaves mix source-derived
    PL atoms (the nominative payload — ``_pl_atom`` keeps up to 24 leading chars
    of argument text) with closed vocabularies and numeric aggregates the export
    contract promises to preserve. ``_OPAQUE_FORMALISM_SPECIFIC`` names the
    nominative leaves and their opacification mode; every key NOT in that table
    (``weight_statistics``, ``program_size``, ``criterion``) survives untouched.

    Topology is preserved everywhere: a list stays a list of the same arity, a
    mapping keeps its key count, and the numeric ``weight`` on each
    ``attack_weights`` entry survives — so downstream quantitative aggregates
    (joint-attack arity, weight distribution) are unaffected, exactly as passes
    4b/4c preserve Dung extension sizes.
    """
    if not isinstance(sidecar, dict):
        return sidecar
    out = dict(sidecar)  # shallow copy; untouched keys (criterion/stats) ride through
    for leaf, mode in _OPAQUE_FORMALISM_SPECIFIC.items():
        if leaf not in out:
            continue
        val = out[leaf]
        if mode == "mapping":
            # Dict keyed by a source atom; opacify keys AND values (values may be
            # a list of atoms — _opacify_list_values handles both str and list).
            if isinstance(val, dict):
                out[leaf] = {
                    (
                        opaque_id(k) if isinstance(k, str) and k else k
                    ): _opacify_list_values(v)
                    for k, v in val.items()
                }
        elif isinstance(mode, tuple) and mode[0] == "dict_list":
            fields = mode[1]
            if isinstance(val, list):
                scrubbed: list[Any] = []
                for entry in val:
                    if isinstance(entry, dict):
                        new_entry = dict(entry)
                        for f in fields:
                            if f in new_entry:
                                new_entry[f] = _opacify_list_values(new_entry[f])
                        scrubbed.append(new_entry)
                    else:
                        scrubbed.append(entry)
                out[leaf] = scrubbed
        elif mode == "atom_list":
            # A source-atom string OR a list of them (DeLP ``program`` can be
            # either); _opacify_list_values handles both shapes uniformly.
            out[leaf] = _opacify_list_values(val)
    return out


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

    # 4c. Opacify nominative list-valued leaves inside a NESTED dict sub-key
    #     of dict-of-dicts fields (dung_frameworks[*].extensions.extensions /
    #     .all_members — the Dung extensions, which are sets of the same claim
    #     texts that live in `arguments`). One level deeper than 4b; same
    #     recursive opacifier, so the nested list-of-lists (extensions) and the
    #     flat list (all_members) are both scrubbed while set arity/topology
    #     survive (#1271, po-2023 FB-39 follow-up to #1265).
    for field, nested_spec in _OPAQUE_NESTED_LIST_SUBKEYS.items():
        if field in data and isinstance(data[field], dict):
            nested_entries: dict[str, Any] = {}
            for key, val in data[field].items():
                if isinstance(val, dict):
                    new_entry = dict(val)
                    for subtree_key, leaf_subkeys in nested_spec.items():
                        subtree = new_entry.get(subtree_key)
                        if isinstance(subtree, dict):
                            new_subtree = dict(subtree)
                            for leaf in leaf_subkeys:
                                if leaf in new_subtree:
                                    new_subtree[leaf] = _opacify_list_values(
                                        new_subtree[leaf]
                                    )
                            new_entry[subtree_key] = new_subtree
                    nested_entries[key] = new_entry
                else:
                    nested_entries[key] = val
            data[field] = nested_entries

    # 4d. Opacify the Wave-2 ``formalism_specific`` sidecar on ``dung_frameworks``
    #     entries (#1702). The six #1648 writers attach this strictly-additive dict
    #     to carry formalism-specific data the native Dung projection has no slot
    #     for (ABA contraries, SetAF joint attacks, Weighted weights, EAF
    #     epistemic beliefs, DeLP program/criterion). Its nominative leaves are
    #     the same source-derived atoms passes 4b/4c opacify one level up, under a
    #     sibling key the dict-of-dicts sub-key passes never inspect. The closed-
    #     vocabulary / numeric-aggregate leaves (criterion, weight_statistics,
    #     program_size) survive by being absent from the spec table.
    if isinstance(data.get("dung_frameworks"), dict):
        for entry in data["dung_frameworks"].values():
            if isinstance(entry, dict) and "formalism_specific" in entry:
                entry["formalism_specific"] = _scrub_formalism_specific(
                    entry["formalism_specific"]
                )

    # 5. Strip nominative sub-keys from list-of-dicts fields.
    for field, text_keys in _TEXT_STRIP_LISTS.items():
        if field in data and isinstance(data[field], list) and text_keys:
            data[field] = _strip_text_from_list(data[field], text_keys)

    # 5b. Opacify the nominative sub-keys of LIST-of-dicts fields — the same
    #     claim text 4b opacifies for the dict-shaped ``dung_frameworks``
    #     (#1664). Four of the five formal-argumentation containers are
    #     declared ``List[Dict]`` and filled by ``append()``, so 4b's
    #     ``isinstance(data[field], dict)`` gate could never reach them.
    for field, subkeys in _OPAQUE_LIST_OF_DICTS_SUBKEYS.items():
        if field in data and isinstance(data[field], list):
            for item in data[field]:
                if not isinstance(item, dict):
                    continue
                for sk in subkeys:
                    if sk in item:
                        item[sk] = _opacify_list_values(item[sk])

    # 5c. Opacify the *keys* of mapping sub-keys inside list-of-dicts fields
    #     (probabilistic_results[*].acceptance_probabilities is indexed by the
    #     argument text). Values are numeric and survive, so the distribution
    #     is unaffected.
    for field, subkeys in _OPAQUE_LIST_OF_DICTS_MAPPING_KEYS.items():
        if field in data and isinstance(data[field], list):
            for item in data[field]:
                if not isinstance(item, dict):
                    continue
                for sk in subkeys:
                    mapping = item.get(sk)
                    if isinstance(mapping, dict):
                        item[sk] = {
                            (opaque_id(k) if isinstance(k, str) and k else k): v
                            for k, v in mapping.items()
                        }

    # 5d. Opacify nominative leaves one level deeper: a list-of-dicts field
    #     whose sub-key is itself a list of dicts (dialogue traces, debate
    #     exchanges). Entry count and turn structure survive.
    for field, nested_spec in _OPAQUE_NESTED_ITEM_SUBKEYS.items():
        if field in data and isinstance(data[field], list):
            for item in data[field]:
                if not isinstance(item, dict):
                    continue
                for subtree_key, leaf_subkeys in nested_spec.items():
                    subtree = item.get(subtree_key)
                    if not isinstance(subtree, list):
                        continue
                    for leaf_item in subtree:
                        if not isinstance(leaf_item, dict):
                            continue
                        for leaf in leaf_subkeys:
                            if leaf in leaf_item:
                                leaf_item[leaf] = _opacify_list_values(leaf_item[leaf])

    # 5e. Opacify nominative leaves nested inside a DICT sub-key of a
    #     list-of-dicts field (#1646): the sub-key is a single dict (not a list
    #     of dicts), so the leaves hang directly off it. Mirrors 5d one level
    #     shallower on the subtree.
    for field, nested_spec in _OPAQUE_DEEP_DICT_LEAVES.items():
        if field in data and isinstance(data[field], list):
            for item in data[field]:
                if not isinstance(item, dict):
                    continue
                for dict_key, leaf_subkeys in nested_spec.items():
                    sub = item.get(dict_key)
                    if not isinstance(sub, dict):
                        continue
                    for leaf in leaf_subkeys:
                        if leaf in sub:
                            sub[leaf] = _opacify_list_values(sub[leaf])

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
