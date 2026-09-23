# -*- coding: utf-8 -*-
"""#2411 — the evaluation unit suite must stay green on a keyless checkout.

Two evaluation tests read the AMBIENT API key (their only config source is
``os.environ`` via ``resolve_chat_endpoint``, which runs before the mocked
client is built): they pass on any machine whose ``.env`` carries a key, and
fail on a keyless checkout ("No LLM API key configured"). They are unit
tests — they never reach the network. The repair makes every test set its
own configuration; this guard runs one keyless pass over the defect
population root (``tests/unit/argumentation_analysis/evaluation/``, plus the
two hermetic nodes the census repaired elsewhere) and asserts it stays green.

The pass is only meaningful keyless: when a key is ambient the run cannot
distinguish a hermetic test from one that borrowed the environment, so the
guard skips itself. CI carries keys and never executes the pass; the DoD's
red-on-main gate is the born-red executed on a keyless checkout, captured
in the PR (the pass names the environment-dependent tests before the fix).

Anti-recursion: the spawned run excludes this file.
"""

import os
import subprocess
import sys

import pytest

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
_EVAL_DIR = os.path.join(_REPO_ROOT, "tests/unit/argumentation_analysis/evaluation")
_KEYS = ("OPENAI_API_KEY", "OPENROUTER_API_KEY")

# The two hermetic repairs the census made outside the evaluation directory:
# their subject is code, so they must never read the suite host's config
# again. (The two api probes the same census classified are `requires_api`,
# hence outside this pass's selection — `-m "not requires_api"` below.)
_REPAIRED_HERMETIC_NODES = (
    "tests/unit/argumentation_analysis/plugins/test_cassette_round_trip.py"
    "::TestCommittedCassettesStillReplay::test_replay_path_uses_cache",
    "tests/unit/scripts/analysis/test_export_scda_state_privacy.py",
)


def test_keyless_evaluation_suite_stays_green():
    if any(os.environ.get(k) for k in _KEYS):
        pytest.skip("the keyless pass requires a keyless environment")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            _EVAL_DIR,
            *_REPAIRED_HERMETIC_NODES,
            "-m",
            "not requires_api",
            "--disable-jvm-session",
            "-q",
            "-p",
            "no:cacheprovider",
            "--ignore",
            os.path.join(_EVAL_DIR, "test_keyless_hermeticity_2411.py"),
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, (
        "an evaluation unit test depends on the ambient API key:\n"
        f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
    )
