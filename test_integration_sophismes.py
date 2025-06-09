#!/usr/bin/env python3
"""
Test d'intégration pour validation du système de détection de sophismes
=====================================================================

Script de test pour valider l'interface simple Flask avec le texte utilisateur
contenant des sophismes variés.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Texte de test utilisateur avec sophismes
TEXTE_TEST_SOPHISMES = """
Franchement, si on commence à interdire les voitures en ville, bientôt on interdira les poussettes et les fauteuils roulants — c'est le début de la fin. Tout le monde sait que les écolos sont des hypocrites : ils prennent l'avion pour aller à Bali en prêchant la décroissance. Et puis, regarde ton voisin : il est pour les zones piétonnes, et il est au chômage — coïncidence ? Je ne crois pas. De toute façon, personne d'intelligent ne soutient ces mesures extrêmes. Si c'était vraiment une bonne idée, tout le monde le ferait déjà. En plus, la pollution n'a jamais empêché nos grands-parents de vivre centenaires, alors pourquoi s'inquiéter maintenant ? Ne pas être d'accord avec moi, c'est forcément vouloir qu'on vive tous enfermés. Et entre nous, vu que cette idée vient du gouvernement, on sait bien que c'est louche. Enfin bon, moi je dis ça, je dis rien — mais vous voilà prévenus.
"""

# Configuration
BASE_URL = "http://localhost:3000"
TIMEOUT = 30

# Exemples de sophismes spécifiques pour Phase 3
SOPHISMES_SPECIFIQUES = [
    {
        "name": "ad_hominem",
        "text": "Tu ne peux pas critiquer le gouvernement, tu n'es même pas citoyen",
        "expected": "ad hominem"
    },
    {
        "name": "faux_dilemme",
        "text": "Soit tu es avec nous, soit tu es contre nous",
        "expected": "false dilemma"
    },
    {
        "name": "appel_popularite",
        "text": "Tout le monde fait ça, donc c'est normal",
        "expected": "bandwagon"
    }
]

def test_status_endpoint():
    """Teste l'endpoint de statut"""
    print("[TEST] Vérification de l'endpoint /status...")
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            print(f"[OK] Status: {status_data.get('status', 'inconnu')}")
            print(f"[OK] ServiceManager: {status_data.get('service_manager_available', False)}")
            print(f"[OK] Analyseurs: {status_data.get('fallacy_analyzers_available', False)}")
            return True
        else:
            print(f"[ERROR] Status endpoint retourne {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Erreur lors du test status: {e}")
        return False

def test_analyze_endpoint():
    """Teste l'endpoint d'analyse avec le texte de sophismes"""
    print("\n[TEST] Analyse du texte contenant des sophismes...")
    print(f"[INFO] Texte à analyser: {len(TEXTE_TEST_SOPHISMES)} caractères")
    
    try:
        # Préparation de la requête
        data = {
            'text': TEXTE_TEST_SOPHISMES,
            'analysis_type': 'complete'
        }
        
        print("[INFO] Envoi de la requête d'analyse...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/analyze", 
            json=data, 
            timeout=TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            print(f"[OK] Analyse terminée en {processing_time:.2f}s")
            return analyze_results(response.json(), processing_time)
        else:
            print(f"[ERROR] Analyse échouée avec status {response.status_code}")
            print(f"[ERROR] Réponse: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'analyse: {e}")
        return False

def test_specific_sophismes():
    """Teste les sophismes spécifiques de la Phase 3"""
    print("\n[TEST PHASE 3] Analyse des sophismes spécifiques...")
    results = []
    
    for sophisme in SOPHISMES_SPECIFIQUES:
        print(f"\n[TEST] {sophisme['name']}: {sophisme['text']}")
        
        try:
            data = {
                'text': sophisme['text'],
                'analysis_type': 'fallacy_detection'
            }
            
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/analyze",
                json=data,
                timeout=TIMEOUT,
                headers={'Content-Type': 'application/json'}
            )
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                
                # Vérifier si des sophismes sont détectés
                sophismes_detectes = 0
                servicemanager_used = 'analysis_id' in result_data
                
                if 'results' in result_data:
                    analysis_results = result_data['results']
                    if 'fallacies' in analysis_results:
                        sophismes_detectes = len(analysis_results['fallacies'])
                    elif 'fallacy_analysis' in analysis_results:
                        sophismes_detectes = analysis_results['fallacy_analysis'].get('total_fallacies', 0)
                
                test_result = {
                    'name': sophisme['name'],
                    'success': sophismes_detectes > 0,
                    'response_time': processing_time,
                    'servicemanager_used': servicemanager_used,
                    'fallacies_count': sophismes_detectes
                }
                
                print(f"[RESULTAT] Sophismes détectés: {sophismes_detectes}")
                print(f"[RESULTAT] ServiceManager: {'Oui' if servicemanager_used else 'Non'}")
                print(f"[RESULTAT] Temps: {processing_time:.2f}s")
                
                results.append(test_result)
                
            else:
                print(f"[ERREUR] Status {response.status_code}")
                results.append({
                    'name': sophisme['name'],
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                })
        
        except Exception as e:
            print(f"[ERREUR] Exception: {e}")
            results.append({
                'name': sophisme['name'],
                'success': False,
                'error': str(e)
            })
        
        time.sleep(0.5)  # Pause entre les tests
    
    # Résumé des tests Phase 3
    print(f"\n[PHASE 3 RESUMÉ]")
    successful_tests = sum(1 for r in results if r.get('success', False))
    total_tests = len(results)
    servicemanager_usage = sum(1 for r in results if r.get('servicemanager_used', False))
    
    print(f"Tests réussis: {successful_tests}/{total_tests}")
    print(f"Usage ServiceManager: {servicemanager_usage}/{total_tests}")
    
    if successful_tests >= total_tests * 0.8:  # 80% de réussite
        print("[SUCCESS] Phase 3 validation réussie!")
        return True
    else:
        print("[WARNING] Phase 3 validation partielle")
        return False

def analyze_results(results: Dict[str, Any], processing_time: float):
    """Analyse les résultats retournés par l'API"""
    print("\n" + "="*60)
    print("ANALYSE DES RÉSULTATS")
    print("="*60)
    
    # Informations générales
    print(f"[MÉTRIQUES] Temps de traitement: {processing_time:.2f}s")
    print(f"[MÉTRIQUES] Taille de la réponse: {len(str(results))} caractères")
    
    # Structure des résultats
    print(f"\n[STRUCTURE] Clés présentes: {list(results.keys())}")
    
    # Analyse des sophismes détectés
    if 'fallacy_analysis' in results:
        fallacy_data = results['fallacy_analysis']
        total_fallacies = fallacy_data.get('total_fallacies', 0)
        print(f"[SOPHISMES] Total détecté: {total_fallacies}")
        
        if total_fallacies > 0:
            print("[SUCCESS] Détection de sophismes fonctionnelle!")
            
            # Détail des sophismes détectés
            if 'fallacies' in fallacy_data:
                fallacies = fallacy_data['fallacies']
                print(f"[DÉTAIL] Sophismes détectés:")
                for i, fallacy in enumerate(fallacies[:5], 1):  # Limite à 5 pour lisibilité
                    fallacy_type = fallacy.get('type', 'Type inconnu')
                    confidence = fallacy.get('confidence', 0)
                    text = fallacy.get('text', '')[:50] + "..." if len(fallacy.get('text', '')) > 50 else fallacy.get('text', '')
                    print(f"   {i}. {fallacy_type} (confiance: {confidence:.2f}) - \"{text}\"")
                
                if len(fallacies) > 5:
                    print(f"   ... et {len(fallacies) - 5} autres")
        else:
            print("[WARNING] Aucun sophisme détecté (pourrait indiquer un problème)")
    
    # Vérification des composants utilisés
    if 'components_used' in results:
        components = results['components_used']
        print(f"\n[COMPOSANTS] Utilisés: {components}")
        
        # Vérification que les vrais analyseurs sont utilisés
        expected_components = ['ComplexFallacyAnalyzer', 'ContextualFallacyAnalyzer']
        components_found = [comp for comp in expected_components if comp in str(components)]
        
        if components_found:
            print(f"[SUCCESS] Vrais analyseurs détectés: {components_found}")
        else:
            print("[WARNING] Analyseurs basiques utilisés (mode dégradé)")
    
    # Validation finale
    success_criteria = [
        total_fallacies > 0 if 'fallacy_analysis' in results else False,
        processing_time < 30,  # Temps raisonnable
        'fallacy_analysis' in results
    ]
    
    success = all(success_criteria)
    
    print(f"\n[RÉSULTAT FINAL] {'SUCCESS' if success else 'PARTIAL'}")
    print("="*60)
    
    return success

def save_results(results: Dict[str, Any]):
    """Sauvegarde les résultats pour documentation"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"logs/test_integration_sophismes_{timestamp}.json"
    
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Résultats sauvegardés dans {filename}")
    except Exception as e:
        print(f"[WARNING] Impossible de sauvegarder: {e}")

def main():
    """Point d'entrée principal"""
    print("[TEST] VALIDATION INTÉGRATION API/SERVICEMANAGER - PHASE 3")
    print("=" * 60)
    print(f"Cible: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results_summary = {
        'status_test': False,
        'analyze_test': False,
        'phase3_sophismes': False,
        'overall_success': False
    }
    
    # 1. Test de connectivité
    print("\n[ÉTAPE 1] Test de connectivité API...")
    if not test_status_endpoint():
        print("[FATAL] Impossible de contacter l'interface. Test interrompu.")
        return False
    results_summary['status_test'] = True
    
    # 2. Test d'analyse générale
    print("\n[ÉTAPE 2] Test d'analyse générale...")
    results_summary['analyze_test'] = test_analyze_endpoint()
    
    # 3. Tests spécifiques Phase 3
    print("\n[ÉTAPE 3] Tests spécifiques Phase 3...")
    results_summary['phase3_sophismes'] = test_specific_sophismes()
    
    # 4. Résumé final
    print("\n" + "="*60)
    print("RÉSUMÉ VALIDATION PHASE 3")
    print("="*60)
    print(f"✓ Test connectivité: {'OK' if results_summary['status_test'] else 'ÉCHEC'}")
    print(f"✓ Test analyse générale: {'OK' if results_summary['analyze_test'] else 'ÉCHEC'}")
    print(f"✓ Tests sophismes Phase 3: {'OK' if results_summary['phase3_sophismes'] else 'ÉCHEC'}")
    
    # Critères de validation Phase 3
    phase3_success = (
        results_summary['status_test'] and
        results_summary['analyze_test'] and
        results_summary['phase3_sophismes']
    )
    
    results_summary['overall_success'] = phase3_success
    
    if phase3_success:
        print("\n[SUCCESS] PHASE 3 VALIDÉE avec succès!")
        print("✅ Intégration API/ServiceManager opérationnelle")
        print("✅ Détection de sophismes fonctionnelle")
        print("✅ Analyses en temps réel validées")
    else:
        print("\n[PARTIAL] PHASE 3 validation partielle")
        print("Système fonctionnel mais optimisations nécessaires")
    
    return phase3_success

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Test interrompu par l'utilisateur")
        exit(1)
    except Exception as e:
        print(f"\n[FATAL] Erreur critique: {e}")
        exit(1)