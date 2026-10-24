"""#2850 — census guard: every coverage-limiting site is registered debt.

The audit measured that a long document is analysed on its opening only:
one 3,000-char LLM extraction window, whole-text heuristic units no
specialist ever touches, and a dozen ``[:N]`` population caps that keep the
first N in insertion order. This guard is the census half of the DoD: on the
analysis path (``argumentation_analysis``), every site that limits coverage
must appear in ``REGISTRY`` below with a contract — what it drops, and where
the render says so. Existing sites are entered as NAMED DEBT (#2850): the
registry is the triage table, not an approval.

Three site classes, read on the AST (never grep — the #1842 pattern):

- ``window`` — a ``selected_text(...)`` / ``selected_text_and_selection(...)``
  call (the #1737 shared mechanism; #3136 added the second spelling, which
  returns the selection as well), or a head slice of a text-bearing
  variable. The reading window decides which part of the document reaches
  the phase at all. Both spellings are censused under ``selected_text``:
  a bounded read must not escape the census by changing its name.
- ``population_cap`` — a head slice over a collection of arguments, claims,
  fallacies/sophisms or counter-arguments: insertion order decides which
  units reach a specialist.
- ``display`` — a truncation of an already-produced string or collection
  for rendering. Not a coverage site, but censused so the classification is
  a claim someone made, not silence.

Census boundary, stated rather than hidden: a site is read when its slice
base carries one of the tokens ``arg``, ``claim``, ``fallac``, ``sophism``,
``counter``, ``sentence``, ``segment``, ``chunk``, ``premise``, ``text``
(case-insensitive; ``list(x.items())[:N]`` is unwrapped to ``x``). The
sentence/segment/chunk/premise tokens were added in the #2854 re-triage:
``sentences[:6]`` is the document's population of argument candidates, not a
render — extending the unit tokens censused 11 previously invisible sites. A
differently-named collection (``results[:4]``) is outside the census — the
boundary is held by the negative-control test below, so it is a documented
limit, not an unknown one.

Registry keys are semantic — ``(relpath, base, cap, ordinal)`` — so a moved
line stays green while a changed cap, a renamed base, a new site or a
deleted one reddens. Ordinals count the occurrences sharing the same first
three fields, in ``ast.walk`` order; the row's lineno is carried in the
census value for readable failures.
"""

import ast
import re
from pathlib import Path

import pytest

from tests.support.tree_walk import iter_tracked_files

ROOT = Path(__file__).resolve().parents[3]

_MECHANISM_MODULE = "argumentation_analysis/core/reading_window.py"
_TEXT_TOKEN = re.compile(r"text", re.IGNORECASE)
_UNIT_TOKEN = re.compile(
    r"arg|claim|fallac|sophism|counter|sentence|segment|chunk|premise", re.IGNORECASE
)


def _base_name(node: ast.expr) -> "str | None":
    """Unwrap ``list(x.items())`` / ``x.values()`` / ``list(x)`` to ``x``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "list" and node.args:
            return _base_name(node.args[0])
        if isinstance(node.func, ast.Attribute) and node.func.attr in (
            "items",
            "values",
            "keys",
        ):
            return _base_name(node.func.value)
    return None


def _upper_repr(node: ast.expr) -> str:
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    return "expr"


def _is_head_slice(node: ast.expr) -> bool:
    """``[:x]`` — lower bound absent, upper bound present, no step."""
    return (
        isinstance(node, ast.Slice)
        and node.lower is None
        and node.upper is not None
        and node.step is None
    )


def _sites_in_tree(tree: ast.Module) -> "list[tuple[str, str, str, int, str]]":
    """(kind, base, cap, lineno, cls) for every coverage site in one module.

    ``kind`` is the raw syntactic class; the registry's contract carries the
    triaged kind (a ``text_head`` row can be triaged ``window`` or
    ``display``).
    """
    found: "list[tuple[str, str, str, int, str]]" = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                getattr(func, "attr", None)
                if isinstance(func, ast.Attribute)
                else (func.id if isinstance(func, ast.Name) else None)
            )
            if name in ("selected_text", "selected_text_and_selection"):
                # #3136 — the second spelling is the same #1737 mechanism
                # with the selection returned (the caller amends its own
                # entry). One base keeps every bounded read in the census.
                cap = _upper_repr(node.args[1]) if len(node.args) > 1 else "?"
                found.append(
                    ("selected_text", cap, str(node.lineno), node.lineno, "window")
                )
        elif isinstance(node, ast.Subscript) and _is_head_slice(node.slice):
            base = _base_name(node.value)
            if base is None:
                continue
            cap = _upper_repr(node.slice.upper)
            if _TEXT_TOKEN.search(base):
                found.append((base, cap, str(node.lineno), node.lineno, "text_head"))
            elif _UNIT_TOKEN.search(base):
                found.append(
                    (base, cap, str(node.lineno), node.lineno, "collection_head")
                )
    return found


def census() -> "dict[tuple[str, str, str, int], tuple[str, int, str]]":
    """Every coverage site in the tracked ``argumentation_analysis`` tree.

    Key: ``(relpath, base, cap, ordinal)``. Value: ``(cls, lineno)`` — the
    raw syntactic class and the site's line, for readable failures.
    """
    rows: "dict[tuple[str, str, str, int], tuple[str, int]]" = {}
    ordinal_of: "dict[tuple[str, str, str], int]" = {}
    for path in iter_tracked_files(ROOT):
        rel = path.relative_to(ROOT).as_posix()
        if not rel.startswith("argumentation_analysis/"):
            continue
        if rel == _MECHANISM_MODULE:
            # The shared mechanism's own delegation (#3136 made it two
            # functions) is not a bounded read: the call sites it serves are
            # censused at their own modules.
            continue
        tree = _parse_module(path, rel)
        for base, cap, _line_str, lineno, cls in _sites_in_tree(tree):
            key3 = (rel, base, cap)
            ordinal_of[key3] = ordinal_of.get(key3, 0) + 1
            rows[(rel, base, cap, ordinal_of[key3])] = (cls, lineno)
    return rows


def _parse_module(path: Path, rel: str) -> ast.Module:
    """Parse one census module, failing LOUD — a census that skips what it
    cannot read measures nothing (#1019). ``utf-8-sig`` because tracked
    modules carry a BOM (measured at guard birth: 10 files)."""
    try:
        return ast.parse(path.read_text(encoding="utf-8-sig"))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        raise RuntimeError(f"census cannot parse {rel}: {exc!r} (#2850)") from exc


# (relpath, base, cap, ordinal) -> (triaged kind, drops, where the render says so).
# Generated from the main census at guard birth; every window/population_cap
# row names #2850 — the debt is registered, never silent.
REGISTRY = {
    (
        "argumentation_analysis/adapters/french_fallacy_adapter.py",
        "FALLACY_LABELS_FR",
        "15",
        1,
    ): ("display", "first 15 of the rendered collection", "display only"),
    (
        "argumentation_analysis/adapters/french_fallacy_adapter.py",
        "selected_text",
        "LLM_EXTRACTION_WINDOW",
        1,
    ): (
        "window",
        "3000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    # --- #2912: the seven off-pipeline unbounded readers enter as windows ---
    (
        "argumentation_analysis/adapters/french_fallacy_adapter.py",
        "selected_text",
        "LLM_EXTRACTION_WINDOW",
        2,
    ): (
        "window",
        "self-hosted tier prompt reads the selected 3000, not the whole text",
        "silent — debt #2850 (was census debt #2908, bounded #2912)",
    ),
    (
        "argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py",
        "selected_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "concrete agent's prompt reads the selected 8000 of its input",
        "silent — debt #2850 (was census debt #2908, bounded #2912)",
    ),
    (
        "argumentation_analysis/orchestration/analysis_runner_v2.py",
        "selected_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "conversational-v2 Phase-1 PM prompt reads the selected 8000",
        "recorded via state= (#2915 item 5); Acts silent — #2850 "
        "(was census debt #2908, bounded #2912)",
    ),
    (
        "argumentation_analysis/orchestration/conversational_orchestrator.py",
        "selected_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "extraction opening prompt reads the selected 8000 (FR and DE variants)",
        "stateless — no shared state reachable in run_conversational_analysis "
        "(#2915 item 5); Acts silent — #2850 (was census debt #2908, bounded #2912)",
    ),
    (
        "argumentation_analysis/orchestration/hierarchical/operational/adapters/informal_agent_adapter.py",
        "selected_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "hierarchical adapter prompt reads the selected 8000 of the joined extracts",
        "silent — debt #2850 (was census debt #2908, bounded #2912)",
    ),
    (
        "argumentation_analysis/utils/extract_repair/verify_extracts_with_llm.py",
        "selected_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "extract-evaluation prompt reads the selected 8000 of the extract",
        "silent — debt #2850 (was census debt #2908, bounded #2912)",
    ),
    ("argumentation_analysis/adapters/french_fallacy_adapter.py", "target", "200", 1): (
        "display",
        "first 200 of the rendered collection",
        "display only",
    ),
    (
        "argumentation_analysis/agents/core/counter_argument/parser.py",
        "text",
        "expr",
        1,
    ): ("display", "first expr chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/core/counter_argument/parser.py",
        "text",
        "start",
        1,
    ): ("display", "first start chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/core/counter_argument/parser.py",
        "sentences",
        "expr",
        1,
    ): (
        "display",
        "no drop — premise/conclusion fallback split, every sentence used",
        "display only",
    ),
    (
        "argumentation_analysis/agents/core/informal/neuro_symbolic_arbitrator.py",
        "input_text",
        "8000",
        1,
    ): ("window", "first 8000 chars of the source text", "silent — debt #2850"),
    (
        "argumentation_analysis/agents/core/informal/neuro_symbolic_arbitrator.py",
        "raw_fallacies",
        "max_candidates",
        1,
    ): (
        "population_cap",
        "first max_candidates in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/agents/core/informal/neuro_symbolic_arbitrator.py",
        "span_text",
        "3000",
        1,
    ): ("window", "first 3000 chars of the source text", "silent — debt #2850"),
    (
        "argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py",
        "detected_sophisms",
        "max_sophisms",
        1,
    ): (
        "population_cap",
        "first max_sophisms in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py",
        "matching_sophisms",
        "max_results",
        1,
    ): (
        "population_cap",
        "first max_results in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/agents/core/logic/propositional_logic_agent.py",
        "text",
        "100",
        1,
    ): ("display", "first 100 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/core/logic/propositional_logic_agent.py",
        "text",
        "100",
        2,
    ): ("display", "first 100 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/core/logic/tweety_bridge_sk.py",
        "text",
        "100",
        1,
    ): ("display", "first 100 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/core/logic/tweety_bridge_sk.py",
        "text",
        "100",
        2,
    ): ("display", "first 100 chars of an already-produced string", "display only"),
    ("argumentation_analysis/agents/core/logic/tweety_bridge_sk.py", "text", "50", 1): (
        "display",
        "first 50 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/agents/core/political/stakes_extractor.py",
        "arguments",
        "30",
        1,
    ): (
        "population_cap",
        "first 30 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/agents/core/political/stakes_extractor.py",
        "selected_text",
        "LLM_EXTRACTION_WINDOW",
        1,
    ): (
        "window",
        "3000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    (
        "argumentation_analysis/agents/core/political/stakes_extractor.py",
        "text",
        "200",
        1,
    ): (
        "window",
        "argument excerpts capped at 200 chars inside the stakes prompt block",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/agents/core/quality/agentic_virtue_detectors.py",
        "arg_text",
        "4000",
        1,
    ): ("window", "first 4000 chars of the source text", "silent — debt #2850"),
    ("argumentation_analysis/agents/sherlock_jtms_agent.py", "context", "100", 1): (
        "display",
        "first 100 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/agents/sherlock_jtms_agent.py", "text", "100", 1): (
        "display",
        "first 100 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/agents/tools/analysis/fact_claim_extractor.py",
        "claims",
        "max_claims",
        1,
    ): (
        "population_cap",
        "first max_claims in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/agents/tools/analysis/fallacy_family_analyzer.py",
        "text",
        "100",
        1,
    ): ("display", "first 100 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/tools/analysis/new/argument_structure_visualizer.py",
        "argument",
        "50",
        1,
    ): ("display", "first 50 of the rendered collection", "display only"),
    (
        "argumentation_analysis/agents/tools/analysis/new/contextual_fallacy_detector.py",
        "argument",
        "50",
        1,
    ): ("display", "first 50 of the rendered collection", "display only"),
    (
        "argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py",
        "arg_text",
        "30",
        1,
    ): ("display", "first 30 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py",
        "arg_text",
        "50",
        1,
    ): ("display", "first 50 chars of an already-produced string", "display only"),
    ("argumentation_analysis/cli/output_formatter.py", "args", "10", 1): (
        "display",
        "first 10 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/cli/output_formatter.py", "counters", "5", 1): (
        "display",
        "first 5 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/cli/output_formatter.py", "fallacies", "10", 1): (
        "display",
        "first 10 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/cli/output_formatter.py", "text", "expr", 1): (
        "display",
        "first expr chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/core/phase_scoped_state.py", "original_text", "200", 1): (
        "display",
        "first 200 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/core/shared_state.py", "arg_desc", "40", 1): (
        "display",
        "first 40 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/core/shared_state.py", "arg_desc", "60", 1): (
        "display",
        "first 60 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/core/shared_state.py", "arg_desc", "60", 2): (
        "display",
        "first 60 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/core/shared_state.py", "original_text", "200", 1): (
        "display",
        "first 200 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/core/state_manager_plugin.py",
        "original_text",
        "200",
        1,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/core/utils/reporting_utils.py",
        "context_text",
        "200",
        1,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/core/utils/reporting_utils.py",
        "original_text",
        "500",
        1,
    ): ("display", "first 500 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/core/utils/text_utils.py",
        "extracted_segment",
        "100",
        1,
    ): ("display", "log-line preview of the extracted segment", "display only"),
    (
        "argumentation_analysis/evaluation/benchmark_runner.py",
        "text",
        "max_text_chars",
        1,
    ): (
        "window",
        "first max_text_chars chars of the source text",
        "silent — debt #2850",
    ),
    ("argumentation_analysis/evaluation/capability_eval.py", "marginals", "5", 1): (
        "display",
        "first 5 of the rendered collection",
        "display only",
    ),
    (
        "argumentation_analysis/evaluation/judge.py",
        "selected_text",
        "_JUDGE_INPUT_WINDOW",
        1,
    ): (
        "window",
        "2000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    ("argumentation_analysis/evaluation/judge.py", "text", "200", 1): (
        "display",
        "first 200 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "arguments",
        "6",
        1,
    ): (
        "population_cap",
        "first 6 in insertion order; rest unanalysed",
        "recorded — the no-key fallback payload's arguments_basis names the "
        "stateless_arguments k de N (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "arguments",
        "8",
        1,
    ): (
        "population_cap",
        "first 8 in insertion order; rest unanalysed",
        "recorded — the debate payload's arguments_basis names the "
        "extract_arguments k de N (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "claims",
        "8",
        1,
    ): (
        "population_cap",
        "first 8 in insertion order; rest unanalysed",
        "recorded — the debate payload's arguments_basis names the "
        "extract_claims k de N (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "sentences",
        "6",
        1,
    ): (
        "population_cap",
        "only the first 6 sentences are debated; rest unanalysed",
        "recorded — the debate payload's arguments_basis names the sentences "
        "k de N (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "selected_text",
        "DEBATE_FALLBACK_WINDOW",
        1,
    ): (
        "window",
        "1500-char window from the selected offset",
        "record_reading_window; measured live (lot 5): reachable when no "
        "sentence exceeds 15 chars — witness pins it; the Acts quote the "
        "recorded bound since lot 6 (reading_record) — #2850",
    ),
    (
        "argumentation_analysis/orchestration/conversation_orchestrator.py",
        "args_str",
        "97",
        1,
    ): (
        "population_cap",
        "first 97 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/conversation_orchestrator.py",
        "fallacies",
        "5",
        1,
    ): (
        "population_cap",
        "first 5 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/conversation_orchestrator.py",
        "text",
        "50",
        1,
    ): ("display", "first 50 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/orchestration/conversation_orchestrator.py",
        "text",
        "50",
        2,
    ): ("display", "first 50 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/orchestration/conversation_orchestrator.py",
        "text",
        "50",
        3,
    ): ("display", "first 50 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/orchestration/conversational_orchestrator.py",
        "fallacy_type",
        "20",
        1,
    ): ("display", "first 20 of the rendered collection", "display only"),
    (
        "argumentation_analysis/orchestration/conversational_orchestrator.py",
        "selected_text",
        "_LANGUAGE_PROBE_WINDOW",
        1,
    ): (
        "window",
        "3000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    ("argumentation_analysis/orchestration/group_chat.py", "text", "50", 1): (
        "display",
        "first 50 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/orchestration/hierarchical/strategic/manager.py",
        "selected_text",
        "_OBJECTIVES_PREVIEW_WINDOW",
        1,
    ): (
        "window",
        "2000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "arg", "80", 1): (
        "display",
        "first 80 of the rendered collection",
        "display only",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "arg_names",
        "expr",
        1,
    ): (
        "population_cap",
        "claim i's justification cites the first min(i+2, len) assumptions in "
        "selection order — an edge-construction head over the recorded "
        "selection (every selected assumption is already in the network; no "
        "unit is dropped from analysis)",
        "the selection is recorded via record_analysis_coverage('atms'); the edge head stays debt #2850 lot 3",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "arg_names",
        "expr",
        2,
    ): (
        "population_cap",
        "h_partial_accept's assumption set is every selected assumption but "
        "the last — a hypothesis-design partition over the recorded "
        "selection, not a corpus drop",
        "the atms trace summary names the hypothesis contexts; the partition stays debt #2850 lot 3",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "arg_names",
        "mid",
        1,
    ): (
        "population_cap",
        "h_first_half's assumption set is the first half of the selected "
        "assumptions — a hypothesis-design partition over the recorded "
        "selection, not a corpus drop",
        "the atms trace summary names the hypothesis contexts; the partition stays debt #2850 lot 3",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "arg_text",
        "200",
        1,
    ): (
        "window",
        "argument excerpt inside the LLM quality-enrichment prompt",
        "recorded — lot 4's llm_enrichment payload key became the persisted "
        "reader: basis.unit_excerpt_chars + units_in_prompt ride the parsed "
        "dict, and the quality trace names the 200-char excerpts (#2850 lot 5)",
    ),
    # #3030 — the NL-fallback head slices: the base moved from the raw
    # extraction window (args) to the recorded selection (_pl_targets /
    # _fol_targets); the cap and the contract are unchanged. #3030 residual
    # (coord review R1088): when the fallback PRODUCES, the coverage record
    # is re-recorded over these 4 attempted units — the rest is NOT picked
    # up by the PL template in that case (it only fires on an empty
    # fallback), so the remainder stays unanalysed on both axes.
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "_pl_targets",
        "4",
        1,
    ): (
        "population_cap",
        "first 4 in text order of the recorded selection; on fallback success the record re-names these 4 (attempted) and the rest is unanalysed; on fallback failure the template arm takes the whole selection",
        "recorded via record_analysis_coverage('propositional_logic') over the attempted head — the cap itself stays debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "_fol_targets",
        "4",
        1,
    ): (
        "population_cap",
        "first 4 in text order of the recorded selection; on fallback success the record re-names these 4 (attempted) and the rest is unanalysed; FOL has no template arm",
        "recorded via record_analysis_coverage('fol_reasoning') over the attempted head — the cap itself stays debt #2850",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "arguments", "4", 1): (
        "population_cap",
        "first 4 in insertion order; rest unanalysed",
        "stateless fallback named — #2850 slice A: when a state mints units the "
        "defeasible rules cite the stratified selection of the frame's units "
        "(record_analysis_coverage('aspic') + aspic_units_considered/_total on "
        "the payload); this [:4] head is what a stateless run reads",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "args", "40", 1): (
        "population_cap",
        "first 40 in insertion order; rest unanalysed",
        "recorded — the helper fills the caller's basis dict; the stateless "
        "arms carry it (pl_metrics/fol_metrics arguments_basis, the nl_to_logic "
        "phase payload, the population tail note) (#2850 lot 5)",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "args", "mid", 1): (
        "population_cap",
        "first mid in insertion order; rest unanalysed",
        "partition, not a cap — #2850: the head half is the proponent's side "
        "and the tail (args[mid:]) is the opponent's; no unit is dropped by "
        "this slice (the split is the dialogue's two-player design)",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "arguments", "6", 1): (
        "population_cap",
        "stateless fallback: first 6 of the extract window become the conflict-detector positions; with a state the positions are the stratified merged-population selection",
        "fallback named — #2850 slice A (recorded via record_analysis_coverage('governance') when a state exists)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "arguments",
        "expr",
        1,
    ): (
        "population_cap",
        "the first min(3, N) arguments become the ABA assumptions under test",
        "recorded — assumptions_basis (tested de N) on the ABA payload's "
        "identity echo (#2850 lot 5)",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "ca_text", "20", 1): (
        "display",
        "first 20 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "claims", "4", 1): (
        "population_cap",
        "first 4 in insertion order; rest unanalysed",
        "recorded via aspic_claims_considered/_total on the phase payload and "
        "the aspic trace summary (deep-synthesis trace reader) — cap stays "
        "debt #2850 (claims are produced facts, not the argument population)",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "claims", "6", 1): (
        "population_cap",
        "first 6 claims become the conflict-detector positions when neither a population nor extract arguments exist",
        "recorded via record_analysis_coverage('governance') k of N claims when a state exists — cap stays debt #2850 (claims are produced facts, not the argument population)",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "claims", "8", 1): (
        "population_cap",
        "first 8 in insertion order; rest unanalysed",
        "recorded — the helper's extract_claims basis, carried by the stateless "
        "arms as for args[:40] (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "counter_args",
        "4",
        1,
    ): (
        "population_cap",
        "first 4 counter-arguments become competing beliefs; the rest is unanalysed",
        "recorded via counter_arguments_considered/_total on the phase payload and the jtms trace summary (deep-synthesis trace reader) — cap stays debt #2850",
    ),
    # #1649 case 5: the undercut lever's counter window (first 4 counters
    # considered; the rest are not candidates for an inference undercut).
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "_aspic_counters",
        "4",
        1,
    ): (
        "population_cap",
        "first 4 counters in insertion order are considered for an "
        "inference undercut; the rest emit nothing and feed no attack",
        "recorded via aspic_undercut_considered/_total on the phase payload "
        "and the aspic trace summary — cap stays debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "detected_fallacies",
        "4",
        1,
    ): (
        "population_cap",
        "first 4 detections become CONTRA contradiction nodes; the rest is unanalysed",
        "recorded via fallacies_considered/fallacies_total on the phase payload and the atms trace summary (deep-synthesis trace reader) — cap stays debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "detected_fallacies",
        "6",
        1,
    ): (
        "population_cap",
        "first 6 detected fallacies feed the retraction network; the rest is unanalysed",
        "recorded via fallacies_considered/_total on the phase payload and the "
        "jtms trace summary (deep-synthesis trace reader) — cap stays debt "
        "#2850 (batch 1 had put this contract on ord=2 by reading the walk as "
        "file order; ast.walk is BFS, and the census maps ord=1 to the jtms "
        "site at :3152)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "detected_fallacies",
        "6",
        2,
    ): (
        "population_cap",
        "first 6 detections build the quality-enrichment prompt's fallacy context",
        "recorded — lot 4 kept this one unnamed for want of a persisted "
        "reader; lot 4's own llm_enrichment payload became one: basis."
        "fallacies_in_prompt de fallacies_available + fallacy_cross_reference."
        "prompt_shown pair shown de found (#2850 lot 5)",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "fallacies", "3", 1): (
        "population_cap",
        "first 3 in insertion order; rest unanalysed",
        "recorded via aspic_fallacies_considered/_total on the phase payload "
        "and the aspic trace summary (deep-synthesis trace reader) — cap "
        "stays debt #2850",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "fallacies", "6", 1): (
        "population_cap",
        "only the first 6 detections feed h_fallacy_excluded's exclusion targets; targets beyond the head leave their arguments inside the hypothesis",
        "recorded via hypothesis_fallacy_targets_considered/_total on the phase payload and the atms trace summary — cap stays debt #2850 lot 3",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "input_text",
        "200",
        1,
    ): (
        "window",
        "the stateless argument population's absolute fallback: the document's "
        "first 200 chars stand in as the single argument",
        "recorded — the helper's document_opening basis path (window_chars) "
        "carried by the stateless arms (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "input_text",
        "200",
        2,
    ): (
        "population_cap",
        "the dialogue topic defaults to the document's first 200 chars when "
        "the caller names none",
        "topic default named — #2850: the reader is the dialogue trace's "
        "round-1 assertion (the handler echoes the topic as the debated "
        "argument; topic_accepted says whether it grounds); the analysis "
        "population is the frame's nodes, not this slice",
    ),
    # #2850 lot 6: the four reconstruction-path ballast entries that sat at
    # ordinals 3-6 here are GONE — the sites were un-seeded (the state no
    # longer claims a head it never had). Census ordinals renumber, so this
    # #3 is the counter-argument target default that used to be #7: the key
    # is semantic in name only, verify the line (invoke_callables.py:2026)
    # before trusting any row.
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "input_text",
        "200",
        3,
    ): (
        "window",
        "the counter-argument target defaults to the first 200 chars",
        "recorded — each evaluation dict carries target_basis "
        "(default_opening/named_target) and the counter trace counts k de n "
        "evaluations against the opening (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "input_text",
        "60",
        1,
    ): ("display", "first 60 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "input_text",
        "_LOCAL_LLM_WINDOW_CHARS",
        1,
    ): (
        "window",
        "the local-tier fallback head window: the document beyond the first "
        "12000 chars, read only when NO extracted population exists (#3124) "
        "— with a population the phase sends the #2850 selection of units "
        "and nothing is windowed",
        "recorded — input_mode='document_window' + input_truncated + "
        "input_chars_total on the local_llm_results record; the local_llm "
        "trace summary names the mode (#3124)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "per_arg_scores",
        "6",
        1,
    ): (
        "population_cap",
        "first 6 in insertion order; rest unanalysed",
        "recorded in the debate material's QUALITY SCORES header (k de N) and "
        "the debate trace summary (deep-synthesis trace reader) — cap stays "
        "debt #2850",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "raw_args", "10", 1): (
        "population_cap",
        "STATELESS FALLBACK ONLY since #2850 slice A: with a merged state "
        "population the jtms premises are select_for_budget(stratified) at "
        "the same budget; this head slice survives for contexts carrying "
        "no state object",
        "fallback named — #2850 slice A",
    ),
    ("argumentation_analysis/orchestration/invoke_callables.py", "raw_args", "8", 1): (
        "population_cap",
        "STATELESS FALLBACK ONLY: with a merged state population the atms "
        "assumptions are select_for_budget(stratified) at the same budget "
        "through the coverage layer (#2896 c, record_analysis_coverage("
        "'atms')); this head slice survives for contexts carrying no state "
        "object",
        "fallback named — #2850 lot 3",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "raw_arguments",
        "6",
        1,
    ): (
        "population_cap",
        "first 6 in insertion order; rest unanalysed",
        "stateless fallback named — #2850 slice A: when a state mints units "
        "the ARGUMENTS block reads the stratified selection "
        "(record_analysis_coverage('debate') names it, the header says k de "
        "N); this [:6] head is what a stateless run reads",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "raw_claims",
        "4",
        1,
    ): (
        "population_cap",
        "first 4 claims become derived ATMS nodes with justifications; the rest is unanalysed",
        "recorded via claims_considered/claims_total on the phase payload and the atms trace summary (deep-synthesis trace reader) — cap stays debt #2850 (claims are produced facts, not the argument population)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "raw_claims",
        "6",
        1,
    ): (
        "population_cap",
        "first 6 claims become belief-network claims; the rest is unanalysed",
        "recorded via claims_in_network/claims_total on the phase payload and the jtms trace summary (deep-synthesis trace reader) — cap stays debt #2850 (claims are produced facts, not the argument population)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "raw_fallacies",
        "5",
        1,
    ): (
        "population_cap",
        "the governance deliberation context names at most 5 fallacy types; detections beyond the head stay unnamed in the deliberation input",
        "recorded via fallacy_types_considered/fallacy_types_total on the phase payload and the governance trace summary (when it fires) — cap stays debt #2850 lot 3 (the prompt itself stays byte-identical, cassette-key stability)",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "raw_fallacies",
        "5",
        2,
    ): (
        "population_cap",
        "first 5 in insertion order; rest unanalysed",
        "recorded in the debate material's FALLACIES header (k de N) and the "
        "debate trace summary (deep-synthesis trace reader) — cap stays debt "
        "#2850",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "_GOVERNANCE_DELIBERATION_WINDOW",
        1,
    ): (
        "window",
        "2000-char window from the selected offset; the fallback fires only "
        "on a run with no material at all (no arguments and no debate/counter/"
        "quality/fallacy/jtms outputs)",
        "recorded via deliberation_window_chars/deliberation_source_length on "
        "the governance payload and the governance trace summary (Lecture de "
        "repli : k de N) — the trace now also fires on a zero-conflict run, "
        "the only shape that reaches the window. Cap stays debt #2850 lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "LOGIC_ARGUMENT_WINDOW",
        1,
    ): (
        "window",
        "2000-char window of ONE unit's text, read when a batch holds a single "
        "unit (PL arm); units longer than it are truncated there",
        "recorded via pl_metrics argument_window_cap/population/over_cap and "
        "the propositional_logic trace entry (Lecture limitée) — cap stays "
        "debt #2850 lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "LOGIC_ARGUMENT_WINDOW",
        2,
    ): (
        "window",
        "2000-char window of ONE unit's text, read when a batch holds a single "
        "unit (FOL arm); units longer than it are truncated there",
        "recorded via fol_metrics argument_window_cap/population/over_cap and "
        "the fol_reasoning trace entry (Lecture limitée) — cap stays debt "
        "#2850 lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "LLM_EXTRACTION_WINDOW",
        1,
    ): (
        "window",
        "3000-char window from the selected offset — the phase that produces "
        "identified_arguments",
        "recorded via reading_window_chars/source_length on the extract "
        "payload and the extract trace summary (Lecture : k des N caractères) "
        "— cap stays debt #2850 lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "LOGIC_READING_WINDOW",
        1,
    ): (
        "window",
        "4000-char window from the selected offset, read by the PL arm's "
        "Pass 1 atom inventory",
        "recorded via pl_metrics reading_window_chars/source_total and the "
        "propositional_logic trace entry (Lecture limitée) — cap stays debt "
        "#2850 lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "LOGIC_READING_WINDOW",
        2,
    ): (
        "window",
        "4000-char window of the ORIGINAL document (_doc_text_fol, not the "
        "directive-prepended input), read by the FOL arm's Pass 1 signature",
        "recorded via fol_metrics reading_window_chars/source_total and the "
        "fol_reasoning trace entry (Lecture limitée) — cap stays debt #2850 "
        "lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "selected_text",
        "_COUNTER_ARGUMENT_FALLBACK_WINDOW",
        1,
    ): (
        "window",
        "500-char window from the selected offset; the fallback fires when no "
        "unit could be targeted (empty population and no quality scores)",
        "recorded via the counter trace summary (Lecture de repli : k de N "
        "caractères) — cap stays debt #2850 lot 4",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "target_arg",
        "30",
        1,
    ): (
        "display",
        "first 30 chars of the defeat's human-readable belief name",
        "display head — #2850: the defeat's identity travels in full via the "
        "justification endpoints (the add_justification argument lists carry "
        "the whole target_arg); the [:30] slice only shortens the name",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "sentences",
        "6",
        1,
    ): (
        "population_cap",
        "only the first 6 sentences become the assumption base (fallback when the selection is empty); rest unanalysed",
        "recorded via assumptions_from_sentences/sentences_total on the phase payload and the atms trace summary (deep-synthesis trace reader) — cap stays debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "sentences",
        "8",
        1,
    ): (
        "population_cap",
        "only the first 8 sentences become argument atoms (fallback when no arguments and no claims); rest unanalysed",
        "recorded via arguments_from_sentences/sentences_total on the phase payload and the jtms trace summary (deep-synthesis trace reader) — cap stays debt #2850",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "sentences",
        "expr",
        1,
    ): (
        "population_cap",
        "only the first min(len, 6) sentences become argument units; rest unanalysed",
        "recorded — the helper's sentences basis path (k de N), carried by "
        "the stateless arms (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/orchestration/plugins/enquete_state_manager_plugin.py",
        "text",
        "50",
        1,
    ): ("display", "first 50 chars of an already-produced string", "display only"),
    ("argumentation_analysis/orchestration/router.py", "text", "LLM_TEXT_LIMIT", 1): (
        "window",
        "the LLM routing decision reads only the first LLM_TEXT_LIMIT chars",
        "silent — debt #2850",
    ),
    ("argumentation_analysis/orchestration/service_manager.py", "text", "50", 1): (
        "display",
        "first 50 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/orchestration/service_manager.py", "text", "50", 2): (
        "display",
        "first 50 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/orchestration/service_manager.py", "text", "50", 3): (
        "display",
        "first 50 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/orchestration/structured_arg_translator.py",
        "selected_text",
        "LLM_EXTRACTION_WINDOW",
        1,
    ): (
        "window",
        "3000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    (
        "argumentation_analysis/plugins/analysis_tools/logic/rhetorical_result_analyzer.py",
        "fallacies_by_severity",
        "3",
        1,
    ): (
        "population_cap",
        "first 3 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/plugins/analysis_tools/logic/rhetorical_result_visualizer.py",
        "arg_text",
        "30",
        1,
    ): ("display", "first 30 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/coordinated_logic_plugin.py",
        "full_text",
        "4000",
        1,
    ): (
        "window",
        "first 4000 chars of the source text",
        "conversational surface — no production constructor (agents/factory "
        "registry name only, the invoke layer never builds it); stateless, "
        "payload-side basis (reader = result) — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/coordinated_logic_plugin.py",
        "selected_text",
        "LOGIC_ARGUMENT_WINDOW",
        1,
    ): (
        "window",
        "2000-char window from the selected offset",
        "conversational surface — no production constructor; stateless call "
        "(no state passed, nothing records), payload-side basis — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/coordinated_logic_plugin.py",
        "selected_text",
        "LOGIC_ARGUMENT_WINDOW",
        2,
    ): (
        "window",
        "2000-char window from the selected offset",
        "conversational surface — no production constructor; stateless call "
        "(no state passed, nothing records), payload-side basis — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/coordinated_logic_plugin.py",
        "selected_text",
        "LOGIC_READING_WINDOW",
        1,
    ): (
        "window",
        "4000-char window from the selected offset",
        "conversational surface — no production constructor; stateless call "
        "(no state passed, nothing records), payload-side basis — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/coordinated_logic_plugin.py",
        "selected_text",
        "LOGIC_READING_WINDOW",
        2,
    ): (
        "window",
        "4000-char window from the selected offset",
        "conversational surface — no production constructor; stateless call "
        "(no state passed, nothing records), payload-side basis — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "argument_text",
        "200",
        1,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "argument_text",
        "200",
        2,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "argument_text",
        "500",
        1,
    ): (
        "window",
        "first 500 chars of the argument text",
        "recorded at _explore_single_branch entry (site fallacy_descent) on "
        "the document path; per-arg instances bound a unit (≤ extract "
        "window) — payload-side, not document-scoped — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "argument_text",
        "500",
        2,
    ): (
        "window",
        "first 500 chars of the argument text",
        "recorded at _explore_single_branch entry (site fallacy_descent) on "
        "the document path; per-arg instances bound a unit (≤ extract "
        "window) — payload-side, not document-scoped — #2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "argument_text",
        "80",
        1,
    ): ("display", "first 80 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "argument_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "the wide-net Phase-1 window — first WIDE_NET_WINDOW (= 8000) chars "
        "of the source text",
        "recorded at _wide_net_candidates entry (site fallacy_widenet) on "
        "the document path; 8000 is the #1087/#2908 backstop, not lifted — "
        "#2850 lot 7",
    ),
    (
        "argumentation_analysis/plugins/fallacy_workflow_plugin.py",
        "selected_text",
        "WIDE_NET_WINDOW",
        1,
    ): (
        "window",
        "WIDE_NET_WINDOW-char window (= 8000, the constant shared with the "
        "wide-net slice above — R1058: one constant, two readers) from the "
        "selected offset — the one-shot fallback's text, bound by #2908 (was "
        "the pipeline's only unbounded reader); drops the rest of the document",
        "recorded on the document path (state threaded to the call, site "
        "fallacy_one_shot) — #2850 lot 7; per-arg instances stay stateless "
        "(unit ≤ 3000, no cut)",
    ),
    (
        "argumentation_analysis/plugins/kb_to_tweety_plugin.py",
        "belief_text",
        "200",
        1,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/kb_to_tweety_plugin.py",
        "belief_text",
        "200",
        2,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/kb_to_tweety_plugin.py",
        "belief_text",
        "200",
        3,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/plugins/kb_to_tweety_plugin.py",
        "belief_text",
        "200",
        4,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    ("argumentation_analysis/plugins/kb_to_tweety_plugin.py", "belief_text", "50", 1): (
        "display",
        "first 50 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/plugins/narrative_synthesis_plugin.py", "text", "60", 1): (
        "window",
        "argument resolution matches on a 60-char prefix only",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/reporting/document_assembler.py",
        "critical_fallacies",
        "2",
        1,
    ): (
        "population_cap",
        "first 2 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    ("argumentation_analysis/reporting/document_assembler.py", "fallacies", "3", 1): (
        "population_cap",
        "first 3 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/reporting/document_assembler.py",
        "result_text",
        "200",
        1,
    ): ("display", "first 200 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/reporting/real_time_trace_analyzer.py",
        "args_str",
        "147",
        1,
    ): (
        "population_cap",
        "first 147 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/reporting/restitution/act_reader_contract_check.py",
        "sentence",
        "117",
        1,
    ): (
        "display",
        "first 117 chars of an already-diagnosed rendered-act sentence — "
        "the finding's appendix excerpt (#1914 criteria 2-4, #2916)",
        "display only",
    ),
    (
        "argumentation_analysis/reporting/restitution/act3_conclusion_plugin.py",
        "citable_args",
        "_MAX_CLAIM_EXCERPTS",
        1,
    ): (
        "population_cap",
        "the writer's excerpt list is bounded at the _MAX_CLAIM_EXCERPTS "
        "most-cited units (winner, salience, targets — #2965); the dict fills "
        "only the budget the citations leave unused. The old `args[:cap]` "
        "second cap is GONE (#2850 lot 4): it could never bind before the "
        "budget did, so the population is now the whole dict and the selected "
        "set is byte-identical",
        "recorded via claim_excerpts_total (cited units plus the dict's, "
        "distinct) and the writer-prompt truncation notice — the #1622 idiom "
        "the counters list already uses. Cap stays debt #2850 lot 4",
    ),
    (
        "argumentation_analysis/reporting/restitution/arena_record.py",
        "text",
        "expr",
        1,
    ): (
        "display",
        "first ARENA_CAP (= 160) chars of an already-produced arena string "
        "(#3073's shared record: one metadata/extractor field, capped once "
        "so both acts quote the same extent)",
        "display only — the […] marker rides the very line both acts render",
    ),
    ("argumentation_analysis/reporting/summary_generator.py", "argument", "50", 1): (
        "display",
        "first 50 of the rendered collection",
        "display only",
    ),
    ("argumentation_analysis/reporting/trace_analyzer.py", "args_str", "147", 1): (
        "population_cap",
        "first 147 in insertion order; rest unanalysed",
        "silent — debt #2850",
    ),
    ("argumentation_analysis/run_orchestration.py", "text_content", "500", 1): (
        "window",
        "the investigation opening prompt is built from the first 500 chars",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/services/ai_shield/layers/llm_validator.py",
        "selected_text",
        "_SHIELD_VALIDATION_WINDOW",
        1,
    ): (
        "window",
        "2000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    (
        "argumentation_analysis/services/extract_service.py",
        "context_html",
        "match_start_in_context",
        1,
    ): (
        "display",
        "first match_start_in_context chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/services/extract_service.py", "chunk", "expr", 1): (
        "display",
        "marker-length head recorded for highlighting, not a content cut",
        "display only",
    ),
    ("argumentation_analysis/services/nl_to_logic.py", "arguments", "10", 1): (
        "population_cap",
        "first 10 in insertion order; rest unanalysed",
        "recorded — TranslationBatchResult.requested_population pairs the "
        "translations with what the caller sent (k de N); the cap bites only "
        "on the plugin surface — the invoke arms select ≤10 first (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/services/nl_to_logic.py",
        "selected_text",
        "_NL_TO_LOGIC_RETRY_WINDOW",
        1,
    ): (
        "window",
        "1000-char window from the selected offset",
        "named — the translation result's validation_message pairs the retry "
        "window with the argument's length, counts only (lot 6); the "
        "'record_reading_window' the census wrote for this row was "
        "inaccurate: no state reaches this service, so nothing was ever "
        "recorded — #2850",
    ),
    (
        "argumentation_analysis/services/nl_to_logic.py",
        "selected_text",
        "_NL_TO_LOGIC_WINDOW",
        1,
    ): (
        "window",
        "2000-char window from the selected offset",
        "named — the translation result's validation_message pairs the "
        "window with the argument's length, counts only (lot 6); the "
        "'record_reading_window' the census wrote for this row was "
        "inaccurate: no state reaches this service, so nothing was ever "
        "recorded — #2850",
    ),
    ("argumentation_analysis/services/nl_to_logic.py", "sentences", "3", 1): (
        "population_cap",
        "only the first 3 sentences are propositionalised; rest unanalysed",
        "recorded — the heuristic modal message carries k atomes sur N "
        "phrases (#2850 lot 5)",
    ),
    ("argumentation_analysis/services/nl_to_logic.py", "sentences", "5", 1): (
        "population_cap",
        "only the first 5 sentences are propositionalised; rest unanalysed",
        "recorded — the heuristic propositional message carries k atomes sur "
        "N phrases (#2850 lot 5)",
    ),
    ("argumentation_analysis/services/nl_to_logic.py", "sentences", "5", 2): (
        "population_cap",
        "only the first 5 sentences are propositionalised; rest unanalysed",
        "recorded — the heuristic FOL message carries k prédicats sur N "
        "phrases (#2850 lot 5)",
    ),
    ("argumentation_analysis/services/nl_to_logic.py", "text", "80", 1): (
        "window",
        "the formula variable maps to only the first 80 chars of its source",
        "recorded — the degenerate atom's message carries atome décrit par 80 "
        "de N caractères (#2850 lot 5)",
    ),
    (
        "argumentation_analysis/services/web_api/services/analysis_service.py",
        "clean_text",
        "expr",
        1,
    ): ("display", "first expr chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/services/web_api/services/analysis_service.py",
        "clean_text",
        "expr",
        2,
    ): ("display", "first expr chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/services/web_api/services/analysis_service.py",
        "sentences",
        "expr",
        1,
    ): (
        "display",
        "no drop — premise/conclusion fallback split, every sentence used",
        "display only",
    ),
    (
        "argumentation_analysis/services/web_api/services/analysis_service.py",
        "text",
        "50",
        1,
    ): ("display", "first 50 chars of an already-produced string", "display only"),
    ("argumentation_analysis/ui/app.py", "texte_analyse_prepare_local", "1500", 1): (
        "window",
        "first 1500 chars of the source text",
        "silent — debt #2850",
    ),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "extracted_text",
        "1000",
        1,
    ): ("window", "first 1000 chars of the source text", "silent — debt #2850"),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "extracted_text",
        "1000",
        2,
    ): ("window", "first 1000 chars of the source text", "silent — debt #2850"),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "extracted_text",
        "500",
        1,
    ): ("display", "first 500 chars of an already-produced string", "display only"),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "html_text",
        "position_in_visible",
        1,
    ): (
        "display",
        "first position_in_visible chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/utils/analysis_config.py",
        "selected_text",
        "_INFORMAL_ANALYSIS_WINDOW",
        1,
    ): (
        "window",
        "1000-char window from the selected offset",
        "record_reading_window; Acts silent — #2850",
    ),
    ("argumentation_analysis/utils/analysis_config.py", "text", "200", 1): (
        "display",
        "first 200 chars of an already-produced string",
        "display only",
    ),
    ("argumentation_analysis/utils/analysis_config.py", "text", "200", 2): (
        "display",
        "first 200 chars of an already-produced string",
        "display only",
    ),
    (
        "argumentation_analysis/utils/taxonomy_loader.py",
        "segments",
        "2",
        1,
    ): (
        "population_cap",
        "the middle segments of a taxonomy path deeper than three levels "
        "(root, branch and leaf are kept, the levels between are dropped)",
        "the root > branch > leaf chain fallacy_taxonomy_label prints at the "
        "three evidence sites — #2850",
    ),
    ("argumentation_analysis/utils/text_processing.py", "text", "70", 1): (
        "display",
        "first 70 chars of an already-produced string",
        "display only",
    ),
}


def test_every_site_on_the_analysis_path_is_registered():
    """The gate: census keys == registry keys, both directions.

    A site the census reads and the registry lacks is NEW UNREGISTERED
    COVERAGE DEBT — name it in ``REGISTRY`` with its contract (and #2850
    until triaged), or remove the window. A registry row without a site is
    STALE — the site moved past the census boundary or was deleted; delete
    the row, do not keep dead debt.
    """
    found = census()
    missing = sorted(set(found) - set(REGISTRY))
    stale = sorted(set(REGISTRY) - set(found))
    lines = []
    if missing:
        shown = [
            f"  {rel}:{found[(rel, base, cap, o)][1]} {base}[…:{cap}] #{o} ({found[(rel, base, cap, o)][0]})"
            for rel, base, cap, o in missing[:20]
        ]
        lines.append(
            "NEW coverage-limiting site(s) not in REGISTRY — register them "
            "with a contract (drops + render) naming #2850, or remove the "
            f"window:\n"
            + "\n".join(shown)
            + (f"\n  … and {len(missing) - 20} more" if len(missing) > 20 else "")
        )
    if stale:
        shown = [f"  {rel} {base}[…:{cap}] #{o}" for rel, base, cap, o in stale[:20]]
        lines.append(
            "STALE registry row(s) — no such site in the census (renamed "
            "base, changed cap, or deleted); delete the row:\n"
            + "\n".join(shown)
            + (f"\n  … and {len(stale) - 20} more" if len(stale) > 20 else "")
        )
    assert not lines, "\n\n".join(lines)


def test_registered_debt_names_its_issue():
    """Every window / population_cap contract names #2850 — the debt is
    registered, never silent (the whole point of the census). Display rows
    are not debt and carry no tag."""
    untagged = []
    for key, (kind, drops, render) in REGISTRY.items():
        if kind in ("window", "population_cap") and "#2850" not in (drops + render):
            untagged.append(key)
    assert (
        untagged == []
    ), f"window/population_cap row(s) whose contract never names #2850: {untagged}"


def test_the_detector_reads_the_three_classes():
    """Positive control on a synthetic module: the detector finds each class
    with its exact key material — the census is a measurement, and this
    mutation-proofs the instrument on all three classes at once."""
    snippet = (
        "from x import selected_text\n"
        "def f(input_text, args, results, sentences):\n"
        "    a = selected_text(input_text, 3000, 'site')\n"  # window
        "    b = input_text[:8000]\n"  # text_head
        "    c = list(args.items())[:10]\n"  # collection_head, unwrapped
        "    h = sentences[:6]\n"  # collection_head, extended unit token
        "    d = args[1:3]\n"  # NOT head (lower bound)
        "    e = input_text[:]\n"  # NOT a cap
        "    g = results[:4]\n"  # boundary token
        "    return a, b, c, d, e, g, h\n"
    )
    sites = _sites_in_tree(ast.parse(snippet))
    sig = {(base, cap, cls) for base, cap, _s, _l, cls in sites}
    assert ("selected_text", "3000", "window") in sig
    assert ("input_text", "8000", "text_head") in sig
    assert (
        "args",
        "10",
        "collection_head",
    ) in sig, "list(x.items())[:N] must unwrap to x"
    assert (
        "sentences",
        "6",
        "collection_head",
    ) in sig, "the sentence token must read the argument-candidate population"
    # What the census deliberately does NOT read — its stated boundary.
    assert not any(
        base == "results" for base, *_ in sites
    ), "a non-token base entered the census — update the boundary docstring"
    assert not any(cap == "3" for _b, cap, *_ in sites), "args[1:3] is not a head slice"
    assert not any(cap == "None" for _b, cap, *_ in sites), "[:] carries no cap"


def test_an_unparseable_file_fails_loud(tmp_path):
    """A census that skips what it cannot parse would silently shrink its
    population — ``_parse_module`` raises instead (#1019)."""
    bad = tmp_path / "broken_2850.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="census cannot parse"):
        _parse_module(bad, str(bad))
