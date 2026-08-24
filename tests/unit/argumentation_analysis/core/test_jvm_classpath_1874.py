"""#1874 (Piège 2): the loader must not be preempted by the thin Tweety aggregator.

``jvm_setup._build_tweety_classpath`` selects the classpath handed to ``startJVM``.
The preemption key used to be ``"full"``, which *also* matched the Maven
``copy-dependencies`` thin aggregator ``org.tweetyproject.tweety-full-1.29.jar``
(1918 bytes, 0 class). A ``copy-dependencies`` layout deposits that thin jar
alongside the ~150 real module jars; the old preemption kept the thin jar and
dropped the module jars — a JVM that "boots" with no Tweety class on its classpath.

These tests pin the fix with synthetic names only (no JVM, no Maven needed): a
fat-jar layout resolves to the latest single jar, a multi-jar assembly loads in
full (harmlessly including the thin aggregator), and an empty directory yields no
classpath. Born-red against the old ``"full"`` predicate: the Maven-layout test
fails on the pre-fix code (kept only the thin jar) and passes post-fix.
"""

from pathlib import Path

import requests

from argumentation_analysis.core.jvm_setup import (
    _build_tweety_classpath,
    download_tweety_jars,
)


def _mkjars(tmp_path: Path, *names: str):
    for name in names:
        (tmp_path / name).touch()
    return tmp_path


def test_fat_jars_resolve_to_latest_single_jar(tmp_path):
    _mkjars(
        tmp_path,
        "org.tweetyproject.tweety-full-1.28-with-dependencies.jar",
        "org.tweetyproject.tweety-full-1.29-with-dependencies.jar",
    )
    cp = _build_tweety_classpath(tmp_path)
    assert len(cp) == 1, f"fat layout must yield a single jar, got {len(cp)}: {cp}"
    assert "1.29" in cp[0], "the latest cached version must be preferred"


def test_maven_layout_loads_all_jars_including_thin_aggregator(tmp_path):
    # A copy-dependencies assembly: module jars + the 0-class thin aggregator.
    # The thin jar is named tweety-full but MUST NOT preempt the real module jars.
    _mkjars(
        tmp_path,
        "org.tweetyproject.tweety-full-1.29.jar",  # thin aggregator, 0 class
        "org.tweetyproject.logics.commons-1.29.jar",
        "org.tweetyproject.logics.pl.parser-1.29.jar",
        "org.tweetyproject.logics.pl.syntax-1.29.jar",
        "org.tweetyproject.logics.fol.syntax-1.29.jar",
    )
    cp = _build_tweety_classpath(tmp_path)
    names = [Path(p).name for p in cp]
    assert len(cp) == 5, f"multi-jar assembly must load in full, got {len(cp)}: {names}"
    assert any(
        "logics.commons-1.29.jar" in n for n in names
    ), "#1874 Piège 1: the `commons` module jar must be present (prependGroupId)"
    assert any(
        n.startswith("org.tweetyproject.tweety-full-1.29.jar") for n in names
    ), "the thin aggregator is on the classpath but must not preempt the rest"


def test_empty_directory_yields_no_classpath(tmp_path):
    assert _build_tweety_classpath(tmp_path) == []


def test_download_tweety_jars_accepts_assembly_mode(tmp_path, monkeypatch):
    """#1874 Piège 3: initialize_jvm gates on download_tweety_jars, which insists on the
    ``-with-dependencies`` fat jar and hits tweetyproject.org/builds/ when absent — a URL
    that is now dead (404). In Maven-assembly mode the fat jar is absent but the module
    jars are present, so the gate must accept them WITHOUT reaching the network.

    Born-red: the ``requests.head`` mock raises (simulating the dead URL), so pre-fix the
    exception propagated to ``download_file`` path and returned False; post-fix the
    assembly branch short-circuits to True before any network call.
    """
    (tmp_path / "org.tweetyproject.arg.bipolar-1.30.jar").touch()
    (tmp_path / "org.tweetyproject.logics.pl-1.31.jar").touch()

    def _dead(*args, **kwargs):
        raise requests.RequestException("404 from /builds/ (removed, #1874)")

    monkeypatch.setattr("argumentation_analysis.core.jvm_setup.requests.head", _dead)
    assert download_tweety_jars(version="1.31", target_dir=tmp_path) is True
