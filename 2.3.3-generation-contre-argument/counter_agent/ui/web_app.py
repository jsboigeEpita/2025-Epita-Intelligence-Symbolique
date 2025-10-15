"""
Interface web pour l'agent de génération de contre-arguments.

Ce module fournit une interface web simple pour interagir
avec l'agent de génération de contre-arguments.
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, List, Any, Optional

from flask import Flask, request, jsonify, render_template
import traceback

# Imports pour le nouvel orchestrateur
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatCompletion,
)
from ..agent.orchestration.fallacy_workflow_orchestrator import (
    FallacyWorkflowOrchestrator,
)
from ..agent.definitions import (
    CounterArgumentType,
    RhetoricalStrategy,
)  # Gardé pour les types d'API
from ..agent.plugins.exploration_tool import ExplorationTool
from ..agent.plugins.hypothesis_validation_tool import HypothesisValidationTool
from ..agent.plugins.aggregation_tool import AggregationTool


# Gestionnaire de taxonomie
class TaxonomyManager:
    def __init__(self, data_folder_path):
        self.data_folder = data_folder_path
        self.taxonomies = self._load_taxonomies()

    def _load_taxonomies(self):
        taxonomies = {}
        if not os.path.exists(self.data_folder):
            logger.warning(f"Le dossier de données '{self.data_folder}' n'existe pas.")
            return taxonomies

        for filename in os.listdir(self.data_folder):
            if filename.endswith(".csv"):
                try:
                    taxonomy_name = os.path.splitext(filename)[0]
                    taxonomies[taxonomy_name] = pd.read_csv(
                        os.path.join(self.data_folder, filename)
                    )
                    logger.info(f"Taxonomie '{taxonomy_name}' chargée avec succès.")
                except Exception as e:
                    logger.error(
                        f"Erreur lors du chargement de la taxonomie {filename}: {e}"
                    )
        return taxonomies

    def get_taxonomy_names(self):
        return list(self.taxonomies.keys())

    def get_taxonomy(self, name):
        return self.taxonomies.get(name)

    def get_branch(self, taxonomy_name, node_id):
        taxonomy_df = self.get_taxonomy(taxonomy_name)
        if taxonomy_df is None or "id" not in taxonomy_df.columns:
            return None

        node_data = taxonomy_df[taxonomy_df["id"] == node_id]
        if not node_data.empty:
            return node_data.to_dict("records")[0]
        return None


# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialiser l'application Flask
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# Variables globales
kernel = None
orchestrator = None
taxonomy_manager = None
agent_config = None


@app.route("/")
def index():
    """Page d'accueil."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
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
        argument_text = data.get("argument", "")

        if not argument_text:
            return jsonify({"error": "Argument manquant"}), 400

        # Initialiser l'agent si nécessaire
        global agent, agent_config
        if agent is None:
            agent = CounterArgumentAgent(agent_config)

        # Analyser l'argument
        argument = agent.parser.parse_argument(argument_text)

        # Identifier les vulnérabilités
        vulnerabilities = agent.parser.identify_vulnerabilities(argument)

        return jsonify(
            {
                "argument": {
                    "content": argument.content,
                    "premises": argument.premises,
                    "conclusion": argument.conclusion,
                    "argument_type": argument.argument_type,
                },
                "vulnerabilities": [
                    {
                        "type": v.type,
                        "target": v.target,
                        "score": v.score,
                        "description": v.description,
                    }
                    for v in vulnerabilities
                ],
            }
        )

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/generate", methods=["POST"])
def generate_counter_argument():
    """
    Lance le workflow d'analyse de sophismes.

    Requête JSON:
    {
        "argument": "Texte de l'argument original",
        "taxonomy": "nom_de_la_taxonomie",
        "enabled_tools": ["ExplorationTool", "HypothesisValidationTool"]
    }
    """
    import asyncio

    try:
        data = request.json
        argument_text = data.get("argument")
        taxonomy_name = data.get("taxonomy")
        enabled_tools = data.get("enabled_tools")

        if not all([argument_text, taxonomy_name, enabled_tools]):
            return jsonify({"error": "Argument, taxonomie ou outils manquants"}), 400

        global agent_config, kernel, taxonomy_manager

        taxonomy_df = taxonomy_manager.get_taxonomy(taxonomy_name)
        if taxonomy_df is None:
            return jsonify({"error": f"Taxonomie '{taxonomy_name}' non trouvée."}), 400

        # Simuler l'objet taxonomie attendu par l'orchestrateur
        class DynamicTaxonomy:
            def get_branch(self, node_id):
                node_data = taxonomy_df[taxonomy_df["id"] == int(node_id)]
                if not node_data.empty:
                    return node_data.to_dict("records")[0]
                return None

        # Initialisation du kernel si ce n'est pas fait
        if kernel is None:
            kernel = sk.Kernel()
            api_key = agent_config.get("openai_api_key")
            # Dans un cas réel, on lirait la config pour le service à utiliser
            kernel.add_service(
                OpenAIChatCompletion(service_id="default", api_key=api_key, org_id="")
            )

        # Instancier l'orchestrateur avec la configuration dynamique
        orchestrator = FallacyWorkflowOrchestrator(kernel, enabled_tools=enabled_tools)

        # Lancer le workflow
        final_report = asyncio.run(
            orchestrator.analyze_argument(argument_text, DynamicTaxonomy())
        )

        return jsonify(final_report)

    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/counter_types", methods=["GET"])
def get_counter_types():
    """Retourne la liste des types de contre-arguments disponibles."""
    counter_types = [
        {
            "value": ct.value,
            "name": ct.value.replace("_", " ").title(),
            "description": _get_counter_type_description(ct),
        }
        for ct in CounterArgumentType
    ]

    return jsonify(counter_types)


@app.route("/api/rhetorical_strategies", methods=["GET"])
def get_rhetorical_strategies():
    """Retourne la liste des stratégies rhétoriques disponibles."""
    strategies = [
        {
            "value": rs.value,
            "name": rs.value.replace("_", " ").title(),
            "description": _get_strategy_description(rs),
        }
        for rs in RhetoricalStrategy
    ]

    return jsonify(strategies)


@app.route("/api/available-taxonomies", methods=["GET"])
def get_available_taxonomies():
    """Retourne la liste des taxonomies disponibles."""
    global taxonomy_manager
    if taxonomy_manager is None:
        return (
            jsonify({"error": "Le gestionnaire de taxonomie n'est pas initialisé"}),
            500,
        )
    return jsonify(taxonomy_manager.get_taxonomy_names())


@app.route("/api/available-tools", methods=["GET"])
def get_available_tools():
    """Retourne la liste des outils disponibles pour l'orchestrateur."""
    return jsonify(list(FallacyWorkflowOrchestrator.ALL_TOOLS.keys()))


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Retourne les métriques de performance de l'agent."""
    # Cette fonction est obsolète car l'ancien agent n'est plus utilisé
    return jsonify({"message": "Cette route de métriques est obsolète."})


def _get_counter_type_description(counter_type: CounterArgumentType) -> str:
    """Retourne une description du type de contre-argument."""
    descriptions = {
        CounterArgumentType.DIRECT_REFUTATION: "Attaque directement la conclusion de l'argument en montrant qu'elle est fausse.",
        CounterArgumentType.COUNTER_EXAMPLE: "Fournit un exemple qui contredit une généralisation faite dans l'argument.",
        CounterArgumentType.ALTERNATIVE_EXPLANATION: "Propose une explication alternative qui rend compte des mêmes faits.",
        CounterArgumentType.PREMISE_CHALLENGE: "Remet en question la validité d'une ou plusieurs prémisses de l'argument.",
        CounterArgumentType.REDUCTIO_AD_ABSURDUM: "Montre que l'argument mène à des conséquences absurdes ou contradictoires.",
    }

    return descriptions.get(counter_type, "Description non disponible.")


def _get_strategy_description(strategy: RhetoricalStrategy) -> str:
    """Retourne une description de la stratégie rhétorique."""
    descriptions = {
        RhetoricalStrategy.SOCRATIC_QUESTIONING: "Pose des questions qui exposent les failles dans le raisonnement.",
        RhetoricalStrategy.REDUCTIO_AD_ABSURDUM: "Pousse le raisonnement jusqu'à l'absurde pour montrer ses limites.",
        RhetoricalStrategy.ANALOGICAL_COUNTER: "Utilise une analogie pour montrer les failles de l'argument.",
        RhetoricalStrategy.AUTHORITY_APPEAL: "Fait appel à une autorité reconnue pour contredire l'argument.",
        RhetoricalStrategy.STATISTICAL_EVIDENCE: "Utilise des données statistiques pour contredire l'argument.",
    }

    return descriptions.get(strategy, "Description non disponible.")


def start_app(host="0.0.0.0", port=5000, debug=False, config=None):
    """
    Démarre l'application web.

    Args:
        host: L'hôte sur lequel démarrer l'application
        port: Le port sur lequel démarrer l'application
        debug: Activer le mode debug
        config: Configuration pour l'agent
    """
    global agent_config, taxonomy_manager

    # Initialiser le gestionnaire de taxonomie
    data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    taxonomy_manager = TaxonomyManager(data_path)

    agent_config = config

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    start_app(debug=True)
