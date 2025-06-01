"""
Script de démonstration pour le projet d'Intelligence Symbolique EPITA.

Ce script a pour but de démontrer les fonctionnalités clés du dépôt, incluant :
1. L'exécution des tests unitaires.
2. L'analyse rhétorique sur un exemple de texte clair, tentant d'utiliser les services réels `InformalAgent` et `create_llm_service`.
   Si `OPENAI_API_KEY` n'est pas configurée ou si `create_llm_service` ne peut être importé, un `MockLLMService` est utilisé.
3. L'analyse rhétorique sur des données chiffrées. Le script tente d'utiliser les services réels `CryptoService`
   et `DefinitionService` pour le déchiffrement. L'analyse rhétorique d'un extrait est ensuite effectuée
   par un `InformalAgent` réel (utilisant le résultat de `create_llm_service` réel si configuré, sinon un mock).
   **Correction (Sous-tâche F)**: `MockDefinitionService` retourne maintenant un objet `ExtractDefinitions` (ou son mock) correctement formé.
   **Correction (Sous-tâche I)**: L'initialisation de `RealDefinitionService` est corrigée pour inclure `config_file`.
4. La génération d'un rapport complet à partir des résultats d'analyse de l'extrait chiffré.

Prérequis importants :
- Python 3.x installé.
- Dépendances du projet : Ce script vérifie et tente d'installer `flask-cors` et `seaborn` si manquants.
  Pour les autres dépendances majeures (`pytest`, `python-dotenv`, `pandas`, `matplotlib`, `markdown`, `semantic-kernel`),
  assurez-vous qu'elles sont installées (par exemple, via `pip install -r requirements.txt` ou `pip install -e .`).
- Pour la partie "analyse de données chiffrées" et l'utilisation des services LLM réels :
    - Un fichier `argumentation_analysis/.env` doit exister et être correctement configuré.
    - Ce fichier `.env` DOIT contenir la variable `TEXT_CONFIG_PASSPHRASE` avec la passphrase correcte
      pour déchiffrer le fichier `argumentation_analysis/data/extract_sources.json.gz.enc`.
    - La variable `ENCRYPTION_KEY` doit être définie dans `argumentation_analysis/ui/config.py` pour utiliser `RealCryptoService`.
    - Pour utiliser le service LLM réel (via `create_llm_service`, pour l'analyse de texte clair et/ou l'analyse de l'extrait déchiffré),
      la variable `OPENAI_API_KEY` DOIT être définie dans le fichier `.env` ou dans l'environnement système.
      Sinon, un `MockLLMService` sera utilisé.
- Les tests unitaires (lancés par ce script) utilisent généralement des mocks pour les services externes.
- Ce script est conçu pour être exécuté depuis la racine du projet.

Comment exécuter le script :
Exécutez la commande suivante depuis la racine du projet :
python scripts/demonstration_epita.py
"""
# Imports nécessaires
import subprocess
import json
from pathlib import Path
import os
import sys # Ajouté pour sys.executable et sys.stdout/stderr.encoding
import io # Ajouté pour TextIOWrapper
import time # Ajouté pour mesurer le temps d'exécution
# import traceback # Décommenter pour un traceback complet si nécessaire dans les excepts
import semantic_kernel as sk # Ajouté pour l'initialisation de InformalAgent
print("INFO [DEMO_IMPORT_DEBUG]: Après imports Python standards et semantic_kernel.")

# Reconfigurer sys.stdout et sys.stderr pour utiliser UTF-8
# Cela est plus robuste que de changer l'encodage de la console elle-même
try:
    # Note: os.system("chcp 65001 > nul") sur Windows est omis pour se concentrer sur TextIOWrapper.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    print("INFO: sys.stdout et sys.stderr reconfigurés pour utiliser UTF-8 avec errors='replace'.")
except Exception as e_reconfig_utf8:
    # Utiliser le stderr original (__stderr__) si la reconfiguration échoue,
    # car sys.stderr pourrait être dans un état indéfini.
    # On ne peut pas utiliser print() directement si sys.stdout est aussi cassé.
    # On tente d'écrire sur le stderr original, qui est généralement plus sûr.
    original_stderr = getattr(sys, '__stderr__', sys.stderr) # Accès plus sûr à __stderr__
    if original_stderr: # Vérifier si original_stderr est accessible
        try:
            original_stderr.write(f"AVERTISSEMENT: Impossible de reconfigurer stdout/stderr en UTF-8 : {e_reconfig_utf8}\n")
            original_stderr.flush() # S'assurer que le message est écrit
        except Exception as e_write_original_stderr:
            # En dernier recours, si même l'écriture sur __stderr__ échoue, on ne peut plus rien faire de propre.
            # On pourrait logger dans un fichier, mais pour ce script, on laisse tomber.
            pass # Impossible d'afficher l'avertissement

# Ajoute le répertoire parent (racine du projet) au sys.path
# pour permettre les imports comme argumentation_analysis.services.xxx
# __file__ est le chemin du script actuel (demonstration_epita.py)
current_script_path = os.path.abspath(__file__)
# scripts_dir est le répertoire 'scripts'
scripts_dir = os.path.dirname(current_script_path)
# project_root est le répertoire parent de 'scripts'
project_root = os.path.dirname(scripts_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Amélioration du débogage des imports et de sys.path
print(f"INFO [DEBUG_PATH]: Calculated project_root: {project_root}")
print(f"INFO [DEBUG_PATH]: Current sys.path: {sys.path}")

# Vérification des chemins pour les modules problématiques
print("INFO [DEBUG_IMPORT]: Vérification des chemins pour les modules problématiques...")
# Assurez-vous que 'project_root' est la variable contenant le chemin racine du projet
# (par exemple, C:\dev\2025-Epita-Intelligence-Symbolique)

path_to_arg_analysis_init = os.path.join(project_root, "argumentation_analysis", "__init__.py")

path_to_agents = os.path.join(project_root, "argumentation_analysis", "agents")
path_to_agents_init = os.path.join(path_to_agents, "__init__.py")
path_to_informal_agent_py_new = os.path.join(project_root, "argumentation_analysis", "agents", "core", "informal", "informal_agent.py")

# Mise à jour du chemin pour llm_service.py
path_to_core_module = os.path.join(project_root, "argumentation_analysis", "core")
path_to_llm_service_py_new = os.path.join(path_to_core_module, "llm_service.py")
path_to_services_init_old = os.path.join(project_root, "argumentation_analysis", "services", "__init__.py") # Ancien chemin pour services init

print(f"INFO [DEBUG_IMPORT]: project_root='{project_root}', existe: {os.path.exists(project_root)}")
print(f"INFO [DEBUG_IMPORT]: Chemin vers argumentation_analysis/__init__.py: '{path_to_arg_analysis_init}', existe: {os.path.exists(path_to_arg_analysis_init)}")

print(f"INFO [DEBUG_IMPORT]: Chemin vers argumentation_analysis/agents/: '{path_to_agents}', existe: {os.path.exists(path_to_agents)}")
print(f"INFO [DEBUG_IMPORT]: Chemin vers argumentation_analysis/agents/__init__.py: '{path_to_agents_init}', existe: {os.path.exists(path_to_agents_init)}")
print(f"INFO [DEBUG_IMPORT]: Nouveau chemin vers argumentation_analysis/agents/core/informal/informal_agent.py: '{path_to_informal_agent_py_new}', existe: {os.path.exists(path_to_informal_agent_py_new)}")

print(f"INFO [DEBUG_IMPORT]: Chemin vers argumentation_analysis/core/: '{path_to_core_module}', existe: {os.path.exists(path_to_core_module)}")
print(f"INFO [DEBUG_IMPORT]: Nouveau chemin vers argumentation_analysis/core/llm_service.py: '{path_to_llm_service_py_new}', existe: {os.path.exists(path_to_llm_service_py_new)}")
print(f"INFO [DEBUG_IMPORT]: Ancien chemin vers argumentation_analysis/services/__init__.py: '{path_to_services_init_old}', existe: {os.path.exists(path_to_services_init_old)}")


# Import pour charger les variables d'environnement
from dotenv import load_dotenv
print("INFO [DEMO_IMPORT_DEBUG]: Après import dotenv.")

# Variable globale pour suivre l'état des services réels pour l'analyse chiffrée
REAL_CRYPTO_DEFINITION_SERVICES_IMPORTED = False
REAL_EXTRACT_MODELS_IMPORTED = False
REAL_ENCRYPTION_KEY_IMPORTED = False # Pour suivre l'import de la clé de chiffrement réelle

# Variables globales pour suivre l'état des services réels pour l'analyse de texte clair
REAL_INFORMAL_AGENT_IMPORTED = False
REAL_LLM_SERVICE_FUNCTION_IMPORTED = False # Changé de REAL_LLM_SERVICE_IMPORTED
InformalAgent = None # Placeholder, sera remplacé par l'import réel
# LLMService a été remplacé par une fonction create_llm_service
create_llm_service = None # Placeholder, sera remplacé par l'import réel de la fonction

# Placeholders pour les classes qui seront soit importées soit mockées
Extract = None
ExtractDefinitions = None
SourceDefinition = None


# Définition de Mocks globaux qui seront utilisés si les imports réels échouent

class MockFallacyDetector:
    """Mock minimal pour le détecteur de sophismes."""
    def detect(self, text: str):
        print(f"INFO: MockFallacyDetector.detect appelé pour le texte (premiers 100 chars): {text[:100]}...")
        # Retourne une liste vide pour simuler aucune détection ou un format de base
        return [
            {"fallacy_type": "Mock Fallacy", "description": "Ceci est un sophisme mocké.", "confidence": 0.99}
        ]

class MockCryptoService:
    def __init__(self, passphrase=None, encryption_key=None): # Ajout de encryption_key pour la cohérence
        print("INFO: Utilisation de Mock CryptoService (import réel, configuration ou clé de chiffrement échoué).")
        if passphrase is None and encryption_key is None:
            print("AVERTISSEMENT: Mock CryptoService initialisé sans passphrase ni clé de chiffrement.")
    def decrypt_data(self, data):
        print("INFO: Mock CryptoService - simulation du déchiffrement (retourne les données telles quelles).")
        return data
    def encrypt_data(self, data):
        print("INFO: Mock CryptoService - simulation du chiffrement (retourne les données telles quelles).")
        return data
print("INFO [DEMO_IMPORT_DEBUG]: Avant try-except import CryptoService/DefinitionService.")

# Tentative d'importation des classes réelles pour l'analyse chiffrée (CryptoService, DefinitionService).
try:
    from argumentation_analysis.services.crypto_service import CryptoService as RealCryptoService # Alias pour le message d'erreur
    from argumentation_analysis.services.definition_service import DefinitionService as RealDefinitionService # Alias
    REAL_CRYPTO_DEFINITION_SERVICES_IMPORTED = True
    print("INFO: Services réels (CryptoService, DefinitionService) pour l'analyse chiffrée importés avec succès.")
    # Assigner les versions réelles aux variables globales si l'import réussit
    CryptoService = RealCryptoService
    DefinitionService = RealDefinitionService
except Exception as e_import_cds: # Capture d'exception plus large
    print(f"AVERTISSEMENT: Erreur détaillée d'importation des services réels (CryptoService, DefinitionService): {type(e_import_cds).__name__}: {e_import_cds}.")
    # import traceback # Décommenter pour un traceback complet si nécessaire
    # print(f"TRACEBACK [Crypto/DefinitionService]: {traceback.format_exc()}")
    print("L'analyse des données chiffrées utilisera des Mocks pour CryptoService et DefinitionService.")
    # Assigner les mocks aux variables globales si l'import échoue
    CryptoService = MockCryptoService
    DefinitionService = None # Sera défini plus bas après MockDefinitionService
    REAL_CRYPTO_DEFINITION_SERVICES_IMPORTED = False
print("INFO [DEMO_IMPORT_DEBUG]: Après try-except import CryptoService/DefinitionService.")


# Tentative d'importation des modèles d'extrait réels (ExtractDefinitions, Extract, SourceDefinition).
try:
    from argumentation_analysis.models.extract_definition import ExtractDefinitions as RealExtractDefinitions, SourceDefinition as RealSourceDefinition, Extract as RealExtract
    ExtractDefinitions = RealExtractDefinitions
    SourceDefinition = RealSourceDefinition
    Extract = RealExtract
    REAL_EXTRACT_MODELS_IMPORTED = True
    print("INFO: Modèles d'extrait réels (ExtractDefinitions, SourceDefinition, Extract) importés avec succès depuis extract_definition.")
except Exception as e_import_extract_models: # Capture d'exception plus large
    print(f"AVERTISSEMENT: Erreur détaillée d'importation des modèles d'extrait depuis 'extract_definition': {type(e_import_extract_models).__name__}: {e_import_extract_models}.")
    # import traceback # Décommenter pour un traceback complet si nécessaire
    # print(f"TRACEBACK [ExtractModels]: {traceback.format_exc()}")
    print("Utilisation de Mocks pour ExtractDefinitions, SourceDefinition et Extract.")

    class MockExtractPydanticCompat:
        """Mock pour Extract, simulant un modèle Pydantic pour la compatibilité."""
        def __init__(self, **kwargs):
            self.id = kwargs.get("id", "mock_id")
            self.source_id = kwargs.get("source_id", "mock_source_id")
            self.source_type = kwargs.get("source_type", "mock_type")
            self.text_content = kwargs.get("text_content", "Contenu simulé de l'extrait.")
            self.title = kwargs.get("title", "Titre simulé de l'extrait.")
            self.metadata = kwargs.get("metadata", {})
            # Permettre l'accès par attribut pour d'autres champs potentiels
            for key, value in kwargs.items():
                if not hasattr(self, key): # Évite de réécrire les attributs déjà définis
                    setattr(self, key, value)
        
        # Méthode get pour simuler un dictionnaire si nécessaire (bien que getattr soit préféré)
        def get(self, key, default=None):
            return getattr(self, key, default)

    class MockSourceDefinitionPydanticCompat:
        """Mock pour SourceDefinition."""
        def __init__(self, **kwargs):
            self.id = kwargs.get("id", "mock_source_def_id")
            self.description = kwargs.get("description", "Description simulée de la source.")
            # ... autres champs ...

    class MockExtractDefinitionsPydanticCompat:
        """Mock pour ExtractDefinitions, simulant un modèle Pydantic."""
        def __init__(self, extracts=None, version="1.0_mock", sources=None, **kwargs):
            self.version = version
            self.sources = sources if sources is not None else {}
            self.extracts = extracts if extracts is not None else []
            # Permettre l'accès par attribut pour d'autres champs potentiels
            for key, value in kwargs.items():
                if not hasattr(self, key):
                    setattr(self, key, value)
            print(f"INFO: MockExtractDefinitionsPydanticCompat initialisé avec {len(self.extracts)} extraits.")

        # Méthode get pour simuler un dictionnaire si nécessaire
        def get(self, key, default=None):
             return getattr(self, key, default)

    ExtractDefinitions = MockExtractDefinitionsPydanticCompat
    SourceDefinition = MockSourceDefinitionPydanticCompat
    Extract = MockExtractPydanticCompat
    REAL_EXTRACT_MODELS_IMPORTED = False
print("INFO [DEMO_IMPORT_DEBUG]: Après try-except import modèles Extract.")


class MockDefinitionService:
    """
    Mock pour DefinitionService.
    Sa méthode load_definitions retourne maintenant un objet ExtractDefinitions (réel ou mock)
    correctement formé, contenant une liste d'objets Extract (réels ou mocks).
    """
    def __init__(self, crypto_service, config_file): # config_file ajouté pour correspondre à la signature réelle
        print(f"INFO: Utilisation de MockDefinitionService pour le fichier de configuration (implicite): {config_file}.")
        self.crypto_service = crypto_service
        self.config_file = config_file # Stocker pour référence si nécessaire

    def load_definitions(self):
        print("INFO: MockDefinitionService - simulation du chargement et déchiffrement de définitions.")
        print("INFO: MockDefinitionService retourne un objet ExtractDefinitions (réel ou mock) avec des extraits mockés.")
        
        mock_extract_1_data = {
            # "source_id": "mock_source_A_encrypted", # Clé retirée pour corriger TypeError
            "source_type": "mock_encrypted",
            "text_content": "Ceci est le premier extrait mocké, simulant des données déchiffrées.",
            "title": "Extrait Mock 1",
            "metadata": {"source_details": "Mocked source for demo"}
        }
        mock_extract_2_data = {
            # "source_id": "mock_source_B_encrypted", # Clé retirée pour corriger TypeError
            "source_type": "mock_encrypted",
            "text_content": "Deuxième extrait mocké pour la démo chiffrée, avec un contenu différent.",
            "title": "Extrait Mock 2",
            "metadata": {"source_details": "Another mocked source"}
        }
        
        extract_instance_1 = Extract(**mock_extract_1_data)
        extract_instance_2 = Extract(**mock_extract_2_data)
        
        list_of_mock_extracts = [extract_instance_1, extract_instance_2]
        extract_definitions_object = ExtractDefinitions(extracts=list_of_mock_extracts)
        
        return extract_definitions_object

# Si DefinitionService n'a pas été importé (REAL_CRYPTO_DEFINITION_SERVICES_IMPORTED est False),
# ou si l'import de RealDefinitionService a spécifiquement échoué, on assigne MockDefinitionService.
if not REAL_CRYPTO_DEFINITION_SERVICES_IMPORTED or DefinitionService is None:
    DefinitionService = MockDefinitionService
print("INFO [DEMO_IMPORT_DEBUG]: Après assignation MockDefinitionService si besoin.")


# Tentative d'importation des classes réelles pour l'analyse de texte clair.
try:
    # Correction de l'import pour InformalAgent pour refléter son nouvel emplacement
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent as RealInformalAgent
    InformalAgent = RealInformalAgent # Assigner à la variable globale
    REAL_INFORMAL_AGENT_IMPORTED = True
    print("INFO: RealInformalAgent (InformalAgent) importé avec succès depuis argumentation_analysis.agents.core.informal.informal_agent.")
except Exception as e_import_ia:
    InformalAgent = None # Reste None si l'import échoue
    print(f"AVERTISSEMENT: Erreur détaillée d'importation de RealInformalAgent (depuis argumentation_analysis.agents.core.informal.informal_agent): {type(e_import_ia).__name__}: {e_import_ia}")
    # import traceback # Décommenter pour un traceback complet si nécessaire
    # print(f"TRACEBACK [InformalAgent]: {traceback.format_exc()}")
    REAL_INFORMAL_AGENT_IMPORTED = False
print("INFO [DEMO_IMPORT_DEBUG]: Après try-except import InformalAgent.")

try:
    # Mise à jour de l'import pour utiliser create_llm_service depuis argumentation_analysis.core.llm_service
    from argumentation_analysis.core.llm_service import create_llm_service as real_create_llm_service
    create_llm_service = real_create_llm_service # Assigner à la variable globale
    REAL_LLM_SERVICE_FUNCTION_IMPORTED = True
    print("INFO: Fonction real_create_llm_service (create_llm_service) importée avec succès depuis argumentation_analysis.core.llm_service.")
except Exception as e_import_llms:
    create_llm_service = None # Reste None si l'import échoue
    print(f"AVERTISSEMENT: Erreur détaillée d'importation de real_create_llm_service (depuis argumentation_analysis.core.llm_service): {type(e_import_llms).__name__}: {e_import_llms}")
    print(f"AVERTISSEMENT: Le module 'argumentation_analysis.core.llm_service.py' n'a pas été trouvé ou une erreur est survenue lors de son import.")
    print("AVERTISSEMENT: Par conséquent, MockLLMService sera utilisé si un service LLM est requis.")
    # import traceback # Décommenter pour un traceback complet si nécessaire
    # print(f"TRACEBACK [create_llm_service]: {traceback.format_exc()}")
    REAL_LLM_SERVICE_FUNCTION_IMPORTED = False
print("INFO [DEMO_IMPORT_DEBUG]: Après try-except import create_llm_service.")


# Mock pour le service LLM, utilisé si la clé API n'est pas trouvée ou si l'import de create_llm_service échoue.
# Ce mock simule l'objet retourné par create_llm_service (qui est une instance de OpenAIChatCompletion ou AzureChatCompletion)
# et doit donc avoir une méthode invoke.
class MockLLMService: # Ce mock simule l'instance de service LLM, pas la fonction create_llm_service
    def __init__(self, service_id: str = "mock_llm_service"): # service_id pour correspondre à create_llm_service
        self.service_id = service_id
        print(f"INFO: MockLLMService (instance) initialisé avec service_id='{self.service_id}'.")

    # La méthode attendue par semantic kernel est souvent `complete_async` ou similaire,
    # mais pour un usage direct simple, `invoke` est gardé pour la démo.
    # Si semantic kernel est utilisé, ce mock devra être adapté pour être un connecteur SK valide.
    async def complete_async(self, prompt: str, request_settings: sk.connectors.ai.PromptExecutionSettings) -> str: # Signature pour SK
        print(f"INFO: MockLLMService.complete_async appelé avec le prompt (premiers 100 chars): {prompt[:100]}...")
        mock_response_data = {
            "sophismes_identifies": [
                {"type": "Ad Hominem (Mock - LLM)", "passage": "Votre argument est invalide parce que vous êtes stupide."},
                {"type": "Homme de paille (Mock - LLM)", "passage": "Vous dites que nous devrions investir plus dans l'éducation, donc vous voulez ruiner le pays."}
            ],
            "score_global_sophistication": 0.2
        }
        # Pour SK, la réponse doit être une chaîne de caractères simple ou un objet `SKContext`
        # Ici, nous retournons une chaîne JSON pour la démo, mais cela pourrait nécessiter un ajustement
        # si InformalAgent s'attend à un format spécifique de SK.
        return json.dumps(mock_response_data)

    def invoke(self, prompt: str) -> str: # Méthode synchrone pour compatibilité si appelée directement
        print(f"INFO: MockLLMService.invoke appelé avec le prompt (premiers 100 chars): {prompt[:100]}...")
        mock_response_data = {
            "sophismes_identifies": [
                {"type": "Ad Hominem (Mock - LLM)", "passage": "Votre argument est invalide parce que vous êtes stupide."},
                {"type": "Homme de paille (Mock - LLM)", "passage": "Vous dites que nous devrions investir plus dans l'éducation, donc vous voulez ruiner le pays."}
            ],
            "score_global_sophistication": 0.2
        }
        return json.dumps(mock_response_data)

# Fonction mock pour create_llm_service si l'import réel échoue
def mock_create_llm_service(service_id: str = "mock_llm_service_via_creator") -> MockLLMService:
    print(f"INFO: Utilisation de mock_create_llm_service (retourne une instance de MockLLMService) pour service_id='{service_id}'.")
    return MockLLMService(service_id=service_id)

# Assigner la fonction mock si l'import réel a échoué
if not REAL_LLM_SERVICE_FUNCTION_IMPORTED or create_llm_service is None:
    create_llm_service = mock_create_llm_service


def check_and_install_dependencies():
    """
    Vérifie la présence des packages listés (`flask-cors`, `seaborn`, `semantic-kernel`) et tente de les installer s'ils sont manquants.
    Les autres dépendances majeures sont supposées être installées.
    """
    print("\n--- Vérification et installation des dépendances (flask-cors, seaborn, semantic-kernel) ---")
    dependencies = ["flask-cors", "seaborn", "semantic-kernel", "markdown"]
    for package_name in dependencies:
        try:
            module_name = package_name.replace("-", "_")
            __import__(module_name)
            print(f"INFO: Le package '{package_name}' (module '{module_name}') est déjà installé.")
        except ImportError:
            print(f"AVERTISSEMENT: Le package '{package_name}' (module '{module_name}') n'est pas trouvé. Tentative d'installation...")
            try:
                # Utiliser capture_output=True et text=True pour subprocess.run
                # S'assurer que l'encodage est géré pour la sortie du subprocess
                pip_result = subprocess.run([sys.executable, "-m", "pip", "install", package_name], 
                                            check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
                print(f"SUCCÈS: Le package '{package_name}' a été installé.")
                if pip_result.stdout:
                    print(f"Sortie pip (stdout):\n{pip_result.stdout}")
            except subprocess.CalledProcessError as e:
                print(f"ERREUR: Échec de l'installation de '{package_name}'. Code de retour : {e.returncode}")
                # e.stdout et e.stderr sont déjà des chaînes si text=True a été utilisé, ou des bytes sinon.
                # Si text=True n'était pas utilisé (ou si on veut être ultra-prudent), on décode.
                # Ici, on suppose que si text=True est utilisé dans l'appel original, e.stdout/stderr sont des str.
                # Si on veut être sûr, on peut décoder comme pour la sortie pytest.
                # Pour simplifier, on les traite comme des chaînes (résultat de text=True).
                if e.stdout:
                    print(f"Sortie pip (stdout):\n{e.stdout}")
                if e.stderr:
                    print(f"Sortie pip (stderr):\n{e.stderr}")
                print(f"Veuillez vérifier votre connexion internet et installer '{package_name}' manuellement (ex: pip install {package_name}).")
            except FileNotFoundError:
                print(f"ERREUR: La commande '{sys.executable} -m pip' n'a pas été trouvée. Assurez-vous que pip est installé et accessible dans l'environnement Python actuel.")
                print(f"Veuillez installer '{package_name}' manuellement.")
            except Exception as e:
                print(f"ERREUR: Une erreur inattendue est survenue lors de la tentative d'installation de '{package_name}': {e}")
                print(f"Veuillez installer '{package_name}' manuellement.")
        except Exception as e:
            print(f"ERREUR: Une erreur inattendue est survenue lors de la vérification de '{package_name}': {e}")


def run_unit_tests():
    print("\n--- Exécution des tests unitaires ---")
    print("INFO: Les tests unitaires utilisent typiquement des mocks pour isoler le code testé.")
    start_time_tests = time.time()
    print(f"INFO: Début de l'exécution des tests unitaires : {start_time_tests}")
    try:
        # MODIFICATION 1: Capturer en bytes (retrait de text=True, encoding, errors)
        # Ajout d'un timeout de 900 secondes (15 minutes)
        print("INFO: Exécution de pytest avec un timeout de 900 secondes...")
        pytest_process = subprocess.run([sys.executable, "-m", "pytest"], capture_output=True, check=False, timeout=900) # Timeout augmenté
        
        end_time_tests = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires : {end_time_tests}")
        print(f"INFO: Tests unitaires exécutés en {end_time_tests - start_time_tests:.2f} secondes.")

        # MODIFICATION 2: Décodage robuste de stdout et stderr
        pytest_stdout_str = ""
        pytest_stderr_str = ""

        if pytest_process.stdout:
            try:
                pytest_stdout_str = pytest_process.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError as e_decode_utf8:
                print(f"AVERTISSEMENT: Échec du décodage UTF-8 pour stdout: {e_decode_utf8}. Tentative avec latin-1.")
                try:
                    pytest_stdout_str = pytest_process.stdout.decode('latin-1', errors='replace')
                except UnicodeDecodeError as e_decode_latin1:
                    print(f"ERREUR: Échec du décodage latin-1 pour stdout après échec UTF-8: {e_decode_latin1}.")
                    # Représentation des bytes si tout échoue
                    pytest_stdout_str = f"Impossible de décoder stdout. Données brutes (repr): {repr(pytest_process.stdout)}"
            except Exception as e_decode_other_stdout:
                print(f"ERREUR: Erreur inattendue lors du décodage de stdout: {e_decode_other_stdout}")
                pytest_stdout_str = f"Erreur inattendue lors du décodage de stdout. Données brutes (repr): {repr(pytest_process.stdout)}"


        if pytest_process.stderr:
            try:
                pytest_stderr_str = pytest_process.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError as e_decode_utf8_err:
                print(f"AVERTISSEMENT: Échec du décodage UTF-8 pour stderr: {e_decode_utf8_err}. Tentative avec latin-1.")
                try:
                    pytest_stderr_str = pytest_process.stderr.decode('latin-1', errors='replace')
                except UnicodeDecodeError as e_decode_latin1_err:
                    print(f"ERREUR: Échec du décodage latin-1 pour stderr après échec UTF-8: {e_decode_latin1_err}.")
                    pytest_stderr_str = f"Impossible de décoder stderr. Données brutes (repr): {repr(pytest_process.stderr)}"
            except Exception as e_decode_other_stderr:
                 print(f"ERREUR: Erreur inattendue lors du décodage de stderr: {e_decode_other_stderr}")
                 pytest_stderr_str = f"Erreur inattendue lors du décodage de stderr. Données brutes (repr): {repr(pytest_process.stderr)}"

        print("\nRésultat de l'exécution de pytest:")

        # MODIFICATION 3: Impression de stdout (try-except commenté)
        if pytest_stdout_str:
            print("\n--- Sortie Standard Pytest ---")
            # try:
            print(pytest_stdout_str)
            # except UnicodeEncodeError:
            #     print("(Encodage forcé pour la sortie standard en raison d'une UnicodeEncodeError)")
            #     output_encoding_stdout = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
            #     print(pytest_stdout_str.encode(output_encoding_stdout, errors='replace').decode(output_encoding_stdout, errors='ignore'))
            # finally:
            print("--- Fin Sortie Standard Pytest ---")
        
        # MODIFICATION 4: Impression de stderr (try-except commenté)
        if pytest_stderr_str:
            print("\n--- Sortie d'Erreur Pytest ---")
            # try:
            print(pytest_stderr_str)
            # except UnicodeEncodeError:
            #     print("(Encodage forcé pour la sortie d'erreur en raison d'une UnicodeEncodeError)")
            #     output_encoding_stderr = sys.stderr.encoding if sys.stderr.encoding else 'utf-8'
            #     print(pytest_stderr_str.encode(output_encoding_stderr, errors='replace').decode(output_encoding_stderr, errors='ignore'))
            # finally:
            print("--- Fin Sortie d'Erreur Pytest ---")

        # MODIFICATION 5: Utiliser pytest_process.returncode et pytest_stdout_str pour le résumé
        if pytest_process.returncode == 0:
            print("\nTests unitaires réussis !")
        else:
            print(f"\nÉchec des tests unitaires ou certains tests ont échoué (code de retour : {pytest_process.returncode}).")
            
            summary_lines = []
            if pytest_stdout_str: 
                try:
                    keywords = ["collected", "passed", "failed", "error", "skipped", "xfailed", "xpassed", "short test summary info", "===="]
                    summary_lines = [line for line in pytest_stdout_str.splitlines() if any(keyword in line.lower() for keyword in keywords)]
                except Exception as e_split: 
                    print(f"AVERTISSEMENT: Erreur lors du découpage de la sortie standard pour le résumé: {e_split}")
                    summary_lines = ["Erreur lors de l'extraction du résumé."] # Fournir un message d'erreur dans le résumé

            if summary_lines:
                summary_to_print = "\n".join(summary_lines)
                print("\n--- Résumé des tests (extrait de la sortie) ---")
                # try:
                print(summary_to_print)
                # except UnicodeEncodeError:
                #     print("(Encodage forcé pour le résumé en raison d'une UnicodeEncodeError)")
                #     output_encoding_summary = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
                #     print(summary_to_print.encode(output_encoding_summary, errors='replace').decode(output_encoding_summary, errors='ignore'))
                # finally:
                print("--- Fin Résumé des tests ---")
            elif pytest_stdout_str : # Si stdout n'est pas vide mais aucun résumé pertinent
                 print("Aucun résumé pertinent trouvé dans la sortie de pytest.")
            else: # Si pytest_stdout_str est vide
                print("Impossible d'extraire un résumé : la sortie standard de pytest était vide.")
    except subprocess.TimeoutExpired:
        print("ERREUR: L'exécution de pytest a dépassé le timeout de 900 secondes.") # Message mis à jour
        # pytest_process n'existera pas complètement dans ce cas, ou sa sortie sera vide.
        # On pourrait vouloir logger cela différemment.
        end_time_tests_timeout = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires (timeout) : {end_time_tests_timeout}")
        print(f"INFO: Tests unitaires (tentative) exécutés en {end_time_tests_timeout - start_time_tests:.2f} secondes avant timeout.")
    except FileNotFoundError:
        print("ERREUR: La commande 'pytest' n'a pas été trouvée. Assurez-vous que pytest est installé et dans votre PATH.")
        end_time_tests_error = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires (erreur FileNotFoundError) : {end_time_tests_error}")
        print(f"INFO: Tests unitaires (tentative) exécutés en {end_time_tests_error - start_time_tests:.2f} secondes.")
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de l'exécution des tests : {e}")
        import traceback
        traceback.print_exc()
        end_time_tests_exception = time.time()
        print(f"INFO: Fin de l'exécution des tests unitaires (erreur Exception) : {end_time_tests_exception}")
        print(f"INFO: Tests unitaires (tentative) exécutés en {end_time_tests_exception - start_time_tests:.2f} secondes.")


def analyze_clear_text_example(example_file_path: str):
    print(f"\n--- Analyse du fichier texte (avec services réels si possible) : {example_file_path} ---")
    global InformalAgent, create_llm_service # Utiliser les variables globales

    try:
        file_path = Path(example_file_path)
        if not file_path.is_file():
            print(f"Erreur : Le fichier d'exemple '{example_file_path}' n'a pas été trouvé.")
            default_content = "Ceci est un texte d'exemple pour l'analyse de sophismes. L'argument de mon adversaire est ridicule, il doit être idiot. De plus, tout le monde sait que j'ai raison."
            print(f"Création d'un fichier d'exemple à '{file_path}' avec contenu par défaut pour la démonstration.")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(default_content)
        
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        print(f"Contenu du fichier (premiers 200 caractères) :\n{text_content[:200]}...\n")
        
        if not REAL_INFORMAL_AGENT_IMPORTED or InformalAgent is None:
            print("ERREUR CRITIQUE: Real InformalAgent (depuis son nouvel emplacement) n'a pas été importé correctement ou n'est pas disponible.")
            print("L'analyse de texte clair avec la version réelle de l'agent ne peut pas continuer.")
            return

        current_llm_service_instance = None
        analysis_description = "RealInformalAgent (depuis agents.core.informal)"
        
        openai_api_key = os.getenv("OPENAI_API_KEY") # create_llm_service le lira de .env

        start_time_llm_init_clear = time.time()
        print(f"INFO: Début de l'initialisation du LLMService (texte clair) : {start_time_llm_init_clear}")
        if REAL_LLM_SERVICE_FUNCTION_IMPORTED and create_llm_service is not mock_create_llm_service and openai_api_key:
            try:
                # create_llm_service ne prend pas api_key directement, il le lit depuis .env
                current_llm_service_instance = create_llm_service(service_id="clear_text_llm")
                analysis_description += " avec LLM Service réel (via create_llm_service)"
                print("INFO: Utilisation du service LLM réel (via create_llm_service) pour l'analyse de texte clair.")
            except Exception as e:
                print(f"ERREUR: Échec de l'appel à create_llm_service (réel): {e}")
                print("INFO: Passage à MockLLMService.")
                current_llm_service_instance = mock_create_llm_service(service_id="clear_text_llm_fallback_after_real_error")() # Appel de la fonction mock
                analysis_description += " avec MockLLMService (suite à erreur create_llm_service réel)"
        else:
            if not openai_api_key:
                print("AVERTISSEMENT: OPENAI_API_KEY non trouvée dans les variables d'environnement. create_llm_service (réel) pourrait échouer ou utiliser des mocks internes.")
            elif not (REAL_LLM_SERVICE_FUNCTION_IMPORTED and create_llm_service is not mock_create_llm_service):
                print("AVERTISSEMENT: La fonction real_create_llm_service (depuis argumentation_analysis.core.llm_service) n'a pas été importée correctement ou n'est pas disponible.")
            
            print("INFO: Utilisation de MockLLMService (via mock_create_llm_service) pour l'analyse de texte clair.")
            current_llm_service_instance = mock_create_llm_service(service_id="clear_text_llm_default_fallback")() # Appel de la fonction mock
            analysis_description += " avec MockLLMService"
        end_time_llm_init_clear = time.time()
        print(f"INFO: Fin de l'initialisation du LLMService (texte clair) : {end_time_llm_init_clear}")
        print(f"INFO: LLMService (texte clair) initialisé en {end_time_llm_init_clear - start_time_llm_init_clear:.2f} secondes.")

        start_time_agent_init_clear = time.time()
        print(f"INFO: Début de l'initialisation de InformalAgent (texte clair) : {start_time_agent_init_clear}")
        try:
            # Création du kernel sémantique
            kernel = sk.Kernel()
            if current_llm_service_instance:
                 # Le nom du service ("chat-gpt" ou autre) doit correspondre à ce que InformalAgent attend ou configure.
                 # Pour l'instant, on utilise un nom générique.
                kernel.add_service(current_llm_service_instance)
                print(f"INFO: Semantic Kernel initialisé et service LLM '{type(current_llm_service_instance).__name__}' ajouté.")
            else:
                print("AVERTISSEMENT: Aucune instance de service LLM n'a été créée. InformalAgent pourrait ne pas fonctionner correctement.")
            
            # InformalAgent est déjà la classe RealInformalAgent (ou None si échec import)
            agent_instance = InformalAgent(
                agent_id="clear_text_agent", 
                tools={"fallacy_detector": MockFallacyDetector()}, # Fournir le mock détecteur
                semantic_kernel=kernel # Passer le kernel configuré
            )
            print(f"INFO: Real InformalAgent initialisé ({analysis_description}).")
        except Exception as e:
            print(f"ERREUR CRITIQUE: Échec de l'initialisation de Real InformalAgent avec le service LLM sélectionné: {e}")
            print("L'analyse de texte clair ne peut pas continuer. Vérifiez la compatibilité entre l'agent et le service LLM.")
            import traceback
            traceback.print_exc()
            end_time_agent_init_clear_error = time.time()
            print(f"INFO: Fin de l'initialisation de InformalAgent (texte clair, erreur) : {end_time_agent_init_clear_error}")
            print(f"INFO: InformalAgent (texte clair, tentative) initialisé en {end_time_agent_init_clear_error - start_time_agent_init_clear:.2f} secondes.")
            return
        end_time_agent_init_clear = time.time()
        print(f"INFO: Fin de l'initialisation de InformalAgent (texte clair) : {end_time_agent_init_clear}")
        print(f"INFO: InformalAgent (texte clair) initialisé en {end_time_agent_init_clear - start_time_agent_init_clear:.2f} secondes.")
            
        start_time_analyze_clear = time.time()
        print(f"INFO: Début de l'analyse des sophismes (texte clair) : {start_time_analyze_clear}")
        analysis_results = agent_instance.analyze_fallacies(text_content)
        end_time_analyze_clear = time.time()
        print(f"INFO: Fin de l'analyse des sophismes (texte clair) : {end_time_analyze_clear}")
        print(f"INFO: Analyse des sophismes (texte clair) effectuée en {end_time_analyze_clear - start_time_analyze_clear:.2f} secondes.")

        print(f"Résultats de l'analyse des sophismes ({analysis_description}) :")
        # S'assurer que analysis_results est sérialisable en JSON
        try:
            print(json.dumps(analysis_results, indent=4, ensure_ascii=False))
        except TypeError:
            print(f"AVERTISSEMENT: Les résultats de l'analyse ne sont pas directement sérialisables en JSON. Affichage brut : {analysis_results}")


    except Exception as e:
        print(f"Une erreur est survenue lors de l'analyse du fichier '{example_file_path}' : {e}")
        import traceback
        traceback.print_exc()


def analyze_encrypted_data() -> str | None:
    print("\n--- Analyse des données chiffrées (avec services réels et analyse rhétorique réelle sur un extrait) ---")
    global REAL_ENCRYPTION_KEY_IMPORTED, CryptoService, DefinitionService, InformalAgent, create_llm_service, Extract, ExtractDefinitions, project_root

    REAL_ENCRYPTION_KEY = None
    try:
        from argumentation_analysis.ui.config import ENCRYPTION_KEY as IMPORTED_REAL_ENCRYPTION_KEY
        REAL_ENCRYPTION_KEY = IMPORTED_REAL_ENCRYPTION_KEY
        REAL_ENCRYPTION_KEY_IMPORTED = True
        print("INFO: Clé de chiffrement réelle (ENCRYPTION_KEY) importée depuis ui.config.")
    except ImportError:
        REAL_ENCRYPTION_KEY = None
        REAL_ENCRYPTION_KEY_IMPORTED = False
        print("AVERTISSEMENT: Impossible d'importer REAL_ENCRYPTION_KEY depuis argumentation_analysis.ui.config.")
        print("RealCryptoService ne pourra pas être initialisé avec cette clé. Passage au mock si RealCryptoService est tenté.")

    current_crypto_service = None
    current_definition_service = None
    analysis_results_list = []

    env_path = Path(project_root) / "argumentation_analysis" / ".env" # Utilisation de project_root
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True) 
        print(f"INFO: Chargement des variables depuis {env_path}")
    else:
        print(f"AVERTISSEMENT: Fichier .env non trouvé à {env_path}.")
        print("La clé OPENAI_API_KEY est requise pour l'analyse réelle avec create_llm_service.")
        print("ENCRYPTION_KEY de ui.config est requise pour RealCryptoService.")

    # Initialisation de CryptoService (réel ou mock)
    start_time_crypto_init = time.time()
    print(f"INFO: Début de l'initialisation de CryptoService : {start_time_crypto_init}")
    if CryptoService is not MockCryptoService and REAL_ENCRYPTION_KEY_IMPORTED and REAL_ENCRYPTION_KEY:
        try:
            current_crypto_service = CryptoService(encryption_key=REAL_ENCRYPTION_KEY)
            print("INFO: RealCryptoService initialisé avec ENCRYPTION_KEY depuis ui.config.")
        except Exception as e:
            print(f"ERREUR: Impossible d'initialiser CryptoService réel avec ENCRYPTION_KEY : {e}")
            print("INFO: Utilisation de Mock CryptoService (échec initialisation réel avec ENCRYPTION_KEY).")
            current_crypto_service = MockCryptoService()
    elif CryptoService is not MockCryptoService and not (REAL_ENCRYPTION_KEY_IMPORTED and REAL_ENCRYPTION_KEY):
        print("AVERTISSEMENT: REAL_ENCRYPTION_KEY non disponible ou non importée, impossible d'initialiser RealCryptoService.")
        print("INFO: Utilisation de Mock CryptoService.")
        current_crypto_service = MockCryptoService()
    else: 
        print("INFO: Utilisation de MockCryptoService (import de RealCryptoService a échoué ou clé non dispo).")
        current_crypto_service = MockCryptoService()
    end_time_crypto_init = time.time()
    print(f"INFO: Fin de l'initialisation de CryptoService : {end_time_crypto_init}")
    print(f"INFO: CryptoService initialisé en {end_time_crypto_init - start_time_crypto_init:.2f} secondes.")


    # Définition du chemin du fichier de configuration pour DefinitionService
    abs_definitions_file_path = os.path.join(project_root, "argumentation_analysis", "data", "extract_sources.json.gz.enc")
    print(f"INFO: Chemin absolu pour definitions_file_path (config_file pour DefinitionService): {abs_definitions_file_path}")

    if not os.path.exists(abs_definitions_file_path): # Vérifier l'existence du fichier de config
        print(f"ERREUR: Le fichier de configuration des définitions '{abs_definitions_file_path}' n'existe pas.")
        print("Assurez-vous que le fichier est présent pour la démonstration.")
        return None
            
    # Initialisation de DefinitionService (réel ou mock)
    start_time_def_init = time.time()
    print(f"INFO: Début de l'initialisation de DefinitionService : {start_time_def_init}")
    try:
        if DefinitionService is not MockDefinitionService: 
            if current_crypto_service: 
                current_definition_service = DefinitionService(
                    crypto_service=current_crypto_service,
                    config_file=abs_definitions_file_path
                )
                print(f"INFO: RealDefinitionService initialisé avec config_file: {abs_definitions_file_path}")
            else:
                raise ValueError("CryptoService n'est pas initialisé, ne peut pas initialiser RealDefinitionService.")
        else: 
             current_definition_service = MockDefinitionService(
                crypto_service=current_crypto_service, 
                config_file=abs_definitions_file_path
            )
             print(f"INFO: MockDefinitionService initialisé avec config_file: {abs_definitions_file_path}")
        
        service_type = "RealDefinitionService" if DefinitionService is not MockDefinitionService else "MockDefinitionService"
        crypto_type = "RealCryptoService" if not isinstance(current_crypto_service, MockCryptoService) else "MockCryptoService"
        print(f"INFO: {service_type} initialisé (pour {abs_definitions_file_path}) avec {crypto_type}.")

    except Exception as e_init_ds:
        print(f"ERREUR: Impossible d'initialiser DefinitionService : {type(e_init_ds).__name__}: {e_init_ds}")
        print("INFO: Passage au mock DefinitionService explicite.")
        current_definition_service = MockDefinitionService(
            crypto_service=current_crypto_service, 
            config_file=abs_definitions_file_path
        )
    end_time_def_init = time.time()
    print(f"INFO: Fin de l'initialisation de DefinitionService : {end_time_def_init}")
    print(f"INFO: DefinitionService initialisé en {end_time_def_init - start_time_def_init:.2f} secondes.")


    try:
        start_time_load_defs = time.time()
        print(f"INFO: Début du chargement des définitions d'extraits : {start_time_load_defs}")
        print("INFO: Tentative de chargement (et déchiffrement si réel) des définitions d'extraits...")
        extract_definitions_obj = current_definition_service.load_definitions() 
        end_time_load_defs = time.time()
        print(f"INFO: Fin du chargement des définitions d'extraits : {end_time_load_defs}")
        print(f"INFO: Définitions d'extraits chargées en {end_time_load_defs - start_time_load_defs:.2f} secondes.")
        
        if not extract_definitions_obj or not hasattr(extract_definitions_obj, 'sources') or not isinstance(extract_definitions_obj.sources, list) or not extract_definitions_obj.sources:
             print("ERREUR: Aucune définition de source n'a été chargée ou l'objet retourné est invalide/ne contient pas d'attribut 'sources' de type liste non vide.")
             print(f"Type de extract_definitions_obj: {type(extract_definitions_obj)}")
             if hasattr(extract_definitions_obj, 'sources'):
                 print(f"Type de extract_definitions_obj.sources: {type(extract_definitions_obj.sources)}")
             print("Vérifiez l'implémentation de load_definitions() du service utilisé (réel ou mock).")
             return None

        # Pour la démo, nous prenons la première source et ses extraits.
        first_source = extract_definitions_obj.sources[0]
        if not hasattr(first_source, 'extracts') or not isinstance(first_source.extracts, list):
            print(f"ERREUR: La première source ('{getattr(first_source, 'source_name', 'N/A')}') ne contient pas d'attribut 'extracts' de type liste.")
            return None

        num_extracts_in_first_source = len(first_source.extracts)
        print(f"SUCCÈS (ou simulation de chargement): {len(extract_definitions_obj.sources)} source(s) chargée(s).")
        print(f"La première source contient {num_extracts_in_first_source} extrait(s).")

        if num_extracts_in_first_source == 0:
            print("INFO: Aucun extrait à analyser dans la première source.")
            return None

        selected_extract = first_source.extracts[0]
        
        # Mise à jour pour utiliser les attributs réels de la classe Extract
        extract_id = getattr(selected_extract, 'extract_name', 'N/A') # extract_name au lieu de id
        text_content_extract = getattr(selected_extract, 'text_content', '')

        print(f"\n--- Analyse rhétorique réelle de l'extrait déchiffré (ID: {extract_id}) ---")
        print(f"Texte de l'extrait sélectionné (premiers 200 chars):\n{text_content_extract[:200]}...")

        if not REAL_INFORMAL_AGENT_IMPORTED or InformalAgent is None:
            print("ERREUR CRITIQUE: Real InformalAgent (depuis son nouvel emplacement) n'a pas été importé correctement ou n'est pas disponible.")
            print("L'analyse rhétorique réelle ne peut pas continuer.")
            return None

        current_llm_service_instance_for_encrypted = None
        analysis_description_encrypted = "RealInformalAgent (depuis agents.core.informal)"
        
        openai_api_key = os.getenv("OPENAI_API_KEY") # create_llm_service le lira de .env

        start_time_llm_init_encrypted = time.time()
        print(f"INFO: Début de l'initialisation du LLMService (données chiffrées) : {start_time_llm_init_encrypted}")
        if REAL_LLM_SERVICE_FUNCTION_IMPORTED and create_llm_service is not mock_create_llm_service and openai_api_key:
            try:
                current_llm_service_instance_for_encrypted = create_llm_service(service_id="encrypted_data_llm")
                analysis_description_encrypted += " avec LLM Service réel (via create_llm_service)"
                print("INFO: Utilisation du service LLM réel (via create_llm_service) pour l'analyse de l'extrait déchiffré.")
            except Exception as e:
                print(f"ERREUR: Échec de l'appel à create_llm_service (réel) pour l'extrait déchiffré: {e}")
                print("INFO: Passage à MockLLMService pour l'extrait déchiffré.")
                current_llm_service_instance_for_encrypted = mock_create_llm_service(service_id="encrypted_llm_fallback_after_real_error")()
                analysis_description_encrypted += " avec MockLLMService (suite à erreur create_llm_service réel)"
        else:
            if not openai_api_key:
                print("AVERTISSEMENT: OPENAI_API_KEY non trouvée. Requis pour create_llm_service réel.")
            elif not (REAL_LLM_SERVICE_FUNCTION_IMPORTED and create_llm_service is not mock_create_llm_service):
                print("AVERTISSEMENT: La fonction real_create_llm_service (depuis argumentation_analysis.core.llm_service) n'a pas été importée correctement ou n'est pas disponible.")
            print("INFO: Utilisation de MockLLMService (via mock_create_llm_service) pour l'analyse de l'extrait déchiffré.")
            current_llm_service_instance_for_encrypted = mock_create_llm_service(service_id="encrypted_llm_default_fallback")()
            analysis_description_encrypted += " avec MockLLMService"
        end_time_llm_init_encrypted = time.time()
        print(f"INFO: Fin de l'initialisation du LLMService (données chiffrées) : {end_time_llm_init_encrypted}")
        print(f"INFO: LLMService (données chiffrées) initialisé en {end_time_llm_init_encrypted - start_time_llm_init_encrypted:.2f} secondes.")

        start_time_agent_init_encrypted = time.time()
        print(f"INFO: Début de l'initialisation de InformalAgent (données chiffrées) : {start_time_agent_init_encrypted}")
        try:
            kernel_encrypted = sk.Kernel()
            if current_llm_service_instance_for_encrypted:
                kernel_encrypted.add_service(current_llm_service_instance_for_encrypted)
                print(f"INFO: Semantic Kernel initialisé et service LLM '{type(current_llm_service_instance_for_encrypted).__name__}' ajouté pour l'analyse chiffrée.")
            else:
                print("AVERTISSEMENT: Aucune instance de service LLM n'a été créée pour l'analyse chiffrée.")

            agent_instance_encrypted = InformalAgent(
                agent_id="encrypted_data_agent",
                tools={"fallacy_detector": MockFallacyDetector()}, # Fournir le mock détecteur
                semantic_kernel=kernel_encrypted
            )
            print(f"INFO: Real InformalAgent initialisé ({analysis_description_encrypted}) pour l'extrait déchiffré.")
        except Exception as e:
            print(f"ERREUR CRITIQUE: Échec de l'initialisation de Real InformalAgent pour l'extrait déchiffré: {e}")
            import traceback
            traceback.print_exc()
            end_time_agent_init_encrypted_error = time.time()
            print(f"INFO: Fin de l'initialisation de InformalAgent (données chiffrées, erreur) : {end_time_agent_init_encrypted_error}")
            print(f"INFO: InformalAgent (données chiffrées, tentative) initialisé en {end_time_agent_init_encrypted_error - start_time_agent_init_encrypted:.2f} secondes.")
            return None
        end_time_agent_init_encrypted = time.time()
        print(f"INFO: Fin de l'initialisation de InformalAgent (données chiffrées) : {end_time_agent_init_encrypted}")
        print(f"INFO: InformalAgent (données chiffrées) initialisé en {end_time_agent_init_encrypted - start_time_agent_init_encrypted:.2f} secondes.")
            
        start_time_analyze_encrypted = time.time()
        print(f"INFO: Début de l'analyse des sophismes (données chiffrées) : {start_time_analyze_encrypted}")
        real_analysis_data = agent_instance_encrypted.analyze_fallacies(text_content_extract)
        end_time_analyze_encrypted = time.time()
        print(f"INFO: Fin de l'analyse des sophismes (données chiffrées) : {end_time_analyze_encrypted}")
        print(f"INFO: Analyse des sophismes (données chiffrées) effectuée en {end_time_analyze_encrypted - start_time_analyze_encrypted:.2f} secondes.")

        structured_analysis_result = {
            "extract_id": extract_id,
            "analysis_type": f"Rhetorical Analysis ({analysis_description_encrypted})",
            "analysis_details": real_analysis_data
        }
        analysis_results_list.append(structured_analysis_result)

        print("\nRésultat de l'analyse de l'extrait (formaté pour sauvegarde) :")
        try:
            print(json.dumps(analysis_results_list, indent=4, ensure_ascii=False)) 
        except TypeError:
            print(f"AVERTISSEMENT: Les résultats de l'analyse (chiffrée) ne sont pas directement sérialisables en JSON. Affichage brut : {analysis_results_list}")


        results_dir = Path(project_root) / "results" # Utilisation de project_root
        os.makedirs(results_dir, exist_ok=True) 
        
        analysis_output_path = results_dir / "analysis_encrypted_extract_demo.json"
        with open(analysis_output_path, "w", encoding="utf-8") as f:
            # S'assurer que ce qui est sauvegardé est sérialisable
            try:
                json.dump(analysis_results_list, f, indent=4, ensure_ascii=False)
            except TypeError:
                f.write(str(analysis_results_list)) # Sauvegarde en chaîne si non sérialisable
                print(f"AVERTISSEMENT: Le résultat de l'analyse chiffrée n'était pas sérialisable en JSON, sauvegardé comme chaîne.")
        print(f"\nRésultat de l'analyse sauvegardé dans : {analysis_output_path.resolve()}")
        
        return str(analysis_output_path.resolve())

    except FileNotFoundError as e: 
        print(f"ERREUR Fichier non trouvé : {e}")
    except KeyError as e: 
        print(f"ERREUR Variable d'environnement manquante : {e}")
    except json.JSONDecodeError as e: 
        print(f"ERREUR de décodage JSON (fichier potentiellement corrompu ou mauvaise clé si réel) : {e}")
    except AttributeError as e:
        print(f"ERREUR d'attribut : {e}. Cela peut indiquer un problème avec la structure des objets mockés ou réels.")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de l'analyse des données chiffrées : {e}")
        import traceback
        traceback.print_exc()
    return None


def generate_report_from_analysis(analysis_json_path: str):
    print(f"\n--- Génération du rapport à partir de : {analysis_json_path} ---")
    global project_root # S'assurer que project_root est accessible
    
    report_script_path = Path(project_root) / "scripts" / "generate_comprehensive_report.py" # Utilisation de project_root
    if not report_script_path.exists():
        print(f"ERREUR: Le script de génération de rapport '{report_script_path}' n'a pas été trouvé.")
        return

    if not Path(analysis_json_path).exists():
        print(f"ERREUR: Le fichier de résultats d'analyse '{analysis_json_path}' n'a pas été trouvé.")
        return

    start_time_report_gen = time.time()
    print(f"INFO: Début de la génération du rapport : {start_time_report_gen}")
    try:
        command = [
            sys.executable, str(report_script_path.resolve()), 
            "--advanced-results", str(Path(analysis_json_path).resolve())
        ]
        print(f"Exécution de la commande : {' '.join(command)}")
 
        # Utilisation de la même logique de capture et d'impression robuste que pour pytest
        # Ajout d'un timeout de 300 secondes (5 minutes)
        print("INFO: Exécution du script de génération de rapport avec un timeout de 300 secondes...")
        report_process = subprocess.run(command, capture_output=True, check=False, cwd=project_root, timeout=300)
 
        report_stdout_str = ""
        report_stderr_str = ""

        if report_process.stdout:
            try:
                report_stdout_str = report_process.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError: # Ne pas afficher de message d'erreur ici, juste essayer latin-1
                try:
                    report_stdout_str = report_process.stdout.decode('latin-1', errors='replace')
                except: # Si tout échoue, laisser vide ou mettre un message d'erreur
                    report_stdout_str = f"Impossible de décoder stdout du script de rapport. Données brutes (repr): {repr(report_process.stdout)}"
        
        if report_process.stderr:
            try:
                report_stderr_str = report_process.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                try:
                    report_stderr_str = report_process.stderr.decode('latin-1', errors='replace')
                except:
                    report_stderr_str = f"Impossible de décoder stderr du script de rapport. Données brutes (repr): {repr(report_process.stderr)}"


        print("\nRésultat de la génération du rapport :")
        if report_stdout_str:
            print("\n--- Sortie Standard du script de rapport ---")
            # try:
            print(report_stdout_str)
            # except UnicodeEncodeError:
            #     print("(Encodage forcé pour la sortie standard du rapport en raison d'une UnicodeEncodeError)")
            #     output_encoding_stdout_report = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
            #     print(report_stdout_str.encode(output_encoding_stdout_report, errors='replace').decode(output_encoding_stdout_report, errors='ignore'))
            # finally:
            print("--- Fin Sortie Standard du script de rapport ---")
        
        if report_stderr_str:
            print("\n--- Sortie d'Erreur du script de rapport ---")
            # try:
            print(report_stderr_str)
            # except UnicodeEncodeError:
            #     print("(Encodage forcé pour la sortie d'erreur du rapport en raison d'une UnicodeEncodeError)")
            #     output_encoding_stderr_report = sys.stderr.encoding if sys.stderr.encoding else 'utf-8'
            #     print(report_stderr_str.encode(output_encoding_stderr_report, errors='replace').decode(output_encoding_stderr_report, errors='ignore'))
            # finally:
            print("--- Fin Sortie d'Erreur du script de rapport ---")
        
        if report_process.returncode == 0:
            print("\nSUCCÈS: Génération du rapport terminée.")
            print(f"Les rapports devraient être disponibles dans le dossier '{Path(project_root) / 'results' / 'reports' / 'comprehensive'}'")
        else:
            print(f"\nÉCHEC: La génération du rapport a échoué (code de retour : {report_process.returncode}).")
            print("Vérifiez les logs ci-dessus et les dépendances du script de rapport.")
    except subprocess.TimeoutExpired:
        print("ERREUR: L'exécution du script de génération de rapport a dépassé le timeout de 300 secondes.")
        end_time_report_gen_timeout = time.time()
        print(f"INFO: Fin de la génération du rapport (timeout) : {end_time_report_gen_timeout}")
        print(f"INFO: Génération du rapport (tentative) effectuée en {end_time_report_gen_timeout - start_time_report_gen:.2f} secondes avant timeout.")
    except FileNotFoundError:
        print(f"ERREUR: L'interpréteur Python ('{sys.executable}') ou le script de rapport n'a pas été trouvé.")
    except Exception as e:
        print(f"Une erreur inattendue est survenue lors de la génération du rapport : {e}")
        import traceback
        traceback.print_exc()
    end_time_report_gen = time.time()
    print(f"INFO: Fin de la génération du rapport : {end_time_report_gen}")
    print(f"INFO: Génération du rapport effectuée en {end_time_report_gen - start_time_report_gen:.2f} secondes.")


if __name__ == "__main__":
    print("=== Début du script de démonstration EPITA ===")
    print("INFO [MAIN_EXEC]: Atteint le bloc if __name__ == \"__main__\", avant check_and_install_dependencies.") # Ligne de débogage
    check_and_install_dependencies()
    run_unit_tests()
    example_file = os.path.join(project_root, "examples", "exemple_sophisme.txt") # Utilisation de project_root
    analyze_clear_text_example(example_file)
    encrypted_analysis_output_file = analyze_encrypted_data()

    if encrypted_analysis_output_file:
        generate_report_from_analysis(encrypted_analysis_output_file)
    else:
        print("\nINFO: La génération de rapport à partir des données chiffrées a été sautée.")
        print("Cela peut être dû à une erreur lors de l'étape d'analyse chiffrée ou parce qu'aucun résultat n'a été produit.")

    print("\n=== Fin du script de démonstration EPITA ===")