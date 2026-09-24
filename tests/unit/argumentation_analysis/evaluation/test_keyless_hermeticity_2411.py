# -*- coding: utf-8 -*-
"""#2411 — the evaluation unit suite must stay green on a keyless environment.

Two evaluation tests read the AMBIENT API key (their only config source is
``os.environ`` via ``resolve_chat_endpoint``, which runs before the mocked
client is built): they pass on any machine whose ``.env`` carries a key, and
fail on a keyless checkout ("No LLM API key configured"). They are unit
tests — they never reach the network. The repair makes every test set its
own configuration; this guard runs one keyless pass over the defect
population root (``tests/unit/argumentation_analysis/evaluation/``, plus the
two hermetic nodes the census repaired elsewhere) and asserts it stays green.

The child runs keyless by carrying EMPTY values for the three config
variables, not by waiting for a keyless checkout: an empty value counts as
absent (``resolve_chat_endpoint``) yet as caller-set, so it survives the
``pytest_configure`` dotenv reload (#2472/#2475 — the root ``.env`` fills in
only what the environment does not already carry). The guard therefore runs
on every harness seat — CI (keys as secrets), keyed dev checkouts, keyless
ones — instead of skipping exactly where regressions land.

Anti-recursion: the spawned run excludes this file.
"""

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
_EVAL_DIR = os.path.join(_REPO_ROOT, "tests/unit/argumentation_analysis/evaluation")

# Empty counts as absent for the readers, and as caller-set for the dotenv
# reload (#2475): the child is keyless on every checkout, .env or not.
_EMPTIED_CONFIG = ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "TEXT_CONFIG_PASSPHRASE")

# The two hermetic repairs the census made outside the evaluation directory:
# their subject is code, so they must never read the suite host's config
# again. (The two api probes the same census classified are `requires_api`,
# hence outside this pass's selection — `-m` below.)

# Tests whose subject IS the ambient config: they cannot pass keyless, by
# construction, so this pass leaves them out. `requires_dataset_passphrase`
# tests fail instead of skipping when CI is set and the passphrase is empty,
# which is what this pass does to it: unselected, they turned the pass red.
_AMBIENT_SUBJECT_MARKERS = "not requires_api and not requires_dataset_passphrase"
_REPAIRED_HERMETIC_NODES = (
    "tests/unit/argumentation_analysis/plugins/test_cassette_round_trip.py"
    "::TestCommittedCassettesStillReplay::test_replay_path_uses_cache",
    "tests/unit/scripts/analysis/test_export_scda_state_privacy.py",
)


def test_keyless_evaluation_suite_stays_green():
    child_env = {**os.environ, **{name: "" for name in _EMPTIED_CONFIG}}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            _EVAL_DIR,
            *_REPAIRED_HERMETIC_NODES,
            "-m",
            _AMBIENT_SUBJECT_MARKERS,
            "--disable-jvm-session",
            "-q",
            "-p",
            "no:cacheprovider",
            "--ignore",
            os.path.join(_EVAL_DIR, "test_keyless_hermeticity_2411.py"),
        ],
        cwd=_REPO_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, (
        "an evaluation unit test depends on the ambient config:\n"
        f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
    )
