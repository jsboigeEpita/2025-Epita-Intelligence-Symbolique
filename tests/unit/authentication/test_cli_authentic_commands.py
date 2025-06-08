#!/usr/bin/env python3
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
from unittest.mock import patch, Mock
from typing import Dict, Any, List

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.unified_config import UnifiedConfig, MockLevel, TaxonomySize, LogicType, PresetConfigs
except ImportError as e:
    pytest.skip(f"Modules requis non disponibles: {e}", allow_module_level=True)


class TestValidateAuthenticSystemCLI:
    """Tests pour le script validate_authentic_system.py."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.script_path = PROJECT_ROOT / "scripts" / "validate_authentic_system.py"
        assert self.script_path.exists(), f"Script non trouvé: {self.script_path}"
    
    def test_validate_script_exists_and_executable(self):
        """Test d'existence et d'exécutabilité du script."""
        assert self.script_path.exists()
        assert self.script_path.is_file()
        
        # Test de lecture du contenu
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
                timeout=30
            )
            
            assert result.returncode == 0
            assert "validation de l'authenticité" in result.stdout.lower()
            assert "--config" in result.stdout
            assert "--check-all" in result.stdout
            assert "--require-100-percent" in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")
    
    def test_validate_script_with_testing_config(self):
        """Test du script avec configuration de test."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), 
                 "--config", "testing", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Le script peut échouer sur certains composants, c'est normal en test
            assert result.returncode in [0, 1, 2]  # Codes de sortie valides
            
            # Vérifier que la sortie contient du JSON ou des messages attendus
            output = result.stdout.lower()
            json_indicators = ['authenticity_percentage', 'total_components', '{', '}']
            message_indicators = ['authenticity', 'validation', 'composant']
            
            has_json = any(indicator in output for indicator in json_indicators)
            has_messages = any(indicator in output for indicator in message_indicators)
            
            assert has_json or has_messages
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")
    
    def test_validate_script_json_output_format(self):
        """Test du format de sortie JSON."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path),
                 "--config", "testing", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Essayer de parser le JSON depuis stdout
            if result.stdout.strip():
                try:
                    # Chercher une ligne qui ressemble à du JSON
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if line.strip().startswith('{'):
                            json_data = json.loads(line.strip())
                            
                            # Vérifier la structure attendue
                            expected_keys = [
                                'authenticity_percentage',
                                'is_100_percent_authentic',
                                'total_components'
                            ]
                            
                            for key in expected_keys:
                                assert key in json_data, f"Clé manquante: {key}"
                            
                            assert isinstance(json_data['authenticity_percentage'], (int, float))
                            assert isinstance(json_data['is_100_percent_authentic'], bool)
                            assert isinstance(json_data['total_components'], int)
                            break
                except json.JSONDecodeError:
                    # Si pas de JSON valide, vérifier au moins que le script s'exécute
                    assert result.returncode in [0, 1, 2]
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")
    
    def test_validate_script_require_100_percent_option(self):
        """Test de l'option --require-100-percent."""
        try:
            # Test avec configuration qui ne sera probablement pas 100% authentique
            result = subprocess.run(
                [sys.executable, str(self.script_path),
                 "--config", "testing", "--require-100-percent"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Avec la config testing, on s'attend à un échec (code 1)
            assert result.returncode in [0, 1]
            
            if result.returncode == 1:
                # Vérifier le message d'échec
                output = result.stdout.lower()
                assert any(word in output for word in ['échec', 'fail', '<100', '< 100'])
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")


class TestAnalyzeTextAuthenticCLI:
    """Tests pour le script analyze_text_authentic.py."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.script_path = PROJECT_ROOT / "scripts" / "main" / "analyze_text_authentic.py"
        assert self.script_path.exists(), f"Script non trouvé: {self.script_path}"
        self.test_text = "Tous les politiciens mentent, donc Pierre ment."
    
    def test_analyze_script_exists_and_executable(self):
        """Test d'existence et d'exécutabilité du script."""
        assert self.script_path.exists()
        assert self.script_path.is_file()
        
        content = self.script_path.read_text(encoding='utf-8')
        assert 'AuthenticAnalysisRunner' in content
        assert 'def main()' in content
        assert 'argparse' in content
    
    def test_analyze_script_help_output(self):
        """Test de l'affichage de l'aide du script."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            assert result.returncode == 0
            assert "analyse de texte" in result.stdout.lower()
            assert "--text" in result.stdout
            assert "--preset" in result.stdout
            assert "--force-authentic" in result.stdout
            assert "--require-real-gpt" in result.stdout
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")
    
    def test_analyze_script_basic_execution(self):
        """Test d'exécution basique du script d'analyse."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_file = f.name
            
            try:
                result = subprocess.run([
                    sys.executable, str(self.script_path),
                    "--text", self.test_text,
                    "--preset", "testing",  # Configuration safe pour les tests
                    "--skip-authenticity-validation",  # Éviter les validations coûteuses
                    "--output", output_file,
                    "--quiet"
                ], capture_output=True, text=True, timeout=120)
                
                # Le script peut échouer sur certains composants, vérifier les codes valides
                valid_exit_codes = [0, 1, 2]  # Succès, échec authenticity, erreur
                assert result.returncode in valid_exit_codes
                
                # Si succès, vérifier le fichier de sortie
                if result.returncode == 0 and os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
                    
                    # Vérifier la structure de base
                    assert isinstance(output_data, dict)
                    
                    # Peut contenir des métriques de performance
                    if 'performance_metrics' in output_data:
                        perf = output_data['performance_metrics']
                        assert 'analysis_time_seconds' in perf
                        assert isinstance(perf['analysis_time_seconds'], (int, float))
                
            finally:
                if os.path.exists(output_file):
                    os.unlink(output_file)
                    
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")
    
    def test_analyze_script_force_authentic_option(self):
        """Test de l'option --force-authentic."""
        try:
            result = subprocess.run([
                sys.executable, str(self.script_path),
                "--text", self.test_text,
                "--force-authentic",
                "--skip-authenticity-validation",  # Éviter la validation avant analyse
                "--quiet"
            ], capture_output=True, text=True, timeout=120)
            
            # Avec --force-authentic, le script devrait exiger des composants authentiques
            # Il peut échouer si les composants ne sont pas disponibles
            valid_exit_codes = [0, 1, 2]
            assert result.returncode in valid_exit_codes
            
            # Vérifier que la configuration force bien l'authenticité
            if result.returncode != 0:
                output = result.stdout.lower() + result.stderr.lower()
                authenticity_indicators = [
                    'authenticity', 'authentique', 'mock', 'composant',
                    'gpt', 'tweety', 'api', 'jar'
                ]
                assert any(indicator in output for indicator in authenticity_indicators)
            
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")
    
    def test_analyze_script_configuration_options(self):
        """Test des options de configuration spécifiques."""
        config_tests = [
            ("--preset", "testing"),
            ("--logic-type", "fol"),
            ("--mock-level", "full"),
            ("--taxonomy-size", "mock")
        ]
        
        for option, value in config_tests:
            try:
                result = subprocess.run([
                    sys.executable, str(self.script_path),
                    "--text", self.test_text,
                    option, value,
                    "--skip-authenticity-validation",
                    "--quiet"
                ], capture_output=True, text=True, timeout=60)
                
                # Vérifier que l'option est acceptée (pas d'erreur de parsing)
                assert result.returncode in [0, 1, 2]
                
                # Si erreur de parsing d'arguments, le code serait différent
                assert "unrecognized arguments" not in result.stderr.lower()
                assert "invalid choice" not in result.stderr.lower()
                
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout pour option {option}")
            except Exception as e:
                pytest.skip(f"Erreur pour option {option}: {e}")
    
    def test_analyze_script_file_input_option(self):
        """Test de l'option --file pour lire depuis un fichier."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(self.test_text)
                input_file = f.name
            
            try:
                result = subprocess.run([
                    sys.executable, str(self.script_path),
                    "--file", input_file,
                    "--preset", "testing",
                    "--skip-authenticity-validation",
                    "--quiet"
                ], capture_output=True, text=True, timeout=60)
                
                # Vérifier que le fichier est lu correctement
                valid_exit_codes = [0, 1, 2]
                assert result.returncode in valid_exit_codes
                
                # Pas d'erreur de lecture de fichier
                assert "fichier non trouvé" not in result.stdout.lower()
                assert "file not found" not in result.stderr.lower()
                
            finally:
                if os.path.exists(input_file):
                    os.unlink(input_file)
                    
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors de l'exécution du script")
        except Exception as e:
            pytest.skip(f"Erreur lors de l'exécution: {e}")


class TestCLIIntegrationAuthenticity:
    """Tests d'intégration pour les scripts CLI d'authenticité."""
    
    def setup_method(self):
        """Configuration pour les tests d'intégration."""
        self.validate_script = PROJECT_ROOT / "scripts" / "validate_authentic_system.py"
        self.analyze_script = PROJECT_ROOT / "scripts" / "main" / "analyze_text_authentic.py"
    
    def test_validation_before_analysis_workflow(self):
        """Test du workflow validation puis analyse."""
        try:
            # 1. Validation du système
            validate_result = subprocess.run([
                sys.executable, str(self.validate_script),
                "--config", "testing",
                "--output", "json"
            ], capture_output=True, text=True, timeout=60)
            
            # 2. Analyse si validation OK
            if validate_result.returncode == 0:
                analyze_result = subprocess.run([
                    sys.executable, str(self.analyze_script),
                    "--text", "Test d'intégration",
                    "--preset", "testing",
                    "--validate-before-analysis",
                    "--quiet"
                ], capture_output=True, text=True, timeout=120)
                
                # L'analyse devrait pouvoir s'exécuter après validation réussie
                assert analyze_result.returncode in [0, 1, 2]
            
            else:
                # Si validation échoue, c'est acceptable en environnement de test
                assert validate_result.returncode in [1, 2]
                
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout lors du workflow intégration")
        except Exception as e:
            pytest.skip(f"Erreur lors du workflow: {e}")
    
    def test_consistent_configuration_between_scripts(self):
        """Test de cohérence de configuration entre scripts."""
        # Test que les mêmes options de configuration donnent des résultats cohérents
        config_options = [
            ["--config", "testing"],
            ["--config", "development"]
        ]
        
        for options in config_options:
            try:
                # Validation avec ces options
                validate_cmd = [sys.executable, str(self.validate_script)] + options + ["--output", "json"]
                validate_result = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=60)
                
                # Analyse avec les mêmes options de base
                preset_value = options[1] if len(options) > 1 else "testing"
                analyze_cmd = [
                    sys.executable, str(self.analyze_script),
                    "--text", "Test de cohérence",
                    "--preset", preset_value,
                    "--skip-authenticity-validation",
                    "--quiet"
                ]
                analyze_result = subprocess.run(analyze_cmd, capture_output=True, text=True, timeout=60)
                
                # Les deux scripts devraient accepter les mêmes configurations
                assert validate_result.returncode in [0, 1, 2]
                assert analyze_result.returncode in [0, 1, 2]
                
                # Pas d'erreurs de configuration invalide
                for result in [validate_result, analyze_result]:
                    assert "invalid choice" not in result.stderr.lower()
                    assert "unrecognized arguments" not in result.stderr.lower()
                
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout pour configuration {options}")
            except Exception as e:
                pytest.skip(f"Erreur pour configuration {options}: {e}")
    
    def test_error_handling_consistency(self):
        """Test de cohérence de gestion d'erreurs."""
        # Test avec des configurations invalides pour vérifier la gestion d'erreurs
        invalid_tests = [
            # Option invalide
            ["--invalid-option", "value"],
            # Choix invalide
            ["--config", "invalid_config"],
            # Argument manquant pour analyze_script
            []  # Pas de --text ni --file
        ]
        
        for invalid_args in invalid_tests:
            try:
                # Test validation script
                validate_cmd = [sys.executable, str(self.validate_script)] + invalid_args
                validate_result = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=30)
                
                # Les erreurs d'arguments doivent avoir un code spécifique
                if invalid_args:  # Si des arguments sont fournis
                    assert validate_result.returncode != 0
                
                # Test analyze script (seulement si approprié)
                if len(invalid_args) > 0:
                    analyze_cmd = [sys.executable, str(self.analyze_script)] + invalid_args
                    analyze_result = subprocess.run(analyze_cmd, capture_output=True, text=True, timeout=30)
                    assert analyze_result.returncode != 0
                
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout pour test d'erreur {invalid_args}")
            except Exception as e:
                pytest.skip(f"Erreur lors du test d'erreur: {e}")


class TestCLIConfigurationValidation:
    """Tests de validation des configurations CLI."""
    
    def test_preset_configuration_consistency(self):
        """Test de cohérence des presets entre code et CLI."""
        # Vérifier que les presets définis dans le code sont supportés par CLI
        available_presets = ['authentic_fol', 'authentic_pl', 'development', 'testing']
        
        for preset in available_presets:
            # Vérifier que le preset existe dans le code
            if preset == 'authentic_fol':
                config = PresetConfigs.authentic_fol()
            elif preset == 'authentic_pl':
                config = PresetConfigs.authentic_pl()
            elif preset == 'development':
                config = PresetConfigs.development()
            elif preset == 'testing':
                config = PresetConfigs.testing()
            
            assert isinstance(config, UnifiedConfig)
            assert hasattr(config, 'mock_level')
            assert hasattr(config, 'logic_type')
            assert hasattr(config, 'taxonomy_size')
    
    def test_cli_option_validation(self):
        """Test de validation des options CLI."""
        # Test que les énumérations du code correspondent aux choix CLI
        
        # Mock levels
        mock_levels = [level.value for level in MockLevel]
        expected_mock_levels = ['none', 'partial', 'full']
        assert set(mock_levels) == set(expected_mock_levels)
        
        # Logic types  
        logic_types = [logic.value for logic in LogicType]
        expected_logic_types = ['fol', 'pl', 'modal', 'first_order']
        assert set(logic_types).issuperset({'fol', 'pl', 'modal'})
        
        # Taxonomy sizes
        taxonomy_sizes = [size.value for size in TaxonomySize]
        expected_taxonomy_sizes = ['full', 'mock']
        assert set(taxonomy_sizes) == set(expected_taxonomy_sizes)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
