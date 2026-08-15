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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent

from argumentation_analysis.orchestration.invoke_callables import (
    LLMBudgetExceeded,
    _bump_sk_budget,
)
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.contents.chat_history import ChatHistory

from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
    record_unresolved_designation,
)
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.orchestration.trace_analyzer import (
    ConversationalTraceAnalyzer,
)

logger = logging.getLogger("ConversationalOrchestrator")


@dataclass
class WallClockBudget:
    """Wall-clock deadline for a conversational run (C1 #1500).

    The turn-count cap (CONV-C #1334 ``max_total_turns``) bounds the NUMBER
    of agent turns, but on a real LLM each turn is a slow round-trip — so a
    turn-bounded run can still exceed 600s wall-clock (the R653 firsthand
    finding that motivated this Epic). This budget bounds WALL-CLOCK time.

    When exhausted, the run exits CLEANLY between turns: the partial state
    accumulated so far IS the verdict. This is the anti-#1019 point — a real
    bounded verdict at the bound, not a ``return None`` nor a coroutine
    killed mid-flight by an external ``asyncio.wait_for`` (which would lose
    the partial state and report ``decides=False``).
    """

    max_seconds: Optional[float]
    start: float

    @property
    def active(self) -> bool:
        """True iff a wall-clock bound was requested."""
        return self.max_seconds is not None

    @property
    def deadline(self) -> Optional[float]:
        """Absolute wall-clock deadline, or None when inactive."""
        return (self.start + self.max_seconds) if self.active else None

    def is_exhausted(self, now: float) -> bool:
        """True iff the bound is active and ``now`` has reached the deadline."""
        deadline = self.deadline
        return deadline is not None and now >= deadline


def _detect_language(text: str) -> str:
    """Detect text language using heuristic word-frequency analysis.

    Distinguishes DE, FR, EN based on common function words and articles.
    Returns ISO 639-1 code: 'de', 'fr', 'en', or 'unknown'.
    """
    sample = text[:3000].lower()
    scores: Dict[str, int] = {"de": 0, "fr": 0, "en": 0}

    de_markers = [
        r"\bder\b",
        r"\bdie\b",
        r"\bdas\b",
        r"\bund\b",
        r"\bist\b",
        r"\bein\b",
        r"\beine\b",
        r"\bden\b",
        r"\bmit\b",
        r"\bfür\b",
        r"\bauf\b",
        r"\bdes\b",
        r"\bsich\b",
        r"\bnicht\b",
        r"\bvon\b",
        r"\bsind\b",
        r"\bwird\b",
        r"\bdurch\b",
        r"\bwir\b",
        r"\bals\b",
        r"\bauch\b",
        r"\bnoch\b",
        r"\bnach\b",
        r"\büber\b",
    ]
    fr_markers = [
        r"\ble\b",
        r"\bla\b",
        r"\bles\b",
        r"\bde\b",
        r"\bdes\b",
        r"\bet\b",
        r"\best\b",
        r"\bque\b",
        r"\bqui\b",
        r"\bdu\b",
        r"\bun\b",
        r"\bune\b",
        r"\bpour\b",
        r"\bdans\b",
        r"\bsur\b",
        r"\bce\b",
        r"\bil\b",
        r"\bne\b",
        r"\bse\b",
        r"\bsont\b",
    ]
    en_markers = [
        r"\bthe\b",
        r"\band\b",
        r"\bis\b",
        r"\bto\b",
        r"\bof\b",
        r"\bin\b",
        r"\bthat\b",
        r"\bfor\b",
        r"\bit\b",
        r"\bwith\b",
        r"\bas\b",
        r"\bwas\b",
        r"\bon\b",
        r"\bare\b",
        r"\bhave\b",
        r"\bthis\b",
        r"\bwe\b",
        r"\bour\b",
        r"\bthey\b",
        r"\bnot\b",
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

# NOTE (RA-6 #1051): The inline "ProjectManager" ChatCompletionAgent defined below
# is the CANONICAL PM for the conversational path. It uses StateManagerPlugin's
# designate_next_agent() kernel function, which writes to state._next_agent_designated.
# DelegatingSelectionStrategy (wired in _run_phase) reads that field to honour PM
# designation. The separate ProjectManagerAgent in agents/core/pm/pm_agent.py serves
# a different entry point (enhanced_pm_analysis_runner.py) and is NOT used here.
AGENT_CONFIG = {
    "ProjectManager": {
        "speciality": "project_manager",
        "instructions": (
            "Tu es le chef de projet. Tu conduis l'analyse pour produire un ETAT RICHE "
            "(couverture de toutes les dimensions pertinentes du texte), pas pour suivre un script. "
            "Aucune sequence n'est imposee : c'est a toi de juger, a chaque tour, qui doit parler.\n\n"
            "A CHAQUE TOUR :\n"
            "1. Lis l'etat courant via get_current_state_snapshot().\n"
            "2. Decide, en fonction de ce qui manque ou de ce qu'un resultat intermediaire "
            "t'apprend, quel specialiste doit parler ensuite — ET POURQUOI.\n"
            "3. Enregistre ta decision via record_designation(agent, motivation, trigger). "
            "La motivation est OBLIGATOIRE : 1-2 phrases sur ce qui te fait convoquer cet agent "
            "MAINTENANT (ex. 'InformalAgent a trouve une contradiction sur arg_3, je convoque "
            "FormalAgent pour la formaliser'). trigger parmi : initial, deepening, synergy, convergence.\n"
            "4. Designe l'agent via designate_next_agent(nom_exact) et pose-lui une question precise.\n\n"
            "CARTE DES CAPACITES — ces synergies existent, c'est a toi d'en juger l'opportunite "
            "(personne ne te l'impose) :\n"
            "- ExtractAgent — extrait les arguments (add_identified_argument). [Fait : les "
            "specialistes travaillent sur l'etat partage ; tant que l'extraction n'a rien "
            "enregistre, l'etat est vide et rien d'autre n'a de substrate.]\n"
            "- InformalAgent — sophismes (run_guided_analysis, add_identified_fallacy).\n"
            "- FormalAgent — coherence logique (inconsistances signalees).\n"
            "- QualityAgent — peut evaluer EN CONTEXTE les sophismes detectes "
            "(evaluate_with_cross_kb_context).\n"
            "- CounterAgent — peut cibler les arguments faibles.\n"
            "- DebateAgent — positions adversariales ; GovernanceAgent — consensus, conflits, "
            "vote (detect_conflicts, social_choice_vote).\n"
            "- JTMS — croyances et retractations (jtms_create_belief, jtms_check_consistency) ; "
            "une retractation peut invalider un fil.\n\n"
            "BUDGET : tu as au plus {budget_turns} tours (pipeline-global) pour couvrir "
            "l'analyse. La couverture prime sur l'epuisement du budget, mais le budget est DUR — "
            "si tu l'atteins sans converger, le depassement est tracé (pas silencieux).\n\n"
            "CONVERGENCE : quand l'etat est suffisamment couvert (dimensions pertinentes remplies, "
            "consensus evalue si des positions divergent), appelle set_final_conclusion() avec ta synthese."
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
            "WORKFLOW OBLIGATOIRE (5 etapes) :\n\n"
            "#1333 (a) PRIORITE ABSOLUE - VERDICTS DE COHERENCE : ta mission premiere "
            "est de PRODUIRE DES VERDICTS via les solveurs Tweety "
            "(check_pl_consistency / check_fol_consistency / check_modal_consistency), "
            "PAS d'accumuler des traductions. DES QUE des formules existent dans l'etat "
            "(tes add_nl_to_logic_translation / add_belief_set), appelle le check_*_consistency "
            "adequat DESSUS AVANT de generer d'autres formules. Ne laisse JAMAIS une formule "
            "non-verifiee -- la verification est le coeur de ton role, pas une etape finale optionnelle.\n\n"
            "ETAPE 0 — Build Shared Atom/Signature Inventory (#560/#561, modal #1396) :\n"
            "1. Lis l'etat via get_current_state_snapshot() pour obtenir le texte source\n"
            "2. Appelle extract_shared_pl_atoms(full_text=source_text) pour extraire les atomes PL partages\n"
            "3. Appelle extract_shared_fol_signature(full_text=source_text) pour extraire la signature FOL partagee\n"
            "4. MODAL CUE-GATE (#1396) : si le texte source contient des CUES modaux "
            "('doit', 'faut', 'peut', 'necessairement', 'possible', 'obligatoire', "
            "'interdit', 'permis'), appelle extract_shared_modal_signature(full_text=source_text) "
            "pour extraire l'inventaire d'atomes modaux partages. Si le texte n'a AUCUN "
            "cue modal, SAUTE cet appel (l'outil retournerait un vide honnete, #1019 -- "
            "ne fabrique pas d'atomes modaux sur un texte non-modal).\n"
            "5. Si atomic_propositions, fol_shared_signature ou l'inventaire modal existent DEJA dans l'etat, saute les appels correspondants\n"
            "6. Stock les resultats via add_belief_set ou dans l'etat pour coherence inter-arguments\n\n"
            "ETAPE 1 — NL → Traduction Formelle (2-pass coordinated, 3 logiques co-egales #1396) :\n"
            "RAISONNEMENT : 3 logiques co-egales, le choix se fait selon les CUES "
            "du texte, sans priorite fixe entre elles (#1396 : retire le biais "
            "historique FOL-only qui affamait le modal, R544/R545) :\n"
            "- FOL capture les relations et predicats entre entites (qui a fait quoi, "
            "qui croit quoi) qu'un atome booleen ne peut pas exprimer -- un argument "
            "reliant un acteur a une action est une relation. Cues : acteur, action, relation, causalite.\n"
            "- PL capture les propositions pures booleennes (P et Q, P implique Q) "
            "quand l'argument est purement propositionnel, sans acteur ni relation.\n"
            "- MODAL capture la necessite/possibilite/obligation. Cues : 'doit', "
            "'faut', 'peut', 'necessairement', 'possible', 'obligatoire', 'interdit', "
            "'permis'. Un argument normatif (devoir, permission, interdiction) est "
            "MODAL, pas un universel FOL -- un 'doit' n'est pas un 'forall'.\n"
            "Pour chaque argument cle, choisis SA logique d'apres ses cues (plusieurs logiques possibles si l'argument melange les cues).\n"
            "1. Lis les arguments identifies dans l'etat via get_current_state_snapshot()\n"
            "2. Si une signature FOL partagee existe (ETAPE 0), pour chaque argument cle :\n"
            "   - Appelle generate_fol_formulas_with_shared_signature("
            "argument_text='...', shared_signature=signature_json)\n"
            "3. Si des atomes PL partages existent, pour chaque argument cle :\n"
            "   - Appelle generate_pl_formulas_with_shared_atoms("
            "argument_text='...', shared_atoms=atoms_json)\n"
            "4. Si aucun inventaire partage n'existe (fallback) : utilise translate_to_fol "
            "puis translate_to_pl comme avant\n"
            "5. MODAL (#1391/#1396) : pour chaque argument cle qui exprime une modalite "
            "(cues : 'doit', 'faut', 'peut', 'necessairement', 'possible', 'obligatoire', "
            "'interdit', 'permis'), appelle translate_to_modal(text='...', "
            "shared_atoms=<atoms_de_extract_shared_modal_signature>) -> belief set modal "
            "(declarations 'type(<atom>)' + formules [] / <>, #1327). Passe shared_atoms "
            "de l'inventaire ETAPE 0 (#1396) pour la coherence inter-arguments ; si aucun "
            "inventaire modal n'existe, appelle translate_to_modal(text='...'). Stock le "
            "resultat via add_nl_to_logic_translation(logic_type='modal'). Si l'argument "
            "n'a aucune saveur modale, l'outil retourne un resultat valide vide "
            "(honnete absent, #1019) -- NE fabrique PAS de contenu modal.\n"
            "6. Stock la traduction via add_nl_to_logic_translation(\n"
            "   original_text='...', formula='...', logic_type='propositional'|'fol'|'modal',\n"
            "   is_valid=True/False, variables=JSON. confidence=0.0-1.0)\n\n"
            "ETAPE 2 — Validation Tweety (OBLIGATOIRE et IMMEDIATE apres ETAPE 1, pas finale) :\n"
            "#1333 (a) Pour CHAQUE formule generee en ETAPE 1 (sans exception, pas seulement les valides) :\n"
            '1. PL: appelle check_pl_consistency(belief_set="p => q\\np")  (formules separees par \\n)\n'
            '2. FOL: appelle check_fol_consistency(belief_set="forall X: (P(X))")\n'
            "3. Modal (possibilite/obligation): appelle check_modal_consistency(\n"
            '   payload=\'{"belief_set": "<belief_set_modal_de_translate_to_modal>", '
            '"logic_type": "K"}\')  (K/T/S4/S5). #1391: passe le belief set modal '
            "PRODUIT par translate_to_modal (ETAPE 1 step 5), ne le freehand pas.\n"
            "4. Si inconstistances: signalez au PM. NE PAS passer a ETAPE 3 tant que chaque formule n'a pas de verdict.\n\n"
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
            "Modal: Si tu detectes des modalites (possibilite/necessite), utilise check_modal_consistency()."
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

# ---------------------------------------------------------------------------
# #1760 — steering room policies. The PM's capability map names 8 specialists,
# but phase_configs freezes rooms of 3-4: the PM designates real, wired agents
# that are simply not in the room it sits in (#1751 made that observable;
# this is the fix side). The three "voies" of the issue are switchable here so
# the choice is settled by comparative measurement, not on paper.
# ---------------------------------------------------------------------------
ROOM_POLICY_PHASE_CASTING = "phase_casting"  # status quo — baseline to beat
ROOM_POLICY_TRUTH = "truth"  # voie 1: PM prompt names the actual phase roster
ROOM_POLICY_REPROMPT = "reprompt"  # voie 2: hand the floor back on absorption
ROOM_POLICY_ALL_AGENTS = "all_agents"  # voie 3: the room IS the full roster

_ROOM_POLICIES = (
    ROOM_POLICY_PHASE_CASTING,
    ROOM_POLICY_TRUTH,
    ROOM_POLICY_REPROMPT,
    ROOM_POLICY_ALL_AGENTS,
)

# #1760 voie 2: per-phase cap on absorption re-prompts. A PM that re-designates
# the same absent agent must not turn the cap into a private debate loop.
_ABSORPTION_REPROMPT_LIMIT = 2


def _pm_room_section(present_agents: List[str]) -> str:
    """Voie 1 (#1760): the room line appended to the PM instructions each phase.

    Pure function so the DoD test can assert on the constructed prompt: it must
    name EXACTLY the phase roster — every present agent, and no absent one.
    """
    names = ", ".join(present_agents)
    return (
        "\n\nSALLE ACTUELLE — agents presents dans cette phase : " + names + ".\n"
        "Designate uniquement parmi eux : les autres specialistes de ta carte ne "
        "sont PAS dans la piece pour cette phase, une designation hors salle ne "
        "peut pas aboutir."
    )


def _pm_instructions_with_room(budget_turns: int, present_agents: List[str]) -> str:
    """Voie 1 (#1760): PM instructions + the room truth for the current phase.

    Rebuilt from the AGENT_CONFIG template each phase (single source of truth)
    so the room section never accumulates across phases. The capability map of
    8 stays (anti-pendule: amputating it to kill impossible designations would
    restore the very steering loss the mandate condemns).
    """
    base = AGENT_CONFIG["ProjectManager"]["instructions"].format(
        budget_turns=budget_turns
    )
    return base + _pm_room_section(present_agents)


def _apply_room_truth_to_pm(
    pm_agent: Optional[Any], present_agents: List[str], budget_turns: int
) -> None:
    """Voie 1 (#1760): tell the PM, at phase entry, who is actually in the room.

    Mutates ``instructions`` (SK agents are Pydantic with
    ``validate_assignment=True`` and not frozen, so assignment is allowed and
    read at each invoke). No-op when the PM is not in the created roster.
    """
    if pm_agent is None:
        return
    pm_agent.instructions = _pm_instructions_with_room(budget_turns, present_agents)


def _resolve_room_agents(
    room_policy: str, phase_agents: List[Any], all_agents: List[Any]
) -> List[Any]:
    """Voie 3 (#1760): under ``all_agents`` the room is the full roster.

    The phase casting still exists (initial prompts still steer the phase
    focus) — what changes is who can be designated and take the floor.
    """
    if room_policy == ROOM_POLICY_ALL_AGENTS:
        return list(all_agents)
    return phase_agents


def _absorption_feedback(requested_agent: str, present_agents: List[str]) -> str:
    """Voie 2 (#1760): the message handed back to the PM on absorption."""
    return (
        f"Ta designation de '{requested_agent}' n'a pas abouti : cet agent n'est "
        f"pas dans la salle de cette phase. Agents presents : "
        f"{', '.join(present_agents)}. Re-designe parmi les presents via "
        f"designate_next_agent(nom_exact) et pose-lui ta question, ou poursuis "
        f"avec un agent present."
    )


def _unresolved_designation_markers(state: Any) -> List[Dict[str, Any]]:
    """#1751 markers currently in the state's deliberation trace."""
    return [
        r
        for r in getattr(state, "deliberation_trace", [])
        if isinstance(r, dict) and r.get("record_type") == "designation_unresolved"
    ]


def _fresh_absorbed_designation(
    state: Any, unresolved_before: int
) -> Optional[Dict[str, Any]]:
    """The absorption marker recorded since ``unresolved_before`` was counted.

    Returns the newest marker when the count grew this turn, else ``None``.
    Used by voie 2 to re-prompt the PM exactly when its designation was
    absorbed — a stale marker from an earlier turn must not re-fire.
    """
    markers = _unresolved_designation_markers(state)
    if len(markers) <= unresolved_before:
        return None
    return markers[-1]


def create_conversational_agents(
    kernel: sk.Kernel,
    state: RhetoricalAnalysisState,
    llm_service_id: str,
    agent_names: Optional[List[str]] = None,
    agent_state_class: Optional[Dict[str, type]] = None,
    pm_budget_turns: Optional[int] = None,
) -> List[ChatCompletionAgent]:
    """Create agents with specialized plugins for conversational mode.

    Each agent gets:
    - StateManagerPlugin (or phase-scoped variant if tool gating is enabled)
    - Its own specialized plugins (loaded via factory.get_plugin_instances())
    - FunctionChoiceBehavior.Auto() for auto tool invocation

    Plugin loading is delegated to the central factory registry
    (AGENT_SPECIALITY_MAP + _PLUGIN_REGISTRY) to avoid duplication.

    Args:
        kernel: SK Kernel instance.
        state: Shared analysis state.
        llm_service_id: LLM service ID in the kernel.
        agent_names: Optional subset of agent names to create.
        agent_state_class: Optional mapping of agent_name → phase-scoped state
            plugin class (#605). When provided, the mapped agent gets the
            scoped class instead of the full StateManagerPlugin.
        pm_budget_turns: CONV-C #1334 — pipeline-global tour budget surfaced to
            the PM as the ``{budget_turns}`` placeholder in its instructions
            (design doc §6). None falls back to a conservative default.
    """
    from argumentation_analysis.agents.factory import get_plugin_instances

    llm_service = kernel.get_service(llm_service_id)
    if agent_state_class is None:
        agent_state_class = {}

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
        state_cls = agent_state_class.get(name)
        plugins = get_plugin_instances(
            speciality,
            state=state,
            kernel=kernel,
            llm_service=llm_service,
            state_plugin_class=state_cls,
        )

        # CONV-C #1334: the PM instructions carry a {budget_turns} placeholder
        # (design doc §5/§6) surfacing the pipeline-global cap to the conductor.
        # Format it once at build time; non-PM agents have no placeholder.
        instructions = config["instructions"]
        if name == "ProjectManager":
            budget = pm_budget_turns if pm_budget_turns else 30
            instructions = instructions.format(budget_turns=budget)

        agent = ChatCompletionAgent(
            kernel=kernel,
            service=llm_service,
            name=name,
            instructions=instructions,
            plugins=plugins,
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                auto_invoke_kernel_functions=True,
                # CONV-B #1333 DoD #1 (po-2025, dispatch R545): the FormalAgent's
                # prescribed 4-stage cascade is ETAPE 0 (3 tool-calls: snapshot +
                # extract_shared_pl_atoms + extract_shared_fol_signature) -> ETAPE 1
                # (>=2: generate_fol_formulas + generate_pl_formulas + store) ->
                # ETAPE 2 (up to 4 deciders: PL/FOL/modal/Dung). A cap of 5 starves
                # the descent: the budget is exhausted at ETAPE 0+1 before the
                # deciding kernel_functions (#1371/#1374) are ever reached mid-turn,
                # so the FormalAgent answers from parametric knowledge instead of
                # invoking a solver (the CONV-A #1332 "tagheur"). 12 covers the
                # full cascade (3+3+4=10) with a small margin; a hard bound (not
                # unlimited) still guards against a runaway tool-call loop.
                maximum_auto_invoke_attempts=12,
            ),
        )
        agents.append(agent)
        plugin_names = [type(p).__name__ for p in plugins]
        state_type = state_cls.__name__ if state_cls else "StateManagerPlugin"
        logger.info(
            f"Created agent '{name}' (speciality={speciality}, state={state_type}) "
            f"with plugins: {plugin_names}"
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
    enable_tool_gating: bool = False,
    enable_reprompt_tracing: bool = False,
    source_metadata: Optional[Dict[str, str]] = None,
    selector_context: Optional[Dict[str, Any]] = None,
    max_total_turns: Optional[int] = None,
    max_wall_seconds: Optional[float] = None,
    render_restitution: bool = False,
    room_policy: str = ROOM_POLICY_PHASE_CASTING,
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
        enable_tool_gating: If True, use phase-scoped state plugins so agents
            only see StateManagerPlugin functions relevant to their phase (#605).
        enable_reprompt_tracing: If True, capture structured RepromptTrace
            records from growth validation re-prompt events (#609).
        max_total_turns: CONV-C #1334 — pipeline-global tour budget (design doc
            §6). When set, the sum of turns across phases is capped and surfaced
            to the PM as its ``{budget_turns}``. The cap is a fixed contract
            (not adjusted at runtime); hitting it appends a ``CapBreachRecord``
            and ends the run with status ``BUDGET_EXHAUSTED`` (#708 fail-loud).
            None defaults to the sum of the three macro-phase caps.
        max_wall_seconds: C1 #1500 — wall-clock budget in seconds. When set,
            the run checks elapsed time before each phase and before each agent
            turn; on exhaustion it records a ``CapBreachRecord(cap_kind=
            "wall_clock")`` and exits CLEANLY, returning the partial state as a
            REAL verdict (status ``WALL_CLOCK_BOUNDED``) — anti-#1019: a vrai
            verdict at the bound, not a killed coroutine / ``return None``.
            None (default) leaves the run wall-clock-unbounded (turn-cap only),
            preserving the prior behaviour for callers that do not opt in.
        render_restitution: CONV-D #1335 — if True, generate the 3-act
            restitution report from the completed state and attach it under
            ``result["restitution_report"]``. The conversational path does not
            run the act-generation phases, so the acts are produced from the
            completed ``UnifiedAnalysisState`` (same renderer/acts as the
            pipeline path). Fail-loud-non-fatal: reporting never fails the run.
        room_policy: #1760 — how the room the PM steers in relates to its
            8-agent capability map. ``"phase_casting"`` (default) is the
            status quo: the AgentGroupChat is built with the phase's hard-coded
            casting alone and an off-room designation is absorbed (#1751
            marker). ``"truth"`` appends the actual phase roster to the PM
            instructions at each phase entry. ``"reprompt"`` hands the floor
            back to the PM with the present roster when a designation is
            absorbed (capped at ``_ABSORPTION_REPROMPT_LIMIT`` per phase).
            ``"all_agents"`` builds the room with every created agent, so no
            designation can be structurally impossible. The default stays the
            baseline until the #1760 comparative measurement says otherwise.

    Returns dict with state snapshot, conversation history, and metrics.
    """
    start_time = time.time()

    # 0a. Activate per-run LLM-call circuit breaker (#950).
    # Mirrors workflow_dsl.py:334 — every LLM call from every phase counts
    # against one ceiling, so a degenerate counter-arg sweep cannot run away
    # into thousands of round-trips (issue #708 origin).  Re-entrant: if a
    # budget scope is already active (e.g. from a parent orchestrator), it is
    # reused without resetting the count.
    from argumentation_analysis.orchestration.invoke_callables import (
        llm_budget_scope,
    )

    with llm_budget_scope():
        return await _run_conversational_analysis_inner(
            text=text,
            max_turns_per_phase=max_turns_per_phase,
            agent_names=agent_names,
            spectacular=spectacular,
            extraction_max_turns=extraction_max_turns,
            formal_max_turns=formal_max_turns,
            synthesis_max_turns=synthesis_max_turns,
            reanalysis_max_turns=reanalysis_max_turns,
            enable_growth_validation=enable_growth_validation,
            growth_re_prompt_limit=growth_re_prompt_limit,
            enable_tool_gating=enable_tool_gating,
            enable_reprompt_tracing=enable_reprompt_tracing,
            source_metadata=source_metadata,
            selector_context=selector_context,
            max_total_turns=max_total_turns,
            max_wall_seconds=max_wall_seconds,
            render_restitution=render_restitution,
            room_policy=room_policy,
        )


def _formal_axis_genuine(results: List[Any]) -> bool:
    """True iff at least one result entry is a genuine reasoning artifact.

    Constat n°5 (#1355): a formal axis (FOL/modal/PL) counts as *genuinely
    used* only when an entry carries non-empty ``formulas`` (something was
    actually formalized) AND bears no explicit ``unavailable:*`` degradation
    token. Requiring non-empty formulas prevents an empty theory from reading
    as a "trivially consistent" decision — the exact theatre #1019 forbids.
    The ``unavailable:`` marker is the canonical honest-degradation signal
    written by the FOL/modal writers (#1278/#1279: ``no-translation``,
    ``parse-fail``, ``no-solver``).
    """
    for entry in results:
        if not isinstance(entry, dict):
            continue
        message = entry.get("message")
        if isinstance(message, str) and message.startswith("unavailable:"):
            continue
        if entry.get("formulas"):
            return True
    return False


def _axis_produced_formulas(results: List[Any]) -> bool:
    """True iff at least one entry carries non-empty formulas.

    Distinct from :func:`_formal_axis_genuine`: NL→formal *translation*
    succeeded whenever formulas exist on an axis, even if the solver later
    degraded (e.g. modal ``unavailable:no-solver`` keeps the translated
    formulas — invoke_callables.py:6429). This lets ``nl_to_logic_translation``
    be reported genuine while ``modal_logic`` is reported degraded.
    """
    for entry in results:
        if isinstance(entry, dict) and entry.get("formulas"):
            return True
    return False


def _classify_formal_capabilities(
    state: Any,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Split FormalAgent participation into honest used/degraded/missing sets.

    Constat n°5 (#1355): the spectacular rollup previously declared every
    formal capability as ``used`` the moment FormalAgent spoke — even when
    FOL/modal were ``degraded=true`` (parse-fail, no-translation, solver OOM).
    This crosses participation with the REAL per-axis decision status already
    recorded in ``state`` (``fol/modal/propositional_analysis_results``),
    mirroring the honest ``structured_arg_status`` layer but for the
    ``fol_reasoning``/``modal_logic``/``propositional_logic``/
    ``nl_to_logic_translation`` vocabulary.

    Returns ``(used, degraded, missing)``:
      * *used* — axis genuinely decided/produced (non-empty formulas, no
        ``unavailable:*`` token).
      * *degraded* — axis participated but every entry is a degradation.
      * *missing* — FormalAgent participated but the axis left no entry.

    Anti-théâtre #1019: a degraded axis is never reported as ``used``; an empty
    theory is never reported as a genuine decision.
    """
    fol_res = list(getattr(state, "fol_analysis_results", []) or [])
    modal_res = list(getattr(state, "modal_analysis_results", []) or [])
    pl_res = list(getattr(state, "propositional_analysis_results", []) or [])
    used: Set[str] = set()
    degraded: Set[str] = set()
    missing: Set[str] = set()
    for cap, results in (
        ("fol_reasoning", fol_res),
        ("modal_logic", modal_res),
        ("propositional_logic", pl_res),
    ):
        if _formal_axis_genuine(results):
            used.add(cap)
        elif results:
            degraded.add(cap)
        else:
            missing.add(cap)
    # nl_to_logic_translation is genuine iff translation produced formulas on
    # ANY axis (distinct from the solver later degrading). If FormalAgent
    # participated but produced no formulas anywhere, it degraded; if it left
    # no formal entries at all, it is missing.
    if any(_axis_produced_formulas(r) for r in (fol_res, modal_res, pl_res)):
        used.add("nl_to_logic_translation")
    elif fol_res or modal_res or pl_res:
        degraded.add("nl_to_logic_translation")
    else:
        missing.add("nl_to_logic_translation")
    return used, degraded, missing


async def _run_conversational_analysis_inner(
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
    enable_tool_gating: bool = False,
    enable_reprompt_tracing: bool = False,
    source_metadata: Optional[Dict[str, str]] = None,
    selector_context: Optional[Dict[str, Any]] = None,
    max_total_turns: Optional[int] = None,
    max_wall_seconds: Optional[float] = None,
    render_restitution: bool = False,
    room_policy: str = ROOM_POLICY_PHASE_CASTING,
) -> Dict[str, Any]:
    """Inner implementation of run_conversational_analysis, already inside llm_budget_scope."""
    start_time = time.time()

    # #1760: a mistyped policy must fail loud, never silently run the baseline
    # (anti-#1019 — an unknown value falling through to phase_casting would
    # make a measurement row that claims to be a variant but is the control).
    if room_policy not in _ROOM_POLICIES:
        raise ValueError(
            f"Unknown room_policy {room_policy!r}; expected one of "
            f"{', '.join(_ROOM_POLICIES)}"
        )
    absorption_reprompt_limit = (
        _ABSORPTION_REPROMPT_LIMIT if room_policy == ROOM_POLICY_REPROMPT else None
    )

    # C1 #1500: wall-clock budget. Checked before each phase (coarse) and
    # threaded as an absolute deadline into _run_phase (per-turn, fine). On
    # exhaustion the run exits cleanly and the partial state becomes the
    # verdict — anti-#1019 (real bounded verdict, not a killed coroutine).
    wall = WallClockBudget(max_seconds=max_wall_seconds, start=start_time)

    # CONV-C #1334 §6: pipeline-global tour cap. Default = sum of every phase
    # cap (3 macro + conditional Re-Analysis), derived from the per-phase config
    # so the default never binds (the cap only constrains when a caller sets a
    # smaller explicit budget). The cap is a fixed contract surfaced to the PM
    # and enforced across phases; breach is recorded (CapBreachRecord) and ends
    # the run fail-loud.
    if max_total_turns is None:
        max_total_turns = (
            extraction_max_turns
            + formal_max_turns
            + synthesis_max_turns
            + reanalysis_max_turns
        )
    turns_used = 0
    budget_exhausted = False
    wall_clock_bounded = False

    # 0b. Env var override for growth validation (#597)
    _env_growth = os.environ.get("ENABLE_GROWTH_VALIDATION", "").lower()
    if _env_growth in ("0", "false", "no"):
        enable_growth_validation = False

    # 0c. Env var override for tool gating (#605)
    _env_gating = os.environ.get("ENABLE_TOOL_GATING", "").lower()
    if _env_gating in ("1", "true", "yes"):
        enable_tool_gating = True

    # 0d. Env var override for re-prompt tracing (#609)
    _env_trace = os.environ.get("ENABLE_REPROMPT_TRACING", "").lower()
    if _env_trace in ("1", "true", "yes"):
        enable_reprompt_tracing = True

    # 0e. Re-prompt trace accumulator (#609)
    reprompt_extractor = None
    if enable_reprompt_tracing:
        from argumentation_analysis.reporting.reprompt_trace import (
            RepromptTraceExtractor,
        )

        reprompt_extractor = RepromptTraceExtractor()

    # 1. Setup kernel + LLM
    # Route through create_llm_service so the OpenRouter toggle applies: if
    # OPENROUTER_BASE_URL + OPENROUTER_API_KEY are set, calls go to OpenRouter
    # (OpenAI-compatible); otherwise the official OpenAI endpoint is used. This
    # is the single linchpin service shared by every conversational agent and
    # plugin, so the toggle here covers the whole pipeline. force_authentic=True
    # preserves the prior behavior (a real LLM was always built here, never a
    # mock, even under PYTEST_CURRENT_TEST).
    kernel = sk.Kernel()
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
    try:
        llm_service = create_llm_service(
            service_id="conversational_llm",
            model_id=model_id,
            force_authentic=True,
        )
    except ValueError as e:
        raise RuntimeError(
            f"{e} Conversational mode requires an LLM. Ensure .env is loaded."
        )
    kernel.add_service(llm_service)

    # 2. Setup shared state (#363: UnifiedAnalysisState for spectacular coverage)
    state_cls = UnifiedAnalysisState if spectacular else RhetoricalAnalysisState
    state = state_cls(text)

    # 2b. Build agent → phase-scoped state plugin mapping (#605)
    agent_state_class = {}
    if enable_tool_gating:
        from argumentation_analysis.core.phase_scoped_state import AGENT_PHASE_MAP

        agent_state_class = dict(AGENT_PHASE_MAP)
        logger.info(
            f"Tool gating enabled: {len(agent_state_class)} agents get phase-scoped state plugins"
        )

    # 3. Create all agents
    all_agents = create_conversational_agents(
        kernel,
        state,
        "conversational_llm",
        agent_names,
        agent_state_class=agent_state_class,
        pm_budget_turns=max_total_turns,
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
    # CE #1537: accumulate each phase's execution_path (surfaced at the source
    # by _run_phase) so the result can report whether the run was a genuine
    # AgentGroupChat or a round-robin fallback. Read explicitly from the phase
    # meta — never deduced from metrics (anti-#1019 / leçon #1531).
    phase_execution_paths: List[str] = []

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
        # CONV-C #1334 §6: pipeline-global cap — stop once the budget is spent.
        # The cap is a fixed contract; hitting it ends the run fail-loud
        # (CapBreachRecord + BUDGET_EXHAUSTED status), not a silent truncation.
        if turns_used >= max_total_turns:
            budget_exhausted = True
            if hasattr(state, "record_cap_breach"):
                state.record_cap_breach(
                    cap_kind="pipeline_global",
                    turn=turns_used,
                    detail=(
                        f"budget {max_total_turns} atteint avant phase "
                        f"'{phase_cfg['name']}'"
                    ),
                )
            logger.warning(
                f"[CONV-C] Budget pipeline-global atteint ({turns_used}/"
                f"{max_total_turns}) — phase '{phase_cfg['name']}' et les "
                f"suivantes sont sautées."
            )
            break

        # C1 #1500: wall-clock budget — stop once the deadline is reached.
        # Distinct from the turn-count cap above: this bounds ELAPSED time so
        # the mode terminates in a comparable timeframe on a real (slow) LLM.
        # Breach is recorded (CapBreachRecord cap_kind="wall_clock") and the
        # run ends with status WALL_CLOCK_BOUNDED; the partial state built
        # after the loop IS the verdict (anti-#1019 — real, not faked/None).
        if wall.is_exhausted(time.time()):
            wall_clock_bounded = True
            if hasattr(state, "record_cap_breach"):
                state.record_cap_breach(
                    cap_kind="wall_clock",
                    turn=turns_used,
                    detail=(
                        f"wall-clock budget {max_wall_seconds:g}s atteint "
                        f"avant phase '{phase_cfg['name']}'"
                    ),
                )
            logger.warning(
                f"[C1] Wall-clock budget atteint ({max_wall_seconds:g}s) — "
                f"phase '{phase_cfg['name']}' et les suivantes sont sautées "
                f"(verdict partiel honnête)."
            )
            break

        phase_name = phase_cfg["name"]
        phase_agent_names = phase_cfg["agents"]
        phase_agents, phase_agents_missing = _resolve_phase_agents(
            agent_by_name, phase_agent_names
        )
        if phase_agents_missing:
            # #1751 item 3: name them. A phase that runs with 2 of its 4 agents
            # is not the phase that was configured, and the PM is steering in
            # the shrunken room without being told.
            logger.warning(
                "[#1751] Phase '%s': %d agent(s) du casting absents du roster "
                "et retirés de la salle: %s (présents: %s)",
                phase_name,
                len(phase_agents_missing),
                phase_agents_missing,
                [getattr(a, "name", "?") for a in phase_agents],
            )

        if not phase_agents:
            logger.warning(f"No agents available for phase '{phase_name}', skipping")
            continue

        # #1760: the room the AgentGroupChat is actually built with. Under
        # ``all_agents`` it is the full created roster (voie 3); otherwise the
        # phase casting (baseline / truth / reprompt all keep the casting).
        room_agents = _resolve_room_agents(room_policy, phase_agents, all_agents)

        # #1760 voie 1: at phase entry, the PM's prompt names exactly who is in
        # the room — instead of the implicit "8" its capability map implies.
        if room_policy == ROOM_POLICY_TRUTH:
            _apply_room_truth_to_pm(
                agent_by_name.get("ProjectManager"),
                [a.name for a in room_agents],
                max_total_turns,
            )

        # Per-phase turn limit (falls back to global max_turns_per_phase),
        # further clamped to the remaining pipeline-global budget (§6).
        phase_max_turns = phase_cfg.get("max_turns", max_turns_per_phase)
        remaining = max_total_turns - turns_used
        effective_max_turns = min(phase_max_turns, remaining)

        logger.info(
            f"=== Phase: {phase_name} ({len(phase_agents)} agents, "
            f"max {effective_max_turns} turns) ==="
        )

        # Trace: capture state before phase
        try:
            trace.begin_phase(phase_name, state.get_state_snapshot(summarize=False))
        except Exception:
            trace.begin_phase(phase_name)

        phase_log = await _run_phase(
            room_agents,
            phase_cfg["initial_prompt"],
            max_turns=effective_max_turns,
            phase_name=phase_name,
            state=state,
            enable_growth_validation=enable_growth_validation,
            growth_re_prompt_limit=growth_re_prompt_limit,
            reprompt_extractor=reprompt_extractor,
            deadline=wall.deadline,
            execution_path_recorder=phase_execution_paths,
            absorption_reprompt_limit=absorption_reprompt_limit,
        )
        conversation_log.extend(phase_log)

        # CONV-C #1334 §6: accumulate turns consumed (highest turn index in the
        # phase) against the pipeline-global budget.
        phase_turns = max(
            (m.get("turn", 0) for m in phase_log if isinstance(m.get("turn"), int)),
            default=0,
        )
        turns_used += phase_turns

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
            harness_log = await _run_parent_harness_fallback(
                text,
                state,
                selector_context=selector_context,
            )
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

    # CB #1528 item 3 (C1 #1500): ONE shared predicate for every stage that
    # runs after the phase loop. Before this, ``wall_clock_bounded`` was set at
    # the breach and then read ONLY to build the result dict — it gated
    # nothing. The cap therefore behaved as a scheduling decision ("do not
    # start the next PHASE") while the run kept issuing LLM round-trips for the
    # conditional Re-Analysis phase and the five ``spectacular`` stages below,
    # until an external safety-net cut the coroutine and discarded the state it
    # had just populated (firsthand: arguments and counter-arguments written
    # seconds before the cut, reported as an empty row).
    #
    # Anti-pendule: these stages are NOT removed — they carry the analytical
    # value of the mode. They are SKIPPED once the budget is spent, which is
    # what "verdict partiel honnête" already means everywhere else here. And
    # no second budget mechanism is introduced: ``wall`` is the one authority.
    def _budget_allows(stage: str) -> bool:
        nonlocal wall_clock_bounded
        if not wall.is_exhausted(time.time()):
            return True
        # The loop may have finished all phases and the deadline passed only
        # during post-processing: record the bound so the result stays honest.
        wall_clock_bounded = True
        logger.info(
            f"[C1] Wall-clock budget épuisé ({max_wall_seconds:g}s) — étage "
            f"post-boucle '{stage}' sauté (verdict partiel honnête)."
        )
        return False

    # 5b. Conditional Phase 4: Re-Analysis (#305)
    # If the enrichment summary shows gaps (e.g., JTMS retracted beliefs not
    # re-evaluated, arguments missing fallacy analysis), add an extra phase
    # to re-analyze using informal + quality + governance agents.
    reanalysis_added = False
    # CONV-C #1334 §6: skip the conditional Re-Analysis phase if the
    # pipeline-global budget is already exhausted (the run ended fail-loud).
    # CB #1528 item 3: ``budget_exhausted`` is the TURN-COUNT flag; the
    # wall-clock bound is a distinct budget and was not consulted here, so a
    # run stopped by the clock still ran a whole extra 4-agent phase.
    if (
        not budget_exhausted
        and hasattr(state, "get_enrichment_summary")
        and _budget_allows("Re-Analysis")
    ):
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
                            if detected_lang == "de"
                            else ""
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
                    # #1760: same room treatment as the macro-phases — the
                    # conditional 4th room is a room too.
                    reanalysis_room = _resolve_room_agents(
                        room_policy, reanalysis_agents, all_agents
                    )
                    if room_policy == ROOM_POLICY_TRUTH:
                        _apply_room_truth_to_pm(
                            agent_by_name.get("ProjectManager"),
                            [a.name for a in reanalysis_room],
                            max_total_turns,
                        )
                    logger.info(
                        f"=== Phase: {phase_name} ({len(reanalysis_room)} agents, "
                        f"max {reanalysis_cfg['max_turns']} turns) ==="
                    )

                    # CONV-C #1334 §6: clamp Re-Analysis to remaining budget.
                    remaining = max(0, max_total_turns - turns_used)
                    reanalysis_effective = max(
                        1, min(reanalysis_cfg["max_turns"], remaining)
                    )

                    try:
                        trace.begin_phase(
                            phase_name, state.get_state_snapshot(summarize=False)
                        )
                    except Exception:
                        trace.begin_phase(phase_name)

                    phase_log = await _run_phase(
                        reanalysis_room,
                        reanalysis_cfg["initial_prompt"],
                        max_turns=reanalysis_effective,
                        phase_name=phase_name,
                        state=state,
                        enable_growth_validation=enable_growth_validation,
                        growth_re_prompt_limit=growth_re_prompt_limit,
                        reprompt_extractor=reprompt_extractor,
                        deadline=wall.deadline,
                        execution_path_recorder=phase_execution_paths,
                        absorption_reprompt_limit=absorption_reprompt_limit,
                    )
                    conversation_log.extend(phase_log)

                    turns_used += max(
                        (
                            m.get("turn", 0)
                            for m in phase_log
                            if isinstance(m.get("turn"), int)
                        ),
                        default=0,
                    )

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
    #
    # CB #1528 item 3 — the next four stages (Dung, modal, ASPIC, belief
    # revision) are deliberately NOT gated by ``_budget_allows``. They are
    # synchronous (no ``await``, no kernel/agent/LLM call — checked by AST)
    # and only re-read state the conversation has already populated, so they
    # cost milliseconds and cannot push the run past its deadline. Gating them
    # would strip content from an honest partial verdict for no time saved.
    # What the budget must cut is what still SPENDS it: the awaited stages.
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

    # 5b-6. Counter-argument enrichment (GG #696)
    # The conversational dialogue under-produces counter-arguments (often 1),
    # losing to the zero-shot baseline on the quantitative axis. Sweep every
    # identified argument and ensure >=1 counter-argument per argument, so the
    # collaborative path matches the sequential path's coverage.
    n_args = len(getattr(state, "identified_arguments", []) or [])
    n_cas = len(getattr(state, "counter_arguments", []) or [])
    if (
        spectacular
        and n_args
        and n_cas < n_args
        and _budget_allows("counter_arguments")
    ):
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _generate_counter_arguments_from_state,
            )

            ca_result = await _generate_counter_arguments_from_state(state)
            if ca_result and ca_result.get("added"):
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "counter_argument_enrichment",
                        "added": ca_result["added"],
                        "targets": ca_result["targets"],
                    }
                )
        except Exception as e:
            logger.warning(f"Counter-argument enrichment post-processing failed: {e}")

    # 5b-7. Formal logic enrichment — PL/FOL volet-1 writers (HH #697)
    # The conversational dialogue routes formal logic to belief_sets, leaving
    # propositional_analysis_results / fol_analysis_results empty (PL/FOL = 0,
    # losing to the zero-shot baseline). Mirror the Dung/modal/ASPIC
    # post-processors: reuse the sequential Tweety-verified PL/FOL invoke
    # callables so the collaborative path emits the same volet-1 formulas.
    if (
        spectacular
        and hasattr(state, "propositional_analysis_results")
        and not state.propositional_analysis_results
        and not getattr(state, "fol_analysis_results", None)
        and _budget_allows("formal_logic_enrichment")
    ):
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _run_formal_logic_from_state,
            )

            formal_result = await _run_formal_logic_from_state(state, text)
            if formal_result and (
                formal_result.get("pl_added") or formal_result.get("fol_added")
            ):
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "formal_logic_enrichment",
                        "pl_formulas": formal_result["pl_added"],
                        "fol_formulas": formal_result["fol_added"],
                    }
                )
        except Exception as e:
            logger.warning(f"Formal logic enrichment post-processing failed: {e}")

    # 5b-8. Quality sweep enrichment (JJ #699)
    # The conversational QualityAgent depends on the agent turn budget; when it
    # runs out the dialogue emits 0 quality scores (path-dependent, some corpora
    # end at 0). Mirror the other post-processors: reuse the robust sequential
    # 9-virtue evaluator over every identified argument so the collaborative path
    # always has quality scores. Gated on under-production — fills gaps only.
    n_quality = len(getattr(state, "argument_quality_scores", {}) or {})
    if (
        spectacular
        and n_args
        and n_quality < n_args
        and _budget_allows("quality_sweep")
    ):
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _run_quality_sweep_from_state,
            )

            q_result = await _run_quality_sweep_from_state(state)
            if q_result and q_result.get("added"):
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "quality_sweep_enrichment",
                        "added": q_result["added"],
                    }
                )
        except Exception as e:
            logger.warning(f"Quality sweep post-processing failed: {e}")

    # 5b-10. Stakes & Stakeholders extraction (Track TT #723)
    if spectacular and _budget_allows("stakes_extraction"):
        try:
            from argumentation_analysis.orchestration.invoke_callables import (
                _invoke_stakes_extractor,
            )

            stakes_ctx = {
                "_state_object": state,
                "source_metadata": source_metadata or {},
            }
            stakes_result = await _invoke_stakes_extractor("", stakes_ctx)
            if "error" not in stakes_result:
                n_stakes = len(stakes_result.get("stakes", []))
                n_sh = len(stakes_result.get("stakeholders", []))
                logger.info(
                    f"Stakes extraction: {n_stakes} stakes, {n_sh} stakeholders"
                )
                conversation_log.append(
                    {
                        "phase": "post_processing",
                        "type": "stakes_extraction",
                        "stakes": n_stakes,
                        "stakeholders": n_sh,
                        "rhetorical_register": stakes_result.get(
                            "rhetorical_register", ""
                        ),
                    }
                )
        except Exception as e:
            logger.warning(f"Stakes extraction post-processing failed: {e}")

    # 5c. Deep Synthesis post-phase (#534)
    # Run DeepSynthesisAgent on the accumulated state to produce a 9-section
    # grounded markdown report. Appended as terminal step after all agents.
    deep_synthesis_result = None
    if spectacular and _budget_allows("deep_synthesis"):
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
            # PP #715: merge caller-provided source_metadata
            if source_metadata:
                source_meta.update(source_metadata)
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

    # Dict[str, Any] (matches the return type): the literal holds heterogeneous
    # value types (state objects, counts, lists, the RenderedReport), and a
    # narrow inference rejects later heterogeneous assignments (#1335 wiring).
    result: Dict[str, Any] = {
        "mode": "conversational",
        "workflow_name": "spectacular_analysis" if spectacular else "conversational",
        "phases": [p["name"] for p in phase_configs],
        # CE #1537: which execution path actually ran, aggregated from each
        # phase's source-recorded meta (NOT deduced from metrics). "agent_group_chat"
        # only if every phase ran the SK AgentGroupChat path; any fallback
        # (construction failure, runtime error, or SK unavailable) downgrades to
        # "round_robin_fallback" so the comparison harness cannot read a fallback
        # run as a genuine group-chat run (anti-#1019).
        # CB #1528 item 3: when NO phase ran (the wall-clock deadline was
        # already past at entry, e.g. a budget smaller than the agent setup),
        # there is no path to report. Claiming "round_robin_fallback" here
        # would assert a branch that never executed — the CE defect itself.
        # ``None`` renders as "—" in the harness table, like every other mode
        # that records no path.
        "execution_path": (
            None
            if not phase_execution_paths
            else (
                "agent_group_chat"
                if all(p == "agent_group_chat" for p in phase_execution_paths)
                else "round_robin_fallback"
            )
        ),
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
        # CONV-C #1334 §6 + C1 #1500: budget accounting + fail-loud status.
        # wall_clock_bounded is surfaced so downstream readers (BO-4 harness,
        # reports) can distinguish a real PARTIAL verdict reached at the
        # wall-clock bound from a clean completion — both are successes (a
        # verdict was produced), the flag is the honest nuance (anti-#1019).
        "budget": {
            "max_total_turns": max_total_turns,
            "turns_used": turns_used,
            "exhausted": budget_exhausted,
            "max_wall_seconds": max_wall_seconds,
            "wall_clock_bounded": wall_clock_bounded,
            "deliberation_turn_count": _deliberation_turn_count(state),
            "cap_breaches": [
                r
                for r in getattr(state, "deliberation_trace", [])
                if r.get("record_type") == "cap_breach"
            ],
            # #1751: designations the PM emitted for an agent absent from its
            # phase room. Surfaced next to the caps because it is the same kind
            # of fact: the run did not do what the trace appears to say. A
            # non-empty list means the chief was contradicted by the casting,
            # not that it changed its mind.
            "designations_unresolved": [
                r
                for r in getattr(state, "deliberation_trace", [])
                if r.get("record_type") == "designation_unresolved"
            ],
        },
        "status": (
            "WALL_CLOCK_BOUNDED"
            if wall_clock_bounded
            else ("BUDGET_EXHAUSTED" if budget_exhausted else "COMPLETED")
        ),
        "summary": {
            "completed": len(phase_configs),
            "failed": 0,
            "skipped": 0,
            "total": len(phase_configs),
            "total_messages": len(conversation_log),
        },
    }

    # Spectacular mode: add capability mapping from conversation log.
    # Constat n°5 (#1355): formal capabilities are crossed with the REAL
    # per-axis decision status in ``state`` — a degraded axis (parse-fail,
    # no-translation, solver OOM) is reported via ``capabilities_degraded``,
    # NOT as ``used`` identical to a genuine decision (anti-théâtre #1019).
    # ``capabilities_missing`` reflects axes that participated but left no
    # entry, instead of a hardcoded empty list.
    if spectacular:
        capabilities_used: Set[str] = set()
        capabilities_degraded: Set[str] = set()
        capabilities_missing: Set[str] = set()
        formal_participated = False
        for msg in conversation_log:
            agent = msg.get("agent", "")
            if agent == "ExtractAgent":
                capabilities_used.add("fact_extraction")
            elif agent == "InformalAgent":
                capabilities_used.update(
                    ["neural_fallacy_detection", "hierarchical_fallacy_detection"]
                )
            elif agent == "FormalAgent":
                formal_participated = True
            elif agent == "QualityAgent":
                capabilities_used.add("argument_quality")
            elif agent == "CounterAgent":
                capabilities_used.add("counter_argument_generation")
            elif agent == "DebateAgent":
                capabilities_used.add("adversarial_debate")
            elif agent == "GovernanceAgent":
                capabilities_used.add("governance_simulation")
        if formal_participated:
            f_used, f_degraded, f_missing = _classify_formal_capabilities(state)
            capabilities_used |= f_used
            capabilities_degraded |= f_degraded
            capabilities_missing |= f_missing
        # Sorted for deterministic output (golden/compare snapshots, #1355).
        result["capabilities_used"] = sorted(capabilities_used)
        result["capabilities_degraded"] = sorted(capabilities_degraded)
        result["capabilities_missing"] = sorted(capabilities_missing)

    logger.info(
        f"Conversational analysis complete: {len(conversation_log)} messages, "
        f"{non_empty} state fields, {duration:.1f}s"
    )

    # CONV-D #1335 périmètre 1+2: assemble the readable 3-act restitution report
    # from the completed conversational state. The conversational path does not
    # run the act-generation phases (it runs Extraction/Formal/Synthesis
    # macro-phases via AgentGroupChat), so the acts are generated here from the
    # completed state, then rendered. Honest on any state — missing/unavailable
    # acts are named by the renderer, never fabricated (#1019/#369). Reporting
    # never fails the run (same fail-loud-non-fatal idiom as the pipeline path).
    if render_restitution and state is not None:
        try:
            from argumentation_analysis.reporting.restitution.conversational_adapter import (
                generate_and_render_for_conversational_state,
            )

            result["restitution_report"] = (
                await generate_and_render_for_conversational_state(state, text)
            )
        except Exception as exc:  # noqa: BLE001 — reporting must never fail the run
            logger.warning(
                "Conversational restitution rendering failed (fail-loud, "
                "non-fatal): %s",
                exc,
            )
            result["restitution_report"] = None

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


def _backfill_designation_if_present(state: Any, agent: Optional[str]) -> None:
    """CONV-C #1334 §7.3: close the open DesignationRecord when its agent returns.

    Thin guard around ``state.backfill_last_designation_for`` so ``_run_phase``
    callers don't branch on state type: a no-op for base
    ``RhetoricalAnalysisState`` (no deliberation trace) or when ``agent`` is
    None. The matching logic (designated_agent == agent) lives on the state.
    """
    if agent is None:
        return
    backfill = getattr(state, "backfill_last_designation_for", None)
    if backfill is None:
        return
    try:
        backfill(agent)
    except Exception:
        logger.debug("backfill_last_designation_for failed", exc_info=True)


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


def _deliberation_turn_count(state: Any) -> int:
    """Number of genuine PM designations in the deliberation trace (#1751).

    A DesignationRecord carries **no** ``record_type`` (it is the ``asdict`` of
    the dataclass); every non-designation entry declares one. Counting by
    allow-list — "a designation is a record with no marker" — instead of by
    exclusion list ("everything that is not a ``cap_breach``") is what keeps
    this number honest when a marker type is added: the previous form would
    have silently counted each ``designation_unresolved`` as one more
    deliberation turn, inflating the very metric #1751 exists to correct.
    """
    return sum(
        1
        for r in getattr(state, "deliberation_trace", [])
        if r.get("record_type") is None
    )


def _resolve_phase_agents(
    agent_by_name: Dict[str, Any], phase_agent_names: List[str]
) -> Tuple[List[Any], List[str]]:
    """Resolve a phase casting, returning the agents AND the names that missed.

    #1751 scope item 3. The comprehension this replaces dropped any unknown
    name silently, so a phase configured with four agents could run with two
    and say nothing. The room the PM is steering in is exactly what this issue
    is about: it has to be reported, not inferred.
    """
    resolved = [agent_by_name[n] for n in phase_agent_names if n in agent_by_name]
    missing = [n for n in phase_agent_names if n not in agent_by_name]
    return resolved, missing


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

        # Designated agent not in this phase, fall through to round-robin.
        # #1751: third absorption site, and the quietest of the three — DEBUG.
        # Round-robin then hands the floor to whoever is next in the casting,
        # which reads downstream as an ordinary turn.
        record_unresolved_designation(
            state,
            requested_agent=designated,
            present_agents=[getattr(a, "name", "?") for a in agents],
            selection_path="round_robin",
        )
        logger.debug(
            f"  PM designated '{designated}' but not in phase agents, using round-robin"
        )

    # Round-robin fallback
    return agents[turn % len(agents)]


def _find_agent_by_name(
    agents: List["ChatCompletionAgent"], name: Optional[str]
) -> Optional["ChatCompletionAgent"]:
    """CF #1538: locate the agent that just spoke in an AgentGroupChat turn.

    ``AgentGroupChat.invoke()`` yields ``ChatMessageContent`` whose ``.name``
    identifies the speaking agent; this looks it up in the phase's ``agents``
    list so the growth re-prompt targets the agent that produced the
    zero-growth turn (not a round-robin pick). Returns None if the name is
    missing/unknown — the caller skips the re-prompt (safe no-op).
    """
    if not name:
        return None
    for agent in agents:
        if getattr(agent, "name", None) == name:
            return agent
    return None


async def _bounded_invoke(
    async_gen: Any,
    deadline: Optional[float],
    phase_name: str,
    path_label: str,
) -> Any:
    """CB #1528 item 5: yield from ``async_gen`` (an ``invoke()`` async
    generator), bounding EACH ``__anext__`` to the remaining wall-clock budget.

    Why this exists: the live AgentGroupChat path's first ``chat.invoke()``
    drives a function-calling agent that chains ~12 LLM round-trips before
    yielding a single response (measured R716/R717, published on #1528). Every
    inter-turn deadline guard (item 3 #1544 / item 4 #1546) checks BETWEEN
    turns — none can fire inside a turn that never ends, so a tight wall-clock
    budget was blown by ONE invocation and the external net caught it,
    throwing away a populated state. This checkpoint bounds the invocation
    ITSELF: a single ``__anext__`` cannot consume the whole remaining budget.

    On timeout, the in-flight response is lost — but the shared ``state``
    object is NOT. Plugins write to it DURING the invocation; the
    ``CancelledError`` ``asyncio.wait_for`` raises at the await point leaves
    those writes intact, so the partial state becomes the honest partial
    verdict (same observation as R715, viewed from the other end).

    This is NOT the "coroutine killed mid-flight by an external
    ``asyncio.wait_for``" the ``WallClockBudget`` docstring (L67-68) rejects:
    that kills the WHOLE ``run_conversational_analysis`` and loses its return
    dict (``decides=False``); this bounds a single ``__anext__`` INSIDE
    ``_run_phase``, which then returns normally with the messages accumulated
    so far — the verdict comes from the populated ``state``, not from a
    constructed-but-lost return value.

    Anti-pendule: a SINGLE mechanism, derived from the existing ``deadline``
    (no second budget). When ``deadline`` is None the generator is yielded
    unchanged (no-op for unbounded runs — the unbounded path is preserved
    byte-for-byte, mutation-verified by the dedicated test).
    """
    agen = async_gen.__aiter__()
    try:
        while True:
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    logger.info(
                        f"  [{phase_name}] Wall-clock deadline atteinte avant "
                        f"un tour ({path_label}, borne intra-invocation CB "
                        f"#1528 item 5) ; invocation stoppée, état accumulé "
                        f"préservé comme verdict partiel."
                    )
                    return
                try:
                    response = await asyncio.wait_for(
                        agen.__anext__(), timeout=remaining
                    )
                except StopAsyncIteration:
                    return
                except asyncio.TimeoutError:
                    logger.info(
                        f"  [{phase_name}] Wall-clock deadline atteinte PENDANT "
                        f"l'invocation ({path_label}, borne intra-invocation "
                        f"CB #1528 item 5) ; réponse en vol perdue, état "
                        f"accumulé préservé comme verdict partiel."
                    )
                    return
            else:
                try:
                    response = await agen.__anext__()
                except StopAsyncIteration:
                    return
            yield response
    finally:
        # Best-effort cleanup of the underlying generator. It may already be
        # exhausted (normal completion) or cancelled mid-flight (timeout); in
        # either case aclose is a safe no-op or a swallowable exception, never
        # fatal to the bounded path.
        try:
            await agen.aclose()
        except Exception:  # noqa: BLE001 — cleanup must never mask the bound
            pass


async def _run_phase(
    agents: List[ChatCompletionAgent],
    initial_prompt: str,
    max_turns: int = 5,
    phase_name: str = "",
    state=None,
    enable_growth_validation: bool = True,
    growth_re_prompt_limit: int = 2,
    reprompt_extractor=None,
    deadline: Optional[float] = None,
    execution_path_recorder: Optional[List[str]] = None,
    absorption_reprompt_limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Run a single conversational phase with a set of agents.

    Uses SK AgentGroupChat if available, otherwise falls back to
    round-robin invocation with PM designation support and convergence detection.

    When ``enable_growth_validation`` is True, after each agent turn in a
    growth-expecting phase (Extraction, Detection, Re-Analysis), the hook
    compares a state fingerprint before/after.  If no growth occurred, the
    agent is re-prompted with explicit function-call feedback up to
    ``growth_re_prompt_limit`` times per turn.

    ``deadline`` (C1 #1500) is an absolute wall-clock timestamp; when set, the
    phase checks it before each agent turn and exits cleanly when passed, so a
    wall-clock-bounded run preserves the partial state as the verdict.

    ``execution_path_recorder`` (CE #1537): optional accumulator list. When
    provided, the phase appends the path that actually ran
    (``"agent_group_chat"`` or ``"round_robin_fallback"``) — recorded at the
    source (here), never deduced from metrics. The path is NOT added to the
    returned message list: polluting it would break C1 contracts that count on
    its exact length/content (``test_deadline_in_past_breaks_before_first_turn``).

    ``absorption_reprompt_limit`` (#1760 voie 2): when set, a turn that opened
    with an absorbed designation (a fresh ``designation_unresolved`` marker
    recorded by the selection strategy, whose fallback speaker — the first
    agent of the room — then took the floor) is followed by ONE re-prompt of
    that fallback speaker carrying the present roster, up to ``limit`` times
    per phase. Uses the growth re-prompt mechanism (direct ``agent.invoke`` on
    a deep-copied history — ``chat.add_chat_message`` is forbidden while the
    chat is active). ``None`` disables it (every policy except ``reprompt``).
    """
    messages: List[Dict[str, Any]] = []
    total_re_prompts = 0

    # C1 #1500 / CB #1528 item 3: check the deadline BEFORE entering either
    # execution path. The round-robin loop already checks before invoking the
    # next agent, but the AgentGroupChat path invoked ``chat.invoke()``
    # unconditionally and only checked *after* the first response had come
    # back — so a phase entered with an already-expired deadline still burned
    # one full multi-agent turn. Since CD #1534 the group-chat path is the
    # live one, and the existing regression test does NOT cover it: it injects
    # a raising AgentGroupChat precisely to force the round-robin fallback.
    # No path is recorded here on purpose: nothing ran, and asserting a path
    # that did not execute is the CE #1537 residual defect.
    if deadline is not None and time.time() >= deadline:
        logger.info(
            f"  [{phase_name}] Wall-clock deadline déjà atteint à l'entrée de "
            f"la phase — aucun tour entamé (verdict partiel honnête)."
        )
        return messages

    chat_history = ChatHistory()
    chat_history.add_user_message(initial_prompt)

    # CE #1537: track which execution path actually ran, surfaced at the source
    # (here) so the comparison harness can distinguish a real AgentGroupChat run
    # from a silent round-robin fallback (anti-#1019: "renseigné à la source,
    # pas déduit"). Default is the fallback; only the AgentGroupChat path that
    # completes without raising sets "agent_group_chat". A construction failure
    # or a runtime invoke error falls through to round-robin and keeps the
    # default — which is exactly the indistinguishable-from-success case CD
    # #1534 made LOUD in logs; CE #1537 makes it visible in the RESULT too.
    _executed_path = "round_robin_fallback"

    # Try SK native AgentGroupChat first
    try:
        _chat_constructed = (
            False  # CD #1534: distinguish construction vs invoke failure
        )
        from semantic_kernel.agents.group_chat.agent_group_chat import (
            AgentGroupChat,
        )

        # RA-6 #1051: Wire DelegatingSelectionStrategy so PM designation
        # (state._next_agent_designated set via designate_next_agent) is actually
        # consumed by the SK-native AgentGroupChat. Without this, the PM "directs
        # into the void" — designation is written but never read on this path.
        selection = None
        if state is not None and hasattr(state, "consume_next_agent_designation"):
            try:
                from argumentation_analysis.core.strategies import (
                    DelegatingSelectionStrategy,
                )

                selection = DelegatingSelectionStrategy(agents=agents, state=state)
            except (ImportError, TypeError, ValueError):
                logger.warning(
                    "DelegatingSelectionStrategy unavailable, using SK default selection"
                )

        # CD #1534 (anti-#1019): a failure on the AgentGroupChat path must be
        # VISIBLE, never silent. Pre-CD, a construction failure logged WARNING
        # and silently delivered round-robin — the mode advertised AgentGroupChat
        # and shipped something else (the #1019 "fake success" failure).
        # _chat_constructed distinguishes a construction failure (ERROR — the mode
        # is fundamentally broken) from a runtime invoke error (WARNING — mid-
        # execution degrade); both fall back to round-robin so a transient error
        # does not abort the phase. A hard raise on construction failure was
        # considered but rejected: it breaks the merged C1 contract
        # (test_deadline_in_past_breaks_before_first_turn injects a raising
        # AgentGroupChat to force round-robin) — migrating it is scope-creep
        # beyond CD #1534. ERROR (not WARNING) makes a construction regression
        # surface in log monitoring; that is the "loud" DoD #3 requires.
        chat = AgentGroupChat(
            agents=agents,
            selection_strategy=selection,
        )
        _chat_constructed = True
        # Add initial prompt to the group chat
        await chat.add_chat_message(
            chat_history.messages[-1] if chat_history.messages else initial_prompt
        )
        turn = 0
        # CF #1538: baseline the growth fingerprint before the first group-chat
        # turn; each turn's delta is measured against the previous turn's state
        # (mirrors the round-robin path's fp_before/fp_after pattern).
        fp_before_tour = _get_growth_fingerprint(state)
        # #1760 voie 2: baseline the unresolved-designation markers before the
        # first turn, and remember the default speaker (the first agent of the
        # room) — that is who an absorbed designation falls back to.
        unresolved_before_turn = len(_unresolved_designation_markers(state))
        default_speaker_name = getattr(agents[0], "name", None) if agents else None
        absorption_re_prompts = 0
        # CB #1528 item 5: bound EACH __anext__ of the invocation to the
        # remaining budget. A function-calling agent chains ~12 LLM round-trips
        # inside a single chat.invoke() before yielding (measured R716/R717) —
        # so the first __anext__ can blow the whole budget and every inter-turn
        # guard above (item 3/4) is powerless inside a turn that never ends.
        # _bounded_invoke wraps the generator: on timeout it stops cleanly,
        # preserving the populated `state` (plugins wrote to it during the
        # aborted invocation) as the partial verdict. See its docstring for why
        # this is not the "killed mid-flight" the WallClockBudget rejects.
        async for response in _bounded_invoke(
            chat.invoke(), deadline, phase_name, "group-chat path"
        ):
            _bump_sk_budget()
            turn += 1
            msg_entry = {
                "phase": phase_name,
                "turn": turn,
                "agent": getattr(response, "name", getattr(response, "role", "?")),
                "content": str(getattr(response, "content", response)),
            }
            messages.append(msg_entry)
            logger.info(f"  [{phase_name}] Turn {turn}: {msg_entry['agent']}")

            # CONV-C #1334 §7.3: close the open DesignationRecord when its
            # designated agent returns (no-op if the PM spoke or no record is
            # open). Pairs each motivated designation with the state delta it
            # produced, without a new measurement path.
            _backfill_designation_if_present(state, msg_entry["agent"])

            # #1760 voie 2: if this turn opened with an absorbed designation
            # (fresh marker recorded by the selection strategy, whose fallback
            # speaker then took the floor), hand the floor BACK to the PM with
            # the present roster. Same mechanism as the growth re-prompt below
            # (direct agent.invoke on a deep-copied history). Capped per phase;
            # a marker that is not fresh must not re-fire.
            if absorption_reprompt_limit is not None:
                fresh = _fresh_absorbed_designation(state, unresolved_before_turn)
                if (
                    fresh is not None
                    and msg_entry["agent"] == default_speaker_name
                    and absorption_re_prompts < absorption_reprompt_limit
                ):
                    if deadline is not None and time.time() >= deadline:
                        logger.info(
                            f"  [{phase_name}] Wall-clock deadline atteinte "
                            f"avant l'absorption re-prompt — annulé."
                        )
                    else:
                        feedback = _absorption_feedback(
                            str(fresh.get("requested_agent", "?")),
                            [a.name for a in agents],
                        )
                        absorbing_agent = _find_agent_by_name(
                            agents, str(msg_entry["agent"])
                        )
                        if absorbing_agent is not None:
                            abs_history = chat.history.model_copy(deep=True)
                            abs_history.add_user_message(feedback)
                            abs_content = ""
                            _bump_sk_budget()
                            try:
                                async for abs_response in absorbing_agent.invoke(
                                    abs_history  # type: ignore[arg-type]
                                ):
                                    if hasattr(abs_response, "content"):
                                        abs_content += str(abs_response.content)
                                    elif hasattr(abs_response, "value"):
                                        abs_content += str(abs_response.value)
                                    else:
                                        abs_content += str(abs_response)
                            except Exception as abs_exc:
                                logger.warning(
                                    f"  [{phase_name}] absorption re-prompt failed "
                                    f"({type(abs_exc).__name__}: {abs_exc}); "
                                    f"skipping remaining absorption re-prompts "
                                    f"for this phase."
                                )
                                absorption_re_prompts = absorption_reprompt_limit
                            if abs_content:
                                messages.append(
                                    {
                                        "phase": phase_name,
                                        "turn": turn,
                                        "agent": msg_entry["agent"],
                                        "content": (
                                            abs_content[:500]
                                            if abs_content
                                            else "(empty)"
                                        ),
                                        "type": "absorption_reprompt",
                                        "requested_agent": fresh.get("requested_agent"),
                                        "path": "agent_group_chat",
                                    }
                                )
                            absorption_re_prompts += 1
                unresolved_before_turn = len(_unresolved_designation_markers(state))

            # Convergence check
            if _check_convergence(state, phase_name, messages):
                break
            if turn >= max_turns:
                break

            # C1 #1500: wall-clock deadline — exit cleanly between turns so the
            # partial state accumulated so far is preserved as the verdict
            # (anti-#1019: real bounded verdict, not a killed coroutine).
            if deadline is not None and time.time() >= deadline:
                logger.info(
                    f"  [{phase_name}] Wall-clock deadline atteint au tour "
                    f"{turn} — sortie propre (verdict partiel)."
                )
                break

            # CF #1538: growth validation on the AgentGroupChat path. CD #1534
            # removed the previous block because it used chat.add_chat_message()
            # + a nested chat.invoke() — both forbidden while AgentChat._is_active
            # is set (agent_chat.py:41-46, "Unable to proceed while another agent
            # is active."). CF #1538 re-establishes the validation by invoking
            # the SPEAKING AGENT directly via agent.invoke(), which is a
            # ChatCompletionAgent method and never touches AgentChat._is_active
            # (the flag lives on the chat, not the agent — verified firsthand).
            # The group-chat's own history is NOT mutated: a deep copy
            # (chat.history.model_copy(deep=True)) + the re-prompt feedback is
            # passed, so the selection/termination strategies read an undisturbed
            # history. Mirrors the round-robin enable_growth_validation block,
            # including the #609 reprompt_extractor trace. Placed after the
            # convergence/max_turns/deadline breaks so a turn that is already
            # exiting does not spend re-prompt budget.
            fp_after = _get_growth_fingerprint(state)
            if enable_growth_validation and not _validate_state_growth(
                fp_before_tour, fp_after, phase_name
            ):
                speaking_agent = _find_agent_by_name(agents, msg_entry["agent"])
                if speaking_agent is not None:
                    for rp in range(growth_re_prompt_limit):
                        # CB #1528 item 4: a re-prompt is a fresh LLM invocation
                        # and the turn's first agent.invoke may have consumed the
                        # whole budget already. Re-check the deadline BEFORE each
                        # re-prompt (the entry-of-phase check at L1896 only guards
                        # entering the phase; the group-chat path is the live one
                        # since CD #1534, so this is an active post-cap LLM site).
                        # The intra-invocation case (a single invoke that never
                        # yields) is item 5, not item 4 — this guard catches the
                        # inter-re-prompt case.
                        if deadline is not None and time.time() >= deadline:
                            logger.info(
                                f"  [{phase_name}] Wall-clock deadline atteinte "
                                f"avant le growth re-prompt {rp + 1}/"
                                f"{growth_re_prompt_limit} (group-chat path) ; "
                                f"re-prompts restants annulés."
                            )
                            break
                        logger.info(
                            f"  [{phase_name}] Growth re-prompt {rp + 1}/"
                            f"{growth_re_prompt_limit} (group-chat path)"
                        )
                        # Deep copy: isolate the group-chat history so neither
                        # the feedback nor the agent response mutates it
                        # (chat.add_chat_message is forbidden here, and a direct
                        # mutation would desync selection/termination).
                        re_history = chat.history.model_copy(deep=True)
                        re_history.add_user_message(_RE_PROMPT_FEEDBACK)
                        rp_content = ""
                        _bump_sk_budget()
                        try:
                            async for rp_response in speaking_agent.invoke(re_history):
                                if hasattr(rp_response, "content"):
                                    chunk = str(rp_response.content)
                                elif hasattr(rp_response, "value"):
                                    chunk = str(rp_response.value)
                                else:
                                    chunk = str(rp_response)
                                rp_content += chunk
                        except Exception as rp_exc:
                            logger.warning(
                                f"  [{phase_name}] group-chat growth re-prompt "
                                f"failed ({type(rp_exc).__name__}: {rp_exc}); "
                                f"skipping remaining re-prompts for this turn."
                            )
                            break
                        if rp_content:
                            messages.append(
                                {
                                    "phase": phase_name,
                                    "turn": turn,
                                    "agent": speaking_agent.name,
                                    "content": (
                                        rp_content[:500] if rp_content else "(empty)"
                                    ),
                                    "re_prompt": rp + 1,
                                    "path": "agent_group_chat",
                                }
                            )
                        total_re_prompts += 1
                        fp_after = _get_growth_fingerprint(state)
                        if reprompt_extractor is not None:
                            rp_outcome = (
                                "ok"
                                if _validate_state_growth(
                                    fp_before_tour, fp_after, phase_name
                                )
                                else (
                                    "reran"
                                    if rp + 1 < growth_re_prompt_limit
                                    else "gave_up"
                                )
                            )
                            reprompt_extractor.record(
                                phase_name=phase_name,
                                turn=turn,
                                attempt_idx=rp + 1,
                                fingerprint_before=fp_before_tour,
                                fingerprint_after=fp_after,
                                outcome=rp_outcome,
                                agent_name=speaking_agent.name,
                            )
                        if _validate_state_growth(fp_before_tour, fp_after, phase_name):
                            break
            fp_before_tour = fp_after

        if total_re_prompts > 0:
            messages.append(
                {
                    "phase": phase_name,
                    "type": "growth_validation",
                    "re_prompt_count": total_re_prompts,
                }
            )

        # CE #1537: the AgentGroupChat path completed without raising — record
        # the real path at the source via the recorder (NOT in `messages`:
        # polluting the message list would break C1 contracts that count on its
        # exact length/content — test_deadline_in_past_breaks_before_first_turn).
        _executed_path = "agent_group_chat"
        if execution_path_recorder is not None:
            execution_path_recorder.append(_executed_path)
        return messages

    except ImportError:
        # SK not installed in this environment — round-robin is the legitimate
        # degraded path (not a masked failure). INFO, not WARNING.
        logger.info("SK AgentGroupChat not importable, using round-robin fallback")
    except Exception as e:
        # CD #1534 (anti-#1019): construction failure is LOUD (ERROR), runtime
        # invoke error is a degrade (WARNING); both fall back to round-robin so
        # a transient error does not abort the phase. See the pre-construction
        # comment above for the raise-vs-log rationale.
        if not _chat_constructed:
            logger.error(
                f"SK AgentGroupChat CONSTRUCTION failed ({type(e).__name__}: {e}); "
                f"falling back to round-robin but surfacing LOUD (anti-#1019, CD #1534)."
            )
        else:
            logger.warning(
                f"SK AgentGroupChat runtime error ({type(e).__name__}: {e}), "
                f"using round-robin fallback"
            )

    # Fallback: round-robin invocation with PM designation support
    # In SK 1.40, ChatCompletionAgent.invoke() returns an AsyncGenerator
    for turn in range(1, max_turns + 1):
        # C1 #1500: wall-clock deadline — check before invoking the next agent
        # so a bounded run exits cleanly between turns (partial state = verdict).
        if deadline is not None and time.time() >= deadline:
            logger.info(
                f"  [{phase_name}] Wall-clock deadline atteint avant tour "
                f"{turn} — sortie propre (verdict partiel)."
            )
            break

        agent = _select_next_agent(state, agents, turn)
        try:
            fp_before = _get_growth_fingerprint(state)
            content = ""
            # SK 1.40: invoke() is an async generator, iterate to collect messages
            # Bump budget BEFORE the loop: ChatCompletionAgent.invoke() may yield
            # multiple streaming chunks per call — we count 1 LLM call = 1 bump,
            # regardless of chunk count (NanoClaw concern #1).
            _bump_sk_budget()
            # CB #1528 item 5: same intra-invocation bound as the group-chat
            # path — a single agent.invoke() can also chain function-calling
            # round-trips and blow the budget inside one turn. The inter-turn
            # guard above (L2153) checks BEFORE the turn; this bounds the turn
            # itself. Re-prompt loops below are pre-guarded by item 4 (check
            # before each re-prompt) and kept out of scope here.
            async for response in _bounded_invoke(
                agent.invoke(chat_history), deadline, phase_name, "round-robin path"
            ):
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

            # CONV-C #1334 §7.3: close the open DesignationRecord when its
            # designated agent returns (mirrors the AgentGroupChat path).
            _backfill_designation_if_present(state, agent.name)

            # Convergence check after each turn
            if _check_convergence(state, phase_name, messages):
                break

            # Growth validation hook (round-robin path)
            if enable_growth_validation:
                fp_after = _get_growth_fingerprint(state)
                if not _validate_state_growth(fp_before, fp_after, phase_name):
                    for rp in range(growth_re_prompt_limit):
                        # CB #1528 item 4: same deadline guard as the group-chat
                        # re-prompt loop above (symmetric). The round-robin path's
                        # re-prompt is also a fresh LLM invocation that must not
                        # fire after the wall-clock budget is exhausted. Mirrors
                        # the entry-of-phase check (L1896) inside the loop.
                        if deadline is not None and time.time() >= deadline:
                            logger.info(
                                f"  [{phase_name}] Wall-clock deadline atteinte "
                                f"avant le growth re-prompt {rp + 1}/"
                                f"{growth_re_prompt_limit} (round-robin path) ; "
                                f"re-prompts restants annulés."
                            )
                            break
                        logger.info(
                            f"  [{phase_name}] Growth re-prompt {rp + 1}/{growth_re_prompt_limit}"
                        )
                        chat_history.add_user_message(_RE_PROMPT_FEEDBACK)
                        rp_content = ""
                        # Bump budget BEFORE the loop (per-call, not per-chunk).
                        _bump_sk_budget()
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
                                "content": (
                                    rp_content[:500] if rp_content else "(empty)"
                                ),
                                "re_prompt": rp + 1,
                            }
                        )
                        total_re_prompts += 1
                        fp_after = _get_growth_fingerprint(state)
                        # Record re-prompt trace (#609)
                        if reprompt_extractor is not None:
                            rp_outcome = (
                                "ok"
                                if _validate_state_growth(
                                    fp_before, fp_after, phase_name
                                )
                                else (
                                    "reran"
                                    if rp + 1 < growth_re_prompt_limit
                                    else "gave_up"
                                )
                            )
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

        except LLMBudgetExceeded:
            # Anti-theater (#1019): budget guard must STOP the phase, not just
            # log.  Re-raise so the caller (workflow executor) handles it as a
            # hard cap violation — same semantics as the pipeline path.
            raise

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
            {
                "phase": phase_name,
                "type": "growth_validation",
                "re_prompt_count": total_re_prompts,
            }
        )

    # CE #1537: round-robin path — reached because AgentGroupChat is unavailable
    # (ImportError) or raised (construction/runtime). _executed_path kept its
    # "round_robin_fallback" default. Record at the source via the recorder so
    # the harness can tell this apart from a genuine AgentGroupChat run.
    if execution_path_recorder is not None:
        execution_path_recorder.append(_executed_path)
    return messages


_UNUSABLE_FALLACY_NAMES = frozenset(
    {
        "Type Inconnu",
        "Type inconnu",
        "type inconnu",
        "TYPE INCONNU",
        "unknown",
        "Unknown",
        "Sophisme inconnu",
        "",
    }
)


def _is_usable_fallacy_type(name: str) -> bool:
    """Return False for empty, generic, or machine-generated fallacy type names (#655 Track KK)."""
    if not name or not name.strip():
        return False
    if name.strip() in _UNUSABLE_FALLACY_NAMES:
        return False
    if name.startswith("unknown_class_"):
        return False
    return True


def _extract_fallacy_type(fallacy_dict: Dict[str, Any]) -> str:
    """Extract the best available fallacy type name from a fallacy dict (#655 Track KK).

    Tries multiple key names in priority order, then validates via
    _is_usable_fallacy_type. Returns "" if no usable name found.
    """
    for key in ("fallacy_type", "type", "nom", "name", "name_fr"):
        val = fallacy_dict.get(key, "")
        if isinstance(val, str) and _is_usable_fallacy_type(val):
            return val.strip()
    return ""


async def _run_parent_harness_fallback(
    text: str,
    state: Any,
    selector_context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Invoke tier-3 parent harness on dense texts after Detection phase (#578, #600).

    Always fires on texts > 5000 chars to catch fallacies the single-pass
    InformalAgent may have missed. Falls back silently if unavailable.

    #655 Track KK: skips fallacies with unusable type names (Type Inconnu,
    unknown, empty) and adds a wide-net whole-text fusion pass after the
    per-argument pass to capture framing/tonal fallacies.
    """
    try:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_hierarchical_fallacy_per_argument,
            _invoke_hierarchical_fallacy,
        )
        from argumentation_analysis.orchestration.state_writers import (
            resolve_fallacy_target_arg_id,
        )

        context = {"_state_object": state}
        # Merge selector context from API (#920)
        if selector_context:
            context.update(selector_context)

        # --- Per-argument pass (existing) ---
        per_arg_result = await _invoke_hierarchical_fallacy_per_argument(text, context)
        fallacies = per_arg_result.get("fallacies", [])

        # --- Wide-net whole-text fusion pass (#655 Track KK) ---
        # Catch framing, tonal, or discourse-level fallacies that span
        # multiple arguments and are invisible in per-argument extraction.
        whole_text_fallacies: List[Dict[str, Any]] = []
        if len(text) > 500:
            try:
                whole_result = await _invoke_hierarchical_fallacy(text, context)
                whole_text_fallacies = whole_result.get("fallacies", [])
            except Exception as e:
                logger.debug("Wide-net whole-text pass failed: %s", e)

        # Deduplicate whole-text findings against per-argument results
        per_arg_signatures: set = set()
        for f in fallacies:
            if isinstance(f, dict):
                sig = (
                    str(f.get("taxonomy_pk") or f.get("fallacy_type") or ""),
                    str(f.get("source_arg_id") or ""),
                )
                per_arg_signatures.add(sig)

        extra_count = 0
        for wf in whole_text_fallacies:
            if not isinstance(wf, dict):
                continue
            sig = (
                str(wf.get("taxonomy_pk") or wf.get("fallacy_type") or ""),
                "",
            )
            if sig not in per_arg_signatures:
                wf["source_arg_id"] = "whole_text"
                wf["wide_net"] = True
                fallacies.append(wf)
                extra_count += 1

        if extra_count:
            logger.info(
                "Wide-net whole-text pass: %d additional fallacies", extra_count
            )

        if not fallacies:
            logger.info("Parent harness: no additional fallacies found")
            return None

        # Register fallacies into state — skip unusable type names (#655 Track KK).
        added = 0
        skipped_unusable = 0
        for f in fallacies:
            if not isinstance(f, dict):
                continue
            fallacy_type = _extract_fallacy_type(f)
            if not fallacy_type:
                skipped_unusable += 1
                continue
            justification = (
                f.get("justification")
                or f.get("explanation")
                or f"Detected by parent harness (confidence: {f.get('confidence', 'N/A')})"
            )
            # #1633 site 3: resolve through the same ladder the pipeline lane
            # uses. This used to read ``source_arg_id or target_argument_id``,
            # which inverted the precedence AND skipped the membership guard —
            # so the sentinel ``"whole_text"`` stamped above was stored as a
            # target that matches no argument, and the two lanes disagreed on
            # the ASPIC survivor/defeated partition for identical input.
            target_arg_id = resolve_fallacy_target_arg_id(state, f)
            try:
                if hasattr(state, "add_fallacy"):
                    state.add_fallacy(
                        fallacy_type=fallacy_type,
                        justification=justification,
                        target_arg_id=target_arg_id,
                    )
                    added += 1
                elif hasattr(state, "add_identified_fallacy"):
                    state.add_identified_fallacy(
                        fallacy_type=fallacy_type,
                        justification=justification,
                    )
                    added += 1
            except Exception:
                pass

        logger.info(
            "Parent harness: %d fallacies found (%d whole-text extra), "
            "%d registered, %d skipped (unusable type)",
            len(fallacies),
            extra_count,
            added,
            skipped_unusable,
        )

        return {
            "phase": "Detection",
            "type": "parent_harness",
            "fallacies_found": len(fallacies),
            "fallacies_registered": added,
            "fallacies_skipped_unusable": skipped_unusable,
            "wide_net_extras": extra_count,
            "exploration_method": per_arg_result.get(
                "exploration_method", "per_argument_parallel"
            ),
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
    """Build a Dung AF from identified_arguments + fallacy targets (#564, rev #1668).

    Constructs attack relations from fallacies that target an argument and
    computes the grounded extension via the pure-Python DungFramework.
    Writes the result to state.dung_frameworks if non-trivial.

    #1668 — the counter-argument strategy branch was removed. The original
    #564 implementation filtered counter-arguments through a
    ``strategy in ("UNDERCUT", "REBUT", "REBUTTAL")`` gate on the assumption
    that the producer would emit that vocabulary. It never did: the counter-
    argument producer (``collaborative_debate``) emits free-text strategy
    names, disjoint from this triplet. Two independent real runs measured
    0/66 (pipeline voie) and 0/16 (conversational voie) matches — a structural
    property, not a draw. The branch produced zero attacks on every real run;
    the framework was in fact populated solely by the fallacy branch below.
    Removing the dead branch is behaviourally neutral (see
    ``test_dung_conversational`` post-removal coverage) and deletes no live
    capacity.
    """
    if not hasattr(state, "identified_arguments") or not state.identified_arguments:
        return None

    if not hasattr(state, "add_dung_framework"):
        return None

    # Collect argument IDs as Dung nodes
    arg_ids = list(state.identified_arguments.keys())
    if len(arg_ids) < 2:
        return None

    # Build attack relations from fallacies targeting arguments.
    # #1668: the counter-argument strategy branch (the
    # ``strategy in ("UNDERCUT", "REBUT", "REBUTTAL")`` gate) previously lived
    # here — removed, see the function docstring for why.
    attacks = []

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
            {m for r in state.modal_analysis_results for m in r.get("modalities", [])}
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
        current_arg_id = f"arg_{i + 1}"
        for f in fallacies:
            if not isinstance(f, dict):
                continue
            target = f.get("target_argument_id", "")
            target_text = f.get("target_argument", "")
            if target and target == current_arg_id:
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
        current_arg_id = f"arg_{i + 1}"
        for f in fallacies:
            if not isinstance(f, dict):
                continue
            target = f.get("target_argument_id", "")
            target_text = f.get("target_argument", "")
            if (target and target == current_arg_id) or (
                target_text and target_text.lower()[:30] in desc.lower()
            ):
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

    #1646 incr 3: also computes the axis's singular insight — the **minimal
    retraction** (smallest set of beliefs whose removal restores consistency) —
    JVM-free via PySAT, and carries it through ``minimal_retraction`` so the
    Acte III reader can NAME it. The pipeline producer carries the same insight
    via ``_invoke_belief_revision``; the two producers are **mode-exclusive**
    (``workflow_name="conversational"`` returns from ``run_conversational_analysis``
    before pipeline capabilities run, and vice-versa), so BOTH must compute it or
    the insight dies in whichever mode the run uses. Guarded against the
    ``logic/__init__`` jpype cascade (#1697): on ImportError the insight degrades
    to cardinality -1 (honest — the reader stays mute), the contraction is
    unaffected. Mirrors the pipeline wiring in ``_invoke_belief_revision``.
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
    original_beliefs = [
        bdata.get("name", "")
        for bdata in jtms_beliefs.values()
        if bdata.get("valid", False)
    ]
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

    # #1646: minimal-retraction insight, JVM-free. A targeted belief is negated
    # (the fallacy undermines its tenability) — build_belief_base adds the
    # negation clause, minimal_retractions isolates the smallest set to give up.
    # ``negated_indices`` = beliefs the fallacy loop removed from ``revised``.
    negated_indices = [i for i, b in enumerate(original_beliefs) if b not in revised]
    minimal_retraction: Optional[Dict[str, Any]] = None
    try:
        from argumentation_analysis.agents.core.logic.belief_revision_insight import (
            build_belief_base,
            minimal_retractions,
        )

        base, names = build_belief_base(original_beliefs, negated_indices)
        card, options = minimal_retractions(base)
        named_options = [[names[i] for i in opt] for opt in options]
        touched = len({i for opt in options for i in opt})
        minimal_retraction = {
            "cardinality": card,
            "options": named_options,
            "base_size": len(base),
            "touched_count": touched,
            "degraded": False,
        }
    except ImportError:
        # logic/__init__ jpype cascade (#1697) OR missing pysat: the insight
        # degrades honestly (cardinality -1 → reader mute), the phase continues.
        minimal_retraction = {
            "cardinality": -1,
            "options": [],
            "base_size": 0,
            "touched_count": 0,
            "degraded": True,
        }

    try:
        state.add_belief_revision_result(
            method="fallacy_contraction",
            original=original_beliefs,
            revised=revised,
            minimal_retraction=minimal_retraction,
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
