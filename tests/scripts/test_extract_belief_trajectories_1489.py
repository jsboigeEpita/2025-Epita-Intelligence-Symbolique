"""Tests for extract_belief_trajectories.py (TPM-1 #1489).

Static + functional tests with NO LLM / NO key. Mirrors the BO-4 #1480
test pattern (``inspect.getsource``-style introspection when the harness
needs JVM/keys we don't have locally).

What's tested:
- Module is importable via importlib (file-disjoint from main bundle).
- ``_state_label`` bucketing is deterministic + covers edge cases.
- ``build_tpm`` returns IMPOSSIBILITY for empty / degenerate / sparse inputs.
- ``build_tpm`` returns a valid stochastic matrix for sane inputs.
- The ``MODE_RUNNERS``-equivalent contract: the script exposes a CLI
  (``--dry-run``) that prints the contract without needing LLM/keys.
- The state-space definition mentions the 5 pre-existing democratech phases
  we capture (privacy HARD: no raw_text references).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import textwrap

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "extract_belief_trajectories.py"


def _load_module():
    """Import the script as a module (file-disjoint, mirrors test_compare_orchestration_modes_1480).

    Registers the module in sys.modules so that ``dataclass`` field introspection
    (cls.__module__) resolves correctly — otherwise ``field(default_factory=dict)``
    raises ``AttributeError: 'NoneType' object has no attribute '__dict__'``
    during test collection.
    """
    spec = importlib.util.spec_from_file_location(
        "extract_belief_trajectories", str(SCRIPT_PATH)
    )
    if spec is None or spec.loader is None:
        pytest.fail(f"Cannot create import spec for {SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["extract_belief_trajectories"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop("extract_belief_trajectories", None)
        raise
    return mod


# Load once at module import time (cheap, side-effect free).
m = _load_module()


class TestStateSpaceBucketing:
    """`_state_label` is the heart of the TPM — bucketing must be deterministic."""

    def test_empty_state_no_vote(self):
        label = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 0,
                "n_fallacies": 0,
                "n_counters": 0,
                "vote_winner": None,
            }
        )
        assert label.startswith("completed:")
        assert "args0" in label
        assert "fall0" in label
        assert "ctr0" in label
        assert "votenone" in label

    def test_medium_args_low_fallacies(self):
        label = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 4,
                "n_fallacies": 1,
                "n_counters": 2,
                "vote_winner": None,
            }
        )
        assert "args3-5" in label
        assert "fall1-2" in label
        assert "ctr1+" in label

    def test_high_args_with_winner_high_consensus(self):
        label = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 8,
                "n_fallacies": 4,
                "n_counters": 5,
                "vote_winner": "arg_1",
                "vote_consensus": 0.85,
            }
        )
        assert "args6+" in label
        assert "fall3+" in label
        assert "votearg_1:high" in label

    def test_low_consensus(self):
        label = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 3,
                "n_fallacies": 0,
                "n_counters": 1,
                "vote_winner": "arg_2",
                "vote_consensus": 0.15,
            }
        )
        assert "votearg_2:low" in label

    def test_failed_phase(self):
        label = m._state_label(
            {
                "phase_status": "failed",
                "n_arguments": 0,
                "n_fallacies": 0,
                "n_counters": 0,
                "vote_winner": None,
            }
        )
        assert label.startswith("failed:")

    def test_beliefs_bucket_adds_to_label(self):
        """The state vector now includes n_beliefs (JTMS-style signal) — R664
        fix. State label format adds `bel<bucket>` between `ctr<bucket>` and
        `vote<...>`. Three buckets: 0 / 1-5 / 6+.
        """
        label_low = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 3,
                "n_fallacies": 0,
                "n_counters": 0,
                "n_beliefs": 0,
                "vote_winner": None,
            }
        )
        assert "bel0" in label_low
        label_mid = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 3,
                "n_beliefs": 4,
                "vote_winner": None,
            }
        )
        assert "bel1-5" in label_mid
        label_high = m._state_label(
            {
                "phase_status": "completed",
                "n_arguments": 3,
                "n_beliefs": 14,
                "vote_winner": None,
            }
        )
        assert "bel6+" in label_high

    def test_label_deterministic_for_same_input(self):
        """Identical inputs MUST produce identical labels (replay determinism)."""
        snap = {
            "phase_status": "completed",
            "n_arguments": 3,
            "n_fallacies": 0,
            "n_counters": 1,
            "vote_winner": "arg_1",
            "vote_consensus": 0.5,
        }
        assert m._state_label(snap) == m._state_label(snap)


class TestTPMConstruction:
    """`build_tpm` is the falsifiable gate — test all 4 branches."""

    def test_empty_impossible(self):
        tpm = m.build_tpm([])
        assert tpm.impossible is True
        # For an empty input, the state-space is empty (0 distinct states) —
        # the degenerate check fires first and is the more honest reason.
        assert "degenerate state space" in tpm.impossibility_reason
        assert tpm.n_trajectories == 0
        assert tpm.n_transitions == 0

    def test_insufficient_signal_branch(self):
        """2 obs (>=2 states, but <3 total) → 'insufficient signal' branch."""
        # 2 observations of DIFFERENT states but only 2 total obs.
        obs1 = m.PhaseObservation(
            phase_name="extract",
            capability="x",
            phase_status="completed",
            snapshot={},
            state_label="s1",
            elapsed_seconds=0.0,
        )
        obs2 = m.PhaseObservation(
            phase_name="vote",
            capability="y",
            phase_status="completed",
            snapshot={},
            state_label="s2",
            elapsed_seconds=0.0,
        )
        traj = m.Trajectory(
            corpus_id="p1", corpus_label="L1", observations=[obs1, obs2]
        )
        tpm = m.build_tpm([traj])
        assert tpm.impossible is True
        assert "insufficient signal" in tpm.impossibility_reason

    def test_one_state_degenerate_impossible(self):
        obs = m.PhaseObservation(
            phase_name="extract",
            capability="fact_extraction",
            phase_status="completed",
            snapshot={},
            state_label="completed:args3-5:fall0:ctr0:votenone",
            elapsed_seconds=0.0,
        )
        traj = m.Trajectory(
            corpus_id="p1", corpus_label="L1", observations=[obs]
        )
        tpm = m.build_tpm([traj])
        assert tpm.impossible is True
        assert "degenerate state space" in tpm.impossibility_reason
        assert len(tpm.states) == 1

    def test_sparse_transitions_impossible(self):
        """Fewer transitions than states → sparse → impossibility."""
        # 3 states but only 1 transition between 2 of them.
        obs1 = m.PhaseObservation(
            phase_name="extract",
            capability="x",
            phase_status="completed",
            snapshot={},
            state_label="s1",
            elapsed_seconds=0.0,
        )
        obs2 = m.PhaseObservation(
            phase_name="vote",
            capability="y",
            phase_status="completed",
            snapshot={},
            state_label="s2",
            elapsed_seconds=0.0,
        )
        obs3 = m.PhaseObservation(
            phase_name="quality_recheck",
            capability="z",
            phase_status="completed",
            snapshot={},
            state_label="s3",  # disjoint from s1, no transition observed
            elapsed_seconds=0.0,
        )
        traj = m.Trajectory(
            corpus_id="p1",
            corpus_label="L1",
            observations=[obs1, obs2, obs3],
        )
        tpm = m.build_tpm([traj])
        assert tpm.impossible is True
        assert "sparse transitions" in tpm.impossibility_reason
        assert len(tpm.states) == 3

    def test_valid_tpm_is_row_stochastic(self):
        """A valid TPM must have each row sum to 1.0 (row-stochastic)."""
        # 2 trajectories, each: s1 -> s2 -> s2 (s2 self-loop)
        obs_seq = [
            m.PhaseObservation(
                phase_name=p,
                capability="c",
                phase_status="completed",
                snapshot={},
                state_label=s,
                elapsed_seconds=0.0,
            )
            for p, s in [
                ("extract", "s1"),
                ("vote", "s2"),
                ("indexing", "s2"),
            ]
        ]
        traj_a = m.Trajectory(corpus_id="a", corpus_label="A", observations=obs_seq)
        traj_b = m.Trajectory(corpus_id="b", corpus_label="B", observations=obs_seq)
        tpm = m.build_tpm([traj_a, traj_b])
        assert tpm.impossible is False
        assert set(tpm.states) == {"s1", "s2"}
        assert tpm.n_transitions == 4  # 2 per traj × 2 traj
        matrix = tpm.as_stochastic_matrix()
        # s1 row: 2 transitions s1→s2 → [0, 1.0]
        s1_idx = tpm.states.index("s1")
        s2_idx = tpm.states.index("s2")
        assert matrix[s1_idx][s2_idx] == pytest.approx(1.0)
        assert matrix[s1_idx][s1_idx] == pytest.approx(0.0)
        # s2 row: 2 transitions s2→s2 (self-loops) → [0, 1.0]
        assert matrix[s2_idx][s2_idx] == pytest.approx(1.0)
        assert matrix[s2_idx][s1_idx] == pytest.approx(0.0)
        # All rows sum to 1.0.
        for row in matrix:
            assert sum(row) == pytest.approx(1.0)

    def test_tpm_to_dict_serializable(self):
        obs_seq = [
            m.PhaseObservation(
                phase_name="extract",
                capability="x",
                phase_status="completed",
                snapshot={"n_arguments": 3},
                state_label="s1",
                elapsed_seconds=0.0,
            ),
            m.PhaseObservation(
                phase_name="vote",
                capability="y",
                phase_status="completed",
                snapshot={"vote_winner": "arg_1"},
                state_label="s2",
                elapsed_seconds=0.0,
            ),
        ]
        traj = m.Trajectory(corpus_id="p1", corpus_label="L", observations=obs_seq)
        tpm = m.build_tpm([traj])
        d = tpm.to_dict()
        # Must round-trip through json.
        js = json.dumps(d)
        parsed = json.loads(js)
        assert parsed["states"] == tpm.states
        assert parsed["n_transitions"] == tpm.n_transitions


class TestDryRunContract:
    """The CLI `--dry-run` MUST work without any LLM/key (the user's DoD gate)."""

    def test_dry_run_does_not_import_pipeline(self, capsys, monkeypatch):
        """Dry-run must EXIT before any pipeline import (no JVM, no API)."""
        # Simulate no API key.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
        # Run the script via subprocess so we don't pollute the test process.
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **__import__("os").environ,
                "PYTHONPATH": str(REPO_ROOT),
            },
        )
        assert result.returncode == 0, (
            f"dry-run failed (rc={result.returncode}): "
            f"stdout={result.stdout[:500]} stderr={result.stderr[:500]}"
        )
        # Print the contract.
        assert "TPM-1 #1489" in result.stdout
        assert "demo5" in result.stdout
        assert "State label" in result.stdout
        # Privacy HARD: must mention the privacy contract.
        assert "no raw_text" in result.stdout or "no corpus" in result.stdout


class TestScriptPrivacyContract:
    """Static guarantees — the script MUST NOT load raw corpus data."""

    def test_no_corpus_loaders(self):
        """The script must not import the encrypted corpus loader or extract_sources."""
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        forbidden = ("extract_sources", "TEXT_CONFIG_PASSPHRASE", ".json.gz.enc")
        for term in forbidden:
            assert term not in src, f"Forbidden term found in script: {term}"

    def test_no_raw_text_in_outputs(self):
        """The state-space definition uses aggregates only (counts, buckets)."""
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        # Phase summarizer must not include raw_text / full_text / quote.
        # Allow "source_quote" reference only inside a comment / docstring.
        forbidden_in_code = ("raw_text=", "full_text=")
        for term in forbidden_in_code:
            assert term not in src, (
                f"Forbidden field reference in code: {term} (privacy HARD)"
            )

    def test_uses_pre_existing_hooks_only(self):
        """Anti-sur-instrumentation: pipeline must NOT be modified."""
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        # Must USE checkpoint_callback (pre-existing).
        assert "checkpoint_callback" in src
        # Must USE state.get_state_snapshot (pre-existing).
        assert "get_state_snapshot" in src
        # Must NOT patch / monkey-patch / override WorkflowExecutor.
        forbidden = ("monkeypatch", "patch.", "WorkflowExecutor.__")
        for term in forbidden:
            assert term not in src, (
                f"Anti-sur-instrumentation breach: {term}"
            )

    def test_uses_run_unified_analysis_with_checkpoint(self):
        """The script wires the checkpoint through run_unified_analysis (pre-existing
        ``checkpoint_callback`` parameter) — NOT via run_deliberation, which does
        not accept checkpoint_callback. This architecture preserves
        anti-sur-instrumentation while still feeding the catcher.
        """
        src = SCRIPT_PATH.read_text(encoding="utf-8")
        # Must USE run_unified_analysis directly (it accepts checkpoint_callback).
        assert "run_unified_analysis" in src
        assert "checkpoint_callback=catcher" in src
        # Must NOT call run_deliberation (would silently drop the catcher — bug
        # discovered during the LLM smoke validation on 2026-07-19: run_deliberation
        # exposes no checkpoint_callback parameter, so wiring it produced 0 obs).
        assert "run_deliberation(" not in src, (
            "Script MUST call run_unified_analysis directly — run_deliberation does "
            "not accept checkpoint_callback and will silently drop the catcher."
        )


class TestPhaseSummaryShape:
    """`_summarize_phase_output` must return LIGHT aggregates per phase."""

    def test_extract_phase(self):
        out = {
            "arguments": [{"text": f"arg_{i}"} for i in range(4)],
            "claims": [{"text": f"claim_{i}"} for i in range(2)],
            "extraction_status": "ok",
        }
        s = m._summarize_phase_output("extract", out)
        assert s["n_arguments"] == 4
        assert s["n_claims"] == 2
        assert s["extraction_status"] == "ok"

    def test_quality_baseline_phase(self):
        out = {
            "quality_scores": [{"score": 0.7}, {"score": 0.8}],
        }
        s = m._summarize_phase_output("quality_baseline", out)
        assert s["quality_avg"] == pytest.approx(0.75, abs=0.001)

    def test_fallacy_detection_phase(self):
        out = {"fallacies": [{"type": "ad_hominem"} for _ in range(3)]}
        s = m._summarize_phase_output("fallacy_detection", out)
        assert s["n_fallacies"] == 3

    def test_democratic_vote_phase_with_winners(self):
        out = {
            "governance_verdict": {
                "winners_per_method": {
                    "majority": "arg_A",
                    "borda": "arg_A",
                    "condorcet": "arg_A",
                }
            },
            "consensus_rate": 0.82,
            "governance_decided_firsthand": True,
        }
        s = m._summarize_phase_output("democratic_vote", out)
        assert s["vote_winner"] == "arg_A"
        assert s["n_methods"] == 3
        assert s["vote_consensus"] == 0.82
        assert s["decides_firsthand"] is True

    def test_belief_tracking_phase(self):
        out = {
            "belief_sets": [{"logic_type": "fol"}, {"logic_type": "modal"}],
            "contractions": [{"belief": "b1"}],
        }
        s = m._summarize_phase_output("belief_tracking", out)
        assert s["n_beliefs"] == 2
        assert s["n_contractions"] == 1

    def test_non_dict_input_handled(self):
        """Defensive: never crash on None / non-dict phase output."""
        assert m._summarize_phase_output("extract", None) == {"phase": "extract"}
        assert m._summarize_phase_output("extract", "garbage") == {"phase": "extract"}
        assert m._summarize_phase_output("extract", 42) == {"phase": "extract"}


class TestStateOverlay:
    """`_merge_state_counts` must prefer higher counts (state is source of truth)."""

    def test_overlay_overrides_optimistic_phase_counts(self):
        summary = {"n_arguments": 2, "n_fallacies": 0}
        snapshot = {
            "argument_count": 5,  # state says more
            "fallacy_count": 1,
        }
        merged = m._merge_state_counts(summary, snapshot)
        assert merged["n_arguments"] == 5  # max(2, 5) = 5
        assert merged["n_fallacies"] == 1
        assert merged["_state_overlay"] is True

    def test_overlay_uses_jtms_belief_count_r664(self):
        """R664 fix: state overlay must read ``jtms_belief_count`` (the JTMS
        signal exposed by ``get_state_snapshot(summarize=True)``), not the
        logical ``belief_set_count`` (FOL/Modal belief_sets, distinct concept).
        Smoke-validation surfaced this: 14 jtms_beliefs observed but the
        ``n_beliefs`` field stayed 0 because of the wrong mapping. This test
        locks the correct mapping.
        """
        summary = {"n_beliefs": 0}
        snapshot = {
            "jtms_belief_count": 14,  # Real JTMS signal
            "belief_set_count": 2,    # Logical belief_sets (ignored by map)
        }
        merged = m._merge_state_counts(summary, snapshot)
        assert merged["n_beliefs"] == 14, (
            "jtms_belief_count must drive n_beliefs; got %s" % merged["n_beliefs"]
        )

    def test_no_snapshot_returns_phase_only(self):
        summary = {"n_arguments": 3}
        merged = m._merge_state_counts(summary, None)
        assert merged["n_arguments"] == 3
        assert merged["_state_overlay"] is False
