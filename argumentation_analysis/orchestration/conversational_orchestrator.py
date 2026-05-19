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
import re
import time
from typing import Any, Dict, List, Optional

import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.orchestration.trace_analyzer import (
    ConversationalTraceAnalyzer,
)

logger = logging.getLogger("ConversationalOrchestrator")


def _detect_language(text: str) -> str:
    """Detect text language using heuristic word-frequency analysis.

    Distinguishes DE, FR, EN based on common function words and articles.
    Returns ISO 639-1 code: 'de', 'fr', 'en', or 'unknown'.
    """
    sample = text[:3000].lower()
    scores: Dict[str, int] = {"de": 0, "fr": 0, "en": 0}

    de_markers = [
        r"\bder\b", r"\bdie\b", r"\bdas\b", r"\bund\b", r"\bist\b",
        r"\bein\b", r"\beine\b", r"\bden\b", r"\bmit\b", r"\bfür\b",
        r"\bauf\b", r"\bdes\b", r"\bsich\b", r"\bnicht\b", r"\bvon\b",
        r"\bsind\b", r"\bwird\b", r"\bdurch\b", r"\bwir\b", r"\bals\b",
        r"\bauch\b", r"\bnoch\b", r"\bnach\b", r"\büber\b",
    ]
    fr_markers = [
        r"\ble\b", r"\bla\b", r"\bles\b", r"\bde\b", r"\bdes\b",
        r"\bet\b", r"\best\b", r"\bque\b", r"\bqui\b", r"\bdu\b",
        r"\bun\b", r"\bune\b", r"\bpour\b", r"\bdans\b", r"\bsur\b",
        r"\bce\b", r"\bil\b", r"\bne\b", r"\bse\b", r"\bsont\b",
    ]
    en_markers = [
        r"\bthe\b", r"\band\b", r"\bis\b", r"\bto\b", r"\bof\b",
        r"\bin\b", r"\bthat\b", r"\bfor\b", r"\bit\b", r"\bwith\b",
        r"\bas\b", r"\bwas\b", r"\bon\b", r"\bare\b", r"\bhave\b",
        r"\bthis\b", r"\bwe\b", r"\bour\b", r"\bthey\b", r"\bnot\b",
    ]

    for pattern in de_markers:
        scores["de"] += len(re.findall(pattern, sample))
    for pattern in fr_markers:
        scores["fr"] += len(re.findall(pattern, sample))
    for pattern in en_markers:
        scores["en"] += len(re.findall(pattern, sample))

    if max(scores.values()) < 3:
        return "unknown"

    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Agent configuration: instructions + speciality key for plugin loading.
# Plugin instances are loaded via factory.get_plugin_instances() using the
# speciality key, ensuring a single source of truth for plugin→module mapping.
# See ARCHEOLOGIE_ORCHESTRATION.md section 3 for rationale.
# ---------------------------------------------------------------------------

AGENT_CONFIG = {
    "ProjectManager": {
        "speciality": "project_manager",
        "instructions": (
            "Tu es le chef de projet d'analyse argumentative. Tu coordonnes l'equipe "
            "d'agents specialises. A chaque tour :\n"
            "1. Lis l'etat courant via get_current_state_snapshot()\n"
            "2. Identifie ce qui manque (arguments? sophismes? formalisation? qualite? JTMS?)\n"
            "3. Designe l'agent suivant via designate_next_agent(nom_exact)\n"
            "4. Formule une question precise pour cet agent\n\n"
            "EXTRACTION GATE (#595) — AVANT toute autre action :\n"
            "- Verifie state.identified_arguments dans le snapshot. Si la liste est VIDE, "
            "designe ExtractAgent en priorite ABSOLUE et demande-lui d'extraire TOUS les arguments.\n"
            "- Ne passe PAS a InformalAgent, FormalAgent ou autre agent tant que identified_arguments est vide.\n"
            "- Extraire des arguments est plus important que creer des croyances JTMS.\n"
            "- Le minimum acceptable est 3 arguments sur un texte de >5000 mots.\n\n"
            "CROSS-KB ENRICHMENT (#208-I) — tu dois diriger les synergies entre agents :\n"
            "- Apres ExtractAgent : demande-lui d'abord de verifier que identified_arguments est rempli. "
            "ENSUITE seulement, demande de creer des croyances JTMS (jtms_create_belief)\n"
            "- Apres InformalAgent : demande a QualityAgent de TENIR COMPTE des sophismes detectes "
            "en utilisant evaluate_with_cross_kb_context() avec les sophismes en contexte\n"
            "- Apres QualityAgent : demande a CounterAgent de CIBLER les arguments faibles (score < 5/9)\n"
            "- Apres FormalAgent : signale aux autres si des INCONSISTANCES logiques ont ete trouvees\n"
            "- Apres DebateAgent : demande a GovernanceAgent d'evaluer le CONSENSUS avec "
            "detect_conflicts() puis social_choice_vote() si des positions divergent\n"
            "- Si JTMS retracte une croyance (jtms_check_consistency), signale-le et demande re-evaluation\n\n"
            "CONVERGENCE : Quand tous les aspects sont couverts et que le consensus est evalue, "
            "appelle set_final_conclusion() avec ta synthese. Cela signalera la fin de la phase."
        ),
    },
    "ExtractAgent": {
        "speciality": "extract",
        "instructions": (
            "Tu es l'agent d'extraction d'arguments. Quand le PM te donne la parole :\n\n"
            "REGLE CRITIQUE : Tu dois APPELER les fonctions, pas decrire les arguments en prose.\n"
            "Si tu ecris 'Argument 1: ...' sans appeler add_identified_argument(), l'argument est PERDU.\n"
            "Un argument n'existe QUE s'il a ete enregistre via add_identified_argument().\n\n"
            "ETAPE 1 — EXTRACTION (APPELLE LA FONCTION POUR CHAQUE ARGUMENT) :\n"
            "1. Lis le texte source pour identifier les arguments, premisses et conclusions\n"
            "2. Pour CHAQUE argument, appelle IMMEDIATEMENT add_identified_argument(\n"
            "   description='premisses: ... conclusion: ...') — un appel par argument\n"
            "3. Objectif minimum : 3 appels a add_identified_argument sur un texte de >5000 mots\n"
            "4. NE PAS utiliser jtms_create_belief ou add_jtms_belief AVANT add_identified_argument\n\n"
            "ETAPE 2 — JTMS (APRES ETAPE 1 COMPLETE) :\n"
            "Pour chaque argument extrait, cree une croyance JTMS :\n"
            "- jtms_create_belief(belief_name='arg_N', agent_source='ExtractAgent', confidence=0.7)\n"
            "- Si un argument A soutient B : "
            "jtms_add_justification(in_list=['arg_A'], out_list=[], conclusion='arg_B', agent_source='ExtractAgent')\n\n"
            "ORDRE STRICT : add_identified_argument AVANT jtms_create_belief. TOUJOURS."
        ),
    },
    "InformalAgent": {
        "speciality": "informal_fallacy",
        "instructions": (
            "Tu es l'agent de detection de sophismes.\n\n"
            "REGLE CRITIQUE : Tu dois APPELER add_identified_fallacy() pour chaque sophisme detecte.\n"
            "Si tu ecris 'Sophisme: Ad hominem' sans appeler add_identified_fallacy(), le sophisme est PERDU.\n"
            "Un sophisme n'existe QUE s'il a ete enregistre via add_identified_fallacy().\n\n"
            "OUTILS DE DETECTION :\n"
            "- run_guided_analysis() : OBLIGATOIRE en premier. Navigation hierarchique dans la taxonomie.\n"
            "- detect_fallacies() : FALLBACK si run_guided_analysis ne detecte rien.\n\n"
            "WORKFLOW :\n"
            "1. Lis les arguments identifies via get_current_state_snapshot()\n"
            "2. Pour CHAQUE argument, appelle run_guided_analysis(argument_text=texte_argument)\n"
            "3. Pour CHAQUE sophisme detecte, appelle IMMEDIATEMENT add_identified_fallacy(\n"
            "   type='nom_du_sophisme', justification='pourquoi', target_arg_id='arg_N')\n"
            "4. Si aucun argument n'est identifie, analyse le texte brut directement\n\n"
            "OBJECTIF : Sur un texte de >10000 mots, vise au minimum 5 sophismes couvrant 3 familles.\n"
            "Si run_guided_analysis retourne moins de 3 resultats, appele detect_fallacies() en FALLBACK.\n\n"
            "JTMS : Pour chaque sophisme detecte :\n"
            "- jtms_create_belief(belief_name='fallacy_on_arg_N', agent_source='InformalAgent', confidence=0.8)\n"
            "- jtms_retract_belief(belief_name='arg_N', reason='fallacy: type_du_sophisme')\n\n"
            "CROSS-KB : Si FormalAgent a identifie des inconsistances logiques, verifie les sophismes formels."
        ),
    },
    "FormalAgent": {
        "speciality": "formal_logic",
        "instructions": (
            "Tu es l'agent de logique formelle. Quand le PM te donne la parole :\n\n"
            "WORKFLOW OBLIGATOIRE (4 etapes) :\n\n"
            "ETAPE 0 — Build Shared Atom/Signature Inventory (#560/#561) :\n"
            "1. Lis l'etat via get_current_state_snapshot() pour obtenir le texte source\n"
            "2. Appelle extract_shared_pl_atoms(full_text=source_text) pour extraire les atomes PL partages\n"
            "3. Appelle extract_shared_fol_signature(full_text=source_text) pour extraire la signature FOL partagee\n"
            "4. Si atomic_propositions ou fol_shared_signature existent DEJA dans l'etat, saute les appels correspondants\n"
            "5. Stock les resultats via add_belief_set ou dans l'etat pour coherence inter-arguments\n\n"
            "ETAPE 1 — NL → Traduction Formelle (2-pass coordinated) :\n"
            "1. Lis les arguments identifies dans l'etat via get_current_state_snapshot()\n"
            "2. Si une signature FOL partagee existe (ETAPE 0), pour chaque argument cle :\n"
            "   - Appelle generate_fol_formulas_with_shared_signature("
            "argument_text='...', shared_signature=signature_json)\n"
            "3. Si des atomes PL partages existent, pour chaque argument cle :\n"
            "   - Appelle generate_pl_formulas_with_shared_atoms("
            "argument_text='...', shared_atoms=atoms_json)\n"
            "4. Si aucun inventaire partage n'existe (fallback) : utilise translate_to_fol "
            "puis translate_to_pl comme avant\n"
            "5. Stock la traduction via add_nl_to_logic_translation(\n"
            "   original_text='...', formula='...', logic_type='propositional'|'fol',\n"
            "   is_valid=True/False, variables=JSON. confidence=0.0-1.0)\n\n"
            "ETAPE 2 — Validation Tweety :\n"
            "1. Pour les formules valides, appeelle check_propositional_consistency(\n"
            '   input=\'{"formulas": ["p => q", "q"]}\') \n'
            "2. Pour FOL: check_fol_consistency(input='{\"formulas\": [...]}')\n"
            "3. Pour les modalites (possibilite/obligation): check_modal_satisfiability(\n"
            '   input=\'{"formula": "<>P", "logic_type": "S5"}\')\n'
            "4. Si inconstistances: signalez au PM\n\n"
            "ETAPE 3 — Analyse Dung (Argumentation Abstraite) :\n"
            "1. Construis un graphe d'attaque depuis les arguments et sophismes detectes\n"
            "2. Appelle analyze_dung_framework(input=JSON) avec :\n"
            "   - arguments: liste des arguments extraits\n"
            "   - attacks: paires [attaquant, cible] basees sur les contradictions\n"
            "   - semantics: 'preferred' (ou 'grounded', 'stable')\n"
            "3. Les extensions identifient quels arguments sont collectivement acceptables\n"
            "4. CROSS-KB: Les arguments fallacieux (detectes par InformalAgent) doivent "
            "   attaquer les arguments qu'ils ciblent dans le graphe Dung\n\n"
            "ETAPE 4 — Stockage Resultats :\n"
            "1. Utilise add_belief_set(logic_type='propositional', content='formulas')\n"
            "2. Enregistre les resultats via log_query_result(belief_set_id, query, raw_result)\n"
            "3. Stocke FOL results with add_belief_set(logic_type='fol', ...)\n\n"
            "Si Tweety n'est pas disponible, fais l'analyse logique manuellement.\n\n"
            "JTMS : Apres formalisation, ajoute des justifications logiques :\n"
            "- Pour chaque implication P => Q, ajoute :\n"
            "  jtms_add_justification(in_list=['P'], out_list=[], conclusion='Q', agent_source='FormalAgent')\n"
            "- Verifie la consistance JTMS via jtms_check_consistency()\n\n"
            "CROSS-KB (#208-I) : Lis les sophismes detectes par InformalAgent — si un argument "
            "est fallacieux, sa formalisation doit refleter cette faiblesse (ex: premisse contestee).\n"
            "Modal: Si tu detectes des modalites (possibilite/necessite), utilise check_modal_satisfiability()."
        ),
    },
    "QualityAgent": {
        "speciality": "quality",
        "instructions": (
            "Tu es l'agent d'evaluation de qualite. Quand le PM te donne la parole :\n"
            "1. Lis les arguments ET les sophismes identifies dans l'etat via get_current_state_snapshot()\n"
            "2. Pour chaque argument, obtiens d'abord les scores heuristiques de base :\n"
            "   evaluate_argument_quality(text='...') → scores sur 9 vertus\n"
            "3. PUIS, utilise evaluate_with_cross_kb_context(text='...', cross_kb_context=JSON) "
            "en passant les sophismes detectes et resultats formels en contexte JSON :\n"
            '   cross_kb_context = \'{"fallacies": [...], "formal_inconsistencies": [...]}\'\n'
            "4. Le plugin retourne des scores de base + des recommandations d'ajustement\n"
            "5. Applique ton propre raisonnement LLM pour produire des scores AJUSTES finaux\n\n"
            "CROSS-KB (#208-I) — ajustements bases sur les autres agents :\n"
            "- Sophismes detectes → REDUIS le score de 'structure logique' et 'fiabilite' de 2-3 points\n"
            "- Inconsistances formelles → REDUIS le score de 'coherence' de 1-2 points\n"
            "- Argument sans sources citees → REDUIS 'sources' et 'exhaustivite'\n"
            "Fournis un rapport detaille avec scores heuristiques, scores ajustes, et justifications."
        ),
    },
    "DebateAgent": {
        "speciality": "debate",
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
        "speciality": "counter_argument",
        "instructions": (
            "Tu es l'agent de contre-argumentation. Quand le PM te donne la parole :\n"
            "1. Lis l'etat courant via get_current_state_snapshot()\n"
            "2. IDENTIFIE tes cibles dans cet ordre de priorite :\n"
            "   a. TOUS les arguments marques comme fallacieux par InformalAgent\n"
            "   b. Les 3 arguments avec le score de qualite le plus bas\n"
            "   c. Les arguments formellement inconsistants (si FormalAgent l'a signale)\n"
            "3. Pour CHAQUE cible, genere un contre-argument dedie :\n"
            "   - Appelle identify_vulnerabilities(text=argument_cible)\n"
            "   - Choisis la strategie en fonction du type de faiblesse :\n"
            "     * Sophisme ad hominem → reformulation\n"
            "     * Generalisation hative → contre-exemple\n"
            "     * Faux dilemme → distinction\n"
            "     * Inconsistance logique → reductio ad absurdum\n"
            "     * Score evidence faible → contre-exemple avec sources\n"
            "     * Assertion forte sans preuve → distinction\n"
            "   - Genere le contre-argument via suggest_strategy()\n"
            "4. Pour chaque contre-argument, appelle add_counter_argument(\n"
            "   target_argument_id=..., strategy='...', counter_text='...')\n"
            "5. OBJECTIF : produire au moins 1 contre-argument par cible identifiee.\n"
            "   Tu dois traiter TOUTES les cibles, pas seulement la premiere.\n\n"
            "CROSS-KB (#208-I) : Chaque contre-argument DOIT referenceer explicitement :\n"
            "- Le type de faiblesse cible (fallacy type ou quality dimension)\n"
            "- La citation exacte du passage contre-argue\n"
            "- La strategie rhetorique choisie et POURQUOI elle est adaptee\n\n"
            "QUANTITE : Vise au minimum 10 contre-arguments sur un texte dense.\n"
            "Un seul contre-argument generique = echec. Chaque cible merit un contre-argument dedie."
        ),
    },
    "GovernanceAgent": {
        "speciality": "governance",
        "instructions": (
            "Tu es l'agent de gouvernance et vote. Tu disposes de ces outils SPECIFIQUES :\n"
            "- detect_conflicts(positions_json) : detecte les conflits entre positions d'agents. "
            'Input: JSON mapping noms d\'agents → positions (ex: \'{"DebateAgent": "pour", "CounterAgent": "contre"}\')\n'
            "- compute_consensus_metrics(results_json) : calcule taux de consensus. "
            "Input: JSON avec 'votes' et 'winner'\n"
            "- social_choice_vote(input_json) : lance un vote formel. "
            "Input: JSON avec 'method' (copeland/schulze/stv/approval), 'ballots' (listes de preferences), 'options' (candidats). "
            'Ex: \'{"method": "copeland", "ballots": [["A","B","C"],["B","A","C"]], "options": ["A","B","C"]}\'\n'
            "- find_condorcet_winner(input_json) : trouve le vainqueur de Condorcet. "
            "Input: JSON avec 'ballots' et 'options'\n\n"
            "Quand le PM te donne la parole :\n"
            "1. Lis l'etat via get_current_state_snapshot() pour voir les positions des agents\n"
            "2. Construis le JSON des positions a partir du debat et des contre-arguments\n"
            "3. Appelle detect_conflicts() pour identifier les divergences\n"
            "4. Si des positions divergent, organise un VOTE formel via social_choice_vote() :\n"
            "   - Definis les options (les positions en concurrence)\n"
            "   - Construis les ballots a partir des preferences des agents\n"
            "   - Lance le vote avec la methode copeland ou schulze\n"
            "5. Appelle compute_consensus_metrics() sur les resultats du vote\n\n"
            "CROSS-KB (#208-I) : Base ton evaluation de consensus sur :\n"
            "- Nombre de sophismes detectes (beaucoup = debat de mauvaise qualite)\n"
            "- Scores de qualite moyens (< 5 = consensus fragile)\n"
            "- Resultats du debat adversarial (positions convergentes/divergentes)\n"
            "- Force des contre-arguments (forts = positions contestees)\n"
            "Fournis une evaluation de la solidite du consensus avec les metriques calculees."
        ),
    },
}


def create_conversational_agents(
    kernel: sk.Kernel,
    state: RhetoricalAnalysisState,
    llm_service_id: str,
    agent_names: Optional[List[str]] = None,
) -> List[ChatCompletionAgent]:
    """Create agents with specialized plugins for conversational mode.

    Each agent gets:
    - StateManagerPlugin (shared, for reading/writing analysis state)
    - Its own specialized plugins (loaded via factory.get_plugin_instances())
    - FunctionChoiceBehavior.Auto() for auto tool invocation

    Plugin loading is delegated to the central factory registry
    (AGENT_SPECIALITY_MAP + _PLUGIN_REGISTRY) to avoid duplication.
    """
    from argumentation_analysis.agents.factory import get_plugin_instances

    llm_service = kernel.get_service(llm_service_id)

    if agent_names is None:
        agent_names = list(AGENT_CONFIG.keys())

    agents = []
    for name in agent_names:
        config = AGENT_CONFIG.get(name)
        if config is None:
            logger.warning(f"Unknown agent name: {name}, skipping")
            continue

        # Get plugin instances from central factory registry
        speciality = config["speciality"]
        plugins = get_plugin_instances(
            speciality, state=state, kernel=kernel, llm_service=llm_service
        )

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
        plugin_names = [type(p).__name__ for p in plugins]
        logger.info(
            f"Created agent '{name}' (speciality={speciality}) with plugins: {plugin_names}"
        )

    return agents


async def run_conversational_analysis(
    text: str,
    max_turns_per_phase: int = 5,
    agent_names: Optional[List[str]] = None,
    spectacular: bool = True,
    extraction_max_turns: int = 7,
    formal_max_turns: int = 5,
    synthesis_max_turns: int = 10,
    reanalysis_max_turns: int = 5,
    enable_growth_validation: bool = True,
    growth_re_prompt_limit: int = 2,
    enable_reprompt_tracing: bool = False,
) -> Dict[str, Any]:
    """Run a full conversational analysis on the input text.

    Creates agents, sets up an AgentGroupChat, and runs 3 macro-phases:
    1. Extraction + Detection (PM, ExtractAgent, InformalAgent)
    2. Formal Analysis (PM, FormalAgent, QualityAgent)
    3. Synthesis (PM, DebateAgent, CounterAgent, GovernanceAgent)

    Args:
        text: Input text to analyze.
        max_turns_per_phase: Default max turns per phase (overridden by specific params).
        agent_names: Optional subset of agent names to use.
        spectacular: If True, use UnifiedAnalysisState for 28+/32 field
            coverage matching the spectacular workflow profile (#363).
        extraction_max_turns: Max turns for Extraction & Detection phase.
        formal_max_turns: Max turns for Formal Analysis & Quality phase.
        synthesis_max_turns: Max turns for Synthesis & Debate phase.
        reanalysis_max_turns: Max turns for Re-Analysis phase (if triggered).
        enable_growth_validation: If True, re-prompt agents on zero-growth
            turns in Extraction/Detection/Re-Analysis phases (#597).
        growth_re_prompt_limit: Max re-prompts per turn when growth is absent.
        enable_reprompt_tracing: If True, capture structured RepromptTrace
            records from growth validation re-prompt events (#609).

    Returns dict with state snapshot, conversation history, and metrics.
    """
    start_time = time.time()

    # 0b. Env var override for growth validation (#597)
    _env_growth = os.environ.get("ENABLE_GROWTH_VALIDATION", "").lower()
    if _env_growth in ("0", "false", "no"):
        enable_growth_validation = False

    # 0c. Re-prompt trace accumulator (#609)
    reprompt_extractor = None
    if enable_reprompt_tracing:
        from argumentation_analysis.reporting.reprompt_trace import RepromptTraceExtractor
        reprompt_extractor = RepromptTraceExtractor()

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

    # 2. Setup shared state (#363: UnifiedAnalysisState for spectacular coverage)
    state_cls = UnifiedAnalysisState if spectacular else RhetoricalAnalysisState
    state = state_cls(text)

    # 3. Create all agents
    all_agents = create_conversational_agents(
        kernel, state, "conversational_llm", agent_names
    )
    agent_by_name = {a.name: a for a in all_agents}

    # 4. Setup trace analyzer (#208-S)
    trace = ConversationalTraceAnalyzer()
    trace.start()

    # 4b. Detect text language for adaptive prompting (#539)
    detected_lang = _detect_language(text)
    if detected_lang != "en" and detected_lang != "unknown":
        logger.info(f"Detected non-English text language: {detected_lang}")

    # 5. Run 3 macro-phases
    conversation_log = []

    extraction_prompt = (
        f"Analysez ce texte argumentatif. Identifiez les arguments, "
        f"claims et sophismes.\n\nTexte:\n{text}"
    )
    if detected_lang == "de":
        extraction_prompt = (
            f"Analysez ce texte argumentatif. Identifiez les arguments, "
            f"claims et sophismes.\n\n"
            f"IMPORTANT : Le texte est en allemand. Pour la detection de sophismes "
            f"(InformalAgent), traduisez mentalement les passages en anglais avant "
            f"d'appliquer la taxonomie de sophismes. Pour les citations textuelles, "
            f"conservez IMPERATIVEMENT le texte original allemand — ne traduisez "
            f"jamais les citations. Les arguments doivent etre extraits en anglais "
            f"avec citations en allemand.\n\n"
            f"Texte:\n{text}"
        )

    phase_configs = [
        {
            "name": "Extraction & Detection",
            "agents": ["ProjectManager", "ExtractAgent", "InformalAgent"],
            "max_turns": extraction_max_turns,
            "initial_prompt": extraction_prompt,
        },
        {
            "name": "Formal Analysis & Quality",
            "agents": ["ProjectManager", "FormalAgent", "QualityAgent"],
            "max_turns": formal_max_turns,
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
            "agents": [
                "ProjectManager",
                "DebateAgent",
                "CounterAgent",
                "GovernanceAgent",
            ],
            "max_turns": synthesis_max_turns,
            "initial_prompt": (
                "Finalisez l'analyse en exploitant TOUTES les contributions precedentes.\n"
                "CROSS-KB: Utilisez les resultats des phases 1 et 2 :\n"
                "- DebateAgent : ciblez les arguments avec les scores les plus bas\n"
                "- CounterAgent : TRAITEZ SYSTEMATIQUEMENT chaque argument fallacieux ET chaque "
                "argument faible. Ne vous contentez pas d'un contre-argument generique. "
                "Pour CHAQUE cible, produisez un contre-argument dedie avec la strategie "
                "rhetorique adaptee au type de faiblesse. Visez au moins 10 contre-arguments.\n"
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

        # Per-phase turn limit (falls back to global max_turns_per_phase)
        phase_max_turns = phase_cfg.get("max_turns", max_turns_per_phase)

        logger.info(
            f"=== Phase: {phase_name} ({len(phase_agents)} agents, "
            f"max {phase_max_turns} turns) ==="
        )

        # Trace: capture state before phase
        try:
            trace.begin_phase(phase_name, state.get_state_snapshot(summarize=False))
        except Exception:
            trace.begin_phase(phase_name)

        phase_log = await _run_phase(
            phase_agents,
            phase_cfg["initial_prompt"],
            max_turns=phase_max_turns,
            phase_name=phase_name,
            state=state,
            enable_growth_validation=enable_growth_validation,
            growth_re_prompt_limit=growth_re_prompt_limit,
            reprompt_extractor=reprompt_extractor,
        )
        conversation_log.extend(phase_log)

        # Conflict resolution (#214): detect and resolve conflicts between agents
        conflict_resolutions = await _resolve_phase_conflicts(
            state, phase_name, strategy="confidence_based"
        )
        if conflict_resolutions:
            conversation_log.append(
                {
                    "phase": phase_name,
                    "type": "conflict_resolution",
                    "resolutions": conflict_resolutions,
                    "resolution_count": len(conflict_resolutions),
                }
            )

        # Parent harness (#578 tier 3): always fire on dense texts after Detection
        if "etection" in phase_name and len(text) > 5000:
            harness_log = await _run_parent_harness_fallback(text, state)
            if harness_log:
                conversation_log.append(harness_log)

        # JTMS retraction on fallacies (#287): automatically retract beliefs
        # associated with detected fallacies between phases.
        retraction_log = _retract_fallacious_beliefs(state, phase_name)
        if retraction_log:
            conversation_log.append(retraction_log)

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

    # 5b. Conditional Phase 4: Re-Analysis (#305)
    # If the enrichment summary shows gaps (e.g., JTMS retracted beliefs not
    # re-evaluated, arguments missing fallacy analysis), add an extra phase
    # to re-analyze using informal + quality + governance agents.
    reanalysis_added = False
    if hasattr(state, "get_enrichment_summary"):
        try:
            enrichment = state.get_enrichment_summary()
            needs_reanalysis = _should_add_reanalysis_phase(enrichment, state)
            if needs_reanalysis:
                reanalysis_cfg = {
                    "name": "Re-Analysis",
                    "agents": [
                        "ProjectManager",
                        "InformalAgent",
                        "QualityAgent",
                        "GovernanceAgent",
                    ],
                    "max_turns": reanalysis_max_turns,
                    "initial_prompt": (
                        "Re-analysez en tenant compte des resultats de l'analyse formelle.\n"
                        "JTMS a retracte certaines croyances. Re-evaluez :\n"
                        "- InformalAgent : re-detectez les sophismes sur les arguments invalides\n"
                        "- QualityAgent : ajustez les scores de qualite\n"
                        "- GovernanceAgent : re-evaluez le consensus\n"
                        "Basez-vous sur les retractations JTMS et les lacunes identifiees."
                        + (
                            "\n\nRAPPEL : Le texte est en allemand. Traduisez mentalement "
                            "en anglais pour la detection de sophismes. "
                            "Conservez les citations en allemand."
                            if detected_lang == "de" else ""
                        )
                    ),
                }

                reanalysis_agents = [
                    agent_by_name[n]
                    for n in reanalysis_cfg["agents"]
                    if n in agent_by_name
                ]

                if reanalysis_agents:
                    reanalysis_added = True
                    phase_name = reanalysis_cfg["name"]
                    logger.info(
                        f"=== Phase: {phase_name} ({len(reanalysis_agents)} agents, "
                        f"max {reanalysis_cfg['max_turns']} turns) ==="
                    )

                    try:
                        trace.begin_phase(
                            phase_name, state.get_state_snapshot(summarize=False)
                        )
                    except Exception:
                        trace.begin_phase(phase_name)

                    phase_log = await _run_phase(
                        reanalysis_agents,
                        reanalysis_cfg["initial_prompt"],
                        max_turns=reanalysis_cfg["max_turns"],
                        phase_name=phase_name,
                        state=state,
                        enable_growth_validation=enable_growth_validation,
                        growth_re_prompt_limit=growth_re_prompt_limit,
                        reprompt_extractor=reprompt_extractor,
                    )
                    conversation_log.extend(phase_log)

                    # Trace recording
                    for msg in phase_log:
                        trace.record_turn(
                            phase=msg.get("phase", phase_name),
                            turn=msg.get("turn", 0),
                            agent=msg.get("agent", "?"),
                            content=msg.get("content", ""),
                        )
                    try:
                        trace.end_phase(
                            phase_name, state.get_state_snapshot(summarize=False)
                        )
                    except Exception:
                        trace.end_phase(phase_name)

                    phase_configs.append(reanalysis_cfg)
        except Exception as e:
            logger.warning(f"Re-analysis phase check failed: {e}")

    # 5b-2. Dung framework construction (#564)
    # Build Dung AF from identified_arguments + counter_arguments/fallacies
    # after all conversational phases have populated the state.
    dung_result = None
    if spectacular and hasattr(state, "dung_frameworks") and not state.dung_frameworks:
        try:
            dung_result = _build_dung_framework_from_state(state)
            if dung_result:
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "dung_framework",
                        "arguments": dung_result["arguments"],
                        "attacks": dung_result["attacks"],
                    }
                )
        except Exception as e:
            logger.warning(f"Dung framework post-processing failed: {e}")

    # 5b-3. Modal logic analysis (#563)
    # Detect modal markers in arguments and persist modal_analysis_results.
    modal_result = None
    if spectacular and hasattr(state, "modal_analysis_results"):
        try:
            modal_result = _detect_and_run_modal_analysis(state)
            if modal_result:
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "modal_analysis",
                        "results": modal_result["modal_results"],
                        "modalities": modal_result["modalities_found"],
                    }
                )
        except Exception as e:
            logger.warning(f"Modal analysis post-processing failed: {e}")

    # 5b-4. ASPIC+ framework construction (#565)
    # Build ASPIC strict/defeasible rules from arguments and fallacy targeting.
    aspic_result = None
    if spectacular and hasattr(state, "aspic_results") and not state.aspic_results:
        try:
            aspic_result = _build_aspic_from_state(state)
            if aspic_result:
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "aspic_framework",
                        "strict_rules": aspic_result["strict_rules"],
                        "defeasible_rules": aspic_result["defeasible_rules"],
                        "surviving": aspic_result["surviving"],
                        "defeated": aspic_result["defeated"],
                    }
                )
        except Exception as e:
            logger.warning(f"ASPIC post-processing failed: {e}")

    # 5b-5. Belief revision (#566)
    # Contract beliefs contradicted by detected fallacies (AGM pattern).
    revision_result = None
    if spectacular and hasattr(state, "belief_revision_results"):
        try:
            revision_result = _run_belief_revision_from_state(state)
            if revision_result:
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "belief_revision",
                        "method": revision_result["method"],
                        "removed": revision_result["removed"],
                    }
                )
        except Exception as e:
            logger.warning(f"Belief revision post-processing failed: {e}")

    # 5c. Deep Synthesis post-phase (#534)
    # Run DeepSynthesisAgent on the accumulated state to produce a 9-section
    # grounded markdown report. Appended as terminal step after all agents.
    deep_synthesis_result = None
    if spectacular:
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _invoke_deep_synthesis,
            )

            source_meta = {
                "opaque_id": getattr(state, "source_id", "conversational_analysis"),
                "era": "",
                "language": detected_lang if detected_lang != "unknown" else "",
                "discourse_type": "",
            }
            ctx = {
                "_state_object": state,
                "source_metadata": source_meta,
            }
            deep_synthesis_result = await _invoke_deep_synthesis("", ctx)
            if "error" not in deep_synthesis_result:
                logger.info(
                    f"Deep synthesis completed: "
                    f"{deep_synthesis_result.get('sections_populated', '?')}/9 sections"
                )
            else:
                logger.warning(
                    f"Deep synthesis skipped: {deep_synthesis_result.get('error', '?')}"
                )
        except Exception as e:
            logger.warning(f"Deep synthesis post-phase failed: {e}")

    # 6. Stop trace and build results
    trace.stop()
    duration = time.time() - start_time

    try:
        state_snapshot = state.get_state_snapshot(summarize=False)
    except Exception:
        state_snapshot = {}

    # Count non-empty fields
    non_empty = sum(
        1 for v in state_snapshot.values() if v and v not in ([], {}, "", None, 0)
    )

    # Generate trace report (#208-S)
    trace_report = trace.generate_report()

    result = {
        "mode": "conversational",
        "workflow_name": "spectacular_analysis" if spectacular else "conversational",
        "phases": [p["name"] for p in phase_configs],
        "conversation_log": conversation_log,
        "total_messages": len(conversation_log),
        "duration_seconds": duration,
        "deep_synthesis": deep_synthesis_result,
        "state_snapshot": state_snapshot,
        "state_non_empty_fields": non_empty,
        "state_total_fields": len(state_snapshot),
        "state_coverage_pct": (
            non_empty / len(state_snapshot) * 100 if state_snapshot else 0
        ),
        "unified_state": state,
        "trace_report": trace_report,
        "reprompt_traces": reprompt_extractor.to_dict() if reprompt_extractor else None,
        "summary": {
            "completed": len(phase_configs),
            "failed": 0,
            "skipped": 0,
            "total": len(phase_configs),
            "total_messages": len(conversation_log),
        },
    }

    # Spectacular mode: add capability mapping from conversation log
    if spectacular:
        capabilities_used = set()
        for msg in conversation_log:
            agent = msg.get("agent", "")
            if agent == "ExtractAgent":
                capabilities_used.add("fact_extraction")
            elif agent == "InformalAgent":
                capabilities_used.update(
                    ["neural_fallacy_detection", "hierarchical_fallacy_detection"]
                )
            elif agent == "FormalAgent":
                capabilities_used.update(
                    [
                        "nl_to_logic_translation",
                        "fol_reasoning",
                        "modal_logic",
                        "propositional_logic",
                    ]
                )
            elif agent == "QualityAgent":
                capabilities_used.add("argument_quality")
            elif agent == "CounterAgent":
                capabilities_used.add("counter_argument_generation")
            elif agent == "DebateAgent":
                capabilities_used.add("adversarial_debate")
            elif agent == "GovernanceAgent":
                capabilities_used.add("governance_simulation")
        result["capabilities_used"] = list(capabilities_used)
        result["capabilities_missing"] = []

    logger.info(
        f"Conversational analysis complete: {len(conversation_log)} messages, "
        f"{non_empty} state fields, {duration:.1f}s"
    )

    return result


def _should_add_reanalysis_phase(
    enrichment: Dict[str, Any],
    state: Any,
) -> bool:
    """Determine whether a re-analysis phase is warranted (#305).

    Returns True when the enrichment summary reveals gaps that could be
    addressed by re-running informal + quality + governance analysis:
    - Arguments that have no fallacy analysis
    - JTMS retracted beliefs that haven't been re-evaluated

    Args:
        enrichment: Output of state.get_enrichment_summary().
        state: The shared analysis state.

    Returns:
        True if re-analysis would be beneficial.
    """
    total = enrichment.get("total_arguments", 0)
    if total == 0:
        return False

    # Gap 1: arguments with no fallacy analysis
    with_fallacy = enrichment.get("with_fallacy_analysis", 0)
    fallacy_coverage = with_fallacy / total if total > 0 else 1.0

    # Gap 2: JTMS retracted beliefs (indicates formal analysis found issues)
    has_jtms_retractions = False
    jtms_beliefs = getattr(state, "jtms_beliefs", {})
    if isinstance(jtms_beliefs, dict):
        for _bid, bdata in jtms_beliefs.items():
            if isinstance(bdata, dict) and bdata.get("valid") is False:
                has_jtms_retractions = True
                break

    # Also check via JTMS session if available
    if not has_jtms_retractions and hasattr(state, "_jtms_session"):
        session = state._jtms_session
        if hasattr(session, "extended_beliefs"):
            for _name, ext_b in session.extended_beliefs.items():
                if not ext_b.valid:
                    has_jtms_retractions = True
                    break

    # Gap 3: explicit gaps list
    gaps = enrichment.get("gaps", [])

    # Trigger re-analysis if: low fallacy coverage OR JTMS retractions OR many gaps
    if fallacy_coverage < 0.5 and total >= 2:
        return True
    if has_jtms_retractions:
        return True
    if len(gaps) >= 3:
        return True

    return False


def _check_convergence(state, phase_name: str, messages: list) -> bool:
    """Check if the phase has converged and can exit early.

    Convergence signals:
    1. Final conclusion has been set (Synthesis phase)
    2. State hasn't changed in last 2 agent turns (stagnation)
    3. Agent explicitly signals completion in content
    """
    # Signal 1: conclusion set during Synthesis phase only
    # (final_conclusion persists across phases — checking it in Extraction or
    # Formal Analysis would cause premature convergence before downstream agents run)
    if state and state.final_conclusion and "ynthesis" in phase_name:
        logger.info(
            f"  [{phase_name}] CONVERGENCE: final conclusion set, exiting early"
        )
        return True

    # Signal 2: stagnation detection (last 2 messages empty or identical)
    if len(messages) >= 3:
        recent = [m.get("content", "") for m in messages[-2:]]
        if all(c in ("(empty)", "", "ERROR") or len(c) < 10 for c in recent):
            logger.info(
                f"  [{phase_name}] CONVERGENCE: stagnation detected, exiting early"
            )
            return True

    return False


def _get_growth_fingerprint(state: Any) -> tuple[int, ...]:
    """Return a tuple of key state counters for growth detection."""
    if state is None:
        return (0,)
    return (
        len(getattr(state, "identified_arguments", {})),
        len(getattr(state, "identified_fallacies", {})),
        len(getattr(state, "counter_arguments", [])),
        len(getattr(state, "jtms_beliefs", {})),
        len(getattr(state, "dung_frameworks", {})),
        len(getattr(state, "aspic_results", [])),
        len(getattr(state, "belief_revision_results", [])),
        len(getattr(state, "nl_to_logic_translations", [])),
        len(getattr(state, "fol_analysis_results", [])),
        len(getattr(state, "propositional_analysis_results", [])),
        len(getattr(state, "modal_analysis_results", [])),
    )


# Phases where state growth is expected (Extraction, Fallacy, Re-Analysis).
_GROWTH_EXPECTING_PATTERNS = (
    "xtraction",
    "etection",
    "e-Analysis",
    "e-analysis",
    "Reanalysis",
)

# Re-prompt feedback templates.
_RE_PROMPT_FEEDBACK = (
    "Your previous response did not produce any state changes. "
    "You MUST call the provided functions (add_identified_argument, "
    "add_identified_fallacy, etc.) to register your findings. "
    "Do not just describe your analysis in prose — use the tools."
)


def _validate_state_growth(
    fingerprint_before: tuple[int, ...],
    fingerprint_after: tuple[int, ...],
    phase_name: str,
) -> bool:
    """Check whether a phase that expects growth actually produced any.

    Returns True if growth was detected (or phase doesn't require growth).
    Returns False if a growth-expecting phase produced zero delta.
    """
    expects_growth = any(p in phase_name for p in _GROWTH_EXPECTING_PATTERNS)
    if not expects_growth:
        return True

    return fingerprint_after != fingerprint_before


def _select_next_agent(
    state, agents: list, turn: int, agent_by_name: dict = None
) -> "ChatCompletionAgent":
    """Select next agent, honoring PM's designation if available.

    Falls back to round-robin if no designation or designated agent not in phase.
    """
    # Check if PM designated a specific agent
    if (
        state
        and hasattr(state, "_next_agent_designated")
        and state._next_agent_designated
    ):
        designated = state._next_agent_designated
        state._next_agent_designated = None  # Consume the designation

        # Look up by name in agents list
        for agent in agents:
            if agent.name == designated:
                logger.debug(f"  PM designated agent: {designated}")
                return agent

        # Designated agent not in this phase, fall through to round-robin
        logger.debug(
            f"  PM designated '{designated}' but not in phase agents, using round-robin"
        )

    # Round-robin fallback
    return agents[turn % len(agents)]


async def _run_phase(
    agents: List[ChatCompletionAgent],
    initial_prompt: str,
    max_turns: int = 5,
    phase_name: str = "",
    state=None,
    enable_growth_validation: bool = True,
    growth_re_prompt_limit: int = 2,
    reprompt_extractor=None,
) -> List[Dict[str, Any]]:
    """Run a single conversational phase with a set of agents.

    Uses SK AgentGroupChat if available, otherwise falls back to
    round-robin invocation with PM designation support and convergence detection.

    When ``enable_growth_validation`` is True, after each agent turn in a
    growth-expecting phase (Extraction, Detection, Re-Analysis), the hook
    compares a state fingerprint before/after.  If no growth occurred, the
    agent is re-prompted with explicit function-call feedback up to
    ``growth_re_prompt_limit`` times per turn.
    """
    messages: List[Dict[str, Any]] = []
    total_re_prompts = 0
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
            fp_before = _get_growth_fingerprint(state)
            msg_entry = {
                "phase": phase_name,
                "turn": turn,
                "agent": getattr(response, "name", getattr(response, "role", "?")),
                "content": str(getattr(response, "content", response)),
            }
            messages.append(msg_entry)
            logger.info(f"  [{phase_name}] Turn {turn}: {msg_entry['agent']}")

            # Convergence check
            if _check_convergence(state, phase_name, messages):
                break
            if turn >= max_turns:
                break

            # Growth validation hook (AgentGroupChat path)
            if enable_growth_validation:
                fp_after = _get_growth_fingerprint(state)
                if not _validate_state_growth(fp_before, fp_after, phase_name):
                    for rp in range(growth_re_prompt_limit):
                        logger.info(
                            f"  [{phase_name}] Growth re-prompt {rp + 1}/{growth_re_prompt_limit}"
                        )
                        await chat.add_chat_message(
                            _RE_PROMPT_FEEDBACK
                        )
                        async for rp_response in chat.invoke():
                            rp_agent = getattr(
                                rp_response, "name",
                                getattr(rp_response, "role", "?"),
                            )
                            msg_entry = {
                                "phase": phase_name,
                                "turn": turn,
                                "agent": rp_agent,
                                "content": str(
                                    getattr(rp_response, "content", rp_response)
                                ),
                                "re_prompt": rp + 1,
                            }
                            messages.append(msg_entry)
                            total_re_prompts += 1
                        fp_after = _get_growth_fingerprint(state)
                        # Record re-prompt trace (#609)
                        if reprompt_extractor is not None:
                            rp_outcome = "ok" if _validate_state_growth(fp_before, fp_after, phase_name) else ("reran" if rp + 1 < growth_re_prompt_limit else "gave_up")
                            reprompt_extractor.record(
                                phase_name=phase_name,
                                turn=turn,
                                attempt_idx=rp + 1,
                                fingerprint_before=fp_before,
                                fingerprint_after=fp_after,
                                outcome=rp_outcome,
                                agent_name=rp_agent,
                            )
                        if _validate_state_growth(fp_before, fp_after, phase_name):
                            break

        if total_re_prompts > 0:
            messages.append(
                {"phase": phase_name, "type": "growth_validation", "re_prompt_count": total_re_prompts}
            )

        return messages

    except ImportError:
        logger.info("SK AgentGroupChat not importable, using round-robin fallback")
    except Exception as e:
        logger.warning(
            f"SK AgentGroupChat failed ({type(e).__name__}: {e}), using round-robin fallback"
        )

    # Fallback: round-robin invocation with PM designation support
    # In SK 1.40, ChatCompletionAgent.invoke() returns an AsyncGenerator
    for turn in range(1, max_turns + 1):
        agent = _select_next_agent(state, agents, turn)
        try:
            fp_before = _get_growth_fingerprint(state)
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

            messages.append(
                {
                    "phase": phase_name,
                    "turn": turn,
                    "agent": agent.name,
                    "content": content[:500] if content else "(empty)",
                }
            )
            logger.info(f"  [{phase_name}] Turn {turn}: {agent.name}")

            # Convergence check after each turn
            if _check_convergence(state, phase_name, messages):
                break

            # Growth validation hook (round-robin path)
            if enable_growth_validation:
                fp_after = _get_growth_fingerprint(state)
                if not _validate_state_growth(fp_before, fp_after, phase_name):
                    for rp in range(growth_re_prompt_limit):
                        logger.info(
                            f"  [{phase_name}] Growth re-prompt {rp + 1}/{growth_re_prompt_limit}"
                        )
                        chat_history.add_user_message(_RE_PROMPT_FEEDBACK)
                        rp_content = ""
                        async for response in agent.invoke(chat_history):
                            chunk = ""
                            if hasattr(response, "content"):
                                chunk = str(response.content)
                            elif hasattr(response, "value"):
                                chunk = str(response.value)
                            else:
                                chunk = str(response)
                            rp_content += chunk
                        if rp_content:
                            chat_history.add_assistant_message(rp_content)
                        messages.append(
                            {
                                "phase": phase_name,
                                "turn": turn,
                                "agent": agent.name,
                                "content": rp_content[:500] if rp_content else "(empty)",
                                "re_prompt": rp + 1,
                            }
                        )
                        total_re_prompts += 1
                        fp_after = _get_growth_fingerprint(state)
                        # Record re-prompt trace (#609)
                        if reprompt_extractor is not None:
                            rp_outcome = "ok" if _validate_state_growth(fp_before, fp_after, phase_name) else ("reran" if rp + 1 < growth_re_prompt_limit else "gave_up")
                            reprompt_extractor.record(
                                phase_name=phase_name,
                                turn=turn,
                                attempt_idx=rp + 1,
                                fingerprint_before=fp_before,
                                fingerprint_after=fp_after,
                                outcome=rp_outcome,
                                agent_name=agent.name,
                            )
                        if _validate_state_growth(fp_before, fp_after, phase_name):
                            break

        except Exception as exc:
            logger.error(f"  [{phase_name}] Turn {turn}: {agent.name} failed: {exc}")
            messages.append(
                {
                    "phase": phase_name,
                    "turn": turn,
                    "agent": agent.name,
                    "content": f"ERROR: {exc}",
                }
            )

    if total_re_prompts > 0:
        messages.append(
            {"phase": phase_name, "type": "growth_validation", "re_prompt_count": total_re_prompts}
        )

    return messages


async def _run_parent_harness_fallback(
    text: str, state: Any
) -> Optional[Dict[str, Any]]:
    """Invoke tier-3 parent harness on dense texts after Detection phase (#578, #600).

    Always fires on texts > 5000 chars to catch fallacies the single-pass
    InformalAgent may have missed. Falls back silently if unavailable.
    """
    try:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
        )

        context = {"_state_object": state}
        result = await _invoke_hierarchical_fallacy_per_argument(text, context)

        fallacies = result.get("fallacies", [])
        if not fallacies:
            logger.info("Parent harness: no additional fallacies found")
            return None

        # Register any new fallacies into state
        added = 0
        for f in fallacies:
            if not isinstance(f, dict):
                continue
            if hasattr(state, "add_identified_fallacy"):
                try:
                    state.add_identified_fallacy(
                        fallacy_type=f.get("fallacy_type") or f.get("nom", "unknown"),
                        justification=f.get(
                            "justification",
                            f"Detected by parent harness (confidence: {f.get('confidence', 'N/A')})",
                        ),
                        confidence=f.get("confidence", 0.6),
                        source_arg_id=f.get("source_arg_id"),
                    )
                    added += 1
                except Exception:
                    pass

        logger.info(
            "Parent harness: %d fallacies found, %d registered into state",
            len(fallacies),
            added,
        )

        return {
            "phase": "Detection",
            "type": "parent_harness",
            "fallacies_found": len(fallacies),
            "fallacies_registered": added,
            "exploration_method": result.get("exploration_method", "per_argument_parallel"),
        }

    except ImportError:
        logger.debug("Parent harness not available (import error)")
        return None
    except Exception as e:
        logger.warning("Parent harness fallback failed: %s", e)
        return None


async def _resolve_phase_conflicts(
    state: RhetoricalAnalysisState,
    phase_name: str,
    strategy: str = "confidence_based",
) -> List[Dict[str, Any]]:
    """Detect and resolve conflicts between agent contributions after a phase (#214).

    Uses ConflictResolver from jtms_communication_hub to reconcile conflicting beliefs
    from different agents (e.g., InformalAgent says "fallacy" vs QualityAgent says "good").

    Args:
        state: Shared analysis state with all agent contributions
        phase_name: Name of the phase just completed
        strategy: Resolution strategy (confidence_based, evidence_based, consensus, etc.)

    Returns:
        List of resolution results applied to the state.
    """
    from argumentation_analysis.services.jtms.conflict_resolution import (
        ConflictResolver,
    )

    resolver = ConflictResolver()
    resolutions = []

    # Collect potential conflicts from state
    # Conflict patterns:
    # 1. Same argument marked as fallacy AND high quality
    # 2. Contradictory formalizations (A vs not A)
    # 3. Debate disagreements without consensus

    conflicts = []

    # Pattern 1: Fallacy vs High Quality
    try:
        fallacies_dict = (
            state.identified_fallacies if hasattr(state, "identified_fallacies") else {}
        )
        fallacies = (
            list(fallacies_dict.values())
            if isinstance(fallacies_dict, dict)
            else fallacies_dict
        )
        quality_scores = (
            state.argument_quality_scores
            if hasattr(state, "argument_quality_scores")
            else {}
        )

        if fallacies and quality_scores:
            for fallacy in fallacies:
                if not isinstance(fallacy, dict):
                    continue
                target_arg = fallacy.get("target_argument_id", "")
                if target_arg in quality_scores:
                    quality = quality_scores[target_arg]
                    if isinstance(quality, dict):
                        score = quality.get("note_finale", 0)
                        if score > 5.0:  # High quality but marked as fallacy = conflict
                            conflicts.append(
                                {
                                    "conflict_id": f"fallacy_quality_{target_arg}",
                                    "type": "fallacy_vs_quality",
                                    "agents": {
                                        "InformalAgent": {
                                            "belief_name": f"FALLACY:{fallacy.get('type', fallacy.get('fallacy_type', 'unknown'))}",
                                            "confidence": fallacy.get(
                                                "confidence", 0.7
                                            ),
                                            "evidence": fallacy.get("explanation", ""),
                                        },
                                        "QualityAgent": {
                                            "belief_name": f"QUALITY:{target_arg}",
                                            "confidence": score
                                            / 9.0,  # Normalize to 0-1
                                            "evidence": f"Quality score {score}/9",
                                        },
                                    },
                                    "subject": target_arg,
                                }
                            )
    except Exception as e:
        logger.warning(f"Error detecting fallacy/quality conflicts: {e}")

    # Resolve detected conflicts
    for conflict in conflicts:
        try:
            # Use standalone ConflictResolver.resolve() (sync, no agents param)
            resolution = resolver.resolve(conflict, strategy=strategy)

            if resolution.get("resolved"):
                # Apply resolution to state
                # For now, just log - future: update state with resolution
                logger.info(
                    f"[{phase_name}] Conflict resolved: {resolution.get('reasoning', 'No reasoning')}"
                )
                resolutions.append(
                    {
                        "phase": phase_name,
                        "conflict_id": conflict.get("conflict_id"),
                        "resolution": resolution,
                    }
                )
        except Exception as e:
            logger.error(f"Error resolving conflict {conflict.get('conflict_id')}: {e}")

    if resolutions:
        logger.info(
            f"[{phase_name}] Resolved {len(resolutions)} conflicts using strategy '{strategy}'"
        )

    return resolutions


def _retract_fallacious_beliefs(
    state: RhetoricalAnalysisState,
    phase_name: str,
) -> Optional[Dict[str, Any]]:
    """Retract JTMS beliefs associated with detected fallacies (#287).

    After a phase completes, scans the state for detected fallacies and
    automatically retracts the corresponding JTMS beliefs. This is the core
    TMS behavior that justifies the student project: fallacy → retraction → propagation.

    Args:
        state: Shared analysis state with fallacies and JTMS session.
        phase_name: Name of the phase just completed.

    Returns:
        Dict with retraction log if any retractions occurred, None otherwise.
    """
    if not hasattr(state, "_jtms_session"):
        return None

    fallacies_dict = getattr(state, "identified_fallacies", {})
    fallacies = (
        list(fallacies_dict.values())
        if isinstance(fallacies_dict, dict)
        else fallacies_dict
    )
    if not fallacies:
        return None

    session = state._jtms_session
    retractions = []

    for fallacy in fallacies:
        if not isinstance(fallacy, dict):
            continue

        target_arg = fallacy.get("target_argument_id", "")
        fallacy_type = fallacy.get("type", fallacy.get("fallacy_type", "unknown"))

        if not target_arg:
            continue

        # Try exact match then partial match for JTMS belief names
        belief_name = None
        if target_arg in session.extended_beliefs:
            belief_name = target_arg
        else:
            # Try common patterns: arg_N, argument_N, belief about arg_N
            candidates = [
                name
                for name in session.extended_beliefs
                if target_arg.lower() in name.lower()
                or name.lower() in target_arg.lower()
            ]
            if candidates:
                belief_name = candidates[0]

        if belief_name is None:
            continue

        ext_belief = session.extended_beliefs[belief_name]

        # Only retract if currently valid (avoid double retraction)
        if not ext_belief.valid:
            continue

        reason = f"fallacy:{fallacy_type} detected by InformalAgent"

        try:
            # Core TMS retraction: set validity to None and propagate
            session.jtms.set_belief_validity(belief_name, None)

            # Record retraction in extended belief via modification history
            import datetime

            ext_belief.record_modification(
                "retract",
                {
                    "reason": reason,
                    "timestamp": datetime.datetime.now().isoformat(),
                },
            )
            ext_belief.context["retracted"] = True
            ext_belief.context["retraction_reason"] = reason

            # Sync retraction to state.jtms_beliefs dict (#562)
            if hasattr(state, "jtms_beliefs"):
                for bid, bdata in state.jtms_beliefs.items():
                    if bdata.get("name") == belief_name:
                        bdata["valid"] = False
                        bdata["retracted"] = True
                        bdata["retraction_reason"] = reason
                        break

            # Count affected beliefs
            affected = []
            for name, b in session.extended_beliefs.items():
                if name != belief_name and not b.valid:
                    for j in b.justifications:
                        if belief_name in j.get("in_list", []):
                            affected.append(name)

            retraction = {
                "belief": belief_name,
                "fallacy_type": fallacy_type,
                "reason": reason,
                "affected_beliefs": affected,
                "affected_count": len(affected),
            }
            retractions.append(retraction)
            logger.info(
                f"[{phase_name}] JTMS retracted '{belief_name}' "
                f"(fallacy: {fallacy_type}, affected: {len(affected)})"
            )

        except Exception as e:
            logger.warning(
                f"[{phase_name}] Failed to retract belief '{belief_name}': {e}"
            )

    if not retractions:
        return None

    return {
        "phase": phase_name,
        "type": "jtms_retraction",
        "retraction_count": len(retractions),
        "retractions": retractions,
    }


def _build_dung_framework_from_state(state: Any) -> Optional[Dict[str, Any]]:
    """Build a Dung AF from identified_arguments + counter_arguments (#564).

    Constructs attack relations from counter-argument strategies (UNDERCUT,
    REBUT) and computes grounded extension via pure-Python DungFramework.
    Writes the result to state.dung_frameworks if non-trivial.
    """
    if not hasattr(state, "identified_arguments") or not state.identified_arguments:
        return None

    if not hasattr(state, "add_dung_framework"):
        return None

    # Collect argument IDs as Dung nodes
    arg_ids = list(state.identified_arguments.keys())
    if len(arg_ids) < 2:
        return None

    # Build attack relations from counter-arguments
    attacks = []
    counter_args = getattr(state, "counter_arguments", [])
    for ca in counter_args:
        strategy = ca.get("strategy", "").upper()
        if strategy in ("UNDERCUT", "REBUT", "REBUTTAL"):
            original = ca.get("original_argument", "")
            counter_text = ca.get("counter_argument", "")
            if not original:
                continue
            # Match counter-arg to argument IDs
            source_id = None
            target_id = None
            for aid, desc in state.identified_arguments.items():
                if desc and (original[:60] in desc or desc[:60] in original):
                    target_id = aid
                    break
            # Source: find which argument the counter supports
            for aid, desc in state.identified_arguments.items():
                if desc and counter_text and (counter_text[:40] in desc or desc[:40] in counter_text):
                    source_id = aid
                    break
            if source_id and target_id and source_id != target_id:
                attacks.append([source_id, target_id])

    # Also build attacks from fallacies targeting arguments
    fallacies = getattr(state, "identified_fallacies", {})
    if isinstance(fallacies, dict):
        fallacies = list(fallacies.values())
    for fallacy in fallacies:
        if not isinstance(fallacy, dict):
            continue
        target_arg = fallacy.get("target_argument_id", "")
        fallacy_type = fallacy.get("type", fallacy.get("fallacy_type", ""))
        if target_arg and target_arg in state.identified_arguments:
            # Fallacy undermines the target — find an attacker
            # Use fallacy_type as a pseudo-argument attacking the target
            attacker = f"fallacy_{fallacy_type[:20]}"
            if attacker not in arg_ids:
                arg_ids.append(attacker)
            attacks.append([attacker, target_arg])

    if not attacks:
        return None

    # Compute extensions via pure-Python DungFramework
    try:
        from argumentation_analysis.agents.core.logic.dung_native import DungFramework

        fw = DungFramework()
        for aid in arg_ids:
            fw.add_argument(aid)
        for src, tgt in attacks:
            fw.add_attack(src, tgt)

        grounded = fw.grounded_extension()
        extensions = {"grounded": sorted(grounded)} if grounded else {}

        state.add_dung_framework(
            name="conversational_dung",
            arguments=arg_ids,
            attacks=attacks,
            extensions=extensions,
        )

        logger.info(
            f"Dung AF built: {len(arg_ids)} arguments, {len(attacks)} attacks, "
            f"grounded extension size={len(grounded)}"
        )

        return {
            "arguments": len(arg_ids),
            "attacks": len(attacks),
            "grounded_extension": sorted(grounded),
        }
    except Exception as e:
        logger.warning(f"Dung framework construction failed: {e}")
        return None


def _detect_and_run_modal_analysis(state: Any) -> Optional[Dict[str, Any]]:
    """Scan arguments for modal markers and persist modal analysis (#563).

    Detects epistemic (believes, knows), deontic (must, should, ought),
    and alethic (possible, necessary) markers in argument text. For each
    argument containing modal language, creates a modal_analysis_result
    entry in state.
    """
    if not hasattr(state, "identified_arguments") or not state.identified_arguments:
        return None
    if not hasattr(state, "add_modal_analysis_result"):
        return None
    if not hasattr(state, "modal_analysis_results"):
        return None

    # Already populated — skip
    if state.modal_analysis_results:
        return None

    import re

    MODAL_PATTERNS = {
        "epistemic": [
            r"\b(believes?|knows?|is aware|certain|convinced|doubts?)\b",
            r"\b(il croit|elle sait|il est certain|convaincu|doute)\b",
        ],
        "deontic": [
            r"\b(must|should|ought|obliged|required|has to|shall|may not)\b",
            r"\b(doit|devrait|il faut|obligé?e?|nécessaire|interdit)\b",
        ],
        "alethic": [
            r"\b(possible|possibly|necessary|necessarily|can|could|impossible)\b",
            r"\b(possible|nécessaire|impossible|peut|pourrait)\b",
        ],
    }

    results_count = 0
    for arg_id, desc in state.identified_arguments.items():
        if not desc or not isinstance(desc, str):
            continue

        detected_modalities = []
        for modality, patterns in MODAL_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, desc, re.IGNORECASE):
                    detected_modalities.append(modality)
                    break

        if not detected_modalities:
            continue

        # Build modal formula representation
        formulas = []
        for mod in detected_modalities:
            if mod == "epistemic":
                formulas.append(f"K(agent, prop({arg_id}))")
            elif mod == "deontic":
                formulas.append(f"O(prop({arg_id}))")
            elif mod == "alethic":
                formulas.append(f"<>({arg_id})")

        try:
            state.add_modal_analysis_result(
                formulas=formulas,
                valid=True,
                modalities=detected_modalities,
            )
            results_count += 1
        except Exception as e:
            logger.warning(f"Modal analysis failed for {arg_id}: {e}")

    if results_count == 0:
        return None

    logger.info(f"Modal analysis: {results_count} arguments with modal markers")
    return {
        "modal_results": results_count,
        "modalities_found": list(
            {
                m
                for r in state.modal_analysis_results
                for m in r.get("modalities", [])
            }
        ),
    }


def _build_aspic_from_state(state: Any) -> Optional[Dict[str, Any]]:
    """Build ASPIC+ framework from state arguments + fallacies (#565).

    Classifies arguments as strict (factual/certain) or defeasible (hedged/contingent),
    applies fallacy-based undermining, and persists to state.aspic_results via
    pure-Python fallback (no JVM required).
    """
    if not hasattr(state, "identified_arguments") or not state.identified_arguments:
        return None
    if not hasattr(state, "add_aspic_result"):
        return None

    args = list(state.identified_arguments.values())
    if len(args) < 1:
        return None

    import re

    STRICT_CUES = [
        r"\b(is|are|was|were|has|have|had|always|every|all|never|fact|proven)\b",
        r"\b(est|sont|était|ont|toujours|jamais|tous|fait|prouvé)\b",
    ]
    DEFEASIBLE_CUES = [
        r"\b(usually|often|might|could|may|seems|appears|likely|probably|generally)\b",
        r"\b(généralement|souvent|peut|pourrait|semble|probablement|habituellement)\b",
    ]

    fallacies = list(getattr(state, "identified_fallacies", {}).values())

    # Classify arguments into strict vs defeasible rules
    strict_rules = []
    defeasible_rules = []
    for i, desc in enumerate(args):
        if not desc or not isinstance(desc, str):
            continue
        has_strict = any(re.search(p, desc, re.IGNORECASE) for p in STRICT_CUES)
        has_defeasible = any(re.search(p, desc, re.IGNORECASE) for p in DEFEASIBLE_CUES)

        # Fallacy-targeted arguments are defeasible regardless
        is_undermined = False
        for f in fallacies:
            if not isinstance(f, dict):
                continue
            target = f.get("target_argument_id", "")
            target_text = f.get("target_argument", "")
            arg_ids = list(state.identified_arguments.keys())
            if target and target == (arg_ids[i] if i < len(arg_ids) else ""):
                is_undermined = True
                break
            if target_text and target_text.lower()[:30] in desc.lower():
                is_undermined = True
                break

        label = f"arg_{i+1}"
        if is_undermined or has_defeasible:
            defeasible_rules.append(f"{label}({desc[:50]}) => conclusion_{i+1}")
        elif has_strict:
            strict_rules.append(f"{label}({desc[:50]}) -> conclusion_{i+1}")
        else:
            # Default: defeasible for safety
            defeasible_rules.append(f"{label}({desc[:50]}) => conclusion_{i+1}")

    # Compute surviving vs defeated arguments
    surviving = []
    defeated = []
    for i, desc in enumerate(args):
        if not desc:
            continue
        is_undermined = False
        for f in fallacies:
            if not isinstance(f, dict):
                continue
            arg_ids = list(state.identified_arguments.keys())
            target = f.get("target_argument_id", "")
            target_text = f.get("target_argument", "")
            if (target and target == (arg_ids[i] if i < len(arg_ids) else "")) or \
               (target_text and target_text.lower()[:30] in desc.lower()):
                is_undermined = True
                break
        if is_undermined:
            defeated.append(desc[:80])
        else:
            surviving.append(desc[:80])

    if not strict_rules and not defeasible_rules:
        return None

    extensions = [surviving] if surviving else [[args[0][:80]] if args else []]
    statistics = {
        "total_arguments": len(args),
        "surviving": len(surviving),
        "defeated": len(defeated),
        "strict_rules": len(strict_rules),
        "defeasible_rules": len(defeasible_rules),
        "fallacies_applied": len(fallacies),
    }

    try:
        state.add_aspic_result(
            reasoner_type="python_fallback",
            extensions=extensions,
            statistics=statistics,
        )
    except Exception as e:
        logger.warning(f"ASPIC result persistence failed: {e}")
        return None

    logger.info(
        f"ASPIC framework built: {len(strict_rules)} strict, "
        f"{len(defeasible_rules)} defeasible, "
        f"{len(surviving)} surviving, {len(defeated)} defeated"
    )

    return {
        "strict_rules": len(strict_rules),
        "defeasible_rules": len(defeasible_rules),
        "surviving": len(surviving),
        "defeated": len(defeated),
    }


def _run_belief_revision_from_state(state: Any) -> Optional[Dict[str, Any]]:
    """Run AGM belief revision when fallacy-triggered contradictions exist (#566).

    When fallacies target arguments that have JTMS beliefs, the beliefs are
    contradicted. This function records the revision: original beliefs →
    revised (contradicted beliefs removed).
    """
    if not hasattr(state, "belief_revision_results"):
        return None
    if not hasattr(state, "add_belief_revision_result"):
        return None
    if not hasattr(state, "identified_fallacies"):
        return None

    # Already populated — skip
    if state.belief_revision_results:
        return None

    fallacies = list(state.identified_fallacies.values())
    if not fallacies:
        return None

    # Collect beliefs that should be revised (targeted by fallacies)
    jtms_beliefs = getattr(state, "jtms_beliefs", {})
    original_beliefs = [bdata.get("name", "") for bdata in jtms_beliefs.values()
                        if bdata.get("valid", False)]
    if not original_beliefs:
        return None

    revised = list(original_beliefs)
    removed = []

    for f in fallacies:
        if not isinstance(f, dict):
            continue
        target_arg = f.get("target_argument_id", "")
        fallacy_type = f.get("type", f.get("fallacy_type", "unknown"))
        if not target_arg:
            continue

        # Find belief matching the targeted argument
        for bname in original_beliefs:
            if bname == target_arg or target_arg in bname:
                if bname in revised:
                    revised.remove(bname)
                    removed.append(f"{bname} (undermined by {fallacy_type})")
                    break

    if not removed:
        return None

    try:
        state.add_belief_revision_result(
            method="fallacy_contraction",
            original=original_beliefs,
            revised=revised,
        )
    except Exception as e:
        logger.warning(f"Belief revision persistence failed: {e}")
        return None

    logger.info(
        f"Belief revision: {len(removed)} beliefs contracted "
        f"({len(original_beliefs)} → {len(revised)})"
    )

    return {
        "method": "fallacy_contraction",
        "original_count": len(original_beliefs),
        "revised_count": len(revised),
        "removed": removed,
    }
