"""#2672 — the readers of ``dung_frameworks`` find the Dung framework behind the sidecars.

``state.dung_frameworks`` holds every formalism. On a pipeline run its first
entry is DeLP's sidecar (``delp_analysis``, no arguments), and the native Dung
verification is filed as one ``verification_{sem}`` entry per semantics whose
``extensions`` is ``{"extensions": [[...]], "count", "sizes", "all_members"}``.

Four readers took the first entry and read ``extensions["grounded"]``: section
5 of the deep synthesis, its artifact briefing and its prompt, the CLI, and the
pattern-mining topology detector. Measured on 9 local run states out of 9, section 5
printed "No Dung framework computed" next to a native framework of 6 to 14
arguments.

The states here are built by the real writers from the real enrichment of
``_invoke_dung_extensions``; only the reasoner call (``analyze_multi_semantics``)
and the attack derivation are stubbed. The conversational shape
(``conversational_dung``, ``{"grounded": [...]}``), which section 5 read correctly
before, is the control.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    DeepSynthesisReport,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.pattern_mining import DungTopologyDetector
from argumentation_analysis.orchestration.state_writers import (
    _write_aba_to_state,
    _write_delp_to_state,
    _write_dung_extensions_to_state,
)

pytestmark = pytest.mark.usefixtures("dung_attacks_offline")

ARGS = ["arg_1", "arg_2", "arg_3", "arg_4"]
# arg_1 and arg_2 attack each other, arg_2 attacks arg_3, arg_4 is unattacked.
ATTACKS = [["arg_1", "arg_2"], ["arg_2", "arg_1"], ["arg_2", "arg_3"]]
GROUNDED = [["arg_4"]]
PREFERRED = [["arg_1", "arg_3", "arg_4"], ["arg_2", "arg_4"]]
REASONER = {"grounded": GROUNDED, "preferred": PREFERRED, "stable": PREFERRED}


def _fake_module(name: str, **attrs: Any) -> types.ModuleType:
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


@pytest.fixture
def reasoner(monkeypatch):
    """Stub the JVM boundary only: the enrichment and the writer run for real."""

    class _Initializer:
        pass

    class _AFHandler:
        def __init__(self, initializer: Any) -> None:
            pass

        def analyze_multi_semantics(self, arguments, attacks, semantics):
            return {"extensions": {sem: REASONER[sem] for sem in semantics}}

    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.tweety_initializer",
        _fake_module(
            "argumentation_analysis.agents.core.logic.tweety_initializer",
            ready_initializer=lambda: _Initializer(),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.af_handler",
        _fake_module(
            "argumentation_analysis.agents.core.logic.af_handler",
            AFHandler=_AFHandler,
            SEMANTICS_REASONERS={sem: None for sem in REASONER},
        ),
    )


def _write_delp(state: UnifiedAnalysisState) -> None:
    _write_delp_to_state(
        {
            "query_results": [{"query": "q", "answer": "YES"}],
            "program": "q <- p.",
            "program_size": 1,
            "criterion": "generalized_specificity",
        },
        state,
        {},
    )


async def _pipeline_state(dung_attacks_offline) -> UnifiedAnalysisState:
    """DeLP first, then the Dung verification, then an ABA sidecar.

    The order of the 11 local run states that carry ``dung_frameworks``: DeLP's
    sidecar is the first entry in all 11.
    """
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_dung_extensions,
    )

    dung_attacks_offline.return_value = [list(a) for a in ATTACKS]
    state = UnifiedAnalysisState("A short discourse.")
    _write_delp(state)
    output = await _invoke_dung_extensions(
        "A short discourse.", {"phase_extract_output": {"arguments": list(ARGS)}}
    )
    _write_dung_extensions_to_state(output, state, {})
    _write_aba_to_state(
        {
            "semantics": "preferred",
            "assumptions": ["a1", "a2"],
            "extensions": [["a1"]],
        },
        state,
        {},
    )
    return state


def _uncomputed_state() -> UnifiedAnalysisState:
    """The reasoner timed out: the writer files ``verification_unavailable``."""
    state = UnifiedAnalysisState("A short discourse.")
    _write_delp(state)
    _write_dung_extensions_to_state(
        {
            "degraded": True,
            "semantics": "unavailable",
            "extensions": {},
            "arguments": list(ARGS),
            "attacks": [list(a) for a in ATTACKS],
        },
        state,
        {},
    )
    return state


def _conversational_state() -> UnifiedAnalysisState:
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        _build_dung_framework_from_state,
    )

    state = UnifiedAnalysisState("A short discourse.")
    first = state.add_argument("First claim")
    state.add_argument("Second claim")
    state.add_fallacy("ad hominem", "attacks the person", first)
    assert _build_dung_framework_from_state(state) is not None
    return state


async def _prompt_for(state: UnifiedAnalysisState) -> str:
    kernel = create_autospec(Kernel, instance=True)
    kernel.get_prompt_execution_settings_from_service_id = MagicMock(
        return_value=MagicMock()
    )
    capture = AsyncMock(return_value="## 1. C\n## 6. L")
    kernel.invoke_prompt = capture
    report = DeepSynthesisReport()
    report.dung_structure = DeepSynthesisAgent._build_dung_structure(state)
    stub = SimpleNamespace(_llm_service_id="default", kernel=kernel)
    await DeepSynthesisAgent._llm_synthesis(stub, report)
    return capture.call_args[1]["prompt"]


def _grounded_line(prompt: str) -> str:
    line = next(
        line for line in prompt.splitlines() if "Dung grounded extension" in line
    )
    return line[line.index("Dung grounded extension") :]


def _cli_lines(state: UnifiedAnalysisState) -> List[str]:
    from argumentation_analysis.cli.output_formatter import _render_dung

    console = MagicMock()
    _render_dung(console, {"dung_frameworks": state.dung_frameworks})
    return [str(c.args[0]) for c in console.print.call_args_list]


class TestPipelineState:
    """Born red: every reader took ``delp_analysis`` (0 arguments)."""

    async def test_section5_reads_the_native_framework(
        self, reasoner, dung_attacks_offline
    ):
        ds = DeepSynthesisAgent._build_dung_structure(
            await _pipeline_state(dung_attacks_offline)
        )
        assert ds.framework_name == "verification_preferred"
        assert ds.arguments == ARGS
        assert sorted(map(tuple, ds.attacks)) == sorted(map(tuple, ATTACKS))
        assert ds.grounded_extension == ["arg_4"]
        assert ds.preferred_extensions == PREFERRED
        assert ds.stable_extensions == PREFERRED
        assert {"grounded", "preferred", "stable"} <= set(ds.computed_semantics)

    async def test_section5_markdown_shows_it(self, reasoner, dung_attacks_offline):
        report = DeepSynthesisReport()
        report.dung_structure = DeepSynthesisAgent._build_dung_structure(
            await _pipeline_state(dung_attacks_offline)
        )
        md = DeepSynthesisAgent.render_markdown(report)
        assert "No Dung framework computed" not in md
        assert "**Framework**: verification_preferred (4 arguments, 3 attacks)" in md
        assert "**Grounded extension**: `arg_4`" in md

    async def test_prompt_carries_the_computed_grounded_extension(
        self, reasoner, dung_attacks_offline
    ):
        prompt = await _prompt_for(await _pipeline_state(dung_attacks_offline))
        assert _grounded_line(prompt).strip() == "Dung grounded extension: arg_4."

    async def test_briefing_names_extensions_only_where_computed(
        self, reasoner, dung_attacks_offline
    ):
        state = await _pipeline_state(dung_attacks_offline)
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        by_name = {
            line.split("name=")[1].split()[0]: line
            for line in briefing.splitlines()
            if "[artifact:dung_frameworks." in line
        }
        assert "grounded_extensions=[['arg_4']]" in by_name["verification_grounded"]
        # A sidecar's own keys are not Dung extensions, and DeLP's sidecar
        # never computed a grounded extension.
        assert "_extensions=" not in by_name["delp_analysis"]
        assert "_extensions=" not in by_name["aba_preferred"]

    async def test_cli_prints_the_native_grounded_extension(
        self, reasoner, dung_attacks_offline
    ):
        lines = _cli_lines(await _pipeline_state(dung_attacks_offline))
        assert "  verification_preferred: grounded={arg_4}" in lines

    async def test_topology_reads_the_native_framework(
        self, reasoner, dung_attacks_offline
    ):
        state = await _pipeline_state(dung_attacks_offline)
        topo = DungTopologyDetector().detect(
            {"state": {"dung_frameworks": state.dung_frameworks}}
        )
        assert topo["n_args"] == 4.0
        assert topo["n_attacks"] == 3.0
        # grounded (1) + preferred (2) + stable (2); ``sizes`` and
        # ``all_members`` are not extensions.
        assert topo["n_extensions"] == 5.0
        assert topo["max_extension_size"] == 3.0


class TestUncomputedExtensions:
    """A framework whose extensions were never computed says so."""

    def test_section5_says_nothing_was_computed(self):
        ds = DeepSynthesisAgent._build_dung_structure(_uncomputed_state())
        assert ds.framework_name == "verification_unavailable"
        assert len(ds.arguments) == 4
        assert ds.computed_semantics == []
        assert ds.grounded_extension == []
        assert "No extension was computed" in ds.interpretation

    async def test_prompt_says_not_computed_rather_than_none(self):
        prompt = await _prompt_for(_uncomputed_state())
        assert (
            _grounded_line(prompt).strip() == "Dung grounded extension: not computed."
        )

    def test_cli_says_not_computed(self):
        lines = _cli_lines(_uncomputed_state())
        assert "  verification_unavailable: grounded extension not computed" in lines


class TestSidecarsOnly:
    """A state holding only formalism sidecars has no Dung framework."""

    def _state(self) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState("A short discourse.")
        _write_delp(state)
        _write_aba_to_state(
            {"semantics": "preferred", "assumptions": ["a1"], "extensions": [["a1"]]},
            state,
            {},
        )
        return state

    def test_section5_is_empty(self):
        ds = DeepSynthesisAgent._build_dung_structure(self._state())
        assert ds.arguments == [] and ds.framework_name == ""

    def test_cli_says_sidecars_only(self):
        assert any("sidecars only" in line for line in _cli_lines(self._state()))

    def test_topology_is_zero(self):
        topo = DungTopologyDetector().detect(
            {"state": {"dung_frameworks": self._state().dung_frameworks}}
        )
        assert topo["n_args"] == 0.0 and topo["n_extensions"] == 0.0


class TestDeclaredFrameControl:
    """Control: a framework an agent declared without extensions.

    ``StateManagerPlugin.add_dung_framework`` makes ``extensions_json``
    optional. Main showed such a frame in section 5 (it was the first entry);
    it still does, and now says its extensions were not computed.
    """

    def _state(self) -> UnifiedAnalysisState:
        from argumentation_analysis.core.state_manager_plugin import (
            StateManagerPlugin,
        )

        state = UnifiedAnalysisState("A short discourse.")
        StateManagerPlugin(state).add_dung_framework(
            name="agent_framework",
            arguments_json='["arg_1", "arg_2"]',
            attacks_json='[["arg_1", "arg_2"]]',
        )
        return state

    def test_section5(self):
        ds = DeepSynthesisAgent._build_dung_structure(self._state())
        assert ds.framework_name == "agent_framework"
        assert ds.arguments == ["arg_1", "arg_2"]
        assert ds.attacks == [["arg_1", "arg_2"]]

    def test_section5_says_nothing_was_computed(self):
        ds = DeepSynthesisAgent._build_dung_structure(self._state())
        assert ds.computed_semantics == []
        assert "No extension was computed" in ds.interpretation


class TestConversationalShapeControl:
    """Control: the shape section 5 already read correctly reads the same.

    Green on main and after the repair; it asserts only what main produced.
    """

    def test_section5(self):
        state = _conversational_state()
        (fw,) = state.dung_frameworks.values()
        ds = DeepSynthesisAgent._build_dung_structure(state)
        assert ds.framework_name == "conversational_dung"
        assert ds.arguments == fw["arguments"]
        assert ds.attacks == fw["attacks"]
        assert ds.grounded_extension == fw["extensions"]["grounded"] != []

    def test_cli(self):
        state = _conversational_state()
        (fw,) = state.dung_frameworks.values()
        members = ", ".join(fw["extensions"]["grounded"])
        assert any(
            line.endswith(f": grounded={{{members}}}") for line in _cli_lines(state)
        )

    def test_computed_semantics_names_it(self):
        ds = DeepSynthesisAgent._build_dung_structure(_conversational_state())
        assert ds.computed_semantics == ["grounded"]
