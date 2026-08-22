"""One capability surface per module — static guards (#1842).

#1842 established that ``debate``, ``governance`` and ``quality`` declared
their capabilities TWICE, in two vocabularies: the production surface
(``orchestration/registry_setup.py``, called by ``setup_registry``) and a
per-module ``register_with_capability_registry`` that only tests ever called
(for ``debate`` the two even collided on the ``register_agent`` name — wiring
both would crash registry construction with ``ValueError``). A fifth definer
(``synthesis/deep_synthesis_agent.py``) was dead under even tests.

These guards pin the subtractive resolution:

1. ``test_register_functions_are_all_wired`` — every module defining
   ``register_with_capability_registry`` must be the one ``registry_setup``
   imports and calls. A new dead definer (the deep_synthesis failure mode)
   reddens immediately.
2. ``test_declared_capabilities_have_production_demanders`` — every
   capability declared for the five specialists is demanded by production
   code: an ``add_phase(capability=...)`` literal (the real consumption
   mechanism, workflow_dsl resolution) or a ``find_*_for_capability(...)``
   literal. The find_* idiom is mostly test-side, so production literals are
   the criterion; the census is on string literals in ``argumentation_analysis/``.

Out of scope by design (#1842 ≠ #1604): the formal/Tweety specialists'
declarations are not covered by guard 2 — their orphan census is #1604's.
"""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROD_ROOT = PROJECT_ROOT / "argumentation_analysis"
REGISTRY_SETUP = PROD_ROOT / "orchestration" / "registry_setup.py"

IN_SCOPE_COMPONENTS = {
    "counter_argument_agent",
    "quality_evaluator",
    "debate_agent",
    "governance_agent",
    "deep_synthesis_service",
}


def _module_path(py: Path) -> str:
    rel = py.relative_to(PROJECT_ROOT)
    parts = rel.with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]  # match ast.ImportFrom module paths for packages
    return ".".join(parts)


def _definers_of_register_function() -> set[str]:
    """Modules under argumentation_analysis/ defining the register function."""
    definers = set()
    for py in PROD_ROOT.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and (
                node.name == "register_with_capability_registry"
            ):
                definers.add(_module_path(py))
    return definers


def _wired_register_modules() -> set[str]:
    """Modules whose register function registry_setup actually imports."""
    tree = ast.parse(REGISTRY_SETUP.read_text(encoding="utf-8"))
    wired = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "register_with_capability_registry":
                    wired.add(node.module)
    return wired


def _declared_capabilities() -> dict[str, list[str]]:
    """Component -> capabilities, from the wired declaration surfaces."""
    sources = [
        REGISTRY_SETUP,
        PROD_ROOT / "agents" / "core" / "counter_argument" / "__init__.py",
    ]
    declared: dict[str, list[str]] = {}
    for src in sources:
        tree = ast.parse(src.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fname = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
            if not fname.startswith("register_"):
                continue
            comp = None
            if node.args and isinstance(node.args[0], ast.Constant):
                comp = node.args[0].value
            for kw in node.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    comp = kw.value.value
            if comp not in IN_SCOPE_COMPONENTS:
                continue
            for kw in node.keywords:
                if kw.arg == "capabilities" and isinstance(kw.value, ast.List):
                    caps = [
                        e.value for e in kw.value.elts if isinstance(e, ast.Constant)
                    ]
                    declared.setdefault(comp, []).extend(caps)
    return declared


def _production_demanded_capabilities() -> set[str]:
    """Capability string literals production code actually asks for."""
    demanded = set()
    for py in PROD_ROOT.rglob("*.py"):
        if "test" in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
            if callee == "add_phase":
                for kw in node.keywords:
                    if kw.arg == "capability" and isinstance(kw.value, ast.Constant):
                        demanded.add(kw.value.value)
            elif "for_capability" in callee:
                if node.args and isinstance(node.args[0], ast.Constant):
                    demanded.add(node.args[0].value)
    return demanded


class TestOneCapabilitySurface:
    def test_register_functions_are_all_wired(self):
        """Every definer of the register function is wired through setup_registry.

        The pre-#1842 state had four definers no production code called —
        for ``debate`` wiring the second surface would not merely dilute
        metrics, it would crash registry construction (name collision).
        """
        definers = _definers_of_register_function()
        wired = _wired_register_modules()
        unwired = definers - wired
        assert not unwired, (
            f"Modules defining register_with_capability_registry that "
            f"registry_setup never wires: {sorted(unwired)}. A second, dead "
            f"capability surface — the #1842 defect (and its deep_synthesis "
            f"recurrence). Either wire it or delete the function."
        )

    def test_declared_capabilities_have_production_demanders(self):
        """No specialist capability stays declared-and-never-demanded."""
        declared = _declared_capabilities()
        demanded = _production_demanded_capabilities()
        orphans = {
            comp: [c for c in caps if c not in demanded]
            for comp, caps in declared.items()
        }
        orphans = {comp: caps for comp, caps in orphans.items() if caps}
        assert not orphans, (
            f"Declared capabilities with zero production demanders: "
            f"{orphans}. Every kept capability needs an add_phase or "
            f"find_*_for_capability consumer, or it must leave the "
            f"declaration (#1842 DoD). Formal/Tweety specialists are "
            f"#1604's scope, not this guard's."
        )

    def test_in_scope_components_are_declared(self):
        """The census itself is alive: all five specialists declare a table."""
        declared = _declared_capabilities()
        missing = IN_SCOPE_COMPONENTS - set(declared)
        assert not missing, (
            f"In-scope components with no capability declaration found in "
            f"the wired surfaces: {sorted(missing)} — the declaration "
            f"extraction is likely stale (renamed component or moved file)."
        )


@pytest.mark.parametrize(
    "capability",
    sorted(
        {
            "adversarial_debate",
            "argument_quality",
            "governance_simulation",
            "counter_argument_generation",
            "deep_synthesis",
        }
    ),
)
def test_kept_capabilities_resolve_in_real_registry(capability):
    """Runtime pin: the real setup_registry serves every kept capability.

    Population is the production registry — not one the test fabricates
    (the #1842 DoD replacing the old convenience-functions test).
    """
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    registry = setup_registry(include_optional=False)
    providers = registry.find_for_capability(capability)
    assert providers, (
        f"Capability {capability!r} has no provider in the real "
        f"setup_registry population."
    )
