# -*- coding: utf-8 -*-
"""
Test de validation - Élimination des mocks Épita
Test direct des nouvelles capacités
"""

import sys
from .custom_data_processor import CustomDataProcessor, AdaptiveAnalyzer


def test_elimination_mocks():
    """Test principal de validation de l'élimination des mocks"""
    print("\n" + "=" * 80)
    print("VALIDATION ELIMINATION DES MOCKS - DEMO EPITA")
    print("=" * 80)

    # Datasets de test avec marqueurs EPITA
    datasets = {
        "logique": "[EPITA_LOGIC_1749417400] Tous les étudiants EPITA qui étudient l'IA symbolique comprennent la logique. Marie étudie l'IA symbolique. Donc Marie comprend la logique.",
        "sophisme": "[EPITA_FALLACY_1749417401] 90% des entreprises tech utilisent cette méthode. Notre projet doit l'adopter pour réussir.",
        "integration": "[EPITA_API_1749417402] Le système utilise JSON, REST API, Python-Java JPype avec Tweety pour la logique formelle.",
        "unicode": "[EPITA_UNICODE_1749417403] Algorithme: O(n²) → O(n log n) 🚀 Performance ✓ Tests: ✅ 中文",
    }

    # Initialisation
    processor = CustomDataProcessor("validation_test")
    analyzer = AdaptiveAnalyzer(processor)

    # Métriques de validation
    validation_metrics = {
        "total_tests": len(datasets),
        "real_processing_count": 0,
        "mock_usage_count": 0,
        "markers_detected_total": 0,
        "sophistries_detected_total": 0,
        "unicode_support_verified": False,
    }

    print(f"\nTest de {len(datasets)} datasets avec traitement REEL...")

    for test_name, content in datasets.items():
        print(f"\nTest: {test_name.upper()}")
        print(f"   Contenu: {content[:50]}...")

        # Traitement avec le nouveau processeur
        results = processor.process_custom_data(content, f"test_{test_name}")

        # Vérification anti-mock
        is_real_processing = results["processing_metadata"]["real_processing"]
        is_mock_used = results["processing_metadata"]["mock_used"]

        # Mise à jour des métriques
        if is_real_processing and not is_mock_used:
            validation_metrics["real_processing_count"] += 1
            print("   [OK] Traitement REEL confirme")
        else:
            validation_metrics["mock_usage_count"] += 1
            print("   [ERREUR] Mock detecte!")

        validation_metrics["markers_detected_total"] += len(results["markers_found"])
        validation_metrics["sophistries_detected_total"] += len(
            results["sophistries_detected"]
        )

        # Test Unicode
        if test_name == "unicode" and results["unicode_support"]["has_unicode"]:
            validation_metrics["unicode_support_verified"] = True
            print(
                f"   [OK] Support Unicode verifie: {results['unicode_support']['unicode_count']} caracteres"
            )

        print(f"   Hash: {results['content_hash'][:16]}...")
        print(f"   Marqueurs: {len(results['markers_found'])}")
        print(f"   Sophismes: {len(results['sophistries_detected'])}")

        # Test de l'analyseur adaptatif
        if test_name == "logique":
            modal_analysis = analyzer.analyze_modal_logic(content)
            print(f"   Logique modale: {modal_analysis['has_modal_logic']}")
        elif test_name == "integration":
            integration_analysis = analyzer.analyze_integration_capacity(content)
            print(
                f"   Potentiel integration: {integration_analysis['integration_potential']}"
            )

    # Calcul des métriques finales
    real_processing_rate = (
        validation_metrics["real_processing_count"] / validation_metrics["total_tests"]
    ) * 100
    mock_elimination_rate = (
        (validation_metrics["total_tests"] - validation_metrics["mock_usage_count"])
        / validation_metrics["total_tests"]
    ) * 100

    print("\n" + "=" * 80)
    print("RESULTATS DE VALIDATION")
    print("=" * 80)
    print(f"Taux de traitement REEL: {real_processing_rate:.1f}%")
    print(f"Taux d'elimination des mocks: {mock_elimination_rate:.1f}%")
    print(f"Total marqueurs detectes: {validation_metrics['markers_detected_total']}")
    print(
        f"Total sophismes detectes: {validation_metrics['sophistries_detected_total']}"
    )
    print(
        f"Support Unicode verifie: {'[OK]' if validation_metrics['unicode_support_verified'] else '[NON]'}"
    )

    # Statistiques globales du processeur
    processor_stats = processor.get_processing_stats()
    print("\nSTATISTIQUES PROCESSEUR:")
    print(f"   • Données traitées: {processor_stats['total_processed']}")
    print(f"   • Marqueurs totaux: {processor_stats['total_markers']}")
    print(f"   • Hash uniques: {processor_stats['unique_hashes']}")
    print(f"   • Traitement réel: {processor_stats['mock_usage']['real_processing']}")
    print(
        f"   • Utilisation de mocks: {processor_stats['mock_usage']['mock_processing']}"
    )

    # Verdict final
    print("\n" + "=" * 80)
    if real_processing_rate >= 80 and mock_elimination_rate >= 90:
        print("VALIDATION REUSSIE - Elimination des mocks confirmee!")
        success = True
    else:
        print(
            "VALIDATION PARTIELLE - Ameliorations detectees mais objectifs non atteints"
        )
        success = False

    print("=" * 80)

    return success, validation_metrics


if __name__ == "__main__":
    success, metrics = test_elimination_mocks()
    sys.exit(0 if success else 1)
