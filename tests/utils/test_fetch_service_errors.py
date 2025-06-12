
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests pour la gestion des erreurs réseau du FetchService avec pytest.
"""

import pytest
import requests
from unittest.mock import patch, MagicMock


# Définir une classe de service de récupération simplifiée pour les tests
class FetchService:
    def __init__(self):
        self.timeout = 30
        self.max_retries = 3
        self.user_agent = "ArgumentAnalysisApp/1.0"
    
    def fetch_url(self, url, retry_count=0):
        """Récupère le contenu d'une URL avec gestion des erreurs."""
        headers = {"User-Agent": self.user_agent}
        
        try:
            # print(f"Tentative de récupération de {url}...") # Commenté pour les tests pytest
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
            # print(f"Récupération réussie: {response.status_code}") # Commenté pour les tests pytest
            return response.text, None
        except requests.exceptions.ConnectionError as e:
            # error_msg = f"Erreur de connexion: {e}" # Commenté pour les tests pytest
            # print(error_msg) # Commenté pour les tests pytest
            
            if "Failed to resolve" in str(e):
                return None, f"Erreur DNS: Impossible de résoudre le nom d'hôte '{url}'"
            elif "Connection refused" in str(e):
                return None, f"Erreur de connexion: Connexion refusée à '{url}'"
            else:
                return None, f"Erreur de connexion lors de la récupération de '{url}': {e}"
        
        except requests.exceptions.Timeout as e:
            # error_msg = f"Erreur de timeout: {e}" # Commenté pour les tests pytest
            # print(error_msg) # Commenté pour les tests pytest
            
            if retry_count < self.max_retries:
                # print(f"Nouvelle tentative ({retry_count + 1}/{self.max_retries})...") # Commenté
                return self.fetch_url(url, retry_count + 1)
            else:
                return None, f"Timeout après {self.max_retries} tentatives pour '{url}'"
        
        except requests.exceptions.TooManyRedirects as e:
            # error_msg = f"Erreur de redirection: {e}" # Commenté pour les tests pytest
            # print(error_msg) # Commenté pour les tests pytest
            return None, f"Trop de redirections pour '{url}'"
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            # error_msg = f"Erreur HTTP {status_code}: {e}" # Commenté pour les tests pytest
            # print(error_msg) # Commenté pour les tests pytest
            
            if status_code == 404:
                return None, f"Erreur 404: Page non trouvée pour '{url}'"
            elif status_code == 403:
                return None, f"Erreur 403: Accès interdit pour '{url}'"
            elif status_code == 500:
                return None, f"Erreur 500: Erreur serveur interne pour '{url}'"
            else:
                return None, f"Erreur HTTP {status_code} pour '{url}': {e}"
        
        except requests.exceptions.RequestException as e: # SSLError est un sous-type de RequestException
            # error_msg = f"Erreur de requête: {e}" # Commenté pour les tests pytest
            # print(error_msg) # Commenté pour les tests pytest
            if isinstance(e, requests.exceptions.SSLError):
                 return None, f"Erreur SSL lors de la récupération de '{url}': {e}"
            return None, f"Erreur lors de la récupération de '{url}': {e}"
        
        except Exception as e:
            # error_msg = f"Erreur inattendue: {e}" # Commenté pour les tests pytest
            # print(error_msg) # Commenté pour les tests pytest
            return None, f"Erreur inattendue lors de la récupération de '{url}': {e}"

@pytest.fixture
def fetch_service():
    """Fixture pour fournir une instance de FetchService."""
    return FetchService()

def test_connection_timeout(fetch_service):
    url = "https://example.com/timeout"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out after 30 seconds")
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Timeout après {fetch_service.max_retries} tentatives pour '{url}'"

def test_dns_resolution_failure(fetch_service):
    url = "https://nonexistent-domain-12345.com"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to resolve 'nonexistent-domain-12345.com'")
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur DNS: Impossible de résoudre le nom d'hôte '{url}'"

def test_ssl_certificate_error(fetch_service):
    url = "https://expired.badssl.com/"
    # Note: La logique actuelle de FetchService intercepte SSLError via RequestException.
    # Si nous voulions un message plus spécifique pour SSLError directement depuis FetchService,
    # il faudrait ajouter un bloc `except requests.exceptions.SSLError as e:` avant `RequestException`.
    # Pour l'instant, nous testons le comportement existant.
    expected_error_message_fragment = "Erreur de connexion lors de la récupération de"
    with patch('requests.get') as mock_get:
        ssl_error_instance = requests.exceptions.SSLError("SSL: CERTIFICATE_VERIFY_FAILED")
        mock_get.side_effect = ssl_error_instance
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error is not None
        assert expected_error_message_fragment in error
        assert url in error
        assert "SSL: CERTIFICATE_VERIFY_FAILED" in error


def test_http_404_error(fetch_service):
    url = "https://example.com/nonexistent"
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("404 Client Error: Not Found")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur 404: Page non trouvée pour '{url}'"

def test_http_403_error(fetch_service):
    url = "https://example.com/forbidden"
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 403
        http_error = requests.exceptions.HTTPError("403 Client Error: Forbidden")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur 403: Accès interdit pour '{url}'"

def test_http_500_error(fetch_service):
    url = "https://example.com/server-error"
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError("500 Server Error: Internal Server Error")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur 500: Erreur serveur interne pour '{url}'"

def test_connection_refused(fetch_service):
    url = "https://example.com/refused"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur de connexion: Connexion refusée à '{url}'"

def test_too_many_redirects(fetch_service):
    url = "https://example.com/redirect-loop"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.TooManyRedirects("Too many redirects")
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Trop de redirections pour '{url}'"

def test_successful_fetch(fetch_service):
    url = "https://example.com/success"
    expected_text = "<html><body><h1>Success</h1></body></html>"
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = expected_text
        # Simuler l'absence d'erreur HTTP en s'assurant que raise_for_status ne fait rien
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        content, error = fetch_service.fetch_url(url)
        assert error is None
        assert content == expected_text
        mock_get.assert_called_once_with(url, headers={"User-Agent": fetch_service.user_agent}, timeout=fetch_service.timeout)
        mock_response.raise_for_status.assert_called_once()

def test_unknown_connection_error(fetch_service):
    url = "https://example.com/unknown-connection-error"
    original_error_message = "Some other connection problem"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError(original_error_message)
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur de connexion lors de la récupération de '{url}': {original_error_message}"

def test_unknown_http_error(fetch_service):
    url = "https://example.com/unknown-http-error"
    original_error_message = "418 I'm a teapot"
    status_code = 418
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        http_error = requests.exceptions.HTTPError(original_error_message)
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur HTTP {status_code} pour '{url}': {http_error}"

def test_unexpected_generic_exception(fetch_service):
    url = "https://example.com/unexpected-generic"
    original_error_message = "A very generic error occurred"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception(original_error_message)
        content, error = fetch_service.fetch_url(url)
        assert content is None
        assert error == f"Erreur inattendue lors de la récupération de '{url}': {original_error_message}"