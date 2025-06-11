#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'investigation systématique des fonctionnalités rhétoriques et crypto.
"""

import sys
import os
import json
import traceback

def test_complex_fallacy_analyzer():
    """Test de l'analyseur de sophismes complexes."""
    print("=" * 60)
    print("TEST: Complex Fallacy Analyzer")
    print("=" * 60)
    try:
        from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
        print("[OK] Import ComplexFallacyAnalyzer reussi")
        
        analyzer = ComplexFallacyAnalyzer()
        print("[OK] Initialisation ComplexFallacyAnalyzer reussie")
        
        # Test d'identification de combinaisons
        test_text = "Les experts sont unanimes : ce produit est sûr. Des millions l'utilisent déjà, donc vous devriez l'essayer aussi."
        results = analyzer.identify_combined_fallacies(test_text)
        print(f"[OK] Test combinaisons sophismes: {len(results)} detectees")
        
        # Test de motifs
        test_patterns = analyzer.identify_fallacy_patterns(test_text + "\n\nSi vous n'agissez pas maintenant, vous le regretterez.")
        print(f"[OK] Test motifs sophismes: {len(test_patterns)} detectes")
        
        return True
    except Exception as e:
        print(f"[ERREUR] ComplexFallacyAnalyzer: {e}")
        traceback.print_exc()
        return False

def test_contextual_fallacy_analyzer():
    """Test de l'analyseur contextuel de sophismes."""
    print("=" * 60)
    print("TEST: Contextual Fallacy Analyzer")
    print("=" * 60)
    try:
        from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
        print("[OK] Import ContextualFallacyAnalyzer reussi")
        
        analyzer = ContextualFallacyAnalyzer()
        print("[OK] Initialisation ContextualFallacyAnalyzer reussie")
        return True
    except Exception as e:
        print(f"[ERREUR] ContextualFallacyAnalyzer: {e}")
        traceback.print_exc()
        return False

def test_crypto_utils():
    """Test des utilitaires de chiffrement."""
    print("=" * 60)
    print("TEST: Crypto Utils")
    print("=" * 60)
    try:
        from argumentation_analysis.utils.core_utils.crypto_utils import (
            derive_encryption_key, 
            encrypt_data_with_fernet, 
            decrypt_data_with_fernet
        )
        print("[OK] Import crypto_utils reussi")
        
        # Test de dérivation de clé
        passphrase = "test_passphrase_investigation"
        key = derive_encryption_key(passphrase)
        if key:
            print("[OK] Derivation de cle reussie")
        else:
            print("[ERREUR] Derivation de cle echouee")
            return False
        
        # Test de chiffrement/déchiffrement
        test_data = b"Donnees de test pour investigation crypto-rhetorique"
        encrypted = encrypt_data_with_fernet(test_data, key)
        if encrypted:
            print("[OK] Chiffrement reussi")
        else:
            print("[ERREUR] Chiffrement echoue")
            return False
        
        decrypted = decrypt_data_with_fernet(encrypted, key)
        if decrypted == test_data:
            print("[OK] Dechiffrement reussi")
        else:
            print("[ERREUR] Dechiffrement echoue")
            return False
        
        return True
    except Exception as e:
        print(f"[ERREUR] crypto_utils: {e}")
        traceback.print_exc()
        return False

def test_crypto_service():
    """Test du service de chiffrement."""
    print("=" * 60)
    print("TEST: Crypto Service")
    print("=" * 60)
    try:
        from argumentation_analysis.services.crypto_service import CryptoService
        print("✓ Import CryptoService réussi")
        
        service = CryptoService()
        print("✓ Initialisation CryptoService réussie")
        
        # Test de dérivation de clé
        passphrase = "test_service_passphrase"
        key = service.derive_key_from_passphrase(passphrase)
        if key:
            print("✓ Dérivation de clé service réussie")
            service.set_encryption_key(key)
        else:
            print("✗ Dérivation de clé service échouée")
            return False
        
        # Test de chiffrement/déchiffrement
        test_data = b"Test service crypto pour analyse rhetorique"
        encrypted = service.encrypt_data(test_data)
        if encrypted:
            print("✓ Chiffrement service réussi")
        else:
            print("✗ Chiffrement service échoué")
            return False
        
        decrypted = service.decrypt_data(encrypted)
        if decrypted == test_data:
            print("✓ Déchiffrement service réussi")
        else:
            print("✗ Déchiffrement service échoué")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Erreur CryptoService: {e}")
        traceback.print_exc()
        return False

def test_severity_evaluator():
    """Test de l'évaluateur de sévérité."""
    print("=" * 60)
    print("TEST: Fallacy Severity Evaluator")
    print("=" * 60)
    try:
        from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
        print("✓ Import FallacySeverityEvaluator réussi")
        
        evaluator = FallacySeverityEvaluator()
        print("✓ Initialisation FallacySeverityEvaluator réussie")
        return True
    except Exception as e:
        print(f"✗ Erreur FallacySeverityEvaluator: {e}")
        traceback.print_exc()
        return False

def check_encryption_tools():
    """Vérification des outils de chiffrement dans agents/tools/encryption."""
    print("=" * 60)
    print("INVESTIGATION: Outils de chiffrement")
    print("=" * 60)
    
    encryption_dir = "argumentation_analysis/agents/tools/encryption"
    if os.path.exists(encryption_dir):
        files = os.listdir(encryption_dir)
        print(f"✓ Répertoire encryption trouvé avec {len(files)} fichiers:")
        for file in files:
            if file.endswith('.py'):
                print(f"  - {file}")
        return True
    else:
        print("✗ Répertoire encryption non trouvé")
        return False

def main():
    """Fonction principale d'investigation."""
    print("INVESTIGATION SYSTEMATIQUE DES FONCTIONNALITES RHETORIQUE-CRYPTO")
    print("=" * 80)
    
    results = {}
    
    # Tests des analyseurs rhétoriques
    results['complex_fallacy'] = test_complex_fallacy_analyzer()
    results['contextual_fallacy'] = test_contextual_fallacy_analyzer()
    results['severity_evaluator'] = test_severity_evaluator()
    
    # Tests des systèmes de chiffrement
    results['crypto_utils'] = test_crypto_utils()
    results['crypto_service'] = test_crypto_service()
    
    # Investigation des outils
    results['encryption_tools'] = check_encryption_tools()
    
    # Résumé
    print("\n" + "=" * 80)
    print("RESUME DE L'INVESTIGATION")
    print("=" * 80)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"Tests réussis: {success_count}/{total_count}")
    print("\nDétail des résultats:")
    for test_name, success in results.items():
        status = "✓ REUSSI" if success else "✗ ECHEC"
        print(f"  {test_name}: {status}")
    
    if success_count == total_count:
        print("\n🎉 INVESTIGATION COMPLETE: Toutes les fonctionnalités testées avec succès!")
    else:
        print(f"\n⚠️  INVESTIGATION PARTIELLE: {total_count - success_count} problèmes détectés")
    
    # Sauvegarde du rapport
    report = {
        "investigation_date": "2025-01-08",
        "investigation_type": "crypto-rhetorique",
        "results": results,
        "success_rate": f"{success_count}/{total_count}",
        "recommendations": [
            "Analyser les échecs pour identifier les dépendances manquantes",
            "Tester l'intégration crypto-rhétorique end-to-end",
            "Valider les performances sur des textes chiffrés volumineux"
        ]
    }
    
    with open("investigation_rhetorique_crypto_rapport.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Rapport sauvegardé: investigation_rhetorique_crypto_rapport.json")

if __name__ == "__main__":
    main()