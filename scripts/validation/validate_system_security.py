#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de validation de la sécurité du système de basculement.

Ce script valide que le système de basculement entre sources simples et complexes
fonctionne correctement et que la sécurité des données politiques est préservée.
"""

import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict

# Ajouter le chemin du projet
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from argumentation_analysis.core.source_manager import create_source_manager
from argumentation_analysis.paths import PROJECT_ROOT_DIR

logger = logging.getLogger(__name__)


class SystemSecurityValidator:
    """
    Validateur de sécurité pour le système de basculement.
    """

    def __init__(self):
        """Initialise le validateur."""
        self.project_root = PROJECT_ROOT_DIR
        self.validation_results: Dict[str, Dict] = {}

        # Configuration du logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def validate_source_manager_simple(self) -> Dict[str, any]:
        """
        Valide le fonctionnement du SourceManager en mode simple.

        Returns:
            Dictionnaire avec les résultats de validation
        """
        logger.info("=== Validation du SourceManager (mode simple) ===")

        try:
            with create_source_manager("simple") as source_manager:
                # Test du chargement
                extract_definitions, status = source_manager.load_sources()

                # Vérifications
                checks = {
                    "sources_loaded": extract_definitions is not None,
                    "status_success": "succès" in status.lower(),
                    "sources_count": len(extract_definitions.sources)
                    if extract_definitions
                    else 0,
                    "text_selection": False,
                    "anonymization_active": source_manager.config.anonymize_logs,
                    "auto_cleanup": source_manager.config.auto_cleanup,
                }

                # Test de sélection de texte
                if extract_definitions:
                    text, description = source_manager.select_text_for_analysis(
                        extract_definitions
                    )
                    checks["text_selection"] = bool(text and len(text) > 50)
                    checks["text_length"] = len(text) if text else 0
                    checks["description"] = description

                logger.info(
                    f"Mode simple - Sources chargées: {checks['sources_count']}"
                )
                logger.info(
                    f"Mode simple - Texte sélectionné: {checks['text_selection']}"
                )

                return {
                    "success": all(
                        [
                            checks["sources_loaded"],
                            checks["status_success"],
                            checks["text_selection"],
                        ]
                    ),
                    "details": checks,
                    "error": None,
                }

        except Exception as e:
            logger.error(f"Erreur en mode simple: {e}")
            return {"success": False, "details": {}, "error": str(e)}

    def validate_source_manager_complex_fallback(self) -> Dict[str, any]:
        """
        Valide le fonctionnement du SourceManager en mode complex avec fallback.

        Returns:
            Dictionnaire avec les résultats de validation
        """
        logger.info("=== Validation du SourceManager (mode complex - fallback) ===")

        try:
            # Test avec passphrase incorrecte pour déclencher le fallback
            with create_source_manager(
                "complex", passphrase="wrong_passphrase"
            ) as source_manager:
                # Test du chargement (doit échouer et déclencher fallback)
                extract_definitions, status = source_manager.load_sources()

                # Test de sélection avec fallback
                text, description = source_manager.select_text_for_analysis(
                    extract_definitions
                )

                checks = {
                    "fallback_triggered": extract_definitions is None,
                    "error_status": "échec" in status.lower()
                    or "erreur" in status.lower(),
                    "fallback_text_provided": bool(text and len(text) > 20),
                    "fallback_description": "fallback" in description.lower(),
                    "anonymization_active": source_manager.config.anonymize_logs,
                    "auto_cleanup": source_manager.config.auto_cleanup,
                }

                logger.info(
                    f"Mode complex - Fallback déclenché: {checks['fallback_triggered']}"
                )
                logger.info(
                    f"Mode complex - Texte fallback fourni: {checks['fallback_text_provided']}"
                )

                return {
                    "success": all(
                        [checks["fallback_triggered"], checks["fallback_text_provided"]]
                    ),
                    "details": checks,
                    "error": None,
                }

        except Exception as e:
            logger.error(f"Erreur en mode complex: {e}")
            return {"success": False, "details": {}, "error": str(e)}

    def validate_encrypted_corpus_access(self) -> Dict[str, any]:
        """
        Valide l'accès au corpus chiffré.

        Returns:
            Dictionnaire avec les résultats de validation
        """
        logger.info("=== Validation de l'accès au corpus chiffré ===")

        corpus_path = (
            self.project_root
            / "argumentation_analysis"
            / "data"
            / "extract_sources.json.gz.enc"
        )

        checks = {
            "corpus_exists": corpus_path.exists(),
            "corpus_size": corpus_path.stat().st_size if corpus_path.exists() else 0,
            "corpus_readable": False,
            "gitignore_protected": False,
        }

        if checks["corpus_exists"]:
            try:
                # Test de lecture (sans déchiffrement)
                with open(corpus_path, "rb") as f:
                    data = f.read(100)  # Lire les premiers 100 bytes
                checks["corpus_readable"] = len(data) > 0

            except Exception as e:
                logger.warning(f"Erreur lecture corpus: {e}")

        # Vérifier la protection .gitignore
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    gitignore_content = f.read()
                checks["gitignore_protected"] = (
                    "!data/extract_sources.json.gz.enc" in gitignore_content
                )
            except Exception:
                pass

        logger.info(f"Corpus chiffré - Existe: {checks['corpus_exists']}")
        logger.info(f"Corpus chiffré - Taille: {checks['corpus_size']} bytes")
        logger.info(
            f"Corpus chiffré - Protégé par .gitignore: {checks['gitignore_protected']}"
        )

        return {
            "success": checks["corpus_exists"]
            and checks["corpus_readable"]
            and checks["gitignore_protected"],
            "details": checks,
            "error": None,
        }

    def validate_demo_script_integration(self) -> Dict[str, any]:
        """
        Valide l'intégration du script de démonstration.

        Returns:
            Dictionnaire avec les résultats de validation
        """
        logger.info("=== Validation de l'intégration du script de démonstration ===")

        demo_script = (
            self.project_root / "scripts" / "demo" / "run_rhetorical_analysis_demo.py"
        )

        checks = {
            "script_exists": demo_script.exists(),
            "source_type_arg": False,
            "import_source_manager": False,
            "help_contains_source_type": False,
        }

        if checks["script_exists"]:
            try:
                with open(demo_script, "r", encoding="utf-8") as f:
                    content = f.read()

                # Vérifier les intégrations clés
                checks["source_type_arg"] = "--source-type" in content
                checks["import_source_manager"] = (
                    "from argumentation_analysis.core.source_manager" in content
                )

                # Test de l'aide
                result = subprocess.run(
                    [sys.executable, str(demo_script), "--help"],
                    capture_output=True,
                    text=True,
                    cwd=str(demo_script.parent),
                    timeout=10,
                )

                if result.returncode == 0:
                    checks["help_contains_source_type"] = (
                        "--source-type" in result.stdout
                    )

            except Exception as e:
                logger.warning(f"Erreur validation script: {e}")

        logger.info(f"Script démo - Existe: {checks['script_exists']}")
        logger.info(
            f"Script démo - Argument --source-type: {checks['source_type_arg']}"
        )
        logger.info(
            f"Script démo - Import SourceManager: {checks['import_source_manager']}"
        )

        return {"success": all(checks.values()), "details": checks, "error": None}

    def validate_cleanup_script(self) -> Dict[str, any]:
        """
        Valide le script de nettoyage des données sensibles.

        Returns:
            Dictionnaire avec les résultats de validation
        """
        logger.info("=== Validation du script de nettoyage ===")

        cleanup_script = (
            self.project_root / "scripts" / "utils" / "cleanup_sensitive_traces.py"
        )

        checks = {
            "script_exists": cleanup_script.exists(),
            "dry_run_works": False,
            "help_available": False,
        }

        if checks["script_exists"]:
            try:
                # Test du mode dry-run
                result = subprocess.run(
                    [sys.executable, str(cleanup_script), "--dry-run"],
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_root),
                    timeout=30,
                )

                checks["dry_run_works"] = (
                    result.returncode == 0 and "SIMULATION TERMINÉE" in result.stdout
                )

                # Test de l'aide
                result = subprocess.run(
                    [sys.executable, str(cleanup_script), "--help"],
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_root),
                    timeout=10,
                )

                checks["help_available"] = result.returncode == 0

            except Exception as e:
                logger.warning(f"Erreur validation nettoyage: {e}")

        logger.info(f"Script nettoyage - Existe: {checks['script_exists']}")
        logger.info(f"Script nettoyage - Dry-run fonctionne: {checks['dry_run_works']}")

        return {"success": all(checks.values()), "details": checks, "error": None}

    def run_full_validation(self) -> Dict[str, Dict]:
        """
        Exécute la validation complète du système.

        Returns:
            Dictionnaire avec tous les résultats de validation
        """
        logger.info("🔒 DÉBUT DE LA VALIDATION DE SÉCURITÉ DU SYSTÈME 🔒")

        validations = {
            "source_manager_simple": self.validate_source_manager_simple(),
            "source_manager_complex": self.validate_source_manager_complex_fallback(),
            "encrypted_corpus": self.validate_encrypted_corpus_access(),
            "demo_integration": self.validate_demo_script_integration(),
            "cleanup_script": self.validate_cleanup_script(),
        }

        # Résumé global
        all_success = all(result["success"] for result in validations.values())
        total_tests = len(validations)
        passed_tests = sum(1 for result in validations.values() if result["success"])

        logger.info("🔒 RÉSUMÉ DE LA VALIDATION 🔒")
        logger.info(f"Tests passés: {passed_tests}/{total_tests}")

        for test_name, result in validations.items():
            status = "✅ SUCCÈS" if result["success"] else "❌ ÉCHEC"
            logger.info(f"  - {test_name}: {status}")
            if not result["success"] and result.get("error"):
                logger.error(f"    Erreur: {result['error']}")

        if all_success:
            logger.info("🎉 VALIDATION COMPLÈTE RÉUSSIE - SYSTÈME SÉCURISÉ 🎉")
        else:
            logger.warning("⚠️ CERTAINS TESTS ONT ÉCHOUÉ - VÉRIFICATION REQUISE ⚠️")

        return validations


def main():
    """Fonction principale du script."""
    validator = SystemSecurityValidator()
    results = validator.run_full_validation()

    # Code de sortie selon les résultats
    all_success = all(result["success"] for result in results.values())
    exit_code = 0 if all_success else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
