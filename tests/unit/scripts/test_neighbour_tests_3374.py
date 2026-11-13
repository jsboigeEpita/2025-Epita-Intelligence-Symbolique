"""The neighbours of a change are derived, not remembered (#3374).

``docs/guides/MEASUREMENT_DISCIPLINE.md`` §3.2 says a targeted green run is
not its neighbours, and names the instrument as a recipe to follow by hand.
Four gate reds came after green targeted runs anyway — the last one on a
guard the page names for exactly that kind of change. ``neighbour_tests.py``
turns the recipe into a set; these witnesses hold what the set must contain.

Synthetic sources for the selection rules (no git, no disk), the real tree
for the two things only it can say: the gate's paths, and that the guards a
red was already paid for are seen as population guards.
"""

from __future__ import annotations

import re
import subprocess
import sys

import pytest

from scripts.ci import neighbour_tests as nt
from scripts.ci.neighbour_tests import (
    GATE_FILTER,
    Neighbours,
    gate_paths,
    is_population_guard,
    is_test_file,
    pytest_command,
    report,
    select,
    token_for,
)

GATE = ["tests/unit/", "tests/scripts/", "tests/test_named_by_the_gate.py"]

# Guards whose red was paid for after a green targeted run, with the change
# that met them. Each must be seen as a population guard: they name no module
# of the change, so nothing else would bring them into the set.
KNOWN_POPULATION_GUARDS = [
    # #3193 and #3526: a prompt line carrying document text
    "tests/unit/argumentation_analysis/test_unbounded_prompt_census_2908.py",
    # #2937: a README that cites a symbol the change retired
    "tests/unit/argumentation_analysis/agents/core/test_leaf_readme_citations_2669.py",
    "tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py",
    "tests/unit/test_undefined_names_gate_2536.py",
    "tests/unit/test_index_backed_tree_walk_2821.py",
    "tests/scripts/test_env_loader_one_parser_2487.py",
]

_IMPORTER = "from argumentation_analysis.core.reading_window import persona_reading\n"
_WALKER = "for path in ROOT.rglob('*.py'):\n    tree = ast.parse(path.read_text())\n"
_PLAIN = "def test_nothing():\n    assert 1 + 1 == 2\n"


class TestWhatATouchedFileIsCalled:
    def test_a_module_is_called_by_its_stem(self):
        token = token_for("argumentation_analysis/core/reading_window.py")

        assert token.name == "reading_window"
        assert token.word is True
        assert token.qualified == ("core.reading_window", "core/reading_window")

    def test_a_package_init_is_called_by_the_package(self):
        token = token_for("argumentation_analysis/agents/core/context/__init__.py")

        assert token.name == "context"
        assert token.qualified == ("core.context", "core/context")

    def test_any_other_file_is_called_by_its_file_name(self):
        token = token_for(".github/workflows/ci.yml")

        assert token.name == "ci.yml"
        assert token.word is False
        assert token.qualified == ("workflows/ci.yml",)

    def test_a_test_file_is_not_a_name_to_look_for(self):
        assert token_for("tests/unit/core/test_reading_window.py") is None

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("tests/unit/test_a.py", True),
            ("tests/unit/a_test.py", True),
            ("tests/unit/conftest.py", False),
            ("tests/nested_pytest.py", False),
            ("scripts/test_a.py", False),
            ("tests/unit/test_a.md", False),
        ],
    )
    def test_a_test_file_is_what_pytest_collects_under_tests(self, path, expected):
        assert is_test_file(path) is expected


class TestTheSet:
    def test_a_test_that_imports_the_touched_module_is_a_neighbour(self):
        sources = {
            "tests/unit/core/test_importer.py": _IMPORTER,
            "tests/unit/core/test_plain.py": _PLAIN,
        }

        found = select(["argumentation_analysis/core/reading_window.py"], sources, GATE)

        assert found.run_paths() == ["tests/unit/core/test_importer.py"]

    def test_a_guard_that_walks_the_tree_is_a_neighbour_of_every_change(self):
        """The shape of #3526: the census guard names no module of the change,
        and reddened on it. Nothing but "it walks the tree" brings it in."""
        sources = {
            "tests/unit/test_census.py": _WALKER,
            "tests/unit/core/test_plain.py": _PLAIN,
        }

        found = select(["argumentation_analysis/core/reading_window.py"], sources, GATE)

        assert "reading_window" not in sources["tests/unit/test_census.py"]
        assert found.population == ["tests/unit/test_census.py"]
        assert found.run_paths() == ["tests/unit/test_census.py"]

    @pytest.mark.parametrize(
        "call",
        [
            "subprocess.run(['git', 'ls-files'])",
            "ROOT.rglob('*.md')",
            "os.walk(ROOT)",
            "ROOT.glob('*.py')",
            "ROOT.iterdir()",
            "ast.parse(source)",
        ],
    )
    def test_each_way_of_walking_the_tree_is_seen(self, call):
        assert is_population_guard(f"def test_x():\n    {call}\n") is True

    def test_a_test_that_reads_nothing_but_its_inputs_is_not_a_guard(self):
        assert is_population_guard(_IMPORTER + _PLAIN) is False

    def test_a_longer_name_is_another_module(self):
        sources = {
            "tests/unit/test_other.py": "from pkg import reading_window_extra\n",
            "tests/unit/test_dotted.py": "import pkg.core.reading_window as rw\n",
        }

        found = select(["pkg/core/reading_window.py"], sources, GATE)

        assert found.mentions["pkg/core/reading_window.py"] == [
            "tests/unit/test_dotted.py"
        ]

    def test_a_file_is_found_by_its_file_name(self):
        sources = {
            "tests/unit/test_lock.py": "ENV = ROOT / 'environment.yml'\n",
            "tests/unit/test_plain.py": _PLAIN,
        }

        found = select(["environment.yml"], sources, GATE)

        assert found.run_paths() == ["tests/unit/test_lock.py"]

    def test_a_name_that_is_vocabulary_is_narrowed_and_the_set_says_so(self):
        """`utils` in half the suite is not a neighbour relation. The
        narrowing is recorded, never silent: a reader sees how many files the
        bare name reached and which forms were kept."""
        sources = {f"tests/unit/test_{i}.py": "import utils\n" for i in range(5)}
        sources["tests/unit/test_real.py"] = "from pkg.core.utils import helper\n"

        found = select(["pkg/core/utils.py"], sources, GATE, threshold=3)

        assert found.narrowed == {"pkg/core/utils.py": 6}
        assert found.mentions["pkg/core/utils.py"] == ["tests/unit/test_real.py"]
        text = report(found, ["pkg/core/utils.py"], "origin/main")
        assert "narrowed: 6 test files name `utils`" in text
        assert "core.utils or core/utils" in text

    def test_a_name_at_the_threshold_is_kept_whole(self):
        sources = {f"tests/unit/test_{i}.py": "import utils\n" for i in range(3)}

        found = select(["pkg/core/utils.py"], sources, GATE, threshold=3)

        assert found.narrowed == {}
        assert len(found.mentions["pkg/core/utils.py"]) == 3

    def test_a_touched_test_is_in_the_set_and_a_deleted_one_is_not(self):
        sources = {"tests/unit/test_kept.py": _PLAIN}

        found = select(
            ["tests/unit/test_kept.py", "tests/unit/test_deleted.py"], sources, GATE
        )

        assert found.touched == ["tests/unit/test_kept.py"]
        assert found.run_paths() == ["tests/unit/test_kept.py"]

    def test_what_the_gate_does_not_run_is_listed_and_not_run(self):
        sources = {
            "tests/e2e/test_browser.py": _IMPORTER + _WALKER,
            "tests/unit/core/test_importer.py": _IMPORTER,
        }

        found = select(["argumentation_analysis/core/reading_window.py"], sources, GATE)

        assert found.outside_gate == ["tests/e2e/test_browser.py"]
        assert found.run_paths() == ["tests/unit/core/test_importer.py"]
        assert "outside the gate's paths, not run: 1" in report(
            found, ["argumentation_analysis/core/reading_window.py"], "origin/main"
        )

    def test_a_file_the_gate_names_one_by_one_is_in_the_gate(self):
        sources = {"tests/test_named_by_the_gate.py": _WALKER}

        found = select(["anything.py"], sources, GATE)

        assert found.population == ["tests/test_named_by_the_gate.py"]

    def test_a_touched_file_no_test_names_is_said(self):
        """No reader is a finding, not a blank: the report names the file."""
        found = select(["pkg/core/orphan.py"], {"tests/unit/test_a.py": _PLAIN}, GATE)

        assert found.mentions == {"pkg/core/orphan.py": []}
        assert "no test names 1 touched file(s): pkg/core/orphan.py" in report(
            found, ["pkg/core/orphan.py"], "origin/main"
        )


class TestAConftestReachesWhatIsBelowIt:
    def test_a_conftest_under_the_gate_makes_its_directory_the_neighbour(self):
        sources = {
            "tests/unit/core/test_a.py": _PLAIN,
            "tests/unit/core/deep/test_b.py": _WALKER,
            "tests/unit/other/test_c.py": _PLAIN,
        }

        found = select(["tests/unit/core/conftest.py"], sources, GATE)

        assert found.conftest_roots == ["tests/unit/core"]
        # The directory is handed to pytest once; its files are not repeated.
        assert found.run_paths() == ["tests/unit/core"]

    def test_the_root_conftest_makes_the_gate_the_neighbour_never_tests_whole(self):
        """`pytest tests/` whole is not the gate (a full run died at the
        six-hour limit): a conftest above the gate's paths yields those
        paths, not their parent."""
        found = select(["tests/conftest.py"], {"tests/unit/test_a.py": _PLAIN}, GATE)

        assert found.conftest_roots == [
            "tests/unit",
            "tests/scripts",
            "tests/test_named_by_the_gate.py",
        ]
        assert "tests" not in found.run_paths()

    def test_a_conftest_outside_the_gate_adds_nothing(self):
        found = select(
            ["tests/e2e/conftest.py"], {"tests/unit/test_a.py": _PLAIN}, GATE
        )

        assert found.conftest_roots == []
        assert found.run_paths() == []


class TestTheGatesPaths:
    _LINE = (
        "          conda run -n projet-is --no-capture-output pytest tests/unit/ "
        'tests/scripts/ tests/test_one.py -m "not slow and not requires_api" '
        "--junitxml=pytest_report.xml -v"
    )

    def test_the_paths_stop_at_the_first_option(self):
        assert gate_paths("steps:\n" + self._LINE + "\n") == [
            "tests/unit/",
            "tests/scripts/",
            "tests/test_one.py",
        ]

    @pytest.mark.parametrize("copies", [0, 2])
    def test_a_workflow_with_no_gate_call_or_two_is_refused(self, copies):
        with pytest.raises(ValueError, match=f"found {copies}"):
            gate_paths("\n".join([self._LINE] * copies))

    def test_a_pytest_call_without_the_gates_filter_is_not_the_gate(self):
        band = self._LINE.replace("not slow and not requires_api", "requires_api")

        assert gate_paths(self._LINE + "\n" + band) == [
            "tests/unit/",
            "tests/scripts/",
            "tests/test_one.py",
        ]

    def test_the_real_workflow_is_read_and_every_path_exists(self):
        text = nt.CI_YML.read_text(encoding="utf-8")
        paths = gate_paths(text)

        assert "tests/unit/" in paths
        assert len(paths) > 10
        missing = [p for p in paths if not (nt.REPO_ROOT / p).exists()]
        assert missing == []
        # Re-derived another way: every `tests/...` word of the one command
        # line (not a comment) that carries the gate's filter.
        line = [
            row
            for row in text.splitlines()
            if f'-m "{GATE_FILTER}"' in row and not row.lstrip().startswith("#")
        ]
        assert len(line) == 1
        assert paths == re.findall(r"(?<=\s)tests/\S+", line[0].split(" -m ")[0])


@pytest.fixture(scope="module")
def tree():
    """The real test sources and the gate's paths, read once."""
    return (
        nt.test_sources(),
        gate_paths(nt.CI_YML.read_text(encoding="utf-8")),
    )


class TestTheRealTree:

    @pytest.mark.parametrize("guard", KNOWN_POPULATION_GUARDS)
    def test_a_guard_a_red_was_paid_for_is_a_neighbour_of_any_change(self, tree, guard):
        sources, gate = tree

        found = select(["argumentation_analysis/anything_at_all.py"], sources, gate)

        assert guard in sources, "the guard moved: update the pinned path"
        assert guard in found.population
        assert guard in found.run_paths()

    def test_the_change_that_reddened_the_census_meets_it(self, tree):
        """#3526 touched this module and its own test, ran both green, and
        the gate reddened on the census. The derived set holds the census
        AND the tests that name the module."""
        sources, gate = tree

        found = select(["argumentation_analysis/core/reading_window.py"], sources, gate)
        paths = found.run_paths()

        assert (
            "tests/unit/argumentation_analysis/test_unbounded_prompt_census_2908.py"
            in paths
        )
        assert (
            "tests/unit/argumentation_analysis/core/test_reading_window.py"
            in found.mentions["argumentation_analysis/core/reading_window.py"]
        )

    def test_the_population_is_a_minority_of_the_suite(self, tree):
        """The fixed cost of every use. If most tests came to match, the
        pattern would have stopped meaning "walks the tree"."""
        sources, gate = tree

        found = select([], sources, gate)

        assert 50 < len(found.population) < len(sources) // 5


class TestTheChange:
    """What "the change" is, on a repository made for the test.

    The instrument is run BEFORE the commit as often as after it: a change
    read from the commits alone would miss the file being written.
    """

    @staticmethod
    def _git(root, *args):
        done = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        return done.stdout

    def test_committed_staged_unstaged_and_untracked_files_are_the_change(
        self, tmp_path
    ):
        git = self._git
        git(tmp_path, "init", "-q", "-b", "main")
        (tmp_path / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        (tmp_path / "modified.py").write_text("a = 1\n", encoding="utf-8")
        (tmp_path / "untouched.py").write_text("b = 1\n", encoding="utf-8")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "base")
        git(tmp_path, "switch", "-q", "-c", "work")
        (tmp_path / "committed.py").write_text("c = 1\n", encoding="utf-8")
        git(tmp_path, "add", "committed.py")
        git(tmp_path, "commit", "-q", "-m", "work")
        (tmp_path / "modified.py").write_text("a = 2\n", encoding="utf-8")
        (tmp_path / "staged.py").write_text("d = 1\n", encoding="utf-8")
        git(tmp_path, "add", "staged.py")
        (tmp_path / "untracked.py").write_text("e = 1\n", encoding="utf-8")
        (tmp_path / "ignored.tmp").write_text("scratch\n", encoding="utf-8")

        assert nt.changed_files("main", root=tmp_path) == [
            "committed.py",
            "modified.py",
            "staged.py",
            "untracked.py",
        ]

    def test_what_main_gained_since_the_branch_left_it_is_not_the_change(
        self, tmp_path
    ):
        """Three dots, not two: a file merged into the base after the branch
        point is somebody else's change."""
        git = self._git
        git(tmp_path, "init", "-q", "-b", "main")
        (tmp_path / "base.py").write_text("a = 1\n", encoding="utf-8")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "base")
        git(tmp_path, "switch", "-q", "-c", "work")
        (tmp_path / "mine.py").write_text("b = 1\n", encoding="utf-8")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "work")
        git(tmp_path, "switch", "-q", "main")
        (tmp_path / "theirs.py").write_text("c = 1\n", encoding="utf-8")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "theirs")
        git(tmp_path, "switch", "-q", "work")

        assert nt.changed_files("main", root=tmp_path) == ["mine.py"]


class TestTheCommand:
    def test_the_run_keeps_the_gates_marker_filter(self):
        command = pytest_command(["tests/unit/test_a.py"])

        assert command[:3] == [sys.executable, "-m", "pytest"]
        assert command[command.index("-m", 3) + 1] == GATE_FILTER
        assert "-rs" in command, "skips are read, not assumed"
        assert "-n" not in command

    def test_workers_are_passed_only_when_asked(self):
        command = pytest_command(["tests/unit/test_a.py"], workers=4)

        assert command[-2:] == ["-n", "4"]

    def test_run_paths_hands_each_path_once(self):
        found = Neighbours(
            touched=["tests/unit/test_a.py"],
            mentions={"x.py": ["tests/unit/test_a.py", "tests/unit/test_b.py"]},
            population=["tests/unit/test_b.py", "tests/unit/test_c.py"],
        )

        assert found.run_paths() == [
            "tests/unit/test_a.py",
            "tests/unit/test_b.py",
            "tests/unit/test_c.py",
        ]

    def test_paths_mode_prints_the_set_for_an_explicit_list(self, capsys):
        code = nt.main(
            ["--paths", "--files", "argumentation_analysis/core/reading_window.py"]
        )

        printed = capsys.readouterr().out.split()
        assert code == 0
        assert (
            "tests/unit/argumentation_analysis/test_unbounded_prompt_census_2908.py"
            in printed
        )
        assert all(path.startswith("tests/") for path in printed)

    def test_a_base_git_does_not_know_is_an_error_not_an_empty_set(self, capsys):
        """An empty change and an unanswered question look the same in a
        count; the exit code keeps them apart."""
        code = nt.main(["--base", "no-such-ref-for-the-neighbour-test"])

        assert code == nt.EXIT_GIT
        assert "git did not answer" in capsys.readouterr().err

    def test_a_long_run_goes_through_an_args_file(self, monkeypatch, capsys):
        """Windows refuses a command line near 32 767 characters, and a
        conftest or a central module yields hundreds of paths."""
        launched = []
        real_run = nt.subprocess.run

        def fake_run(command, **kwargs):
            if command[0] != sys.executable:
                return real_run(command, **kwargs)
            launched.append(command)

            class Done:
                returncode = 0

            return Done()

        monkeypatch.setattr(nt.subprocess, "run", fake_run)
        monkeypatch.setattr(nt, "MAX_COMMAND_CHARS", 200)

        code = nt.main(
            ["--run", "--files", "argumentation_analysis/core/reading_window.py"]
        )

        assert code == 0
        assert len(launched) == 1
        args_file = [arg for arg in launched[0] if arg.startswith("@")]
        assert len(args_file) == 1
        listed = open(args_file[0][1:], encoding="utf-8").read().split()
        assert (
            "tests/unit/argumentation_analysis/test_unbounded_prompt_census_2908.py"
            in listed
        )
        assert launched[0][launched[0].index("-m", 3) + 1] == GATE_FILTER
