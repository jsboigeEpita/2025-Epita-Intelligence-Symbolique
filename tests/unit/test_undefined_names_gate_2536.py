"""#2536: an undefined name fails a gate that can fail.

The CI lint step runs flake8 with ``continue-on-error: true``, so its green
says nothing about undefined names. This test is the gate for that one code:
it runs flake8's F821 check, with the repository's configuration, over every
tracked root that holds Python files, and expects no site **in a tracked
file**.

Its control is the blind spot #2536 measured. While ``.flake8`` listed F821 in
``ignore``, ``flake8 --select=F821`` printed nothing for a file with an
undefined name. The control runs the same command on such a file and expects
the site.

#2873: the sites are kept only when the file they name is in the index. flake8
walks the roots on disk, so an untracked tree under a tracked root reached the
verdict — measured on a seat holding a 3.8 GB local Octave install (0 files in
the index) under ``libs/``: hundreds of F821 sites CI can never reproduce, and
a gate that says "no tracked root has an undefined name" while measuring what
the seat happened to download. Filtering the REPORT against ``git ls-files``
rather than changing what flake8 walks keeps the configuration's exclusions
intact — passing explicit file paths instead was measured to bypass them and
resurrect 12 sites in archived/student trees that the config excludes.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOUND = 300


def _git_ls_files(pattern):
    listed = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout.splitlines()
    return [path for path in listed if path.strip()]


def _tracked_python_roots():
    roots = sorted({path.split("/", 1)[0] for path in _git_ls_files("*.py")})
    # Non-vacuity: a silent index (wrong cwd, git missing, an empty checkout)
    # would otherwise make the gate pass by measuring nothing.
    assert "argumentation_analysis" in roots and "tests" in roots, roots
    return roots


def _tracked_python_files():
    files = _git_ls_files("*.py")
    assert "argumentation_analysis/core/jvm_setup.py" in files, files[:10]
    return set(files)


def _f821(*paths):
    return subprocess.run(
        [sys.executable, "-m", "flake8", "--select=F821", *paths],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=BOUND,
    )


def _site_path(line):
    """The file a flake8 line names, in the index's spelling (posix, relative)."""
    return line.split(":", 1)[0].replace("\\", "/")


def _tracked_sites(result):
    """The reported sites whose file is in the index — the gate's population."""
    tracked = _tracked_python_files()
    return [
        line
        for line in result.stdout.splitlines()
        if line.strip() and _site_path(line) in tracked
    ]


def test_the_check_sees_an_undefined_name(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text("def f():\n    return undefined_name_2536\n", encoding="utf-8")
    result = _f821(str(probe))
    assert "F821 undefined name 'undefined_name_2536'" in result.stdout, (
        result.stdout + result.stderr
    )


def test_no_tracked_root_has_an_undefined_name():
    result = _f821(*_tracked_python_roots())
    offenders = _tracked_sites(result)
    assert not offenders, "\n".join(offenders)
    assert result.returncode in (
        0,
        1,
    ), f"flake8 did not run: rc={result.returncode}\n{result.stderr}"


def test_an_untracked_file_under_a_tracked_root_is_not_counted(tmp_path):
    """The #2873 witness: the verdict follows the index, not the disk.

    The probe is a real, untracked file inside the tracked ``tests`` root
    carrying the same undefined name the control uses. flake8 walking the root
    DOES report it (asserted below — otherwise this witness would pass for the
    wrong reason), and the gate's population drops it because no index entry
    names it. As a control of the control, a TRACKED file with the same site
    stays counted (asserted by the sibling test below — without it, a filter
    that dropped everything would pass this witness).
    """
    probe = REPO / "tests" / "_untracked_probe_2873.py"
    try:
        probe.write_text("def f():\n    return undefined_name_2873\n", encoding="utf-8")
        assert probe.is_file()
        assert probe.relative_to(REPO).as_posix() not in _tracked_python_files()

        on_disk = _f821(str(probe))
        assert (
            "undefined_name_2873" in on_disk.stdout
        ), "the probe must be a site flake8 sees when pointed at it"
        walked = _f821("tests")
        assert (
            "undefined_name_2873" in walked.stdout
        ), "flake8 walking the root must see the probe — the disk walk is real"
        assert "undefined_name_2873" not in "\n".join(_tracked_sites(walked))
    finally:
        probe.unlink()
    assert not probe.exists()


def test_a_tracked_file_with_the_same_site_stays_counted(tmp_path, monkeypatch):
    """The control of the control the #2873 witness promises: the population
    follows the index, so once the file is tracked the SAME site is kept.

    Hermetic: the probe is staged into a throwaway index (GIT_INDEX_FILE),
    seeded from HEAD — the checkout's real index is never written. The
    helpers inherit the environment, so the gate reads the same index this
    test staged into.
    """
    probe = REPO / "tests" / "_tracked_probe_2873.py"
    probe.write_text("def f():\n    return undefined_name_2873\n", encoding="utf-8")
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "index-2873"))
    subprocess.run(
        ["git", "read-tree", "HEAD"],
        cwd=REPO,
        check=True,
        timeout=120,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "--", "tests/_tracked_probe_2873.py"],
        cwd=REPO,
        check=True,
        timeout=120,
        capture_output=True,
    )
    try:
        assert (
            "tests/_tracked_probe_2873.py" in _tracked_python_files()
        ), "the probe must be in the index the gate reads"
        walked = _f821("tests")
        assert (
            "undefined_name_2873" in walked.stdout
        ), "the probe is a real site — the walk must see it"
        assert "undefined_name_2873" in "\n".join(
            _tracked_sites(walked)
        ), "a TRACKED file with the same site stays counted"
    finally:
        probe.unlink()
    assert not probe.exists()
