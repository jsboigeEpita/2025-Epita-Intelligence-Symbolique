#!/usr/bin/env python
"""
Script principal pour lancer l'interface web de l'agent de génération de contre-arguments.

Ce script configure le logging et démarre l'application web.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env s'il existe
load_dotenv()

# Vérifier la présence de la clé API OpenAI
if 'OPENAI_API_KEY' not in os.environ:
    print("⚠️  Attention: La variable d'environnement OPENAI_API_KEY n'est pas définie.")
    print("    Les fonctionnalités utilisant l'API OpenAI ne fonctionneront pas correctement.")
    print("    Créez un fichier .env à la racine du projet avec votre clé API:")
    print("    OPENAI_API_KEY=votre-clé-api-openai")

# Ajouter le répertoire parent au sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from counter_agent.ui import start_app


def setup_logging(level=logging.INFO):
    """Configure le logging pour l'application."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('counter_agent.log')
        ]
    )


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description='Lance l\'interface web de l\'agent de génération de contre-arguments.')
    parser.add_argument('--host', default='127.0.0.1', help='Hôte sur lequel exécuter l\'application (défaut: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Port sur lequel exécuter l\'application (défaut: 5000)')
    parser.add_argument('--debug', action='store_true', help='Activer le mode debug')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Niveau de logging (défaut: INFO)')
    parser.add_argument('--api-key', help='Clé API OpenAI (remplace la variable d\'environnement OPENAI_API_KEY)')
    
    return parser.parse_args()


def main():
    """Fonction principale."""
    args = parse_arguments()
    
    # Configurer la clé API OpenAI si fournie en argument
    if args.api_key:
        os.environ['OPENAI_API_KEY'] = args.api_key
        print("✓ Clé API OpenAI définie à partir des arguments.")
    
    # Configurer le logging
    log_level = getattr(logging, args.log_level)
    setup_logging(level=log_level)
    
    # Afficher les informations de démarrage
    print(f"Démarrage de l'application sur http://{args.host}:{args.port}")
    print("Appuyez sur Ctrl+C pour arrêter.")
    
    # Démarrer l'application
    config = {
        'openai_api_key': os.environ.get('OPENAI_API_KEY'),
        'tweety_jar_path': os.path.join(os.path.dirname(__file__), 'libs', 'tweety-full.jar')
    }
    
    start_app(host=args.host, port=args.port, debug=args.debug, config=config)


if __name__ == '__main__':
    main() 