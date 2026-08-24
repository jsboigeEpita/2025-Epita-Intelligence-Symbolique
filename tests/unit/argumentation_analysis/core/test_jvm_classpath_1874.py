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

from argumentation_analysis.core.jvm_setup import _build_tweety_classpath


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


# --------------------------------------------------------------------------- #1884
# Consolidation of po-2025's PR #1884. Its `test_download_tweety_jars_accepts_
# assembly_mode` had the right intent -- the gate must accept an assembled directory
# without touching the network -- but its fixture laid down only 2 jars, which is
# also what a *failed* assembly leaves behind. The intent is kept here with a fixture
# that clears a real floor, and the case its predicate could not distinguish is added
# as its own test.


def _assembled(tmp_path: Path, count: int = 60):
    """A directory that looks like a completed `dependency:copy-dependencies` run."""
    _mkjars(tmp_path, *[f"org.tweetyproject.arg.m{i}-1.31.jar" for i in range(count)])
    return tmp_path


def test_download_accepts_a_real_assembly_without_touching_the_network(
    tmp_path, monkeypatch
):
    """Assembly mode has no `-with-dependencies` jar, so the gate must not chase it.

    Born-red intent (po-2025, #1884): `requests.head` raises to simulate the dead
    /builds/ URL. If the gate reaches the network at all, this reddens.
    """
    import requests

    from argumentation_analysis.core.jvm_setup import download_tweety_jars

    _assembled(tmp_path)

    def _dead(*args, **kwargs):
        raise AssertionError("the gate must not reach the network on an assembled dir")

    monkeypatch.setattr(requests, "head", _dead)
    assert download_tweety_jars(version="1.31", target_dir=tmp_path) is True


def test_download_refuses_a_directory_holding_only_the_thin_aggregator(
    tmp_path, monkeypatch
):
    """The case a bare `glob("*.jar")` predicate cannot see (#1884 review).

    The Maven thin aggregator is a real .jar carrying zero classes. Accepting it
    returns True on a classpath that starts a JVM and then fails every Tweety
    import -- the silent skip shape, not an error. Measured on #1884's branch:
    `download_tweety_jars` returned True and the classpath held 1 useless entry.

    Degenerate substitution: replace the body of `is_already_assembled` with
    `bool(list(d.glob("*.jar")))` and this test is the one that reddens.
    """
    from argumentation_analysis.core import tweety_assembly
    from argumentation_analysis.core.jvm_setup import download_tweety_jars

    _mkjars(tmp_path, "org.tweetyproject.tweety-full-1.31.jar")
    monkeypatch.setattr(tweety_assembly, "maven_executable", lambda: None)
    assert download_tweety_jars(version="1.31", target_dir=tmp_path) is False
