"""#2641 — the logic-agent contract has one calling convention.

``BaseLogicAgent`` and its three production subclasses disagreed, method by
method, on whether each contract method is a coroutine. Each consumer was
written against one agent, so each worked for that agent only. The unified
pipeline's formal mode awaited ``is_consistent`` and ``execute_query`` and failed
for the propositional and modal agents. ``_handle_query_task`` awaited neither
``execute_query`` nor ``interpret_results`` and failed for FOL. #2360 had
aligned one method of the same split.

The convention is declared on ``BaseLogicAgent``. These guards hold it there:
every override keeps the declared kind, and no production call of a workflow
method on a logic agent is left unawaited.
"""

import ast
import inspect
import subprocess
from pathlib import Path

import pytest

from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import (
    FirstOrderBeliefSet,
    PropositionalBeliefSet,
)
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
    PropositionalLogicAgent,
)
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

ROOT = Path(__file__).resolve().parents[6]
PRODUCTION_ROOTS = [
    "argumentation_analysis",
    "api",
    "interface_web",
    "scripts",
    "examples",
    "project_core",
    "services",
]
AGENT_BASES = "argumentation_analysis/agents/core/abc/agent_bases.py"
WORKFLOW = (
    "text_to_belief_set",
    "generate_queries",
    "execute_query",
    "is_consistent",
    "interpret_results",
)
HELPERS = ("validate_formula", "_create_belief_set_from_data")

# Unawaited calls of a workflow method's NAME on a receiver that is not a logic
# agent. Exact: a new site reddens, and so does an entry that no longer exists.
HOMONYMS = {
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "atms",
        "is_consistent",
    ): 2,
    ("argumentation_analysis/plugins/atms_plugin.py", "atms", "is_consistent"): 1,
    (
        "argumentation_analysis/plugins/tweety_logic_plugin.py",
        "handler",
        "is_consistent",
    ): 1,
}


def _production_trees():
    files = subprocess.run(
        ["git", "ls-files", "--", *[f"{r}/*.py" for r in PRODUCTION_ROOTS]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    trees, unparsed = {}, []
    for rel in files:
        try:
            trees[rel] = ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))
        except SyntaxError:
            unparsed.append(rel)
    assert not unparsed, f"files the census cannot read: {unparsed}"
    return trees


def _classes(trees):
    found = {}
    for rel, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b).split(".")[-1] for b in node.bases]
                found.setdefault(node.name, []).append((rel, bases, node))
    return found


def _logic_agent_classes(classes):
    names = {"BaseLogicAgent"}
    grew = True
    while grew:
        grew = False
        for name, defs in classes.items():
            if name not in names and any(set(b) & names for _, b, _ in defs):
                names.add(name)
                grew = True
    return names


def _methods(class_node):
    return {
        n.name: isinstance(n, ast.AsyncFunctionDef)
        for n in class_node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _declared_kinds(classes):
    # BaseAgent first, BaseLogicAgent over it: what a logic agent inherits.
    kinds = {}
    for base in ("BaseAgent", "BaseLogicAgent"):
        _, _, node = next(d for d in classes[base] if d[0] == AGENT_BASES)
        kinds.update(_methods(node))
    return kinds


TREES = _production_trees()
CLASSES = _classes(TREES)
LOGIC_AGENTS = _logic_agent_classes(CLASSES)


def test_the_census_sees_the_three_production_agents():
    assert {
        "FOLLogicAgent",
        "PropositionalLogicAgent",
        "ModalLogicAgent",
    } <= LOGIC_AGENTS


@pytest.mark.parametrize("name", WORKFLOW)
def test_workflow_methods_are_declared_coroutines(name):
    assert inspect.iscoroutinefunction(getattr(BaseLogicAgent, name))


@pytest.mark.parametrize("name", HELPERS)
def test_helpers_are_declared_plain_functions(name):
    assert not inspect.iscoroutinefunction(getattr(BaseLogicAgent, name))


@pytest.mark.parametrize("agent", sorted(LOGIC_AGENTS - {"BaseLogicAgent"}))
def test_every_override_keeps_the_declared_kind(agent):
    declared = _declared_kinds(CLASSES)
    drift = []
    for rel, _, node in CLASSES[agent]:
        for method, is_async in _methods(node).items():
            if method in declared and declared[method] != is_async:
                want = "async def" if declared[method] else "def"
                drift.append(f"{rel}: {agent}.{method} should be `{want}`")
    assert not drift, "\n".join(drift)


def _unawaited_workflow_calls():
    sites = {}
    for rel, tree in TREES.items():
        parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in WORKFLOW
                and not isinstance(parents.get(node), ast.Await)
            ):
                continue
            receiver = ast.unparse(node.func.value)
            if receiver == "self":
                owner = parents.get(node)
                while owner is not None and not isinstance(owner, ast.ClassDef):
                    owner = parents.get(owner)
                if owner is None or owner.name not in LOGIC_AGENTS:
                    continue  # a method of the enclosing class, not of an agent
            key = (rel, receiver, node.func.attr)
            sites[key] = sites.get(key, 0) + 1
    return sites


def test_no_workflow_call_on_a_logic_agent_is_left_unawaited():
    sites = _unawaited_workflow_calls()
    unexpected = {k: v for k, v in sites.items() if k not in HOMONYMS}
    stale = {k: v for k, v in HOMONYMS.items() if sites.get(k) != v}
    assert not unexpected, f"unawaited workflow calls: {unexpected}"
    assert not stale, f"homonym entries that no longer match: {stale}"


class _StateManager:
    def __init__(self):
        self.answers, self.logged = [], []

    def add_answer(self, task_id, author_agent, answer_text, source_ids):
        self.answers.append(answer_text)

    def log_query_result(self, belief_set_id, query, raw_result):
        self.logged.append((query, raw_result))
        return f"qlog_{len(self.logged)}"

    def get_current_state_snapshot(self, summarize=False):
        return {
            "raw_text": "Tous les hommes sont mortels, donc Socrate est mortel.",
            "belief_sets": {
                "bs1": {
                    "logic_type": "first_order",
                    "content": "forall X: (Man(X) => Mortal(X))\nMan(socrate)",
                }
            },
        }


class _Bridge:
    def __init__(self):
        self.checked = []

    def check_consistency(self, belief_set, logic_type):
        self.checked.append(belief_set)
        return True, "consistent"


def test_the_double_is_no_richer_than_the_real_bridge():
    assert "check_consistency" in dir(TweetyBridge)


async def test_the_query_task_runs_through_the_fol_agent(mock_kernel_with_llm):
    # FOL's query path needs no LLM: its queries are rule-based, and so is its
    # interpretation. The stored belief set is the dict the translation task
    # writes.
    bridge = _Bridge()
    agent = FOLLogicAgent(kernel=mock_kernel_with_llm, tweety_bridge=bridge)
    state = _StateManager()

    result = await agent.process_task(
        "t1", "Exécuter les Requêtes sur belief_set_id: bs1", state
    )

    assert result["status"] == "success", result
    assert isinstance(result["message"], str)
    assert state.logged[0][0] == "consistency_check"
    assert bridge.checked, "the consistency check never reached the bridge"
    assert "Man(socrate)" in bridge.checked[0]


def test_fol_rebuilds_the_belief_set_the_translation_task_stores(
    mock_kernel_with_llm,
):
    agent = FOLLogicAgent(kernel=mock_kernel_with_llm, tweety_bridge=_Bridge())
    stored = {"logic_type": "first_order", "content": "P(a)"}

    belief_set = agent._create_belief_set_from_data(stored)

    assert isinstance(belief_set, FirstOrderBeliefSet)
    assert belief_set.content == "P(a)"


def test_pl_rebuilds_the_stored_belief_set_without_the_llm():
    # The former override re-translated the stored (already formal) content
    # through the LLM, as a coroutine the handler never awaited. The rebuild is
    # a pure construction now; building a PL agent would need a JVM.
    stored = {
        "logic_type": "propositional",
        "content": "pluie => mouille",
        "propositions": ["pluie", "mouille"],
    }

    belief_set = PropositionalLogicAgent._create_belief_set_from_data(None, stored)

    assert isinstance(belief_set, PropositionalBeliefSet)
    assert belief_set.content == "pluie => mouille"
    assert belief_set.propositions == ["pluie", "mouille"]
