#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rapide pour valider le Unified Production Analyzer
======================================================

Script de validation pour vérifier que le script consolidé
fonctionne correctement avant déploiement.
"""

import asyncio
import sys
from pathlib import Path

# Ajout du chemin pour import
sys.path.insert(0, str(Path(__file__).parent))

from unified_production_analyzer import (
    UnifiedProductionConfig,
    UnifiedProductionAnalyzer,
    LogicType,
    MockLevel,
    OrchestrationType,
    AnalysisMode
)

async def test_configuration():
    """Test de la configuration de base"""
    print("🔧 Test configuration...")
    
    config = UnifiedProductionConfig(
        mock_level=MockLevel.FULL,  # Mode test
        require_real_gpt=False,
        require_real_tweety=False,
        check_dependencies=False,
        analysis_modes=[AnalysisMode.UNIFIED]
    )
    
    valid, errors = config.validate()
    assert valid, f"Configuration invalide: {errors}"
    print("✅ Configuration validée")

async def test_analyzer_initialization():
    """Test d'initialisation de l'analyseur"""
    print("🚀 Test initialisation...")
    
    config = UnifiedProductionConfig(
        mock_level=MockLevel.FULL,
        require_real_gpt=False,
        require_real_tweety=False,
        check_dependencies=False
    )
    
    analyzer = UnifiedProductionAnalyzer(config)
    
    # Test d'initialisation (doit réussir en mode mock)
    success = await analyzer.initialize()
    assert success, "Échec initialisation"
    print("✅ Analyseur initialisé")
    
    return analyzer

async def test_text_analysis():
    """Test d'analyse de texte simple"""
    print("📝 Test analyse texte...")
    
    analyzer = await test_analyzer_initialization()
    
    # Analyse d'un texte simple
    test_text = "L'intelligence artificielle va changer notre monde."
    
    result = await analyzer.analyze_text(test_text)
    
    assert "id" in result, "ID manquant dans résultat"
    assert "session_id" in result, "Session ID manquant"
    assert "results" in result, "Résultats manquants"
    assert result["text_length"] == len(test_text), "Longueur incorrecte"
    
    print(f"✅ Analyse terminée: {result['id']}")
    print(f"   Temps: {result['execution_time']:.2f}s")
    print(f"   Modes: {result['modes_analyzed']}")

async def test_batch_analysis():
    """Test d'analyse batch"""
    print("📦 Test analyse batch...")
    
    analyzer = await test_analyzer_initialization()
    
    test_texts = [
        "Premier texte à analyser.",
        "Deuxième texte pour le batch.",
        "Troisième et dernier texte."
    ]
    
    results = await analyzer.analyze_batch(test_texts)
    
    assert len(results) == 3, f"Attendu 3 résultats, reçu {len(results)}"
    print(f"✅ Batch terminé: {len(results)} analyses")

async def test_report_generation():
    """Test de génération de rapport"""
    print("📊 Test rapport...")
    
    analyzer = await test_analyzer_initialization()
    
    # Quelques analyses pour remplir l'historique
    await analyzer.analyze_text("Texte test 1")
    await analyzer.analyze_text("Texte test 2")
    
    # Génération rapport
    report = analyzer.generate_report()
    
    assert "session_info" in report, "Info session manquante"
    assert "results_summary" in report, "Résumé manquant"
    assert report["session_info"]["total_analyses"] == 2, "Nombre analyses incorrect"
    
    print(f"✅ Rapport généré: {report['session_info']['id']}")
    print(f"   Analyses: {report['session_info']['total_analyses']}")

async def main():
    """Fonction principale de test"""
    print("🧪 Tests Unified Production Analyzer")
    print("=" * 50)
    
    try:
        await test_configuration()
        await test_analyzer_initialization()
        await test_text_analysis()
        await test_batch_analysis()
        await test_report_generation()
        
        print("=" * 50)
        print("🎉 Tous les tests réussis !")
        print("✅ Le Unified Production Analyzer est fonctionnel")
        
    except Exception as e:
        print(f"❌ Échec test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())