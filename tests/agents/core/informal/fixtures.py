import pytest
import sys
import logging
from unittest.mock import MagicMock
from typing import Optional # Ajout de l'import

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""

    def __init__(self):
        self.plugins = {}

    def add_plugin(self, plugin_instance, plugin_name):
        """Simule l'ajout d'un plugin. S'assure que le conteneur pour les fonctions du plugin existe."""
        if plugin_name not in self.plugins: self.plugins[plugin_name] = {}

# Ajout des méthodes manquantes pour simuler le Kernel SK plus fidèlement
    def add_function(self, *, prompt: str, function_name: str, plugin_name: Optional[str] = None, description: Optional[str] = None, prompt_template_config = None, prompt_execution_settings = None):
        """Simule l'ajout d'une fonction sémantique."""
        # Pour les tests, on peut juste s'assurer qu'elle est appelée, ou stocker les infos si besoin.
        # Pour l'instant, un simple MagicMock suffit pour la fonction elle-même.
        # La vraie méthode retourne une KernelFunction.
        mock_function = MagicMock(name=f"{plugin_name}_{function_name}")
        if plugin_name:
            # S'assurer que le dictionnaire pour ce plugin existe
            if plugin_name not in self.plugins:
                self.plugins[plugin_name] = {}
            # Stocker la fonction mockée sous son nom dans le plugin approprié
            self.plugins[plugin_name][function_name] = mock_function
        # else:
            # Gérer le cas où plugin_name est None si nécessaire,
            # bien que pour SK, un plugin_name soit généralement attendu.
            # Si les fonctions pouvaient être globales (pas le cas standard de SK) :
            # self.plugins[function_name] = mock_function
        return mock_function # Retourner un mock de KernelFunction

    def get_prompt_execution_settings_from_service_id(self, service_id: str):
        """Simule la récupération des settings d'exécution."""
        # Retourner des settings par défaut ou un MagicMock si les tests doivent vérifier les interactions.
        return MagicMock(name=f"execution_settings_for_{service_id}")
    def create_semantic_function(self, prompt, function_name=None, plugin_name=None, description=None, max_tokens=None, temperature=None, top_p=None):
        """Crée une fonction sémantique."""
        return MagicMock()

    def register_semantic_function(self, function, plugin_name, function_name):
        """Enregistre une fonction sémantique."""
        if plugin_name not in self.plugins:
            self.plugins[plugin_name] = {}
        self.plugins[plugin_name][function_name] = function
@pytest.fixture
def mock_semantic_kernel_instance():
    return MockSemanticKernel()

@pytest.fixture(autouse=True) # autouse=True si ce patch doit toujours être actif pour ces tests
def patch_semantic_kernel(monkeypatch):
    mock_sk_module = MagicMock()
    mock_sk_module.Kernel = MockSemanticKernel # Utilise la classe définie ci-dessus
    monkeypatch.setitem(sys.modules, 'semantic_kernel', mock_sk_module)
    return mock_sk_module
@pytest.fixture
def mock_fallacy_detector():
    detector = MagicMock()
    # Retourne un sophisme mock pour satisfaire les assertions
    # Ajout de la clé "text" attendue par le test et correction de "confidence"
    detector.detect = MagicMock(return_value=[{"fallacy_type": "Appel à l'autorité", "text": "Les experts affirment que ce produit est sûr.", "confidence": 0.7, "details": "Mocked fallacy"}])
    return detector

@pytest.fixture
def mock_rhetorical_analyzer():
    analyzer = MagicMock()
    # Retourne un dictionnaire pour satisfaire les assertions
    # Changement de "figures" en "techniques" et ajustement des valeurs, ajout de "effectiveness"
    analyzer.analyze = MagicMock(return_value={"tone": "persuasif", "style": "émotionnel", "techniques": ["appel à l'émotion", "question rhétorique"], "effectiveness": 0.8})
    return analyzer

@pytest.fixture
def mock_contextual_analyzer():
    analyzer = MagicMock()
    # Renommé en analyze_context et retourne un dictionnaire plus complet
    analyzer.analyze_context = MagicMock(return_value={"context_type": "commercial", "audience": "general", "intent": "persuade", "confidence": 0.9}) # Ajout de 'confidence'
    return analyzer
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin # Ajout pour spec

@pytest.fixture
def informal_agent_instance(mock_semantic_kernel_instance): # Utilise le kernel mocké
    """
    Crée une instance de InformalAnalysisAgent correctement initialisée pour les tests.
    Note: Les 'outils' (fallacy_detector, etc.) sont maintenant internes au plugin de l'agent.
    Les tests devront mocker les appels au kernel ou au plugin si nécessaire.
    """
    kernel = mock_semantic_kernel_instance
    agent_name = "test_informal_agent_fixture"
    
    # Simuler l'instanciation du plugin si nécessaire pour setup_agent_components
    # ou s'assurer que setup_agent_components peut gérer un kernel avec des mocks.
    # Pour l'instant, on suppose que setup_agent_components va ajouter son propre plugin.
    # Si le plugin doit être mocké de l'extérieur, cette fixture devra être plus complexe.
    
    # Patch pour InformalAnalysisPlugin pour contrôler son instanciation pendant le setup de CETTE fixture
    # afin que setup_agent_components utilise une instance mockée si besoin.
    with patch('argumentation_analysis.agents.core.informal.informal_agent.InformalAnalysisPlugin') as mock_plugin_class:
        mock_plugin_instance = MagicMock(spec=InformalAnalysisPlugin)
        mock_plugin_class.return_value = mock_plugin_instance

        agent = InformalAnalysisAgent(kernel=kernel, agent_name=agent_name, taxonomy_file_path="argumentation_analysis/data/mock_taxonomy_small.csv")
        agent.setup_agent_components(llm_service_id="test_llm_service_fixture")
        
        # Attacher le mock du plugin à l'agent si les tests en ont besoin pour des assertions
        # Cela dépend de la manière dont les tests veulent interagir avec le plugin.
        # Si les tests mockent `kernel.invoke`, cela pourrait ne pas être nécessaire.
        agent.mocked_informal_plugin = mock_plugin_instance
        
        return agent
import os
from unittest.mock import patch # Ajout de patch

@pytest.fixture
def setup_test_taxonomy_csv(tmp_path):
    """Crée un fichier test_taxonomy.csv temporaire et retourne son chemin."""
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir(exist_ok=True)
    test_taxonomy_path = test_data_dir / "test_taxonomy.csv"
    
    content = """PK,Name,Category,Description,Example,Counter_Example
1,Appel a l'autorite,Fallacy,Invoquer une autorite non pertinente,"Einstein a dit que Dieu ne joue pas aux des, donc la mecanique quantique est fausse.","Selon le consensus scientifique, le rechauffement climatique est reel."
2,Pente glissante,Fallacy,Suggerer qu'une action menera inevitablement a une chaine d'evenements indesirables,"Si nous legalisons la marijuana, bientot toutes les drogues seront legales.","Si nous augmentons le salaire minimum, certaines entreprises pourraient reduire leurs effectifs."
3,Ad hominem,Fallacy,Attaquer la personne plutot que ses idees,"Vous etes trop jeune pour comprendre la politique.","Votre argument est base sur des donnees obsoletes."
"""
    
    with open(test_taxonomy_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    yield test_taxonomy_path # Retourne le chemin et attend la fin du test

    # Nettoyage (optionnel si tmp_path gère tout, mais explicite ici)
    if os.path.exists(test_taxonomy_path):
        os.unlink(test_taxonomy_path)
    if os.path.exists(test_data_dir) and not os.listdir(test_data_dir):
        os.rmdir(test_data_dir)

@pytest.fixture
def taxonomy_loader_patches(monkeypatch, setup_test_taxonomy_csv):
    """
    Fournit le chemin vers un fichier CSV de taxonomie de test.
    Anciennement, cette fixture patchait des fonctions qui n'existent plus.
    Maintenant, elle fournit principalement le chemin pour que d'autres fixtures/tests
    puissent configurer InformalAnalysisPlugin correctement.
    """
    test_taxonomy_file_path = str(setup_test_taxonomy_csv)
    
    # Les fonctions get_taxonomy_path et validate_taxonomy_file n'existent plus
    # dans informal_definitions.py de la même manière, donc les patchs directs sont supprimés.
    # Les tests ou fixtures qui dépendent de cela devront s'assurer que
    # InformalAnalysisPlugin est initialisé avec ce chemin.

    # Retourner le chemin pour référence, et potentiellement des mocks si d'autres
    # fonctions de chargement/validation devaient être patchées à l'avenir.
    return {
        "test_taxonomy_file_path": test_taxonomy_file_path,
        "mock_get_path": MagicMock(return_value=test_taxonomy_file_path), # Au cas où un test voudrait simuler un ancien get_path
        "mock_validate_file": MagicMock(return_value=True) # Au cas où un test voudrait simuler une ancienne validation
    }

# Fixture pour le InformalAnalysisPlugin qui utilise les mocks de taxonomie
# from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin # Déjà importé plus haut

@pytest.fixture
def informal_analysis_plugin_instance(setup_test_taxonomy_csv): # Dépend directement de setup_test_taxonomy_csv
    """Crée une instance de InformalAnalysisPlugin utilisant le fichier CSV de taxonomie de test."""
    test_taxonomy_path = str(setup_test_taxonomy_csv)
    plugin = InformalAnalysisPlugin(taxonomy_file_path=test_taxonomy_path)
    return plugin
@pytest.fixture
def sample_test_text():
    return "Ceci est un texte d'exemple pour les tests. Il contient plusieurs phrases et pourrait être analysé pour des sophismes ou des figures de style."