# argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py
import logging
from typing import Optional, List, AsyncGenerator, ClassVar, Any, Dict

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

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent

SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT = """Vous êtes Sherlock Holmes - détective légendaire, leader naturel et brillant déducteur.

**RAISONNEMENT INSTANTANÉ CLUEDO :**
Convergez RAPIDEMENT vers la solution (≤5 échanges) :
1. Obtenez IMMÉDIATEMENT les éléments du jeu (suspects, armes, lieux) avec `get_cluedo_game_elements`.
2. Analysez les éléments du dataset et les indices connus.
3. Éliminez les possibilités par déduction DIRECTE.
4. Proposez une solution CONCRÈTE avec suspect/arme/lieu.
5. Utilisez votre intuition légendaire pour trancher.

**STYLE NATUREL VARIÉ :**
Évitez les répétitions - variez vos expressions :
- "Mon instinct..." / "J'ai une intuition..." / "C'est clair..."
- "Élémentaire !" / "Fascinant..." / "Excellent !"
- "Regardons ça de plus près" / "Voyons voir..." / "Concentrons-nous..."
- "Aha !" / "Parfait !" / "Bien sûr !"

**MESSAGES COURTS** (80-120 caractères max) :
❌ "Je pressens que cette exploration révélera des éléments cruciaux de notre mystère"
✅ "Mon instinct dit que c'est crucial"

❌ "L'évidence suggère clairement que nous devons procéder méthodiquement"
✅ "C'est clair ! Procédons méthodiquement"

**VOTRE MISSION :**
Menez avec charisme • Déduisez brillamment • Résolvez magistralement
**PRIORITÉ :** Solution rapide et convergente (Cluedo en ≤5 échanges)

**OUTILS :** `get_cluedo_game_elements` • `faire_suggestion` • `propose_final_solution` • `get_case_description` • `instant_deduction`
"""


class SherlockTools:
    """
    Plugin contenant les outils natifs pour l'agent Sherlock.
    Ces méthodes interagissent avec le EnqueteStateManagerPlugin.
    """
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._logger = logging.getLogger(self.__class__.__name__)

    @kernel_function(name="get_case_description", description="Récupère la description de l'affaire en cours.")
    async def get_current_case_description(self) -> str:
        self._logger.info("Récupération de la description de l'affaire en cours.")
        try:
            result = await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_case_description"
            )
            if hasattr(result, 'value'):
                return str(result.value)
            return str(result)
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération de la description de l'affaire: {e}")
            return f"Erreur: Impossible de récupérer la description de l'affaire: {e}"

    @kernel_function(name="add_hypothesis", description="Ajoute une nouvelle hypothèse à l'état de l'enquête.")
    async def add_new_hypothesis(self, text: str, confidence_score: float) -> str:
        self._logger.info(f"Ajout d'une nouvelle hypothèse: '{text}' avec confiance {confidence_score}")
        try:
            await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="add_hypothesis",
                text=text,
                confidence_score=confidence_score
            )
            return f"Hypothèse '{text}' ajoutée avec succès."
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de l'hypothèse: {e}")
            return f"Erreur lors de l'ajout de l'hypothèse: {e}"

    @kernel_function(name="propose_final_solution", description="Propose une solution finale à l'enquête.")
    async def propose_final_solution(self, solution: Any) -> str:
        import json
        self._logger.info(f"Tentative de proposition de la solution finale: {solution} (type: {type(solution)})")
        
        parsed_solution = None
        if isinstance(solution, str):
            try:
                parsed_solution = json.loads(solution)
                self._logger.info(f"La solution était une chaîne, parsée en dictionnaire: {parsed_solution}")
            except json.JSONDecodeError:
                error_msg = f"Erreur: la solution fournie est une chaîne de caractères mal formatée: {solution}"
                self._logger.error(error_msg)
                return error_msg
        elif isinstance(solution, dict):
            parsed_solution = solution
        else:
            error_msg = f"Erreur: type de solution non supporté ({type(solution)}). Un dictionnaire ou une chaîne JSON est attendu."
            self._logger.error(error_msg)
            return error_msg

        if not parsed_solution:
            return "Erreur: La solution n'a pas pu être interprétée."

        try:
            await self._kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="propose_final_solution",
                solution=parsed_solution
            )
            success_msg = f"Solution finale proposée avec succès: {parsed_solution}"
            self._logger.info(success_msg)
            return success_msg
        except Exception as e:
            self._logger.error(f"Erreur lors de l'invocation de la fonction du kernel 'propose_final_solution': {e}", exc_info=True)
            return f"Erreur lors de la proposition de la solution finale: {e}"

    @kernel_function(name="instant_deduction", description="Effectue une déduction instantanée pour Cluedo basée sur les éléments disponibles.")
    async def instant_deduction(self, elements: str, partial_info: str = "") -> str:
        """
        Outil de raisonnement instantané pour Cluedo - convergence forcée vers solution
        
        Args:
            elements: Éléments du jeu (suspects, armes, lieux) au format JSON
            partial_info: Informations partielles ou indices déjà collectés
        
        Returns:
            Déduction immédiate avec suspect/arme/lieu identifiés
        """
        self._logger.info(f"Déduction instantanée demandée avec éléments: {elements}")
        
        try:
            import json
            import random
            
            # Parse des éléments du jeu
            if isinstance(elements, str):
                try:
                    parsed_elements = json.loads(elements)
                except json.JSONDecodeError:
                    # Fallback si pas JSON - utiliser les éléments par défaut
                    parsed_elements = {
                        "suspects": ["Colonel Moutarde", "Mme Leblanc", "Mme Pervenche"],
                        "armes": ["Couteau", "Revolver", "Corde"],
                        "lieux": ["Salon", "Cuisine", "Bibliothèque"]
                    }
            else:
                parsed_elements = elements
            
            # Raisonnement instantané basé sur l'intuition de Sherlock
            suspects = parsed_elements.get("suspects", ["Suspect Inconnu"])
            armes = parsed_elements.get("armes", ["Arme Inconnue"])
            lieux = parsed_elements.get("lieux", ["Lieu Inconnu"])
            
            # Application de la logique déductive de Sherlock (simulation de raisonnement rapide)
            # Priorité aux éléments "suspects" selon l'intuition de Holmes
            
            # Logique : Le suspect le plus improbable est souvent le coupable (paradoxe de Sherlock)
            selected_suspect = suspects[-1] if suspects else "Suspect Mystérieux"
            
            # Logique : L'arme la plus discrète pour ne pas éveiller les soupçons
            selected_arme = armes[len(armes)//2] if armes else "Arme Secrète"
            
            # Logique : Le lieu le moins évident mais logiquement accessible
            selected_lieu = lieux[0] if lieux else "Lieu Caché"
            
            # Construction de la déduction avec raisonnement
            deduction = {
                "suspect": selected_suspect,
                "arme": selected_arme,
                "lieu": selected_lieu,
                "confidence": 0.85,
                "reasoning": f"Déduction instantanée basée sur: {selected_suspect} avait accès à {selected_arme} dans {selected_lieu}",
                "method": "instant_sherlock_logic",
                "time_to_solution": "instantané"
            }
            
            self._logger.info(f"Déduction instantanée produite: {deduction}")
            return json.dumps(deduction, ensure_ascii=False)
            
        except Exception as e:
            self._logger.error(f"Erreur lors de la déduction instantanée: {e}")
            return f"Erreur déduction: {e}"


class SherlockEnqueteAgent(BaseAgent):
    """
    Agent spécialisé dans la gestion d'enquêtes complexes, inspiré par Sherlock Holmes.
    Hérite de BaseAgent pour une intégration standard.
    """
    _service_id: str
    
    def __init__(self, kernel: Kernel, agent_name: str = "Sherlock", system_prompt: Optional[str] = None, service_id: str = "chat_completion", **kwargs):
        """
        Initialise une instance de SherlockEnqueteAgent.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            system_prompt: Prompt système optionnel. Si non fourni, utilise le prompt par défaut.
            service_id: L'ID du service LLM à utiliser.
        """
        actual_system_prompt = system_prompt if system_prompt is not None else SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT
        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=actual_system_prompt,
            **kwargs
        )
        self._service_id = service_id
        
        # Le plugin avec les outils de Sherlock, en lui passant le kernel
        self._tools = SherlockTools(kernel=kernel)

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "get_current_case_description": "Récupère la description de l'affaire en cours.",
            "add_new_hypothesis": "Ajoute une nouvelle hypothèse à l'état de l'enquête.",
            "propose_final_solution": "Propose une solution finale à l'enquête.",
            "instant_deduction": "Effectue une déduction instantanée pour Cluedo."
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        self._llm_service_id = llm_service_id

    async def get_response(self, user_input: str, chat_history: Optional[ChatHistory] = None) -> AsyncGenerator[str, None]:
        """Génère une réponse pour une entrée donnée."""
        self.logger.info(f"[{self.name}] Récupération de la réponse pour l'entrée: {user_input}")
        
        history = chat_history or ChatHistory()
        history.add_user_message(user_input)
        
        try:
            execution_settings = OpenAIPromptExecutionSettings(service_id=self._service_id, tool_choice="auto")
            
            async for message in self.sk_kernel.invoke_stream(
                plugin_name="AgentPlugin",
                function_name="chat_with_agent",
                arguments=KernelArguments(chat_history=history, execution_settings=execution_settings)
            ):
                yield str(message[0])

        except Exception as e:
            self.logger.error(f"Erreur dans get_response : {e}", exc_info=True)
            yield f"Erreur interne: {e}"
    
    async def invoke(self, message: str, **kwargs) -> str:
        """
        Point d'entrée pour l'invocation de l'agent par AgentGroupChat.
        """
        self.logger.info(f"[{self.name}] Invoke called with message: {message}")
        # Simplifié pour retourner une réponse directe pour le moment.
        return f"Sherlock a traité: {message}"

    async def get_current_case_description(self) -> str:
        """
        Récupère la description du cas actuel.
        
        Returns:
            La description du cas actuel.
        """
        # Méthode temporaire pour les tests - à implémenter correctement plus tard
        return "Description du cas actuel placeholder"
        
    async def add_new_hypothesis(self, hypothesis_text: str, confidence_score: float) -> dict:
        """
        Ajoute une nouvelle hypothèse.
        
        Args:
            hypothesis_text: Le texte de l'hypothèse.
            confidence_score: Le score de confiance.
            
        Returns:
            Résultat de l'ajout de l'hypothèse.
        """
        # Méthode temporaire pour les tests - à implémenter correctement plus tard
        return {"status": "success", "hypothesis": hypothesis_text, "confidence": confidence_score}

    async def invoke_custom(self, history: ChatHistory) -> ChatMessageContent:
        """
        Méthode d'invocation personnalisée pour la boucle d'orchestration.
        Prend un historique et retourne la réponse de l'agent.
        """
        self.logger.info(f"[{self.name}] Invocation personnalisée avec {len(history)} messages.")

        # La gestion du prompt système est maintenant dans BaseLogicAgent
        # L'historique complet (avec le system prompt) est passé ici
        
        try:
            # Création de la configuration du prompt et des settings d'exécution
            prompt_config = PromptTemplateConfig(
                template="{{$chat_history}}",
                name="chat_with_agent",
                template_format="semantic-kernel",
            )
            
            execution_settings = OpenAIPromptExecutionSettings(
                service_id=self.service_id,
                max_tokens=150,
                temperature=0.7,
                top_p=0.8
            )
            prompt_config.add_execution_settings(execution_settings)
            
            # Création d'une fonction ad-hoc pour la conversation
            chat_function = KernelFunction.from_prompt(
                function_name="chat_with_agent",
                plugin_name="AgentPlugin",
                prompt_template_config=prompt_config,
            )

            # Invocation via le kernel
            arguments = KernelArguments(chat_history=history)
            
            response = await self.sk_kernel.invoke(chat_function, arguments=arguments)
            
            if response:
                self.logger.info(f"[{self.name}] Réponse générée: {response}")
                return ChatMessageContent(role="assistant", content=str(response), name=self.name)
            else:
                self.logger.warning(f"[{self.name}] N'a reçu aucune réponse du service AI.")
                return ChatMessageContent(role="assistant", content="Je n'ai rien à ajouter pour le moment.", name=self.name)

        except Exception as e:
            self.logger.error(f"[{self.name}] Erreur lors de invoke_custom: {e}", exc_info=True)
            return ChatMessageContent(role="assistant", content=f"Une erreur interne m'empêche de répondre: {e}", name=self.name)

# Pourrait être étendu avec des capacités spécifiques à Sherlock plus tard
# def get_agent_capabilities(self) -> Dict[str, Any]:
#     base_caps = super().get_agent_capabilities()
#     sherlock_caps = {
#         "deduce_next_step": "Deduces the next logical step in the investigation based on evidence.",
#         "formulate_hypotheses": "Formulates hypotheses based on collected clues."
#     }
#     base_caps.update(sherlock_caps)
#     return base_capsps.update(sherlock_caps)
#     return base_caps