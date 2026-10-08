"""#2993 — every caller of :func:`ModalHandler.is_modal_kb_consistent`
either builds its KB through :func:`build_modal_kb` (the one legaliser,
#2471) or carries an explicit reason in the census row.

The defect (paid run 07/10, doc_A): ``MlParser`` reads the OPENING lines of
a belief base as its signature section — a raw ``"\\n".join(formulas)`` has
the first formula parsed as a sort declaration and the whole KB rejected
(``Illegal characters in sort definition``), so the lane returned honest
``None`` (degraded) on every NL-translated base. Two production sites fed
raw or hand-declared KBs at the #2993 fix: the external modal lane
(``_invoke_external_modal_solver`` — both its SPASS branch and its
TweetyBridge fallback raw-joined), and ``ModalLogicAgent.validate_argument``
(inline ``type()`` loop that declared reserved words, missed
uppercase-initial atoms and emitted illegal ``type(heavy_rain)``
identifiers). Both now build through ``build_modal_kb``.

The remaining rows are reason-only: ``_invoke_modal_logic`` builds through
on its nl path (#1224/#2471) and joins its pre-typed direct-formulas input
verbatim by design; ``text_to_belief_set`` builds through
``_construct_modal_kb_from_json`` which declares but does not legalise —
``ModalHandler``'s parse-point normaliser (#1326) is the legaliser of record
for that path (verdict comment on site); ``is_consistent`` and the
``TweetyBridge.check_consistency`` wrapper are pure consumers/routes of an
already-built base.

The census keys on ``(module, enclosing function)`` — stable under line
shifts — and for every row that CLAIMS the legaliser, the guard re-checks
that ``build_modal_kb`` actually appears in that function's source: a claim
the guard verifies, never trusts. It fails when a new caller appears that
is neither fixed nor listed (``missing``), when a row outlives its caller
(``stale``), or when a "builds through" row loses its legaliser
(``claim broken``).
"""

import ast
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
SEARCH_ROOTS = (REPO_ROOT / "argumentation_analysis",)

# Paths excluded from the census: nothing production-side is excluded today —
# the legaliser itself does not call ``is_modal_kb_consistent`` (it IS the
# parse-point normaliser surface), and the handler's own ``def`` is a
# FunctionDef, not an Attribute access, so it is skipped naturally.
_EXCLUDE_DIR_NAMES = {"_archives", "docs", ".claude"}


def _iter_python_files() -> Iterator[Path]:
    for root in SEARCH_ROOTS:
        for path in root.rglob("*.py"):
            if any(part in _EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            yield path


def _uses(tree: ast.AST) -> List[Tuple[str, ast.Attribute]]:
    """Collect ``(enclosing_function, node)`` for every attribute access to
    ``is_modal_kb_consistent``.

    A method REFERENCE passed as an argument (``asyncio.to_thread(handler.
    is_modal_kb_consistent, ...)``) is an Attribute node exactly like a
    direct call — both are uses and both are collected. Mentions inside
    strings (``hasattr(obj, "is_modal_kb_consistent")``, docstrings,
    comments) are Constants, not Attribute nodes, and are skipped naturally.
    """
    found: List[Tuple[str, ast.Attribute]] = []

    def _visit(node: ast.AST, func: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = func
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
            if (
                isinstance(child, ast.Attribute)
                and child.attr == "is_modal_kb_consistent"
            ):
                found.append((func, child))
            _visit(child, name)

    _visit(tree, "<module>")
    return found


def census() -> Dict[Tuple[str, str], str]:
    """Every production use, keyed by ``(relpath, enclosing_function)``."""
    found: Dict[Tuple[str, str], str] = {}
    for path in _iter_python_files():
        relpath = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for func, node in _uses(tree):
            found[(relpath, func)] = f"line {node.lineno}"
    return found


# ALLOWED rows — (module, function) -> (builds_through, reason).
# builds_through=True means the guard RE-CHECKS that the function's own
# source contains ``build_modal_kb`` (the claim is verified, not trusted).
# A new call site without a row fails as ``missing``; a row whose caller is
# gone fails as ``stale`` — delete the row, do not keep dead debt.

ALLOWED: Dict[Tuple[str, str], Tuple[bool, str]] = {
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "_invoke_modal_logic",
    ): (
        True,
        "nl path builds belief_set_str via build_modal_kb (#1224/#2471); the "
        "direct-formulas path joins verbatim BY DESIGN — those KBs are "
        "pre-typed (already carry their declarations), re-legalising would "
        "rename declared atoms a second time",
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "_invoke_external_modal_solver",
    ): (
        True,
        "#2993/R1076: the external lane's SPASS branch AND TweetyBridge "
        "fallback both build via build_modal_kb; the fallback decides "
        "CONSISTENCY through the bridge's modal routing (check_consistency, "
        "tri-state #1634) — the pre-rework execute_modal_query(kb, kb) "
        "passed the KB as the QUERY and could never render a consistency "
        "verdict (KB ⊨ KB holds for every KB); when the modal translation "
        "produced no formulas the lane sends nothing "
        "(unavailable:no-translation)",
    ),
    (
        "argumentation_analysis/plugins/tweety_logic_plugin.py",
        "check_modal_satisfiability",
    ): (
        True,
        "#2993: single-formula wrapper builds via build_modal_kb([formula]); "
        "the verdict echoes the ORIGINAL formula, not the legalised one",
    ),
    (
        "argumentation_analysis/agents/core/logic/modal_logic_agent.py",
        "validate_argument",
    ): (
        True,
        "#2993: the temporary KB {premises + ¬conclusion} builds via "
        "build_modal_kb — the previous inline type() loop declared reserved "
        "words (type(implies)), missed uppercase-initial atoms and emitted "
        "illegal type(heavy_rain) identifiers",
    ),
    (
        "argumentation_analysis/agents/core/logic/tweety_bridge.py",
        "check_consistency",
    ): (
        False,
        "routing wrapper by logic_type — the base is opaque here; "
        "legalisation is the CALLER's responsibility, and every modal caller "
        "of this wrapper is itself a census row",
    ),
    (
        "argumentation_analysis/agents/core/logic/modal_logic_agent.py",
        "text_to_belief_set",
    ): (
        False,
        "content from _construct_modal_kb_from_json: declares type(prop) "
        "(#1213) but does NOT legalise identifiers — the #2993 verdict "
        "comment on site names ModalHandler's parse-point normaliser (#1326) "
        "as the legaliser of record for this path; double-legalising here "
        "would add a second regime for no measured gain",
    ),
    (
        "argumentation_analysis/agents/core/logic/modal_logic_agent.py",
        "is_consistent",
    ): (
        False,
        "pure consumer of an already-built belief_set.content — no "
        "construction happens here; the producers are census rows and the "
        "parse-point normaliser legalises whatever reaches the parser",
    ),
}


def _function_source(relpath: str, func_name: str) -> str:
    """Source text of ``func_name`` in ``relpath`` (repo-relative)."""
    path = REPO_ROOT / relpath
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                lines = path.read_text(encoding="utf-8").splitlines()
                return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    raise AssertionError(f"function {func_name} not found in {relpath}")


def test_every_caller_of_is_modal_kb_consistent_is_registered():
    """The gate: census == ALLOWED keys, both directions."""
    found = census()
    missing = sorted(set(found) - set(ALLOWED))
    stale = sorted(set(ALLOWED) - set(found))
    lines: list[str] = []
    if missing:
        shown = [
            f"  {mod} :: {func} ({found[(mod, func)]})" for mod, func in missing[:20]
        ]
        lines.append(
            "NEW is_modal_kb_consistent caller(s) not in ALLOWED — build the "
            "KB through build_modal_kb, or register a row with the reason:\n"
            + "\n".join(shown)
            + (f"\n  … and {len(missing) - 20} more" if len(missing) > 20 else "")
        )
    if stale:
        shown = [f"  {mod} :: {func}" for mod, func in stale[:20]]
        lines.append(
            "STALE ALLOWED row(s) — no such caller in the census (fixed, "
            "renamed or deleted); delete the row:\n"
            + "\n".join(shown)
            + (f"\n  … and {len(stale) - 20} more" if len(stale) > 20 else "")
        )
    assert not lines, "\n\n".join(lines)


def test_rows_claiming_the_legaliser_actually_use_it():
    """A builds_through=True row is re-checked against the function's source:
    the claim that the KB passes through ``build_modal_kb`` is verified, not
    trusted — a refactor that drops the legaliser while keeping the row
    reddens here."""
    broken: list[str] = []
    for (mod, func), (builds, _reason) in sorted(ALLOWED.items()):
        if not builds:
            continue
        source = _function_source(mod, func)
        if "build_modal_kb" not in source:
            broken.append(f"  {mod} :: {func} claims the legaliser, source has none")
    assert not broken, "\n".join(broken)
