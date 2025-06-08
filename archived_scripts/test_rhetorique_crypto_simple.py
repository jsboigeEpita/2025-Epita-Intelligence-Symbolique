#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simple d'investigation des fonctionnalités rhétoriques et crypto.
"""

import sys
import os
import json
import traceback

def test_imports():
    """Test d'importation des modules principaux."""
    print("=" * 60)
    print("TEST: Imports des modules")
    print("=" * 60)
    
    success = 0
    total = 0
    
    # Test ComplexFallacyAnalyzer
    total += 1
    try:
        from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
        print("[OK] ComplexFallacyAnalyzer importe")
        success += 1
    except Exception as e:
        print(f"[ERREUR] ComplexFallacyAnalyzer: {e}")
    
    # Test ContextualFallacyAnalyzer
    total += 1
    try:
        from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
        print("[OK] ContextualFallacyAnalyzer importe")
        success += 1
    except Exception as e:
        print(f"[ERREUR] ContextualFallacyAnalyzer: {e}")
    
    # Test FallacySeverityEvaluator
    total += 1
    try:
        from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
        print("[OK] FallacySeverityEvaluator importe")
        success += 1
    except Exception as e:
        print(f"[ERREUR] FallacySeverityEvaluator: {e}")
    
    # Test crypto_utils
    total += 1
    try:
        from argumentation_analysis.utils.core_utils.crypto_utils import derive_encryption_key
        print("[OK] crypto_utils importe")
        success += 1
    except Exception as e:
        print(f"[ERREUR] crypto_utils: {e}")
    
    # Test CryptoService
    total += 1
    try:
        from argumentation_analysis.services.crypto_service import CryptoService
        print("[OK] CryptoService importe")
        success += 1
    except Exception as e:
        print(f"[ERREUR] CryptoService: {e}")
    
    print(f"\nResultat imports: {success}/{total} reussis")
    return success, total

def test_crypto_fonctionnel():
    """Test fonctionnel du système crypto."""
    print("=" * 60)
    print("TEST: Fonctionnalités crypto")
    print("=" * 60)
    
    try:
        from argumentation_analysis.utils.core_utils.crypto_utils import (
            derive_encryption_key, 
            encrypt_data_with_fernet, 
            decrypt_data_with_fernet
        )
        
        # Test complet
        passphrase = "test_investigation_2025"
        test_data = b"Test donnees crypto pour analyse rhetorique"
        
        key = derive_encryption_key(passphrase)
        if not key:
            print("[ERREUR] Derivation de cle echouee")
            return False
        print("[OK] Derivation de cle reussie")
        
        encrypted = encrypt_data_with_fernet(test_data, key)
        if not encrypted:
            print("[ERREUR] Chiffrement echoue")
            return False
        print("[OK] Chiffrement reussi")
        
        decrypted = decrypt_data_with_fernet(encrypted, key)
        if decrypted != test_data:
            print("[ERREUR] Dechiffrement echoue")
            return False
        print("[OK] Dechiffrement reussi")
        
        print("[OK] Test crypto complet reussi")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test crypto: {e}")
        return False

def test_rhetorique_fonctionnel():
    """Test fonctionnel des analyseurs rhétoriques."""
    print("=" * 60)
    print("TEST: Analyseurs rhetoriques")
    print("=" * 60)
    
    try:
        from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
        
        analyzer = ComplexFallacyAnalyzer()
        print("[OK] ComplexFallacyAnalyzer initialise")
        
        # Test avec un argument contenant des sophismes
        test_argument = "Les experts disent que ce produit est excellent. Des millions de personnes l'utilisent deja, donc il doit etre bon. Si vous ne l'achetez pas maintenant, vous le regretterez."
        
        # Test combinaisons
        combinaisons = analyzer.identify_combined_fallacies(test_argument)
        print(f"[OK] Combinaisons detectees: {len(combinaisons)}")
        
        # Test motifs
        motifs = analyzer.identify_fallacy_patterns(test_argument)
        print(f"[OK] Motifs detectes: {len(motifs)}")
        
        print("[OK] Test rhetorique complet reussi")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Test rhetorique: {e}")
        traceback.print_exc()
        return False

def check_outils_chiffrement():
    """Vérification des outils de chiffrement."""
    print("=" * 60)
    print("INVESTIGATION: Outils chiffrement")
    print("=" * 60)
    
    encryption_dir = "argumentation_analysis/agents/tools/encryption"
    if os.path.exists(encryption_dir):
        files = [f for f in os.listdir(encryption_dir) if f.endswith('.py')]
        print(f"[OK] Repertoire encryption: {len(files)} fichiers Python")
        for file in files:
            print(f"  - {file}")
        return len(files) > 0
    else:
        print("[INFO] Repertoire encryption non trouve")
        return False

def analyse_enhanced_tools():
    """Analyse des outils enhanced."""
    print("=" * 60)
    print("INVESTIGATION: Outils enhanced")
    print("=" * 60)
    
    enhanced_dir = "argumentation_analysis/agents/tools/analysis/enhanced"
    if os.path.exists(enhanced_dir):
        files = [f for f in os.listdir(enhanced_dir) if f.endswith('.py')]
        print(f"[OK] Repertoire enhanced: {len(files)} fichiers Python")
        
        # Test import des enhanced
        success = 0
        for file in files:
            if file.startswith('test_') or file == '__init__.py':
                continue
            module_name = file[:-3]  # Remove .py
            try:
                # Import dynamique
                module_path = f"argumentation_analysis.agents.tools.analysis.enhanced.{module_name}"
                __import__(module_path)
                print(f"  [OK] {module_name}")
                success += 1
            except Exception as e:
                print(f"  [ERREUR] {module_name}: {e}")
        
        return success > 0
    else:
        print("[INFO] Repertoire enhanced non trouve")
        return False

def main():
    """Investigation principale."""
    print("INVESTIGATION FONCTIONNALITES RHETORIQUE-CRYPTO")
    print("=" * 80)
    
    resultats = {}
    
    # Tests d'imports
    success_imports, total_imports = test_imports()
    resultats['imports'] = success_imports == total_imports
    
    # Tests fonctionnels
    resultats['crypto_fonctionnel'] = test_crypto_fonctionnel()
    resultats['rhetorique_fonctionnel'] = test_rhetorique_fonctionnel()
    
    # Investigations
    resultats['outils_chiffrement'] = check_outils_chiffrement()
    resultats['outils_enhanced'] = analyse_enhanced_tools()
    
    # Résumé
    print("\n" + "=" * 80)
    print("RESUME INVESTIGATION")
    print("=" * 80)
    
    success_count = sum(1 for v in resultats.values() if v)
    total_count = len(resultats)
    
    print(f"Tests reussis: {success_count}/{total_count}")
    print(f"Taux de reussite: {(success_count/total_count)*100:.1f}%")
    
    print("\nDetail:")
    for test, result in resultats.items():
        status = "[OK]" if result else "[KO]"
        print(f"  {status} {test}")
    
    # Recommandations
    print("\nRECOMMANDATIONS:")
    if not resultats['imports']:
        print("- Verifier les dependances manquantes")
    if not resultats['crypto_fonctionnel']:
        print("- Diagnostiquer les problemes de chiffrement")
    if not resultats['rhetorique_fonctionnel']:
        print("- Verifier la taxonomie des sophismes")
    if success_count == total_count:
        print("- Tous les tests passent : systeme fonctionnel")
    
    # Sauvegarde
    rapport = {
        "date": "2025-01-08",
        "investigation": "crypto-rhetorique",
        "resultats": resultats,
        "taux_reussite": f"{success_count}/{total_count}",
        "imports_status": f"{success_imports}/{total_imports}",
        "statut": "FONCTIONNEL" if success_count == total_count else "PARTIEL"
    }
    
    with open("rapport_investigation_crypto_rhetorique.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    
    print(f"\nRapport sauvegarde: rapport_investigation_crypto_rhetorique.json")
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)