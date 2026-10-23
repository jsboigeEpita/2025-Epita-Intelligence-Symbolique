# -*- coding: utf-8 -*-
"""#3014 — an AF-family node carries its unit id, never the argument text.

Batch 1: the four ``add_dung_framework`` callables — SETAF, weighted,
social, EAF. Each built its frame over the TEXTS
``_extract_arguments_from_context`` returns (the extraction window: on the
measured doc_A state 7 of 94 units), so every downstream surface keyed by
``arg_N`` held free text instead: the ``set_attacks`` / ``attack_weights`` /
``epistemic_beliefs`` / ``social_ranking`` sidecars the Act III projector
reads, and ``native_dung.extension_lists``, could never join a node back to
the unit it came from — the same dead join #3008 measured on Dung (0/7 exact
joins, 7/7 positional prefix).

Batch 2a (this file's last three classes): the three ``add_*_result``
callables — ranking, probabilistic, bipolar. Same defect, one more surface
each: ``ranking_results`` entries (``arguments`` / ``comparisons``),
``probabilistic_results`` (``arguments`` and the keys of
``acceptance_probabilities``) and ``bipolar_results`` (``arguments`` and the
``supports`` endpoints) carried extraction-window texts as nodes — the
six-way ``multi_format_exporter`` reads and the sanitizer scrubs could not
join them back to the units.

The fix mirrors #3009 at each site: the nodes are minted by the family
builder ``_population_node_units`` (state ``identified_arguments`` ids first,
extract positional fallback second), the texts travel as labels through every
text-consuming seam (translators, derivation read prose and translate back
EXACTLY — both sides from the same in-memory pairs, never a prefix join),
and each return site carries ``argument_labels`` (+ the named id-absence)
for its writer to curate.

Born red on ``main`` (the source edits stashed, the file alone): the
producers return text nodes and text-keyed edges, votes and beliefs, and the
writers curate entries without labels. Green after: the frames are built
over ``arg_1..arg_N`` with labels alongside.

Privacy HARD: synthetic French sentences only — no corpus text.
"""

from __future__ import annotations

import importlib
import re
import sys
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from argumentation_analysis.orchestration import invoke_callables as ic
from argumentation_analysis.orchestration.state_writers import (
    _write_aba_to_state,
    _write_adf_to_state,
    _write_aspic_to_state,
    _write_belief_revision_to_state,
    _write_bipolar_to_state,
    _write_dialogue_to_state,
    _write_eaf_to_state,
    _write_probabilistic_to_state,
    _write_ranking_to_state,
    _write_setaf_to_state,
    _write_social_to_state,
    _write_weighted_to_state,
)

# The measured defect shape (#3009 fixture form): the extraction-window text
# is a 120-char TRUNCATION of the identified unit's text — prefix-equal,
# never equal.
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

_LABELS = {"arg_1": _UNIT_1, "arg_2": _UNIT_2}


def _measured_context(state: Any) -> Dict[str, Any]:
    """The measured defect context: state population + truncated extract."""
    return {
        "_state_object": state,
        "phase_extract_output": {"arguments": [{"text": _TRUNC_1}, {"text": _TRUNC_2}]},
    }


class _RecordingState(SimpleNamespace):
    """A state stub whose ``add_dung_framework`` mirrors the real entry shape.

    Accepts the pre-#3008 four-keyword call AND the labelled one, so the same
    witness runs red on the old tree by ASSERTION, not by TypeError.
    """

    def __init__(self, **fields: Any) -> None:
        super().__init__(**fields)
        self.dung_frameworks: Dict[str, Dict[str, Any]] = {}
        self.ranking_results: List[Dict[str, Any]] = []
        self.probabilistic_results: List[Dict[str, Any]] = []
        self.bipolar_results: List[Dict[str, Any]] = []
        self.aspic_results: List[Dict[str, Any]] = []
        self.belief_revision_results: List[Dict[str, Any]] = []
        self.dialogue_results: List[Dict[str, Any]] = []
        self.traces: List[str] = []

    def add_dung_framework(
        self,
        name: str,
        arguments: List[str],
        attacks: List[Any],
        extensions: Optional[Dict[str, Any]] = None,
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
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
        self._counters(entry, population_total, dropped_unresolved)
        self.dung_frameworks[df_id] = entry
        return df_id

    # The batch-2a sinks mirror the same contract: accept the pre-#3014
    # positional call AND the labelled one, so the witness runs red on the
    # old tree by ASSERTION, not by TypeError.
    def _curated(
        self,
        base: Dict[str, Any],
        argument_labels: Any,
        reason: Any,
        population_total: Any = None,
        dropped_unresolved: Any = None,
    ) -> Dict[str, Any]:
        if argument_labels is not None:
            base["argument_labels"] = argument_labels
        if reason is not None:
            base["argument_ids_absent_reason"] = reason
        return self._counters(base, population_total, dropped_unresolved)

    def _counters(
        self, base: Dict[str, Any], population_total: Any, dropped_unresolved: Any
    ) -> Dict[str, Any]:
        """#3014 item 2: the two identity counters ride the entry when set —
        mirrors the real ``UnifiedAnalysisState`` sinks, so the writer's
        ``**_identity_counts(output)`` pass-through lands by ASSERTION."""
        if population_total is not None:
            base["population_total"] = population_total
        if dropped_unresolved is not None:
            base["dropped_unresolved"] = dropped_unresolved
        return base

    def add_ranking_result(
        self,
        method: str,
        arguments: List[str],
        comparisons: List[Dict[str, Any]],
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
    ) -> str:
        entry = self._curated(
            {"method": method, "arguments": arguments, "comparisons": comparisons},
            argument_labels,
            argument_ids_absent_reason,
            population_total,
            dropped_unresolved,
        )
        self.ranking_results.append(entry)
        return f"rank_{len(self.ranking_results)}"

    def add_probabilistic_result(
        self,
        arguments: List[str],
        acceptance_probs: Dict[str, float],
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
        probabilities_source: Optional[str] = None,
    ) -> str:
        entry = self._curated(
            {"arguments": arguments, "acceptance_probabilities": acceptance_probs},
            argument_labels,
            argument_ids_absent_reason,
            population_total,
            dropped_unresolved,
        )
        # #3096 item 3 — stored only when set, mirroring the real state sink.
        if probabilities_source is not None:
            entry["probabilities_source"] = probabilities_source
        self.probabilistic_results.append(entry)
        return f"prob_{len(self.probabilistic_results)}"

    def add_bipolar_result(
        self,
        framework_type: str,
        arguments: List[str],
        supports: List[List[str]],
        support_cycles: Optional[List[List[str]]] = None,
        articulation_points: Optional[List[Dict[str, Any]]] = None,
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
    ) -> str:
        entry = self._curated(
            {
                "framework_type": framework_type,
                "arguments": arguments,
                "supports": supports,
                "support_cycles": support_cycles or [],
                "articulation_points": articulation_points or [],
            },
            argument_labels,
            argument_ids_absent_reason,
            population_total,
            dropped_unresolved,
        )
        self.bipolar_results.append(entry)
        return f"bipolar_{len(self.bipolar_results)}"

    def add_aspic_result(
        self,
        reasoner_type: str,
        extensions: List[Any],
        statistics: Dict[str, Any],
        attacks: Optional[List[Dict[str, Any]]] = None,
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
    ) -> str:
        entry = self._curated(
            {
                "reasoner_type": reasoner_type,
                "extensions": extensions,
                "statistics": statistics,
                "attacks": list(attacks) if attacks is not None else [],
            },
            argument_labels,
            argument_ids_absent_reason,
            population_total,
            dropped_unresolved,
        )
        self.aspic_results.append(entry)
        return f"aspic_{len(self.aspic_results)}"

    def add_belief_revision_result(
        self,
        method: str,
        original: List[str],
        revised: List[str],
        minimal_retraction: Optional[Dict[str, Any]] = None,
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
        degraded: Optional[bool] = None,
        absent_reason: Optional[str] = None,
    ) -> str:
        entry = self._curated(
            {"method": method, "original": original, "revised": revised},
            argument_labels,
            argument_ids_absent_reason,
            population_total,
            dropped_unresolved,
        )
        if minimal_retraction is not None:
            entry["minimal_retraction"] = minimal_retraction
        # #3178 — the tri-state marker, stored only when stated.
        if isinstance(degraded, bool):
            entry["degraded"] = degraded
        if absent_reason:
            entry["absent_reason"] = absent_reason
        self.belief_revision_results.append(entry)
        return f"brevision_{len(self.belief_revision_results)}"

    def add_dialogue_result(
        self,
        topic: str,
        outcome: str,
        trace: List[Dict[str, Any]],
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
        population_total: Optional[int] = None,
        dropped_unresolved: Optional[int] = None,
    ) -> str:
        entry = self._curated(
            {"topic": topic, "outcome": outcome, "trace": trace},
            argument_labels,
            argument_ids_absent_reason,
            population_total,
            dropped_unresolved,
        )
        self.dialogue_results.append(entry)
        return f"dialogue_{len(self.dialogue_results)}"

    def add_trace_entry(self, **kw: Any) -> None:
        self.traces.append(str(kw.get("summary", "")))


def _install_fake_handler(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    class_name: str,
    method_name: str,
    received: List[Dict[str, Any]],
    returns: Any,
    takes_initializer: bool = True,
) -> None:
    """Patch the JVM seam on its home module (the callable imports at call
    time): the handler records what it received and answers ``returns`` —
    a static dict, or a callable building the echo from the call args.
    ``takes_initializer=False`` for the batch-2a handlers constructed with
    no initializer argument (ranking / probabilistic / bipolar)."""
    import argumentation_analysis.agents.core.logic.tweety_initializer as twi

    mod = importlib.import_module(
        f"argumentation_analysis.agents.core.logic.{module_name}"
    )

    def _analyze(self: Any, *call_args: Any, **call_kwargs: Any) -> Dict[str, Any]:
        received.append({"args": call_args, "kwargs": call_kwargs})
        if callable(returns):
            out = dict(returns(*call_args))
        else:
            out = dict(returns)
        # The real handlers echo the inventory they were handed.
        out.setdefault("arguments", list(call_args[0]))
        return out

    fake_init = (
        (lambda self, initializer: None) if takes_initializer else (lambda self: None)
    )
    fake_cls = type(class_name, (), {"__init__": fake_init, method_name: _analyze})
    monkeypatch.setattr(mod, class_name, fake_cls)
    monkeypatch.setattr(twi, "ready_initializer", lambda: object())


def _install_fake_translator(
    monkeypatch: pytest.MonkeyPatch,
    fn_name: str,
    relations: Any,
    seen: List[List[str]],
) -> None:
    """Stand in for the #1698 translator: answer label-referencing relations
    and record the inventory it was fed (the seam keeps reading TEXTS). Takes
    the seam's named ``atomizer`` (#3014) under its real name — an absorbing
    ``**kwargs`` certifies call shapes the real site never makes (#3064)."""
    import argumentation_analysis.orchestration.structured_arg_translator as sat

    async def _fake(text: str, arguments: List[str], atomizer: Any = None) -> Any:
        seen.append(list(arguments))
        return SimpleNamespace(relations=relations, cause="evaluated", error="")

    monkeypatch.setattr(sat, fn_name, _fake)


def _install_fake_derivation(
    monkeypatch: pytest.MonkeyPatch, pairs: List[List[str]]
) -> None:
    """Stand in for _derive_dung_attacks: label-referencing edges, no JVM."""

    async def _fake(
        input_text: str,
        arguments: List[str],
        context: Dict[str, Any],
        *,
        capability: str,
    ) -> List[List[str]]:
        return [list(p) for p in pairs]

    monkeypatch.setattr(ic, "_derive_dung_attacks", _fake)


# --------------------------------------------------------------------------
# SETAF — joint attacks keyed by unit ids
# --------------------------------------------------------------------------


class TestSetafNodesAreUnits:
    async def test_the_frame_and_joint_attacks_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        handler_seen: List[Dict[str, Any]] = []
        translator_seen: List[List[str]] = []
        # The translator answers over the FULL texts — the inventory the seam
        # must keep reading — never over ids.
        _install_fake_translator(
            monkeypatch,
            "translate_to_setaf_attacks",
            [{"attackers": [_UNIT_1], "target": _UNIT_2}],
            translator_seen,
        )
        _install_fake_handler(
            monkeypatch,
            "setaf_handler",
            "SetAFHandler",
            "analyze_setaf",
            handler_seen,
            {"extensions": [["arg_2"]], "statistics": {}},
        )

        result = await ic._invoke_setaf(_UNIT_1, context)

        # The translator seam kept reading TEXTS (full units, not truncations).
        assert translator_seen == [[_UNIT_1, _UNIT_2]]
        # The frame's nodes are the units' ids.
        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        # The handler received ids — arguments AND joint-attack members.
        args, attacks, _semantics = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        assert list(attacks) == [{"attackers": ["arg_1"], "target": "arg_2"}]
        # The honest echo (#1698) is id-keyed too.
        assert result["attacks"] == [{"attackers": ["arg_1"], "target": "arg_2"}]

    async def test_the_writer_curates_labels_and_the_sidecar(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_translator(
            monkeypatch,
            "translate_to_setaf_attacks",
            [{"attackers": [_UNIT_1], "target": _UNIT_2}],
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "setaf_handler",
            "SetAFHandler",
            "analyze_setaf",
            handler_seen,
            {"extensions": [["arg_2"]], "statistics": {}},
        )

        result = await ic._invoke_setaf(_UNIT_1, context)
        _write_setaf_to_state(result, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        # The #1648 sidecar the Act III projector reads joins by id now.
        sidecar = entry.get("formalism_specific", {}).get("set_attacks")
        assert sidecar == [{"attackers": ["arg_1"], "target": "arg_2"}]


# --------------------------------------------------------------------------
# Weighted — attack endpoints (and their weights) keyed by unit ids
# --------------------------------------------------------------------------


class TestWeightedNodesAreUnits:
    async def test_the_frame_and_weighted_edges_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        handler_seen: List[Dict[str, Any]] = []
        translator_seen: List[List[str]] = []
        _install_fake_translator(
            monkeypatch,
            "translate_to_weighted_attacks",
            [(_UNIT_1, _UNIT_2, 0.8)],
            translator_seen,
        )
        _install_fake_handler(
            monkeypatch,
            "weighted_handler",
            "WeightedHandler",
            "analyze_weighted_framework",
            handler_seen,
            {"extensions": [["arg_2"]], "statistics": {}},
        )

        result = await ic._invoke_weighted(_UNIT_1, context)

        assert translator_seen == [[_UNIT_1, _UNIT_2]]
        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        args, attacks, _semantics = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        # The endpoints translated to ids and the weight rode along unchanged
        # (the retention echo normalizes triples to dicts, #2068).
        assert [tuple(a) for a in attacks] == [("arg_1", "arg_2", 0.8)]
        assert result["attacks"] == [
            {"source": "arg_1", "target": "arg_2", "weight": 0.8}
        ]

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_translator(
            monkeypatch,
            "translate_to_weighted_attacks",
            [(_UNIT_1, _UNIT_2, 0.8)],
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "weighted_handler",
            "WeightedHandler",
            "analyze_weighted_framework",
            [],
            {"extensions": [["arg_2"]], "statistics": {}},
        )

        result = await ic._invoke_weighted(_UNIT_1, context)
        _write_weighted_to_state(result, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        # The #1648 sidecar (attack_weights) joins by id now, weight intact.
        sidecar = entry.get("formalism_specific", {}).get("attack_weights")
        assert sidecar == [{"source": "arg_1", "target": "arg_2", "weight": 0.8}]


# --------------------------------------------------------------------------
# Social — attacks, votes and scores keyed by unit ids
# --------------------------------------------------------------------------


class TestSocialNodesAreUnits:
    async def test_the_frame_votes_and_edges_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # Votes keyed by argument NAME (the upstream contract); one key joins
        # no node and must be dropped, never guessed onto one.
        context["votes"] = {_UNIT_1: [1, 2], "Texte non membre": [3]}
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "social_handler",
            "SocialHandler",
            "analyze_social_framework",
            handler_seen,
            {"ranking": ["arg_2", "arg_1"], "scores": {"arg_2": 2, "arg_1": 1}},
        )

        result = await ic._invoke_social(_UNIT_1, context)

        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        args, attacks, votes = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        assert [list(a) for a in attacks] == [["arg_1", "arg_2"]]
        # Vote keys translated label→id; the non-member key joined nothing.
        assert votes == {"arg_1": (1, 2)}
        assert result["attacks"] == [["arg_1", "arg_2"]]

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "social_handler",
            "SocialHandler",
            "analyze_social_framework",
            [],
            {"ranking": ["arg_2", "arg_1"], "scores": {"arg_2": 2, "arg_1": 1}},
        )

        result = await ic._invoke_social(_UNIT_1, context)
        _write_social_to_state(result, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        # The ranking/scores extensions (native_dung reads them) follow the
        # ids, joinable to the units.
        assert entry["extensions"]["social_ranking"] == ["arg_2", "arg_1"]


# --------------------------------------------------------------------------
# EAF — attacks and per-agent beliefs keyed by unit ids
# --------------------------------------------------------------------------


class TestEafNodesAreUnits:
    async def test_the_frame_attacks_and_beliefs_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # Beliefs keyed by agent, members by argument NAME; one member joins
        # no node and is dropped — an agent whose list empties is dropped too.
        context["epistemic_beliefs"] = {
            "agent_a": [_UNIT_1, "Texte non membre"],
            "agent_b": [_UNIT_2],
        }
        handler_seen: List[Dict[str, Any]] = []

        def _echo(
            args: Any, attacks: Any, beliefs: Any, semantics: Any
        ) -> Dict[str, Any]:
            return {
                "extensions": [["arg_2"]],
                "epistemic_beliefs": {a: list(v) for a, v in beliefs.items()},
            }

        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "eaf_handler",
            "EAFHandler",
            "analyze_epistemic_framework",
            handler_seen,
            _echo,
        )

        result = await ic._invoke_eaf(_UNIT_1, context)

        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        args, attacks, beliefs, _semantics = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        assert [list(a) for a in attacks] == [["arg_1", "arg_2"]]
        assert beliefs == {"agent_a": ["arg_1"], "agent_b": ["arg_2"]}
        # The #1648 sidecar the Act III projector reads joins by id now.
        assert result["epistemic_beliefs"] == {
            "agent_a": ["arg_1"],
            "agent_b": ["arg_2"],
        }

    async def test_an_agent_whose_list_joins_nothing_is_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An agent left holding NO resolvable member joins nothing — None
        lets the handler default to its documented baseline (#1019), never a
        fabricated empty-agent structure."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["epistemic_beliefs"] = {"agent_a": ["Texte non membre"]}
        handler_seen: List[Dict[str, Any]] = []

        def _echo(
            args: Any, attacks: Any, beliefs: Any, semantics: Any
        ) -> Dict[str, Any]:
            return {"extensions": [], "epistemic_beliefs": beliefs or {}}

        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "eaf_handler",
            "EAFHandler",
            "analyze_epistemic_framework",
            handler_seen,
            _echo,
        )

        result = await ic._invoke_eaf(_UNIT_1, context)

        _args, _attacks, beliefs, _sem = handler_seen[0]["args"]
        assert beliefs is None
        assert result.get("argument_labels") == _LABELS

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["epistemic_beliefs"] = {"agent_a": [_UNIT_1]}

        def _echo(
            args: Any, attacks: Any, beliefs: Any, semantics: Any
        ) -> Dict[str, Any]:
            return {"extensions": [["arg_2"]], "epistemic_beliefs": dict(beliefs or {})}

        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "eaf_handler",
            "EAFHandler",
            "analyze_epistemic_framework",
            [],
            _echo,
        )

        result = await ic._invoke_eaf(_UNIT_1, context)
        _write_eaf_to_state(result, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        sidecar = entry.get("formalism_specific", {}).get("epistemic_beliefs")
        assert sidecar == {"agent_a": ["arg_1"]}


# --------------------------------------------------------------------------
# The named absence — the tri-state travels through the family builder
# --------------------------------------------------------------------------


class TestTheNamedAbsence:
    async def test_no_population_names_the_absence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Neither state nor extract output: the sentence fallback keeps real
        content as nodes but says explicitly that no unit id exists — the
        same #3009 contract, through the family builder."""
        context: Dict[str, Any] = {}
        _install_fake_translator(
            monkeypatch,
            "translate_to_setaf_attacks",
            [],
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "setaf_handler",
            "SetAFHandler",
            "analyze_setaf",
            [],
            {"extensions": [], "statistics": {}},
        )

        result = await ic._invoke_setaf(
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
# Batch 2a — ranking, probabilistic, bipolar: the *_results callables
# --------------------------------------------------------------------------


class TestRankingNodesAreUnits:
    async def test_the_frame_and_edges_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # Caller-seam edges: label-referencing pairs (the upstream contract),
        # translated back to node ids — never a prefix join.
        context["attacks"] = [[_UNIT_1, _UNIT_2]]
        context["ranking_method"] = "burden"
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "ranking_handler",
            "RankingHandler",
            "rank_arguments",
            handler_seen,
            {
                "ranking": ["arg_2", "arg_1"],
                "scores": {"arg_2": 2, "arg_1": 1},
                "method": "burden",
            },
            takes_initializer=False,
        )

        result = await ic._invoke_ranking(_UNIT_1, context)

        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        # The handler received ids — nodes AND edges AND the method rode along.
        args, attacks, method = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        assert [list(a) for a in attacks] == [["arg_1", "arg_2"]]
        assert method == "burden"
        # The ranking itself is id-keyed — joinable to the units.
        assert result["ranking"] == ["arg_2", "arg_1"]

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["attacks"] = [[_UNIT_1, _UNIT_2]]
        _install_fake_handler(
            monkeypatch,
            "ranking_handler",
            "RankingHandler",
            "rank_arguments",
            [],
            {
                "ranking": ["arg_2", "arg_1"],
                "comparisons": [{"a": "arg_2", "b": "arg_1", "relation": ">"}],
                "method": "burden",
            },
            takes_initializer=False,
        )

        result = await ic._invoke_ranking(_UNIT_1, context)
        _write_ranking_to_state(result, state, {})

        entry = state.ranking_results[-1]
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        assert entry["method"] == "burden"
        assert entry["comparisons"] == [{"a": "arg_2", "b": "arg_1", "relation": ">"}]


class TestProbabilisticNodesAreUnits:
    async def test_the_frame_probs_and_edges_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # Probabilities keyed by argument NAME (the upstream contract); one
        # key joins no node and must be dropped, never guessed onto one.
        context["probabilities"] = {_UNIT_1: 0.9, "Texte non membre": 0.1}
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])

        def _echo(args: Any, attacks: Any, probs: Any) -> Dict[str, Any]:
            return {
                "acceptance_probabilities": dict(probs),
                "statistics": {},
            }

        _install_fake_handler(
            monkeypatch,
            "probabilistic_handler",
            "ProbabilisticHandler",
            "analyze_probabilistic_framework",
            handler_seen,
            _echo,
            takes_initializer=False,
        )

        result = await ic._invoke_probabilistic(_UNIT_1, context)

        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        args, attacks, probs = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        assert [list(a) for a in attacks] == [["arg_1", "arg_2"]]
        # The probability keys translated label→id; the non-member joined nothing.
        assert probs == {"arg_1": 0.9}
        # The echoed acceptance table the export reads is id-keyed too.
        assert result["acceptance_probabilities"] == {"arg_1": 0.9}

    async def test_absent_probs_default_over_the_ids(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No ``probabilities`` in context: the honest 0.5 baseline is keyed by
        the node ids — not by texts the reader could never join."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_derivation(monkeypatch, [])
        _install_fake_handler(
            monkeypatch,
            "probabilistic_handler",
            "ProbabilisticHandler",
            "analyze_probabilistic_framework",
            [],
            lambda args, attacks, probs: {
                "acceptance_probabilities": dict(probs),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_probabilistic(_UNIT_1, context)

        assert result["acceptance_probabilities"] == {"arg_1": 0.5, "arg_2": 0.5}

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["probabilities"] = {_UNIT_1: 0.9}
        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "probabilistic_handler",
            "ProbabilisticHandler",
            "analyze_probabilistic_framework",
            [],
            lambda args, attacks, probs: {
                "acceptance_probabilities": dict(probs),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_probabilistic(_UNIT_1, context)
        _write_probabilistic_to_state(result, state, {})

        entry = state.probabilistic_results[-1]
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        assert entry["acceptance_probabilities"] == {"arg_1": 0.9}


class TestBipolarNodesAreUnits:
    async def test_the_frame_supports_and_cycles_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["attacks"] = [[_UNIT_2, _UNIT_1]]
        handler_seen: List[Dict[str, Any]] = []
        translator_seen: List[List[str]] = []
        # A planted mutual-support cycle, answered over the FULL texts — the
        # inventory the seam must keep reading.
        _install_fake_translator(
            monkeypatch,
            "translate_to_bipolar_supports",
            [[_UNIT_1, _UNIT_2], [_UNIT_2, _UNIT_1]],
            translator_seen,
        )

        def _echo(
            args: Any, attacks: Any, supports: Any, fw_type: Any
        ) -> Dict[str, Any]:
            return {
                "extensions": [["arg_2"]],
                "statistics": {},
                "supports": [list(s) for s in supports],
            }

        _install_fake_handler(
            monkeypatch,
            "bipolar_handler",
            "BipolarHandler",
            "analyze_bipolar_framework",
            handler_seen,
            _echo,
            takes_initializer=False,
        )

        result = await ic._invoke_bipolar(_UNIT_1, context)

        # The translator seam kept reading TEXTS (full units).
        assert translator_seen == [[_UNIT_1, _UNIT_2]]
        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        args, attacks, supports, _fw_type = handler_seen[0]["args"]
        assert list(args) == ["arg_1", "arg_2"]
        assert [list(a) for a in attacks] == [["arg_2", "arg_1"]]
        assert [list(s) for s in supports] == [["arg_1", "arg_2"], ["arg_2", "arg_1"]]
        # The echoed supports the export reads are id-keyed, and the #1645
        # insight (circular authority) is computed over the id-keyed edges.
        assert result["supports"] == [["arg_1", "arg_2"], ["arg_2", "arg_1"]]
        assert result["support_cycles"] == [["arg_1", "arg_2"]]

    async def test_the_honest_absent_payload_still_joins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The JVM-down degraded return carries the node identity fields too —
        every return site, degraded or not, is joinable (#3009 parity)."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_translator(
            monkeypatch,
            "translate_to_bipolar_supports",
            [[_UNIT_1, _UNIT_2]],
            [],
        )
        # The code resolves the JVM state at call time from the home module
        # (import inside the function): pin "not started" there so the
        # honest-absent branch fires regardless of the conftest session JVM,
        # then make the handler's own import raise via None in sys.modules.
        import argumentation_analysis.core.jvm_setup as jvm_setup

        monkeypatch.setattr(jvm_setup, "is_jvm_started", lambda: False)
        monkeypatch.setitem(
            sys.modules,
            "argumentation_analysis.agents.core.logic.bipolar_handler",
            None,
        )

        result = await ic._invoke_bipolar(_UNIT_1, context)

        assert result.get("degraded") is True
        assert result["arguments"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        # The supports the translator established before the failure survive,
        # translated to node ids.
        assert result["supports"] == [["arg_1", "arg_2"]]

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_translator(
            monkeypatch,
            "translate_to_bipolar_supports",
            [[_UNIT_1, _UNIT_2]],
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "bipolar_handler",
            "BipolarHandler",
            "analyze_bipolar_framework",
            [],
            lambda args, attacks, supports, fw_type: {
                "extensions": [["arg_2"]],
                "statistics": {},
                "supports": [list(s) for s in supports],
            },
            takes_initializer=False,
        )

        result = await ic._invoke_bipolar(_UNIT_1, context)
        _write_bipolar_to_state(result, state, {})

        entry = state.bipolar_results[-1]
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        assert entry["supports"] == [["arg_1", "arg_2"]]
        # The #1645 insight was computed over the id-keyed edges and stored:
        # a single support edge holds no cycle — an honest "none detected",
        # not a silently missing field.
        assert entry["support_cycles"] == []


# --------------------------------------------------------------------------
# R1084 review item 1 — the join strips on BOTH sides
# --------------------------------------------------------------------------


class TestStrippedLabelsKeepTheirEdges:
    """A unit whose text carries boundary whitespace keeps its translated edge.

    Every ``translate_to_*`` builds its inventory on the STRIPPED text
    (``_build_inventory``), so the canonical pairs the seam returns reference
    the stripped label while the unit's own text may end in whitespace. The
    join keyed the unstripped text, so such an edge dropped silently — no
    count, no log (on main since #3009, measured by the R1084 review). One
    normalization in one place now: the frame keys ``node_by_label`` by the
    stripped label and ``_node_id_for`` strips the incoming name — labels
    themselves still travel UNSTRIPPED (display).
    """

    async def test_dung_keeps_the_edge_of_a_unit_ending_in_a_space(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1 + "  ", "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # The derivation mirrors the real seam: its inventory strips, so the
        # canonical pair comes back STRIPPED — while the unit's own text (the
        # frame's label, and the label the seam was FED) ends in two spaces.
        _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
        _install_fake_handler(
            monkeypatch,
            "af_handler",
            "AFHandler",
            "analyze_multi_semantics",
            [],
            {"extensions": {"grounded": [["arg_2"]]}, "statistics": {}},
        )

        result = await ic._invoke_dung_extensions(_UNIT_1, context)

        # The labels travel UNSTRIPPED — only the join key strips.
        assert result.get("argument_labels") == {
            "arg_1": _UNIT_1 + "  ",
            "arg_2": _UNIT_2,
        }
        # Born red: the pre-R1084 join keyed the unstripped text and dropped
        # this very edge to [].
        assert result["attacks"] == [["arg_1", "arg_2"]]

    async def test_setaf_keeps_the_joint_attack_of_a_unit_ending_in_a_space(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2 + "  "}
        )
        context = _measured_context(state)
        # The translator answers the stripped canonical pair (its inventory
        # strips); the target unit's own text ends in two spaces.
        _install_fake_translator(
            monkeypatch,
            "translate_to_setaf_attacks",
            [{"attackers": [_UNIT_1], "target": _UNIT_2}],
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "setaf_handler",
            "SetAFHandler",
            "analyze_setaf",
            [],
            {"extensions": [["arg_2"]], "statistics": {}},
        )

        result = await ic._invoke_setaf(_UNIT_1, context)

        # Both endpoints resolved through the stripped join — born red: the
        # target joined nothing and the whole joint attack was dropped.
        assert result["attacks"] == [{"attackers": ["arg_1"], "target": "arg_2"}]
        assert result.get("argument_labels") == {
            "arg_1": _UNIT_1,
            "arg_2": _UNIT_2 + "  ",
        }


# --------------------------------------------------------------------------
# Batch 2b — ABA, ADF, ASPIC: the rule-based theory callables
# --------------------------------------------------------------------------


class TestAbaNodesAreUnits:
    async def test_the_theory_and_contraries_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        handler_seen: List[Dict[str, Any]] = []
        translator_seen: List[List[str]] = []
        # The translator answers over the FULL texts (its inventory); the
        # contrary VALUE is the LLM's defeating sentence — free prose, never
        # an inventory member.
        _install_fake_translator(
            monkeypatch,
            "translate_to_aba_contraries",
            {_UNIT_1: "Sentence contraire synthétique de la première thèse."},
            translator_seen,
        )
        _install_fake_handler(
            monkeypatch,
            "aba_handler",
            "ABAHandler",
            "analyze_aba_framework",
            handler_seen,
            {"extensions": [["arg_1"]], "statistics": {}},
            takes_initializer=False,
        )

        result = await ic._invoke_aba(_UNIT_1, context)

        # The translator seam kept reading TEXTS (full units).
        assert translator_seen == [[_UNIT_1, _UNIT_2]]
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        # The handler received id assumptions, id rules, and an ATOM for the
        # contrary sentence (a Tweety Proposition name, never prose). With 2
        # units both are assumptions, so the derived rule is the theory's
        # non-empty self-loop (head=body=first assumption).
        assumptions, rules, contraries, _semantics = handler_seen[0]["args"]
        assert list(assumptions) == ["arg_1", "arg_2"]
        assert rules == [{"head": "arg_1", "body": ["arg_1"]}]
        assert list(contraries) == ["arg_1"]
        contrary_atom = contraries["arg_1"]
        assert contrary_atom.startswith("contrary_")
        assert " " not in contrary_atom
        # The ECHOED contraries keep the SENTENCE (a label), keyed by id.
        assert result["contraries"] == {
            "arg_1": "Sentence contraire synthétique de la première thèse."
        }

    async def test_the_writer_curates_labels_and_the_sidecar(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_translator(
            monkeypatch,
            "translate_to_aba_contraries",
            {_UNIT_1: "Sentence contraire synthétique."},
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "aba_handler",
            "ABAHandler",
            "analyze_aba_framework",
            [],
            # The real handler echoes the assumptions it was handed.
            lambda assumptions, rules, contraries, semantics: {
                "extensions": [["arg_1"]],
                "assumptions": list(assumptions),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_aba(_UNIT_1, context)
        _write_aba_to_state(result, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        sidecar = entry.get("formalism_specific", {}).get("contraries")
        assert sidecar == {"arg_1": "Sentence contraire synthétique."}


class TestAdfNodesAreUnits:
    async def test_the_statements_and_attacked_conditions_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # Label-keyed caller attacks: the derivation must mark the TARGET
        # statement's condition "F" — through the single join.
        context["attacks"] = [[_UNIT_1, _UNIT_2]]
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "adf_handler",
            "ADFHandler",
            "analyze_adf",
            handler_seen,
            {"interpretations": [["arg_2"]], "statistics": {}},
            takes_initializer=False,
        )

        result = await ic._invoke_adf(_UNIT_1, context)

        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        statements, conditions, _semantics = handler_seen[0]["args"]
        assert list(statements) == ["arg_1", "arg_2"]
        assert conditions == {"arg_1": "T", "arg_2": "F"}

    async def test_a_negation_override_resolves_the_peer_by_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An override condition referencing a peer by TEXT resolves the peer's
        id — the override path stays internally consistent with the id-keyed
        statements (before, the reference missed and silently degraded to a
        tautology)."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["acceptance_conditions"] = {_UNIT_2: f"negation:{_UNIT_1}"}
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "adf_handler",
            "ADFHandler",
            "analyze_adf",
            handler_seen,
            {"interpretations": [], "statistics": {}},
            takes_initializer=False,
        )

        await ic._invoke_adf(_UNIT_1, context)

        _statements, conditions, _semantics = handler_seen[0]["args"]
        assert conditions == {"arg_2": "negation:arg_1"}

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        _install_fake_handler(
            monkeypatch,
            "adf_handler",
            "ADFHandler",
            "analyze_adf",
            [],
            # The real handler echoes the statements it was handed.
            lambda statements, conditions, semantics: {
                "interpretations": [],
                "statements": list(statements),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_adf(_UNIT_1, context)
        _write_adf_to_state(result, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert entry["arguments"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS


class TestAspicNodesAreUnits:
    async def test_the_theory_atoms_are_unit_ids(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # #3064: the REAL translator runs. The old double replaced it and
        # called the atomizer one-arg — exactly what the real validators did
        # NOT do (they passed ``prefix=`` and every real run died in TypeError
        # → ``translator_failed`` since #3017). The seam is now one level
        # lower: the LLM relation extraction answers one genuine rule
        # (premise arg1 → conclusion arg2 over the LABELS) and the real
        # validators + the real ``_atom`` of ``_invoke_aspic`` run under it.
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        handler_seen: List[Dict[str, Any]] = []
        llm_seen: List[Any] = []

        import argumentation_analysis.orchestration.structured_arg_translator as sat

        async def _llm_one_rule(text: str, arguments: List[str], relation_kind: str):
            llm_seen.append((list(arguments), relation_kind))
            return {"rules": [{"premises": ["arg1"], "conclusion": "arg2"}]}

        monkeypatch.setattr(sat, "_llm_extract_relations", _llm_one_rule)
        _install_fake_handler(
            monkeypatch,
            "aspic_handler",
            "ASPICHandler",
            "analyze_aspic_framework",
            handler_seen,
            {"extensions": [["arg_2"]], "statistics": {}},
            takes_initializer=False,
        )

        result = await ic._invoke_aspic(_UNIT_1, context)

        # The seam kept reading TEXTS (the LLM-facing inventory is labels).
        assert llm_seen[0] == ([_UNIT_1, _UNIT_2], "aspic_rules")
        assert result.get("argument_labels") == _LABELS
        assert "argument_ids_absent_reason" not in result
        # The translator survived the real validators (#3064): the axis is
        # labelled evaluated, not translator_failed.
        from argumentation_analysis.orchestration.state_writers import (
            _record_structured_arg_status,
            _translation_cause_key,
        )

        assert (
            context.get(_translation_cause_key("aspic_plus_reasoning")) == "evaluated"
        )
        # The translator-derived rule cites the unit IDS — joinable atoms,
        # not slug+hash atoms derived from prose.
        expected_rule = {"head": "arg_2", "body": ["arg_1"], "name": "def_rule_1"}
        assert context["defeasible_rules"] == [expected_rule]
        strict, defeasible, _axioms = handler_seen[0]["args"]
        assert defeasible[0] == expected_rule

        # The real recorder labels the axis "evaluated" from this context
        # (the structured_arg_status shape the DoD names).
        class _StatusState:
            def __init__(self) -> None:
                self.rows: List[Any] = []

            def add_structured_arg_status(self, *row: Any) -> None:
                self.rows.append(row)

        status_state = _StatusState()
        _record_structured_arg_status(
            status_state, "aspic_plus_reasoning", result, context
        )
        assert status_state.rows, "the recorder filed nothing for the axis"
        assert status_state.rows[0][0] == "aspic_plus_reasoning"
        assert status_state.rows[0][1] == "evaluated"
        assert status_state.rows[0][2] is False

    async def test_the_writer_curates_labels(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # #1591 hermeticity: without rules the invoke calls the REAL
        # translator — answer an honest empty outcome (no LLM request).
        _install_fake_translator(
            monkeypatch,
            "translate_to_aspic_rules",
            [],
            [],
        )
        _install_fake_handler(
            monkeypatch,
            "aspic_handler",
            "ASPICHandler",
            "analyze_aspic_framework",
            [],
            {"extensions": [["arg_2"]], "statistics": {}},
            takes_initializer=False,
        )

        result = await ic._invoke_aspic(_UNIT_1, context)
        from unittest.mock import patch as _patch

        with _patch(
            "argumentation_analysis.orchestration.state_writers._record_structured_arg_status"
        ):
            _write_aspic_to_state(result, state, {})

        entry = state.aspic_results[-1]
        assert entry.get("argument_labels") == _LABELS
        assert entry["reasoner_type"]


# --------------------------------------------------------------------------
# Batch 2c — belief revision and dialogue join the population nodes
# --------------------------------------------------------------------------


class TestBeliefRevisionNodesAreUnits:
    async def test_the_base_and_options_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The belief base is the population: the handler's atoms and the
        retraction options name ``arg_N`` (joinable), never a truncated
        extraction text; the texts travel as ``argument_labels``."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # One fallacy on arg_1: the base gains the real clash whose minimal
        # retraction the reader names (#1646) — now over the unit ids.
        context["phase_hierarchical_fallacy_output"] = {
            "fallacies": [{"type": "ad_hominem", "target_argument": "arg_1"}]
        }
        received: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "belief_revision_handler",
            "BeliefRevisionHandler",
            "revise",
            received,
            lambda belief_set, new_belief, method: {
                "method": method,
                "original": list(belief_set),
                "revised": sorted(belief_set),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_belief_revision(_UNIT_1, context)

        # The handler's belief atoms ARE the unit ids (valid PL atoms).
        assert received[0]["args"][0] == ["arg_1", "arg_2"]
        assert result["original"] == ["arg_1", "arg_2"]
        # The retraction options name the clashing unit and its negation.
        flat = {
            label for opt in result["minimal_retraction"]["options"] for label in opt
        }
        assert any(label == "arg_1" for label in flat)
        assert any(label == "¬arg_1" for label in flat)
        assert result.get("argument_labels") == _LABELS

    async def test_a_caller_belief_set_joins_the_units(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A caller ``belief_set`` entry that names a unit by its text
        resolves to the unit's id (the historical caller seam, joined); a
        free-text belief stays a sanitized atom, never a unit."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["belief_set"] = [_UNIT_1, "croyance libre hors population"]
        received: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "belief_revision_handler",
            "BeliefRevisionHandler",
            "revise",
            received,
            lambda belief_set, new_belief, method: {
                "method": method,
                "original": list(belief_set),
                "revised": [],
                "statistics": {},
            },
            takes_initializer=False,
        )

        await ic._invoke_belief_revision(_UNIT_1, context)

        atoms = received[0]["args"][0]
        # The unit-named belief resolves to its id and passes through
        # verbatim (never a prefixed, hashed atom).
        assert atoms[0] == "arg_1"
        # The free-text belief stays a belief: a sanitized PL atom, no unit.
        assert atoms[1] != "croyance libre hors population"
        assert " " not in atoms[1]
        assert atoms[1] != "arg_1" and atoms[1] != "arg_2"

    async def test_the_honest_absent_echo_still_joins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The JVM-down degraded return carries the node identity fields too —
        every return site, degraded or not, is joinable (#3009 parity)."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["phase_hierarchical_fallacy_output"] = {
            "fallacies": [{"type": "ad_hominem", "target_argument": "arg_1"}]
        }
        # Pin "not started" on the home module so the honest-absent branch
        # fires regardless of the conftest session JVM, then make the
        # handler's own import raise via None in sys.modules.
        import argumentation_analysis.core.jvm_setup as jvm_setup

        monkeypatch.setattr(jvm_setup, "is_jvm_started", lambda: False)
        monkeypatch.setitem(
            sys.modules,
            "argumentation_analysis.agents.core.logic.belief_revision_handler",
            None,
        )

        result = await ic._invoke_belief_revision(_UNIT_1, context)

        assert result.get("degraded") is True
        assert result["original"] == ["arg_1", "arg_2"]
        assert result.get("argument_labels") == _LABELS
        # The JVM-free insight still names the units on the degraded path.
        flat = {
            label for opt in result["minimal_retraction"]["options"] for label in opt
        }
        assert any(label == "arg_1" for label in flat)

    def test_the_writer_curates_labels(self) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        output = {
            "method": "dalal",
            "original": ["arg_1", "arg_2"],
            "revised": ["arg_1"],
            "minimal_retraction": {"cardinality": 1, "options": [["arg_1"]]},
            "argument_labels": dict(_LABELS),
        }

        _write_belief_revision_to_state(output, state, {})

        entry = state.belief_revision_results[-1]
        assert entry["original"] == ["arg_1", "arg_2"]
        assert entry.get("argument_labels") == _LABELS
        assert entry["minimal_retraction"]["options"] == [["arg_1"]]

    def test_the_reader_renders_the_units_text(self) -> None:
        """The Act III reader resolves an id-keyed option through the entry's
        labels — the prose names the belief's TEXT (and the negation's text),
        never a bare id."""
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _belief_revision_finding,
        )

        state = SimpleNamespace(
            belief_revision_results=[
                {
                    "minimal_retraction": {
                        "cardinality": 1,
                        "options": [["arg_1"], ["¬arg_1"]],
                        "base_size": 3,
                        "touched_count": 2,
                        "degraded": False,
                    },
                    "argument_labels": dict(_LABELS),
                }
            ]
        )

        finding = _belief_revision_finding(state)

        assert finding is not None
        assert "Première thèse" in finding.statement
        # The negation clause renders the negated unit's text too.
        assert "¬Première thèse" in finding.statement
        assert "arg_1" not in finding.statement


class TestDialogueNodesAreUnits:
    async def test_the_positions_and_edges_are_id_keyed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The proponent's position is the population's unit ids; the
        opponent's counter stays a text (it is not a unit); every edge
        endpoint resolves to its id when it names a unit, and a topic naming
        a unit resolves too — the membership check that decides ``accepted``
        keeps its meaning across the keying change."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        ca_text = "Contre-argument synthétique visant la première thèse du corpus."
        context["phase_counter_output"] = {
            "llm_counter_arguments": [
                {"counter_argument": ca_text, "target_unit_id": "arg_1"}
            ]
        }
        context["phase_hierarchical_fallacy_output"] = {
            "fallacies": [{"type": "ad_hominem", "target_argument": "arg_1"}]
        }
        context["topic"] = _UNIT_1
        received: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "dialogue_handler",
            "DialogueHandler",
            "execute_dialogue",
            received,
            lambda pro, pro_atk, opp, opp_atk, topic: {
                "topic": topic,
                "outcome": "accepted",
                "dialogue_trace": [],
                "merged_framework": {
                    "arguments": sorted(set(pro) | set(opp)),
                    "attacks": [list(a) for a in pro_atk + opp_atk],
                },
            },
            takes_initializer=False,
        )

        result = await ic._invoke_dialogue(_UNIT_1, context)

        pro, pro_atk, opp, opp_atk, topic = received[0]["args"]
        # The proponent's position = the population units; the opponent's
        # counter stays a text (a dialogue member no unit exists for).
        assert pro == ["arg_1", "arg_2"]
        assert opp == [ca_text]
        # The fallacy edge targets the unit's id; the counter-derived edge
        # keeps its "CA:" pseudo-source and targets the id — both exactly as
        # the dialogue's lists carry them (the handler's membership filter).
        assert pro_atk == [
            ["fallacy_0_ad_hominem", "arg_1"],
            [f"CA: {ca_text[:50]}", "arg_1"],
        ]
        # An opponent edge names BOTH endpoints exactly as the lists carry
        # them (#2968): the counter text attacking the unit's id.
        assert opp_atk == [[ca_text, "arg_1"]]
        assert topic == "arg_1"
        assert result.get("argument_labels") == _LABELS
        assert result["merged_framework"]["attacks"] == [
            ["fallacy_0_ad_hominem", "arg_1"],
            [f"CA: {ca_text[:50]}", "arg_1"],
            [ca_text, "arg_1"],
        ]

    async def test_the_split_halves_are_ids(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without counters the population splits in halves — both positions
        are unit ids."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        received: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "dialogue_handler",
            "DialogueHandler",
            "execute_dialogue",
            received,
            lambda pro, pro_atk, opp, opp_atk, topic: {
                "topic": topic,
                "outcome": "rejected",
                "dialogue_trace": [],
            },
            takes_initializer=False,
        )

        result = await ic._invoke_dialogue(_UNIT_1, context)

        pro, _, opp, _, _ = received[0]["args"]
        assert pro == ["arg_1"]
        assert opp == ["arg_2"]
        assert result.get("argument_labels") == _LABELS

    def test_the_writer_curates_labels(self) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        output = {
            "topic": "arg_1",
            "outcome": "accepted",
            "dialogue_trace": [
                {
                    "round": 1,
                    "speaker": "proponent",
                    "action": "assert",
                    "argument": "arg_1",
                }
            ],
            "argument_labels": dict(_LABELS),
        }

        _write_dialogue_to_state(output, state, {})

        entry = state.dialogue_results[-1]
        assert entry["topic"] == "arg_1"
        assert entry.get("argument_labels") == _LABELS
        assert entry["trace"][0]["argument"] == "arg_1"


# --------------------------------------------------------------------------
# #3014 follow-up (R1085 review item 3) — a dropped endpoint is counted
# --------------------------------------------------------------------------


class TestDroppedUnresolvedIsCounted:
    """A name the family join cannot resolve is COUNTED, never silent.

    Before the follow-up, every translation site dropped unresolved names
    BEFORE the #1698 retention accounting, with no count anywhere: edges,
    joint-attack targets and attackers, weighted triple endpoints, vote
    keys, EAF belief members, probability keys — and the same-class key
    drops of ABA (assumptions, rule heads and bodies, contrary keys) and
    ADF (statements, condition keys). A caller ``probabilities`` dict whose
    keys all failed to resolve became ``{}`` with no way to tell it apart
    from "no keys given". Every family member now reports
    ``dropped_unresolved`` in its payload — 0 when nothing was dropped.
    """

    async def test_an_edge_endpoint_that_joins_nothing_is_counted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        # One caller edge names a non-member: a half-resolved edge enters no
        # frame, and the failed endpoint is counted — never dropped silently.
        context["attacks"] = [[_UNIT_1, "Texte non membre"]]
        context["probabilities"] = {_UNIT_1: 0.9}
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_handler(
            monkeypatch,
            "probabilistic_handler",
            "ProbabilisticHandler",
            "analyze_probabilistic_framework",
            handler_seen,
            lambda args, attacks, probs: {
                "acceptance_probabilities": dict(probs),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_probabilistic(_UNIT_1, context)

        _args, attacks, _probs = handler_seen[0]["args"]
        assert [list(a) for a in attacks] == []
        assert result["dropped_unresolved"] == 1

    async def test_nothing_dropped_reports_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["attacks"] = [[_UNIT_1, _UNIT_2]]
        context["probabilities"] = {_UNIT_1: 0.9}
        _install_fake_derivation(monkeypatch, [])
        _install_fake_handler(
            monkeypatch,
            "probabilistic_handler",
            "ProbabilisticHandler",
            "analyze_probabilistic_framework",
            [],
            lambda args, attacks, probs: {
                "acceptance_probabilities": dict(probs),
                "statistics": {},
            },
            takes_initializer=False,
        )

        result = await ic._invoke_probabilistic(_UNIT_1, context)

        assert result["dropped_unresolved"] == 0

    async def test_probability_keys_that_all_join_nothing_stay_distinguishable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All keys unresolved → the handler gets ``{}`` (NOT the 0.5 default)
        and the payload says how many — versus "no keys given", which defaults
        and counts 0. The two outcomes never merge again."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        context["probabilities"] = {"Premier non-membre": 0.9, "Second non-membre": 0.8}
        handler_seen: List[Dict[str, Any]] = []
        _install_fake_derivation(monkeypatch, [])
        _install_fake_handler(
            monkeypatch,
            "probabilistic_handler",
            "ProbabilisticHandler",
            "analyze_probabilistic_framework",
            handler_seen,
            lambda args, attacks, probs: {
                "acceptance_probabilities": dict(probs),
                "statistics": {},
            },
            takes_initializer=False,
        )

        all_dropped = await ic._invoke_probabilistic(_UNIT_1, context)
        _args, _attacks, probs = handler_seen[0]["args"]
        # The empty table after resolution is NOT the default baseline.
        assert probs == {}
        assert all_dropped["acceptance_probabilities"] == {}
        assert all_dropped["dropped_unresolved"] == 2

        # The same callable with NO keys given: the honest 0.5 default over
        # the ids, and a zero count — a reader can tell the two apart.
        context.pop("probabilities")
        defaulted = await ic._invoke_probabilistic(_UNIT_1, context)
        assert defaulted["acceptance_probabilities"] == {"arg_1": 0.5, "arg_2": 0.5}
        assert defaulted["dropped_unresolved"] == 0

    @pytest.mark.parametrize(
        "member",
        [
            "ranking",
            "bipolar",
            "aba",
            "adf",
            "probabilistic",
            "setaf",
            "weighted",
            "social",
            "eaf",
            "dung",
        ],
    )
    async def test_every_family_member_reports_the_count(
        self, monkeypatch: pytest.MonkeyPatch, member: str
    ) -> None:
        """All-resolvable inputs: each member's payload carries the count, 0.

        The census of the follow-up: a member missing the key reddens here
        (a site added later with a silent drop cannot reappear unnoticed)."""
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        if member == "ranking":
            context["attacks"] = [[_UNIT_1, _UNIT_2]]
            _install_fake_handler(
                monkeypatch,
                "ranking_handler",
                "RankingHandler",
                "rank_arguments",
                [],
                {"ranking": ["arg_1", "arg_2"], "scores": {"arg_1": 1, "arg_2": 2}},
                takes_initializer=False,
            )
            result = await ic._invoke_ranking(_UNIT_1, context)
        elif member == "bipolar":
            context["attacks"] = [[_UNIT_2, _UNIT_1]]
            context["supports"] = [[_UNIT_1, _UNIT_2]]
            _install_fake_handler(
                monkeypatch,
                "bipolar_handler",
                "BipolarHandler",
                "analyze_bipolar_framework",
                [],
                lambda args, attacks, supports, fw_type: {
                    "extensions": [["arg_1"]],
                    "statistics": {},
                },
                takes_initializer=False,
            )
            result = await ic._invoke_bipolar(_UNIT_1, context)
        elif member == "aba":
            _install_fake_translator(
                monkeypatch,
                "translate_to_aba_contraries",
                {_UNIT_1: "Sentence contraire synthétique."},
                [],
            )
            _install_fake_handler(
                monkeypatch,
                "aba_handler",
                "ABAHandler",
                "analyze_aba_framework",
                [],
                {"extensions": [["arg_1"]], "statistics": {}},
                takes_initializer=False,
            )
            result = await ic._invoke_aba(_UNIT_1, context)
        elif member == "adf":
            _install_fake_handler(
                monkeypatch,
                "adf_handler",
                "ADFHandler",
                "analyze_adf",
                [],
                {"interpretations": [], "statistics": {}},
                takes_initializer=False,
            )
            result = await ic._invoke_adf(_UNIT_1, context)
        elif member == "probabilistic":
            context["probabilities"] = {_UNIT_1: 0.9}
            _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
            _install_fake_handler(
                monkeypatch,
                "probabilistic_handler",
                "ProbabilisticHandler",
                "analyze_probabilistic_framework",
                [],
                lambda args, attacks, probs: {
                    "acceptance_probabilities": dict(probs),
                    "statistics": {},
                },
                takes_initializer=False,
            )
            result = await ic._invoke_probabilistic(_UNIT_1, context)
        elif member == "setaf":
            context["set_attacks"] = [{"attackers": [_UNIT_1], "target": _UNIT_2}]
            _install_fake_handler(
                monkeypatch,
                "setaf_handler",
                "SetAFHandler",
                "analyze_setaf",
                [],
                {"extensions": [["arg_2"]], "statistics": {}},
            )
            result = await ic._invoke_setaf(_UNIT_1, context)
        elif member == "weighted":
            context["weighted_attacks"] = [[_UNIT_1, _UNIT_2, 0.7]]
            _install_fake_handler(
                monkeypatch,
                "weighted_handler",
                "WeightedHandler",
                "analyze_weighted_framework",
                [],
                {"extensions": [["arg_2"]], "statistics": {}},
            )
            result = await ic._invoke_weighted(_UNIT_1, context)
        elif member == "social":
            context["votes"] = {_UNIT_1: [1, 2]}
            _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
            _install_fake_handler(
                monkeypatch,
                "social_handler",
                "SocialHandler",
                "analyze_social_framework",
                [],
                {"ranking": ["arg_2", "arg_1"], "scores": {"arg_2": 2, "arg_1": 1}},
            )
            result = await ic._invoke_social(_UNIT_1, context)
        elif member == "eaf":
            context["epistemic_beliefs"] = {"agent_a": [_UNIT_1], "agent_b": [_UNIT_2]}
            _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
            _install_fake_handler(
                monkeypatch,
                "eaf_handler",
                "EAFHandler",
                "analyze_epistemic_framework",
                [],
                lambda args, attacks, beliefs, semantics: {
                    "extensions": [["arg_2"]],
                    "epistemic_beliefs": {a: list(v) for a, v in beliefs.items()},
                },
            )
            result = await ic._invoke_eaf(_UNIT_1, context)
        else:
            assert member == "dung"
            _install_fake_derivation(monkeypatch, [[_UNIT_1, _UNIT_2]])
            _install_fake_handler(
                monkeypatch,
                "af_handler",
                "AFHandler",
                "analyze_multi_semantics",
                [],
                {"extensions": {"grounded": [["arg_2"]]}, "statistics": {}},
            )
            result = await ic._invoke_dung_extensions(_UNIT_1, context)

        assert result.get("dropped_unresolved") == 0, member
        # #3014 body item 2: the same census holds the pre-cap population
        # total — a member that stops carrying it loses the "40 of 94" line.
        assert result.get("population_total") == 2, member


class TestPopulationTotalIsThePreCapCount:
    """#3014 body item 2 — the 40-node budget cap is NAMED, never silent.

    ``_population_node_units`` returns ``units[:40]`` (budget parity with the
    historical extraction) and, beside it, the size of the population BEFORE
    the cap: a 94-unit state yields a 40-node frame whose payload says 94 —
    the reader can say « 40 retenus sur 94 », pre-fix it could only say 40.
    """

    def test_the_builder_returns_the_pre_cap_total(self) -> None:
        state = _RecordingState(
            identified_arguments={
                f"arg_{i + 1}": (
                    f"Unité argumentative synthétique numéro {i + 1}, assez "
                    "longue pour ressembler à un vrai argument extrait."
                )
                for i in range(45)
            }
        )
        context = _measured_context(state)
        pairs, no_id_reason, total = ic._population_node_units(_UNIT_1, context)
        assert no_id_reason is None
        assert len(pairs) == 40, "the frame keeps its 40-node budget cap"
        assert total == 45, "the payload names what the cap cut"

    def test_a_frame_under_the_cap_reports_its_own_size(self) -> None:
        # Below the cap the total equals the frame size — the reader's
        # « N sur M » collapses honestly to the plain frame.
        state = _RecordingState(
            identified_arguments={"arg_1": _UNIT_1, "arg_2": _UNIT_2}
        )
        context = _measured_context(state)
        pairs, no_id_reason, total = ic._population_node_units(_UNIT_1, context)
        assert no_id_reason is None
        assert len(pairs) == 2
        assert total == 2

    def test_the_caller_seam_population_also_names_its_total(self) -> None:
        # The ``context["arguments"]`` fallback (no state population, no
        # extract output) mints positional ids — its total is the caller
        # list's size, not the capped frame's.
        context: Dict[str, Any] = {
            "arguments": [_UNIT_1, _UNIT_2],
        }
        node_ids, _labels, _by_label, payload = ic._af_family_frame(_UNIT_1, context)
        assert len(node_ids) == 2
        assert payload["population_total"] == 2

    def test_a_45_unit_caller_seam_names_45(self) -> None:
        context: Dict[str, Any] = {
            "arguments": [
                f"Argument synthétique fourni par l'appelant numéro {i}."
                for i in range(45)
            ],
        }
        node_ids, _labels, _by_label, payload = ic._af_family_frame(_UNIT_1, context)
        assert len(node_ids) == 40
        assert payload["population_total"] == 45
