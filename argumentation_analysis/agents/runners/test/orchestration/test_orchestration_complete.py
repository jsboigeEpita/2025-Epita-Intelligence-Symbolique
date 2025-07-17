#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test d'intégration complet pour l'orchestration des agents.

Ce script exécute un scénario de test de bout en bout :
1.  Charge un texte d'analyse prédéfini (discours du Kremlin depuis un cache).
2.  Initialise l'environnement complet (JVM, service LLM).
3.  Instancie un `ConversationTracer` pour enregistrer tous les échanges.
4.  Lance une conversation d'analyse complète entre tous les agents.
5.  À la fin de l'exécution, génère deux artefacts :
    - Un **fichier de trace JSON** détaillé (ex: `trace_complete_*.json`).
    - Un **rapport d'analyse Markdown** (ex: `rapport_analyse_*.md`).

Ce script est le "moteur" exécuté par le script parent
`run_complete_test_and_analysis.py`.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from argumentation_analysis.paths import LIBS_DIR

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
root_dir = parent_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestOrchestrationComplete")

# Créer un répertoire pour les traces
TRACES_DIR = Path(parent_dir) / "execution_traces" / "orchestration"
TRACES_DIR.mkdir(exist_ok=True, parents=True)

async def load_kremlin_speech():
    """
    Charge directement le texte complet du discours du Kremlin depuis le cache.
    
    Returns:
        Le texte complet du discours
    """
    # Identifiant du fichier cache pour le discours du Kremlin
    cache_id = "4cf2d4853745719f6504a54610237738ad016de4f64176c3e8f5218f8fd2c01b"
    cache_path = Path(root_dir) / "text_cache" / f"{cache_id}.txt"
    
    logger.info(f"Chargement direct du discours du Kremlin depuis le cache...")
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text:
            logger.error("Le fichier cache est vide.")
            return None
        
        logger.info(f"Texte chargé avec succès ({len(text)} caractères)")
        return text
    except Exception as e:
        logger.error(f"Erreur lors du chargement du fichier cache: {e}")
        return None

class ConversationTracer:
    """
    Enregistre les messages échangés durant une conversation d'agents.

    Cette classe agit comme un "enregistreur" qui peut être branché au système
    d'orchestration via un "hook". Chaque fois qu'un message est envoyé, la
    méthode `add_message` est appelée, ce qui permet de construire une trace
    complète de la conversation.

    À la fin du processus, `finalize_trace` sauvegarde l'historique complet,
    y compris les statistiques, dans un fichier JSON horodaté.
    """
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.trace = {
            "timestamp_debut": datetime.now().isoformat(),
            "messages": [],
            "agents_utilises": set(),
            "timestamp_fin": None,
            "duree_totale": None,
            "statistiques": {
                "nombre_messages": 0,
                "messages_par_agent": {}
            }
        }
    
    def add_message(self, agent_name, message_content, message_type="message"):
        """
        Ajoute un message à la trace.
        """
        timestamp = datetime.now().isoformat()
        self.trace["messages"].append({
            "timestamp": timestamp,
            "agent": agent_name,
            "type": message_type,
            "content": message_content
        })
        
        # Mettre à jour les statistiques
        self.trace["agents_utilises"].add(agent_name)
        self.trace["statistiques"]["nombre_messages"] += 1
        
        if agent_name not in self.trace["statistiques"]["messages_par_agent"]:
            self.trace["statistiques"]["messages_par_agent"][agent_name] = 0
        
        self.trace["statistiques"]["messages_par_agent"][agent_name] += 1
    
    def finalize_trace(self):
        """
        Finalise la trace et calcule les statistiques.
        """
        end_time = datetime.now()
        self.trace["timestamp_fin"] = end_time.isoformat()
        
        # Calculer la durée totale
        start_time = datetime.fromisoformat(self.trace["timestamp_debut"])
        duration = (end_time - start_time).total_seconds()
        self.trace["duree_totale"] = duration
        
        # Convertir le set en liste pour la sérialisation JSON
        self.trace["agents_utilises"] = list(self.trace["agents_utilises"])
        
        # Sauvegarder la trace
        trace_path = self.output_dir / f"trace_complete_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(self.trace, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Trace complète sauvegardée dans {trace_path}")
        return trace_path

async def run_orchestration_test():
    """
    Orchestre le scénario de test complet de l'analyse d'un texte.

    Cette fonction est le cœur du script. Elle exécute séquentiellement toutes
    les étapes nécessaires pour le test :
    - Chargement du texte source.
    - Initialisation de la JVM et du service LLM.
    - Création du `ConversationTracer`.
    - Lancement de `run_analysis_conversation` avec le hook de traçage.
    - Finalisation de la trace et génération du rapport post-exécution.
    """
    # Charger le texte du discours du Kremlin directement depuis le cache
    text_content = await load_kremlin_speech()
    
    if not text_content:
        logger.error("Impossible de charger le texte pour le test.")
        return
    
    logger.info(f"Texte chargé pour le test ({len(text_content)} caractères)")
    
    # Initialiser l'environnement (le chargement de .env est maintenant implicite via settings)
    
    # Initialisation de la JVM
    from argumentation_analysis.core.jvm_setup import initialize_jvm
    jvm_ready_status = initialize_jvm(lib_dir_path=LIBS_DIR)
    
    if not jvm_ready_status:
        logger.warning("⚠️ JVM n'a pas pu être initialisée. L'agent PropositionalLogicAgent ne fonctionnera pas.")
    
    # Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service
    llm_service = create_llm_service(service_id="orchestration_test", model_id="gpt-4o-mini")
    
    if not llm_service:
        logger.error("❌ Impossible de créer le service LLM.")
        return
    
    # Initialiser le traceur de conversation
    tracer = ConversationTracer(TRACES_DIR)
    
    # Exécuter l'orchestration avec tous les agents
    from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
    
    logger.info("Lancement de l'orchestration avec tous les agents...")
    start_time = asyncio.get_event_loop().time()
    
    # Créer un hook pour intercepter les messages entre agents
    def message_hook(agent_name, message_content, message_type="message"):
        tracer.add_message(agent_name, message_content, message_type)
        logger.info(f"Message de {agent_name} intercepté ({len(message_content)} caractères)")
    
    try:
        # S'assurer que tous les agents sont activés, y compris l'agent Informel
        await run_analysis_conversation(
            texte_a_analyser=text_content,
            llm_service=llm_service,
            use_informal_agent=True,  # Activer explicitement l'agent Informel
            use_pl_agent=True,        # Activer explicitement l'agent PL
            message_hook=message_hook  # Hook pour intercepter les messages
        )
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        logger.info(f"🏁 Orchestration terminée avec succès en {duration:.2f} secondes.")
        
        # Finaliser la trace
        trace_path = tracer.finalize_trace()
        
        # Générer un rapport d'analyse
        await generate_analysis_report(trace_path, duration)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'orchestration: {e}", exc_info=True)

async def generate_analysis_report(trace_path: str, duration: float):
    """
    Génère un rapport d'analyse sommaire à partir d'un fichier de trace.

    Cette fonction ne réalise pas d'analyse sémantique. Elle charge le fichier
    de trace JSON, en extrait des statistiques de haut niveau (nombre de messages,
    agents impliqués, etc.) et les formate dans un fichier Markdown lisible.

    Le rapport généré contient des sections "À évaluer manuellement", indiquant
    qu'il sert de base pour une analyse humaine plus approfondie.

    Args:
        trace_path (str): Le chemin vers le fichier de trace JSON.
        duration (float): La durée totale de l'exécution en secondes.
    """
    logger.info("Génération du rapport d'analyse...")
    
    # Charger la trace
    with open(trace_path, "r", encoding="utf-8") as f:
        trace = json.load(f)
    
    # Créer le rapport
    report = {
        "titre": "Rapport d'Analyse d'Orchestration Complète",
        "date": datetime.now().isoformat(),
        "duree_execution": duration,
        "statistiques": {
            "nombre_messages_total": trace["statistiques"]["nombre_messages"],
            "agents_utilises": trace["agents_utilises"],
            "messages_par_agent": trace["statistiques"]["messages_par_agent"]
        },
        "analyse_qualitative": {
            "performance_agent_informel": "À évaluer manuellement",
            "qualite_analyse_argumentative": "À évaluer manuellement",
            "integration_agents": "À évaluer manuellement"
        },
        "recommandations": [
            "Évaluer la qualité des sophismes identifiés par l'agent Informel",
            "Vérifier l'intégration entre l'agent Informel et l'agent PL",
            "Analyser la pertinence des arguments extraits"
        ]
    }
    
    # Sauvegarder le rapport
    report_path = Path(parent_dir) / "documentation" / "reports" / f"rapport_analyse_orchestration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Créer une version markdown du rapport pour une meilleure lisibilité
    md_report = f"""# {report['titre']}

## Informations Générales
- **Date d'exécution:** {datetime.fromisoformat(report['date']).strftime('%d/%m/%Y %H:%M:%S')}
- **Durée d'exécution:** {report['duree_execution']:.2f} secondes

## Statistiques
- **Nombre total de messages:** {report['statistiques']['nombre_messages_total']}
- **Agents utilisés:** {', '.join(report['statistiques']['agents_utilises'])}

### Messages par agent
{chr(10).join([f"- **{agent}:** {count}" for agent, count in report['statistiques']['messages_par_agent'].items()])}

## Analyse Qualitative
- **Performance de l'agent Informel:** {report['analyse_qualitative']['performance_agent_informel']}
- **Qualité de l'analyse argumentative:** {report['analyse_qualitative']['qualite_analyse_argumentative']}
- **Intégration entre les agents:** {report['analyse_qualitative']['integration_agents']}

## Recommandations
{chr(10).join([f"- {rec}" for rec in report['recommandations']])}

## Conclusion
Ce rapport a été généré automatiquement après l'exécution de l'orchestration complète. Une analyse manuelle plus approfondie est recommandée pour évaluer la qualité de l'analyse argumentative produite.
"""
    
    md_report_path = Path(parent_dir) / "documentation" / "reports" / f"rapport_analyse_orchestration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    
    logger.info(f"Rapport d'analyse sauvegardé dans {md_report_path}")

async def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage du test d'orchestration complète...")
    await run_orchestration_test()
    logger.info("Test d'orchestration terminé.")

if __name__ == "__main__":
    asyncio.run(main())