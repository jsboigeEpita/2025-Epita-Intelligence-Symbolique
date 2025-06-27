import os
from typing import Dict, Any

from ..core.models import DialogueType
from ..agents.multi_agent_system import MultiAgentDialogueSystem
from .config import DialogueSystemConfig


class DialogueSystemCLI:
    """Interface en ligne de commande pour le système de dialogue"""
    
    def __init__(self):
        self.system = MultiAgentDialogueSystem()
        self.agents_config = {}
    
    def run(self):
        """Lance l'interface interactive"""
        print("=== Système de Dialogue Argumentatif Walton-Krabbe ===")
        print("Version 1.0.0")
        
        while True:
            print("\nOptions disponibles:")
            print("1. Charger agents depuis configuration")
            print("2. Créer agents prédéfinis (test)")
            print("3. Créer dialogue")
            print("4. Lister agents")
            print("5. Lister dialogues actifs")
            print("6. Voir archive des dialogues")
            print("7. Quitter")
            
            choice = input("\nVotre choix: ").strip()
            
            if choice == "1":
                self._load_agents()
            elif choice == "2":
                self._create_test_agents()
            elif choice == "3":
                self._create_dialogue()
            elif choice == "4":
                self._list_agents()
            elif choice == "5":
                self._list_active_dialogues()
            elif choice == "6":
                self._show_archive()
            elif choice == "7":
                print("Au revoir!")
                break
            else:
                print("Choix invalide")
    
    def _load_agents(self):
        """Charge les agents depuis un fichier de configuration"""
        filepath = input("Chemin du fichier de configuration: ").strip()
        if not os.path.exists(filepath):
            print("Fichier non trouvé")
            return
            
        try:
            config = DialogueSystemConfig.load_from_file(filepath)
            for agent_config in config.get("agents", []):
                agent = DialogueSystemConfig.create_agent_from_config(agent_config)
                self.system.register_agent(agent)
                print(f"Agent {agent.id} chargé avec succès")
        except Exception as e:
            print(f"Erreur lors du chargement: {e}")
    
    def _create_test_agents(self):
        """Crée des agents de test prédéfinis"""
        from ..core.knowledge_base import KnowledgeBase
        from ..core.models import Proposition, Argument
        from ..agents.dialogue_agent import DialogueAgent
        from ..protocols.inquiry_protocol import InquiryProtocol
        
        # Agent 1: Expert en climat
        kb1 = KnowledgeBase()
        kb1.add_proposition(Proposition("Le réchauffement climatique est causé par l'activité humaine", True, 0.9))
        kb1.add_proposition(Proposition("Les émissions de CO2 ont augmenté depuis 1950", True, 0.95))
        kb1.add_proposition(Proposition("Les températures moyennes augmentent", True, 0.9))
        
        protocol1 = InquiryProtocol(DialogueType.INQUIRY)
        agent1 = DialogueAgent("expert_climat", kb1, protocol1, "collaborative")
        
        # Agent 2: Sceptique
        kb2 = KnowledgeBase()
        kb2.add_proposition(Proposition("Les variations climatiques sont naturelles", True, 0.7))
        kb2.add_proposition(Proposition("Les modèles climatiques sont imprécis", True, 0.6))
        kb2.add_proposition(Proposition("L'activité solaire influence le climat", True, 0.8))
        
        protocol2 = InquiryProtocol(DialogueType.INQUIRY)
        agent2 = DialogueAgent("sceptique_climat", kb2, protocol2, "skeptical")
        
        self.system.register_agent(agent1)
        self.system.register_agent(agent2)
        
        print("Agents de test créés:")
        print("- expert_climat (stratégie collaborative)")
        print("- sceptique_climat (stratégie sceptique)")
    
    def _create_dialogue(self):
        """Crée un nouveau dialogue"""
        if len(self.system.agents) < 2:
            print("Au moins 2 agents requis")
            return
        
        print("\nAgents disponibles:", list(self.system.agents.keys()))
        agent1_id = input("ID du premier agent: ").strip()
        agent2_id = input("ID du second agent: ").strip()
        
        if agent1_id not in self.system.agents or agent2_id not in self.system.agents:
            print("Agent(s) non trouvé(s)")
            return
        
        topic = input("Sujet du dialogue: ").strip()
        
        print("\nTypes de dialogue:")
        for i, dt in enumerate(DialogueType, 1):
            print(f"{i}. {dt.value}")
        
        type_choice = input("Type de dialogue (numéro, défaut=2): ").strip()
        try:
            if not type_choice:
                dialogue_type = DialogueType.INQUIRY
            else:
                dialogue_type = list(DialogueType)[int(type_choice) - 1]
                
            dialogue_id = self.system.create_dialogue(agent1_id, agent2_id, topic, dialogue_type)
            print(f"\nDialogue créé: {dialogue_id}")
            
            max_turns = input("Nombre max de tours (défaut=15): ").strip()
            max_turns = int(max_turns) if max_turns.isdigit() else 15
            
            print(f"\n=== Exécution du dialogue (max {max_turns} tours) ===")
            summary = self.system.run_dialogue(dialogue_id, max_turns)
            self._display_dialogue_summary(summary)
            
        except (ValueError, IndexError) as e:
            print(f"Erreur: {e}")
    
    def _list_agents(self):
        """Liste tous les agents enregistrés"""
        if not self.system.agents:
            print("Aucun agent enregistré")
            return
        
        print("\nAgents enregistrés:")
        for agent_id, agent in self.system.agents.items():
            print(f"- {agent_id} (stratégie: {agent.strategy})")
            print(f"  Propositions: {len(agent.kb.get_all_propositions())}")
            print(f"  Arguments: {len(agent.kb.get_all_arguments())}")
    
    def _list_active_dialogues(self):
        """Liste les dialogues actifs"""
        active = self.system.get_active_dialogues()
        if not active:
            print("Aucun dialogue actif")
            return
        
        for dialogue_id, info in active.items():
            print(f"\nID: {dialogue_id}")
            print(f"  Participants: {info['participants']}")
            print(f"  Sujet: {info['topic']}")
            print(f"  Type: {info['type']}")
            print(f"  Démarré: {info['started']}")
    
    def _show_archive(self):
        """Affiche l'archive des dialogues"""
        archive = self.system.get_dialogue_archive()
        if not archive:
            print("Aucun dialogue archivé")
            return
        
        for i, summary in enumerate(archive, 1):
            print(f"\n=== Dialogue {i} ===")
            self._display_dialogue_summary(summary)
    
    def _display_dialogue_summary(self, summary: Dict[str, Any]):
        """Affiche un résumé de dialogue"""
        print(f"\nID: {summary['dialogue_id']}")
        print(f"Participants: {summary['participants']}")
        print(f"Total mouvements: {summary['total_moves']}")
        
        print(f"\n--- Échanges ---")
        for i, move in enumerate(summary['moves'], 1):
            print(f"{i:2d}. {move['speaker']:15s}: {move['act']:10s} - {move['content']}")
        
        print(f"\n--- Statistiques ---")
        if 'agent1_summary' in summary and summary['agent1_summary']:
            agent1_stats = summary['agent1_summary'].get('move_distribution', {})
            print(f"Agent 1 ({summary['participants'][0]}): {agent1_stats}")
        
        if 'agent2_summary' in summary and summary['agent2_summary']:
            agent2_stats = summary['agent2_summary'].get('move_distribution', {})
            print(f"Agent 2 ({summary['participants'][1]}): {agent2_stats}")
