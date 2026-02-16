#!/usr/bin/env python3
"""
Test unitaire pour diagnostiquer le problème JPype dans DependencyValidator
du unified_production_analyzer.py

Ce test valide que JPype1 est correctement installé et peut être importé
par le DependencyValidator, reproduisant l'erreur exacte.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajouter le répertoire racine au sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Skip tests that need real jpype when --disable-jvm-session mocks it
_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)


class TestJPypeDependencyValidator:
    """Tests pour diagnostiquer le problème JPype dans DependencyValidator"""

    @pytest.mark.skipif(_jpype_is_mocked, reason="jpype is mocked by --disable-jvm-session")
    def test_jpype_import_direct(self):
        """Test 1: Vérifier que jpype peut être importé directement"""
        try:
            import jpype

            assert hasattr(jpype, "__version__"), "jpype n'a pas d'attribut __version__"
            assert hasattr(
                jpype, "isJVMStarted"
            ), "jpype n'a pas de méthode isJVMStarted"
            assert hasattr(
                jpype, "getDefaultJVMPath"
            ), "jpype n'a pas de méthode getDefaultJVMPath"
            print(f"✅ JPype version: {jpype.__version__}")
        except ImportError as e:
            pytest.fail(f"Impossible d'importer jpype: {e}")

    @pytest.mark.skipif(_jpype_is_mocked, reason="jpype is mocked by --disable-jvm-session")
    def test_jpype_import_alternative(self):
        """Test 2: Vérifier l'import jpype alternatif"""
        try:
            import jpype

            assert hasattr(jpype, "__version__"), "jpype n'a pas d'attribut __version__"
            print(f"✅ JPype version (import direct): {jpype.__version__}")
        except ImportError:
            print("ℹ️  Import jpype direct non disponible (normal)")

    def test_dependency_validator_jpype_check(self):
        """Test 3: Reproduire exactement le code du DependencyValidator"""

        # Simuler la méthode _validate_tweety_dependencies
        errors = []

        try:
            # Code exact de la ligne 490 du unified_production_analyzer.py
            import jpype

            # Vérifications supplémentaires comme dans le validateur
            if not jpype.isJVMStarted():
                try:
                    # On ne démarre pas réellement la JVM dans le test
                    print("ℹ️  JVM non démarrée (normal en test)")
                except Exception as e:
                    errors.append(
                        f"Impossible de démarrer la JVM pour TweetyProject: {e}"
                    )

        except ImportError:
            errors.append("jpype non installé - requis pour TweetyProject")

        # Assertion: pas d'erreurs d'import
        assert not any(
            "jpype non installé" in err for err in errors
        ), f"Erreur d'import jpype détectée: {errors}"

    # def test_unified_production_analyzer_import(self):
    #     """Test 4: Vérifier que le module unified_production_analyzer peut être importé"""
    #     try:
    #         from argumentation_analysis.rhetorical_analysis.unified_production_analyzer import DependencyValidator
    #         print("✅ DependencyValidator importé avec succès")
    #     except ImportError as e:
    #         pytest.fail(f"Impossible d'importer DependencyValidator: {e}")

    # @patch('jpype.isJVMStarted', return_value=False)
    # @patch('jpype.startJVM')
    # def test_dependency_validator_instance(self, mock_start_jvm, mock_is_started):
    #     """Test 5: Tester une instance réelle de DependencyValidator avec mocks"""

    #     # Configuration mock pour éviter les dépendances lourdes
    #     from argumentation_analysis.rhetorical_analysis.unified_production_analyzer import (
    #         DependencyValidator,
    #         UnifiedProductionConfig
    #     )

    #     # Configuration minimale
    #     config = UnifiedProductionConfig()

    #     # Créer le validateur
    #     validator = DependencyValidator(config)

    #     # Tester la validation tweety (method privée, on teste via validate_all)
    #     try:
    #         # Cette méthode est async, on teste juste l'instantiation
    #         assert validator is not None
    #         assert hasattr(validator, '_validate_tweety_dependencies')
    #         print("✅ DependencyValidator instancié avec succès")
    #     except Exception as e:
    #         pytest.fail(f"Erreur lors de l'instantiation du DependencyValidator: {e}")

    def test_environment_diagnostics(self):
        """Test 6: Diagnostics détaillés de l'environnement"""
        import pkg_resources

        # Rechercher tous les packages JPype
        jpype_packages = [
            pkg
            for pkg in pkg_resources.working_set
            if "jpype" in pkg.project_name.lower()
        ]

        print(f"\n📦 Packages JPype trouvés: {len(jpype_packages)}")
        for pkg in jpype_packages:
            print(f"   - {pkg.project_name} {pkg.version} ({pkg.location})")

        # Vérifier l'environnement Python
        print(f"\n🐍 Environnement Python:")
        print(f"   - Exécutable: {sys.executable}")
        print(f"   - Version: {sys.version}")
        print(f"   - Préfixe: {sys.prefix}")

        # Au moins un package JPype doit être présent
        assert (
            len(jpype_packages) > 0
        ), "Aucun package JPype trouvé dans l'environnement"

    def test_auto_env_activation(self):
        """Test 7: Vérifier que auto_env fonctionne correctement"""
        try:
            from argumentation_analysis.core.environment import ensure_env

            # Ne pas appeler ensure_env() dans les tests pour éviter les effets de bord
            print("✅ Module auto_env importé avec succès")
        except ImportError as e:
            pytest.fail(f"Impossible d'importer auto_env: {e}")


if __name__ == "__main__":
    # Permettre l'exécution directe du test pour débogage
    pytest.main([__file__, "-v", "-s"])
