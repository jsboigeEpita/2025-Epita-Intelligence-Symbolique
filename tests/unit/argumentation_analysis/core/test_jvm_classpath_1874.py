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

import zipfile

from pathlib import Path

import pytest

from argumentation_analysis.core.jvm_setup import _build_tweety_classpath

# These five tests need neither a JVM nor a jar on disk, but without this marker the
# session guard (`tests/conftest.py`) skips everything it did not start a JVM for --
# so the guards written for #1874 were skipped in CI *during* the very skip storm they
# exist to diagnose. Measured on run 32765607500: all of them SKIPPED.
pytestmark = pytest.mark.no_jvm_session


def _mkjars(tmp_path: Path, *names: str, loadable: bool = True):
    """Real zips, because the loader now selects on content rather than on name.

    A jar carrying the fat name but no Tweety class must not preempt the assembly
    next to it, so a fixture of empty files can no longer stand in for a usable fat
    jar -- and that is the point: `.touch()` produced exactly the shape (fat name,
    zero class) that a truncated download leaves behind.
    """
    for name in names:
        path = tmp_path / name
        if loadable:
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("org/tweetyproject/logics/pl/syntax/Proposition.class", b"x")
        else:
            path.touch()
    return tmp_path


def test_fat_jars_at_the_configured_version_yield_one_jar(tmp_path, monkeypatch):
    """A fat layout yields exactly the jar of the CONFIGURED version (#2367).

    This test used to assert "the latest cached version must be preferred", which
    was the alphabetical fallback in disguise: with nothing carrying the
    configured version the selector served ``sorted()[-1]``. #2367 retires that
    fallback (a version disagreement now refuses, see
    ``test_version_disagreement_refuses_instead_of_reducing_silently``), so the
    fixture is made coherent instead -- the version is pinned to the one on disk,
    and the shape property (one jar for a fat layout) is what gets measured.
    """
    import argumentation_analysis.core.jvm_setup as js

    _mkjars(
        tmp_path,
        "org.tweetyproject.tweety-full-1.28-with-dependencies.jar",
        "org.tweetyproject.tweety-full-1.29-with-dependencies.jar",
    )
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.29")
    cp = _build_tweety_classpath(tmp_path)
    assert len(cp) == 1, f"fat layout must yield a single jar, got {len(cp)}: {cp}"
    assert "1.29" in cp[0], "the configured version must be the one served"


def test_maven_layout_loads_all_jars_including_thin_aggregator(tmp_path, monkeypatch):
    # A copy-dependencies assembly: module jars + the 0-class thin aggregator.
    # The thin jar is named tweety-full but MUST NOT preempt the real module jars.
    # The version is pinned to the fixture's own (#2367): the property under test is
    # preemption, not version selection, and leaving it at the default made the
    # selector refuse before reaching it -- the refusal is covered by its own test.
    import argumentation_analysis.core.jvm_setup as js

    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.29")
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
    import requests

    from argumentation_analysis.core import tweety_assembly
    from argumentation_analysis.core.jvm_setup import download_tweety_jars

    _mkjars(tmp_path, "org.tweetyproject.tweety-full-1.31.jar")
    monkeypatch.setattr(tweety_assembly, "maven_executable", lambda: None)

    # Without this the test really does hit tweetyproject.org: a unit verdict that
    # depends on an external host, and a 10s timeout on an egress-blocked runner.
    # Its sibling above already guards the network with a raising `_dead`; here the
    # legacy branch must be REACHED, so it gets a canned 404 rather than a refusal.
    class _Gone:
        status_code = 404

    monkeypatch.setattr(requests, "head", lambda *a, **k: _Gone())
    assert download_tweety_jars(version="1.31", target_dir=tmp_path) is False


# --------------------------------------------------------------------------- #1880 review
# The name-only fast path survived #1880: a jar carrying the fat name but no class
# still preempted the module jars next to it. That layer *decides* the classpath, so
# whatever it gets wrong the JVM then boots on -- and the provisioning layer lets a
# truncated download through (it only warns on an inconsistent size).


def test_a_zero_byte_fat_jar_does_not_preempt_the_assembly(tmp_path, monkeypatch):
    import argumentation_analysis.core.jvm_setup as js

    # #2367: pin the version to the fixture's so the property under test is the
    # decoy's non-preemption, not version selection (which has its own test).
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.29")
    _mkjars(
        tmp_path,
        *[f"org.tweetyproject.arg.m{i}-1.29.jar" for i in range(62)],
    )
    (tmp_path / "org.tweetyproject.tweety-full-1.29-with-dependencies.jar").touch()
    cp = _build_tweety_classpath(tmp_path)
    assert len(cp) == 62, (
        "a 0-byte fat jar must not preempt 62 real module jars, and must not ride "
        "along on the fallback either -- it is unusable. "
        f"on an empty classpath. got {len(cp)}: {[Path(p).name for p in cp]}"
    )


def test_a_truncated_fat_jar_does_not_preempt_the_assembly(tmp_path, monkeypatch):
    """1 KB of a 54 MB download: a valid prefix, not a valid zip."""
    import argumentation_analysis.core.jvm_setup as js

    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.29")  # #2367, cf. above
    _mkjars(tmp_path, *[f"org.tweetyproject.arg.m{i}-1.29.jar" for i in range(62)])
    (tmp_path / "org.tweetyproject.tweety-full-1.29-with-dependencies.jar").write_bytes(
        b"PK\x03\x04" + b"\x00" * 1020
    )
    cp = _build_tweety_classpath(tmp_path)
    assert len(cp) == 62, f"truncated fat jar preempted the assembly: {len(cp)} entries"


def test_a_fat_jar_holding_no_tweety_class_does_not_preempt(tmp_path, monkeypatch):
    """A perfectly valid zip of the wrong content -- the shape a name check cannot see."""
    import argumentation_analysis.core.jvm_setup as js

    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.29")  # #2367, cf. above
    _mkjars(tmp_path, *[f"org.tweetyproject.arg.m{i}-1.29.jar" for i in range(62)])
    decoy = tmp_path / "org.tweetyproject.tweety-full-1.29-with-dependencies.jar"
    with zipfile.ZipFile(decoy, "w") as z:
        z.writestr("ch/qos/logback/classic/Logger.class", b"x")
    cp = _build_tweety_classpath(tmp_path)
    assert len(cp) == 62, f"a 0-Tweety-class fat jar preempted: {len(cp)} entries"


def test_the_configured_version_wins_over_alphabetical_order(tmp_path, monkeypatch):
    """`sorted()[-1]` is not version order: "1.9" sorts after "1.10". Two cached fat
    jars is a real state -- libs/tweety holds 1.28 and 1.29 on this machine -- and
    silently loading a version other than the configured one is the wrong neighbour
    for a per-module pinning feature."""
    import argumentation_analysis.core.jvm_setup as js

    _mkjars(
        tmp_path,
        "org.tweetyproject.tweety-full-1.28-with-dependencies.jar",
        "org.tweetyproject.tweety-full-1.29-with-dependencies.jar",
    )
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.28")
    cp = _build_tweety_classpath(tmp_path)
    assert len(cp) == 1 and "1.28" in cp[0], f"configured version ignored: {cp}"


# --------------------------------------------------------------------------- #2246
# Piste A (arbitrated): the legacy 1.28 layout deposits ~34 MODULE fat jars
# (each module + its dependencies) that ALL carry ``-1.28-`` in their name. The
# single-jar branch returned only the alphabetically-first (``action``), whose
# transitive closure carries logics.pl and arg.dung but NOT arg.aspic -- the
# JVM booted, then the first ASPIC JClass raised TypeError. When several uber
# jars share the version tag, they all go on the classpath; and any reduction
# to one jar among several must be logged -- the silence was half the bug.


def test_multiple_version_matching_fat_jars_all_go_on_the_classpath(
    tmp_path, monkeypatch
):
    import argumentation_analysis.core.jvm_setup as js

    _mkjars(
        tmp_path,
        "org.tweetyproject.action-1.28-with-dependencies.jar",
        "org.tweetyproject.arg.aspic-1.28-with-dependencies.jar",
        "org.tweetyproject.logics.pl-1.28-with-dependencies.jar",
    )
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.28")
    cp = _build_tweety_classpath(tmp_path)
    names = [Path(p).name for p in cp]
    assert len(cp) == 3, (
        "#2246: 3 version-matching module fat jars must all load -- returning "
        f"only the first amputates the rest. got {names}"
    )
    assert any("arg.aspic" in n for n in names), "the aspic module was amputated"


def test_version_disagreement_refuses_instead_of_reducing_silently(
    tmp_path, monkeypatch
):
    """#2367 supersedes the silent-reduction contract this test used to pin.

    #2246's second half was "the reduction to one jar must be logged, never
    silent": a WARNING in a 40-line JVM startup. Measured, nobody reads it, and
    the reduction it announced was the alphabetical fallback -- a version the
    code was not written for. #2278 removed the ``JVM_TWEETY_VERSION`` pin that
    hid this, so the selector is the last place that could still serve it. It now
    refuses, and both versions travel on the exception.
    """
    import argumentation_analysis.core.jvm_setup as js

    _mkjars(
        tmp_path,
        "org.tweetyproject.tweety-full-1.28-with-dependencies.jar",
        "org.tweetyproject.tweety-full-1.29-with-dependencies.jar",
    )
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.31")
    with pytest.raises(js.TweetyClasspathVersionError) as excinfo:
        _build_tweety_classpath(tmp_path)

    assert excinfo.value.configured == "1.31"
    assert set(excinfo.value.present) == {"1.28", "1.29"}, (
        "the refusal must name EVERY version the tree holds, not just the last "
        f"one it would have served: {excinfo.value.present}"
    )
    said = str(excinfo.value)
    assert "1.31" in said and "1.29" in said and "1.28" in said


# --------------------------------------------------------------------------- #2367
# Two filters, each correct alone, applied in the wrong ORDER -- and the order was
# the defect. Measured on main `772ce4a1`, env `projet-is-roo-new`:
#
#   libs/tweety: 74 jars. The 49 that carry Tweety classes are named
#   ``<module>-1.31.jar`` (version FINAL, no fat suffix); the jar that carries the
#   aggregation name ``org.tweetyproject.tweety-full-1.31.jar`` holds 1947 bytes and
#   ZERO Tweety classes. On a machine where the older provisioning had also left
#   ``…tweety-full-1.28-with-dependencies.jar`` and ``…-1.29-…`` (what
#   ``download_tweety_jars`` fetches), the nominal pre-filter kept only those two,
#   so the content check never saw the 49, ``matching`` came out empty and the
#   selector served the 1.29 fat jar -- ONE entry, for a tree holding 49 jars of
#   the configured version.
#
# Two independent spellings of the same failure, and both must be pinned:
#   (a) membership decided by NAME before content (#2367 DoD 1)
#   (b) the version tag spelled ``-{v}-``, a TRAILING dash, which cannot match a
#       version-final name (#2367, found while measuring -- the issue does not
#       mention it, and a fix for (a) alone leaves the selector still unable to
#       recognise the configured version on the module layout)


def _module_layout(tmp_path: Path, version: str, count: int = 49) -> Path:
    """The measured shape: ``count`` module jars + the 0-class thin aggregator."""
    _mkjars(
        tmp_path, *[f"org.tweetyproject.arg.m{i}-{version}.jar" for i in range(count)]
    )
    _mkjars(tmp_path, f"org.tweetyproject.tweety-full-{version}.jar", loadable=False)
    return tmp_path


def test_the_fat_layout_does_not_hide_the_module_layout(tmp_path, monkeypatch):
    """(a) Born-red: the 49 module jars of the configured version are selected.

    Pre-fix this returned a single entry -- the 1.29 fat jar -- because the name
    filter kept only the two fat jars and the content check never saw the 49.
    """
    import argumentation_analysis.core.jvm_setup as js

    _mkjars(
        tmp_path,
        "org.tweetyproject.tweety-full-1.28-with-dependencies.jar",
        "org.tweetyproject.tweety-full-1.29-with-dependencies.jar",
    )
    # A third-party jar carries NO Tweety class (`loadable=False`) -- `_mkjars` writes a
    # Tweety class into every name it is given, so building it loadable would make it a
    # Tweety jar of version 3.2 and it would be excluded as another version. Measured
    # here first: that fixture bug is what reddened this test, not the selector.
    _mkjars(tmp_path, "commons-math3-3.2.jar", loadable=False)
    _module_layout(tmp_path, "1.31")
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.31")

    cp = _build_tweety_classpath(tmp_path)
    names = sorted(Path(p).name for p in cp)
    modules = [n for n in names if n.startswith("org.tweetyproject.arg.m")]

    assert len(modules) == 49, (
        "every class-carrying jar of the configured version belongs on the "
        f"classpath -- asserted as a LIST, not a count. got {len(modules)}: {names}"
    )
    assert not [n for n in names if "1.28" in n or "1.29" in n], (
        "a class-carrying jar of ANOTHER version must not sit on the same "
        f"classpath (it shadows the configured one): {names}"
    )
    assert "commons-math3-3.2.jar" in names, (
        "the third-party dependencies are resolved from separate jars in this "
        f"layout and must stay: {names}"
    )


def test_the_version_tag_is_read_in_both_spellings(tmp_path):
    """(b) Born-red: ``<module>-1.31.jar`` carries the version as much as ``-1.31-``.

    ``f"-{v}-" in name`` -- the spelling the selector used -- matches only the
    interior form. Measured on the 49-jar module layout: it matched nothing, so
    even a selector that reached the content check could not recognise the
    configured version there.
    """
    from argumentation_analysis.core import tweety_assembly

    # Born-red premise, asserted: the spelling the selector used CANNOT match the
    # module layout. If this ever stops holding, the defect's premise is broken and
    # the rest of this test measures nothing.
    assert f"-{'1.31'}-" not in "org.tweetyproject.arg.dung-1.31.jar", (
        "born-red premise broken: the old trailing-dash spelling must miss the "
        "version-final name"
    )

    assert tweety_assembly.versions_in_name("org.tweetyproject.arg.dung-1.31.jar") == {
        "1.31"
    }, "version-final spelling (module layout) must be read"
    assert tweety_assembly.versions_in_name(
        "org.tweetyproject.tweety-full-1.31-with-dependencies.jar"
    ) == {"1.31"}, "interior spelling (fat assembly) must be read"
    assert tweety_assembly.versions_in_name("org.tweetyproject.arg.dung-1.29.jar") == {
        "1.29"
    }, "a non-configured version must still be recognised as SOME version"


def test_the_module_layout_is_the_healthy_case_the_guard_can_render(
    tmp_path, monkeypatch
):
    """Non-vacuity (DoD 5): the same code path renders green on a good layout.

    A guard that only ever reddens discriminates nothing. Here the configured
    version IS present, so the selector returns a classpath instead of refusing --
    measured by the same call, on a layout differing only in the version tag.
    """
    import argumentation_analysis.core.jvm_setup as js

    _module_layout(tmp_path, "1.31")
    monkeypatch.setattr(js.settings.jvm, "tweety_version", "1.31")
    cp = _build_tweety_classpath(tmp_path)
    # 49 module jars + the 0-class thin aggregator: it makes no fat-jar claim, so it
    # stays on the classpath -- the behaviour #1874 pins, asserted in
    # `test_maven_layout_loads_all_jars_including_thin_aggregator`. Measured 50 here
    # after expecting 49: the count is not the assertion, the list is.
    names = sorted(Path(p).name for p in cp)
    assert len([n for n in names if n.startswith("org.tweetyproject.arg.m")]) == 49
    assert "org.tweetyproject.tweety-full-1.31.jar" in names


def test_initialize_jvm_refuses_and_names_both_versions(tmp_path, monkeypatch, caplog):
    """DoD 3 at the caller: the refusal must reach ``initialize_jvm``, not just the selector.

    A selector that raises into an unguarded call is a crash, not a refusal; and a
    refusal that only logs is a WARNING by another name. This pins the three
    properties together: it returns False (no JVM on an arbitrary version), it says
    critical, and the message names BOTH versions.

    Stubbed at the smallest seam that reaches the classpath decision: jpype (no JVM
    in a unit test), the download, the JDK lookup, and the selector itself.
    """
    import logging

    import argumentation_analysis.core.jvm_setup as js

    class _NoJVM:
        @staticmethod
        def isJVMStarted():
            return False

    def _raises(_dir):
        raise js.TweetyClasspathVersionError("1.31", ["1.29"])

    monkeypatch.setattr(js, "jpype", _NoJVM)
    monkeypatch.setattr(js, "_JVM_WAS_SHUTDOWN", False)
    monkeypatch.setattr(js, "download_tweety_jars", lambda **kwargs: True)
    monkeypatch.setattr(js, "find_valid_java_home", lambda: str(tmp_path))
    monkeypatch.setattr(js, "_build_tweety_classpath", _raises)

    with caplog.at_level(logging.CRITICAL, logger="Orchestration.JPype.Setup"):
        started = js.initialize_jvm()

    assert started is False, (
        "no JVM may start on a version the code was not written for — returning "
        "True here is the silent-arbitrary boot #2367 removes"
    )
    said = caplog.text
    assert "refusé" in said, f"the refusal must be logged as such: {said!r}"
    assert (
        "1.31" in said and "1.29" in said
    ), f"the refusal must name BOTH versions (configured and present): {said!r}"


def test_the_real_tree_serves_the_configured_version():
    """DoD 2, corrected by measurement: the version ON the classpath, not its count.

    DoD 2 asked for "the 50 jars ``-1.31-``". Measured on this tree: **49** carry
    Tweety classes, and the 50th -- ``org.tweetyproject.tweety-full-1.31.jar``,
    1947 bytes -- carries **zero**. Asserting 50 would put the #1874 thin
    aggregator back on the classpath and pin the defect the content check exists to
    catch. The assertion is therefore on the LIST: every class-carrying ``-1.31-``
    jar of the tree, and no class-carrying jar of another version.

    ``libs/`` is machine-local and absent in CI; when it is absent this test says so
    instead of passing quietly, because a skip that reads as a green is the shape
    this file's whole history is about.
    """
    import argumentation_analysis.core.jvm_setup as js
    from argumentation_analysis.core import tweety_assembly

    repo = Path(__file__).resolve().parents[4]
    tweety_dir = repo / "libs" / "tweety"
    if not tweety_dir.is_dir():
        pytest.skip(
            f"libs/tweety absent on this machine ({tweety_dir}) — real-tree check "
            "unmeasurable; the synthetic layout carries the discriminating power in CI"
        )

    configured = js.settings.jvm.tweety_version
    expected = sorted(
        jar.name
        for jar in sorted(tweety_dir.glob("*.jar"))
        if tweety_assembly.carries_tweety_classes(jar)
        and configured in tweety_assembly.versions_in_name(jar.name)
    )
    assert expected, (
        "the tree holds no class-carrying jar of the configured version "
        f"v{configured} — the selector would refuse here"
    )

    names = sorted(Path(p).name for p in _build_tweety_classpath(tweety_dir))
    missing = [n for n in expected if n not in names]
    assert not missing, (
        "the configured version's jars are not all on the classpath — the defect "
        f"#2367 measured. missing {len(missing)} of {len(expected)}: {missing[:5]}"
    )
