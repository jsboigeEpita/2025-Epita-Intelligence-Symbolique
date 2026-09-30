"""#2884 — a package provided by BOTH conda and pip runs a version no
entry describes.

CI installs the conda half of ``conda-lock.yml`` first, then the pip
half: a pip entry overwrites the conda files while conda's metadata
still names its own version — the env then runs a version that no
single lock entry describes, and nothing reported it. #2861 repaired
the file-level instance of the same shape (two providers of
``libiomp5md.dll`` stopped torch from loading); this guard catches the
package-level class.

Measured on ``main``'s lock at the issue's opening: ``werkzeug`` (conda
3.1.8 for flask, pip 3.1.1 for openapi-core) and ``websockets`` (conda
16.1.1 for uvicorn-standard, pip 15.0.1 for semantic-kernel). The
settlement is one provider per name, pinned conda-side (``#2857`` did
werkzeug; this issue does websockets).

Conda-only aliases — the same name listed twice with the SAME manager
and version (``email-validator``, ``typing-extensions`` on the lock at
issue time) — are not the defect and are not flagged: nothing overwrites
anything.

Privacy: package names and version specifiers only. No JVM, no LLM, no
network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
LOCK_FILE = ROOT / "conda-lock.yml"


@pytest.fixture(scope="module")
def lock() -> dict:
    return yaml.safe_load(LOCK_FILE.read_text(encoding="utf-8"))


def _requirers(lock: dict, wanted: str) -> list[str]:
    """``manager name version (spec)`` of every entry whose dependencies
    ask for ``wanted`` — the "who asks" the failure message carries."""
    found = []
    for entry in lock["package"]:
        spec = (entry.get("dependencies") or {}).get(wanted)
        if spec is not None:
            found.append(
                f"{entry['manager']} {entry['name']} {entry['version']} "
                f"({spec or 'any'})"
            )
    return found


def test_no_package_has_both_a_conda_and_a_pip_entry(lock: dict) -> None:
    """The guard: group the lock's entries by normalised name; a group
    whose managers differ is a two-provider name, and the run FAILS
    naming, for each, both versions and who asks for each."""
    entries: dict[str, list[dict]] = {}
    for entry in lock["package"]:
        entries.setdefault(canonicalize_name(entry["name"]), []).append(entry)

    doubles = {
        name: group
        for name, group in entries.items()
        if len({e["manager"] for e in group}) > 1
    }

    assert not doubles, (
        "conda-lock.yml provides these packages from BOTH conda and pip "
        "(CI installs conda then pip, so the pip files overwrite the conda "
        "ones and the env runs a version no entry describes — one provider "
        "per name, #2884):\n"
        + "\n".join(
            f"  - {name}: "
            + " vs ".join(f"{e['manager']} {e['version']}" for e in group)
            + f" — asked by: {', '.join(_requirers(lock, name))}"
            for name, group in sorted(doubles.items())
        )
    )


def test_the_guard_reads_a_two_provider_shape() -> None:
    """The guard is not vacuous: on a minimal two-provider lock it FAILS
    naming the package, both versions, and the requirer (born-red shape,
    #2884's own opening measurement)."""
    fake = {
        "package": [
            {
                "name": "uvicorn-standard",
                "version": "0.52.4",
                "manager": "conda",
                "dependencies": {"websockets": ">=10.4"},
            },
            {
                "name": "websockets",
                "version": "16.1.1",
                "manager": "conda",
                "dependencies": {},
            },
            {
                "name": "semantic-kernel",
                "version": "1.44.0",
                "manager": "pip",
                "dependencies": {"websockets": ">=13,<16"},
            },
            {
                "name": "websockets",
                "version": "15.0.1",
                "manager": "pip",
                "dependencies": {},
            },
        ]
    }
    with pytest.raises(AssertionError, match=r"websockets.*16\.1\.1.*15\.0\.1"):
        test_no_package_has_both_a_conda_and_a_pip_entry(fake)


def test_conda_only_aliases_are_not_the_defect() -> None:
    """The same name twice with ONE manager is the lock's alias habit
    (``email-validator`` at issue time), not an overwrite: not flagged."""
    fake = {
        "package": [
            {
                "name": "email-validator",
                "version": "2.3.0",
                "manager": "conda",
                "dependencies": {},
            },
            {
                "name": "email_validator",
                "version": "2.3.0",
                "manager": "conda",
                "dependencies": {},
            },
        ]
    }
    test_no_package_has_both_a_conda_and_a_pip_entry(fake)
