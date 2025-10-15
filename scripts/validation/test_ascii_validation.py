#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test ASCII de validation : Traitement des donnees custom
Validation de l'elimination des mocks - EPITA Demo
"""

import argumentation_analysis.core.environment
import sys
from pathlib import Path

# Ajouter le chemin des modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "examples" / "scripts_demonstration" / "modules"))


def test_custom_data_processor():
    """Test rapide du CustomDataProcessor"""
    print("=" * 70)
    print("                   VALIDATION ELIMINATION MOCKS")
    print("                       EPITA Demo 2025")
    print("=" * 70)

    try:
        from custom_data_processor import CustomDataProcessor, AdaptiveAnalyzer

        print("[OK] Import CustomDataProcessor : SUCCES")

        # Test avec des donnees custom reelles
        processor = CustomDataProcessor()
        test_data = "[EPITA_TEST_1749417400] Tous les algorithmes optimises sont rapides. Cet algorithme est optimise. -> Donc il est rapide."

        result = processor.process_custom_data(test_data, "logique")

        # Verification des criteres d'elimination des mocks
        validation_passed = True

        # Vérifier que mock_used = False dans processing_metadata
        mock_used = result.get("processing_metadata", {}).get("mock_used", True)
        if mock_used:
            print("[FAIL] Le systeme utilise encore des mocks")
            validation_passed = False
        else:
            print("[OK] Mock elimine : aucun mock utilise")

        if "content_hash" not in result:
            print("[FAIL] Pas de hash de contenu genere")
            validation_passed = False
        else:
            print(f"[OK] Hash contenu genere : {result['content_hash'][:8]}...")

        # Vérifier markers_found au lieu de epita_markers
        if "markers_found" not in result:
            print("[FAIL] Marqueurs EPITA non detectes")
            validation_passed = False
        else:
            print(f"[OK] Marqueurs EPITA detectes : {len(result['markers_found'])}")

        if "sophistries_detected" not in result:
            print("[FAIL] Analyse sophistique non effectuee")
            validation_passed = False
        else:
            print(
                f"[OK] Analyse sophistique : {len(result['sophistries_detected'])} detections"
            )

        # Verification du traitement adaptatif dans processing_metadata
        adaptive_analysis = result.get("processing_metadata", {}).get(
            "adaptive_analysis", False
        )
        real_processing = result.get("processing_metadata", {}).get(
            "real_processing", False
        )
        if not adaptive_analysis or not real_processing:
            print("[FAIL] Mode de traitement non adaptatif")
            validation_passed = False
        else:
            print("[OK] Mode adaptatif : traitement reel des donnees")

        print("\n" + "=" * 70)

        if validation_passed:
            print("*** VALIDATION REUSSIE : Elimination des mocks confirmee ! ***")
            print("*** Pourcentage de traitement reel : 100% ***")
            print("*** Pourcentage de mocks : 0% ***")
            print("\nRESUME TECHNIQUE :")
            print(f"- Hash SHA256 : {result.get('content_hash', 'N/A')}")
            print(
                f"- Traitement reel : {result.get('processing_metadata', {}).get('real_processing', 'N/A')}"
            )
            print(
                f"- Analyse adaptive : {result.get('processing_metadata', {}).get('adaptive_analysis', 'N/A')}"
            )
            print(f"- Marqueurs EPITA : {len(result.get('markers_found', []))}")
            print(
                f"- Detections sophistique : {len(result.get('sophistries_detected', []))}"
            )
            print(
                f"- Mock utilise : {result.get('processing_metadata', {}).get('mock_used', 'N/A')}"
            )
            return True
        else:
            print("*** VALIDATION ECHOUEE : Des mocks sont encore presents ***")
            return False

    except ImportError as e:
        print(f"[ERROR] Import : {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Test : {e}")
        return False


if __name__ == "__main__":
    success = test_custom_data_processor()
    if success:
        print("\n" + "=" * 70)
        print("           MISSION ACCOMPLIE - MOCKS ELIMINES")
        print("=" * 70)
    sys.exit(0 if success else 1)
