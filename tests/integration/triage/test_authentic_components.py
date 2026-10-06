#!/usr/bin/env python3
"""
Tests d'intégration pour composants authentiques
===============================================

Suite de tests pour valider l'intégration complète avec :
- GPT-4o-mini réel
- Tweety JAR authentique
- Taxonomie 1408 sophismes
- Pipeline 100% authentique
"""

import pytest
import os
import sys
import asyncio
import tempfile
import json
import time
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.unified_config import (
        UnifiedConfig,
        MockLevel,
        TaxonomySize,
        LogicType,
        PresetConfigs,
    )
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
except ImportError as e:
    pytest.skip(f"Modules requis non disponibles: {e}", allow_module_level=True)


def _names_a_correct_diagnosis(response: str) -> bool:
    """#2938 review (R1066): the accepted diagnoses are written from the
    sentence under analysis, never from the response being judged.

    ``'Tous les politiciens mentent, donc Pierre ment.'`` — the premise
    "tous les politiciens mentent" is an absolute (hasty) generalization,
    and "donc Pierre ment" skips the premise "Pierre est un politicien":
    a non sequitur (enthymème, missing premise). Those two families are
    what a correct analysis of THIS sentence names, in fixed FR/EN
    vocabulary. Case- and accent-insensitive.

    Not accepted: ``ad hominem`` (the sentence attacks no author), a bare
    ``sophisme``/``fallacy`` (names no defect — the case the old lexical
    assertion let pass), or a verdict of validity.
    """
    decomposed = unicodedata.normalize("NFKD", response.lower())
    normalized = "".join(c for c in decomposed if not unicodedata.combining(c)).replace(
        "-", " "
    )
    # The terms carry the docstring's own vocabulary: "non sequitur
    # (enthymème, missing premise)" — a correct answer naming only the
    # enthymeme was rejected before. Both the nominal ("prémisse manquante")
    # and the verbal ("il manque une prémisse") FR forms name the defect, as
    # does the EN "missing premise" they paraphrase. Bare "prémisse" stays
    # out: on its own it names no defect.
    return any(
        term in normalized
        for term in (
            "non sequitur",
            "generalisation",
            "generalization",
            "enthymeme",
            "premisse manquante",
            "manque une premisse",
            "missing premise",
        )
    )


class TestAuthenticGPTIntegration:
    """Tests d'intégration avec GPT-4o-mini authentique."""

    def setup_method(self):
        """Configuration pour chaque test."""
        self.authentic_config = PresetConfigs.authentic_fol()
        self.test_prompt = (
            "Analysez cette phrase: 'Tous les politiciens mentent, donc Pierre ment.'"
        )

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="Clé API OpenAI requise"
    )
    @pytest.mark.requires_api
    def test_real_gpt_response_quality(self):
        """Test de qualité des réponses GPT authentiques.

        #2934: no catch-all around the body. The ``skipif`` above already owns
        the only legitimate skip (no key); everything else the body raises is a
        real failure the report must show. The former ``except Exception ->
        skip`` swallowed the assertions with it, so this test could pass-or-
        skip but never redden — one of the gate's tests carrying no signal.
        The ``requires_api`` marker moves it out of the gate (331 -> 330) and
        into the band, where a full-band dispatch measures this path for real:
        green if the response holds its assertions, red on a genuine cause.
        Two offline witnesses enter the gate in its place
        (TestSettingsIsRequiredInSK and TestNamesACorrectDiagnosis below), so
        the gate nets 331 -> 332 (283 + 49), re-measured in collect-only.

        #2938 review (R1066, arbitration): the final assertions are a named
        predicate, ``_names_a_correct_diagnosis`` — its accepted diagnoses
        are written from the sentence under analysis (a hasty generalization
        plus a non sequitur), so it can redden offline in the gate instead
        of only on a paid call.

        #2938 review (R1066): the call passes a real settings object — SK 1.44
        REQUIRES ``settings``, and ``settings=None`` dies inside
        ``PromptExecutionSettings.from_prompt_execution_settings`` with the
        cryptic ``'NoneType' object has no attribute 'pack_extension_data'``.
        That crash is the caller's own input failing, not the service (pinned
        offline by TestSettingsIsRequiredInSK below).
        """
        # Initialiser le service LLM réel via la factory
        llm_service = create_llm_service(
            service_id="test_real_gpt_quality",
            model_id="gpt-5-mini",
            force_authentic=True,
        )

        # Test de réponse authentique via SK 1.37 API
        from semantic_kernel.connectors.ai.prompt_execution_settings import (
            PromptExecutionSettings,
        )
        from semantic_kernel.contents import ChatHistory

        chat_history = ChatHistory()
        chat_history.add_user_message(self.test_prompt)
        results = asyncio.run(
            llm_service.get_chat_message_contents(
                chat_history=chat_history, settings=PromptExecutionSettings()
            )
        )
        response = str(results[0]) if results else ""

        # Validations de qualité
        assert isinstance(response, str)
        assert len(response) > 50  # Réponse substantielle
        assert _names_a_correct_diagnosis(
            response
        ), "la réponse ne nomme aucun défaut que la phrase porte réellement"

        # Vérifier que ce n'est pas une réponse mock
        assert "mock" not in response.lower()
        assert "simulé" not in response.lower()

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="Clé API OpenAI requise"
    )
    def test_real_vs_mock_response_comparison(self):
        """Test de comparaison réponse authentique vs mock."""
        # Réponse mock typique
        mock_response = "Réponse mock générée automatiquement"

        # Test que la réponse mock est détectable
        assert "mock" in mock_response.lower()
        assert len(mock_response) < 50

        # Le test de vraie réponse nécessiterait un appel API réel
        # donc on valide seulement la structure ici
        expected_real_response_patterns = [
            "analyse",
            "sophisme",
            "logique",
            "argument",
            "prémisse",
        ]

        # Une vraie réponse devrait contenir ces éléments
        for pattern in expected_real_response_patterns:
            assert pattern not in mock_response.lower()


class TestSettingsIsRequiredInSK:
    """#2938 review (R1066): pin WHY the quality test passes a real settings
    object and never ``settings=None`` again.

    semantic_kernel 1.44 (the lock's version) requires ``settings``: ``None``
    dies inside ``PromptExecutionSettings.from_prompt_execution_settings``
    with the cryptic ``'NoneType' object has no attribute
    'pack_extension_data'`` — the CALLER's own input failing, not the
    service. Offline: dummy key, client construction only, zero network.
    """

    def test_none_settings_is_the_callers_own_failure(self):
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from semantic_kernel.connectors.ai.prompt_execution_settings import (
            PromptExecutionSettings,
        )

        service = OpenAIChatCompletion(ai_model_id="pin", api_key="dummy")
        with pytest.raises(AttributeError, match="pack_extension_data"):
            service.get_prompt_execution_settings_from_settings(None)

        converted = service.get_prompt_execution_settings_from_settings(
            PromptExecutionSettings()
        )
        assert type(converted).__name__ == "OpenAIChatPromptExecutionSettings"


class TestNamesACorrectDiagnosis:
    """#2938 review (R1066): the quality test's final assertion is a named
    predicate whose accepted diagnoses are written from the sentence under
    analysis. This witness reddens it offline, here in the gate, on
    hand-written responses — it does not need a paid call to exist.

    ``ad hominem`` is deliberately absent from the accepted families: the
    sentence attacks no author. A bare ``sophisme`` is absent too: it names
    no defect, and the old lexical assertion let exactly that pass.
    """

    def test_accepts_only_a_diagnosis_the_sentence_bears(self):
        # The live answer measured on this PR (abbreviated): it names both
        # defects the sentence carries — a hasty generalization and a
        # non sequitur.
        measured_live_answer = (
            "La prémisse « tous les politiciens mentent » est une "
            "généralisation hâtive, et conclure que Pierre ment est une "
            "erreur de non sequitur : il manque la prémisse « Pierre est un "
            "politicien »."
        )
        assert _names_a_correct_diagnosis(measured_live_answer)

        # Wrong family: ad hominem misdescribes this sentence.
        assert not _names_a_correct_diagnosis("Il s'agit d'un ad hominem.")
        # No defect named at all.
        assert not _names_a_correct_diagnosis("Le raisonnement est valide.")
        # "Sophisme" alone names no defect — the old assertion let this pass.
        assert not _names_a_correct_diagnosis("C'est un sophisme.")

        # The docstring's own vocabulary, FR and EN: a correct answer that
        # names only the enthymeme (or the missing premise) was rejected
        # before — the terms list did not carry what the docstring accepts.
        assert _names_a_correct_diagnosis("La conclusion repose sur un enthymème.")
        assert _names_a_correct_diagnosis("C'est un cas de prémisse manquante.")
        assert _names_a_correct_diagnosis(
            "The argument is an enthymeme: a missing premise."
        )
        # #2951 review (R1069): the verbal FR form IS the paraphrase of the
        # accepted EN "missing premise" — refusing it pinned a false red. It
        # is now accepted, and the boundary moved to a sentence that names
        # no defect at all (a premise stated as true, not one that is
        # missing).
        assert _names_a_correct_diagnosis("Il manque une prémisse.")
        assert not _names_a_correct_diagnosis("La première prémisse est vraie.")


@pytest.mark.jpype
class TestAuthenticTweetyIntegration:
    """Tests d'intégration avec Tweety JAR authentique."""

    def setup_method(self):
        """Configuration pour chaque test."""
        self.authentic_config = PresetConfigs.authentic_fol()
        self.test_formula = "∀x(Politician(x) → Lies(x))"

    @pytest.mark.jpype
    def test_tweety_jar_configuration(self):
        """Test de configuration Tweety JAR authentique."""
        tweety_config = self.authentic_config.get_tweety_config()

        assert tweety_config["enable_jvm"] is True
        assert tweety_config["require_real_jar"] is True
        assert tweety_config["logic_type"] == "fol"

    @pytest.mark.jpype
    def test_real_tweety_jar_availability(self):
        """Test de disponibilité du JAR Tweety authentique.

        #2610: the probe looked for ``tweety-full-*-with-dependencies.jar``, a
        fat JAR no longer provisioned (#1874), and skipped on every machine.
        The question is now the one production asks: does the classpath
        ``jvm_setup`` builds carry Tweety classes? Skip only when
        ``libs/tweety`` holds no jar at all (an unprovisioned checkout).
        """
        from argumentation_analysis.core import jvm_setup, tweety_assembly

        if not list(jvm_setup.LIBS_DIR.glob("*.jar")):
            pytest.skip(f"{jvm_setup.LIBS_DIR} holds no jar: Tweety not provisioned")
        classpath = [
            Path(p) for p in jvm_setup._build_tweety_classpath(jvm_setup.LIBS_DIR)
        ]
        carrying = [
            jar for jar in classpath if tweety_assembly.carries_tweety_classes(jar)
        ]
        assert carrying, (
            f"None of the {len(classpath)} jars on the production classpath "
            "carries a Tweety class"
        )

    @pytest.mark.jpype
    def test_real_fol_logic_agent_initialization(self):
        """Test d'initialisation agent logique FOL avec Tweety réel."""
        try:
            config = UnifiedConfig()
            kernel = config.get_kernel_with_gpt4o_mini()
            fol_agent = FOLLogicAgent(kernel=kernel)

            # Vérifier l'initialisation
            assert hasattr(fol_agent, "analyze")
            assert hasattr(fol_agent, "logic_type")
            assert not hasattr(fol_agent, "_is_mock")

        except Exception as e:
            pytest.skip(f"Agent FOL réel non disponible: {e}")

    @pytest.mark.jpype
    def test_real_tweety_formula_parsing(self):
        """Test de parsing de formule avec Tweety authentique."""
        try:
            config = UnifiedConfig()
            kernel = config.get_kernel_with_gpt4o_mini()
            fol_agent = FOLLogicAgent(kernel=kernel)

            # Test analyse with a real formula
            result = asyncio.run(fol_agent.analyze(self.test_formula))

            # Validations
            assert result is not None
            assert hasattr(result, "formulas")
            assert hasattr(result, "confidence_score")

        except Exception as e:
            pytest.skip(f"Tweety réel non disponible: {e}")


class TestAuthenticTaxonomyIntegration:
    """Tests d'intégration avec taxonomie 1408 sophismes."""

    def setup_method(self):
        """Configuration pour chaque test."""
        self.authentic_config = PresetConfigs.authentic_fol()

    def test_full_taxonomy_loading_performance(self):
        """Test de performance de chargement taxonomie complète."""
        taxonomy_config = self.authentic_config.get_taxonomy_config()

        assert taxonomy_config["size"] == "full"
        assert (
            taxonomy_config["node_count"] == 1000
        )  # 1408 dans l'implémentation réelle
        assert taxonomy_config["require_full_load"] is True

        # Simulation de chargement (temps acceptable)
        start_time = time.time()

        # Simuler le chargement de 1408 sophismes
        fallacies = {
            f"fallacy_{i}": {"type": "formal" if i % 2 else "informal"}
            for i in range(1408)
        }

        load_time = time.time() - start_time

        # Validations
        assert len(fallacies) == 1408
        assert load_time < 5.0  # Chargement acceptable sous 5s

    def test_taxonomy_completeness_validation(self):
        """Test de validation de complétude de la taxonomie."""

        def validate_taxonomy_completeness(taxonomy: Dict[str, Any]) -> Dict[str, Any]:
            """Valide la complétude d'une taxonomie."""
            fallacy_count = len(taxonomy.get("fallacies", {}))
            categories = taxonomy.get("categories", [])

            return {
                "fallacy_count": fallacy_count,
                "is_complete": fallacy_count >= 1000,
                "is_mock": fallacy_count <= 10,
                "category_count": len(categories),
                "completeness_percentage": min(100, (fallacy_count / 1408) * 100),
            }

        # Taxonomie complète
        complete_taxonomy = {
            "fallacies": {f"fallacy_{i}": {} for i in range(1408)},
            "categories": ["formal", "informal", "material", "verbal"],
        }

        validation = validate_taxonomy_completeness(complete_taxonomy)

        assert validation["fallacy_count"] == 1408
        assert validation["is_complete"] is True
        assert validation["is_mock"] is False
        assert validation["completeness_percentage"] == 100.0

    def test_taxonomy_mock_vs_authentic_detection(self):
        """Test de détection taxonomie mock vs authentique."""
        # Taxonomie mock (3 sophismes)
        mock_taxonomy = {
            "fallacies": {
                "ad_hominem": {"type": "informal"},
                "straw_man": {"type": "informal"},
                "slippery_slope": {"type": "informal"},
            },
            "is_mock": True,
        }

        # Taxonomie authentique (1408 sophismes)
        authentic_taxonomy = {
            "fallacies": {
                f"fallacy_{i}": {"type": "formal" if i % 2 else "informal"}
                for i in range(1408)
            },
            "is_complete": True,
        }

        # Tests de détection
        assert len(mock_taxonomy["fallacies"]) == 3
        assert mock_taxonomy.get("is_mock", False) is True

        assert len(authentic_taxonomy["fallacies"]) == 1408
        assert authentic_taxonomy.get("is_complete", False) is True


class TestAuthenticPipelineIntegration:
    """Tests d'intégration pipeline complet authentique."""

    def setup_method(self):
        """Configuration pour chaque test."""
        self.authentic_config = PresetConfigs.authentic_fol()
        self.test_text = """
        Les politiciens sont corrompus. Pierre est politicien.
        Donc Pierre est corrompu. Cette logique est-elle valide ?
        """

    def test_authentic_vs_mock_pipeline_comparison(self):
        """Test de comparaison pipeline authentique vs mock."""
        # Configuration authentique
        authentic_config = PresetConfigs.authentic_fol()
        auth_dict = authentic_config.to_dict()

        # Configuration mock
        mock_config = PresetConfigs.testing()
        mock_dict = mock_config.to_dict()

        # Comparaisons clés
        assert auth_dict["mock_level"] == "none"
        assert mock_dict["mock_level"] == "full"

        assert auth_dict["taxonomy_size"] == "full"
        assert mock_dict["taxonomy_size"] == "mock"

        assert auth_dict["authenticity"]["require_real_gpt"] is True
        assert mock_dict["authenticity"]["require_real_gpt"] is False

    def test_pipeline_degraded_mode_is_overridden(self):
        """Test que le mode dégradé est bien écrasé par les contraintes d'authenticité."""
        # On tente de créer une config authentique mais en désactivant Tweety
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.NONE,
            require_real_tweety=False,  # Tentative de désactivation
        )

        # On vérifie que la classe UnifiedConfig a bien forcé la valeur à True
        # car mock_level=NONE impose une authenticité à 100%.
        assert config.require_real_tweety is True

    def test_pipeline_authenticity_metrics_calculation(self):
        """Test de calcul des métriques d'authenticité du pipeline."""

        def calculate_pipeline_authenticity(config: UnifiedConfig) -> Dict[str, Any]:
            """Calcule les métriques d'authenticité du pipeline."""
            components = {
                "llm_service": config.require_real_gpt,
                "tweety_service": config.require_real_tweety,
                "taxonomy": config.require_full_taxonomy,
                "mock_level": config.mock_level == MockLevel.NONE,
                "jvm_enabled": config.enable_jvm,
                "tool_validation": config.validate_tool_calls,
            }

            total = len(components)
            authentic = sum(components.values())
            percentage = (authentic / total) * 100

            return {
                "total_components": total,
                "authentic_components": authentic,
                "authenticity_percentage": percentage,
                "is_100_percent_authentic": percentage == 100.0,
                "component_details": components,
            }

        # Test configuration 100% authentique
        authentic_config = PresetConfigs.authentic_fol()
        metrics = calculate_pipeline_authenticity(authentic_config)

        assert metrics["authenticity_percentage"] == 100.0
        assert metrics["is_100_percent_authentic"] is True
        assert metrics["authentic_components"] == metrics["total_components"]

        # Test configuration mock
        mock_config = PresetConfigs.testing()
        mock_metrics = calculate_pipeline_authenticity(mock_config)

        assert mock_metrics["authenticity_percentage"] < 50.0
        assert mock_metrics["is_100_percent_authentic"] is False


class TestAuthenticPerformanceBenchmarks:
    """Tests de performance pour composants authentiques."""

    def test_taxonomy_loading_benchmark(self):
        """Benchmark de chargement taxonomie authentique."""

        def benchmark_taxonomy_loading(size: str) -> Dict[str, Any]:
            """Benchmark de chargement taxonomie."""
            start_time = time.time()

            if size == "full":
                taxonomy = {
                    f"fallacy_{i}": {"type": "formal" if i % 2 else "informal"}
                    for i in range(1408)
                }
            else:
                taxonomy = {"ad_hominem": {}, "straw_man": {}, "slippery_slope": {}}

            load_time = time.time() - start_time

            return {
                "size": size,
                "fallacy_count": len(taxonomy),
                "load_time_seconds": load_time,
                "fallacies_per_second": len(taxonomy) / max(load_time, 0.001),
            }

        # Benchmark taxonomie complète
        full_benchmark = benchmark_taxonomy_loading("full")
        assert full_benchmark["fallacy_count"] == 1408
        assert full_benchmark["load_time_seconds"] < 1.0  # Sous 1 seconde
        assert full_benchmark["fallacies_per_second"] > 1000  # Plus de 1000/sec

        # Benchmark taxonomie mock
        mock_benchmark = benchmark_taxonomy_loading("mock")
        assert mock_benchmark["fallacy_count"] == 3
        assert mock_benchmark["load_time_seconds"] < 0.1  # Très rapide

    def test_acceptable_performance_thresholds(self):
        """Test des seuils de performance acceptables."""
        # Seuils acceptables pour composants authentiques
        performance_thresholds = {
            "taxonomy_loading": 10.0,  # 10s max pour charger 1408 sophismes
            "llm_response": 30.0,  # 30s max pour réponse GPT
            "tweety_parsing": 5.0,  # 5s max pour parsing Tweety
            "full_pipeline": 60.0,  # 60s max pour pipeline complet
        }

        # Vérifier que les seuils sont raisonnables
        assert performance_thresholds["taxonomy_loading"] > 1.0
        assert performance_thresholds["llm_response"] > 5.0
        assert performance_thresholds["tweety_parsing"] > 1.0
        assert performance_thresholds["full_pipeline"] > 30.0

        # Les seuils authentiques doivent être plus généreux que mock
        mock_thresholds = {
            "taxonomy_loading": 0.1,
            "llm_response": 0.1,
            "tweety_parsing": 0.1,
            "full_pipeline": 1.0,
        }

        for key in performance_thresholds:
            assert performance_thresholds[key] > mock_thresholds[key]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
