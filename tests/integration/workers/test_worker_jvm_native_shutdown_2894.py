# -*- coding: utf-8 -*-
"""#2894: the native exit shutdown runs, in its non-blocking form.

``initialize_jvm`` used to disable jpype's exit hook outright
(``jpype.config.onexit = False``, #2866): the JVM died with the process and
no native teardown ever ran. The hook is now left armed and only the form is
pinned: jpype's ``_JTerminate`` atexit calls
``_jpype.shutdown(config.destroy_jvm, False)``, and ``destroy_jvm = False``
is the form measured to return — 2-3 s on ai-01's fuller child, 0.00 s
direct on po-2023 (17/11) — while ``shutdown(True, ...)`` (``DestroyJavaVM``)
blocks the exiting interpreter, which is the hang #2866 worked around.

The witness has two halves, one child, its own interpreter: the **config**
the initialiser leaves behind (the hook armed, the destroy form refused) and
the **exit** itself — the hook runs at interpreter exit, so a clean return
under the bound is the behavioural half. Born red on ``main``, where the
workaround leaves ``onexit = False``.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import run_bounded

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2894 test requires the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# A start and a clean exit take about 15 s here; the hook adds a few seconds
# on fuller seats (2-3 s measured on ai-01). Well above both.
_BOUND = 120

_CHILD = """
import logging
logging.disable(logging.CRITICAL)
from argumentation_analysis.core.jvm_setup import initialize_jvm
ok = initialize_jvm()
import jpype
print("cfg", ok, bool(jpype.config.onexit), bool(jpype.config.destroy_jvm), flush=True)
"""


def test_the_exit_shutdown_is_armed_in_its_non_blocking_form():
    done = run_bounded(
        [sys.executable, "-c", _CHILD],
        _BOUND,
        failure="the #2894 hang: the process did not exit",
    )
    cfg = next((l for l in done.stdout.splitlines() if l.startswith("cfg ")), None)
    assert cfg is not None, done.stdout + done.stderr[-2000:]
    _, ok, onexit, destroy = cfg.split()
    assert ok == "True", done.stderr[-2000:]
    # The mechanism half: the workaround left the hook disabled.
    assert onexit == "True", "#2894: the native exit hook must stay armed"
    assert destroy == "False", "#2894: DestroyJavaVM must not run at exit — it blocks"
    # The behaviour half: the hook runs at exit and returns.
    assert done.returncode == 0, done.stderr[-2000:]
