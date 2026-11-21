# Native failures watch — #2005, #2080, #2894

Each family carries its trigger in its own issue thread. The runner reads
every cycle's `pipeline.log` against the three signatures
(`scripts/panel/run_cycle.py`, table `NATIVE_PATTERNS` — the single source,
printed verbatim below; `tests/unit/scripts/test_native_watch_3540.py`
checks this page carries exactly those strings). The count rides
`pipeline.json` as `native_watch` beside `verdict`; a count that meets a
trigger is printed at the end of the cycle with its issue number. **A
report, never a gate**: the cycle's exit status is unchanged. When the log
is absent, the record says so; it does not report 0.

Grep rule (#2080 body): signatures are case-SENSITIVE — a case-insensitive
`GIL` grep matches French words of the prompts (`fragilise` counts 0).
A Python traceback says `most recent call last`; only a faulthandler dump
says `most recent call first`. **One dump lists EVERY thread** — its thread
headers each carry that string (3 on the real #2080 positive-control dump):
the dump EVENT is its one-shot `Timeout (` line (exactly one per dump), so
that is what `teardown_dumps` counts.

## #2005 — pybind11 `dec_ref` on an `EnumMeta` object

- **State on `main`**: parked (R913, 02/09), no workaround.
- **Unpark trigger**: #2005 comment 1 (R913) — a mid-run pybind11 abort on
  the `EnumMeta` object, or a Python-level fatal abort, in a batch log.
- **Signature / grep**:

  ```text
  pybind11::handle::dec_ref()
  Fatal Python error
  ```

- **Counted as**: `pybind11_signature`, `fatal_abort`.

## #2080 — the executor-join hang (teardown watchdog)

- **State on `main`**: instrument on `main`
  (`scripts/dataset/run_corpus_batch.py:1071-1088`, `_arm_teardown_watchdog`,
  #3290) — a one-shot faulthandler dump, `exit=False`, `repeat=False`:
  observation only, nothing is killed, no timeout hides the hang.
- **Reopen trigger**: #2080 comment 3 and the reopen trigger of its closing
  comment — a watchdog arming FOLLOWED BY a faulthandler dump.
- **Signature / grep**:

  ```text
  teardown watchdog armed
  Timeout (
  ```

- **Counted as**: `teardown_armed`, `teardown_dumps`. The printed alert is
  on `teardown_dumps`: arming alone is the healthy path (114 armings, 0
  dumps on the c0–c6 logs); a dump after arming is what reopens #2080.

## #2894 — the jpype native shutdown

- **State on `main`**: dormant behind `jpype.config.onexit = False`
  (`argumentation_analysis/core/jvm_setup.py:1393`); `destroy_jvm=False`
  since #3628 (2r) replaced the mandatory `onexit=False`.
- **Unpark trigger**: #2894 body — a `_JTerminate` native frame (the
  `DestroyJavaVM` determinant measured 17/11) in a batch log.
- **Signature / grep**:

  ```text
  _JTerminate
  ```

- **Counted as**: `jpype_terminate`.

## Reference measure

Coordinator seat, 13 local panel logs c0–c6: 114 armed, 0 dumps, 0
pybind11, 0 fatal, 0 `_JTerminate`. The one-shot confirmation of the
counter over those logs stays with the coordinator (gitignored logs).
