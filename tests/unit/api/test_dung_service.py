import pytest
from api.services import DungAnalysisService
from api.dependencies import get_dung_analysis_service
import os

# S'assurer que JAVA_HOME est défini pour les tests
if not os.environ.get('JAVA_HOME'):
    pytest.fail("La variable d'environnement JAVA_HOME est requise pour ces tests.")

@pytest.fixture(scope="module")
def dung_service(integration_jvm) -> DungAnalysisService:
    """
    Fixture pour fournir une instance unique du service pour tous les tests du module.
    Dépend de 'integration_jvm' pour s'assurer que la JVM est démarrée.
    """
    if not integration_jvm or not integration_jvm.isJVMStarted():
        pytest.fail("La fixture integration_jvm n'a pas réussi à démarrer la JVM.")
    return get_dung_analysis_service()

def test_service_initialization(dung_service: DungAnalysisService):
    """Vérifie que le service est initialisé sans erreur."""
    assert dung_service is not None
    # La gestion de la JVM est maintenant externe (via conftest),
    # donc on vérifie juste qu'une classe Java a pu être chargée.
    assert hasattr(dung_service, 'DungTheory'), "L'attribut 'DungTheory' devrait exister après l'initialisation."

def test_analyze_simple_framework(dung_service: DungAnalysisService):
    """Teste l'analyse d'un framework simple (a -> b -> c)."""
    arguments = ["a", "b", "c"]
    attacks = [["a", "b"], ["b", "c"]]
    
    result = dung_service.analyze_framework(arguments, [(s, t) for s, t in attacks])
    
    # Vérification des sémantiques
    # c n'est pas attaqué, il doit donc être dans la grounded extension
    assert result['semantics']['grounded'] == ["a", "c"]
    assert result['semantics']['preferred'] == [["a", "c"]]
    assert result['semantics']['stable'] == [["a", "c"]]
    
    # Vérification du statut des arguments
    assert result['argument_status']['a']['credulously_accepted'] is True
    assert result['argument_status']['a']['skeptically_accepted'] is True
    assert result['argument_status']['c']['credulously_accepted'] is True
    
    # Vérification des propriétés du graphe
    assert result['graph_properties']['num_arguments'] == 3
    assert result['graph_properties']['num_attacks'] == 2
    assert result['graph_properties']['has_cycles'] is False

def test_analyze_cyclic_framework(dung_service: DungAnalysisService):
    """Teste un framework avec un cycle (a <-> b)."""
    arguments = ["a", "b"]
    attacks = [["a", "b"], ["b", "a"]]
    
    result = dung_service.analyze_framework(arguments, [(s, t) for s, t in attacks])
    
    # Dans un cycle simple, l'extension fondée est vide
    assert result['semantics']['grounded'] == []
    # Les extensions préférées contiennent chaque argument séparément
    assert result['semantics']['preferred'] == [["a"], ["b"]]
    assert result['semantics']['stable'] == [["a"], ["b"]]
    
    # Vérification des propriétés du graphe
    assert result['graph_properties']['has_cycles'] is True
    assert len(result['graph_properties']['cycles']) > 0

def test_analyze_empty_framework(dung_service: DungAnalysisService):
    """Teste un framework vide."""
    arguments = []
    attacks = []
    
    result = dung_service.analyze_framework(arguments, [(s, t) for s, t in attacks])
    
    assert result['semantics']['grounded'] == []
    assert result['semantics']['preferred'] == [[]]
    assert result['graph_properties']['num_arguments'] == 0
    assert result['graph_properties']['num_attacks'] == 0

def test_self_attacking_argument(dung_service: DungAnalysisService):
    """Teste un argument qui s'auto-attaque (a -> a)."""
    arguments = ["a", "b"]
    attacks = [["a", "a"], ["a", "b"]]
    
    result = dung_service.analyze_framework(arguments, [(s, t) for s, t in attacks])

    # Un argument qui s'auto-attaque ne peut pas être dans une extension
    assert result['semantics']['grounded'] == []
    assert result['semantics']['preferred'] == [[]]
    assert result['argument_status']['a']['credulously_accepted'] is False
    
    # Vérification des propriétés
    assert result['graph_properties']['self_attacking_nodes'] == ["a"]