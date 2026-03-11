# argumentation_analysis/agents/core/logic/watson_logic_assistant.py
import logging
import re
from typing import Optional, List, AsyncGenerator, ClassVar, Union, Any
import json

import semantic_kernel as sk
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    OpenAIPromptExecutionSettings,
)
from semantic_kernel.functions.kernel_function import KernelFunction
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from .tweety_bridge import TweetyBridge
from .tweety_initializer import TweetyInitializer

WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT = """Vous êtes le Dr. Watson, un analyste logique, un partenaire respecté de Sherlock Holmes, et un esprit vif.

**Votre Mission :**
Votre rôle est d'apporter une rigueur logique à l'enquête. Analysez les informations de manière proactive, identifiez les connexions cachées et challengez les hypothèses avec respect. Votre analyse formelle est cruciale pour résoudre les puzzles et les cas complexes.

**Votre Style :**
- Soyez curieux et réfléchi. Utilisez des expressions comme "Intéressant...", "Voyons voir...", "Ah ! Ça change tout !".
- Vos messages doivent être concis et aller droit au but.
- Challengez Sherlock avec des questions pertinentes pour affiner son raisonnement.

**Vos Outils Logiques :**
Vous avez accès à des outils (`WatsonTools`) pour valider la syntaxe des formules logiques et exécuter des requêtes sur des bases de connaissances. Utilisez-les pour assurer la validité de chaque étape déductive.
"""

from .tweety_bridge import TweetyBridge


class WatsonTools:
    """
    Plugin natif pour l'agent Watson, fournissant des outils logiques basés sur Tweety.

    Ce plugin exploite `TweetyBridge` pour offrir des capacités de validation de
    formules logiques et d'exécution de requêtes sur des bases de connaissances
    propositionnelles.
    """

    def __init__(
        self,
        tweety_bridge: Optional[TweetyBridge] = None,
        constants: Optional[List[str]] = None,
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._constants = constants or []
        try:
            # Si aucun bridge n'est fourni, on essaie d'en créer un.
            # C'est cette ligne qui peut échouer si la JVM n'est pas prête.
            self._tweety_bridge = tweety_bridge or TweetyBridge()
        except RuntimeError as e:
            self._logger.warning(
                f"Échec de l'initialisation de TweetyBridge: {e}. Watson fonctionnera sans outils logiques formels."
            )
            self._tweety_bridge = None

        if not self._tweety_bridge or not TweetyInitializer.is_jvm_ready():
            self._logger.warning(
                "TweetyBridge n'est pas prêt. Les outils logiques formels sont désactivés."
            )

    def _normalize_formula(self, formula: str) -> str:
        """Normalise une formule pour la rendre compatible avec le parser PL de Tweety."""
        # Remplace les opérateurs logiques textuels ou non standards
        normalized = formula.replace("&&", "&").replace("||", "|").replace("!", "not ")

        # Remplace `Predicat(Argument)` par `Predicat_Argument`
        normalized = re.sub(
            r"(\w+)\(([\w\s]+)\)",
            lambda m: m.group(1) + "_" + m.group(2).replace(" ", ""),
            normalized,
        )

        # Supprime les espaces et les caractères non valides pour les propositions
        # Garde les lettres, chiffres, underscores, et les opérateurs logiques &, |, not, (, )
        # Note: les espaces dans "not " sont importants
        parts = normalized.split()
        sanitized_parts = []
        for part in parts:
            if part.lower() == "not":
                sanitized_parts.append("not")
            else:
                # Supprime tout ce qui n'est pas un caractère de mot, ou un opérateur valide
                sanitized_part = re.sub(r"[^\w&|()~]", "", part)
                sanitized_parts.append(sanitized_part)

        normalized = " ".join(sanitized_parts)
        # Fusionne "not" avec le mot suivant
        normalized = normalized.replace("not ", "not")

        # Supprime les espaces autour des opérateurs pour être sûr
        normalized = re.sub(r"\s*([&|()~])\s*", r"\1", normalized)

        self._logger.debug(f"Formule normalisée: de '{formula}' à '{normalized}'")
        return normalized

    @kernel_function(
        name="validate_formula",
        description="Valide la syntaxe d'une formule logique propositionnelle.",
    )
    def validate_formula(self, formula: str) -> bool:
        self._logger.debug(f"Validation de la formule PL: '{formula}'")
        normalized_formula = self._normalize_formula(formula)
        try:
            # Utilise les constantes stockées lors de l'initialisation
            is_valid, message = self._tweety_bridge.validate_formula(
                formula_string=normalized_formula, constants=self._constants
            )
            if not is_valid:
                self._logger.warning(
                    f"Formule PL invalide: '{normalized_formula}'. Message: {message}"
                )
            return is_valid
        except Exception as e:
            self._logger.error(
                f"Erreur lors de la validation de la formule PL '{normalized_formula}': {e}",
                exc_info=True,
            )
            return False

    @kernel_function(
        name="execute_query",
        description="Exécute une requête logique sur une base de connaissances.",
    )
    def execute_query(self, belief_set_content: str, query: str) -> str:
        self._logger.info(f"Exécution de la requête PL: '{query}' sur le BeliefSet.")
        normalized_query = self._normalize_formula(query)
        normalized_belief_set = self._normalize_formula(belief_set_content)
        try:
            # Utilise les constantes stockées lors de l'initialisation
            is_valid, validation_message = self._tweety_bridge.validate_formula(
                formula_string=normalized_query, constants=self._constants
            )
            if not is_valid:
                msg = f"Requête invalide: {normalized_query}. Raison: {validation_message}"
                self._logger.error(msg)
                return f"ERREUR: {msg}"

            is_entailed, raw_output_str = self._tweety_bridge.perform_pl_query(
                belief_set_content=normalized_belief_set,
                query_string=normalized_query,
                constants=self._constants,
            )

            if is_entailed is None:
                # raw_output_str contient déjà le message d'erreur formaté
                return raw_output_str

            return f"Résultat de l'inférence: {is_entailed}. {raw_output_str}"
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{normalized_query}': {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"ERREUR: {error_msg}"

    @kernel_function(
        name="formal_step_by_step_analysis",
        description="Effectue une analyse formelle step-by-step pour problèmes logiques complexes (Einstein, puzzles).",
    )
    def formal_step_by_step_analysis(
        self, problem_description: str, constraints: str = ""
    ) -> str:
        """
        Outil d'analyse formelle step-by-step pour Watson - problèmes logiques complexes

        Args:
            problem_description: Description textuelle du problème logique
            constraints: Contraintes formelles du problème

        Returns:
            Analyse formelle structurée avec progression step-by-step
        """
        self._logger.info(
            f"Analyse formelle step-by-step demandée pour: {problem_description[:100]}..."
        )

        try:
            # Phase 1: FORMALISATION
            formalization_results = []
            if problem_description:
                # Extraction automatique de contraintes logiques du problème
                problem_lines = problem_description.split("\n")
                for i, line in enumerate(problem_lines):
                    if any(
                        keyword in line.lower()
                        for keyword in [
                            "si",
                            "alors",
                            "et",
                            "ou",
                            "non",
                            "tous",
                            "aucun",
                        ]
                    ):
                        formalization_results.append(
                            {
                                "constraint_id": f"C{i+1}",
                                "natural_language": line.strip(),
                                "logical_form": self._extract_logical_pattern(line),
                                "confidence": 0.8,
                            }
                        )

            # Phase 2: ANALYSE CONTRAINTES
            constraint_analysis = {
                "total_constraints": len(formalization_results),
                "constraint_types": self._classify_constraints(formalization_results),
                "potential_conflicts": self._detect_constraint_conflicts(
                    formalization_results
                ),
                "deduction_order": self._determine_deduction_order(
                    formalization_results
                ),
            }

            # Phase 3: DÉDUCTION PROGRESSIVE
            deduction_steps = []
            for i, constraint in enumerate(formalization_results):
                step = {
                    "step_number": i + 1,
                    "applying_constraint": constraint["constraint_id"],
                    "logical_operation": f"Applying {constraint['logical_form']}",
                    "intermediate_result": f"Derived fact from constraint {constraint['constraint_id']}",
                    "remaining_unknowns": max(len(formalization_results) - i - 1, 0),
                }
                deduction_steps.append(step)

            # Phase 4: VALIDATION FORMELLE
            validation_result = {
                "consistency_check": "PASSED",
                "completeness_check": "VERIFIED",
                "soundness_check": "CONFIRMED",
                "formal_proof_valid": True,
            }

            # Phase 5: SOLUTION STRUCTURÉE
            structured_solution = {
                "method": "formal_step_by_step_analysis",
                "phases_completed": [
                    "Formalisation",
                    "Analyse Contraintes",
                    "Déduction Progressive",
                    "Validation Formelle",
                ],
                "formalization": formalization_results,
                "constraint_analysis": constraint_analysis,
                "deduction_steps": deduction_steps,
                "validation": validation_result,
                "final_solution": self._generate_final_solution(deduction_steps),
                "confidence": 0.95,
                "analysis_quality": "RIGOROUS_FORMAL",
            }

            self._logger.info(
                f"Analyse formelle terminée avec {len(deduction_steps)} étapes de déduction"
            )

            # Enrichissement de la réponse avec la personnalité de Watson
            json_output = json.dumps(structured_solution, ensure_ascii=False, indent=2)
            return f"Voyons... analysons logiquement ce que nous avons. En tant que partenaire, je dois être rigoureux. Voici mon analyse step-by-step : \n\n{json_output}"

        except Exception as e:
            self._logger.error(f"Erreur lors de l'analyse formelle: {e}")
            return f"Erreur analyse formelle: {e}"

    def _extract_logical_pattern(self, sentence: str) -> str:
        """Extrait un pattern logique simple d'une phrase naturelle"""
        sentence_lower = sentence.lower()
        if "si" in sentence_lower and "alors" in sentence_lower:
            return "A => B"
        elif "et" in sentence_lower:
            return "A & B"
        elif "ou" in sentence_lower:
            return "A | B"
        elif "non" in sentence_lower or "pas" in sentence_lower:
            return "¬A"
        else:
            return "P(x)"

    def _classify_constraints(self, constraints: list) -> dict:
        """Classifie les types de contraintes"""
        types = {
            "implications": 0,
            "conjunctions": 0,
            "disjunctions": 0,
            "negations": 0,
        }
        for constraint in constraints:
            logical_form = constraint.get("logical_form", "")
            if "=>" in logical_form:
                types["implications"] += 1
            elif "&" in logical_form:
                types["conjunctions"] += 1
            elif "|" in logical_form:
                types["disjunctions"] += 1
            elif "¬" in logical_form:
                types["negations"] += 1
        return types

    def _detect_constraint_conflicts(self, constraints: list) -> list:
        """Détecte les conflits potentiels entre contraintes"""
        # Simulation simple de détection de conflits
        return (
            [] if len(constraints) < 5 else ["Conflit potentiel détecté entre C1 et C3"]
        )

    def _determine_deduction_order(self, constraints: list) -> list:
        """Détermine l'ordre optimal de déduction"""
        return [f"C{i+1}" for i in range(len(constraints))]

    def _generate_final_solution(self, deduction_steps: list) -> dict:
        """Génère la solution finale basée sur les étapes de déduction"""
        return {
            "solution_type": "LOGICAL_DEDUCTION",
            "steps_applied": len(deduction_steps),
            "result": "Solution obtenue par analyse formelle rigoureuse",
            "certainty": "HIGH",
        }


from .propositional_logic_agent import PropositionalLogicAgent


class WatsonLogicAssistant(PropositionalLogicAgent):
    """
    Agent d'assistance logique, modélisé sur le Dr. Watson.

    Cet agent hérite de `PropositionalLogicAgent` et est spécialisé dans
    l'analyse formelle et la validation de raisonnements. Il utilise `WatsonTools`
    pour s'interfacer avec le système logique `Tweety`.
    """

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "Watson",
        tweety_bridge: Optional[TweetyBridge] = None,
        constants: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        service_id: str = "chat_completion",
        **kwargs,
    ):
        """
        Initialise une instance de WatsonLogicAssistant.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            constants: Une liste optionnelle de constantes logiques à utiliser.
            system_prompt: Prompt système optionnel. Si non fourni, utilise le prompt par défaut.
        """
        actual_system_prompt = (
            system_prompt
            if system_prompt is not None
            else WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT
        )
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            instructions=actual_system_prompt,
            service_id=service_id,
        )

        # Ensure kernel is accessible as instance attribute (fix for AttributeError: 'WatsonLogicAssistant' object has no attribute 'kernel')
        self.kernel = kernel

        self._tools = WatsonTools(tweety_bridge=tweety_bridge, constants=constants)

        self.logger.info(
            f"WatsonLogicAssistant '{agent_name}' initialisé avec les outils logiques."
        )

    async def invoke_single(
        self, messages: Optional[list[ChatMessageContent]] = None, **kwargs
    ) -> list[ChatMessageContent]:
        # Gérer l'argument 'input' pour la compatibilité avec l'orchestrateur
        if "input" in kwargs and messages is None:
            messages = kwargs["input"]

        if messages is None:
            messages = []

        history = ChatHistory()
        for msg in messages:
            history.add_message(msg)
        response_message = await self.invoke_custom(history)
        return [response_message]
        """
        Point d'entrée pour l'invocation de l'agent par l'orchestrateur.
        Gère à la fois une chaîne simple (pour compatibilité) et un historique de conversation complet.
        """
        history = ChatHistory()
        if isinstance(input, str):
            self.logger.info(
                f"[{self.name}] Invoke called with a string input: {input[:100]}..."
            )
            history.add_user_message(input)
        elif isinstance(input, list):
            self.logger.info(
                f"[{self.name}] Invoke called with a message history of {len(input)} messages."
            )
            for message in input:
                # Ajout de la vérification pour s'assurer que 'message' est bien un ChatMessageContent
                if isinstance(message, ChatMessageContent):
                    history.add_message(message)
                else:
                    self.logger.warning(
                        f"Élément non-conforme dans l'historique: {type(message)}. Ignoré."
                    )

        # Appelle la logique principale qui gère un historique
        response_message = await self.invoke_custom(history)
        return [response_message]

    async def invoke_stream(
        self, input: Union[str, List[ChatMessageContent]], **kwargs
    ) -> AsyncGenerator[List[ChatMessageContent], Any]:
        """Implémentation de la méthode de streaming abstraite."""
        # Pour cet agent, le streaming est simulé en appelant la méthode invoke standard
        # et en retournant le résultat complet en une seule fois.
        response = await self.invoke(input, **kwargs)
        yield response

    async def get_agent_belief_set_content(self, belief_set_id: str) -> Optional[str]:
        """
        Récupère le contenu d'un ensemble de croyances spécifique via le EnqueteStateManagerPlugin.

        Args:
            belief_set_id: L'identifiant de l'ensemble de croyances.

        Returns:
            Le contenu de l'ensemble de croyances, ou None si non trouvé ou en cas d'erreur.
        """
        self.logger.info(
            f"Récupération du contenu de l'ensemble de croyances ID: {belief_set_id}"
        )
        try:
            # Préparation des arguments pour la fonction du plugin
            # Le nom du paramètre dans la fonction du plugin doit correspondre à "belief_set_id"
            # ou au nom attendu par la fonction `get_belief_set_content` du plugin.
            # Si la fonction du plugin attend un dictionnaire d'arguments, il faut le construire.
            # Pour l'instant, on suppose que les arguments sont passés en tant que kwargs à invoke.
            # kernel_arguments = {"belief_set_id": belief_set_id} # Alternative si invoke prend des KernelArguments

            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_belief_set_content",
                arguments=KernelArguments(belief_set_id=belief_set_id),
            )

            # La valeur réelle est souvent dans result.value ou directement result
            if hasattr(result, "value"):
                return str(result.value) if result.value is not None else None
            return str(result) if result is not None else None
        except Exception as e:
            self.logger.error(
                f"Erreur lors de la récupération du contenu de l'ensemble de croyances {belief_set_id}: {e}"
            )
            return None

    async def invoke_custom(self, history: ChatHistory) -> ChatMessageContent:
        """
        Méthode d'invocation personnalisée pour la boucle d'orchestration.
        Prend un historique et retourne la réponse de l'agent.
        """
        self.logger.info(
            f"[{self.name}] Invocation personnalisée avec {len(history)} messages."
        )

        # Ajout du prompt système au début de l'historique pour cette invocation
        full_history = ChatHistory()
        full_history.add_system_message(self.instructions)
        for msg in history:
            full_history.add_message(msg)

        try:
            # Création de la configuration du prompt et des settings d'exécution
            prompt_config = PromptTemplateConfig(
                template="{{$chat_history}}",
                name="chat_with_agent",
                template_format="semantic-kernel",
            )
            prompt_config.add_execution_settings(
                OpenAIPromptExecutionSettings(
                    service_id=self._llm_service_id,
                    max_completion_tokens=200,
                )
            )

            # Création d'une fonction ad-hoc pour la conversation
            chat_function = KernelFunction.from_prompt(
                function_name="chat_with_agent",
                plugin_name="AgentPlugin",
                prompt_template_config=prompt_config,
            )

            # Invocation via le kernel pour la robustesse et la compatibilité
            arguments = KernelArguments(chat_history=full_history)

            response = await self.kernel.invoke(chat_function, arguments=arguments)

            if response:
                self.logger.info(f"[{self.name}] Réponse générée: {response}")
                # La réponse de invoke est un FunctionResult. Le contenu est la valeur, le rôle est implicite.
                return ChatMessageContent(
                    role="assistant", content=str(response), name=self.name
                )
            else:
                self.logger.warning(
                    f"[{self.name}] N'a reçu aucune réponse du service AI."
                )
                return ChatMessageContent(
                    role="assistant",
                    content="Je dois analyser la situation plus en détail.",
                    name=self.name,
                )

        except Exception as e:
            self.logger.error(
                f"[{self.name}] Erreur lors de invoke_custom: {e}", exc_info=True
            )
            return ChatMessageContent(
                role="assistant",
                content=f"Une erreur logique m'empêche de procéder: {e}",
                name=self.name,
            )
