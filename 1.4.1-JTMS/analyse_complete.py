#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ANALYSE COMPLÈTE DU MODULE JTMS ÉTUDIANT
========================================
"""

print("=== ANALYSE JTMS CONTRIBUTION ÉTUDIANTE ===\n")

# Test 1: Import et création instance
print("1. TEST IMPORT ET INSTANCE")
try:
    from jtms import JTMS, Belief, Justification
    from belifs_loader import load_beliefs
    
    jtms = JTMS()
    print("✓ Instance JTMS créée avec succès")
except Exception as e:
    print(f"✗ Erreur création: {e}")
    exit(1)

# Test 2: Fonctionnalités de base
print("\n2. TEST FONCTIONNALITÉS DE BASE")
try:
    # Ajout beliefs
    jtms.add_belief("A")
    jtms.add_belief("B") 
    jtms.add_belief("C")
    print(f"✓ Beliefs ajoutées: {list(jtms.beliefs.keys())}")
    
    # Justification simple 
    jtms.add_justification(["A"], [], "B")  # B vrai si A vrai
    print("✓ Justification ajoutée: A -> B")
    
    # Test propagation
    jtms.set_belief_validity("A", True)
    print(f"✓ A défini à True, B devient: {jtms.beliefs['B'].valid}")
    
except Exception as e:
    print(f"✗ Erreur fonctionnalités de base: {e}")

# Test 3: Test avec loader JSON
print("\n3. TEST LOADER BELIEFS JSON")
try:
    jtms_json = JTMS()
    load_beliefs("simple_beliefs.json", jtms_json)
    print(f"✓ Beliefs chargées depuis JSON: {list(jtms_json.beliefs.keys())}")
    
    # Affichage états
    for name, belief in jtms_json.beliefs.items():
        print(f"  - {name}: {belief.valid}")
        
except Exception as e:
    print(f"✗ Erreur loader JSON: {e}")

# Test 4: Fonctionnalités avancées
print("\n4. TEST FONCTIONNALITÉS AVANCÉES")
try:
    jtms_adv = JTMS()
    
    # Test justifications complexes
    for letter in "ABCD":
        jtms_adv.add_belief(letter)
    
    # A et B -> C
    jtms_adv.add_justification(["A", "B"], [], "C")
    # C et NOT D -> résultat
    jtms_adv.add_justification(["C"], ["D"], "result")
    
    jtms_adv.set_belief_validity("A", True)
    jtms_adv.set_belief_validity("B", True) 
    jtms_adv.set_belief_validity("D", False)
    
    print("✓ Justifications complexes testées")
    print(f"  - Résultat: {jtms_adv.beliefs.get('result', {}).valid if 'result' in jtms_adv.beliefs else 'N/A'}")
    
except Exception as e:
    print(f"✗ Erreur fonctionnalités avancées: {e}")

# Test 5: Évaluation robustesse
print("\n5. TEST ROBUSTESSE")
try:
    jtms_robust = JTMS(strict=True)
    jtms_robust.add_belief("test")
    
    # Test erreur belief inexistante en mode strict
    try:
        jtms_robust.add_justification(["inexistant"], [], "test")
        print("✗ Mode strict non respecté")
    except KeyError:
        print("✓ Mode strict fonctionne correctement")
        
    # Test suppression belief
    jtms_robust.remove_belief("test")
    print("✓ Suppression belief fonctionne")
    
except Exception as e:
    print(f"✗ Erreur robustesse: {e}")

# Test 6: Analyse code qualité
print("\n6. ANALYSE QUALITÉ CODE")

# Vérification présence méthodes essentielles
required_methods = ['add_belief', 'remove_belief', 'add_justification', 'set_belief_validity']
missing_methods = []

for method in required_methods:
    if not hasattr(JTMS, method):
        missing_methods.append(method)

if missing_methods:
    print(f"✗ Méthodes manquantes: {missing_methods}")
else:
    print("✓ Toutes les méthodes essentielles présentes")

# Test visualisation si disponible
print("\n7. TEST VISUALISATION")
try:
    if hasattr(jtms, 'visualize'):
        print("✓ Méthode visualize() présente")
        # jtms.visualize()  # Commenté pour éviter ouverture fichier
    else:
        print("✗ Méthode visualize() manquante")
except Exception as e:
    print(f"✗ Erreur visualisation: {e}")

print("\n=== FIN ANALYSE ===")