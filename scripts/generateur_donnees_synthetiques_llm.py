#!/usr/bin/env python3
"""
Générateur de données synthétiques avec vrais LLMs OpenRouter
===========================================================
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path

def load_env_file():
    """Charge le fichier .env"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"').strip("'")
                    os.environ[key] = value

load_env_file()

def generate_synthetic_datasets():
    """Génère des datasets argumentatifs complexes"""
    
    prompts = [
        {
            "name": "arguments_ethique_ia",
            "prompt": "Générez 3 arguments structurés sur l'éthique de l'IA, avec prémisses, conclusions et contre-arguments."
        },
        {
            "name": "logique_modale_complexe", 
            "prompt": "Créez un raisonnement modal avec nécessité, possibilité et contingence sur la justice sociale."
        },
        {
            "name": "paradoxes_logiques",
            "prompt": "Formulez 2 paradoxes logiques originaux avec analyse de leur structure argumentative."
        },
        {
            "name": "sophismes_detectes",
            "prompt": "Rédigez des exemples de 5 sophismes différents (appel à l'autorité, ad hominem, etc.) dans un débat politique."
        }
    ]
    
    results = []
    
    for i, dataset in enumerate(prompts, 1):
        print(f"[*] Génération dataset {i}/4: {dataset['name']}")
        
        try:
            response = requests.post(
                'http://localhost:3000/analyze',
                json={
                    'text': dataset['prompt'],
                    'analysis_type': 'comprehensive',
                    'options': {'generate_examples': True}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                synthetic_data = {
                    'dataset_name': dataset['name'],
                    'generation_time': datetime.now().isoformat(),
                    'prompt': dataset['prompt'],
                    'llm_response': result,
                    'analysis_id': result.get('analysis_id'),
                    'quality_metrics': {
                        'response_length': len(str(result)),
                        'structure_completeness': 'results' in result and 'metadata' in result,
                        'processing_time': result.get('metadata', {}).get('duration', 0)
                    }
                }
                
                results.append(synthetic_data)
                print(f"[OK] Dataset généré - ID: {result.get('analysis_id', 'N/A')}")
            else:
                print(f"[ERREUR] Génération échouée: {response.status_code}")
                
        except Exception as e:
            print(f"[ERREUR] Dataset {dataset['name']}: {e}")
    
    return results

def save_synthetic_datasets(datasets):
    """Sauvegarde les datasets"""
    
    # Création du répertoire de données
    data_dir = Path('data/synthetic_datasets')
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarde globale
    with open(data_dir / 'synthetic_datasets_llm.json', 'w', encoding='utf-8') as f:
        json.dump({
            'generation_timestamp': datetime.now().isoformat(),
            'llm_provider': 'OpenRouter gpt-4o-mini',
            'total_datasets': len(datasets),
            'datasets': datasets
        }, f, indent=2, ensure_ascii=False)
    
    # Sauvegarde individuelle
    for dataset in datasets:
        filename = f"{dataset['dataset_name']}.json"
        with open(data_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] {len(datasets)} datasets sauvegardés dans {data_dir}")
    return data_dir

def main():
    """Point d'entrée"""
    print("=" * 70)
    print("  GÉNÉRATION DONNÉES SYNTHÉTIQUES AVEC VRAIS LLMs")
    print("=" * 70)
    
    # Vérification connexion Flask
    try:
        response = requests.get('http://localhost:3000/status', timeout=5)
        if response.status_code == 200:
            print("[OK] Interface Flask active")
        else:
            print("[ERREUR] Interface Flask non accessible")
            return 1
    except:
        print("[ERREUR] Interface Flask non accessible")
        return 1
    
    # Génération
    datasets = generate_synthetic_datasets()
    
    if datasets:
        data_dir = save_synthetic_datasets(datasets)
        
        print(f"\n[SUCCÈS] {len(datasets)} datasets synthétiques générés")
        print(f"[INFO] Répertoire: {data_dir}")
        
        # Statistiques
        total_chars = sum(d['quality_metrics']['response_length'] for d in datasets)
        avg_time = sum(d['quality_metrics']['processing_time'] for d in datasets) / len(datasets)
        
        print(f"[STATS] Volume total: {total_chars:,} caractères")
        print(f"[STATS] Temps moyen: {avg_time:.2f}s par dataset")
        
        return 0
    else:
        print("\n[ÉCHEC] Aucun dataset généré")
        return 1

if __name__ == "__main__":
    exit(main())