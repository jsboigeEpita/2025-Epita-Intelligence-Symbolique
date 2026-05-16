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
            "CROSS-KB ENRICHMENT (#208-I) — tu dois diriger les synergies entre agents :\n"
            "- Apres ExtractAgent : demande-lui de creer des croyances JTMS pour chaque argument "
            "(jtms_create_belief) et des justifications entre premisses et conclusions\n"
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
            "Tu es l'agent d'extraction d'arguments. Quand le PM te donne la parole :\n"
            "1. Analyse le texte pour identifier les arguments, premisses et conclusions\n"
            "2. Pour chaque argument, appelle add_identified_argument(description)\n"
            "3. Identifie les relations entre arguments (support, attaque)\n\n"
            "JTMS : Pour chaque argument extrait, cree aussi une croyance JTMS :\n"
            "- jtms_create_belief(belief_name='arg_N', agent_source='ExtractAgent', confidence=0.7)\n"
            "- Si un argument A soutient B, ajoute : "
            "jtms_add_justification(in_list=['arg_A'], out_list=[], conclusion='arg_B', agent_source='ExtractAgent')\n"
            "Cela permet au systeme de maintenir un reseau de dependances entre arguments.\n"
            "Sois precis et exhaustif dans tes extractions."
        ),
    },
    "InformalAgent": {
        "speciality": "informal_fallacy",
        "instructions": (
            "Tu es l'agent de detection de sophismes. Tu disposes de 2 outils de detection :\n"
            "- run_guided_analysis() : OBLIGATOIRE en premier. Detection approfondie via navigation "
            "hierarchique dans la taxonomie (explore les familles de sophismes branche par branche). "
            "Cet outil est PLUS PRECIS et produit des classifications au niveau feuille de la taxonomie.\n"
            "- detect_fallacies() : detection rapide par heuristiques (utilise UNIQUEMENT si "
            "run_guided_analysis echoue ou n'est pas disponible)\n\n"
            "Quand le PM te donne la parole :\n"
            "1. Lis les arguments identifies via get_current_state_snapshot()\n"
            "2. Pour CHAQUE argument, lance run_guided_analysis(argument_text=texte_argument) "
            "pour une detection taxonomique complete.\n"
            "3. Pour chaque sophisme trouve, appelle add_identified_fallacy(type, justification, target_arg_id)\n"
            "4. Sois exhaustif : traite TOUS les arguments, pas seulement les plus evidents.\n\n"
            "JTMS : Quand tu detectes un sophisme sur un argument :\n"
            "- jtms_create_belief(belief_name='fallacy_on_arg_N', agent_source='InformalAgent', confidence=0.8)\n"
            "- jtms_add_justification(in_list=['fallacy_on_arg_N'], out_list=['arg_N'], "
            "conclusion='arg_N_weakened', agent_source='InformalAgent')\n"
            "- jtms_retract_belief(belief_name='arg_N', reason='fallacy: type_du_sophisme') "
            "pour retracter la croyance et propager la defaite\n\n"
            "Sois rigoureux : cite le texte exact et explique pourquoi c'est un sophisme.\n\n"
            "CROSS-KB (#208-I) : Si FormalAgent a deja identifie des inconsistances logiques, "
            "verifie si elles correspondent a des sophismes formels (non sequitur, affirmation du consequent)."
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
                "opaque_id": source_id or "unknown",
                "era": "",
                "language": "",
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
    # Signal 1: conclusion set during Synthesis
    if state and state.final_conclusion:
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
) -> List[Dict[str, Any]]:
    """Run a single conversational phase with a set of agents.

    Uses SK AgentGroupChat if available, otherwise falls back to
    round-robin invocation with PM designation support and convergence detection.
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

            # Convergence check
            if _check_convergence(state, phase_name, messages):
                break
            if turn >= max_turns:
                break

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

    return messages


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
