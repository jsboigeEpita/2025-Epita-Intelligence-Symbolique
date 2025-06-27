#!/usr/bin/env python3
"""
Dialogical Argumentation System
A multi-agent debate system where AI agents with different personalities 
argue about various topics using structured argumentation.
"""

from openai import OpenAI
import asyncio
import json
import random
import time
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import os

# Set up OpenAI client (you'll need to set this environment variable)
try:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except Exception:
    client = None  # Will be handled in the validation step

@dataclass
class Argument:
    """Represents a single argument in the debate"""
    agent_name: str
    position: str  # "for" or "against"
    content: str
    argument_type: str  # "claim", "evidence", "rebuttal", "counter-rebuttal"
    timestamp: str
    references: List[str] = None  # References to previous arguments
    strength: float = 0.0  # Argument strength (0-1)

@dataclass
class DebateState:
    """Tracks the current state of the debate"""
    topic: str
    agents: List[str]
    arguments: List[Argument]
    current_turn: int
    max_turns: int
    winner: Optional[str] = None
    audience_votes: Dict[str, int] = None

class ArgumentationAgent:
    """Base class for argumentation agents"""
    
    def __init__(self, name: str, personality: str, position: str):
        self.name = name
        self.personality = personality
        self.position = position  # "for" or "against"
        self.memory = []  # Store previous arguments for context
        
    async def generate_argument(self, debate_state: DebateState, argument_type: str = "claim") -> Argument:
        """Generate an argument based on current debate state"""
        
        # Build context from previous arguments
        context = self._build_context(debate_state)
        
        # Create prompt based on personality and argument type
        prompt = self._create_prompt(debate_state.topic, context, argument_type)
        
        try:
            response = await self._call_gpt(prompt)
            
            argument = Argument(
                agent_name=self.name,
                position=self.position,
                content=response.strip(),
                argument_type=argument_type,
                timestamp=datetime.now().isoformat(),
                references=self._extract_references(context),
                strength=self._calculate_strength(response)
            )
            
            self.memory.append(argument)
            return argument
            
        except Exception as e:
            print(f"Error generating argument for {self.name}: {e}")
            return self._fallback_argument(debate_state.topic, argument_type)
    
    def _build_context(self, debate_state: DebateState) -> str:
        """Build context from recent arguments"""
        recent_args = debate_state.arguments[-5:]  # Last 5 arguments
        context_parts = []
        
        for arg in recent_args:
            context_parts.append(f"{arg.agent_name} ({arg.position}): {arg.content}")
        
        return "\n".join(context_parts)
    
    def _create_prompt(self, topic: str, context: str, argument_type: str) -> str:
        """Create a prompt for GPT based on agent personality and argument type"""
        
        base_prompt = f"""You are {self.name}, an AI agent with the following personality: {self.personality}

You are debating the topic: "{topic}"
Your position: {self.position.upper()}

Previous arguments in this debate:
{context}

Generate a {argument_type} that is:
1. Consistent with your personality and position
2. Logically structured and persuasive
3. Directly addresses the topic and previous arguments
4. Between 50-150 words
5. Professional but reflects your personality

Your {argument_type}:"""

        return base_prompt
    
    async def _call_gpt(self, prompt: str) -> str:
        """Call OpenAI GPT API"""
        if client is None:
            raise Exception("OpenAI client not initialized. Please set OPENAI_API_KEY.")
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are participating in a structured debate. Provide clear, logical arguments."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling GPT API: {e}")
            return f"I maintain my {self.position} stance on this important topic."
    
    def _extract_references(self, context: str) -> List[str]:
        """Extract references to previous arguments"""
        # Simple implementation - could be enhanced with NLP
        return []
    
    def _calculate_strength(self, argument_text: str) -> float:
        """Calculate argument strength based on content"""
        # Simple heuristic - could be enhanced with ML
        strength = 0.5
        
        # Check for evidence indicators
        evidence_words = ["studies show", "research indicates", "data suggests", "according to", "evidence"]
        for word in evidence_words:
            if word in argument_text.lower():
                strength += 0.1
        
        # Check for logical connectors
        logic_words = ["therefore", "because", "since", "thus", "hence", "consequently"]
        for word in logic_words:
            if word in argument_text.lower():
                strength += 0.05
        
        return min(strength, 1.0)
    
    def _fallback_argument(self, topic: str, argument_type: str) -> Argument:
        """Fallback argument if GPT call fails"""
        fallback_content = f"I maintain my {self.position} position on {topic}. This is an important issue that requires careful consideration."
        
        return Argument(
            agent_name=self.name,
            position=self.position,
            content=fallback_content,
            argument_type=argument_type,
            timestamp=datetime.now().isoformat(),
            strength=0.3
        )

class DebateModerator:
    """Manages the debate flow and rules"""
    
    def __init__(self):
        self.debate_rules = {
            "max_turns_per_agent": 5,
            "max_argument_length": 150,
            "required_argument_types": ["claim", "evidence", "rebuttal"]
        }
    
    async def run_debate(self, topic: str, agents: List[ArgumentationAgent], max_turns: int = 10) -> DebateState:
        """Run a complete debate between agents"""
        
        debate_state = DebateState(
            topic=topic,
            agents=[agent.name for agent in agents],
            arguments=[],
            current_turn=0,
            max_turns=max_turns,
            audience_votes={}
        )
        
        print(f"\n🎭 Starting debate on: {topic}")
        print(f"📋 Participants: {', '.join([f'{agent.name} ({agent.position})' for agent in agents])}")
        print("=" * 80)
        
        # Debate loop
        for turn in range(max_turns):
            for agent in agents:
                if debate_state.current_turn >= max_turns:
                    break
                
                # Determine argument type based on turn
                argument_type = self._determine_argument_type(debate_state, agent)
                
                print(f"\n🗣️  Turn {debate_state.current_turn + 1}: {agent.name} ({agent.position})")
                
                # Generate argument
                argument = await agent.generate_argument(debate_state, argument_type)
                debate_state.arguments.append(argument)
                
                # Display argument
                print(f"📝 {argument.content}")
                print(f"💪 Strength: {argument.strength:.2f}")
                
                debate_state.current_turn += 1
                
                # Add pause for readability
                await asyncio.sleep(1)
        
        # Determine winner
        winner = self._determine_winner(debate_state)
        debate_state.winner = winner
        
        print("\n" + "=" * 80)
        print(f"🏆 Debate concluded! Winner: {winner}")
        
        return debate_state
    
    def _determine_argument_type(self, debate_state: DebateState, agent: ArgumentationAgent) -> str:
        """Determine what type of argument the agent should make"""
        agent_args = [arg for arg in debate_state.arguments if arg.agent_name == agent.name]
        
        if len(agent_args) == 0:
            return "claim"
        elif len(agent_args) == 1:
            return "evidence"
        else:
            return "rebuttal"
    
    def _determine_winner(self, debate_state: DebateState) -> str:
        """Determine debate winner based on argument quality"""
        agent_scores = {}
        
        for agent_name in debate_state.agents:
            agent_args = [arg for arg in debate_state.arguments if arg.agent_name == agent_name]
            
            # Calculate score based on argument strength and variety
            total_strength = sum(arg.strength for arg in agent_args)
            argument_types = set(arg.argument_type for arg in agent_args)
            variety_bonus = len(argument_types) * 0.1
            
            agent_scores[agent_name] = total_strength + variety_bonus
        
        return max(agent_scores, key=agent_scores.get)

class ArgumentationSystem:
    """Main system that orchestrates the argumentation"""
    
    def __init__(self):
        self.moderator = DebateModerator()
        self.agent_personalities = {
            "The Scholar": "You are academic and evidence-based. You rely on research, studies, and logical reasoning. You speak formally and cite sources when possible.",
            "The Pragmatist": "You focus on practical implications and real-world consequences. You're concerned with what works in practice rather than theory.",
            "The Devil's Advocate": "You challenge assumptions and play devil's advocate. You're contrarian and enjoy pointing out flaws in reasoning.",
            "The Idealist": "You argue from principles and moral foundations. You believe in doing what's right regardless of practical considerations.",
            "The Skeptic": "You question everything and demand strong evidence. You're naturally suspicious of claims and prefer proof over assertions.",
            "The Populist": "You represent common sense and popular opinion. You speak for the average person and their concerns."
        }
    
    def create_agents(self, topic: str, num_agents: int = 2) -> List[ArgumentationAgent]:
        """Create agents with different personalities for the debate"""
        available_personalities = list(self.agent_personalities.keys())
        selected_personalities = random.sample(available_personalities, min(num_agents, len(available_personalities)))
        
        agents = []
        positions = ["for", "against"]
        
        for i, personality in enumerate(selected_personalities):
            position = positions[i % 2]
            agent = ArgumentationAgent(
                name=personality,
                personality=self.agent_personalities[personality],
                position=position
            )
            agents.append(agent)
        
        return agents
    
    async def start_debate(self, topic: str, num_agents: int = 2, max_turns: int = 10):
        """Start a new debate on the given topic"""
        
        # Validate API key
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ Error: OPENAI_API_KEY environment variable not set!")
            print("Please set your OpenAI API key:")
            print("export OPENAI_API_KEY='your-api-key-here'")
            return None
        
        # Create agents
        agents = self.create_agents(topic, num_agents)
        
        # Run debate
        debate_state = await self.moderator.run_debate(topic, agents, max_turns)
        
        # Save results
        self._save_debate_results(debate_state)
        
        return debate_state
    
    def _save_debate_results(self, debate_state: DebateState):
        """Save debate results to JSON file"""
        filename = f"debate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert to dict for JSON serialization
        debate_dict = asdict(debate_state)
        
        try:
            with open(filename, 'w') as f:
                json.dump(debate_dict, f, indent=2, default=str)
            print(f"💾 Debate saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving debate: {e}")

# Interactive functions
def get_user_input():
    """Get debate topic and parameters from user"""
    print("🎭 Welcome to the Dialogical Argumentation System!")
    print("=" * 50)
    
    topic = input("🤔 What topic would you like the agents to debate? ")
    
    try:
        num_agents = int(input("👥 How many agents? (2-6, default 2): ") or "2")
        num_agents = max(2, min(6, num_agents))
    except ValueError:
        num_agents = 2
    
    try:
        max_turns = int(input("🔄 Maximum turns? (default 10): ") or "10")
        max_turns = max(4, min(20, max_turns))
    except ValueError:
        max_turns = 10
    
    return topic, num_agents, max_turns

async def main():
    """Main function to run the argumentation system"""
    
    # Check if running interactively or with command line arguments
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
        num_agents = 2
        max_turns = 10
    else:
        topic, num_agents, max_turns = get_user_input()
    
    # Create and run the argumentation system
    system = ArgumentationSystem()
    
    print(f"\n🚀 Initializing debate...")
    await system.start_debate(topic, num_agents, max_turns)

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Debate interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please make sure you have set your OPENAI_API_KEY environment variable.")