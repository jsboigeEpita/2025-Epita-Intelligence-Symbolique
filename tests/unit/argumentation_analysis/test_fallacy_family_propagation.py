# -*- coding: utf-8 -*-
"""Tests for fallacy family propagation through the analysis pipeline (#714).

Verifies that the CSV ``Famille`` column survives the full chain:
  identification_models → shared_state → state_writers → deep_synthesis_agent
"""

import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)
from argumentation_analysis.plugins.identification_models import IdentifiedFallacy
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    FallacyDiagnosis,
)


# ---------------------------------------------------------------------------
# 1. IdentifiedFallacy model carries family
# ---------------------------------------------------------------------------


class TestIdentifiedFallacyModel:
    """Step 1: Pydantic model accepts and stores the family field."""

    def test_identified_fallacy_carries_family(self):
        f = IdentifiedFallacy(
            fallacy_type="Appel à la peur",
            taxonomy_pk="pk_42",
            explanation="Uses fear to persuade",
            family="Influence",
        )
        assert f.family == "Influence"

    def test_identified_fallacy_default_empty(self):
        f = IdentifiedFallacy(
            fallacy_type="Ad hominem",
            taxonomy_pk="pk_7",
            explanation="Personal attack",
        )
        assert f.family == ""


# ---------------------------------------------------------------------------
# 2. shared_state stores family
# ---------------------------------------------------------------------------


class TestSharedStateFamily:
    """Step 2: add_fallacy stores family / taxonomy_path in the entry dict."""

    def test_add_fallacy_stores_family(self):
        state = RhetoricalAnalysisState("test text")
        fid = state.add_fallacy(
            "ad hominem",
            "Personal attack",
            family="Tricherie",
            taxonomy_path="Tricherie > Manipulation > Ad hominem",
        )
        entry = state.identified_fallacies[fid]
        assert entry["family"] == "Tricherie"
        assert entry["taxonomy_path"] == "Tricherie > Manipulation > Ad hominem"

    def test_add_fallacy_backward_compat(self):
        """Old callers that omit family/taxonomy_path still work."""
        state = RhetoricalAnalysisState("test text")
        fid = state.add_fallacy("slippery slope", "Unwarranted causal chain")
        entry = state.identified_fallacies[fid]
        assert "family" not in entry
        assert "taxonomy_path" not in entry
        assert entry["type"] == "slippery slope"

    def test_add_identified_fallacies_passes_famille(self):
        """add_identified_fallacies reads 'famille' key and passes it through."""
        state = UnifiedAnalysisState("test text")
        state.add_identified_fallacies(
            [
                {
                    "nom": "Appel au peuple",
                    "explication": "Bandwagon appeal",
                    "famille": "Influence",
                    "taxonomy_path": "Influence > Appel au peuple",
                }
            ]
        )
        # Find the fallacy entry
        entries = list(state.identified_fallacies.values())
        assert len(entries) == 1
        assert entries[0]["family"] == "Influence"
        assert entries[0]["taxonomy_path"] == "Influence > Appel au peuple"


# ---------------------------------------------------------------------------
# 3. DeepSynthesisAgent reads stored family
# ---------------------------------------------------------------------------


class TestSynthesisFamilyRead:
    """Step 6: _build_fallacy_diagnoses prefers stored family over keyword table."""

    def test_build_fallacy_diagnoses_uses_stored_family(self):
        """When family is in the state dict, synthesis uses it directly."""
        state = UnifiedAnalysisState("test text")
        state.add_fallacy(
            "Pseudorationalisme",
            "Appears rational but isn't",
            family="Tricherie",
            taxonomy_path="Tricherie > Pensée biaisée > Pseudorationalisme",
        )
        diagnoses = DeepSynthesisAgent._build_fallacy_diagnoses(state)
        assert len(diagnoses) == 1
        d = diagnoses[0]
        assert isinstance(d, FallacyDiagnosis)
        assert d.family == "Tricherie"
        assert "Tricherie" in d.taxonomy_path
        assert "Pseudorationalisme" in d.taxonomy_path

    def test_build_fallacy_diagnoses_fallback_to_keyword(self):
        """When family is empty, synthesis falls back to _fallacy_family keyword table."""
        state = UnifiedAnalysisState("test text")
        # "ad hominem" matches the keyword table → "presumption"
        state.add_fallacy("ad hominem", "Personal attack")
        diagnoses = DeepSynthesisAgent._build_fallacy_diagnoses(state)
        assert len(diagnoses) == 1
        d = diagnoses[0]
        assert d.family != ""  # keyword table should resolve something
        assert "ad hominem" in d.taxonomy_path


# ---------------------------------------------------------------------------
# 4. All 7 CSV families propagate end-to-end
# ---------------------------------------------------------------------------

CSV_FAMILIES = [
    "Insuffisance",
    "Influence",
    "Erreur mathematique",
    "Erreur de raisonnement",
    "Abus de langage",
    "Tricherie",
    "Obstruction",
]


@pytest.mark.parametrize("family", CSV_FAMILIES)
def test_all_7_csv_families_propagate(family: str):
    """Each of the 7 CSV families survives through state → synthesis."""
    fallacy_name = f"Sophisme de test ({family})"
    state = UnifiedAnalysisState("test text")
    state.add_fallacy(
        fallacy_name,
        f"Test justification for {family}",
        family=family,
    )
    diagnoses = DeepSynthesisAgent._build_fallacy_diagnoses(state)
    assert len(diagnoses) == 1
    assert diagnoses[0].family == family
