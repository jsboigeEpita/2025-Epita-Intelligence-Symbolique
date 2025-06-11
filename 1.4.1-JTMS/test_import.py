#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    import jtms
    print("✓ Module JTMS importé avec succès")
    
    # Test création instance
    jtms_instance = jtms.JTMS()
    print("✓ Instance JTMS créée")
    
    # Test ajout belief
    jtms_instance.add_belief("test")
    print("✓ Belief ajoutée")
    
    print(f"✓ Beliefs dans JTMS: {list(jtms_instance.beliefs.keys())}")
    
except ImportError as e:
    print(f"✗ Erreur import: {e}")
except Exception as e:
    print(f"✗ Erreur: {e}")