#!/usr/bin/env python3
"""Script de test pour vérifier tous les imports de l'AXE B JTMS"""

def test_imports():
    print("=== VALIDATION DES IMPORTS AXE B - PLUGIN SEMANTIC KERNEL JTMS ===")
    
    # Test des imports principaux
    try:
        from argumentation_analysis.services.jtms_service import JTMSService
        print("[OK] Service JTMS: Import réussi")
    except Exception as e:
        print(f"[ERREUR] Service JTMS: {e}")
        return False
    
    try:
        from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager
        print("[OK] Session Manager: Import réussi")
    except Exception as e:
        print(f"[ERREUR] Session Manager: {e}")
        return False
    
    try:
        from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import JTMSSemanticKernelPlugin
        print("[OK] Plugin SK: Import réussi")
    except Exception as e:
        print(f"[ERREUR] Plugin SK: {e}")
        return False
    
    try:
        import argumentation_analysis.api.jtms_models
        print("[OK] Modèles API: Import réussi")
    except Exception as e:
        print(f"[ERREUR] Modèles API: {e}")
        return False
    
    try:
        import argumentation_analysis.api.jtms_endpoints
        print("[OK] Endpoints API: Import réussi")
    except Exception as e:
        print(f"[ERREUR] Endpoints API: {e}")
        return False
    
    try:
        import argumentation_analysis.integrations.semantic_kernel_integration
        print("[OK] Intégrations SK: Import réussi")
    except Exception as e:
        print(f"[ERREUR] Intégrations SK: {e}")
        return False
    
    print("\n=== TOUS LES IMPORTS VALIDÉS AVEC SUCCÈS ===")
    return True

if __name__ == "__main__":
    test_imports()