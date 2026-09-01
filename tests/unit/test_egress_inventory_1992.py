"""#1992 — egress inventory guard.

The fix that closed #1988 / #1992 added ``@pytest.mark.requires_api`` to
``tests/integration/triage/test_agent_family.py`` (PR #1993). The path
that produced the bug was structural: tests that need a real LLM were
guarded only by ``@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"),
...)``. That ``skipif`` is a **runtime** barrier — it skips the test
when the key is absent. It is NOT a **selector** — the CI argv
``-m "not slow and not requires_api"`` does not see it, so the test is
collected (and runs, if the key happens to be in the env) in the free
lane, where it fires real POSTs to ``api.openai.com``.

The fix replaces the ``skipif``-alone with a ``pytestmark`` list that
includes ``pytest.mark.requires_api``. The marker is the selector — it
moves the test to the API lane.

This guard verifies the **relation**: in ``tests/integration/triage/``,
every test function whose decorator list contains an
``OPENAI_API_KEY``-gated ``skipif`` must ALSO carry
``@pytest.mark.requires_api`` (or ``requires_openai``) either as a
function decorator or via the module-level ``pytestmark``.

Adding a new real-LLM test under ``triage/`` without the marker reopens
#1992. The guard pins that.

Negative control (subprocess, see ``scratchpad/probe_egress_inventory_1992.py``):
a tmp_path tree containing a fake ``test_xxx.py`` with the bad shape
makes the guard redden. Live tree is GREEN.
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_jvm_session


TRIAGE_DIR = Path(__file__).resolve().parents[2] / "tests" / "integration" / "triage"


def _decorators_strings(node: ast.AST) -> list:
    out = []
    for d in node.decorator_list:
        try:
            out.append(ast.unparse(d))
        except Exception:
            out.append(repr(d))
    return out


def _module_pytestmark(tree: ast.Module) -> list:
    """Module-level ``pytestmark = [...]`` or ``pytestmark = mark.X(...)``.

    Returns a list of decorator strings.
    """
    out = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "pytestmark":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            try:
                                out.append(ast.unparse(elt))
                            except Exception:
                                out.append(repr(elt))
                    else:
                        try:
                            out.append(ast.unparse(node.value))
                        except Exception:
                            out.append(repr(node.value))
    return out


def _has_openai_key_skipif(decorators: list) -> bool:
    """True if any decorator is a skipif gating on OPENAI_API_KEY
    absence. Pattern matches the #1988/#1992 shape exactly.
    """
    for d in decorators:
        if "skipif" not in d:
            continue
        if "OPENAI_API_KEY" not in d:
            continue
        if "not os.getenv" in d or "!=" in d:
            return True
    return False


def _has_requires_marker(decorators: list) -> bool:
    """True if any decorator mentions requires_api or requires_openai."""
    for d in decorators:
        if "requires_api" in d or "requires_openai" in d:
            return True
    return False


def _collect_tests(tree: ast.Module):
    """Yield (function_node, enclosing_class_name_or_None) for every
    def test_*/async test_* in the module, walking into class bodies.
    """

    def _walk(node, cls):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                yield from _walk(child, node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                yield (node, cls)

    for stmt in tree.body:
        yield from _walk(stmt, None)


def _test_body_invokes_llm(node: ast.AST) -> bool:
    """Heuristic: does the test body contain a real LLM invocation?

    Looks for direct calls OR attribute calls OR await calls whose
    chain name contains an LLM-invocation pattern. ``asyncio.run``
    wrapping is also counted (the awaited coroutine is inside the
    call). A test that only constructs an agent (factory.create_*_agent,
    isinstance checks, hasattr probes) returns False.

    Patterns considered as LLM invocations:
    - ``analyze_text``, ``invoke``, ``invoke_async``, ``get_chat_message_contents``,
      ``add_chat_message``, ``chat_completion``, ``get_current_case_description``
    - ``run_analysis_async`` (Orchestrator.run_analysis_async)
    - any await whose func chain name contains those substrings
    """
    INVOCATION_SUBSTRINGS = (
        "analyze_text",
        "invoke_async",
        "invoke(",
        "get_chat_message_contents",
        "add_chat_message",
        "chat_completions.create",
        "chat_completion(",
        "get_current_case_description",
        "run_analysis_async",
    )

    def _chain_contains_invocation(func_node: ast.AST) -> bool:
        try:
            rendered = ast.unparse(func_node)
        except Exception:
            return False
        return any(sub in rendered for sub in INVOCATION_SUBSTRINGS)

    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if _chain_contains_invocation(sub.func):
                return True
        elif isinstance(sub, ast.Await):
            # ``await x.invoke(...)`` — the value's chain name appears
            # as the Await's ``value`` which is a Call node.
            if isinstance(sub.value, ast.Call):
                if _chain_contains_invocation(sub.value.func):
                    return True
            elif isinstance(sub.value, ast.Attribute):
                # ``await obj.attr`` — chain ends at .attr.
                chain = ast.unparse(sub.value)
                if any(sub in chain for sub in INVOCATION_SUBSTRINGS):
                    return True
    return False


def _scan_triage_for_orphans(triage_dir=TRIAGE_DIR):
    """Return list of (file_path, qualified_test_name, decorator_strs)
    for every test in ``triage_dir`` whose decorators include an
    OPENAI_API_KEY-gated ``skipif`` but no ``requires_api`` marker,
    AND whose body makes a real LLM invocation.

    Pure-creation tests (factory.create_*_agent, isinstance, hasattr)
    are excluded — they do not egress even with a key in env.
    """
    orphans = []
    for fp in sorted(triage_dir.glob("test_*.py")):
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            tree = ast.parse(src, filename=str(fp))
        except SyntaxError:
            continue
        module_marks = _module_pytestmark(tree)
        for node, cls in _collect_tests(tree):
            decorators = module_marks + _decorators_strings(node)
            if not _has_openai_key_skipif(decorators):
                continue
            if _has_requires_marker(decorators):
                continue
            if not _test_body_invokes_llm(node):
                continue
            qualified = f"{cls}.{node.name}" if cls else node.name
            orphans.append((fp, qualified, _decorators_strings(node)))
    return orphans


# ---------------------------------------------------------------------------
# The relation guard
# ---------------------------------------------------------------------------


class TestEgressInventory:
    """The guard: in triage/, every test that gates on OPENAI_API_KEY
    absence must also carry a requires_api selector. #1988 / #1992.
    """

    def test_no_openai_key_skipif_without_requires_marker(self):
        orphans = _scan_triage_for_orphans()
        if not orphans:
            return  # GREEN path
        details = "\n".join(
            f"  {fp.relative_to(TRIAGE_DIR)}::{qname}  decorators={decs}"
            for fp, qname, decs in orphans
        )
        pytest.fail(
            f"#1992: {len(orphans)} test(s) in triage/ have an "
            f"OPENAI_API_KEY skipif but no @pytest.mark.requires_api. "
            f"Each must carry the marker (or be moved out of triage/). "
            f"#1988 / #1879 path: skipif alone does not deselect from "
            f"the CI gate, real POSTs leak through.\n{details}"
        )

    def test_triage_dir_exists(self):
        assert (
            TRIAGE_DIR.is_dir()
        ), f"triage/ dir not found at expected location: {TRIAGE_DIR}"

    def test_scan_is_deterministic(self):
        """Run the scan twice and compare — guards against the scan
        itself depending on filesystem ordering."""
        a = _scan_triage_for_orphans()
        b = _scan_triage_for_orphans()
        assert a == b


# ---------------------------------------------------------------------------
# Negative control — must redden on a mutation that introduces the bad shape
# ---------------------------------------------------------------------------


def _write_fake_triage(tmp_path):
    """Create a tmp_path tree with one fake test file that exhibits the
    #1992 shape (skipif without requires_api) AND a body that invokes
    the LLM, and one good file. Return the path to inject as the triage dir.
    """
    fake_dir = tmp_path / "triage"
    fake_dir.mkdir()
    bad = fake_dir / "test_bad_shape_1992.py"
    bad.write_text(
        "import pytest\n"
        "import os\n"
        "\n"
        "@pytest.mark.skipif(\n"
        '    not os.getenv("OPENAI_API_KEY"),\n'
        '    reason="needs key",\n'
        ")\n"
        "def test_real_llm_call():\n"
        "    # Real LLM invocation — must carry the marker.\n"
        '    return asyncio.run(orchestrator.run_analysis_async("hello"))\n',
        encoding="utf-8",
    )
    good = fake_dir / "test_good_shape_1992.py"
    good.write_text(
        "import pytest\n"
        "import os\n"
        "\n"
        "pytestmark = [\n"
        "    pytest.mark.requires_api,\n"
        "    pytest.mark.skipif(\n"
        '        not os.getenv("OPENAI_API_KEY"),\n'
        '        reason="needs key",\n'
        "    ),\n"
        "]\n"
        "def test_real_llm_call_marked():\n"
        '    return asyncio.run(orchestrator.run_analysis_async("hello"))\n',
        encoding="utf-8",
    )
    return fake_dir


def test_mutation_orphan_shape_reddens(tmp_path):
    """Negative control: write a fake triage/ with a test that has the
    ``skipif``-only shape and verify the scanner catches it.
    """
    fake_dir = _write_fake_triage(tmp_path)
    orphans = _scan_triage_for_orphans(fake_dir)
    assert orphans, (
        "Scanner missed the bad shape — the guard cannot catch #1992 "
        "regressions. Refactor _scan_triage_for_orphans."
    )
    bad = [qname for _, qname, _ in orphans]
    assert "test_real_llm_call" in bad, f"Scanner flagged the wrong function: {bad}"


def test_mutation_good_shape_does_not_redden(tmp_path):
    """A tree of only-good files must yield an empty orphan list."""
    fake_dir = tmp_path / "triage"
    fake_dir.mkdir()
    good = fake_dir / "test_only_good.py"
    good.write_text(
        "import pytest\n"
        "import os\n"
        "\n"
        "pytestmark = [\n"
        "    pytest.mark.requires_api,\n"
        "    pytest.mark.skipif(\n"
        '        not os.getenv("OPENAI_API_KEY"),\n'
        '        reason="needs key",\n'
        "    ),\n"
        "]\n"
        "def test_real_llm_call_marked():\n"
        "    pass\n",
        encoding="utf-8",
    )
    orphans = _scan_triage_for_orphans(fake_dir)
    assert not orphans, f"Scanner false-positived on the good shape: {orphans}"
