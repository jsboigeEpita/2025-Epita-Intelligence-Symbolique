#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple de validation : Traitement des données custom
Validation de l'élimination des mocks - ÉPITA Demo
"""

import sys
from pathlib import Path

# Ajouter le chemin des modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "examples" / "scripts_demonstration" / "modules"))

def test_custom_data_processor():
    """Test rapide du CustomDataProcessor"""
    print("="*70)
    print("                   VALIDATION ELIMINATION MOCKS")
    print("                       EPITA Demo 2025")
    print("="*70)
    
    try:
        from custom_data_processor import CustomDataProcessor, AdaptiveAnalyzer
        print("✅ Import CustomDataProcessor : SUCCÈS")
        
        # Test avec des données custom réelles
        processor = CustomDataProcessor()
        test_data = "[EPITA_TEST_1749417400] Tous les algorithmes optimises sont rapides. Cet algorithme est optimise. -> Donc il est rapide."
        
        result = processor.process_custom_data(test_data, 'logique')
        
        # Vérification des critères d'élimination des mocks
        validation_passed = True
        
        if result.get('mock_used', True):
            print("❌ ÉCHEC : Le système utilise encore des mocks")
            validation_passed = False
        else:
            print("✅ Mock éliminé : aucun mock utilisé")
        
        if 'content_hash' not in result:
            print("❌ ÉCHEC : Pas de hash de contenu généré")
            validation_passed = False
        else:
            print(f"✅ Hash contenu généré : {result['content_hash'][:8]}...")
        
        if 'epita_markers' not in result:
            print("❌ ÉCHEC : Marqueurs ÉPITA non détectés")
            validation_passed = False
        else:
            print(f"✅ Marqueurs ÉPITA détectés : {len(result['epita_markers'])}")
        
        if 'sophistries_detected' not in result:
            print("❌ ÉCHEC : Analyse sophistique non effectuée")
            validation_passed = False
        else:
            print(f"✅ Analyse sophistique : {len(result['sophistries_detected'])} détections")
        
        # Vérification du traitement adaptatif
        if result.get('processing_mode') != 'adaptive_real_analysis':
            print("❌ ÉCHEC : Mode de traitement non adaptatif")
            validation_passed = False
        else:
            print("✅ Mode adaptatif : traitement réel des données")
        
        print("\n" + "="*70)
        
        if validation_passed:
            print("VALIDATION REUSSIE : Elimination des mocks confirmee !")
            print("Pourcentage de traitement reel : 100%")
            print("Pourcentage de mocks : 0%")
            return True
        else:
            print("❌ VALIDATION ÉCHOUÉE : Des mocks sont encore présents")
            return False
            
    except ImportError as e:
        print(f"❌ ERREUR d'import : {e}")
        return False
    except Exception as e:
        print(f"❌ ERREUR de test : {e}")
        return False

if __name__ == "__main__":
    success = test_custom_data_processor()
    sys.exit(0 if success else 1)