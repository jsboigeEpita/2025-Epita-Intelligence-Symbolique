# -*- coding: utf-8 -*-
"""#3008 — a Dung node carries its unit id, never the argument text.

The producer built the graph over the TEXTS ``_extract_arguments_from_context``
returns (ids discarded at the source), so every reader keyed by "opaque arg_id"
held free text instead: on the measured doc_A state the 15 ``dung_frameworks``
entries carry 0 ``arg_N`` (join to ``identified_arguments`` by exact text 0/7,
by 60-char prefix 7/7 — positional, unvalidated), Act III's decisive rejection
quotes truncated prose where the id should be, and its anchors — the quotation —
are never keys of ``identified_arguments``, so the rejected unit never reaches
the cited excerpts.

The fix is at the source: nodes are minted by the same builder that mints the
population (``merged_population_units`` — state ids first, the extract output's
positional ``arg_N`` fallback second), the text travels as a separate label,
and the attack edges are translated text→id against the very list that produced
them (exact, by construction — never a prefix/substring heuristic). The writer
then refuses a pipeline payload whose arguments are not ids while units exist,
unless the payload names the absence.

Born red on ``main`` (measured on ``f40349378``): the producer returns text
nodes, the writer accepts them, the reader quotes prose. Green after: the frame
is built over ``arg_1..arg_N``, ``argument_labels`` reaches the curated entry,
and the decisive rejection names its unit.

Privacy HARD: synthetic French sentences only — no corpus text.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from argumentation_analysis.orchestration import invoke_callables as ic
from argumentation_analysis.orchestration.state_writers import (
    _write_dung_extensions_to_state,
)

# The measured defect shape: the Dung-source text is a 120-char TRUNCATION of
# the identified unit's text — prefix-equal, never equal (the exact form the
# issue measured: exact join 0/7, prefix join 7/7).
_UNIT_1 = (
    "Première thèse synthétique suffisamment longue pour que sa troncature à "
    "cent vingt caractères devienne un texte distinct mais préfixe-égal, ce "
    "qui est exactement la forme mesurée sur l'état réel."
)
_UNIT_2 = (
    "Seconde thèse synthétique, distincte de la première, elle aussi assez "
    "longue pour que le producteur historique la tronque en un libellé qui ne "
    "rejoint plus jamais l'unité identifiée correspondante."
)
assert len(_UNIT_1) > 120 and len(_UNIT_2) > 120
_TRUNC_1, _TRUNC_2 = _UNIT_1[:120], _UNIT_2[:120]


def _state(**fields: Any) -> SimpleNamespace:
    """Lightweight state stub carrying the fields the readers read."""
    base: Dict[str, Any] = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        argument_provenance={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
        analysis_coverage={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


class _RecordingState(SimpleNamespace):
    """A state stub whose ``add_dung_framework`` mirrors the real entry shape.

    Accepts the pre-fix four-keyword call AND the post-fix one (extra optional
    parameters), so the same witness runs red on the old tree by ASSERTION,
    not by TypeError.
    """

    def __init__(self, **fields: Any) -> None:
        super().__init__(**fields)
        self.dung_frameworks: Dict[str, Dict[str, Any]] = {}
        self.traces: List[str] = []

    def add_dung_framework(
        self,
        name: str,
        arguments: List[str],
        attacks: List[List[str]],
        extensions: Optional[Dict[str, Any]] = None,
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
    ) -> str:
        df_id = f"dung_{len(self.dung_frameworks) + 1}"
        entry: Dict[str, Any] = {
            "name": name,
            "arguments": arguments,
            "attacks": attacks,
            "extensions": extensions or {},
        }
        if argument_labels is not None:
            entry["argument_labels"] = argument_labels
        if argument_ids_absent_reason is not None:
            entry["argument_ids_absent_reason"] = argument_ids_absent_reason
        self.dung_frameworks[df_id] = entry
        return df_id

    def add_trace_entry(self, **kw: Any) -> None:
        self.traces.append(str(kw.get("summary", "")))


def _patch_solver(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the JVM path deterministic: preferred/grounded accept only arg_2.

    Patches the module attributes the producer imports at CALL time, so the
    witness neither launches a JVM nor depends on the seat's Tweety build.
    """
    import argumentation_analysis.agents.core.logic.af_handler as afh
    import argumentation_analysis.agents.core.logic.tweety_initializer as twi

    class _FakeAFHandler:
        def __init__(self, initializer: Any) -> None:
            pass

        def analyze_multi_semantics(
            self, arguments: List[str], attacks: Any, semantics: List[str]
        ) -> Dict[str, Any]:
            members = [a for a in arguments if arguments and a != arguments[0]]
            return {"extensions": {sem: [list(members)] for sem in semantics}}

    monkeypatch.setattr(afh, "AFHandler", _FakeAFHandler)
    monkeypatch.setattr(afh, "SEMANTICS_REASONERS", {"preferred": 1, "grounded": 2})
    monkeypatch.setattr(twi, "ready_initializer", lambda: object())


def _patch_translator(monkeypatch: pytest.MonkeyPatch, pairs: List[List[str]]) -> None:
    """Stand in for the #1698 translator: return canonical TEXT pairs."""

    async def fake_translate(text: str, arguments: List[str]) -> Any:
        return (pairs, "evaluated", "")

    monkeypatch.setattr(ic, "_translate_dung_attacks_once", fake_translate)


# --------------------------------------------------------------------------
# The producer — nodes minted from the SAME source as identified_arguments
# --------------------------------------------------------------------------


class TestTheProducerMintsIdNodes:
    async def test_the_frame_is_built_over_unit_ids_not_texts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The state population wins over the extract output even when both
        exist — the ids are the state's, the texts only labels."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context: Dict[str, Any] = {
            "_state_object": state,
            # The extract output carries the HISTORICAL truncated texts — the
            # prefix-equal-≠ shape the issue measured. The old producer built
            # the graph over these; the fixed one reads the state population.
            "phase_extract_output": {
                "arguments": [{"text": _TRUNC_1}, {"text": _TRUNC_2}]
            },
        }
        _patch_solver(monkeypatch)
        _patch_translator(monkeypatch, [[_UNIT_1, _UNIT_2]])

        result = await ic._invoke_dung_extensions(_UNIT_1, context)

        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == {"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        assert result.get("attacks") == [["arg_1", "arg_2"]]
        assert "argument_ids_absent_reason" not in result

    async def test_without_a_state_the_extract_fallback_is_positional(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No state object: the extract output's own enumeration mints the ids
        — the #1629 arithmetic, not a text join."""
        context: Dict[str, Any] = {
            "phase_extract_output": {
                "arguments": [{"text": _UNIT_1}, {"text": _UNIT_2}]
            }
        }
        _patch_solver(monkeypatch)
        _patch_translator(monkeypatch, [[_UNIT_1, _UNIT_2]])

        result = await ic._invoke_dung_extensions(_UNIT_1, context)

        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == {"arg_1": _UNIT_1, "arg_2": _UNIT_2}

    async def test_no_population_at_all_names_the_absence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Neither state nor extract output: the sentence fallback keeps real
        content as nodes but says explicitly that no unit id exists — never a
        guessed id."""
        context: Dict[str, Any] = {}
        _patch_solver(monkeypatch)
        _patch_translator(monkeypatch, [])

        result = await ic._invoke_dung_extensions(
            "Une première phrase synthétique assez longue pour exister seule. "
            "Une seconde phrase synthétique distincte et tout aussi longue.",
            context,
        )

        assert result["arguments"], "the sentence fallback must keep real nodes"
        assert all(
            not re.fullmatch(r"arg_\d+", str(a)) for a in result["arguments"]
        ), "no id may be guessed when no population minted one"
        assert result.get("argument_labels") in (None, {})
        reason = str(result.get("argument_ids_absent_reason") or "")
        assert reason, "the absence of ids must be named, not silent"


# --------------------------------------------------------------------------
# The writer — the guard and the label map
# --------------------------------------------------------------------------


class TestTheWriterGuard:
    def test_a_non_id_population_with_units_present_is_refused(self) -> None:
        """The measured defect shape reaching the writer post-fix is a
        producer regression: fail loud, never curate text nodes again."""
        state = _RecordingState(identified_arguments={"arg_1": _UNIT_1})
        legacy_payload: Dict[str, Any] = {
            "semantics": "multi",
            "extensions": {"all_members": [_TRUNC_2]},
            "all_extensions": {
                "preferred": {"extensions": [[_TRUNC_2]], "all_members": [_TRUNC_2]}
            },
            "arguments": [_TRUNC_1, _TRUNC_2],
            "attacks": [],
        }
        with pytest.raises(ValueError, match="3008"):
            _write_dung_extensions_to_state(legacy_payload, state, {})

    def test_the_named_absence_is_honest_not_red(self) -> None:
        """A payload that declares it had no population keeps its sentence
        nodes — the tri-state: a named absence is not a hidden one."""
        state = _RecordingState(identified_arguments={"arg_1": _UNIT_1})
        fallback_payload: Dict[str, Any] = {
            "semantics": "multi",
            "extensions": {},
            "all_extensions": {},
            "arguments": ["Une phrase synthétique sans unité rattachable."],
            "attacks": [],
            "argument_labels": {},
            "argument_ids_absent_reason": (
                "no identified_arguments population — sentence fallback"
            ),
        }
        _write_dung_extensions_to_state(fallback_payload, state, {})
        entry = next(iter(state.dung_frameworks.values()))
        assert entry["argument_ids_absent_reason"]

    def test_the_label_map_reaches_the_curated_entry(self) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        payload: Dict[str, Any] = {
            "semantics": "multi",
            "extensions": {"all_members": ["arg_2"]},
            "all_extensions": {
                "preferred": {"extensions": [["arg_2"]], "all_members": ["arg_2"]}
            },
            "arguments": ["arg_1", "arg_2"],
            "attacks": [["arg_1", "arg_2"]],
            "argument_labels": {"arg_1": _UNIT_1, "arg_2": _UNIT_2},
        }
        _write_dung_extensions_to_state(payload, state, {})
        entries = list(state.dung_frameworks.values())
        assert entries, "the writer must curate the framework"
        for entry in entries:
            assert entry.get("argument_labels") == {
                "arg_1": _UNIT_1,
                "arg_2": _UNIT_2,
            }


# --------------------------------------------------------------------------
# The full chain — producer + writer + readers, born red on main
# --------------------------------------------------------------------------


async def _produce_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> _RecordingState:
    """Drive the REAL producer and writer over the measured defect context."""
    state = _RecordingState(
        identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2},
        analysis_coverage={"fallacy_per_argument": {"unit_ids": ["arg_1", "arg_2"]}},
        argument_quality_scores={
            "arg_1": {"overall": 2.0, "scores": {"clarte": 1.0, "pertinence": 1.0}},
            "arg_2": {"overall": 2.0, "scores": {"clarte": 1.0, "pertinence": 1.0}},
        },
    )
    context: Dict[str, Any] = {
        "_state_object": state,
        "phase_extract_output": {"arguments": [{"text": _TRUNC_1}, {"text": _TRUNC_2}]},
    }
    _patch_solver(monkeypatch)
    _patch_translator(monkeypatch, [[_UNIT_1, _UNIT_2]])
    result = await ic._invoke_dung_extensions(_UNIT_1, context)
    _write_dung_extensions_to_state(result, state, {})
    return state


class TestTheFullChainNamesTheUnit:
    async def test_the_rejection_is_keyed_by_the_unit_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from argumentation_analysis.reporting.restitution.native_dung import (
            decode_native_dung,
        )

        state = await _produce_and_write(monkeypatch)
        rejected = decode_native_dung(state).rejected_by_arg
        # The semantics label depends on the writer's entry order (the primary
        # entry files first); the CONTRACT here is the KEY: the unit id, never
        # a quotation.
        assert list(rejected) == ["arg_1"]

    async def test_the_decisive_role_cites_the_id_not_the_quotation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from argumentation_analysis.reporting.restitution.specialist_roles import (
            ROLE_DECISIF,
            classify_specialist_roles,
        )

        state = await _produce_and_write(monkeypatch)
        decisif = [
            r
            for r in classify_specialist_roles(state)
            if r.role == ROLE_DECISIF and "Dung" in r.statement
        ]
        assert decisif, "the Dung rejection must earn the decisive role"
        statement = decisif[0].statement
        assert "arg_1" in statement
        assert _TRUNC_1 not in statement and _UNIT_1 not in statement
        assert decisif[0].cites[0] == "arg_1"

    async def test_act_ii_names_the_unit_like_the_other_axes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        state = await _produce_and_write(monkeypatch)
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "ne retient pas arg_1" in prompt
        assert f"ne retient pas {_TRUNC_1}" not in prompt

    async def test_a_dung_rejected_unit_is_not_an_unchallenged_strength(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The cross-axis consequence: with text keys the exclusion never
        fired, so a Dung-rejected unit could still read as « holding ». Keyed
        by id, the rejection excludes it from the strengths."""
        from argumentation_analysis.reporting.restitution.conclusion_salience import (
            _unchallenged_strengths,
        )

        state = await _produce_and_write(monkeypatch)
        cited = {c for item in _unchallenged_strengths(state) for c in item.cites}
        assert "arg_2" in cited, "the surviving unit keeps its strength line"
        assert "arg_1" not in cited, "the Dung-rejected unit must not hold"

    async def test_the_rejected_unit_reaches_the_act_iii_weak_points(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _collect_weak_points,
        )
        from argumentation_analysis.reporting.restitution.native_dung import (
            decode_native_dung,
        )

        state = await _produce_and_write(monkeypatch)
        points = _collect_weak_points(
            {}, decode_native_dung(state).rejected_by_arg, 0, 0
        )
        dung_points = [p for p in points if p.source == "dung"]
        assert dung_points and dung_points[0].target_arg_id == "arg_1"


# --------------------------------------------------------------------------
# Export privacy — the label stays within the scrub's reach
# --------------------------------------------------------------------------


class TestTheLabelStaysScrubbed:
    def test_the_export_scrub_opacifies_the_label_map(self) -> None:
        """Moving the text out of the node identity must not move it out of
        the scrub's reach: ``argument_labels`` values are scrubbed like the
        ``arguments`` list always was."""
        from argumentation_analysis.evaluation.state_export_scrub import (
            _scrub_state_for_export,
        )

        label = "Un libellé synthétique bien plus long que dix caractères."
        state_data: Dict[str, Any] = {
            "identified_arguments": {"arg_1": "<scrubbed-in-pass-2>"},
            "dung_frameworks": {
                "dung_1": {
                    "name": "verification_preferred",
                    "arguments": ["arg_1"],
                    "attacks": [],
                    "extensions": {"all_members": ["arg_1"]},
                    "argument_labels": {"arg_1": label},
                }
            },
        }
        cleaned = _scrub_state_for_export(state_data, instance_re=re.compile(r"(?!)"))
        entry = cleaned["dung_frameworks"]["dung_1"]
        assert (
            entry["argument_labels"]["arg_1"] != label
        ), "the label must be opacified exactly like the arguments list"
