"""#1702 — the export scrubber covers only what it names; this guards the relation.

``sanitize_state`` is the repository's UNIQUE declared export boundary (six
modules cite it as such, and ``scripts/dataset/run_corpus_batch.py`` calls it on
the real export path). Coverage is **ALLOWLIST-DRIVEN** — a container absent
from every table traverses intact. Seven prior issues (#741, #1265, #1271,
#1662, #1664, #1681, #1703) each closed a leak by adding the missing path du
jour, and the leak reopened at the next container added downstream, silently,
because nothing went red. This module stops the récidive: it does not name a
path, it measures the relation between what the producers WRITE and what the
scrubber COVERS, and fails when the two diverge from a frozen baseline.

Oracle side = **PRODUCER** (the real ``add_*`` entry points + the direct
assignment sites the writers use, ``state.X.append(...)`` / ``state.X[k] = ...``),
never the scrubber's own tables — those are the object under test. A unique NL
canary is planted into every natural-language slot a producer writes; the
sanitized output is walked recursively; any path where the canary survives is
an uncovered container. This is the dynamic generalisation of
``TestListShapedContainers1664.test_no_planted_claim_text_survives_anywhere``,
extended from "no canary survives" (green today on the covered set) to "the
survivors are exactly this frozen set" (green today, red tomorrow on any new
leak, and red today on the gaps the coord triages on #1702).

Why a frozen baseline and not a bare "zero survivors" assertion: the current
state has measured gaps (``formal_synthesis_reports.phase_results`` republishing
Dung extensions verbatim; the Wave-2 ``formalism_specific`` sidecars). Closing
them is a privacy decision — opacify vs drop vs export-elsewhere — that needs
"who reads this field?", a préalable not a detail (coord R785 SCOPE). This PR
does NOT patch the scrubber. The gaps are frozen here so they stay *visible*
until triaged, and posted on #1702; the guard catches any NEW gap the instant a
writer adds an uncovered NL path.

Falsifiability — two degenerate substitutions the dispatch (#1702 R785/R788)
requires:

* **Scrubber alive (internal control)** — if ``dung_frameworks[*].arguments``
  (a pass-4b-covered path) ever lets its canary through, the instrument is dead
  and a green ``survivors == EXPECTED`` proves nothing. ``test_scrubber_is_alive``
  dies first and names that path, so a dead scrubber cannot masquerade as a
  clean bill of health.
* **Substitution control (parametrised)** — remove a scrub table entry ⇒ the
  canary it killed reappears in survivors, naming the container. A guard that
  stays green under table surgery is vacuous; this one does not.

Anti-blindness — the coordinator's own measurement on this issue found that a
hand-maintained recension of NL-bearing paths was a strict *subset* of the real
surface: ``formal_synthesis_reports``, a **first-level** field, was in nobody's
list. ``test_every_written_top_level_field_is_exercised`` guards exactly that
failure mode — the canary must reach every top-level field the producers write,
enumerated once as a frozen set, so a field added to ``UnifiedAnalysisState``
without a canary fails here instead of drifting unseen.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation import sanitize_state as _sanitize_mod
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import (
    _write_atms_to_state,
    _write_fact_extraction_to_state,
    _write_jtms_to_state,
)


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch):
    """#1973: ``opaque_id`` has no default salt any more and raises without one.

    Every source this module feeds the scrubber is fabricated (see the module
    docstring), so a salt protects nothing here — it is pinned at the perimeter
    of the synthetic fixtures rather than provisioned as a CI secret. Two
    reasons, in that order: a repository secret makes the dependency invisible
    (green in CI, red on a fresh clone), and a root-scope ``autouse`` would
    disarm the #1973 fail-loud guard for the whole test environment, letting a
    future production path that forgets the salt pass green. Scoped to this
    module, the guard keeps its teeth everywhere else and
    ``test_opaque_id.py`` keeps asserting the raise.
    """
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1973")


# Two distinct canaries so pair-shaped slots (attacks, supports, extensions) can
# be exercised without a string coincidentally matching itself. Both are > 40
# chars of claim-shaped natural language — the threshold the coordinator's probe
# used, so they stand in for the real nominative payload.
CANARY = (
    "CANARY_1702 the orator insists that the proposed reform remains the sole "
    "viable course forward for the assembly"
)
CANARY2 = (
    "CANARY_1702_b a rival claim contending that the announced timetable was "
    "never realistically achievable in practice"
)


def _canaried_state() -> UnifiedAnalysisState:
    """Build a state with a canary planted in every NL slot a producer writes.

    Producer-faithful: every assignment mirrors a real ``_write_*_to_state``
    site (the ``add_*`` public API the writers call, or the direct
    ``state.X.append`` / ``state.X[k] = ...`` sites they use for the sidecars
    the ``add_*`` API does not expose). If a producer writes NL to a path, the
    canary is planted here; if the scrubber then lets it through, the path is
    uncovered. Synthetic only in that the payload is a marker string — the
    *shapes* are the real writer shapes (verified at each ``add_*`` call site
    in ``state_writers.py``), which is what the allow-list gates on.
    """
    s = UnifiedAnalysisState("initial text")
    NL, NL2 = CANARY, CANARY2

    # --- RhetoricalAnalysisState (base) NL fields -----------------------------
    # ``identified_arguments[arg_id] = description`` stores a STRING value
    # (shared_state.py:132, ``add_identified_argument`` / ``add_identified_arguments
    # (List[str])``). Pass 3 covers string values; planting a dict value here
    # would fabricate a shape no producer emits — the #1664 anti-pattern this
    # module exists to catch, not to reproduce.
    s.identified_arguments["arg_1"] = NL  # pass 3 (_TEXT_STRIP_DICTS)
    # #3235 — planted through the real ``add_fallacy`` writer. The previous
    # hand-built dict was the #3227 pattern: an oracle that does not plant
    # what the producer writes. ``problematic_quote`` stayed invisible to
    # this guard until the coordinator's probe measured 1 267 verbatim
    # argument spans surviving under it (74 states); pass 4 now drops it.
    s.add_fallacy(
        fallacy_type="ad_hominem",
        justification=NL,
        target_arg_id="arg_1",
        family="relevance",
        problematic_quote=NL2,
    )
    # ``add_argument`` (shared_state.py:311) is the sole producer of
    # ``argument_provenance`` — the entry carries closed-vocab ``producer`` /
    # ``offset_basis``, int ``offset``, and the VERBATIM ``source_quote``
    # (#2850's carrier, #3162's read). #3217: that quote survived sanitize
    # byte-identical (360/360 on the stored states) while the argument text
    # beside it was stripped. Planted through the real ``add_*`` call the
    # writer makes (state_writers.py:1623), not a hand-built dict.
    s.add_argument(NL, producer="llm_extract", source_quote=NL2)
    s.add_belief_set("Propositional Logic", NL)  # pass 4 (.content)
    s.argument_quality_scores["arg_1"] = {  # pass 4 (.llm_assessment)
        "overall": 0.5,
        "llm_assessment": NL,
    }

    # --- UnifiedAnalysisState NL fields ---------------------------------------
    # #3228 — the display-label maps (``{arg_N: label}``) ride on the seven AF
    # containers; the label IS the argument text (measured: every stored label
    # equals an ``identified_arguments`` value). Planted through the real
    # ``argument_labels`` kwarg the writers pass, on every container that has
    # one — the canary must reach this key or a leak here stays invisible
    # (which is exactly how #3228 happened: the first PR covered four writers
    # while ``shared_state`` has seven; the coordinator's replay of the stored
    # states surfaced the three the issue under-counted).
    labels: dict[str, str] = {"arg_1": NL, "arg_2": NL2}
    s.add_counter_argument(NL, NL2, "distinction", 0.6)  # pass 5
    s.add_ranking_result(  # pass 5b (.arguments) + 5g (.argument_labels)
        "burden",
        [NL],
        [{"rank": 1}],
        argument_labels=labels,
    )
    s.add_aspic_result(  # passes 5b (.extensions) + 5d (.attacks) + 5g
        "simple",
        [[NL], [NL, NL2]],
        {"n": 2},
        attacks=[
            {
                "target": NL,
                "attacker_premises": [NL2],
                "scope": "undercut",
                "attacker_rule": "def_con_1",
            }
        ],
        argument_labels=labels,
    )
    s.add_belief_revision_result(  # passes 5b + 5e (.options) + 5g
        "dalal",
        [NL],
        [NL2],
        minimal_retraction={
            "cardinality": 1,
            "options": [[NL]],
            "base_size": 2,
            "touched_count": 1,
        },
        argument_labels=labels,
    )
    s.add_dialogue_result(  # pass 5b (.topic) + 5d (.trace) + 5g (.labels)
        NL,
        "accepted",
        [
            {
                "round": 1,
                "speaker": "opponent",
                "action": "attack",
                "argument": NL2,
                "target": NL,
            }
        ],
        argument_labels=labels,  # pass 5g (#3228 rework: 5th of 7 writers)
    )
    # pass 5b + 5c (keys) + 5g (.labels) — #3228 rework: 6th of 7 writers.
    s.add_probabilistic_result([NL], {NL: 0.75}, argument_labels=labels)
    # pass 5b + 5g (.labels) — #3228 rework: 7th of 7 writers.
    s.add_bipolar_result("necessity", [NL], [[NL, NL2]], argument_labels=labels)
    s.add_debate_transcript(  # pass 5 (.topic) + 5d (.exchanges point/rebuttal)
        # #2135: the producer oracle plants what the REAL writer stores —
        # point/rebuttal (+ closed-vocab scheme fields). The old
        # proponent_move/opponent_move names were fabricated by no writer, so
        # planting them let the 5d entry agree with itself while covering
        # nothing a producer emits.
        NL,
        [
            {
                "point": NL,
                "rebuttal": NL2,
                "scheme": "Opinion d'expert",
                "scheme_key": "expert_opinion",
            }
        ],
        "proponent",
    )
    s.transcription_segments.append({"text": NL, "speaker": NL2})  # pass 5
    s.neural_fallacy_scores.append({"text_segment": NL})  # pass 5
    s.analysis_trace.append({"summary": NL})  # pass 5
    s.nl_to_logic_translations.append(  # pass 5 (.original_text) + 6 (.variables)
        {"original_text": NL, "variables": {"p": NL2}}
    )
    s.semantic_index_refs.append({"query": NL, "snippet": NL2})  # pass 5
    # #3242 — extracts, through the real ``_write_fact_extraction_to_state``
    # writer (state_writers.py:1592): it appends ``{"type", "content",
    # "source_quote"}`` straight onto ``state.extracts``, bypassing
    # ``add_extract`` — a hand plant without the quote key was blind to the
    # leaf, which is exactly how 427 verbatim source spans survived on the
    # stored states. A bare-string claim rides along to keep the no-quote
    # shape exercised.
    _write_fact_extraction_to_state(
        {"claims": [{"text": NL, "source_quote": NL2}, NL2], "arguments": []},
        s,
        {},
    )
    s.source_metadata = {"title": NL, "genre": "speech"}  # pass 2b (dict values)
    s.narrative_synthesis = NL  # pass 7
    s.act1_framing = NL  # pass 7
    s.act2_narrative = NL  # pass 7
    s.act3_conclusion = NL  # pass 7
    s.final_conclusion = NL  # pass 7
    s.stakes_and_stakeholders = {  # pass 8 (.stakes/.stakeholders → counts)
        "stakes": [NL],
        "stakeholders": [NL2],
        "rhetorical_register": "deliberative",
        "discursive_arena": "assembly",
    }

    # --- dung_frameworks: covered paths (4b/4c) + the GAP sidecar -------------
    # The real ``extensions`` shape is heterogeneous (``extensions`` = list of
    # lists = the Dung sets; ``all_members`` = flat list), so the value type is
    # ``Any`` — the ``add_dung_framework`` signature narrows it to
    # ``Dict[str, List[str]]``, which the producer itself does not satisfy.
    dung_extensions: dict[str, Any] = {  # pass 4c (.extensions / .all_members)
        "extensions": [[NL, NL2]],
        "all_members": [NL],
        # ``count`` (int) and ``sizes`` (List[int]) are structural aggregates
        # the real producer writes here too — they carry no NL, so they are
        # irrelevant to the canary scan and omitted here.
    }
    df_id = s.add_dung_framework(
        "dung_arbitration",
        [NL],  # pass 4b (.arguments)
        [[NL, NL2]],  # pass 4b (.attacks)
        extensions=dung_extensions,
        argument_labels=labels,  # pass 5g (#3228)
    )
    # #1648 Wave-2 sidecar — attached by direct assignment exactly as the
    # ``_write_setaf/weighted/eaf/delp`` writers do. NOT in any scrubber table.
    s.dung_frameworks[df_id]["formalism_specific"] = {
        "set_attacks": [{"attackers": [NL], "target": NL2}],
        "attack_weights": [{"source": NL, "target": NL2, "weight": 0.5}],
        "epistemic_beliefs": {"agent_1": [NL]},
        "contraries": {NL: NL2},
        "delp_arguments": [NL],
    }

    # --- formal_synthesis_reports: .summary covered (pass 5), .phase_results GAP
    # The phase_results dict republishes each formal phase's output verbatim
    # (coord R785 measure: 1024–2304 occurrences of the Dung extensions text
    # here, per corpus). The scrubber names only ``.summary`` for this field.
    s.add_formal_synthesis_report(
        summary=NL,
        phase_results={
            "dung_extensions": {
                "all_extensions": {
                    "conflict_free": {"extensions": [[NL, NL2]]},
                    "admissible": {"extensions": [[NL, NL2], [NL]]},
                }
            },
            "fol": {"message": NL},
        },
        overall_validity=0.5,
    )

    # --- formal-logic axes: .message is the NL slot (formulas are symbolic) ----
    s.add_fol_analysis_result(["p ∧ q"], True, ["q"], 0.9, message=NL)
    s.add_propositional_analysis_result(["p ∧ q"], True, {"p": True}, message=NL)
    s.add_modal_analysis_result(["□p"], True, ["belief"], message=NL)

    # --- jtms_beliefs: belief name can be argument text; justifications free-form
    # #3235 — the real ``_write_jtms_to_state`` shape: the JTMS phase
    # serialises justifications as dicts (``{"in_list": [name[:40]...],
    # "out_list": [...]}``, invoke_callables.py); the bare-string shape
    # survives only in the ATMS writer's beliefs (planted below). The old
    # bare-string-only plant exercised a shape the JTMS producer no longer
    # emits — the #1664 anti-pattern — so the dict leaves stayed invisible.
    s.add_jtms_belief(NL, True, justifications=[{"in_list": [NL2], "out_list": [NL]}])

    # #3242 — the retraction cascade trace, through the real
    # ``_write_jtms_to_state`` writer (state_writers.py:722 stores the chain
    # the JTMS session produced, invoke_callables.py:3618).
    # ``trigger``/``retracted``/``cascaded`` carry belief names (jtms_core.py
    # :236/:422 — measured on the stored states: 412/412 cascaded items equal
    # a raw ``jtms_beliefs`` name); ``reason`` is the producer's closed
    # formula (``f"directly set to {validity}"``, jtms_core.py:240) and
    # carries a real literal — planting NL there would freeze a gap no
    # producer can write (#1664, the atms-label precedent above).
    _write_jtms_to_state(
        {
            "beliefs": {},
            "retraction_chain": [
                {
                    "trigger": NL,
                    "retracted": [NL],
                    "cascaded": [NL, NL2],
                    "reason": "directly set to False",
                }
            ],
        },
        s,
        {},
    )

    # #3242 — ``fol_shared_signature``, the FOL pass-1 writer's exact product
    # (invoke_callables.py:10412 assigns ``{sorts, predicates, constants_raw,
    # fol_solver}`` inline in the async LLM path — no ``add_*`` API exists, so
    # the plant mirrors the assigned shape). ``constants_raw`` carries the
    # canary as KEY and as value (both halves nominative — 1 588 keys /
    # 1 208 NL values on the coordinator's 79 states, personal names among
    # the keys); ``sorts`` members are the same identifiers under closed sort
    # names (the pass-1 prompt: 'If unsure about sort, use "Thing"').
    # ``predicates`` (sort-typed signature) and ``fol_solver`` (a solver id)
    # carry no canary: not this issue's surface, no scrub on suspicion
    # (#1664).
    s.fol_shared_signature["src_1"] = {
        "sorts": {"Person": [NL], "Thing": [NL, NL2]},
        "predicates": {"advocate": ["Person", "Thing"]},
        "constants_raw": {NL: NL2, NL2: NL},
        "fol_solver": "tweety",
    }

    # atms_contexts + the ATMS-written jtms beliefs, planted through the real
    # ``_write_atms_to_state`` (which does ``state.atms_contexts =
    # output.get("atms_contexts", [])``). The producer (``_invoke_atms``)
    # builds each context as ``{hypothesis_id, label, assumptions, coherent,
    # derivable_beliefs, contradicting_beliefs, derivation_count,
    # contradiction_count}`` — there is NO ``hypotheses`` key. The three
    # atom lists are source-derived (via ``_generate_hypotheses``) and carry
    # the canary; ``label`` is a CLOSED vocabulary at that producer (six
    # literals; 4 distinct values measured on the stored states, 0
    # argument-text matches), so the plant carries a real literal — the
    # ``dung_frameworks.name`` verdict, planting NL there would freeze a
    # "gap" no producer can write. The ``environments`` entry below makes
    # the same writer plant the bare-string justification shape
    # (``assumption_env:['CANARY…']``) into jtms_beliefs.
    _write_atms_to_state(
        {
            "environments": {
                "node_a": {"is_assumption": True, "environments": [[NL]]},
            },
            "atms_contexts": [
                {
                    "hypothesis_id": "ctx_1",
                    "label": "Skeptical: single argument only",
                    "assumptions": [NL, NL2],
                    "coherent": True,
                    "derivable_beliefs": [NL],
                    "contradicting_beliefs": [NL2],
                    "derivation_count": 1,
                    "contradiction_count": 1,
                }
            ],
        },
        s,
        {},
    )

    # governance_decisions: structural (method/winner/scores). Exercised so the
    # field is in the written-set, but no NL canary — producer values are short
    # entity labels, not claim text.
    s.add_governance_decision("borda", "option_a", {"option_a": 0.6})

    return s


# Every top-level state field the producers write (the anti-blindness set — see
# ``test_every_written_top_level_field_is_exercised``). A field added to
# ``UnifiedAnalysisState`` that a producer fills MUST be added here too, or this
# test fails: that is precisely the failure mode the coordinator's own
# recension hit on this issue (``formal_synthesis_reports`` was in nobody's
# list). ``raw_text`` and friends are intentionally absent — they are stripped
# top-level by pass 1 and never carry a canary by design.
WRITTEN_TOP_LEVEL_FIELDS = frozenset(
    {
        "identified_arguments",
        "argument_provenance",
        "identified_fallacies",
        "belief_sets",
        "argument_quality_scores",
        "counter_arguments",
        "ranking_results",
        "aspic_results",
        "belief_revision_results",
        "dialogue_results",
        "probabilistic_results",
        "bipolar_results",
        "debate_transcripts",
        "transcription_segments",
        "neural_fallacy_scores",
        "analysis_trace",
        "nl_to_logic_translations",
        "semantic_index_refs",
        "extracts",
        "source_metadata",
        "narrative_synthesis",
        "act1_framing",
        "act2_narrative",
        "act3_conclusion",
        "final_conclusion",
        "stakes_and_stakeholders",
        "dung_frameworks",
        # #3242 — populated by the real ``_write_fact_extraction_to_state``
        # writer's ``record_anchor_census()`` (#2973): counts, per-producer
        # tallies and ``arg_N`` ids — structural, the governance_decisions
        # verdict (declared and exercised, no NL canary: planting NL here
        # would fabricate a shape no producer writes, #1664).
        "analysis_coverage",
        "formal_synthesis_reports",
        "fol_analysis_results",
        "fol_shared_signature",
        "propositional_analysis_results",
        "modal_analysis_results",
        "jtms_beliefs",
        "jtms_retraction_chain",
        "atms_contexts",
        "governance_decisions",
    }
)


_RUNTIME_ID_SUFFIX = re.compile(r"_[0-9]+$")


def _is_runtime_key(seg: str) -> bool:
    """True for generated ids / entity labels / NL keys — collapse to ``[*]``.

    Structural field names (``arguments``, ``formalism_specific``, ``message``)
    are KEPT so sibling sub-paths stay distinguishable in the fingerprint.
    ``_generate_id`` produces ids like ``dung_1`` / ``jtms_1`` / ``fsyn_1``
    (``prefix + "_" + N``); entity-label dict keys and any NL/canary key also
    collapse — none are stable across runs, and keeping them would make the
    baseline brittle. List indices are non-str and handled by the caller.
    """
    if _RUNTIME_ID_SUFFIX.search(seg):
        return True
    if CANARY in seg or " " in seg or len(seg) > 50:
        return True
    return False


def _normalize_path(path: tuple[Any, ...]) -> str:
    """Render a recursive-descent path with indices/ids collapsed to ``[*]``.

    A canary planted under ``dung_frameworks["dung_1"]`` survives under a
    runtime-generated id; the frozen baseline must not depend on that id, so
    generated-id / NL dict keys and every list index collapse to ``[*]`` while
    structural field names survive. The resulting set is a stable structural
    fingerprint, not an address.
    """
    parts: list[str] = []
    for seg in path:
        if isinstance(seg, int):
            parts.append("[*]")
        elif isinstance(seg, str):
            parts.append("[*]" if _is_runtime_key(seg) else seg)
        else:
            parts.append("[*]")
    out = ""
    for i, seg in enumerate(parts):
        if seg == "[*]":
            out += "[*]"
        elif i == 0:
            out = seg
        else:
            out += f".{seg}"
    return out


def _surviving_paths(sanitized: dict[str, Any]) -> dict[str, set[str]]:
    """Walk ``sanitized``; collect normalized paths where a canary survives.

    Returns ``{top_level_field: {normalized_path, ...}}``. The top-level field
    is the first path segment (the root key) — that is the granularity at which
    the allow-list blindness mode operates (a whole first-level field unseen,
    as ``formal_synthesis_reports`` was). Sub-path detail is preserved inside
    each set so a NEW uncovered sub-path under an already-gapped field is still
    caught (the set grows ⇒ baseline mismatch).
    """

    def walk(node: Any, path: tuple[Any, ...], acc: dict[str, set[str]]) -> None:
        top = path[0] if path else None
        if isinstance(node, str):
            if CANARY in node or CANARY2 in node:
                field = str(top) if top is not None else "<root>"
                acc.setdefault(field, set()).add(_normalize_path(path))
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + (k,), acc)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + (i,), acc)

    acc: dict[str, set[str]] = {}
    walk(sanitized, (), acc)
    return acc


# The frozen gap baseline (green on main; red the moment a NEW uncovered path
# appears, or the moment a gapped path gets covered without updating this set).
# Each entry is a top-level field whose canary survives sanitize_state today,
# with the normalized sub-paths. The fate of each (opacify / drop / export-
# elsewhere) is a privacy decision pending triage on #1702 — see the module
# docstring for why this PR does not patch the scrubber.
EXPECTED_UNCOVERED: dict[str, frozenset[str]] = {
    # The Wave-2 ``formalism_specific`` sidecar on ``dung_frameworks`` was a
    # frozen gap at #1711; #1702 covered it via pass 4d
    # (``_scrub_formalism_specific`` — see sanitize_state.py). Its seven
    # nominative paths are now opacified, so ``dung_frameworks`` no longer
    # appears in the uncovered set. The canary plan still plants them (so a
    # regression in 4d re-leaks here immediately), and ``test_scrubber_is_alive``
    # keeps watching the sibling 4b ``.arguments`` path.
    #
    # ``formal_synthesis_reports`` no longer appears here: #3229 settled the
    # deferred triage — no script reads ``phase_results`` from a sanitized
    # export, so pass 5 drops it. The canary plant above stays (a regression
    # in pass 5 re-leaks here immediately).
    #
    # Formal-logic status messages can carry NL (``"unavailable: <reason>"``).
    # Not in any scrubber table. #3235 settled the sibling gaps; these stay
    # frozen under their own OPEN owner: #3239 (0/0/2 argument-text matches
    # measured — a producer census must decide drop vs closed-vocabulary).
    "fol_analysis_results": frozenset({"fol_analysis_results[*].message"}),
    "propositional_analysis_results": frozenset(
        {"propositional_analysis_results[*].message"}
    ),
    "modal_analysis_results": frozenset({"modal_analysis_results[*].message"}),
    # ``jtms_beliefs`` and ``atms_contexts`` no longer appear here: #3235
    # settled both frozen gaps. jtms — the belief name (``{unit_id}:{text}``)
    # and both justification shapes (dict ``in_list``/``out_list`` leaves and
    # the ATMS ``assumption_env:[…]`` strings) are opacified (passes 4b/5d):
    # the name↔in_list linkage is a measured join (122 exact overlaps), so
    # opacify, not drop. atms — ``assumptions`` is opacified (the one export
    # reader counts it, pattern_mining.AtmsBranchingDetector),
    # ``derivable_beliefs``/``contradicting_beliefs`` are dropped (no reader;
    # ``derivation_count``/``contradiction_count`` ints carry the signal) and
    # ``label`` is a closed vocabulary at the producer (six literals) that
    # survives untouched — the ``dung_frameworks.name`` verdict, so the canary
    # plants a real literal. The plants above stay exactly as they were: a
    # regression in any of those passes re-leaks here immediately.
}


class TestScrubberCoverageGuard:
    """#1702 — the allow-list scrubber, guarded by a producer-side oracle."""

    def test_scrubber_is_alive_internal_control(self) -> None:
        """If a pass-4b-covered path leaks, the instrument is dead — fail first.

        ``dung_frameworks[*].arguments`` is opacified by pass 4b. If its canary
        ever survives, ``sanitize_state`` is no longer doing its work, and every
        other assertion in this class (which presupposes a working scrubber) is
        moot. The check is scoped to the ``.arguments`` list of each framework
        entry — the ``formalism_specific`` sidecar is a *known gap* that
        legitimately leaks its own canary under the same top-level field, so the
        whole-field blob would always be dirty and could not discriminate a dead
        scrubber from a live one with a documented gap.
        """
        out = sanitize_state(_canaried_state().get_state_snapshot())
        for entry in out["dung_frameworks"].values():
            for arg in entry.get("arguments", []):
                assert CANARY not in str(arg) and CANARY2 not in str(arg), (
                    "dung_frameworks[*].arguments canary survived — the scrubber "
                    "is dead; the coverage baseline below is meaningless until "
                    "pass 4b is fixed."
                )

    def test_uncovered_paths_match_frozen_baseline(self) -> None:
        """The canary survivors are exactly EXPECTED_UNCOVERED — both directions.

        Red when a NEW uncovered path appears (a writer added an NL sub-path no
        table covers) AND when a frozen gap gets covered without updating the
        set (so the baseline cannot drift stale-green). The diff is printed as
        ``{+new_leaks, -newly_covered}`` so the failure names the container.
        """
        survivors = _surviving_paths(
            sanitize_state(_canaried_state().get_state_snapshot())
        )
        survivor_norm = {f: frozenset(paths) for f, paths in survivors.items() if paths}
        expected = dict(EXPECTED_UNCOVERED)
        new_leaks = {
            f: sorted(survivor_norm.get(f, set()) - expected.get(f, set()))
            for f in set(survivor_norm) | set(expected)
        }
        new_leaks = {f: p for f, p in new_leaks.items() if p}
        newly_covered = {
            f: sorted(expected.get(f, set()) - survivor_norm.get(f, set()))
            for f in set(survivor_norm) | set(expected)
        }
        newly_covered = {f: p for f, p in newly_covered.items() if p}
        assert not new_leaks and not newly_covered, (
            "scrubber coverage diverged from the frozen #1702 baseline.\n"
            f"  new leaks (uncovered NL paths — triage on #1702): {new_leaks}\n"
            f"  newly covered (update EXPECTED_UNCOVERED): {newly_covered}"
        )

    def test_formal_synthesis_reports_gap_is_attested(self) -> None:
        """DoD item 2 — formal_synthesis_reports reaches the coverage oracle.

        The first-level field the coordinator's own recension missed. #3229
        settled the deferred triage (no export reader of ``phase_results``):
        pass 5 drops it. This test pinned the gap while it was open; it now
        pins its closure — the canary plant above stays, so a pass-5
        regression re-leaks here immediately.
        """
        out = sanitize_state(_canaried_state().get_state_snapshot())
        # Covered half: pass 5 strips the ``summary`` KEY entirely
        # (``_strip_text_from_dict`` drops it), so it is absent — not merely
        # opacified. Asserting on its value would KeyError.
        assert "summary" not in out["formal_synthesis_reports"][0]
        # Closed half (#3229): .phase_results is dropped with it — no canary
        # survives under the field, and the frozen set no longer names it.
        assert CANARY not in repr(out["formal_synthesis_reports"])
        assert "phase_results" not in out["formal_synthesis_reports"][0]
        assert "formal_synthesis_reports" not in EXPECTED_UNCOVERED

    def test_every_written_top_level_field_is_exercised(self) -> None:
        """Anti-blindness — the canary reaches every producer-written field.

        The coordinator's measurement on this issue found a hand recension of
        NL paths was a strict subset of the real surface
        (``formal_synthesis_reports`` was in nobody's list). This guards that
        failure mode: every field a producer writes must (a) appear in the
        canaried snapshot and (b) be declared in WRITTEN_TOP_LEVEL_FIELDS. A
        field added to ``UnifiedAnalysisState`` without both fails here.
        """
        snap = _canaried_state().get_state_snapshot()
        written_now = {k for k, v in snap.items() if v not in (None, "", [], {})}
        # Every declared field must actually be populated by the canary plan.
        missing_from_snapshot = WRITTEN_TOP_LEVEL_FIELDS - written_now
        assert not missing_from_snapshot, (
            "these declared fields are not populated by _canaried_state — the "
            f"canary never reaches them: {sorted(missing_from_snapshot)}"
        )
        # Every populated producer field must be declared (anti-drift).
        undeclared = written_now - WRITTEN_TOP_LEVEL_FIELDS
        # Tolerate only the pass-1 top-level strips, the structural
        # bookkeeping the scrubber removes or never fills, and — #3242 — the
        # containers the census measured (issue comment 6399207162, 49 stored
        # states). ``fol_shared_signature`` and ``jtms_retraction_chain`` LEFT
        # this set: both are now canaried through their real writers above
        # and scrubbed (passes 5h / 5b). Every remaining entry carries its
        # measurement beside it; the five NL-bearing ones are owned by the
        # follow-up #3249 (reader census + decision per leaf — no scrub on
        # suspicion, #1664).
        tolerated = {
            "raw_text",
            "raw_text_snippet",
            "full_text",
            "full_text_segment",
            "id",
            "task_count",
            "deanonymized",
            "source_id",
            # producer NL measured on the stored states (#3242 census),
            # each awaiting its #3249 census:
            "structured_arg_status",  # 48 states, 288 NL ≥ 30
            "atomic_propositions",  # 48 states, 734 NL — atoms named after the text
            "fol_signature",  # 48 states, 197 NL — members carry entity names
            "restitution_acts_degraded",  # 41 states, 51 NL (degraded notes)
            "workflow_results",  # 49 states, 47 NL — free-form values
            # unexercised on this corpus (0 of 49 states carry them, #3242
            # census; #3131's crossing measured the same for
            # local_llm_results' ``response``):
            "ai_shield_results",
            "local_llm_results",
            "deliberation_trace",
        }
        undeclared = undeclared - tolerated
        assert not undeclared, (
            "these populated state fields are not in WRITTEN_TOP_LEVEL_FIELDS — "
            f"add them (and a canary) or document why they carry no NL: "
            f"{sorted(undeclared)}"
        )


class TestSubstitutionControl:
    """DoD item 4 — remove a scrub rule ⇒ the canary it killed reappears.

    A coverage guard that stays green when the scrubber is surgically weakened
    is vacuous. Each test temporarily deletes one table entry and asserts the
    canary that entry was opacifying now survives, NAMING the container. The
    guard is restored via monkeypatch after the assertion.
    """

    @pytest.mark.parametrize(
        "table_attr,remove_field,survivor_field,expected_path_fragment",
        [
            # Pass 4 (#3217): argument_provenance.source_quote — the verbatim
            # corpus quote the producer extracted. Removing the entry re-leaks
            # it under the provenance container; the structural keys
            # (producer/offset/offset_basis) stay covered by nothing else,
            # which is deliberate — they are closed vocabulary.
            (
                "_TEXT_STRIP_DICT_OF_DICTS",
                "argument_provenance",
                "argument_provenance",
                ".source_quote",
            ),
            # Pass 5g (#3228): the display-label maps on the seven AF
            # containers — {arg_N: label}, the label being the argument text
            # itself. Removing one container's entry re-leaks its canary
            # under .argument_labels; the other six stay covered.
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "dung_frameworks",
                "dung_frameworks",
                ".argument_labels",
            ),
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "ranking_results",
                "ranking_results",
                ".argument_labels",
            ),
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "aspic_results",
                "aspic_results",
                ".argument_labels",
            ),
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "belief_revision_results",
                "belief_revision_results",
                ".argument_labels",
            ),
            # #3228 rework (coordinator review of b92f8b193): the three
            # list-appended writers the issue under-counted.
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "dialogue_results",
                "dialogue_results",
                ".argument_labels",
            ),
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "probabilistic_results",
                "probabilistic_results",
                ".argument_labels",
            ),
            (
                "_OPAQUE_LABEL_MAP_SUBKEYS",
                "bipolar_results",
                "bipolar_results",
                ".argument_labels",
            ),
            # Pass 4b: dung_frameworks.arguments/attacks.
            (
                "_OPAQUE_LIST_SUBKEYS",
                "dung_frameworks",
                "dung_frameworks",
                ".arguments",
            ),
            # Pass 5b: aspic_results.extensions.
            (
                "_OPAQUE_LIST_OF_DICTS_SUBKEYS",
                "aspic_results",
                "aspic_results",
                ".extensions",
            ),
            # Pass 5b: belief_revision_results.original/revised.
            (
                "_OPAQUE_LIST_OF_DICTS_SUBKEYS",
                "belief_revision_results",
                "belief_revision_results",
                ".original",
            ),
            # Pass 5d: aspic_results.attacks target/attacker_premises.
            (
                "_OPAQUE_NESTED_ITEM_SUBKEYS",
                "aspic_results",
                "aspic_results",
                ".attacks",
            ),
            # Pass 4 (#3235): identified_fallacies.problematic_quote — the
            # verbatim argument span the real add_fallacy writer stores.
            # Removing the entry re-leaks it (and .justification) under the
            # fallacy container.
            (
                "_TEXT_STRIP_DICT_OF_DICTS",
                "identified_fallacies",
                "identified_fallacies",
                ".problematic_quote",
            ),
            # Pass 4b (#3235): jtms_beliefs name + bare-string justifications.
            (
                "_OPAQUE_LIST_SUBKEYS",
                "jtms_beliefs",
                "jtms_beliefs",
                ".name",
            ),
            # Pass 5 (#3235): the two ATMS belief lists no export reader names.
            (
                "_TEXT_STRIP_LISTS",
                "atms_contexts",
                "atms_contexts",
                ".derivable_beliefs",
            ),
            # Pass 5b (#3235): atms assumptions — the reader counts them.
            (
                "_OPAQUE_LIST_OF_DICTS_SUBKEYS",
                "atms_contexts",
                "atms_contexts",
                ".assumptions",
            ),
            # Pass 5d (#3235): jtms dict justifications' in_list/out_list.
            (
                "_OPAQUE_NESTED_ITEM_SUBKEYS",
                "jtms_beliefs",
                "jtms_beliefs",
                ".justifications",
            ),
            # Pass 4d (#1702): formalism_specific leaves. Removing a leaf from
            # the spec re-leaks its canary under the dung_frameworks top-level
            # field — the new pass is not vacuous. The table key (``set_attacks``)
            # differs from the survivor field (``dung_frameworks``) because the
            # sidecar is nested inside a dung_frameworks entry, not a top-level.
            (
                "_OPAQUE_FORMALISM_SPECIFIC",
                "set_attacks",
                "dung_frameworks",
                ".formalism_specific.set_attacks",
            ),
            (
                "_OPAQUE_FORMALISM_SPECIFIC",
                "contraries",
                "dung_frameworks",
                ".formalism_specific.contraries",
            ),
            (
                "_OPAQUE_FORMALISM_SPECIFIC",
                "attack_weights",
                "dung_frameworks",
                ".formalism_specific.attack_weights",
            ),
            # Pass 5 (#3242): extracts.source_quote — the verbatim source
            # span the real fact-extraction writer attaches to each claim.
            (
                "_TEXT_STRIP_LISTS",
                "extracts",
                "extracts",
                ".source_quote",
            ),
            # Pass 5h (#3242): the FOL signature atom maps — constants_raw
            # keys+values, sorts members (the same table, one entry).
            (
                "_OPAQUE_ATOM_MAP_SUBKEYS",
                "fol_shared_signature",
                "fol_shared_signature",
                ".constants_raw",
            ),
            # Pass 5b (#3242): the retraction-chain belief-name leaves.
            (
                "_OPAQUE_LIST_OF_DICTS_SUBKEYS",
                "jtms_retraction_chain",
                "jtms_retraction_chain",
                ".cascaded",
            ),
        ],
    )
    def test_removing_a_rule_lets_the_canary_through(
        self,
        monkeypatch: pytest.MonkeyPatch,
        table_attr: str,
        remove_field: str,
        survivor_field: str,
        expected_path_fragment: str,
    ) -> None:
        original_table = getattr(_sanitize_mod, table_attr)
        # Surgical copy minus the one field — the rest of the table stays armed.
        reduced = {k: v for k, v in original_table.items() if k != remove_field}
        monkeypatch.setattr(_sanitize_mod, table_attr, reduced)

        survivors = _surviving_paths(
            sanitize_state(_canaried_state().get_state_snapshot())
        )
        field_paths = survivors.get(survivor_field, set())
        # The canary that the removed rule was killing must now survive, and at
        # least one surviving path must carry the expected sub-path fragment.
        assert field_paths, (
            f"removing {table_attr}[{remove_field!r}] did NOT let the canary "
            "through — the substitution control is vacuous (some other pass "
            "also covers it, or the canary never reached it)."
        )
        assert any(
            expected_path_fragment in p for p in field_paths
        ), f"expected a surviving path under {expected_path_fragment!r}, got {sorted(field_paths)}"


def gap_report() -> dict[str, list[str]]:
    """Produce the ``{field: [paths]}`` gap list to post on #1702.

    Not a test — a helper invoked once to capture the frozen baseline verbatim
    (paths only, never content — privacy HARD). Run via:
    ``python -c "from <thismodule> import gap_report; print(gap_report())"``
    """
    return {f: sorted(paths) for f, paths in EXPECTED_UNCOVERED.items()}
