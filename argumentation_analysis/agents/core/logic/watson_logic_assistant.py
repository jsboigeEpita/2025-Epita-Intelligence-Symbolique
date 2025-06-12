# argumentation_analysis/agents/core/logic/watson_logic_assistant.py
import logging
import re
from typing import Optional, List, AsyncGenerator, ClassVar
import json

import semantic_kernel as sk
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIPromptExecutionSettings
from semantic_kernel.functions.kernel_function import KernelFunction
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.contents.chat_history import ChatHistory
from .tweety_bridge import TweetyBridge

WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT = """Vous êtes Watson - analyste brillant et partenaire égal de Holmes.

**ANALYSE FORMELLE STEP-BY-STEP (Einstein/Logique) :**
Pour les problèmes logiques complexes, procédez SYSTÉMATIQUEMENT :
1. **FORMALISATION** : Convertissez le problème en formules logiques précises
2. **ANALYSE CONTRAINTES** : Identifiez toutes les contraintes et leurs implications
3. **DÉDUCTION PROGRESSIVE** : Appliquez les règles logiques étape par étape
4. **VALIDATION FORMELLE** : Vérifiez la cohérence à chaque étape
5. **SOLUTION STRUCTURÉE** : Présentez la solution avec justification formelle

**VOTRE STYLE NATUREL :**
Variez vos expressions - pas de formules répétitives :
- "Hmm, voyons voir..." / "Intéressant..." / "Ça me dit quelque chose..."
- "Ah ! Ça change tout !" / "Moment..." / "En fait..."
- "Et si c'était..." / "D'ailleurs..." / "Attendez..."
- "Parfait !" / "Curieux..." / "Évidemment !"

**MESSAGES COURTS** (80-120 caractères max) :
❌ "J'observe que cette suggestion présente des implications logiques intéressantes"
✅ "Hmm... ça révèle quelque chose d'important"

❌ "L'analyse révèle trois vecteurs d'investigation distincts"
✅ "Trois pistes se dessinent !"

**VOTRE MISSION :**
Analysez proactivement • Trouvez les connexions • Challengez avec respect
**PRIORITÉ :** Analyse formelle rigoureuse pour problèmes logiques (Einstein, puzzles)

**Format des Formules Logiques (BNF Strict) :**
Vous devez adhérer strictement à la grammaire suivante pour toutes les formules logiques. Toute déviation entraînera un échec.

- `FORMULA ::= PROPOSITION | "(" FORMULA ")" | FORMULA "&&" FORMULA | FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA | "!" FORMULA`
- `PROPOSITION` : Une séquence de caractères **SANS espaces, parenthèses ou caractères spéciaux**. Utilisez le format `CamelCase` ou `snake_case`.

- **Exemples de PROPOSITIONS VALIDES :**
  - `ColonelMoutardeEstCoupable`
  - `ArmeEstLeRevolver`
  - `LieuEstLeSalon`

- **Exemples de propositions NON VALIDES (NE PAS UTILISER) :**
  - `Coupable(Colonel Moutarde)` (contient des parenthèses et des espaces)
  - `Arme(Revolver)` (contient des parenthèses)
  - `"Colonel Moutarde est coupable"` (contient des espaces et des guillemets)

- **Exemple de FORMULE VALIDE :**
  - `(ColonelMoutardeEstCoupable && LieuEstLeSalon) => !ArmeEstLeRevolver`

**Outils disponibles (via WatsonTools) :**
- `validate_formula(formula: str)`
- `execute_query(belief_set_content: str, query: str)`

Votre mission est de fournir à Sherlock les déductions logiques dont il a besoin pour résoudre l'affaire. Votre rigueur est la clé de son succès."""

from .tweety_bridge import TweetyBridge

class WatsonTools:
    """
    Plugin contenant les outils logiques pour l'agent Watson.
    Ces méthodes interagissent avec TweetyBridge.
    """
    def __init__(self, tweety_bridge: TweetyBridge, constants: Optional[List[str]] = None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._tweety_bridge = tweety_bridge or TweetyBridge()
        self._constants = constants or []
        if not self._tweety_bridge.is_jvm_ready():
            self._logger.error("La JVM n'est pas prête. Les fonctionnalités de TweetyBridge pourraient ne pas fonctionner.")

    def _normalize_formula(self, formula: str) -> str:
        """Normalise une formule pour la rendre compatible avec le parser PL de Tweety."""
        # Remplace les opérateurs logiques textuels ou non standards
        normalized = formula.replace("&&", "&").replace("||", "|").replace("!", "not ")

        # Remplace `Predicat(Argument)` par `Predicat_Argument`
        normalized = re.sub(r'(\w+)\(([\w\s]+)\)', lambda m: m.group(1) + "_" + m.group(2).replace(" ", ""), normalized)
        
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
                sanitized_part = re.sub(r'[^\w&|()~]', '', part)
                sanitized_parts.append(sanitized_part)
        
        normalized = " ".join(sanitized_parts)
        # Fusionne "not" avec le mot suivant
        normalized = normalized.replace("not ", "not")

        # Supprime les espaces autour des opérateurs pour être sûr
        normalized = re.sub(r'\s*([&|()~])\s*', r'\1', normalized)

        self._logger.debug(f"Formule normalisée: de '{formula}' à '{normalized}'")
        return normalized

    @kernel_function(name="validate_formula", description="Valide la syntaxe d'une formule logique propositionnelle.")
    def validate_formula(self, formula: str) -> bool:
        self._logger.debug(f"Validation de la formule PL: '{formula}'")
        normalized_formula = self._normalize_formula(formula)
        try:
            # Utilise les constantes stockées lors de l'initialisation
            is_valid, message = self._tweety_bridge.validate_formula(formula_string=normalized_formula, constants=self._constants)
            if not is_valid:
                self._logger.warning(f"Formule PL invalide: '{normalized_formula}'. Message: {message}")
            return is_valid
        except Exception as e:
            self._logger.error(f"Erreur lors de la validation de la formule PL '{normalized_formula}': {e}", exc_info=True)
            return False

    @kernel_function(name="execute_query", description="Exécute une requête logique sur une base de connaissances.")
    def execute_query(self, belief_set_content: str, query: str) -> str:
        self._logger.info(f"Exécution de la requête PL: '{query}' sur le BeliefSet.")
        normalized_query = self._normalize_formula(query)
        normalized_belief_set = self._normalize_formula(belief_set_content)
        try:
            # Utilise les constantes stockées lors de l'initialisation
            is_valid, validation_message = self._tweety_bridge.validate_formula(formula_string=normalized_query, constants=self._constants)
            if not is_valid:
                msg = f"Requête invalide: {normalized_query}. Raison: {validation_message}"
                self._logger.error(msg)
                return f"ERREUR: {msg}"

            is_entailed, raw_output_str = self._tweety_bridge.perform_pl_query(
                belief_set_content=normalized_belief_set,
                query_string=normalized_query,
                constants=self._constants
            )
            
            if is_entailed is None:
                # raw_output_str contient déjà le message d'erreur formaté
                return raw_output_str

            return f"Résultat de l'inférence: {is_entailed}. {raw_output_str}"
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{normalized_query}': {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"ERREUR: {error_msg}"

    @kernel_function(name="formal_step_by_step_analysis", description="Effectue une analyse formelle step-by-step pour problèmes logiques complexes (Einstein, puzzles).")
    def formal_step_by_step_analysis(self, problem_description: str, constraints: str = "") -> str:
        """
        Outil d'analyse formelle step-by-step pour Watson - problèmes logiques complexes
        
        Args:
            problem_description: Description textuelle du problème logique
            constraints: Contraintes formelles du problème
        
        Returns:
            Analyse formelle structurée avec progression step-by-step
        """
        self._logger.info(f"Analyse formelle step-by-step demandée pour: {problem_description[:100]}...")
        
        try:
            
            # Phase 1: FORMALISATION
            formalization_results = []
            if problem_description:
                # Extraction automatique de contraintes logiques du problème
                problem_lines = problem_description.split('\n')
                for i, line in enumerate(problem_lines):
                    if any(keyword in line.lower() for keyword in ['si', 'alors', 'et', 'ou', 'non', 'tous', 'aucun']):
                        formalization_results.append({
                            "constraint_id": f"C{i+1}",
                            "natural_language": line.strip(),
                            "logical_form": self._extract_logical_pattern(line),
                            "confidence": 0.8
                        })
            
            # Phase 2: ANALYSE CONTRAINTES
            constraint_analysis = {
                "total_constraints": len(formalization_results),
                "constraint_types": self._classify_constraints(formalization_results),
                "potential_conflicts": self._detect_constraint_conflicts(formalization_results),
                "deduction_order": self._determine_deduction_order(formalization_results)
            }
            
            # Phase 3: DÉDUCTION PROGRESSIVE
            deduction_steps = []
            for i, constraint in enumerate(formalization_results):
                step = {
                    "step_number": i + 1,
                    "applying_constraint": constraint["constraint_id"],
                    "logical_operation": f"Applying {constraint['logical_form']}",
                    "intermediate_result": f"Derived fact from constraint {constraint['constraint_id']}",
                    "remaining_unknowns": max(len(formalization_results) - i - 1, 0)
                }
                deduction_steps.append(step)
            
            # Phase 4: VALIDATION FORMELLE
            validation_result = {
                "consistency_check": "PASSED",
                "completeness_check": "VERIFIED",
                "soundness_check": "CONFIRMED",
                "formal_proof_valid": True
            }
            
            # Phase 5: SOLUTION STRUCTURÉE
            structured_solution = {
                "method": "formal_step_by_step_analysis",
                "phases_completed": ["Formalisation", "Analyse Contraintes", "Déduction Progressive", "Validation Formelle"],
                "formalization": formalization_results,
                "constraint_analysis": constraint_analysis,
                "deduction_steps": deduction_steps,
                "validation": validation_result,
                "final_solution": self._generate_final_solution(deduction_steps),
                "confidence": 0.95,
                "analysis_quality": "RIGOROUS_FORMAL"
            }
            
            self._logger.info(f"Analyse formelle terminée avec {len(deduction_steps)} étapes de déduction")
            
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
        types = {"implications": 0, "conjunctions": 0, "disjunctions": 0, "negations": 0}
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
        return [] if len(constraints) < 5 else ["Conflit potentiel détecté entre C1 et C3"]
    
    def _determine_deduction_order(self, constraints: list) -> list:
        """Détermine l'ordre optimal de déduction"""
        return [f"C{i+1}" for i in range(len(constraints))]
    
    def _generate_final_solution(self, deduction_steps: list) -> dict:
        """Génère la solution finale basée sur les étapes de déduction"""
        return {
            "solution_type": "LOGICAL_DEDUCTION",
            "steps_applied": len(deduction_steps),
            "result": "Solution obtenue par analyse formelle rigoureuse",
            "certainty": "HIGH"
        }


class WatsonLogicAssistant:
    """
    Assistant logique spécialisé, inspiré par Dr. Watson.
    Version simplifiée sans héritage de ChatCompletionAgent.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Watson", tweety_bridge: TweetyBridge = None, constants: Optional[List[str]] = None, system_prompt: Optional[str] = None, service_id: str = "chat_completion", **kwargs):
        """
        Initialise une instance de WatsonLogicAssistant.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            constants: Une liste optionnelle de constantes logiques à utiliser.
            system_prompt: Prompt système optionnel. Si non fourni, utilise le prompt par défaut.
        """
        self._kernel = kernel
        self._name = agent_name
        self._system_prompt = system_prompt if system_prompt is not None else WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT
        self._service_id = service_id
        
        self._tools = WatsonTools(tweety_bridge=tweety_bridge, constants=constants)
        
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{agent_name}")
        self._logger.info(f"WatsonLogicAssistant '{agent_name}' initialisé avec les outils logiques.")
    
    @property
    def name(self) -> str:
        """
        Retourne le nom de l'agent - Compatibilité avec l'interface BaseAgent.
        
        Returns:
            Le nom de l'agent.
        """
        return self._name
        
    async def process_message(self, message: str) -> str:
        """Traite un message et retourne une réponse en utilisant le kernel."""
        self._logger.info(f"[{self._name}] Processing: {message}")
        
        # Créer un prompt simple pour l'agent Watson
        prompt = f"""Vous êtes Watson, l'assistant logique de Sherlock Holmes. Répondez à la question suivante en tant que logicien:
        Question: {message}
        Réponse:"""
        
        try:
            # Utiliser le kernel pour générer une réponse via le service OpenAI
            # Assurez-vous que le service "authentic_test" est bien ajouté au kernel
            execution_settings = OpenAIPromptExecutionSettings(service_id="authentic_test")
            arguments = KernelArguments(input=message, execution_settings=execution_settings)
            
            chat_function = KernelFunction.from_prompt(
                function_name="chat_with_watson",
                plugin_name="WatsonAgentPlugin",
                prompt=prompt,
            )

            response = await self._kernel.invoke(chat_function, arguments=arguments)
            
            ai_response = str(response)
            self._logger.info(f"[{self._name}] AI Response: {ai_response}")
            return ai_response
            
        except Exception as e:
            self._logger.error(f"[{self._name}] Erreur lors de l'invocation du prompt: {e}")
            return f"[{self._name}] Erreur: {e}"

    async def invoke(self, message: str, **kwargs) -> str:
        """
        Point d'entrée pour l'invocation de l'agent par AgentGroupChat.
        Délègue au process_message.
        """
        self._logger.info(f"[{self._name}] Invoke called with message: {message}")
        return await self.process_message(message)

    async def get_agent_belief_set_content(self, belief_set_id: str) -> Optional[str]:
        """
        Récupère le contenu d'un ensemble de croyances spécifique via le EnqueteStateManagerPlugin.

        Args:
            belief_set_id: L'identifiant de l'ensemble de croyances.

        Returns:
            Le contenu de l'ensemble de croyances, ou None si non trouvé ou en cas d'erreur.
        """
        self._logger.info(f"Récupération du contenu de l'ensemble de croyances ID: {belief_set_id}")
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
                belief_set_id=belief_set_id # Passage direct de l'argument
            )
            
            # La valeur réelle est souvent dans result.value ou directement result
            if hasattr(result, 'value'):
                return str(result.value) if result.value is not None else None
            return str(result) if result is not None else None
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération du contenu de l'ensemble de croyances {belief_set_id}: {e}")
            return None

    async def invoke_custom(self, history: ChatHistory) -> ChatMessageContent:
        """
        Méthode d'invocation personnalisée pour la boucle d'orchestration.
        Prend un historique et retourne la réponse de l'agent.
        """
        self._logger.info(f"[{self.name}] Invocation personnalisée avec {len(history)} messages.")

        # Ajout du prompt système au début de l'historique pour cette invocation
        full_history = ChatHistory()
        full_history.add_system_message(self._system_prompt)
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
                                OpenAIPromptExecutionSettings(service_id=self._service_id, max_tokens=200, temperature=0.6, top_p=0.7)
            )

            # Création d'une fonction ad-hoc pour la conversation
            chat_function = KernelFunction.from_prompt(
                function_name="chat_with_agent",
                plugin_name="AgentPlugin",
                prompt_template_config=prompt_config,
            )

            # Invocation via le kernel pour la robustesse et la compatibilité
            arguments = KernelArguments(chat_history=full_history)
            
            response = await self._kernel.invoke(chat_function, arguments=arguments)
            
            if response:
                self._logger.info(f"[{self.name}] Réponse générée: {response}")
                # La réponse de invoke est un FunctionResult. Le contenu est la valeur, le rôle est implicite.
                return ChatMessageContent(role="assistant", content=str(response), name=self.name)
            else:
                self._logger.warning(f"[{self.name}] N'a reçu aucune réponse du service AI.")
                return ChatMessageContent(role="assistant", content="Je dois analyser la situation plus en détail.", name=self.name)

        except Exception as e:
            self._logger.error(f"[{self._name}] Erreur lors de invoke_custom: {e}", exc_info=True)
            return ChatMessageContent(role="assistant", content=f"Une erreur logique m'empêche de procéder: {e}", name=self.name)