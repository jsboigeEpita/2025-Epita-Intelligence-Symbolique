#!/usr/bin/env python3
"""
Test minimal pour diagnostiquer le blocage JTMS
"""
import sys
import traceback

print("=== DÉBUT TEST DIAGNOSTIC ===")

def test_imports_basiques():
    print("1. Test imports basiques...")
    try:
        import flask
        print(f"   ✅ Flask {flask.__version__}")
    except Exception as e:
        print(f"   ❌ Flask: {e}")
    
    try:
        import asyncio
        print("   ✅ Asyncio")
    except Exception as e:
        print(f"   ❌ Asyncio: {e}")

def test_auto_env():
    print("2. Test auto_env...")
    try:
        # Ne pas importer auto_env directement - juste tester sa présence
        import os
        from pathlib import Path
        auto_env_path = Path("scripts/core/auto_env.py")
        if auto_env_path.exists():
            print("   ✅ auto_env.py existe")
        else:
            print("   ❌ auto_env.py introuvable")
    except Exception as e:
        print(f"   ❌ auto_env: {e}")

def test_imports_jtms_simple():
    print("3. Test imports JTMS (sans auto_env)...")
    try:
        # Test sans activation d'environnement
        sys.path.append('.')
        from argumentation_analysis.services.jtms_service import JTMSService
        print("   ✅ JTMSService importé")
    except ImportError as e:
        print(f"   ⚠️ JTMSService manquant: {e}")
    except Exception as e:
        print(f"   ❌ JTMSService erreur: {e}")
        traceback.print_exc()

def test_service_manager():
    print("4. Test ServiceManager...")
    try:
        from argumentation_analysis.orchestration.service_manager import ServiceManager
        print("   ✅ ServiceManager importé")
    except ImportError as e:
        print(f"   ⚠️ ServiceManager manquant: {e}")
    except Exception as e:
        print(f"   ❌ ServiceManager erreur: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        test_imports_basiques()
        test_auto_env()
        test_imports_jtms_simple()
        test_service_manager()
        print("=== TEST TERMINÉ AVEC SUCCÈS ===")
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}")
        traceback.print_exc()
    finally:
        print("=== FIN DU TEST ===")