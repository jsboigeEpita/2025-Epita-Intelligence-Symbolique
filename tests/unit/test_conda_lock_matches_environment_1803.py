"""conda-lock.yml provides what environment.yml asks for (#1803 step 5).

CI installs the ``projet-is`` env from the tracked ``conda-lock.yml`` through
``.github/actions/setup-projet-is`` (user decision 2026-09-28, option b of
#1803 step 5). ``environment.yml`` stays the input the lock is solved from.

That split has one failure mode: a dependency added, or a pin changed, in
``environment.yml`` without regenerating the lock. CI would keep installing the
old lock and nothing would say so; the lock would lie the other way round from
the stale one #1803 found. These tests make that edit red in the gate.

They read both files as data: no solver, no network, no conda-lock import. They
check that every spec of ``environment.yml`` is met by a locked package, not
that the lock is byte-for-byte the output of a fresh solve (a fresh solve moves
with the channels every day, which is what the lock exists to stop).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / "environment.yml"
LOCK_FILE = ROOT / "conda-lock.yml"
ACTION_FILE = ROOT / ".github" / "actions" / "setup-projet-is" / "action.yml"
WORKFLOWS = ROOT / ".github" / "workflows"

# The conda spec forms environment.yml uses. Any other form fails the parse
# below instead of being skipped: a spec this test cannot read is a spec it
# does not check.
_CONDA_SPEC = re.compile(
    r"^(?P<name>[A-Za-z0-9_.\-]+)\s*(?:(?P<op>==|>=|<=|=|<)\s*(?P<ver>\S+))?$"
)


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def env() -> dict:
    return _load(ENV_FILE)


@pytest.fixture(scope="module")
def lock() -> dict:
    return _load(LOCK_FILE)


def _locked(lock: dict, manager: str) -> dict[str, str]:
    return {
        canonicalize_name(p["name"]): p["version"]
        for p in lock["package"]
        if p["manager"] == manager
    }


def _split_env_deps(env: dict) -> tuple[list[str], list[str]]:
    conda_specs: list[str] = []
    pip_specs: list[str] = []
    for dep in env["dependencies"]:
        if isinstance(dep, dict):
            assert set(dep) == {"pip"}, f"unexpected mapping in dependencies: {dep}"
            pip_specs.extend(dep["pip"])
        else:
            conda_specs.append(dep)
    return conda_specs, pip_specs


def _conda_spec_met(op: str | None, wanted: str | None, locked: str) -> bool:
    if op is None:
        return True
    if op == "==":
        return locked == wanted
    if op == "=":  # conda: version prefix, `=1.25.0` means 1.25.0.*
        return locked == wanted or locked.startswith(wanted + ".")
    if op == ">=":
        return Version(locked) >= Version(wanted)
    if op == "<":  # #2857: the werkzeug single-provider pin
        return Version(locked) < Version(wanted)
    # op == "<="
    return Version(locked) <= Version(wanted)


def test_lock_targets_the_ci_platform_from_environment_yml(env, lock):
    meta = lock["metadata"]
    assert meta["platforms"] == ["win-64"], "CI runs on windows-latest only"
    assert meta["sources"] == ["environment.yml"]
    assert [c["url"] for c in meta["channels"]] == env[
        "channels"
    ], "environment.yml channels changed since the lock was generated: regenerate it"


def test_every_conda_spec_is_met_by_the_lock(env, lock):
    locked = _locked(lock, "conda")
    conda_specs, _ = _split_env_deps(env)
    assert conda_specs, "no conda spec read from environment.yml"
    problems = []
    for spec in conda_specs:
        m = _CONDA_SPEC.match(spec.strip())
        if m is None:
            problems.append(f"{spec!r}: spec form this test cannot read")
            continue
        name = canonicalize_name(m["name"])
        if name not in locked:
            problems.append(f"{spec!r}: not in conda-lock.yml")
            continue
        try:
            ok = _conda_spec_met(m["op"], m["ver"], locked[name])
        except InvalidVersion as exc:
            problems.append(
                f"{spec!r}: cannot compare with locked {locked[name]} ({exc})"
            )
            continue
        if not ok:
            problems.append(f"{spec!r}: locked {locked[name]}")
    assert not problems, (
        "environment.yml asks for what conda-lock.yml does not provide; regenerate "
        "the lock (command in .github/actions/setup-projet-is/action.yml):\n  "
        + "\n  ".join(problems)
    )


def test_every_pip_spec_is_met_by_the_lock(env, lock):
    pip_locked = _locked(lock, "pip")
    conda_locked = _locked(lock, "conda")
    _, pip_specs = _split_env_deps(env)
    assert pip_specs, "no pip spec read from environment.yml"
    problems = []
    for spec in pip_specs:
        req = Requirement(spec)
        name = canonicalize_name(req.name)
        # conda-lock leaves a pip spec out of the pip section when a conda
        # package of the same name already provides it (psutil, for one).
        version = pip_locked.get(name) or conda_locked.get(name)
        if version is None:
            problems.append(f"{spec!r}: not in conda-lock.yml")
            continue
        if req.specifier and not req.specifier.contains(
            Version(version), prereleases=True
        ):
            problems.append(f"{spec!r}: locked {version}")
    assert not problems, (
        "environment.yml asks for what conda-lock.yml does not provide; regenerate "
        "the lock (command in .github/actions/setup-projet-is/action.yml):\n  "
        + "\n  ".join(problems)
    )


def test_every_locked_package_is_pinned_by_checksum(lock):
    unpinned = [
        f"{p['manager']}:{p['name']}"
        for p in lock["package"]
        if not p.get("url") or not p.get("hash", {}).get("sha256")
    ]
    assert lock["package"], "empty lock"
    assert not unpinned, f"locked packages without url or sha256: {unpinned}"


def test_ci_installs_the_lock_and_nothing_else(lock):
    """Every workflow gets projet-is from the action; the action pins the
    installer the lock itself carries."""
    re_solvers = [
        wf.name
        for wf in sorted(WORKFLOWS.glob("*.yml"))
        if "environment-file:" in wf.read_text(encoding="utf-8")
        or "setup-miniconda@" in wf.read_text(encoding="utf-8")
    ]
    assert not re_solvers, (
        f"{re_solvers} set up conda directly; use ./.github/actions/setup-projet-is "
        "so every workflow runs the locked env (#1803 step 5)"
    )
    users = [
        wf.name
        for wf in sorted(WORKFLOWS.glob("*.yml"))
        if "uses: ./.github/actions/setup-projet-is" in wf.read_text(encoding="utf-8")
    ]
    assert "ci.yml" in users, "the gate workflow no longer uses the locked env"

    action = ACTION_FILE.read_text(encoding="utf-8")
    assert "conda-lock install --name projet-is conda-lock.yml" in action
    pinned = re.findall(r'"conda-lock=([^"]+)"', action)
    assert len(pinned) == 1, f"expected one pinned installer version, found {pinned}"
    assert (
        pinned[0] == _locked(lock, "conda")["conda-lock"]
    ), "the CI installer and the conda-lock in the lock differ"
