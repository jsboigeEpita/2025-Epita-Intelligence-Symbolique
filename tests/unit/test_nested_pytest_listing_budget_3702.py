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
