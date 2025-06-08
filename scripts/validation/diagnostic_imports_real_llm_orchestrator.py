#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour valider les problèmes d'imports dans real_llm_orchestrator.py
===================================================================================

Ce script teste systématiquement chaque import défaillant pour confirmer le diagnostic.
"""

import sys
import importlib.util
from pathlib import Path

def test_import(module_path, class_name, description):
    """Teste un import spécifique et log le résultat."""
    print(f"\n[TEST] {description}")
    print(f"Module: {module_path}")
    print(f"Classe: {class_name}")
    
    try:
        # Tenter l'import du module
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec is None or spec.loader is None:
            print(f"[ECHEC] Module introuvable - {module_path}")
            return False
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Tenter l'accès à la classe
        if hasattr(module, class_name):
            print(f"[SUCCES] Classe {class_name} trouvée")
            return True
        else:
            print(f"[ECHEC] Classe {class_name} introuvable dans le module")
            return False
            
    except Exception as e:
        print(f"[ERREUR] {str(e)}")
        return False

def test_circular_import():
    """Teste l'import circulaire entre real_llm_orchestrator et unified_text_analysis."""
    print(f"\n[CIRCULAR] Test Import Circulaire")
    
    try:
        # Essayer d'importer unified_text_analysis en premier
        from argumentation_analysis.pipelines.unified_text_analysis import UnifiedTextAnalysisPipeline
        print("[SUCCES] unified_text_analysis.py importé avec succès")
        
        # Puis essayer real_llm_orchestrator
        from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
        print("[ECHEC ATTENDU] real_llm_orchestrator.py ne devrait pas s'importer")
        return False
        
    except ImportError as e:
        print(f"[CONFIRME] Import circulaire détecté - {str(e)}")
        return True
    except Exception as e:
        print(f"[ERREUR INATTENDUE] {str(e)}")
        return False

def main():
    """Exécute tous les tests de diagnostic."""
    print("=" * 80)
    print("DIAGNOSTIC IMPORTS - real_llm_orchestrator.py")
    print("=" * 80)
    
    base_path = Path("argumentation_analysis")
    
    # Tests des imports manquants
    missing_imports = [
        ("analyzers/syntactic_analyzer.py", "SyntacticAnalyzer", "Analyseur Syntaxique"),
        ("analyzers/semantic_analyzer.py", "SemanticAnalyzer", "Analyseur Sémantique"), 
        ("analyzers/pragmatic_analyzer.py", "PragmaticAnalyzer", "Analyseur Pragmatique"),
        ("analyzers/logical_analyzer.py", "LogicalAnalyzer", "Analyseur Logique"),
        ("extraction/entity_extractor.py", "EntityExtractor", "Extracteur d'Entités"),
        ("extraction/relation_extractor.py", "RelationExtractor", "Extracteur de Relations"),
        ("validation/consistency_validator.py", "ConsistencyValidator", "Validateur de Cohérence"),
        ("validation/coherence_validator.py", "CoherenceValidator", "Validateur de Cohérence"),
        ("utils/error_handler.py", "ErrorHandler", "Gestionnaire d'Erreurs"),
        ("pipelines/unified_text_analysis.py", "UnifiedTextAnalyzer", "Analyseur de Texte Unifié")
    ]
    
    success_count = 0
    total_count = len(missing_imports)
    
    for module_rel_path, class_name, description in missing_imports:
        module_path = base_path / module_rel_path
        success = test_import(module_path, class_name, description)
        if success:
            success_count += 1
    
    # Test import circulaire
    print(f"\n" + "=" * 40)
    circular_detected = test_circular_import()
    
    # Résumé diagnostic
    print(f"\n" + "=" * 80)
    print("RESUME DIAGNOSTIC")
    print("=" * 80)
    print(f"[SUCCES] Imports réussis: {success_count}/{total_count}")
    print(f"[ECHEC] Imports échoués: {total_count - success_count}/{total_count}")
    print(f"[CIRCULAIRE] Import circulaire détecté: {'OUI' if circular_detected else 'NON'}")
    
    print(f"\nCONCLUSION:")
    if success_count == 0 and circular_detected:
        print("[CONFIRME] HYPOTHÈSE CONFIRMÉE: Problème d'imports manquants + import circulaire")
        print("[SOLUTION] Créer des classes stub ou corriger les imports")
    else:
        print("[REVOIR] HYPOTHÈSE À REVOIR: Résultats inattendus")
    
    print("=" * 80)

if __name__ == "__main__":
    main()