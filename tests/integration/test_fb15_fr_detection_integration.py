#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Integration value-gate tests for FB-15 #1032 — FR detection end-to-end (D3/D6/D7).

Unlike the per-marker unit value-gates in
``test_fb15_fr_detection_enrichment.py`` (which test one synthetic exemplar per
dimension via ``detect_contextual_fallacies``), these integration tests exercise
the **full multi-argument detection flow** that the reporting pipeline uses
(``detect_multiple_contextual_fallacies``): a synthetic document is split into
arguments, context is inferred, markers are matched, and contextual severity
filters each detection — the same path a real analysis run takes.

Privacy HARD: all exemplars are synthetic FR rhetorical patterns. No corpus
content, no raw_text, no corpus-specific phrasing.

Anti-pendule: tests use genuine FR registers (elitist ad-populum, critical-theory
circularity, affective drive→relief), NOT corpus_X-specific phrases.
"""

import pytest

from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
    ContextualFallacyDetector,
)

# ---------------------------------------------------------------------------
# Synthetic document fixtures (NOT from corpus)
# ---------------------------------------------------------------------------

# A synthetic political speech containing the 3 FB-15 registers plus a neutral
# control argument. Each register is concentrated in one argument so that
# per-argument attribution can be asserted.
D3_ARGUMENT = (
    "Seules les personnes éclairées et compétentes saisissent l'urgence "
    "de cette réforme. Ceux qui s'y opposent ne sont pas initiés à la "
    "réalité de la situation."
)

D6_ARGUMENT = (
    "Ceux qui refusent de voir l'évidence sont aveuglés et sous l'emprise "
    "d'une doctrine qui les empêche de penser librement."
)

D7_ARGUMENT = (
    "La crise nous menace, l'angoisse grandit chaque jour, mais il existe "
    "un salut : notre solution apportera le soulagement et la réassurance "
    "dont le pays a besoin."
)

# Neutral control — no enriched markers, should produce no detection.
NEUTRAL_ARGUMENT = (
    "La réunion du conseil se tiendra jeudi à quatorze heures dans la "
    "salle principale du bâtiment administratif."
)

# Mixed argument combining D6 + D7 registers in a single statement.
MIXED_D6_D7_ARGUMENT = (
    "Ceux qui, sous l'emprise de l'aveuglement idéologique, refusent notre "
    "salut précipitent la crise ; notre solution est l'unique soulagement."
)

POLITICAL_CONTEXT = "Discours politique lors d'une campagne électorale"


# ---------------------------------------------------------------------------
# End-to-end multi-argument flow
# ---------------------------------------------------------------------------


class TestFB15MultiArgumentDetection:
    """End-to-end detection across a synthetic multi-argument document."""

    def setup_method(self):
        self.detector = ContextualFallacyDetector()
        self.document = [D3_ARGUMENT, D6_ARGUMENT, D7_ARGUMENT, NEUTRAL_ARGUMENT]

    def test_all_three_registers_detected_in_document(self):
        """D3, D6, D7 are all surfaced across the synthetic document."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )

        # Flatten all detected fallacy types across all arguments.
        all_types = set()
        for arg_res in result["argument_results"]:
            for f in arg_res.get("detected_fallacies", []):
                all_types.add(f["fallacy_type"])

        # The 3 enriched registers must be represented.
        assert (
            "appel_inapproprié_popularité" in all_types
        ), f"D3 (popularité) missing from document detection: {all_types}"
        assert (
            "disqualification_circulaire" in all_types
        ), f"D6 (disqualification_circulaire) missing from document detection: {all_types}"
        assert (
            "appel_inapproprié_émotion" in all_types
        ), f"D7 (émotion) missing from document detection: {all_types}"

    def test_at_least_three_distinct_fallacy_types(self):
        """Document-level detection surfaces ≥3 distinct fallacy types."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )

        all_types = set()
        for arg_res in result["argument_results"]:
            for f in arg_res.get("detected_fallacies", []):
                all_types.add(f["fallacy_type"])

        assert (
            len(all_types) >= 3
        ), f"Expected ≥3 distinct fallacy types end-to-end, got {len(all_types)}: {all_types}"

    def test_neutral_control_argument_undetected(self):
        """The neutral control argument (index 3) produces no detection."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )

        arg_results = result["argument_results"]
        assert len(arg_results) == 4, "Expected one result per argument"

        control = arg_results[3]
        assert control["argument"] == NEUTRAL_ARGUMENT
        detected = control.get("detected_fallacies", [])
        assert (
            detected == []
        ), f"Neutral control argument should produce no detection, got: {detected}"

    def test_per_argument_attribution(self):
        """Each register is detected in its dedicated argument (not the others)."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )
        arg_results = result["argument_results"]

        def _types(idx):
            return {
                f["fallacy_type"]
                for f in arg_results[idx].get("detected_fallacies", [])
            }

        # D3 concentrated in argument 0
        assert "appel_inapproprié_popularité" in _types(
            0
        ), f"D3 should be in argument 0, got {_types(0)}"
        # D6 concentrated in argument 1
        assert "disqualification_circulaire" in _types(
            1
        ), f"D6 should be in argument 1, got {_types(1)}"
        # D7 concentrated in argument 2
        assert "appel_inapproprié_émotion" in _types(
            2
        ), f"D7 should be in argument 2, got {_types(2)}"

    def test_contextual_factors_inferred_as_political(self):
        """Political context is inferred and propagated to every detection."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )

        for arg_res in result["argument_results"]:
            factors = arg_res.get("contextual_factors", {})
            assert (
                factors.get("domain") == "politique"
            ), f"Expected inferred domain 'politique', got {factors.get('domain')!r}"

    def test_severity_above_threshold_for_all_registers(self):
        """Every detected enriched register clears the >0.5 severity gate."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )

        for arg_res in result["argument_results"]:
            for f in arg_res.get("detected_fallacies", []):
                assert (
                    f["severity"] > 0.5
                ), f"Detection below severity gate: {f['fallacy_type']} = {f['severity']}"

    def test_argument_index_and_count_metadata(self):
        """Integration metadata (argument_index, count) is consistent."""
        result = self.detector.detect_multiple_contextual_fallacies(
            self.document, POLITICAL_CONTEXT
        )

        assert result["argument_count"] == 4
        assert result["context_description"] == POLITICAL_CONTEXT
        indices = [r["argument_index"] for r in result["argument_results"]]
        assert indices == [0, 1, 2, 3], f"Unexpected argument indices: {indices}"


# ---------------------------------------------------------------------------
# Cross-register robustness
# ---------------------------------------------------------------------------


class TestFB15CrossRegisterDetection:
    """A single argument combining registers surfaces multiple types."""

    def setup_method(self):
        self.detector = ContextualFallacyDetector()

    def test_mixed_d6_d7_argument_detects_both(self):
        """An argument combining D6+D7 registers detects both fallacy types."""
        result = self.detector.detect_multiple_contextual_fallacies(
            [MIXED_D6_D7_ARGUMENT], POLITICAL_CONTEXT
        )

        types = {
            f["fallacy_type"]
            for f in result["argument_results"][0].get("detected_fallacies", [])
        }
        assert (
            "disqualification_circulaire" in types
        ), f"D6 missing from mixed argument: {types}"
        assert (
            "appel_inapproprié_émotion" in types
        ), f"D7 missing from mixed argument: {types}"


# ---------------------------------------------------------------------------
# Anti-regression: enriched markers are load-bearing
# ---------------------------------------------------------------------------


class TestFB15EnrichmentLoadBearing:
    """Proves the enrichment (not generic noise) drives the detections."""

    def setup_method(self):
        self.detector = ContextualFallacyDetector()

    def test_neutralized_text_detects_no_enriched_register(self):
        """Replacing enriched markers with neutral wording removes all 3 registers."""
        # Same syntactic shape as D3/D6/D7 but with the enriched markers removed.
        neutralized = [
            # D3 without elitist markers
            "Certains citoyens soutiennent cette réforme pour des raisons variées.",
            # D6 without circularity markers
            "Les opposants avancent des arguments différents sur ce sujet.",
            # D7 without drive→relief markers
            "La situation économique évolue et plusieurs pistes sont étudiées.",
        ]

        result = self.detector.detect_multiple_contextual_fallacies(
            neutralized, POLITICAL_CONTEXT
        )

        all_types = set()
        for arg_res in result["argument_results"]:
            for f in arg_res.get("detected_fallacies", []):
                all_types.add(f["fallacy_type"])

        enriched = {
            "appel_inapproprié_popularité",
            "disqualification_circulaire",
            "appel_inapproprié_émotion",
        }
        leaked = all_types & enriched
        assert not leaked, (
            f"Enriched registers detected on neutralized text — enrichment is not "
            f"load-bearing (false positives): {leaked}"
        )

    def test_empty_document_handled_cleanly(self):
        """An empty argument list produces a well-formed empty result."""
        result = self.detector.detect_multiple_contextual_fallacies(
            [], POLITICAL_CONTEXT
        )
        assert result["argument_count"] == 0
        assert result["argument_results"] == []


# ---------------------------------------------------------------------------
# Context-sensitivity of the enriched registers
# ---------------------------------------------------------------------------


class TestFB15ContextSensitivity:
    """Enriched registers respond to domain the same way the pipeline expects."""

    def setup_method(self):
        self.detector = ContextualFallacyDetector()

    def test_d7_commercial_context_below_threshold(self):
        """D7 drive→relief has commercial severity exactly 0.5 (NOT >0.5) → no detection.

        This pins the severity-gate semantics: 0.5 is rejected, only >0.5 passes.
        Guards against a future loosen-the-gate pendulum.
        """
        result = self.detector.detect_multiple_contextual_fallacies(
            [D7_ARGUMENT], "Campagne marketing commercial"
        )

        factors = result["argument_results"][0]["contextual_factors"]
        assert (
            factors["domain"] == "commercial"
        ), f"Expected inferred domain 'commercial', got {factors.get('domain')!r}"
        types = {
            f["fallacy_type"]
            for f in result["argument_results"][0].get("detected_fallacies", [])
        }
        assert "appel_inapproprié_émotion" not in types, (
            f"D7 should NOT clear the >0.5 gate in commercial context (severity=0.5), "
            f"got: {types}"
        )
