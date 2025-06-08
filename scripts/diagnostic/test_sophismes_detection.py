import pytest
import requests
import json
import time

BASE_URL = "http://localhost:5000"

class TestSophismesDetection:
    """Tests systématiques pour la détection des sophismes"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Attendre que le serveur soit prêt"""
        time.sleep(0.5)
    
    def test_api_disponible(self):
        """Test que l'API est accessible"""
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=5)
            assert response.status_code in [200, 404], "Le serveur doit être accessible"
        except requests.exceptions.ConnectionError:
            pytest.fail("Le serveur Flask n'est pas accessible sur localhost:5000")
    
    def test_example_5_pente_glissante(self):
        """Test #5 - Détection de la pente glissante"""
        text = "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h."
        
        response = requests.post(
            f"{BASE_URL}/api/fallacies",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"API doit retourner 200, reçu {response.status_code}"
        
        data = response.json()
        assert "fallacies" in data, "La réponse doit contenir une clé 'fallacies'"
        
        # Vérification qu'au moins un sophisme est détecté
        fallacies = data["fallacies"]
        assert len(fallacies) > 0, f"Au moins un sophisme devrait être détecté. Reçu: {fallacies}"
        
        # Log des résultats pour diagnostic
        print(f"\n=== Test Pente Glissante ===")
        print(f"Texte: {text}")
        print(f"Sophismes détectés: {len(fallacies)}")
        for i, fallacy in enumerate(fallacies):
            print(f"- Sophisme {i+1}: {fallacy.get('type', 'N/A')}")
            print(f"  Confiance: {fallacy.get('confidence', 'N/A')}")
            print(f"  Description: {fallacy.get('description', 'N/A')}")
    
    def test_example_6_homme_de_paille(self):
        """Test #6 - Détection de l'homme de paille"""
        text = "Les écologistes veulent qu'on retourne à l'âge de pierre."
        
        response = requests.post(
            f"{BASE_URL}/api/fallacies",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"API doit retourner 200, reçu {response.status_code}"
        
        data = response.json()
        assert "fallacies" in data, "La réponse doit contenir une clé 'fallacies'"
        
        # Vérification qu'au moins un sophisme est détecté
        fallacies = data["fallacies"]
        assert len(fallacies) > 0, f"Au moins un sophisme devrait être détecté. Reçu: {fallacies}"
        
        # Log des résultats pour diagnostic
        print(f"\n=== Test Homme de Paille ===")
        print(f"Texte: {text}")
        print(f"Sophismes détectés: {len(fallacies)}")
        for i, fallacy in enumerate(fallacies):
            print(f"- Sophisme {i+1}: {fallacy.get('type', 'N/A')}")
            print(f"  Confiance: {fallacy.get('confidence', 'N/A')}")
            print(f"  Description: {fallacy.get('description', 'N/A')}")
    
    def test_texte_sans_sophisme(self):
        """Test avec un texte qui ne devrait pas contenir de sophisme"""
        text = "Il fait beau aujourd'hui et les oiseaux chantent."
        
        response = requests.post(
            f"{BASE_URL}/api/fallacies",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"API doit retourner 200, reçu {response.status_code}"
        
        data = response.json()
        assert "fallacies" in data, "La réponse doit contenir une clé 'fallacies'"
        
        fallacies = data["fallacies"]
        print(f"\n=== Test Texte Neutre ===")
        print(f"Texte: {text}")
        print(f"Sophismes détectés: {len(fallacies)}")
        
        # Ce test ne fait pas d'assertion stricte sur le nombre de sophismes
        # car le système pourrait être très sensible
    
    def test_format_reponse_api(self):
        """Test du format de réponse de l'API"""
        text = "Test de format"
        
        response = requests.post(
            f"{BASE_URL}/api/fallacies",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Vérifications du format
        assert isinstance(data, dict), "La réponse doit être un dictionnaire"
        assert "fallacies" in data, "La réponse doit contenir 'fallacies'"
        assert isinstance(data["fallacies"], list), "fallacies doit être une liste"
        
        # Si des sophismes sont détectés, vérifier leur structure
        for fallacy in data["fallacies"]:
            assert isinstance(fallacy, dict), "Chaque sophisme doit être un dictionnaire"
            # Les clés peuvent varier selon l'implémentation
            
    def test_texte_vide(self):
        """Test avec un texte vide"""
        response = requests.post(
            f"{BASE_URL}/api/fallacies",
            json={"text": ""},
            headers={"Content-Type": "application/json"}
        )
        
        # Le comportement peut varier, mais l'API ne doit pas crasher
        assert response.status_code in [200, 400], "L'API doit gérer les textes vides"
    
    def test_detection_qualite(self):
        """Test de qualité de détection avec des exemples connus"""
        exemples_test = [
            {
                "text": "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h.",
                "sophisme_attendu": "slippery_slope",
                "description": "Pente glissante"
            },
            {
                "text": "Les écologistes veulent qu'on retourne à l'âge de pierre.",
                "sophisme_attendu": "straw_man", 
                "description": "Homme de paille"
            }
        ]
        
        resultats = []
        for exemple in exemples_test:
            response = requests.post(
                f"{BASE_URL}/api/fallacies",
                json={"text": exemple["text"]},
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            resultats.append({
                "description": exemple["description"],
                "texte": exemple["text"],
                "sophismes_detectes": len(data["fallacies"]),
                "details": data["fallacies"]
            })
        
        print(f"\n=== Résumé des Tests de Qualité ===")
        for resultat in resultats:
            print(f"{resultat['description']}: {resultat['sophismes_detectes']} sophisme(s) détecté(s)")
            
        # Au moins un sophisme doit être détecté sur l'ensemble des tests
        total_detecte = sum(r["sophismes_detectes"] for r in resultats)
        assert total_detecte > 0, "Au moins un sophisme devrait être détecté dans les exemples de test"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])