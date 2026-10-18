# -*- coding: utf-8 -*-
"""#3062 — a caller-neutralised env survives collecting ``tests/e2e/python``.

Measured on ``main`` (R1094, seat ai-01): ``pytest.main`` collecting
``tests/e2e/python`` imported ``scripts.apps.webapp.unified_web_orchestrator``,
whose import-time ``load_dotenv(override=True)`` reloaded the root ``.env``
over the caller's neutralised keys for the whole session. A later full run
under that env made 12 705 paid calls through ``.env`` — the #2472 contract
(a value the caller set wins, even ``""``) was broken at import time.

The witness runs in a child interpreter: it neutralises the LLM credentials
in-process — a fake ``OPENAI_API_KEY`` and an empty ``OPENROUTER_API_KEY``,
the incident's exact shapes — collects ``tests/e2e/python`` with
``--collect-only`` (no test executes, zero LLM call), then reports BOOLEANS
only: a key value never leaves the child. On main the booleans flip (the
collection replaced both); the fix keeps the caller's values.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# The child driver. It is a file, not ``-c`` source: nested quoting around the
# probe values has bitten before, and a file debugs from the pytest output.
_DRIVER = """
import json, os, sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo))

# The caller neutralises the LLM credentials (#2472 shapes): a fake key and an
# empty one must both survive the collection that follows.
os.environ["OPENAI_API_KEY"] = "sk-fake-3062-witness"
os.environ["OPENROUTER_API_KEY"] = ""

import pytest

rc = pytest.main(
    [
        "--collect-only",
        "-q",
        "-p", "no:cacheprovider",
        "--disable-jvm-session",
        str(repo / "tests" / "e2e" / "python"),
    ]
)

report = {
    "rc": int(rc),
    "openai_still_fake": os.environ.get("OPENAI_API_KEY") == "sk-fake-3062-witness",
    "openrouter_still_empty": os.environ.get("OPENROUTER_API_KEY") == "",
}
print("WITNESS_3062=" + json.dumps(report))
"""


def test_a_neutralised_env_survives_e2e_collection(tmp_path):
    """Collecting ``tests/e2e/python`` must not reload the root ``.env``.

    The child sets both credentials itself, in-process, before pytest is
    imported: whatever this session's environment holds, the child's caller
    env is the neutralised one. The parent strips the names from the spawned
    environment too, so the report measures collection and only collection.
    """
    driver = tmp_path / "witness_3062.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    env = dict(os.environ)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        env.pop(name, None)
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_XDIST_WORKER", None)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(driver), str(REPO)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
        timeout=600,
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("WITNESS_3062=")]
    assert lines, (
        f"no witness output — rc={proc.returncode}, "
        f"stdout tail: {proc.stdout[-600:]!r}, stderr tail: {proc.stderr[-600:]!r}"
    )
    report = json.loads(lines[-1][len("WITNESS_3062=") :])
    assert report["rc"] == 0, "collecting tests/e2e/python must itself succeed"
    assert report["openai_still_fake"], (
        "collecting tests/e2e/python replaced the caller's OPENAI_API_KEY — "
        "#2472 broken at import (#3062)"
    )
    assert report["openrouter_still_empty"], (
        "collecting tests/e2e/python reloaded OPENROUTER_API_KEY from .env — " "#3062"
    )
