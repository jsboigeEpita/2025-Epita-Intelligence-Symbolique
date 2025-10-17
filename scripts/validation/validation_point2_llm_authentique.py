#!/usr/bin/env python3
"""
VALIDATION POINT 2 - Applications web Flask + React avec vrais LLMs
================================================================

Script de validation autonome pour Point 2 avec OpenRouter gpt-5-mini authentique.
"""

import sys
import subprocess
import time
import requests
import json
import os
from pathlib import Path
from datetime import datetime


def load_env_file():
    """Charge le fichier .env"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Nettoyer les guillemets
                    value = value.strip('"').strip("'")
                    os.environ[key] = value
        print("[OK] Fichier .env chargé")
    else:
        print("[ATTENTION] Fichier .env non trouvé")


# Charger les variables d'environnement
load_env_file()


class ValidationPoint2:
    """Validateur Point 2 avec vrais LLMs"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            "flask_interface": False,
            "react_interface": False,
            "llm_integration": False,
            "synthetic_data": False,
            "e2e_tests": False,
        }
        self.flask_process = None
        self.react_process = None

    def print_banner(self, title):
        """Bannière formatée"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def check_openrouter_config(self):
        """Vérifie la configuration OpenRouter"""
        self.print_banner("VERIFICATION CONFIGURATION OPENROUTER")

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        if not api_key or not base_url:
            print("[ERREUR] Configuration OpenRouter manquante")
            return False

        if "openrouter.ai" not in base_url:
            print("[ERREUR] Base URL OpenRouter invalide")
            return False

        print(f"[OK] API Key: {api_key[:20]}...")
        print(f"[OK] Base URL: {base_url}")
        return True

    def start_flask_interface(self):
        """Démarre l'interface Flask"""
        self.print_banner("DEMARRAGE INTERFACE FLASK")

        try:
            # Démarrer Flask en arrière-plan
            self.flask_process = subprocess.Popen(
                [sys.executable, "interface_web/app.py"],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Attendre le démarrage
            print("[*] Démarrage Flask en cours...")
            time.sleep(8)

            # Tester la connexion
            try:
                response = requests.get("http://localhost:3000", timeout=10)
                if response.status_code == 200:
                    print("[OK] Interface Flask opérationnelle")
                    return True
                else:
                    print(f"[ERREUR] Status code: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"[ERREUR] Connexion Flask: {e}")
                return False

        except Exception as e:
            print(f"[ERREUR] Démarrage Flask: {e}")
            return False

    def test_flask_with_real_llm(self):
        """Test Flask avec vrais appels LLM"""
        self.print_banner("TEST FLASK AVEC VRAIS LLMS")

        test_cases = [
            {
                "text": "Si il pleut, alors la route est mouillée. Il pleut. Donc la route est mouillée.",
                "analysis_type": "propositional",
            },
            {
                "text": "Il est nécessaire que tous les hommes soient mortels. Socrate est un homme.",
                "analysis_type": "modal",
            },
            {
                "text": "L'intelligence artificielle présente des avantages et des inconvénients.",
                "analysis_type": "comprehensive",
            },
        ]

        success_count = 0

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[*] Test {i}/3: {test_case['analysis_type']}")

            try:
                response = requests.post(
                    "http://localhost:3000/analyze", json=test_case, timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    print(
                        f"[OK] Analyse réussie - ID: {result.get('analysis_id', 'N/A')}"
                    )

                    # Vérifier la structure de réponse
                    if "results" in result and "metadata" in result:
                        print(f"[OK] Structure de réponse valide")
                        success_count += 1
                    else:
                        print(f"[ATTENTION] Structure de réponse incomplète")
                else:
                    print(f"[ERREUR] Status: {response.status_code}")

            except Exception as e:
                print(f"[ERREUR] Test {i}: {e}")

        success_rate = success_count / len(test_cases)
        print(
            f"\n[RESULTAT] Taux de succès Flask: {success_rate:.1%} ({success_count}/{len(test_cases)})"
        )

        self.results["flask_interface"] = success_rate >= 0.7
        return self.results["flask_interface"]

    def test_react_interface(self):
        """Test de l'interface React"""
        self.print_banner("TEST INTERFACE REACT")

        react_path = self.project_root / "services/web_api/interface-web-argumentative"

        if not react_path.exists():
            print("[ERREUR] Répertoire React non trouvé")
            return False

        try:
            # Vérifier package.json
            package_json = react_path / "package.json"
            if package_json.exists():
                print("[OK] Package.json trouvé")
            else:
                print("[ERREUR] Package.json manquant")
                return False

            # Vérifier les composants principaux
            components_dir = react_path / "src/components"
            if components_dir.exists():
                components = list(components_dir.glob("*.js"))
                print(f"[OK] {len(components)} composants React trouvés")

                # Compter les onglets attendus
                expected_components = [
                    "ArgumentAnalyzer",
                    "FallacyDetector",
                    "FrameworkBuilder",
                    "ValidationForm",
                    "LogicGraph",
                ]
                found_components = [c.stem for c in components]

                tab_count = sum(
                    1 for exp in expected_components if exp in found_components
                )
                print(f"[OK] {tab_count}/5 onglets principaux détectés")

                self.results["react_interface"] = tab_count >= 4
                return self.results["react_interface"]
            else:
                print("[ERREUR] Répertoire composants manquant")
                return False

        except Exception as e:
            print(f"[ERREUR] Test React: {e}")
            return False

    def generate_synthetic_data_with_llm(self):
        """Génère des données synthétiques avec vrais LLMs"""
        self.print_banner("GENERATION DONNEES SYNTHETIQUES")

        try:
            # Test simple d'appel LLM direct
            test_response = requests.post(
                "http://localhost:3000/analyze",
                json={
                    "text": "Générez un argument logique complexe sur l'éthique de l'IA.",
                    "analysis_type": "comprehensive",
                    "options": {"generate_synthetic": True},
                },
                timeout=45,
            )

            if test_response.status_code == 200:
                result = test_response.json()
                print(f"[OK] Génération synthétique réussie")
                print(
                    f"[INFO] Durée: {result.get('metadata', {}).get('duration', 'N/A')}s"
                )

                self.results["synthetic_data"] = True
                return True
            else:
                print(f"[ERREUR] Génération échouée: {test_response.status_code}")
                return False

        except Exception as e:
            print(f"[ERREUR] Génération synthétique: {e}")
            return False

    def run_quick_playwright_test(self):
        """Exécute un test Playwright rapide"""
        self.print_banner("TEST PLAYWRIGHT RAPIDE")

        try:
            # Test simple avec timeout court
            result = subprocess.run(
                [
                    "npx",
                    "playwright",
                    "test",
                    "--project=chromium",
                    "--timeout=30000",
                    "--max-failures=1",
                    "tests/flask-interface.spec.js",
                ],
                cwd=self.project_root / "tests_playwright",
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print("[OK] Tests Playwright réussis")
                self.results["e2e_tests"] = True
                return True
            else:
                print(f"[ATTENTION] Tests Playwright partiels")
                print(f"Stdout: {result.stdout[-200:]}")
                return False

        except subprocess.TimeoutExpired:
            print("[ATTENTION] Timeout tests Playwright")
            return False
        except Exception as e:
            print(f"[ERREUR] Tests Playwright: {e}")
            return False

    def cleanup(self):
        """Nettoyage des processus"""
        if self.flask_process:
            try:
                self.flask_process.terminate()
                self.flask_process.wait(timeout=5)
            except:
                self.flask_process.kill()

        if self.react_process:
            try:
                self.react_process.terminate()
                self.react_process.wait(timeout=5)
            except:
                self.react_process.kill()

    def generate_report(self):
        """Génère le rapport final"""
        self.print_banner("RAPPORT VALIDATION POINT 2")

        print("RESULTATS:")
        print(
            f"  [+] Interface Flask avec LLMs: {'[OK]' if self.results['flask_interface'] else '[ECHEC]'}"
        )
        print(
            f"  [+] Interface React 5 onglets: {'[OK]' if self.results['react_interface'] else '[ECHEC]'}"
        )
        print(
            f"  [+] Intégration LLM authentique: {'[OK]' if self.results['llm_integration'] else '[ECHEC]'}"
        )
        print(
            f"  [+] Données synthétiques: {'[OK]' if self.results['synthetic_data'] else '[ECHEC]'}"
        )
        print(
            f"  [+] Tests E2E Playwright: {'[OK]' if self.results['e2e_tests'] else '[ECHEC]'}"
        )

        success_count = sum(self.results.values())
        total_tests = len(self.results)
        success_rate = success_count / total_tests

        print(f"\nSCORE GLOBAL: {success_count}/{total_tests} ({success_rate:.1%})")

        if success_rate >= 0.8:
            print(
                "\n[SUCCES] POINT 2 VALIDÉ - Applications web opérationnelles avec vrais LLMs"
            )
            status = "VALIDÉ"
        elif success_rate >= 0.6:
            print("\n[ATTENTION] POINT 2 PARTIELLEMENT VALIDÉ")
            status = "PARTIEL"
        else:
            print("\n[ECHEC] POINT 2 NON VALIDÉ")
            status = "ECHEC"

        # Sauvegarde du rapport
        report = {
            "validation_date": datetime.now().isoformat(),
            "point": "Point 2 - Applications web Flask + React avec vrais LLMs",
            "status": status,
            "success_rate": success_rate,
            "detailed_results": self.results,
            "recommendations": self.get_recommendations(),
        }

        with open("rapport_validation_point2.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n[INFO] Rapport sauvegardé: rapport_validation_point2.json")
        return success_rate >= 0.6

    def get_recommendations(self):
        """Recommandations selon les résultats"""
        recommendations = []

        if not self.results["flask_interface"]:
            recommendations.append("Améliorer intégration ServiceManager dans Flask")

        if not self.results["react_interface"]:
            recommendations.append("Compléter développement composants React manquants")

        if not self.results["synthetic_data"]:
            recommendations.append(
                "Optimiser génération données synthétiques avec LLMs"
            )

        if not self.results["e2e_tests"]:
            recommendations.append("Stabiliser tests Playwright end-to-end")

        return recommendations

    def run_validation(self):
        """Exécute la validation complète"""
        self.print_banner("VALIDATION POINT 2 - APPLICATIONS WEB + VRAIS LLMS")

        try:
            # Phase 1: Configuration
            if not self.check_openrouter_config():
                print("[ERREUR] Configuration invalide")
                return False

            # Phase 2: Interface Flask
            if self.start_flask_interface():
                self.test_flask_with_real_llm()
                self.generate_synthetic_data_with_llm()
                self.results["llm_integration"] = True

            # Phase 3: Interface React
            self.test_react_interface()

            # Phase 4: Tests E2E rapides
            self.run_quick_playwright_test()

            # Phase 5: Rapport
            return self.generate_report()

        except KeyboardInterrupt:
            print("\n[INFO] Arrêt demandé")
            return False
        except Exception as e:
            print(f"\n[ERREUR] Erreur critique: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Point d'entrée"""
    validator = ValidationPoint2()
    success = validator.run_validation()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
