"""#3116 — an import-time auto-load must not overwrite a value set in-process.

The three modules that load the root ``.env`` **as a side effect of being
imported** (``core.environment``, ``config.settings``, the legacy
``project_core.core_from_scripts.load_dotenv``) all construct an
``EnvironmentManager`` at module level. Its loader replaces every name whose
current value differs from ``_CALLER_ENVIRONMENT`` — the snapshot taken when
``env_loader`` was first imported. A value a caller imposes **after** that
snapshot (a synthetic seat, a test fixture, an entry point's own decision) is
therefore not "caller-set" and gets clobbered by whichever import happens
next. #2352 measured exactly that: importing the orchestration package flipped
the seat's route to the root ``.env``'s.

The contract these guards pin, per site:

- an **import-time** auto-load only fills names the process does not have
  (the convenience bootstrap must never stomp a value someone set);
- an **explicit** ``EnvironmentManager()`` keeps the project policy — root
  ``.env`` replaces an in-process value left by a sub-``.env`` (#1295) — and
  still loses to a value the caller started the process with, even "" (#2472).

Each probe runs in a subprocess so the import is genuinely the first one, and
patches ``env_loader._find_repo_root`` to a throwaway checkout: hermetic, and
it runs on a seat with no ``.env`` of its own.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SEAT_NAME = "ENV3116_SEAT_MODEL"
_FILLED_NAME = "ENV3116_FILLED"

# The synthetic root .env: one name that a caller will have already set
# in-process (must keep the caller's value), one name nobody set (must be
# filled by the auto-load — that is #2130's contract, still owed).
_ROOT_ENV = f"{_SEAT_NAME}=from-dotenv\n{_FILLED_NAME}=filled-by-load\n"

_PROBE = r"""
import json, os, sys
from pathlib import Path
checkout = Path(sys.argv[1])
import argumentation_analysis.config.env_loader as loader
loader._find_repo_root = lambda: checkout
# Imposed AFTER env_loader's snapshot: the exact #3116 shape.
os.environ[{seat!r}] = "seat-imposed"
os.environ.pop({filled!r}, None)
{import_line}
print("PROBE_RESULT=" + json.dumps({{
    "seat": os.environ.get({seat!r}),
    "filled": os.environ.get({filled!r}),
}}))
"""

_SITES = [
    # (id, the import that triggers the module-level EnvironmentManager)
    ("core_environment", "import argumentation_analysis.core.environment"),
    ("config_settings", "import argumentation_analysis.config.settings"),
    (
        "legacy_loader",
        "import project_core.core_from_scripts.load_dotenv",
    ),
    (
        "webapp_orchestrator",
        "import scripts.apps.webapp.unified_web_orchestrator",
    ),
]


@pytest.mark.parametrize(("site", "import_line"), _SITES, ids=[s[0] for s in _SITES])
def test_import_time_load_keeps_an_in_process_value_3116(
    tmp_path: Path, site: str, import_line: str
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".env").write_text(_ROOT_ENV, encoding="utf-8")

    code = _PROBE.format(seat=_SEAT_NAME, filled=_FILLED_NAME, import_line=import_line)
    env = os.environ.copy()
    env.pop(_SEAT_NAME, None)
    env.pop(_FILLED_NAME, None)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-c", code, str(checkout)],
        cwd=str(tmp_path),
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    marker = [
        line for line in proc.stdout.splitlines() if line.startswith("PROBE_RESULT=")
    ]
    assert marker, f"probe printed no result — stdout tail: {proc.stdout[-500:]!r}"
    result = json.loads(marker[-1][len("PROBE_RESULT=") :])

    assert result["seat"] == "seat-imposed", (
        f"{site}: importing this module overwrote a value set in-process after "
        f"env_loader's snapshot — got {result['seat']!r}, expected the caller's "
        "'seat-imposed'. This is the #3116 landmine: any innocent import of the "
        "module re-arms the clobber."
    )
    assert result["filled"] == "filled-by-load", (
        f"{site}: the import-time auto-load stopped filling a name the process "
        "did not have — #2130's contract (consumers import the module for "
        "auto-activation) must survive #3116's repair."
    )
