#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal unifié d'analyse textuelle rhétorique - Version refactorisée.

Ce script remplace et consolide tous les scripts d'analyse éparpillés :
- rhetorical_analysis.py
- advanced_rhetorical_analysis.py
- complete_rhetorical_analysis_demo.py
- run_rhetorical_analysis_demo.py
- run_full_python_analysis_workflow.py

**REFACTORISATION MAJEURE :**
La logique métier a été extraite vers `argumentation_analysis.pipelines.unified_text_analysis`
Ce script devient un point d'entrée CLI léger qui délègue vers le pipeline réutilisable.

Fonctionnalités préservées :
- Interface CLI complète et riche
- Sélection interactive de sources (simple/complexe/personnalisée)
- Configuration d'analyse avancée
- Modes batch et interactif
- Compatibilité avec les 5+ scripts remplacés
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ajout du répertoire racine du projet au chemin
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("UnifiedTextAnalysisCLI")

# Imports des modules unifiés (legacy - preserved for CLI)
from scripts.core.unified_source_selector import UnifiedSourceSelector
from scripts.core.unified_report_generator import UnifiedReportGeneratorLegacy as UnifiedReportGenerator

# Import de la configuration dynamique unifiée
try:
    from config.unified_config import (
        UnifiedConfig, LogicType, MockLevel, OrchestrationType,
        SourceType, TaxonomySize, AgentType, PresetConfigs,
        load_config_from_env, validate_config
    )
except ImportError as e:
    logger.error(f"❌ Erreur d'importation de la configuration unifiée: {e}")
    logger.error("Assurez-vous que unified_config.py est correctement installé.")
    sys.exit(1)

# Import du nouveau pipeline unifié refactorisé
try:
    from argumentation_analysis.pipelines.unified_text_analysis import (
        UnifiedAnalysisConfig,
        UnifiedTextAnalysisPipeline,
        run_unified_text_analysis_pipeline,
        create_unified_config_from_legacy
    )
except ImportError as e:
    logger.error(f"❌ Erreur d'importation du pipeline unifié: {e}")
    logger.error("Assurez-vous que le pipeline unifié est correctement installé.")
    sys.exit(1)


def create_unified_config_from_args(args) -> UnifiedConfig:
    """
    Crée une configuration dynamique unifiée depuis les arguments CLI.
    
    Cette fonction utilise le nouveau système de configuration dynamique
    pour permettre la sélection de FOL/PL et l'élimination des mocks.
    """
    # Parsing des agents depuis la CLI
    agent_names = [name.strip() for name in args.agents.split(",")]
    agents = []
    for name in agent_names:
        try:
            if name == "fol_logic":
                agents.append(AgentType.FOL_LOGIC)
            elif name == "logic":
                agents.append(AgentType.LOGIC)  # Legacy
            else:
                agents.append(AgentType(name))
        except ValueError:
            logger.warning(f"⚠️ Agent inconnu ignoré: {name}")
    
    # Conversion du type de logique
    logic_type = LogicType.FOL  # Défaut FOL pour éviter échecs Modal
    if args.logic_type in ["fol", "first_order"]:
        logic_type = LogicType.FOL
    elif args.logic_type in ["pl", "propositional"]:
        logic_type = LogicType.PL
    elif args.logic_type == "modal":
        logic_type = LogicType.MODAL
        logger.warning("⚠️ Logique Modal sélectionnée - Risque d'échecs élevé")
    
    # Détermination du mode d'orchestration
    orchestration_type = OrchestrationType.UNIFIED
    if hasattr(args, 'orchestration'):
        try:
            orchestration_type = OrchestrationType(args.orchestration)
        except ValueError:
            logger.warning(f"⚠️ Type d'orchestration inconnu: {args.orchestration}")
    elif args.advanced:
        orchestration_type = OrchestrationType.CONVERSATION
    
    # Détermination du niveau de mock
    mock_level = MockLevel.NONE  # Défaut: Aucun mock pour authenticité
    if args.mocks:  # Legacy support a priorité
        mock_level = MockLevel.FULL
        logger.warning("⚠️ --mocks legacy détecté, utilisez --mock-level à l'avenir")
    elif hasattr(args, 'mock_level'):
        try:
            mock_level = MockLevel(args.mock_level)
        except ValueError:
            logger.warning(f"⚠️ Niveau de mock inconnu: {args.mock_level}")
    
    # Taxonomie
    taxonomy_size = TaxonomySize.FULL
    if hasattr(args, 'taxonomy'):
        try:
            taxonomy_size = TaxonomySize(args.taxonomy)
        except ValueError:
            logger.warning(f"⚠️ Taille de taxonomie inconnue: {args.taxonomy}")
    
    # Configuration d'authenticité
    # Si legacy mocks est activé, forcer la cohérence avec MockLevel.FULL
    if args.mocks:
        require_real_gpt = False
        require_real_tweety = False
        require_full_taxonomy = False
    else:
        require_real_gpt = getattr(args, 'require_real_gpt', True)
        require_real_tweety = getattr(args, 'require_real_tweety', True)
        require_full_taxonomy = getattr(args, 'require_full_taxonomy', True)
    validate_tools = getattr(args, 'validate_tools', True)
    
    # Création de la configuration unifiée
    config = UnifiedConfig(
        logic_type=logic_type,
        agents=agents,
        orchestration_type=orchestration_type,
        mock_level=mock_level,
        taxonomy_size=taxonomy_size,
        analysis_modes=[mode.strip() for mode in args.modes.split(",")],
        enable_advanced_tools=args.advanced,
        enable_jvm=not args.no_jvm,
        require_real_llm=require_real_gpt,
        output_format=args.format,
        output_template=getattr(args, 'template', 'default'),
        output_mode=getattr(args, 'output_mode', 'both'),
        output_path=getattr(args, 'output', None),
        require_real_gpt=require_real_gpt,
        require_real_tweety=require_real_tweety,
        require_full_taxonomy=require_full_taxonomy,
        validate_tool_calls=validate_tools,
        log_level=logging.getLevelName(logging.getLogger().level),
        enable_conversation_logging=True,
        enable_trace_validation=True,
        verbose=getattr(args, 'verbose', False)
    )
    
    # Validation de la configuration
    errors = validate_config(config)
    if errors:
        logger.warning("⚠️ Problèmes de configuration détectés:")
        for error in errors:
            logger.warning(f"  - {error}")
    
    # Log de la configuration pour transparence
    logger.info("📋 Configuration dynamique unifiée:")
    logger.info(f"  - Logique: {config.logic_type.value}")
    logger.info(f"  - Agents: {[a.value for a in config.agents]}")
    logger.info(f"  - Orchestration: {config.orchestration_type.value}")
    logger.info(f"  - Mock Level: {config.mock_level.value}")
    logger.info(f"  - Taxonomie: {config.taxonomy_size.value}")
    logger.info(f"  - Authenticité GPT: {config.require_real_gpt}")
    logger.info(f"  - Authenticité Tweety: {config.require_real_tweety}")
    logger.info(f"  - Taxonomie complète: {config.require_full_taxonomy}")
    
    return config


def convert_unified_to_pipeline_config(unified_config: UnifiedConfig) -> UnifiedAnalysisConfig:
    """
    Convertit une UnifiedConfig vers UnifiedAnalysisConfig pour compatibilité pipeline.
    
    Args:
        unified_config: Configuration unifiée nouvelle
        
    Returns:
        UnifiedAnalysisConfig: Configuration compatible avec le pipeline existant
    """
    # Détermination du mode d'orchestration pour le pipeline
    orchestration_mode = "standard"
    if unified_config.orchestration_type == OrchestrationType.CONVERSATION:
        orchestration_mode = "conversation"
    elif unified_config.orchestration_type == OrchestrationType.REAL:
        orchestration_mode = "real"
    elif unified_config.orchestration_type == OrchestrationType.UNIFIED:
        orchestration_mode = "unified"
    
    # Conversion du mock level
    use_mocks = unified_config.mock_level != MockLevel.NONE
    
    return UnifiedAnalysisConfig(
        analysis_modes=unified_config.analysis_modes,
        logic_type=unified_config.logic_type.value,
        output_format=unified_config.output_format,
        use_advanced_tools=unified_config.enable_advanced_tools,
        use_mocks=use_mocks,
        enable_jvm=unified_config.enable_jvm,
        orchestration_mode=orchestration_mode,
        enable_conversation_logging=unified_config.enable_conversation_logging
    )

def create_argument_parser() -> argparse.ArgumentParser:
    """Crée le parser d'arguments unifié."""
    parser = argparse.ArgumentParser(
        description="Analyseur de texte rhétorique unifié",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

  # Mode interactif avec sélection de source
  python analyze_text.py --interactive

  # Analyse avec source complexe chiffrée
  python analyze_text.py --source-type complex --passphrase-env

  # Analyse complète avec tous les modes
  python analyze_text.py --interactive --modes fallacies,coherence,semantic,formal,unified --format markdown

  # Mode console rapide
  python analyze_text.py --source-type simple --format console --template summary

  # Analyse batch avec fichier personnalisé
  python analyze_text.py --enc-file corpus.enc --format json --output rapport.json
        """
    )
    
    # Modes de fonctionnement
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Mode interactif avec sélection de source"
    )
    
    # Sources de données
    source_group = parser.add_argument_group("Sources de données")
    source_group.add_argument(
        "--source-type",
        choices=["simple", "complex"],
        help="Type de source prédéfinie (simple=démo, complex=corpus chiffré)"
    )
    source_group.add_argument(
        "--enc-file",
        type=str,
        help="Chemin vers un fichier .enc personnalisé"
    )
    source_group.add_argument(
        "--text-file",
        type=str,
        help="Chemin vers un fichier texte local"
    )
    source_group.add_argument(
        "--source-index",
        type=int,
        default=0,
        help="Index de la source à utiliser (pour source-type=complex)"
    )
    
    # Authentification
    auth_group = parser.add_argument_group("Authentification")
    auth_group.add_argument(
        "--passphrase",
        type=str,
        help="Phrase secrète pour déchiffrement"
    )
    auth_group.add_argument(
        "--passphrase-env",
        action="store_true",
        help="Utilise TEXT_CONFIG_PASSPHRASE depuis l'environnement"
    )
    
    # Configuration d'analyse
    analysis_group = parser.add_argument_group("Configuration d'analyse")
    analysis_group.add_argument(
        "--modes",
        type=str,
        default="fallacies,coherence,semantic",
        help="Modes d'analyse séparés par virgules (fallacies,coherence,semantic,formal,unified)"
    )
    analysis_group.add_argument(
        "--logic-type",
        choices=["fol", "pl", "first_order", "propositional", "modal"],
        default="fol",
        help="Type de logique pour l'analyse formelle (défaut: fol pour éviter échecs modal)"
    )
    analysis_group.add_argument(
        "--agents",
        type=str,
        default="informal,fol_logic,synthesis",
        help="Liste des agents séparés par virgules (informal,fol_logic,synthesis,extract,pm)"
    )
    analysis_group.add_argument(
        "--orchestration",
        choices=["unified", "conversation", "custom", "real"],
        default="unified",
        help="Type d'orchestration à utiliser"
    )
    analysis_group.add_argument(
        "--mock-level",
        choices=["none", "partial", "full"],
        default="none",
        help="Niveau de mocking (none=authentique, partial=dev, full=test)"
    )
    analysis_group.add_argument(
        "--taxonomy",
        choices=["full", "mock"],
        default="full",
        help="Taille de taxonomie (full=1000 nœuds, mock=3 nœuds)"
    )
    analysis_group.add_argument(
        "--advanced",
        action="store_true",
        help="Utilise les outils d'analyse avancés"
    )
    analysis_group.add_argument(
        "--mocks",
        action="store_true",
        help="Force l'utilisation des outils simulés (legacy - utilisez --mock-level)"
    )
    analysis_group.add_argument(
        "--no-jvm",
        action="store_true",
        help="Désactive l'initialisation JVM"
    )
    
    # Validation d'authenticité
    auth_validation_group = parser.add_argument_group("Validation d'authenticité")
    auth_validation_group.add_argument(
        "--require-real-gpt",
        action="store_true",
        default=True,
        help="Force l'utilisation de GPT-4o-mini réel (défaut: True)"
    )
    auth_validation_group.add_argument(
        "--require-real-tweety",
        action="store_true",
        default=True,
        help="Force l'utilisation de Tweety JAR authentique (défaut: True)"
    )
    auth_validation_group.add_argument(
        "--require-full-taxonomy",
        action="store_true",
        default=True,
        help="Force l'utilisation de la taxonomie 1000 nœuds (défaut: True)"
    )
    auth_validation_group.add_argument(
        "--validate-tools",
        action="store_true",
        default=True,
        help="Valide l'authenticité des tool calls (défaut: True)"
    )
    
    # Sortie et rapports
    output_group = parser.add_argument_group("Sortie et rapports")
    output_group.add_argument(
        "--format",
        choices=["console", "markdown", "json", "html"],
        default="markdown",
        help="Format de sortie du rapport"
    )
    output_group.add_argument(
        "--template",
        choices=["default", "summary", "detailed", "web"],
        default="default",
        help="Template de rapport à utiliser"
    )
    output_group.add_argument(
        "--output",
        type=str,
        help="Chemin de sortie personnalisé"
    )
    output_group.add_argument(
        "--output-mode",
        choices=["file", "console", "both"],
        default="both",
        help="Mode de sortie (fichier, console, ou les deux)"
    )
    
    # Options générales
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux (logs DEBUG)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Mode silencieux (logs WARNING uniquement)"
    )
    
    return parser

async def main():
    """
    Fonction principale du script unifié refactorisé.
    
    Cette version délègue la logique métier vers le pipeline unifié
    tout en préservant l'interface CLI complète existante.
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configuration du logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    logger.info("🚀 Démarrage de l'analyseur de texte rhétorique unifié refactorisé")
    logger.info(f"📋 Configuration CLI: {vars(args)}")
    
    try:
        # 1. Sélection de la source (conservée - logique CLI spécifique)
        logger.info("📁 Sélection de la source...")
        
        passphrase = None
        if args.passphrase:
            passphrase = args.passphrase
        elif args.passphrase_env:
            passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
        
        source_selector = UnifiedSourceSelector(passphrase=passphrase)
        
        if args.interactive:
            selected_text, description, source_type = source_selector.select_source_interactive()
        else:
            # Mode batch
            if args.enc_file:
                selected_text, description, source_type = source_selector.load_source_batch(
                    "enc_file", enc_file=args.enc_file
                )
            elif args.text_file:
                selected_text, description, source_type = source_selector.load_source_batch(
                    "text_file", text_file=args.text_file
                )
            elif args.source_type:
                selected_text, description, source_type = source_selector.load_source_batch(
                    args.source_type, source_index=args.source_index
                )
            else:
                logger.error("❌ Aucune source spécifiée. Utilisez --interactive ou --source-type")
                sys.exit(1)
        
        logger.info(f"✅ Source chargée: {description}")
        
        # 2. Création de la configuration dynamique unifiée depuis les arguments CLI
        unified_config = create_unified_config_from_args(args)
        
        # 3. Conversion vers l'interface pipeline existante (compatibilité)
        config = convert_unified_to_pipeline_config(unified_config)
        
        # 3. Préparation des informations de source
        source_info = {
            "description": description,
            "type": source_type,
            "cli_args": vars(args)  # Préservation du contexte CLI
        }
        
        # 4. DÉLÉGATION vers le pipeline unifié refactorisé
        logger.info("🔄 Délégation vers le pipeline unifié d'analyse...")
        results = await run_unified_text_analysis_pipeline(
            text=selected_text,
            source_info=source_info,
            config=config,
            log_level=logging.getLevelName(logging.getLogger().level)
        )
        
        if not results:
            logger.error("❌ Le pipeline unifié n'a retourné aucun résultat")
            sys.exit(1)
        
        logger.info("✅ Analyse pipeline unifiée terminée avec succès")
        
        # 5. Génération du rapport (conservée - logique CLI spécifique)
        logger.info("📝 Génération du rapport via générateur unifié...")
        report_generator = UnifiedReportGenerator()
        
        # Adaptation des résultats pour le générateur legacy
        adapted_results = {
            **results,
            "metadata": {
                **results.get("metadata", {}),
                "cli_interface": "unified_analyze_text_v2.0",
                "pipeline_version": results.get("metadata", {}).get("pipeline_version", "unified_v1.0")
            }
        }
        
        report = report_generator.generate_report(
            analysis_data=adapted_results,
            format_type=args.format,
            output_mode=args.output_mode,
            template=args.template,
            output_path=args.output
        )
        
        # 6. Affichage des logs conversationnels si disponibles
        conversation_log = results.get("conversation_log", {})
        if conversation_log and args.verbose:
            logger.info("💬 Log conversationnel disponible:")
            messages = conversation_log.get("messages", [])
            if messages:
                logger.info(f"   - {len(messages)} messages échangés")
            tools = conversation_log.get("tool_calls", [])
            if tools:
                logger.info(f"   - {len(tools)} appels d'outils")
        
        logger.info("✅ Analyse complète avec pipeline unifié terminée avec succès!")
        
    except KeyboardInterrupt:
        logger.info("❌ Analyse interrompue par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'analyse: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Configuration spécifique Windows si nécessaire
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())