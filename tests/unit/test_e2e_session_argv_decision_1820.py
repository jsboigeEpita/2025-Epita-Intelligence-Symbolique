"""#1820 — ``is_e2e_session`` decided from the collection argv, not a cache slot
that ``pytest_collection_finish`` writes after ``pytest_sessionstart`` reads it.

Pre-fix ``pytest_sessionstart`` (tests/conftest.py) read ``is_e2e_session`` from
``config.cache``. The slot is only written LATER, by ``pytest_collection_finish``
— the reader runs first, so on a cold cache it reads the default ``False`` and
boots the JVM even for an e2e session (the exact torch/JVM DLL crash that D3.1.1
exists to prevent), and on a warm cache it reads a PRIOR run's value. The
defect is transport-order, not logic: the truth is knowable from the argv
(paths + ``-m``) at ``pytest_sessionstart`` time.

``test_sessionstart_cold_cache_e2e_session_skips_jvm`` is the born-red control:
it calls the REAL ``pytest_sessionstart`` (e.g. ``test_conftest_jvm_return_1641``
pattern) with a config whose argv reaches ``tests/e2e`` and a cold cache. On the
pre-fix code the reader falls through to ``initialize_jvm`` → the control FAILS;
with the archive it reads the argv and skips init → GREEN.

``test_conftest_jvm_return_1641`` must stay green unmodified: its mock
``session.config`` is a bare MagicMock, so the classifier must return ``False``
(it reaches the JVM-init path) for such an object — pinned by
``test_classifier_magicmock_returns_false``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests import _e2e_session_decision as d
from tests._e2e_session_decision import _argv_decides_e2e_session

_REPO = Path(__file__).resolve().parents[2]
_CONFTEST_PATH = _REPO / "tests" / "conftest.py"
_JVM_SETUP = "argumentation_analysis.core.jvm_setup.initialize_jvm"


def _cfg(args=None, markexpr="", testpaths=None):
    """A REAL pytest Config with the given collection argv. ``markexpr`` is the
    ``-m`` string (pytest stores it on ``config.option.markexpr`` when passed
    through ``fromdictargs``)."""
    import _pytest.config as c

    opt = {"rootdir": str(_REPO)}
    if markexpr:
        opt["markexpr"] = markexpr
    if testpaths is not None:
        opt["testpaths"] = testpaths
    return c.Config.fromdictargs(opt, args or [])


class _ColdCache:
    """A cache provider that answers the default for every key — the state of a
    fresh pytest cache before any run has populated ``is_e2e_session``."""

    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass


class _ContaminatedCache:
    """A cache provider carrying the value a PRIOR run wrote for every key —
    the ``.pytest_cache`` state when an earlier invocation collected e2e."""

    def __init__(self, stale):
        self._stale = stale

    def get(self, key, default=None):
        return self._stale

    def set(self, key, value):
        pass


@pytest.fixture(scope="module")
def _sessionstart():
    """Load the real tests/conftest.py and expose its pytest_sessionstart hook
    (mirrors test_conftest_jvm_return_1641)."""
    spec = importlib.util.spec_from_file_location(
        "_conftest_under_test_1820", _CONFTEST_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.pytest_sessionstart


class TestClassifierArgv:
    """The decision logic, on REAL pytest Config objects."""

    def test_reaching_e2e_path_is_e2e_session(self):
        cfg = _cfg(args=["tests/e2e/python/test_argument_reconstructor.py"])
        assert _argv_decides_e2e_session(cfg) is True

    def test_e2e_dir_itself_is_e2e_session(self):
        cfg = _cfg(args=["tests/e2e"])
        assert _argv_decides_e2e_session(cfg) is True

    def test_sibling_unit_path_is_not_e2e_session(self):
        cfg = _cfg(args=["tests/unit/argumentation_analysis"])
        assert _argv_decides_e2e_session(cfg) is False

    def test_broad_tests_path_reaches_e2e(self):
        # `pytest tests` collects tests/e2e too, so it IS an e2e session.
        cfg = _cfg(args=["tests"])
        assert _argv_decides_e2e_session(cfg) is True

    def test_bare_pytest_uses_testpaths_and_reaches_e2e(self):
        # No path given: pytest expands `testpaths = tests` into config.args.
        cfg = _cfg(args=[], testpaths="tests")
        assert _argv_decides_e2e_session(cfg) is True

    def test_markexpr_not_e2e_overrides_reaching_path(self):
        # `pytest tests -m "not e2e"` keeps no e2e item → NOT an e2e session,
        # the JVM must boot.
        cfg = _cfg(args=["tests"], markexpr="not e2e")
        assert _argv_decides_e2e_session(cfg) is False

    def test_markexpr_transitively_excludes_e2e(self):
        cfg = _cfg(args=["tests"], markexpr="not (e2e or slow)")
        assert _argv_decides_e2e_session(cfg) is False

    def test_markexpr_that_keeps_e2e_is_still_e2e(self):
        # `-m "not slow"` keeps every e2e item that is not also marked slow, so
        # an e2e item may survive → e2e session (conservative: do not boot JVM).
        cfg = _cfg(args=["tests"], markexpr="not slow")
        assert _argv_decides_e2e_session(cfg) is True


class TestClassifierMockTolerance:
    """The conftest tests feed bare MagicMocks as `session.config`; those must
    keep reaching the JVM-init path (the prod behavior they assert)."""

    def test_classifier_magicmock_returns_false(self):
        # Mirrors test_conftest_jvm_return_1641._mock_session(): a bare
        # MagicMock with a few boolean option attrs set.
        config = MagicMock()
        config.option.collectonly = False
        config.getoption.return_value = False
        config.cache.get.return_value = False
        assert _argv_decides_e2e_session(config) is False
        # Sanity: the mock's args really is a MagicMock (not a list), which is
        # precisely the shape that must fall through.
        assert isinstance(config.args, MagicMock) and not isinstance(config.args, list)


class TestTransportControl:
    """The born-red control: pytest_sessionstart must skip JVM init for an e2e
    session even on a COLD cache, because the decision comes from argv, not
    from the (not-yet-written) cache slot."""

    def test_sessionstart_cold_cache_e2e_session_skips_jvm(self, _sessionstart):
        cfg = _cfg(args=["tests/e2e/python/test_argument_reconstructor.py"])
        cfg.cache = _ColdCache()  # fresh cache: is_e2e_session not yet written
        session = MagicMock()
        session.config = cfg

        with patch(_JVM_SETUP) as mock_init:
            _sessionstart(session)

        mock_init.assert_not_called()

    def test_sessionstart_contaminated_cache_non_e2e_session_boots_jvm(
        self, _sessionstart
    ):
        # Two-invocation contamination (DoD item 2): a PRIOR run collected e2e
        # and left is_e2e_session=True in the persistent cache. THIS run's argv
        # is a plain unit path — it must boot the JVM (unit tests need it), and
        # the decision must come from the argv, not from the contaminated slot.
        # Pre-fix this FAILS: the reader trusts the slot and skips the JVM.
        cfg = _cfg(args=["tests/unit/argumentation_analysis"])
        cfg.cache = _ContaminatedCache(True)
        session = MagicMock()
        session.config = cfg

        with patch(_JVM_SETUP) as mock_init:
            _sessionstart(session)

        mock_init.assert_called()
