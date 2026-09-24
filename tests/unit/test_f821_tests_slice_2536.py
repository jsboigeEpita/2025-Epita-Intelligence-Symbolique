"""Sondes né-rouge pour la tranche tests/ de #2536 (F821 : noms indéfinis).

Mesure de référence (2026-09-24) : `git stash` → rouge en valeurs →
`git stash pop` → vert. Trois formes de sondes :
- fonctionnelle (F1) : la méthode template `_make_authentic_llm_call` est
  appelée non-liée avec un faux self dont le factory raise — pré-fix, le
  handler NameError sur ``logger`` ; post-fix, retour du fallback. Aucun
  appel LLM réel.
- binding (imports F4/F5) : l'import réparé doit exister dans le module.
- témoin source (suppressions classe 3, captures F3) : le nom mort est
  absent / la capture présente dans le source.
"""

import asyncio
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

F1_FILES = [
    "tests/unit/agents/test_fol_logic_agent.py",
    "tests/unit/argumentation_analysis/agents/core/extract/test_extract_definitions.py",
    "tests/unit/argumentation_analysis/agents/core/oracle/test_dataset_access_manager.py",
    "tests/unit/argumentation_analysis/agents/core/oracle/test_error_handling.py",
    "tests/unit/argumentation_analysis/agents/tools/analysis/test_complex_fallacy_analyzer.py",
    "tests/unit/argumentation_analysis/agents/tools/analysis/test_contextual_fallacy_analyzer.py",
    "tests/unit/argumentation_analysis/core/test_cluedo_oracle_state.py",
    "tests/unit/argumentation_analysis/test_configuration_cli.py",
    "tests/unit/argumentation_analysis/test_crypto_service.py",
    "tests/unit/argumentation_analysis/test_definition_service.py",
    "tests/unit/argumentation_analysis/test_fetch_service.py",
    "tests/unit/argumentation_analysis/test_mock_elimination.py",
    "tests/unit/argumentation_analysis/test_tactical_operational_interface.py",
    "tests/unit/argumentation_analysis/test_trace_analyzer.py",
    "tests/unit/argumentation_analysis/test_tweety_error_analyzer.py",
    "tests/unit/argumentation_analysis/test_utils.py",
    "tests/unit/argumentation_analysis/test_verify_extracts.py",
    "tests/unit/authentication/test_mock_elimination_advanced.py",
    "tests/unit/config/test_unified_config.py",
    "tests/unit/integration/test_unified_config_integration.py",
    "tests/unit/test_service_manager_complete.py",
    "tests/core/test_enquete_states.py",
    "tests/integration/triage/test_authentic_components_integration.py",
    "tests/integration/workers/worker_fol_pipeline.py",
    "tests/performance/test_oracle_performance.py",
    "tests/project_core/dev_utils/test_verification_utils.py",
    "tests/test_complex_trace_authentic.py",
]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


class _RaisingSelf:
    async def _create_authentic_gpt4o_mini_instance(self):
        raise RuntimeError("boom-p2536-tests")


@pytest.mark.parametrize("relpath", F1_FILES)
def test_authentic_template_error_branch_binds_logger(relpath):
    """Pré-fix : NameError ``logger`` dans le handler du template authentique."""
    module = _load(REPO_ROOT / relpath, "f821_probe_" + Path(relpath).stem)
    holder = None
    for value in vars(module).values():
        if isinstance(value, type) and hasattr(value, "_make_authentic_llm_call"):
            holder = value
            break

    def _call(func, *args):
        # Le template existe en variantes async et sync : dispatcher.
        if inspect.iscoroutinefunction(func):
            return asyncio.run(func(*args))
        return func(*args)

    if holder is not None:
        result = _call(holder._make_authentic_llm_call, _RaisingSelf(), "prompt")
    elif hasattr(module, "_make_authentic_llm_call"):
        # Forme module-level (ex. test_authentic_components_integration) :
        # on remplace le factory module-global le temps de l'appel.
        async def _raise():
            raise RuntimeError("boom-p2536-tests")

        original = module._create_authentic_gpt4o_mini_instance
        module._create_authentic_gpt4o_mini_instance = _raise
        try:
            result = _call(module._make_authentic_llm_call, "prompt")
        finally:
            module._create_authentic_gpt4o_mini_instance = original
    else:
        pytest.fail(f"template _make_authentic_llm_call introuvable dans {relpath}")
    assert result == "Authentic LLM call failed"


def test_f4_mock_imports_bound():
    """Pré-fix : Mock/MagicMock/patch/AsyncMock/asyncio absents des modules."""
    reporting = _load(
        REPO_ROOT
        / "tests/unit/argumentation_analysis/pipelines/test_reporting_pipeline.py",
        "f821_probe_reporting",
    )
    assert hasattr(reporting, "patch")
    helpers = _load(
        REPO_ROOT / "tests/utils/common_test_helpers.py", "f821_probe_helpers"
    )
    assert hasattr(helpers, "MagicMock") and hasattr(helpers, "patch")
    extract = _load(
        REPO_ROOT
        / "tests/unit/argumentation_analysis/agents/core/extract/test_extract_definitions.py",
        "f821_probe_extract",
    )
    assert hasattr(extract, "AsyncMock")
    fol = _load(
        REPO_ROOT / "tests/integration/workers/worker_fol_pipeline.py",
        "f821_probe_fol",
    )
    assert hasattr(fol, "Mock")
    smc = _load(
        REPO_ROOT / "tests/unit/test_service_manager_complete.py", "f821_probe_smc"
    )
    assert hasattr(smc, "asyncio") and hasattr(smc, "logging")


def test_f5_real_names_have_providers():
    """Pré-fix : UnifiedConfig / run_cluedo_oracle_game non importés."""
    balanced = _load(
        REPO_ROOT
        / "tests/unit/argumentation_analysis/test_integration_balanced_strategy.py",
        "f821_probe_balanced",
    )
    assert hasattr(balanced, "UnifiedConfig")
    cluedo = _load(
        REPO_ROOT / "tests/integration/workers/worker_sherlock_watson_moriarty.py",
        "f821_probe_cluedo",
    )
    assert hasattr(cluedo, "run_cluedo_oracle_game")


def test_class3_removals_and_captures_present_in_source():
    """Témoins source : pré-fix, chaque assertion échoue (nom mort présent,
    capture absente)."""
    hardening = (
        REPO_ROOT
        / "tests/integration/argumentation_analysis/workers/worker_hardening_cases.py"
    ).read_text(encoding="utf-8")
    assert "JvmManager" not in hardening
    assert "initialize_jvm" in hardening

    taac = (
        REPO_ROOT / "tests/integration/triage/test_argument_analyzer_client.py"
    ).read_text(encoding="utf-8")
    assert "flask_client" not in taac
    assert "pytest.mark.skip" in taac  # la tombstone reste

    tac = (
        REPO_ROOT / "tests/integration/triage/test_authentic_components.py"
    ).read_text(encoding="utf-8")
    assert "UnifiedOrchestrator" not in tac

    oracle = (
        REPO_ROOT
        / "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_enhanced_behavior.py"
    ).read_text(encoding="utf-8")
    assert "mock_semantic_kernel" not in oracle
    assert (
        "await self._create" not in oracle
    )  # la fixture morte utilisait self hors classe

    playwright = (REPO_ROOT / "tests/e2e/runners/playwright_js_runner.py").read_text(
        encoding="utf-8"
    )
    assert "self.stderr = timeout_stderr" in playwright
    assert "self.stderr = error_message" in playwright
    assert 'timeout_stderr = e.stderr if e.stderr else "TimeoutExpired"' in playwright

    fcm = (REPO_ROOT / "tests/mocks/fact_checking_mocks.py").read_text(encoding="utf-8")
    assert '"to_dict": lambda: {"error": error_message}' in fcm
