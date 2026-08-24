"""Offline tests for the Maven assembly of the Tweety classpath (#1874).

No Maven, no JVM, no network: everything asserted here is a pure function or a
subprocess boundary that is monkeypatched. The one thing these tests deliberately
do NOT claim is that Maven actually resolves the closure -- that is proven by the
real assembly run recorded in the PR, because no fixture can prove it (a fixture
would contain whatever answer the author put in it).
"""

import subprocess
from pathlib import Path

import pytest

from argumentation_analysis.core import tweety_assembly as ta

# ------------------------------------------------------------------ pin parsing


def test_empty_pin_spec_is_the_common_case():
    assert ta.parse_pin_spec("") == {}
    assert ta.parse_pin_spec("   ") == {}
    assert ta.parse_pin_spec(None) == {}


def test_pin_spec_parses_the_1874_pin():
    assert ta.parse_pin_spec("org.tweetyproject.arg:bipolar:1.30") == {
        "org.tweetyproject.arg:bipolar": "1.30"
    }


def test_pin_spec_parses_several_and_trims():
    assert ta.parse_pin_spec(" a:b:1 , c:d:2 ") == {"a:b": "1", "c:d": "2"}


@pytest.mark.parametrize("bad", ["a:b", "a:b:c:d", "a::1", ":b:1", "a:b:"])
def test_malformed_pin_raises_instead_of_being_dropped(bad):
    """A silently dropped pin reinstates the capability loss it was added to stop.

    Dropping it would leave the assembly succeeding with the WRONG module version
    and nothing downstream would notice -- the failure would surface much later as
    a missing class, far from its cause.
    """
    with pytest.raises(ValueError, match="pin invalide"):
        ta.parse_pin_spec(bad)


def test_exclude_spec_parsing_and_rejection():
    assert ta.parse_exclude_spec("org.tweetyproject:web") == [
        ("org.tweetyproject", "web")
    ]
    assert ta.parse_exclude_spec("") == []
    with pytest.raises(ValueError, match="exclusion invalide"):
        ta.parse_exclude_spec("org.tweetyproject:web:1.31")


# ------------------------------------------------------------------ POM rendering


def test_pom_without_pins_declares_only_the_aggregator():
    pom = ta.render_assembly_pom("1.29")
    assert ta.pinned_versions_in_pom(pom) == {"org.tweetyproject:tweety-full": "1.29"}


def test_pinned_module_is_a_direct_dependency_so_nearest_wins():
    """Maven resolves conflicts by nearest definition, not by highest version.

    The pin must therefore be a direct <dependency>, not merely mentioned. Reading
    it back with a real XML parser (not a substring check) is what makes this a
    decoding test rather than a template echo.
    """
    pom = ta.render_assembly_pom("1.31", pins={"org.tweetyproject.arg:bipolar": "1.30"})
    decoded = ta.pinned_versions_in_pom(pom)
    assert decoded["org.tweetyproject.arg:bipolar"] == "1.30"
    assert decoded["org.tweetyproject:tweety-full"] == "1.31"


def test_pin_is_emitted_before_the_aggregator():
    pom = ta.render_assembly_pom("1.31", pins={"org.tweetyproject.arg:bipolar": "1.30"})
    assert pom.index("<artifactId>bipolar</artifactId>") < pom.index(
        "<artifactId>tweety-full</artifactId>"
    )


def test_exclusion_is_attached_to_the_aggregator():
    pom = ta.render_assembly_pom("1.31", excludes=[("org.tweetyproject", "web")])
    assert "<exclusions>" in pom
    assert pom.index("<artifactId>tweety-full</artifactId>") < pom.index("<exclusion>")


def test_rendered_pom_is_well_formed_xml_in_every_combination():
    pom = ta.render_assembly_pom(
        "1.31",
        pins={"org.tweetyproject.arg:bipolar": "1.30", "x.y:z": "9"},
        excludes=[("org.tweetyproject", "web"), ("a", "b")],
    )
    decoded = ta.pinned_versions_in_pom(pom)  # raises on malformed XML
    assert decoded["x.y:z"] == "9"


# ------------------------------------------------------- counting / idempotence


def _touch(d: Path, *names):
    for n in names:
        (d / n).write_bytes(b"PK\x03\x04")


def test_thin_aggregator_is_not_counted_as_a_module(tmp_path):
    """The 1918-byte, zero-class aggregator must not make a directory look assembled.

    This is the same defect #1880 fixed on the loader side; counting it here would
    let a 1-jar directory pass for a full closure.
    """
    _touch(tmp_path, "org.tweetyproject.tweety-full-1.31.jar")
    assert ta.count_module_jars(tmp_path) == 0
    assert ta.is_already_assembled(tmp_path) is False


def test_fat_jar_alone_counts_as_assembled(tmp_path):
    _touch(tmp_path, "org.tweetyproject.tweety-full-1.29-with-dependencies.jar")
    assert ta.is_already_assembled(tmp_path) is True


def test_partial_directory_is_not_assembled(tmp_path):
    _touch(tmp_path, *[f"org.tweetyproject.arg.m{i}-1.31.jar" for i in range(5)])
    assert ta.count_module_jars(tmp_path) == 5
    assert ta.is_already_assembled(tmp_path) is False


def test_full_directory_is_assembled(tmp_path):
    _touch(
        tmp_path,
        "org.tweetyproject.tweety-full-1.31.jar",
        *[f"org.tweetyproject.arg.m{i}-1.31.jar" for i in range(ta.MIN_EXPECTED_JARS)],
    )
    assert ta.is_already_assembled(tmp_path) is True


def test_missing_directory_is_not_assembled(tmp_path):
    assert ta.is_already_assembled(tmp_path / "nope") is False


# --------------------------------------------------------------- failure is loud


def test_absent_maven_names_the_cause(tmp_path, monkeypatch):
    monkeypatch.setattr(ta, "maven_executable", lambda: None)
    with pytest.raises(ta.AssemblyError, match="Maven introuvable"):
        ta.assemble("1.31", tmp_path)


def test_maven_failure_reports_the_1_28_trap(tmp_path, monkeypatch):
    """The most likely cause of a resolution failure is an unbuildable version.

    1.26 and 1.28 publish the aggregator without its modules, so mvn fails with a
    resolution error that reads like a network problem. Naming the trap in the
    message is what stops the next reader from retrying the run.
    """
    monkeypatch.setattr(ta, "maven_executable", lambda: "mvn")
    monkeypatch.setattr(
        ta.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", "Could not resolve"),
    )
    with pytest.raises(ta.AssemblyError, match="1.26 et 1.28 ne sont PAS"):
        ta.assemble("1.28", tmp_path)


def test_thin_success_is_refused(tmp_path, monkeypatch):
    """A partial classpath starts the JVM and fails every import -- refuse it.

    That shape is exactly what produces a skip storm instead of an error, which is
    the failure #1873 had to build a guard against.
    """
    monkeypatch.setattr(ta, "maven_executable", lambda: "mvn")

    def fake_run(cmd, **kwargs):
        _touch(tmp_path, *[f"org.tweetyproject.arg.m{i}-1.31.jar" for i in range(3)])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(ta.subprocess, "run", fake_run)
    with pytest.raises(ta.AssemblyError, match="moins que le plancher"):
        ta.assemble("1.31", tmp_path)


def test_timeout_is_reported_as_such(tmp_path, monkeypatch):
    monkeypatch.setattr(ta, "maven_executable", lambda: "mvn")

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 900)

    monkeypatch.setattr(ta.subprocess, "run", fake_run)
    with pytest.raises(ta.AssemblyError, match="depassement"):
        ta.assemble("1.31", tmp_path, timeout=900)


def test_successful_assembly_returns_the_module_count(tmp_path, monkeypatch):
    monkeypatch.setattr(ta, "maven_executable", lambda: "mvn")

    def fake_run(cmd, **kwargs):
        _touch(tmp_path, "org.tweetyproject.tweety-full-1.31.jar")
        _touch(
            tmp_path,
            *[f"org.tweetyproject.arg.m{i}-1.31.jar" for i in range(60)],
        )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(ta.subprocess, "run", fake_run)
    assert ta.assemble("1.31", tmp_path) == 60


def test_prepend_group_id_is_passed_to_maven(tmp_path, monkeypatch):
    """Load-bearing flag: without it same-named artifacts across Tweety groups
    overwrite each other and the classpath silently loses modules."""
    seen = {}
    monkeypatch.setattr(ta, "maven_executable", lambda: "mvn")

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        _touch(tmp_path, *[f"org.tweetyproject.arg.m{i}-1.31.jar" for i in range(60)])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(ta.subprocess, "run", fake_run)
    ta.assemble("1.31", tmp_path)
    assert "-Dmdep.prependGroupId=true" in seen["cmd"]
