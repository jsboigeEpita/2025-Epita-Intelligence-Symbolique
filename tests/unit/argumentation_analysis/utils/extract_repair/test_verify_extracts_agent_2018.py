"""#2018: the LLM verify module must import — and build its evaluation agent —
on the declared dependencies alone.

Measured (2026-09-03): the historical class name exists in no resolvable
version of the once-declared dependency — gone from the ``autogen`` namespace
at ag2 0.11.4, absent from the ``ag2`` namespace at 1.0.3 (which has no
``agentchat`` submodule at all) — and the call site's keyword arguments are
exactly Semantic Kernel's ``ChatCompletionAgent`` signature. The module now
imports the SK agent directly, so these tests carry no dependency skip: they
must run wherever the suite runs. The service construction deletes the
ambient model id and passes its own — a local run with the repo ``.env``
loaded proves nothing about CI, which has no ``.env`` at all.
"""

import importlib

import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

MODULE_NAME = "argumentation_analysis.utils.extract_repair.verify_extracts_with_llm"


def _import_verify_module():
    return importlib.import_module(MODULE_NAME)


def test_module_imports_on_declared_dependencies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the module adds a FileHandler at import
    module = _import_verify_module()
    assert callable(module.verify_extracts_with_llm)
    assert callable(module.setup_evaluation_agent)
    assert callable(module.generate_report)


def test_runner_entry_point_imports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module(
        "argumentation_analysis.scripts.run_verify_extracts_llm"
    )
    assert callable(module.main)
    assert callable(module.build_verify_parser)


async def test_setup_evaluation_agent_builds_sk_agent(tmp_path, monkeypatch):
    # The conftest import chain loads the repo .env into os.environ at session
    # start (module-level load_dotenv in service_setup), which is exactly the
    # ambient state CI does not share — delete it so green here means green there.
    monkeypatch.delenv("OPENAI_CHAT_MODEL_ID", raising=False)
    monkeypatch.chdir(tmp_path)
    module = _import_verify_module()
    service = OpenAIChatCompletion(
        service_id="test_eval", ai_model_id="test-model", api_key="dummy-key"
    )
    kernel, agent = await module.setup_evaluation_agent(service)
    assert isinstance(kernel, sk.Kernel)
    assert isinstance(agent, ChatCompletionAgent)
    assert agent.name == "EvaluationAgent"
