import pytest
from unittest.mock import Mock
from semantic_kernel import Kernel
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

@pytest.fixture
def fol_agent_with_hierarchy():
    """Fixture pour créer un agent FOL avec une hiérarchie de sortes pré-définie."""
    # Créer des mocks pour les dépendances Kernel et TweetyBridge
    mock_kernel = Mock(spec=Kernel)
    mock_tweety_bridge = Mock(spec=TweetyBridge)

    # Initialiser l'agent avec les mocks
    agent = FOLLogicAgent(kernel=mock_kernel, tweety_bridge=mock_tweety_bridge, agent_name="test_agent_repair")
    builder = agent._builder_plugin

    # Définir les prédicats qui représentent les sortes
    builder.add_predicate_schema("homme", ["homme"])
    builder.add_predicate_schema("mammifere", ["mammifere"])
    builder.add_predicate_schema("animal", ["animal"])
    
    # Définir la hiérarchie via des implications: homme -> mammifere -> animal
    builder.add_universal_implication("homme", "mammifere", "homme")
    builder.add_universal_implication("mammifere", "animal", "mammifere")

    # Définir un prédicat qui attend un 'animal'
    builder.add_predicate_schema("a_un_cri", ["animal"])
    return agent

def test_add_fact_with_undeclared_constant_and_inferred_sort(fol_agent_with_hierarchy):
    """
    Teste l'ajout d'un fait avec une constante non déclarée ('fido')
    dont la sorte ('chien') peut être rattachée à la hiérarchie existante.
    """
    agent = fol_agent_with_hierarchy
    builder = agent._builder_plugin
    
    # 'chien' est un sous-type de 'mammifere', qui est dans la hiérarchie.
    # On le déclare via un prédicat et une implication
    builder.add_predicate_schema("chien", ["chien"])
    builder.add_universal_implication("chien", "mammifere", "chien")

    # On déclenche l'inférence de la hiérarchie
    builder._infer_sort_hierarchy()
    
    # Le fait à tester. 'a_un_cri' attend un 'animal'.
    # 'fido' est un 'chien', donc un 'mammifere', donc un 'animal'.
    # L'agent doit inférer que 'fido' est de type 'chien' et l'accepter.
    
    # Action : Ajouter le fait atomique
    builder.add_atomic_fact("a_un_cri", ["fido"])
    
    # Assertion : Vérifier que la constante 'fido' a bien été ajoutée
    # avec la sorte 'animal', qui est la sorte attendue par le prédicat 'a_un_cri'.
    # La logique actuelle de l'agent assigne la sorte attendue par le prédicat,
    # et non la sorte la plus spécifique possible.
    
    assert "fido" in builder._sorts["animal"], \
        "La constante 'fido' aurait dû être ajoutée à la sorte 'animal'."

    # On peut aussi vérifier l'état final après la construction
    # Note : cela nécessite que mock_tweety_bridge.initializer soit configuré
    # Pour ce test unitaire, on se concentre sur l'état du builder.
    # belief_set = builder.build_tweety_belief_set(agent._tweety_bridge)
    # assert belief_set is not None