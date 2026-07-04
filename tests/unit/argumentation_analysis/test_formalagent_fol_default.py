"""Unit tests for FormalAgent translation logic (#552, rebalanced #1396).

#1396 retired the 'FOL-by-default' bias that starved modal in the coordinated
pipeline (R544/R545 root cause). The 3 logics (PL/FOL/modal) are now co-equal,
cue-keyed. Tests verify the rebalanced behavior while preserving the FOL
rationale content (relations/predicates, #1375) and the ETAPE 0-4 structure.
"""

import pytest


class TestFormalAgentFOLDefault:

    def test_fol_is_default_translation(self):
        """FormalAgent should start with FOL, not PL.

        Post-CONV-C (#1345) the ETAPE 1 wording evolved from the single-shot
        "commence par translate_to_fol" to a 2-pass coordinated flow that builds
        a shared signature first. The FOL-default INTENT is preserved: FOL
        formulas are generated BEFORE PL in ETAPE 1 (generate_fol_formulas
        precedes generate_pl_formulas), and translate_to_fol remains the
        no-shared-inventory fallback. We assert the current primary FOL path +
        the fallback rather than the retired word-level phrase.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        # FOL is generated first in the 2-pass coordinated ETAPE 1 (#1345)
        assert "generate_fol_formulas_with_shared_signature" in instructions
        # translate_to_fol remains the fallback when no shared inventory exists
        assert "translate_to_fol" in instructions
        # FOL generation must appear before PL generation (FOL is the default)
        assert instructions.index("generate_fol_formulas") < instructions.index(
            "generate_pl_formulas"
        )

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
        """#1396: FOL rationale preserved in CONTENT while 'par defaut' bias retired.

        The ETAPE 1 RAISONNEMENT was rebalanced from 'FOL par defaut' to 3
        co-equal cue-keyed logics (#1396 anti-pendule: retire the bias that
        starved modal, don't replace it). The FOL rationale CONTENT
        (relations/predicates between entities, #1375) is preserved.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
        )

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        # FOL rationale content preserved (#1375 intent)
        assert "relations" in instructions or "predicats" in instructions
        # The bias phrase 'logique par defaut' is RETIRED (#1396 anti-pendule)
        assert "logique par defaut" not in instructions
        # 3 logics co-equal cue-keyed rationale is present
        assert "co-egales" in instructions

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
        # CONV-B #1333 DoD #1: ETAPE 2 must cite the REAL advertised
        # kernel_function names. The instruction previously named
        # ``check_propositional_consistency`` / ``check_modal_satisfiability``
        # (TweetyLogicPlugin method names that are NOT registered on the
        # conversational kernel's manifest), so the FormalAgent LLM could not
        # resolve them and never emitted the tool_calls -> 0 decider verdicts.
        # The manifest advertises ``LogicAgentPlugin-check_pl_consistency``
        # (and check_fol/modal_consistency); the instruction now cites those.
        assert "check_pl_consistency" in instructions
        assert "check_modal_consistency" in instructions

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
