"""Unit tests for InformalAgent taxonomy injection (#600).

Tests cover:
1. Per-family explicit injection in agent instructions
2. German keyword coverage in FallacyWorkflowPlugin._map_fallacy_to_root_pk
3. Parent harness fallback integration
4. Taxonomy 7-family traversal coverage
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os


class TestInformalAgentInstructions:
    """Verify per-family explicit injection in system instructions."""

    def test_instructions_contain_seven_families(self):
        """INFORMAL_AGENT_INSTRUCTIONS must enumerate all 7 families."""
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            INFORMAL_AGENT_INSTRUCTIONS,
        )

        expected_families = [
            "Insuffisance",
            "Influence",
            "Erreur mathématique",
            "Erreur de raisonnement",
            "Abus de langage",
            "Tricherie",
            "Obstruction",
        ]
        for family in expected_families:
            assert family in INFORMAL_AGENT_INSTRUCTIONS, (
                f"Family '{family}' missing from INFORMAL_AGENT_INSTRUCTIONS"
            )

    def test_instructions_contain_english_family_names(self):
        """INFORMAL_AGENT_INSTRUCTIONS must include English family names."""
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            INFORMAL_AGENT_INSTRUCTIONS,
        )

        expected_en = [
            "Insufficiency",
            "Influence",
            "Mathematical error",
            "Faulty logics",
            "Misleading language",
            "Cheating",
            "Obstruction",
        ]
        for name in expected_en:
            assert name in INFORMAL_AGENT_INSTRUCTIONS, (
                f"English name '{name}' missing from INFORMAL_AGENT_INSTRUCTIONS"
            )

    def test_instructions_contain_systematic_traversal_section(self):
        """INFORMAL_AGENT_INSTRUCTIONS must have systematic traversal section."""
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            INFORMAL_AGENT_INSTRUCTIONS,
        )

        assert "PARCOURS SYSTÉMATIQUE" in INFORMAL_AGENT_INSTRUCTIONS
        assert "list_fallacies_in_category" in INFORMAL_AGENT_INSTRUCTIONS
        assert "CHAQUE famille" in INFORMAL_AGENT_INSTRUCTIONS

    def test_instructions_contain_multilingual_support(self):
        """INFORMAL_AGENT_INSTRUCTIONS must include multilingual guidance."""
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            INFORMAL_AGENT_INSTRUCTIONS,
        )

        assert "multilingue" in INFORMAL_AGENT_INSTRUCTIONS.lower() or "allemand" in INFORMAL_AGENT_INSTRUCTIONS.lower()
        assert "traduisez mentalement" in INFORMAL_AGENT_INSTRUCTIONS.lower()

    def test_instructions_still_has_gold_rule(self):
        """Existing Gold Rule of Specificity must be preserved."""
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            INFORMAL_AGENT_INSTRUCTIONS,
        )

        assert "Spécificité" in INFORMAL_AGENT_INSTRUCTIONS
        assert "explore_fallacy_hierarchy" in INFORMAL_AGENT_INSTRUCTIONS


class TestGermanKeywordCoverage:
    """Verify German keyword support in FallacyWorkflowPlugin keyword mapping."""

    @pytest.fixture
    def plugin(self):
        """Create a FallacyWorkflowPlugin with mock dependencies."""
        with patch(
            "argumentation_analysis.plugins.fallacy_workflow_plugin.TaxonomyNavigator"
        ):
            from argumentation_analysis.plugins.fallacy_workflow_plugin import (
                FallacyWorkflowPlugin,
            )

            mock_kernel = MagicMock()
            mock_llm = MagicMock()
            return FallacyWorkflowPlugin(
                master_kernel=mock_kernel,
                llm_service=mock_llm,
                taxonomy_data=[],
            )

    def test_german_straw_man(self, plugin):
        """'Strohmann' (German for straw man) should map to a root PK."""
        roots_index = {
            "straw man": "PK_straw",
            "insufficiency": "PK_insuf",
        }
        result = plugin._map_fallacy_to_root_pk("Strohmann-Argument", roots_index)
        assert result == "PK_straw"

    def test_german_slippery_slope(self, plugin):
        """'Dammbruch' (German for slippery slope) should map."""
        roots_index = {
            "slippery slope": "PK_slip",
        }
        result = plugin._map_fallacy_to_root_pk("Dammbruch-Argument", roots_index)
        assert result == "PK_slip"

    def test_german_false_dilemma(self, plugin):
        """'Entweder-Oder' (German for false dilemma) should map."""
        roots_index = {
            "false dilemma": "PK_dilemma",
        }
        result = plugin._map_fallacy_to_root_pk("Entweder-Oder Fehlschluss", roots_index)
        assert result == "PK_dilemma"

    def test_german_circular_reasoning(self, plugin):
        """'Zirkelschluss' (German for circular reasoning) should map."""
        roots_index = {
            "circular reasoning": "PK_circ",
        }
        result = plugin._map_fallacy_to_root_pk("Zirkelschluss", roots_index)
        assert result == "PK_circ"

    def test_german_hasty_generalization(self, plugin):
        """'Vorschnelle Verallgemeinerung' should map."""
        roots_index = {
            "hasty generalization": "PK_hasty",
        }
        result = plugin._map_fallacy_to_root_pk(
            "Vorschnelle Verallgemeinerung", roots_index
        )
        assert result == "PK_hasty"

    def test_german_red_herring(self, plugin):
        """'Roter Hering' (German for red herring) should map."""
        roots_index = {
            "red herring": "PK_red",
        }
        result = plugin._map_fallacy_to_root_pk("Roter Hering", roots_index)
        assert result == "PK_red"

    def test_german_poisoning_well(self, plugin):
        """'Brunnenvergiftung' should map."""
        roots_index = {
            "poisoning the well": "PK_pwell",
        }
        result = plugin._map_fallacy_to_root_pk("Brunnenvergiftung", roots_index)
        assert result == "PK_pwell"

    def test_german_bandwagon(self, plugin):
        """'Mitläufereffekt' should map to bandwagon."""
        roots_index = {
            "bandwagon": "PK_band",
        }
        result = plugin._map_fallacy_to_root_pk("Mitläufereffekt", roots_index)
        assert result == "PK_band"

    def test_french_keywords_still_work(self, plugin):
        """Existing French keywords must still work after DE additions."""
        # roots_index uses mixed FR/EN names — matching works via patterns
        roots_index = {
            "straw man": "PK_straw",
            "appel à l'émotion": "PK_emo",
            "faux dilemme": "PK_dilemma",
        }
        assert plugin._map_fallacy_to_root_pk("Appel à l'émotion", roots_index) == "PK_emo"
        assert plugin._map_fallacy_to_root_pk("Faux dilemme", roots_index) == "PK_dilemma"

    def test_english_keywords_still_work(self, plugin):
        """Existing English keywords must still work."""
        roots_index = {
            "authority": "PK_auth",
            "ad hominem": "PK_adh",
            "slippery slope": "PK_slip",
        }
        assert plugin._map_fallacy_to_root_pk("Appeal to authority", roots_index) == "PK_auth"
        assert plugin._map_fallacy_to_root_pk("Ad hominem attack", roots_index) == "PK_adh"
        assert plugin._map_fallacy_to_root_pk("Slippery slope", roots_index) == "PK_slip"


class TestParentHarnessFallback:
    """Verify parent harness fallback function."""

    @pytest.mark.asyncio
    async def test_harness_no_fallacies(self):
        """Harness returns None when no additional fallacies found."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        mock_state = MagicMock()

        with patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_invoke_hierarchical_fallacy_per_argument",
            new_callable=AsyncMock,
            return_value={"fallacies": [], "exploration_method": "per_argument_parallel"},
        ):
            result = await _run_parent_harness_fallback("short text", mock_state)
            assert result is None

    @pytest.mark.asyncio
    async def test_harness_registers_fallacies(self):
        """Harness registers found fallacies into a REAL UnifiedAnalysisState (#648).

        Regression for Track HH: the previous version of this test used a bare
        MagicMock state, on which every attribute (incl. the nonexistent
        ``add_identified_fallacy``) auto-exists — so it passed while the harness
        silently dropped every fallacy on the real state. Use the real state so
        the registration path is actually exercised end-to-end.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="x")
        # The real state must NOT have the singular method the old code relied on.
        assert not hasattr(state, "add_identified_fallacy")
        assert hasattr(state, "add_fallacy")

        fake_fallacies = [
            {
                "fallacy_type": "straw_man",
                "justification": "Detected by parent harness",
                "confidence": 0.85,
                "source_arg_id": "arg-1",
            },
            {
                "fallacy_type": "ad_hominem",
                "justification": "Also detected",
                "confidence": 0.72,
                "source_arg_id": "arg-2",
            },
        ]

        with patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_invoke_hierarchical_fallacy_per_argument",
            new_callable=AsyncMock,
            return_value={
                "fallacies": fake_fallacies,
                "exploration_method": "per_argument_parallel",
            },
        ):
            result = await _run_parent_harness_fallback("long text" * 200, state)
            assert result is not None
            assert result["fallacies_found"] == 2
            assert result["fallacies_registered"] == 2
            # The fallacies must actually land in the canonical state field that
            # DeepSynthesisAgent._build_fallacy_diagnoses reads.
            assert len(state.identified_fallacies) == 2
            types = {f["type"] for f in state.identified_fallacies.values()}
            assert types == {"straw_man", "ad_hominem"}
            targets = {
                f.get("target_argument_id") for f in state.identified_fallacies.values()
            }
            assert targets == {"arg-1", "arg-2"}

    @pytest.mark.asyncio
    async def test_harness_singular_method_fallback(self):
        """State types exposing only add_identified_fallacy still register (#648)."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        # A state spec'd to expose ONLY the singular method (e.g. PhaseScopedState).
        state = MagicMock(spec=["add_identified_fallacy"])

        with patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_invoke_hierarchical_fallacy_per_argument",
            new_callable=AsyncMock,
            return_value={
                "fallacies": [{"type": "post_hoc", "explanation": "x"}],
                "exploration_method": "per_argument_parallel",
            },
        ):
            result = await _run_parent_harness_fallback("long text" * 200, state)
            assert result is not None
            assert result["fallacies_registered"] == 1
            assert state.add_identified_fallacy.call_count == 1

    @pytest.mark.asyncio
    async def test_harness_handles_import_error(self):
        """Harness returns None gracefully on ImportError."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        mock_state = MagicMock()

        with patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_invoke_hierarchical_fallacy_per_argument",
            side_effect=ImportError("not available"),
        ):
            result = await _run_parent_harness_fallback("text", mock_state)
            assert result is None

    @pytest.mark.asyncio
    async def test_harness_handles_generic_error(self):
        """Harness returns None on generic exception."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_parent_harness_fallback,
        )

        mock_state = MagicMock()

        with patch(
            "argumentation_analysis.orchestration.invoke_callables."
            "_invoke_hierarchical_fallacy_per_argument",
            side_effect=RuntimeError("API key missing"),
        ):
            result = await _run_parent_harness_fallback("text", mock_state)
            assert result is None


class TestTaxonomyFamilyCoverage:
    """Verify taxonomy CSV has expected structure."""

    def test_taxonomy_has_seven_families(self):
        """taxonomy_full.csv must have exactly 7 depth-1 families."""
        import pandas as pd

        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "data",
            "taxonomy_full.csv",
        )
        csv_path = os.path.normpath(csv_path)
        if not os.path.exists(csv_path):
            pytest.skip("taxonomy_full.csv not found")

        df = pd.read_csv(csv_path)
        depth1 = df[df["depth"] == 1]
        assert len(depth1) == 7, f"Expected 7 families, got {len(depth1)}"

    def test_taxonomy_has_required_columns(self):
        """taxonomy_full.csv must have FR and EN columns."""
        import pandas as pd

        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "data",
            "taxonomy_full.csv",
        )
        csv_path = os.path.normpath(csv_path)
        if not os.path.exists(csv_path):
            pytest.skip("taxonomy_full.csv not found")

        df = pd.read_csv(csv_path)
        required = ["PK", "depth", "Famille", "text_fr", "text_en", "desc_en"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_no_german_columns_yet(self):
        """Confirm DE language columns are not yet in taxonomy (expected baseline).

        crossLink_Denounces contains '_de' substring but is NOT a German column.
        We check for explicit language columns like text_de, desc_de, etc.
        """
        import pandas as pd

        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "data",
            "taxonomy_full.csv",
        )
        csv_path = os.path.normpath(csv_path)
        if not os.path.exists(csv_path):
            pytest.skip("taxonomy_full.csv not found")

        df = pd.read_csv(csv_path)
        de_lang_cols = [
            c for c in df.columns
            if c.startswith(("text_de", "desc_de", "example_de", "link_de", "Family_de"))
        ]
        # When DE enrichment is added, this test should be updated.
        assert len(de_lang_cols) == 0, f"Unexpected DE language columns: {de_lang_cols}"
