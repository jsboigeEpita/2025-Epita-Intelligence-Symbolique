"""
RA-9 #1061 — Value-gate tests for D6/D7 detection directive refinement.

These tests verify that the fallacy descent prompts contain explicit guidance
for detecting:

- D6: Indirect/implicit circular reasoning (petitio principii via paraphrase,
  not just literal repetition)
- D7: Appeal to emotion as primary persuasive operator (distinct from
  illustrative emotional language)

The tests also verify a negative case: that the directives do NOT transform
every reformulation into circularity or every emotional expression into a
fallacy — this would be the pendulum failure.

These tests run WITHOUT API keys (prompt-content-only assertions).
"""

import pytest


class TestDescentPromptD6CircularIndirect:
    """Verify descent prompts contain guidance for indirect circular reasoning."""

    @pytest.fixture
    def plugin_source(self):
        try:
            from argumentation_analysis.plugins import fallacy_workflow_plugin
        except ImportError:
            pytest.skip("fallacy_workflow_plugin not importable")
        import inspect
        return inspect.getsource(fallacy_workflow_plugin.FallacyWorkflowPlugin)

    def test_descent_system_prompt_mentions_circular_paraphrase(self, plugin_source):
        """Main descent system prompt MUST mention paraphrase/indirect circular reasoning."""
        assert "paraphrase" in plugin_source.lower() or "paraphrasée" in plugin_source.lower(), (
            "Descent prompt missing guidance on paraphrase-based circular reasoning (D6)"
        )

    def test_descent_system_prompt_mentions_implicit_circularity(self, plugin_source):
        """Main descent system prompt MUST mention implicit circularity."""
        assert "implicit" in plugin_source.lower() or "implicite" in plugin_source.lower(), (
            "Descent prompt missing guidance on implicit circularity (D6)"
        )

    def test_descent_system_prompt_mentions_petitio_or_circular(self, plugin_source):
        """Descent prompt MUST reference circular reasoning or petitio principii."""
        has_circular = (
            "circular" in plugin_source.lower()
            or "circulaire" in plugin_source.lower()
            or "petitio" in plugin_source.lower()
        )
        assert has_circular, (
            "Descent prompt missing reference to circular reasoning / petitio principii"
        )


class TestDescentPromptD7EmotionOperator:
    """Verify descent prompts distinguish emotional operator from illustration."""

    @pytest.fixture
    def plugin_source(self):
        try:
            from argumentation_analysis.plugins import fallacy_workflow_plugin
        except ImportError:
            pytest.skip("fallacy_workflow_plugin not importable")
        import inspect
        return inspect.getsource(fallacy_workflow_plugin.FallacyWorkflowPlugin)

    def test_descent_prompt_mentions_appeal_to_emotion(self, plugin_source):
        """Descent prompt MUST mention appeal to emotion as a fallacy category."""
        has_emotion = (
            "appeal to emotion" in plugin_source.lower()
            or "appel" in plugin_source.lower() and "émotion" in plugin_source.lower()
            or "appeal.*emotion" in plugin_source.lower()
        )
        assert has_emotion, (
            "Descent prompt missing reference to appeal to emotion (D7)"
        )

    def test_descent_prompt_distinguishes_operator_from_illustration(self, plugin_source):
        """Descent prompt MUST distinguish emotional operator from illustrative emotion."""
        src_lower = plugin_source.lower()
        has_operator = (
            ("operator" in src_lower or "opérateur" in src_lower or "primary" in src_lower)
            and ("illustrat" in src_lower or "accessoire" in src_lower or "merely" in src_lower)
        )
        assert has_operator, (
            "Descent prompt missing distinction between emotional operator (fallacious) "
            "and illustrative emotion (non-fallacious) — D7 anti-pendule guard"
        )

    def test_descent_prompt_mentions_fear_indignation_pride(self, plugin_source):
        """Descent prompt SHOULD mention specific emotion types for D7 coverage."""
        src_lower = plugin_source.lower()
        emotion_types = ["fear", "indignation", "pride", "peur", "indignation", "fierté"]
        found = sum(1 for e in emotion_types if e in src_lower)
        assert found >= 2, (
            f"Descent prompt should mention specific emotion types for D7 detection. "
            f"Found {found}/6 expected keywords."
        )


class TestLeafPromptD6D7Guidance:
    """Verify leaf confirmation prompt has D6/D7 guidance."""

    @pytest.fixture
    def plugin_source(self):
        try:
            from argumentation_analysis.plugins import fallacy_workflow_plugin
        except ImportError:
            pytest.skip("fallacy_workflow_plugin not importable")
        import inspect
        return inspect.getsource(fallacy_workflow_plugin.FallacyWorkflowPlugin)

    def test_leaf_system_prompt_has_circular_guidance(self, plugin_source):
        """Leaf confirmation prompt MUST include circular reasoning guidance."""
        src_lower = plugin_source.lower()
        assert "circular" in src_lower or "circulaire" in src_lower, (
            "Leaf confirmation prompt missing circular reasoning guidance"
        )

    def test_leaf_system_prompt_has_emotion_guidance(self, plugin_source):
        """Leaf confirmation prompt MUST include appeal to emotion guidance."""
        src_lower = plugin_source.lower()
        assert "emotion" in src_lower, (
            "Leaf confirmation prompt missing appeal to emotion guidance"
        )


class TestBeamDescentPromptD6D7:
    """Verify beam descent system prompt includes D6/D7 awareness."""

    @pytest.fixture
    def plugin_source(self):
        try:
            from argumentation_analysis.plugins import fallacy_workflow_plugin
        except ImportError:
            pytest.skip("fallacy_workflow_plugin not importable")
        import inspect
        return inspect.getsource(fallacy_workflow_plugin.FallacyWorkflowPlugin)

    def test_beam_prompt_mentions_paraphrase_or_indirect(self, plugin_source):
        """Beam descent prompt MUST be aware of indirect forms."""
        src_lower = plugin_source.lower()
        has_indirect = (
            "indirect" in src_lower
            or "paraphrase" in src_lower
            or "paraphrasée" in src_lower
        )
        assert has_indirect, (
            "Beam descent prompt missing awareness of indirect fallacy forms"
        )

    def test_beam_prompt_mentions_emotion_not_just_illustration(self, plugin_source):
        """Beam descent prompt MUST distinguish emotional fallacy from illustration."""
        src_lower = plugin_source.lower()
        has_emotion_distinction = (
            "emotion" in src_lower
            and ("drives" in src_lower or "primary" in src_lower
                 or "illustrat" in src_lower or "merely" in src_lower)
        )
        assert has_emotion_distinction, (
            "Beam descent prompt missing emotion operator vs illustration distinction"
        )


class TestAntiPenduleGuard:
    """Verify directives do NOT over-trigger (anti-pendule check)."""

    @pytest.fixture
    def plugin_source(self):
        try:
            from argumentation_analysis.plugins import fallacy_workflow_plugin
        except ImportError:
            pytest.skip("fallacy_workflow_plugin not importable")
        import inspect
        return inspect.getsource(fallacy_workflow_plugin.FallacyWorkflowPlugin)

    def test_no_regex_or_heuristic_fallback_added(self, plugin_source):
        """Verify no regex/heuristic fallback was introduced (anti-pendule HARD)."""
        src_lower = plugin_source.lower()
        forbidden_patterns = [
            "re.match",
            "re.search",
            "regex",
            "startswith.*circular",
            "if 'circular' in",
            "if 'emotion' in",
        ]
        for pattern in forbidden_patterns:
            assert pattern.lower() not in src_lower, (
                f"Anti-pendule violation: found heuristic pattern '{pattern}' "
                "in fallacy_workflow_plugin.py — detection must remain LLM-conducted"
            )

    def test_legitimate_emotion_still_excluded(self, plugin_source):
        """Verify the original 'legitimate uses of emotion are NOT fallacies' guard is preserved."""
        src_lower = plugin_source.lower()
        assert "legitimate" in src_lower and "emotion" in src_lower and "not fallac" in src_lower, (
            "Original guard against false positives on legitimate emotion usage is missing"
        )


class TestNegativeCaseCanary:
    """
    Canary: verify prompt directives describe the NEGATIVE case explicitly.

    This is the '≥1 cas négatif testé' from the DoD — at prompt level, we verify
    the prompt text explicitly mentions what is NOT a fallacy, preventing
    over-classification.
    """

    @pytest.fixture
    def plugin_source(self):
        try:
            from argumentation_analysis.plugins import fallacy_workflow_plugin
        except ImportError:
            pytest.skip("fallacy_workflow_plugin not importable")
        import inspect
        return inspect.getsource(fallacy_workflow_plugin.FallacyWorkflowPlugin)

    def test_circular_directive_has_negative_boundary(self, plugin_source):
        """Circular reasoning directive MUST describe when it is NOT circular."""
        # The D6 directive should not just say "confirm circular" — it must
        # also provide boundary: e.g. "only confirm if..." with exclusion criteria
        src_lower = plugin_source.lower()
        # Check for boundary language near circular/paraphrase mentions
        has_only_if = "only confirm" in src_lower or "confirm only" in src_lower
        has_genuinely = "genuinely fallacious" in src_lower
        assert has_only_if or has_genuinely, (
            "Circular reasoning directive missing negative boundary "
            "(when is paraphrase NOT circular?)"
        )

    def test_emotion_directive_has_negative_boundary(self, plugin_source):
        """Emotion directive MUST describe when emotional language is NOT a fallacy."""
        src_lower = plugin_source.lower()
        # Must distinguish between (a) primary operator and (b) illustration
        has_illustrative = (
            "illustrat" in src_lower or "merely" in src_lower or "accessoire" in src_lower
        )
        has_only_a = "only" in src_lower and ("primary" in src_lower or "operator" in src_lower)
        assert has_illustrative or has_only_a, (
            "Emotion directive missing negative boundary "
            "(when is emotional language NOT a fallacy?)"
        )
