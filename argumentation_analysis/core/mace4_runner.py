"""Mace4 (LADR model-finder) subprocess runner — FP-19 #1243.

Mace4 is the vendored LADR ``2009-11A`` model-finder (``libs/prover9/bin/mace4.exe``,
the sibling of Prover9, sharing ``cygwin1.dll``). It is wired here as a
**selectable, comparable** FOL backend (mandate R468: "tous les solvers handy …
pour comparer les résultats").

Why Mace4 is the *consistency* side of the comparison
----------------------------------------------------
Mace4 searches for a **finite model** of the assumptions. It is a
**semi-decision procedure for satisfiability**:

* a model found ⇒ the KB is **CONSISTENT** (sound — a real model exists);
* no model found is only conclusive *within the searched domain bound* — for
  arbitrary FOL "no model ≤ N" does **not** prove inconsistency (the KB may have
  only larger or infinite models). It is the sound complement of a refutation
  prover (EProver/Prover9 prove **INCONSISTENT**); together they cross-validate.

Two firsthand facts (po-2025, 2026-06-23, synthetic atoms) shape this runner:

1. **An unbounded model search hangs forever on an inconsistent KB.**
   ``{P(a), -P(a)}`` with no domain bound climbs domain sizes (660, 661, …)
   looking for a model and never terminates. So Mace4 MUST be run **bounded**
   (``-n 2 -N <max_domain>``) AND with a **hard subprocess timeout** — an
   unbounded hang is a *silent* failure (anti-théâtre #1019; the #1240 Prover9
   no-timeout bug, in the Mace4 dimension).
2. **Bounded, it terminates cleanly:** ``{P(a)}`` → ``exit (max_models)`` with a
   ``MODEL`` (consistent); ``{P(a), -P(a)}`` → ``exit (exhausted)`` with
   ``current_models=0`` (no finite model ≤ N).

A timeout / crash / fatal-parse is surfaced as ``RuntimeError`` so the caller
falls back honestly — never a fabricated verdict on degraded execution.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

MACE4_BIN_DIR = Path(__file__).parent.parent.parent / "libs" / "prover9" / "bin"
MACE4_EXECUTABLE = MACE4_BIN_DIR / "mace4.exe"

# Default bounded search. The bound is the maximum domain (model) size Mace4 will
# try; "no model ≤ this size" is what an ``exhausted`` exit reports. Ground /
# propositional contradictions exhaust at tiny sizes, so a modest bound decides
# the common cases fast while keeping the unbounded hang impossible.
MACE4_DEFAULT_MAX_DOMAIN = 10
# A hard ceiling: a genuine bounded search on a small KB returns well under 1s.
MACE4_DEFAULT_TIMEOUT = 30


def run_mace4(
    input_content: str,
    max_domain: int = MACE4_DEFAULT_MAX_DOMAIN,
    timeout: int = MACE4_DEFAULT_TIMEOUT,
) -> str:
    """Run Mace4 on LADR ``input_content`` and return its stdout.

    Args:
        input_content: LADR text, e.g. ``formulas(assumptions). P(a). end_of_list.``
        max_domain: upper bound on the model (domain) size searched (``-N``).
            REQUIRED to be finite — an unbounded search hangs on an
            inconsistent KB.
        timeout: hard subprocess timeout in seconds. A timeout is re-raised as
            ``RuntimeError`` so the caller can fall back honestly.

    Returns:
        Mace4 stdout (whether a model was found or the search was exhausted —
        both are SEMANTIC outcomes the caller interprets via
        :func:`interpret_mace4_output`).

    Raises:
        FileNotFoundError: if the Mace4 binary is not present.
        RuntimeError: on timeout (deadlock / runaway search) or a fatal Mace4
            parse error (malformed input must surface, not masquerade as a
            verdict — #1019).
    """
    if not MACE4_EXECUTABLE.is_file():
        raise FileNotFoundError(f"Mace4 executable not found at {MACE4_EXECUTABLE}")

    temp_input_path = None
    try:
        # ASCII + Unix newlines, mirroring the Prover9 runner (the cygwin binary
        # expects LF, not CRLF).
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".in", encoding="ascii", newline="\n"
        ) as temp_input_file:
            temp_input_file.write(input_content)
            temp_input_path = temp_input_file.name

        # Mace4 needs cygwin1.dll resolvable → run with cwd = the bin dir; the
        # input path is absolute so it is found regardless of cwd.
        executable_path = os.path.normpath(os.path.abspath(MACE4_EXECUTABLE))
        command = [
            executable_path,
            "-n",
            "2",
            "-N",
            str(max_domain),
            "-f",
            os.path.abspath(temp_input_path),
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(MACE4_BIN_DIR),
                encoding="cp1252",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"Mace4 timed out after {e.timeout}s (unbounded/large model "
                "search) — surfacing instead of hanging the pipeline (#1019/#1240)."
            ) from e

        stdout = process.stdout or ""
        # A genuine parse error must surface, not be read as "no model".
        if "Fatal error" in stdout or "Fatal error" in (process.stderr or ""):
            raise RuntimeError(
                "Mace4 reported a fatal error (likely malformed LADR input):\n"
                f"{stdout}\n{process.stderr or ''}"
            )
        return stdout
    finally:
        if temp_input_path is not None and os.path.exists(temp_input_path):
            os.remove(temp_input_path)


def interpret_mace4_output(stdout: str) -> Tuple[Optional[bool], str]:
    """Interpret Mace4 stdout into a tri-state consistency verdict.

    Returns ``(is_consistent, note)``:

    * ``True``  — a finite MODEL was found ⇒ **CONSISTENT** (sound).
    * ``False`` — the bounded search was ``exhausted`` with no model ⇒ no finite
      model up to the domain bound. Reported as inconsistent, but the note makes
      the epistemic status explicit: this is a *bounded model search*, not a
      refutation proof (the sound refutation side is EProver/Prover9).
    * ``None``  — indeterminate (Mace4 stopped for a resource reason such as
      ``max_megs`` / ``max_seconds`` before either finding a model or exhausting
      the search) ⇒ degraded, never a fabricated verdict (#1019).
    """
    # Model found: Mace4 prints a MODEL block and exits with ``max_models`` /
    # ``all_models`` having kept ≥1 model.
    if (
        "============================== MODEL" in stdout
        or "exit (max_models)" in stdout
    ):
        return True, "Mace4: finite model found (consistent — sound)."
    if "exit (exhausted)" in stdout:
        return (
            False,
            "Mace4: search exhausted — no finite model up to the domain bound "
            "(bounded model search, NOT a refutation proof; EProver/Prover9 are "
            "the sound refutation side).",
        )
    # Resource-limited stop (max_megs / max_seconds / etc.) without a verdict.
    return (
        None,
        "Mace4: search stopped without a model or exhaustion (resource limit) — "
        "degraded, no verdict.",
    )
