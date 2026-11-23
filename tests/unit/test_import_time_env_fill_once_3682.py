"""#3682 — an import-time auto-load fills a file at most once per process.

#3116 closed one half of the landmine: an import-time auto-load no longer
*replaces* a value a caller imposed in-process. The other half stayed open.
The same auto-load still *re-filled a name the caller removed*: four modules
construct ``EnvironmentManager(fill_only=True)`` at import, and each of them
loaded the root ``.env`` again. A seat driver that removes a route variable
after its first import (the #2352 ``final_tranche`` script) saw it come back
with the next unrelated import.

The contract these guards pin:

- **Once.** An import-time auto-load fills a given file at most once per
  process. A later one — another site's first import, a reloaded module —
  writes nothing, whatever names were removed since. The same file reached
  through another spelling of its path counts as loaded.
- **Per file.** The count is kept per file: another file's first fill happens.
- **First fill** (control, #2130): the names the process lacks are filled by
  the first import-time load.
- **Caller wins** (control, #3116): a value set in-process is never replaced.
- **Explicit constructions keep their contract** (control, #1295, #2472): an
  ``EnvironmentManager()`` after an import-time fill still applies the
  replacing policy, still loses to a value the caller started the process
  with, and does not re-arm the import-time fill.

Each probe runs in a subprocess so the imports are genuinely first, and
patches ``env_loader._find_repo_root`` to a throwaway checkout: hermetic, and
it runs on a seat with no ``.env`` of its own.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SEAT_NAME = "ENV3682_SEAT_MODEL"
_FILLED_NAME = "ENV3682_FILLED"
_CALLER_NAME = "ENV3682_CALLER_MODEL"
_FIRST_FILE_NAME = "ENV3682_FIRST_FILE"
_SECOND_FILE_NAME = "ENV3682_SECOND_FILE"

# The synthetic root .env of the main checkout.
_ROOT_ENV = (
    f"{_SEAT_NAME}=from-dotenv\n"
    f"{_FILLED_NAME}=filled-by-load\n"
    f"{_CALLER_NAME}=from-dotenv\n"
    f"{_FIRST_FILE_NAME}=filled-from-the-first-file\n"
)

# Every import statement a probe can run, by id.
_STEPS: Dict[str, str] = {
    # The four modules that construct EnvironmentManager(fill_only=True) at
    # module level.
    "core_environment": "import argumentation_analysis.core.environment",
    "config_settings": "import argumentation_analysis.config.settings",
    "legacy_loader": "import project_core.core_from_scripts.load_dotenv",
    "webapp_orchestrator": "import scripts.apps.webapp.unified_web_orchestrator",
    # What PR #3678's fallacy plugin imports at module level.
    "invoke_callables": "import argumentation_analysis.orchestration.invoke_callables",
    # Its own import-time load goes through config.settings.
    "fallacy_plugin": "import argumentation_analysis.plugins.fallacy_workflow_plugin",
    # What tests/integration/argumentation_analysis/test_hardening_cases.py
    # does after deleting a name the root .env may declare.
    "settings_reloaded": "importlib.reload(argumentation_analysis.config.settings)",
}
_SITES = (
    "core_environment",
    "config_settings",
    "legacy_loader",
    "webapp_orchestrator",
)

# (first step, second step, root the second step's loader resolves to)
_CASES = [
    # Every ordered pair of sites: whichever loads first, no later one refills.
    *[
        (first, second, "checkout")
        for first in _SITES
        for second in _SITES
        if first != second
    ],
    # The chain measured in #3682: the fallacy plugin, then invoke_callables.
    ("fallacy_plugin", "invoke_callables", "checkout"),
    ("config_settings", "settings_reloaded", "checkout"),
    # The same file, reached through another spelling of its path.
    ("config_settings", "core_environment", 'checkout / ".." / checkout.name'),
]

# The #2352 seat driver's gesture between two imports.
_PROBE = r"""
import importlib, json, os, sys
from pathlib import Path
checkout = Path(sys.argv[1])
import argumentation_analysis.config.env_loader as loader
loader._find_repo_root = lambda: checkout
# Imposed AFTER env_loader's snapshot: the exact #3116 shape.
os.environ[{seat!r}] = "seat-imposed"
os.environ.pop({filled!r}, None)
{first_import}
first = os.environ.get({filled!r})
os.environ.pop({filled!r}, None)
loader._find_repo_root = lambda: {second_root}
{second_import}
print("PROBE_RESULT=" + json.dumps({{
    "seat": os.environ.get({seat!r}),
    "first": first,
    "after_second": os.environ.get({filled!r}),
}}))
"""

# The count is per file: a second root .env gets its own first fill.
_TWO_FILES_PROBE = r"""
import json, os, sys
from pathlib import Path
checkout, other = Path(sys.argv[1]), Path(sys.argv[2])
import argumentation_analysis.config.env_loader as loader
loader._find_repo_root = lambda: checkout
import argumentation_analysis.config.settings
loader._find_repo_root = lambda: other
import argumentation_analysis.core.environment
print("PROBE_RESULT=" + json.dumps({{
    "first_file": os.environ.get({first_file!r}),
    "second_file": os.environ.get({second_file!r}),
}}))
"""

# An explicit construction after an import-time fill.
_EXPLICIT_PROBE = r"""
import json, os, sys
from pathlib import Path
checkout = Path(sys.argv[1])
import argumentation_analysis.config.env_loader as loader
loader._find_repo_root = lambda: checkout
os.environ[{seat!r}] = "seat-imposed"
import argumentation_analysis.config.settings
imported = os.environ.get({filled!r})
# The #1295 shape: a value something else set in-process.
os.environ[{filled!r}] = "left-by-another-env"
explicit = loader.EnvironmentManager()
after_explicit = {{
    "filled": os.environ.get({filled!r}),
    "seat": os.environ.get({seat!r}),
    "caller": os.environ.get({caller!r}),
    "loaded": explicit.dotenv_loaded,
}}
os.environ.pop({filled!r}, None)
import argumentation_analysis.core.environment
print("PROBE_RESULT=" + json.dumps({{
    "imported": imported,
    "after_explicit": after_explicit,
    "after_next_import": os.environ.get({filled!r}),
}}))
"""

_SYNTHETIC_NAMES = (
    _SEAT_NAME,
    _FILLED_NAME,
    _CALLER_NAME,
    _FIRST_FILE_NAME,
    _SECOND_FILE_NAME,
)


def _run_probe(
    tmp_path: Path, template: str, caller_value: str = "", **fields: str
) -> dict:
    """Run ``template`` in a fresh interpreter over a throwaway checkout."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".env").write_text(_ROOT_ENV, encoding="utf-8")
    other = tmp_path / "other"
    other.mkdir()
    (other / ".env").write_text(
        f"{_SECOND_FILE_NAME}=filled-from-the-second-file\n", encoding="utf-8"
    )

    env = os.environ.copy()
    for name in _SYNTHETIC_NAMES:
        env.pop(name, None)
    if caller_value:
        env[_CALLER_NAME] = caller_value
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-c", template.format(**fields), str(checkout), str(other)],
        cwd=str(tmp_path),
        env=env,
        text=True,
        capture_output=True,
        # The plugin chain imports torch and semantic kernel: seconds warm, more
        # on a cold runner.
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    marker = [
        line for line in proc.stdout.splitlines() if line.startswith("PROBE_RESULT=")
    ]
    assert marker, f"probe printed no result — stdout tail: {proc.stdout[-500:]!r}"
    return json.loads(marker[-1][len("PROBE_RESULT=") :])


@pytest.mark.parametrize(
    ("first", "second", "second_root"),
    _CASES,
    ids=[
        "-".join(
            part for part in (first, second, "" if root == "checkout" else "spelling")
        )
        for first, second, root in _CASES
    ],
)
def test_a_later_import_time_load_does_not_refill_a_removed_name(
    tmp_path: Path, first: str, second: str, second_root: str
) -> None:
    result = _run_probe(
        tmp_path,
        _PROBE,
        seat=_SEAT_NAME,
        filled=_FILLED_NAME,
        first_import=_STEPS[first],
        second_import=_STEPS[second],
        second_root=second_root,
    )

    assert result["first"] == "filled-by-load", (
        f"{first} -> {second}: the first import-time load stopped filling a name "
        "the process did not have — #2130's contract must survive #3682."
    )
    assert result["seat"] == "seat-imposed", (
        f"{first} -> {second}: an import-time load replaced a value set "
        f"in-process — got {result['seat']!r}. This is the #3116 half."
    )
    assert result["after_second"] is None, (
        f"{first} -> {second}: the caller removed {_FILLED_NAME} after the first "
        f"import-time load, and the next one filled it again (got "
        f"{result['after_second']!r}). An unrelated import undoes the caller's "
        "removal: the #3682 landmine."
    )


def test_the_count_is_kept_per_file(tmp_path: Path) -> None:
    result = _run_probe(
        tmp_path,
        _TWO_FILES_PROBE,
        first_file=_FIRST_FILE_NAME,
        second_file=_SECOND_FILE_NAME,
    )

    assert result["first_file"] == "filled-from-the-first-file"
    assert result["second_file"] == "filled-from-the-second-file", (
        "the once-per-file count was applied once per process: the second root "
        ".env was never filled — #2130's contract for that file."
    )


def test_an_explicit_construction_keeps_its_contract(tmp_path: Path) -> None:
    result = _run_probe(
        tmp_path,
        _EXPLICIT_PROBE,
        caller_value="from-caller",
        seat=_SEAT_NAME,
        filled=_FILLED_NAME,
        caller=_CALLER_NAME,
    )

    assert result["imported"] == "filled-by-load"
    assert result["after_explicit"] == {
        # The root .env replaces a value set in-process (#1295) ...
        "filled": "filled-by-load",
        "seat": "from-dotenv",
        # ... and loses to the value the caller started the process with (#2472).
        "caller": "from-caller",
        "loaded": True,
    }
    assert result["after_next_import"] is None, (
        "an explicit load re-armed the import-time fill: the next import "
        f"refilled the removed name (got {result['after_next_import']!r})."
    )
