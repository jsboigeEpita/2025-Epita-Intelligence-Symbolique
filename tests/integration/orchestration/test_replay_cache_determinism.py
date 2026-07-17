"""BO-3 #1473 DoD #1 at the pipeline level: a ``democratech`` run is
DETERMINISTICALLY REPRODUCIBLE. Recording one live run, then replaying the
same input against the cache, yields an IDENTICAL governance verdict decided
firsthand on BOTH runs — proven firsthand, not asserted.

This is the 3rd axis of Epic #1470 (reproducibility). It complements the unit
tests in ``test_llm_cache.py`` (which prove the cache mechanics in isolation)
by proving the property END-TO-END through ``run_unified_analysis``: every
direct-path phase (extract/quality/counter/fallacy/debate/governance) routes
through ``_guarded_chat_completion`` → ``cached_raw_chat_completion``, so a
replay run reuses the recorded responses instead of hitting the API.

Two DoDs:
  #1 (determinism firsthand): record → replay → identical governance verdict
     (winner + winners_per_method + governance_decided_firsthand) AND identical
     per-phase decisional output (wall-clock fields stripped — they measure
     time, not the decision, and are never reproducible by construction).
  #2 (fail-loud on miss, at the cache layer): a replay miss raises
     ``LLMCacheMiss`` and NEVER silently calls the API — covered in
     ``test_llm_cache.py::test_replay_mode_miss_raises_fail_loud`` (calls == 0).

Privacy HARD: synthetic domain-public chess-club budget proposition only — no
corpus, no real names. Marked ``requires_api``+``slow``: skips without a key
and on the fast per-push gate (the record leg needs a real LLM, ~3-5 calls).

NOTE on the JTMS wall-clock field: ``belief_tracking`` embeds
``creation_timestamp`` (set to ``datetime.now()`` at extended_belief.py:32) in
its output. That field is wall-clock by construction, so it can NEVER match
between two real runs — cache or no cache (the phase makes no LLM call). The
decisional hash below strips wall-clock keys so it measures decisional
determinism (what the cache must reproduce), not wall-time.
"""

import hashlib
import json
import os
import shutil
import tempfile

import pytest


PROPOSITION = (
    "Le club d'echecs dispose d'un budget participatif de 2000 euros. "
    "Trois options divergentes s'affrontent. "
    "Option A : organiser un tournoi inter-villes avec buffet et prix pour 2000 "
    "euros, ce qui augmentera la visibilite du club. "
    "Option B : investir les 2000 euros en materiel pedagogique, echiquiers neufs. "
    "Option C : un format hybride, 1000 euros tournoi reduit et 1000 euros materiel."
)

# Wall-clock fields are never reproducible between two real runs (they measure
# time, not the decision). The cache cannot and should not make them equal, so
# they are stripped from the decisional hash.
_WALLCLOCK_KEYS = {"creation_timestamp", "timestamp", "created_at", "modified_at"}


def _strip_wallclock(obj):
    if isinstance(obj, dict):
        return {k: _strip_wallclock(v) for k, v in obj.items() if k not in _WALLCLOCK_KEYS}
    if isinstance(obj, list):
        return [_strip_wallclock(v) for v in obj]
    return obj


def _decisional_hash(obj) -> str:
    """Deterministic SHA-256[:12] of a JSON-able object (wall-clock stripped)."""
    cleaned = _strip_wallclock(obj)
    raw = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _phase_output(phase_val):
    if phase_val is None:
        return {}
    if hasattr(phase_val, "output"):
        return phase_val.output or {}
    if isinstance(phase_val, dict):
        return phase_val.get("output") or phase_val
    return {}


async def _run_democratech(cache_dir, mode):
    """Run the democratech workflow with the cache pointed at ``cache_dir``.

    ``LLM_CACHE_MODE``/``LLM_CACHE_DIR`` are set + the raw-cache singleton is
    reset so each run sees a fresh view of the cache backend.
    """
    os.environ["LLM_CACHE_MODE"] = mode
    os.environ["LLM_CACHE_DIR"] = cache_dir
    from argumentation_analysis.services import llm_cache as lc
    lc.reset_raw_cache()
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )
    return await run_unified_analysis(PROPOSITION, workflow_name="democratech")


def _governance_verdict(result):
    phases = result.get("phases", {}) if isinstance(result, dict) else {}
    gov = phases.get("democratic_vote", {})
    out = _phase_output(gov)
    verdict = out.get("governance_verdict") or {}
    return {
        "winner": verdict.get("condorcet_winner"),
        "firsthand": out.get("governance_decided_firsthand"),
        "methods": dict(verdict.get("winners_per_method", {})),
    }


def _phase_hashes(result):
    phases = result.get("phases", {}) if isinstance(result, dict) else {}
    return {name: _decisional_hash(_phase_output(val)) for name, val in phases.items()}


@pytest.mark.requires_api
@pytest.mark.slow
class TestReplayCacheDeterminism:
    """DoD #1: record → replay → identical governance verdict + per-phase output."""

    @pytest.mark.asyncio
    async def test_record_then_replay_yields_identical_governance_verdict(self, tmp_path):
        cache_dir = str(tmp_path / "llm_cache")
        try:
            record_result = await _run_democratech(cache_dir, "record")
            replay_result = await _run_democratech(cache_dir, "replay")

            rec_verdict = _governance_verdict(record_result)
            rep_verdict = _governance_verdict(replay_result)

            # The record run itself must decide firsthand (else the proposition
            # or invocation is the problem, not the cache).
            assert rec_verdict["firsthand"] is True, (
                f"RECORD governance not firsthand (firsthand="
                f"{rec_verdict['firsthand']}). Proposition/invocation issue."
            )
            # DoD #1: identical governance verdict, decided firsthand on both.
            assert rep_verdict["firsthand"] is True, (
                "REPLAY governance not firsthand — replay diverged from record"
            )
            assert rec_verdict["winner"] == rep_verdict["winner"], (
                f"winner differs: {rec_verdict['winner']} vs {rep_verdict['winner']}"
            )
            assert rec_verdict["methods"] == rep_verdict["methods"], (
                "winners_per_method differs between record and replay"
            )
            assert rec_verdict["methods"], "expected ≥1 voting method decided"

            # DoD #1 (per-phase): every phase's decisional output is identical
            # (wall-clock stripped). A divergence here would be a REAL cache bug,
            # not a cosmetic timestamp — this is the core anti-théâtre guarantee.
            rec_hashes = _phase_hashes(record_result)
            rep_hashes = _phase_hashes(replay_result)
            diverged = {
                name: (rec_hashes[name], rep_hashes.get(name))
                for name in rec_hashes
                if rec_hashes[name] != rep_hashes.get(name)
            }
            assert not diverged, (
                f"phases diverged decisionally between record and replay "
                f"(not wall-clock — real cache miss): {diverged}"
            )
        finally:
            os.environ.pop("LLM_CACHE_MODE", None)
            os.environ.pop("LLM_CACHE_DIR", None)
            from argumentation_analysis.services import llm_cache as lc
            lc.reset_raw_cache()
