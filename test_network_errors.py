#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour évaluer les messages d'erreur réseau.
"""

import sys
import os
import requests
from unittest.mock import patch, MagicMock

# Ajouter le répertoire du projet au PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

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
            print(f"Tentative de récupération de {url}...")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
            print(f"Récupération réussie: {response.status_code}")
            return response.text, None
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Erreur de connexion: {e}"
            print(error_msg)
            
            if "Failed to resolve" in str(e):
                return None, f"Erreur DNS: Impossible de résoudre le nom d'hôte '{url}'"
            elif "Connection refused" in str(e):
                return None, f"Erreur de connexion: Connexion refusée à '{url}'"
            else:
                return None, f"Erreur de connexion lors de la récupération de '{url}': {e}"
        
        except requests.exceptions.Timeout as e:
            error_msg = f"Erreur de timeout: {e}"
            print(error_msg)
            
            if retry_count < self.max_retries:
                print(f"Nouvelle tentative ({retry_count + 1}/{self.max_retries})...")
                return self.fetch_url(url, retry_count + 1)
            else:
                return None, f"Timeout après {self.max_retries} tentatives pour '{url}'"
        
        except requests.exceptions.TooManyRedirects as e:
            error_msg = f"Erreur de redirection: {e}"
            print(error_msg)
            return None, f"Trop de redirections pour '{url}'"
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_msg = f"Erreur HTTP {status_code}: {e}"
            print(error_msg)
            
            if status_code == 404:
                return None, f"Erreur 404: Page non trouvée pour '{url}'"
            elif status_code == 403:
                return None, f"Erreur 403: Accès interdit pour '{url}'"
            elif status_code == 500:
                return None, f"Erreur 500: Erreur serveur interne pour '{url}'"
            else:
                return None, f"Erreur HTTP {status_code} pour '{url}': {e}"
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Erreur de requête: {e}"
            print(error_msg)
            return None, f"Erreur lors de la récupération de '{url}': {e}"
        
        except Exception as e:
            error_msg = f"Erreur inattendue: {e}"
            print(error_msg)
            return None, f"Erreur inattendue lors de la récupération de '{url}': {e}"

def test_connection_timeout():
    print("\n=== Test d'erreur de timeout ===")
    service = FetchService()
    
    # Simuler un timeout
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out after 30 seconds")
        content, error = service.fetch_url("https://example.com/timeout")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_dns_resolution_failure():
    print("\n=== Test d'erreur de résolution DNS ===")
    service = FetchService()
    
    # Simuler une erreur de résolution DNS
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to resolve 'nonexistent-domain-12345.com'")
        content, error = service.fetch_url("https://nonexistent-domain-12345.com")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_ssl_certificate_error():
    print("\n=== Test d'erreur de certificat SSL ===")
    service = FetchService()
    
    # Simuler une erreur de certificat SSL
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.SSLError("SSL: CERTIFICATE_VERIFY_FAILED")
        content, error = service.fetch_url("https://expired.badssl.com/")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_http_404_error():
    print("\n=== Test d'erreur HTTP 404 ===")
    service = FetchService()
    
    # Simuler une erreur HTTP 404
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("404 Client Error: Not Found")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = service.fetch_url("https://example.com/nonexistent")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_http_403_error():
    print("\n=== Test d'erreur HTTP 403 ===")
    service = FetchService()
    
    # Simuler une erreur HTTP 403
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 403
        http_error = requests.exceptions.HTTPError("403 Client Error: Forbidden")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = service.fetch_url("https://example.com/forbidden")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_http_500_error():
    print("\n=== Test d'erreur HTTP 500 ===")
    service = FetchService()
    
    # Simuler une erreur HTTP 500
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError("500 Server Error: Internal Server Error")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        content, error = service.fetch_url("https://example.com/server-error")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_connection_refused():
    print("\n=== Test d'erreur de connexion refusée ===")
    service = FetchService()
    
    # Simuler une erreur de connexion refusée
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        content, error = service.fetch_url("https://example.com/refused")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

def test_too_many_redirects():
    print("\n=== Test d'erreur de trop de redirections ===")
    service = FetchService()
    
    # Simuler une erreur de trop de redirections
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.TooManyRedirects("Too many redirects")
        content, error = service.fetch_url("https://example.com/redirect-loop")
        print(f"Contenu: {content}")
        print(f"Erreur: {error}")

if __name__ == "__main__":
    print("=== Tests des messages d'erreur réseau ===")
    test_connection_timeout()
    test_dns_resolution_failure()
    test_ssl_certificate_error()
    test_http_404_error()
    test_http_403_error()
    test_http_500_error()
    test_connection_refused()
    test_too_many_redirects()