"""#2634 — `create_llm_service` has a default service id again, and every call binds.

`fdbb54e20` (2025-07-12) made `service_id` required, with no reason written in
its message or diff. Callers written against the old default were never
updated. On ``main`` ``938621b20`` five production calls did not bind to the
signature (AST census below; a grep for the literal ``create_llm_service()``
found four of them, missing ``create_llm_service(force_mock=True)``). Each raised
``TypeError``, and three of the five sat inside an ``except`` that hid it.

The default is Semantic Kernel's ``DEFAULT_SERVICE_NAME``, the id ``BaseAgent``
resolves when no id is given.

The same swallowed path held a second, independent break: two production calls
passed ``lib_dir_path`` to ``jvm_setup.initialize_jvm``, which has had no such
parameter since 2025-06. ``initialize_jvm`` has homonyms (``TweetyBridge``,
``tweety_initializer``), so that census resolves each call through the file's
imports rather than by name.
"""

import ast
import inspect
import subprocess
from pathlib import Path

import pytest
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.const import DEFAULT_SERVICE_NAME

from argumentation_analysis.core import jvm_setup
from argumentation_analysis.core.llm_service import create_llm_service

ROOT = Path(__file__).resolve().parents[4]
PRODUCTION_ROOTS = [
    "argumentation_analysis",
    "api",
    "interface_web",
    "scripts",
    "examples",
    "project_core",
]
JVM_SETUP = "argumentation_analysis.core.jvm_setup"


def test_a_call_without_an_id_builds_the_default_service():
    service = create_llm_service(force_mock=True)
    assert service.service_id == DEFAULT_SERVICE_NAME


def test_the_authentic_service_without_an_id_carries_the_default_id(monkeypatch):
    # A dummy key: the service is built, never called.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    service = create_llm_service(force_authentic=True)
    assert isinstance(service, OpenAIChatCompletion)
    assert service.service_id == DEFAULT_SERVICE_NAME


def _production_trees():
    files = subprocess.run(
        ["git", "ls-files", "--", *[f"{r}/*.py" for r in PRODUCTION_ROOTS]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    trees, unparsed = [], []
    for rel in files:
        try:
            trees.append((rel, ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))))
        except SyntaxError:
            unparsed.append(rel)
    return files, trees, unparsed


def _create_llm_service_calls(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name == "create_llm_service":
                yield node


def _initialize_jvm_calls(tree):
    """Calls that resolve to ``jvm_setup.initialize_jvm`` through this file's imports."""
    names, modules = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == JVM_SETUP or (node.level and module.endswith("jvm_setup")):
                names |= {
                    a.asname or a.name for a in node.names if a.name == "initialize_jvm"
                }
            elif module == "argumentation_analysis.core":
                modules |= {
                    a.asname or a.name for a in node.names if a.name == "jvm_setup"
                }
        elif isinstance(node, ast.Import):
            modules |= {
                a.asname for a in node.names if a.name == JVM_SETUP and a.asname
            }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in names:
            yield node
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == "initialize_jvm"
            and isinstance(func.value, ast.Name)
            and func.value.id in modules
        ):
            yield node


@pytest.mark.parametrize(
    "function, find_calls, minimum",
    [
        (create_llm_service, _create_llm_service_calls, 20),
        (jvm_setup.initialize_jvm, _initialize_jvm_calls, 10),
    ],
    ids=["create_llm_service", "initialize_jvm"],
)
def test_every_production_call_binds_to_the_signature(function, find_calls, minimum):
    files, trees, unparsed = _production_trees()
    assert not unparsed, f"files the census could not read: {unparsed}"
    calls = [
        (f"{rel}:{node.lineno}", node)
        for rel, tree in trees
        for node in find_calls(tree)
    ]
    # Non-vacuity: the census reads the tree, and the tree calls the function.
    assert len(files) > 500 and len(calls) > minimum, (len(files), len(calls))

    signature = inspect.signature(function)
    failures = []
    for where, node in calls:
        if any(isinstance(a, ast.Starred) for a in node.args) or any(
            k.arg is None for k in node.keywords
        ):
            failures.append(f"{where}: *args/**kwargs, cannot be checked")
            continue
        try:
            signature.bind(
                *[None] * len(node.args), **{k.arg: None for k in node.keywords}
            )
        except TypeError as e:
            failures.append(f"{where}: {e}")
    assert not failures, "\n".join(failures)
