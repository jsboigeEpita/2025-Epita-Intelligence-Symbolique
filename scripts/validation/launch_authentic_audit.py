#!/usr/bin/env python3
"""
LANCEUR D'AUDIT AUTHENTIQUE
===========================

Script de lancement pour l'audit d'authenticité avec préparation de l'environnement.
Vérifie les prérequis et configure l'environnement avant le test.
"""

import argumentation_analysis.core.environment
import os
import sys
import subprocess
from pathlib import Path


def check_prerequisites():
    """Vérifie les prérequis pour l'audit authentique."""
    print("[SCAN] VERIFICATION DES PREREQUIS")
    print("-" * 40)

    # Vérifier Python
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print(
            f"[OK] Python {python_version.major}.{python_version.minor}.{python_version.micro}"
        )
    else:
        print(
            f"[ERROR] Python {python_version.major}.{python_version.minor} (3.8+ requis)"
        )
        return False

    # Vérifier les modules critiques
    required_modules = [
        "openai",
        "semantic_kernel",
        "asyncio",
        "json",
        "hashlib",
        "uuid",
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"[OK] Module {module}")
        except ImportError:
            print(f"[ERROR] Module {module} manquant")
            missing_modules.append(module)

    if missing_modules:
        print(f"\n[ERROR] Modules manquants: {', '.join(missing_modules)}")
        print("Installer avec: pip install openai semantic-kernel")
        return False

    # Vérifier la structure du projet
    critical_paths = [
        "argumentation_analysis/orchestration/cluedo_orchestrator.py",
        "config/.env",
    ]

    for path in critical_paths:
        if os.path.exists(path):
            print(f"[OK] Fichier {path}")
        else:
            print(f"[ERROR] Fichier {path} manquant")
            return False

    print("\n[SUCCESS] TOUS LES PREREQUIS SONT SATISFAITS")
    return True


def setup_environment():
    """Configure l'environnement pour l'audit authentique."""
    print("\n[CONFIG] CONFIGURATION DE L'ENVIRONNEMENT")
    print("-" * 40)

    # Demander la clé API à l'utilisateur
    print("CONFIGURATION API OPENAI REQUISE:")
    print("Pour un audit authentique, une vraie clé API OpenAI est nécessaire.")
    print("Vous pouvez:")
    print("1. Définir la variable d'environnement OPENAI_API_KEY_REAL")
    print("2. Ou la saisir maintenant (elle ne sera pas sauvegardée)")
    print()

    # Vérifier si une clé est déjà définie
    real_api_key = os.getenv("OPENAI_API_KEY_REAL")

    if not real_api_key:
        print("[ERROR] Variable OPENAI_API_KEY_REAL non définie")
        print("\nPour un test AUTHENTIQUE, définissez cette variable :")
        print("Windows: set OPENAI_API_KEY_REAL=sk-votre-vraie-cle")
        print("Linux/Mac: export OPENAI_API_KEY_REAL=sk-votre-vraie-cle")
        print(
            "\nPour continuer en mode SIMULATION (détection de mocks) appuyez sur Entrée"
        )

        user_input = input("Clé API (optionnel pour simulation): ").strip()
        if user_input:
            os.environ["OPENAI_API_KEY_REAL"] = user_input
            real_api_key = user_input
            print("[OK] Clé API temporairement définie")
        else:
            print("[WARNING] MODE SIMULATION activé (détectera les mocks)")
    else:
        # Masquer la clé pour affichage
        masked_key = (
            real_api_key[:7] + "*" * 20 + real_api_key[-4:]
            if len(real_api_key) > 11
            else "sk-***"
        )
        print(f"[OK] Clé API détectée: {masked_key}")

    # Configurer les variables d'environnement pour l'audit
    os.environ["OPENAI_API_KEY"] = real_api_key or "sk-test-will-be-detected-as-mock"
    os.environ["AUDIT_MODE"] = "AUTHENTIC"
    os.environ["PYTHONPATH"] = os.getcwd()

    print("[OK] ENVIRONNEMENT CONFIGURE")
    return True


def run_audit():
    """Lance l'audit d'authenticité."""
    print("\n[LAUNCH] LANCEMENT DE L'AUDIT D'AUTHENTICITE")
    print("=" * 50)

    try:
        # Lancer le script d'audit
        result = subprocess.run(
            [sys.executable, "test_authenticite_reelle_audit.py"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )

        print("SORTIE AUDIT:")
        print("-" * 20)
        print(result.stdout)

        if result.stderr:
            print("ERREURS:")
            print("-" * 20)
            print(result.stderr)

        print(f"\nCODE DE RETOUR: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ ERREUR LANCEMENT AUDIT: {e}")
        return False


def main():
    """Point d'entrée principal."""
    print("[AUDIT] AUDIT D'AUTHENTICITE DU SYSTEME")
    print("Elimination des mocks de complaisance")
    print("=" * 50)

    # Vérifier les prérequis
    if not check_prerequisites():
        print("\n[ERROR] PREREQUIS NON SATISFAITS")
        print("Veuillez installer les dépendances manquantes")
        return False

    # Configurer l'environnement
    if not setup_environment():
        print("\n[ERROR] CONFIGURATION ENVIRONNEMENT ECHOUEE")
        return False

    # Lancer l'audit
    success = run_audit()

    if success:
        print("\n[SUCCESS] AUDIT TERMINE AVEC SUCCES")
        print("Consultez le rapport dans le dossier reports/")
    else:
        print("\n[ERROR] AUDIT ECHOUE")
        print("Vérifiez les logs et corrigez les problèmes détectés")

    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[STOP] AUDIT INTERROMPU PAR L'UTILISATEUR")
        sys.exit(1)
    except Exception as e:
        print(f"\n[CRITICAL] ERREUR CRITIQUE: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
