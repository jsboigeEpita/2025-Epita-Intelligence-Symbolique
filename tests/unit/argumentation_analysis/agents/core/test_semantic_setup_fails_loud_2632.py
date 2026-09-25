"""#2632: registering an agent's semantic functions, and resolving its service's
prompt settings, fail loud.

Before #2632, five setups (PL agent, modal agent, PM agent, ``setup_pm_kernel``,
``setup_pl_kernel``, ``setup_informal_kernel``) and the extract verifier wrapped
``kernel.add_function`` / ``get_prompt_execution_settings_from_service_id`` in an
``except`` that logged and carried on. The agent then existed without its
functions, or ran them on the kernel's default settings instead of its
service's. Measured on ``main`` ``448e900e1``: a PL, modal or PM agent named
``"<X>-Agent"`` (a valid Semantic Kernel agent name, an invalid plugin name) is
built with **no** semantic function at all, and a modal agent given a service id
the kernel does not hold is built on default settings.

Two layers of test:

* one witness per module, each red on ``main``: a real ``Kernel`` and a real
  registration failure make construction or setup raise ``SemanticSetupError``,
  naming what was configured and what failed;
* a father guard: an AST census over every tracked production ``.py`` file.
  No call to either method may sit in the body of a ``try`` whose handlers
  swallow (no ``raise``). The census prints its population and fails on any
  file it cannot parse, rather than skipping it.
"""

import ast
import subprocess
import types
from pathlib import Path

import pytest
import semantic_kernel as sk
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.exceptions import KernelServiceNotFoundError
from semantic_kernel.functions import kernel_function

from argumentation_analysis.agents.core.semantic_setup import SemanticSetupError

REPO = Path(__file__).resolve().parents[5]

CALLEES = {"add_function", "get_prompt_execution_settings_from_service_id"}

# Sites allowed behind a handler that does not raise, as
# (file, enclosing function, callee) -> the issue that owns them. Empty since
# #2648 moved the deep-synthesis lookups out of their chat-call handlers. An
# entry that no longer matches reddens, so the map cannot outlive its sites.
DEGRADE_AT_INVOCATION = {}


def _kernel(service_id="svc"):
    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(service_id=service_id, ai_model_id="m", api_key="dummy")
    )
    return kernel


def _ready_bridge():
    # The PL constructor reads only ``initializer.is_jvm_ready()`` from the
    # bridge; the witnesses test registration, not Tweety.
    return types.SimpleNamespace(
        initializer=types.SimpleNamespace(is_jvm_ready=lambda: True)
    )


def _functions(kernel):
    return {name: sorted(plugin.functions) for name, plugin in kernel.plugins.items()}


def _raise_not_found(self, service_id, *args, **kwargs):
    raise KernelServiceNotFoundError(f"no settings for '{service_id}' (#2632)")


# --- witnesses, one per module ------------------------------------------------


class TestPropositionalAgent:
    def test_a_name_the_kernel_rejects_as_plugin_raises(self):
        from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
            PropositionalLogicAgent,
        )

        with pytest.raises(SemanticSetupError, match=r"PL-Agent\.TextToPLDefs"):
            PropositionalLogicAgent(
                _kernel(),
                agent_name="PL-Agent",
                service_id="svc",
                tweety_bridge=_ready_bridge(),
            )

    def test_a_settings_failure_raises(self, monkeypatch):
        from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
            PropositionalLogicAgent,
        )

        # The service exists (the base agent resolves it through get_service);
        # only its settings lookup fails.
        monkeypatch.setattr(
            Kernel, "get_prompt_execution_settings_from_service_id", _raise_not_found
        )
        with pytest.raises(SemanticSetupError, match="'svc'"):
            PropositionalLogicAgent(
                _kernel(), service_id="svc", tweety_bridge=_ready_bridge()
            )

    def test_a_valid_setup_registers_every_function(self):
        from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
            PropositionalLogicAgent,
        )

        agent = PropositionalLogicAgent(
            _kernel(), service_id="svc", tweety_bridge=_ready_bridge()
        )
        assert _functions(agent.kernel) == {
            "PropositionalLogicAgent": [
                "GeneratePLQueryIdeas",
                "InterpretPLResults",
                "TextToPLDefs",
                "TextToPLFormulas",
            ]
        }


class TestModalAgent:
    def test_a_service_id_the_kernel_lacks_raises(self):
        from argumentation_analysis.agents.core.logic.modal_logic_agent import (
            ModalLogicAgent,
        )

        # Since #2627 the id reaches BaseAgent, which refuses it before the
        # settings lookup: either way the agent is never built on the
        # kernel's default settings.
        with pytest.raises(ValueError, match="'absent'"):
            ModalLogicAgent(
                _kernel("default"), service_id="absent", tweety_bridge=_ready_bridge()
            )

    def test_a_name_the_kernel_rejects_as_plugin_raises(self):
        from argumentation_analysis.agents.core.logic.modal_logic_agent import (
            ModalLogicAgent,
        )

        with pytest.raises(
            SemanticSetupError, match=r"Modal-Agent\.TextToModalBeliefSet"
        ):
            ModalLogicAgent(
                _kernel("default"),
                agent_name="Modal-Agent",
                service_id="default",
                tweety_bridge=_ready_bridge(),
            )


class TestProjectManagerAgent:
    def test_a_name_the_kernel_rejects_as_plugin_raises(self):
        from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent

        agent = ProjectManagerAgent(_kernel("default"), agent_name="PM-Agent")
        with pytest.raises(
            SemanticSetupError, match=r"PM-Agent\.DefineTasksAndDelegate"
        ):
            agent.setup_agent_components("default")


class TestSetupPmKernel:
    def test_a_service_id_the_kernel_lacks_raises(self):
        from argumentation_analysis.agents.core.pm.pm_definitions import (
            setup_pm_kernel,
        )

        with pytest.raises(SemanticSetupError, match="'absent'"):
            setup_pm_kernel(Kernel(), types.SimpleNamespace(service_id="absent"))

    def test_a_prompt_the_kernel_rejects_raises(self, monkeypatch):
        from argumentation_analysis.agents.core.pm import pm_definitions

        monkeypatch.setattr(pm_definitions, "prompt_define_tasks_v12", "")
        with pytest.raises(
            SemanticSetupError, match=r"PM\.semantic_DefineTasksAndDelegate"
        ):
            pm_definitions.setup_pm_kernel(Kernel(), None)


class _PLPluginStandIn:
    """The native facade ``setup_pl_kernel`` expects, without Tweety."""

    _jvm_ok = True

    @kernel_function(name="execute_pl_query")
    def execute_pl_query(self, belief_set_content: str, query_string: str) -> str:
        return ""


class TestSetupPlKernel:
    @pytest.fixture(autouse=True)
    def _jvm_free(self, monkeypatch):
        from argumentation_analysis.agents.core.pl import pl_definitions

        monkeypatch.setattr(pl_definitions.jpype, "isJVMStarted", lambda: True)
        monkeypatch.setattr(
            pl_definitions, "PropositionalLogicPlugin", _PLPluginStandIn
        )

    def test_a_service_id_the_kernel_lacks_raises(self):
        from argumentation_analysis.agents.core.pl.pl_definitions import (
            setup_pl_kernel,
        )

        with pytest.raises(SemanticSetupError, match="'absent'"):
            setup_pl_kernel(Kernel(), types.SimpleNamespace(service_id="absent"))

    def test_a_prompt_the_kernel_rejects_raises(self, monkeypatch):
        from argumentation_analysis.agents.core.pl import pl_definitions

        monkeypatch.setattr(pl_definitions, "prompt_gen_pl_queries_v8", "")
        with pytest.raises(
            SemanticSetupError, match=r"PLAnalyzer\.semantic_GeneratePLQueries"
        ):
            pl_definitions.setup_pl_kernel(Kernel(), None)


class TestSetupInformalKernel:
    def test_a_service_id_the_kernel_lacks_raises(self):
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            setup_informal_kernel,
        )

        with pytest.raises(SemanticSetupError, match="'absent'"):
            setup_informal_kernel(Kernel(), types.SimpleNamespace(service_id="absent"))

    def test_a_prompt_the_kernel_rejects_raises(self, monkeypatch):
        from argumentation_analysis.agents.core.informal import informal_definitions

        kernel = _kernel()
        monkeypatch.setattr(
            informal_definitions, "prompt_analyze_fallacies_v3_tool_use", ""
        )
        with pytest.raises(
            SemanticSetupError, match=r"InformalAnalyzer\.semantic_AnalyzeFallacies"
        ):
            informal_definitions.setup_informal_kernel(
                kernel, types.SimpleNamespace(service_id="svc")
            )


class TestVerifyExtractsEvaluationAgent:
    async def test_a_settings_failure_raises(self, tmp_path, monkeypatch):
        import importlib

        monkeypatch.chdir(tmp_path)  # the module adds a FileHandler at import
        module = importlib.import_module(
            "argumentation_analysis.utils.extract_repair.verify_extracts_with_llm"
        )
        monkeypatch.setattr(
            sk.Kernel, "get_prompt_execution_settings_from_service_id", _raise_not_found
        )
        service = OpenAIChatCompletion(
            service_id="test_eval", ai_model_id="test-model", api_key="dummy-key"
        )
        with pytest.raises(SemanticSetupError, match="EvaluationAgent"):
            await module.setup_evaluation_agent(service)


# --- father guard: no setup call behind a swallowing handler -------------------


def _enclosing_function(node, parents):
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur.name
    return "<module>"


def _swallows(try_node):
    return any(
        not any(isinstance(n, ast.Raise) for n in ast.walk(handler))
        for handler in try_node.handlers
    )


def census(source, path):
    """Every call to a CALLEES method in ``source``, with whether any enclosing
    ``try`` (the call in its body) has a handler that does not raise."""
    tree = ast.parse(source)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    rows = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in CALLEES
        ):
            continue
        swallowed, cur = False, node
        while cur in parents:
            parent = parents[cur]
            if isinstance(parent, ast.Try) and cur in parent.body and _swallows(parent):
                swallowed = True
                break
            cur = parent
        rows.append(
            (path, _enclosing_function(node, parents), node.func.attr, swallowed)
        )
    return rows


def _production_files():
    listed = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [
        f
        for f in listed
        if not f.startswith(("tests/", "docs/"))
        and "/_archives/" not in f
        and "/archives/" not in f
    ]


def test_the_census_detects_a_swallow_and_passes_a_reraise():
    swallowing = (
        "def f(k):\n"
        "    try:\n"
        "        k.add_function(prompt='p', plugin_name='a', function_name='b')\n"
        "    except Exception as e:\n"
        "        log(e)\n"
    )
    nested = (
        "def g(k):\n"
        "    try:\n"
        "        try:\n"
        "            k.get_prompt_execution_settings_from_service_id('s')\n"
        "        except KeyError:\n"
        "            raise\n"
        "    except Exception:\n"
        "        pass\n"
    )
    reraising = (
        "def h(k):\n"
        "    try:\n"
        "        k.add_function(prompt='p', plugin_name='a', function_name='b')\n"
        "    except Exception as e:\n"
        "        raise RuntimeError('x') from e\n"
    )
    in_handler = (
        "def i(k):\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        k.add_function(prompt='p', plugin_name='a', function_name='b')\n"
    )
    assert census(swallowing, "s") == [("s", "f", "add_function", True)]
    assert census(nested, "n") == [
        ("n", "g", "get_prompt_execution_settings_from_service_id", True)
    ]
    assert census(reraising, "r") == [("r", "h", "add_function", False)]
    assert census(in_handler, "i") == [("i", "i", "add_function", False)]


def test_no_setup_call_sits_behind_a_swallowing_handler():
    files = _production_files()
    rows, unparsed = [], []
    for rel in files:
        try:
            source = (REPO / rel).read_text(encoding="utf-8-sig")
            rows.extend(census(source, rel))
        except (SyntaxError, UnicodeDecodeError) as e:
            unparsed.append(f"{rel}: {type(e).__name__}")
    print(f"census: {len(files)} tracked production files, {len(rows)} calls")
    assert not unparsed, f"files the census could not read: {unparsed}"
    # Positive control: the helper's own two calls are seen, and not as
    # swallowed; without them a zero below would prove nothing.
    helper = "argumentation_analysis/agents/core/semantic_setup.py"
    assert sorted((r[2], r[3]) for r in rows if r[0] == helper) == [
        ("add_function", False),
        ("get_prompt_execution_settings_from_service_id", False),
    ]

    swallowed = {(path, fn, callee) for path, fn, callee, sw in rows if sw}
    unexpected = sorted(swallowed - set(DEGRADE_AT_INVOCATION))
    stale = sorted(set(DEGRADE_AT_INVOCATION) - swallowed)
    assert not unexpected, (
        "setup calls behind a handler that does not raise — route them through "
        f"agents/core/semantic_setup.py: {unexpected}"
    )
    assert not stale, f"DEGRADE_AT_INVOCATION entries no longer present: {stale}"
