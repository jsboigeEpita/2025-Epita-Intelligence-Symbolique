#!/usr/bin/env python3
"""
Point d'entrée principal pour le système de dialogue argumentatif Walton-Krabbe.

Usage:
    python main.py                    # Lance l'interface CLI
    python main.py --demo            # Lance une démonstration
    python main.py --config path     # Charge une configuration
"""

import sys
import os
import argparse

# Ajoute le répertoire src au path Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.interfaces.cli import DialogueSystemCLI
from src.agents.multi_agent_system import MultiAgentDialogueSystem
from src.interfaces.config import DialogueSystemConfig
from src.core.models import DialogueType, Proposition
from src.core.knowledge_base import KnowledgeBase
from src.agents.dialogue_agent import DialogueAgent
from src.protocols.inquiry_protocol import InquiryProtocol
from src.protocols.persuasion_protocol import PersuasionProtocol


def create_rich_demo_agents(system: MultiAgentDialogueSystem):
    """Crée des agents avec une base de connaissances enrichie"""
    
    try:
        config_path = "config/rich_agents_demo.yaml"
        if os.path.exists(config_path):
            config = DialogueSystemConfig.load_from_file(config_path)
            agents = []
            for agent_config in config.get("agents", []):
                agent = DialogueSystemConfig.create_agent_from_config(agent_config)
                system.register_agent(agent)
                agents.append(agent)
            return agents
        else:
            print("Fichier de configuration enrichie non trouvé, utilisation des agents de base")
            return create_demo_agents(system)
    except Exception as e:
        print(f"Erreur lors du chargement de la configuration enrichie: {e}")
        return create_demo_agents(system)

def run_rich_demo():
    """Lance une démonstration enrichie du système"""
    print("=== DÉMONSTRATION ENRICHIE DU SYSTÈME WALTON-KRABBE ===\n")
    
    system = MultiAgentDialogueSystem()
    agents = create_rich_demo_agents(system)
    
    if len(agents) < 2:
        print("Agents de base utilisés car configuration enrichie indisponible")
        run_demo()
        return
    
    print("Agents créés avec bases de connaissances enrichies:")
    for agent in agents:
        kb_size = len(agent.kb.get_all_propositions())
        arg_size = len(agent.kb.get_all_arguments())
        print(f"- {agent.id}: {kb_size} propositions, {arg_size} arguments")
    
    # Dialogue complexe 1: Climat et économie
    print("\n" + "="*80)
    print("DIALOGUE 1: Science climatique vs Économie énergétique")
    print("Type: INQUIRY | Participants: climate_scientist vs energy_economist")
    print("="*80)
    
    dialogue1_id = system.create_dialogue(
        "climate_scientist", 
        "energy_economist", 
        "Comment concilier urgence climatique et réalités économiques?",
        DialogueType.INQUIRY
    )
    
    summary1 = system.run_dialogue(dialogue1_id, max_turns=20)
    print_detailed_dialogue_summary(summary1)
    
    # Dialogue complexe 2: Innovation vs Politique
    print("\n" + "="*80)
    print("DIALOGUE 2: Innovation technologique vs Politiques publiques") 
    print("Type: DELIBERATION | Participants: tech_innovator vs policy_maker")
    print("="*80)
    
    dialogue2_id = system.create_dialogue(
        "tech_innovator",
        "policy_maker",
        "Faut-il privilégier l'innovation ou la régulation pour atteindre la neutralité carbone?",
        DialogueType.INQUIRY
    )
    
    summary2 = system.run_dialogue(dialogue2_id, max_turns=18)
    print_detailed_dialogue_summary(summary2)
    
    # Dialogue complexe 3: Activisme vs Scepticisme
    print("\n" + "="*80)
    print("DIALOGUE 3: Activisme citoyen vs Scepticisme climatique")
    print("Type: PERSUASION | Participants: citizen_activist vs climate_skeptic")
    print("="*80)
    
    dialogue3_id = system.create_dialogue(
        "citizen_activist",
        "climate_skeptic", 
        "L'urgence climatique justifie-t-elle des actions radicales?",
        DialogueType.PERSUASION
    )
    
    summary3 = system.run_dialogue(dialogue3_id, max_turns=16)
    print_detailed_dialogue_summary(summary3)
    
    # Statistiques finales
    print("\n" + "="*80)
    print("STATISTIQUES DE LA DÉMONSTRATION ENRICHIE")
    print("="*80)
    total_moves = summary1['total_moves'] + summary2['total_moves'] + summary3['total_moves']
    print(f"Total dialogues: 3")
    print(f"Total échanges: {total_moves}")
    print(f"Moyenne par dialogue: {total_moves/3:.1f}")
    print(f"Domaines couverts: Science, Économie, Politique, Technologie, Activisme")
    print(f"Arguments utilisés: {sum(len(agent.kb.get_all_arguments()) for agent in agents)}")

def print_detailed_dialogue_summary(summary):
    """Affiche un résumé détaillé avec analyse"""
    print(f"\nRésultat: {summary['total_moves']} échanges")
    
    # Analyse des actes de parole
    act_counts = {}
    for move in summary['moves']:
        act = move['act']
        act_counts[act] = act_counts.get(act, 0) + 1
    
    print(f"Distribution des actes: {act_counts}")
    
    # Affichage des échanges avec numérotation
    for i, move in enumerate(summary['moves'], 1):
        speaker_label = move['speaker'].replace('_', ' ').title()
        act_label = move['act'].replace('_', ' ').title()
        content = move['content']
        
        # Limite la longueur pour l'affichage
        if len(content) > 100:
            content = content[:97] + "..."
            
        print(f"{i:2d}. {speaker_label:18s}: {act_label:12s} | {content}")

# Modification du main pour inclure la démo enrichie
def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Système de Dialogue Argumentatif Walton-Krabbe")
    parser.add_argument("--demo", action="store_true", help="Lance une démonstration")
    parser.add_argument("--rich-demo", action="store_true", help="Lance une démonstration enrichie")
    parser.add_argument("--config", type=str, help="Chemin vers un fichier de configuration")
    parser.add_argument("--topic", type=str, help="Sujet de dialogue pour la démo rapide")
    
    args = parser.parse_args()
    
    if args.rich_demo:
        run_rich_demo()
    # ... reste du code existant

    elif args.config:
        if not os.path.exists(args.config):
            print(f"Erreur: Fichier de configuration '{args.config}' non trouvé")
            sys.exit(1)
        
        print(f"Chargement de la configuration: {args.config}")
        system = MultiAgentDialogueSystem()
        
        try:
            config = DialogueSystemConfig.load_from_file(args.config)
            for agent_config in config.get("agents", []):
                agent = DialogueSystemConfig.create_agent_from_config(agent_config)
                system.register_agent(agent)
                print(f"Agent {agent.id} chargé")
                
            if len(system.agents) >= 2:
                agents_list = list(system.agents.keys())
                topic = args.topic or "Sujet de test depuis configuration"
                
                dialogue_id = system.create_dialogue(
                    agents_list[0], 
                    agents_list[1], 
                    topic,
                    DialogueType.INQUIRY
                )
                
                print(f"\nDémarrage dialogue: {topic}")
                summary = system.run_dialogue(dialogue_id)
                print_dialogue_summary(summary)
            else:
                print("Configuration doit contenir au moins 2 agents")
                
        except Exception as e:
            print(f"Erreur lors du chargement: {e}")
            sys.exit(1)
    else:
        # Lance l'interface CLI interactive
        cli = DialogueSystemCLI()
        cli.run()


if __name__ == "__main__":
    main()
