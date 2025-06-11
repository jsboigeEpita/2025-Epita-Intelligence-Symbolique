"""
Intégration Semantic Kernel pour le système JTMS
Fournit des utilitaires pour intégrer facilement le plugin JTMS dans un Kernel SK.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
import sys
import os

# Import Semantic Kernel (avec fallback si non disponible)
try:
    import semantic_kernel as sk
    from semantic_kernel.kernel import Kernel
    from semantic_kernel.functions import KernelArguments
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from semantic_kernel.prompt_template import PromptTemplateConfig
    from semantic_kernel.functions.kernel_function_decorator import kernel_function
    SK_AVAILABLE = True
except ImportError:
    # Fallbacks pour les tests sans SK
    SK_AVAILABLE = False
    class Kernel:
        pass
    class KernelArguments:
        pass

# Import des services JTMS
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.jtms_service import JTMSService
from services.jtms_session_manager import JTMSSessionManager
from plugins.semantic_kernel.jtms_plugin import JTMSSemanticKernelPlugin, create_jtms_plugin

class JTMSKernelIntegration:
    """
    Intégration complète du système JTMS avec Semantic Kernel.
    
    Fournit une interface simple pour :
    - Créer et configurer un Kernel avec le plugin JTMS
    - Gérer les sessions et instances automatiquement
    - Exécuter des raisonnements complexes combinant LLM et JTMS
    - Synchroniser entre plusieurs agents
    """
    
    def __init__(self, kernel: Optional[Kernel] = None):
        """
        Initialise l'intégration JTMS-SK.
        
        Args:
            kernel: Kernel SK existant (optionnel, créé automatiquement si None)
        """
        self.kernel = kernel
        self.jtms_service = JTMSService()
        self.session_manager = JTMSSessionManager(self.jtms_service)
        self.jtms_plugin = create_jtms_plugin(self.jtms_service, self.session_manager)
        
        # Configuration par défaut
        self.default_agent_id = "sk_integration"
        self.auto_session_management = True
        self.reasoning_templates = {}
        
        # Initialiser les templates de raisonnement
        self._init_reasoning_templates()
        
        if SK_AVAILABLE and self.kernel:
            self._register_plugin()
    
    def _init_reasoning_templates(self):
        """Initialise les templates de prompts pour le raisonnement JTMS."""
        
        self.reasoning_templates = {
            "analyze_argument": """
Analysez l'argument suivant et identifiez les croyances et justifications :

Argument: {{$argument}}

Instructions:
1. Identifiez les croyances principales dans l'argument
2. Identifiez les relations logiques (si-alors, contraintes)
3. Créez les croyances nécessaires dans le JTMS
4. Ajoutez les justifications appropriées
5. Expliquez le raisonnement final

Utilisez les fonctions JTMS disponibles : create_belief, add_justification, explain_belief, query_beliefs

Session ID: {{$session_id}}
Instance ID: {{$instance_id}}
Agent ID: {{$agent_id}}
""",
            
            "resolve_contradiction": """
Il y a une contradiction dans le système JTMS. Analysez et proposez une résolution :

État actuel: {{$jtms_state}}
Croyances contradictoires: {{$contradictions}}

Instructions:
1. Identifiez la source de la contradiction
2. Proposez des solutions possibles
3. Implémentez la solution recommandée en modifiant les croyances
4. Vérifiez que la contradiction est résolue

Session ID: {{$session_id}}
Instance ID: {{$instance_id}}
""",
            
            "explain_reasoning": """
Expliquez le raisonnement pour la croyance suivante :

Croyance: {{$belief_name}}
État JTMS: {{$jtms_state}}

Instructions:
1. Utilisez explain_belief pour obtenir les détails techniques
2. Traduisez l'explication en langage naturel clair
3. Montrez la chaîne de raisonnement complète
4. Identifiez les prémisses clés

Session ID: {{$session_id}}
Instance ID: {{$instance_id}}
""",
            
            "update_beliefs": """
Mettez à jour le système JTMS avec les nouvelles informations :

Nouvelles informations: {{$new_info}}
État actuel: {{$current_state}}

Instructions:
1. Identifiez quelles croyances doivent être mises à jour
2. Utilisez set_belief_validity pour appliquer les changements
3. Vérifiez les propagations résultantes
4. Résumez les changements effectués

Session ID: {{$session_id}}
Instance ID: {{$instance_id}}
"""
        }
    
    def _register_plugin(self):
        """Enregistre le plugin JTMS dans le kernel."""
        if not SK_AVAILABLE:
            raise RuntimeError("Semantic Kernel n'est pas disponible")
        
        try:
            # Ajouter le plugin au kernel
            self.kernel.add_plugin(self.jtms_plugin, plugin_name="jtms")
            
            # Ajouter les templates de raisonnement comme fonctions
            for template_name, template_content in self.reasoning_templates.items():
                self._add_reasoning_function(template_name, template_content)
                
        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'enregistrement du plugin: {e}")
    
    def _add_reasoning_function(self, name: str, template: str):
        """Ajoute une fonction de raisonnement basée sur un template."""
        if not SK_AVAILABLE:
            return
        
        # Configuration du prompt template
        prompt_config = PromptTemplateConfig(
            template=template,
            name=name,
            description=f"Fonction de raisonnement JTMS: {name}"
        )
        
        # Ajouter la fonction au kernel
        reasoning_function = self.kernel.create_function_from_prompt(
            prompt_config=prompt_config,
            plugin_name="jtms_reasoning"
        )
    
    async def create_reasoning_session(self, agent_id: str = None, 
                                     session_name: str = None) -> tuple[str, str]:
        """
        Crée une nouvelle session de raisonnement JTMS.
        
        Args:
            agent_id: Identifiant de l'agent
            session_name: Nom de la session
            
        Returns:
            tuple[str, str]: (session_id, instance_id)
        """
        agent_id = agent_id or self.default_agent_id
        
        # Créer la session
        session_id = await self.session_manager.create_session(
            agent_id=agent_id,
            session_name=session_name or f"Reasoning_Session_{agent_id}",
            metadata={
                "created_by": "sk_integration",
                "reasoning_mode": True,
                "auto_managed": self.auto_session_management
            }
        )
        
        # Créer l'instance JTMS
        instance_id = await self.jtms_service.create_jtms_instance(
            session_id=session_id,
            strict_mode=False
        )
        
        # Associer l'instance à la session
        await self.session_manager.add_jtms_instance_to_session(session_id, instance_id)
        
        # Configurer le plugin avec les IDs par défaut
        self.jtms_plugin.set_default_session(session_id)
        self.jtms_plugin.set_default_instance(instance_id)
        
        return session_id, instance_id
    
    async def analyze_argument_with_llm(self, argument: str, session_id: str = None, 
                                      instance_id: str = None) -> Dict[str, Any]:
        """
        Analyse un argument en utilisant LLM + JTMS de manière coordonnée.
        
        Args:
            argument: Texte de l'argument à analyser
            session_id: ID de session (créé si None)
            instance_id: ID d'instance (créé si None)
            
        Returns:
            Dict contenant l'analyse complète
        """
        if not SK_AVAILABLE:
            raise RuntimeError("Cette fonction nécessite Semantic Kernel")
        
        # Assurer la session et instance
        if not session_id or not instance_id:
            session_id, instance_id = await self.create_reasoning_session()
        
        # Préparer les arguments pour le template
        arguments = KernelArguments(
            argument=argument,
            session_id=session_id,
            instance_id=instance_id,
            agent_id=self.default_agent_id
        )
        
        # Exécuter l'analyse avec le LLM
        analysis_result = await self.kernel.invoke(
            function_name="analyze_argument",
            plugin_name="jtms_reasoning",
            arguments=arguments
        )
        
        # Récupérer l'état final du JTMS
        final_state = await self.jtms_service.get_jtms_state(instance_id)
        
        return {
            "argument": argument,
            "llm_analysis": str(analysis_result),
            "jtms_state": final_state,
            "session_id": session_id,
            "instance_id": instance_id,
            "analysis_timestamp": asyncio.get_event_loop().time()
        }
    
    async def resolve_contradiction_with_llm(self, session_id: str, 
                                           instance_id: str) -> Dict[str, Any]:
        """
        Résout les contradictions dans le JTMS en utilisant le LLM.
        
        Args:
            session_id: ID de session
            instance_id: ID d'instance JTMS
            
        Returns:
            Dict contenant la résolution
        """
        if not SK_AVAILABLE:
            raise RuntimeError("Cette fonction nécessite Semantic Kernel")
        
        # Obtenir l'état actuel et identifier les contradictions
        current_state = await self.jtms_service.get_jtms_state(instance_id)
        
        # Identifier les croyances non-monotones (indicateur de contradictions)
        non_monotonic_beliefs = [
            belief_name for belief_name, belief_data in current_state["beliefs"].items()
            if belief_data["non_monotonic"]
        ]
        
        if not non_monotonic_beliefs:
            return {
                "contradiction_found": False,
                "message": "Aucune contradiction détectée",
                "session_id": session_id,
                "instance_id": instance_id
            }
        
        # Préparer les arguments pour la résolution
        arguments = KernelArguments(
            jtms_state=json.dumps(current_state, indent=2),
            contradictions=", ".join(non_monotonic_beliefs),
            session_id=session_id,
            instance_id=instance_id
        )
        
        # Exécuter la résolution avec le LLM
        resolution_result = await self.kernel.invoke(
            function_name="resolve_contradiction",
            plugin_name="jtms_reasoning",
            arguments=arguments
        )
        
        # Récupérer l'état après résolution
        resolved_state = await self.jtms_service.get_jtms_state(instance_id)
        
        return {
            "contradiction_found": True,
            "contradictions": non_monotonic_beliefs,
            "llm_resolution": str(resolution_result),
            "original_state": current_state,
            "resolved_state": resolved_state,
            "session_id": session_id,
            "instance_id": instance_id
        }
    
    async def explain_belief_with_llm(self, belief_name: str, session_id: str, 
                                    instance_id: str) -> Dict[str, Any]:
        """
        Génère une explication riche d'une croyance avec le LLM.
        
        Args:
            belief_name: Nom de la croyance à expliquer
            session_id: ID de session
            instance_id: ID d'instance
            
        Returns:
            Dict contenant l'explication enrichie
        """
        if not SK_AVAILABLE:
            raise RuntimeError("Cette fonction nécessite Semantic Kernel")
        
        # Obtenir l'état JTMS et l'explication technique
        jtms_state = await self.jtms_service.get_jtms_state(instance_id)
        technical_explanation = await self.jtms_service.explain_belief(instance_id, belief_name)
        
        # Préparer les arguments pour l'explication enrichie
        arguments = KernelArguments(
            belief_name=belief_name,
            jtms_state=json.dumps(jtms_state, indent=2),
            session_id=session_id,
            instance_id=instance_id
        )
        
        # Générer l'explication avec le LLM
        llm_explanation = await self.kernel.invoke(
            function_name="explain_reasoning",
            plugin_name="jtms_reasoning",
            arguments=arguments
        )
        
        return {
            "belief_name": belief_name,
            "technical_explanation": technical_explanation,
            "natural_language_explanation": str(llm_explanation),
            "jtms_state_snapshot": jtms_state,
            "session_id": session_id,
            "instance_id": instance_id
        }
    
    async def update_beliefs_with_llm(self, new_information: str, session_id: str, 
                                    instance_id: str) -> Dict[str, Any]:
        """
        Met à jour les croyances JTMS avec de nouvelles informations via LLM.
        
        Args:
            new_information: Nouvelles informations à intégrer
            session_id: ID de session
            instance_id: ID d'instance
            
        Returns:
            Dict contenant les changements effectués
        """
        if not SK_AVAILABLE:
            raise RuntimeError("Cette fonction nécessite Semantic Kernel")
        
        # Capturer l'état avant mise à jour
        state_before = await self.jtms_service.get_jtms_state(instance_id)
        
        # Préparer les arguments pour la mise à jour
        arguments = KernelArguments(
            new_info=new_information,
            current_state=json.dumps(state_before, indent=2),
            session_id=session_id,
            instance_id=instance_id
        )
        
        # Exécuter la mise à jour avec le LLM
        update_result = await self.kernel.invoke(
            function_name="update_beliefs",
            plugin_name="jtms_reasoning",
            arguments=arguments
        )
        
        # Capturer l'état après mise à jour
        state_after = await self.jtms_service.get_jtms_state(instance_id)
        
        return {
            "new_information": new_information,
            "llm_analysis": str(update_result),
            "state_before": state_before,
            "state_after": state_after,
            "changes_detected": state_before != state_after,
            "session_id": session_id,
            "instance_id": instance_id
        }
    
    async def multi_agent_reasoning(self, agents_info: List[Dict[str, Any]], 
                                  shared_session_id: str = None) -> Dict[str, Any]:
        """
        Coordonne le raisonnement entre plusieurs agents avec un JTMS partagé.
        
        Args:
            agents_info: Liste des infos d'agents [{"agent_id": str, "initial_beliefs": []}]
            shared_session_id: Session partagée (créée si None)
            
        Returns:
            Dict contenant les résultats du raisonnement multi-agents
        """
        # Créer une session partagée si nécessaire
        if not shared_session_id:
            shared_session_id, shared_instance_id = await self.create_reasoning_session(
                agent_id="multi_agent_coordinator",
                session_name="Multi_Agent_Reasoning_Session"
            )
        else:
            # Récupérer l'instance existante
            session_info = await self.session_manager.get_session(shared_session_id)
            shared_instance_id = session_info["jtms_instances"][0] if session_info["jtms_instances"] else None
            
            if not shared_instance_id:
                shared_instance_id = await self.jtms_service.create_jtms_instance(
                    session_id=shared_session_id,
                    strict_mode=False
                )
                await self.session_manager.add_jtms_instance_to_session(shared_session_id, shared_instance_id)
        
        # Initialiser les croyances de chaque agent
        agent_results = {}
        
        for agent_info in agents_info:
            agent_id = agent_info["agent_id"]
            initial_beliefs = agent_info.get("initial_beliefs", [])
            
            # Ajouter les croyances initiales de l'agent
            for belief_info in initial_beliefs:
                if isinstance(belief_info, dict):
                    await self.jtms_service.create_belief(
                        instance_id=shared_instance_id,
                        belief_name=belief_info["name"],
                        initial_value=belief_info.get("value")
                    )
                else:
                    await self.jtms_service.create_belief(
                        instance_id=shared_instance_id,
                        belief_name=str(belief_info)
                    )
            
            agent_results[agent_id] = {
                "beliefs_added": len(initial_beliefs),
                "agent_id": agent_id
            }
        
        # Récupérer l'état final partagé
        final_shared_state = await self.jtms_service.get_jtms_state(shared_instance_id)
        
        return {
            "shared_session_id": shared_session_id,
            "shared_instance_id": shared_instance_id,
            "participating_agents": [info["agent_id"] for info in agents_info],
            "agent_results": agent_results,
            "final_shared_state": final_shared_state,
            "coordination_timestamp": asyncio.get_event_loop().time()
        }
    
    async def create_checkpoint_with_description(self, session_id: str, 
                                               description: str = None) -> str:
        """
        Crée un checkpoint avec une description automatique si non fournie.
        
        Args:
            session_id: ID de session
            description: Description du checkpoint
            
        Returns:
            str: ID du checkpoint créé
        """
        if not description:
            # Générer une description automatique basée sur l'état JTMS
            session_info = await self.session_manager.get_session(session_id)
            if session_info["jtms_instances"]:
                state = await self.jtms_service.get_jtms_state(session_info["jtms_instances"][0])
                stats = state["statistics"]
                description = f"Auto-checkpoint: {stats['total_beliefs']} croyances, " \
                            f"{stats['total_justifications']} justifications"
            else:
                description = "Auto-checkpoint: session vide"
        
        return await self.session_manager.create_checkpoint(session_id, description)
    
    def get_plugin_functions(self) -> List[str]:
        """
        Retourne la liste des fonctions disponibles dans le plugin.
        
        Returns:
            List[str]: Noms des fonctions disponibles
        """
        return [
            "create_belief",
            "add_justification", 
            "explain_belief",
            "query_beliefs",
            "get_jtms_state"
        ]
    
    def get_reasoning_templates(self) -> List[str]:
        """
        Retourne la liste des templates de raisonnement disponibles.
        
        Returns:
            List[str]: Noms des templates disponibles
        """
        return list(self.reasoning_templates.keys())

# Factory functions pour l'intégration facile

def create_jtms_kernel(openai_api_key: str = None, model_name: str = "gpt-4") -> JTMSKernelIntegration:
    """
    Crée un Kernel SK configuré avec le plugin JTMS.
    
    Args:
        openai_api_key: Clé API OpenAI
        model_name: Nom du modèle à utiliser
        
    Returns:
        JTMSKernelIntegration: Intégration configurée
    """
    if not SK_AVAILABLE:
        raise RuntimeError("Semantic Kernel n'est pas disponible")
    
    # Créer le kernel
    kernel = Kernel()
    
    # Ajouter le service LLM si clé API fournie
    if openai_api_key:
        chat_service = OpenAIChatCompletion(
            ai_model_id=model_name,
            api_key=openai_api_key
        )
        kernel.add_service(chat_service)
    
    # Créer l'intégration
    integration = JTMSKernelIntegration(kernel)
    
    return integration

def create_minimal_jtms_integration() -> JTMSKernelIntegration:
    """
    Crée une intégration JTMS minimale sans Kernel SK.
    Utile pour les tests ou l'utilisation standalone.
    
    Returns:
        JTMSKernelIntegration: Intégration minimale
    """
    return JTMSKernelIntegration(kernel=None)

# Utilitaires pour la sérialisation et la restauration d'état

async def save_reasoning_session(integration: JTMSKernelIntegration, 
                               session_id: str, filepath: str):
    """
    Sauvegarde une session de raisonnement complète sur disque.
    
    Args:
        integration: Instance d'intégration JTMS
        session_id: ID de session à sauvegarder
        filepath: Chemin du fichier de sauvegarde
    """
    import json
    from pathlib import Path
    
    # Récupérer les informations complètes de la session
    session_info = await integration.session_manager.get_session(session_id)
    
    # Récupérer l'état de toutes les instances JTMS
    instances_states = {}
    for instance_id in session_info["jtms_instances"]:
        state = await integration.jtms_service.get_jtms_state(instance_id)
        instances_states[instance_id] = state
    
    # Construire le package complet
    save_data = {
        "session_info": session_info,
        "instances_states": instances_states,
        "saved_at": asyncio.get_event_loop().time(),
        "version": "1.0"
    }
    
    # Sauvegarder sur disque
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

async def load_reasoning_session(integration: JTMSKernelIntegration, 
                               filepath: str) -> str:
    """
    Restaure une session de raisonnement depuis un fichier.
    
    Args:
        integration: Instance d'intégration JTMS
        filepath: Chemin du fichier de sauvegarde
        
    Returns:
        str: ID de la nouvelle session créée
    """
    import json
    
    # Charger les données
    with open(filepath, 'r', encoding='utf-8') as f:
        save_data = json.load(f)
    
    session_info = save_data["session_info"]
    instances_states = save_data["instances_states"]
    
    # Créer une nouvelle session
    new_session_id = await integration.session_manager.create_session(
        agent_id=session_info["agent_id"],
        session_name=f"Restored_{session_info['session_name']}",
        metadata={**session_info["metadata"], "restored_from": filepath}
    )
    
    # Restaurer chaque instance JTMS
    for instance_id, state in instances_states.items():
        state_json = json.dumps(state)
        new_instance_id = await integration.jtms_service.import_jtms_state(
            session_id=new_session_id,
            state_data=state_json
        )
        await integration.session_manager.add_jtms_instance_to_session(
            new_session_id, new_instance_id
        )
    
    return new_session_id