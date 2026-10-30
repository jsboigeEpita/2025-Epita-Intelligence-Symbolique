"""A band ``--deselect`` flag that matches no selected node is silent (#3294).

``pytest --deselect <id>`` deselects nothing and says nothing when ``<id>``
names no *selected* node: the flag keeps reading as a protection while
providing none. #3039 is the measured instance — it removed ``requires_api``
from ``test_real_sherlock_case_description``, whose flag then matched nothing,
and nothing in the tree noticed for two weeks.

This guard collects the files each call's flags name, under that call's own
marker, and holds every flag to a selected node. A flag that matches nothing
must be named in ``INERT_DESELECT`` with the issue that owns its measurement;
an entry that starts matching again — or whose flag left the workflow — fails
too, so an allowance cannot outlive its cause.

The collect runs pytest in a subprocess over the flagged files only: 27 s to
117 s measured for this file across runs (2026-10-30) — 15 files / 48 nodes
since #3291 removed the inert flag. The subprocess collect dominates: a bare
probe of the same collect costs 21 s. It deliberately carries no ``slow``
marker: excluded from the gate, it would guard nothing.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BAND_YML = ROOT / ".github" / "workflows" / "requires_api_band.yml"

PYTEST_CALL = "--no-capture-output pytest "
MARKER_ASSIGN = '$marker = "'

# Flag -> issue that owns the measurement which made it inert.
# EMPTY since #3291. Its only entry was #3039's flag for
# test_real_sherlock_case_description: that issue removed the test's
# ``requires_api`` marker on its own measurement (0 cache keys; the method
# reads local state), so the test left this call's selection and the flag
# matched nothing. #1867 option (a) authorised the workflow half, and the
# flag is now gone from the replay call — leaving the entry behind would
# trip this guard's symmetry check, which is exactly what that check is for:
# an allowance must not outlive its cause. A future inert flag is named here
# with the issue that measures it, never silenced.
INERT_DESELECT: dict = {}


def _calls() -> dict:
    """Marker -> its ``--deselect`` flags, for the band calls that carry any."""
    calls, marker = {}, None
    for line in BAND_YML.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(MARKER_ASSIGN):
            marker = stripped[len(MARKER_ASSIGN) :].split('"', 1)[0]
        elif PYTEST_CALL in stripped:
            assert marker is not None, "band pytest call with no $marker before it"
            flags = re.findall(r'--deselect "([^"]+)"', stripped)
            if flags:
                calls[marker] = flags
    assert calls, (
        f"no call carrying a --deselect flag was found in {BAND_YML.name}: the "
        "parse found nothing, so the parametrised test below would vanish "
        "instead of failing. A void parse is an error, never a pass."
    )
    return calls


def _selected_nodes(marker: str, files: list) -> set:
    """Node ids the marker selects among ``files``, collected in a subprocess."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *files,
            "--collect-only",
            "-q",
            "-m",
            marker,
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"collect under {marker!r} failed (rc={proc.returncode}): the measurement "
        f"is void, not a verdict\n--- stdout ---\n{proc.stdout[-2000:]}"
        f"\n--- stderr ---\n{proc.stderr[-2000:]}"
    )
    nodes = {
        re.sub(r"\s+\[.*$", "", line).strip().replace("\\", "/")
        for line in proc.stdout.splitlines()
        if "::" in line
    }
    assert nodes, (
        f"collect under {marker!r} returned no node at all: a void measurement, "
        "never a pass"
    )
    return nodes


def _matches(flag: str, nodes: set) -> bool:
    """Whether ``flag`` names a selected node, or the prefix of one."""
    norm = flag.replace("\\", "/")
    return any(
        node == norm or node.startswith(norm + "::") or node.startswith(norm + "[")
        for node in nodes
    )


@pytest.mark.parametrize("marker", sorted(_calls()))
def test_every_band_deselect_matches_a_selected_node(marker):
    flags = _calls()[marker]
    nodes = _selected_nodes(marker, sorted({f.split("::", 1)[0] for f in flags}))

    unnamed = [f for f in flags if f not in INERT_DESELECT and not _matches(f, nodes)]
    assert not unnamed, (
        f"under {marker!r} these --deselect flags match no selected node and are "
        f"silent: {unnamed}; either they are dead and must go, or name them in "
        "INERT_DESELECT with the issue that owns why they are inert"
    )

    stale = [f for f in INERT_DESELECT if f in flags and _matches(f, nodes)]
    assert not stale, (
        f"INERT_DESELECT names {stale}, which matches a selected node again: the "
        "allowance outlived its cause, remove the entry"
    )


def test_inert_deselect_entries_still_name_a_live_flag():
    present = {f for flags in _calls().values() for f in flags}
    gone = [f for f in INERT_DESELECT if f not in present]
    assert not gone, (
        f"INERT_DESELECT names {gone}, which the workflow's argv no longer "
        "carries: remove the entry"
    )
