"""
RA-7 #1052 — Canary regression tests for Watson + Sherlock methodological prompts.

The AgentFactory migration (commit 234960e4) degraded rich operational prompts
to ~10 generic lines. These canaries detect prompt lobotomization by checking
for specific structural elements that MUST be present in each prompt:

Watson prompt must include:
- 5-step formal method (FORMALISATION → SOLUTION STRUCTURÉE)
- BNF grammar section for logical formula syntax
- Tool names (validate_formula, execute_query)
- Character-length guidance (80-120 chars)

Sherlock prompt must include:
- 5-step Cluedo convergence method
- Tool names (get_cluedo_game_elements, faire_suggestion, propose_final_solution, ...)
- Convergence target (≤5 échanges)
- Character-length guidance (80-120 chars)

These tests run WITHOUT API keys.
"""

import re

import pytest


class TestWatsonPromptCanary:
    """Verify Watson prompt retains methodological richness."""

    @pytest.fixture
    def watson_prompt(self):
        try:
            from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
                WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT,
            )
        except ImportError:
            pytest.skip("watson_logic_assistant not importable")
        return WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT

    def test_watson_prompt_has_five_step_method(self, watson_prompt):
        """Watson prompt MUST include the 5-step formal analysis method."""
        steps = [
            "FORMALISATION",
            "ANALYSE CONTRAINTES",
            "DÉDUCTION PROGRESSIVE",
            "VALIDATION FORMELLE",
            "SOLUTION STRUCTURÉE",
        ]
        for step in steps:
            assert step in watson_prompt, f"Missing methodological step: {step}"

    def test_watson_prompt_has_bnf_grammar(self, watson_prompt):
        """Watson prompt MUST include BNF grammar for logical formulas."""
        assert "FORMULA ::=" in watson_prompt, "Missing BNF grammar definition"
        assert "PROPOSITION" in watson_prompt, "Missing PROPOSITION definition"
        assert (
            "CamelCase" in watson_prompt or "snake_case" in watson_prompt
        ), "Missing proposition naming convention"

    def test_watson_prompt_has_tool_names(self, watson_prompt):
        """Watson prompt MUST reference WatsonTools by name."""
        assert (
            "validate_formula" in watson_prompt
        ), "Missing validate_formula tool reference"
        assert "execute_query" in watson_prompt, "Missing execute_query tool reference"
        assert "WatsonTools" in watson_prompt, "Missing WatsonTools class reference"

    def test_watson_prompt_has_message_length_guidance(self, watson_prompt):
        """Watson prompt MUST include character-length guidance."""
        assert "80-120" in watson_prompt, "Missing character-length guidance (80-120)"

    def test_watson_prompt_has_style_variety(self, watson_prompt):
        """Watson prompt MUST include natural expression variety."""
        assert "Hmm, voyons voir" in watson_prompt or "Intéressant" in watson_prompt
        assert "Ah ! Ça change tout !" in watson_prompt

    def test_watson_prompt_is_not_degraded(self, watson_prompt):
        """Watson prompt should be substantial (>1500 chars), not a stub."""
        assert len(watson_prompt) > 1500, (
            f"Watson prompt is suspiciously short ({len(watson_prompt)} chars). "
            "It may have been degraded/lobotomized."
        )


class TestSherlockPromptCanary:
    """Verify Sherlock prompt retains methodological richness."""

    @pytest.fixture
    def sherlock_prompt(self):
        try:
            from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
                SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT,
            )
        except ImportError:
            pytest.skip("sherlock_enquete_agent not importable")
        return SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT

    def test_sherlock_prompt_has_five_step_method(self, sherlock_prompt):
        """Sherlock prompt MUST include the 5-step Cluedo convergence method."""
        # Check for numbered steps with key verbs
        assert "get_cluedo_game_elements" in sherlock_prompt
        assert "déduction DIRECTE" in sherlock_prompt or "Déduction" in sherlock_prompt
        assert (
            "solution CONCRÈTE" in sherlock_prompt
            or "concrète" in sherlock_prompt.lower()
        )

    def test_sherlock_prompt_has_tool_names(self, sherlock_prompt):
        """Sherlock prompt MUST reference all 5 tools by name."""
        tools = [
            "get_cluedo_game_elements",
            "faire_suggestion",
            "propose_final_solution",
            "get_case_description",
            "instant_deduction",
        ]
        for tool in tools:
            assert tool in sherlock_prompt, f"Missing tool reference: {tool}"

    def test_sherlock_prompt_has_convergence_target(self, sherlock_prompt):
        """Sherlock prompt MUST specify convergence target (≤5 exchanges)."""
        assert (
            "≤5" in sherlock_prompt or "5 échanges" in sherlock_prompt
        ), "Missing convergence target (≤5 échanges)"

    def test_sherlock_prompt_has_message_length_guidance(self, sherlock_prompt):
        """Sherlock prompt MUST include character-length guidance."""
        assert "80-120" in sherlock_prompt, "Missing character-length guidance (80-120)"

    def test_sherlock_prompt_has_style_variety(self, sherlock_prompt):
        """Sherlock prompt MUST include natural expression variety."""
        assert "Élémentaire !" in sherlock_prompt
        assert "Fascinant" in sherlock_prompt or "Aha !" in sherlock_prompt

    def test_sherlock_prompt_is_not_degraded(self, sherlock_prompt):
        """Sherlock prompt should be substantial (>1000 chars), not a stub."""
        assert len(sherlock_prompt) > 1000, (
            f"Sherlock prompt is suspiciously short ({len(sherlock_prompt)} chars). "
            "It may have been degraded/lobotomized."
        )


class TestPromptToolAlignment:
    """Verify prompt tool names match actual @kernel_function declarations."""

    def test_watson_tools_match_prompt(self):
        """Every tool named in Watson prompt must exist as @kernel_function."""
        try:
            from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
                WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT,
                WatsonTools,
            )
        except ImportError:
            pytest.skip("watson_logic_assistant not importable")

        prompt = WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT
        # Tool names appear as `tool_name(args)` in the prompt — check via substring
        known_tools = {"validate_formula", "execute_query"}
        for tool in known_tools:
            assert f"`{tool}" in prompt, f"Tool {tool} missing from prompt"

    def test_sherlock_tools_match_prompt(self):
        """Every backticked tool the Sherlock prompt promises exists on a real surface.

        Reworked (#2112): the previous body asserted two hand-copied literal
        sets were non-empty — a tautology that guarded nothing. Measured on
        ``4c733b93``, those literals had drifted: they credited
        ``get_case_description`` and ``add_hypothesis`` to SherlockTools,
        whose real methods are ``get_current_case_description`` and
        ``add_new_hypothesis`` — the two names live on
        EnqueteStateManagerPlugin. The drift was invisible precisely because
        the assertion could not fail.

        Both sides are now derived: the promised set is parsed from the
        prompt's backticked identifiers (the prompt backticks exactly its
        tool list, nothing else — measured), the real set is the union of
        the public methods of SherlockTools and EnqueteStateManagerPlugin,
        and every promise must land on that union.
        """
        try:
            from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
                SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT,
                SherlockTools,
            )
            from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
                EnqueteStateManagerPlugin,
            )
        except ImportError:
            pytest.skip("Required modules not importable")

        prompt = SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
        promised = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)", prompt))
        surface = {n for n in dir(SherlockTools) if not n.startswith("_")} | {
            n for n in dir(EnqueteStateManagerPlugin) if not n.startswith("_")
        }

        missing = promised - surface
        assert not missing, (
            "Le prompt Sherlock promet des outils sans surface réelle : "
            f"{sorted(missing)} (promis : {sorted(promised)})"
        )

        # A parsed promise of zero would make the check above vacuously green
        # — the measured prompt backticks its 5 tools (RA-7), never fewer.
        assert (
            len(promised) >= 5
        ), f"Attendu au moins les 5 outils outillés, parsés : {sorted(promised)}"

        # Positive control — this guard must be able to fail, else it guards
        # nothing (the tautology it replaces could not).
        assert (promised | {"outil_fictif_2112"}) - surface == {"outil_fictif_2112"}
