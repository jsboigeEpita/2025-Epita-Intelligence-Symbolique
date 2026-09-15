"""Né-rouge guard for #2130 — importing ``core.environment`` must load the .env.

Measured on the pristine tree (base ``14fbe867``): the module's import-time block
advertised an essential ``ensure_env()`` call ("NE JAMAIS DÉSACTIVER") around a
bare ``pass`` — the auto-load was a dead path. Every consumer importing the module
for "Auto-activation environnement intelligent" (agent adapters, service_manager,
group_chat, validation scripts) got **nothing**: ``SELF_HOSTED_LLM_*`` and friends
stayed absent from ``os.environ`` and the self-hosted fallacy phase reported
"not configured" on seats whose ``.env`` was fully populated.

Instrument: a subprocess imports the module with the very variables scrubbed from
its inherited environment, then reports their presence. The guard proves the module
did the loading — not process inheritance. Skips cleanly where no ``.env`` exists
(CI), mirroring the repo's "tests auto-skip without API keys" convention.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"

_PROBE = r"""
import json, os, sys
repo = sys.argv[1]
names = sys.argv[2].split(",")
sys.path.insert(0, repo)
before = {k: bool(os.environ.get(k)) for k in names}
import argumentation_analysis.core.environment  # noqa: F401 — the side effect under test
after = {k: bool(os.environ.get(k)) for k in names}
print("PROBE_RESULT=" + json.dumps({"before": before, "after": after}))
"""


def _declared_env_names() -> list[str]:
    """Names declared in the repo .env — names only, values are never read here."""
    names = []
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*([A-Z][A-Z0-9_]+)\s*=", line)
        if m:
            names.append(m.group(1))
    return names


def test_import_loads_the_declared_env_2130():
    if not ENV_FILE.is_file():
        pytest.skip("no repo .env on this seat (CI) — nothing to autoload")

    names = [n for n in _declared_env_names() if n != "E2E_TESTING_MODE"]
    assert names, "the .env declares no variable — the probe would measure nothing"

    env = {k: v for k, v in os.environ.items() if k not in set(names)}
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, str(REPO_ROOT), ",".join(names)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    marker = [l for l in proc.stdout.splitlines() if l.startswith("PROBE_RESULT=")]
    assert marker, (
        f"probe produced no result — stdout tail: {proc.stdout[-400:]!r}, "
        f"stderr tail: {proc.stderr[-400:]!r}"
    )
    probe = json.loads(marker[-1][len("PROBE_RESULT=") :])

    scrubbed = {k for k, present in probe["before"].items() if not present}
    assert scrubbed == set(names), (
        f"control failed: these vars leaked into the scrubbed subprocess: "
        f"{sorted(set(names) - scrubbed)}"
    )
    loaded = {k for k, present in probe["after"].items() if present}
    missing = sorted(set(names) - loaded)
    assert not missing, (
        "importing argumentation_analysis.core.environment left these declared "
        f".env variables out of os.environ: {missing} — the auto-load is a dead "
        "path and self-hosted phases report 'not configured' on populated seats "
        "(#2130)"
    )


def test_import_does_not_raise_without_conda_gate():
    """The autoload must stay safe outside an activated conda shell.

    ensure_env() raises RuntimeError when CONDA_DEFAULT_ENV is unset — the
    import-time path must never carry that gate (that is why the original
    auto-execution was defused into ``pass``).
    """
    if not ENV_FILE.is_file():
        pytest.skip("no repo .env on this seat (CI)")
    env = {k: v for k, v in os.environ.items() if k != "CONDA_DEFAULT_ENV"}
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "import argumentation_analysis.core.environment; print('IMPORT_OK')",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert (
        "IMPORT_OK" in proc.stdout
    ), f"import crashed outside a conda shell — stderr tail: {proc.stderr[-400:]!r}"
