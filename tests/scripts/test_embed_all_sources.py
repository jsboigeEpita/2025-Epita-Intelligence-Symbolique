# -*- coding: utf-8 -*-
import pytest
import subprocess
import json
import gzip
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajuster le sys.path pour les imports locaux
import sys
SCRIPT_DIR_TEST = Path(__file__).resolve().parent.parent.parent # Remonter à la racine du projet
sys.path.insert(0, str(SCRIPT_DIR_TEST))

from argumentation_analysis.ui import utils as aa_utils
from argumentation_analysis.ui import file_operations
from argumentation_analysis.ui.config import FIXED_SALT as CONFIG_FIXED_SALT # Importer le sel
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

# Chemin vers le script à tester
EMBED_SCRIPT_PATH = SCRIPT_DIR_TEST / "scripts" / "embed_all_sources.py"

@pytest.fixture
def test_passphrase():
    # Passphrase offusquée pour les tests (équivalent à "Propaganda")
    # Simple décalage de caractères et inversion
    obfuscated = "Oqnobfzmeb"  # "Propaganda" avec décalage -1
    return "".join([chr(ord(c) + 1) for c in obfuscated])

@pytest.fixture
def test_key(test_passphrase):
    # aa_utils attend une clé Fernet (bytes), le script utilise la passphrase directement
    # Pour les besoins du test, on va générer une clé compatible avec aa_utils pour créer/lire les fichiers
    # Le script lui-même n'utilise pas Fernet.generate_key mais une dérivation (implicite dans aa_utils.load/save)
    # Pour ce test, on va utiliser la même logique que aa_utils pour la clé dérivée si possible,
    # ou juste une clé Fernet pour chiffrer/déchiffrer les fichiers de test.
    # Le script passe la passphrase à aa_utils, qui s'en sert pour dériver la clé.
    # Donc, on a juste besoin de la passphrase.
    # Pour créer des fichiers de test chiffrés, on utilise aa_utils.save_extract_definitions
    # qui prend la passphrase et la convertit en clé.
    return Fernet.generate_key() # Clé factice pour les tests, la vraie dérivation est dans aa_utils

@pytest.fixture
def minimal_config_data_no_text():
    return [
        {
            "source_name": "Minimal Source",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/file1.txt",
            "extracts": [{"extract_name": "e1", "start_marker": "START1", "end_marker": "END1"}],
            # full_text est manquant
        }
    ]

@pytest.fixture
def minimal_config_data_with_text():
    return [
        {
            "source_name": "Minimal Source With Text",
            "source_type": "direct_download",
            "schema": "http",
            "host_parts": ["testserver"],
            "path": "/file2.txt",
            "extracts": [],
            "full_text": "This text is already here."
        }
    ]

# Fonction de dérivation de clé (copiée/adaptée de embed_all_sources.py)
def derive_key_for_test(passphrase: str) -> bytes:
    if not passphrase:
        raise ValueError("Passphrase vide pour dérivation de clé de test")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=CONFIG_FIXED_SALT, # Utiliser le sel importé
        iterations=480000, # Doit correspondre au script
        backend=default_backend()
    )
    derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
    return base64.urlsafe_b64encode(derived_key_raw)

@pytest.fixture
def create_encrypted_config_file(tmp_path, test_passphrase):
    def _creator(filename: str, data: list, passphrase_override=None):
        input_file = tmp_path / filename
        
        current_passphrase = passphrase_override or test_passphrase
        derived_key = derive_key_for_test(current_passphrase)

        should_embed = any("full_text" in item for item in data)

        file_operations.save_extract_definitions(
            extract_definitions=data,
            config_file=input_file,
            encryption_key=derived_key, # Passer la clé dérivée (bytes)
            embed_full_text=should_embed,
            config={}
        )
        assert input_file.exists()
        return input_file
    return _creator

# Mocker les fonctions de aa_utils qui font des appels réseau ou manipulent le cache global
@pytest.fixture(autouse=True)
def mock_aa_utils_network_calls(tmp_path): # Ajout de tmp_path pour TEMP_DOWNLOAD_DIR
    # Mocker get_full_text_for_source pour contrôler son retour et éviter les appels réseau
    # Patcher la fonction get_full_text_for_source dans le module ui.utils
    # et patcher requests.get dans le module ui.utils car c'est là qu'il est appelé par fetch_direct_text
    with patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text, \
         patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None), \
         patch('argumentation_analysis.ui.utils.save_to_cache', return_value=None), \
         patch('argumentation_analysis.ui.config.load_extract_sources') as mock_load_extract_sources, \
         patch('argumentation_analysis.ui.utils.requests.get') as mock_requests_get:

        # Configurer le mock de requests.get pour simuler des réponses réseau
        def mock_requests_get_side_effect(url, **kwargs):
            mock_response = MagicMock()
            if "testserver/file1.txt" in url:
                mock_response.status_code = 200
                mock_response.content = f"Fetched content for /file1.txt".encode('utf-8')
                mock_response.text = f"Fetched content for /file1.txt"
                mock_response.raise_for_status = MagicMock()
            elif "error/error.txt" in url: # Pour simuler une erreur de fetch
                mock_response.status_code = 404
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Simulated HTTP error")
            else: # Comportement par défaut pour d'autres URLs
                mock_response.status_code = 404
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("URL not mocked")
            return mock_response
        mock_requests_get.side_effect = mock_requests_get_side_effect
        
        # Configurer le mock de get_full_text_for_source (la fonction patchée directement dans son module d'origine)
        def side_effect_get_text(source_info, app_config=None):
            # Simuler la récupération de texte
            if source_info["source_name"] == "Minimal Source":
                return f"Fetched content for {source_info['path']}"
            elif source_info["source_name"] == "Source Error":
                raise ConnectionError("Simulated network error")
            return None # Par défaut
        mock_get_text.side_effect = side_effect_get_text
        
        # Configurer le mock de load_app_config pour retourner un objet AppConfig simulé
        mock_app_config_instance = MagicMock() # Mock flexible pour permettre l'ajout d'attributs
        
        config_values_for_get = {
            'JINA_READER_PREFIX': "mock_jina_prefix_via_get",
            'TIKA_SERVER_URL': "mock_tika_url_via_get",
            'PLAINTEXT_EXTENSIONS': ['.mocktxt'],
            'TEMP_DOWNLOAD_DIR': tmp_path / "mock_temp_dir_via_get" # Important que ce soit un Path
        }
        
        def app_config_get_side_effect(key, default=None):
            # Simule le comportement de .get() d'un dictionnaire
            return config_values_for_get.get(key, default)
            
        mock_app_config_instance.get.side_effect = app_config_get_side_effect
        
        mock_app_config_instance.JINA_READER_PREFIX = config_values_for_get['JINA_READER_PREFIX']
        mock_app_config_instance.TIKA_SERVER_URL = config_values_for_get['TIKA_SERVER_URL']
        mock_app_config_instance.PLAINTEXT_EXTENSIONS = config_values_for_get['PLAINTEXT_EXTENSIONS']
        mock_app_config_instance.TEMP_DOWNLOAD_DIR = config_values_for_get['TEMP_DOWNLOAD_DIR']
        
        mock_load_extract_sources.return_value = mock_app_config_instance

        # Configurer le mock_get_text (qui est le patch de 'argumentation_analysis.ui.utils.get_full_text_for_source')
        mock_get_text.side_effect = side_effect_get_text

        yield mock_get_text, mock_load_extract_sources


# Importer la fonction main du script pour l'appeler directement
from scripts.embed_all_sources import main as embed_main
from cryptography.fernet import InvalidToken # Importer pour le test d'exception

@pytest.fixture
def mock_sys_argv(monkeypatch):
    """Fixture pour mocker sys.argv."""
    def _mocker(args_list):
        # Le premier élément de sys.argv est le nom du script
        monkeypatch.setattr(sys, 'argv', [str(EMBED_SCRIPT_PATH)] + args_list)
    return _mocker

@pytest.fixture
def mock_os_environ(monkeypatch):
    """Fixture pour mocker os.environ pour la durée d'un test."""
    original_environ = os.environ.copy()
    
    # Cette fixture ne retourne rien, elle modifie directement os.environ via monkeypatch
    # et pytest s'occupe du teardown (restauration de os.environ par monkeypatch)
    # Si on veut passer des env_vars spécifiques au test, le test doit le faire via monkeypatch.setenv

    # Pour permettre aux tests de définir des variables spécifiques :
    class EnvSetter:
        def __init__(self, mp):
            self.monkeypatch = mp
            self.modified_keys = {}

        def set_env(self, env_vars_dict):
            for k, v in env_vars_dict.items():
                self.modified_keys[k] = self.monkeypatch.getenv(k, None) # Sauvegarder l'ancienne valeur
                self.monkeypatch.setenv(k, str(v))

        def clear_env(self, keys_to_clear):
            for k in keys_to_clear:
                self.modified_keys[k] = self.monkeypatch.getenv(k, None)
                self.monkeypatch.delenv(k, raising=False)
        
        def __enter__(self):
            return self # Permet d'utiliser avec "with" si on veut, mais pas obligatoire

        def __exit__(self, type, value, traceback):
            # Monkeypatch gère la restauration des valeurs originales à la fin du test
            # Mais si on a modifié des clés spécifiques, on peut les restaurer ici si monkeypatch ne le fait pas pour setenv/delenv
            # Cependant, monkeypatch.setenv et delenv devraient gérer cela automatiquement.
            pass

    yield EnvSetter(monkeypatch) # Le test recevra l'objet EnvSetter

    # Monkeypatch devrait restaurer os.environ à son état original après le test
    # Si ce n'est pas le cas pour setenv/delenv, il faudrait une restauration manuelle ici.
    # Mais typiquement, monkeypatch s'en charge.


def run_script_direct(args_list: list, mock_sys_argv, env_setter, env_vars_to_set: dict = None):
    """Exécute la fonction main() du script directement, en mockant sys.argv et os.environ."""
    mock_sys_argv(args_list)
    
    if env_vars_to_set:
        env_setter.set_env(env_vars_to_set)
    
    # Si certaines variables doivent être absentes (comme TEXT_CONFIG_PASSPHRASE pour un test)
    # le test devrait utiliser env_setter.clear_env() avant d'appeler run_script_direct,
    # ou run_script_direct pourrait prendre un autre paramètre `env_vars_to_clear`.

    from io import StringIO
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    return_code = 0

    with patch('sys.stdout', stdout_capture), patch('sys.stderr', stderr_capture):
        try:
            embed_main()
        except SystemExit as e:
            return_code = e.code if isinstance(e.code, int) else 1
        except Exception:
            import traceback
            stderr_capture.write("\nEXCEPTION IN SCRIPT:\n")
            stderr_capture.write(traceback.format_exc())
            return_code = 1
            
    # Restaurer l'environnement
    if env_vars_to_set: # Correction ici: utiliser env_vars_to_set
        for k, v_orig in original_environ_values.items():
            if v_orig is None:
                if k in os.environ: del os.environ[k]
            else:
                os.environ[k] = v_orig
            
    class MockCompletedProcess:
        def __init__(self, stdout, stderr, returncode):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    return MockCompletedProcess(stdout_capture.getvalue(), stderr_capture.getvalue(), return_code)


def decrypt_and_load_json(file_path: Path, passphrase: str) -> list:
    # Utiliser aa_utils.load_extract_definitions pour déchiffrer
    # Le paramètre 'config' (app_config) est optionnel pour load_extract_definitions
    # s'il n'est pas utilisé pour la logique de fallback ou autre.
    # Ici, on veut juste le contenu déchiffré.
    derived_key = derive_key_for_test(passphrase)
    loaded_data = file_operations.load_extract_definitions(
        config_file=file_path,
        key=derived_key, # Passer la clé dérivée (bytes)
        # app_config={}
    )
    return loaded_data


# --- Tests ---

def test_embed_script_success_no_text_initially(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase, mock_aa_utils_network_calls, mock_sys_argv, mock_os_environ
):
    mock_get_text, _ = mock_aa_utils_network_calls
    input_file = create_encrypted_config_file("input.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    # Utiliser run_script_direct avec les fixtures mock_sys_argv et mock_os_environ
    # Ces fixtures doivent être passées en argument au test qui utilise run_script_direct
    # Pour l'instant, on suppose qu'elles sont disponibles dans le scope du test via pytest
    # Ceci nécessitera d'ajouter mock_sys_argv et mock_os_environ aux paramètres des fonctions de test.
    # Pour l'instant, je vais appeler la fonction interne de la fixture pour mock_os_environ.
    # La fixture mock_sys_argv est appelée directement.
    # Correction: mock_os_environ est maintenant un EnvSetter.
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)


    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0, f"Le script a échoué avec le code {result.returncode}"
    assert output_file.exists()

    # Vérifier que get_full_text_for_source a été appelé
    mock_get_text.assert_called_once()
    call_args = mock_get_text.call_args[0][0] # Premier argument positionnel de l'appel
    assert call_args["source_name"] == "Minimal Source"


    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert len(output_data) == 1
    assert output_data[0]["source_name"] == "Minimal Source"
    assert "full_text" in output_data[0]
    assert output_data[0]["full_text"] == "Fetched content for /file1.txt"
    # Les logs vont sur stderr
    assert "Traitement des sources terminé. 1 sources mises à jour, 0 erreurs de récupération." in result.stderr
    assert "Script d'embarquement des sources terminé avec succès." in result.stderr

def test_embed_script_text_already_present(
    tmp_path, create_encrypted_config_file, minimal_config_data_with_text, test_passphrase, mock_aa_utils_network_calls, mock_sys_argv, mock_os_environ
):
    mock_get_text, _ = mock_aa_utils_network_calls
    input_file = create_encrypted_config_file("input_with_text.enc", minimal_config_data_with_text)
    output_file = tmp_path / "output_with_text.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    assert output_file.exists()

    # get_full_text_for_source ne devrait pas être appelé si le texte est déjà là
    mock_get_text.assert_not_called()

    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert len(output_data) == 1
    assert output_data[0]["full_text"] == "This text is already here."
    assert "Le texte complet est déjà présent pour la source" in result.stderr
    assert "Traitement des sources terminé. 0 sources mises à jour, 0 erreurs de récupération." in result.stderr

def test_embed_script_force_overwrite(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase, mock_sys_argv, mock_os_environ
):
    input_file = create_encrypted_config_file("input_force.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_force.enc"
    output_file.write_text("pre_existing_content") # Créer un fichier existant

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase, "--force"]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)
    assert result.returncode == 0
    assert output_file.exists()
    assert output_file.read_text() != "pre_existing_content" # Doit être écrasé
    assert f"Le fichier de sortie {output_file} existe et sera écrasé (--force activé)." in result.stderr # sur stderr


def test_embed_script_output_exists_no_force(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase, mock_sys_argv, mock_os_environ
):
    input_file = create_encrypted_config_file("input_noforce.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_noforce.enc"
    output_file.write_text("pre_existing_content")

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)
    assert result.returncode == 1 # Doit échouer
    assert f"Le fichier de sortie {output_file} existe déjà. Utilisez --force pour l'écraser. Arrêt." in result.stderr
    assert output_file.read_text() == "pre_existing_content" # Ne doit pas être modifié


def test_embed_script_passphrase_from_env(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase, mock_sys_argv, mock_os_environ
):
    input_file = create_encrypted_config_file("input_env_pass.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_env_pass.enc"

    env_vars = {"TEXT_CONFIG_PASSPHRASE": test_passphrase}
    args = ["--input-config", str(input_file), "--output-config", str(output_file)] # Pas de --passphrase
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=env_vars)
    assert result.returncode == 0
    assert output_file.exists()
    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert output_data[0]["full_text"] == "Fetched content for /file1.txt"


def test_embed_script_missing_passphrase(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, mock_sys_argv, mock_os_environ
):
    input_file = create_encrypted_config_file("input_no_pass.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_no_pass.enc"

    # S'assurer que la variable d'env n'est pas définie
    env_vars = os.environ.copy()
    if "TEXT_CONFIG_PASSPHRASE" in env_vars:
        del env_vars["TEXT_CONFIG_PASSPHRASE"]

    args = ["--input-config", str(input_file), "--output-config", str(output_file)]
    # S'assurer que TEXT_CONFIG_PASSPHRASE n'est pas dans l'environnement pour ce test
    # La fixture mock_os_environ (via EnvSetter) gère la restauration.
    # On doit s'assurer que la variable est absente avant l'appel.
    mock_os_environ.clear_env(["TEXT_CONFIG_PASSPHRASE"])
    
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None) # env_vars_to_set est None car on a déjà nettoyé
    assert result.returncode == 1
    assert "Passphrase non fournie (ni via --passphrase, ni via TEXT_CONFIG_PASSPHRASE). Arrêt." in result.stderr


def test_embed_script_input_file_not_found(tmp_path, test_passphrase, mock_sys_argv, mock_os_environ):
    non_existent_input = tmp_path / "ghost.enc"
    output_file = tmp_path / "output_ghost.enc"
    args = ["--input-config", str(non_existent_input), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)
    assert result.returncode == 1
    assert f"Le fichier d'entrée {non_existent_input} n'existe pas. Arrêt." in result.stderr


def test_embed_script_incorrect_passphrase(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase, mock_sys_argv, mock_os_environ
):
    input_file = create_encrypted_config_file("input_bad_pass.enc", minimal_config_data_no_text, passphrase_override=test_passphrase)
    output_file = tmp_path / "output_bad_pass.enc"
    wrong_passphrase = "thisiswrong"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", wrong_passphrase]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)
    # Le script devrait échouer car load_extract_definitions (le mock) lèvera InvalidToken
    # que le script principal attrape.
    # L'erreur exacte dépend de comment aa_utils.load_extract_definitions gère une mauvaise clé.
    # Typiquement, Fernet lèvera InvalidToken.
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 1 # Ou un autre code d'erreur si géré différemment
    # Vérifier un message d'erreur approprié.
    # Le script principal loggue "Erreur lors du chargement ou du déchiffrement" sur stderr
    assert f"Erreur lors du chargement ou du déchiffrement de {input_file}" in result.stderr
    # Le log de file_operations.load_extract_definitions (via App.UI.Utils) concernant l'échec de déchiffrement va aussi sur stderr
    assert "Échec déchiffrement. Utilisation définitions par défaut." in result.stderr

def test_embed_script_source_fetch_error(
    tmp_path, create_encrypted_config_file, test_passphrase, mock_aa_utils_network_calls, mock_sys_argv, mock_os_environ
):
    mock_get_text, _ = mock_aa_utils_network_calls
    source_error_data = [{
        "source_name": "Source Error", "source_type": "direct_download",
        "schema": "http", "host_parts": ["error"], "path": "/error.txt", "extracts": []
    }]
    input_file = create_encrypted_config_file("input_fetch_error.enc", source_error_data)
    output_file = tmp_path / "output_fetch_error.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0 # Le script doit finir, mais avec des erreurs logguées
    
    # Vérifier que get_full_text_for_source a été appelé et a levé une exception (simulée par le mock)
    mock_get_text.assert_called_once()
    assert "Erreur lors de la récupération du texte pour la source Source Error: Simulated network error" in result.stderr # sur stderr
    assert "Traitement des sources terminé. 0 sources mises à jour, 1 erreurs de récupération." in result.stderr # sur stderr

    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert len(output_data) == 1
    assert "full_text" not in output_data[0] # Le texte n'a pas pu être récupéré


def test_embed_script_empty_input_config(
    tmp_path, create_encrypted_config_file, test_passphrase, mock_sys_argv, mock_os_environ
):
    # Créer un fichier de config vide (ou avec une liste vide de sources)
    input_file = create_encrypted_config_file("input_empty.enc", [])
    output_file = tmp_path / "output_empty.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script_direct(args, mock_sys_argv, mock_os_environ, env_vars_to_set=None)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    # Le message "4 définitions d'extraits chargées et déchiffrées." vient du script si le chargement initial échoue et prend les défauts.
    # Si le fichier d'entrée est vraiment vide (et correctement déchiffré comme vide), le script devrait loguer qqch comme "0 définitions d'extraits chargées"
    # ou le message d'avertissement si la liste est vide après chargement.
    # Le log "Aucune définition d'extrait trouvée dans..." est un WARNING, donc sur stderr.
    assert f"Aucune définition d'extrait trouvée dans {input_file}" in result.stderr # Vérifier le warning sur stderr
    # Avec la correction dans embed_all_sources.py, le script essaie de sauvegarder même si les définitions sont vides.
    # Donc, le message "Aucune définition d'extrait à sauvegarder..." ne devrait plus apparaître si la sauvegarde réussit.
    # On vérifie plutôt que le fichier de sortie est créé et que les logs de sauvegarde sont présents.
    assert output_file.exists()
    assert f"Sauvegarde des définitions d'extraits (mises à jour ou vides) dans {output_file}" in result.stderr
    assert f"Définitions d'extraits sauvegardées avec succès dans {output_file}" in result.stderr

    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert output_data == []