"""
Interface web pour l'agent de génération de contre-arguments.

Ce module fournit une interface web simple pour interagir
avec l'agent de génération de contre-arguments.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from flask import Flask, request, jsonify, render_template
import traceback

from ..agent.counter_agent import CounterArgumentAgent
from ..agent.definitions import CounterArgumentType, RhetoricalStrategy

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialiser l'application Flask
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

# Variables globales
agent = None
agent_config = None

@app.route('/')
def index():
    """Page d'accueil."""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze_argument():
    """
    Analyse un argument et retourne sa structure.
    
    Requête JSON:
    {
        "argument": "Texte de l'argument à analyser"
    }
    """
    try:
        data = request.json
        argument_text = data.get('argument', '')
        
        if not argument_text:
            return jsonify({'error': 'Argument manquant'}), 400
        
        # Initialiser l'agent si nécessaire
        global agent, agent_config
        if agent is None:
            agent = CounterArgumentAgent(agent_config)
        
        # Analyser l'argument
        argument = agent.parser.parse_argument(argument_text)
        
        # Identifier les vulnérabilités
        vulnerabilities = agent.parser.identify_vulnerabilities(argument)
        
        return jsonify({
            'argument': {
                'content': argument.content,
                'premises': argument.premises,
                'conclusion': argument.conclusion,
                'argument_type': argument.argument_type
            },
            'vulnerabilities': [
                {
                    'type': v.type,
                    'target': v.target,
                    'score': v.score,
                    'description': v.description
                }
                for v in vulnerabilities
            ]
        })
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate_counter_argument():
    """
    Génère un contre-argument.
    
    Requête JSON:
    {
        "argument": "Texte de l'argument original",
        "counter_type": "direct_refutation" (optionnel),
        "rhetorical_strategy": "socratic_questioning" (optionnel)
    }
    """
    try:
        data = request.json
        argument_text = data.get('argument', '')
        
        if not argument_text:
            return jsonify({'error': 'Argument manquant'}), 400
        
        # Paramètres optionnels
        counter_type_str = data.get('counter_type')
        rhetorical_strategy_str = data.get('rhetorical_strategy')
        
        # Convertir les chaînes en énumérations
        counter_type = None
        if counter_type_str:
            try:
                counter_type = CounterArgumentType(counter_type_str)
            except ValueError:
                return jsonify({'error': f'Type de contre-argument invalide: {counter_type_str}'}), 400
        
        rhetorical_strategy = None
        if rhetorical_strategy_str:
            try:
                rhetorical_strategy = RhetoricalStrategy(rhetorical_strategy_str)
            except ValueError:
                return jsonify({'error': f'Stratégie rhétorique invalide: {rhetorical_strategy_str}'}), 400
        
        # Initialiser l'agent si nécessaire
        global agent, agent_config
        if agent is None:
            agent = CounterArgumentAgent(agent_config)
        
        # Générer le contre-argument
        result = agent.generate_counter_argument(
            argument_text,
            counter_type=counter_type,
            rhetorical_strategy=rhetorical_strategy
        )
        
        # Formater la réponse
        response = {
            'original_argument': {
                'content': result['original_argument'].content,
                'premises': result['original_argument'].premises,
                'conclusion': result['original_argument'].conclusion,
                'argument_type': result['original_argument'].argument_type
            },
            'counter_argument': {
                'content': result['counter_argument'].counter_content,
                'type': result['counter_argument'].counter_type.value,
                'target_component': result['counter_argument'].target_component,
                'strength': result['counter_argument'].strength.value,
                'rhetorical_strategy': result['counter_argument'].rhetorical_strategy
            },
            'vulnerabilities': [
                {
                    'type': v.type,
                    'target': v.target,
                    'score': v.score,
                    'description': v.description
                }
                for v in result.get('vulnerabilities', [])
            ],
            'evaluation': {
                'relevance': result['evaluation'].relevance,
                'logical_strength': result['evaluation'].logical_strength,
                'persuasiveness': result['evaluation'].persuasiveness,
                'originality': result['evaluation'].originality,
                'clarity': result['evaluation'].clarity,
                'overall_score': result['evaluation'].overall_score,
                'recommendations': result['evaluation'].recommendations
            },
            'validation': {
                'is_valid_attack': result['validation'].is_valid_attack,
                'original_survives': result['validation'].original_survives,
                'counter_succeeds': result['validation'].counter_succeeds,
                'logical_consistency': result['validation'].logical_consistency
            }
        }
        
        if hasattr(result['validation'], 'formal_representation'):
            response['validation']['formal_representation'] = result['validation'].formal_representation
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/counter_types', methods=['GET'])
def get_counter_types():
    """Retourne la liste des types de contre-arguments disponibles."""
    counter_types = [
        {
            'value': ct.value,
            'name': ct.value.replace('_', ' ').title(),
            'description': _get_counter_type_description(ct)
        }
        for ct in CounterArgumentType
    ]
    
    return jsonify(counter_types)


@app.route('/api/rhetorical_strategies', methods=['GET'])
def get_rhetorical_strategies():
    """Retourne la liste des stratégies rhétoriques disponibles."""
    strategies = [
        {
            'value': rs.value,
            'name': rs.value.replace('_', ' ').title(),
            'description': _get_strategy_description(rs)
        }
        for rs in RhetoricalStrategy
    ]
    
    return jsonify(strategies)


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Retourne les métriques de performance de l'agent."""
    global agent, agent_config
    
    if agent is None:
        agent = CounterArgumentAgent(agent_config)
    
    metrics = agent.metrics.get_summary_metrics()
    
    return jsonify(metrics)


def _get_counter_type_description(counter_type: CounterArgumentType) -> str:
    """Retourne une description du type de contre-argument."""
    descriptions = {
        CounterArgumentType.DIRECT_REFUTATION: "Attaque directement la conclusion de l'argument en montrant qu'elle est fausse.",
        CounterArgumentType.COUNTER_EXAMPLE: "Fournit un exemple qui contredit une généralisation faite dans l'argument.",
        CounterArgumentType.ALTERNATIVE_EXPLANATION: "Propose une explication alternative qui rend compte des mêmes faits.",
        CounterArgumentType.PREMISE_CHALLENGE: "Remet en question la validité d'une ou plusieurs prémisses de l'argument.",
        CounterArgumentType.REDUCTIO_AD_ABSURDUM: "Montre que l'argument mène à des conséquences absurdes ou contradictoires."
    }
    
    return descriptions.get(counter_type, "Description non disponible.")


def _get_strategy_description(strategy: RhetoricalStrategy) -> str:
    """Retourne une description de la stratégie rhétorique."""
    descriptions = {
        RhetoricalStrategy.SOCRATIC_QUESTIONING: "Pose des questions qui exposent les failles dans le raisonnement.",
        RhetoricalStrategy.REDUCTIO_AD_ABSURDUM: "Pousse le raisonnement jusqu'à l'absurde pour montrer ses limites.",
        RhetoricalStrategy.ANALOGICAL_COUNTER: "Utilise une analogie pour montrer les failles de l'argument.",
        RhetoricalStrategy.AUTHORITY_APPEAL: "Fait appel à une autorité reconnue pour contredire l'argument.",
        RhetoricalStrategy.STATISTICAL_EVIDENCE: "Utilise des données statistiques pour contredire l'argument."
    }
    
    return descriptions.get(strategy, "Description non disponible.")


def start_app(host='0.0.0.0', port=5000, debug=False, config=None):
    """
    Démarre l'application web.
    
    Args:
        host: L'hôte sur lequel démarrer l'application
        port: Le port sur lequel démarrer l'application
        debug: Activer le mode debug
        config: Configuration pour l'agent
    """
    # Configurer l'agent
    global agent_config
    agent_config = config
    
    # Si l'agent est déjà initialisé et que la config a changé, le réinitialiser
    global agent
    if agent is not None and config is not None:
        agent = CounterArgumentAgent(config)
    
    # Démarrer l'application
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    start_app(debug=True) 