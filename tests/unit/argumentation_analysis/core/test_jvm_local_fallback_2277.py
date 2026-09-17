"""#2277/#2276 — ``initialize_jvm`` boots on the complete local Tweety set.

Root cause (measured A/B/C in the #2277 diagnosis): a machine holding a fully
assembled local set at vX (1.28) with no Maven and no env pin returned
``False`` from ``initialize_jvm`` — the configured default vY (1.31) has no
local set and cannot be assembled (the legacy fat-jar channel 404s since
#1874, Maven is absent). Every run on such a machine then degraded bipolar to
``jvm_not_started`` — the x40 WARN motif of the campaign — unless the operator
carried the workaround pin ``JVM_TWEETY_VERSION=1.28``.

These tests pin the repair's contract AND the #1874 guarantees it must not
relax:

* the fallback fires only when unpinned (env/.env pin = strict) AND Maven is
  absent (a machine that *can* assemble must move on with the config, not
  serve a stale local set forever);
* the local set must be COMPLETE — ``is_already_assembled`` arbitration:
  incomplete markers, stub fat jars and version-blind counts all refuse;
* the resolved version is what ``initialize_jvm`` provisions and what
  ``_build_tweety_classpath`` will match (the settings mutation).
"""

import zipfile

import pytest

from argumentation_analysis.config.settings import JVMSettings, settings
from argumentation_analysis.core import jvm_setup, tweety_assembly


def _fake_fat_jar(target, version: str, *, tweety: bool = True):
    """A fat jar whose *content* decides usability, like the real ones.

    ``carries_tweety_classes`` reads the zip entries, not the name: the stub
    variant (``tweety=False``) keeps a valid fat-jar name while holding no
    Tweety class — the interrupted-download shape #1880/#2246 documented.
    """
    jar = target / f"org.tweetyproject.tweety-full-{version}-with-dependencies.jar"
    with zipfile.ZipFile(jar, "w") as archive:
        if tweety:
            archive.writestr("org/tweetyproject/Stub.class", b"\xca\xfe\xba\xbe")
        else:
            archive.writestr("com/example/Stub.class", b"\x00")
    return jar


def _no_maven(monkeypatch):
    monkeypatch.setattr(tweety_assembly, "maven_executable", lambda: None)


def _unpinned_settings(monkeypatch):
    monkeypatch.delenv("JVM_TWEETY_VERSION", raising=False)
    fresh = JVMSettings(_env_file=None)
    assert (
        "tweety_version" not in fresh.model_fields_set
    ), "precondition brisée: sans env ni .env le champ doit être non-épinglé"
    monkeypatch.setattr(settings, "jvm", fresh)
    return fresh


def _pinned_settings(monkeypatch, version: str = "1.28"):
    monkeypatch.delenv("JVM_TWEETY_VERSION", raising=False)
    fresh = JVMSettings(_env_file=None, tweety_version=version)
    monkeypatch.setattr(settings, "jvm", fresh)
    return fresh


class TestDetectLocalVersion:
    def test_picks_the_highest_complete_set(self, tmp_path):
        _fake_fat_jar(tmp_path, "1.28")
        _fake_fat_jar(tmp_path, "1.30", tweety=False)  # stub: name says yes, content no
        assert tweety_assembly.detect_local_version(tmp_path) == "1.28"

    def test_refuses_empty_and_unborn_directories(self, tmp_path):
        assert tweety_assembly.detect_local_version(tmp_path) is None
        assert tweety_assembly.detect_local_version(tmp_path / "absent") is None

    def test_refuses_incomplete_marker(self, tmp_path):
        _fake_fat_jar(tmp_path, "1.28")
        (tmp_path / tweety_assembly.INCOMPLETE_MARKER).write_text("interrupted")
        assert tweety_assembly.detect_local_version(tmp_path) is None

    def test_none_when_nothing_carries_tweety_classes(self, tmp_path):
        _fake_fat_jar(tmp_path, "1.30", tweety=False)
        _fake_fat_jar(tmp_path, "1.31", tweety=False)
        assert tweety_assembly.detect_local_version(tmp_path) is None

    def test_serves_a_complete_module_set_over_a_higher_stub(self, tmp_path):
        # 34 module jars at 1.28 (the real assembled shape) vs a 1.31 stub.
        for index in range(tweety_assembly.MIN_EXPECTED_JARS):
            jar = tmp_path / f"org.tweetyproject.mod{index:02d}-1.28.jar"
            with zipfile.ZipFile(jar, "w") as archive:
                archive.writestr("org/tweetyproject/Mod.class", b"\xca\xfe\xba\xbe")
        _fake_fat_jar(tmp_path, "1.31", tweety=False)
        assert tweety_assembly.detect_local_version(tmp_path) == "1.28"


class TestResolverContract:
    def test_pinned_version_is_strict_even_with_a_better_local_set(
        self, monkeypatch, tmp_path
    ):
        _pinned_settings(monkeypatch, version="1.28")
        _no_maven(monkeypatch)
        monkeypatch.setattr(jvm_setup, "LIBS_DIR", tmp_path)
        _fake_fat_jar(tmp_path, "1.30")  # higher AND complete: must NOT win
        assert jvm_setup._resolve_effective_tweety_version() == "1.28"
        assert settings.jvm.tweety_version == "1.28"  # not mutated

    def test_maven_present_keeps_the_configured_version(self, monkeypatch, tmp_path):
        _unpinned_settings(monkeypatch)
        monkeypatch.setattr(tweety_assembly, "maven_executable", lambda: "/usr/bin/mvn")
        monkeypatch.setattr(jvm_setup, "LIBS_DIR", tmp_path)
        _fake_fat_jar(tmp_path, "1.28")  # complete local set: must NOT win
        assert jvm_setup._resolve_effective_tweety_version() == "1.31"
        assert settings.jvm.tweety_version == "1.31"  # not mutated

    def test_unpinned_without_maven_falls_back_and_mutates_settings(
        self, monkeypatch, tmp_path
    ):
        fresh = _unpinned_settings(monkeypatch)
        _no_maven(monkeypatch)
        monkeypatch.setattr(jvm_setup, "LIBS_DIR", tmp_path)
        _fake_fat_jar(tmp_path, "1.28")
        assert jvm_setup._resolve_effective_tweety_version() == "1.28"
        # the mutation is the point: _build_tweety_classpath reads settings live
        assert fresh.tweety_version == "1.28"

    def test_no_local_set_keeps_configured(self, monkeypatch, tmp_path):
        _unpinned_settings(monkeypatch)
        _no_maven(monkeypatch)
        monkeypatch.setattr(jvm_setup, "LIBS_DIR", tmp_path)  # empty dir
        assert jvm_setup._resolve_effective_tweety_version() == "1.31"
        assert settings.jvm.tweety_version == "1.31"


class TestInitializeJvmWiring:
    def test_provisions_the_resolved_version_not_the_module_constant(
        self, monkeypatch, tmp_path
    ):
        """The wiring: initialize_jvm passes the resolver's answer to
        download_tweety_jars — the module constant TWEETY_VERSION (bound at
        import to the configured 1.31) must not leak back in."""
        _unpinned_settings(monkeypatch)
        _no_maven(monkeypatch)
        monkeypatch.setattr(jvm_setup, "LIBS_DIR", tmp_path)
        _fake_fat_jar(tmp_path, "1.28")

        recorded = []
        monkeypatch.setattr(
            jvm_setup,
            "download_tweety_jars",
            lambda version=None, target_dir=None: recorded.append(version) or True,
        )
        monkeypatch.setattr(jvm_setup, "find_valid_java_home", lambda: None)
        monkeypatch.setattr(jvm_setup, "_JVM_WAS_SHUTDOWN", False)
        monkeypatch.setattr(jvm_setup.jpype, "isJVMStarted", lambda: False)

        jvm_setup.initialize_jvm()  # returns False (no java home) — irrelevant here
        assert recorded == ["1.28"]
