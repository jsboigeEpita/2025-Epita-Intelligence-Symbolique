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
    _write_bipolar_to_state,
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
        self.traces: List[str] = []

    def add_dung_framework(
        self,
        name: str,
        arguments: List[str],
        attacks: List[Any],
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

    # The batch-2a sinks mirror the same contract: accept the pre-#3014
    # positional call AND the labelled one, so the witness runs red on the
    # old tree by ASSERTION, not by TypeError.
    def _curated(
        self, base: Dict[str, Any], argument_labels: Any, reason: Any
    ) -> Dict[str, Any]:
        if argument_labels is not None:
            base["argument_labels"] = argument_labels
        if reason is not None:
            base["argument_ids_absent_reason"] = reason
        return base

    def add_ranking_result(
        self,
        method: str,
        arguments: List[str],
        comparisons: List[Dict[str, Any]],
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
    ) -> str:
        entry = self._curated(
            {"method": method, "arguments": arguments, "comparisons": comparisons},
            argument_labels,
            argument_ids_absent_reason,
        )
        self.ranking_results.append(entry)
        return f"rank_{len(self.ranking_results)}"

    def add_probabilistic_result(
        self,
        arguments: List[str],
        acceptance_probs: Dict[str, float],
        argument_labels: Optional[Dict[str, str]] = None,
        argument_ids_absent_reason: Optional[str] = None,
    ) -> str:
        entry = self._curated(
            {"arguments": arguments, "acceptance_probabilities": acceptance_probs},
            argument_labels,
            argument_ids_absent_reason,
        )
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
        )
        self.bipolar_results.append(entry)
        return f"bipolar_{len(self.bipolar_results)}"

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
    and record the inventory it was fed (the seam keeps reading TEXTS)."""
    import argumentation_analysis.orchestration.structured_arg_translator as sat

    async def _fake(text: str, arguments: List[str]) -> Any:
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
