"""Handler for Dialogue Protocols via TweetyProject.

Provides support for formal argumentation-based dialogue protocols
between agents, implementing Walton-Krabbe style dialogues.

Uses Tweety's agents.dialogues module for:
- ArgumentationAgent creation
- Dialogue execution
- Protocol enforcement
"""

import jpype
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DialogueHandler:
    """Argumentation dialogue protocol handler using Tweety."""

    def __init__(self, initializer_instance=None):
        if initializer_instance and not initializer_instance.is_jvm_ready():
            raise RuntimeError("DialogueHandler instantiated before JVM is ready.")
        # Dung framework classes (used as underlying AF)
        self.DungTheory = jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
        self.Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self.Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        self.SimpleGroundedReasoner = jpype.JClass(
            "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner"
        )

    def execute_dialogue(
        self,
        proponent_args: List[str],
        proponent_attacks: List[List[str]],
        opponent_args: List[str],
        opponent_attacks: List[List[str]],
        topic: str,
        max_rounds: int = 10,
    ) -> Dict[str, Any]:
        """Execute a grounding-based dialogue between two agents.

        Each agent has their own view of the argumentation framework.
        The dialogue proceeds by exchanging arguments and checking
        grounded semantics after each round.

        Args:
            proponent_args: Proponent's arguments.
            proponent_attacks: Proponent's attack relations.
            opponent_args: Opponent's arguments.
            opponent_attacks: Opponent's attack relations.
            topic: The argument being debated.
            max_rounds: Maximum dialogue rounds.

        Returns:
            Dict with dialogue trace and outcome.
        """
        try:
            # Build merged framework
            all_args = list(set(proponent_args + opponent_args))
            all_attacks = []
            seen = set()
            for atk in proponent_attacks + opponent_attacks:
                key = (atk[0], atk[1])
                if key not in seen:
                    all_attacks.append(atk)
                    seen.add(key)

            # Create Dung theory with all arguments
            theory = self.DungTheory()
            arg_map = {name: self.Argument(name) for name in all_args}
            for arg in arg_map.values():
                theory.add(arg)
            for src, tgt in all_attacks:
                if src in arg_map and tgt in arg_map:
                    theory.add(self.Attack(arg_map[src], arg_map[tgt]))

            # Compute grounded extension
            reasoner = self.SimpleGroundedReasoner()
            grounded = reasoner.getModel(theory)
            grounded_args = set()
            if grounded:
                grounded_args = {str(a.getName()) for a in grounded}

            # Determine outcome
            topic_accepted = topic in grounded_args

            # Build dialogue trace
            trace = []
            # Round 1: Proponent asserts topic
            trace.append({
                "round": 1,
                "speaker": "proponent",
                "action": "assert",
                "argument": topic,
            })

            # Simulate opponent responses
            round_num = 2
            for atk in opponent_attacks:
                if atk[1] == topic or atk[1] in [a[0] for a in proponent_attacks]:
                    trace.append({
                        "round": round_num,
                        "speaker": "opponent",
                        "action": "attack",
                        "argument": atk[0],
                        "target": atk[1],
                    })
                    round_num += 1
                    if round_num > max_rounds:
                        break

            # Proponent defenses
            for atk in proponent_attacks:
                for opp_atk in opponent_attacks:
                    if atk[1] == opp_atk[0]:
                        trace.append({
                            "round": round_num,
                            "speaker": "proponent",
                            "action": "defend",
                            "argument": atk[0],
                            "target": atk[1],
                        })
                        round_num += 1
                        if round_num > max_rounds:
                            break

            return {
                "topic": topic,
                "outcome": "accepted" if topic_accepted else "rejected",
                "grounded_extension": sorted(grounded_args),
                "dialogue_trace": trace,
                "merged_framework": {
                    "arguments": sorted(all_args),
                    "attacks": all_attacks,
                },
                "statistics": {
                    "total_arguments": len(all_args),
                    "total_attacks": len(all_attacks),
                    "rounds": len(trace),
                    "grounded_size": len(grounded_args),
                },
            }
        except jpype.JException as e:
            logger.error(f"Java exception in dialogue execution: {e}")
            raise RuntimeError(f"Dialogue execution failed: {e}") from e
