# =====================================================================================
# VÉRIFICATION DE LA VERSION DE SEMANTIC-KERNEL
# Le projet requiert une version moderne et agentique. Cette importation précoce
# garantit que le programme s'arrête immédiatement si la version est obsolète.
# =====================================================================================
try:
    from argumentation_analysis.utils import version_validator
except ImportError as e:
    import sys
    print(f"ERREUR CRITIQUE: {e}", file=sys.stderr)
    sys.exit(1)
# =====================================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pipeline Unifié - Point d'Entrée Principal avec Orchestration Étendue
====================================================================

Ce module sert de point d'entrée principal pour l'analyse argumentative,
intégrant à la fois le pipeline original et le nouveau pipeline d'orchestration
avec l'architecture hiérarchique complète.

MIGRATION VERS L'ORCHESTRATION ÉTENDUE :
Ce fichier facilite la transition depuis l'API existante vers les nouvelles
capacités d'orchestration hiérarchique et spécialisée.

Usage recommandé :
- Pour une compatibilité maximale : utiliser les fonctions de ce module
- Pour les nouvelles fonctionnalités : utiliser directement unified_orchestration_pipeline
- Pour des performances optimales : utiliser l'orchestration automatique

Version: 2.0.0 (avec orchestration étendue)
Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import asyncio
import logging
import warnings
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Imports du pipeline original
try:
    from argumentation_analysis.pipelines.unified_text_analysis import (
        run_unified_text_analysis_pipeline,
        UnifiedAnalysisConfig,
        create_unified_config_from_legacy
    )
    ORIGINAL_PIPELINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Pipeline original non disponible: {e}")
    ORIGINAL_PIPELINE_AVAILABLE = False

# Imports du nouveau pipeline d'orchestration
try:
    from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
        run_unified_orchestration_pipeline,
        run_extended_unified_analysis,
        compare_orchestration_approaches,
        ExtendedOrchestrationConfig,
        OrchestrationMode,
        AnalysisType,
        create_extended_config_from_params
    )
    ORCHESTRATION_PIPELINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Pipeline d'orchestration non disponible: {e}")
    ORCHESTRATION_PIPELINE_AVAILABLE = False

logger = logging.getLogger("UnifiedPipeline")


class PipelineMode:
    """Modes de pipeline disponibles."""
    
    ORIGINAL = "original"           # Pipeline original seulement
    ORCHESTRATION = "orchestration" # Pipeline d'orchestration seulement
    AUTO = "auto"                   # Sélection automatique
    HYBRID = "hybrid"               # Exécution hybride avec comparaison


async def analyze_text(
    text: str,
    mode: str = "auto",
    analysis_type: str = "comprehensive",
    orchestration_mode: str = "auto_select",
    use_mocks: bool = False,
    source_info: Optional[str] = None,
    enable_orchestration: bool = True,
    enable_comparison: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Fonction d'entrée principale pour l'analyse argumentative unifiée.
    
    Cette fonction intelligente sélectionne automatiquement le meilleur pipeline
    selon la disponibilité des composants et les paramètres fournis.
    
    Args:
        text: Texte à analyser
        mode: Mode de pipeline ("original", "orchestration", "auto", "hybrid")
        analysis_type: Type d'analyse ("comprehensive", "rhetorical", "logical", etc.)
        orchestration_mode: Mode d'orchestration ("auto_select", "hierarchical", etc.)
        use_mocks: Utilisation des mocks pour les tests
        source_info: Information sur la source du texte
        enable_orchestration: Active l'orchestration étendue si disponible
        enable_comparison: Active la comparaison entre pipelines
        **kwargs: Paramètres additionnels
    
    Returns:
        Dictionnaire des résultats d'analyse avec métadonnées de pipeline
    """
    start_time = datetime.now()
    
    logger.info(f"[UNIFIED] Analyse démarrée - Mode: {mode}, Type: {analysis_type}")
    
    # Détection automatique du meilleur pipeline
    if mode == "auto":
        mode = _detect_best_pipeline_mode(enable_orchestration)
        logger.info(f"[UNIFIED] Mode détecté automatiquement: {mode}")
    
    # Validation des paramètres
    if not text or not text.strip():
        raise ValueError("Texte vide ou invalide fourni pour l'analyse")
    
    # Structure de résultats unifiée
    results = {
        "metadata": {
            "analysis_timestamp": start_time.isoformat(),
            "pipeline_version": "unified_2.0_with_orchestration",
            "pipeline_mode": mode,
            "analysis_type": analysis_type,
            "orchestration_mode": orchestration_mode,
            "text_length": len(text),
            "source_info": source_info,
            "orchestration_available": ORCHESTRATION_PIPELINE_AVAILABLE,
            "original_available": ORIGINAL_PIPELINE_AVAILABLE
        },
        "pipeline_results": {},
        "comparison": {},
        "recommendations": [],
        "execution_time": 0,
        "status": "in_progress"
    }
    
    try:
        # Exécution selon le mode sélectionné
        if mode == "orchestration":
            results = await _run_orchestration_pipeline(text, analysis_type, orchestration_mode, use_mocks, source_info, results, **kwargs)
        
        elif mode == "original":
            results = await _run_original_pipeline(text, analysis_type, use_mocks, source_info, results, **kwargs)
        
        elif mode == "hybrid":
            results = await _run_hybrid_pipeline(text, analysis_type, orchestration_mode, use_mocks, source_info, results, **kwargs)
        
        else:
            # Fallback vers le mode disponible
            if ORCHESTRATION_PIPELINE_AVAILABLE:
                results = await _run_orchestration_pipeline(text, analysis_type, orchestration_mode, use_mocks, source_info, results, **kwargs)
            elif ORIGINAL_PIPELINE_AVAILABLE:
                results = await _run_original_pipeline(text, analysis_type, use_mocks, source_info, results, **kwargs)
            else:
                raise RuntimeError("Aucun pipeline disponible")
        
        # Comparaison optionnelle des pipelines
        if enable_comparison and ORCHESTRATION_PIPELINE_AVAILABLE:
            comparison_results = await _compare_pipelines(text, analysis_type, use_mocks)
            results["comparison"] = comparison_results
        
        # Génération des recommandations
        results["recommendations"] = _generate_unified_recommendations(results)
        
        results["status"] = "success"
        
    except Exception as e:
        logger.error(f"[UNIFIED] Erreur lors de l'analyse: {e}")
        results["status"] = "error"
        results["error"] = str(e)
        
        # Tentative de fallback en cas d'erreur
        if mode != "original" and ORIGINAL_PIPELINE_AVAILABLE:
            logger.info("[UNIFIED] Tentative de fallback vers le pipeline original...")
            try:
                fallback_results = await _run_original_pipeline(text, analysis_type, use_mocks, source_info, {}, **kwargs)
                results["pipeline_results"]["fallback"] = fallback_results["pipeline_results"]["original"]
                results["status"] = "partial_success"
                results["fallback_used"] = True
            except Exception as fallback_error:
                logger.error(f"[UNIFIED] Échec du fallback: {fallback_error}")
    
    # Finalisation
    results["execution_time"] = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"[UNIFIED] Analyse terminée - Statut: {results['status']}, Temps: {results['execution_time']:.2f}s")
    
    return results


def _detect_best_pipeline_mode(enable_orchestration: bool) -> str:
    """Détecte automatiquement le meilleur mode de pipeline."""
    if enable_orchestration and ORCHESTRATION_PIPELINE_AVAILABLE:
        return "orchestration"
    elif ORIGINAL_PIPELINE_AVAILABLE:
        return "original"
    else:
        raise RuntimeError("Aucun pipeline disponible")


async def _run_orchestration_pipeline(
    text: str, 
    analysis_type: str, 
    orchestration_mode: str, 
    use_mocks: bool, 
    source_info: Optional[str],
    results: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Exécute le pipeline d'orchestration étendu."""
    logger.info("[UNIFIED] Exécution du pipeline d'orchestration étendu...")
    
    if not ORCHESTRATION_PIPELINE_AVAILABLE:
        raise RuntimeError("Pipeline d'orchestration non disponible")
    
    # Configuration étendue
    config = create_extended_config_from_params(
        orchestration_mode=orchestration_mode,
        analysis_type=analysis_type,
        use_mocks=use_mocks,
        **kwargs
    )
    
    # Exécution
    orchestration_results = await run_unified_orchestration_pipeline(text, config, source_info)
    
    # Intégration des résultats
    results["pipeline_results"]["orchestration"] = orchestration_results
    
    # Copier les champs principaux pour compatibilité
    for key in ["informal_analysis", "formal_analysis", "unified_analysis", "orchestration_analysis"]:
        if key in orchestration_results:
            results[key] = orchestration_results[key]
    
    # Copier les nouveaux champs d'orchestration
    for key in ["strategic_analysis", "tactical_coordination", "operational_results", "specialized_orchestration"]:
        if key in orchestration_results:
            results[key] = orchestration_results[key]
    
    return results


async def _run_original_pipeline(
    text: str, 
    analysis_type: str, 
    use_mocks: bool, 
    source_info: Optional[str],
    results: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Exécute le pipeline original."""
    logger.info("[UNIFIED] Exécution du pipeline original...")
    
    if not ORIGINAL_PIPELINE_AVAILABLE:
        raise RuntimeError("Pipeline original non disponible")
    
    # Configuration originale
    config = create_unified_config_from_legacy(
        mode=_map_analysis_type_to_legacy_mode(analysis_type),
        use_mocks=use_mocks,
        **kwargs
    )
    
    # Exécution
    original_results = await run_unified_text_analysis_pipeline(text, config, source_info)
    
    # Intégration des résultats
    results["pipeline_results"]["original"] = original_results
    
    # Copier les champs principaux pour compatibilité
    for key in ["informal_analysis", "formal_analysis", "unified_analysis", "orchestration_analysis"]:
        if key in original_results:
            results[key] = original_results[key]
    
    return results


async def _run_hybrid_pipeline(
    text: str, 
    analysis_type: str, 
    orchestration_mode: str, 
    use_mocks: bool, 
    source_info: Optional[str],
    results: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Exécute les deux pipelines et compare les résultats."""
    logger.info("[UNIFIED] Exécution du pipeline hybride...")
    
    # Exécuter les deux pipelines si disponibles
    if ORCHESTRATION_PIPELINE_AVAILABLE:
        try:
            results = await _run_orchestration_pipeline(text, analysis_type, orchestration_mode, use_mocks, source_info, results, **kwargs)
        except Exception as e:
            logger.warning(f"[UNIFIED] Échec pipeline orchestration: {e}")
    
    if ORIGINAL_PIPELINE_AVAILABLE:
        try:
            results = await _run_original_pipeline(text, analysis_type, use_mocks, source_info, results, **kwargs)
        except Exception as e:
            logger.warning(f"[UNIFIED] Échec pipeline original: {e}")
    
    # Synthèse hybride
    results = _synthesize_hybrid_results(results)
    
    return results


def _synthesize_hybrid_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Synthétise les résultats des deux pipelines."""
    orchestration_results = results["pipeline_results"].get("orchestration", {})
    original_results = results["pipeline_results"].get("original", {})
    
    # Prendre les meilleurs résultats de chaque pipeline
    if orchestration_results and original_results:
        # Combiner les analyses informelles
        orch_informal = orchestration_results.get("informal_analysis", {})
        orig_informal = original_results.get("informal_analysis", {})
        
        if orch_informal and orig_informal:
            orch_fallacies = orch_informal.get("fallacies", [])
            orig_fallacies = orig_informal.get("fallacies", [])
            
            # Fusionner les sophismes détectés (sans doublons)
            all_fallacies = list(orch_fallacies)
            for fallacy in orig_fallacies:
                fallacy_type = fallacy.get("type", "")
                if not any(f.get("type") == fallacy_type for f in all_fallacies):
                    all_fallacies.append(fallacy)
            
            results["informal_analysis"] = {
                "fallacies": all_fallacies,
                "summary": {
                    "total_fallacies": len(all_fallacies),
                    "orchestration_count": len(orch_fallacies),
                    "original_count": len(orig_fallacies),
                    "source": "hybrid_synthesis"
                }
            }
    
    return results


async def _compare_pipelines(text: str, analysis_type: str, use_mocks: bool) -> Dict[str, Any]:
    """Compare les performances des différents pipelines."""
    logger.info("[UNIFIED] Comparaison des pipelines...")
    
    comparison = {
        "comparison_timestamp": datetime.now().isoformat(),
        "approaches_tested": [],
        "performance_metrics": {},
        "recommendations": []
    }
    
    try:
        if ORCHESTRATION_PIPELINE_AVAILABLE:
            approaches = ["pipeline", "hierarchical", "specialized"]
            comparison_results = await compare_orchestration_approaches(text, approaches)
            
            comparison["approaches_tested"] = approaches
            comparison["performance_metrics"] = comparison_results.get("comparison", {})
            comparison["detailed_results"] = comparison_results.get("approaches", {})
            
            # Recommandations de comparaison
            if "fastest" in comparison["performance_metrics"]:
                comparison["recommendations"].append(
                    f"Approche la plus rapide: {comparison['performance_metrics']['fastest']}"
                )
    
    except Exception as e:
        logger.warning(f"[UNIFIED] Erreur comparaison pipelines: {e}")
        comparison["error"] = str(e)
    
    return comparison


def _map_analysis_type_to_legacy_mode(analysis_type: str) -> str:
    """Mappe les nouveaux types d'analyse vers les modes legacy."""
    mapping = {
        "comprehensive": "unified",
        "rhetorical": "informal",
        "logical": "formal",
        "investigative": "unified",
        "fallacy_focused": "informal",
        "argument_structure": "formal",
        "debate_analysis": "unified",
        "custom": "unified"
    }
    return mapping.get(analysis_type, "unified")


def _generate_unified_recommendations(results: Dict[str, Any]) -> List[str]:
    """Génère des recommandations basées sur les résultats unifiés."""
    recommendations = []
    
    # Recommandations basées sur le mode utilisé
    mode = results["metadata"]["pipeline_mode"]
    
    if mode == "orchestration":
        if "strategic_analysis" in results:
            recommendations.append("Architecture hiérarchique utilisée - Analyse stratégique disponible")
        if "specialized_orchestration" in results:
            orchestrator = results["specialized_orchestration"].get("orchestrator_used", "")
            if orchestrator:
                recommendations.append(f"Orchestrateur spécialisé '{orchestrator}' utilisé avec succès")
    
    elif mode == "hybrid":
        recommendations.append("Analyse hybride complétée - Comparaison des approches disponible")
    
    # Recommandations basées sur les performances
    exec_time = results.get("execution_time", 0)
    if exec_time > 10:
        recommendations.append("Temps d'exécution élevé - Considérer l'optimisation ou les mocks")
    elif exec_time < 1:
        recommendations.append("Analyse rapide complétée - Performance optimale")
    
    # Recommandations basées sur les erreurs
    if results.get("status") == "error":
        recommendations.append("Erreur détectée - Vérifier la configuration et les dépendances")
    elif results.get("fallback_used"):
        recommendations.append("Fallback utilisé - Considérer la résolution des problèmes du pipeline principal")
    
    # Recommandation par défaut
    if not recommendations:
        recommendations.append("Analyse unifiée complétée avec succès")
    
    return recommendations


# ==========================================
# FONCTIONS DE COMPATIBILITÉ ET MIGRATION
# ==========================================

async def run_analysis(text: str, **kwargs) -> Dict[str, Any]:
    """
    Fonction de compatibilité simple pour l'analyse.
    
    Cette fonction maintient la compatibilité avec l'API la plus simple
    tout en utilisant les nouvelles capacités d'orchestration.
    """
    return await analyze_text(text, **kwargs)


async def run_enhanced_analysis(
    text: str,
    enable_hierarchical: bool = True,
    enable_specialized: bool = True,
    orchestration_mode: str = "auto_select",
    **kwargs
) -> Dict[str, Any]:
    """
    Fonction pour l'analyse avancée avec contrôle fin des capacités d'orchestration.
    
    Args:
        text: Texte à analyser
        enable_hierarchical: Active l'architecture hiérarchique
        enable_specialized: Active les orchestrateurs spécialisés
        orchestration_mode: Mode d'orchestration spécifique
        **kwargs: Paramètres additionnels
    """
    if enable_hierarchical or enable_specialized:
        return await analyze_text(
            text, 
            mode="orchestration",
            orchestration_mode=orchestration_mode,
            **kwargs
        )
    else:
        return await analyze_text(text, mode="original", **kwargs)


def get_available_features() -> Dict[str, bool]:
    """
    Retourne les fonctionnalités disponibles dans l'installation actuelle.
    
    Returns:
        Dictionnaire des fonctionnalités disponibles
    """
    return {
        "original_pipeline": ORIGINAL_PIPELINE_AVAILABLE,
        "orchestration_pipeline": ORCHESTRATION_PIPELINE_AVAILABLE,
        "hierarchical_architecture": ORCHESTRATION_PIPELINE_AVAILABLE,
        "specialized_orchestrators": ORCHESTRATION_PIPELINE_AVAILABLE,
        "service_manager": ORCHESTRATION_PIPELINE_AVAILABLE,
        "communication_middleware": ORCHESTRATION_PIPELINE_AVAILABLE,
        "orchestration_comparison": ORCHESTRATION_PIPELINE_AVAILABLE,
        "hybrid_mode": ORIGINAL_PIPELINE_AVAILABLE and ORCHESTRATION_PIPELINE_AVAILABLE
    }


def print_feature_status():
    """Affiche le statut des fonctionnalités disponibles."""
    features = get_available_features()
    
    print("=== STATUT DES FONCTIONNALITÉS DU PIPELINE UNIFIÉ ===")
    print()
    
    for feature, available in features.items():
        status = "✅ Disponible" if available else "❌ Non disponible"
        print(f"  {feature:30} {status}")
    
    print()
    
    if features["orchestration_pipeline"]:
        print("🚀 Pipeline d'orchestration étendu DISPONIBLE")
        print("   → Architecture hiérarchique complète")
        print("   → Orchestrateurs spécialisés")
        print("   → Service manager centralisé")
    else:
        print("⚠️ Pipeline d'orchestration étendu NON DISPONIBLE")
        print("   → Utilisation du pipeline original uniquement")
    
    if features["hybrid_mode"]:
        print("🔄 Mode hybride DISPONIBLE")
        print("   → Comparaison automatique des approches")
    
    print()


# Message de migration pour les utilisateurs
_MIGRATION_MESSAGE_SHOWN = False

def _show_migration_message():
    """Affiche un message de migration vers les nouvelles fonctionnalités."""
    global _MIGRATION_MESSAGE_SHOWN
    
    if not _MIGRATION_MESSAGE_SHOWN and ORCHESTRATION_PIPELINE_AVAILABLE:
        warnings.warn(
            "Nouvelles fonctionnalités d'orchestration disponibles ! "
            "Utilisez mode='orchestration' ou enable_orchestration=True pour "
            "accéder à l'architecture hiérarchique et aux orchestrateurs spécialisés. "
            "Consultez la documentation dans docs/unified_orchestration_architecture.md",
            UserWarning,
            stacklevel=3
        )
        _MIGRATION_MESSAGE_SHOWN = True


# ==========================================
# POINT D'ENTRÉE PRINCIPAL
# ==========================================

if __name__ == "__main__":
    # Script de démonstration rapide
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline Unifié d'Analyse Argumentative")
    parser.add_argument("text", help="Texte à analyser")
    parser.add_argument("--mode", choices=["auto", "original", "orchestration", "hybrid"], 
                       default="auto", help="Mode de pipeline")
    parser.add_argument("--type", default="comprehensive", help="Type d'analyse")
    parser.add_argument("--status", action="store_true", help="Afficher le statut des fonctionnalités")
    
    args = parser.parse_args()
    
    if args.status:
        print_feature_status()
    else:
        async def main():
            results = await analyze_text(args.text, mode=args.mode, analysis_type=args.type, use_mocks=False)
            print(f"Statut: {results['status']}")
            print(f"Temps d'exécution: {results['execution_time']:.2f}s")
            print(f"Mode utilisé: {results['metadata']['pipeline_mode']}")
            
            if results.get("recommendations"):
                print("Recommandations:")
                for rec in results["recommendations"]:
                    print(f"  • {rec}")
        
        asyncio.run(main())