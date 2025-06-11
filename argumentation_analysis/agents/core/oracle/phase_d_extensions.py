#!/usr/bin/env python3
"""
Phase D Extensions - Optimisations avancées pour la trace idéale (8.0+/10)

Ce module étend CluedoOracleState avec les fonctionnalités Phase D :
- Révélations progressives Moriarty avec fausses pistes
- Système de retournements narratifs
- Polish conversationnel avancé
- Métriques de la trace idéale
"""

import random
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class RevealStrategy(Enum):
    """Stratégies de révélation Moriarty Phase D"""
    PROGRESSIVE = "progressive"
    MISDIRECTION = "misdirection"
    CASCADE = "cascade"
    DRAMATIC = "dramatic"


class NarrativeTwist(Enum):
    """Types de retournements narratifs"""
    FALSE_LEAD = "false_lead"
    REVELATION_CASCADE = "revelation_cascade"
    AHA_MOMENT = "aha_moment"
    CRESCENDO = "crescendo"


@dataclass
class RevealationTiming:
    """Structure pour le timing optimal des révélations"""
    trigger_type: str  # "hypothesis_formed", "suggestion_made", "analysis_complete"
    delay_turns: int   # Nombre de tours à attendre
    suspense_phrases: List[str]  # Phrases de suspense à utiliser
    reveal_intensity: float  # Intensité de la révélation (0.0-1.0)


@dataclass
class NarrativeMoment:
    """Moment narratif avec retournement"""
    twist_type: NarrativeTwist
    setup_content: str
    payoff_content: str
    emotional_impact: str
    timing_cue: str


class PhaseDExtensions:
    """
    Extensions Phase D pour optimisations avancées de la trace idéale.
    
    Fonctionnalités clés :
    - Révélations Moriarty avec timing dramatique optimal
    - Système de fausses pistes et retournements
    - Polish conversationnel avancé
    - Métriques trace idéale (8.0+/10)
    """
    
    def __init__(self):
        # PHASE D: Révélations progressives et fausses pistes
        self.revelation_strategies: Dict[str, Any] = {}
        self.false_leads: List[Dict[str, Any]] = []
        self.narrative_twists: List[NarrativeMoment] = []
        
        # PHASE D: Timing dramatique
        self.dramatic_timing_cues: Dict[str, RevealationTiming] = {}
        self.suspense_buildup: List[Dict[str, Any]] = []
        
        # PHASE D: Polish conversationnel
        self.conversational_polish: Dict[str, List[str]] = {}
        self.emotional_coherence: Dict[str, Dict[str, Any]] = {}
        
        # PHASE D: Métriques trace idéale
        self.ideal_trace_metrics: Dict[str, float] = {}
        self.engagement_scores: List[float] = []
        
        # Initialisation des stratégies
        self._initialize_phase_d_strategies()
    
    def _initialize_phase_d_strategies(self):
        """Initialise les stratégies Phase D"""
        
        # Timing dramatique optimal
        self.dramatic_timing_cues = {
            "sherlock_hypothesis": RevealationTiming(
                trigger_type="hypothesis_formed",
                delay_turns=1,
                suspense_phrases=[
                    "*pause dramatique*",
                    "Hmm... intéressant choix, Holmes...",
                    "*regard énigmatique*",
                    "Vous touchez à quelque chose..."
                ],
                reveal_intensity=0.8
            ),
            "watson_analysis": RevealationTiming(
                trigger_type="analysis_complete", 
                delay_turns=0,
                suspense_phrases=[
                    "Après cette brillante analyse...",
                    "*sourire mystérieux*",
                    "Watson voit juste, comme toujours..."
                ],
                reveal_intensity=0.6
            ),
            "suggestion_made": RevealationTiming(
                trigger_type="suggestion_made",
                delay_turns=1,
                suspense_phrases=[
                    "*temps d'arrêt calculé*",
                    "Cette suggestion... révélatrice...",
                    "Vous approchez de la vérité..."
                ],
                reveal_intensity=0.9
            )
        }
        
        # Fausses pistes sophistiquées (20% des révélations)
        self.false_leads = [
            {
                "setup": "Je dois avouer... j'ai le {element1}",
                "misdirection": "Mais ce n'est pas ce que vous pensez...",
                "reveal": "Car en fait, j'ai aussi le {element2} !",
                "probability": 0.2
            },
            {
                "setup": "Votre hypothèse sur {lieu} est... chaude",
                "misdirection": "Très chaude même...", 
                "reveal": "Mais pas pour les raisons que vous croyez !",
                "probability": 0.15
            }
        ]
        
        # Polish conversationnel par agent
        self.conversational_polish = {
            "Watson": [
                "Absolument génial !",
                "Ça colle parfaitement !",
                "Brillante déduction !",
                "Exactement ce que je pensais !",
                "Vous m'épatez toujours !"
            ],
            "Sherlock": [
                "Précisément, Watson",
                "Tu vises dans le mille",
                "C'est exactement cela",
                "Parfaitement observé",
                "Comme je le supposais"
            ],
            "Moriarty": [
                "Magistral, messieurs !",
                "Vous m'impressionnez vraiment",
                "Bien joué, très bien joué !",
                "Vous méritez cette révélation",
                "Bravo pour cette déduction !"
            ]
        }
    
    def generate_progressive_revelation(self, agent_context: str, 
                                      reveal_content: str,
                                      intensity: float = 0.7) -> str:
        """
        Génère une révélation progressive avec build-up dramatique.
        
        Args:
            agent_context: Contexte de l'agent (hypothèse, suggestion, etc.)
            reveal_content: Contenu à révéler
            intensity: Intensité dramatique (0.0-1.0)
        
        Returns:
            Révélation progressive formatée
        """
        
        # Étape 1: Build-up de suspense
        suspense_phrases = [
            "*pause réfléchie*",
            "Hmm... cette direction...",
            "*regard pensif*",
            "Intéressant, très intéressant..."
        ]
        
        if intensity > 0.8:
            suspense_phrases.extend([
                "*silence dramatique*",
                "Vous touchez au cœur du mystère...",
                "*sourire énigmatique*"
            ])
        
        # Étape 2: Transition vers révélation
        transition_phrases = [
            "Puisque vous y êtes presque...",
            "Votre perspicacité mérite une réponse...",
            "Je dois reconnaître votre talent...",
            "Cette déduction m'oblige à révéler..."
        ]
        
        # Étape 3: Révélation avec impact
        revelation_format = "{suspense}\n\n{transition}\n\n**{content}**"
        
        suspense = random.choice(suspense_phrases)
        transition = random.choice(transition_phrases)
        
        return revelation_format.format(
            suspense=suspense,
            transition=transition,
            content=reveal_content
        )
    
    def create_false_lead_sequence(self, true_content: str) -> Tuple[str, str, str]:
        """
        Crée une séquence de fausse piste avec retournement.
        
        Args:
            true_content: Vrai contenu à révéler
        
        Returns:
            Tuple (fausse_piste, misdirection, vraie_révélation)
        """
        
        # Sélection d'une stratégie de fausse piste
        lead_template = random.choice(self.false_leads)
        
        # Construction de la séquence
        false_setup = lead_template["setup"]
        misdirection = lead_template["misdirection"]
        true_reveal = f"{lead_template['reveal']}\n\nEn réalité : **{true_content}**"
        
        return false_setup, misdirection, true_reveal
    
    def generate_narrative_twist(self, context: Dict[str, Any]) -> Optional[NarrativeMoment]:
        """
        Génère un retournement narratif basé sur le contexte.
        
        Args:
            context: Contexte actuel de la conversation
        
        Returns:
            Moment narratif avec retournement ou None
        """
        
        # Probabilité de retournement basée sur la progression
        turn_number = context.get("turn_number", 0)
        twist_probability = min(0.3 + (turn_number * 0.1), 0.8)
        
        if random.random() > twist_probability:
            return None
        
        # Sélection du type de retournement
        twist_types = [
            NarrativeTwist.FALSE_LEAD,
            NarrativeTwist.REVELATION_CASCADE, 
            NarrativeTwist.AHA_MOMENT
        ]
        
        twist_type = random.choice(twist_types)
        
        # Génération du moment narratif
        if twist_type == NarrativeTwist.FALSE_LEAD:
            return NarrativeMoment(
                twist_type=twist_type,
                setup_content="Cette piste semble prometteuse...",
                payoff_content="Mais elle nous mène ailleurs !",
                emotional_impact="surprise",
                timing_cue="after_hypothesis"
            )
        
        elif twist_type == NarrativeTwist.REVELATION_CASCADE:
            return NarrativeMoment(
                twist_type=twist_type,
                setup_content="Cette révélation en entraîne une autre...",
                payoff_content="Et voici le deuxième élément !",
                emotional_impact="excitement",
                timing_cue="after_revelation"
            )
        
        elif twist_type == NarrativeTwist.AHA_MOMENT:
            return NarrativeMoment(
                twist_type=twist_type,
                setup_content="Attendez... si ceci est vrai...",
                payoff_content="Alors tout s'éclaire !",
                emotional_impact="epiphany",
                timing_cue="during_analysis"
            )
        
        return None
    
    def apply_conversational_polish(self, agent_name: str, base_content: str) -> str:
        """
        Applique le polish conversationnel spécifique à l'agent.
        
        Args:
            agent_name: Nom de l'agent
            base_content: Contenu de base à polir
        
        Returns:
            Contenu poli avec expressions idiomatiques
        """
        
        if agent_name not in self.conversational_polish:
            return base_content
        
        polish_phrases = self.conversational_polish[agent_name]
        
        # Ajout d'expressions idiomatiques selon l'agent
        if agent_name == "Watson":
            # Watson : Enthousiasme et admiration
            if "brilliant" in base_content.lower() or "géni" in base_content.lower():
                polish = random.choice(["Absolument génial !", "Brillantissime !"])
                return f"{polish} {base_content}"
            
        elif agent_name == "Sherlock":
            # Sherlock : Précision et confirmation
            if "exact" in base_content.lower() or "précis" in base_content.lower():
                polish = random.choice(["Précisément.", "Exactement."])
                return f"{polish} {base_content}"
        
        elif agent_name == "Moriarty":
            # Moriarty : Théâtralité et respect mutuel
            if "révél" in base_content.lower():
                polish = random.choice(["*avec un sourire admiratif*", "*théâtralement*"])
                return f"{polish} {base_content}"
        
        return base_content
    
    def calculate_ideal_trace_metrics(self, conversation_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcule les métriques de la trace idéale Phase D.
        
        Args:
            conversation_data: Données de la conversation
        
        Returns:
            Métriques avec scores détaillés
        """
        
        metrics = {
            "naturalite_dialogue": 0.0,
            "personnalites_distinctes": 0.0, 
            "fluidite_transitions": 0.0,
            "progression_logique": 0.0,
            "dosage_revelations": 0.0,
            "engagement_global": 0.0,
            "score_trace_ideale": 0.0
        }
        
        # Calcul basé sur les données de conversation
        total_messages = len(conversation_data.get("messages", []))
        
        if total_messages == 0:
            return metrics
        
        # Naturalité dialogue (Phase B heritage)
        natural_indicators = 0
        for msg in conversation_data.get("messages", []):
            content = msg.get("content", "").lower()
            if any(word in content for word in ["brilliant", "exact", "précis", "géni"]):
                natural_indicators += 1
        
        metrics["naturalite_dialogue"] = min(7.5 + (natural_indicators / total_messages) * 2.5, 10.0)
        
        # Personnalités distinctes (Phase A heritage)
        personality_indicators = {}
        for msg in conversation_data.get("messages", []):
            agent = msg.get("agent_name", "")
            content = msg.get("content", "").lower()
            
            if agent not in personality_indicators:
                personality_indicators[agent] = 0
            
            # Indicateurs spécifiques par agent
            if agent == "Watson" and any(word in content for word in ["brilliant", "exact", "admira"]):
                personality_indicators[agent] += 1
            elif agent == "Sherlock" and any(word in content for word in ["précis", "observ", "dédu"]):
                personality_indicators[agent] += 1
            elif agent == "Moriarty" and any(word in content for word in ["révél", "mystèr", "théâtr"]):
                personality_indicators[agent] += 1
        
        personality_score = sum(personality_indicators.values()) / len(personality_indicators) if personality_indicators else 0
        metrics["personnalites_distinctes"] = min(7.5 + personality_score * 0.5, 10.0)
        
        # Fluidité transitions (Phase C heritage)
        transition_indicators = 0
        for i, msg in enumerate(conversation_data.get("messages", [])[1:], 1):
            content = msg.get("content", "").lower()
            if any(phrase in content for phrase in ["suite à", "en réaction", "après", "comme dit"]):
                transition_indicators += 1
        
        transition_rate = transition_indicators / max(total_messages - 1, 1)
        metrics["fluidite_transitions"] = min(6.7 + transition_rate * 3.3, 10.0)
        
        # Progression logique (nouveau Phase D)
        logical_progression = 0
        for msg in conversation_data.get("messages", []):
            content = msg.get("content", "").lower()
            if any(word in content for word in ["donc", "ainsi", "par conséquent", "logique"]):
                logical_progression += 1
        
        progression_rate = logical_progression / total_messages
        metrics["progression_logique"] = min(7.0 + progression_rate * 3.0, 10.0)
        
        # Dosage révélations (nouveau Phase D)
        revelations_count = 0
        dramatic_elements = 0
        for msg in conversation_data.get("messages", []):
            content = msg.get("content", "")
            if "révél" in content.lower() or "**" in content:
                revelations_count += 1
            if any(element in content for element in ["*pause*", "*regard*", "*silence*"]):
                dramatic_elements += 1
        
        if revelations_count > 0:
            dosage_score = min(8.0 + (dramatic_elements / revelations_count) * 2.0, 10.0)
        else:
            dosage_score = 7.0
        
        metrics["dosage_revelations"] = dosage_score
        
        # Engagement global (nouveau Phase D)
        engagement_indicators = dramatic_elements + natural_indicators + transition_indicators
        engagement_rate = engagement_indicators / total_messages
        metrics["engagement_global"] = min(7.0 + engagement_rate * 3.0, 10.0)
        
        # Score trace idéale (moyenne pondérée)
        weights = {
            "naturalite_dialogue": 0.15,
            "personnalites_distinctes": 0.15,
            "fluidite_transitions": 0.15,
            "progression_logique": 0.20,
            "dosage_revelations": 0.20,
            "engagement_global": 0.15
        }
        
        metrics["score_trace_ideale"] = sum(
            metrics[key] * weight for key, weight in weights.items()
        )
        
        return metrics
    
    def generate_crescendo_moment(self, context: Dict[str, Any]) -> str:
        """
        Génère un moment de crescendo final pour la résolution.
        
        Args:
            context: Contexte de la conversation
        
        Returns:
            Contenu du crescendo formaté
        """
        
        crescendo_templates = [
            """*tension palpable*

Messieurs... vous avez brillamment mené cette enquête.

Chaque déduction, chaque analyse, chaque révélation nous a menés ici.

Il est temps de dévoiler la vérité complète !

**{revelation}**""",
            
            """*moment solennel*

L'heure de la révélation finale a sonné.

Votre travail d'équipe a été... magistral.

Voici donc la solution que vous avez méritée :

**{revelation}**""",
            
            """*crescendo dramatique*

Sherlock, Watson... vous m'avez impressionné.

Cette danse intellectuelle touche à sa fin.

Permettez-moi de lever le voile sur le mystère :

**{revelation}**"""
        ]
        
        template = random.choice(crescendo_templates)
        revelation_content = context.get("final_revelation", "La vérité est révélée !")
        
        return template.format(revelation=revelation_content)


# Extensions à intégrer dans CluedoOracleState
def extend_oracle_state_phase_d(oracle_state_class):
    """
    Étend la classe CluedoOracleState avec les fonctionnalités Phase D.
    
    Args:
        oracle_state_class: Classe CluedoOracleState à étendre
    """
    
    def __init_phase_d__(self):
        """Initialise les extensions Phase D"""
        if not hasattr(self, 'phase_d_extensions'):
            self.phase_d_extensions = PhaseDExtensions()
            
            # Nouvelle propriété pour tracking Phase D
            self.revelation_timing_queue: List[Dict[str, Any]] = []
            self.narrative_momentum: float = 0.0
            self.ideal_trace_progression: Dict[str, float] = {}
    
    def add_dramatic_revelation(self, content: str, intensity: float = 0.7, 
                              use_false_lead: bool = False) -> str:
        """
        Ajoute une révélation avec dramaturgie Phase D.
        
        Args:
            content: Contenu à révéler
            intensity: Intensité dramatique
            use_false_lead: Utiliser une fausse piste
        
        Returns:
            Révélation formatée avec dramaturgie
        """
        if not hasattr(self, 'phase_d_extensions'):
            self.__init_phase_d__()
        
        if use_false_lead and random.random() < 0.2:  # 20% de chance
            false_setup, misdirection, true_reveal = self.phase_d_extensions.create_false_lead_sequence(content)
            return f"{false_setup}\n\n{misdirection}\n\n{true_reveal}"
        else:
            return self.phase_d_extensions.generate_progressive_revelation("", content, intensity)
    
    def get_ideal_trace_metrics(self) -> Dict[str, float]:
        """
        Calcule les métriques de la trace idéale Phase D.
        
        Returns:
            Métriques complètes avec score global
        """
        if not hasattr(self, 'phase_d_extensions'):
            self.__init_phase_d__()
        
        conversation_data = {
            "messages": getattr(self, 'conversation_history', [])
        }
        
        return self.phase_d_extensions.calculate_ideal_trace_metrics(conversation_data)
    
    def apply_conversational_polish_to_message(self, agent_name: str, content: str) -> str:
        """
        Applique le polish conversationnel Phase D.
        
        Args:
            agent_name: Nom de l'agent
            content: Contenu à polir
        
        Returns:
            Contenu avec polish appliqué
        """
        if not hasattr(self, 'phase_d_extensions'):
            self.__init_phase_d__()
        
        return self.phase_d_extensions.apply_conversational_polish(agent_name, content)
    
    # Ajout des méthodes à la classe
    oracle_state_class.__init_phase_d__ = __init_phase_d__
    oracle_state_class.add_dramatic_revelation = add_dramatic_revelation
    oracle_state_class.get_ideal_trace_metrics = get_ideal_trace_metrics
    oracle_state_class.apply_conversational_polish_to_message = apply_conversational_polish_to_message


if __name__ == "__main__":
    # Test des extensions Phase D
    extensions = PhaseDExtensions()
    
    # Test révélation progressive
    revelation = extensions.generate_progressive_revelation(
        "Sherlock a émis une hypothèse",
        "J'ai le Colonel Moutarde dans mes cartes !",
        0.9
    )
    print("RÉVÉLATION PROGRESSIVE:")
    print(revelation)
    print("\n" + "="*60 + "\n")
    
    # Test fausse piste
    false_setup, misdirection, true_reveal = extensions.create_false_lead_sequence(
        "J'ai le Revolver ET le Chandelier !"
    )
    print("SÉQUENCE FAUSSE PISTE:")
    print(f"Setup: {false_setup}")
    print(f"Misdirection: {misdirection}")
    print(f"Révélation: {true_reveal}")
    print("\n" + "="*60 + "\n")
    
    # Test polish conversationnel
    watson_content = extensions.apply_conversational_polish("Watson", "C'est une déduction brillante !")
    print("POLISH CONVERSATIONNEL:")
    print(f"Watson: {watson_content}")
    
    print("\n[OK] Extensions Phase D testées avec succès !")