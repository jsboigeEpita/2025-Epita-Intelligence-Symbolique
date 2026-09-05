"""#2036 tranche 1 — the two raw editorial notes never reach a loaded taxonomy.

PK 41 and PK 992 of the vendored Argumentum fallacies taxonomy carry raw
editorial notes in ``nom_vulgarisé`` (verbatim upstream: a titling
brainstorm « Je n'aime aucun des titres… » and a column-swap question
« ON INVERSERAIT PAS LE TEXT_FR… »). ``taxonomy_sophism_detector`` echoes
``nom_vulgarisé`` on every detection, so a detection of PK 41 can put the
whole note in reader prose.

The vendored CSV stays a byte-faithful mirror of upstream (integrity guard
#1956): the purge lives in a code-level override applied at load. These
tests pin the property on every loader that feeds a name-bearing surface —
the informal plugin dataframe (runtime detector chain), the fallacy
workflow plugin's navigator (runtime LLM prompts), and the benchmark runner
(evaluation reports).
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import semantic_kernel as sk

from argumentation_analysis.paths import DATA_DIR

REAL_CSV = Path(DATA_DIR) / "argumentum_fallacies_taxonomy.csv"

# The two known raw editorial notes (upstream Argumentum content, not corpus
# text — quotable verbatim).
_NOTE_SIGNATURES = (
    "aucun des titres",
    "ON INVERSERAIT PAS LE TEXT_FR",
)
_PURGED_PKS = ("41", "992")


def _real_csv_rows() -> list:
    with open(REAL_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestOverrideTableTargetsExistingRows:
    """A dead override (PK absent from the data) would be a silent no-op —
    the 'garde périmée' shape. Every purged PK must exist upstream."""

    def test_every_purged_pk_exists_in_the_csv(self):
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            EDITORIAL_NOTE_PURGES,
        )

        rows = _real_csv_rows()
        present = {r["PK"] for r in rows}
        for pk in EDITORIAL_NOTE_PURGES:
            assert str(pk) in present, (
                f"PK {pk} is purged by the override table but absent from "
                "the vendored CSV — the override is dead"
            )


class TestInformalPluginDataframeIsPurged:
    def test_purged_pks_carry_no_editorial_note(self):
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            InformalAnalysisPlugin,
        )

        plugin = InformalAnalysisPlugin(
            kernel=MagicMock(spec=sk.Kernel), taxonomy_file_path=str(REAL_CSV)
        )
        df = plugin._get_taxonomy_dataframe()

        assert "nom_vulgarisé" in df.columns
        for pk in _PURGED_PKS:
            assert int(pk) in df.index
            value = df.loc[int(pk), "nom_vulgarisé"]
            assert value == "" or value is None or value != value, (
                f"PK {pk} nom_vulgarisé should be empty after the purge, got: {value!r}"
            )

    def test_no_editorial_note_signature_in_the_column(self):
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            InformalAnalysisPlugin,
        )

        plugin = InformalAnalysisPlugin(
            kernel=MagicMock(spec=sk.Kernel), taxonomy_file_path=str(REAL_CSV)
        )
        df = plugin._get_taxonomy_dataframe()
        for value in df["nom_vulgarisé"].fillna("").astype(str):
            for signature in _NOTE_SIGNATURES:
                assert signature not in value


class TestFallacyWorkflowNavigatorIsPurged:
    def test_navigator_rows_carry_no_editorial_note(self):
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        plugin = FallacyWorkflowPlugin(
            master_kernel=sk.Kernel(),
            llm_service=MagicMock(),
            taxonomy_file_path=str(REAL_CSV),
        )
        for pk in _PURGED_PKS:
            node = plugin.taxonomy_navigator.get_node(pk)
            assert node is not None, f"PK {pk} missing from navigator"
            assert node.get("nom_vulgarisé", "") == "", (
                f"PK {pk} nom_vulgarisé should be empty after the purge"
            )


class TestBenchmarkRunnerIsPurged:
    def test_benchmark_rows_carry_no_editorial_note(self):
        from argumentation_analysis.evaluation.fallacy_benchmark import (
            FallacyBenchmarkRunner,
        )

        runner = FallacyBenchmarkRunner()
        for pk in _PURGED_PKS:
            node = runner.node_map.get(pk)
            assert node is not None, f"PK {pk} missing from benchmark rows"
            assert node.get("nom_vulgarisé", "") == "", (
                f"PK {pk} nom_vulgarisé should be empty after the purge"
            )
