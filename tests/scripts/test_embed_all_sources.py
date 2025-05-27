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

from argumentation_analysis.ui import utils as aa_utils # Pour générer/lire les fichiers de test
from argumentation_analysis.ui import file_operations # Pour save_extract_definitions
from cryptography.fernet import Fernet

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

@pytest.fixture
def create_encrypted_config_file(tmp_path, test_passphrase):
    def _creator(filename: str, data: list, passphrase_override=None):
        input_file = tmp_path / filename
        # Utiliser la fonction de sauvegarde de aa_utils pour créer un fichier chiffré valide
        # save_extract_definitions s'attend à une clé Fernet, mais le script passe une passphrase.
        # On va simuler le comportement du script en passant la passphrase.
        # aa_utils.save_extract_definitions gère la dérivation de la clé depuis la passphrase.
        
        # Le paramètre 'config' de save_extract_definitions est optionnel et sert à get_full_text_for_source
        # Pour la création du fichier d'entrée, on peut le mettre à None ou un dict vide.
        # On met embed_full_text=False pour s'assurer que le texte n'est pas ajouté par cette sauvegarde.
        # Si data contient déjà full_text, il sera conservé si embed_full_text=True, ou retiré si False.
        # Pour ce test, on veut contrôler si le script l'ajoute.
        
        # Déterminer si on doit pré-embarquer le texte ou non basé sur la présence de 'full_text' dans data
        # et le but du test. Pour un fichier d'entrée "sans texte", on s'assure qu'il n'y est pas.
        should_embed = any("full_text" in item for item in data)

        file_operations.save_extract_definitions(
            data, # definitions_obj (premier paramètre positionnel)
            input_file, # definitions_path (deuxième paramètre positionnel)
            passphrase_override or test_passphrase, # key_path (troisième paramètre positionnel)
            embed_full_text=should_embed, # embed_full_text (paramètre nommé)
            config={} # config (paramètre nommé)
        )
        assert input_file.exists()
        return input_file
    return _creator

# Mocker les fonctions de aa_utils qui font des appels réseau ou manipulent le cache global
@pytest.fixture(autouse=True)
def mock_aa_utils_network_calls(tmp_path): # Ajout de tmp_path pour TEMP_DOWNLOAD_DIR
    # Mocker get_full_text_for_source pour contrôler son retour et éviter les appels réseau
    with patch('argumentation_analysis.ui.utils.get_full_text_for_source') as mock_get_text, \
         patch('argumentation_analysis.ui.utils.load_from_cache', return_value=None), \
         patch('argumentation_analysis.ui.utils.save_to_cache', return_value=None), \
         patch('argumentation_analysis.ui.config.load_extract_sources') as mock_load_extract_sources:

        # Configurer le mock de get_full_text_for_source
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
        
        # Définir aussi les attributs directs au cas où le code y accède directement
        # (bien que get_full_text_for_source semble utiliser .get())
        mock_app_config_instance.JINA_READER_PREFIX = config_values_for_get['JINA_READER_PREFIX']
        mock_app_config_instance.TIKA_SERVER_URL = config_values_for_get['TIKA_SERVER_URL']
        mock_app_config_instance.PLAINTEXT_EXTENSIONS = config_values_for_get['PLAINTEXT_EXTENSIONS']
        mock_app_config_instance.TEMP_DOWNLOAD_DIR = config_values_for_get['TEMP_DOWNLOAD_DIR']
        
        mock_load_extract_sources.return_value = mock_app_config_instance

        yield mock_get_text, mock_load_extract_sources


def run_script(args_list: list, env_vars: dict = None):
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    process = subprocess.run(
        [sys.executable, str(EMBED_SCRIPT_PATH)] + args_list,
        capture_output=True,
        text=True,
        env=env,
        check=False # On vérifiera le code de retour manuellement
    )
    return process

def decrypt_and_load_json(file_path: Path, passphrase: str) -> list:
    # Utiliser aa_utils.load_extract_definitions pour déchiffrer
    # Le paramètre 'config' (app_config) est optionnel pour load_extract_definitions
    # s'il n'est pas utilisé pour la logique de fallback ou autre.
    # Ici, on veut juste le contenu déchiffré.
    loaded_data = aa_utils.load_extract_definitions(
        config_file=file_path, # Doit être config_file
        key=passphrase, # Doit être key
        # app_config={} # Fournir un app_config minimal si nécessaire
    )
    return loaded_data


# --- Tests ---

def test_embed_script_success_no_text_initially(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase, mock_aa_utils_network_calls
):
    mock_get_text, _ = mock_aa_utils_network_calls
    input_file = create_encrypted_config_file("input.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script(args)

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
    assert "Traitement des sources terminé. 1 sources mises à jour, 0 erreurs de récupération." in result.stdout
    assert "Script d'embarquement des sources terminé avec succès." in result.stdout

def test_embed_script_text_already_present(
    tmp_path, create_encrypted_config_file, minimal_config_data_with_text, test_passphrase, mock_aa_utils_network_calls
):
    mock_get_text, _ = mock_aa_utils_network_calls
    input_file = create_encrypted_config_file("input_with_text.enc", minimal_config_data_with_text)
    output_file = tmp_path / "output_with_text.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script(args)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    assert output_file.exists()

    # get_full_text_for_source ne devrait pas être appelé si le texte est déjà là
    mock_get_text.assert_not_called()

    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert len(output_data) == 1
    assert output_data[0]["full_text"] == "This text is already here."
    assert "Le texte complet est déjà présent pour la source" in result.stdout # Vérifier le log
    assert "Traitement des sources terminé. 0 sources mises à jour, 0 erreurs de récupération." in result.stdout


def test_embed_script_force_overwrite(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase
):
    input_file = create_encrypted_config_file("input_force.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_force.enc"
    output_file.write_text("pre_existing_content") # Créer un fichier existant

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase, "--force"]
    result = run_script(args)
    assert result.returncode == 0
    assert output_file.exists()
    assert output_file.read_text() != "pre_existing_content" # Doit être écrasé
    assert f"Le fichier de sortie {output_file} existe et sera écrasé (--force activé)." in result.stdout


def test_embed_script_output_exists_no_force(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase
):
    input_file = create_encrypted_config_file("input_noforce.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_noforce.enc"
    output_file.write_text("pre_existing_content")

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script(args)
    assert result.returncode == 1 # Doit échouer
    assert f"Le fichier de sortie {output_file} existe déjà. Utilisez --force pour l'écraser. Arrêt." in result.stderr
    assert output_file.read_text() == "pre_existing_content" # Ne doit pas être modifié


def test_embed_script_passphrase_from_env(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase
):
    input_file = create_encrypted_config_file("input_env_pass.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_env_pass.enc"

    env_vars = {"TEXT_CONFIG_PASSPHRASE": test_passphrase}
    args = ["--input-config", str(input_file), "--output-config", str(output_file)] # Pas de --passphrase
    result = run_script(args, env_vars=env_vars)
    assert result.returncode == 0
    assert output_file.exists()
    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert output_data[0]["full_text"] == "Fetched content for /file1.txt"


def test_embed_script_missing_passphrase(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text
):
    input_file = create_encrypted_config_file("input_no_pass.enc", minimal_config_data_no_text)
    output_file = tmp_path / "output_no_pass.enc"

    # S'assurer que la variable d'env n'est pas définie
    env_vars = os.environ.copy()
    if "TEXT_CONFIG_PASSPHRASE" in env_vars:
        del env_vars["TEXT_CONFIG_PASSPHRASE"]

    args = ["--input-config", str(input_file), "--output-config", str(output_file)]
    result = run_script(args, env_vars=env_vars) # Exécuter avec un env propre pour cette var
    assert result.returncode == 1
    assert "Passphrase non fournie (ni via --passphrase, ni via TEXT_CONFIG_PASSPHRASE). Arrêt." in result.stderr


def test_embed_script_input_file_not_found(tmp_path, test_passphrase):
    non_existent_input = tmp_path / "ghost.enc"
    output_file = tmp_path / "output_ghost.enc"
    args = ["--input-config", str(non_existent_input), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script(args)
    assert result.returncode == 1
    assert f"Le fichier d'entrée {non_existent_input} n'existe pas. Arrêt." in result.stderr


def test_embed_script_incorrect_passphrase(
    tmp_path, create_encrypted_config_file, minimal_config_data_no_text, test_passphrase
):
    input_file = create_encrypted_config_file("input_bad_pass.enc", minimal_config_data_no_text, passphrase_override=test_passphrase)
    output_file = tmp_path / "output_bad_pass.enc"
    wrong_passphrase = "thisiswrong"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", wrong_passphrase]
    result = run_script(args)
    # Le script devrait échouer car load_extract_definitions retournera les valeurs par défaut ou lèvera une erreur
    # que le script principal attrape.
    # L'erreur exacte dépend de comment aa_utils.load_extract_definitions gère une mauvaise clé.
    # Typiquement, Fernet lèvera InvalidToken.
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 1 # Ou un autre code d'erreur si géré différemment
    # Vérifier un message d'erreur approprié. aa_utils.load_extract_definitions loggue déjà.
    # Le script principal loggue "Erreur lors du chargement ou du déchiffrement"
    assert f"Erreur lors du chargement ou du déchiffrement de {input_file}" in result.stderr
    # Ou plus spécifiquement, si on peut prédire le log de aa_utils:
    # assert "Échec déchiffrement" in result.stdout # aa_utils loggue en WARNING ou ERROR

def test_embed_script_source_fetch_error(
    tmp_path, create_encrypted_config_file, test_passphrase, mock_aa_utils_network_calls
):
    mock_get_text, _ = mock_aa_utils_network_calls
    source_error_data = [{
        "source_name": "Source Error", "source_type": "direct_download",
        "schema": "http", "host_parts": ["error"], "path": "/error.txt", "extracts": []
    }]
    input_file = create_encrypted_config_file("input_fetch_error.enc", source_error_data)
    output_file = tmp_path / "output_fetch_error.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script(args)

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0 # Le script doit finir, mais avec des erreurs logguées
    
    # Vérifier que get_full_text_for_source a été appelé et a levé une exception (simulée par le mock)
    mock_get_text.assert_called_once()
    assert "Erreur lors de la récupération du texte pour la source Source Error: Simulated network error" in result.stdout
    assert "Traitement des sources terminé. 0 sources mises à jour, 1 erreurs de récupération." in result.stdout

    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert len(output_data) == 1
    assert "full_text" not in output_data[0] # Le texte n'a pas pu être récupéré


def test_embed_script_empty_input_config(
    tmp_path, create_encrypted_config_file, test_passphrase
):
    # Créer un fichier de config vide (ou avec une liste vide de sources)
    input_file = create_encrypted_config_file("input_empty.enc", [])
    output_file = tmp_path / "output_empty.enc"

    args = ["--input-config", str(input_file), "--output-config", str(output_file), "--passphrase", test_passphrase]
    result = run_script(args)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0
    assert "Aucune définition d'extrait trouvée ou erreur lors du chargement" in result.stdout # ou "0 définitions d'extraits chargées."
    assert "Aucune définition d'extrait à sauvegarder ou aucune mise à jour effectuée." in result.stdout
    assert output_file.exists() # Le fichier de sortie est créé même s'il est vide

    output_data = decrypt_and_load_json(output_file, test_passphrase)
    assert output_data == []