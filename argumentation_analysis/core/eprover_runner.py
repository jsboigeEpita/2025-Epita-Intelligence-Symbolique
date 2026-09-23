"""EProver subprocess runner (#2516).

Tweety's ``EFOLReasoner.query`` runs E through ``NativeShell`` and returns
``false`` on every outcome other than ``# Proof found!``. That covers an input
E refuses (exit status 3, the message on stderr), a run that ends without a
verdict, and a shell failure: its exception table maps each of them to
``false`` (``javap -c``, Tweety 1.31). Our sites read that ``false`` as
"consistent" or "not entailed". It also runs E without a timeout, and
``--auto-schedule`` forks a child that outlives its parent when only the
parent is killed (measured on Windows, E 2.0 Turzum: 1.4 GB after four
minutes on a pigeonhole problem).

So Tweety's ``TPTPWriter`` stays the writer, and this runner runs E itself:

* ``# Proof found!`` (exit 0) is ``True``;
* ``# No proof found!`` (exit 1) is ``False``: E saturated without a proof;
* an input E refuses (exit 3) raises ``EProverInputRejected``. We built the
  input, so a caller that degrades lets this one through (#2509, #2511);
* a timeout, or a run without either marker, raises ``RuntimeError`` so the
  caller degrades with the reason. On a timeout the whole process tree is
  killed.
"""

import os
import signal
import subprocess
import tempfile

from argumentation_analysis.core.prover9_runner import SolverInputDefect

# A genuine check on the sets our phases build returns in well under a
# second; the ceiling only stops a runaway search (E ignores ``--cpu-limit``
# on Windows: "Could not set limit RLIMIT_CPU").
EPROVER_DEFAULT_TIMEOUT = 60

# E's exit status for an input it cannot read, measured on a syntax error and
# on a symbol used with two arities.
_EXIT_INPUT_ERROR = 3


class EProverInputRejected(SolverInputDefect):
    """EProver refused its input: exit status 3, its message on stderr
    (#2516). The input is Tweety's ``TPTPWriter`` output for the set
    ``fol_handler`` hands it.
    """


def _kill_tree(process: subprocess.Popen) -> None:
    """Kill ``process`` and the children ``--auto-schedule`` forked."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.kill()
    process.communicate()


def run_eprover(
    problem: str, eprover_path: str, timeout: float = EPROVER_DEFAULT_TIMEOUT
) -> bool:
    """Run E on the TPTP ``problem``: ``True`` iff it proved the conjecture.

    Raises:
        EProverInputRejected: E refused the input (exit status 3).
        RuntimeError: E timed out, or ended without ``# Proof found!`` or
            ``# No proof found!``.
    """
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".p", encoding="utf-8", newline="\n"
        ) as problem_file:
            problem_file.write(problem)
            temp_path = problem_file.name

        process = subprocess.Popen(
            [str(eprover_path), "--auto-schedule", "--tptp3-format", temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name != "nt",
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as e:
            _kill_tree(process)
            raise RuntimeError(
                f"EProver timed out after {timeout}s; no verdict (#2516)."
            ) from e

        if "# Proof found!" in stdout:
            return True
        if "# No proof found!" in stdout:
            return False
        if process.returncode == _EXIT_INPUT_ERROR:
            raise EProverInputRejected(
                f"EProver refused its input (exit {process.returncode}): "
                f"{stderr.strip()}\n--- input ---\n{problem}"
            )
        tail = (stderr.strip() or stdout.strip())[-500:]
        raise RuntimeError(
            f"EProver ended without a verdict (exit {process.returncode}): {tail}"
        )
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.remove(temp_path)
