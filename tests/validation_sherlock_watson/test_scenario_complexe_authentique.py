# -*- coding: utf-8 -*-
"""
Test de validation d'un scénario complexe et authentique de bout en bout.
Ce test a pour but de valider le pipeline d'analyse rhétorique sur des textes
chiffrés, en utilisant des données complexes qui ne peuvent pas être traitées
correctement par des mocks.
"""

import time
import pytest
from pathlib import Path

from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer as EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector as EnhancedContextualFallacyAnalyzer
from argumentation_analysis.utils.text_processing import split_text_into_arguments

@pytest.fixture(scope="module")
def crypto_service():
    """Fixture pour initialiser le CryptoService avec une clé générée."""
    key = CryptoService.generate_static_key()
    return CryptoService(encryption_key=key)

@pytest.fixture(scope="module")
def complex_rhetorical_text():
    """
    Fournit un texte avec une argumentation complexe et des sophismes imbriqués.
    Le texte est conçu pour être difficile à analyser pour des mocks.
    """
    return (
        "Si nous autorisons l'installation de cette simple antenne 5G, cela mènera inévitablement à une surveillance de masse généralisée. "
        "De la surveillance de masse, nous passerons à un contrôle total de nos vies par le gouvernement. "
        "Et de là, il n'y a qu'un pas vers un régime totalitaire. "
        "Nous devons donc choisir : soit nous interdisons cette antenne pour préserver notre liberté, soit nous acceptons la tyrannie."
    )

def test_full_crypto_rhetoric_pipeline(crypto_service, complex_rhetorical_text, tmp_path):
    """
    Teste le pipeline complet : chiffrement, déchiffrement et analyse rhétorique.
    """
    # 1. Chiffrement du texte
    start_time_encrypt = time.time()
    encrypted_text = crypto_service.encrypt_data(complex_rhetorical_text.encode('utf-8'))
    end_time_encrypt = time.time()
    assert encrypted_text is not None
    print(f"\nTexte chiffré : {encrypted_text.hex()}")
    print(f"Temps de chiffrement : {end_time_encrypt - start_time_encrypt:.4f}s")

    # 2. Déchiffrement du texte
    start_time_decrypt = time.time()
    decrypted_text_bytes = crypto_service.decrypt_data(encrypted_text)
    end_time_decrypt = time.time()
    assert decrypted_text_bytes is not None
    decrypted_text = decrypted_text_bytes.decode('utf-8')
    print(f"Texte déchiffré : {decrypted_text}")
    print(f"Temps de déchiffrement : {end_time_decrypt - start_time_decrypt:.4f}s")
    assert decrypted_text == complex_rhetorical_text

    # 3. Analyse rhétorique
    complex_analyzer = EnhancedComplexFallacyAnalyzer()
    contextual_analyzer = EnhancedContextualFallacyAnalyzer()
    
    arguments = split_text_into_arguments(decrypted_text)
    analysis_context = "test_scenario_complexe"

    start_time_analysis = time.time()
    complex_fallacies = complex_analyzer.detect_composite_fallacies(arguments, analysis_context)
    contextual_fallacies = contextual_analyzer.analyze_context(decrypted_text, analysis_context)
    end_time_analysis = time.time()

    print(f"Temps d'analyse rhétorique : {end_time_analysis - start_time_analysis:.4f}s")

    # 4. Validation des résultats
    print("\n--- Résultats de l'analyse des sophismes complexes ---")
    print(complex_fallacies)
    assert any('Pente glissante' in comp['fallacy_type'] for comb in complex_fallacies.get('basic_combinations', []) for comp in comb.get('component_fallacies', [])), "Le sophisme 'Pente glissante' n'a pas été détecté."

    print("\n--- Résultats de l'analyse des sophismes contextuels ---")
    print(contextual_fallacies)
    assert any('Faux dilemme' in f['fallacy_type'] for f in contextual_fallacies.get('contextual_fallacies', [])), "Le sophisme 'Faux dilemme' n'a pas été détecté."