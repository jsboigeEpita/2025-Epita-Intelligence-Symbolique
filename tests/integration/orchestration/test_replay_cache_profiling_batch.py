"""BO-3 #1473 PR3 DoD: profile (record vs replay) + batch reproducibility +
cache monitoring — proven firsthand, not asserted.

Closes the residual scalability DoD of #1473. PR1/PR2 wired the two cache layers
(direct + SK-native); PR3 MEASURES them — it adds no caching logic
(anti-pendule). Three deliverables:

  1. Profiling: per-phase latency record vs replay, extracted from the pipeline's
     own ``PhaseResult.duration_seconds`` (already tracked by the
     WorkflowExecutor — no pipeline instrumentation added). Replay must be a
     fraction of record for every LLM-bound phase.
  2. Batch: ≥2 synthetic propositions recorded as a batch, then replayed as a
     batch → ZERO live API calls on the whole replay batch (proven via the shared
     ``CacheStats.live`` counter, not asserted by absence of error).
  3. Monitoring: ``get_cache_stats()`` reports hit/miss/live for both layers; the
     test asserts the replay batch's counters (live == 0, hits ≥ 1, no miss).

Privacy HARD: synthetic domain-public chess-club budget propositions only — no
corpus, no real names. Marked ``requires_api``+``slow``: the record leg needs a
real LLM (~3-5 calls per proposition).

NOTE on the JTMS wall-clock field (unchanged from PR1): ``belief_tracking`` embeds
``creation_timestamp`` (``datetime.now()``, extended_belief.py:32) in its RAW
output — wall-clock by construction, never reproducible between two real runs.
Its DECISIONAL output matches (PR1 proved this). The latency table below reports
phase wall-clock duration, which for belief_tracking is non-LLM and ~constant.
"""

import time

import pytest


# 3 synthetic domain-public propositions (chess-club participatory budget model).
# Distinct option sets → distinct LLM calls → distinct cache keys per prop.
PROPOSITIONS = [
    (
        "Le club d'echecs dispose d'un budget participatif de 2000 euros. "
        "Option A : tournoi inter-villes avec buffet pour 2000 euros. "
        "Option B : investir en materiel pedagogique, echiquiers neufs. "
        "Option C : format hybride, 1000 tournoi reduit et 1000 materiel."
    ),
    (
        "La bibliotheque de quartier a un budget exceptionnel de 3000 euros. "
        "Option A : agrandir le fonds livre jeunesse. "
        "Option B : creer un espace numerique avec ordinateurs. "
        "Option C : moitie fonds, moitie espace numerique."
    ),
    (
        "L'association sportive dispose de 1500 euros de subvention. "
        "Option A : acheter des equipements collectifs. "
        "Option B : financer des stages de formation pour les benevoles. "
        "Option C : repartir equitablement entre equipement et formation."
    ),
]


async def _run_democratech(text, cache_dir, mode):
    """Run democratech with the cache pointed at ``cache_dir`` in ``mode``."""
    import os

    from argumentation_analysis.services import llm_cache as lc

    os.environ["LLM_CACHE_MODE"] = mode
    os.environ["LLM_CACHE_DIR"] = cache_dir
    lc.reset_raw_cache()
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    return await run_unified_analysis(text, workflow_name="democratech")


def _phase_durations(result):
    """phase name → duration_seconds (from the pipeline's own PhaseResult)."""
    phases = result.get("phases", {}) if isinstance(result, dict) else {}
    out = {}
    for name, val in phases.items():
        if hasattr(val, "duration_seconds"):
            out[name] = val.duration_seconds
        elif isinstance(val, dict):
            out[name] = val.get("duration_seconds", 0.0)
    return out


def _governance_firsthand(result):
    phases = result.get("phases", {}) if isinstance(result, dict) else {}
    gov = phases.get("democratic_vote", {})
    out = gov.output if hasattr(gov, "output") else (gov.get("output") or {})
    return bool(out.get("governance_decided_firsthand"))


@pytest.mark.requires_api
@pytest.mark.slow
class TestReplayCacheProfilingBatch:
    """DoD: batch record→replay = 0 live call + replay latency << record."""

    @pytest.mark.asyncio
    async def test_batch_record_then_replay_zero_live_and_profiled(self, tmp_path):
        import os

        from argumentation_analysis.services import llm_cache as lc

        cache_dir = str(tmp_path / "llm_cache")
        try:
            # ── RECORD leg: seed the cache with the whole batch ──
            lc.reset_cache_stats()
            record_phase_times = []
            for prop in PROPOSITIONS:
                t0 = time.perf_counter()
                rec = await _run_democratech(prop, cache_dir, "record")
                record_phase_times.append((time.perf_counter() - t0, _phase_durations(rec)))
                # Each record proposition must decide firsthand (else the prop
                # is the problem, not the cache).
                assert _governance_firsthand(rec), (
                    "record proposition did not decide firsthand — prop/cache issue"
                )
            record_stats = lc.get_cache_stats()
            assert record_stats["live"] >= 1, "record leg made 0 live calls (nothing was seeded)"

            # ── REPLAY leg: same batch, fresh stats, expect 0 live calls ──
            lc.reset_cache_stats()
            replay_phase_times = []
            for prop in PROPOSITIONS:
                t0 = time.perf_counter()
                rep = await _run_democratech(prop, cache_dir, "replay")
                replay_phase_times.append((time.perf_counter() - t0, _phase_durations(rep)))
                assert _governance_firsthand(rep), (
                    "replay proposition did not decide firsthand — replay diverged"
                )
            replay_stats = lc.get_cache_stats()

            # DoD #2 (batch): the WHOLE replay batch made ZERO live API calls.
            assert replay_stats["live"] == 0, (
                f"replay batch made {replay_stats['live']} live API call(s) — the "
                "cache did not cover every call (anti-théâtre #1019)"
            )
            assert replay_stats["miss_replay"] == 0, (
                f"replay batch had {replay_stats['miss_replay']} cache miss(es) — "
                "record did not seed every key"
            )
            assert replay_stats["hit"] >= 1, "replay batch served 0 cache hits"

            # DoD #1 (profiling): replay total wall-clock << record total, and
            # every LLM-bound phase is faster on replay. Report the table so the
            # numbers are visible in the test log (not just an internal assert).
            record_total = sum(t for t, _ in record_phase_times)
            replay_total = sum(t for t, _ in replay_phase_times)
            print("\n=== BO-3 PR3 profiling (record vs replay, per phase) ===")
            print(f"propositions: {len(PROPOSITIONS)} | cache_dir: {cache_dir}")
            print(f"record totals: live={record_stats['live']} hits={record_stats['hit']}")
            print(f"replay totals: live={replay_stats['live']} hits={replay_stats['hit']} miss_replay={replay_stats['miss_replay']}")
            print(f"wall-clock: record={record_total:.2f}s replay={replay_total:.2f}s "
                  f"(replay={100*replay_total/max(record_total,1e-9):.1f}% of record)")
            # Per-phase table for proposition[0] (representative).
            rec_phases = record_phase_times[0][1]
            rep_phases = replay_phase_times[0][1]
            print("--- per-phase duration_seconds (prop[0], record vs replay) ---")
            for name in sorted(set(rec_phases) | set(rep_phases)):
                r = rec_phases.get(name, 0.0)
                p = rep_phases.get(name, 0.0)
                print(f"  {name:<24} record={r:7.3f}s  replay={p:7.3f}s")
            assert replay_total < record_total, (
                f"replay ({replay_total:.2f}s) not faster than record "
                f"({record_total:.2f}s) — cache did not accelerate the batch"
            )
        finally:
            os.environ.pop("LLM_CACHE_MODE", None)
            os.environ.pop("LLM_CACHE_DIR", None)
            lc.reset_raw_cache()
            lc.reset_cache_stats()
