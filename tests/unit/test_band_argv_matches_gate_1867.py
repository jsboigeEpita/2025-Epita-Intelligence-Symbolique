"""The requires_api band runs what the gate deselects, on the gate's argv (#1867).

``ci.yml`` "Run automated tests" deselects ``requires_api``; the two jobs of
``requires_api_band.yml`` select it. A directory the gate names but the band
does not leaves its ``requires_api`` tests run by no lane: #2823 admitted
``tests/agents/`` to the gate and marked 8 of its tests ``requires_api``, and
the band's argv did not follow.

The live job carries the gate's argv exactly. The replay-band job replays
committed cassettes, so a directory whose tests have none cannot enter it
without making ``miss_replay`` red: each such directory is named in
``REPLAY_PENDING`` with the issue that owns its admission, and an entry that
outlives the admission fails too.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
BAND_YML = ROOT / ".github" / "workflows" / "requires_api_band.yml"

PYTEST_CALL = "--no-capture-output pytest "
GATE_FILTER = '-m "not slow and not requires_api"'
MARKER_ASSIGN = '$marker = "'
LIVE = "requires_api and llm_light"
REPLAY = "requires_api and not llm_light"

# Gate directory -> issue that owns its admission to the replay-band job.
REPLAY_PENDING = {"tests/agents/": "#2829"}


def _paths(line: str) -> list:
    """Positional test paths of a pytest call, up to its first option."""
    paths = []
    for arg in line.split(PYTEST_CALL, 1)[1].split():
        if arg.startswith("-"):
            break
        paths.append(arg)
    return paths


def _gate_paths() -> list:
    calls = [
        line
        for line in CI_YML.read_text(encoding="utf-8").splitlines()
        if PYTEST_CALL in line and GATE_FILTER in line
    ]
    assert len(calls) == 1, f"expected 1 gate pytest call in ci.yml, found {len(calls)}"
    return _paths(calls[0])


def _band_paths() -> dict:
    """Paths of each band job's pytest call, keyed by the marker it selects."""
    calls = {}
    marker = None
    for line in BAND_YML.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(MARKER_ASSIGN):
            marker = stripped[len(MARKER_ASSIGN) :].split('"', 1)[0]
        elif PYTEST_CALL in line:
            assert marker is not None, "band pytest call with no $marker before it"
            assert marker not in calls, f"two band pytest calls under {marker!r}"
            calls[marker] = _paths(line)
    return calls


def test_band_has_one_live_and_one_replay_call():
    assert set(_band_paths()) == {LIVE, REPLAY}


def test_live_band_carries_the_gate_argv():
    gate, live = _gate_paths(), _band_paths()[LIVE]
    assert live == gate, (
        "the live band must select requires_api on exactly the gate's argv; "
        f"gate only: {[p for p in gate if p not in live]}, "
        f"band only: {[p for p in live if p not in gate]}"
    )


def test_replay_band_carries_the_gate_argv_minus_named_pending():
    gate, replay = _gate_paths(), _band_paths()[REPLAY]
    extra = [p for p in replay if p not in gate]
    assert not extra, f"replay-band argv names paths the gate does not: {extra}"
    missing = [p for p in gate if p not in replay]
    unnamed = [p for p in missing if p not in REPLAY_PENDING]
    assert not unnamed, (
        f"gate paths absent from the replay-band argv with no owner: {unnamed}; "
        "admit them or name them in REPLAY_PENDING with their issue"
    )
    stale = [p for p in REPLAY_PENDING if p not in missing]
    assert not stale, (
        f"REPLAY_PENDING names {stale}, which the replay-band argv already "
        "carries or the gate no longer names: remove the entry"
    )
    assert replay == [p for p in gate if p in replay], "replay-band argv order differs"
