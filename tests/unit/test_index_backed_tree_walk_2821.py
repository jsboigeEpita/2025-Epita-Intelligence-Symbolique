"""#2821 — a census population comes from the git index, not the filesystem.

The root-walking guards built their population with a filesystem walk
(``iter_files``), so a seat's gitignored local files entered the census: the
#2720 config census collected 31 cases on a seat holding ``.playwright-mcp/``
page snapshots and 24 in a clean worktree of the same commit — the gate never
ran those 7. Worse in the other direction: a config naming a class that
exists only in a seat-local untracked file passed the census on that seat and
failed on CI.

These witnesses hold after the index-backed population:

- a gitignored ``.yml`` naming a class and a gitignored ``.py`` defining one,
  planted in the real checkout (the ``.playwright-mcp/`` class the issue
  measured), cannot enter the #2720 census population;
- the same immunity, replayed on a temporary checkout whose tracked content
  is known — the verdict there is exact, not merely unchanged;
- ``iter_tracked_files`` fails LOUD when git is unavailable — it never
  silently falls back to walking the filesystem, which would put the census
  back on the seat-local population the index exists to exclude.
"""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _make_repo(tmp_path):
    """A tiny checkout: one good config naming a class that exists, one
    tracked vendored tree (must stay excluded), and a gitignored ``local/``."""
    (tmp_path / ".gitignore").write_text("local/\n", encoding="utf-8")
    (tmp_path / "good.yaml").write_text("class: RealClass\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("class RealClass:\n    pass\n", encoding="utf-8")
    vendored = tmp_path / "libs"
    vendored.mkdir()
    (vendored / "vendored.py").write_text("class VendoredClass:\n    pass\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(
        tmp_path,
        "-c",
        "user.email=census@example.invalid",
        "-c",
        "user.name=census",
        "commit",
        "-qm",
        "2821 witness fixtures",
    )


class TestConfigCensusIgnoresGitignoredSeatFiles:
    """Plants the measured class of gitignored files (a ``.playwright-mcp``
    page snapshot + a stray ``.py``) in the real checkout and requires the
    #2720 census not to see them."""

    PROBE_DIR = ROOT / ".playwright-mcp"

    def setup_method(self):
        from tests.unit.argumentation_analysis.config import (
            test_config_classes_resolve_2720 as census,
        )

        self._census = census
        self.probe_yaml = self.PROBE_DIR / "2821_probe.yml"
        self.probe_py = self.PROBE_DIR / "ghost_2821.py"
        self._existed = self.PROBE_DIR.exists()
        self.PROBE_DIR.mkdir(exist_ok=True)
        ignored = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "-q", str(self.probe_yaml)]
        )
        assert ignored.returncode == 0, (
            f"{self.probe_yaml.relative_to(ROOT)} is not gitignored on this seat; "
            "the witness needs a path the index refuses"
        )
        self.probe_yaml.write_text("class: Ghost2821\n", encoding="utf-8")
        self.probe_py.write_text(
            "class Ghost2821Defined:\n    pass\n", encoding="utf-8"
        )

    def teardown_method(self):
        self.probe_yaml.unlink(missing_ok=True)
        self.probe_py.unlink(missing_ok=True)
        if not self._existed:
            # The directory the issue measured was absent here; leave the
            # checkout as found.
            try:
                self.PROBE_DIR.rmdir()
            except OSError:
                pass

    def test_gitignored_yaml_stays_out_of_the_config_population(self):
        population = self._census._yaml_configs()
        names = {p.name for p in population}
        assert "2821_probe.yml" not in names, (
            "a gitignored seat-local file entered the config census: the seat "
            "population diverges from CI's"
        )

    def test_gitignored_py_stays_out_of_the_defined_classes(self):
        defined = self._census._defined_classes()
        assert "Ghost2821Defined" not in defined, (
            "a class defined only in a gitignored seat-local file counts as "
            "existing: a config naming it passes here and fails on CI"
        )


class TestCensusVerdictOnATemporaryCheckout:
    """The DoD's temporary-checkout replay: with tracked content known, the
    census verdict is exact — the ignored files cannot sway either side, and
    the tracked vendored prefix stays excluded."""

    @pytest.fixture()
    def repo(self, tmp_path):
        _make_repo(tmp_path)
        # The ignored files: a config naming a class that exists nowhere
        # tracked, and a .py defining a class only it defines.
        local = tmp_path / "local"
        local.mkdir()
        (local / "bad.yml").write_text("class: MissingEverywhere\n", encoding="utf-8")
        (local / "ghost.py").write_text("class LocalGhost:\n    pass\n")
        return tmp_path

    def test_population_is_exactly_the_tracked_configs(self, repo):
        from tests.unit.argumentation_analysis.config import (
            test_config_classes_resolve_2720 as census,
        )

        assert [p.name for p in census._yaml_configs(repo)] == ["good.yaml"]

    def test_defined_classes_exclude_ignored_and_vendored(self, repo):
        from tests.unit.argumentation_analysis.config import (
            test_config_classes_resolve_2720 as census,
        )

        defined = census._defined_classes(repo)
        assert defined == {
            "RealClass"
        }, f"expected exactly the tracked, non-vendored classes, got {sorted(defined)}"


class TestIterTrackedFiles:
    def test_yields_the_tracked_pattern_and_nothing_else(self, tmp_path):
        from tests.support.tree_walk import iter_tracked_files

        _make_repo(tmp_path)
        (tmp_path / "untracked.py").write_text("x = 1\n", encoding="utf-8")
        got = [p.name for p in iter_tracked_files(tmp_path, "*.py")]
        # Both tracked .py files — the vendored one too: with the default
        # skip_prefixes nothing excludes it; only the untracked stray is out.
        assert sorted(got) == ["real.py", "vendored.py"], got

    def test_git_unavailable_fails_loud_not_silent(self, tmp_path):
        from tests.support.tree_walk import iter_tracked_files

        (tmp_path / "stray.py").write_text("x = 1\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="git"):
            list(iter_tracked_files(tmp_path, "*.py"))

    def test_tracked_skip_prefixes_still_apply(self, tmp_path):
        from tests.support.tree_walk import iter_tracked_files

        _make_repo(tmp_path)
        got = [
            p.name
            for p in iter_tracked_files(tmp_path, "*.py", skip_prefixes=("libs",))
        ]
        assert got == ["real.py"], got

    def test_tracked_non_ascii_path_is_returned_readable(self, tmp_path):
        """#2833 review: without ``-z``, ``git ls-files`` quotes non-ASCII
        paths (``core.quotepath`` defaults on) and octal-escapes their bytes,
        so ``root / rel`` builds a path that does not exist — the file left
        the population without a trace (measured 930 ``.md`` on main's index
        instead of 932). A tracked accented path must come back as itself,
        and every returned path must exist on disk."""
        from tests.support.tree_walk import iter_tracked_files

        _make_repo(tmp_path)
        accented = tmp_path / "données_é_2821.py"
        accented.write_text("x = 1\n", encoding="utf-8")
        _git(tmp_path, "add", "-A")
        _git(
            tmp_path,
            "-c",
            "user.email=census@example.invalid",
            "-c",
            "user.name=census",
            "commit",
            "-qm",
            "accented path fixture",
        )
        # Reproduce git's DEFAULT on any seat: this seat carries
        # ``core.quotepath=off``, CI does not — without this line the witness
        # passes on a quiet seat and misses the defect entirely.
        _git(tmp_path, "config", "core.quotepath", "true")
        got = list(iter_tracked_files(tmp_path, "*.py"))
        names = [p.name for p in got]
        assert (
            accented.name in names
        ), f"the tracked accented path left the population: {sorted(names)}"
        assert all(p.exists() for p in got), (
            "a returned path does not exist on disk — the population holds a "
            "quoted mangle, which census readers silently skip"
        )
