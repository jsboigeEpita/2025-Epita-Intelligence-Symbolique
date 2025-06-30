#!/usr/bin/env python
"""
Script d'exemple pour tester l'agent de génération de contre-arguments.

Ce script illustre l'utilisation de l'agent sans interface web.
"""

import os
import sys
import logging
import time
from pprint import pprint
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env s'il existe
load_dotenv()

# Vérifier la présence de la clé API OpenAI
if 'OPENAI_API_KEY' not in os.environ:
    print("⚠️  Attention: La variable d'environnement OPENAI_API_KEY n'est pas définie.")
    print("    Les fonctionnalités utilisant l'API OpenAI ne fonctionneront pas correctement.")
    print("    Créez un fichier .env à la racine du projet avec votre clé API:")
    print("    OPENAI_API_KEY=votre-clé-api-openai")
    print("    Ou fournissez votre clé API comme argument: --api-key=votre-clé-api")
    print()

# Ajouter le répertoire parent au sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from counter_agent.agent.counter_agent import CounterArgumentAgent
from counter_agent.agent.definitions import CounterArgumentType, RhetoricalStrategy


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Fonction principale."""
    # Traiter les arguments de ligne de commande
    import argparse
    parser = argparse.ArgumentParser(description='Exemple d\'utilisation de l\'agent de génération de contre-arguments.')
    parser.add_argument('--api-key', help='Clé API OpenAI (remplace la variable d\'environnement OPENAI_API_KEY)')
    args = parser.parse_args()
    
    # Configurer la clé API OpenAI si fournie en argument
    if args.api_key:
        os.environ['OPENAI_API_KEY'] = args.api_key
        print("✓ Clé API OpenAI définie à partir des arguments.")
    
    # Configuration de l'agent
    config = {
        'openai_api_key': os.environ.get('OPENAI_API_KEY'),
        'tweety_jar_path': os.path.join(os.path.dirname(__file__), 'counter_agent', 'tweety-full.jar')
    }
    
    # Initialiser l'agent
    logger.info("Initialisation de l'agent...")
    agent = CounterArgumentAgent(config)
    
    # Définir quelques arguments de test
    test_arguments = [
        {
            'name': 'Argument sur le réchauffement climatique',
            'text': 'Le réchauffement climatique n\'est pas un problème sérieux car les températures ont toujours fluctué au cours de l\'histoire de la Terre.'
        },
        {
            'name': 'Argument sur les vaccins',
            'text': 'Les vaccins sont dangereux parce que de nombreuses personnes ont signalé des effets secondaires graves après leur vaccination.'
        },
        {
            'name': 'Argument sur la réussite académique',
            'text': 'Tous les étudiants qui travaillent dur réussissent leurs examens. Marie travaille dur. Donc Marie réussira ses examens.'
        }
    ]
    
    # Tester l'agent sur chaque argument
    for test_arg in test_arguments:
        print("\n" + "=" * 80)
        print(f"Test de l'argument: {test_arg['name']}")
        print("=" * 80)
        
        # Générer un contre-argument
        print(f"\nArgument original: {test_arg['text']}")
        print("\nGénération du contre-argument...")
        
        start_time = time.time()
        result = agent.generate_counter_argument(test_arg['text'])
        generation_time = time.time() - start_time
        
        # Afficher les résultats
        print(f"\nContre-argument généré ({generation_time:.2f} secondes):")
        print("-" * 50)
        print(result['counter_argument'].counter_content)
        print("-" * 50)
        
        print("\nInformations sur le contre-argument:")
        print(f"- Type: {result['counter_argument'].counter_type.value}")
        print(f"- Cible: {result['counter_argument'].target_component}")
        print(f"- Force: {result['counter_argument'].strength.value}")
        print(f"- Stratégie rhétorique: {result['counter_argument'].rhetorical_strategy}")
        
        print("\nÉvaluation:")
        print(f"- Score global: {result['evaluation'].overall_score:.2f}")
        print(f"- Pertinence: {result['evaluation'].relevance:.2f}")
        print(f"- Force logique: {result['evaluation'].logical_strength:.2f}")
        print(f"- Persuasion: {result['evaluation'].persuasiveness:.2f}")
        print(f"- Originalité: {result['evaluation'].originality:.2f}")
        print(f"- Clarté: {result['evaluation'].clarity:.2f}")
        
        print("\nRecommandations:")
        for recommendation in result['evaluation'].recommendations:
            print(f"- {recommendation}")
        
        print("\nValidation logique:")
        print(f"- Attaque valide: {result['validation'].is_valid_attack}")
        print(f"- L'argument original survit: {result['validation'].original_survives}")
        print(f"- Le contre-argument réussit: {result['validation'].counter_succeeds}")
        print(f"- Cohérence logique: {result['validation'].logical_consistency}")
    
    # Afficher les métriques globales
    print("\n" + "=" * 80)
    print("Métriques globales")
    print("=" * 80)
    
    summary = agent.metrics.get_summary_metrics()
    print("\nRésumé des performances:")
    print(f"- Nombre d'échantillons: {summary['sample_count']}")
    print(f"- Taux de succès: {summary['success_rate']:.2%}")
    print(f"- Score global moyen: {summary['average_overall_score']:.3f}")
    print(f"- Temps de génération moyen: {summary['average_generation_time']:.3f} secondes")
    
    # Exporter un rapport complet
    report = agent.metrics.export_metrics_report()
    with open('metrics_report.txt', 'w') as f:
        f.write(report)
    
    print("\nRapport de métriques exporté dans 'metrics_report.txt'")


if __name__ == '__main__':
    main() 