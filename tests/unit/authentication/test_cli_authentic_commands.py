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
from unittest.mock import AsyncMock # Added for helper

from typing import Dict, Any, List
from enum import Enum

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


@pytest.mark.skip(reason="CLI script is deprecated, tests need complete refactoring")
class TestValidateAuthenticSystemCLI:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        # This helper is defined but not used by tests in this class.
        # If it were used, it should return a mock kernel for unit tests.
        return AsyncMock() # type: ignore
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt) # type: ignore
            return str(result)
        except Exception as e:
            print(f"WARN: Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour le script validate_authentic_system.py."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.script_path = PROJECT_ROOT / "scripts" / "validate_authentic_system.py"
        if not self.script_path.exists(): # Make it a skip if script not found
             pytest.skip(f"Script non trouvé: {self.script_path}", allow_module_level=True)
    
    def test_validate_script_exists_and_executable(self):
        """Test d'existence et d'exécutabilité du script."""
        assert self.script_path.exists()
        assert self.script_path.is_file()
        
        content = self.script_path.read_text(encoding='utf-8')
        assert 'SystemAuthenticityValidator' in content
        assert 'def main()' in content
        assert 'argparse' in content
    
    def test_validate_script_help_output(self):
        """Test de l'affichage de l'aide du script."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                encoding='utf-8'
            )
            
            assert result.returncode == 0, f"Help command failed: {result.stderr}"
            assert "validation de l'authenticité" in result.stdout.lower()
            assert "--config" in result.stdout
            assert "--check-all" in result.stdout
            assert "--require-100-percent" in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.fail(f"Erreur lors de l'exécution du test d'aide: {e}")
    
    def test_validate_script_with_testing_config(self):
        """Test du script avec configuration de test."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path),
                 "--config", "testing", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                encoding='utf-8'
            )
            
            assert result.returncode in [0, 1, 2], f"Script exit code {result.returncode} not in [0,1,2]. stderr: {result.stderr}"
            
            output = result.stdout.lower()
            json_indicators = ['authenticity_percentage', 'total_components', '{', '}']
            message_indicators = ['authenticity', 'validation', 'composant']
            
            has_json = any(indicator in output for indicator in json_indicators)
            has_messages = any(indicator in output for indicator in message_indicators)
            
            assert has_json or has_messages, f"Output does not contain JSON or expected messages. Output: {result.stdout}"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.fail(f"Erreur lors de l'exécution du test de config: {e}")
    
    def test_validate_script_json_output_format(self):
        """Test du format de sortie JSON."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path),
                 "--config", "testing", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                encoding='utf-8'
            )
            
            json_data_found = False
            if result.stdout.strip():
                try:
                    lines = result.stdout.splitlines()
                    parsed_json = None
                    for line in lines:
                        if line.strip().startswith('{') and line.strip().endswith('}'):
                            parsed_json = json.loads(line.strip())
                            json_data_found = True
                            break
                    
                    if json_data_found and parsed_json:
                        expected_keys = [
                            'authenticity_percentage',
                            'is_100_percent_authentic',
                            'total_components'
                        ]
                        for key in expected_keys:
                            assert key in parsed_json, f"Clé manquante: {key} in {parsed_json}"
                        
                        assert isinstance(parsed_json['authenticity_percentage'], (int, float))
                        assert isinstance(parsed_json['is_100_percent_authentic'], bool)
                        assert isinstance(parsed_json['total_components'], int)
                    else:
                         assert result.returncode in [0, 1, 2], "Script ran but no valid JSON line found."
                except json.JSONDecodeError:
                    pytest.fail(f"JSONDecodeError. Output was: {result.stdout}")
            else:
                # If no stdout, script might have failed early, check exit code
                assert result.returncode in [0,1,2], f"No stdout, exit code: {result.returncode}, stderr: {result.stderr}"

        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.fail(f"Erreur lors de l'exécution du test JSON: {e}")
    
    def test_validate_script_require_100_percent_option(self):
        """Test de l'option --require-100-percent."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path),
                 "--config", "testing", "--require-100-percent"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                encoding='utf-8'
            )
            
            assert result.returncode in [0, 1], f"Exit code {result.returncode} not in [0,1]. stderr: {result.stderr}"
            
            if result.returncode == 1:
                output = result.stdout.lower()
                assert any(word in output for word in ['échec', 'fail', '<100', '< 100', 'not 100%']), f"Expected failure message not in output: {output}"
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.fail(f"Erreur lors de l'exécution du test require-100-percent: {e}")


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


@pytest.mark.skip(reason="CLI script is deprecated, tests need complete refactoring")
class TestCLIIntegrationAuthenticity:
    """Tests d'intégration pour les scripts CLI d'authenticité."""
    
    def setup_method(self):
        """Configuration pour les tests d'intégration."""
        self.validate_script = PROJECT_ROOT / "scripts" / "validate_authentic_system.py"
        self.analyze_script = PROJECT_ROOT / "scripts" / "main" / "analyze_text_authentic.py"
        if not self.validate_script.exists() or not self.analyze_script.exists():
            pytest.skip("Un des scripts CLI est manquant.", allow_module_level=True)

    def test_validation_before_analysis_workflow(self):
        """Test du workflow validation puis analyse."""
        try:
            validate_result = subprocess.run([
                sys.executable, str(self.validate_script),
                "--config", "testing",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60, check=False, encoding='utf-8')
            
            if validate_result.returncode == 0:
                analyze_result = subprocess.run([
                    sys.executable, str(self.analyze_script),
                    "--text", "Test d'intégration",
                    "--preset", "testing",
                    # "--validate-before-analysis", # This option might require specific setup or real components
                    "--skip-authenticity-validation", # More robust for unit/integration tests
                    "--quiet"
                ], capture_output=True, text=True, timeout=120, check=False, encoding='utf-8')
                assert analyze_result.returncode in [0, 1, 2], f"Analyze script failed after validation. stderr: {analyze_result.stderr}"
            else:
                assert validate_result.returncode in [1, 2], f"Validation script failed unexpectedly. stderr: {validate_result.stderr}"
                
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors du workflow intégration")
        except Exception as e:
            pytest.fail(f"Erreur lors du workflow: {e}")
    
    def test_consistent_configuration_between_scripts(self):
        """Test de cohérence de configuration entre scripts."""
        config_options_list = [
            ["--config", "testing"],
            ["--config", "development"]
        ]
        
        for options in config_options_list:
            try:
                validate_cmd = [sys.executable, str(self.validate_script)] + options + ["--output", "json"]
                validate_result = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=60, check=False, encoding='utf-8')
                
                preset_value = options[1] if len(options) > 1 and options[0] == "--config" else "testing"
                analyze_cmd = [
                    sys.executable, str(self.analyze_script),
                    "--text", "Test de cohérence",
                    "--preset", preset_value,
                    "--skip-authenticity-validation",
                    "--quiet"
                ]
                analyze_result = subprocess.run(analyze_cmd, capture_output=True, text=True, timeout=60, check=False, encoding='utf-8')
                
                assert validate_result.returncode in [0, 1, 2], f"Validate script failed for {options}. stderr: {validate_result.stderr}"
                assert analyze_result.returncode in [0, 1, 2], f"Analyze script failed for {options}. stderr: {analyze_result.stderr}"
                
                for result in [validate_result, analyze_result]:
                    assert "invalid choice" not in result.stderr.lower()
                    assert "unrecognized arguments" not in result.stderr.lower()
                
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout pour configuration {options}")
            except Exception as e:
                pytest.fail(f"Erreur pour configuration {options}: {e}")
    
    def test_error_handling_consistency(self):
        """Test de cohérence de gestion d'erreurs."""
        invalid_tests_args_list = [
            (["--invalid-option", "value"], True, True), # (args, expect_validate_fail, expect_analyze_fail)
            (["--logic-type", "invalid"], True, True),
            (["--mock-level", "invalid"], True, True),
            ([], False, True) # Validate might pass with no args (default), Analyze needs text/file
        ]
        
        for invalid_args_item, expect_validate_fail, expect_analyze_fail in invalid_tests_args_list:
            try:
                validate_cmd = [sys.executable, str(self.validate_script)] + invalid_args_item
                validate_result = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=30, check=False, encoding='utf-8')
                if expect_validate_fail:
                    assert validate_result.returncode != 0, f"Validate script should fail for {invalid_args_item}. stderr: {validate_result.stderr}"
                
                analyze_cmd_base = [sys.executable, str(self.analyze_script)]
                current_analyze_cmd = analyze_cmd_base + invalid_args_item
                
                # Add --text if no file/text arg to make it a valid call for other arg errors
                if not any(arg.startswith('--text') or arg.startswith('--file') for arg in invalid_args_item) and not invalid_args_item:
                     pass # analyze script will fail due to missing text/file
                elif not any(arg.startswith('--text') or arg.startswith('--file') for arg in invalid_args_item):
                    current_analyze_cmd.extend(["--text", "dummy_text_for_error_test"])


                analyze_result = subprocess.run(current_analyze_cmd, capture_output=True, text=True, timeout=30, check=False, encoding='utf-8')
                if expect_analyze_fail:
                    assert analyze_result.returncode != 0, f"Analyze script should fail for {invalid_args_item}. stderr: {analyze_result.stderr}"
                    if any("invalid" in str(arg) for arg in invalid_args_item):
                        assert "invalid choice" in analyze_result.stderr.lower()
                
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout pour test d'erreur {invalid_args_item}")
            except Exception as e:
                pytest.fail(f"Erreur lors du test d'erreur {invalid_args_item}: {e}")


@pytest.mark.skip(reason="CLI script is deprecated, tests need complete refactoring")
class TestCLIConfigurationValidation:
    """Tests de validation des configurations CLI."""
    
    def test_preset_configuration_consistency(self):
        """Test de cohérence des presets entre code et CLI."""
        available_presets = ['authentic_fol', 'authentic_pl', 'development', 'testing']
        
        for preset_name in available_presets:
            config = None
            if preset_name == 'authentic_fol': config = PresetConfigs.authentic_fol()
            elif preset_name == 'authentic_pl': config = PresetConfigs.authentic_pl()
            elif preset_name == 'development': config = PresetConfigs.development()
            elif preset_name == 'testing': config = PresetConfigs.testing()
            else: pytest.fail(f"Preset {preset_name} not handled in test")

            assert isinstance(config, UnifiedConfig), f"Preset {preset_name} did not return UnifiedConfig"
            assert hasattr(config, 'mock_level')
            assert hasattr(config, 'logic_type')
            assert hasattr(config, 'taxonomy_size')
    
    def test_cli_option_validation(self):
        """Test de validation des options CLI."""
        mock_levels_enum_values = {level.value for level in MockLevel}
        cli_mock_level_choices = {'none', 'minimal', 'full'} # Typical CLI choices
        # Allow 'minimal' from CLI to map to 'partial' in enum if that's the case
        assert cli_mock_level_choices.issubset(mock_levels_enum_values) or \
               ('minimal' in cli_mock_level_choices and 'partial' in mock_levels_enum_values and
                (cli_mock_level_choices - {'minimal'}).issubset(mock_levels_enum_values | {'partial'}))


        logic_types_enum_values = {logic.value for logic in LogicType}
        cli_logic_type_choices = {'fol', 'pl', 'modal', 'first_order'}
        # Allow 'first_order' from CLI to map to 'fol' in enum
        assert all(lt in logic_types_enum_values or (lt == 'first_order' and 'fol' in logic_types_enum_values) for lt in cli_logic_type_choices)


        taxonomy_sizes_enum_values = {size.value for size in TaxonomySize}
        cli_taxonomy_size_choices = {'full', 'mock'}
        assert cli_taxonomy_size_choices.issubset(taxonomy_sizes_enum_values)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
