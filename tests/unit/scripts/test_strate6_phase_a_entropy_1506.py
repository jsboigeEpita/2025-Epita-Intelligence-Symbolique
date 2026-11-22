"""#1506 R1107 — the Phase-A driver reports the three discrimination quantities.

The reference regimes are deliberately independent of every corpus and of the
LLM pipeline.  A reversible four-state ring has zero entropy production.  The
same ring with clockwise drift has the closed-form value

    sigma = n * (1 / n) * (forward - reverse) * ln(forward / reverse)
          = 4 * 0.25 * 0.8 * ln 9.

The driver must expose that value together with the directed spectral gap and
the ergodicity verdict.  When several recurrent classes leave the stationary
distribution non-unique, substituting an empirical occupancy distribution
would produce a number that is not *the* chain's entropy production, so that
case must be named rather than filled with a plausible value.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_driver():
    path = _REPO_ROOT / "scripts" / "coursia_strate6_phaseA_grounding.py"
    spec = importlib.util.spec_from_file_location("strate6_phaseA_sigma", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def driver():
    return _load_driver()


def _ring(forward: float) -> list[list[float]]:
    n = 4
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][(i + 1) % n] = forward
        matrix[i][(i - 1) % n] = 1.0 - forward
    return matrix


def test_reversible_and_drift_rings_have_the_closed_form_sigma(driver):
    reversible = driver.entropy_production(_ring(0.5))
    drift = driver.entropy_production(_ring(0.9))

    assert reversible.analysis_skipped is False
    assert reversible.irreducible is True
    assert reversible.sigma == pytest.approx(0.0, abs=1e-12)
    assert drift.analysis_skipped is False
    assert drift.irreducible is True
    assert drift.sigma == pytest.approx(0.8 * math.log(9.0), rel=1e-12)
    assert drift.sigma > reversible.sigma


def test_a_transient_cascade_does_not_invent_a_one_way_pair(driver):
    forward_cascade = [
        [0.5, 0.5, 0.0, 0.0],
        [0.0, 0.5, 0.5, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 1.0, 0.0],
    ]
    result = driver.entropy_production(forward_cascade)

    assert result.analysis_skipped is False
    assert result.irreducible is False
    assert result.one_way_pairs == 0
    assert result.sigma == pytest.approx(0.0, abs=1e-12)
    assert result.stationary == pytest.approx([0.0, 0.0, 0.5, 0.5], abs=1e-9)


def test_an_irreducible_one_way_chain_reports_positive_infinity(driver):
    clockwise_only = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        clockwise_only[i][(i + 1) % 4] = 1.0
    result = driver.entropy_production(clockwise_only)

    assert result.analysis_skipped is True
    assert result.irreducible is True
    assert result.sigma is None
    assert result.one_way_pairs == 4
    assert "+inf" in result.skip_reason
    assert result.stationary == pytest.approx([0.25] * 4)


def test_one_recurrent_class_with_a_transient_state_has_a_unique_pi(driver):
    matrix = [
        [0.5, 0.5, 0.0],
        [0.5, 0.5, 0.0],
        [0.5, 0.5, 0.0],
    ]
    result = driver.entropy_production(matrix)

    assert result.analysis_skipped is False
    assert result.irreducible is False
    assert result.sigma == pytest.approx(0.0, abs=1e-12)
    assert result.stationary == pytest.approx([0.5, 0.5, 0.0])


def test_two_recurrent_classes_refuse_a_surrogate_stationary(driver):
    matrix = [
        [0.5, 0.5, 0.0],
        [0.5, 0.5, 0.0],
        [0.0, 0.0, 1.0],
    ]
    result = driver.entropy_production(matrix)

    assert result.analysis_skipped is True
    assert result.irreducible is False
    assert result.sigma is None
    assert "unique stationary" in result.skip_reason


def test_the_verdict_carries_all_three_quantities_and_renders_sigma(driver):
    matrix = _ring(0.9)
    ergodicity = driver.ergodicity_from_matrix(matrix)
    spectral = driver.spectral_gap(matrix)
    entropy = driver.entropy_production(matrix)
    payload = {
        "n_trajectories": 1,
        "n_observations_total": 8,
        "n_transitions": 7,
        "n_states": 4,
        "impossible": False,
        "trajectories": [
            {"observations": [{"snapshot": {"n_arguments": 1, "n_beliefs": 1}}]}
        ],
    }
    verdict = driver._build_verdict(
        "R", payload, ergodicity, spectral, entropy_result=entropy
    )
    assert verdict.entropy["sigma"] == pytest.approx(0.8 * math.log(9.0))
    assert verdict.ergodicity["irreducible"] is True
    assert verdict.spectral["spectral_gap"] == pytest.approx(0.0, abs=1e-12)

    text = driver._render_verdict_markdown(verdict, payload, "inner/report.md")
    assert "Production d'entropie" in text
    assert "σ = **1.7578**" in text


def test_reference_regimes_are_separated_by_sigma_not_by_the_gap(driver):
    reversible = _ring(0.5)
    drift = _ring(0.9)
    reversible_ergodicity = driver.ergodicity_from_matrix(reversible)
    drift_ergodicity = driver.ergodicity_from_matrix(drift)

    assert reversible_ergodicity["irreducible"] is True
    assert drift_ergodicity["irreducible"] is True
    assert driver.spectral_gap(reversible).spectral_gap == pytest.approx(0.0, abs=1e-12)
    assert driver.spectral_gap(drift).spectral_gap == pytest.approx(0.0, abs=1e-12)
    assert driver.entropy_production(reversible).sigma == pytest.approx(0.0, abs=1e-12)
    assert driver.entropy_production(drift).sigma == pytest.approx(
        0.8 * math.log(9.0), rel=1e-12
    )


def test_run_for_corpus_persists_sigma_not_scraped_ergodicity(
    driver, tmp_path, monkeypatch
):
    matrix = _ring(0.9)
    counts = [[int(round(value * 10)) for value in row] for row in matrix]
    inner_dir = tmp_path / "inner"
    inner_dir.mkdir()
    tpm_json = inner_dir / "tpm.json"
    tpm_json.write_text(
        json.dumps(
            {
                "n_trajectories": 1,
                "n_observations_total": 8,
                "n_transitions": 7,
                "n_states": 4,
                "impossible": False,
                "tpm": {"transition_counts": counts},
                "trajectories": [
                    {
                        "corpus_id": "regime_R",
                        "corpus_label": "regime_R",
                        "observations": [
                            {
                                "snapshot": {
                                    "n_arguments": 1,
                                    "n_fallacies": 0,
                                    "n_counters": 0,
                                    "n_beliefs": 1,
                                }
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (inner_dir / "report.md").write_text(
        "## Analyse d'ergodicité\n- Irréductible : **NON**\n- SCC : **99**\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(driver, "INNER_TPM_ROOT", inner_dir)
    monkeypatch.setattr(driver, "_run_inner_extractor", lambda *args: tpm_json)
    verdict_dir = driver.run_for_corpus("R", tmp_path / "out", 1.0, 1.0)
    verdict = json.loads((verdict_dir / "verdict.json").read_text(encoding="utf-8"))

    assert verdict["ergodicity"]["irreducible"] is True
    assert verdict["ergodicity"]["n_scc"] == 1
    assert "raw_section" not in verdict["ergodicity"]
    assert verdict["entropy"]["sigma"] == pytest.approx(0.8 * math.log(9.0))
    assert verdict["spectral"]["spectral_gap"] == pytest.approx(0.0, abs=1e-12)
    assert "σ = **1.7578**" in (verdict_dir / "verdict.md").read_text(encoding="utf-8")
