"""
Conversational multi-agent orchestrator using SK AgentGroupChat.

Restores the original multi-agent dialogue pattern where agents converse,
invoke their specialized plugins as tool calls, and collaboratively enrich
a shared RhetoricalAnalysisState via StateManagerPlugin.

Entry point: run_conversational_analysis()

Usage:
    python run_orchestration.py --text "..." --mode conversational

Architecture:
    - Each agent gets ONLY its specialized plugins + StateManager (shared)
    - PM orchestrates by reading state and designating next agent
    - FunctionChoiceBehavior.Auto() enables agents to invoke plugins as tools
    - ConversationalPipeline manages multi-turn convergence

See docs/architecture/ARCHEOLOGIE_ORCHESTRATION.md for pattern origins.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.orchestration.trace_analyzer import (
    ConversationalTraceAnalyzer,
)

logger = logging.getLogger("ConversationalOrchestrator")

# ---------------------------------------------------------------------------
# Agent-plugin mapping (each agent gets ONLY its specialty + StateManager)
# See ARCHEOLOGIE_ORCHESTRATION.md section 3 for rationale.
# ---------------------------------------------------------------------------

AGENT_PLUGIN_MAP = {
    "ProjectManager": {
        "plugins": [],  # PM uses only StateManager to coordinate
        "instructions": (
            "Tu es le chef de projet d'analyse argumentative. Tu coordonnes l'equipe "
            "d'agents specialises. A chaque tour :\n"
            "1. Lis l'etat courant via get_current_state_snapshot()\n"
            "2. Identifie ce qui manque (arguments? sophismes? formalisation? qualite?)\n"
            "3. Designe l'agent suivant via designate_next_agent(nom_exact)\n"
            "4. Formule une question precise pour cet agent\n\n"
            "CROSS-KB ENRICHMENT (#208-I) — tu dois diriger les synergies entre agents :\n"
            "- Apres InformalAgent : demande a QualityAgent de TENIR COMPTE des sophismes detectes\n"
            "- Apres QualityAgent : demande a CounterAgent de CIBLER les arguments faibles (score < 5/9)\n"
            "- Apres FormalAgent : signale aux autres si des INCONSISTANCES logiques ont ete trouvees\n"
            "- Apres DebateAgent : demande a GovernanceAgent d'evaluer le CONSENSUS du debat\n"
            "- Si JTMS retracte une croyance, signale-le et demande re-evaluation\n\n"
            "Quand tous les aspects sont couverts, appelle set_final_conclusion() avec ta synthese."
        ),
    },
    "ExtractAgent": {
        "plugins": [],  # Uses StateManager to write arguments/claims
        "instructions": (
            "Tu es l'agent d'extraction d'arguments. Quand le PM te donne la parole :\n"
            "1. Analyse le texte pour identifier les arguments, premisses et conclusions\n"
            "2. Pour chaque argument, appelle add_identified_argument(description)\n"
            "3. Identifie les relations entre arguments (support, attaque)\n"
            "Sois precis et exhaustif dans tes extractions."
        ),
    },
    "InformalAgent": {
        "plugins": ["FrenchFallacyPlugin"],
        "instructions": (
            "Tu es l'agent de detection de sophismes. Quand le PM te donne la parole :\n"
            "1. Lis les arguments identifies via get_current_state_snapshot()\n"
            "2. Pour chaque argument, cherche des sophismes (appel a l'autorite, ad hominem, "
            "faux dilemme, pente glissante, ad populum, fausse analogie, tu quoque, etc.)\n"
            "3. Utilise detect_fallacies() pour la detection automatique\n"
            "4. Pour chaque sophisme trouve, appelle add_identified_fallacy(type, justification, target_arg_id)\n"
            "Sois rigoureux : cite le texte exact et explique pourquoi c'est un sophisme.\n\n"
            "CROSS-KB (#208-I) : Si FormalAgent a deja identifie des inconsistances logiques, "
            "verifie si elles correspondent a des sophismes formels (non sequitur, affirmation du consequent)."
        ),
    },
    "FormalAgent": {
        "plugins": ["TweetyLogicPlugin"],
        "instructions": (
            "Tu es l'agent de logique formelle. Quand le PM te donne la parole :\n"
            "1. Lis les arguments identifies dans l'etat\n"
            "2. Traduis les arguments en logique propositionnelle ou du premier ordre\n"
            "3. Utilise add_belief_set() pour enregistrer la formalisation\n"
            "4. Verifie la consistance et les implications logiques\n"
            "5. Enregistre les resultats via log_query_result()\n"
            "Si Tweety n'est pas disponible, fais l'analyse logique manuellement.\n\n"
            "CROSS-KB (#208-I) : Lis les sophismes detectes par InformalAgent — si un argument "
            "est fallacieux, sa formalisation doit refleter cette faiblesse (ex: premisse contestee). "
            "Si NL-to-logic est disponible, utilise-le pour traduire les arguments."
        ),
    },
    "QualityAgent": {
        "plugins": ["QualityScoringPlugin"],
        "instructions": (
            "Tu es l'agent d'evaluation de qualite. Quand le PM te donne la parole :\n"
            "1. Lis les arguments ET les sophismes identifies dans l'etat\n"
            "2. Evalue chaque argument sur les 9 vertus (clarte, pertinence, sources, "
            "refutation, structure logique, analogie, fiabilite, exhaustivite, redondance)\n"
            "3. Utilise evaluate_argument_quality() pour le scoring\n\n"
            "CROSS-KB (#208-I) — ajustements bases sur les autres agents :\n"
            "- Sophismes detectes → REDUIS le score de 'structure logique' et 'fiabilite'\n"
            "- Inconsistances formelles → REDUIS le score de 'coherence'\n"
            "- Argument sans sources citees → REDUIS 'sources' et 'exhaustivite'\n"
            "Fournis un rapport detaille avec scores et justifications."
        ),
    },
    "DebateAgent": {
        "plugins": ["DebatePlugin"],
        "instructions": (
            "Tu es l'agent de debat adversarial. Quand le PM te donne la parole :\n"
            "1. Lis les arguments, sophismes et scores de qualite dans l'etat\n"
            "2. Mene un debat contradictoire : identifie l'argument le plus fort et le plus faible\n"
            "3. Utilise analyze_argument_quality() et suggest_debate_strategy()\n"
            "4. Produis un transcript avec les echanges cles\n\n"
            "CROSS-KB (#208-I) : Utilise les scores de qualite pour calibrer l'intensite du debat. "
            "Les arguments faibles (score < 5) meritent un challenge fort. "
            "Les sophismes detectes sont des cibles prioritaires. "
            "Sois critique et constructif."
        ),
    },
    "CounterAgent": {
        "plugins": ["CounterArgumentPlugin"],
        "instructions": (
            "Tu es l'agent de contre-argumentation. Quand le PM te donne la parole :\n"
            "1. Lis les arguments, sophismes ET scores de qualite dans l'etat\n"
            "2. CIBLE en priorite :\n"
            "   a. Les arguments marques comme fallacieux par InformalAgent\n"
            "   b. Les arguments avec le score de qualite le plus bas\n"
            "   c. Les arguments formellement inconsistants (si FormalAgent l'a signale)\n"
            "3. Utilise parse_argument() et suggest_strategy() pour choisir ta strategie\n"
            "4. Genere des contre-arguments precis (reductio, contre-exemple, distinction, reformulation)\n\n"
            "CROSS-KB (#208-I) : Adapte ta strategie au type de faiblesse :\n"
            "- Sophisme ad hominem → reformulation\n"
            "- Generalisation hative → contre-exemple\n"
            "- Faux dilemme → distinction\n"
            "- Inconsistance logique → reductio ad absurdum\n"
            "Fournis des contre-arguments substantiels, pas des templates."
        ),
    },
    "GovernanceAgent": {
        "plugins": ["GovernancePlugin"],
        "instructions": (
            "Tu es l'agent de gouvernance et vote. Quand le PM te donne la parole :\n"
            "1. Lis les resultats du debat, contre-arguments et scores de qualite dans l'etat\n"
            "2. Evalue le consensus entre les differentes positions\n"
            "3. Utilise detect_conflicts() et compute_consensus_metrics()\n"
            "4. Si necessaire, lance un vote via social_choice_vote()\n\n"
            "CROSS-KB (#208-I) : Base ton evaluation de consensus sur :\n"
            "- Nombre de sophismes detectes (beaucoup = debat de mauvaise qualite)\n"
            "- Scores de qualite moyens (< 5 = consensus fragile)\n"
            "- Resultats du debat adversarial (positions convergentes/divergentes)\n"
            "- Force des contre-arguments (forts = positions contestees)\n"
            "Fournis une evaluation de la solidite du consensus."
        ),
    },
}


def _load_plugin_instance(plugin_name: str) -> Any:
    """Lazy-load a plugin instance by name."""
    loaders = {
        "FrenchFallacyPlugin": lambda: _safe_import(
            "argumentation_analysis.plugins.french_fallacy_plugin", "FrenchFallacyPlugin"
        ),
        "TweetyLogicPlugin": lambda: _safe_import(
            "argumentation_analysis.plugins.tweety_logic_plugin", "TweetyLogicPlugin"
        ),
        "QualityScoringPlugin": lambda: _safe_import(
            "argumentation_analysis.plugins.quality_scoring_plugin", "QualityScoringPlugin"
        ),
        "DebatePlugin": lambda: _safe_import(
            "argumentation_analysis.agents.core.debate.debate_agent", "DebatePlugin"
        ),
        "CounterArgumentPlugin": lambda: _safe_import(
            "argumentation_analysis.agents.core.counter_argument.counter_agent",
            "CounterArgumentPlugin",
        ),
        "GovernancePlugin": lambda: _safe_import(
            "argumentation_analysis.plugins.governance_plugin", "GovernancePlugin"
        ),
    }
    loader = loaders.get(plugin_name)
    if loader is None:
        logger.warning(f"Unknown plugin: {plugin_name}")
        return None
    return loader()


def _safe_import(module_path: str, class_name: str) -> Any:
    """Import and instantiate a class, returning None on failure."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls()
    except Exception as e:
        logger.warning(f"Could not load {class_name} from {module_path}: {e}")
        return None


def create_conversational_agents(
    kernel: sk.Kernel,
    state: RhetoricalAnalysisState,
    llm_service_id: str,
    agent_names: Optional[List[str]] = None,
) -> List[ChatCompletionAgent]:
    """Create agents with specialized plugins for conversational mode.

    Each agent gets:
    - StateManagerPlugin (shared, for reading/writing analysis state)
    - Its own specialized plugins (per AGENT_PLUGIN_MAP)
    - FunctionChoiceBehavior.Auto() for auto tool invocation
    """
    state_manager = StateManagerPlugin(state)
    llm_service = kernel.get_service(llm_service_id)

    if agent_names is None:
        agent_names = list(AGENT_PLUGIN_MAP.keys())

    agents = []
    for name in agent_names:
        config = AGENT_PLUGIN_MAP.get(name)
        if config is None:
            logger.warning(f"Unknown agent name: {name}, skipping")
            continue

        # Build plugin list: StateManager (always) + specialized plugins
        plugins = [state_manager]
        for plugin_name in config["plugins"]:
            plugin = _load_plugin_instance(plugin_name)
            if plugin is not None:
                plugins.append(plugin)

        agent = ChatCompletionAgent(
            kernel=kernel,
            service=llm_service,
            name=name,
            instructions=config["instructions"],
            plugins=plugins,
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                auto_invoke_kernel_functions=True,
                maximum_auto_invoke_attempts=5,
            ),
        )
        agents.append(agent)
        logger.info(
            f"Created agent '{name}' with plugins: "
            f"[StateManager, {', '.join(config['plugins'])}]"
        )

    return agents


async def run_conversational_analysis(
    text: str,
    max_turns_per_phase: int = 5,
    agent_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run a full conversational analysis on the input text.

    Creates agents, sets up an AgentGroupChat, and runs 3 macro-phases:
    1. Extraction + Detection (PM, ExtractAgent, InformalAgent)
    2. Formal Analysis (PM, FormalAgent, QualityAgent)
    3. Synthesis (PM, DebateAgent, CounterAgent, GovernanceAgent)

    Returns dict with state snapshot, conversation history, and metrics.
    """
    start_time = time.time()

    # 1. Setup kernel + LLM
    kernel = sk.Kernel()
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Conversational mode requires an LLM. "
            "Ensure .env is loaded."
        )
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
    llm_service = OpenAIChatCompletion(
        service_id="conversational_llm",
        ai_model_id=model_id,
        api_key=api_key,
    )
    kernel.add_service(llm_service)

    # 2. Setup shared state
    state = RhetoricalAnalysisState(text)

    # 3. Create all agents
    all_agents = create_conversational_agents(
        kernel, state, "conversational_llm", agent_names
    )
    agent_by_name = {a.name: a for a in all_agents}

    # 4. Setup trace analyzer (#208-S)
    trace = ConversationalTraceAnalyzer()
    trace.start()

    # 5. Run 3 macro-phases
    conversation_log = []

    phase_configs = [
        {
            "name": "Extraction & Detection",
            "agents": ["ProjectManager", "ExtractAgent", "InformalAgent"],
            "initial_prompt": (
                f"Analysez ce texte argumentatif. Identifiez les arguments, "
                f"claims et sophismes.\n\nTexte:\n{text}"
            ),
        },
        {
            "name": "Formal Analysis & Quality",
            "agents": ["ProjectManager", "FormalAgent", "QualityAgent"],
            "initial_prompt": (
                "Continuez l'analyse en tenant compte des resultats de Phase 1.\n"
                "CROSS-KB: Les sophismes detectes doivent influencer :\n"
                "- FormalAgent : premisses contestees dans la formalisation\n"
                "- QualityAgent : scores reduits pour les arguments fallacieux\n"
                "Formalisez les arguments en logique et evaluez la qualite."
            ),
        },
        {
            "name": "Synthesis & Debate",
            "agents": ["ProjectManager", "DebateAgent", "CounterAgent", "GovernanceAgent"],
            "initial_prompt": (
                "Finalisez l'analyse en exploitant TOUTES les contributions precedentes.\n"
                "CROSS-KB: Utilisez les resultats des phases 1 et 2 :\n"
                "- DebateAgent : ciblez les arguments avec les scores les plus bas\n"
                "- CounterAgent : ciblez en priorite les arguments fallacieux\n"
                "- GovernanceAgent : evaluez le consensus en tenant compte de la qualite globale\n"
                "Menez un debat adversarial, generez des contre-arguments, evaluez le consensus, "
                "et produisez une conclusion finale."
            ),
        },
    ]

    for phase_cfg in phase_configs:
        phase_name = phase_cfg["name"]
        phase_agent_names = phase_cfg["agents"]
        phase_agents = [
            agent_by_name[n] for n in phase_agent_names if n in agent_by_name
        ]

        if not phase_agents:
            logger.warning(f"No agents available for phase '{phase_name}', skipping")
            continue

        logger.info(
            f"=== Phase: {phase_name} ({len(phase_agents)} agents, "
            f"max {max_turns_per_phase} turns) ==="
        )

        # Trace: capture state before phase
        try:
            trace.begin_phase(phase_name, state.get_state_snapshot(summarize=False))
        except Exception:
            trace.begin_phase(phase_name)

        phase_log = await _run_phase(
            phase_agents,
            phase_cfg["initial_prompt"],
            max_turns=max_turns_per_phase,
            phase_name=phase_name,
        )
        conversation_log.extend(phase_log)

        # Trace: record turns and capture state after phase
        for msg in phase_log:
            trace.record_turn(
                phase=msg.get("phase", phase_name),
                turn=msg.get("turn", 0),
                agent=msg.get("agent", "?"),
                content=msg.get("content", ""),
            )
        try:
            trace.end_phase(phase_name, state.get_state_snapshot(summarize=False))
        except Exception:
            trace.end_phase(phase_name)

    # 6. Stop trace and build results
    trace.stop()
    duration = time.time() - start_time

    try:
        state_snapshot = state.get_state_snapshot(summarize=False)
    except Exception:
        state_snapshot = {}

    # Count non-empty fields
    non_empty = sum(
        1 for v in state_snapshot.values()
        if v and v not in ([], {}, "", None, 0)
    )

    # Generate trace report (#208-S)
    trace_report = trace.generate_report()

    result = {
        "mode": "conversational",
        "phases": [p["name"] for p in phase_configs],
        "conversation_log": conversation_log,
        "total_messages": len(conversation_log),
        "duration_seconds": duration,
        "state_snapshot": state_snapshot,
        "state_non_empty_fields": non_empty,
        "unified_state": state,
        "trace_report": trace_report,
    }

    logger.info(
        f"Conversational analysis complete: {len(conversation_log)} messages, "
        f"{non_empty} state fields, {duration:.1f}s"
    )

    return result


async def _run_phase(
    agents: List[ChatCompletionAgent],
    initial_prompt: str,
    max_turns: int = 5,
    phase_name: str = "",
) -> List[Dict[str, Any]]:
    """Run a single conversational phase with a set of agents.

    Uses SK AgentGroupChat if available, otherwise falls back to
    round-robin invocation.
    """
    messages = []
    chat_history = ChatHistory()
    chat_history.add_user_message(initial_prompt)

    # Try SK native AgentGroupChat first
    try:
        from semantic_kernel.agents.group_chat.agent_group_chat import (
            AgentGroupChat,
        )

        chat = AgentGroupChat(agents=agents)
        # Add initial prompt to the group chat
        await chat.add_chat_message(
            chat_history.messages[-1] if chat_history.messages else initial_prompt
        )
        turn = 0
        async for response in chat.invoke():
            turn += 1
            msg_entry = {
                "phase": phase_name,
                "turn": turn,
                "agent": getattr(response, "name", getattr(response, "role", "?")),
                "content": str(getattr(response, "content", response)),
            }
            messages.append(msg_entry)
            logger.info(f"  [{phase_name}] Turn {turn}: {msg_entry['agent']}")

            if turn >= max_turns:
                break

        return messages

    except ImportError:
        logger.info("SK AgentGroupChat not importable, using round-robin fallback")
    except Exception as e:
        logger.warning(
            f"SK AgentGroupChat failed ({type(e).__name__}: {e}), using round-robin fallback"
        )

    # Fallback: round-robin invocation
    # In SK 1.40, ChatCompletionAgent.invoke() returns an AsyncGenerator
    for turn in range(1, max_turns + 1):
        agent = agents[turn % len(agents)]
        try:
            content = ""
            # SK 1.40: invoke() is an async generator, iterate to collect messages
            async for response in agent.invoke(chat_history):
                chunk = ""
                if hasattr(response, "content"):
                    chunk = str(response.content)
                elif hasattr(response, "value"):
                    chunk = str(response.value)
                else:
                    chunk = str(response)
                content += chunk

            if content:
                chat_history.add_assistant_message(content)

            messages.append({
                "phase": phase_name,
                "turn": turn,
                "agent": agent.name,
                "content": content[:500] if content else "(empty)",
            })
            logger.info(f"  [{phase_name}] Turn {turn}: {agent.name}")

        except Exception as exc:
            logger.error(f"  [{phase_name}] Turn {turn}: {agent.name} failed: {exc}")
            messages.append({
                "phase": phase_name,
                "turn": turn,
                "agent": agent.name,
                "content": f"ERROR: {exc}",
            })

    return messages
