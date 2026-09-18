# -*- coding: utf-8 -*-
"""#2282 guard: the run-level environment stamp must survive an aborted run.

PR #2287 gave the corpus batch a LOUD run-level environment stamp on stdout
so a campaign that rendered on a dead JVM is named as such instead of read as
"ok" (#2276: 11 phases failed on a dead JVM and nothing said so).

The stamp is printed at the *end* of ``main()``, and that position is
load-bearing: ``jvm_started`` must report the JVM of the run that actually
happened, not one probed before anything started. This guard does not move
it and must not be "simplified" by moving it.

But the end position left the instrument unreachable in precisely the case it
exists for. An aborted run is when the environment is the prime suspect --
and an abort printed *nothing* about it. Measured firsthand on ai-01 the
18/09: a mini-campaign died at corpus expansion on an unset ``OPAQUE_ID_SALT``
(itself absent from ``.env.example`` until the same PR) and emitted zero
environment information. A canary that is silent on failure is not a canary.

So the abort path probes too, under its own distinct banner. What is pinned
here is the property, not the wording of a line:

1. an abort emits an environment stamp;
2. the abort banner is distinguishable from a completed run's, so an abort
   stamp can never be misread as a finished campaign's;
3. the original exception still propagates -- the stamp is an addition to the
   failure, never a swallowing of it;
4. a probe that itself fails does not replace the real traceback with its own
   (a guard must not depend on what it probes);
5. the ``__main__`` seam actually routes through the wrapper -- a guard the
   entry point does not call is not a guard.

Lives in ``tests/scripts/`` for the same measured reason as its
``test_corpus_batch_*`` siblings: the CI argv names only
``orchestration|services|workers|api`` under ``tests/integration/``.

Hermetic: no subprocess, no encrypted dataset, no LLM call, no JVM required.
"""

import importlib.util
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "dataset" / "run_corpus_batch.py"
)
ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_corpus_batch_under_test_2282abort", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Boom(RuntimeError):
    """The abort. Distinct type so we can assert THIS one propagates."""


def _raiser(exc):
    def _raise(*_args, **_kwargs):
        raise exc

    return _raise


class TestStampSurvivesAbort:
    def test_abort_emits_an_environment_stamp(self, monkeypatch, capsys):
        """An aborted run says what it was running on."""
        runner = _load_runner()
        monkeypatch.setattr(runner, "main", _raiser(_Boom("died early")))

        with pytest.raises(_Boom):
            runner._run_with_environment_stamp_on_abort()

        out = capsys.readouterr().out
        assert "ENVIRONMENT" in out, (
            "an aborted run printed no environment stamp -- the #2282 canary is "
            f"silent exactly when it is needed. stdout was: {out!r}"
        )
        # The stamp must be the real probe, not a placeholder: the axes the
        # renderer names have to be there.
        lowered = out.lower()
        for axis in ("jvm:", "llm", "torch"):
            assert axis in lowered, f"stamp is missing the {axis!r} axis: {out!r}"

    def test_abort_banner_is_distinguishable_from_a_completed_run(
        self, monkeypatch, capsys
    ):
        """An abort stamp must never read as a finished campaign's stamp.

        This is the control that keeps the test above from being satisfied by
        any stamp at all: the abort surface has to carry its own marker.
        """
        runner = _load_runner()
        monkeypatch.setattr(runner, "main", _raiser(_Boom("died early")))

        with pytest.raises(_Boom):
            runner._run_with_environment_stamp_on_abort()

        out = capsys.readouterr().out
        assert "ABORTED" in out, (
            "the abort path emitted a stamp with no abort marker: a reader "
            f"cannot tell it from a completed run. stdout was: {out!r}"
        )

    def test_normal_return_is_untouched(self, monkeypatch, capsys):
        """Degenerate substitution: no abort, no abort banner, value passes through.

        Without this, the tests above would still pass if the wrapper printed
        the abort banner unconditionally.
        """
        runner = _load_runner()
        monkeypatch.setattr(runner, "main", lambda *a, **k: 0)

        assert runner._run_with_environment_stamp_on_abort() == 0
        assert "ABORTED" not in capsys.readouterr().out

    def test_systemexit_passes_through_without_a_banner(self, monkeypatch, capsys):
        """``--help`` and explicit exits are not aborts."""
        runner = _load_runner()
        monkeypatch.setattr(runner, "main", _raiser(SystemExit(0)))

        with pytest.raises(SystemExit):
            runner._run_with_environment_stamp_on_abort()
        assert "ABORTED" not in capsys.readouterr().out

    def test_failing_probe_does_not_replace_the_real_traceback(
        self, monkeypatch, capsys
    ):
        """A guard must not depend on what it probes.

        If the environment is broken enough that probing it throws, the
        operator must still receive the ORIGINAL exception -- the probe's own
        failure is a note, not a substitution.
        """
        runner = _load_runner()
        monkeypatch.setattr(runner, "main", _raiser(_Boom("died early")))
        monkeypatch.setattr(
            runner,
            "environment_manifest",
            _raiser(OSError("probe itself is broken")),
        )

        with pytest.raises(_Boom):
            runner._run_with_environment_stamp_on_abort()

        out = capsys.readouterr().out
        assert "environment stamp unavailable at abort" in out, (
            "the probe failed silently: the operator sees neither a stamp nor "
            f"a reason. stdout was: {out!r}"
        )


class TestEntryPointRoutesThroughTheWrapper:
    def test_main_block_calls_the_wrapper(self):
        """A guard the entry point does not call is not a guard.

        Pinned structurally because the wiring lives in the ``__main__``
        block, which no import can execute. Re-simplifying the seam back to
        a bare ``main()`` call reddens here.
        """
        source = SCRIPT.read_text(encoding="utf-8")
        tail = source.split('if __name__ ==')[-1]
        assert "_run_with_environment_stamp_on_abort()" in tail, (
            "the __main__ seam no longer routes through the abort-stamp "
            f"wrapper: {tail!r}"
        )


class TestSaltIsDocumentedInTheTemplate:
    def test_env_example_names_the_required_salt(self):
        """``OPAQUE_ID_SALT`` is REQUIRED; a template that omits it is a trap.

        ``opaque_id()`` raises without it, so a seat installed by following
        ``.env.example`` saw the corpus batch die on the first document. Same
        omission class as the ``VLLM_ENDPOINT_i`` family already documented in
        that file.
        """
        template = ENV_EXAMPLE.read_text(encoding="utf-8", errors="replace")
        assert "OPAQUE_ID_SALT" in template, (
            "OPAQUE_ID_SALT is required by opaque_id.py but absent from "
            ".env.example: following the template yields a broken seat."
        )

    def test_template_ships_no_usable_salt_value(self):
        """The absent default is the contract, not an oversight.

        A public salt would let any reader of the repo confirm a guessed name
        against a published opaque ID. Documenting the key must not smuggle in
        a working value.
        """
        template = ENV_EXAMPLE.read_text(encoding="utf-8", errors="replace")
        live = [
            line
            for line in template.splitlines()
            if line.strip().startswith("OPAQUE_ID_SALT=")
        ]
        assert not live, f"a usable salt is shipped in the template: {live!r}"
