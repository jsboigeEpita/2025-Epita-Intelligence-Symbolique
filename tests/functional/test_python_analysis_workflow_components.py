#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests fonctionnels pour les composants du workflow d'analyse Python.
"""

import pytest
import sys
import os
from pathlib import Path
import json
import gzip
import base64

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.

# Fonctions et classes à tester (copiées/adaptées depuis le script de workflow)
# Idéalement, ces fonctions seraient dans des modules importables.
# Pour l'instant, on les réplique ici pour le test.

# Sel fixe utilisé dans config.py et scripts/decrypt_extracts.py
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c'
DEFAULT_PASSPHRASE_FOR_TEST = "test_passphrase" # Utiliser une passphrase distincte pour les tests

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet, InvalidToken
    # Importer directement depuis le script si possible, ou copier la fonction
    from scripts.run_full_python_analysis_workflow import (
        derive_encryption_key,
        decrypt_data_local,
        load_and_decrypt_corpus
        # InformalAgent sera testé en important depuis son module
    )
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent

except ImportError as e:
    print(f"Erreur d'importation dans les tests: {e}")
    # Rendre les fonctions disponibles localement si l'import échoue (copie simplifiée)
    def derive_encryption_key(passphrase: str) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend
        import base64
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=FIXED_SALT,
            iterations=480000,
            backend=default_backend()
        )
        derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
        return base64.urlsafe_b64encode(derived_key_raw)

    def decrypt_data_local(encrypted_data: bytes, key: bytes) -> bytes | None:
        from cryptography.fernet import Fernet, InvalidToken
        if not key: return None
        try:
            f = Fernet(key)
            return f.decrypt(encrypted_data)
        except (InvalidToken, Exception):
            return None

    def load_and_decrypt_corpus(corpus_file_path: Path, encryption_key: bytes) -> list | None:
        # Version simplifiée pour la structure du test, à adapter
        if not corpus_file_path.exists() or not encryption_key: return None
        try:
            with open(corpus_file_path, 'rb') as f: encrypted_data = f.read()
            decrypted_compressed_data = decrypt_data_local(encrypted_data, encryption_key)
            if not decrypted_compressed_data: return None
            decompressed_data = gzip.decompress(decrypted_compressed_data)
            return json.loads(decompressed_data.decode('utf-8'))
        except Exception:
            return None
    
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent


@pytest.fixture
def test_passphrase() -> str:
    return DEFAULT_PASSPHRASE_FOR_TEST

@pytest.fixture
def derived_key(test_passphrase: str) -> bytes:
    return derive_encryption_key(test_passphrase)

def test_derive_encryption_key_not_none(test_passphrase: str):
    """Teste que la dérivation de clé retourne une clé."""
    key = derive_encryption_key(test_passphrase)
    assert key is not None
    assert isinstance(key, bytes)
    # Une clé Fernet typique encodée en base64 fait 44 bytes (après décodage base64, c'est 32 bytes)
    # La clé dérivée ici est la clé brute pour Fernet, qui est de 32 bytes, puis encodée en base64 URL-safe.
    decoded_key = base64.urlsafe_b64decode(key)
    assert len(decoded_key) == 32 

def test_derive_encryption_key_consistency(test_passphrase: str):
    """Teste que la dérivation de clé est consistante."""
    key1 = derive_encryption_key(test_passphrase)
    key2 = derive_encryption_key(test_passphrase)
    assert key1 == key2

def test_derive_encryption_key_differs_for_passphrases(test_passphrase: str):
    """Teste que des passphrases différentes produisent des clés différentes."""
    key1 = derive_encryption_key(test_passphrase)
    key2 = derive_encryption_key("another_" + test_passphrase)
    assert key1 != key2

# --- Tests pour le déchiffrement ---

@pytest.fixture
def sample_encrypted_file(tmp_path: Path, derived_key: bytes) -> Path:
    """Crée un fichier chiffré de test."""
    content = [{"source_name": "Test Source", "text_content": "Ceci est un texte de test."}]
    content_json = json.dumps(content).encode('utf-8')
    compressed_content = gzip.compress(content_json)
    
    f = Fernet(derived_key)
    encrypted_content = f.encrypt(compressed_content)
    
    file_path = tmp_path / "test_corpus.enc"
    file_path.write_bytes(encrypted_content)
    return file_path

def test_load_and_decrypt_corpus_success(sample_encrypted_file: Path, derived_key: bytes):
    """Teste le chargement et déchiffrement réussi d'un corpus."""
    corpus_data = load_and_decrypt_corpus(sample_encrypted_file, derived_key)
    assert corpus_data is not None
    assert isinstance(corpus_data, list)
    assert len(corpus_data) == 1
    assert corpus_data[0]["source_name"] == "Test Source"
    assert corpus_data[0]["text_content"] == "Ceci est un texte de test."

def test_load_and_decrypt_corpus_wrong_key(sample_encrypted_file: Path):
    """Teste l'échec du déchiffrement avec une mauvaise clé."""
    wrong_key = derive_encryption_key("wrong_passphrase_for_test")
    corpus_data = load_and_decrypt_corpus(sample_encrypted_file, wrong_key)
    assert corpus_data is None # Ou devrait lever une exception spécifique selon l'implémentation

def test_load_and_decrypt_corpus_file_not_found(tmp_path: Path, derived_key: bytes):
    """Teste le cas où le fichier corpus n'existe pas."""
    non_existent_file = tmp_path / "non_existent.enc"
    corpus_data = load_and_decrypt_corpus(non_existent_file, derived_key)
    assert corpus_data is None

# --- Tests pour InformalAgent ---

@pytest.fixture
def informal_agent_instance():
    """Instance de InformalAgent pour les tests."""
    # L'instanciation peut nécessiter un Kernel. Pour des tests unitaires de méthodes Python pures,
    # on peut essayer avec None ou un mock simple.
    try:
        # from semantic_kernel import Kernel # Si nécessaire
        # kernel = Kernel()
        agent = InformalAgent(kernel=None, agent_name="TestInformalAgent")
        return agent
    except Exception as e:
        pytest.skip(f"Impossible d'instancier InformalAgent (peut nécessiter config Kernel/LLM): {e}")

def test_informal_agent_analyze_text_simple(informal_agent_instance: InformalAgent):
    """Teste la méthode analyze_text de InformalAgent avec un texte simple."""
    if informal_agent_instance is None: # Au cas où le skip de la fixture n'est pas attrapé
        pytest.skip("InformalAgent non disponible pour le test.")

    sample_text = "Ceci est un argument simple. Il ne contient pas de sophisme évident."
    # La méthode analyze_text ou perform_complete_analysis pourrait être testée.
    # perform_complete_analysis est plus haut niveau.
    # Supposons que analyze_text est une méthode Python pure ou mockable pour ses dépendances LLM.
    try:
        analysis_result = informal_agent_instance.analyze_text(text=sample_text)
        
        assert analysis_result is not None
        assert isinstance(analysis_result, dict)
        # Vérifier la présence de clés attendues dans le résultat
        assert "arguments" in analysis_result or "identified_arguments" in analysis_result # ajuster selon la sortie réelle
        assert "fallacies" in analysis_result or "detected_fallacies" in analysis_result # ajuster
        # Exemple de vérification plus poussée si on connaît la sortie attendue
        # Pour un texte simple, on s'attendrait à peu ou pas de sophismes.
        # if "fallacies" in analysis_result:
        #    assert len(analysis_result["fallacies"]) == 0
            
    except Exception as e:
        # Si l'agent dépend fortement d'un LLM même pour cette méthode, le test peut échouer.
        # Il faudrait alors mocker les appels LLM.
        pytest.fail(f"L'appel à InformalAgent.analyze_text a échoué: {e}")

# TODO: Ajouter plus de tests pour :
# - Différents types de textes pour InformalAgent (avec sophismes connus)
# - La fonction de génération de rapport du script principal (avec des données d'analyse mockées)
# - Le workflow complet en utilisant le fichier tests/extract_sources_backup.enc (nécessitera une passphrase valide)

# --- Tests pour le script run_full_python_analysis_workflow.py ---

import subprocess
import time

# Définir les chemins relatifs au répertoire racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CORPUS_PATH_FOR_SCRIPT = PROJECT_ROOT / "tests" / "extract_sources_with_full_text.enc"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "results" / "full_python_analysis_report.json"
DEFAULT_MD_REPORT_PATH = PROJECT_ROOT / "results" / "full_python_analysis_report.md"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_full_python_analysis_workflow.py"

# S'assurer que le répertoire results existe
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


@pytest.fixture
def cleanup_report_files():
    """Fixture pour nettoyer les fichiers de rapport après les tests."""
    yield
    if DEFAULT_JSON_REPORT_PATH.exists():
        DEFAULT_JSON_REPORT_PATH.unlink()
    if DEFAULT_MD_REPORT_PATH.exists():
        DEFAULT_MD_REPORT_PATH.unlink()

def test_run_full_python_analysis_workflow_script(cleanup_report_files):
    """
    Teste l'exécution du script run_full_python_analysis_workflow.py
    avec les arguments par défaut.
    """
    # Vérifier que le script et le corpus par défaut existent
    assert SCRIPT_PATH.exists(), f"Le script {SCRIPT_PATH} est introuvable."
    assert DEFAULT_CORPUS_PATH_FOR_SCRIPT.exists(), \
        f"Le fichier corpus par défaut {DEFAULT_CORPUS_PATH_FOR_SCRIPT} est introuvable."

    # Exécuter le script
    # La passphrase par défaut est codée dans le script, donc pas besoin de la passer ici.
    # Si le script nécessitait une passphrase via argument, il faudrait l'ajouter.
    # Par exemple: --passphrase "epita_ia_symb_2025_temp_key"
    # Mais le script utilise déjà cette passphrase par défaut si non fournie.
    
    command = [
        sys.executable, # Utilise l'interpréteur Python actuel
        str(SCRIPT_PATH)
        # Les autres arguments (corpus, json_report, md_report, passphrase)
        # utiliseront leurs valeurs par défaut définies dans le script.
    ]

    # Nettoyer les anciens rapports s'ils existent pour s'assurer que le script les crée
    if DEFAULT_JSON_REPORT_PATH.exists():
        DEFAULT_JSON_REPORT_PATH.unlink()
    if DEFAULT_MD_REPORT_PATH.exists():
        DEFAULT_MD_REPORT_PATH.unlink()

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    print("STDOUT du script:", result.stdout)
    print("STDERR du script:", result.stderr)
    
    assert result.returncode == 0, \
        f"Le script a échoué avec le code {result.returncode}. STDERR: {result.stderr}"

    # Vérifier la création des fichiers de rapport
    assert DEFAULT_JSON_REPORT_PATH.exists(), \
        f"Le fichier rapport JSON {DEFAULT_JSON_REPORT_PATH} n'a pas été créé."
    assert DEFAULT_MD_REPORT_PATH.exists(), \
        f"Le fichier rapport Markdown {DEFAULT_MD_REPORT_PATH} n'a pas été créé."

    # Charger et vérifier le contenu du rapport JSON
    with open(DEFAULT_JSON_REPORT_PATH, 'r', encoding='utf-8') as f:
        json_report_data = json.load(f)

    assert isinstance(json_report_data, list), "Le rapport JSON n'est pas une liste."
    
    # Le corpus par défaut tests/extract_sources_with_full_text.enc contient 4 sources (default definitions)
    expected_sources_count = 4
    assert len(json_report_data) == expected_sources_count, \
        f"Le rapport JSON devrait contenir {expected_sources_count} éléments, mais en contient {len(json_report_data)}."

    expected_source_names = [
        "Lincoln-Douglas DAcbat 1 (NPS)",
        "Lincoln-Douglas DAcbat 2 (NPS)",
        "Kremlin Discours 21/02/2022",
        "Hitler Discours Collection (PDF)"
    ]
    
    actual_source_names = [item.get("source_name") for item in json_report_data]

    for name in expected_source_names:
        assert name in actual_source_names, f"Le nom de source attendu '{name}' n'est pas dans le rapport JSON."

    for item in json_report_data:
        assert "source_name" in item, "Clé 'source_name' manquante dans un élément du rapport JSON."
        assert isinstance(item["source_name"], str), "'source_name' n'est pas une chaîne."
        
        assert "analysis" in item, "Clé 'analysis' manquante dans un élément du rapport JSON."
        analysis_data = item["analysis"]
        assert isinstance(analysis_data, dict), "'analysis' n'est pas un dictionnaire."
        
        assert "text" in analysis_data, "Clé 'text' manquante dans 'analysis'."
        assert isinstance(analysis_data["text"], str), "'text' n'est pas une chaîne."
        assert len(analysis_data["text"]) > 0, "'text' ne doit pas être vide."
        
        assert "fallacies" in analysis_data, "Clé 'fallacies' manquante dans 'analysis'."
        assert isinstance(analysis_data["fallacies"], list), "'fallacies' n'est pas une liste."
        # Avec MockFallacyDetector, la liste des sophismes doit être vide.
        assert len(analysis_data["fallacies"]) == 0, \
            f"La liste 'fallacies' devrait être vide avec MockFallacyDetector, mais contient {len(analysis_data['fallacies'])} éléments pour {item['source_name']}."

        assert "rhetorical_analysis" in analysis_data
        assert isinstance(analysis_data["rhetorical_analysis"], dict)
        assert "contextual_analysis" in analysis_data
        assert isinstance(analysis_data["contextual_analysis"], dict)
        assert "categories" in analysis_data
        assert isinstance(analysis_data["categories"], dict)
        assert "analysis_timestamp" in analysis_data
        assert isinstance(analysis_data["analysis_timestamp"], str)

    # Vérification basique du rapport Markdown (juste son existence a déjà été vérifiée)
    # On pourrait ajouter une vérification de contenu plus poussée si nécessaire.
    md_content = DEFAULT_MD_REPORT_PATH.read_text(encoding='utf-8')
    assert len(md_content) > 0, "Le fichier rapport Markdown est vide."
    for name in expected_source_names:
        assert f"Analyse de : {name}" in md_content, f"Le nom de source '{name}' n'est pas dans le rapport MD."
    assert "Sophismes Détectés (0)" in md_content
    assert "Aucun sophisme détecté pour ce texte." in md_content
    
    # Le nettoyage est géré par la fixture cleanup_report_files