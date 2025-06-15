# Imports nécessaires pour les tests
import pytest
import argparse
import sys
from unittest.mock import patch, MagicMock
import asyncio
from pathlib import Path

# Ajout du répertoire racine au `sys.path` pour permettre l'import des modules du projet
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import des classes et fonctions à tester depuis le nouveau script
from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import (
    UnifiedProductionConfig,
    LogicType,
    MockLevel,
    OrchestrationType,
    AnalysisMode,
    create_config_from_args,
    create_cli_parser
)

class MockArgs:
    """Classe flexible pour simuler les arguments parsés par argparse."""
    def __init__(self, **kwargs):
        # Définition d'un ensemble complet de valeurs par défaut saines
        defaults = {
            'input': 'default text',
            'batch': False,
            'llm_service': 'openai',
            'llm_model': 'gpt-4',
            'llm_temperature': 0.3,
            'llm_max_tokens': 2000,
            'logic_type': 'fol',
            'enable_fallback': True,
            'mock_level': 'none',
            'require_real_gpt': True,
            'require_real_tweety': True,
            'orchestration_type': 'unified',
            'enable_conversation_trace': True,
            'max_agents': 5,
            'analysis_modes': ['unified'],
            'enable_parallel': True,
            'max_workers': 4,
            'tweety_retry_count': 5,
            'tweety_retry_delay': 2.0,
            'llm_retry_count': 3,
            'output_format': 'json',
            'output_file': None,
            'save_intermediate': False,
            'report_level': 'production',
            'validate_inputs': True,
            'check_dependencies': True,
            'verbose': False,
            'quiet': False,
            'config_file': None
        }
        # Met à jour les valeurs par défaut avec celles fournies en argument
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(self, key, value)

class TestConfigurationCLI:
    """Suite de tests pour la configuration via la ligne de commande."""

    def test_logic_type_cli_argument(self):
        """Vérifie que l'argument --logic-type est correctement mappé."""
        args_fol = MockArgs(logic_type='fol')
        config_fol = create_config_from_args(args_fol)
        assert config_fol.logic_type == LogicType.FOL

        args_pl = MockArgs(logic_type='propositional')
        config_pl = create_config_from_args(args_pl)
        assert config_pl.logic_type == LogicType.PL

    def test_mock_level_cli_argument(self):
        """Vérifie le mapping de --mock-level et ses implications."""
        args_none = MockArgs(mock_level='none')
        config_none = create_config_from_args(args_none)
        assert config_none.mock_level == MockLevel.NONE
        assert config_none.require_real_gpt
        assert config_none.require_real_tweety

        args_partial = MockArgs(mock_level='partial', require_real_gpt=False, require_real_tweety=False)
        config_partial = create_config_from_args(args_partial)
        assert config_partial.mock_level == MockLevel.PARTIAL
        assert not config_partial.require_real_gpt

    def test_orchestration_type_cli_argument(self):
        """Vérifie le mapping de --orchestration-type."""
        args_unified = MockArgs(orchestration_type='unified')
        config_unified = create_config_from_args(args_unified)
        assert config_unified.orchestration_type == OrchestrationType.UNIFIED

        args_conversation = MockArgs(orchestration_type='conversation')
        config_conversation = create_config_from_args(args_conversation)
        assert config_conversation.orchestration_type == OrchestrationType.CONVERSATION

    def test_analysis_modes_cli_argument(self):
        """Vérifie que --analysis-modes est traité comme une liste d'enums."""
        args_modes = MockArgs(analysis_modes=['fallacies', 'coherence'])
        config_modes = create_config_from_args(args_modes)
        assert config_modes.analysis_modes == [AnalysisMode.FALLACIES, AnalysisMode.COHERENCE]

    def test_config_validation(self):
        """Teste la méthode de validation de la configuration."""
        # Configuration valide
        config_valid = create_config_from_args(MockArgs(mock_level='none', require_real_gpt=True))
        is_valid, errors = config_valid.validate()
        assert is_valid and not errors

        # Configuration invalide
        config_invalid = create_config_from_args(MockArgs(mock_level='none', require_real_gpt=False))
        is_valid, errors = config_invalid.validate()
        assert not is_valid and "Mode production requiert require_real_gpt=True" in errors[0]

    def test_argument_parser_defaults(self):
        """Vérifie les valeurs par défaut du parser d'arguments."""
        parser = create_cli_parser()
        args = parser.parse_args([])
        assert args.logic_type == 'fol'
        assert args.mock_level == 'none'
        assert args.orchestration_type == 'unified'
        assert args.analysis_modes == ['unified']
        assert args.require_real_gpt is True

    @patch('project_core.rhetorical_analysis_from_scripts.unified_production_analyzer.UnifiedProductionAnalyzer')
    @patch('project_core.rhetorical_analysis_from_scripts.unified_production_analyzer.asyncio.run')
    def test_end_to_end_cli_flow(self, mock_async_run, mock_analyzer_class):
        """Simule un flux CLI complet avec des mocks pour vérifier l'intégration."""
        
        # 1. Configuration des mocks
        mock_analyzer_instance = mock_analyzer_class.return_value
        mock_analyzer_instance.initialize.return_value = asyncio.Future()
        mock_analyzer_instance.initialize.return_value.set_result(True)

        mock_analyzer_instance.analyze_text.return_value = asyncio.Future()
        mock_analyzer_instance.analyze_text.return_value.set_result({"id": "analysis_123"})
        
        mock_analyzer_instance.generate_report.return_value = {"summary": "mocked report"}

        # 2. Définition des arguments CLI pour la simulation
        cli_args = [
            'my_script.py', 'un texte pour analyse',
            '--mock-level', 'full',
            '--llm-service', 'mock',
            '--no-check-dependencies'
        ]

        # 3. Patch de `sys.argv` pour simuler l'appel CLI
        with patch('sys.argv', cli_args):
            # 4. Importation de la fonction `main` à l'intérieur du contexte du patch
            from project_core.rhetorical_analysis_from_scripts.unified_production_analyzer import main
            
            # 5. Appel de la fonction `main` (elle sera exécutée de manière synchrone grâce au mock d'asyncio.run)
            asyncio.run(main())

            # 6. Vérifications
            mock_analyzer_class.assert_called_once()
            config_arg = mock_analyzer_class.call_args[0][0]
            assert isinstance(config_arg, UnifiedProductionConfig)
            assert config_arg.mock_level == MockLevel.FULL
            
            mock_analyzer_instance.initialize.assert_awaited_once()
            mock_analyzer_instance.analyze_text.assert_awaited_once()
            mock_analyzer_instance.generate_report.assert_called_once()


# Point d'entrée pour exécuter les tests avec pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])