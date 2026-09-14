"""Guards for #2145 — the plugin mount path stops being blind and silent.

Three contracts, one per dimension of the dispatch:

1. a declared plugin that does not reach the agent is reported, never a
   `debug` line nobody reads. The pristine tree carries **seven** silences,
   measured, not assumed: six amputations logged at `debug` (shared state ×2,
   failed instantiation ×2, `fallacy_workflow` missing its `llm_service` ×2),
   plus a seventh that was not even logged — `get_plugin_instances` did a bare
   `continue` on a declared name with no registry entry, where its twin
   `load_plugins_for_agent` already warned. The same failure was loud on one
   mount path and invisible on the other;
2. homonym `@kernel_function` names among the plugins mounted for one
   speciality are detected and reported — the agent sees two tools with the
   same leaf name and nothing marks the canonical one;
3. the plugin whose body raises is mounted nowhere — detected by the
   *identity* of its callables, never by its name, which any alias defeats —
   and the day the body lands the guard reddens and forces the re-mount
   decision.

Instrument discipline: a detector that returns nothing has not proved
anything, so every zero here is paired with a positive control.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.factory import (
    AGENT_SPECIALITY_MAP,
    _PLUGIN_REGISTRY,
    _function_collisions,
    get_plugin_instances,
    load_plugins_for_agent,
)
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import (
    SemanticArgumentAnalyzer,
)
from argumentation_analysis.plugins.toulmin_plugin import ToulminPlugin

FACTORY_LOGGER = "AgentFactory"

# ---------------------------------------------------------------------------
# Dimension 2 — the collision surface, measured
#
# Pinned as *named debt* (#2145), not as a contract anyone wants: each pair is
# two real implementations mounted side by side for the same agent, and both
# sides are pinned by tests, so neither can simply be deleted. This map reddens
# in both directions — a NEW collision appearing, and a listed one disappearing
# (a stale entry must not survive the fix that removes it).
# ---------------------------------------------------------------------------

EXPECTED_COLLISIONS = {
    "formal_logic": {
        "analyze_aspic": ["aspic", "tweety_logic"],
        "check_fol_consistency": ["logic_agents", "tweety_logic"],
        "rank_arguments": ["ranking", "tweety_logic"],
        "revise_beliefs": ["belief_revision", "tweety_logic"],
    },
    # The issue recensed four pairs "reunited by formal_logic". There is a
    # fifth: `watson` mounts tweety_logic + logic_agents together
    # (`factory.py`, AGENT_SPECIALITY_MAP) and collides on the same name.
    "watson": {
        "check_fol_consistency": ["logic_agents", "tweety_logic"],
    },
}


def _mounted_functions(speciality: str) -> dict[str, list[str]]:
    """Plugin name → function names, as a real kernel ends up holding them."""
    kernel = Kernel()
    load_plugins_for_agent(kernel, speciality)
    return {
        name: list(plugin.functions.keys()) for name, plugin in kernel.plugins.items()
    }


def test_collision_detector_is_not_blind():
    """Positive and negative control: the detector must be able to say both."""
    collided = _function_collisions(
        {"plugin_a": ["shared_name"], "plugin_b": ["shared_name", "lonely"]}
    )
    assert collided == [("shared_name", ["plugin_a", "plugin_b"])]

    clean = _function_collisions({"plugin_a": ["one"], "plugin_b": ["other"]})
    assert clean == [], "the negative control must be empty, not merely unchecked"

    single = _function_collisions({})
    assert single == []


def test_known_collisions_are_enumerated_2145():
    """The whole mount surface, pinned: no silent new collision, no stale entry."""
    measured: dict[str, dict[str, list[str]]] = {}
    for speciality in AGENT_SPECIALITY_MAP:
        found = dict(_function_collisions(_mounted_functions(speciality)))
        if found:
            measured[speciality] = found

    assert measured == EXPECTED_COLLISIONS, (
        "The homonym surface moved. A new collision must be arbitrated, not "
        "absorbed; a listed pair that disappeared means this map is stale and "
        "must shrink by hand (#2145)."
    )


def test_collisions_are_reported_loudly_2145(caplog):
    """A collision is not enough to exist — it must be said at a visible level."""
    with caplog.at_level(logging.WARNING, logger=FACTORY_LOGGER):
        load_plugins_for_agent(Kernel(), "formal_logic")

    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert sum("analyze_aspic" in m for m in messages) == 1, messages
    assert any("aspic" in m and "tweety_logic" in m for m in messages), messages


# ---------------------------------------------------------------------------
# Dimension 1 — the factory stops swallowing
# ---------------------------------------------------------------------------


def test_broken_plugin_is_reported_not_swallowed_2145(caplog, monkeypatch):
    """Né-rouge: this was a `debug` line, so the amputation was invisible."""
    monkeypatch.setitem(
        _PLUGIN_REGISTRY,
        "probe_broken",
        ("argumentation_analysis.plugins.this_module_does_not_exist", "Nope"),
    )
    monkeypatch.setitem(AGENT_SPECIALITY_MAP, "probe_speciality", ["probe_broken"])

    with caplog.at_level(logging.WARNING, logger=FACTORY_LOGGER):
        loaded = load_plugins_for_agent(Kernel(), "probe_speciality")

    assert loaded == [], "the broken plugin must not be claimed as loaded"
    assert any(
        "probe_broken" in r.getMessage() and r.levelno >= logging.WARNING
        for r in caplog.records
    ), f"the amputation stayed silent: {[r.getMessage() for r in caplog.records]}"


def test_declared_name_without_registry_entry_is_reported_2145(caplog, monkeypatch):
    """The unlogged silence — the worst of the seven, because nothing was emitted.

    `get_plugin_instances` skipped an unmapped name with a bare `continue`.
    `load_plugins_for_agent` already warned for this exact case, so the same
    declaration failed loudly on one mount path and invisibly on the other.
    """
    monkeypatch.setitem(AGENT_SPECIALITY_MAP, "probe_undeclared", ["not_in_registry"])

    with caplog.at_level(logging.WARNING, logger=FACTORY_LOGGER):
        instances = get_plugin_instances("probe_undeclared")

    assert instances == []
    assert any(
        "not_in_registry" in r.getMessage() for r in caplog.records
    ), f"the unmapped name stayed silent: {[r.getMessage() for r in caplog.records]}"


def test_degraded_agent_is_reported_2145(caplog):
    """A skip by missing prerequisite is still an amputation, and says so."""
    with caplog.at_level(logging.WARNING, logger=FACTORY_LOGGER):
        loaded = load_plugins_for_agent(Kernel(), "informal_fallacy")

    assert "fallacy_workflow" not in loaded
    assert any(
        "fallacy_workflow" in r.getMessage() and r.levelno >= logging.WARNING
        for r in caplog.records
    ), f"the degraded agent stayed silent: {[r.getMessage() for r in caplog.records]}"


# ---------------------------------------------------------------------------
# Dimension 3 — Toulmin: the mount is coupled to the body
# ---------------------------------------------------------------------------


def _toulmin_body_raises() -> bool:
    """Execute the body — the authority on whether the tool can do anything."""
    plugin = ToulminPlugin()
    try:
        asyncio.run(plugin.analyze_argument("peu importe le texte"))
    except NotImplementedError:
        return True
    return False


def _raising_surface() -> tuple[set[Any], set[str]]:
    """(callables, leaf names) of the plugin whose body raises, derived by mounting it.

    Deriving beats spelling. The review's point is that a guard keyed on the
    literal `"Toulmin"` misses a re-mount under any other alias; reading the
    mounted plugin instead survives a different plugin name *and* a different
    function name. `KernelFunctionFromMethod` exposes its bound method
    publicly (`method`), so the callable itself is reachable — that identity
    is the authority, not a string.
    """
    kernel = Kernel()
    plugin = kernel.add_plugin(ToulminPlugin(), plugin_name="probe_raising_body")
    return _mounted_callables(kernel), set(plugin.functions)


def _mounted_callables(kernel: Kernel) -> set[Any]:
    """Every method-backed tool a kernel really holds (prompt tools hold none)."""
    mounted: set[Any] = set()
    for plugin in kernel.plugins.values():
        for function in plugin.functions.values():
            method = getattr(function, "method", None)
            if method is not None:
                mounted.add(getattr(method, "__func__", method))
    return mounted


def test_raising_tool_detector_sees_through_an_alias():
    """Control: the detector must catch the re-mount a name check let through.

    Measured on a throwaway kernel — this is exactly the gap the review named.
    The previous assertion read the plugin *name*, so mounting the same
    raising plugin as `toulmin_tool` (or any other alias) kept it green; the
    assertions below hold both halves at once: the alias really does hide the
    old name, and the widened detector sees the callable anyway.
    """
    raising, raising_names = _raising_surface()
    assert raising, "the probe found no callable — its zero would prove nothing"
    assert raising_names, "the probe found no function name"

    aliased = Kernel()
    aliased.add_plugin(ToulminPlugin(), plugin_name="toulmin_tool")
    assert "Toulmin" not in aliased.plugins, (
        "the control is only meaningful while the alias hides the name the old "
        "check keyed on."
    )
    assert _mounted_callables(aliased) & raising, (
        "the detector is name-blind: it must see the raising callable however "
        "the plugin is aliased (#2145 review)."
    )

    benign = Kernel()
    benign.add_function(
        function_name="toulmin_analysis",
        plugin_name="ToulminOrchestrator",
        prompt="Analyse selon Toulmin. {{$input}}",
    )
    assert _mounted_callables(benign) & raising == set(), (
        "the negative control must be empty — a prompt tool holds no method, "
        "and must never be mistaken for the raising plugin."
    )


def test_toulmin_body_check_is_an_execution_not_an_assumption():
    """Control: the probe above must actually run the function."""
    assert callable(ToulminPlugin().analyze_argument)
    assert _toulmin_body_raises() is True, (
        "If the body no longer raises, the mount guard below is what must "
        "change — not this assertion."
    )


def test_toulmin_mount_follows_its_body_2145():
    """The arbitration, self-maintaining: no mount while the body raises.

    Withdrawing the mount withdraws a *promise*, not a capability — the tool
    could only ever raise. The day the body is implemented this reddens, and
    the remount becomes a decision someone makes on purpose.
    """
    mounted_in = [s for s, names in AGENT_SPECIALITY_MAP.items() if "toulmin" in names]

    if _toulmin_body_raises():
        assert mounted_in == [], (
            f"`toulmin` cannot succeed but is still offered to {mounted_in}: a "
            "live agent gets a tool that only burns a turn (#2145)."
        )
    else:
        assert mounted_in, (
            "The Toulmin body is implemented — remount it on the specialities "
            "that need it, then update this guard (#2145)."
        )


def test_toulmin_capability_was_not_deleted_2145():
    """Anti-pendulum: the arbitration removed a mount, not a module."""
    assert (
        "toulmin" in _PLUGIN_REGISTRY
    ), "The plugin stays registered; only its mount was withdrawn."
    assert _toulmin_body_raises(), (
        "The raise-pinning test lives in test_tweety_plugins.py — this file "
        "only asserts the module was not quietly deleted alongside the mount."
    )


def test_toulmin_benchmark_case_still_reports_the_death():
    """The benchmark is the instrument that shows the failure; it stays."""
    from argumentation_analysis.evaluation.plugin_benchmark import (
        PLUGIN_BENCHMARK_CASES,
    )

    cases = PLUGIN_BENCHMARK_CASES.get("toulmin")
    assert cases, "the toulmin benchmark case is the measured witness of the death"
    assert cases[0]["expected"] == {"returns_json": True}, (
        "It expects a JSON result from a function that raises — that permanent "
        "red is the point, and must not be softened into a passing expectation."
    )


def _asks_for_the_toulmin_analysis(template: str) -> bool:
    """True when the prompt asks for the analysis — not merely names its output.

    `ToulminAnalysisResult` is the *shape of the reply*; a template that only
    named it would be ordering nothing. Stripping it first is what makes this
    predicate discriminate — the substring test alone was satisfied by the
    output model's name, which is the vacuity the review named.
    """
    return "toulmin" in template.replace("ToulminAnalysisResult", "").lower()


def test_the_purpose_check_is_not_satisfied_by_the_output_model_name():
    """Control: the review's vacuity must be impossible, in both directions."""
    assert _asks_for_the_toulmin_analysis(
        "Analyse le texte selon le modèle argumentatif de Toulmin."
    ), "the positive control must be able to answer yes"
    assert not _asks_for_the_toulmin_analysis(
        "Réponds uniquement en JSON conforme au modèle ToulminAnalysisResult."
    ), "naming the output model is not asking for an analysis (#2145 review)."


def test_analyzer_does_not_promise_a_raising_tool_2145():
    """The #2212 arbitration, extended to the analyzer's own kernel.

    The analyzer drives a finetuned model that produces the Toulmin JSON
    itself (`run()` parses it); the plugin it used to mount on its own
    kernel could only ever raise, and its prompt went as far as ordering
    the LLM to call that dead tool. While the body raises, the analyzer
    must neither mount the tool nor name it. When the body is implemented
    this guard stops constraining — going back to tool-calling becomes a
    free decision, not an obligation.

    Executed, not deduced: the analyzer is really instantiated, and the
    mounted tools are matched by the *identity* of their callables rather
    than by the plugin's name — an alias must not buy silence.
    """
    if not _toulmin_body_raises():
        return

    analyzer = SemanticArgumentAnalyzer()
    raising, raising_names = _raising_surface()

    mounted = _mounted_callables(analyzer.kernel)
    offenders = sorted(m.__qualname__ for m in mounted & raising)
    assert not offenders, (
        f"The analyzer mounts a tool whose only body raises ({offenders}) — "
        "however the plugin is aliased, a live agent gets a tool that can only "
        f"burn a turn. Mounted plugins: {sorted(analyzer.kernel.plugins)}"
    )

    template = analyzer.prompt_function.prompt_template.prompt_template_config.template
    promised = sorted(n for n in raising_names if n in template)
    assert not promised, (
        f"The prompt still orders the LLM to call {promised} — functions of a "
        "plugin that cannot do anything but raise. The model is asked "
        "directly, not routed through a dead tool (#2145)."
    )
    # Anti-pendulum: what was withdrawn is the dead detour, not the analysis.
    assert _asks_for_the_toulmin_analysis(template), (
        "The analyzer must still ask for the Toulmin analysis — withdrawing "
        "the tool detour withdrew a promise, not the purpose (#2145)."
    )
