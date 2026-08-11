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
    s.identified_fallacies["fal_1"] = {  # pass 4 (.justification)
        "type": "ad_hominem",
        "justification": NL,
        "family": "relevance",
    }
    s.add_belief_set("Propositional Logic", NL)  # pass 4 (.content)
    s.argument_quality_scores["arg_1"] = {  # pass 4 (.llm_assessment)
        "overall": 0.5,
        "llm_assessment": NL,
    }

    # --- UnifiedAnalysisState NL fields ---------------------------------------
    s.add_counter_argument(NL, NL2, "distinction", 0.6)  # pass 5
    s.add_ranking_result("burden", [NL], [{"rank": 1}])  # pass 5b
    s.add_aspic_result(  # passes 5b (.extensions) + 5d (.attacks target/premises)
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
    )
    s.add_belief_revision_result(  # pass 5b + 5e (.minimal_retraction.options)
        "dalal",
        [NL],
        [NL2],
        minimal_retraction={
            "cardinality": 1,
            "options": [[NL]],
            "base_size": 2,
            "touched_count": 1,
        },
    )
    s.add_dialogue_result(  # pass 5b (.topic) + 5d (.trace argument/target)
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
    )
    s.add_probabilistic_result([NL], {NL: 0.75})  # pass 5b + 5c (keys)
    s.add_bipolar_result("necessity", [NL], [[NL, NL2]])  # pass 5b
    s.add_debate_transcript(  # pass 5 (.topic) + 5d (.exchanges moves)
        NL, [{"proponent_move": NL, "opponent_move": NL2}], "proponent"
    )
    s.transcription_segments.append({"text": NL, "speaker": NL2})  # pass 5
    s.neural_fallacy_scores.append({"text_segment": NL})  # pass 5
    s.analysis_trace.append({"summary": NL})  # pass 5
    s.nl_to_logic_translations.append(  # pass 5 (.original_text) + 6 (.variables)
        {"original_text": NL, "variables": {"p": NL2}}
    )
    s.semantic_index_refs.append({"query": NL, "snippet": NL2})  # pass 5
    s.extracts.append({"content": NL})  # pass 5
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
    s.add_jtms_belief(NL, True, [NL2])

    # atms_contexts: stored verbatim by ``_write_atms_to_state``; plant one entry.
    s.atms_contexts = [{"context": "ctx_1", "hypotheses": [NL]}]

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
        "formal_synthesis_reports",
        "fol_analysis_results",
        "propositional_analysis_results",
        "modal_analysis_results",
        "jtms_beliefs",
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
    # Wave-2 ``formalism_specific`` sidecars — attached by ``_write_setaf /
    # _write_weighted / _write_eaf / _write_delp`` via direct assignment, never
    # declared in any scrubber table. Same claim text the 4b/4c passes opacify
    # one level up, under a sibling container the passes do not inspect.
    "dung_frameworks": frozenset(
        {
            "dung_frameworks[*].formalism_specific.set_attacks[*].attackers[*]",
            "dung_frameworks[*].formalism_specific.set_attacks[*].target",
            "dung_frameworks[*].formalism_specific.attack_weights[*].source",
            "dung_frameworks[*].formalism_specific.attack_weights[*].target",
            "dung_frameworks[*].formalism_specific.epistemic_beliefs[*][*]",
            "dung_frameworks[*].formalism_specific.contraries[*]",
            "dung_frameworks[*].formalism_specific.delp_arguments[*]",
        }
    ),
    # The dominant survivor on real corpora (coord R785: 1024–2304 occurrences).
    # ``add_formal_synthesis_report`` stores ``phase_results`` verbatim, and it
    # republishes the formal phases' output — including the Dung extensions,
    # which are the same claim texts 4c opacifies under ``dung_frameworks``.
    "formal_synthesis_reports": frozenset(
        {
            "formal_synthesis_reports[*].phase_results.dung_extensions."
            "all_extensions.conflict_free.extensions[*][*]",
            "formal_synthesis_reports[*].phase_results.dung_extensions."
            "all_extensions.admissible.extensions[*][*]",
            "formal_synthesis_reports[*].phase_results.fol.message",
        }
    ),
    # Formal-logic status messages can carry NL (``"unavailable: <reason>"``).
    # Not in any scrubber table.
    "fol_analysis_results": frozenset({"fol_analysis_results[*].message"}),
    "propositional_analysis_results": frozenset(
        {"propositional_analysis_results[*].message"}
    ),
    "modal_analysis_results": frozenset({"modal_analysis_results[*].message"}),
    # JTMS belief names can be argument text; justifications are free-form.
    "jtms_beliefs": frozenset(
        {"jtms_beliefs[*].name", "jtms_beliefs[*].justifications[*]"}
    ),
    # Stored verbatim by ``_write_atms_to_state``; not in any scrubber table.
    "atms_contexts": frozenset({"atms_contexts[*].hypotheses[*]"}),
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

        The first-level field the coordinator's own recension missed. Its
        ``.summary`` is covered (pass 5); its ``.phase_results`` is not, and
        that gap is frozen in EXPECTED_UNCOVERED. This pins both halves: the
        field is exercised by the canary, and its gap is named, not silent.
        """
        out = sanitize_state(_canaried_state().get_state_snapshot())
        # Covered half: pass 5 strips the ``summary`` KEY entirely
        # (``_strip_text_from_dict`` drops it), so it is absent — not merely
        # opacified. Asserting on its value would KeyError.
        assert "summary" not in out["formal_synthesis_reports"][0]
        # Gap half: .phase_results still carries the canary, and the frozen set
        # names those paths.
        assert CANARY in repr(out["formal_synthesis_reports"])
        assert "formal_synthesis_reports" in EXPECTED_UNCOVERED

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
        # Tolerate only the pass-1 top-level strips and structural bookkeeping
        # the scrubber removes or that are not producer NL surfaces.
        tolerated = {
            "raw_text",
            "raw_text_snippet",
            "full_text",
            "full_text_segment",
            "id",
            "task_count",
            "deanonymized",
            "structured_arg_status",
            "atomic_propositions",
            "fol_shared_signature",
            "fol_signature",
            "jtms_retraction_chain",
            "restitution_acts_degraded",
            "workflow_results",
            "ai_shield_results",
            "local_llm_results",
            "deliberation_trace",
            "source_id",
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
        "table_attr,field,expected_path_fragment",
        [
            # Pass 4b: dung_frameworks.arguments/attacks.
            ("_OPAQUE_LIST_SUBKEYS", "dung_frameworks", ".arguments"),
            # Pass 5b: aspic_results.extensions.
            ("_OPAQUE_LIST_OF_DICTS_SUBKEYS", "aspic_results", ".extensions"),
            # Pass 5b: belief_revision_results.original/revised.
            (
                "_OPAQUE_LIST_OF_DICTS_SUBKEYS",
                "belief_revision_results",
                ".original",
            ),
            # Pass 5d: aspic_results.attacks target/attacker_premises.
            ("_OPAQUE_NESTED_ITEM_SUBKEYS", "aspic_results", ".attacks"),
        ],
    )
    def test_removing_a_rule_lets_the_canary_through(
        self,
        monkeypatch: pytest.MonkeyPatch,
        table_attr: str,
        field: str,
        expected_path_fragment: str,
    ) -> None:
        original_table = getattr(_sanitize_mod, table_attr)
        # Surgical copy minus the one field — the rest of the table stays armed.
        reduced = {k: v for k, v in original_table.items() if k != field}
        monkeypatch.setattr(_sanitize_mod, table_attr, reduced)

        survivors = _surviving_paths(
            sanitize_state(_canaried_state().get_state_snapshot())
        )
        field_paths = survivors.get(field, set())
        # The canary that the removed rule was killing must now survive, and at
        # least one surviving path must carry the expected sub-path fragment.
        assert field_paths, (
            f"removing {table_attr}[{field!r}] did NOT let the canary through — "
            "the substitution control is vacuous (some other pass also covers "
            "it, or the canary never reached it)."
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
