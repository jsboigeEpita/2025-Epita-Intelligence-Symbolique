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
before). #2623 settled the services remainder #2137 left behind on closing
(five registry aliases with zero demanders left the declaration, the
mono-capability enrichment sub-step left the registry), and made owner
liveness a measurement: ``scripts/maintenance/
check_pending_triage_owners.py`` lists every owner this map names with its
GitHub state and fails on a closed owner still owning entries. A NEW
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

#2788 repair — two more demand forms sat outside the census. A table of
ROWS that a loop unpacks into ``add_phase(capability=<loop variable>)``
(the evaluation workflows, the router's optional phases) is neither a
literal at the call nor a string table a resolver reads. And the literal
form was read on ``add_phase`` only, while ``add_conditional_phase`` and
``add_loop`` add phases too (five production calls). ``_phase_row_tables``
reads the rows from the source; a phase whose capability the census cannot
read fails it, unless ``DYNAMIC_PHASE_CAPABILITIES`` names the site and
says where its demand is measured — the #1604 rule, applied to demand.
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
# #2623 triaged the six services entries owned by the closed #2137: five
# registry aliases with zero production demanders left the declaration
# (each service stays behind its demanded name), and the mono-capability
# enrichment sub-step left the registry entirely (it lives by direct call,
# see test_shared_capability_provider_selection_1553.py).
# #1604 triaged its seven registry aliases the same way: each component
# (and its #506 service twin) stays behind its demanded name. What remains
# below is not an alias — none of these components declares a demanded name,
# so retiring the names retires the component: that is a wire-or-retire
# decision, not a vocabulary trim.
PENDING_TRIAGE: dict[tuple[str, str], str] = {
    # #1604 — live invoke callables that no phase requests. They were
    # declared inside `for name, caps, ... in <rows>:` loops, which the census
    # could not read before #1604: silence the tree already carried, made
    # visible here rather than created.
    ("multi_axis_compare_service", "multi_axis_compare"): "#1604",
    # dung_arbitration owner -> #1649 (arbitration c.5976719576: "0 eliminations
    # => PENDING_TRIAGE owner -> #1649"). Measured offline, 0 LLM, real corpus
    # (22 docs): 88 candidates, 0 attacks, 0 eliminations, honest_absent on
    # every doc. Structural root: the bridge derives span_id from
    # (detector, family), so same-span groups are always same-family and the
    # rivalry policy skips same-family pairs — zero rivalry edges are
    # derivable for ANY input; the bridge never populates failed critical
    # questions; the only live attack channel is declared Walton-Krabbe
    # relations, whose producer is #1649 (open).
    ("dung_arbitration_service", "dung_arbitration"): "#1649",
    # ("tweety_logic_plugin", "tweety_logic") — retired #1604 (coordinator
    # arbitration): the plugin registration carries no invoke callable, so the
    # MCP invoke_capability route never reached it — only the list readers
    # (list_capabilities, get_registry_summary, proposal_endpoints) lost a
    # name. The plugin stays mounted by name ("tweety_logic") through
    # AgentFactory. Declaration exits, not the component.
    # ("logic_agent_plugin", "propositional_reasoning"/"first_order_reasoning"/
    # "modal_reasoning") — retired #1604: the trio had zero demanders on every
    # surface (no phase, no table, not on the PM map) and every claim they
    # could carry is carried by a phase-resolved capability. The plugin stays
    # mounted by speciality ("logic_agents") — declaration exits, not the
    # component.
    # ("multi_axis_compare_service", "multi_axis_compare") — row RESTORED at
    # #1604 review: the registration is its ONLY production route (the MCP
    # invoke_capability resolves it by name and calls its invoke), and
    # _invoke_multi_axis_compare has no other production caller. Retiring it
    # leaves the function with zero production callers — a function
    # retirement under the Cleanup Gate, not a declaration-only change. The
    # pair is back in PENDING_TRIAGE above pending that decision.
    # ("sat_handler", "sat_solving") — wired #1604 (arbitration): the named
    # MCP tool solve_sat (specialized_tools.py) demands the capability
    # through _invoke_by_capability("sat_solving", ...), which this census
    # reads. Born-red both ways: delete the tool and the declaration is an
    # orphan again; delete the declaration and the tool answers "not
    # available". The registration is _invoke_sat's only production route
    # besides a maintenance script.
    # ("asp_reasoning_handler", "asp_reasoning") — wired #1604: the ASP
    # stable-extension cross-check phase in formal_extended demands it.
    # ("asp_reasoning_handler", "answer_set_programming") — retired #1604:
    # undemanded alias, same retirement as the #2733 aliases.
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


# The registry methods that declare capabilities. ``register_with_capability_
# registry`` (a module function) and the ServiceDiscovery ``register_*_provider``
# family declare none.
_REGISTER_METHODS = {"register_agent", "register_plugin", "register_service"}
# The WorkflowBuilder methods that add a phase; each takes ``capability``
# second (#2788: the census read ``add_phase`` only).
_PHASE_CALLEES = {"add_phase", "add_conditional_phase", "add_loop"}

DECLARATION_SOURCES = [
    REGISTRY_SETUP,
    PROD_ROOT / "agents" / "core" / "counter_argument" / "__init__.py",
]


def _register_call_parts(call: ast.Call) -> tuple[ast.expr | None, ast.expr | None]:
    """The ``name`` and ``capabilities`` expressions of a register call."""
    name = call.args[0] if call.args else None
    caps = None
    for kw in call.keywords:
        if kw.arg == "name":
            name = kw.value
        elif kw.arg == "capabilities":
            caps = kw.value
    return name, caps


def _literal_list(node: ast.expr | None) -> list[str] | None:
    if isinstance(node, ast.List) and all(
        isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts
    ):
        return [e.value for e in node.elts]
    return None


def _loop_rows(tree: ast.Module, loop: ast.For) -> list[ast.expr]:
    """The rows a ``for ... in <rows>:`` loop iterates, read from the source."""
    if isinstance(loop.iter, (ast.List, ast.Tuple)):
        return list(loop.iter.elts)
    if isinstance(loop.iter, ast.Name):
        bound = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == loop.iter.id for t in node.targets
            )
        ]
        if len(bound) == 1 and isinstance(bound[0], (ast.List, ast.Tuple)):
            return list(bound[0].elts)
    raise AssertionError(
        f"line {loop.lineno}: a registering loop iterates {ast.unparse(loop.iter)}, "
        "which the census cannot read as one literal list of rows."
    )


def _declared_capabilities(sources=None) -> dict[str, list[str]]:
    """Component -> capabilities, from every declaration on the wired surface.

    No allow-list: the census measures what ``registry_setup.py`` (and the
    counter_argument module function it calls) actually declares — that is
    the production surface. The #2137 blind spot was exactly a hard-coded
    component filter here.

    #1604: a register call inside ``for name, caps, ... in <rows>:`` takes its
    name and capabilities from the loop targets. The census used to read only
    literal arguments and skipped the rest without a trace, which hid 32 of
    the 56 components ``setup_registry`` registers (measured on ``434ba60e0``).
    Loop rows are now read from the source, and a register call whose name
    or capabilities the census cannot read fails the census instead of
    leaving it.
    """
    declared: dict[str, list[str]] = {}
    unreadable = []
    for src in sources or DECLARATION_SOURCES:
        tree = ast.parse(src.read_text(encoding="utf-8-sig"))
        in_loop = set()
        for loop in ast.walk(tree):
            if not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Tuple):
                continue
            targets = [
                t.id if isinstance(t, ast.Name) else None for t in loop.target.elts
            ]
            for call in ast.walk(loop):
                if not (
                    isinstance(call, ast.Call)
                    and getattr(call.func, "attr", "") in _REGISTER_METHODS
                ):
                    continue
                name, caps = _register_call_parts(call)
                if not (
                    isinstance(name, ast.Name)
                    and isinstance(caps, ast.Name)
                    and name.id in targets
                    and caps.id in targets
                ):
                    continue
                in_loop.add(id(call))
                for row in _loop_rows(tree, loop):
                    comp = (
                        row.elts[targets.index(name.id)]
                        if isinstance(row, ast.Tuple)
                        else None
                    )
                    row_caps = (
                        row.elts[targets.index(caps.id)]
                        if isinstance(row, ast.Tuple)
                        else None
                    )
                    listed = _literal_list(row_caps)
                    if not isinstance(comp, ast.Constant) or listed is None:
                        unreadable.append(f"{src.name}:{row.lineno}")
                        continue
                    declared.setdefault(comp.value, []).extend(listed)
        for call in ast.walk(tree):
            if (
                not (
                    isinstance(call, ast.Call)
                    and getattr(call.func, "attr", "") in _REGISTER_METHODS
                )
                or id(call) in in_loop
            ):
                continue
            name, caps = _register_call_parts(call)
            listed = _literal_list(caps)
            if not isinstance(name, ast.Constant) or listed is None:
                unreadable.append(f"{src.name}:{call.lineno}")
                continue
            declared.setdefault(name.value, []).extend(listed)
    assert not unreadable, (
        f"register calls the declaration census cannot read: {unreadable}. "
        "Give them literal names and capabilities, or teach the census the "
        "form — a skipped declaration is an orphan no guard sees (#1604)."
    )
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
            if callee in _PHASE_CALLEES:
                capability = _phase_capability(node)
                if isinstance(capability, ast.Constant):
                    demanded.add(capability.value)
            elif "for_capability" in callee or callee == "_invoke_by_capability":
                # _invoke_by_capability("<cap>", ...) is how a named MCP tool
                # in specialized_tools.py reaches a capability (#1604): its
                # literal first arg is demand, the same way a resolver call's
                # is. The generic invoke_capability(name) route stays
                # intentionally unread — a client-chosen name is not demand.
                if node.args and isinstance(node.args[0], ast.Constant):
                    demanded.add(node.args[0].value)
    for capabilities in _capability_tables(root).values():
        demanded |= capabilities
    for capabilities in _phase_row_tables(root).values():
        demanded |= capabilities
    return demanded


def _phase_capability(call: ast.Call) -> ast.expr | None:
    """The ``capability`` a phase-adding call passes, keyword or positional."""
    for kw in call.keywords:
        if kw.arg == "capability":
            return kw.value
    return call.args[1] if len(call.args) > 1 else None


# Phases whose capability is neither a literal nor a loop variable over rows
# the census can read (#2788). Each is keyed (module, function, capability
# expression) and says where its demand is measured instead. A stale entry
# reddens (``test_dynamic_phase_capabilities_are_real``).
DYNAMIC_PHASE_CAPABILITIES = {
    (
        "argumentation_analysis.orchestration.hierarchical.hierarchy_bridge",
        "objectives_to_workflow",
        "capability",
    ): "matched through _OBJECTIVE_CAPABILITY_MAP, which _capability_tables "
    "reads (#2424)",
    (
        "argumentation_analysis.orchestration.hierarchical.hierarchy_bridge",
        "objectives_to_workflow",
        "f'objective_{obj_id}'",
    ): "optional placeholder for an objective that matched no capability; no "
    "provider can serve it by construction, so the phase always skips",
}


def _phase_calls(fn: ast.AST) -> list[tuple[ast.Call, list[ast.For]]]:
    """Each phase-adding call of ``fn`` itself, with the loops around it."""
    found = []

    def visit(node: ast.AST, loops: list[ast.For]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
            ):
                continue  # a nested scope is censused as its own function
            callee = getattr(child, "func", None)
            if (
                isinstance(child, ast.Call)
                and (getattr(callee, "attr", "") or getattr(callee, "id", ""))
                in _PHASE_CALLEES
            ):
                found.append((child, loops))
            visit(child, loops + [child] if isinstance(child, ast.For) else loops)

    visit(fn, [])
    return found


def _loop_variable_values(
    tree: ast.Module, loops: list[ast.For], variable: ast.expr
) -> list[str] | None:
    """The strings a loop variable takes over its rows, or ``None``."""
    if not isinstance(variable, ast.Name):
        return None
    for loop in reversed(loops):  # the innermost binding wins
        target = loop.target
        names = (
            [getattr(t, "id", None) for t in target.elts]
            if isinstance(target, ast.Tuple)
            else [getattr(target, "id", None)]
        )
        if variable.id not in names:
            continue
        index = names.index(variable.id) if isinstance(target, ast.Tuple) else None
        try:
            rows = _loop_rows(tree, loop)
        except AssertionError:
            return None
        values = []
        for row in rows:
            cell = row
            if index is not None:
                cell = (
                    row.elts[index]
                    if isinstance(row, ast.Tuple) and len(row.elts) > index
                    else None
                )
            if not (isinstance(cell, ast.Constant) and isinstance(cell.value, str)):
                return None
            values.append(cell.value)
        return values
    return None


def _phase_row_census(
    root: Path = PROD_ROOT,
) -> tuple[dict[str, set[str]], set[tuple[str, str, str]], list[str]]:
    """Row-carried phase demand, the named dynamic sites met, the unreadable."""
    feeding: dict[str, set[str]] = {}
    dynamic_seen: set[tuple[str, str, str]] = set()
    unreadable: list[str] = []
    for py in sorted(root.rglob("*.py")):
        if "test" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8-sig"), filename=str(py))
        module = _module_path(py)
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if fn.name in _PHASE_CALLEES:
                continue  # WorkflowBuilder forwarding its own parameter
            for call, loops in _phase_calls(fn):
                capability = _phase_capability(call)
                if capability is None or isinstance(capability, ast.Constant):
                    continue  # a literal: the literal census reads it
                site = (module, fn.name, ast.unparse(capability))
                if site in DYNAMIC_PHASE_CAPABILITIES:
                    dynamic_seen.add(site)
                    continue
                values = _loop_variable_values(tree, loops, capability)
                if values is None:
                    unreadable.append(f"{module}:{fn.name}:{call.lineno} {site[2]}")
                    continue
                feeding.setdefault(f"{module}:{fn.name}", set()).update(values)
    return feeding, dynamic_seen, unreadable


def _phase_row_tables(root: Path = PROD_ROOT) -> dict[str, set[str]]:
    """Capabilities that row tables feed to a phase, keyed ``module:function``.

    ``for name, capability, deps in PHASES: builder.add_phase(name,
    capability=capability)`` carries its demand in the rows (#2788). A phase
    whose capability the census cannot read, and that
    ``DYNAMIC_PHASE_CAPABILITIES`` does not name, fails the census: skipped,
    it would be demand no guard sees.
    """
    feeding, _, unreadable = _phase_row_census(root)
    assert not unreadable, (
        f"phases whose capability the demand census cannot read: {unreadable}. "
        "Feed them from a literal list of rows, or name the site in "
        "DYNAMIC_PHASE_CAPABILITIES with where its demand is measured (#2788)."
    )
    return feeding


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


def test_declaration_census_reads_loop_rows(tmp_path):
    """#1604 non-vacuity: a declaration made inside a registering loop is in
    the census, whether the loop iterates an inline list or a name bound to
    one. Before #1604 both forms were skipped without a trace — 32 of the 56
    components ``setup_registry`` registers sat outside the census.
    """
    src = (
        "def setup(registry, invoke):\n"
        "    registry.register_service(\n"
        "        name='direct_service', capabilities=['direct_cap'], invoke=invoke\n"
        "    )\n"
        "    rows = [('named_row_service', ['named_row_cap'], 'desc', invoke)]\n"
        "    for name, caps, desc, fn in rows:\n"
        "        registry.register_service(name=name, capabilities=caps, invoke=fn)\n"
        "    for name, caps in [('inline_row_plugin', ['inline_row_cap'])]:\n"
        "        registry.register_plugin(name=name, capabilities=caps)\n"
    )
    source = tmp_path / "loop_registrations.py"
    source.write_text(src, encoding="utf-8")
    assert _declared_capabilities(sources=[source]) == {
        "direct_service": ["direct_cap"],
        "named_row_service": ["named_row_cap"],
        "inline_row_plugin": ["inline_row_cap"],
    }


def test_declaration_census_fails_on_an_unreadable_call(tmp_path):
    """#1604: a register call the census cannot read stops the census — the
    old census skipped it, and the declaration became an orphan no guard saw.
    """
    src = (
        "def setup(registry, computed_caps):\n"
        "    registry.register_service(name='opaque', capabilities=computed_caps)\n"
    )
    source = tmp_path / "opaque_registration.py"
    source.write_text(src, encoding="utf-8")
    with pytest.raises(AssertionError, match="cannot read"):
        _declared_capabilities(sources=[source])


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


def test_demand_census_reads_named_tool_helpers(tmp_path):
    """#1604: a named MCP tool's helper call is demand the census reads.

    ``_invoke_by_capability("sat_solving", ...)`` — the form ``solve_sat``
    uses — must count like a resolver call's literal, or the tool that gives
    ``sat_solving`` its one visible demander would be invisible again. The
    generic ``invoke_capability(name)`` route stays unread on purpose: a
    client-chosen name is not demand.
    """
    (tmp_path / "tools.py").write_text(
        "def tool(text):\n"
        "    return _invoke_by_capability('sat_solving', text, 'solve_sat')\n",
        encoding="utf-8",
    )
    assert "sat_solving" in _production_demanded_capabilities(root=tmp_path)


def test_sat_solving_has_a_named_production_demander():
    """Born-red both ways (#1604): the solve_sat tool's literal is the pair's
    demander — delete the tool and this reddens; the pair then sits
    undemanded again with no PENDING_TRIAGE entry to silence it."""
    assert "sat_solving" in _production_demanded_capabilities()


def test_table_carried_demand_resolves():
    """demanded ⇒ served: every capability a table feeds to a resolver, or a
    row table feeds to a phase (#2788), has a provider in the production
    registry (#2424).

    On ``main`` before #2424 this listed eight names of the bridge map
    (``formal_logic``, ``fol_analysis``, ``debate_management``,
    ``governance_voting``, ``synthesis``, ``coherence_evaluation``,
    ``text_extraction``, ``french_fallacy_detection``), none of which any
    provider has ever declared.
    """
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    registry = setup_registry()  # the call the hierarchical orchestrator makes
    tables = {**_capability_tables(), **_phase_row_tables()}
    dead = {
        f"{table}:{cap}"
        for table, caps in tables.items()
        for cap in caps
        if not registry.find_for_capability(cap)
    }
    assert {key.rsplit(":", 1)[1] for key in dead} == TABLE_DEMAND_GAPS, (
        f"Capabilities demanded through a table with no provider: "
        f"{sorted(dead)}. Rename to the capability the registry serves, "
        f"or name the gap in TABLE_DEMAND_GAPS."
    )


def test_phase_row_census_reads_every_form(tmp_path):
    """#2788 non-vacuity: demand carried by rows, and by the two other phase
    callees, is in the census. Before #2788 none of these names was.
    """
    (tmp_path / "phase_rows.py").write_text(
        "MODULE_ROWS = [('a', 'module_row_cap', [])]\n"
        "\n"
        "\n"
        "def build(builder, selected):\n"
        "    for name, cap, deps in MODULE_ROWS:\n"
        "        builder.add_phase(name=name, capability=cap)\n"
        "    local_rows = [('b', 'local_row_cap'), ('c', 'filtered_row_cap')]\n"
        "    for name, cap in local_rows:\n"
        "        if cap in selected:\n"
        "            builder.add_phase(name, capability=cap)\n"
        "    for cap in ['bare_name_cap']:\n"
        "        builder.add_phase('d', cap)\n"
        "\n"
        "    def nested(b):\n"
        "        for n, c in [('e', 'nested_row_cap')]:\n"
        "            b.add_phase(n, capability=c)\n"
        "\n"
        "    builder.add_conditional_phase('f', capability='conditional_cap')\n"
        "    builder.add_loop('g', 'loop_positional_cap')\n",
        encoding="utf-8",
    )
    demanded = _production_demanded_capabilities(tmp_path)
    assert {
        "module_row_cap",
        "local_row_cap",
        "filtered_row_cap",
        "bare_name_cap",
        "nested_row_cap",
        "conditional_cap",
        "loop_positional_cap",
    } <= demanded, sorted(demanded)


def test_phase_row_census_fails_on_an_unreadable_phase(tmp_path):
    """#2788: a phase whose capability the census cannot read stops the
    census, as an unreadable declaration does (#1604)."""
    (tmp_path / "opaque_phase.py").write_text(
        "def build(builder, caps):\n"
        "    for i, cap in enumerate(caps):\n"
        "        builder.add_phase(f'p{i}', capability=cap)\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="cannot read"):
        _production_demanded_capabilities(tmp_path)


def test_phase_row_census_sees_the_production_tables():
    """Non-vacuity: the row tables production builds phases from are found."""
    assert {
        "argumentation_analysis.evaluation.capability_eval:_build_eval_workflow",
        "argumentation_analysis.evaluation.run_agentic_eval:_build_full_workflow",
        "argumentation_analysis.evaluation.run_iteration:_build_iteration_workflow",
        "argumentation_analysis.orchestration.router:_build_workflow",
    } <= set(_phase_row_tables()), sorted(_phase_row_tables())


def test_dynamic_phase_capabilities_are_real():
    """No stale entry: every named dynamic site is still in production."""
    _, dynamic_seen, _ = _phase_row_census()
    stale = sorted(set(DYNAMIC_PHASE_CAPABILITIES) - dynamic_seen)
    assert not stale, (
        f"DYNAMIC_PHASE_CAPABILITIES entries production no longer has: {stale}. "
        "Remove them so the map shrinks instead of rotting."
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
