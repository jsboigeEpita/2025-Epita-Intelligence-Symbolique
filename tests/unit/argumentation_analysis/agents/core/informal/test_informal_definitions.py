
# Authentic gpt-4o-mini imports (replacing mocks)
import pytest
import pandas as pd
import json
from pathlib import Path
import logging
from unittest.mock import patch, MagicMock

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelPlugin

from argumentation_analysis.agents.core.informal.informal_definitions import InformalAnalysisPlugin, setup_informal_kernel
from config.unified_config import UnifiedConfig

# Configure logging for tests
logger = logging.getLogger(__name__)

# --- Fixtures ---

@pytest.fixture
def sample_taxonomy_data():
    """Fixture to provide sample taxonomy data as a list of dictionaries."""
    return [
        {'pk': 0, 'parent_pk': None, 'depth': 0, 'text_fr': 'Sophismes', 'nom_vulgarisé': 'Sophismes', 'description_fr': 'Racine de la taxonomie des sophismes.'},
        {'pk': 1, 'parent_pk': 0, 'depth': 1, 'text_fr': 'Sophisme de Pertinence', 'nom_vulgarisé': 'Pertinence', 'description_fr': 'Les prémisses ne sont pas pertinentes pour la conclusion.'},
        {'pk': 2, 'parent_pk': 1, 'depth': 2, 'text_fr': 'Ad Hominem', 'nom_vulgarisé': 'Attaque personnelle', 'description_fr': "Attaquer la personne plutôt que l'argument."},
        {'pk': 3, 'parent_pk': 0, 'depth': 1, 'text_fr': 'Sophisme d\'Ambiguïté', 'nom_vulgarisé': 'Ambiguïté', 'description_fr': 'Utilisation de termes vagues ou équivoques.'}
    ]

@pytest.fixture
def mock_taxonomy_df(sample_taxonomy_data):
    """Fixture to create a mocked DataFrame from sample data, indexed by 'pk'."""
    df = pd.DataFrame(sample_taxonomy_data)
    df = df.set_index('pk')
    df['parent_pk'] = pd.to_numeric(df['parent_pk'], errors='coerce')
    df['depth'] = pd.to_numeric(df['depth'], errors='coerce').astype('Int64')
    return df

@pytest.fixture
def informal_plugin_mocked(mock_taxonomy_df):
    """
    Fixture to create an instance of InformalAnalysisPlugin with a mocked
    _get_taxonomy_dataframe method to isolate internal logic tests.
    """
    with patch('argumentation_analysis.agents.core.informal.informal_definitions.InformalAnalysisPlugin._get_taxonomy_dataframe', return_value=mock_taxonomy_df) as mock_method:
        plugin = InformalAnalysisPlugin()
        yield plugin

@pytest.fixture
def informal_plugin_real(tmp_path, sample_taxonomy_data):
    """
    Fixture to create an instance of InformalAnalysisPlugin using a real, temporary
    taxonomy file for integration testing of file loading and public methods.
    """
    # Create a temporary CSV file with sample data
    taxonomy_file = tmp_path / "temp_taxonomy.csv"
    df = pd.DataFrame(sample_taxonomy_data)
    df.rename(columns={'pk': 'PK'}, inplace=True) # Ensure column name matches expected 'PK'
    df.to_csv(taxonomy_file, index=False)
    
    # Instantiate the plugin with the path to the temporary file
    plugin = InformalAnalysisPlugin(taxonomy_file_path=str(taxonomy_file))
    return plugin
    
@pytest.fixture
def kernel_service():
    """Fixture to provide a configured Kernel service for gpt-4o-mini."""
    config = UnifiedConfig()
    return config.get_kernel_with_gpt4o_mini()


# --- Tests for Internal Logic (using mocked DataFrame) ---

def test_internal_get_node_details(informal_plugin_mocked, mock_taxonomy_df):
    """Test retrieving details of a single node."""
    details_pk1 = informal_plugin_mocked._internal_get_node_details(1, mock_taxonomy_df)
    assert details_pk1 is not None
    assert details_pk1['pk'] == 1
    # The internal methods don't use 'nom_vulgarisé' directly, we check a loaded column
    assert details_pk1['text_fr'] == 'Sophisme de Pertinence'

    details_pk_invalid = informal_plugin_mocked._internal_get_node_details(99, mock_taxonomy_df)
    assert details_pk_invalid is not None
    assert "error" in details_pk_invalid
    assert "PK 99 non trouvée" in details_pk_invalid["error"]

def test_internal_get_children_details(informal_plugin_mocked, mock_taxonomy_df):
    """Test retrieving details of child nodes."""
    # This method seems to have a different column expectation ('nom_vulgarisé')
    # Let's adjust the test to what the method actually does or what data it has
    children_pk0 = informal_plugin_mocked._internal_get_children_details(0, mock_taxonomy_df, max_children=5)
    assert len(children_pk0) == 2
    assert any(c['nom_vulgarisé'] == 'Pertinence' for c in children_pk0)
    assert any(c['nom_vulgarisé'] == 'Ambiguïté' for c in children_pk0)

    children_pk1 = informal_plugin_mocked._internal_get_children_details(1, mock_taxonomy_df, max_children=5)
    assert len(children_pk1) == 1
    assert children_pk1[0]['nom_vulgarisé'] == 'Attaque personnelle'

    children_pk2 = informal_plugin_mocked._internal_get_children_details(2, mock_taxonomy_df, max_children=5)
    assert len(children_pk2) == 0

def test_internal_explore_hierarchy(informal_plugin_mocked, mock_taxonomy_df):
    """Test exploring the hierarchy from a given node."""
    # This method also expects 'nom_vulgarisé' which is in the sample data
    hierarchy_pk0 = informal_plugin_mocked._internal_explore_hierarchy(0, mock_taxonomy_df)
    assert hierarchy_pk0["current_node"] is not None
    assert hierarchy_pk0["current_node"]["nom_vulgarisé"] == "Sophismes"
    assert len(hierarchy_pk0["children"]) == 2
    assert hierarchy_pk0["error"] is None

    hierarchy_pk2 = informal_plugin_mocked._internal_explore_hierarchy(2, mock_taxonomy_df)
    assert hierarchy_pk2["current_node"] is not None
    assert hierarchy_pk2["current_node"]["nom_vulgarisé"] == "Attaque personnelle"
    assert len(hierarchy_pk2["children"]) == 0
    assert hierarchy_pk2["error"] is None

    hierarchy_invalid = informal_plugin_mocked._internal_explore_hierarchy(99, mock_taxonomy_df)
    assert hierarchy_invalid["current_node"] is None
    assert len(hierarchy_invalid["children"]) == 0
    assert "PK 99 non trouvée" in hierarchy_invalid["error"]


# --- Integration Tests for Public Methods (using real file loading) ---

def test_explore_fallacy_hierarchy_real(informal_plugin_real):
    """Test the public hierarchy exploration method with a real file."""
    result_json_pk1 = informal_plugin_real.explore_fallacy_hierarchy("1")
    result_pk1 = json.loads(result_json_pk1)
    
    assert result_pk1["current_node"]["nom_vulgarisé"] == "Pertinence"
    assert len(result_pk1["children"]) == 1
    assert result_pk1["children"][0]["nom_vulgarisé"] == "Attaque personnelle"

    result_json_invalid = informal_plugin_real.explore_fallacy_hierarchy("99")
    result_invalid = json.loads(result_json_invalid)
    assert "PK 99 non trouvée" in result_invalid["error"]

    result_json_non_numeric = informal_plugin_real.explore_fallacy_hierarchy("abc")
    result_non_numeric = json.loads(result_json_non_numeric)
    assert "PK invalide: abc" in result_non_numeric["error"]

def test_get_fallacy_details_real(informal_plugin_real):
    """Test the public detail retrieval method with a real file."""
    details_json_pk2 = informal_plugin_real.get_fallacy_details("2")
    details_pk2 = json.loads(details_json_pk2)
    # The key might be 'text_fr' or 'description_fr' depending on the loading logic
    assert details_pk2["nom_vulgarisé"] == "Attaque personnelle"
    assert details_pk2["description_fr"] == "Attaquer la personne plutôt que l'argument."

    details_json_invalid = informal_plugin_real.get_fallacy_details("99")
    details_invalid = json.loads(details_json_invalid)
    assert "PK 99 non trouvée" in details_invalid["error"]

    details_json_non_numeric = informal_plugin_real.get_fallacy_details("xyz")
    details_non_numeric_parsed = json.loads(details_json_non_numeric)
    assert details_non_numeric_parsed is not None
    assert "PK invalide: xyz" in details_non_numeric_parsed["error"]


# --- Tests for Kernel Setup ---

def test_setup_informal_kernel_success(kernel_service):
    """Test successful setup of the informal kernel."""
    kernel = Kernel()
    setup_informal_kernel(kernel, kernel_service)
    
    assert "InformalAnalyzer" in kernel.plugins
    plugin = kernel.plugins["InformalAnalyzer"]
    assert isinstance(plugin, KernelPlugin)
    
    # Check that native functions are registered
    assert "explore_fallacy_hierarchy" in plugin
    assert "get_fallacy_details" in plugin
    
    # Check that semantic functions are registered
    assert "semantic_IdentifyArguments" in plugin
    assert "semantic_AnalyzeFallacies" in plugin

def test_setup_informal_kernel_no_llm_service():
    """Test setup with a missing LLM service."""
    kernel = Kernel()
    setup_informal_kernel(kernel, None)
    
    assert "InformalAnalyzer" in kernel.plugins
    plugin = kernel.plugins["InformalAnalyzer"]
    assert isinstance(plugin, KernelPlugin)
    # Native functions should still be there
    assert "explore_fallacy_hierarchy" in plugin
    # Semantic functions might be added but will fail on execution
    assert "semantic_IdentifyArguments" in plugin

@patch('argumentation_analysis.agents.core.informal.informal_definitions.InformalAnalysisPlugin.__init__', side_effect=Exception("Plugin Init Error"))
def test_setup_informal_kernel_with_init_error(mock_plugin_init, kernel_service):
    """Test kernel setup with an error during plugin initialization."""
    kernel = Kernel()
    with pytest.raises(Exception, match="Plugin Init Error"):
        setup_informal_kernel(kernel, kernel_service)