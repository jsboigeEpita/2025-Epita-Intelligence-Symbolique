"""#2834 — the eight remaining census walks read the git index, not the seat.

#2821 converted six guards to ``iter_tracked_files``; this file holds the
born-red witnesses for the walks that remained — the seven #2834
enumerated, plus #2393's kernel-double census, whose omission was the
issue's (measured by the coordinator's review: an eighth ``iter_files``
caller lived under ``tests/unit/argumentation_analysis/``). Each entry
plants a gitignored file a guard's population would read under a
filesystem walk — shaped to flip that guard's verdict — then runs the
guard and asserts the verdict does not move. Before the conversion every
entry reddened: the planted file entered the population and tripped the
guard. After it, the index cannot list what the seat added (#2821: a
census that counts what CI never runs measures the seat, not the
repository).

Plants live under ``.playwright-mcp/`` — gitignored at any depth
(``.gitignore``) and skipped by pytest collection (``norecursedirs`` holds
``.*``) — except #2486's, whose own collection filter already drops
``_``/``.``-prefixed directories; that one is ignored through
``.git/info/exclude``, git's third ignore source, so the plant still sits
outside the index without touching a tracked file.

The plant contents are written as split string concatenations where a
guard scans THIS file too: #1794's motif reads line text, and a witness
that tripped its own guard would be a permanent red, not a witness.
"""

import importlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Each plant, assembled so this file never trips the guard it plants for.
_MISNAMED_AUTHENTIC_PLANT = (
    "def authentic_service_2834():\n" "    return create_llm_service()\n"
)
_UNBOUND_PATCH_PLANT = (
    "from unittest.mock import patch\n"
    "patch('tests.support.tree_walk.absent_2834_attr')\n"
)
_ORPHAN_WORKER_PLANT = "'''Seat-local orphan worker (#2834 probe).'''\n"
# #1794 scans line text: ``patch(`` must not appear contiguous on one line
# of THIS file, so the call is split across a concatenation.
_SWAP_MOTIF_PLANT = (
    "from unittest import mock\n" "mock.pa" + "tch('probe2834.os.environ', {})\n"
)
_BARE_DOTENV_PLANT = "from dotenv import load_dotenv\nload_dotenv()\n"
_EXTRA_RESOLVER_PLANT = "def find_extra_for_capability(capability):\n" "    return []\n"
_ENV_SEEDER_PLANT = "import os\nos.environ['PROBE_2834'] = '1'\n"
# #2393 counts Assign targets whose name contains "kernel" bound to an
# unspecced MagicMock() — one site, enough to trip its census.
_KERNEL_DOUBLE_PLANT = (
    "from unittest.mock import MagicMock\n" "kernel_2834 = MagicMock()\n"
)


def _assert_gitignored(target: Path) -> None:
    checked = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", str(target)],
        capture_output=True,
    )
    assert checked.returncode == 0, (
        f"{target.relative_to(ROOT)} is NOT gitignored — the plant would be "
        "tracked, so its invisibility would prove nothing (#2834)"
    )


def _plant(relpath: str, content: str):
    """Write a gitignored file into the real checkout; return its cleanup."""
    target = ROOT / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_gitignored(target)
    target.write_text(content, encoding="utf-8")

    def _cleanup():
        target.unlink(missing_ok=True)
        try:
            target.parent.rmdir()  # the probe dir, when we created it
        except OSError:
            pass  # seat-local content already lived there

    return _cleanup


def _exclude_path() -> Path:
    """Resolve ``info/exclude`` through git itself (#2843 review): in a
    linked worktree ``ROOT/.git`` is a file, so concatenating the path makes
    ``mkdir`` raise FileExistsError and the witness reddens in every
    worktree. ``--git-path`` returns this checkout's effective exclude file
    (common-dir, so a worktree resolves to the main repository's), absolute
    or relative to ``ROOT``."""
    resolved = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--git-path", "info/exclude"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    path = Path(resolved)
    return path if path.is_absolute() else ROOT / path


def _plant_via_exclude(relpath: str, content: str):
    """#2486's plant: ignored through ``.git/info/exclude`` — its census
    filter drops ``_``/``.``-prefixed directories, so ``.playwright-mcp``
    would be invisible even to the fs walk being disproven."""
    target = ROOT / relpath
    exclude = _exclude_path()
    exclude.parent.mkdir(parents=True, exist_ok=True)
    before = exclude.read_text(encoding="utf-8") if exclude.exists() else None

    def _restore_exclude():
        if before is None:
            exclude.unlink(missing_ok=True)
        else:
            exclude.write_text(before, encoding="utf-8")

    with open(exclude, "a", encoding="utf-8") as handle:
        handle.write(f"/{relpath}\n")
    try:
        _assert_gitignored(target)
        target.write_text(content, encoding="utf-8")
    except BaseException:
        # The exclude line lives in the REAL checkout's .git — a failure
        # after the append must not leave it behind (coordinator review:
        # the cleanup closure is never returned on the raising path).
        _restore_exclude()
        raise

    def _cleanup():
        target.unlink(missing_ok=True)
        _restore_exclude()

    return _cleanup


def _run_guard(module_name: str, callable_name: str, cache_to_clear: str | None):
    module = importlib.import_module(module_name)
    if cache_to_clear is not None:
        # An lru_cache keyed by root would serve a verdict from before the
        # plant existed — clearing it is what makes the witness measure the
        # walk, not a stale population (#2696's census is cached).
        getattr(module, cache_to_clear).cache_clear()
    guard = getattr(module, callable_name)
    guard()


@pytest.mark.parametrize(
    ("module_name", "callable_name", "cache_to_clear", "planter"),
    [
        pytest.param(
            "tests.unit.test_authentic_helper_names_2604",
            "test_no_helper_named_authentic_serves_the_pytest_mock",
            None,
            lambda: _plant(
                "tests/unit/.playwright-mcp/f2834_authentic.py",
                _MISNAMED_AUTHENTIC_PLANT,
            ),
            id="2604-misnamed-authentic-helper",
        ),
        pytest.param(
            "tests.unit.test_worker_scripts_have_a_launcher_2696",
            "test_every_worker_script_has_a_launcher",
            "_census",
            lambda: _plant(
                "tests/integration/.playwright-mcp/worker_2834_probe.py",
                _ORPHAN_WORKER_PLANT,
            ),
            id="2696-orphan-worker",
        ),
        pytest.param(
            "tests.unit.test_1794_env_premise_guard",
            "test_no_os_environ_identity_swap_in_gate_tree",
            None,
            lambda: _plant(
                "tests/unit/.playwright-mcp/f2834_swap.py",
                _SWAP_MOTIF_PLANT,
            ),
            id="1794-env-swap-motif",
        ),
        pytest.param(
            "tests.unit.project_core.managers.test_single_dotenv_loader_2708",
            "test_production_dotenv_has_one_loader",
            None,
            lambda: _plant(
                "argumentation_analysis/.playwright-mcp/f2834_dotenv.py",
                _BARE_DOTENV_PLANT,
            ),
            id="2708-bare-dotenv-loader",
        ),
        pytest.param(
            "tests.unit.argumentation_analysis.orchestration."
            "test_capability_resolver_surface_1980",
            "test_resolver_surface_is_the_enumerated_five",
            None,
            lambda: _plant(
                "argumentation_analysis/.playwright-mcp/f2834_resolver.py",
                _EXTRA_RESOLVER_PLANT,
            ),
            id="1980-extra-resolver-spelling",
        ),
        pytest.param(
            "tests.integration.triage.test_import_does_not_seed_env",
            "test_no_module_level_env_seeder_in_tests",
            None,
            lambda: _plant(
                "tests/unit/.playwright-mcp/test_f2834_seeder.py",
                _ENV_SEEDER_PLANT,
            ),
            id="seed-env-module-level-seeder",
        ),
    ],
)
def test_a_gitignored_file_cannot_flip_the_verdict(
    module_name, callable_name, cache_to_clear, planter
):
    cleanup = planter()
    try:
        _run_guard(module_name, callable_name, cache_to_clear)
    finally:
        cleanup()


def test_2486_scan_cannot_flip_the_verdict():
    """#2486's guard verdict, run directly: its test takes a module-scoped
    fixture, so the witness replays the guard's own assertion — a dead patch
    target list that must stay empty with the plant in the tree."""
    from tests.unit.test_patch_targets_resolve_2486 import ROOT as _root, scan

    cleanup = _plant_via_exclude("tests/f2834_unbound.py", _UNBOUND_PATCH_PLANT)
    try:
        dead, _census = scan(_root)
        assert (
            dead == []
        ), "patch targets the patched module never reads (#2486):\n" + "\n".join(dead)
    finally:
        cleanup()


def test_2393_census_cannot_flip_the_verdict():
    """#2393's guard, run directly: its test declares ``capsys`` only so its
    prints are captured — the body never touches it — so the witness passes
    ``None``. An unspecced kernel double in a gitignored file must not
    enter the census."""
    from tests.unit.argumentation_analysis.test_kernel_double_spec_guard_2393 import (  # noqa: E501
        test_no_new_unspecced_kernel_doubles as _guard,
    )

    cleanup = _plant("tests/unit/.playwright-mcp/f2834_kernel.py", _KERNEL_DOUBLE_PLANT)
    try:
        _guard(None)
    finally:
        cleanup()


def test_the_plants_are_actually_plantable():
    """Negative control on the instrument: each plant site is gitignored
    today. A seat whose ignore rules change must redden HERE, not pass a
    witness whose plants were born invisible."""
    for relpath in (
        "tests/unit/.playwright-mcp/f2834_authentic.py",
        "tests/integration/.playwright-mcp/worker_2834_probe.py",
        "tests/unit/.playwright-mcp/f2834_swap.py",
        "argumentation_analysis/.playwright-mcp/f2834_dotenv.py",
        "argumentation_analysis/.playwright-mcp/f2834_resolver.py",
        "tests/unit/.playwright-mcp/test_f2834_seeder.py",
        "tests/unit/.playwright-mcp/f2834_kernel.py",
    ):
        _assert_gitignored(ROOT / relpath)
