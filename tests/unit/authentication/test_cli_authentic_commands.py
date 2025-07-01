#!/usr/bin/env python3
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
# from config.unified_config import UnifiedConfig # Imported lower if needed

"""
Tests CLI pour les commandes d'authenticité
==========================================

Suite de tests pour valider les scripts CLI d'authenticité :
- Script de validation d'authenticité
- Script d'analyse authentique
- Options de ligne de commande
- Intégration des configurations
"""

import pytest
import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path
import asyncio
from unittest.mock import AsyncMock, patch # Added for helper

from typing import Dict, Any, List
from enum import Enum
from pydantic import ValidationError

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Nouveau système d'import pour l'analyseur unifié
try:
    from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
        UnifiedProductionAnalyzer,
        UnifiedProductionConfig,
        MockLevel,
        LogicType,
        AnalysisMode,
        OrchestrationType
    )
except ImportError as e:
    pytest.skip(f"Modules de l'analyseur unifié non trouvés: {e}", allow_module_level=True)


@pytest.mark.skip(reason="CLI script is deprecated, tests are now part of TestCLIIntegrationAuthenticity.")
class TestValidateAuthenticSystemCLI:
    """Cette classe est obsolète. Les tests de validation sont intégrés dans le workflow
    de la classe TestCLIIntegrationAuthenticity.
    """
    pass


@pytest.mark.asyncio
class TestAnalyzeTextAuthenticCLI:
    """Tests refactorisés pour le UnifiedProductionAnalyzer."""

    def setup_method(self):
        """Configuration pour chaque test utilisant l'analyseur unifié."""
        self.config = UnifiedProductionConfig(
            mock_level=MockLevel.FULL,  # Utilise des mocks pour l'analyse
            check_dependencies=False,    # Ne pas vérifier les dépendances (Java, etc.)
            llm_service="mock"
        )
        self.analyzer = UnifiedProductionAnalyzer(self.config)
        self.test_text = "Tous les politiciens mentent, donc Pierre ment."

    @pytest.mark.skip(reason="Remplacé par la nouvelle approche via analyseur")
    def test_analyze_script_exists_and_executable(self):
        """Test d'existence et d'exécutabilité du script."""
        pass

    @pytest.mark.skip(reason="CLI test non pertinent pour l'analyseur unifié")
    def test_analyze_script_help_output(self):
        """Test de l'affichage de l'aide du script."""
        pass

    async def test_analyzer_basic_execution(self):
        """Test d'exécution basique de l'analyseur unifié."""
        initialized = await self.analyzer.initialize()
        assert initialized, "L'analyseur n'a pas pu s'initialiser"

        result = await self.analyzer.analyze_text(self.test_text)

        assert isinstance(result, dict)
        assert result['id'] == 'analysis_1'
        assert result['text_length'] == len(self.test_text)
        assert 'results' in result
        
        # Vérifie que le mock a fonctionné
        unified_result = result['results']['unified']
        assert unified_result['authentic'] is False
        assert "[MOCK]" in unified_result['analysis']

    @pytest.mark.asyncio
    async def test_analyzer_force_authentic_option(self):
        """Vérifie que l'option de forcer l'authenticité est bien prise en compte par l'analyseur."""
        # Équivalent de --force-authentic : utiliser un niveau de mock à NONE
        config = UnifiedProductionConfig(
            mock_level=MockLevel.NONE,
            check_dependencies=False,
            llm_service="mock" # On garde un mock pour le LLM pour ne pas dépendre du réseau
        )
        analyzer = UnifiedProductionAnalyzer(config)

        # Vérifier que la configuration interne de l'analyseur est correcte
        assert analyzer.config.mock_level == MockLevel.NONE
        
        # Valider la cohérence de la config (ex: mock_level=NONE implique require_real_gpt=True)
        is_valid, errors = analyzer.config.validate()
        assert is_valid, f"La configuration devrait être valide mais a des erreurs: {errors}"

        # Exécuter l'analyse
        initialized = await analyzer.initialize()
        assert initialized, "L'analyseur n'a pas pu s'initialiser en mode authentique"

        result = await analyzer.analyze_text(self.test_text)

        # Vérifier que le résultat reflète bien une configuration authentique
        assert isinstance(result, dict)
        assert "config_snapshot" in result
        assert result["config_snapshot"]["mock_level"] == MockLevel.NONE.value
        
        # Comme le llm_service est "mock", l'analyse elle-même ne sera PAS authentique.
        # C'est le comportement attendu dans ce test unitaire qui ne doit pas faire d'appel réseau.
        assert "results" in result
        assert result["results"]["unified"]["authentic"] is False

    @pytest.mark.asyncio
    async def test_analyzer_configuration_options(self):
        """Vérifie que les options de configuration (ex: logic_type) sont bien appliquées."""
        # Test avec un type de logique différent (PL)
        config = UnifiedProductionConfig(
            mock_level=MockLevel.FULL,
            check_dependencies=False,
            llm_service="mock",
            logic_type=LogicType.PL
        )
        analyzer = UnifiedProductionAnalyzer(config)

        initialized = await analyzer.initialize()
        assert initialized, "L'analyseur n'a pas pu s'initialiser avec LogicType.PL"

        result = await analyzer.analyze_text(self.test_text)

        # Vérifier que le snapshot de configuration dans le résultat est correct
        assert isinstance(result, dict)
        assert result["config_snapshot"]["logic_type"] == LogicType.PL.value
        assert result["config_snapshot"]["mock_level"] == MockLevel.FULL.value

    @pytest.mark.asyncio
    async def test_analyzer_file_input_option(self, tmp_path):
        """Vérifie que l'analyseur peut traiter une entrée depuis un fichier."""
        # Créer un fichier de test temporaire
        test_file = tmp_path / "test_input.txt"
        test_file.write_text(self.test_text, encoding="utf-8")

        config = UnifiedProductionConfig(
            mock_level=MockLevel.FULL,
            check_dependencies=False,
            llm_service="mock"
        )
        analyzer = UnifiedProductionAnalyzer(config)

        initialized = await analyzer.initialize()
        assert initialized, "L'analyseur n'a pas pu s'initialiser"

        # Lire le contenu du fichier et l'analyser
        file_content = test_file.read_text(encoding="utf-8")
        result = await analyzer.analyze_text(file_content)

        assert isinstance(result, dict)
        assert result["results"]["unified"]["authentic"] is False
        assert result["text_length"] == len(self.test_text)
        # La méthode analyze_text ne renseigne pas sur le fichier d'origine dans le snapshot.
        # Nous vérifions donc juste que le texte source est correct.
        assert "input_file" not in result["config_snapshot"]


@pytest.mark.asyncio
class TestCLIIntegrationAuthenticity:
    """Tests d'intégration refactorisés pour le UnifiedProductionAnalyzer."""

    def setup_method(self):
        """Configuration pour chaque test utilisant l'analyseur unifié."""
        self.test_text = "Ceci est un test d'intégration."

    async def test_validation_before_analysis_workflow(self):
        """
        Vérifie que l'initialisation de l'analyseur (qui inclut la validation)
        se comporte comme prévu avant de procéder à une analyse.
        """
        # Scénario 1: La validation réussit (en utilisant des mocks)
        config_success = UnifiedProductionConfig(
            mock_level=MockLevel.FULL,
            check_dependencies=True,  # Active la validation
            llm_service="mock"
        )
        analyzer_success = UnifiedProductionAnalyzer(config_success)

        initialized_success = await analyzer_success.initialize()
        assert initialized_success, "L'analyseur aurait dû s'initialiser correctement avec des mocks."

        # Si l'initialisation réussit, l'analyse doit être possible
        result = await analyzer_success.analyze_text(self.test_text)
        assert isinstance(result, dict)
        assert result['results']['unified']['authentic'] is False # Mock result

        # Scénario 2: La validation échoue
        # Pour simuler un échec, nous utilisons un mock_level=NONE
        # sans avoir les dépendances réelles, ce qui fera échouer .initialize()
        config_fail = UnifiedProductionConfig(
            mock_level=MockLevel.NONE,
            check_dependencies=True,
            llm_service="mock"
        )
        analyzer_fail = UnifiedProductionAnalyzer(config_fail)

        # On mock la validation pour qu'elle échoue
        with patch.object(analyzer_fail.dependency_validator, 'validate_all', return_value=(False, ["mocked error"])):
            initialized_fail = await analyzer_fail.initialize()
            assert not initialized_fail, "L'analyseur ne devrait PAS s'initialiser sans les dépendances réelles."
    
    @pytest.mark.skip(reason="CLI test deprecated, replaced by modern workflow test.")
    def test_consistent_configuration_between_scripts(self):
        """Test de cohérence de configuration entre scripts."""
        pass

    async def test_consistent_configuration_workflow(self):
        """
        Vérifie que les configurations prédéfinies (presets) peuvent être
        utilisées pour initialiser et exécuter une analyse de manière cohérente.
        """
        # presets_to_test = ["testing", "development"] # Add more presets if needed
        # For now, let's create configs that MIMIC the old presets.
        
        config_testing = UnifiedProductionConfig(
            mock_level=MockLevel.FULL,
            check_dependencies=False,
            llm_service="mock"
        )
        
        config_development = UnifiedProductionConfig(
            mock_level=MockLevel.PARTIAL,
            check_dependencies=False,
            llm_service="mock",
            logic_type=LogicType.PL
        )

        configs_to_test = {
            "testing": config_testing,
            "development": config_development
        }

        for name, config in configs_to_test.items():
            analyzer = UnifiedProductionAnalyzer(config)
            
            initialized = await analyzer.initialize()
            assert initialized, f"L'analyseur n'a pas pu s'initialiser avec la config '{name}'"

            result = await analyzer.analyze_text(self.test_text)
            
            assert isinstance(result, dict), f"Le résultat pour '{name}' n'est pas un dictionnaire."
            assert "config_snapshot" in result
            assert result["config_snapshot"]["mock_level"] == config.mock_level.value, \
                f"Mock level mismatch for config '{name}'"
            assert result["config_snapshot"]["logic_type"] == config.logic_type.value, \
                f"Logic type mismatch for config '{name}'"
    
    @pytest.mark.skip(reason="CLI test deprecated, replaced by modern workflow test.")
    def test_error_handling_consistency(self):
        """Test de cohérence de gestion d'erreurs."""
        pass

    async def test_error_handling_for_invalid_config(self):
        """
        Vérifie que UnifiedProductionConfig et UnifiedProductionAnalyzer
        gèrent correctement les configurations invalides en levant des erreurs.
        """
        # Scénario 1: Valeur invalide pour un Enum
        with pytest.raises(ValidationError):
            UnifiedProductionConfig(logic_type="invalid_logic_type") # type: ignore

        with pytest.raises(ValidationError):
            UnifiedProductionConfig(mock_level="bad_mock_level") # type: ignore

        # Scénario 2: Analyse sans initialisation correcte
        config = UnifiedProductionConfig(mock_level=MockLevel.FULL)
        analyzer_not_initialized = UnifiedProductionAnalyzer(config)
        
        # S'assurer que l'analyse échoue si non initialisé
        with pytest.raises(Exception): # Replace with a more specific exception if available
             await analyzer_not_initialized.analyze_text("some text")

        # Scénario 3: L'initialisation échoue avec une mauvaise configuration
        # (ex: mock_level=NONE sans les dépendances)
        config_fail = UnifiedProductionConfig(
            mock_level=MockLevel.NONE,
            check_dependencies=True # Force la vérification
        )
        analyzer_fail_init = UnifiedProductionAnalyzer(config_fail)
        
        with patch.object(analyzer_fail_init.dependency_validator, 'validate_all', return_value=(False, ["mocked error"])):
            initialized = await analyzer_fail_init.initialize()
            assert not initialized, "L'initialisation aurait dû échouer."


@pytest.mark.skip(reason="CLI test deprecated. Config validation is now part of the analyzer's workflow tests.")
class TestCLIConfigurationValidation:
    """Cette classe est obsolète. La validation des configurations est testée
    via les workflows de TestCLIIntegrationAuthenticity.
    """
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
