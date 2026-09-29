# -*- coding: utf-8 -*-
"""Census guard for #2858: no test shuts the session JVM down.

The gate boots ONE JVM for the whole session (``pytest_sessionstart``,
``tests/conftest.py``). JPype cannot restart a JVM in-process, so a single
``shutdown_jvm()`` call anywhere in the collected tree kills every later JVM
test with "OSError: JVM cannot be restarted" — measured: 30 failures the
moment ``test_tweety_bridge.py``'s tearDown ran its real branch alongside
the other JVM tests. That call is also how the 38 real-Tweety tests of #2858
stayed excludable: the flag that gated them could not be switched on
globally without this tearDown killing the session.

The population is read from the git index (``iter_tracked_files``,
``tests/support/tree_walk.py``) — the #2834 lesson: an untracked seat-local
file is invisible to the census, and CI reads the committed index, so the
population is the same on every seat.

Any ``shutdown_jvm(`` / ``shutdownJVM(`` CALL under ``tests/`` fails, except
the out-of-session owners named below (each runs as its own process, so its
shutdown kills a JVM the session never shared). Mocks don't count:
``patch.object(TweetyBridge, "shutdown_jvm")`` references the method as an
attribute and ``jpype_mock.shutdownJVM = MagicMock()`` assigns one — neither
is a call, and the AST filter sees them for what they are.
"""

import ast
import subprocess
from pathlib import Path

from tests.support.tree_walk import iter_tracked_files

TESTS_DIR = Path(__file__).resolve().parents[1]

# Files that legitimately own their JVM lifecycle: each runs as its own
# process (detached worker / archived debug script / disabled harness), so
# its shutdown never touches the pytest session's JVM. Every entry must stay
# load-bearing — test_allowlist_is_load_bearing reddens if one stops
# carrying a call (the #2137 decoration pattern).
OUT_OF_SESSION_OWNERS = {
    "tests/_archived/diagnostic/workers/worker_jpype_minimal.py": (
        "detached diagnostic worker — subprocess owns its JVM"
    ),
    "tests/_archived/loose_files/debug_create_temp_file_leak.py": (
        "archived debug script — subprocess owns its JVM"
    ),
    "tests/_archived/loose_files/debug_jni_leak.py": (
        "archived debug script — subprocess owns its JVM"
    ),
    "tests/minimal_jvm_pytest_test.py_disabled": (
        "disabled harness — never collected, kept for archaeology"
    ),
}

# The pre-fix revision the born-red control reads: ``bfff7542b``, the main tip
# this branch rebases on — its tearDown still carried the call. PINNED on
# purpose (#2859 review): the old ``origin/main`` spelling would redden main
# the moment this PR lands, because the fix becomes main's own content.
_PRE_FIX_REVISION = "bfff7542bcadc34b1d8ad0a9ae2650c5d3440fe9"
_PRE_FIX_PATH = "tests/agents/core/logic/test_tweety_bridge.py"

_SHUTDOWN_NAMES = {"shutdown_jvm", "shutdownJVM"}


def _shutdown_calls(tree):
    """Yield ``(lineno, name)`` for every shutdown call in an AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            else:
                continue
            if name in _SHUTDOWN_NAMES:
                yield (node.lineno, name)


def _parse(path: Path) -> ast.AST:
    # utf-8-sig: tracked modules carry a BOM and ast.parse rejects the plain
    # utf-8 decoding of those bytes (the #2851 lesson).
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def census():
    """Every offending ``(relpath, lineno, name)`` in the tracked tests/ tree."""
    offenders = []
    for path in iter_tracked_files(TESTS_DIR):
        rel = path.relative_to(TESTS_DIR.parent).as_posix()
        if rel in OUT_OF_SESSION_OWNERS:
            continue
        for lineno, name in _shutdown_calls(_parse(path)):
            offenders.append((rel, lineno, name))
    return offenders


class TestNoTestShutsTheSessionJvm:
    def test_tracked_tree_has_zero_shutdown_calls(self):
        offenders = census()
        assert not offenders, (
            "test files that shut the session JVM down — JPype cannot "
            f"restart it in-process, every later JVM test dies: {offenders}"
        )

    def test_born_red_pre_fix_teardown_reddens(self):
        """Born-red witness: the tearDown at the PINNED revision carried the call.

        The guard, run on the pre-fix tree, must flag the exact defect #2858
        repairs. The revision is pinned (``_PRE_FIX_REVISION``), never
        ``origin/main``: the branch is based on that tip, and after the merge
        ``origin/main`` would *be* the fix — the control would redden main
        (#2859 review). The test job checks out with fetch-depth: 0 (#2014),
        so the object is reachable in CI; under a shallow checkout the control
        fails loudly rather than passing silently — same contract as
        tests/unit/argumentation_analysis/evaluation/test_production_person_sweep_2349.py.
        """
        proc = subprocess.run(
            ["git", "show", f"{_PRE_FIX_REVISION}:{_PRE_FIX_PATH}"],
            capture_output=True,
        )
        if proc.returncode != 0:
            first_stderr = proc.stderr.decode(errors="replace").strip().splitlines()[:1]
            raise AssertionError(
                f"git show {_PRE_FIX_REVISION}:{_PRE_FIX_PATH} failed "
                f"(rc={proc.returncode}) — the born-red control NEEDS history; "
                "a shallow clone makes it unmeasurable, and it must not pass "
                f"silently ({first_stderr})"
            )
        raw = proc.stdout
        # utf-8-sig: that file carries a BOM on main — a plain utf-8 decode
        # hands ast.parse a leading U+FEFF it rejects (#2851 lesson).
        src = raw.decode("utf-8-sig")
        pre_fix_calls = list(_shutdown_calls(ast.parse(src)))
        assert (97, "shutdown_jvm") in pre_fix_calls, pre_fix_calls
        # ...and the fixed tree is clean for that file:
        fixed_calls = list(
            _shutdown_calls(
                _parse(TESTS_DIR / "agents/core/logic/test_tweety_bridge.py")
            )
        )
        assert not fixed_calls, fixed_calls

    def test_allowlist_is_load_bearing(self):
        """Each named owner really carries a call — no decoration."""
        for rel in OUT_OF_SESSION_OWNERS:
            calls = list(_shutdown_calls(_parse(TESTS_DIR.parent / rel)))
            assert calls, f"{rel} carries no shutdown call — remove its exemption"

    def test_scanner_sees_every_call_shape(self):
        """Positive and negative controls on the scanner itself."""
        src = (
            "import jpype\n"
            "jpype.shutdownJVM()\n"
            "x.shutdown_jvm()\n"
            "self.bridge.shutdown_jvm()\n"
        )
        calls = list(_shutdown_calls(ast.parse(src)))
        assert sorted(calls) == [
            (2, "shutdownJVM"),
            (3, "shutdown_jvm"),
            (4, "shutdown_jvm"),
        ]
        # A mock assignment and a patch.object reference are NOT calls:
        mock_src = (
            "import jpype_mock\n"
            "jpype_mock.shutdownJVM = MagicMock()\n"
            "patch.object(TweetyBridge, 'shutdown_jvm')\n"
        )
        assert not list(_shutdown_calls(ast.parse(mock_src)))
