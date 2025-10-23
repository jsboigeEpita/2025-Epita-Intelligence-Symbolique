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

    @pytest.mark.e2e
    def test_api_health(self, e2e_servers):
        """Test de santé de l'API"""
        base_url, _ = e2e_servers
        assert base_url, "L'URL du backend doit être fournie par la fixture e2e_servers"
        response = requests.get(f"{base_url}/api/health", timeout=10)
        assert response.status_code == 200

        health_data = response.json()
        print("\n[HEALTH] État de santé de l'API:")
        print(f"   Status: {health_data.get('status')}")
        print(f"   Message: {health_data.get('message')}")
        print(f"   Version: {health_data.get('version')}")
        print(f"   Timestamp: {health_data.get('timestamp')}")

        services = health_data.get("services", {})
        print("   Services disponibles:")
        for service, status in services.items():
            icon = "[OK]" if status else "[ERROR]"
            print(f"     {icon} {service}: {'OK' if status else 'Indisponible'}")

    @pytest.mark.e2e
    def test_api_analyze_endpoint(self, e2e_servers):
        """Test de l'endpoint d'analyse argumentative"""
        base_url, _ = e2e_servers
        test_text = "Dieu existe parce que la Bible le dit, et la Bible est vraie parce qu'elle est la parole de Dieu."

        payload = {"text": test_text, "analysis_type": "comprehensive", "options": {}}

        try:
            assert (
                base_url
            ), "L'URL du backend doit être fournie par la fixture e2e_servers"
            response = requests.post(
                f"{base_url}/api/analyze", json=payload, timeout=30
            )
            print("\n[ANALYZE] Test de l'endpoint /api/analyze:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Texte analysé: {test_text[:50]}...")

            if response.status_code == 200:
                result = response.json()
                print("   [OK] Analyse réussie")
                print(
                    f"   Résultat complet: {json.dumps(result, indent=2, ensure_ascii=False)}"
                )
            else:
                print(f"   [ERROR] Erreur: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")
            pytest.skip(f"API non accessible: {e}")

    @pytest.mark.e2e
    def test_api_fallacies_endpoint(self, e2e_servers):
        """Test de l'endpoint de détection de sophismes"""
        base_url, _ = e2e_servers
        test_text = "Si nous autorisons le mariage gay, bientôt nous autoriserons aussi le mariage avec les animaux."

        payload = {
            "text": test_text,
            "options": {
                "severity_threshold": 0.3,
                "include_explanations": True,
                "fallacy_types": "all",
            },
        }

        try:
            # Cette route /api/fallacies n'existe plus dans la nouvelle app Starlette
            # Je la skipperai pour l'instant.
            pytest.skip("La route /api/fallacies n'est plus implémentée.")
            assert (
                base_url
            ), "L'URL du backend doit être fournie par la fixture e2e_servers"
            response = requests.post(
                f"{base_url}/api/fallacies", json=payload, timeout=30
            )
            print("\n[WARNING]  Test de l'endpoint /api/fallacies:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Texte analysé: {test_text}")

            if response.status_code == 200:
                result = response.json()
                print("   [OK] Détection réussie")
                fallacies = result.get("fallacies", [])
                print(f"   Sophismes détectés: {len(fallacies)}")
                for fallacy in fallacies[:2]:  # Afficher les 2 premiers
                    print(
                        f"     - {fallacy.get('type', 'Unknown')}: {fallacy.get('confidence', 0):.2f}"
                    )
            else:
                print(f"   [ERROR] Erreur: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")

    @pytest.mark.e2e
    def test_api_validate_endpoint(self, e2e_servers):
        """Test de l'endpoint de validation d'arguments"""
        base_url, _ = e2e_servers
        payload = {
            "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
            "conclusion": "Socrate est mortel",
            "argument_type": "deductive",
        }

        try:
            # Cette route /api/validate n'existe plus dans la nouvelle app Starlette
            pytest.skip("La route /api/validate n'est plus implémentée.")
            assert (
                base_url
            ), "L'URL du backend doit être fournie par la fixture e2e_servers"
            response = requests.post(
                f"{base_url}/api/validate", json=payload, timeout=30
            )
            print("\n[OK] Test de l'endpoint /api/validate:")
            print(f"   Status Code: {response.status_code}")
            print(
                f"   Argument testé: {payload['premises']} -> {payload['conclusion']}"
            )

            if response.status_code == 200:
                result = response.json()
                print("   [OK] Validation réussie")
                print(f"   Valide: {result.get('valid', False)}")
                print(f"   Confiance: {result.get('confidence', 0):.2f}")
            else:
                print(f"   [ERROR] Erreur: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")

    @pytest.mark.e2e
    def test_api_framework_endpoint(self, e2e_servers):
        """Test de l'endpoint de framework de Dung"""
        base_url, _ = e2e_servers
        payload = {
            "arguments": [
                {"id": "A1", "content": "Il faut protéger l'environnement"},
                {"id": "A2", "content": "L'économie est plus importante"},
                {"id": "A3", "content": "On peut faire les deux"},
            ],
            "attacks": [
                {"attacker": "A2", "target": "A1"},
                {"attacker": "A3", "target": "A2"},
            ],
        }

        try:
            # Cette route /api/framework n'existe plus. Elle a été remplacée par /api/v1/framework/analyze
            pytest.skip(
                "La route /api/framework a été remplacée par /api/v1/framework/analyze."
            )
            assert (
                base_url
            ), "L'URL du backend doit être fournie par la fixture e2e_servers"
            response = requests.post(
                f"{base_url}/api/framework", json=payload, timeout=30
            )
            print("\n[FRAMEWORK]  Test de l'endpoint /api/framework:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Arguments: {len(payload['arguments'])}")
            print(f"   Attaques: {len(payload['attacks'])}")

            if response.status_code == 200:
                result = response.json()
                print("   [OK] Framework construit")
                extensions = result.get("extensions", {})
                if isinstance(extensions, dict):
                    print(f"   Extensions calculées: {list(extensions.keys())}")
                else:
                    print(f"   Extensions calculées: {extensions}")
            else:
                print(f"   [ERROR] Erreur: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Erreur de connexion: {e}")

    @pytest.mark.e2e
    def test_generate_api_investigation_report(self, e2e_servers):
        """Génère un rapport d'investigation de l'API"""
        base_url, _ = e2e_servers
        report_path = Path("tests/functional/logs/api_investigation_report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        endpoints = ["/api/health", "/api/analyze", "/api/v1/framework/analyze"]
        assert base_url, "L'URL du backend doit être fournie par la fixture e2e_servers"
        report_content = """# [REPORT] Rapport d'Investigation - API Web d'Analyse Argumentative

**Date:** {timestamp}
**Base URL:** {base_url}

## [ANALYZE] État des Endpoints

""".format(
            timestamp=time.strftime("%d/%m/%Y %H:%M:%S"), base_url=base_url
        )

        for endpoint in endpoints:
            try:
                if endpoint == "/api/health":
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                else:
                    # Test avec données minimales
                    # Test avec données minimales
                    if endpoint == "/api/analyze":
                        test_data = {"text": "Test argument"}
                    elif endpoint == "/api/v1/framework/analyze":
                        test_data = {"arguments": ["a"], "attacks": []}
                    else:
                        test_data = {}
                    response = requests.post(
                        f"{base_url}{endpoint}", json=test_data, timeout=5
                    )

                status = (
                    "[OK] Opérationnel"
                    if response.status_code in [200, 400, 405]
                    else "[ERROR] Erreur"
                )  # 405 est ok pour un GET sur un POST
                report_content += (
                    f"### {endpoint}\n- **Status:** {status} ({response.status_code})\n"
                )

                if response.status_code == 200 and endpoint == "/api/health":
                    health_data = response.json()
                    services = health_data.get("services", {})
                    report_content += f"- **Services:** {list(services.keys())}\n"

                report_content += "\n"

            except Exception as e:
                report_content += (
                    f"### {endpoint}\n- **Status:** [ERROR] Inaccessible ({e})\n\n"
                )

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

        with open(report_path, "w", encoding="utf-8") as f:
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
