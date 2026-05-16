"""Unit tests for FormalAgent FOL-by-default behavior (#552).

Tests verify:
- FormalAgent instructions specify FOL as default (not gated on quantifiers)
- PL is listed as fallback when FOL fails
- Instructions preserve shared state consultation (ETAPE 0)
- Instructions preserve validation (ETAPE 2), Dung (ETAPE 3), storage (ETAPE 4)
"""

import pytest


class TestFormalAgentFOLDefault:

    def test_fol_is_default_translation(self):
        """FormalAgent should start with FOL, not PL."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        # ETAPE 1 should say "commence par translate_to_fol"
        assert "translate_to_fol" in instructions
        assert "commence par translate_to_fol" in instructions

    def test_pl_is_fallback(self):
        """PL should be listed as fallback when FOL fails."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "translate_to_pl" in instructions
        assert "fallback" in instructions

    def test_no_quantifier_gating(self):
        """FOL should NOT be gated on detecting quantifiers."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        # The old gating text "Si l'argument contient des quantificateurs"
        # should NOT appear in ETAPE 1
        assert "Si l'argument contient des quantificateurs" not in instructions

    def test_fol_rationale_present(self):
        """Instructions should explain WHY FOL is default."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "logique par defaut" in instructions
        assert "relations" in instructions or "predicats" in instructions

    def test_etape_0_preserved(self):
        """ETAPE 0 (shared state consultation) should still be present."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 0" in instructions
        assert "atomic_propositions" in instructions
        assert "fol_shared_signature" in instructions

    def test_etape_2_validation_preserved(self):
        """ETAPE 2 (Tweety validation) should still reference FOL consistency."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 2" in instructions
        assert "check_fol_consistency" in instructions
        assert "check_propositional_consistency" in instructions

    def test_etape_3_dung_preserved(self):
        """ETAPE 3 (Dung analysis) should still be present."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 3" in instructions
        assert "analyze_dung_framework" in instructions

    def test_etape_4_storage_preserved(self):
        """ETAPE 4 (storage) should still reference FOL results."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 4" in instructions
        assert "logic_type='fol'" in instructions
