# -*- coding: utf-8 -*-
"""#3702 — the walk below a child says when *it* is the one that failed.

Measured 2026-11-26 on a degraded seat: a gate run at four workers went red in
``test_llm_egress_report_reader_3194`` because ``descendants()``'s process
listing outran its fixed ``timeout=60`` (``Get-CimInstance Win32_Process``),
while the same node passed alone in 79 s. Two defects, both fixed here:

- the budget was a literal; it is now ``LISTING_BASE`` seconds per worker
  sharing the seat, capped at ``LISTING_MAX_FACTOR``, with the same shape as
  the wheel guard's derived budgets (#3698);
- the failure surfaced as ``subprocess.TimeoutExpired``, so the run read as
  the child's failure; it is now ``ProcessListingFailed``, whose message names
  the listing and refuses to say anything about the child.

``descendants``/``_left_behind`` sit on the exit path of **every** bounded run
that does not expire (41 call sites across 22 files under ``tests/``), so a
listing failure must be readable as such wherever it lands.

The first revision had a defect of its own, read again before review
(2026-11-26). ``ProcessListingFailed`` is a ``RuntimeError``, and the walk
below an **expired** child reports through ``_state_at_bound``, whose clause
listed ``OSError`` and ``subprocess.SubprocessError``. So at the bound the
named failure escaped ``run_bounded`` before ``kill_tree``: measured, the
expired child stayed running and the bound's report was lost — where ``main``,
on the same failure under its old name, kills the child. The same measure
showed a defect of ``main``'s own: a walk failure of a kind nobody listed
(``ValueError``) leaves the child running there too. And when the *second*
listing of ``_left_behind`` fails, the message says "the walk found nothing"
while the first listing had seen a process. The last two witnesses pin the
repair: the bound's kill and verdict no longer depend on the walk, and a
failed second listing keeps what the first one saw.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from tests import nested_pytest


def test_the_listing_budget_grows_with_the_workers_sharing_the_seat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One budget per worker, capped — never a single literal."""
    monkeypatch.delenv("PYTEST_XDIST_WORKER_COUNT", raising=False)
    assert nested_pytest.listing_budget() == nested_pytest.LISTING_BASE

    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "1")
    assert nested_pytest.listing_budget() == nested_pytest.LISTING_BASE

    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "2")
    assert nested_pytest.listing_budget() == 2 * nested_pytest.LISTING_BASE

    monkeypatch.setenv(
        "PYTEST_XDIST_WORKER_COUNT", str(nested_pytest.LISTING_MAX_FACTOR + 1)
    )
    capped = nested_pytest.LISTING_MAX_FACTOR * nested_pytest.LISTING_BASE
    assert nested_pytest.listing_budget() == capped

    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "abc")
    assert nested_pytest.listing_budget() == nested_pytest.LISTING_BASE


def test_the_walk_names_its_own_failure_and_not_the_childs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A listing that does not answer is the instrument's failure."""

    def _expire(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))

    monkeypatch.setenv("PYTEST_XDIST_WORKER_COUNT", "2")
    monkeypatch.setattr(nested_pytest.subprocess, "run", _expire)

    with pytest.raises(nested_pytest.ProcessListingFailed) as caught:
        nested_pytest.descendants(os.getpid(), None)

    message = str(caught.value)
    assert "process listing did not answer" in message
    assert str(2 * nested_pytest.LISTING_BASE) in message
    assert "is the walk's failure, not the child's" in message
    # The defect this witness exists for: the run read as the child's exit.
    assert "exited 1" not in message
    assert isinstance(caught.value.__cause__, subprocess.TimeoutExpired)


def test_the_walk_still_reads_a_real_table() -> None:
    """Vacuity control: the derived budget still lets a real listing through."""
    created = nested_pytest._created(os.getpid())
    assert isinstance(nested_pytest.descendants(os.getpid(), created), list)


def test_a_bounded_run_surfaces_the_walks_failure_rather_than_the_childs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``run_bounded`` must not swallow it into a verdict about the child."""

    def _fail(pid, created):
        raise nested_pytest.ProcessListingFailed("the process listing did not answer")

    monkeypatch.setattr(nested_pytest, "descendants", _fail)
    with pytest.raises(nested_pytest.ProcessListingFailed):
        nested_pytest.run_bounded([sys.executable, "-c", "pass"])


def _walk_failure(kind: str) -> BaseException:
    """What the walk raises at the bound: the named failure, or a kind the
    bound's report never listed."""
    if kind == "the-named-failure":
        return nested_pytest.ProcessListingFailed("the process listing did not answer")
    return ValueError("the walk broke")


@pytest.mark.parametrize("kind", ["the-named-failure", "an-unlisted-kind"])
def test_the_bound_still_kills_the_child_when_the_walk_fails(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound's kill and its verdict do not depend on the walk below it.

    A child that outlives its bound must be killed whether or not the walk
    that describes it could read the process table: the walk completes the
    report, it does not decide the kill.
    """

    def _fail(pid, created):
        raise _walk_failure(kind)

    monkeypatch.setattr(nested_pytest, "descendants", _fail)
    # ``run_bounded`` does not hand back the process it started, and a witness
    # that waited for the child to write its own pid would depend on the child
    # starting at all: the process is read from the constructor it calls.
    child = [sys.executable, "-c", "import time; time.sleep(120)"]
    started = []
    real_popen = subprocess.Popen

    def _recording_popen(args, *more, **kwargs):
        process = real_popen(args, *more, **kwargs)
        if args is child:
            started.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", _recording_popen)
    try:
        with pytest.raises(pytest.fail.Exception) as caught:
            nested_pytest.run_bounded(
                child, bound=4, failure="the probe session did not end"
            )
        message = str(caught.value)
        assert "the probe session did not end within 4s" in message
        assert "descendants: not listed" in message
        assert str(_walk_failure(kind)) in message
        assert started, "the run never started the child"
        assert started[0].poll() is not None, "the expired child is still running"
    finally:
        for process in started:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=30)


def test_a_second_listing_that_fails_keeps_what_the_first_saw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first listing saw a process: "found nothing" would be false.

    Nothing is killed on the first listing alone — a pid is killed only where
    a listing reads it below the child again (#2662) — so the failure has to
    carry the sighting instead of dropping it.
    """
    listings = []

    def _listing(pid, created):
        listings.append(pid)
        if len(listings) == 1:
            return [(424242, "java.exe")]
        raise nested_pytest.ProcessListingFailed("the process listing did not answer")

    killed = []
    monkeypatch.setattr(nested_pytest, "descendants", _listing)
    monkeypatch.setattr(nested_pytest, "_created", lambda pid: 1)
    monkeypatch.setattr(nested_pytest, "SETTLE", 0)
    monkeypatch.setattr(nested_pytest, "_kill", lambda pids: killed.append(list(pids)))

    class Exited:
        pid = os.getpid()

    with pytest.raises(nested_pytest.ProcessListingFailed) as caught:
        nested_pytest._left_behind(Exited())

    message = str(caught.value)
    assert "424242 java.exe" in message
    assert "the first listing saw" in message
    assert "found nothing" not in message
    assert "nothing was killed" in message
    assert killed == []
