"""Sondes né-rouge pour la tranche tests/ de #2536 (F821 : noms indéfinis).

Mesure de référence (2026-09-24) : `git stash` → rouge en valeurs →
`git stash pop` → vert. Deux formes de sondes (la troisième, fonctionnelle
F1, sondait le template `_make_authentic_llm_call` ; #2604 a retiré ce
template de tous ses fichiers — aucun appelant — et sa sonde avec lui) :
- binding (imports F4/F5) : l'import réparé doit exister dans le module.
- témoin source (suppressions classe 3, captures F3) : le nom mort est
  absent / la capture présente dans le source.
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_f4_mock_imports_bound():
    """Pré-fix : Mock/MagicMock/patch/AsyncMock absents des modules."""
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
    # ``test_service_manager_complete.py`` n'est plus sondé : ses liaisons F821
    # (``asyncio``, ``logger``) ne servaient que le template
    # ``_make_authentic_llm_call``, retiré par #2604 avec elles.


def test_f5_real_names_have_providers():
    """Pré-fix : run_cluedo_oracle_game non importé (la moitié balanced est
    partie avec test_integration_balanced_strategy.py, retiré en #2699)."""
    cluedo = _load(
        REPO_ROOT / "tests/integration/workers/worker_sherlock_watson_moriarty.py",
        "f821_probe_cluedo",
    )
    assert hasattr(cluedo, "run_cluedo_oracle_game")


def test_class3_removals_and_captures_present_in_source():
    """Témoins source : pré-fix, chaque assertion échoue (nom mort présent,
    capture absente).

    ``worker_hardening_cases.py`` n'est plus lu ici : aucun lanceur ne l'avait
    jamais exécuté, et #2700 l'a retiré (son module Flask était archivé depuis
    #242, copie dans ``docs/archives/flask_tests_249/``)."""
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
