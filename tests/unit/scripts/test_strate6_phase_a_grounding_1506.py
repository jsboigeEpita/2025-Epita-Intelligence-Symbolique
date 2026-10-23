"""#1506 (R1107) — the candidate #2 artifact must say WHAT its matrix counts.

Measured on ``main`` 2026-10-23 under the zero-spend ``LLM_CACHE_MODE=replay``:
the inner extractor's ``extract`` phase fails on every proposition (replay cache
miss, no fixtures), every downstream count stays 0, and corpora A / B / C yield
the *same* matrix — 3 states, λ = [1, 0, 0], g = 1.

Two claims the driver was still making on that state:

1. « **CANDIDAT #2 LIVRÉ** » — while the only varying coordinate of the state
   label is the phase status word. A chain over ``completed`` / ``failed`` /
   ``skipped`` is not a chain over belief states (anti-theatre #1019).
2. « **Mixing rapide** … Distribution stationnaire accessible » — from
   g = 1 − |λ₂| = 1 on a chain the same page calls « Ergodique : NON —
   réductible ». g is a mixing rate only for an irreducible chain.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_driver():
    path = _REPO_ROOT / "scripts" / "coursia_strate6_phaseA_grounding.py"
    spec = importlib.util.spec_from_file_location("strate6_phaseA", path)
    module = importlib.util.module_from_spec(spec)
    # ``dataclasses`` resolves ``cls.__module__`` through ``sys.modules`` while
    # processing ``@dataclass``: without this registration the exec raises
    # ``AttributeError: 'NoneType' object has no attribute '__dict__'``.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def driver():
    return _load_driver()


def _snapshot(**counts):
    base = {"n_arguments": 0, "n_fallacies": 0, "n_counters": 0, "n_beliefs": 0}
    base.update(counts)
    return base


def _payload(snapshots):
    return {
        "trajectories": [
            {"observations": [{"snapshot": s} for s in snapshots]},
        ]
    }


def _verdict(driver, *, snapshots, irreducible, gap, lam2, eigenvalues):
    return driver.Verdict(
        corpus_letter="A",
        n_trajectories=len(snapshots),
        n_observations_total=len(snapshots),
        n_transitions=max(len(snapshots) - 1, 0),
        n_states=len(eigenvalues),
        impossible=False,
        impossibility_reason="",
        ergodicity={
            "n_scc": 3,
            "n_wcc": 1,
            "irreducible": irreducible,
            "ergodic_line": "- **Ergodique** : **NON**",
        },
        spectral={
            "n": len(eigenvalues),
            "eigenvalues_abs": eigenvalues,
            "spectral_gap": gap,
            "second_largest_abs": lam2,
            "analysis_skipped": False,
            "skip_reason": None,
        },
        state_space=driver.belief_state_coverage(_payload(snapshots)),
        coursia_seed_issue="jsboige/CoursIA#7289",
        candidate_id="candidate_2_belief_state_tpm",
    )


class TestTheStateSpaceIsMeasured:
    def test_all_zero_counters_mean_no_belief_state(self, driver):
        block = driver.belief_state_coverage(_payload([_snapshot() for _ in range(5)]))
        assert block["carries_belief_state"] is False
        assert block["observations"] == 5
        assert block["n_arguments"] == 0

    def test_one_non_zero_coordinate_is_enough(self, driver):
        block = driver.belief_state_coverage(
            _payload([_snapshot(), _snapshot(n_fallacies=2)])
        )
        assert block["carries_belief_state"] is True
        assert block["n_fallacies"] == 2


class TestTheVerdictRefusesTheEmptyClaim:
    def _degenerate(self, driver):
        return _verdict(
            driver,
            snapshots=[_snapshot() for _ in range(3)],
            irreducible=False,
            gap=1.0,
            lam2=0.0,
            eigenvalues=[1.0, 0.0, 0.0],
        )

    def test_no_delivery_claim_on_a_status_word_chain(self, driver):
        text = driver._render_verdict_markdown(
            self._degenerate(driver), _payload([]), "inner/report.md"
        )
        assert "CANDIDAT #2 LIVRÉ" not in text
        assert "NON MESURÉ" in text
        assert "ne mesure PAS des états de croyance" in text
        assert "aucun artefact n'est proposé" in text

    def test_the_gap_is_not_read_as_a_mixing_rate_on_a_reducible_chain(self, driver):
        text = driver._render_verdict_markdown(
            self._degenerate(driver), _payload([]), "inner/report.md"
        )
        assert "n'est pas un taux de mélange" in text
        assert "Mixing rapide" not in text


class TestTheControlStillDelivers:
    """A run whose counters DID fire keeps the delivery claim and the mixing
    reading — the guard must not turn every verdict into a refusal."""

    def test_a_measured_irreducible_chain_still_says_delivered(self, driver):
        verdict = _verdict(
            driver,
            snapshots=[_snapshot(n_arguments=3, n_beliefs=2)],
            irreducible=True,
            gap=0.55,
            lam2=0.45,
            eigenvalues=[1.0, 0.45, 0.1],
        )
        text = driver._render_verdict_markdown(verdict, _payload([]), "inner/report.md")
        assert "CANDIDAT #2 LIVRÉ" in text
        assert "Mixing rapide" in text
        assert "NON MESURÉ" not in text
