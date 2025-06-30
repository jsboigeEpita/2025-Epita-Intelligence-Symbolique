import pytest
import pandas as pd
import json
import logging
from unittest.mock import MagicMock, patch
import sys
import semantic_kernel as sk
from semantic_kernel.kernel import Kernel

from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel, logger as informal_logger
from argumentation_analysis.utils.taxonomy_loader import logger as taxonomy_loader_logger

# Configuration du logging pour les tests
informal_logger.setLevel(logging.INFO)
taxonomy_loader_logger.setLevel(logging.INFO)

# L'isolation vis-à-vis de torch est maintenant gérée globalement
# dans la fixture jvm_session_autostart de tests/conftest.py

# Marqueur pour utiliser le vrai NumPy dans ce module de test
pytestmark = pytest.mark.use_real_numpy

# Utilisation explicite de la fixture numpy_setup (même si autouse=True)
# pour s'assurer qu'elle est reconnue.
# Note : la fixture 'numpy_setup' est définie dans 'tests.mocks.numpy_setup'
# et est appliquée automatiquement grâce à autouse=True.


@pytest.fixture
def sample_taxonomy_data():
    """Fixture pour les données de taxonomie de base."""
    return [
        {'PK': 0, 'parent_pk': '<NA>', 'nom_vulgarise': 'Root Fallacy'},
        {'PK': 1, 'parent_pk': 0, 'nom_vulgarise': 'Fallacy of Relevance'},
        {'PK': 2, 'parent_pk': 1, 'nom_vulgarise': 'Ad Hominem'},
        {'PK': 3, 'parent_pk': 1, 'nom_vulgarise': 'Red Herring'}
    ]

@pytest.fixture
def mock_taxonomy_df(sample_taxonomy_data):
    """Fixture pour un DataFrame de taxonomie mocké."""
    df = pd.DataFrame(sample_taxonomy_data)
    df['PK'] = df['PK'].astype('int64')
    df['parent_pk'] = pd.to_numeric(df['parent_pk'], errors='coerce').astype(float)
    df.set_index('PK', inplace=True)
    return df

@pytest.fixture
def informal_plugin_mocked(mock_taxonomy_df):
    """Fixture pour une instance du plugin avec un loader mocké."""
    # Le chemin à patcher est celui utilisé DANS le module informal_definitions
    with patch('argumentation_analysis.agents.core.informal.informal_definitions.load_csv_file', return_value=mock_taxonomy_df.reset_index()) as mock_load:
        mock_kernel = MagicMock(spec=sk.Kernel)
        plugin = InformalAnalysisPlugin(kernel=mock_kernel, taxonomy_file_path="mock/path.csv")
        # Le df est déjà dans le plugin via le __init__ mocké, pas besoin de le recharger
        return plugin
        
@pytest.fixture
def informal_plugin_real(tmp_path, sample_taxonomy_data):
    """Fixture pour une instance du plugin utilisant un vrai fichier CSV temporaire."""
    csv_file = tmp_path / "temp_taxonomy.csv"
    pd.DataFrame(sample_taxonomy_data).to_csv(csv_file, index=False)
    mock_kernel = MagicMock(spec=sk.Kernel)
    # L'instance chargera ce fichier
    return InformalAnalysisPlugin(kernel=mock_kernel, taxonomy_file_path=str(csv_file))

# --- Tests des méthodes internes (nécessitent de gérer le DataFrame manuellement) ---

def test_internal_get_node_details(informal_plugin_mocked, mock_taxonomy_df):
    """Test retrieving details of a single node."""
    details_pk1 = informal_plugin_mocked._internal_get_node_details(1, mock_taxonomy_df)
    assert details_pk1 is not None
    assert details_pk1['parent_pk'] == 0
    assert details_pk1['nom_vulgarise'] == 'Fallacy of Relevance'

    details_pk2 = informal_plugin_mocked._internal_get_node_details(2, mock_taxonomy_df)
    assert details_pk2['nom_vulgarise'] == 'Ad Hominem'

    details_non_existent = informal_plugin_mocked._internal_get_node_details(99, mock_taxonomy_df)
    assert 'error' in details_non_existent

def test_internal_explore_hierarchy(informal_plugin_mocked, mock_taxonomy_df):
    """Test exploring the hierarchy from a given node."""
    # This method also expects 'nom_vulgarise' which is in the sample data
    hierarchy_pk0 = informal_plugin_mocked._internal_explore_hierarchy(0, mock_taxonomy_df)
    assert hierarchy_pk0['current_node']['nom_vulgarise'] == 'Root Fallacy'
    assert len(hierarchy_pk0['children']) == 1
    assert hierarchy_pk0['children'][0]['nom_vulgarise'] == 'Fallacy of Relevance'
    
    hierarchy_pk1 = informal_plugin_mocked._internal_explore_hierarchy(1, mock_taxonomy_df)
    assert hierarchy_pk1['current_node']['nom_vulgarise'] == 'Fallacy of Relevance'
    assert len(hierarchy_pk1['children']) == 2
    assert hierarchy_pk1['children'][0]['nom_vulgarise'] == 'Ad Hominem'

    hierarchy_leaf = informal_plugin_mocked._internal_explore_hierarchy(2, mock_taxonomy_df)
    assert hierarchy_leaf['current_node']['nom_vulgarise'] == 'Ad Hominem'
    assert len(hierarchy_leaf['children']) == 0

# --- Tests des méthodes publiques (l'instance du plugin gère le chargement) ---

def test_explore_fallacy_hierarchy_real(informal_plugin_real):
    """Test the public hierarchy exploration method with a real file."""
    result_json_pk1 = informal_plugin_real.explore_fallacy_hierarchy("1")
    result = json.loads(result_json_pk1)
    assert result['current_node']['nom_vulgarise'] == 'Fallacy of Relevance'
    assert len(result['children']) == 2
    assert result['children'][0]['pk'] == 2

    # Test case sensitivity and conversion for PK
    result_json_pk_str_2 = informal_plugin_real.explore_fallacy_hierarchy(current_pk_str="2")
    result_2 = json.loads(result_json_pk_str_2)
    assert result_2['current_node']['nom_vulgarise'] == 'Ad Hominem'
    assert len(result_2['children']) == 0
    
def test_get_fallacy_details_real(informal_plugin_real):
    """Test the public detail retrieval method with a real file."""
    details_json_pk2 = informal_plugin_real.get_fallacy_details("2")
    details = json.loads(details_json_pk2)
    assert details['nom_vulgarise'] == 'Ad Hominem'
    assert details['parent_pk'] == 1

    # Test non-existent PK
    details_non_existent = informal_plugin_real.get_fallacy_details("99")
    # This should now return a JSON with an error message
    details_err = json.loads(details_non_existent)
    assert "error" in details_err
    assert details_err["error"] is not None


# --- Tests de la méthode de setup du Kernel Semantic ---

def test_setup_informal_kernel_success():
    """Test successful setup of the informal analysis kernel, V13 logic."""
    # Créer les mocks nécessaires
    mock_llm_service = MagicMock()
    mock_llm_service.service_id = "mock_service_id"
    
    mock_kernel = MagicMock(spec=sk.Kernel)
    
    # Simuler le dictionnaire `plugins` et le comportement de `add_plugin`
    mock_kernel.plugins = {}
    def _add_plugin_side_effect(plugin_instance, plugin_name):
        mock_kernel.plugins[plugin_name] = plugin_instance
    mock_kernel.add_plugin.side_effect = _add_plugin_side_effect

    # Simuler le retour de get_prompt_execution_settings...
    mock_settings = MagicMock()
    mock_kernel.get_prompt_execution_settings_from_service_id.return_value = mock_settings

    # Appeler la fonction à tester
    setup_informal_kernel(mock_kernel, llm_service=mock_llm_service)

    # --- Vérifications ---

    # 1. Vérifier que le plugin natif a été ajouté correctement
    mock_kernel.add_plugin.assert_called_once()
    call_args, call_kwargs = mock_kernel.add_plugin.call_args
    assert isinstance(call_args[0], InformalAnalysisPlugin)
    assert call_args[1] == "InformalAnalyzer"

    # 2. Vérifier que les settings ont été récupérés
    mock_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with("mock_service_id")

    # 3. Vérifier que les fonctions sémantiques ont été ajoutées
    assert mock_kernel.add_function.call_count == 3
    
    expected_function_names = [
        "semantic_IdentifyArguments",
        "semantic_AnalyzeFallacies",
        "semantic_JustifyFallacyAttribution"
    ]
    
    actual_function_names = [call.kwargs['function_name'] for call in mock_kernel.add_function.call_args_list]
    
    assert sorted(actual_function_names) == sorted(expected_function_names)

    # 4. Vérifier que le llm_service n'est PAS ajouté directement (logique obsolète)
    mock_kernel.add_service.assert_not_called()

def test_setup_informal_kernel_no_llm_service():
    """Test kernel setup failure when no LLM service is available."""
    # La fonction setup attend un kernel, un llm_service, etc. Pas une instance de plugin.
    with pytest.raises(ValueError, match=r"Le service LLM \(llm_service\) est requis"):
        # On passe un kernel mocké et llm_service=None pour déclencher l'erreur
        setup_informal_kernel(MagicMock(spec=sk.Kernel), llm_service=None)

def test_setup_informal_kernel_with_init_error():
    """
    Test que setup_informal_kernel ne lève PAS d'erreur, mais que l'erreur est
    levée plus tard lors de l'utilisation du plugin (lazy loading).
    """
    # On simule un chemin de fichier invalide
    invalid_path = "non_existent_file.csv"
    
    # Mock le kernel et le service LLM
    mock_kernel = MagicMock()
    mock_llm = MagicMock()

    # L'appel à setup_informal_kernel ne devrait PAS lever d'erreur
    # car le chargement du fichier est différé.
    setup_informal_kernel(mock_kernel, mock_llm, taxonomy_file_path=invalid_path)

    # Récupérer l'instance du plugin qui a été créée et passée à add_plugin
    # `ANY` serait plus simple, mais pour être précis, on récupère l'appel.
    call_args = mock_kernel.add_plugin.call_args
    assert call_args is not None
    plugin_instance = call_args[0][0] # (args, kwargs), args est un tuple

    assert isinstance(plugin_instance, InformalAnalysisPlugin)
    
    # C'est MAINTENANT, en essayant d'utiliser une fonction du plugin,
    # que l'erreur de chargement doit se produire.
    with pytest.raises(Exception): # Attend une erreur de fichier non trouvé ou similaire
        plugin_instance.get_fallacy_details("1")