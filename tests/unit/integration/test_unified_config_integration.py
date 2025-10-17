# Authentic gpt-5-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour le système de configuration unifié.

Ce module teste l'intégration complète du système UnifiedConfig avec :
- Pipeline d'analyse de texte
- Interface CLI 
- Validation de bout en bout
- Tests de performance et régression
"""

import pytest
import asyncio
import sys
import tempfile
import json
from pathlib import Path


from unittest.mock import MagicMock

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.unified_config import (
    UnifiedConfig,
    LogicType,
    MockLevel,
    OrchestrationType,
    TaxonomySize,
    AgentType,
    PresetConfigs,
    validate_config,
)


class TestUnifiedConfigIntegration:
    def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""

        async def _run():
            config = UnifiedConfig()
            return await config.get_kernel_with_gpt4o_mini()

        return asyncio.run(_run())

    def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""

        async def _run():
            try:
                kernel = self._create_authentic_gpt4o_mini_instance()
                result = await kernel.invoke("chat", input=prompt)
                return str(result)
            except Exception as e:
                logger.warning(f"Appel LLM authentique échoué: {e}")
                return "Authentic LLM call failed"

        return asyncio.run(_run())

    """Tests d'intégration pour le système de configuration unifié."""

    def test_full_pipeline_with_authentic_fol_config(self):
        """Test du pipeline complet avec configuration authentique FOL."""
        config = PresetConfigs.authentic_fol()

        # Vérification que la configuration est optimale pour la production
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        assert config.taxonomy_size == TaxonomySize.FULL

        # Test des configurations de service dérivées
        tweety_config = config.get_tweety_config()
        assert tweety_config["require_real_jar"] is True
        assert tweety_config["enable_jvm"] is True

        llm_config = config.get_llm_config()
        assert llm_config["require_real_service"] is True
        assert llm_config["mock_level"] == "none"

        taxonomy_config = config.get_taxonomy_config()
        assert taxonomy_config["node_count"] == 1000
        assert taxonomy_config["require_full_load"] is True

    def test_development_workflow_integration(self):
        """Test du workflow de développement avec mocks partiels."""
        config = PresetConfigs.development()

        # Vérification de la configuration de développement
        assert config.logic_type == LogicType.PL
        assert config.mock_level == MockLevel.PARTIAL
        assert config.taxonomy_size == TaxonomySize.MOCK
        assert config.enable_jvm is False

        # Vérifier que les agents n'incluent pas FOL_LOGIC (pas de JVM)
        assert AgentType.FOL_LOGIC not in config.agents
        assert AgentType.INFORMAL in config.agents
        assert AgentType.SYNTHESIS in config.agents
        assert config.require_real_gpt is False

        # Test de cohérence pour le développement
        taxonomy_config = config.get_taxonomy_config()
        assert taxonomy_config["node_count"] == 3  # Taxonomie réduite pour dev

        llm_config = config.get_llm_config()
        assert llm_config["require_real_service"] is False  # Mocks autorisés

    def test_testing_configuration_isolation(self):
        """Test de l'isolation de la configuration de test."""
        config = PresetConfigs.testing()

        # Vérification que la config de test est rapide et isolée
        assert config.logic_type == LogicType.PL  # Plus rapide que FOL
        assert config.mock_level == MockLevel.FULL
        assert config.taxonomy_size == TaxonomySize.MOCK
        assert config.enable_jvm is False  # Pas de JVM pour les tests
        assert config.timeout_seconds == 30  # Timeout court

        # Les agents ne doivent pas inclure de composants lourds
        assert AgentType.FOL_LOGIC not in config.agents
        assert AgentType.INFORMAL in config.agents
        assert AgentType.SYNTHESIS in config.agents

    def test_configuration_compatibility_matrix(self):
        """Test de la matrice de compatibilité des configurations."""
        # Configurations valides testées
        valid_configs = [
            # Production FOL authentique
            {
                "logic_type": LogicType.FOL,
                "mock_level": MockLevel.NONE,
                "taxonomy_size": TaxonomySize.FULL,
                "orchestration_type": OrchestrationType.UNIFIED,
                "expected_valid": True,
            },
            # Développement avec mocks
            {
                "logic_type": LogicType.FOL,
                "mock_level": MockLevel.PARTIAL,
                "taxonomy_size": TaxonomySize.MOCK,
                "orchestration_type": OrchestrationType.CONVERSATION,
                "require_real_gpt": False,
                "require_real_tweety": False,
                "require_full_taxonomy": False,
                "expected_valid": True,
            },
            # Test rapide PL
            {
                "logic_type": LogicType.PL,
                "mock_level": MockLevel.FULL,
                "taxonomy_size": TaxonomySize.MOCK,
                "orchestration_type": OrchestrationType.CONVERSATION,
                "agents": [AgentType.INFORMAL, AgentType.SYNTHESIS],
                "enable_jvm": False,
                "require_real_gpt": False,
                "require_real_tweety": False,
                "require_full_taxonomy": False,
                "expected_valid": True,
            },
        ]

        for config_params in valid_configs:
            expected_valid = config_params.pop("expected_valid")
            try:
                config = UnifiedConfig(**config_params)
                assert expected_valid, f"Configuration should be valid: {config_params}"
            except Exception as e:
                assert (
                    not expected_valid
                ), f"Configuration should be invalid: {config_params}, error: {e}"

    def test_invalid_configuration_combinations(self):
        """Test des combinaisons de configuration invalides."""
        invalid_configs = [
            # Mock level incompatible avec authenticité
            {
                "mock_level": MockLevel.PARTIAL,
                "require_real_gpt": True,
                "expected_error": "Configuration incohérente",
            },
            # FOL_LOGIC sans JVM
            {
                "agents": [AgentType.FOL_LOGIC],
                "enable_jvm": False,
                "expected_error": "FOL_LOGIC agent nécessite enable_jvm=True",
            },
        ]

        for config_params in invalid_configs:
            expected_error = config_params.pop("expected_error")
            with pytest.raises(ValueError, match=expected_error):
                UnifiedConfig(**config_params)

    def test_configuration_serialization_roundtrip(self):
        """Test de sérialisation/désérialisation de configuration."""
        original_config = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS],
            analysis_modes=["fallacies", "coherence", "semantic"],
        )

        # Sérialisation
        config_dict = original_config.to_dict()

        # Vérification de la structure sérialisée
        assert config_dict["logic_type"] == "fol"
        assert config_dict["mock_level"] == "none"
        assert config_dict["taxonomy_size"] == "full"
        assert config_dict["agents"] == ["informal", "fol_logic", "synthesis"]
        assert "authenticity" in config_dict

        # Vérification des métadonnées d'authenticité
        auth_section = config_dict["authenticity"]
        assert auth_section["require_real_gpt"] is True
        assert auth_section["require_real_tweety"] is True
        assert auth_section["require_full_taxonomy"] is True
        assert auth_section["validate_tool_calls"] is True

    def test_performance_configuration_impact(self):
        """Test de l'impact des configurations sur les performances."""
        # Configuration rapide (test)
        fast_config = PresetConfigs.testing()

        # Configuration complète (production)
        full_config = PresetConfigs.authentic_fol()

        # Vérification des optimisations de performance
        assert fast_config.timeout_seconds < full_config.timeout_seconds
        assert fast_config.taxonomy_size == TaxonomySize.MOCK  # Taxonomie réduite
        assert full_config.taxonomy_size == TaxonomySize.FULL  # Taxonomie complète

        # Vérification des ressources utilisées
        assert fast_config.enable_jvm is False  # Pas de JVM pour vitesse
        assert full_config.enable_jvm is True  # JVM nécessaire pour authenticité

        # Vérification du nombre d'agents
        assert len(fast_config.agents) <= len(full_config.agents)

    def test_configuration_migration_compatibility(self):
        """Test de compatibilité avec les anciennes configurations."""
        # Test que les nouvelles configurations sont compatibles
        # avec les interfaces existantes

        config = UnifiedConfig()

        # Vérification que les méthodes d'interface sont disponibles
        assert hasattr(config, "get_tweety_config")
        assert hasattr(config, "get_llm_config")
        assert hasattr(config, "get_taxonomy_config")
        assert hasattr(config, "get_agent_classes")

        # Test des configurations de service
        tweety_config = config.get_tweety_config()
        required_tweety_keys = {
            "enable_jvm",
            "require_real_jar",
            "logic_type",
            "timeout_seconds",
        }
        assert required_tweety_keys.issubset(tweety_config.keys())

        llm_config = config.get_llm_config()
        required_llm_keys = {
            "require_real_service",
            "mock_level",
            "validate_responses",
            "timeout_seconds",
        }
        assert required_llm_keys.issubset(llm_config.keys())

        taxonomy_config = config.get_taxonomy_config()
        required_taxonomy_keys = {"size", "require_full_load", "node_count"}
        assert required_taxonomy_keys.issubset(taxonomy_config.keys())

    def test_configuration_validation_comprehensive(self):
        """Test de validation complète des configurations."""
        from config.unified_config import validate_config

        # Test configuration valide
        valid_config = PresetConfigs.authentic_fol()
        errors = validate_config(valid_config)
        assert len(errors) == 0

        # Test configuration avec problèmes multiples
        problematic_config = UnifiedConfig(
            mock_level=MockLevel.PARTIAL,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False,
            enable_jvm=True,
            agents=[AgentType.INFORMAL],  # Configuration de base pour éviter exceptions
        )

        # Modifier manuellement pour créer des incohérences
        problematic_config.require_real_gpt = True  # Incohérent avec mock_level
        problematic_config.require_real_tweety = False  # Incohérent avec JVM activée
        problematic_config.agents.append(AgentType.FOL_LOGIC)  # Agent nécessitant JVM
        problematic_config.enable_jvm = False  # Mais JVM désactivée

        errors = validate_config(problematic_config)
        assert len(errors) > 0

        # Vérification des types d'erreurs détectées
        error_text = " ".join(errors)
        assert "Mock level != none mais require_real_gpt=True" in error_text
        assert "Agents logiques nécessitent JVM" in error_text

    @pytest.mark.slow
    def test_real_configuration_stress_test(self):
        """Test de stress avec configurations réelles."""
        # Test de création de multiples configurations
        configs = []

        for logic_type in LogicType:
            for mock_level in MockLevel:
                for taxonomy_size in TaxonomySize:
                    try:
                        # Configuration de base compatible
                        config_params = {
                            "logic_type": logic_type,
                            "mock_level": mock_level,
                            "taxonomy_size": taxonomy_size,
                            "agents": [AgentType.INFORMAL, AgentType.SYNTHESIS],
                            "enable_jvm": False,
                        }

                        # Ajustements pour éviter les erreurs de validation
                        if mock_level != MockLevel.NONE:
                            config_params.update(
                                {
                                    "require_real_gpt": False,
                                    "require_real_tweety": False,
                                    "require_full_taxonomy": False,
                                }
                            )

                        # Ajout FOL_LOGIC si JVM disponible et logique compatible
                        if (
                            logic_type in [LogicType.FOL, LogicType.FIRST_ORDER]
                            and mock_level == MockLevel.NONE
                        ):
                            config_params["agents"] = [
                                AgentType.INFORMAL,
                                AgentType.FOL_LOGIC,
                                AgentType.SYNTHESIS,
                            ]
                            config_params["enable_jvm"] = True

                        config = UnifiedConfig(**config_params)
                        configs.append(config)

                    except ValueError:
                        # Certaines combinaisons sont intentionnellement invalides
                        continue

        # Vérification qu'au moins certaines configurations ont été créées
        assert len(configs) > 0

        # Test que toutes les configurations créées sont valides
        for config in configs:
            errors = validate_config(config)
            assert (
                len(errors) == 0
            ), f"Configuration invalide détectée: {config.to_dict()}"


class TestConfigurationDocumentation:
    """Tests pour documenter les configurations et leurs usages."""

    def test_configuration_examples_documentation(self):
        """Test et documentation des exemples de configuration."""
        examples = {
            "production_fol": {
                "description": "Configuration production optimale avec FOL authentique",
                "config": PresetConfigs.authentic_fol(),
                "use_case": "Analyse en production avec maximum de précision",
            },
            "development": {
                "description": "Configuration développement avec mocks partiels",
                "config": PresetConfigs.development(),
                "use_case": "Développement et débogage rapide",
            },
            "testing": {
                "description": "Configuration test rapide et isolée",
                "config": PresetConfigs.testing(),
                "use_case": "Tests automatisés et CI/CD",
            },
            "production_pl": {
                "description": "Configuration production avec logique propositionnelle",
                "config": PresetConfigs.authentic_pl(),
                "use_case": "Analyse rapide en production",
            },
        }

        # Validation de tous les exemples
        for name, example in examples.items():
            config = example["config"]

            # Vérification de validité
            errors = validate_config(config)
            assert len(errors) == 0, f"Exemple {name} invalide: {errors}"

            # Documentation des caractéristiques
            config_dict = config.to_dict()
            print(f"\n{example['description']}:")
            print(f"  Use case: {example['use_case']}")
            print(f"  Logic: {config_dict['logic_type']}")
            print(f"  Mock level: {config_dict['mock_level']}")
            print(f"  Taxonomy: {config_dict['taxonomy_size']}")
            print(f"  Agents: {config_dict['agents']}")
            print(f"  Authentic: {config_dict['authenticity']['require_real_gpt']}")

    def test_configuration_matrix_documentation(self):
        """Test et documentation de la matrice de compatibilité."""
        compatibility_matrix = []

        test_combinations = [
            (LogicType.FOL, MockLevel.NONE, TaxonomySize.FULL, "Production FOL"),
            (LogicType.PL, MockLevel.NONE, TaxonomySize.FULL, "Production PL"),
            (LogicType.FOL, MockLevel.PARTIAL, TaxonomySize.MOCK, "Development"),
            (LogicType.PL, MockLevel.FULL, TaxonomySize.MOCK, "Testing"),
            (
                LogicType.MODAL,
                MockLevel.PARTIAL,
                TaxonomySize.MOCK,
                "Modal Experimental",
            ),
        ]

        for logic, mock, taxonomy, description in test_combinations:
            try:
                config_params = {
                    "logic_type": logic,
                    "mock_level": mock,
                    "taxonomy_size": taxonomy,
                    "agents": [AgentType.INFORMAL, AgentType.SYNTHESIS],
                    "enable_jvm": False,
                }

                # Ajustements pour authenticité
                if mock != MockLevel.NONE:
                    config_params.update(
                        {
                            "require_real_gpt": False,
                            "require_real_tweety": False,
                            "require_full_taxonomy": False,
                        }
                    )

                config = UnifiedConfig(**config_params)
                compatibility_matrix.append(
                    {
                        "description": description,
                        "logic": logic.value,
                        "mock": mock.value,
                        "taxonomy": taxonomy.value,
                        "valid": True,
                        "config": config.to_dict(),
                    }
                )

            except ValueError as e:
                compatibility_matrix.append(
                    {
                        "description": description,
                        "logic": logic.value,
                        "mock": mock.value,
                        "taxonomy": taxonomy.value,
                        "valid": False,
                        "error": str(e),
                    }
                )

        # Documentation de la matrice
        print("\nMatrice de compatibilité des configurations:")
        for entry in compatibility_matrix:
            status = "✅" if entry["valid"] else "❌"
            print(
                f"  {status} {entry['description']}: {entry['logic']}/{entry['mock']}/{entry['taxonomy']}"
            )
            if not entry["valid"]:
                print(f"    Error: {entry['error']}")

        # Vérification qu'au moins certaines combinaisons sont valides
        valid_count = sum(1 for entry in compatibility_matrix if entry["valid"])
        assert valid_count > 0, "Aucune configuration valide trouvée"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
