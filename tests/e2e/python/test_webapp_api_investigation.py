#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'investigation de la démo web - API et Interface
====================================================

Script d'investigation systématique de la démo web du projet d'Intelligence Symbolique.
"""

import os
import pytest
import requests
import json
import time
from pathlib import Path


class TestWebAppAPIInvestigation:
    """Tests d'investigation de l'API d'analyse argumentative"""
    
    BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:5003")
    
    def test_api_health(self):
        """Test de santé de l'API"""
        response = requests.get(f"{self.BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        
        health_data = response.json()
        print(f"\n[HEALTH] État de santé de l'API:")
        print(f"   Status: {health_data.get('status')}")
        print(f"   Message: {health_data.get('message')}")
        print(f"   Version: {health_data.get('version')}")
        print(f"   Timestamp: {health_data.get('timestamp')}")
        
        services = health_data.get('services', {})
        print(f"   Services disponibles:")
        for service, status in services.items():
            icon = "[OK]" if status else "[ERROR]"
            print(f"     {icon} {service}: {'OK' if status else 'Indisponible'}")
    
    def test_api_analyze_endpoint(self):
        """Test de l'endpoint d'analyse argumentative"""
        test_text = "Dieu existe parce que la Bible le dit, et la Bible est vraie parce qu'elle est la parole de Dieu."
        
        payload = {
            "text": test_text,
            "analyze_fallacies": True,
            "analyze_structure": True,
            "evaluate_coherence": True
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/api/analyze", json=payload, timeout=30)
            print(f"\n[ANALYZE] Test de l'endpoint /api/analyze:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Texte analysé: {test_text[:50]}...")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   [OK] Analyse réussie")
                print(f"   Résultat: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")
            else:
                print(f"   [ERROR] Erreur: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")
            pytest.skip(f"API non accessible: {e}")
    
    def test_api_fallacies_endpoint(self):
        """Test de l'endpoint de détection de sophismes"""
        test_text = "Si nous autorisons le mariage gay, bientôt nous autoriserons aussi le mariage avec les animaux."
        
        payload = {
            "text": test_text,
            "options": {
                "severity_threshold": 0.3,
                "include_explanations": True,
                "fallacy_types": "all"
            }
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/api/fallacies", json=payload, timeout=30)
            print(f"\n[WARNING]  Test de l'endpoint /api/fallacies:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Texte analysé: {test_text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   [OK] Détection réussie")
                fallacies = result.get('fallacies', [])
                print(f"   Sophismes détectés: {len(fallacies)}")
                for fallacy in fallacies[:2]:  # Afficher les 2 premiers
                    print(f"     - {fallacy.get('type', 'Unknown')}: {fallacy.get('confidence', 0):.2f}")
            else:
                print(f"   [ERROR] Erreur: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")
    
    def test_api_validate_endpoint(self):
        """Test de l'endpoint de validation d'arguments"""
        payload = {
            "premises": [
                "Tous les hommes sont mortels",
                "Socrate est un homme"
            ],
            "conclusion": "Socrate est mortel",
            "argument_type": "deductive"
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/api/validate", json=payload, timeout=30)
            print(f"\n[OK] Test de l'endpoint /api/validate:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Argument testé: {payload['premises']} -> {payload['conclusion']}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   [OK] Validation réussie")
                print(f"   Valide: {result.get('valid', False)}")
                print(f"   Confiance: {result.get('confidence', 0):.2f}")
            else:
                print(f"   [ERROR] Erreur: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")
    
    def test_api_framework_endpoint(self):
        """Test de l'endpoint de framework de Dung"""
        payload = {
            "arguments": [
                {"id": "A1", "content": "Il faut protéger l'environnement"},
                {"id": "A2", "content": "L'économie est plus importante"},
                {"id": "A3", "content": "On peut faire les deux"}
            ],
            "attacks": [
                {"attacker": "A2", "target": "A1"},
                {"attacker": "A3", "target": "A2"}
            ]
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/api/framework", json=payload, timeout=30)
            print(f"\n[FRAMEWORK]  Test de l'endpoint /api/framework:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Arguments: {len(payload['arguments'])}")
            print(f"   Attaques: {len(payload['attacks'])}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   [OK] Framework construit")
                extensions = result.get('extensions', {})
                if isinstance(extensions, dict):
                    print(f"   Extensions calculées: {list(extensions.keys())}")
                else:
                    print(f"   Extensions calculées: {extensions}")
            else:
                print(f"   [ERROR] Erreur: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")

    def test_generate_api_investigation_report(self):
        """Génère un rapport d'investigation de l'API"""
        report_path = Path("tests/functional/logs/api_investigation_report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        endpoints = [
            "/api/health",
            "/api/analyze", 
            "/api/fallacies",
            "/api/validate",
            "/api/framework"
        ]
        
        report_content = """# [REPORT] Rapport d'Investigation - API Web d'Analyse Argumentative

**Date:** {timestamp}
**Base URL:** {base_url}

## [ANALYZE] État des Endpoints

""".format(
            timestamp=time.strftime("%d/%m/%Y %H:%M:%S"),
            base_url=self.BASE_URL
        )
        
        for endpoint in endpoints:
            try:
                if endpoint == "/api/health":
                    response = requests.get(f"{self.BASE_URL}{endpoint}", timeout=5)
                else:
                    # Test avec données minimales
                    test_data = {"text": "Test argument"} if "text" in endpoint else {}
                    response = requests.post(f"{self.BASE_URL}{endpoint}", json=test_data, timeout=5)
                
                status = "[OK] Opérationnel" if response.status_code in [200, 400] else "[ERROR] Erreur"
                report_content += f"### {endpoint}\n- **Status:** {status} ({response.status_code})\n"
                
                if response.status_code == 200 and endpoint == "/api/health":
                    health_data = response.json()
                    services = health_data.get('services', {})
                    report_content += f"- **Services:** {list(services.keys())}\n"
                
                report_content += "\n"
                
            except Exception as e:
                report_content += f"### {endpoint}\n- **Status:** [ERROR] Inaccessible ({e})\n\n"
        
        report_content += """
## 📋 Résumé des Fonctionnalités

1. **Analyse Argumentative** (`/api/analyze`)
   - Analyse complète de textes argumentatifs
   - Détection de structure, cohérence et sophismes

2. **Détection de Sophismes** (`/api/fallacies`)
   - Détection spécialisée de fallacies logiques
   - Configuration de seuils de confiance

3. **Validation d'Arguments** (`/api/validate`)
   - Validation formelle de syllogismes
   - Support arguments déductifs et inductifs

4. **Framework de Dung** (`/api/framework`)
   - Construction de frameworks argumentatifs
   - Calcul d'extensions (admissible, préféré, etc.)

## [NEXT] Prochaines Étapes

- [ ] Test de l'interface React frontend
- [ ] Tests d'intégration avec Playwright
- [ ] Validation des workflows complets
- [ ] Tests de performance et robustesse
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n[FILE] Rapport généré: {report_path}")


if __name__ == "__main__":
    # Exécution directe pour investigation
    tester = TestWebAppAPIInvestigation()
    
    print("[INVESTIGATION] DEMO WEB - API")
    print("=" * 50)
    
    try:
        tester.test_api_health()
        tester.test_api_analyze_endpoint()
        tester.test_api_fallacies_endpoint()
        tester.test_api_validate_endpoint()
        tester.test_api_framework_endpoint()
        tester.test_generate_api_investigation_report()
        
        print("\n[OK] Investigation API terminée avec succès")
        
    except Exception as e:
        print(f"\n[ERROR] Erreur durant l'investigation: {e}")
        raise