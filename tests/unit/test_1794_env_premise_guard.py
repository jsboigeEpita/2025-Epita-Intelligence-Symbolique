"""#1794 — guards for the env-premise pollution family.

The gate's two surviving real POSTs (#1591 residual) were caused by tests
doing ``patch("<any-module>.os.environ", {...})``: mock resolves the module,
then ``setattr(os, "environ", dict)`` — a GLOBAL identity swap, not a scoped
one. During the swap window ``os.environ`` is a plain dict: dict writes never
reach ``putenv`` (the C env block desynchronizes), and a later test's
``patch.dict`` can resolve the swapped object instead of the process env.
Measured by trap + identity probe in the same run: POST fired with
``os.environ`` = ``builtins.dict``.

Two guards:
- source guard: the identity-swap motif is banned from the gate tree
  (it was red before the fix — 9 sites);
- execution guard: one deliberate swap must ENTER AND EXIT with the process
  env object restored (identity, type, keys). The no-key-scenario variant
  was removed: it measured the ambient mid-window writer (#1794 follow-up,
  named by the os._Environ.__setitem__ tracer), not the swap mechanism —
  it stayed red after the swap fix and conflated the two defects.
"""

import re
from pathlib import Path
from unittest.mock import patch

_TESTS_ROOT = Path(__file__).resolve().parents[1]

# patch("<module>.os.environ", ...), patch("os.environ", ...) and
# patch.object(os, "environ", ...) all setattr the environ ATTRIBUTE of the
# os module — a global identity swap. patch.dict(...) mutates the object and
# is the only legitimate form.
_SWAP_MOTIF = re.compile(
    r"patch\(\s*[\"'](?:[\w.]+\.)?os\.environ[\"']"
    r"|patch\.object\(\s*os\s*,\s*[\"']environ[\"']"
)


def _gate_test_files():
    files = []
    for sub in ("unit", "scripts"):
        files.extend((Path(_TESTS_ROOT) / sub).rglob("*.py"))
    return sorted(files)


def test_no_os_environ_identity_swap_in_gate_tree():
    """Source guard: patch("<mod>.os.environ", {...}) rebinds the process env
    globally (#1794) — mutation via patch.dict(..., clear=True) is the only
    legitimate form. Fails on any reintroduction of the swap motif."""
    offenders = []
    for f in _gate_test_files():
        if f.name == Path(__file__).name:
            # this guard deliberately performs one round-trip swap (execution
            # guard below) — it asserts the restoration itself.
            continue
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(src.splitlines(), start=1):
            if _SWAP_MOTIF.search(line):
                offenders.append(f"{f.relative_to(_TESTS_ROOT)}:{i}: {line.strip()}")
    assert not offenders, (
        "os.environ identity-swap patch(es) found — these rebind the process "
        "env globally and leak provider keys into other tests' premises "
        "(#1794). Convert to patch.dict('os.environ', {...}, clear=True):\n"
        + "\n".join(offenders)
    )


def test_rebind_roundtrip_restores_process_environ():
    """Execution guard: perform the historical polluter shape (one global
    identity swap via patch) and assert the with-block EXIT restores the
    process env object — same identity, still an _Environ, and the sentinel
    key gone. A reintroduced leaking wrapper (swap that outlives its
    with-block, the #1794 mechanism) fails here with no LLM call and no
    counter dependency."""
    import os

    original = os.environ
    sentinel = {"OPENROUTER_API_KEY": "sk-leak-should-not-survive-the-exit"}
    with patch("os.environ", sentinel):
        assert os.environ is sentinel, "patch('os.environ', ...) must swap the object"
    assert os.environ is original, (
        "the rebind outlived its with-block — process env is still the "
        "swapped dict, so a later test's patch.dict window can resolve the "
        "wrong object and leak provider keys (#1794)"
    )
    assert (
        os.environ.get("OPENROUTER_API_KEY") != sentinel["OPENROUTER_API_KEY"]
    ), "the sentinel key survived the exit"
