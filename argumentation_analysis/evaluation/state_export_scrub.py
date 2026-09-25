"""Décontamination d'un état SCDA avant export — le scrub partagé.

Cette implémentation vivait dans `scripts/analysis/generate_spectacular_bundle.py`.
Un second exportateur, `scripts/analysis/export_scda_state.py`, écrivait le même
type d'état sans aucune décontamination : la seule façon d'y porter la frontière
était de recopier le scrub, et un scrub recopié diverge. `sanitize_state.py`
nommait déjà `generate_spectacular_bundle._scrub_state_for_export` comme « cible
de consolidation, pas un frère » — c'est cette consolidation (#2143).

Les noms gardent leur trait de soulignement : ce sont ceux sous lesquels
`tests/unit/scripts/analysis/test_generate_spectacular_bundle_privacy.py` lie les
objets. Les renommer déplacerait des dizaines d'assertions sans qu'aucune ne
change de sens.

Ce module n'est pas `sanitize_state.sanitize_state()` et ne prétend pas l'être :
les deux politiques diffèrent par conception et cette divergence est documentée
et testée (voir la note de la huitième passe). Ici : liste de suppression +
`<scrubbed>` + balayage d'entités sur un vocabulaire de CLASSE écrit dans ce
fichier et un vocabulaire d'INSTANCE dérivé au runtime depuis les définitions
déchiffrées en mémoire (règle 7, #2168).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Iterator, Optional, cast

# Top-level fields to remove entirely
_PRIVACY_STRIP_FIELDS = frozenset(
    {
        "raw_text",
        "full_text",
        "raw_text_snippet",
        "full_text_segment",
        "source_text",
        "text_content",
        "original_text",
    }
)

# NL fields inside dict values to replace with opaque markers
_NL_SCRUB_KEYS = frozenset(
    {
        "premisses",
        "conclusion",
        "text",
        "justification",
        "quote",
        "reformulation",
        "llm_assessment",
        "content",
        "description",
        "counter_content",
        "topic",
        "reason",
    }
)

# Debate exchanges (nested one level below transcripts): the nominative pair
# the writer stores (#2135). scheme/scheme_key/critical_question are closed
# vocabularies and intentionally absent.
_EXCHANGE_SCRUB_KEYS = frozenset({"point", "rebuttal"})


def _scrub_nl(value: Any) -> Any:
    """Replace natural-language string values with opaque marker."""
    if isinstance(value, str) and len(value) > 10:
        return "<scrubbed>"
    return value


def _strip_privacy(data: Any, depth: int = 0) -> Any:
    """Recursively strip plaintext fields and scrub NL content."""
    if depth > 12:
        return data
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in _PRIVACY_STRIP_FIELDS:
                continue
            if k in _NL_SCRUB_KEYS and isinstance(v, str):
                result[k] = "<scrubbed>"
            elif k == "content" and isinstance(v, str) and len(v) > 50:
                result[k] = "<scrubbed>"
            else:
                result[k] = _strip_privacy(v, depth + 1)
        return result
    if isinstance(data, list):
        return [_strip_privacy(item, depth + 1) for item in data]
    if isinstance(data, str) and depth == 1 and len(data) > 80:
        # Top-level string values in dicts (e.g. arg values that are raw strings)
        return "<scrubbed>"
    return data


def _iter_dimension_entries(dim: Any) -> Iterator[Dict[str, Any]]:
    """Yield the mutable entry dicts of an analysis dimension, whatever its shape.

    #1662: analysis dimensions are stored under two different shapes in
    ``UnifiedAnalysisState`` — a mapping of generated id -> entry
    (``dung_frameworks``) or a plain list of entries (``ranking_results``,
    ``probabilistic_results``, ``bipolar_results``). A scrub keyed on the
    *container's* type only ever reaches one of them. The entries themselves are
    dicts in both cases, so iterate those and let the caller work on the shape
    that is actually stable.

    Entries are yielded by reference: mutating them mutates the exported state.
    """
    if isinstance(dim, dict):
        values: Iterable[Any] = dim.values()
    elif isinstance(dim, list):
        values = dim
    else:
        return
    for item_val in values:
        if isinstance(item_val, dict):
            yield item_val


def _scrub_state_for_export(
    state_data: Dict[str, Any], instance_re: Any = None
) -> Dict[str, Any]:
    """Full privacy scrub: strip raw text + scrub NL in analysis dimensions.

    ``instance_re`` defaults to the corpus's derived instance vocabulary
    (``_instance_pattern``). Pass one explicitly only to run the pass against
    a different vocabulary — the guard does it to show a leak surviving
    without the derivation.
    """
    # First pass: strip top-level privacy fields
    cleaned = {k: v for k, v in state_data.items() if k not in _PRIVACY_STRIP_FIELDS}

    # Second pass: scrub identified_arguments
    args = cleaned.get("identified_arguments", {})
    if isinstance(args, dict):
        scrubbed_args: Dict[Any, Any] = {}
        for arg_id, arg_val in args.items():
            if isinstance(arg_val, dict):
                scrubbed_args[arg_id] = {
                    k: (
                        "<scrubbed>"
                        if k in _NL_SCRUB_KEYS and isinstance(v, str)
                        else v
                    )
                    for k, v in arg_val.items()
                }
            elif isinstance(arg_val, str):
                scrubbed_args[arg_id] = "<scrubbed>"
            else:
                scrubbed_args[arg_id] = arg_val
        cleaned["identified_arguments"] = scrubbed_args

    # Third pass: scrub identified_fallacies
    fallacies = cleaned.get("identified_fallacies", {})
    if isinstance(fallacies, dict):
        scrubbed_fallacies = {}
        for f_id, f_val in fallacies.items():
            if isinstance(f_val, dict):
                scrubbed_fallacies[f_id] = {
                    k: (
                        "<scrubbed>"
                        if k in _NL_SCRUB_KEYS and isinstance(v, str)
                        else v
                    )
                    for k, v in f_val.items()
                }
            else:
                scrubbed_fallacies[f_id] = f_val
        cleaned["identified_fallacies"] = scrubbed_fallacies

    # Fourth pass: scrub argument_quality_scores
    quality = cleaned.get("argument_quality_scores", {})
    if isinstance(quality, dict):
        scrubbed_quality = {}
        for q_id, q_val in quality.items():
            if isinstance(q_val, dict):
                scrubbed_quality[q_id] = {
                    k: (
                        "<scrubbed>"
                        if k in _NL_SCRUB_KEYS and isinstance(v, str)
                        else v
                    )
                    for k, v in q_val.items()
                }
            else:
                scrubbed_quality[q_id] = q_val
        cleaned["argument_quality_scores"] = scrubbed_quality

    # Fifth pass: scrub counter_arguments
    counters = cleaned.get("counter_arguments", [])
    if isinstance(counters, list):
        cleaned["counter_arguments"] = [
            (
                {
                    k: (
                        "<scrubbed>"
                        if k in _NL_SCRUB_KEYS and isinstance(v, str)
                        else v
                    )
                    for k, v in ca.items()
                }
                if isinstance(ca, dict)
                else ca
            )
            for ca in counters
        ]

    # Sixth pass: scrub debate_transcripts — transcript-level keys AND the
    # nested exchanges (#2135: the writer stores point/rebuttal inside
    # exchanges; topic at transcript level). Closed-vocab scheme fields survive.
    debates = cleaned.get("debate_transcripts", [])
    if isinstance(debates, list):
        scrubbed_debates = []
        for dt in debates:
            if not isinstance(dt, dict):
                scrubbed_debates.append(dt)
                continue
            dt = {
                k: ("<scrubbed>" if k in _NL_SCRUB_KEYS and isinstance(v, str) else v)
                for k, v in dt.items()
            }
            exchanges = dt.get("exchanges")
            if isinstance(exchanges, list):
                dt["exchanges"] = [
                    (
                        {
                            k: (
                                "<scrubbed>"
                                if k in _EXCHANGE_SCRUB_KEYS and isinstance(v, str)
                                else v
                            )
                            for k, v in ex.items()
                        }
                        if isinstance(ex, dict)
                        else ex
                    )
                    for ex in exchanges
                ]
            scrubbed_debates.append(dt)
        cleaned["debate_transcripts"] = scrubbed_debates

    # Seventh pass: scrub belief_sets content
    belief_sets = cleaned.get("belief_sets", {})
    if isinstance(belief_sets, dict):
        scrubbed_bs = {}
        for bs_id, bs_val in belief_sets.items():
            if isinstance(bs_val, dict):
                content = bs_val.get("content", "")
                if isinstance(content, str) and len(content) > 20:
                    bs_val = {**bs_val, "content": "<scrubbed>"}
                # PL atoms are named after the text (#2643): opaque ids only.
                propositions = bs_val.get("propositions")
                if isinstance(propositions, list):
                    bs_val = {
                        **bs_val,
                        "propositions": [f"p{i}" for i in range(len(propositions))],
                    }
                scrubbed_bs[bs_id] = bs_val
            else:
                scrubbed_bs[bs_id] = bs_val
        cleaned["belief_sets"] = scrubbed_bs

    # Eighth pass: scrub extracts entries regardless of container shape (#1673).
    # Prod is List[Dict] via add_extract (shared_state.py:94) but the scrub must
    # not gate on the container type — _iter_dimension_entries yields the dict
    # entries whether the container is a list or a mapping (#1662, same family).
    # Divergence note: sanitize_state.py preserves extracts[*].name as a join
    # key for its downstream consumer (l.35-38); this pass scrubs any value
    # above threshold, name included. The two agree on all measured state
    # (0/97 names reach threshold) and this script has no join-key consumer —
    # aligning them without a consumer to arbitrate would be a blind call.
    for entry in _iter_dimension_entries(cleaned.get("extracts")):
        for k, v in list(entry.items()):
            if isinstance(v, str) and len(v) > 20:
                entry[k] = "<scrubbed>"

    # Ninth pass: scrub analysis_tasks (may contain NL instructions)
    tasks = cleaned.get("analysis_tasks", {})
    if isinstance(tasks, dict):
        cleaned["analysis_tasks"] = {
            k: ("<scrubbed>" if isinstance(v, str) and len(v) > 50 else v)
            for k, v in tasks.items()
        }

    # Tenth pass: scrub final_conclusion if present
    conclusion = cleaned.get("final_conclusion")
    if isinstance(conclusion, str) and len(conclusion) > 20:
        cleaned["final_conclusion"] = "<scrubbed>"

    # Eleventh pass: scrub nl_to_logic_translations (FOL predicate slugs embed entities)
    nl_trans = cleaned.get("nl_to_logic_translations", [])
    if isinstance(nl_trans, list):
        scrubbed_nl = []
        for entry in nl_trans:
            if isinstance(entry, dict):
                scrubbed_entry: Dict[Any, Any] = {}
                for k, v in entry.items():
                    if k == "formula":
                        scrubbed_entry[k] = "<scrubbed>"
                    elif k == "original_text":
                        scrubbed_entry[k] = "<scrubbed>"
                    elif k == "variables" and isinstance(v, dict):
                        scrubbed_vars: Dict[Any, Any] = {}
                        for vk, vv in v.items():
                            safe_key = (
                                _global_entity_scrub(vk) if isinstance(vk, str) else vk
                            )
                            if isinstance(safe_key, str) and safe_key != vk:
                                scrubbed_vars[f"var_{len(scrubbed_vars)}"] = vv
                            else:
                                scrubbed_vars[vk] = vv
                        scrubbed_entry[k] = scrubbed_vars
                    else:
                        scrubbed_entry[k] = v
                scrubbed_nl.append(scrubbed_entry)
            else:
                scrubbed_nl.append(entry)
        cleaned["nl_to_logic_translations"] = scrubbed_nl

    # Twelfth pass: scrub nested structures containing argument descriptions
    # (dung_frameworks, ranking_results, probabilistic_results, bipolar_results).
    # Each entry stores List[str] under key "arguments" with raw NL descriptions
    # that bypass the identified_arguments scrub (Pass 2).
    # Note: container shapes differ — see core/shared_state.py:
    #   dung_frameworks:    Dict[str, Dict[str, Any]] (keyed by framework id)
    #   ranking_results:    List[Dict[str, Any]] (append-ordered)
    #   probabilistic_results: List[Dict[str, Any]] (append-ordered)
    #   bipolar_results:    List[Dict[str, Any]] (append-ordered)
    for dim_key in (
        "dung_frameworks",
        "ranking_results",
        "probabilistic_results",
        "bipolar_results",
    ):
        for item_val in _iter_dimension_entries(cleaned.get(dim_key)):
            args_list = item_val.get("arguments")
            if isinstance(args_list, list):
                item_val["arguments"] = [
                    ("<scrubbed>" if isinstance(a, str) and len(a) > 10 else a)
                    for a in args_list
                ]
            # Also scrub "name" field (often contains NL descriptions)
            name = item_val.get("name")
            if isinstance(name, str) and len(name) > 20:
                item_val["name"] = "<scrubbed>"

    # Final pass: global regex scrub on ALL remaining strings (values AND keys)
    return cast(Dict[str, Any], _global_entity_scrub(cleaned, instance_re=instance_re))


# Entity patterns that must never appear in exports.
#
# CLASS vocabulary only (rule 7): generic public vocabulary — public figures,
# states, parties — which is safe to enumerate in a tracked file because it
# maps onto no particular document. The INSTANCE vocabulary (the labels that
# map onto a document of our census) used to sit in this list too; it is now
# derived at run time — see ``_instance_pattern`` and
# ``argumentation_analysis.evaluation.corpus_instance_tokens``. Rule 7:
# "a detector that enumerates corpus identifiers publishes the census the
# encryption protects" (#2168, #2187).
#
# The PERSON alternation is derived from ``PERSON_PATTERNS`` (#2348 pattern,
# #2362 B1): a hand list is a second census that drifts, and the production
# sweep (#2349) reddens on every class member spelled in a tracked file.
# Coverage is WIDENED, not narrowed — the class list carries more members
# than the hand list it replaces, and a scrubber may grow, never shrink
# silently (#1019). The behavior half of that move is pinned by
# ``test_redaction_by_class_2362``: the sweep sees presence, not redaction.
from argumentation_analysis.evaluation.leak_patterns import PERSON_PATTERNS

# Public figures outside the class lists (kept verbatim until the class
# vocabulary itself is arbitrated — Q-R1042-A family; dropping them would be
# a silent narrowing of the scrubber).
_EXTRA_PUBLIC_PERSONS = ("obama", "harris", "clinton", "attal", "netanyahu")

_PERSON_ALTERNATION = "|".join([*PERSON_PATTERNS, *_EXTRA_PUBLIC_PERSONS])

# States, groups, institutions: public generic vocabulary (organisations and
# country names map onto no corpus document); spelling variants absent from
# the class lists stay spelled here.
_ENTITY_PATTERN = re.compile(
    rf"(?i)\b({_PERSON_ALTERNATION})"
    r"|\b(iran|ukraine|russia|china|israel|otan|onu|nato|maidan|crimea|bolchevik|bolchévik)"
    r"|\b(pentagon|white\s*house|united\s*nations|un\s*general\s*assembly)"
    r"|\b(russie|chinese|américaine)\b",
)

# Substring pattern for snake_case identifiers where \b doesn't match
_ENTITY_SUBSTR_PATTERN = re.compile(
    rf"(?i)({_PERSON_ALTERNATION}"
    r"|iran|ukraine|russia|china|israel|otan|onu|nato|maidan|crimea|bolchevik"
    r"|pentagon|white_house|united_nations)"
)

#: Matches nothing. Used when the instance vocabulary is empty (a test that
#: must prove a leak survives without the derivation), so an empty alternation
#: can never degrade into a pattern that matches every string.
_NEVER_MATCHES = re.compile(r"(?!x)x")

_INSTANCE_PATTERN: Optional[re.Pattern[str]] = None


def _load_instance_tokens() -> frozenset[str]:
    """Seam over the derivation, so the heavy import stays out of this module.

    Tests patch *this* name to feed a synthetic census — never a real label
    written down for the occasion.
    """
    from argumentation_analysis.evaluation.corpus_instance_tokens import (
        load_instance_tokens,
    )

    return load_instance_tokens()


def _compile_instance_pattern(tokens: Iterable[str]) -> re.Pattern[str]:
    """Instance alternatives, on the same letter frontier as the class ones.

    A letter boundary (not ``\\b``) so a label is caught in prose *and* inside
    the snake_case identifiers it takes when it enters code (#2012).
    """
    alternatives = "|".join(
        re.escape(token) for token in sorted(tokens, key=len, reverse=True)
    )
    if not alternatives:
        return _NEVER_MATCHES
    return re.compile(rf"(?<![A-Za-z])(?:{alternatives})(?![A-Za-z])", re.IGNORECASE)


def _instance_pattern() -> re.Pattern[str]:
    """The corpus's instance vocabulary, derived in memory and cached.

    Fails loud (``CorpusUnavailableError``) rather than scrubbing with a
    truncated vocabulary: an export produced under a silently weakened
    redaction is worse than no export.
    """
    global _INSTANCE_PATTERN
    if _INSTANCE_PATTERN is None:
        _INSTANCE_PATTERN = _compile_instance_pattern(_load_instance_tokens())
    return _INSTANCE_PATTERN


def _global_entity_scrub(data: Any, depth: int = 0, instance_re: Any = None) -> Any:
    """Recursively replace any string containing entity names with <scrubbed>.
    Also scrubs dict keys that contain entity names (even in snake_case identifiers).

    ``instance_re`` carries the corpus's derived instance vocabulary. It is
    resolved once by the caller (``_scrub_state_for_export``) and threaded
    through rather than re-resolved per node; passing it explicitly is also
    what lets a test run the pass with an empty vocabulary and observe the
    leak the derivation is there to catch.
    """
    if instance_re is None:
        instance_re = _instance_pattern()
    if depth > 15:
        return data
    if isinstance(data, str):
        if (
            _ENTITY_PATTERN.search(data)
            or _ENTITY_SUBSTR_PATTERN.search(data)
            or instance_re.search(data)
        ):
            return "<scrubbed>"
        return data
    if isinstance(data, dict):
        result: Dict[Any, Any] = {}
        for k, v in data.items():
            safe_key = (
                _global_entity_scrub(k, depth + 1, instance_re)
                if isinstance(k, str)
                else k
            )
            if isinstance(safe_key, str) and safe_key == "<scrubbed>":
                safe_key = f"key_{len(result)}"
            result[safe_key] = _global_entity_scrub(v, depth + 1, instance_re)
        return result
    if isinstance(data, list):
        return [_global_entity_scrub(item, depth + 1, instance_re) for item in data]
    return data
