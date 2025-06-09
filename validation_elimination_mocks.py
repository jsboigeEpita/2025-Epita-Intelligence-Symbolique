#!/usr/bin/env python3
"""
Script de validation pour confirmer l'élimination des mocks
et la restauration des connexions réelles.
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Configuration
sys.path.append('.')

# Charger la clé OpenAI du .env
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.split('=', 1)[1].strip()
            os.environ['OPENAI_API_KEY'] = api_key
            break

def print_header(title):
    """Affiche un en-tête formaté."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, success, details=""):
    """Affiche le résultat d'un test."""
    status = "[OK] SUCCES" if success else "[!!] ECHEC"
    print(f"{status} {test_name}")
    if details:
        print(f"   -> {details}")

def validate_openai_connection():
    """Valide la connexion OpenAI réelle."""
    try:
        import openai
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': 'Test connexion. Répondez: CONNEXION_VALIDE'}],
            max_tokens=10,
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        return True, f"Réponse: {content}"
        
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def validate_mock_files_eliminated():
    """Valide que les fichiers de mock obsolètes ont été supprimés."""
    eliminated_files = [
        "tests/unit/mocks/test_mock_vs_real_behavior.py",
        "tests/unit/mocks/test_numpy_rec_mock.py",
        "archived_scripts/phase3_complex_diagnostics.py",
        "archived_scripts/phase3_final_solution.py",
        "archived_scripts/test_phase2_stabilized.py",
        "archived_scripts/test_phase3_complex_fixes.py",
        "archived_scripts/test_phase3_final_validation.py"
    ]
    
    results = []
    for file_path in eliminated_files:
        exists = Path(file_path).exists()
        results.append((file_path, not exists))
        
    all_eliminated = all(result[1] for result in results)
    
    details = f"{sum(1 for _, eliminated in results if eliminated)}/{len(results)} fichiers éliminés"
    return all_eliminated, details

def validate_numpy_native():
    """Valide que NumPy natif fonctionne sans mock."""
    try:
        import numpy
        import numpy.rec
        
        # Test de création d'un recarray
        arr = numpy.rec.recarray((2, 2), formats=['i4', 'f8'], names=['id', 'value'])
        
        return True, f"NumPy {numpy.__version__} avec numpy.rec natif"
        
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def validate_agent_adapters():
    """Valide que les adaptateurs d'agents utilisent les vraies connexions."""
    results = {}
    
    # Test InformalAgent
    try:
        from argumentation_analysis.agents.core.informal.informal_agent_adapter import InformalAgent, REAL_CONNECTIONS_AVAILABLE
        
        agent = InformalAgent(agent_name='ValidationAgent')
        capabilities = agent.get_agent_capabilities()
        
        results['informal'] = {
            'success': True,
            'real_connection_detected': REAL_CONNECTIONS_AVAILABLE,
            'agent_reports_real': capabilities.get('real_connection', False)
        }
        
    except Exception as e:
        results['informal'] = {'success': False, 'error': str(e)}
    
    # Test FirstOrderLogicAgent
    try:
        from argumentation_analysis.agents.core.logic.first_order_logic_agent_adapter import FirstOrderLogicAgent, REAL_CONNECTIONS_AVAILABLE
        
        fol_agent = FirstOrderLogicAgent(agent_name='ValidationFOLAgent')
        fol_capabilities = fol_agent.get_agent_capabilities()
        
        results['fol'] = {
            'success': True,
            'real_connection_detected': REAL_CONNECTIONS_AVAILABLE,
            'agent_reports_real': fol_capabilities.get('real_connection', False)
        }
        
    except Exception as e:
        results['fol'] = {'success': False, 'error': str(e)}
    
    all_success = all(result.get('success', False) for result in results.values())
    real_connections = all(result.get('real_connection_detected', False) for result in results.values() if result.get('success'))
    
    details = f"Informal: {results.get('informal', {}).get('success', False)}, FOL: {results.get('fol', {}).get('success', False)}, Vraies connexions: {real_connections}"
    
    return all_success and real_connections, details

async def validate_orchestrator():
    """Valide que l'orchestrateur fonctionne avec vraies connexions."""
    try:
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        
        # Créer un kernel réel avec OpenAI
        kernel = sk.Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="openai_validation",
            ai_model_id="gpt-4o-mini",
            api_key=os.environ.get('OPENAI_API_KEY')
        )
        kernel.add_service(chat_service)
        
        # Test création orchestrateur avec kernel réel
        orchestrator = CluedoExtendedOrchestrator(
            kernel=kernel,
            max_turns=1,
            max_cycles=1,
            oracle_strategy='enhanced_auto_reveal'
        )
        
        # Test rapide de setup
        elements_jeu = {
            'suspects': ['Colonel Moutarde'],
            'armes': ['Poignard'],
            'lieux': ['Salon']
        }
        
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete='Test Validation',
            elements_jeu=elements_jeu
        )
        
        return True, f"Orchestrateur créé et configuré avec stratégie {orchestrator.oracle_strategy} et kernel réel"
        
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def calculate_authenticity_score():
    """Calcule le score d'authenticité global du système."""
    factors = {
        'openai_connection': False,
        'mock_files_eliminated': False,
        'numpy_native': False,
        'agent_adapters': False,
        'orchestrator': False
    }
    
    # Test de chaque facteur
    print_header("CALCUL DU SCORE D'AUTHENTICITÉ")
    
    # Connexion OpenAI
    success, details = validate_openai_connection()
    factors['openai_connection'] = success
    print_result("Connexion OpenAI réelle", success, details)
    
    # Fichiers mocks éliminés
    success, details = validate_mock_files_eliminated()
    factors['mock_files_eliminated'] = success
    print_result("Fichiers mocks éliminés", success, details)
    
    # NumPy natif
    success, details = validate_numpy_native()
    factors['numpy_native'] = success
    print_result("NumPy natif (sans mock)", success, details)
    
    # Adaptateurs d'agents
    success, details = validate_agent_adapters()
    factors['agent_adapters'] = success
    print_result("Adaptateurs d'agents authentiques", success, details)
    
    # Orchestrateur
    try:
        success, details = asyncio.run(validate_orchestrator())
    except Exception as e:
        success, details = False, f"Erreur async: {str(e)}"
    factors['orchestrator'] = success
    print_result("Orchestrateur avec vraies connexions", success, details)
    
    # Calcul du score
    total_factors = len(factors)
    authentic_factors = sum(factors.values())
    authenticity_percentage = (authentic_factors / total_factors) * 100
    
    return authenticity_percentage, factors

def main():
    """Fonction principale de validation."""
    print_header("VALIDATION DE L'ÉLIMINATION DES MOCKS")
    print(f"Clé OpenAI configurée: {api_key[:20]}... (longueur: {len(api_key)})")
    
    # Calcul et affichage du score d'authenticité
    authenticity_score, factors = calculate_authenticity_score()
    
    print_header("RESULTAT FINAL")
    print(f"*** Score d'authenticite global: {authenticity_score:.1f}%")
    print(f"*** Facteurs authentiques: {sum(factors.values())}/{len(factors)}")
    
    if authenticity_score == 100.0:
        print("*** SYSTEME 100% AUTHENTIQUE - MISSION ACCOMPLIE! ***")
        print("[OK] Tous les mocks temporaires ont ete elimines")
        print("[OK] Toutes les connexions reelles sont operationnelles")
    elif authenticity_score >= 80.0:
        print("*** SYSTEME MAJORITAIREMENT AUTHENTIQUE ***")
        print("[!!] Quelques problemes mineurs a resoudre")
    else:
        print("*** SYSTEME PARTIELLEMENT AUTHENTIQUE ***")
        print("[!!] Des mocks persistent ou des connexions echouent")
    
    # Détail des échecs
    failed_factors = [name for name, success in factors.items() if not success]
    if failed_factors:
        print(f"\n[!!] Facteurs en echec: {', '.join(failed_factors)}")
    
    print_header("VALIDATION TERMINÉE")
    return authenticity_score

if __name__ == "__main__":
    score = main()
    sys.exit(0 if score >= 80.0 else 1)