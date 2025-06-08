<<<<<<< MAIN
#!/usr/bin/env python3
"""
Script d'analyse de texte avec authenticité 100%
===============================================

Script d'analyse rhétorique avec options avancées d'authenticité :
- Configuration authentique complète
- Élimination totale des mocks
- Validation en temps réel des composants
- Métriques d'authenticité
"""

import argparse
import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.unified_config import (
        UnifiedConfig, MockLevel, TaxonomySize, LogicType,
        OrchestrationType, SourceType, AgentType, PresetConfigs
    )
    from scripts.validate_authentic_system import SystemAuthenticityValidator, format_authenticity_report
except ImportError as e:
    print(f"❌ Erreur d'import config: {e}")
    sys.exit(1)

# Imports optionnels pour l'orchestration
try:
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator as UnifiedOrchestrator
    HAS_ORCHESTRATOR = True
except ImportError:
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator as UnifiedOrchestrator
        HAS_ORCHESTRATOR = True
    except ImportError:
        print("⚠️  Modules d'orchestration non disponibles - mode validation uniquement")
        HAS_ORCHESTRATOR = False
        class UnifiedOrchestrator:
            def __init__(self, mode="real", llm_service=None):
                self.mode = mode
                self.llm_service = llm_service
            async def initialize(self):
                return True
            async def orchestrate_analysis(self, text, **kwargs):
                return {"analysis": "Mode validation uniquement - orchestrateur non disponible"}

try:
    from argumentation_analysis.services.logic_service import LLMService
    HAS_LLM_SERVICE = True
except ImportError:
    print("⚠️  Service LLM non disponible - utilisation de simulation")
    HAS_LLM_SERVICE = False


class AuthenticAnalysisRunner:
    """Exécuteur d'analyse avec validation d'authenticité."""
    
    def __init__(self, config: UnifiedConfig, validate_authenticity: bool = True):
        """Initialise l'exécuteur d'analyse."""
        self.config = config
        self.validate_authenticity = validate_authenticity
        self.logger = logging.getLogger(__name__)
        self.validator = SystemAuthenticityValidator(config) if validate_authenticity else None
    
    async def validate_system_before_analysis(self) -> bool:
        """Valide l'authenticité du système avant l'analyse."""
        if not self.validate_authenticity:
            return True
        
        print("🔍 Validation de l'authenticité du système...")
        report = await self.validator.validate_system_authenticity()
        
        if not report.is_100_percent_authentic:
            print(f"⚠️  Système non 100% authentique ({report.authenticity_percentage:.1f}%)")
            
            if self.config.mock_level == MockLevel.NONE:
                print("❌ Configuration exige 100% d'authenticité mais système non conforme")
                print("\n📋 Rapport d'authenticité:")
                print(format_authenticity_report(report, 'console'))
                return False
            else:
                print("⚠️  Poursuite avec mocks autorisés par la configuration")
        else:
            print("✅ Système 100% authentique - Prêt pour l'analyse")
        
        return True
    
    async def run_analysis(self, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Exécute l'analyse complète avec validation d'authenticité."""
        # Validation pré-analyse
        if not await self.validate_system_before_analysis():
            raise RuntimeError("Système non authentique - Analyse interrompue")
        
        # Initialisation de l'orchestrateur
        print("🚀 Initialisation de l'orchestrateur...")
        
        # Déterminer le service LLM selon la configuration
        llm_service = None
        if self.config.require_real_gpt and HAS_LLM_SERVICE:
            try:
                from argumentation_analysis.llm.llm_service import LLMService
                llm_service = LLMService()
                print("✅ Service LLM réel configuré")
            except Exception as e:
                print(f"⚠️  Service LLM non disponible - utilisation de simulation: {e}")
        
        # Création de l'orchestrateur selon le type disponible
        if HAS_ORCHESTRATOR and 'RealLLMOrchestrator' in str(UnifiedOrchestrator):
            # Utilisation du RealLLMOrchestrator
            orchestrator = UnifiedOrchestrator(mode="real", llm_service=llm_service)
            await orchestrator.initialize()
            
            # Mesure de performance
            start_time = time.time()
            
            # Exécution de l'analyse
            print("📊 Exécution de l'analyse rhétorique...")
            result = await orchestrator.orchestrate_analysis(text)
        elif HAS_ORCHESTRATOR:
            # Utilisation du ConversationOrchestrator
            orchestrator = UnifiedOrchestrator(mode="demo")
            
            # Mesure de performance
            start_time = time.time()
            
            # Exécution de l'analyse
            print("📊 Exécution de l'analyse rhétorique...")
            result = {"analysis": orchestrator.run_orchestration(text)}
        else:
            # Mode fallback
            orchestrator = UnifiedOrchestrator()
            
            # Mesure de performance
            start_time = time.time()
            
            # Exécution de l'analyse
            print("📊 Exécution de l'analyse rhétorique...")
            result = await orchestrator.orchestrate_analysis(text)
        
        analysis_time = time.time() - start_time
        
        # Ajout des métriques d'authenticité au résultat
        if self.validate_authenticity:
            authenticity_report = await self.validator.validate_system_authenticity()
            result['authenticity_metrics'] = {
                'authenticity_percentage': authenticity_report.authenticity_percentage,
                'is_100_percent_authentic': authenticity_report.is_100_percent_authentic,
                'authentic_components': authenticity_report.authentic_components,
                'total_components': authenticity_report.total_components,
                'validation_timestamp': time.time()
            }
        
        # Ajout des métriques de performance
        result['performance_metrics'] = {
            'analysis_time_seconds': analysis_time,
            'configuration_used': self.config.to_dict(),
            'timestamp': time.time()
        }
        
        # Sauvegarde si demandée
        if output_path:
            await self._save_results(result, output_path)
        
        return result
    
    async def _save_results(self, result: Dict[str, Any], output_path: str):
        """Sauvegarde les résultats d'analyse."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résultats sauvegardés: {output_file}")


def create_authentic_configuration(args) -> UnifiedConfig:
    """Crée une configuration authentique basée sur les arguments."""
    # Configuration de base selon le preset
    if args.preset == 'authentic_fol':
        config = PresetConfigs.authentic_fol()
    elif args.preset == 'authentic_pl':
        config = PresetConfigs.authentic_pl()
    elif args.preset == 'development':
        config = PresetConfigs.development()
    elif args.preset == 'testing':
        config = PresetConfigs.testing()
    else:
        config = UnifiedConfig()
    
    # Surcharges par les arguments CLI
    if args.logic_type:
        config.logic_type = LogicType(args.logic_type)
    
    if args.mock_level:
        config.mock_level = MockLevel(args.mock_level)
    
    if args.taxonomy_size:
        config.taxonomy_size = TaxonomySize(args.taxonomy_size)
    
    # Options d'authenticité forcée
    if args.require_real_gpt:
        config.require_real_gpt = True
    
    if args.require_real_tweety:
        config.require_real_tweety = True
    
    if args.require_full_taxonomy:
        config.require_full_taxonomy = True
    
    # Option force authentique (remplace tout)
    if args.force_authentic:
        config.mock_level = MockLevel.NONE
        config.taxonomy_size = TaxonomySize.FULL
        config.require_real_gpt = True
        config.require_real_tweety = True
        config.require_full_taxonomy = True
        config.enable_jvm = True
        config.validate_tool_calls = True
        config.enable_cache = False
    
    # Autres options
    if args.disable_validation:
        config.validate_tool_calls = False
    
    if args.timeout:
        config.timeout_seconds = args.timeout
    
    return config


async def main():
    """Fonction principale d'analyse authentique."""
    parser = argparse.ArgumentParser(
        description="Analyse de texte avec authenticité 100%",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

# Analyse authentique complète avec FOL
python scripts/main/analyze_text_authentic.py \\
  --text "Tous les politiciens mentent, donc Pierre ment." \\
  --preset authentic_fol \\
  --force-authentic \\
  --output reports/analysis_authentic.json

# Analyse avec composants spécifiques authentiques
python scripts/main/analyze_text_authentic.py \\
  --text "Argument logique à analyser" \\
  --logic-type fol \\
  --require-real-gpt \\
  --require-real-tweety \\
  --require-full-taxonomy

# Analyse depuis fichier avec validation pré-analyse
python scripts/main/analyze_text_authentic.py \\
  --file examples/text_samples/argument_sample.txt \\
  --mock-level none \\
  --validate-before-analysis \\
  --verbose

# Configuration développement avec fallback authentique
python scripts/main/analyze_text_authentic.py \\
  --text "Test d'analyse" \\
  --preset development \\
  --require-real-gpt \\
  --skip-authenticity-validation
        """
    )
    
    # Arguments de base
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument('--text', help='Texte à analyser directement')
    text_group.add_argument('--file', help='Fichier contenant le texte à analyser')
    
    # Configuration prédéfinie
    parser.add_argument('--preset', 
                       choices=['authentic_fol', 'authentic_pl', 'development', 'testing'],
                       default='authentic_fol',
                       help='Configuration prédéfinie (défaut: authentic_fol)')
    
    # Paramètres de logique
    parser.add_argument('--logic-type', choices=['fol', 'pl', 'modal'],
                       help='Type de logique à utiliser')
    parser.add_argument('--agents', nargs='+',
                       choices=['informal', 'fol_logic', 'synthesis', 'extract', 'pm'],
                       help='Agents à activer')
    
    # Paramètres d'authenticité
    parser.add_argument('--mock-level', choices=['none', 'partial', 'full'],
                       help='Niveau de mocking (none = 100%% authentique)')
    parser.add_argument('--taxonomy-size', choices=['full', 'mock'],
                       help='Taille de la taxonomie (full = 1408 sophismes)')
    
    # Exigences d'authenticité spécifiques
    parser.add_argument('--require-real-gpt', action='store_true',
                       help='Exiger GPT-4o-mini authentique')
    parser.add_argument('--require-real-tweety', action='store_true',
                       help='Exiger Tweety JAR authentique')
    parser.add_argument('--require-full-taxonomy', action='store_true',
                       help='Exiger taxonomie complète (1408 sophismes)')
    
    # Option force authentique
    parser.add_argument('--force-authentic', action='store_true',
                       help='Force 100%% d\'authenticité (surcharge tout)')
    
    # Validation et contrôle
    parser.add_argument('--validate-before-analysis', action='store_true', default=True,
                       help='Valider l\'authenticité avant analyse (défaut: activé)')
    parser.add_argument('--skip-authenticity-validation', action='store_true',
                       help='Ignorer la validation d\'authenticité')
    parser.add_argument('--require-100-percent', action='store_true',
                       help='Échec si authenticité < 100%%')
    
    # Options avancées
    parser.add_argument('--disable-validation', action='store_true',
                       help='Désactiver la validation des tool calls')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout en secondes (défaut: 300)')
    
    # Sortie et affichage
    parser.add_argument('--output', help='Fichier de sortie pour les résultats')
    parser.add_argument('--format', choices=['json', 'markdown', 'both'], default='json',
                       help='Format de sortie')
    parser.add_argument('--verbose', action='store_true',
                       help='Affichage détaillé')
    parser.add_argument('--quiet', action='store_true',
                       help='Affichage minimal')
    
    args = parser.parse_args()
    
    # Configuration du logging
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Lecture du texte
        if args.text:
            text_to_analyze = args.text
        else:
            text_file = Path(args.file)
            if not text_file.exists():
                print(f"❌ Fichier non trouvé: {text_file}")
                sys.exit(1)
            text_to_analyze = text_file.read_text(encoding='utf-8')
        
        print(f"📝 Texte à analyser ({len(text_to_analyze)} caractères)")
        if args.verbose:
            print(f"   Preview: {text_to_analyze[:100]}...")
        
        # Création de la configuration
        config = create_authentic_configuration(args)
        
        if not args.quiet:
            print(f"🔧 Configuration: {args.preset}")
            print(f"🎯 Mock level: {config.mock_level.value}")
            print(f"🧠 Logique: {config.logic_type.value}")
            print(f"📚 Taxonomie: {config.taxonomy_size.value}")
            
            if config.require_real_gpt:
                print("✅ GPT authentique requis")
            if config.require_real_tweety:
                print("✅ Tweety authentique requis")
            if config.require_full_taxonomy:
                print("✅ Taxonomie complète requise")
        
        # Validation des exigences d'authenticité
        validate_authenticity = args.validate_before_analysis and not args.skip_authenticity_validation
        
        # Exécution de l'analyse
        runner = AuthenticAnalysisRunner(config, validate_authenticity)
        result = await runner.run_analysis(text_to_analyze, args.output)
        
        # Affichage des résultats
        if not args.quiet:
            print("\n" + "="*60)
            print("📊 RÉSULTATS D'ANALYSE")
            print("="*60)
            
            # Métriques d'authenticité
            if 'authenticity_metrics' in result:
                auth_metrics = result['authenticity_metrics']
                auth_percent = auth_metrics['authenticity_percentage']
                auth_icon = "✅" if auth_metrics['is_100_percent_authentic'] else "⚠️"
                print(f"{auth_icon} Authenticité: {auth_percent:.1f}%")
                print(f"📊 Composants authentiques: {auth_metrics['authentic_components']}/{auth_metrics['total_components']}")
            
            # Métriques de performance
            if 'performance_metrics' in result:
                perf_metrics = result['performance_metrics']
                print(f"⚡ Temps d'analyse: {perf_metrics['analysis_time_seconds']:.2f}s")
            
            # Résultats d'analyse (aperçu)
            if 'analysis' in result:
                analysis = result['analysis']
                if isinstance(analysis, dict):
                    print(f"🔍 Sophismes détectés: {len(analysis.get('fallacies', []))}")
                    print(f"📈 Score de cohérence: {analysis.get('coherence_score', 'N/A')}")
            
        # Vérification des exigences de pourcentage
        if args.require_100_percent and 'authenticity_metrics' in result:
            if not result['authenticity_metrics']['is_100_percent_authentic']:
                auth_percent = result['authenticity_metrics']['authenticity_percentage']
                print(f"\n❌ ÉCHEC: Authenticité {auth_percent:.1f}% < 100% requis")
                sys.exit(1)
        
        print("\n✅ Analyse terminée avec succès")
        
        if args.output:
            print(f"💾 Résultats sauvegardés: {args.output}")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'analyse: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())

=======
#!/usr/bin/env python3
"""
Script d'analyse de texte avec authenticité 100%
===============================================

Script d'analyse rhétorique avec options avancées d'authenticité :
- Configuration authentique complète
- Élimination totale des mocks
- Validation en temps réel des composants
- Métriques d'authenticité
"""

import argparse
import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.unified_config import (
        UnifiedConfig, MockLevel, TaxonomySize, LogicType,
        OrchestrationType, SourceType, AgentType, PresetConfigs
    )
    from scripts.validate_authentic_system import SystemAuthenticityValidator, format_authenticity_report
except ImportError as e:
    print(f"❌ Erreur d'import config: {e}")
    sys.exit(1)

# Imports optionnels pour l'orchestration
try:
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator as UnifiedOrchestrator
    HAS_ORCHESTRATOR = True
except ImportError:
    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator as UnifiedOrchestrator
        HAS_ORCHESTRATOR = True
    except ImportError:
        print("⚠️  Modules d'orchestration non disponibles - mode validation uniquement")
        HAS_ORCHESTRATOR = False
        class UnifiedOrchestrator:
            def __init__(self, mode="real", llm_service=None):
                self.mode = mode
                self.llm_service = llm_service
            async def initialize(self):
                return True
            async def orchestrate_analysis(self, text, **kwargs):
                return {"analysis": "Mode validation uniquement - orchestrateur non disponible"}

try:
    from argumentation_analysis.services.logic_service import LLMService
    HAS_LLM_SERVICE = True
except ImportError:
    print("⚠️  Service LLM non disponible - utilisation de simulation")
    HAS_LLM_SERVICE = False


class AuthenticAnalysisRunner:
    """Exécuteur d'analyse avec validation d'authenticité."""
    
    def __init__(self, config: UnifiedConfig, validate_authenticity: bool = True):
        """Initialise l'exécuteur d'analyse."""
        self.config = config
        self.validate_authenticity = validate_authenticity
        self.logger = logging.getLogger(__name__)
        self.validator = SystemAuthenticityValidator(config) if validate_authenticity else None
    
    async def validate_system_before_analysis(self) -> bool:
        """Valide l'authenticité du système avant l'analyse."""
        if not self.validate_authenticity:
            return True
        
        print("🔍 Validation de l'authenticité du système...")
        report = await self.validator.validate_system_authenticity()
        
        if not report.is_100_percent_authentic:
            print(f"⚠️  Système non 100% authentique ({report.authenticity_percentage:.1f}%)")
            
            if self.config.mock_level == MockLevel.NONE:
                print("❌ Configuration exige 100% d'authenticité mais système non conforme")
                print("\n📋 Rapport d'authenticité:")
                print(format_authenticity_report(report, 'console'))
                return False
            else:
                print("⚠️  Poursuite avec mocks autorisés par la configuration")
        else:
            print("✅ Système 100% authentique - Prêt pour l'analyse")
        
        return True
    
    async def run_analysis(self, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Exécute l'analyse complète avec validation d'authenticité."""
        # Validation pré-analyse
        if not await self.validate_system_before_analysis():
            raise RuntimeError("Système non authentique - Analyse interrompue")
        
        # Initialisation de l'orchestrateur
        print("🚀 Initialisation de l'orchestrateur...")
        
        # Déterminer le service LLM selon la configuration
        llm_service = None
        if self.config.require_real_gpt and HAS_LLM_SERVICE:
            try:
                from argumentation_analysis.llm.llm_service import LLMService
                llm_service = LLMService()
                print("✅ Service LLM réel configuré")
            except Exception as e:
                print(f"⚠️  Service LLM non disponible - utilisation de simulation: {e}")
        
        # Création de l'orchestrateur selon le type disponible
        if HAS_ORCHESTRATOR and 'RealLLMOrchestrator' in str(UnifiedOrchestrator):
            # Utilisation du RealLLMOrchestrator
            orchestrator = UnifiedOrchestrator(mode="real", llm_service=llm_service)
            await orchestrator.initialize()
            
            # Mesure de performance
            start_time = time.time()
            
            # Exécution de l'analyse
            print("📊 Exécution de l'analyse rhétorique...")
            result = await orchestrator.orchestrate_analysis(text)
        elif HAS_ORCHESTRATOR:
            # Utilisation du ConversationOrchestrator
            orchestrator = UnifiedOrchestrator(mode="demo")
            
            # Mesure de performance
            start_time = time.time()
            
            # Exécution de l'analyse
            print("📊 Exécution de l'analyse rhétorique...")
            result = {"analysis": orchestrator.run_orchestration(text)}
        else:
            # Mode fallback
            orchestrator = UnifiedOrchestrator()
            
            # Mesure de performance
            start_time = time.time()
            
            # Exécution de l'analyse
            print("📊 Exécution de l'analyse rhétorique...")
            result = await orchestrator.orchestrate_analysis(text)
        
        analysis_time = time.time() - start_time
        
        # Ajout des métriques d'authenticité au résultat
        if self.validate_authenticity:
            authenticity_report = await self.validator.validate_system_authenticity()
            result['authenticity_metrics'] = {
                'authenticity_percentage': authenticity_report.authenticity_percentage,
                'is_100_percent_authentic': authenticity_report.is_100_percent_authentic,
                'authentic_components': authenticity_report.authentic_components,
                'total_components': authenticity_report.total_components,
                'validation_timestamp': time.time()
            }
        
        # Ajout des métriques de performance
        result['performance_metrics'] = {
            'analysis_time_seconds': analysis_time,
            'configuration_used': self.config.to_dict(),
            'timestamp': time.time()
        }
        
        # Sauvegarde si demandée
        if output_path:
            await self._save_results(result, output_path)
        
        return result
    
    async def _save_results(self, result: Dict[str, Any], output_path: str):
        """Sauvegarde les résultats d'analyse."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résultats sauvegardés: {output_file}")


def create_authentic_configuration(args) -> UnifiedConfig:
    """Crée une configuration authentique basée sur les arguments."""
    # Configuration de base selon le preset
    if args.preset == 'authentic_fol':
        config = PresetConfigs.authentic_fol()
    elif args.preset == 'authentic_pl':
        config = PresetConfigs.authentic_pl()
    elif args.preset == 'development':
        config = PresetConfigs.development()
    elif args.preset == 'testing':
        config = PresetConfigs.testing()
    else:
        config = UnifiedConfig()
    
    # Surcharges par les arguments CLI
    if args.logic_type:
        config.logic_type = LogicType(args.logic_type)
    
    if args.mock_level:
        config.mock_level = MockLevel(args.mock_level)
    
    if args.taxonomy_size:
        config.taxonomy_size = TaxonomySize(args.taxonomy_size)
    
    # Options d'authenticité forcée
    if args.require_real_gpt:
        config.require_real_gpt = True
    
    if args.require_real_tweety:
        config.require_real_tweety = True
    
    if args.require_full_taxonomy:
        config.require_full_taxonomy = True
    
    # Option force authentique (remplace tout)
    if args.force_authentic:
        config.mock_level = MockLevel.NONE
        config.taxonomy_size = TaxonomySize.FULL
        config.require_real_gpt = True
        config.require_real_tweety = True
        config.require_full_taxonomy = True
        config.enable_jvm = True
        config.validate_tool_calls = True
        config.enable_cache = False
    
    # Autres options
    if args.disable_validation:
        config.validate_tool_calls = False
    
    if args.timeout:
        config.timeout_seconds = args.timeout
    
    return config


async def main():
    """Fonction principale d'analyse authentique."""
    parser = argparse.ArgumentParser(
        description="Analyse de texte avec authenticité 100%",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

# Analyse authentique complète avec FOL
python scripts/main/analyze_text_authentic.py \\
  --text "Tous les politiciens mentent, donc Pierre ment." \\
  --preset authentic_fol \\
  --force-authentic \\
  --output reports/analysis_authentic.json

# Analyse avec composants spécifiques authentiques
python scripts/main/analyze_text_authentic.py \\
  --text "Argument logique à analyser" \\
  --logic-type fol \\
  --require-real-gpt \\
  --require-real-tweety \\
  --require-full-taxonomy

# Analyse depuis fichier avec validation pré-analyse
python scripts/main/analyze_text_authentic.py \\
  --file examples/text_samples/argument_sample.txt \\
  --mock-level none \\
  --validate-before-analysis \\
  --verbose

# Configuration développement avec fallback authentique
python scripts/main/analyze_text_authentic.py \\
  --text "Test d'analyse" \\
  --preset development \\
  --require-real-gpt \\
  --skip-authenticity-validation
        """
    )
    
    # Arguments de base
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument('--text', help='Texte à analyser directement')
    text_group.add_argument('--file', help='Fichier contenant le texte à analyser')
    
    # Configuration prédéfinie
    parser.add_argument('--preset', 
                       choices=['authentic_fol', 'authentic_pl', 'development', 'testing'],
                       default='authentic_fol',
                       help='Configuration prédéfinie (défaut: authentic_fol)')
    
    # Paramètres de logique
    parser.add_argument('--logic-type', choices=['fol', 'pl', 'modal'],
                       help='Type de logique à utiliser')
    parser.add_argument('--agents', nargs='+',
                       choices=['informal', 'fol_logic', 'synthesis', 'extract', 'pm'],
                       help='Agents à activer')
    
    # Paramètres d'authenticité
    parser.add_argument('--mock-level', choices=['none', 'partial', 'full'],
                       help='Niveau de mocking (none = 100%% authentique)')
    parser.add_argument('--taxonomy-size', choices=['full', 'mock'],
                       help='Taille de la taxonomie (full = 1408 sophismes)')
    
    # Exigences d'authenticité spécifiques
    parser.add_argument('--require-real-gpt', action='store_true',
                       help='Exiger GPT-4o-mini authentique')
    parser.add_argument('--require-real-tweety', action='store_true',
                       help='Exiger Tweety JAR authentique')
    parser.add_argument('--require-full-taxonomy', action='store_true',
                       help='Exiger taxonomie complète (1408 sophismes)')
    
    # Option force authentique
    parser.add_argument('--force-authentic', action='store_true',
                       help='Force 100%% d\'authenticité (surcharge tout)')
    
    # Validation et contrôle
    parser.add_argument('--validate-before-analysis', action='store_true', default=True,
                       help='Valider l\'authenticité avant analyse (défaut: activé)')
    parser.add_argument('--skip-authenticity-validation', action='store_true',
                       help='Ignorer la validation d\'authenticité')
    parser.add_argument('--require-100-percent', action='store_true',
                       help='Échec si authenticité < 100%%')
    
    # Options avancées
    parser.add_argument('--disable-validation', action='store_true',
                       help='Désactiver la validation des tool calls')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout en secondes (défaut: 300)')
    
    # Sortie et affichage
    parser.add_argument('--output', help='Fichier de sortie pour les résultats')
    parser.add_argument('--format', choices=['json', 'markdown', 'both'], default='json',
                       help='Format de sortie')
    parser.add_argument('--verbose', action='store_true',
                       help='Affichage détaillé')
    parser.add_argument('--quiet', action='store_true',
                       help='Affichage minimal')
    
    args = parser.parse_args()
    
    # Configuration du logging
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Lecture du texte
        if args.text:
            text_to_analyze = args.text
        else:
            text_file = Path(args.file)
            if not text_file.exists():
                print(f"❌ Fichier non trouvé: {text_file}")
                sys.exit(1)
            text_to_analyze = text_file.read_text(encoding='utf-8')
        
        print(f"📝 Texte à analyser ({len(text_to_analyze)} caractères)")
        if args.verbose:
            print(f"   Preview: {text_to_analyze[:100]}...")
        
        # Création de la configuration
        config = create_authentic_configuration(args)
        
        if not args.quiet:
            print(f"🔧 Configuration: {args.preset}")
            print(f"🎯 Mock level: {config.mock_level.value}")
            print(f"🧠 Logique: {config.logic_type.value}")
            print(f"📚 Taxonomie: {config.taxonomy_size.value}")
            
            if config.require_real_gpt:
                print("✅ GPT authentique requis")
            if config.require_real_tweety:
                print("✅ Tweety authentique requis")
            if config.require_full_taxonomy:
                print("✅ Taxonomie complète requise")
        
        # Validation des exigences d'authenticité
        validate_authenticity = args.validate_before_analysis and not args.skip_authenticity_validation
        
        # Exécution de l'analyse
        runner = AuthenticAnalysisRunner(config, validate_authenticity)
        result = await runner.run_analysis(text_to_analyze, args.output)
        
        # Affichage des résultats
        if not args.quiet:
            print("\n" + "="*60)
            print("📊 RÉSULTATS D'ANALYSE")
            print("="*60)
            
            # Métriques d'authenticité
            if 'authenticity_metrics' in result:
                auth_metrics = result['authenticity_metrics']
                auth_percent = auth_metrics['authenticity_percentage']
                auth_icon = "✅" if auth_metrics['is_100_percent_authentic'] else "⚠️"
                print(f"{auth_icon} Authenticité: {auth_percent:.1f}%")
                print(f"📊 Composants authentiques: {auth_metrics['authentic_components']}/{auth_metrics['total_components']}")
            
            # Métriques de performance
            if 'performance_metrics' in result:
                perf_metrics = result['performance_metrics']
                print(f"⚡ Temps d'analyse: {perf_metrics['analysis_time_seconds']:.2f}s")
            
            # Résultats d'analyse (aperçu)
            if 'analysis' in result:
                analysis = result['analysis']
                if isinstance(analysis, dict):
                    print(f"🔍 Sophismes détectés: {len(analysis.get('fallacies', []))}")
                    print(f"📈 Score de cohérence: {analysis.get('coherence_score', 'N/A')}")
            
        # Vérification des exigences de pourcentage
        if args.require_100_percent and 'authenticity_metrics' in result:
            if not result['authenticity_metrics']['is_100_percent_authentic']:
                auth_percent = result['authenticity_metrics']['authenticity_percentage']
                print(f"\n❌ ÉCHEC: Authenticité {auth_percent:.1f}% < 100% requis")
                sys.exit(1)
        
        print("\n✅ Analyse terminée avec succès")
        
        if args.output:
            print(f"💾 Résultats sauvegardés: {args.output}")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'analyse: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> BACKUP
