from typing import Dict, List, Optional, Union, Any
import logging
import uuid
import random
from datetime import datetime

from ..core.models import Proposition, Argument, DialogueMove, SpeechAct
from ..core.knowledge_base import KnowledgeBase
from ..core.argumentation_engine import ArgumentationEngine
from ..protocols.base_protocol import DialogueProtocol


class DialogueAgent:
    """Agent principal pour l'argumentation dialogique"""
    
    def __init__(self, 
                 agent_id: str,
                 knowledge_base: KnowledgeBase,
                 protocol: DialogueProtocol,
                 strategy: str = "collaborative"):
        self.id = agent_id
        self.kb = knowledge_base
        self.protocol = protocol
        self.strategy = strategy
        self.argumentation_engine = ArgumentationEngine(knowledge_base)
        self.commitment_store: Dict[str, Proposition] = {}
        self.dialogue_history: List[DialogueMove] = []
        self.current_dialogue_id: Optional[str] = None
        self.logger = self._setup_logging()
        self.response_count = {}  # Pour éviter les répétitions
        self.last_responses = []  # Historique des dernières réponses
    
    def _setup_logging(self) -> logging.Logger:
        """Configure le logging pour l'agent"""
        logger = logging.getLogger(f"DialogueAgent_{self.id}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def initiate_dialogue(self, topic: str, other_agent: 'DialogueAgent') -> str:
        """Initie un nouveau dialogue"""
        dialogue_id = str(uuid.uuid4())
        self.current_dialogue_id = dialogue_id
        other_agent.current_dialogue_id = dialogue_id
        
        # Premier mouvement selon le type de dialogue
        if hasattr(self.protocol, 'type'):
            if self.protocol.type.value == "inquiry":
                initial_move = self._create_move(SpeechAct.QUESTION, topic)
            elif self.protocol.type.value == "persuasion":
                initial_move = self._create_move(SpeechAct.CLAIM, topic)
            else:
                initial_move = self._create_move(SpeechAct.QUESTION, topic)
        else:
            initial_move = self._create_move(SpeechAct.QUESTION, topic)
        
        self.dialogue_history.append(initial_move)
        self.logger.info(f"Dialogue initié: {dialogue_id}, Topic: {topic}")
        
        return dialogue_id
    
    def _create_move(self, act: SpeechAct, content: Union[str, Proposition, Argument], 
                    target: Optional[str] = None) -> DialogueMove:
        """Crée un mouvement de dialogue"""
        if isinstance(content, str):
            content = Proposition(content)
        
        return DialogueMove(
            id="",
            speaker=self.id,
            act=act,
            content=content,
            timestamp=datetime.now(),
            target=target
        )
    
    def process_move(self, move: DialogueMove) -> Optional[DialogueMove]:
        """Traite un mouvement reçu et génère une réponse"""
        self.dialogue_history.append(move)
        self.logger.info(f"Mouvement reçu: {move.act.value} - {move.content}")
        
        # Vérification de terminaison
        if self.protocol.is_terminal_state(self.dialogue_history):
            self.logger.info("Dialogue terminé")
            return None
        
        # Détection de boucle
        if self._is_loop_detected():
            self.logger.info("Boucle détectée, tentative de sortie")
            response = self._break_loop_response()
        else:
            # Génération de réponse selon la stratégie
            response = self._generate_response(move)
        
        if response:
            self.dialogue_history.append(response)
            self.logger.info(f"Réponse générée: {response.act.value} - {response.content}")
            self._track_response(response)
        
        return response
    
    def _is_loop_detected(self) -> bool:
        """Détecte si on est dans une boucle"""
        if len(self.dialogue_history) < 4:
            return False
        
        # Vérifie les 4 derniers mouvements pour une répétition
        recent_moves = self.dialogue_history[-4:]
        my_moves = [m for m in recent_moves if m.speaker == self.id]
        
        if len(my_moves) >= 2:
            # Si les deux derniers mouvements de cet agent sont identiques
            return (my_moves[-1].act == my_moves[-2].act and 
                   str(my_moves[-1].content) == str(my_moves[-2].content))
        
        return False
    
    def _track_response(self, response: DialogueMove):
        """Suit les réponses pour éviter les répétitions"""
        response_key = f"{response.act.value}:{str(response.content)[:50]}"
        self.response_count[response_key] = self.response_count.get(response_key, 0) + 1
        self.last_responses.append(response_key)
        
        # Garde seulement les 10 dernières réponses
        if len(self.last_responses) > 10:
            self.last_responses.pop(0)
    
    def _break_loop_response(self) -> Optional[DialogueMove]:
        """Génère une réponse pour sortir d'une boucle"""
        # Propose une proposition de la base de connaissances
        props = self.kb.get_all_propositions()
        if props:
            prop = random.choice(props)
            return self._create_move(SpeechAct.CLAIM, f"Considérons ceci: {prop.content}")
        else:
            return self._create_move(SpeechAct.UNDERSTAND, "Peut-être devrions-nous aborder cela différemment")
    
    def _generate_response(self, incoming_move: DialogueMove) -> Optional[DialogueMove]:
        """Génère une réponse appropriée selon la stratégie"""
        if self.strategy == "collaborative":
            return self._collaborative_response(incoming_move)
        elif self.strategy == "skeptical":
            return self._skeptical_response(incoming_move)
        else:
            return self._default_response(incoming_move)
    
    def _collaborative_response(self, move: DialogueMove) -> Optional[DialogueMove]:
        """Stratégie collaborative - cherche à progresser vers la compréhension"""
        if move.act == SpeechAct.QUESTION:
            # Cherche dans sa base de connaissances pour une réponse pertinente
            topic_words = str(move.content).lower().split()
            relevant_props = []
            
            for prop in self.kb.get_all_propositions():
                if any(word in prop.content.lower() for word in topic_words):
                    relevant_props.append(prop)
            
            if relevant_props:
                best_prop = max(relevant_props, key=lambda p: p.confidence)
                return self._create_move(SpeechAct.CLAIM, f"Selon mes connaissances: {best_prop.content}")
            else:
                return self._create_move(SpeechAct.QUESTION, f"Que savez-vous sur ce sujet?")
        
        elif move.act == SpeechAct.CLAIM:
            # Évalue la revendication par rapport à sa base de connaissances
            topic_words = str(move.content).lower().split()
            supporting_props = []
            conflicting_props = []
            
            for prop in self.kb.get_all_propositions():
                if any(word in prop.content.lower() for word in topic_words):
                    if "not" in str(move.content).lower() or "pas" in str(move.content).lower():
                        conflicting_props.append(prop)
                    else:
                        supporting_props.append(prop)
            
            if supporting_props:
                best_support = max(supporting_props, key=lambda p: p.confidence)
                return self._create_move(SpeechAct.SUPPORT, f"Je suis d'accord. {best_support.content}")
            elif conflicting_props:
                best_conflict = max(conflicting_props, key=lambda p: p.confidence)
                return self._create_move(SpeechAct.CHALLENGE, f"J'ai des réserves. {best_conflict.content}")
            else:
                return self._create_move(SpeechAct.QUESTION, "Pouvez-vous m'expliquer votre raisonnement?")
        
        elif move.act == SpeechAct.SUPPORT:
            return self._create_move(SpeechAct.UNDERSTAND, "Merci pour cette information utile")
        
        elif move.act == SpeechAct.CHALLENGE:
            # Répond au défi avec des preuves
            relevant_props = []
            for prop in self.kb.get_all_propositions():
                if prop.confidence > 0.8:  # Propositions très fiables
                    relevant_props.append(prop)
            
            if relevant_props:
                evidence = random.choice(relevant_props)
                return self._create_move(SpeechAct.ARGUE, f"Voici mon argument: {evidence.content}")
            else:
                return self._create_move(SpeechAct.QUESTION, "Qu'est-ce qui vous fait douter?")
        
        elif move.act == SpeechAct.ARGUE:
            return self._create_move(SpeechAct.UNDERSTAND, "C'est un point de vue intéressant")
        
        return self._create_move(SpeechAct.UNDERSTAND, "Je note votre point")
    
    def _skeptical_response(self, move: DialogueMove) -> Optional[DialogueMove]:
        """Stratégie sceptique améliorée - challenge de façon constructive"""
        if move.act == SpeechAct.QUESTION:
            # Au lieu de dire "pas pertinente", pose une contre-question
            counter_questions = [
                f"Avant de répondre à '{move.content}', ne devrait-on pas définir les termes?",
                f"Cette question sur '{move.content}' est-elle vraiment la plus importante?",
                f"Avez-vous des preuves pour justifier cette question sur '{move.content}'?"
            ]
            return self._create_move(SpeechAct.QUESTION, random.choice(counter_questions))
        
        elif move.act == SpeechAct.CLAIM:
            # Challenge avec des propositions de sa base de connaissances
            topic_words = str(move.content).lower().split()
            counter_props = []
            
            for prop in self.kb.get_all_propositions():
                if any(word in prop.content.lower() for word in topic_words):
                    counter_props.append(prop)
            
            if counter_props:
                counter = random.choice(counter_props)
                return self._create_move(SpeechAct.CHALLENGE, f"Mais que dire de ceci: {counter.content}?")
            else:
                challenges = [
                    f"Je doute de cette affirmation: '{move.content}'. Quelles sont vos preuves?",
                    f"Cette idée me semble discutable: '{move.content}'. Avez-vous considéré les alternatives?",
                    f"Je ne suis pas convaincu par: '{move.content}'. Sur quoi vous basez-vous?"
                ]
                return self._create_move(SpeechAct.CHALLENGE, random.choice(challenges))
        
        elif move.act == SpeechAct.SUPPORT:
            return self._create_move(SpeechAct.CHALLENGE, "Ce soutien me semble insuffisant. Avez-vous d'autres arguments?")
        
        elif move.act == SpeechAct.ARGUE:
            # Cherche des contre-arguments dans sa base
            relevant_props = [p for p in self.kb.get_all_propositions() if p.confidence > 0.7]
            if relevant_props:
                counter_arg = random.choice(relevant_props)
                return self._create_move(SpeechAct.REFUTE, f"Je conteste avec ceci: {counter_arg.content}")
            else:
                return self._create_move(SpeechAct.CHALLENGE, "Cet argument n'est pas assez solide pour me convaincre")
        
        elif move.act == SpeechAct.CHALLENGE:
            # Même un sceptique peut parfois concéder
            if random.random() < 0.3:  # 30% de chance de concéder
                return self._create_move(SpeechAct.CONCEDE, "Vous marquez un point intéressant")
            else:
                return self._create_move(SpeechAct.QUESTION, "Pouvez-vous être plus précis dans votre challenge?")
        
        return self._default_response(move)
    
    def _default_response(self, move: DialogueMove) -> Optional[DialogueMove]:
        """Réponse par défaut variée"""
        default_responses = [
            "Je note votre point",
            "C'est une perspective intéressante",
            "Pouvez-vous développer?",
            "Je vois votre point de vue",
            "Continuons cette discussion"
        ]
        return self._create_move(SpeechAct.UNDERSTAND, random.choice(default_responses))
    
    def get_dialogue_summary(self) -> Dict[str, Any]:
        """Génère un résumé du dialogue"""
        if not self.dialogue_history:
            return {}
        
        move_counts = {}
        for move in self.dialogue_history:
            act = move.act.value
            move_counts[act] = move_counts.get(act, 0) + 1
        
        return {
            "dialogue_id": self.current_dialogue_id,
            "total_moves": len(self.dialogue_history),
            "move_distribution": move_counts,
            "duration": (self.dialogue_history[-1].timestamp - self.dialogue_history[0].timestamp).total_seconds(),
            "final_state": "terminated" if self.protocol.is_terminal_state(self.dialogue_history) else "ongoing"
        }
