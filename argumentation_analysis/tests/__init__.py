"""
Tests unitaires pour le projet d'analyse argumentative.
"""

import sys
import os
import types
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Ajouter le répertoire parent (racine du projet) au PYTHONPATH
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
print(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

# Créer des mocks pour les modules ui qui sont importés dans extract_agent.py
ui_module = types.ModuleType('ui')
ui_config_module = types.ModuleType('ui.config')
ui_utils_module = types.ModuleType('ui.utils')
ui_extract_utils_module = types.ModuleType('ui.extract_utils')

# Ajouter les modules mockés au sys.modules
sys.modules['ui'] = ui_module
sys.modules['ui.config'] = ui_config_module
sys.modules['ui.utils'] = ui_utils_module
sys.modules['ui.extract_utils'] = ui_extract_utils_module

# Configurer les mocks avec les attributs nécessaires
ui_config_module.ENCRYPTION_KEY = "test_encryption_key"
ui_config_module.CONFIG_FILE = "test_config_file"
ui_config_module.CONFIG_FILE_JSON = "test_config_file.json"

# Créer des fonctions mockées pour ui.utils
ui_utils_module.load_from_cache = MagicMock(return_value=None)
ui_utils_module.reconstruct_url = MagicMock(return_value="https://example.com/test")

# Créer des fonctions mockées pour ui.extract_utils
ui_extract_utils_module.load_source_text = MagicMock(return_value=("Sample text", "https://example.com"))
ui_extract_utils_module.extract_text_with_markers = MagicMock(return_value=("Extracted text", "Success", True, True))
ui_extract_utils_module.find_similar_text = MagicMock(return_value=("Similar text", 0.9))
ui_extract_utils_module.load_extract_definitions_safely = MagicMock(return_value=(None, None))
ui_extract_utils_module.save_extract_definitions_safely = MagicMock(return_value=(True, None))

# Créer des mocks pour les modules orchestration qui sont importés dans test_integration.py
# Créer le module argumentation_analysis s'il n'existe pas déjà
if 'argumentation_analysis' not in sys.modules:
    argumentation_analysis_module = types.ModuleType('argumentation_analysis')
    sys.modules['argumentation_analysis'] = argumentation_analysis_module
else:
    argumentation_analysis_module = sys.modules['argumentation_analysis']

# Créer le module orchestration
orchestration_module = types.ModuleType('argumentation_analysis.orchestration')
sys.modules['argumentation_analysis.orchestration'] = orchestration_module
setattr(argumentation_analysis_module, 'orchestration', orchestration_module)

# Créer le module analysis_runner
analysis_runner_module = types.ModuleType('argumentation_analysis.orchestration.analysis_runner')
sys.modules['argumentation_analysis.orchestration.analysis_runner'] = analysis_runner_module
setattr(orchestration_module, 'analysis_runner', analysis_runner_module)

# Ajouter la fonction run_analysis_conversation au module analysis_runner
async def mock_run_analysis_conversation(texte_a_analyser, llm_service):
    return True, "Analyse terminée avec succès"

analysis_runner_module.run_analysis_conversation = AsyncMock(side_effect=mock_run_analysis_conversation)

# Créer le module scripts
scripts_module = types.ModuleType('argumentation_analysis.scripts')
sys.modules['argumentation_analysis.scripts'] = scripts_module
setattr(argumentation_analysis_module, 'scripts', scripts_module)

# Créer le module verify_extracts
verify_extracts_module = types.ModuleType('argumentation_analysis.scripts.verify_extracts')
sys.modules['argumentation_analysis.scripts.verify_extracts'] = verify_extracts_module
setattr(scripts_module, 'verify_extracts', verify_extracts_module)

# Ajouter les fonctions verify_extracts et generate_report au module verify_extracts
def mock_verify_extracts(extract_definitions, fetch_service, extract_service):
    return [
        {
            "source_name": "Source d'intégration",
            "extract_name": "Extrait d'intégration 1",
            "status": "valid",
            "message": "Extraction réussie"
        },
        {
            "source_name": "Source d'intégration",
            "extract_name": "Extrait d'intégration 2",
            "status": "invalid",
            "message": "Marqueur début non trouvé"
        }
    ]

def mock_generate_report(results, output_path):
    # Simuler la génération d'un rapport HTML avec les informations attendues
    html_content = """
    <html>
    <body>
    <h1>Rapport de vérification des extraits</h1>
    <table>
        <tr>
            <th>Source</th>
            <th>Extrait</th>
            <th>Statut</th>
        </tr>
        <tr>
            <td>Source d'intégration</td>
            <td>Extrait d'intégration 1</td>
            <td>valid</td>
        </tr>
        <tr>
            <td>Source d'intégration</td>
            <td>Extrait d'intégration 2</td>
            <td>invalid</td>
        </tr>
    </table>
    </body>
    </html>
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return True

verify_extracts_module.verify_extracts = mock_verify_extracts
verify_extracts_module.generate_report = mock_generate_report

# Créer le module repair_extract_markers
repair_extract_markers_module = types.ModuleType('scripts.repair_extract_markers')
sys.modules['scripts.repair_extract_markers'] = repair_extract_markers_module

# Ajouter la fonction repair_extract_markers au module
async def mock_repair_extract_markers(extract_definitions, llm_service, fetch_service, extract_service):
    # Retourner les définitions inchangées et des résultats simulés
    return extract_definitions, [
        {
            "source_name": "Source d'intégration",
            "extract_name": "Extrait d'intégration 1",
            "status": "repaired",
            "message": "Réparation réussie"
        },
        {
            "source_name": "Source d'intégration",
            "extract_name": "Extrait d'intégration 2",
            "status": "failed",
            "message": "Échec de la réparation"
        }
    ]

# Ajouter la fonction setup_agents au module
async def mock_setup_agents(llm_service):
    # Retourner des mocks pour les agents
    return MagicMock(), MagicMock(), MagicMock()

repair_extract_markers_module.repair_extract_markers = AsyncMock(side_effect=mock_repair_extract_markers)
repair_extract_markers_module.setup_agents = AsyncMock(side_effect=mock_setup_agents)

# Créer le module models
models_module = types.ModuleType('argumentation_analysis.models')
sys.modules['argumentation_analysis.models'] = models_module
setattr(argumentation_analysis_module, 'models', models_module)

# Créer le module extract_definition
extract_definition_module = types.ModuleType('argumentation_analysis.models.extract_definition')
sys.modules['argumentation_analysis.models.extract_definition'] = extract_definition_module
setattr(models_module, 'extract_definition', extract_definition_module)

# Importer les classes réelles pour les utiliser dans le mock
from models.extract_definition import ExtractDefinitions, Extract, SourceDefinition

# Ajouter les classes au module extract_definition
extract_definition_module.ExtractDefinitions = ExtractDefinitions
extract_definition_module.Extract = Extract
extract_definition_module.SourceDefinition = SourceDefinition

# Créer le module extract_result
extract_result_module = types.ModuleType('argumentation_analysis.models.extract_result')
sys.modules['argumentation_analysis.models.extract_result'] = extract_result_module
setattr(models_module, 'extract_result', extract_result_module)

# Importer la classe réelle pour l'utiliser dans le mock
from models.extract_result import ExtractResult

# Ajouter la classe au module extract_result
extract_result_module.ExtractResult = ExtractResult

# Créer le module services
services_module = types.ModuleType('argumentation_analysis.services')
sys.modules['argumentation_analysis.services'] = services_module
setattr(argumentation_analysis_module, 'services', services_module)

# Créer le module extract_service
extract_service_module = types.ModuleType('argumentation_analysis.services.extract_service')
sys.modules['argumentation_analysis.services.extract_service'] = extract_service_module
setattr(services_module, 'extract_service', extract_service_module)

# Importer la classe réelle pour l'utiliser dans le mock
from services.extract_service import ExtractService

# Ajouter la classe au module extract_service
extract_service_module.ExtractService = ExtractService

# Créer le module fetch_service
fetch_service_module = types.ModuleType('argumentation_analysis.services.fetch_service')
sys.modules['argumentation_analysis.services.fetch_service'] = fetch_service_module
setattr(services_module, 'fetch_service', fetch_service_module)

# Importer la classe réelle pour l'utiliser dans le mock
from services.fetch_service import FetchService

# Ajouter la classe au module fetch_service
fetch_service_module.FetchService = FetchService

# Surcharger la méthode fetch_text pour qu'elle retourne toujours un texte non-null
sample_text = """
Ceci est un exemple de texte source.
Il contient plusieurs paragraphes.

Voici un marqueur de début: DEBUT_EXTRAIT
Ceci est le contenu de l'extrait.
Il peut contenir plusieurs lignes.
Voici un marqueur de fin: FIN_EXTRAIT

Et voici la suite du texte après l'extrait.
"""

# Surcharger la méthode fetch_text de FetchService
original_fetch_text = FetchService.fetch_text
def patched_fetch_text(self, source_info, force_refresh=False):
    # Toujours retourner un texte valide, quelle que soit l'URL
    return sample_text, "https://example.com/test"

# Remplacer la méthode originale par notre version patchée
FetchService.fetch_text = patched_fetch_text

def setup_import_paths():
    """
    Configure les chemins d'importation pour résoudre les problèmes d'imports relatifs.
    Cette fonction est utilisée par les tests d'intégration pour s'assurer que tous les modules
    du projet peuvent être importés correctement.
    """
    # Ajouter le répertoire parent (racine du projet) au début du PYTHONPATH
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    return parent_dir