#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour le système de génération de rapports unifié.

Ce script teste l'intégration complète du nouveau système de génération
de rapports avec tous les composants refactorisés de l'écosystème.
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_core_report_generation():
    """Test du composant core de génération de rapports."""
    print("\n" + "="*80)
    print("[TEST] TEST 1: COMPOSANT CORE DE GÉNÉRATION DE RAPPORTS")
    print("="*80)
    
    try:
        from argumentation_analysis.core.report_generation import (
            UnifiedReportGenerator, ReportMetadata, ReportConfiguration,
            generate_quick_report, create_component_report_factory
        )
        print("[OK] Import du composant core réussi")
        
        # Test de création d'instance
        generator = UnifiedReportGenerator()
        print("[OK] Création d'instance UnifiedReportGenerator réussie")
        
        # Test des formats supportés
        formats = generator.get_supported_formats()
        print(f"[OK] Formats supportés: {formats}")
        
        # Test des templates disponibles
        templates = generator.get_available_templates()
        print(f"[OK] Templates disponibles: {len(templates)} templates")
        
        # Test des composants supportés
        components = generator.get_supported_components()
        print(f"[OK] Composants supportés: {components}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test composant core: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_legacy_compatibility():
    """Test de compatibilité avec l'ancienne interface."""
    print("\n" + "="*80)
    print("[TEST] TEST 2: COMPATIBILITÉ AVEC L'ANCIENNE INTERFACE")
    print("="*80)
    
    try:
        from scripts.core.unified_report_generator import (
            UnifiedReportGeneratorLegacy, ReportTemplate,
            create_legacy_generator, generate_component_report
        )
        print("[OK] Import de l'interface de compatibilité réussi")
        
        # Test du générateur legacy
        legacy_generator = create_legacy_generator()
        print("[OK] Création du générateur legacy réussie")
        
        # Test des méthodes de compatibilité
        formats = legacy_generator.get_supported_formats()
        templates = legacy_generator.list_available_templates()
        print(f"[OK] Interface legacy fonctionnelle - Formats: {len(formats)}, Templates: {len(templates)}")
        
        # Test du template de compatibilité
        template_config = {
            "name": "test_template",
            "format": "markdown",
            "sections": ["summary"]
        }
        template = ReportTemplate(template_config)
        print("[OK] Template de compatibilité créé")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test compatibilité: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orchestrator_integration():
    """Test d'intégration avec les orchestrateurs refactorisés."""
    print("\n" + "="*80)
    print("[TEST] TEST 3: INTÉGRATION AVEC LES ORCHESTRATEURS")
    print("="*80)
    
    try:
        from argumentation_analysis.core.report_generation import (
            UnifiedReportGenerator, ReportMetadata, ReportConfiguration
        )
        
        # Données simulées d'orchestration LLM
        llm_orchestration_data = {
            "title": "Rapport Orchestration LLM",
            "metadata": {
                "source_description": "Test d'orchestration LLM",
                "source_type": "text_analysis",
                "text_length": 1500,
                "processing_time_ms": 2500
            },
            "summary": {
                "rhetorical_sophistication": "Élevée",
                "manipulation_level": "Modéré",
                "logical_validity": "Cohérent",
                "confidence_score": 0.85,
                "orchestration_summary": {
                    "agents_count": 3,
                    "orchestration_time_ms": 1200,
                    "execution_status": "Succès complet"
                }
            },
            "orchestration_results": {
                "execution_plan": {
                    "strategy": "Analyse séquentielle",
                    "steps": [
                        {"agent": "FallacyDetector", "description": "Détection des sophismes"},
                        {"agent": "LogicAnalyzer", "description": "Analyse logique"},
                        {"agent": "RhetoricalAnalyzer", "description": "Analyse rhétorique"}
                    ]
                },
                "agent_results": {
                    "FallacyDetector": {
                        "status": "success",
                        "execution_time_ms": 800,
                        "metrics": {"processed_items": 15, "confidence_score": 0.9}
                    },
                    "LogicAnalyzer": {
                        "status": "success", 
                        "execution_time_ms": 600,
                        "metrics": {"processed_items": 8, "confidence_score": 0.8}
                    }
                }
            },
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Ad Hominem",
                        "text_fragment": "Ses arguments sont invalides car il est incompétent",
                        "explanation": "Attaque personnelle plutôt que critique de l'argument",
                        "severity": "Élevé",
                        "confidence": 0.9
                    }
                ]
            },
            "performance_metrics": {
                "total_execution_time_ms": 2500,
                "memory_usage_mb": 128,
                "active_agents_count": 3,
                "success_rate": 1.0
            }
        }
        
        generator = UnifiedReportGenerator()
        
        # Test RealLLMOrchestrator
        llm_metadata = ReportMetadata(
            source_component="RealLLMOrchestrator",
            analysis_type="orchestration",
            generated_at=datetime.now()
        )
        
        llm_config = ReportConfiguration(
            output_format="markdown",
            template_name="llm_orchestration",
            output_mode="console"
        )
        
        llm_report = generator.generate_unified_report(llm_orchestration_data, llm_metadata, llm_config)
        print("[OK] Rapport RealLLMOrchestrator généré")
        print(f"   Longueur: {len(llm_report)} caractères")
        
        # Test ConversationOrchestrator
        conversation_data = {
            "title": "Rapport Orchestration Conversation",
            "metadata": {"source_description": "Test conversation"},
            "conversation": [
                {"user": "Analysez ce texte", "system": "J'analyse le texte fourni"},
                {"user": "Quels sophismes détectez-vous?", "system": "Je détecte un sophisme ad hominem"}
            ],
            "summary": {
                "orchestration_summary": {
                    "agents_count": 2,
                    "execution_status": "Succès partiel"
                }
            }
        }
        
        conv_metadata = ReportMetadata(
            source_component="ConversationOrchestrator",
            analysis_type="conversation_orchestration",
            generated_at=datetime.now()
        )
        
        conv_config = ReportConfiguration(
            output_format="html",
            template_name="conversation_orchestration",
            output_mode="console"
        )
        
        conv_report = generator.generate_unified_report(conversation_data, conv_metadata, conv_config)
        print("[OK] Rapport ConversationOrchestrator généré")
        print(f"   Longueur: {len(conv_report)} caractères")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test orchestrateurs: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analysis_components_integration():
    """Test d'intégration avec les composants d'analyse refactorisés."""
    print("\n" + "="*80)
    print("[TEST] TEST 4: INTÉGRATION AVEC LES COMPOSANTS D'ANALYSE")
    print("="*80)
    
    try:
        from argumentation_analysis.core.report_generation import generate_quick_report
        
        # Test UnifiedTextAnalysis
        text_analysis_data = {
            "title": "Analyse Textuelle Unifiée",
            "metadata": {
                "source_description": "Document de test",
                "text_length": 2000,
                "processing_time_ms": 1500
            },
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Strawman",
                        "text_fragment": "Il prétend que nous voulons détruire l'économie",
                        "explanation": "Déformation de l'argument original",
                        "severity": "Modéré",
                        "confidence": 0.85
                    },
                    {
                        "type": "False Dilemma",
                        "text_fragment": "Soit nous acceptons, soit nous échouons",
                        "explanation": "Présentation de seulement deux options",
                        "severity": "Élevé", 
                        "confidence": 0.9
                    }
                ]
            },
            "formal_analysis": {
                "logic_type": "Propositional Logic",
                "status": "Analyzed",
                "belief_set_summary": {
                    "is_consistent": True,
                    "formulas_validated": 8,
                    "formulas_total": 10
                },
                "queries": [
                    {"query": "P -> Q", "result": "Entailed"},
                    {"query": "Q & R", "result": "Not Entailed"}
                ]
            }
        }
        
        # Test avec l'API simplifiée
        unified_report = generate_quick_report(
            data=text_analysis_data,
            source_component="UnifiedTextAnalysis",
            analysis_type="text_analysis",
            output_format="markdown"
        )
        print("[OK] Rapport UnifiedTextAnalysis généré")
        print(f"   Longueur: {len(unified_report)} caractères")
        
        # Test SourceManagement
        source_management_data = {
            "title": "Rapport Gestion des Sources",
            "metadata": {
                "source_description": "Gestion de corpus",
                "processing_time_ms": 800
            },
            "source_summary": {
                "total_sources": 25,
                "processed_sources": 23,
                "failed_sources": 2,
                "success_rate": 0.92
            },
            "processing_results": {
                "extraction_results": [
                    {"source": "doc1.txt", "status": "success", "size": 1500},
                    {"source": "doc2.txt", "status": "success", "size": 2200},
                    {"source": "doc3.txt", "status": "failed", "error": "Format non supporté"}
                ]
            }
        }
        
        source_report = generate_quick_report(
            data=source_management_data,
            source_component="SourceManagement", 
            analysis_type="source_processing",
            output_format="json"
        )
        print("[OK] Rapport SourceManagement généré")
        print(f"   Longueur: {len(source_report)} caractères")
        
        # Test AdvancedRhetoric
        rhetoric_data = {
            "title": "Analyse Rhétorique Avancée",
            "rhetorical_analysis": {
                "sophistication_level": "Très élevée",
                "rhetorical_devices": ["Métaphore", "Allégorie", "Chiasme"],
                "persuasion_techniques": ["Ethos", "Pathos", "Logos"],
                "effectiveness_score": 0.88
            },
            "sophistication_metrics": {
                "vocabulary_complexity": 0.75,
                "syntactic_complexity": 0.82, 
                "semantic_density": 0.69
            },
            "manipulation_assessment": {
                "manipulation_indicators": ["Faux dilemme", "Appel à l'émotion"],
                "manipulation_score": 0.65,
                "intent_analysis": "Persuasion légitime avec techniques manipulatoires mineures"
            }
        }
        
        rhetoric_report = generate_quick_report(
            data=rhetoric_data,
            source_component="AdvancedRhetoric",
            analysis_type="rhetorical_analysis", 
            output_format="html"
        )
        print("[OK] Rapport AdvancedRhetoric généré")
        print(f"   Longueur: {len(rhetoric_report)} caractères")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test composants d'analyse: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pipeline_integration():
    """Test d'intégration avec le pipeline de rapports existant."""
    print("\n" + "="*80)
    print("[TEST] TEST 5: INTÉGRATION AVEC LE PIPELINE EXISTANT")
    print("="*80)
    
    try:
        from argumentation_analysis.core.report_generation import (
            UnifiedReportGenerator, ReportMetadata, ReportConfiguration
        )
        
        # Test de coexistence avec le pipeline existant
        pipeline_data = {
            "title": "Rapport Pipeline Complet",
            "metadata": {
                "source_description": "Pipeline de traitement complet",
                "processing_time_ms": 5000
            },
            "pipeline_metrics": {
                "stages_completed": 5,
                "total_stages": 5,
                "data_processed": 1000
            },
            "summary": {
                "rhetorical_sophistication": "Élevée",
                "manipulation_level": "Faible"
            },
            "informal_analysis": {
                "fallacies": [
                    {"type": "Généralisation hâtive", "severity": "Modéré", "confidence": 0.8}
                ]
            },
            "performance_metrics": {
                "total_execution_time_ms": 5000,
                "memory_usage_mb": 256,
                "success_rate": 0.95
            }
        }
        
        generator = UnifiedReportGenerator()
        
        metadata = ReportMetadata(
            source_component="ReportingPipeline",
            analysis_type="pipeline_analysis",
            generated_at=datetime.now()
        )
        
        config = ReportConfiguration(
            output_format="markdown",
            output_mode="console",
            include_metadata=True
        )
        
        pipeline_report = generator.generate_unified_report(pipeline_data, metadata, config)
        print("[OK] Rapport Pipeline généré")
        print(f"   Longueur: {len(pipeline_report)} caractères")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_format_generation():
    """Test de génération dans tous les formats supportés."""
    print("\n" + "="*80)
    print("[TEST] TEST 6: GÉNÉRATION DANS TOUS LES FORMATS")
    print("="*80)
    
    try:
        from argumentation_analysis.core.report_generation import (
            UnifiedReportGenerator, ReportMetadata, ReportConfiguration
        )
        
        # Données de test complètes
        test_data = {
            "title": "Test Multi-Format",
            "metadata": {
                "source_description": "Test de tous les formats",
                "text_length": 1000,
                "processing_time_ms": 1000
            },
            "summary": {
                "rhetorical_sophistication": "Modérée",
                "manipulation_level": "Faible",
                "confidence_score": 0.8,
                "orchestration_summary": {
                    "agents_count": 2,
                    "execution_status": "Succès complet"
                }
            },
            "informal_analysis": {
                "fallacies": [
                    {
                        "type": "Ad Hominem",
                        "text_fragment": "Test fragment",
                        "explanation": "Test explanation",
                        "severity": "Modéré",
                        "confidence": 0.8
                    }
                ]
            },
            "performance_metrics": {
                "total_execution_time_ms": 1000,
                "memory_usage_mb": 64,
                "success_rate": 1.0
            }
        }
        
        generator = UnifiedReportGenerator()
        
        metadata = ReportMetadata(
            source_component="MultiFormatTest",
            analysis_type="format_testing",
            generated_at=datetime.now()
        )
        
        formats = ["markdown", "json", "html", "console"]
        reports = {}
        
        for format_type in formats:
            config = ReportConfiguration(
                output_format=format_type,
                output_mode="console"
            )
            
            report = generator.generate_unified_report(test_data, metadata, config)
            reports[format_type] = report
            print(f"[OK] Format {format_type}: {len(report)} caractères")
        
        # Validation des contenus
        assert len(reports["markdown"]) > 100, "Rapport Markdown trop court"
        assert len(reports["json"]) > 100, "Rapport JSON trop court"
        assert len(reports["html"]) > 200, "Rapport HTML trop court"
        assert len(reports["console"]) > 50, "Rapport Console trop court"
        
        print("[OK] Tous les formats validés")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test multi-format: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comparative_reporting():
    """Test de génération de rapports comparatifs."""
    print("\n" + "="*80)
    print("[TEST] TEST 7: GÉNÉRATION DE RAPPORTS COMPARATIFS")
    print("="*80)
    
    try:
        from argumentation_analysis.core.report_generation import (
            UnifiedReportGenerator, ReportMetadata, ReportConfiguration
        )
        
        # Données pour plusieurs analyses
        analysis1_data = {
            "title": "Analyse 1",
            "report_metadata": {
                "source_component": "RealLLMOrchestrator",
                "analysis_type": "orchestration"
            },
            "summary": {"total_fallacies": 3, "rhetorical_sophistication": "Élevée"},
            "performance_metrics": {"total_execution_time_ms": 2000, "memory_usage_mb": 100}
        }
        
        analysis2_data = {
            "title": "Analyse 2", 
            "report_metadata": {
                "source_component": "ConversationOrchestrator",
                "analysis_type": "conversation"
            },
            "summary": {"total_fallacies": 1, "rhetorical_sophistication": "Modérée"},
            "performance_metrics": {"total_execution_time_ms": 1500, "memory_usage_mb": 80}
        }
        
        generator = UnifiedReportGenerator()
        
        comparison_metadata = ReportMetadata(
            source_component="ComparativeAnalysis",
            analysis_type="comparison",
            generated_at=datetime.now()
        )
        
        config = ReportConfiguration(
            output_format="markdown",
            output_mode="console"
        )
        
        comparative_report = generator.generate_comparative_report(
            reports_data=[analysis1_data, analysis2_data],
            comparison_metadata=comparison_metadata,
            config=config
        )
        
        print("[OK] Rapport comparatif généré")
        print(f"   Longueur: {len(comparative_report)} caractères")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test comparatif: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli_interface():
    """Test de l'interface CLI refactorisée."""
    print("\n" + "="*80)
    print("[TEST] TEST 8: INTERFACE CLI REFACTORISÉE")
    print("="*80)
    
    try:
        # Créer des données de test
        test_data = {
            "title": "Test CLI",
            "metadata": {"source_description": "Test CLI"},
            "summary": {"rhetorical_sophistication": "Modérée"},
            "informal_analysis": {"fallacies": []}
        }
        
        # Sauvegarder dans un fichier temporaire
        test_file = Path("test_cli_data.json")
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)
        
        # Test import du module CLI
        from scripts.core.unified_report_generator import main, generate_component_report
        print("[OK] Import de l'interface CLI réussi")
        
        # Test de l'API programmable
        component_report = generate_component_report(
            component_name="TestComponent",
            analysis_data=test_data,
            analysis_type="test",
            output_format="markdown",
            save_file=False
        )
        print("[OK] API programmable fonctionnelle")
        print(f"   Longueur rapport: {len(component_report)} caractères")
        
        # Nettoyer
        if test_file.exists():
            test_file.unlink()
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur test CLI: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_integration_tests():
    """Lance tous les tests d'intégration."""
    print("DEBUT DES TESTS D'INTEGRATION - GENERATION DE RAPPORTS UNIFIES")
    print("="*80)
    
    tests = [
        ("Composant Core", test_core_report_generation),
        ("Compatibilite Legacy", test_legacy_compatibility),
        ("Orchestrateurs", test_orchestrator_integration),
        ("Composants d'Analyse", test_analysis_components_integration),
        ("Pipeline Existant", test_pipeline_integration),
        ("Multi-Format", test_multiple_format_generation),
        ("Rapports Comparatifs", test_comparative_reporting),
        ("Interface CLI", test_cli_interface)
    ]
    
    results = {}
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed += 1
        except Exception as e:
            print(f"[ERREUR] Erreur critique dans {test_name}: {e}")
            results[test_name] = False
    
    # Rapport final
    print("\n" + "="*80)
    print("RESULTATS DES TESTS D'INTEGRATION")
    print("="*80)
    
    for test_name, result in results.items():
        status = "[PASSE]" if result else "[ECHEC]"
        print(f"{status} - {test_name}")
    
    print(f"\nScore global: {passed}/{total} tests reussis ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("TOUS LES TESTS D'INTEGRATION ONT REUSSI!")
        print("Le systeme de generation de rapports unifie est pleinement integre")
    else:
        print("Certains tests ont echoue - revision necessaire")
    
    return passed == total

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)