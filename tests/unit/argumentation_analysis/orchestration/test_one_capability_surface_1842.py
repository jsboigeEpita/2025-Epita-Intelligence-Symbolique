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
   capability declared on the production surface is demanded by production
   code: an ``add_phase(capability=...)`` literal (the real consumption
   mechanism, workflow_dsl resolution) or a ``find_*_for_capability(...)``
   literal. The find_* idiom is mostly test-side, so production literals are
   the criterion; the census is on string literals in ``argumentation_analysis/``.

#2137 repair — the guard's original census filtered declarations through a
hard-coded five-component allow-list, so ``stakes_extractor_service`` could
declare ``stakeholder_analysis`` with zero demanders while the guard stayed
green: the guard measured the components it had been told about, not the
declaration surface. The census now reads EVERY ``register_*`` call in
``registry_setup.py``; (component, capability) pairs still awaiting triage
live in ``PENDING_TRIAGE`` as named debt, each tagged with the issue that
owns its census — the formal/Tweety specialists are #1604's scope (as
before), the services remainder is #2137's own broader triage. A NEW
component declaring an orphan reddens immediately: wire it, remove the
capability, or add a ``PENDING_TRIAGE`` entry with an owning issue — never
silently.
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

# (component, capability) -> owning issue. Debt declared, not hidden: these
# pairs ARE orphans today and their triage belongs to the named issue. The
# map must shrink as those issues land — never grow to absorb new silence.
PENDING_TRIAGE: dict[tuple[str, str], str] = {
    # #1604 — formal/Tweety specialists' census (out of scope since #1842)
    ("atms_service", "environment_tracking"): "#1604",
    ("jtms_service", "truth_maintenance"): "#1604",
    ("jtms_service", "jtms_reasoning"): "#1604",
    ("kb_to_tweety_plugin", "formula_translation"): "#1604",
    ("kb_to_tweety_plugin", "tweety_validation"): "#1604",
    ("logic_agent_plugin", "propositional_reasoning"): "#1604",
    ("logic_agent_plugin", "first_order_reasoning"): "#1604",
    ("logic_agent_plugin", "modal_reasoning"): "#1604",
    ("text_to_kb_plugin", "argument_extraction"): "#1604",
    ("text_to_kb_plugin", "kb_construction"): "#1604",
    ("tweety_logic_plugin", "tweety_logic"): "#1604",
    ("tweety_result_interpretation_plugin", "dung_interpretation"): "#1604",
    # #2137 — services remainder of the declared-without-consumer triage
    ("ai_shield_service", "output_filtering"): "#2137",
    ("ai_shield_service", "adversarial_protection"): "#2137",
    ("hierarchical_fallacy_detector", "fallacy_detection"): "#2137",
    ("hierarchical_fallacy_per_argument", "per_argument_fallacy_detection"): "#2137",
    ("self_hosted_fallacy_detector", "fallacy_detection"): "#2137",
    ("local_llm_service", "chat_completion"): "#2137",
    ("semantic_index_service", "argument_search"): "#2137",
    ("speech_transcription_service", "speech_to_text"): "#2137",
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
    """Component -> capabilities, from every declaration on the wired surface.

    No allow-list: the census measures what ``registry_setup.py`` (and the
    counter_argument module function it calls) actually declares — that is
    the production surface. The #2137 blind spot was exactly a hard-coded
    component filter here.
    """
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
            if comp is None:
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
        """No specialist capability stays declared-and-never-demanded.

        The census covers every declaration on the production surface. Pairs
        still awaiting triage must sit in ``PENDING_TRIAGE`` with an owning
        issue — the pre-#2137 guard instead filtered the census through a
        five-component allow-list and stayed green while
        ``stakes_extractor_service`` declared an undemanded capability.
        """
        declared = _declared_capabilities()
        demanded = _production_demanded_capabilities()
        orphans = {
            f"{comp}:{cap}": PENDING_TRIAGE.get((comp, cap), "NO OWNER")
            for comp, caps in declared.items()
            for cap in caps
            if cap not in demanded and (comp, cap) not in PENDING_TRIAGE
        }
        assert not orphans, (
            f"Declared capabilities with zero production demanders: "
            f"{orphans}. Every kept capability needs an add_phase or "
            f"find_*_for_capability consumer, or it must leave the "
            f"declaration (#1842 DoD). If the pair's triage is genuinely "
            f"deferred, add it to PENDING_TRIAGE with the issue that owns "
            f"it — an untagged orphan is the #2137 blind spot."
        )

    def test_in_scope_components_are_declared(self):
        """The census itself is alive: the historical five still declare."""
        declared = _declared_capabilities()
        missing = IN_SCOPE_COMPONENTS - set(declared)
        assert not missing, (
            f"In-scope components with no capability declaration found in "
            f"the wired surfaces: {sorted(missing)} — the declaration "
            f"extraction is likely stale (renamed component or moved file)."
        )

    def test_pending_triage_entries_are_real(self):
        """No stale debt: every PENDING_TRIAGE pair is a live declaration."""
        declared = _declared_capabilities()
        stale = {
            pair for pair in PENDING_TRIAGE if pair[1] not in declared.get(pair[0], [])
        }
        assert not stale, (
            f"PENDING_TRIAGE entries whose component no longer declares them: "
            f"{sorted(stale)}. Triage landed or the component changed — "
            f"remove the entry so the map shrinks instead of rotting."
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
