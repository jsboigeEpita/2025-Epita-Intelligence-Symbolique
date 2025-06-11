
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour l'intégration CLI du système de configuration unifié.

Ce module teste l'interface ligne de commande et la conversion des arguments
CLI vers la configuration UnifiedConfig, incluant :
- Parsing des arguments CLI (--logic-type, --mock-level, etc.)
- Conversion vers UnifiedConfig
- Validation des combinaisons CLI
- Intégration avec analyze_text.py
"""

import pytest
import argparse
import sys

from pathlib import Path

# Ajout du chemin pour importer les modules du projet
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.unified_config import (
    UnifiedConfig, LogicType, MockLevel, OrchestrationType,
    TaxonomySize, AgentType
)

# Import des fonctions CLI à tester
from scripts.rhetorical_analysis.unified_production_analyzer import (
    create_config_from_args as create_unified_config_from_args,
    # convert_unified_to_pipeline_config, # Cette fonction n'existe plus dans le nouveau script
    create_cli_parser as create_argument_parser
)


class MockArgs:
    """Classe pour simuler les arguments CLI."""
    
    def __init__(self, **kwargs):
        # Valeurs par défaut
        defaults = {
            'logic_type': 'fol',
            'agents': 'informal,fol_logic,synthesis',
            'orchestration': 'unified',
            'mock_level': 'none',
            'taxonomy': 'full',
            'modes': 'fallacies,coherence,semantic',
            'advanced': False,
            'mocks': False,
            'no_jvm': False,
            'require_real_gpt': True,
            'require_real_tweety': True,
            'require_full_taxonomy': True,
            'validate_tools': True,
            'format': 'markdown',
            'template': 'default',
            'output_mode': 'both',
            'output': None,
            'verbose': False
        }
        
        # Mise à jour avec les valeurs fournies
        defaults.update(kwargs)
        
        # Attribution des valeurs comme attributs
        for key, value in defaults.items():
            setattr(self, key, value)


class TestConfigurationCLI:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests unitaires pour l'interface CLI de configuration."""
    
    def test_logic_type_cli_argument(self):
        """Test l'argument CLI --logic-type."""
        # Test FOL
        args_fol = MockArgs(logic_type='fol')
        config = create_unified_config_from_args(args_fol)
        assert config.logic_type == LogicType.FOL
        
        # Test PL
        args_pl = MockArgs(logic_type='pl')
        config = create_unified_config_from_args(args_pl)
        assert config.logic_type == LogicType.PL
        
        # Test propositional (alias)
        args_prop = MockArgs(logic_type='propositional')
        config = create_unified_config_from_args(args_prop)
        assert config.logic_type == LogicType.PL
        
        # Test first_order (alias)
        args_fo = MockArgs(logic_type='first_order')
        config = create_unified_config_from_args(args_fo)
        assert config.logic_type == LogicType.FOL
        
        # Test modal (avec avertissement)
        args_modal = MockArgs(logic_type='modal', mock_level='partial', no_jvm=True,
                             require_real_gpt=False, require_real_tweety=False,
                             require_full_taxonomy=False)
        with patch('scripts.main.analyze_text.logger') as mock_logger:
            config = create_unified_config_from_args(args_modal)
            assert config.logic_type == LogicType.MODAL
            # Vérifier que le warning Modal a été émis (il peut y avoir d'autres warnings)
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if "Modal sélectionnée" in str(call)]
            assert len(warning_calls) > 0

    def test_mock_level_cli_argument(self):
        """Test l'argument CLI --mock-level."""
        # Test none (authentique)
        args_none = MockArgs(mock_level='none')
        config = create_unified_config_from_args(args_none)
        assert config.mock_level == MockLevel.NONE
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        
        # Test partial (développement)
        args_partial = MockArgs(mock_level='partial',
                               require_real_gpt=False, require_real_tweety=False,
                               require_full_taxonomy=False)
        config = create_unified_config_from_args(args_partial)
        assert config.mock_level == MockLevel.PARTIAL
        
        # Test full (test)
        args_full = MockArgs(mock_level='full',
                            require_real_gpt=False, require_real_tweety=False,
                            require_full_taxonomy=False)
        config = create_unified_config_from_args(args_full)
        assert config.mock_level == MockLevel.FULL
        
        # Test legacy --mocks flag
        args_legacy = MockArgs(mocks=True, no_jvm=True,
                              require_real_gpt=False, require_real_tweety=False,
                              require_full_taxonomy=False)
        with patch('scripts.main.analyze_text.logger') as mock_logger:
            config = create_unified_config_from_args(args_legacy)
            assert config.mock_level == MockLevel.FULL
            # Vérifier que le warning legacy a été émis (peut y avoir d'autres warnings)
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if "mocks legacy" in str(call)]
            assert len(warning_calls) > 0

    def test_taxonomy_cli_argument(self):
        """Test l'argument CLI --taxonomy."""
        # Test full (1000 nœuds)
        args_full = MockArgs(taxonomy='full')
        config = create_unified_config_from_args(args_full)
        assert config.taxonomy_size == TaxonomySize.FULL
        taxonomy_config = config.get_taxonomy_config()
        assert taxonomy_config["node_count"] == 1000
        
        # Test mock (3 nœuds)
        args_mock = MockArgs(taxonomy='mock', mock_level='partial',
                            require_real_gpt=False, require_real_tweety=False,
                            require_full_taxonomy=False)
        config = create_unified_config_from_args(args_mock)
        assert config.taxonomy_size == TaxonomySize.MOCK
        taxonomy_config = config.get_taxonomy_config()
        assert taxonomy_config["node_count"] == 3

    def test_orchestration_mode_cli_argument(self):
        """Test l'argument CLI --orchestration."""
        # Test unified
        args_unified = MockArgs(orchestration='unified')
        config = create_unified_config_from_args(args_unified)
        assert config.orchestration_type == OrchestrationType.UNIFIED
        
        # Test conversation
        args_conversation = MockArgs(orchestration='conversation')
        config = create_unified_config_from_args(args_conversation)
        assert config.orchestration_type == OrchestrationType.CONVERSATION
        
        # Test real (legacy)
        args_real = MockArgs(orchestration='real')
        config = create_unified_config_from_args(args_real)
        assert config.orchestration_type == OrchestrationType.REAL
        
        # Test custom
        args_custom = MockArgs(orchestration='custom')
        config = create_unified_config_from_args(args_custom)
        assert config.orchestration_type == OrchestrationType.CUSTOM
        
        # Test fallback avec --advanced
        args_advanced = MockArgs(advanced=True)
        # Supprimer l'attribut orchestration pour tester le fallback
        if hasattr(args_advanced, 'orchestration'):
            delattr(args_advanced, 'orchestration')
        config = create_unified_config_from_args(args_advanced)
        assert config.orchestration_type == OrchestrationType.CONVERSATION

    def test_agents_cli_argument(self):
        """Test l'argument CLI --agents."""
        # Test agents standards
        args_standard = MockArgs(agents='informal,fol_logic,synthesis')
        config = create_unified_config_from_args(args_standard)
        expected_agents = [AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS]
        assert config.agents == expected_agents
        
        # Test avec legacy logic agent
        args_legacy = MockArgs(agents='informal,logic,synthesis')
        with patch('scripts.main.analyze_text.logger') as mock_logger:
            config = create_unified_config_from_args(args_legacy)
            # Le système convertit automatiquement LOGIC -> FOL_LOGIC pour FOL
            expected_agents = [AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS]
            assert config.agents == expected_agents
        
        # Test avec agents étendus
        args_extended = MockArgs(agents='informal,fol_logic,synthesis,extract,pm')
        config = create_unified_config_from_args(args_extended)
        expected_agents = [
            AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS,
            AgentType.EXTRACT, AgentType.PM
        ]
        assert config.agents == expected_agents
        
        # Test avec agent inconnu
        args_unknown = MockArgs(agents='informal,unknown_agent,synthesis')
        with patch('scripts.main.analyze_text.logger') as mock_logger:
            config = create_unified_config_from_args(args_unknown)
            mock_logger.warning.assert_any_call("⚠️ Agent inconnu ignoré: unknown_agent")
            # L'agent inconnu doit être ignoré
            expected_agents = [AgentType.INFORMAL, AgentType.SYNTHESIS]
            assert config.agents == expected_agents

    def test_combined_cli_arguments(self):
        """Test des combinaisons d'arguments CLI."""
        # Configuration production
        args_prod = MockArgs(
            logic_type='fol',
            mock_level='none',
            taxonomy='full',
            orchestration='unified',
            agents='informal,fol_logic,synthesis',
            advanced=True
        )
        config = create_unified_config_from_args(args_prod)
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.taxonomy_size == TaxonomySize.FULL
        assert config.orchestration_type == OrchestrationType.UNIFIED
        assert config.enable_advanced_tools is True
        
        # Configuration développement
        args_dev = MockArgs(
            logic_type='pl',
            mock_level='partial',
            taxonomy='mock',
            orchestration='conversation',
            agents='informal,synthesis',
            no_jvm=True,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        config = create_unified_config_from_args(args_dev)
        assert config.logic_type == LogicType.PL
        assert config.mock_level == MockLevel.PARTIAL
        assert config.taxonomy_size == TaxonomySize.MOCK
        assert config.orchestration_type == OrchestrationType.CONVERSATION
        assert config.enable_jvm is False

    def test_invalid_cli_combinations(self):
        """Test des combinaisons CLI invalides."""
        # Test mock_level=none avec require_real_* activé (doit passer car cohérent)
        args_valid = MockArgs(
            mock_level='none',
            require_real_gpt=True,
            require_real_tweety=True
        )
        config = create_unified_config_from_args(args_valid)
        assert config.mock_level == MockLevel.NONE
        
        # Test combinaison problématique: mock_level=partial avec require_real_gpt=True
        args_invalid = MockArgs(
            mock_level='partial',
            require_real_gpt=True  # Incohérent
        )
        with pytest.raises(ValueError, match="Configuration incohérente"):
            create_unified_config_from_args(args_invalid)

    def test_authenticity_cli_arguments(self):
        """Test les arguments CLI de validation d'authenticité."""
        args_auth = MockArgs(
            require_real_gpt=True,
            require_real_tweety=True,
            require_full_taxonomy=True,
            validate_tools=True
        )
        config = create_unified_config_from_args(args_auth)
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        assert config.require_full_taxonomy is True
        assert config.validate_tool_calls is True

    def test_output_cli_arguments(self):
        """Test les arguments CLI de sortie."""
        args_output = MockArgs(
            format='json',
            template='detailed',
            output_mode='file',
            output='/path/to/output.json'
        )
        config = create_unified_config_from_args(args_output)
        assert config.output_format == 'json'
        assert config.output_template == 'detailed'
        assert config.output_mode == 'file'
        assert config.output_path == '/path/to/output.json'

    # def test_conversion_to_pipeline_config(self):
    #     """Test la conversion vers UnifiedAnalysisConfig pour le pipeline."""
    #     # NOTE: Cette fonction a été supprimée après la refactorisation majeure.
    #     # Le nouveau pipeline utilise directement la configuration.
    #     pass

    def test_argument_parser_creation(self):
        """Test la création du parser d'arguments."""
        parser = create_argument_parser()
        
        # Test parsing d'arguments valides
        args = parser.parse_args([
            '--logic-type', 'fol',
            '--mock-level', 'none',
            '--taxonomy', 'full',
            '--orchestration', 'unified',
            '--agents', 'informal,fol_logic,synthesis',
            '--format', 'markdown'
        ])
        
        assert args.logic_type == 'fol'
        assert args.mock_level == 'none'
        assert args.taxonomy == 'full'
        assert args.orchestration == 'unified'
        assert args.agents == 'informal,fol_logic,synthesis'
        assert args.format == 'markdown'
        
        # Test valeurs par défaut
        default_args = parser.parse_args([])
        assert default_args.logic_type == 'fol'
        assert default_args.mock_level == 'none'
        assert default_args.taxonomy == 'full'
        assert default_args.orchestration == 'unified'
        assert default_args.agents == 'informal,fol_logic,synthesis'
        assert default_args.format == 'markdown'

    def test_configuration_logging(self):
        """Test le logging de la configuration."""
        args = MockArgs()
        
        with patch('scripts.main.analyze_text.logger') as mock_logger:
            config = create_unified_config_from_args(args)
            
            # Vérifier que les logs de configuration sont émis
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            config_logs = [log for log in log_calls if "Configuration dynamique unifiée" in log]
            assert len(config_logs) > 0
            
            # Vérifier les détails loggés
            detail_logs = [log for log in log_calls if any(keyword in log for keyword in 
                          ["Logique:", "Agents:", "Orchestration:", "Mock Level:", "Taxonomie:"])]
            assert len(detail_logs) >= 5  # Au moins 5 détails de configuration

    def test_validation_warnings(self):
        """Test les avertissements de validation."""
        # Configuration avec problèmes potentiels
        args_problematic = MockArgs(
            mock_level='partial',
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False,
            no_jvm=True  # Éviter l'incohérence JVM activée / Tweety non-réel
        )
        
        with patch('scripts.main.analyze_text.logger') as mock_logger:
            # Modifier manuellement pour créer incohérence après création
            config = create_unified_config_from_args(args_problematic)
            
            # Le mock ne devrait pas générer d'avertissement car la config est cohérente
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if call.args[0].startswith("⚠️ Problèmes de configuration détectés")]
            # Cette configuration est cohérente, donc pas d'avertissement attendu
            assert len(warning_calls) == 0


class TestCLIIntegration:
    """Tests d'intégration pour l'interface CLI complète."""
    
    
    
    
    def test_end_to_end_cli_flow(self, mock_report_gen, mock_pipeline, mock_selector):
        """Test du flux CLI de bout en bout."""
        # Configuration des mocks
        mock_selector.return_value.load_source_batch.return_value = (
            "Test text", "Test description", "simple"
        )
        mock_pipeline.return_value = {
            "analysis_results": {"test": "data"},
            "metadata": {"version": "test"}
        }
        mock_report_gen.return_value.generate_report.return_value = "Test report"
        
        # Import et test du main (simulation)
        from scripts.rhetorical_analysis.unified_production_analyzer import create_config_from_args as create_unified_config_from_args
        
        args = MockArgs(
            source_type='simple',
            logic_type='fol',
            mock_level='none',
            format='markdown'
        )
        
        # Test de la création de config depuis les args
        config = create_unified_config_from_args(args)
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.output_format == 'markdown'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])