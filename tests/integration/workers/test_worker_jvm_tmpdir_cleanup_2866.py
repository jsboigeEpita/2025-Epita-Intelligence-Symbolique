# -*- coding: utf-8 -*-
"""#2866: the JVM's temporary files do not outlive the process.

With jpype's exit hook disabled (``jpype.config.onexit = False``, set by
``initialize_jvm``), ``DestroyJavaVM`` never runs at exit, so Java's shutdown
hooks never run either, and Tweety's ``deleteOnExit`` files stayed behind —
measured on the fix's first head: 3 temp files left on 3 created, versus 1 on
3 with the destroy still active.

``initialize_jvm`` therefore points ``java.io.tmpdir`` at a per-process
directory that a Python ``atexit`` handler removes. Born red on ``36d829eeb``
(the head without the sweep): ``java.io.tmpdir`` resolved to ``%TEMP%``
itself, which still exists after the child dies.

The child runs in its own interpreter (the ``run_bounded`` pattern of
#2519/#2530): the sweep happens at interpreter exit, which the test process
cannot reach for itself.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import run_bounded

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2866 cleanup witness requires the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# A start and a clean exit take about 15 s here.
_BOUND = 120

_WITNESS = """
import logging
logging.disable(logging.CRITICAL)
from argumentation_analysis.core.jvm_setup import initialize_jvm
started = initialize_jvm()
import jpype
System = jpype.JClass("java.lang.System")
File = jpype.JClass("java.io.File")
witness = File.createTempFile("witness2866", ".txt")
witness.deleteOnExit()
print("started", started, flush=True)
print("tmpdir", str(System.getProperty("java.io.tmpdir")), flush=True)
"""


def test_the_java_tmpdir_is_swept_at_process_exit():
    """The child creates a ``deleteOnExit`` file, exits, and the directory
    ``java.io.tmpdir`` pointed at is gone: the sweep no longer relies on the
    native shutdown ``initialize_jvm`` disables."""
    done = run_bounded(
        [sys.executable, "-c", _WITNESS],
        _BOUND,
        failure="the #2866 cleanup witness: the process did not exit",
    )

    assert "started True" in done.stdout, done.stdout + done.stderr[-2000:]
    assert done.returncode == 0, done.stderr[-2000:]
    tmpdir_lines = [l for l in done.stdout.splitlines() if l.startswith("tmpdir ")]
    assert tmpdir_lines, done.stdout
    tmpdir = tmpdir_lines[0][len("tmpdir ") :]

    assert not os.path.exists(tmpdir), f"java.io.tmpdir outlived the process: {tmpdir}"
