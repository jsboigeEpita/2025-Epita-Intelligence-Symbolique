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

#2424 repair — the demand census read two literal forms only
(``add_phase(capability="...")`` and ``*for_capability("...")``). A demand
carried by a table value reaches the resolver through a variable
(``for cap in caps: registry.find_for_capability(cap)``), so it was invisible
in both directions: #1842 trimmed ``argument_parsing`` while the delegation
table still translated to it, and the hierarchical bridge map demanded eight
names that no provider has ever declared. ``_capability_tables`` now brings
table-carried demand into the census, and
``test_table_carried_demand_resolves`` checks the other direction
(demanded ⇒ served) against the production registry.
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
    ("text_to_kb_plugin", "kb_construction"): "#1604",
    ("tweety_logic_plugin", "tweety_logic"): "#1604",
    ("tweety_result_interpretation_plugin", "dung_interpretation"): "#1604",
    # #2137 — services remainder of the declared-without-consumer triage
    ("ai_shield_service", "output_filtering"): "#2137",
    ("ai_shield_service", "adversarial_protection"): "#2137",
    ("hierarchical_fallacy_per_argument", "per_argument_fallacy_detection"): "#2137",
    ("local_llm_service", "chat_completion"): "#2137",
    ("semantic_index_service", "argument_search"): "#2137",
    ("speech_transcription_service", "speech_to_text"): "#2137",
}


def _module_path(py: Path) -> str:
    try:
        rel = py.relative_to(PROJECT_ROOT)
    except ValueError:
        return py.stem  # synthetic carrier outside the repo (#2373 control)
    parts = rel.with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]  # match ast.ImportFrom module paths for packages
    return ".".join(parts)


def _definers_of_register_function(root: Path = PROD_ROOT) -> set[str]:
    """Modules under *root* defining the register function."""
    definers = set()
    for py in root.rglob("*.py"):
        # utf-8-sig, and a parse failure raises rather than skips (#2373):
        # BOM'd modules are inside the census, not silently outside it.
        tree = ast.parse(py.read_text(encoding="utf-8-sig"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and (
                node.name == "register_with_capability_registry"
            ):
                definers.add(_module_path(py))
    return definers


def _wired_register_modules() -> set[str]:
    """Modules whose register function registry_setup actually imports."""
    tree = ast.parse(REGISTRY_SETUP.read_text(encoding="utf-8-sig"))
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
        tree = ast.parse(src.read_text(encoding="utf-8-sig"))
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


def _production_demanded_capabilities(root: Path = PROD_ROOT) -> set[str]:
    """Capability string literals production code actually asks for."""
    demanded = set()
    for py in root.rglob("*.py"):
        if "test" in py.parts:
            continue
        # utf-8-sig, and a parse failure raises rather than skips (#2373):
        # a BOM'd demander silently dropped here could orphan a capability.
        tree = ast.parse(py.read_text(encoding="utf-8-sig"), filename=str(py))
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
    for capabilities in _capability_tables(root).values():
        demanded |= capabilities
    return demanded


# Callees that resolve a capability name against the registry (production
# spells ``find_for_capability`` and ``RegistryBackedOperationalRegistry
# .has_capability``).
_RESOLVER_CALLEES = ("for_capability", "has_capability")


def _string_table_values(value: ast.expr) -> list[str] | None:
    """The strings a table literal holds, or ``None`` if it is not one.

    A table is a dict whose values are strings or lists of strings, or a
    list / tuple / set of strings (bare or wrapped in ``frozenset(...)`` etc.).
    """

    def strings(node: ast.expr) -> list[str] | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and all(
            isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts
        ):
            return [e.value for e in node.elts]
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") in ("frozenset", "set", "tuple", "list")
            and len(node.args) == 1
        ):
            return strings(node.args[0])
        return None

    if isinstance(value, ast.Dict):
        parts = [strings(v) for v in value.values]
        if parts and all(p is not None for p in parts):
            return [s for p in parts for s in p]
        return None
    if isinstance(value, ast.Constant):
        return None  # a single string is a constant, not a table
    return strings(value)


def _resolved_import_module(node: ast.ImportFrom, importer: str, is_pkg: bool) -> str:
    """Absolute dotted module of a ``from X import Y``, relative ones included."""
    if not node.level:
        return node.module or ""
    package = importer.split(".") if is_pkg else importer.split(".")[:-1]
    base = package[: len(package) - (node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def _capability_tables(root: Path = PROD_ROOT) -> dict[str, set[str]]:
    """String tables whose values production resolves as capabilities (#2424).

    A table counts when a function that calls a resolver with a non-literal
    argument names it: by bare name in the table's own module, or after a
    ``from <module> import <TABLE>`` (the delegation executor reads the bridge
    map through a lazy import). Tables are module- or class-level assignments.
    Keyed ``module:TABLE``. Parse failures raise, BOM'd files are read (#2373).
    """
    tables: dict[tuple[str, str], set[str]] = {}
    readers: list[tuple[str, set[str], set[tuple[str, str]]]] = []
    for py in root.rglob("*.py"):
        if "test" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8-sig"), filename=str(py))
        module = _module_path(py)
        is_pkg = py.name == "__init__.py"
        bodies = [tree.body] + [
            n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
        ]
        for body in bodies:
            for node in body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target, value = node.targets[0], node.value
                elif isinstance(node, ast.AnnAssign) and node.value is not None:
                    target, value = node.target, node.value
                else:
                    continue
                values = _string_table_values(value)
                if isinstance(target, ast.Name) and values:
                    tables[(module, target.id)] = set(values)
        imports = {
            (_resolved_import_module(n, module, is_pkg), alias.name)
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
            for alias in n.names
        }
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            resolves = False
            for n in ast.walk(fn):
                if not isinstance(n, ast.Call) or not n.args:
                    continue
                callee = getattr(n.func, "attr", "") or getattr(n.func, "id", "")
                if any(r in callee for r in _RESOLVER_CALLEES) and not isinstance(
                    n.args[0], ast.Constant
                ):
                    resolves = True
                    break
            if not resolves:
                continue
            names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} | {
                n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)
            }
            readers.append((module, names, imports))
    feeding: dict[str, set[str]] = {}
    for (module, name), values in tables.items():
        for reader_module, names, imports in readers:
            if name in names and (reader_module == module or (module, name) in imports):
                feeding[f"{module}:{name}"] = values
                break
    return feeding


def test_censuses_see_a_bom_carrier(tmp_path):
    """#2373 non-vacuity: both censuses of this guard must see a module
    behind a UTF-8 BOM. Under the previous strict read the BOM raised
    SyntaxError and the bare ``continue`` dropped the file — 13 BOM'd
    production files sat outside BOTH censuses, so a BOM'd definer could go
    unwired and a BOM'd demander could orphan a real capability.
    """
    src = (
        "﻿"
        "def register_with_capability_registry():\n"
        "    pass\n"
        "\n"
        "\n"
        "def build_workflow(dsl):\n"
        "    dsl.add_phase(capability='bom_carried_capability')\n"
    )
    (tmp_path / "bom_carrier.py").write_text(src, encoding="utf-8")
    assert _definers_of_register_function(tmp_path), (
        "a register_with_capability_registry behind a UTF-8 BOM must be in "
        "the definer census — otherwise the population is amputated (#2373)."
    )
    assert "bom_carried_capability" in _production_demanded_capabilities(tmp_path), (
        "an add_phase(capability=...) behind a UTF-8 BOM must be in the "
        "demanded census — otherwise a BOM'd demander can orphan a real "
        "capability and the guard stays green (#2373)."
    )


# Table-carried demand that no provider serves, named so the set cannot grow
# in silence (#2424). ``argument_visualization`` is the delegation table's
# placeholder; the tactical tier never emits it (see
# ``test_tactical_capabilities_resolve_2345.py``).
TABLE_DEMAND_GAPS = {"argument_visualization"}


def test_capability_table_census_sees_the_production_tables():
    """Non-vacuity: the tables production resolves through are all found."""
    names = {key.rsplit(":", 1)[1] for key in _capability_tables()}
    assert {
        "_OBJECTIVE_CAPABILITY_MAP",  # hierarchy_bridge, delegation fallback
        "LEGACY_TO_REGISTRY_CAPABILITY",  # delegation_orchestrator
        "KNOWN_CAPABILITIES",  # router
    } <= names, sorted(names)


def test_capability_table_census_follows_an_import(tmp_path):
    """A table read through ``from module import TABLE`` is demand; a string
    table that no resolver reads is not."""
    (tmp_path / "tables.py").write_text(
        'ROUTES = {"key": ["table_carried_capability"]}\n'
        'LABELS = {"key": "not_a_capability"}\n',
        encoding="utf-8",
    )
    (tmp_path / "reader.py").write_text(
        "def pick(registry):\n"
        "    from tables import ROUTES\n"
        "    for cap in ROUTES['key']:\n"
        "        if registry.find_for_capability(cap):\n"
        "            return cap\n",
        encoding="utf-8",
    )
    assert _capability_tables(tmp_path) == {
        "tables:ROUTES": {"table_carried_capability"}
    }
    demanded = _production_demanded_capabilities(tmp_path)
    assert "table_carried_capability" in demanded
    assert "not_a_capability" not in demanded


def test_table_carried_demand_resolves():
    """demanded ⇒ served: every capability a table feeds to a resolver has a
    provider in the production registry (#2424).

    On ``main`` before #2424 this listed eight names of the bridge map
    (``formal_logic``, ``fol_analysis``, ``debate_management``,
    ``governance_voting``, ``synthesis``, ``coherence_evaluation``,
    ``text_extraction``, ``french_fallacy_detection``), none of which any
    provider has ever declared.
    """
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    registry = setup_registry()  # the call the hierarchical orchestrator makes
    dead = {
        f"{table}:{cap}"
        for table, caps in _capability_tables().items()
        for cap in caps
        if not registry.find_for_capability(cap)
    }
    assert {key.rsplit(":", 1)[1] for key in dead} == TABLE_DEMAND_GAPS, (
        f"Capabilities demanded through a table with no provider: "
        f"{sorted(dead)}. Rename to the capability the registry serves, "
        f"or name the gap in TABLE_DEMAND_GAPS."
    )


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

    def test_pending_triage_entries_are_still_orphans(self):
        """No answered debt: a pair that production demands is not an orphan.

        Before #2424 the census ignored table-carried demand, so pairs whose
        capability a table does demand sat here as orphans.
        """
        demanded = _production_demanded_capabilities()
        answered = sorted(pair for pair in PENDING_TRIAGE if pair[1] in demanded)
        assert not answered, (
            f"PENDING_TRIAGE entries whose capability production demands: "
            f"{answered}. They have a consumer: remove the entry."
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
