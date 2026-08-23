#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Validation d'API
==========================

Ce script exécute une campagne de test exhaustive sur les endpoints de l'API
FastAPI (`api.main:app`), en utilisant UnifiedWebOrchestrator pour gérer le
cycle de vie du serveur.

Il génère un rapport de test détaillé au format Markdown.
"""

import asyncio
import requests
import json
from pathlib import Path
import sys
from datetime import datetime
from typing import Any, Optional, Dict

# Assurer que la racine du projet est dans le sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# #1853: import the canonical orchestrator — the scripts/apps/webapp copy is a
# stale fork whose `app_module` kwarg no longer exists on the live class.
from argumentation_analysis.webapp.orchestrator import UnifiedWebOrchestrator

REPORT_FILE = (
    project_root / "docs" / "verification_s2" / "03_web_apps_apis_test_results.md"
)


class ReportGenerator:
    """Génère le rapport de test en Markdown."""

    def __init__(self, report_file: Path):
        self.report_file = report_file
        self._initialize_report()

    def _initialize_report(self):
        """Crée le fichier de rapport avec un en-tête."""
        header = "# Rapport de Preuves de Test : Web-Apps et APIs\n\n"
        header += f"Ce document contient les résultats détaillés de la campagne de test exhaustive menée le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
        self.report_file.write_text(header, encoding="utf-8")

    def add_section_header(self, title: str):
        """Ajoute un titre de section au rapport."""
        with self.report_file.open("a", encoding="utf-8") as f:
            f.write(f"## {title}\n\n")

    def add_test_result(
        self,
        name: str,
        command: str,
        response_status: int,
        response_body: Any,
        payload: Optional[Dict] = None,
    ):
        """Ajoute le résultat d'un test individuel."""
        body_str_lower = str(response_body).lower()
        is_success_status = 200 <= response_status < 300
        has_error_in_body = "erreur" in body_str_lower or "error" in body_str_lower

        result_status = (
            "SUCCÈS" if is_success_status and not has_error_in_body else "ÉCHEC"
        )

        content = f"### **Nom :** `{name}`\n"
        content += f"- **Commande de Test :** `{command}`\n"
        if payload:
            content += f"- **Payload :**\n  ```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n  ```\n"

        # Tronquer les réponses très longues
        body_str = json.dumps(response_body, indent=2, ensure_ascii=False)
        if len(body_str) > 1000:
            body_str = body_str[:1000] + "\n... (tronqué)\n"

        content += f"- **Réponse Obtenue :**\n"
        content += f"  - **Status:** {response_status}\n"
        content += f"  - **Body:**\n    ```json\n{body_str}\n    ```\n"
        content += f"- **Résultat :** `{result_status}`\n"
        content += f"- **Corrections Apportées :** Aucune (phase de collecte).\n\n"

        with self.report_file.open("a", encoding="utf-8") as f:
            f.write(content)

        print(f"[{result_status}] Testé : {name}")


class ApiTester:
    """Exécute des requêtes sur une API et rapporte les résultats."""

    def __init__(self, base_url: str, reporter: ReportGenerator):
        self.base_url = base_url
        self.reporter = reporter

    def test_get(self, endpoint, name):
        url = f"{self.base_url}{endpoint}"
        command = f"requests.get('{url}')"
        try:
            response = requests.get(url, timeout=20)
            self.reporter.add_test_result(
                name, command, response.status_code, response.json()
            )
        except requests.RequestException as e:
            self.reporter.add_test_result(name, command, 503, {"error": str(e)})

    def test_post(self, endpoint, name, payload):
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        command = f"requests.post('{url}', json=...)"
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            self.reporter.add_test_result(
                name, command, response.status_code, response.json(), payload
            )
        except requests.RequestException as e:
            self.reporter.add_test_result(
                name, command, 503, {"error": str(e)}, payload
            )


async def run_fastapi_tests(
    orchestrator: UnifiedWebOrchestrator, reporter: ReportGenerator
):
    """Démarre FastAPI et exécute la suite de tests."""
    reporter.add_section_header("1. API FastAPI (`api/main.py`)")

    # #1853: no `app_module` kwarg on the canonical orchestrator — the uvicorn
    # target comes from config/webapp_config.yml (backend.module).
    if not await orchestrator.start_webapp(frontend_enabled=False):
        print("Échec du démarrage du serveur FastAPI.")
        return

    base_url = orchestrator.app_info.backend_url
    tester = ApiTester(base_url, reporter)

    print(f"--- Tests FastAPI sur {base_url} ---")

    # Endpoints du routeur principal
    tester.test_get("/api/health", "FastAPI - GET /api/health")
    tester.test_get("/api/status", "FastAPI - GET /api/status")
    tester.test_get("/api/examples", "FastAPI - GET /api/examples")
    tester.test_get("/api/endpoints", "FastAPI - GET /api/endpoints")

    analyze_payload = {
        "text": "Socrates is a man, all men are mortal, therefore Socrates is mortal."
    }
    tester.test_post("/api/analyze", "FastAPI - POST /api/analyze", analyze_payload)

    # Endpoints du routeur Dung
    # Payload corrigé selon api/models.py:FrameworkAnalysisRequest
    dung_payload = {"arguments": ["a", "b", "c"], "attacks": [["a", "b"], ["b", "c"]]}
    tester.test_post(
        "/api/v1/framework/analyze",
        "FastAPI - POST /api/v1/framework/analyze",
        dung_payload,
    )

    await orchestrator.stop_webapp()
    print("--- Fin des tests FastAPI ---")


async def main():
    """Point d'entrée principal du script de validation."""
    reporter = ReportGenerator(REPORT_FILE)
    orchestrator = UnifiedWebOrchestrator()

    try:
        await run_fastapi_tests(orchestrator, reporter)
    except Exception as e:
        print(f"Une erreur critique est survenue durant l'orchestration des tests: {e}")
    finally:
        print("Script de validation terminé.")


if __name__ == "__main__":
    asyncio.run(main())
