import pytest
import sys
from unittest.mock import MagicMock

# Mock pour semantic_kernel
class MockSemanticKernel:
    """Mock pour semantic_kernel."""

    def __init__(self):
        self.plugins = {}

    def add_plugin(self, plugin, name):
        """Ajoute un plugin au kernel."""
        self.plugins[name] = plugin

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

        agent = InformalAnalysisAgent(kernel=kernel, agent_name=agent_name)
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
    """Patche les fonctions de taxonomy_loader."""
    # Utilise le chemin du fichier CSV créé par la fixture setup_test_taxonomy_csv
    test_taxonomy_file_path = setup_test_taxonomy_csv 

    mock_get_path = MagicMock(return_value=str(test_taxonomy_file_path))
    mock_validate_file = MagicMock(return_value=True)

    monkeypatch.setattr("argumentation_analysis.agents.core.informal.informal_definitions.get_taxonomy_path", mock_get_path)
    monkeypatch.setattr("argumentation_analysis.agents.core.informal.informal_definitions.validate_taxonomy_file", mock_validate_file)
    
    return {
        "get_taxonomy_path": mock_get_path,
        "validate_taxonomy_file": mock_validate_file
    }

# Fixture pour le InformalAnalysisPlugin qui utilise les mocks de taxonomie
# from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin # Déjà importé plus haut

@pytest.fixture
def informal_analysis_plugin_instance(taxonomy_loader_patches):
    # S'assurer que les patches sont actifs avant d'instancier
    # taxonomy_loader_patches est déjà une dépendance, donc les patches sont appliqués.
    plugin = InformalAnalysisPlugin()
    return plugin
@pytest.fixture
def sample_test_text():
    return "Ceci est un texte d'exemple pour les tests. Il contient plusieurs phrases et pourrait être analysé pour des sophismes ou des figures de style."