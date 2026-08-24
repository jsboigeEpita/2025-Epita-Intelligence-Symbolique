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

    @pytest.mark.skipif(
        _jpype_is_mocked, reason="jpype is mocked by --disable-jvm-session"
    )
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

    @pytest.mark.skipif(
        _jpype_is_mocked, reason="jpype is mocked by --disable-jvm-session"
    )
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

    def test_environment_diagnostics(self):
        """Test 6: Diagnostics détaillés de l'environnement"""
        # ATT-1 #1336: pkg_resources est déprécié/retiré dans setuptools récent
        # (>=67 deprecated, retiré par défaut en 81+/82 → ModuleNotFoundError sur
        # CI et localement). Migrer vers importlib.metadata (stdlib, Python 3.8+),
        # replacement officiel pour parcourir les distributions installées.
        from importlib.metadata import distributions

        # Rechercher tous les packages JPype
        jpype_packages = [
            dist
            for dist in distributions()
            if "jpype" in (dist.metadata.get("Name", "") or "").lower()
        ]

        print(f"\n📦 Packages JPype trouvés: {len(jpype_packages)}")
        for dist in jpype_packages:
            print(
                f"   - {dist.metadata['Name']} {dist.version} ({dist.locate_file('')})"
            )

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


# --------------------------------------------------------------------------- #1874
# The tests above *transcribe* the validator ("Code exact de la ligne 490 du
# unified_production_analyzer.py") instead of calling it. A transcription cannot
# drift into a bug, because it is not the code: the jar check it copies shipped
# `len(jar_files) == 0` with zero coverage while this file carried the module's
# name. These tests call the real function.


class TestValidateTweetyJars:
    """`validate_tweety_jars` must see the shape that produces a silent run.

    A count answers "is the directory empty". The failure that actually happens is
    a directory that is *not* empty and still yields no loadable Tweety class --
    the thin aggregator, a truncated download, a leftover of unrelated jars. The
    JVM starts on it and every Tweety import then fails as a **skip**.
    """

    @staticmethod
    def _jar(path, *entries):
        import zipfile

        with zipfile.ZipFile(path, "w") as z:
            for entry in entries:
                z.writestr(entry, b"x")
        return path

    def test_a_healthy_assembly_reports_nothing(self, tmp_path):
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        self._jar(
            tmp_path / "org.tweetyproject.logics.pl-1.29.jar",
            "org/tweetyproject/logics/pl/syntax/Proposition.class",
        )
        assert validate_tweety_jars(tmp_path) == []

    def test_a_missing_directory_is_reported(self, tmp_path):
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        errors = validate_tweety_jars(tmp_path / "absent")
        assert len(errors) == 1 and "manquant" in errors[0]

    def test_an_empty_directory_is_reported(self, tmp_path):
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        errors = validate_tweety_jars(tmp_path)
        assert len(errors) == 1 and "Aucun JAR" in errors[0]

    def test_only_the_thin_aggregator_is_reported(self, tmp_path):
        """1918 bytes, 0 class -- a real .jar that a count accepts.

        Degenerate substitution: put `len(jar_files) == 0` back and this is the
        test that reddens.
        """
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        self._jar(tmp_path / "org.tweetyproject.tweety-full-1.29.jar", "META-INF/X.txt")
        errors = validate_tweety_jars(tmp_path)
        assert len(errors) == 1, f"expected one diagnostic, got {errors}"
        assert "aucun ne porte de classe" in errors[0]

    def test_a_truncated_download_keeping_the_fat_name_is_reported(self, tmp_path):
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        (
            tmp_path / "org.tweetyproject.tweety-full-1.29-with-dependencies.jar"
        ).write_bytes(b"PK\x03\x04" + b"\x00" * 1020)
        errors = validate_tweety_jars(tmp_path)
        assert len(errors) == 1 and "aucun ne porte de classe" in errors[0]

    def test_a_directory_of_unrelated_jars_is_reported(self, tmp_path):
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        for i in range(5):
            self._jar(
                tmp_path / f"third.party.lib{i}-9.9.jar", f"third/party/L{i}.class"
            )
        errors = validate_tweety_jars(tmp_path)
        assert len(errors) == 1 and "aucun ne porte de classe" in errors[0]

    def test_one_real_jar_among_junk_is_enough(self, tmp_path):
        """Anti-pendulum: the criterion is "at least one loadable Tweety class",
        not "every jar is clean". A `copy-dependencies` assembly legitimately
        holds ~80 third-party jars next to the Tweety modules -- a rule requiring
        all of them to carry Tweety classes would redden every healthy run."""
        from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
            validate_tweety_jars,
        )

        for i in range(5):
            self._jar(
                tmp_path / f"third.party.lib{i}-9.9.jar", f"third/party/L{i}.class"
            )
        self._jar(
            tmp_path / "org.tweetyproject.logics.pl-1.29.jar",
            "org/tweetyproject/logics/pl/syntax/Proposition.class",
        )
        assert validate_tweety_jars(tmp_path) == []
