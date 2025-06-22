import pytest
import httpx
import os

# Ce test d'intégration vérifie que le wrapper WsgiToAsgi fonctionne correctement
# en ciblant un endpoint Flask simple (/api/health) après son exposition via ASGI.

#pytest.mark.usefixtures("test_client")
@pytest.mark.integration
def test_wsgi_health_check_via_asgi(backend_url):
    """
    Action: Interroge l'endpoint de santé (/api/health) de l'application Flask
            via le serveur ASGI (Uvicorn).
    Attendu:
        - Reçoit une réponse HTTP 200 OK.
        - Le corps de la réponse est un JSON valide.
        - Le JSON contient une clé "status" avec la valeur "healthy".
    """
    assert backend_url, "La fixture backend_url doit être définie et non vide."

    health_endpoint = f"{backend_url}/api/health"
    
    try:
        with httpx.Client() as client:
            response = client.get(health_endpoint, timeout=10)
        
        # Vérification 1: La requête a réussi
        assert response.status_code == 200, \
            f"La requête à {health_endpoint} a échoué avec le code {response.status_code}. Contenu: {response.text}"
            
        # Vérification 2: Le contenu est bien du JSON
        try:
            response_json = response.json()
        except Exception:
            pytest.fail(f"La réponse de {health_endpoint} n'est pas un JSON valide. Contenu: {response.text}")
            
        # Vérification 3: Le contenu JSON est conforme à ce qui est attendu
        assert "status" in response_json, "La clé 'status' est absente de la réponse JSON."
        assert response_json["status"] == "healthy", \
            f"Le statut attendu était 'healthy', mais nous avons reçu '{response_json.get('status')}'. Réponse complète: {response_json}"

    except httpx.RequestError as e:
        pytest.fail(f"Une erreur de requête est survenue lors de la connexion à {health_endpoint}: {e}")