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
3. `toulmin` is mounted nowhere while its only function raises, and the day
   the body lands the guard reddens and forces the re-mount decision.

Instrument discipline: a detector that returns nothing has not proved
anything, so every zero here is paired with a positive control.
"""

from __future__ import annotations

import asyncio
import logging

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


def test_analyzer_does_not_promise_a_raising_tool_2145():
    """The #2212 arbitration, extended to the analyzer's own kernel.

    The analyzer drives a finetuned model that produces the Toulmin JSON
    itself (`run()` parses it); the plugin it used to mount on its own
    kernel could only ever raise, and its prompt went as far as ordering
    the LLM to call that dead tool. While the body raises, the analyzer
    must neither mount the tool nor name it. When the body is implemented
    this guard stops constraining — going back to tool-calling becomes a
    free decision, not an obligation.

    Executed, not deduced: the analyzer is really instantiated and the
    template is read from the live kernel object.
    """
    if not _toulmin_body_raises():
        return

    analyzer = SemanticArgumentAnalyzer()
    mounted = set(analyzer.kernel.plugins)
    assert (
        "Toulmin" not in mounted
    ), f"The analyzer mounts a plugin whose only function raises: {sorted(mounted)}"

    template = analyzer.prompt_function.prompt_template.prompt_template_config.template
    assert "Toulmin.analyze_argument" not in template, (
        "The prompt still orders the LLM to call a tool that cannot do "
        "anything but raise (#2145)."
    )
    # Anti-pendulum: what was withdrawn is the dead detour, not the analysis.
    assert "Toulmin" in template, (
        "The analyzer must still ask for the Toulmin analysis — withdrawing "
        "the tool detour withdrew a promise, not the purpose (#2145)."
    )
