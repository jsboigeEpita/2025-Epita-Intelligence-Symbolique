"""#2451 — the validation system's component probe names the symbols where they live.

`UnifiedValidationSystem._detect_available_components()` decides which
components exist by importing them. Three of its probes imported paths that no
longer exist (a moved module, a moved package, a renamed class), and
``except ImportError: pass`` turned each into "absent": on ``main`` the report
said 5/8 on every run, and nothing in it said why. A wrong path and a missing
component read the same.
"""

import pytest

from scripts.validation.main import UnifiedValidationSystem
from scripts.validation.validators import ecosystem_validator

MOVED_PROBES = ("llm_service", "fol_agent", "source_selector")


@pytest.fixture(scope="module")
def system():
    return UnifiedValidationSystem()


@pytest.mark.parametrize("key", MOVED_PROBES)
def test_a_component_that_exists_is_detected(system, key):
    assert system.available_components[key] is True, (
        f"#2451: the '{key}' probe reports an existing component as absent: "
        f"{getattr(system, 'component_import_failures', {}).get(key)}"
    )


def test_every_probe_resolves_on_this_tree(system):
    """All 8 probed components exist in the tree, so all 8 resolve."""
    assert system.component_import_failures == {}
    assert all(system.available_components.values())


def test_an_absent_component_is_recorded_with_its_reason(monkeypatch):
    """Non-vacuity: a probe on a module that does not exist is False, and the
    report says which module and why."""
    monkeypatch.setitem(
        UnifiedValidationSystem.COMPONENT_PROBES,
        "fol_agent",
        ("argumentation_analysis.no_such_module_2451", ("FOLLogicAgent",)),
    )
    system = UnifiedValidationSystem()

    assert system.available_components["fol_agent"] is False
    reason = system.component_import_failures["fol_agent"]
    assert "no_such_module_2451" in reason
    assert reason.startswith("ModuleNotFoundError")


def test_a_missing_name_in_an_existing_module_is_recorded(monkeypatch):
    """The renamed-class case: the module imports, the name is gone."""
    monkeypatch.setitem(
        UnifiedValidationSystem.COMPONENT_PROBES,
        "fol_agent",
        (
            "argumentation_analysis.agents.core.logic.fol_logic_agent",
            ("FirstOrderLogicAgent",),
        ),
    )
    system = UnifiedValidationSystem()

    assert system.available_components["fol_agent"] is False
    assert "FirstOrderLogicAgent" in system.component_import_failures["fol_agent"]


def test_the_summary_carries_the_failures(system, monkeypatch):
    monkeypatch.setattr(
        system, "component_import_failures", {"fol_agent": "ImportError: x"}
    )
    system._generate_summary()
    assert system.report.summary["component_import_failures"] == {
        "fol_agent": "ImportError: x"
    }


async def test_the_ecosystem_check_imports_the_real_source_selector():
    """The ecosystem validator's source-selector check was gated on a flag that
    was always False, and imported the same wrong path behind it."""
    results = await ecosystem_validator._validate_source_management(
        {"source_selector": True}
    )
    assert results["module_import"]["status"] == "✅ OK", results
    assert results["instantiation"]["status"] == "✅ OK", results
