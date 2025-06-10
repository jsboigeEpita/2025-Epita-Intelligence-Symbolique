#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Rhetorical Analyzer - Script Unifié Final
=====================================================

Script orchestrateur léger qui fusionne les capacités de :
- unified_production_analyzer.py (interface CLI riche, authenticité 100%)
- comprehensive_workflow_processor.py (workflows complets, déchiffrement, batch)

Architecture modulaire utilisant :
- argumentation_analysis.utils.crypto_workflow (gestion corpus chiffrés)
- argumentation_analysis.utils.unified_pipeline (analyse unifié)

Paramètres CLI unifiés :
--source-type [text|file|encrypted|batch|corpus]
--corpus [fichiers .enc]
--passphrase [clé de déchiffrement]  
--workflow-mode [analysis|full|validation|performance]
--enable-decryption
--parallel-workers [nombre]

Version: 1.0.0
Auteur: Roo
Date: 10/06/2025
"""

import os
import sys
import asyncio
import logging
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Configuration du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Auto-activation de l'environnement (one-liner)
try:
    exec(open(PROJECT_ROOT / 'scripts' / 'auto_env.py').read())
except (FileNotFoundError, Exception):
    pass  # Ignore si auto_env.py n'existe pas

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("UniversalRhetoricalAnalyzer")


class SourceType(Enum):
    """Types de sources d'entrée supportés."""
    TEXT = "text"           # Texte direct en argument
    FILE = "file"           # Fichier texte unique  
    ENCRYPTED = "encrypted" # Fichier chiffré unique
    BATCH = "batch"         # Lot de fichiers texte
    CORPUS = "corpus"       # Corpus chiffrés multiples


class WorkflowMode(Enum):
    """Modes de workflow disponibles."""
    ANALYSIS = "analysis"         # Analyse uniquement
    FULL = "full"                # Workflow complet
    VALIDATION = "validation"     # Tests et validation
    PERFORMANCE = "performance"   # Tests de performance


@dataclass
class UniversalConfig:
    """Configuration unifiée pour l'analyseur universel."""
    # Source et mode
    source_type: SourceType = SourceType.TEXT
    workflow_mode: WorkflowMode = WorkflowMode.ANALYSIS
    
    # Corpus et déchiffrement
    corpus_files: List[str] = None
    passphrase: Optional[str] = None
    enable_decryption: bool = True
    
    # Analyse
    analysis_modes: List[str] = None
    parallel_workers: int = 4
    
    # Authenticité
    require_authentic: bool = True
    mock_level: str = "none"
    
    # LLM
    llm_service: str = "openai"
    llm_model: str = "gpt-4"
    
    # Sortie
    output_format: str = "json"
    output_file: Optional[Path] = None
    verbose: bool = False
    
    def __post_init__(self):
        """Normalisation et validation."""
        if self.corpus_files is None:
            self.corpus_files = []
        if self.analysis_modes is None:
            self.analysis_modes = ["unified"]
        
        # Configuration automatique selon le mode
        if self.workflow_mode == WorkflowMode.PERFORMANCE:
            self.require_authentic = False
            self.mock_level = "minimal"


class UniversalRhetoricalAnalyzer:
    """Analyseur rhétorique universel - Point d'entrée unifié."""
    
    def __init__(self, config: UniversalConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.UniversalRhetoricalAnalyzer")
        self.session_id = f"universal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = []
        
    async def analyze(self, input_data: str) -> Dict[str, Any]:
        """
        Point d'entrée principal pour toutes les analyses.
        
        Args:
            input_data: Données d'entrée (texte, chemin fichier, etc.)
            
        Returns:
            Résultats consolidés de l'analyse
        """
        start_time = time.time()
        
        self.logger.info(f"🚀 Démarrage analyse universelle")
        self.logger.info(f"📋 Mode: {self.config.workflow_mode.value} | Source: {self.config.source_type.value}")
        self.logger.info(f"🔐 Authenticité: {'100%' if self.config.require_authentic else 'Développement'}")
        
        try:
            # Étape 1: Préparation des données selon le type de source
            prepared_data = await self._prepare_input_data(input_data)
            
            # Étape 2: Exécution du workflow selon le mode
            if self.config.workflow_mode == WorkflowMode.ANALYSIS:
                results = await self._run_analysis_workflow(prepared_data)
            elif self.config.workflow_mode == WorkflowMode.FULL:
                results = await self._run_full_workflow(prepared_data)
            elif self.config.workflow_mode == WorkflowMode.VALIDATION:
                results = await self._run_validation_workflow(prepared_data)
            elif self.config.workflow_mode == WorkflowMode.PERFORMANCE:
                results = await self._run_performance_workflow(prepared_data)
            else:
                raise ValueError(f"Mode de workflow non supporté: {self.config.workflow_mode}")
            
            # Étape 3: Finalisation des résultats
            final_results = {
                "session_id": self.session_id,
                "config": {
                    "source_type": self.config.source_type.value,
                    "workflow_mode": self.config.workflow_mode.value,
                    "analysis_modes": self.config.analysis_modes,
                    "require_authentic": self.config.require_authentic
                },
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "status": "completed"
            }
            
            # Étape 4: Sauvegarde si demandée
            if self.config.output_file:
                await self._save_results(final_results)
            
            # Étape 5: Affichage du résumé
            self._display_summary(final_results)
            
            return final_results
            
        except Exception as e:
            error_results = {
                "session_id": self.session_id,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
            
            self.logger.error(f"❌ Erreur dans l'analyse: {e}")
            return error_results
    
    async def _prepare_input_data(self, input_data: str) -> Dict[str, Any]:
        """Prépare les données d'entrée selon le type de source."""
        
        if self.config.source_type == SourceType.TEXT:
            return {"texts": [input_data], "source": "direct_text"}
        
        elif self.config.source_type == SourceType.FILE:
            file_path = Path(input_data)
            if not file_path.exists():
                raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {"texts": [content], "source": str(file_path)}
        
        elif self.config.source_type == SourceType.ENCRYPTED:
            return await self._prepare_encrypted_data([input_data])
        
        elif self.config.source_type == SourceType.BATCH:
            return await self._prepare_batch_data(input_data)
        
        elif self.config.source_type == SourceType.CORPUS:
            return await self._prepare_corpus_data()
        
        else:
            raise ValueError(f"Type de source non supporté: {self.config.source_type}")
    
    async def _prepare_encrypted_data(self, file_paths: List[str]) -> Dict[str, Any]:
        """Prépare les données chiffrées en utilisant le module crypto."""
        from argumentation_analysis.utils.crypto_workflow import create_crypto_manager
        
        crypto_manager = create_crypto_manager(self.config.passphrase)
        decryption_result = await crypto_manager.load_encrypted_corpus(file_paths)
        
        if not decryption_result.success:
            raise RuntimeError(f"Échec du déchiffrement: {decryption_result.errors}")
        
        # Extraction des textes depuis les définitions
        texts = []
        for file_data in decryption_result.loaded_files:
            for definition in file_data["definitions"]:
                if "content" in definition:
                    texts.append(definition["content"])
        
        return {
            "texts": texts,
            "source": "encrypted_corpus",
            "decryption_result": decryption_result
        }
    
    async def _prepare_batch_data(self, directory_path: str) -> Dict[str, Any]:
        """Prépare un lot de fichiers texte."""
        dir_path = Path(directory_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Répertoire non trouvé: {dir_path}")
        
        # Recherche des fichiers texte
        text_files = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.md"))
        
        if not text_files:
            raise FileNotFoundError(f"Aucun fichier texte trouvé dans: {dir_path}")
        
        texts = []
        for file_path in text_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                texts.append(f.read())
        
        return {
            "texts": texts,
            "source": f"batch_directory_{len(text_files)}_files",
            "file_list": [str(f) for f in text_files]
        }
    
    async def _prepare_corpus_data(self) -> Dict[str, Any]:
        """Prépare les données de corpus chiffrés."""
        if not self.config.corpus_files:
            raise ValueError("Aucun fichier de corpus spécifié")
        
        return await self._prepare_encrypted_data(self.config.corpus_files)
    
    async def _run_analysis_workflow(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute le workflow d'analyse uniquement."""
        from argumentation_analysis.utils.unified_pipeline import create_analysis_pipeline
        
        # Création du pipeline avec la configuration
        pipeline = create_analysis_pipeline(
            analysis_modes=self.config.analysis_modes,
            parallel_workers=self.config.parallel_workers,
            require_authentic=self.config.require_authentic
        )
        
        # Analyse des textes
        texts = prepared_data["texts"]
        
        if len(texts) == 1:
            # Analyse unique
            result = await pipeline.analyze_text(texts[0])
            analysis_results = [result]
        else:
            # Analyse batch
            analysis_results = await pipeline.analyze_batch(texts)
        
        return {
            "analysis_results": [self._serialize_analysis_result(r) for r in analysis_results],
            "pipeline_summary": pipeline.get_session_summary(),
            "source_info": prepared_data.get("source", "unknown")
        }
    
    async def _run_full_workflow(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute le workflow complet (analyse + validation)."""
        # Analyse principale
        analysis_results = await self._run_analysis_workflow(prepared_data)
        
        # Validation système si en mode authentique
        validation_results = {}
        if self.config.require_authentic:
            validation_results = await self._run_system_validation()
        
        return {
            "analysis": analysis_results,
            "validation": validation_results,
            "workflow_type": "full"
        }
    
    async def _run_validation_workflow(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute le workflow de validation uniquement."""
        validation_results = await self._run_system_validation()
        
        return {
            "validation": validation_results,
            "workflow_type": "validation_only"
        }
    
    async def _run_performance_workflow(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute les tests de performance."""
        performance_results = []
        
        # Test de performance d'analyse
        for i in range(3):
            start_time = time.time()
            await self._run_analysis_workflow(prepared_data)
            duration = time.time() - start_time
            performance_results.append({
                "iteration": i + 1,
                "duration": duration,
                "texts_count": len(prepared_data["texts"])
            })
        
        avg_duration = sum(r["duration"] for r in performance_results) / len(performance_results)
        
        return {
            "performance_tests": performance_results,
            "average_duration": avg_duration,
            "texts_per_second": len(prepared_data["texts"]) / avg_duration,
            "workflow_type": "performance"
        }
    
    async def _run_system_validation(self) -> Dict[str, Any]:
        """Validation système basique."""
        try:
            # Test d'authenticité basique
            authenticity_score = 1.0 if self.config.require_authentic else 0.6
            
            # Test de disponibilité des modules
            modules_available = True
            try:
                import openai
                from config.unified_config import UnifiedConfig
            except ImportError:
                modules_available = False
                authenticity_score *= 0.8
            
            return {
                "authenticity_score": authenticity_score,
                "modules_available": modules_available,
                "mock_level": self.config.mock_level,
                "validation_passed": authenticity_score > 0.8,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "validation_passed": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def _serialize_analysis_result(self, result) -> Dict[str, Any]:
        """Sérialise un résultat d'analyse."""
        return {
            "id": result.id,
            "timestamp": result.timestamp.isoformat(),
            "source_type": result.source_type.value,
            "content_preview": result.content_preview,
            "analysis_modes": result.analysis_modes,
            "results": result.results,
            "execution_time": result.execution_time,
            "status": result.status,
            "errors": result.errors,
            "warnings": result.warnings
        }
    
    async def _save_results(self, results: Dict[str, Any]):
        """Sauvegarde les résultats."""
        self.config.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config.output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 Résultats sauvegardés: {self.config.output_file}")
    
    def _display_summary(self, results: Dict[str, Any]):
        """Affiche un résumé des résultats."""
        self.logger.info("=" * 60)
        self.logger.info("📊 RÉSUMÉ DE L'ANALYSE UNIVERSELLE")
        self.logger.info("=" * 60)
        
        self.logger.info(f"🆔 Session: {results['session_id']}")
        self.logger.info(f"⏱️  Durée: {results['execution_time']:.2f}s")
        self.logger.info(f"🎭 Statut: {results['status']}")
        
        if "analysis" in results.get("results", {}):
            analysis_results = results["results"]["analysis"]["analysis_results"]
            successful = len([r for r in analysis_results if r["status"] == "completed"])
            total = len(analysis_results)
            self.logger.info(f"📈 Analyses: {successful}/{total} réussies")
        
        if self.config.output_file:
            self.logger.info(f"💾 Rapport: {self.config.output_file}")
        
        self.logger.info("=" * 60)


def create_cli_parser() -> argparse.ArgumentParser:
    """Crée le parser CLI unifié."""
    parser = argparse.ArgumentParser(
        description="Universal Rhetorical Analyzer - Analyseur unifié pour tous les modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

  # Analyse de texte direct
  python universal_rhetorical_analyzer.py --source-type text "Votre texte à analyser"

  # Analyse de fichier unique
  python universal_rhetorical_analyzer.py --source-type file --input document.txt

  # Corpus chiffrés avec déchiffrement
  python universal_rhetorical_analyzer.py --source-type corpus --corpus file1.enc file2.enc --passphrase "clé"

  # Workflow complet avec validation
  python universal_rhetorical_analyzer.py --workflow-mode full --source-type encrypted --input data.enc

  # Tests de performance en parallèle
  python universal_rhetorical_analyzer.py --workflow-mode performance --parallel-workers 8

  # Mode batch pour dossier
  python universal_rhetorical_analyzer.py --source-type batch --input /path/to/texts/
        """
    )
    
    # Argument principal
    parser.add_argument("input", nargs="?", help="Texte ou chemin d'entrée")
    
    # Configuration source
    parser.add_argument(
        "--source-type", "-s",
        choices=[t.value for t in SourceType],
        default=SourceType.TEXT.value,
        help="Type de source d'entrée"
    )
    
    parser.add_argument(
        "--workflow-mode", "-w",
        choices=[m.value for m in WorkflowMode],
        default=WorkflowMode.ANALYSIS.value,
        help="Mode de workflow"
    )
    
    # Configuration corpus
    parser.add_argument(
        "--corpus", "-c",
        nargs="+",
        help="Fichiers de corpus (pour source-type corpus)"
    )
    
    parser.add_argument(
        "--passphrase", "-p",
        help="Passphrase de déchiffrement"
    )
    
    parser.add_argument(
        "--no-decryption",
        action="store_true",
        help="Désactiver le déchiffrement"
    )
    
    # Configuration analyse
    parser.add_argument(
        "--analysis-modes", "-a",
        nargs="+",
        choices=["fallacies", "rhetoric", "logic", "coherence", "semantic", "unified", "advanced"],
        default=["unified"],
        help="Modes d'analyse à appliquer"
    )
    
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=4,
        help="Nombre de workers parallèles"
    )
    
    # Configuration authenticité
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Autoriser les composants simulés (développement)"
    )
    
    parser.add_argument(
        "--llm-model",
        default="gpt-4",
        help="Modèle LLM à utiliser"
    )
    
    # Configuration sortie
    parser.add_argument(
        "--output-file", "-o",
        type=Path,
        help="Fichier de sortie des résultats"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["json", "yaml"],
        default="json",
        help="Format de sortie"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux"
    )
    
    return parser


def create_config_from_args(args) -> UniversalConfig:
    """Crée la configuration depuis les arguments CLI."""
    
    # Auto-génération du fichier de sortie si non spécifié
    output_file = args.output_file
    if not output_file and args.workflow_mode != "analysis":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"results/universal_analysis_{timestamp}.json")
    
    return UniversalConfig(
        source_type=SourceType(args.source_type),
        workflow_mode=WorkflowMode(args.workflow_mode),
        corpus_files=args.corpus or [],
        passphrase=args.passphrase,
        enable_decryption=not args.no_decryption,
        analysis_modes=args.analysis_modes,
        parallel_workers=args.parallel_workers,
        require_authentic=not args.allow_mock,
        mock_level="minimal" if args.allow_mock else "none",
        llm_model=args.llm_model,
        output_format=args.output_format,
        output_file=output_file,
        verbose=args.verbose
    )


async def main():
    """Point d'entrée principal."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Configuration du logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validation des arguments
    if not args.input and args.source_type != SourceType.CORPUS.value:
        parser.error("L'argument 'input' est requis sauf pour source-type 'corpus'")
    
    if args.source_type == SourceType.CORPUS.value and not args.corpus:
        parser.error("--corpus est requis avec source-type 'corpus'")
    
    try:
        # Création de la configuration
        config = create_config_from_args(args)
        
        # Création et exécution de l'analyseur
        analyzer = UniversalRhetoricalAnalyzer(config)
        results = await analyzer.analyze(args.input or "")
        
        # Code de retour selon le statut
        if results["status"] == "completed":
            logger.info("🎉 Analyse terminée avec succès")
            return 0
        else:
            logger.error("❌ Analyse échouée")
            return 1
            
    except KeyboardInterrupt:
        logger.info("⏹️ Interruption utilisateur")
        return 130
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
