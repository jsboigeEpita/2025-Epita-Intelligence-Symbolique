# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires réseau de project_core.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import requests # Pour les exceptions

from argumentation_analysis.utils.core_utils.network_utils import download_file

@pytest.fixture
def mock_requests_get():
    """Fixture pour mocker requests.get."""
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def mock_path_operations():
    """Fixture pour mocker les opérations sur Path (mkdir, stat, open, exists, remove)."""
    with patch.object(Path, 'mkdir') as mock_mkdir, \
         patch.object(Path, 'stat') as mock_stat, \
         patch('builtins.open', new_callable=mock_open) as mock_file_open, \
         patch.object(Path, 'exists') as mock_exists, \
         patch('os.remove') as mock_os_remove:
        
        # Configurer le mock pour stat() afin qu'il retourne un objet avec un attribut st_size
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 0 # Taille par défaut, peut être surchargée dans les tests
        mock_stat.return_value = mock_stat_result
        
        yield {
            "mkdir": mock_mkdir,
            "stat": mock_stat,
            "open": mock_file_open,
            "exists": mock_exists,
            "remove": mock_os_remove
        }

def test_download_file_success(mock_requests_get, mock_path_operations, tmp_path):
    """Teste le téléchargement réussi d'un fichier."""
    url = "http://example.com/file.txt"
    dest_path = tmp_path / "downloaded_file.txt"
    file_content = b"Ceci est le contenu du fichier."
    expected_file_size = len(file_content)

    # Configurer le mock de requests.get
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None # Pas d'erreur HTTP
    mock_response.iter_content.return_value = [file_content] # Simule les chunks
    mock_requests_get.return_value.__enter__.return_value = mock_response # Pour le context manager

    # Configurer le mock de stat pour retourner la bonne taille
    mock_path_operations["stat"].return_value.st_size = expected_file_size
    mock_path_operations["exists"].return_value = True # Simuler que le fichier existe après écriture

    result = download_file(url, dest_path, expected_size=expected_file_size)

    assert result is True, "Le téléchargement aurait dû réussir."
    mock_requests_get.assert_called_once_with(url, stream=True, timeout=30)
    mock_path_operations["mkdir"].assert_any_call(parents=True, exist_ok=True)
    mock_path_operations["open"].assert_called_once_with(dest_path, 'wb')
    # Vérifier que write a été appelé sur le handle de fichier mocké
    handle = mock_path_operations["open"]()
    handle.write.assert_called_once_with(file_content)
    mock_path_operations["stat"].assert_any_call() # stat() est appelé sur dest_path

def test_download_file_http_error(mock_requests_get, mock_path_operations, tmp_path, caplog):
    """Teste la gestion d'une erreur HTTP (ex: 404)."""
    url = "http://example.com/notfound.txt"
    dest_path = tmp_path / "failed_download.txt"

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
    mock_requests_get.return_value.__enter__.return_value = mock_response
    
    # Simuler que le fichier partiel pourrait exister avant suppression
    mock_path_operations["exists"].return_value = True 

    result = download_file(url, dest_path)

    assert result is False, "Le téléchargement aurait dû échouer."
    assert "Erreur de téléchargement (RequestException)" in caplog.text
    mock_path_operations["exists"].assert_called_once_with() # Vérifie si le fichier partiel existe
    mock_path_operations["remove"].assert_called_once_with(dest_path) # Tentative de suppression

def test_download_file_size_mismatch(mock_requests_get, mock_path_operations, tmp_path, caplog):
    """Teste l'échec du téléchargement si la taille du fichier ne correspond pas."""
    url = "http://example.com/file_wrong_size.txt"
    dest_path = tmp_path / "file_wrong_size.txt"
    file_content = b"Contenu."
    actual_size = len(file_content)
    expected_size = actual_size + 10 # Taille attendue incorrecte

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.return_value = [file_content]
    mock_requests_get.return_value.__enter__.return_value = mock_response

    mock_path_operations["stat"].return_value.st_size = actual_size
    mock_path_operations["exists"].return_value = True # Le fichier existe après écriture

    result = download_file(url, dest_path, expected_size=expected_size)

    assert result is False, "Le téléchargement aurait dû échouer en raison d'une taille incorrecte."
    assert "Erreur de taille : la taille du fichier téléchargé" in caplog.text
    # La suppression du fichier en cas de taille incorrecte est commentée dans le code source,
    # donc on ne vérifie pas mock_path_operations["remove"] ici, sauf si cette logique est réactivée.

def test_download_file_os_error_on_write(mock_requests_get, mock_path_operations, tmp_path, caplog):
    """Teste la gestion d'une OSError lors de l'écriture du fichier."""
    url = "http://example.com/file_os_error.txt"
    dest_path = tmp_path / "file_os_error.txt"
    file_content = b"Contenu."

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.return_value = [file_content]
    mock_requests_get.return_value.__enter__.return_value = mock_response

    # Simuler une OSError lors de l'appel à open() ou write()
    mock_path_operations["open"].side_effect = OSError("Simulated Disk Full")

    result = download_file(url, dest_path)

    assert result is False, "Le téléchargement aurait dû échouer en raison d'une OSError."
    assert "Erreur d'écriture ou de suppression du fichier" in caplog.text
    assert "Simulated Disk Full" in caplog.text
    # Vérifier si une tentative de suppression du fichier partiel a eu lieu (si applicable)
    # Dans ce cas, l'erreur se produit avant/pendant l'écriture, donc le fichier n'existe peut-être pas.
    # La logique de suppression dans le bloc `except OSError` n'est pas présente dans le code fourni.

def test_download_file_no_expected_size(mock_requests_get, mock_path_operations, tmp_path):
    """Teste le téléchargement réussi sans vérification de taille."""
    url = "http://example.com/file_no_size_check.txt"
    dest_path = tmp_path / "file_no_size_check.txt"
    file_content = b"Quelque contenu."
    actual_size = len(file_content)

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.return_value = [file_content]
    mock_requests_get.return_value.__enter__.return_value = mock_response

    mock_path_operations["stat"].return_value.st_size = actual_size
    mock_path_operations["exists"].return_value = True

    result = download_file(url, dest_path, expected_size=None) # Pas de taille attendue

    assert result is True, "Le téléchargement aurait dû réussir."
    # Aucune erreur de taille ne devrait être logguée.

def test_download_file_cleans_up_partial_on_request_exception(mock_requests_get, mock_path_operations, tmp_path, caplog):
    """Teste que le fichier partiel est supprimé en cas de RequestException."""
    url = "http://example.com/network_error"
    dest_path = tmp_path / "partial_on_error.dat"

    mock_requests_get.side_effect = requests.exceptions.ConnectionError("Simulated network error")
    
    # Simuler que le fichier existe lorsque la vérification de suppression est faite
    mock_path_operations["exists"].return_value = True 

    result = download_file(url, dest_path)

    assert result is False
    assert "Erreur de téléchargement (RequestException)" in caplog.text
    mock_path_operations["exists"].assert_called_once() # Vérifie si le fichier partiel existe
    mock_path_operations["remove"].assert_called_once_with(dest_path) # Tentative de suppression

def test_download_file_cleans_up_partial_on_unexpected_exception(mock_requests_get, mock_path_operations, tmp_path, caplog):
    """Teste que le fichier partiel est supprimé en cas d'exception inattendue."""
    url = "http://example.com/unexpected_problem"
    dest_path = tmp_path / "partial_on_unexpected.dat"

    # Simuler une exception inattendue pendant le traitement des chunks, par exemple
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.side_effect = Exception("Unexpected error during iteration")
    mock_requests_get.return_value.__enter__.return_value = mock_response
    
    mock_path_operations["exists"].return_value = True

    result = download_file(url, dest_path)

    assert result is False
    assert "Une erreur inattendue est survenue" in caplog.text
    mock_path_operations["exists"].assert_called_once()
    mock_path_operations["remove"].assert_called_once_with(dest_path)

def test_download_file_handles_os_error_on_remove_after_exception(mock_requests_get, mock_path_operations, tmp_path, caplog):
    """
    Teste la gestion d'une OSError lors de la tentative de suppression d'un fichier partiel
    après une autre exception (ex: RequestException).
    """
    url = "http://example.com/fail_then_fail_remove"
    dest_path = tmp_path / "fail_remove.dat"

    mock_requests_get.side_effect = requests.exceptions.Timeout("Simulated timeout")
    mock_path_operations["exists"].return_value = True
    mock_path_operations["remove"].side_effect = OSError("Simulated permission error on remove")

    result = download_file(url, dest_path)
    assert result is False
    assert "Erreur de téléchargement (RequestException)" in caplog.text # Log de l'erreur initiale
    assert "Impossible de supprimer le fichier partiel" in caplog.text # Log de l'erreur de suppression
    assert "Simulated permission error on remove" in caplog.text