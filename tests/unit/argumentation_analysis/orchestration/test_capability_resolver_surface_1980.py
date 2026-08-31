"""Capability resolver surface — the partition a one-spelling grep cannot see (#1980).

CLAUDE.md asserted that ``find_*_for_capability("…")`` is "almost entirely a
*test* idiom — 57 sites under ``tests/``, and in production exactly **one**
real call site". That was measured with a pattern (``find_[a-z_]*_for_capability``)
that structurally cannot match ``find_for_capability`` — it requires a segment
before ``_for``. The claim was therefore an assertion of absence produced by an
instrument blind to the very spelling production uses.

The measured partition is sharper than the claim it replaces, and runs the
other way:

* production calls **only** the untyped ``find_for_capability`` — ``workflow_dsl``
  (phase resolution), ``router``, ``hierarchy_bridge``, the two MCP tool modules;
* the three typed variants (``find_agents_``/``find_plugins_``/``find_services_``)
  have **zero** production callers and live entirely under ``tests/``.

So a grep on one spelling measures whichever half it happened to match. These
guards pin the *relation*, not the counts — they redden when the partition
moves (a sixth spelling appears, a typed variant gains a production caller,
production stops resolving through the registry), and stay silent while the
codebase merely grows.

Deliberately NOT in scope: ``test_one_capability_surface_1842.py``'s docstring
says the find_* idiom is "mostly test-side" and uses production literals as its
criterion. Aggregate is 63 test calls to 12 production ones — "mostly" is exact
and its operational conclusion is sound. It is not a sibling of the false claim.
"""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROD_ROOT = PROJECT_ROOT / "argumentation_analysis"
TESTS_ROOT = PROJECT_ROOT / "tests"

# The resolver surface as measured on def2dd4e. A sixth spelling, or a rename,
# reddens here first — which is the point: enumerate the surface before
# counting it.
RESOLVER_SURFACE = frozenset(
    {
        "find_for_capability",
        "find_all_for_capability",
        "find_agents_for_capability",
        "find_plugins_for_capability",
        "find_services_for_capability",
    }
)

# The variants production never calls. They are a test idiom — that part of the
# old claim was true; it was only ever false of the untyped spelling.
TYPED_VARIANTS = frozenset(
    {
        "find_agents_for_capability",
        "find_plugins_for_capability",
        "find_services_for_capability",
    }
)

UNTYPED_RESOLVER = "find_for_capability"


def _iter_python(root: Path):
    for py in sorted(root.rglob("*.py")):
        try:
            yield py, ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue  # vendored / generated files are not part of the census


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _definitions(root: Path) -> set[str]:
    return {
        node.name
        for _, tree in _iter_python(root)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.endswith("_for_capability")
    }


def _call_sites(root: Path) -> dict[str, list[str]]:
    """Resolver call sites by spelling -> ``path:line`` (defs excluded by AST)."""
    sites: dict[str, list[str]] = {}
    for py, tree in _iter_python(root):
        rel = py.relative_to(PROJECT_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _called_name(node)
            if name and name.endswith("_for_capability"):
                sites.setdefault(name, []).append(f"{rel}:{node.lineno}")
    return sites


def test_resolver_surface_is_the_enumerated_five():
    """A new spelling must not slip in unnamed — that is how #1980 happened."""
    defined = _definitions(PROD_ROOT)
    assert defined == set(RESOLVER_SURFACE), (
        "The capability resolver surface changed.\n"
        f"  defined in production : {sorted(defined)}\n"
        f"  enumerated here       : {sorted(RESOLVER_SURFACE)}\n"
        "Any doc or audit that greps ONE spelling is now measuring an unknown "
        "fraction of the resolver. Update CLAUDE.md's capability paragraph "
        "together with this set."
    )


def test_typed_variants_have_no_production_callers():
    """The half of the partition that IS a test idiom — pinned as such."""
    prod = _call_sites(PROD_ROOT)
    offenders = {name: prod[name] for name in TYPED_VARIANTS if prod.get(name)}
    assert not offenders, (
        "A typed resolver variant gained a production caller: "
        f"{offenders}\n"
        "The partition CLAUDE.md documents (production resolves only through "
        f"the untyped {UNTYPED_RESOLVER!r}) no longer holds — revise it. "
        "If you got here implementing RESTITUTION_REPORT_SPEC.md §wiring or "
        "SPECTACULAR_ANALYSIS_SPEC.md §1 — both prescribe the typed variants — "
        "this red is the decision point, not a bug: either use "
        f"{UNTYPED_RESOLVER!r} like the rest of production, or move the "
        "variant out of TYPED_VARIANTS and update CLAUDE.md's partition with it."
    )
    # Non-vacuity: these names must still be a live test idiom, otherwise the
    # guard above passes because nobody calls them anywhere.
    in_tests = sum(
        len(_call_sites(TESTS_ROOT).get(name, [])) for name in TYPED_VARIANTS
    )
    assert in_tests > 0, (
        "No test calls the typed variants either. The guard above is now "
        "vacuous — it would pass on a codebase where the resolver was deleted."
    )


def test_untyped_resolver_carries_phase_resolution():
    """The other half: production DOES resolve, and through workflow_dsl."""
    prod = _call_sites(PROD_ROOT)
    sites = prod.get(UNTYPED_RESOLVER, [])
    assert sites, (
        f"No production call to {UNTYPED_RESOLVER!r}. Production no longer "
        "resolves capabilities through the registry — that is an architectural "
        "event, not a doc drift."
    )
    dsl = [s for s in sites if "orchestration/workflow_dsl.py" in s]
    assert dsl, (
        f"{UNTYPED_RESOLVER!r} is called in production but no longer from "
        "workflow_dsl.py, which is where phase.capability is resolved at run "
        f"time. Call sites found: {sites}"
    )
