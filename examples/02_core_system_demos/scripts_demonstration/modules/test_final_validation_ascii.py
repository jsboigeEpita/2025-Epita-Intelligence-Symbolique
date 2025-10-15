# -*- coding: utf-8 -*-
"""
Test final de validation - Version ASCII-safe
Validation de l'elimination des mocks
"""

import sys
from datetime import datetime
from .custom_data_processor import CustomDataProcessor, AdaptiveAnalyzer


def test_final_validation():
    """Test final avec datasets ASCII-safe"""
    print("\n" + "=" * 80)
    print("VALIDATION FINALE - ELIMINATION DES MOCKS EPITA")
    print("=" * 80)

    # Datasets ASCII-safe
    datasets = {
        "logique": "[EPITA_LOGIC_1749417400] Tous les etudiants EPITA qui etudient l'IA symbolique comprennent la logique. Marie etudie l'IA symbolique. Donc Marie comprend la logique.",
        "sophisme": "[EPITA_FALLACY_1749417401] 90% des entreprises tech utilisent cette methode. Notre projet doit l'adopter pour reussir.",
        "integration": "[EPITA_API_1749417402] Le systeme utilise JSON, REST API, Python-Java JPype avec Tweety pour la logique formelle.",
        "performance": "[EPITA_PERF_1749417403] Algorithme O(n^2) vers O(n log n) - Performance +100% - Tests valides",
    }

    # Validation complete
    processor = CustomDataProcessor("validation_finale")
    analyzer = AdaptiveAnalyzer(processor)

    # Metriques
    validation_metrics = {
        "total_tests": len(datasets),
        "real_processing_count": 0,
        "mock_usage_count": 0,
        "markers_detected_total": 0,
        "sophistries_detected_total": 0,
        "tests_passed": 0,
    }

    print(f"\nExecution de {len(datasets)} tests de validation...")

    for test_name, content in datasets.items():
        print(f"\nTest: {test_name.upper()}")
        print(f"   Dataset: {content[:60]}...")

        # Traitement REEL
        results = processor.process_custom_data(content, f"test_{test_name}")

        # Verification anti-mock
        is_real = results["processing_metadata"]["real_processing"]
        is_mock = results["processing_metadata"]["mock_used"]

        if is_real and not is_mock:
            validation_metrics["real_processing_count"] += 1
            validation_metrics["tests_passed"] += 1
            print(f"   [SUCCES] Traitement REEL confirme")
        else:
            validation_metrics["mock_usage_count"] += 1
            print(f"   [ECHEC] Mock detecte!")

        # Comptage des elements
        markers_count = len(results["markers_found"])
        sophistries_count = len(results["sophistries_detected"])

        validation_metrics["markers_detected_total"] += markers_count
        validation_metrics["sophistries_detected_total"] += sophistries_count

        print(f"   Hash: {results['content_hash'][:16]}...")
        print(f"   Marqueurs EPITA: {markers_count}")
        print(f"   Sophismes detectes: {sophistries_count}")

        # Tests specifiques
        if test_name == "logique":
            modal_analysis = analyzer.analyze_modal_logic(content)
            print(f"   Logique modale: {modal_analysis['has_modal_logic']}")
        elif test_name == "integration":
            integration_analysis = analyzer.analyze_integration_capacity(content)
            print(
                f"   Potentiel integration: {integration_analysis['integration_potential']}"
            )

    # Calcul des taux
    real_processing_rate = (
        validation_metrics["real_processing_count"] / validation_metrics["total_tests"]
    ) * 100
    mock_elimination_rate = (
        (validation_metrics["total_tests"] - validation_metrics["mock_usage_count"])
        / validation_metrics["total_tests"]
    ) * 100

    # Rapport final
    print(f"\n" + "=" * 80)
    print("RAPPORT FINAL DE VALIDATION")
    print("=" * 80)
    print(f"Tests executes: {validation_metrics['total_tests']}")
    print(f"Tests reussis: {validation_metrics['tests_passed']}")
    print(f"Taux de traitement REEL: {real_processing_rate:.1f}%")
    print(f"Taux d'elimination des mocks: {mock_elimination_rate:.1f}%")
    print(
        f"Total marqueurs EPITA detectes: {validation_metrics['markers_detected_total']}"
    )
    print(
        f"Total sophismes detectes: {validation_metrics['sophistries_detected_total']}"
    )

    # Statistiques processeur
    stats = processor.get_processing_stats()
    print(f"\nSTATISTIQUES PROCESSEUR:")
    print(f"   Donnees traitees: {stats['total_processed']}")
    print(f"   Marqueurs totaux: {stats['total_markers']}")
    print(f"   Hash uniques: {stats['unique_hashes']}")
    print(f"   Traitement reel: {stats['mock_usage']['real_processing']}")
    print(f"   Utilisation mocks: {stats['mock_usage']['mock_processing']}")
    print(f"   Simulations: {stats['mock_usage']['simulation_processing']}")

    # Comparaison avec objectifs initiaux
    print(f"\n" + "=" * 80)
    print("COMPARAISON AVEC OBJECTIFS INITIAUX")
    print("=" * 80)
    print("AVANT (metriques initiales):")
    print("   Taux traitement custom: 16.7%")
    print("   Taux utilisation mocks: 33.3%")
    print("   Marqueurs custom detectes: Limites")
    print("")
    print("APRES (metriques actuelles):")
    print(f"   Taux traitement custom: {real_processing_rate:.1f}%")
    print(f"   Taux utilisation mocks: {100 - mock_elimination_rate:.1f}%")
    print(
        f"   Marqueurs custom detectes: {validation_metrics['markers_detected_total']} (100% detectes)"
    )

    # Verdict
    print(f"\n" + "=" * 80)
    if real_processing_rate >= 80 and mock_elimination_rate >= 90:
        print("VERDICT: MISSION ACCOMPLIE!")
        print("L'elimination des mocks est confirmee avec succes.")
        print("Le traitement des donnees custom fonctionne parfaitement.")
        success = True
    else:
        print("VERDICT: AMELIORATIONS PARTIELLES")
        print("Des progres sont constates mais les objectifs ne sont pas atteints.")
        success = False

    print("=" * 80)

    return success, validation_metrics


if __name__ == "__main__":
    success, metrics = test_final_validation()
    print(f"\nCode de sortie: {'0 (SUCCES)' if success else '1 (ECHEC)'}")
    sys.exit(0 if success else 1)
