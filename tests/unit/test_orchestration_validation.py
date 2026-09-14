"""Né-rouge guards for #2112 — the orchestration validation script stops lying.

Measured on the pristine tree (base ``4c733b93``):

1. Test 8 (``test_orchestration_plugins``) instantiates both plugins WITHOUT
   their required state argument — ``EnqueteStateManagerPlugin`` needs
   ``state``, ``LogiqueComplexePlugin`` needs ``state_instance``. Both raise
   TypeError, the blanket ``except`` swallows it, and a failure is recorded:
   the test can never pass, so "plugins validated" is never a measured fact.
2. ``generate_report`` prints a "Capacites d'Orchestration Validees" section
   where ~20 capabilities are hardcoded ``[OK]`` that no test measured —
   including the two plugins whose test just failed — and a conclusion that
   says "[OK] VALIDE POUR PRODUCTION" whatever ``success_rate`` says.

Instrument discipline: the script module is loaded for real (importlib), with
``PROJECT_ROOT`` redirected to a pytest sandbox so no repo file is written and
``setup_logging`` neutralised so the root logger is not polluted.
"""

import asyncio
import importlib.util
import logging
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validation"
    / "orchestration_validation.py"
)


@pytest.fixture(scope="module")
def script(tmp_path_factory):
    sandbox = tmp_path_factory.mktemp("orchestration_validation_2112")
    spec = importlib.util.spec_from_file_location(
        "orchestration_validation_under_test_2112", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROJECT_ROOT = sandbox
    module.setup_logging = lambda: logging.getLogger("guard_2112")
    # The real setup_logging() creates logs/; the report writes both logs/
    # and reports/ without mkdir, so the sandbox must pre-create them.
    (sandbox / "logs").mkdir()
    (sandbox / "reports").mkdir()
    return module


def _report_after(script, outcomes: dict) -> str:
    """Generate the report for injected outcomes and return its content."""
    validator = script.OrchestrationValidator()
    for name, ok in outcomes.items():
        validator.log_test_result(name, ok)
    validator.calculate_metrics()
    report_path = validator.generate_report()
    return Path(report_path).read_text(encoding="utf-8")


def test_plugins_test_really_exercises_the_plugins_2112(script):
    """Test 8 must succeed by exercising the plugins, not fail forever."""
    validator = script.OrchestrationValidator()
    asyncio.run(validator.test_orchestration_plugins())

    result = validator.results["tests"]["orchestration_plugins"]
    assert result["success"] is True, (
        "Le test 8 avale son erreur d'instanciation (plugins nus, sans leur "
        f"état obligatoire) : {result['details']}"
    )


def test_report_does_not_bless_production_when_a_test_fails_2112(script):
    """No hardcoded [OK] and no production blessing against the measurements."""
    report = _report_after(script, {"orchestration_plugins": False, "smoke": True})

    assert "VALIDE POUR PRODUCTION" not in report, (
        "Le rapport bénit la production alors qu'un test a échoué — la "
        "conclusion doit dériver du taux mesuré, pas d'un gabarit fixe."
    )
    assert "EnqueteStateManagerPlugin [OK]" not in report, (
        "La section 'Capacites d'Orchestration Validees' imprime [OK] pour un "
        "plugin dont le test vient d'échouer : aucun [OK] ne doit exister "
        "sans mesure qui le soutienne."
    )


def test_report_blessing_is_earned_2112(script):
    """Positive control: the report can still say yes when everything passes."""
    report = _report_after(script, {"smoke": True})

    assert "VALIDE POUR PRODUCTION" in report, (
        "Contrôle positif : un run tout vert doit pouvoir conclure à la "
        "validation — un gabarit qui ne sait plus dire oui n'est pas plus "
        "honnête."
    )
    assert "[OK] PASS" in report
