"""#2862 — the e2e argv classifier honors ``--ignore`` / ``--ignore-glob``.

The defect: ``pytest tests/ --ignore=tests/e2e ...`` was decided an E2E
session. ``--ignore`` was never read, so the ancestor root ``tests`` won over
the explicit exclusion; ``pytest_sessionstart`` skipped the JVM boot, every
JVM test skipped at setup, and the run exited 0 — measured at 18,392 skipped.
The storm guard could not catch it either: it ORed the same argv prediction
into its own exemption (``tests/conftest.py``), so the wrong prediction alone
disabled it.

Born-red: ``test_row_one_of_2862_flips_to_not_e2e`` decides ``True`` on
``main`` and ``False`` after the fix — it is the first row of the issue's
table, verbatim. Its neighbour ``test_row_one_without_the_ignore_is_still_e2e``
is the control: the same argv minus the ignore keeps deciding ``True``, so the
ignore is measured to be what flips the row.

The pre-existing rows (``tests/unit`` → False, ``tests/e2e`` → True,
``tests -m "not e2e"`` → False, the MagicMock tolerance) are pinned by
``test_e2e_session_argv_decision_1820.py``, which runs unmodified.

``--deselect`` is out of scope, deliberately, and pinned as such below: a list
of deselected node ids cannot PROVE that every e2e item is deselected without
collecting them first, which is exactly what this decision runs before. The
consequence is covered on the guard side
(``tests/integration/workers/test_worker_e2e_disagreement_2862.py``).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from tests._e2e_session_decision import (
    _argv_decides_e2e_session,
    _ignore_options,
)

_REPO = Path(__file__).resolve().parents[2]


def _cfg(args=None, markexpr="", ignore=None, ignore_glob=None, deselect=None):
    """A REAL pytest Config carrying the given collection argv.

    ``fromdictargs`` puts the option namespace in place before parsing, and
    argparse only fills a default for a dest the namespace does not already
    have — so the ``--ignore``/``--ignore-glob``/``--deselect`` entries land on
    ``config.option`` exactly as pytest's own parser leaves them."""
    import _pytest.config as c

    opt = {"rootdir": str(_REPO)}
    if markexpr:
        opt["markexpr"] = markexpr
    if ignore is not None:
        opt["ignore"] = list(ignore)
    if ignore_glob is not None:
        opt["ignore_glob"] = list(ignore_glob)
    if deselect is not None:
        opt["deselect"] = list(deselect)
    return c.Config.fromdictargs(opt, args or [])


class TestIgnoreFlipsTheIssueRow:
    """Row 1 of the issue's table, and its control."""

    def test_row_one_of_2862_flips_to_not_e2e(self):
        cfg = _cfg(
            args=["tests"],
            markexpr="not slow and not requires_api",
            ignore=["tests/e2e"],
        )
        assert _argv_decides_e2e_session(cfg) is False

    def test_row_one_without_the_ignore_is_still_e2e(self):
        cfg = _cfg(args=["tests"], markexpr="not slow and not requires_api")
        assert _argv_decides_e2e_session(cfg) is True


class TestIgnoreSemantics:
    """What ``--ignore`` prunes: the path itself, or a subtree it contains."""

    def test_ignore_of_e2e_itself_is_not_e2e(self):
        cfg = _cfg(args=["tests"], ignore=["tests/e2e"])
        assert _argv_decides_e2e_session(cfg) is False

    def test_ignore_of_e2e_as_the_root_is_not_e2e(self):
        # The root itself is pruned by the ignore: nothing is collected from it.
        cfg = _cfg(args=["tests/e2e"], ignore=["tests/e2e"])
        assert _argv_decides_e2e_session(cfg) is False

    def test_absolute_ignore_path_is_honored(self):
        # pytest absolutepaths the ignore entries; so does the classifier.
        cfg = _cfg(args=["tests"], ignore=[str(_REPO / "tests" / "e2e")])
        assert _argv_decides_e2e_session(cfg) is False

    def test_ignore_of_an_unrelated_sibling_changes_nothing(self):
        cfg = _cfg(args=["tests"], ignore=["tests/unit"])
        assert _argv_decides_e2e_session(cfg) is True

    def test_ignore_of_a_subdir_of_e2e_leaves_e2e_reachable(self):
        # pytest prunes the subtree of an ignored directory, not the siblings
        # the parent still holds: tests/e2e itself is still collected.
        cfg = _cfg(args=["tests"], ignore=["tests/e2e/python"])
        assert _argv_decides_e2e_session(cfg) is True


class TestIgnoreGlobSemantics:
    """``--ignore-glob`` matches the absolutepath'd path with fnmatch, as
    ``_pytest.main.pytest_ignore_collect`` does."""

    def test_glob_matching_e2e_prunes_it(self):
        cfg = _cfg(args=["tests"], ignore_glob=["*e2e*"])
        assert _argv_decides_e2e_session(cfg) is False

    def test_glob_matching_only_a_subdir_leaves_e2e_reachable(self):
        cfg = _cfg(args=["tests"], ignore_glob=["*e2e/python*"])
        assert _argv_decides_e2e_session(cfg) is True


class TestDeselectStaysOutOfScope:
    """Pinned decision, with its reason: the classifier cannot soundly answer
    "every e2e item is deselected" from a node-id list before collecting."""

    def test_deselect_of_an_e2e_node_id_is_not_read(self):
        cfg = _cfg(
            args=["tests"],
            deselect=["tests/e2e/python/test_webapp_homepage.py"],
        )
        assert _argv_decides_e2e_session(cfg) is True


class TestMockTolerance:
    """The mock configs fed to ``pytest_sessionstart`` by the conftest tests
    must keep reading as "no ignore options" (and stay on the JVM-init path)."""

    def test_magicmock_options_yield_no_ignore_entries(self):
        config = MagicMock()
        assert _ignore_options(config) == ([], [])

    def test_magicmock_config_still_not_e2e(self):
        config = MagicMock()
        config.option.collectonly = False
        config.getoption.return_value = False
        config.cache.get.return_value = False
        assert _argv_decides_e2e_session(config) is False
