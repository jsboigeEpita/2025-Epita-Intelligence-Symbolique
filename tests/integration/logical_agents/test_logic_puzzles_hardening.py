import pytest
from tests.utils.scenario_runner import run_scenario_from_file

# Définit les chemins vers les nouveaux scénarios de test
SCENARIO_FILES = [
    "tests/fixtures/scenarios/ambiguous_scenario.json",
    "tests/fixtures/scenarios/contradictory_scenario.json",
]

@pytest.mark.parametrize("scenario_path", SCENARIO_FILES)
def test_hardening_scenarios(scenario_path, jvm_session):
    """
    Teste les scénarios de "hardening" (ambigus et contradictoires).

    Ce test utilise le 'scenario_runner' pour exécuter chaque scénario
    et valide que le résultat de l'analyse correspond au résultat attendu.

    Args:
        scenario_path (str): Le chemin vers le fichier de scénario.
        jvm_session: La fixture qui gère la session JVM.
    """
    try:
        analysis_result, expected_outcome = run_scenario_from_file(scenario_path)
        
        # Valide que le résultat de l'analyse contient le résultat attendu.
        # C'est une vérification de base ; des assertions plus complexes pourraient être nécessaires
        # en fonction de la structure exacte du résultat de l'analyse.
        assert expected_outcome in analysis_result, \
            f"Le résultat attendu '{expected_outcome}' n'a pas été trouvé dans le résultat de l'analyse."

    except Exception as e:
        pytest.fail(f"Le scénario {scenario_path} a échoué avec une exception inattendue: {e}")
