#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent de logique du premier ordre (FOL) - Alternative authentique à Modal Logic.

Cet agent utilise TweetyProject pour traiter la logique du premier ordre,
évitant les échecs fréquents de l'agent Modal Logic tout en garantissant
une analyse formelle authentique sans mocks.

Fonctionnalités :
- Analyse FOL complète avec TweetyProject
- Conversion automatique de texte naturel vers formules FOL
- Validation de cohérence logique
- Inférence et déduction
- Support complet sans mocks
"""

import logging
import asyncio
import inspect
from typing import Dict, List, Any, Iterable, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from pydantic import PrivateAttr

# Mock éliminé en Phase 2 - utilisation d'objets réels uniquement

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

# PURGE PHASE 3A: ChatCompletionAgent n'existe pas dans SK 0.9.6b1.
# Utiliser la classe Agent de base définie dans cluedo_extended_orchestrator ou une définition locale.
# from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import (
    ChatMessageContent as OriginalChatMessageContent,
)  # Renommer pour éviter conflit
from pydantic import Field

# Import de la classe Agent de base depuis l'orchestrateur principal
# et définition locale de ChatCompletionAgent héritant de celle-ci.
# from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatMessageContent

from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent

# Import BeliefSet avec fallback
try:
    from argumentation_analysis.agents.core.logic.belief_set import (
        BeliefSet,
        FirstOrderBeliefSet,
    )
except ImportError:
    # Fallback pour BeliefSet si non disponible
    class BeliefSet:
        def __init__(self):
            self.beliefs = []

        def add_belief(self, content):
            # Créer un objet belief simple au lieu d'un Mock
            class SimpleBelief:
                def __init__(self, content):
                    self.content = content

                def __str__(self):
                    return str(self.content)

                def __repr__(self):
                    return f"Belief({self.content})"

            self.beliefs.append(SimpleBelief(content))


# #2432 : import direct. ``tweety_bridge`` n'importe au niveau module que la
# stdlib et un jpype optionnel (sous try, #1697) : il ne lève pas ImportError.
# Le repli qui le remplaçait n'était donc jamais atteint, et il fabriquait des
# verdicts (cohérence ``True``, « Inférence simulée pour test »). Garde :
# ``tests/agents/core/logic/test_1773_verdict_reading.py``.
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

logger = logging.getLogger(__name__)


@dataclass
class FOLAnalysisResult:
    """Résultat d'analyse logique FOL."""

    formulas: List[str] = field(default_factory=list)
    interpretations: List[Dict[str, Any]] = field(default_factory=list)
    # #2447 — the Tweety verdict: ``True``/``False`` only when a solver
    # decided, ``None`` when no check ran or the solver did not decide.
    # ``consistency_message`` says which, and why.
    consistency_check: Optional[bool] = None
    consistency_message: str = ""
    inferences: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    reasoning_steps: List[str] = field(default_factory=list)
    # #2441 — components whose setup failed, with their cause (e.g. the
    # Tweety bridge when the JVM is absent). Empty when setup was complete.
    setup_failures: Dict[str, str] = field(default_factory=dict)
    # #2447 — where ``formulas`` came from: "llm" (the conversion prompt) or
    # "heuristic" (``_basic_fol_conversion``: placeholder predicates P0, Q0…,
    # not a translation of the text). ``conversion_message`` says why the
    # heuristic ran.
    formulas_source: str = ""
    conversion_message: str = ""
    # #2447 — the model's answer to the ``analyze_fol`` step, as it gave it.
    # No solver computed any of it, so none of it is copied into
    # ``consistency_check``, ``inferences``, ``interpretations``,
    # ``validation_errors`` or ``confidence_score``.
    llm_assessment: Dict[str, Any] = field(default_factory=dict)


def _source_label(result: "FOLAnalysisResult") -> str:
    if result.formulas_source == "heuristic":
        return f"heuristique de substitution : {result.conversion_message}"
    return result.formulas_source or "source inconnue"


def _consistency_label(result: "FOLAnalysisResult") -> str:
    if result.consistency_check is None:
        return f"⚠️ Non vérifiée ({result.consistency_message or 'raison inconnue'})"
    return "✅ Cohérent" if result.consistency_check else "❌ Incohérent"


class BeliefSetBuilderPlugin:
    """
    Plugin for programmatically building FOL belief sets.

    Accumulates sort/predicate/constant/formula declarations,
    then builds a Tweety FolBeliefSet via create_belief_set_programmatically().
    """

    def __init__(self):
        self._sorts: Dict[str, List[str]] = {}  # sort_name -> [constants]
        self._predicates: Dict[str, List[str]] = {}  # pred_name -> [arg_sort_names]
        self._formulas: List[str] = []

    def reset(self):
        """Clear all accumulated declarations."""
        self._sorts.clear()
        self._predicates.clear()
        self._formulas.clear()

    def add_sort(self, sort_name: str):
        """Declare a sort (type/domain)."""
        if sort_name not in self._sorts:
            self._sorts[sort_name] = []

    def add_constant_to_sort(self, const_name: str, sort_name: str):
        """Add a constant to a sort."""
        if sort_name not in self._sorts:
            self._sorts[sort_name] = []
        if const_name not in self._sorts[sort_name]:
            self._sorts[sort_name].append(const_name)

    def add_predicate_schema(self, pred_name: str, arg_sorts: List[str]):
        """Declare a predicate with its argument sorts."""
        self._predicates[pred_name] = list(arg_sorts)

    def add_atomic_fact(self, pred_name: str, args: List[str]):
        """Add an atomic formula: pred(arg1, arg2, ...)."""
        args_str = ", ".join(args)
        self._formulas.append(f"{pred_name}({args_str})")

    def add_negated_atomic_fact(self, pred_name: str, args: List[str]):
        """Add a negated atomic formula: !pred(arg1, arg2, ...)."""
        args_str = ", ".join(args)
        self._formulas.append(f"!{pred_name}({args_str})")

    def add_universal_implication(
        self, antecedent_pred: str, consequent_pred: str, sort_name: str
    ):
        """Add forall X: (antecedent(X) => consequent(X))."""
        self._formulas.append(
            f"forall X: ({antecedent_pred}(X) => {consequent_pred}(X))"
        )

    def add_existential_conjunction(self, pred1: str, pred2: str, sort_name: str):
        """Add exists X: (pred1(X) && pred2(X))."""
        self._formulas.append(f"exists X: ({pred1}(X) && {pred2}(X))")

    def build_tweety_belief_set(self, tweety_bridge):
        """
        Build a Tweety FolBeliefSet from accumulated declarations.

        Args:
            tweety_bridge: TweetyBridge instance with fol_handler.

        Returns:
            Java FolBeliefSet object.
        """
        builder_data = {
            "_sorts": dict(self._sorts),
            "_predicates": dict(self._predicates),
            "_formulas": list(self._formulas),
        }
        belief_set, _signature = (
            tweety_bridge.fol_handler.create_belief_set_programmatically(builder_data)
        )
        return belief_set


class FOLLogicAgent(BaseLogicAgent):
    """
    Agent de logique du premier ordre utilisant TweetyProject.

    Conçu comme alternative fiable à ModalLogicAgent pour éviter
    les échecs fréquents tout en maintenant une analyse formelle authentique.
    """

    # Attributs privés Pydantic V2 pour éviter ValidationError
    _analysis_cache: Dict[str, "FOLAnalysisResult"] = PrivateAttr(default_factory=dict)
    _conversion_prompt: str = PrivateAttr(default="")
    _analysis_prompt: str = PrivateAttr(default="")
    # #2441 — set only by a setup that registered the plugin, so a failed
    # lazy setup in ``analyze()`` is retried on the next call.
    _components_initialized: bool = PrivateAttr(default=False)
    _setup_failures: Dict[str, str] = PrivateAttr(default_factory=dict)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "FOLLogicAgent",
        tweety_bridge: Optional[TweetyBridge] = None,
        service_id: Optional[str] = None,
    ):
        """
        Initialise l'agent FOL.

        Args:
            kernel: Noyau Semantic Kernel.
            agent_name: Nom de l'agent.
            tweety_bridge (Optional[TweetyBridge]): Instance de TweetyBridge pré-initialisée.
            service_id (Optional[str]): ID du service LLM à utiliser.
        """
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            logic_type_name="first_order",
            llm_service_id=service_id,
        )

        # Configuration spécifique FOL - Utilisation de PrivateAttr pour Pydantic V2
        self._tweety_bridge = tweety_bridge

        # Prompts spécialisés FOL - Utilisation de PrivateAttr
        self._conversion_prompt = self._create_fol_conversion_prompt()
        self._analysis_prompt = self._create_fol_analysis_prompt()

        logger.info(f"Agent {agent_name} initialisé avec logique FOL")

    def _create_fol_conversion_prompt(self) -> str:
        """Crée le prompt de conversion vers FOL (Tweety ASCII syntax)."""
        return """
Tu es un expert en logique du premier ordre (FOL). Convertis le texte naturel suivant en formules FOL valides.

IMPORTANT: Utilise la syntaxe ASCII compatible TweetyProject :
- Quantificateurs : forall X: (...) et exists X: (...)
- Connecteurs : && (et), || (ou), => (implique), ! (non), <=> (équivalent)
- Variables en MAJUSCULES : X, Y, Z
- Constantes en minuscules : socrate, marie
- Prédicats avec majuscule initiale : Homme(X), Mortel(X)

EXEMPLE :
Texte: "Tous les hommes sont mortels. Socrate est un homme."
FOL: forall X: (Homme(X) => Mortel(X))
     Homme(socrate)

ANALYSE LE TEXTE SUIVANT :
{{$text}}

RÉPONDS EN FORMAT JSON :
{
    "formulas": ["forall X: (Homme(X) => Mortel(X))", "Homme(socrate)"],
    "predicates": {"Homme": "est un homme", "Mortel": "est mortel"},
    "variables": {"X": "thing"},
    "reasoning": "explication de la conversion"
}
"""

    def _create_fol_analysis_prompt(self) -> str:
        """Crée le prompt d'analyse FOL."""
        return """
Tu es un expert en analyse logique FOL. Analyse les formules suivantes pour :

1. COHÉRENCE LOGIQUE : Les formules sont-elles consistantes ?
2. INFÉRENCES POSSIBLES : Quelles conclusions peut-on tirer ?
3. VALIDATION : Y a-t-il des erreurs logiques ?
4. INTERPRÉTATIONS : Quels modèles satisfont ces formules ?

FORMULES FOL :
{{$formulas}}

CONTEXTE :
{{$context}}

RÉPONDS EN FORMAT JSON :
{
    "consistency": true/false,
    "inferences": ["conclusion1", "conclusion2", ...],
    "interpretations": [{"description": "...", "model": {...}}, ...],
    "errors": ["erreur1", "erreur2", ...],
    "confidence": 0.95,
    "reasoning_steps": ["étape1", "étape2", ...]
}
"""

    # #2360 — l'ancienne def ``async def setup_agent_components(self) -> bool``
    # (morte par écrasement avant la def vivante de fin de fichier) est
    # supprimée : son corps (pont Tweety + fonctions sémantiques) était déjà
    # un sous-ensemble de la survivante, et son retour booléen n'était lu
    # nulle part (l'appel interne d'``analyze`` ignore la valeur de retour).

    def _register_fol_semantic_functions(self):
        """Enregistre les fonctions sémantiques spécifiques FOL."""
        if not self.kernel:
            logger.warning("⚠️ Pas de kernel - fonctions sémantiques non enregistrées")
            return

        # #2360 — ``Kernel.create_function_from_prompt`` n'existe pas sur le
        # kernel Semantic Kernel de ce dépôt (AttributeError avalée par le
        # try/except de la def vivante : les fonctions ne s'enregistraient
        # JAMAIS, même sur le chemin awaited). ``add_function`` est la forme
        # qui fonctionne (pm_agent, sherlock_enquete_agent).
        self.kernel.add_function(
            function_name="convert_to_fol",
            plugin_name="fol_logic",
            prompt=self._conversion_prompt,
            description="Convertit du texte naturel en formules FOL",
        )

        self.kernel.add_function(
            function_name="analyze_fol",
            plugin_name="fol_logic",
            prompt=self._analysis_prompt,
            description="Analyse la cohérence et les inférences FOL",
        )

        logger.info("✅ Fonctions sémantiques FOL enregistrées")

    async def analyze(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> FOLAnalysisResult:
        """
        Effectue une analyse logique FOL complète du texte.

        Args:
            text: Texte à analyser
            context: Contexte d'analyse optionnel

        Returns:
            FOLAnalysisResult: Résultats de l'analyse FOL
        """
        logger.info(f"🔍 Début analyse FOL pour texte de {len(text)} caractères")

        try:
            # 0. Lazy setup: register semantic functions if not done yet.
            # A failure raises into the except below, which names it in the
            # result; the flag stays False, so the next call retries (#2441).
            if not self._components_initialized:
                self.setup_agent_components()

            # 1. Vérification du cache
            cache_key = self._generate_cache_key(text, context)
            if cache_key in self._analysis_cache:
                logger.info("📋 Résultat FOL trouvé en cache")
                return self._analysis_cache[cache_key]

            # 2. Conversion texte → formules FOL
            logger.info("🔄 Conversion texte vers formules FOL...")
            formulas, heuristic_reason = await self._convert_to_fol(text, context)

            # 3. Analyse logique avec Tweety
            if heuristic_reason is None:
                logger.info("🧮 Analyse logique avec TweetyProject...")
                analysis_result = await self._analyze_with_tweety(formulas, context)
                analysis_result.formulas_source = "llm"
            else:
                # #2447: the heuristic's formulas are placeholders (P0(a),
                # forall X: (P0(X) => Q0(X))…). A solver verdict on them
                # says nothing about the text, so none is computed.
                analysis_result = FOLAnalysisResult(
                    formulas=formulas,
                    formulas_source="heuristic",
                    conversion_message=heuristic_reason,
                    consistency_message=(
                        "Cohérence NON VÉRIFIÉE : formules heuristiques de "
                        "substitution, pas une traduction du texte "
                        f"({heuristic_reason})."
                    ),
                    confidence_score=0.1,
                )

            # 4. Validation et enrichissement
            logger.info("✅ Validation et enrichissement des résultats...")
            final_result = await self._enrich_analysis(analysis_result, text, context)

            final_result.setup_failures = self.setup_failures

            # 5. Mise en cache
            self._analysis_cache[cache_key] = final_result

            logger.info(
                f"✅ Analyse FOL terminée - Confiance: {final_result.confidence_score:.2f}"
            )
            return final_result

        except Exception as e:
            logger.error(f"❌ Erreur analyse FOL: {e}")
            return FOLAnalysisResult(
                validation_errors=[f"Erreur d'analyse: {str(e)}"],
                confidence_score=0.0,
                setup_failures=self.setup_failures,
            )

    async def _convert_to_fol(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], Optional[str]]:
        """
        Convertit le texte naturel en formules FOL.

        Args:
            text: Texte à convertir
            context: Contexte optionnel

        Returns:
            Tuple[List[str], Optional[str]]: les formules, et ``None`` quand le
            LLM les a produites. Sinon, la raison pour laquelle le convertisseur
            heuristique a pris le relais (#2447).
        """
        try:
            if self.kernel and self.kernel.services:
                # Utilisation du LLM pour conversion intelligente
                conversion_args = {
                    "text": text,
                    "context": str(context) if context else "Aucun contexte",
                }

                result = await self.kernel.invoke(
                    function_name="convert_to_fol",
                    plugin_name="fol_logic",
                    arguments=KernelArguments(**conversion_args),
                )

                # Parsing du JSON résultat
                import json

                parsed = json.loads(str(result))
                formulas = parsed.get("formulas", [])

                # Convert any Unicode FOL to ASCII for Tweety compatibility
                formulas = [self.unicode_to_ascii_fol(f) for f in formulas]

                logger.info(f"✅ Conversion LLM: {len(formulas)} formules générées")
                return formulas, None

            else:
                # Fallback : conversion basique par règles
                logger.warning("⚠️ Pas de LLM - conversion par règles basiques")
                return self._basic_fol_conversion(text), "aucun service LLM"

        except Exception as e:
            logger.error(f"❌ Erreur conversion FOL: {e}")
            return self._basic_fol_conversion(text), (
                f"la conversion LLM a levé {type(e).__name__}: {e}"
            )

    @staticmethod
    def unicode_to_ascii_fol(formula: str) -> str:
        """
        Convert Unicode FOL symbols to Tweety-compatible ASCII syntax.

        Tweety's FolParser only accepts ASCII operators:
        - forall/exists (NOT ∀/∃)
        - &&, ||, =>, !, <=>, ^^  (NOT ∧, ∨, →, ¬, ↔)

        See issue #23 and CoursIA tweety_fol_bnf.md for reference.
        """
        replacements = {
            "∀": "forall ",
            "∃": "exists ",
            "∧": "&&",
            "∨": "||",
            "→": "=>",
            "¬": "!",
            "↔": "<=>",
            "⊥": "+",  # Tweety contradiction
            "⊤": "-",  # Tweety tautology
        }
        for unicode_char, ascii_equiv in replacements.items():
            formula = formula.replace(unicode_char, ascii_equiv)
        return formula

    def _basic_fol_conversion(self, text: str) -> List[str]:
        """
        Conversion FOL basique par règles heuristiques.

        Produces Tweety-compatible ASCII FOL with sort/type declarations.

        Args:
            text: Texte à convertir

        Returns:
            List[str]: Formules FOL simples (Tweety ASCII syntax)
        """
        formulas = []
        sentences = text.split(".")

        # Collect predicates and constants for sort/type declarations
        predicates = set()
        predicate_count = 0

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Règles de conversion simples — ASCII syntax for Tweety
            if "tous" in sentence.lower() or "chaque" in sentence.lower():
                predicates.add(f"P{i}")
                predicates.add(f"Q{i}")
                formulas.append(f"forall X: (P{i}(X) => Q{i}(X))")
                predicate_count += 1
            elif "il existe" in sentence.lower() or "certains" in sentence.lower():
                predicates.add(f"P{i}")
                predicates.add(f"Q{i}")
                formulas.append(f"exists X: (P{i}(X) && Q{i}(X))")
                predicate_count += 1
            elif "si" in sentence.lower() and "alors" in sentence.lower():
                predicates.add(f"P{i}")
                predicates.add(f"Q{i}")
                formulas.append(f"forall X: (P{i}(X) => Q{i}(X))")
                predicate_count += 1
            else:
                predicates.add(f"P{i}")
                formulas.append(f"P{i}(a)")

        # Prepend Tweety sort/type declarations (required by FolParser BNF)
        declarations = []
        declarations.append("thing = {a}")  # Default sort with constant
        for pred in sorted(predicates):
            declarations.append(f"type({pred}(thing))")

        # Combine declarations + empty line + formulas (Tweety BNF: SORTSDEC DECLAR FORMULAS)
        return declarations + [""] + formulas

    @staticmethod
    def extract_fol_metadata(
        formulas: List[str], domain: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        """Extract sorts, predicates, and constants from FOL formulas.

        Parses LLM-generated formulas to build a Tweety-compatible signature
        (sort declarations + constant assignments). This pre-declaration is
        required by Tweety's FolParser — without it, unknown constants cause
        parse failures (#348).

        Handles accented characters (e.g. estPrésident), numeric constants
        (e.g. arg1), and function symbols (e.g. f(x)) in addition to the
        standard CamelCase predicate patterns.

        ``domain`` names the declared constants of a larger belief set the
        formulas belong to. They join the ``thing`` sort, so a formula
        checked on its own is read over the set's individuals: a universal
        rule with no constant of its own gets a sort Tweety accepts instead
        of ``thing = {}`` (#2492). Each name must already be a legal
        constant, as the ``constants`` of a call on the whole set are.

        A set that names no individual at all, with no ``domain`` to lend
        one, gets one witness constant in its sort (#2495). Tweety refuses
        ``thing = {}``, so such a set was never decided under any solver. A
        FOL domain is never empty, so an unused constant adds no constraint:
        EProver, Prover9 and Mace4 decide the same set, and the in-JVM check
        puts the witness in its domain (#2494). ``constants`` stays the names
        the formulas and ``domain`` carry; the witness is only in the sort.

        Returns:
            Dict with keys: sorts (Dict[str, List[str]]), predicates (Dict[str, int]),
            constants (set), signature_lines (List[str]), constant_map and
            predicate_map (surface name -> declared name), and formulas: the
            input formulas renamed to the declared names. A belief set is
            ``signature_lines + [""] + formulas``; the input formulas with this
            signature do not parse as soon as one name was renamed (#2468).
        """
        import re

        from argumentation_analysis.agents.core.logic.modal_kb_identifier_normalizer import (
            ModalIdentifierNormalizer,
            fold_to_ascii,
        )

        predicates: Dict[str, int] = {}  # name -> arity
        constants: Set[str] = set()

        # Extended regex: handle accented chars, digits, and underscores in names.
        # Matches both predicate (CamelCase) and function (lowercase) applications.
        # Examples: EstHomme(x), est_president(x, y), P1(a, b), asserte(c1)
        for formula in formulas:
            for match in re.finditer(
                r"([A-Za-z_À-ÖØ-öø-ÿ][A-Za-z0-9_À-ÖØ-öø-ÿ]*)\(([^)]+)\)", formula
            ):
                pred_name = match.group(1)
                args_str = match.group(2)
                args = [a.strip() for a in args_str.split(",")]
                args = [a for a in args if a]
                arity = len(args)
                if not arity:
                    continue
                if pred_name not in predicates or predicates[pred_name] < arity:
                    predicates[pred_name] = arity
                for arg in args:
                    # Constant: starts with lowercase or digit (socrates, c1, 42).
                    # Uppercase-starting identifiers (X, Y, Z) are FOL variables;
                    # they are NOT declared in the Tweety signature (implicitly of
                    # sort `thing`). #1630 retired the collected-but-prod-unread
                    # `variables` set (#1019: a produced-but-never-read field is
                    # decided, not kept).
                    if not arg[0].isupper():
                        constants.add(arg)

        # Also scan for standalone lowercase identifiers not inside predicates
        # (e.g. in "forall X: (Est(X) => Mortel(X))", there are no standalone constants,
        #  but in "socrates && platon", socrates/platon are constants)
        for formula in formulas:
            # Remove already-recognized predicate applications to avoid false positives
            stripped = re.sub(
                r"[A-Za-z_À-ÖØ-öø-ÿ][A-Za-z0-9_À-ÖØ-öø-ÿ]*\([^)]*\)", "", formula
            )
            for match in re.finditer(r"\b([a-z_À-öø-ÿ][a-z0-9_À-öø-ÿ]*)\b", stripped):
                word = match.group(1)
                if word not in (
                    "forall",
                    "exists",
                    "and",
                    "or",
                    "not",
                    "true",
                    "false",
                ):
                    constants.add(word)

        # A predicate declaration must match ``[A-Za-z][A-Za-z0-9]*``: no
        # underscore (measured on the real JVM, #2468: ``A_Fait`` is refused).
        # The modal parser has the same rule, and its legaliser names these
        # predicates too: accents folded, separators dropped in PascalCase
        # (``A_Fait`` -> ``AFait``, ``Évalue`` -> ``Evalue``), a digit suffix on
        # a collision. The names already legal are reserved first, so a
        # generated name never merges two predicates.
        #
        # The sort's name is not a predicate name (#2516): Tweety's TPTP writes
        # the sort as the unary predicate ``thing``, so a predicate ``thing``
        # would be read as membership of the sort (EProver then decides
        # ``!thing(c)`` inconsistent). It gets a digit suffix.
        legal_predicates = {
            p
            for p in predicates
            if re.match(r"^[A-Za-z][A-Za-z0-9]*$", p) and p != "thing"
        }
        legaliser = ModalIdentifierNormalizer(reserved=legal_predicates | {"thing"})
        sanitized_predicates: Dict[str, int] = {}
        predicate_map: Dict[str, str] = {}
        for pred_name, arity in predicates.items():
            if pred_name in legal_predicates:
                base = pred_name
            elif pred_name == "thing":
                base, count = "thing2", 2
                while base in legal_predicates or base in sanitized_predicates:
                    count += 1
                    base = f"thing{count}"
            else:
                base = legaliser.legalize(pred_name)
            sanitized_predicates[base] = arity
            predicate_map[pred_name] = base
        # A constant is named neither like the sort nor like a predicate
        # (#2516): TPTP has one namespace for them, and EProver refuses a
        # name used with two arities.
        reserved_names = {"thing"} | set(sanitized_predicates)

        # Tweety constants (measured on the real JVM, #2468): a letter first,
        # then letters, digits or underscores (``_t_`` is refused; ``jean_paul``
        # and ``c_42`` are accepted). A constant the grammar accepts keeps its
        # name. The others are folded to ASCII (``été`` -> ``ete``), their other
        # characters become ``_``, and ``c_`` is prefixed when the first
        # character is no letter. Distinct surface forms that land on one name
        # (``jean-paul`` next to ``jean_paul``) get ``_v2``, ``_v3``... The
        # legal names are reserved first and the rest is taken in sorted order,
        # so no generated name shadows a real one and the map does not depend
        # on the set's iteration order.
        legal_constant = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
        constant_map: Dict[str, str] = {
            c: c
            for c in constants
            if legal_constant.match(c) and c not in reserved_names
        }
        sanitized_constants = set(constant_map.values())
        for c in sorted(constants - set(constant_map)):
            base = re.sub(r"[^A-Za-z0-9_]", "_", fold_to_ascii(c))
            if not re.match(r"[A-Za-z]", base):
                base = f"c_{base}"
            name, count = base, 1
            while name in sanitized_constants or name in reserved_names:
                count += 1
                name = f"{base}_v{count}"
            sanitized_constants.add(name)
            constant_map[c] = name

        if domain is not None:
            domain_names = set(domain)
            illegal = sorted(n for n in domain_names if not legal_constant.match(n))
            if illegal:
                raise ValueError(
                    f"domain names must be legal Tweety constants: {illegal}"
                )
            sanitized_constants |= domain_names

        # Build sort declarations from constants. Tweety refuses an empty
        # sort, and a FOL domain is never empty: a set without a constant
        # declares one witness, which no formula names (#2495).
        sorted_consts = sorted(sanitized_constants)
        if not sorted_consts:
            witness, count = "witness", 1
            while witness in predicates:
                count += 1
                witness = f"witness{count}"
            sorted_consts = [witness]
        sorts: Dict[str, List[str]] = {"thing": sorted_consts}
        signature_lines = [f"thing = {{{', '.join(sorted_consts)}}}"]
        for base, arity in sanitized_predicates.items():
            sort_args = ", ".join(["thing"] * arity)
            signature_lines.append(f"type({base}({sort_args}))")

        return {
            "sorts": sorts,
            "predicates": sanitized_predicates,
            "constants": sanitized_constants,
            "signature_lines": signature_lines,
            "constant_map": constant_map,
            "predicate_map": predicate_map,
            "formulas": FOLLogicAgent._rename_to_signature(
                formulas, predicate_map, constant_map
            ),
        }

    @staticmethod
    def _rename_to_signature(
        formulas: List[str],
        predicate_map: Dict[str, str],
        constant_map: Dict[str, str],
    ) -> List[str]:
        """Rewrite ``formulas`` with the declared names (#2468).

        A predicate is renamed where it is applied (``name(``), a constant where
        it stands alone. One pass over each formula: a name is never renamed
        twice, so ``jean-paul`` -> ``jean_paul_v2`` cannot be caught again by
        the rule for ``jean_paul``.
        """
        import re

        ident = "A-Za-z0-9_À-ÖØ-öø-ÿ"
        preds = sorted(
            (k for k, v in predicate_map.items() if k != v), key=len, reverse=True
        )
        consts = sorted(
            (k for k, v in constant_map.items() if k != v), key=len, reverse=True
        )
        alternatives = []
        if preds:
            alternatives.append(
                "(?P<pred>" + "|".join(map(re.escape, preds)) + r")(?=\()"
            )
        if consts:
            alternatives.append(
                "(?P<const>" + "|".join(map(re.escape, consts)) + f")(?![{ident}(])"
            )
        if not alternatives:
            return list(formulas)
        pattern = re.compile(f"(?<![{ident}])(?:" + "|".join(alternatives) + ")")

        def rename(match):
            if match.lastgroup == "pred":
                return predicate_map[match.group("pred")]
            return constant_map[match.group("const")]

        return [pattern.sub(rename, formula) for formula in formulas]

    @staticmethod
    def build_signature_prefixed_formulas(formulas: List[str]) -> List[str]:
        """Prepend signature declarations to formulas for Tweety parsing.

        Tweety's FolParser requires sort/type declarations before formulas.
        This method extracts metadata from formulas, generates declarations,
        and combines them with the formulas renamed to the declared names
        (#2468: the formulas used to go as written, so a name the signature
        had to rename was never declared).
        """
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        if not meta["constants"] and not meta["predicates"]:
            return formulas
        return meta["signature_lines"] + [""] + meta["formulas"]

    def _validate_fol_formula(self, formula: str) -> bool:
        """Validation basique syntaxe FOL (accepts both Unicode and ASCII)."""
        # Vérifications de base
        has_quantifier = any(q in formula for q in ["∀", "∃", "forall", "exists"])
        has_predicate = "(" in formula and ")" in formula
        balanced_parens = formula.count("(") == formula.count(")")

        # Variables libres (heuristique simple)
        return (has_quantifier or has_predicate) and balanced_parens

    async def _analyze_with_tweety(
        self, formulas: List[str], context: Optional[Dict[str, Any]] = None
    ) -> FOLAnalysisResult:
        """
        Analyse les formules FOL avec TweetyProject.

        Args:
            formulas: Formules FOL à analyser
            context: Contexte d'analyse

        Returns:
            FOLAnalysisResult: Résultats bruts de l'analyse
        """
        result = FOLAnalysisResult(formulas=formulas)

        bridge = getattr(self, "_tweety_bridge", None)
        if not bridge:
            logger.warning("⚠️ TweetyBridge non initialisé - analyse limitée")
            # #2447: no bridge, no check, so no verdict (it was ``True``).
            result.consistency_check = None
            result.consistency_message = (
                "Cohérence NON VÉRIFIÉE : aucun bridge Tweety "
                f"(setup_failures: {self.setup_failures or 'aucun'})."
            )
            result.confidence_score = 0.5
            return result

        try:
            # Test de cohérence — handle both sync and async bridges.
            # #2447: the conversion prompt asks for bare formulas, and the FOL
            # parser needs the sorts and predicates declared first. Without
            # them every LLM conversion failed to parse, so no verdict was
            # ever computed on this path.
            content_str = "\n".join(self.build_signature_prefixed_formulas(formulas))
            raw = bridge.check_consistency(content_str, "first_order")
            if inspect.isawaitable(raw):
                raw = await raw
            is_consistent = raw[0] if isinstance(raw, tuple) else raw
            result.consistency_check = is_consistent
            if isinstance(raw, tuple) and len(raw) > 1:
                result.consistency_message = str(raw[1])

            # Calcul d'inférences
            if is_consistent is None:
                # #2447: the solver did not decide. That is no inconsistency,
                # so it adds no "incohérentes" entry.
                if not result.consistency_message:
                    result.consistency_message = "Cohérence NON DÉCIDÉE par le solveur."
                result.confidence_score = 0.5
            elif is_consistent and hasattr(bridge, "derive_inferences"):
                raw_inf = bridge.derive_inferences(formulas)
                if inspect.isawaitable(raw_inf):
                    raw_inf = await raw_inf
                result.inferences = raw_inf
                result.confidence_score = 0.9
            elif is_consistent:
                result.confidence_score = 0.8
            else:
                result.validation_errors.append("Formules incohérentes détectées")
                result.confidence_score = 0.3

            # Génération d'interprétations
            if hasattr(bridge, "generate_models"):
                raw_models = bridge.generate_models(formulas)
                if inspect.isawaitable(raw_models):
                    raw_models = await raw_models
                result.interpretations = raw_models

        except Exception as e:
            logger.error(f"❌ Erreur analyse Tweety: {e}")
            result.validation_errors.append(f"Erreur Tweety: {str(e)}")
            if result.consistency_check is None:
                result.consistency_message = (
                    "Cohérence NON VÉRIFIÉE : le contrôle a levé "
                    f"{type(e).__name__}: {e}"
                )
            result.confidence_score = 0.1

        return result

    async def _enrich_analysis(
        self,
        result: FOLAnalysisResult,
        original_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> FOLAnalysisResult:
        """
        Enrichit l'analyse avec des informations supplémentaires.

        Args:
            result: Résultat d'analyse à enrichir
            original_text: Texte original
            context: Contexte d'analyse

        Returns:
            FOLAnalysisResult: Résultat enrichi
        """
        try:
            # Ajout d'étapes de raisonnement
            result.reasoning_steps = [
                f"Conversion de {len(original_text)} caractères en "
                f"{len(result.formulas)} formules FOL ({_source_label(result)})",
                f"Test de cohérence: {_consistency_label(result)}",
                f"Inférences trouvées: {len(result.inferences)}",
                f"Modèles générés: {len(result.interpretations)}",
            ]

            # Amélioration du score de confiance basé sur les résultats
            if (
                result.consistency_check
                and result.inferences
                and not result.validation_errors
            ):
                result.confidence_score = min(0.95, result.confidence_score + 0.1)
            elif result.validation_errors:
                result.confidence_score = max(0.1, result.confidence_score - 0.2)

            # Analyse LLM complémentaire si disponible
            if self.kernel and self.kernel.services:
                enhanced_analysis = await self._llm_enhanced_analysis(
                    result, original_text
                )
                if enhanced_analysis:
                    result = enhanced_analysis

        except Exception as e:
            logger.error(f"❌ Erreur enrichissement: {e}")
            result.validation_errors.append(f"Erreur enrichissement: {str(e)}")

        return result

    async def _llm_enhanced_analysis(
        self, result: FOLAnalysisResult, original_text: str
    ) -> Optional[FOLAnalysisResult]:
        """
        Améliore l'analyse avec le LLM.

        Args:
            result: Résultat à améliorer
            original_text: Texte original

        Returns:
            Optional[FOLAnalysisResult]: Résultat amélioré ou None
        """
        try:
            analysis_args = {
                "formulas": "\n".join(result.formulas),
                "context": original_text,
            }

            llm_result = await self.kernel.invoke(
                function_name="analyze_fol",
                plugin_name="fol_logic",
                arguments=KernelArguments(**analysis_args),
            )

            # Parsing et intégration des résultats LLM
            import json

            parsed = json.loads(str(llm_result))

            # #2447: nothing the model answers here was computed by a solver.
            # Its answer is kept as it came, in ``llm_assessment``, with one
            # labelled step. It writes none of the solver's fields: it used to
            # replace the verdict, add its inferences, interpretations and
            # errors unlabelled, and raise ``confidence_score`` to its own
            # self-rating (a ``max``).
            if not isinstance(parsed, dict):
                parsed = {"raw": parsed}
            result.llm_assessment = parsed
            result.reasoning_steps.append(
                "Avis du LLM (non vérifié par un solveur) : "
                f"cohérence={parsed.get('consistency', '?')}, "
                f"{len(parsed.get('inferences') or [])} inférence(s), "
                f"{len(parsed.get('errors') or [])} erreur(s) signalée(s)"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Erreur analyse LLM: {e}")
            return None

    def _generate_cache_key(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Génère une clé de cache pour l'analyse."""
        import hashlib

        content = text + str(context) if context else text
        return hashlib.md5(content.encode()).hexdigest()

    # ==================== PROPERTIES BACKWARD COMPATIBILITY ====================

    @property
    def analysis_cache(self) -> Dict[str, "FOLAnalysisResult"]:
        """Expose _analysis_cache for backward compatibility."""
        return self._analysis_cache

    @property
    def conversion_prompt(self) -> str:
        """Expose _conversion_prompt for backward compatibility."""
        return self._conversion_prompt

    @property
    def analysis_prompt(self) -> str:
        """Expose _analysis_prompt for backward compatibility."""
        return self._analysis_prompt

    @property
    def tweety_bridge(self):
        """Expose _tweety_bridge for programmatic belief set construction."""
        return self._tweety_bridge

    @property
    def setup_failures(self) -> Dict[str, str]:
        """Components whose last setup failed, with their cause (#2441).

        Empty when the last ``setup_agent_components`` set everything up.
        Only degradable components appear here (the Tweety bridge); a
        failure of the parent setup or of the plugin registration raises.
        """
        return dict(self._setup_failures)

    @property
    def _builder_plugin(self) -> "BeliefSetBuilderPlugin":
        """Lazy-initialized BeliefSetBuilderPlugin for programmatic FOL construction."""
        if (
            not hasattr(self, "_builder_plugin_instance")
            or self._builder_plugin_instance is None
        ):
            object.__setattr__(
                self, "_builder_plugin_instance", BeliefSetBuilderPlugin()
            )
        return self._builder_plugin_instance

    # ==================== IMPLÉMENTATION MÉTHODES ABSTRAITES ====================

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit les capacités de l'agent FOL."""
        return {
            "logic_type": "first_order",
            "syntax_support": ["forall", "exists", "=>", "&&", "||", "!", "<=>"],
            "predicates": True,
            "quantifiers": True,
            "tweety_integration": True,
            "analysis_features": [
                "consistency_checking",
                "inference_derivation",
                "model_generation",
                "syntax_validation",
            ],
        }

    def setup_agent_components(self, llm_service_id: Optional[str] = None) -> None:
        """Configure les composants de l'agent FOL.

        Contrat sync de ``BaseLogicAgent.setup_agent_components`` (agent_bases.py),
        partagé par les 8 autres agents : l'API web (``logic_service``) et les
        autres appelants génériques appellent cette méthode SANS ``await`` —
        l'unique def async (#2360) laissait la configuration en coroutine jamais
        attendue, silencieusement.

        #2441 — les trois étapes sont indépendantes et chacune a sa conduite
        d'échec. Un seul ``try`` les enveloppait : un échec du pont sautait
        l'enregistrement du plugin, qui n'a pas besoin du pont, et ce même
        ``try`` avait caché #2360 pendant des mois.

        1. Configuration parente : ses arguments viennent du code, elle lève.
        2. Pont Tweety : dépendance d'environnement (JVM, jars) dont l'agent
           peut se passer. Son échec se dégrade **par son nom** dans
           ``setup_failures`` (et dans ``FOLAnalysisResult.setup_failures``).
        3. Plugin ``fol_logic`` : un plugin absent est un défaut de
           configuration, l'échec lève. ``_components_initialized`` n'est
           posé qu'après cette étape.
        """
        if llm_service_id:
            super().setup_agent_components(llm_service_id)

        self._setup_failures.pop("tweety_bridge", None)
        if not getattr(self, "_tweety_bridge", None):
            try:
                self._tweety_bridge = TweetyBridge()
                logger.info("✅ TweetyBridge FOL configuré")
            except Exception as e:
                self._setup_failures["tweety_bridge"] = f"{type(e).__name__}: {e}"
                logger.warning(
                    f"⚠️ TweetyBridge FOL indisponible, analyse formelle "
                    f"dégradée: {self._setup_failures['tweety_bridge']}"
                )

        self._register_fol_semantic_functions()
        self._components_initialized = True

    async def text_to_belief_set(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BeliefSet], str]:
        """Convertit texte en ensemble de croyances FOL.

        #2447 item 5: the conversion is the LLM's (``_convert_to_fol``), and
        the belief set carries the sort and predicate declarations the parser
        needs. It used to be ``_basic_fol_conversion(text)`` directly: the LLM
        was never called, and placeholder formulas (``P0(a)``) were returned
        as the text's translation. When only the heuristic converter can run,
        its formulas translate nothing: no belief set is returned, and the
        status names why (``BaseLogicAgent`` reports a ``None`` belief set as
        a failed conversion).
        """
        # The ``fol_logic`` plugin is registered by the setup. ``analyze()``
        # runs it lazily, and so does this entry point: without it the
        # conversion cannot be invoked and only the heuristic would run.
        if not self._components_initialized:
            self.setup_agent_components()

        formulas, heuristic_reason = await self._convert_to_fol(text, context)
        if heuristic_reason is not None:
            return None, (
                "Conversion LLM impossible, aucune formule traduite du texte "
                f"({heuristic_reason})."
            )
        if not formulas:
            return None, "Conversion resulted in no formulas, likely invalid input."

        content_str = "\n".join(self.build_signature_prefixed_formulas(formulas))
        return (
            FirstOrderBeliefSet(content=content_str),
            f"Converted to {len(formulas)} FOL formulas (llm)",
        )

    async def generate_queries(
        self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Génère requêtes FOL pertinentes."""
        queries = []

        # Requêtes de cohérence
        queries.append("consistency_check")

        # Requêtes d'inférence basiques
        if "donc" in text.lower() or "alors" in text.lower():
            queries.append("derive_conclusions")

        if "tous" in text.lower() or "∀" in text or "forall" in text.lower():
            queries.append("universal_instances")

        if "il existe" in text.lower() or "∃" in text or "exists" in text.lower():
            queries.append("existential_witnesses")

        return queries

    async def execute_query(
        self, belief_set: BeliefSet, query: str
    ) -> Tuple[Optional[bool], str]:
        """Exécute requête sur ensemble de croyances.

        Supports both command queries ("consistency_check", "derive_conclusions")
        and formula-based queries (e.g., "Mortal(socrate)") for entailment checking.

        #2338, carried here from the retired adapter (#2432): the verdict is
        tri-state — ``True`` entailed, ``False`` refused, ``None`` not computed,
        with a message naming why. No path returns a verdict nothing computed.
        """
        try:
            bridge = getattr(self, "_tweety_bridge", None)

            if query == "consistency_check":
                return await self.is_consistent(belief_set)

            elif query == "derive_conclusions":
                # Dérivation d'inférences
                formulas = [
                    f.strip() for f in belief_set.content.split("\n") if f.strip()
                ]
                if bridge and hasattr(bridge, "derive_inferences"):
                    result = bridge.derive_inferences(formulas)
                    if inspect.isawaitable(result):
                        result = await result
                    return len(result) > 0, f"Inferences: {result}"
                # ``TweetyBridge`` exposes no inference derivation: the former
                # ``True, "Inferences simulated"`` claimed conclusions nobody
                # derived (#2432).
                return None, (
                    "Dérivation NON CALCULÉE (dégradation nommée) : le bridge "
                    "n'expose aucune dérivation d'inférences."
                )

            else:
                # Treat as a formula-based entailment query
                if bridge and hasattr(bridge, "fol_handler"):
                    java_obj = getattr(belief_set, "java_object", None)
                    if java_obj is not None:
                        raw = bridge.fol_handler.execute_fol_query(java_obj, query)
                    else:
                        raw = bridge.fol_handler.execute_fol_query(
                            belief_set.content, query
                        )
                    if inspect.isawaitable(raw):
                        raw = await raw
                    if isinstance(raw, tuple):
                        return raw[0], raw[1]
                    return raw, f"Query result: {raw}"
                elif bridge:
                    # Try execute_fol_query on bridge directly
                    raw = bridge.execute_fol_query(belief_set.content, query)
                    if inspect.isawaitable(raw):
                        raw = await raw
                    if isinstance(raw, tuple):
                        return raw[0], raw[1]
                    return raw, f"Query result: {raw}"
                else:
                    return None, f"No Tweety bridge available for query: {query}"

        except Exception as e:
            # A failure computes no verdict: ``False`` would read as a refusal
            # (#2338, #2432).
            return None, (
                "Verdict FOL NON CALCULÉ (dégradation nommée) : la requête a levé "
                f"{type(e).__name__}: {e}"
            )

    async def interpret_results(
        self,
        text: str,
        belief_set: BeliefSet,
        queries: List[str],
        results: List[Tuple[Optional[bool], str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Interprète résultats en langage naturel."""
        interpretation = []

        for query, (result, details) in zip(queries, results):
            if query == "consistency_check":
                if result is True:
                    interpretation.append(
                        "✅ L'argumentation est logiquement cohérente."
                    )
                elif result is False:
                    interpretation.append(
                        "❌ L'argumentation contient des contradictions."
                    )
                else:
                    interpretation.append("❓ Cohérence indéterminée.")

            elif query == "derive_conclusions":
                if result is True:
                    interpretation.append("✅ Des conclusions peuvent être dérivées.")
                elif result is False:
                    interpretation.append("⚠️ Aucune conclusion dérivable.")
                else:
                    interpretation.append("❓ Dérivation non calculée.")

            interpretation.append(f"   Détails: {details}")

        return "\n".join(interpretation)

    def validate_formula(self, formula: str) -> bool:
        """Valide syntaxe formule FOL."""
        return self._validate_fol_formula(formula)

    async def is_consistent(self, belief_set: BeliefSet) -> Tuple[Optional[bool], str]:
        """Vérifie cohérence ensemble de croyances.

        #1192: propagate degraded (``None``) verdicts from the FOL handler
        instead of masking them as ``True``. A missing reasoner is not a
        consistency claim (anti-theater #1019).
        """
        try:
            bridge = getattr(self, "_tweety_bridge", None)
            if bridge:
                # Prefer java_object if available (from programmatic construction)
                java_obj = getattr(belief_set, "java_object", None)
                if java_obj is not None and hasattr(bridge, "fol_handler"):
                    # Direct path: pass Java object to FOL handler
                    raw = bridge.fol_handler.check_consistency(java_obj)
                else:
                    # String path: TweetyBridge parses the content
                    raw = bridge.check_consistency(belief_set.content, "first_order")
                if inspect.isawaitable(raw):
                    raw = await raw
                if isinstance(raw, tuple):
                    return raw[0], f"Tweety consistency check: {raw[1]}"
                return raw, f"Tweety consistency check: {raw}"
            else:
                # No bridge → cannot reason about consistency. Degraded, not
                # "assumed consistent" (anti-theater #1019, #1192).
                return None, "Degraded: no Tweety bridge; no consistency verdict."

        except Exception as e:
            # A failure is no inconsistency claim (#2432).
            return None, (
                "Cohérence NON CALCULÉE (dégradation nommée) : le contrôle a levé "
                f"{type(e).__name__}: {e}"
            )

    async def get_response(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Obtient réponse de l'agent FOL."""
        try:
            result = await self.analyze(text, context)

            response = f"Analyse FOL:\n"
            response += f"Formules: {len(result.formulas)}\n"
            response += f"Cohérence: {_consistency_label(result)}\n"
            response += f"Confiance: {result.confidence_score:.2f}\n"

            if result.inferences:
                response += f"Inférences: {', '.join(result.inferences[:3])}\n"

            return response

        except Exception as e:
            return f"Erreur analyse FOL: {str(e)}"

    async def invoke_single(
        self, text: str, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> FOLAnalysisResult:
        """
        Exécute la logique principale de l'agent (analyse FOL) et retourne une réponse unique.
        Implémentation de la méthode abstraite de BaseAgent.
        """
        return await self.analyze(text, context)

    async def validate_argument(
        self, premises: List[str], conclusion: str, **kwargs
    ) -> bool:
        """
        Valide si une conclusion découle logiquement d'un ensemble de prémisses.

        L'argument est valide si {prémisses} ∪ {¬conclusion} est incohérent. Le
        bridge reçoit ce qu'il attend : une chaîne précédée de la signature que
        le parseur Tweety exige, la négation Tweety ``!``, et ``"first_order"``.

        #2447 : l'ancienne version passait une liste sans ``logic_type``,
        capturait l'erreur et rendait ``False`` (« invalide ») pour tout
        argument, et aussi sans bridge. Les prémisses viennent du code
        appelant : quand rien ne peut être vérifié, la méthode lève au lieu de
        rendre un verdict.

        Args:
            premises (List[str]): La liste des prémisses en format FOL.
            conclusion (str): La conclusion en format FOL.

        Returns:
            bool: True si le solveur a décidé l'argument valide, False s'il a
            trouvé les prémisses compatibles avec la négation de la conclusion.

        Raises:
            RuntimeError: aucun bridge Tweety, ou le solveur n'a pas décidé.
        """
        bridge = self._tweety_bridge
        if not bridge:
            raise RuntimeError(
                "validate_argument : aucun bridge Tweety, l'argument n'est pas "
                f"vérifié (setup_failures : {self.setup_failures or 'aucune'})."
            )

        formulas = list(premises) + [f"!({conclusion})"]
        belief_set = "\n".join(self.build_signature_prefixed_formulas(formulas))
        raw = bridge.check_consistency(belief_set, "first_order")
        if inspect.isawaitable(raw):
            raw = await raw
        is_consistent, message = raw
        if is_consistent is None:
            raise RuntimeError(
                f"validate_argument : le solveur n'a pas décidé ({message})."
            )
        return not is_consistent

    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé des analyses effectuées.

        Returns:
            Dict[str, Any]: Résumé statistique
        """
        total_analyses = len(self._analysis_cache)
        if total_analyses == 0:
            return {
                "total_analyses": 0,
                "avg_confidence": 0.0,
                "agent_type": "FOL_Logic",
                "tweety_enabled": self._tweety_bridge is not None,
            }

        avg_confidence = (
            sum(r.confidence_score for r in self._analysis_cache.values())
            / total_analyses
        )
        consistent_count = sum(
            1 for r in self._analysis_cache.values() if r.consistency_check
        )
        # #2447: the rate is over the analyses a solver decided; the others
        # are counted apart, not as "inconsistent".
        decided_count = sum(
            1 for r in self._analysis_cache.values() if r.consistency_check is not None
        )

        return {
            "total_analyses": total_analyses,
            "avg_confidence": avg_confidence,
            "consistency_rate": (
                consistent_count / decided_count if decided_count else None
            ),
            "consistency_undetermined": total_analyses - decided_count,
            "agent_type": "FOL_Logic",
            "tweety_enabled": self._tweety_bridge is not None,
        }

    def _create_belief_set_from_data(
        self, belief_set_data: Dict[str, Any]
    ) -> BeliefSet:
        """
        Reconstruit un `FirstOrderBeliefSet` à partir du dictionnaire que
        `_handle_translation_task` stocke (`{"logic_type", "content"}`).

        #2641 : cette méthode attendait une liste de formules, que rien ne lui
        passe ; le dictionnaire stocké donnait un ensemble vide.
        """
        return FirstOrderBeliefSet(content=belief_set_data.get("content", ""))


# ==================== FACTORY ET UTILITAIRES ====================


def create_fol_agent(
    kernel: Optional[Kernel] = None, agent_name: str = "FOLLogicAgent"
) -> FOLLogicAgent:
    """
    Factory pour créer un agent FOL configuré.

    Args:
        kernel: Noyau Semantic Kernel
        agent_name: Nom de l'agent

    Returns:
        FOLLogicAgent: Agent FOL prêt à l'emploi
    """
    agent = FOLLogicAgent(kernel=kernel, agent_name=agent_name)
    logger.info(f"Agent FOL cree: {agent_name}")
    return agent


async def test_fol_agent_basic():
    """Test basique de l'agent FOL."""
    agent = create_fol_agent()

    test_text = (
        "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
    )

    result = await agent.analyze(test_text)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_fol_agent_basic())
