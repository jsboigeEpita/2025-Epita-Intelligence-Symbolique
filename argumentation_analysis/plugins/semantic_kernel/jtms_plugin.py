"""
Plugin Semantic Kernel natif pour l'intégration JTMS
Implémente 5 fonctions natives SK pour la manipulation des systèmes JTMS
avec support de sessions et synchronisation multi-agents.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Annotated
import sys
import os

# Import du framework Semantic Kernel
try:
    from semantic_kernel.functions import kernel_function
    from semantic_kernel.functions.kernel_function_decorator import kernel_function
    SK_AVAILABLE = True
except ImportError:
    # Fallback si SK n'est pas installé
    def kernel_function(name: str = None, description: str = None):
        def decorator(func):
            func._sk_function_name = name or func.__name__
            func._sk_function_description = description or func.__doc__
            return func
        return decorator
    SK_AVAILABLE = False

# Import des services JTMS
from argumentation_analysis.services.jtms_service import JTMSService
from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager

class JTMSSemanticKernelPlugin:
    """
    Plugin Semantic Kernel natif pour l'intégration JTMS.
    
    Fournit 5 fonctions natives SK pour la manipulation des systèmes JTMS :
    - create_belief : Création de croyances
    - add_justification : Ajout de justifications/règles
    - explain_belief : Génération d'explications
    - query_beliefs : Interrogation et filtrage
    - get_jtms_state : Récupération d'état complet
    """
    
    def __init__(self, jtms_service: JTMSService = None, session_manager: JTMSSessionManager = None):
        """
        Initialise le plugin avec les services JTMS.
        
        Args:
            jtms_service: Service JTMS centralisé
            session_manager: Gestionnaire de sessions
        """
        self.jtms_service = jtms_service or JTMSService()
        self.session_manager = session_manager or JTMSSessionManager(self.jtms_service)
        
        # Configuration par défaut
        self.default_session_id = None
        self.default_instance_id = None
        self.auto_create_session = True
        self.auto_create_instance = True
        
    async def _ensure_session_and_instance(self, session_id: str = None, instance_id: str = None, 
                                         agent_id: str = "semantic_kernel") -> tuple[str, str]:
        """
        S'assure qu'une session et une instance JTMS existent.
        
        Args:
            session_id: ID de session (optionnel)
            instance_id: ID d'instance (optionnel)  
            agent_id: ID de l'agent pour la création automatique
            
        Returns:
            tuple[str, str]: (session_id, instance_id)
        """
        # Gérer la session
        if not session_id:
            if self.default_session_id:
                session_id = self.default_session_id
            elif self.auto_create_session:
                session_id = await self.session_manager.create_session(
                    agent_id=agent_id,
                    session_name=f"SK_Session_{agent_id}",
                    metadata={"created_by": "semantic_kernel_plugin", "auto_created": True}
                )
                self.default_session_id = session_id
            else:
                raise ValueError("Aucune session spécifiée et création automatique désactivée")
        
        # Gérer l'instance JTMS
        if not instance_id:
            if self.default_instance_id:
                instance_id = self.default_instance_id
            elif self.auto_create_instance:
                instance_id = await self.jtms_service.create_jtms_instance(
                    session_id=session_id,
                    strict_mode=False
                )
                await self.session_manager.add_jtms_instance_to_session(session_id, instance_id)
                self.default_instance_id = instance_id
            else:
                raise ValueError("Aucune instance spécifiée et création automatique désactivée")
        
        return session_id, instance_id
    
    @kernel_function(
        name="create_belief",
        description="Crée une nouvelle croyance dans le système JTMS avec valeur initiale optionnelle"
    )
    async def create_belief(
        self,
        belief_name: Annotated[str, "Nom unique de la croyance à créer"],
        initial_value: Annotated[str, "Valeur initiale: 'true', 'false', ou 'unknown'"] = "unknown",
        session_id: Annotated[str, "Identifiant de la session JTMS"] = "",
        instance_id: Annotated[str, "Identifiant de l'instance JTMS"] = "",
        agent_id: Annotated[str, "Identifiant de l'agent créateur"] = "semantic_kernel"
    ) -> str:
        """
        Fonction SK native : Création de croyances dans le système JTMS.
        
        Permet de créer de nouvelles croyances avec des valeurs initiales
        et de les associer automatiquement à des sessions d'agents.
        
        Exemples d'usage :
        - create_belief("pluie", "true", session_123, instance_456, "sherlock")
        - create_belief("route_mouillée", "unknown") 
        
        Returns:
            str: JSON avec les détails de la croyance créée
        """
        try:
            # S'assurer que session et instance existent
            session_id, instance_id = await self._ensure_session_and_instance(
                session_id if session_id else None,
                instance_id if instance_id else None,
                agent_id
            )
            
            # Convertir la valeur initiale
            initial_bool_value = None
            if initial_value.lower() == "true":
                initial_bool_value = True
            elif initial_value.lower() == "false":
                initial_bool_value = False
            elif initial_value.lower() == "unknown":
                initial_bool_value = None
            else:
                raise ValueError(f"Valeur initiale invalide: {initial_value}. Utilisez 'true', 'false' ou 'unknown'")
            
            # Créer la croyance
            belief_data = await self.jtms_service.create_belief(
                instance_id=instance_id,
                belief_name=belief_name,
                initial_value=initial_bool_value
            )
            
            # Structure encapsulée attendue par les tests
            result = {
                "operation": "create_belief",
                "status": "success",
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id,
                "belief": belief_data  # Encapsuler les données de la croyance
            }
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_result = {
                "operation": "create_belief",
                "status": "error",
                "error": str(e),
                "belief_name": belief_name,
                "initial_value": initial_value,
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id
            }
            return json.dumps(error_result, indent=2, ensure_ascii=False)
    
    @kernel_function(
        name="add_justification",
        description="Ajoute une justification/règle de déduction au système JTMS"
    )
    async def add_justification(
        self,
        in_beliefs: Annotated[str, "Liste des croyances positives (séparées par des virgules)"],
        out_beliefs: Annotated[str, "Liste des croyances négatives (séparées par des virgules)"],
        conclusion: Annotated[str, "Croyance conclusion de la règle"],
        session_id: Annotated[str, "Identifiant de la session JTMS"] = "",
        instance_id: Annotated[str, "Identifiant de l'instance JTMS"] = "",
        agent_id: Annotated[str, "Identifiant de l'agent créateur"] = "semantic_kernel"
    ) -> str:
        """
        Fonction SK native : Ajout de justifications/règles de déduction.
        
        Permet d'ajouter des règles logiques du type :
        "Si (in_beliefs) ET NON (out_beliefs) alors conclusion"
        
        Exemples d'usage :
        - add_justification("pluie", "", "route_mouillée")
        - add_justification("pluie,vent", "soleil", "mauvais_temps")
        - add_justification("", "pluie", "temps_sec")
        
        Returns:
            str: JSON avec les détails de la justification ajoutée
        """
        try:
            # S'assurer que session et instance existent
            session_id, instance_id = await self._ensure_session_and_instance(
                session_id if session_id else None,
                instance_id if instance_id else None,
                agent_id
            )
            
            # Parser les listes de croyances
            in_beliefs_list = [b.strip() for b in in_beliefs.split(",") if b.strip()] if in_beliefs else []
            out_beliefs_list = [b.strip() for b in out_beliefs.split(",") if b.strip()] if out_beliefs else []
            
            # Validation
            if not conclusion.strip():
                raise ValueError("La conclusion ne peut pas être vide")
            
            # Ajouter la justification
            justification_data = await self.jtms_service.add_justification(
                instance_id=instance_id,
                in_beliefs=in_beliefs_list,
                out_beliefs=out_beliefs_list,
                conclusion=conclusion.strip()
            )
            
            # Structure encapsulée attendue par les tests
            result = {
                "operation": "add_justification",
                "status": "success",
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id,
                "rule_description": f"Si {in_beliefs_list} ET NON {out_beliefs_list} alors {conclusion}",
                "justification": justification_data  # Encapsuler les données de la justification
            }
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_result = {
                "operation": "add_justification",
                "status": "error",
                "error": str(e),
                "in_beliefs": in_beliefs,
                "out_beliefs": out_beliefs,
                "conclusion": conclusion,
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id
            }
            return json.dumps(error_result, indent=2, ensure_ascii=False)
    
    @kernel_function(
        name="explain_belief",
        description="Génère une explication détaillée pour une croyance donnée"
    )
    async def explain_belief(
        self,
        belief_name: Annotated[str, "Nom de la croyance à expliquer"],
        session_id: Annotated[str, "Identifiant de la session JTMS"] = "",
        instance_id: Annotated[str, "Identifiant de l'instance JTMS"] = "",
        agent_id: Annotated[str, "Identifiant de l'agent demandeur"] = "semantic_kernel"
    ) -> str:
        """
        Fonction SK native : Génération d'explications pour une croyance.
        
        Fournit une explication complète incluant :
        - Statut actuel de la croyance
        - Toutes les justifications applicables
        - Analyse de validité de chaque justification
        - Implications et dépendances
        
        Exemples d'usage :
        - explain_belief("route_mouillée")
        - explain_belief("temps_sec", session_123, instance_456)
        
        Returns:
            str: JSON avec l'explication structurée de la croyance
        """
        try:
            # S'assurer que session et instance existent
            session_id, instance_id = await self._ensure_session_and_instance(
                session_id if session_id else None,
                instance_id if instance_id else None,
                agent_id
            )
            
            # Générer l'explication
            result = await self.jtms_service.explain_belief(
                instance_id=instance_id,
                belief_name=belief_name
            )
            
            # Enrichir le résultat
            result["session_id"] = session_id
            result["instance_id"] = instance_id
            result["agent_id"] = agent_id
            result["operation"] = "explain_belief"
            result["status"] = "success"
            
            # Ajouter une explication en langage naturel
            status_text = "vraie" if result["current_status"] is True else \
                         "fausse" if result["current_status"] is False else "inconnue"
            
            if result["non_monotonic"]:
                status_text += " (non-monotone - présente dans une boucle logique)"
            
            result["natural_language_summary"] = f"La croyance '{belief_name}' est actuellement {status_text}. " \
                                               f"Elle a {len(result['justifications'])} justification(s) " \
                                               f"et {result['implications_count']} implication(s)."
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_result = {
                "operation": "explain_belief",
                "status": "error",
                "error": str(e),
                "belief_name": belief_name,
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id
            }
            return json.dumps(error_result, indent=2, ensure_ascii=False)
    
    @kernel_function(
        name="query_beliefs",
        description="Interroge et filtre les croyances selon leur statut ou propriétés"
    )
    async def query_beliefs(
        self,
        filter_status: Annotated[str, "Filtre par statut: 'valid', 'invalid', 'unknown', 'non_monotonic', ou 'all'"] = "all",
        session_id: Annotated[str, "Identifiant de la session JTMS"] = "",
        instance_id: Annotated[str, "Identifiant de l'instance JTMS"] = "",
        agent_id: Annotated[str, "Identifiant de l'agent demandeur"] = "semantic_kernel"
    ) -> str:
        """
        Fonction SK native : Interrogation et filtrage des croyances.
        
        Permet de récupérer et filtrer les croyances selon différents critères :
        - 'valid' : croyances vraies
        - 'invalid' : croyances fausses  
        - 'unknown' : croyances indéterminées
        - 'non_monotonic' : croyances dans des boucles logiques
        - 'all' : toutes les croyances
        
        Exemples d'usage :
        - query_beliefs("valid") -> toutes les croyances vraies
        - query_beliefs("non_monotonic") -> croyances problématiques
        - query_beliefs("all") -> état complet
        
        Returns:
            str: JSON avec la liste filtrée des croyances et statistiques
        """
        try:
            # S'assurer que session et instance existent
            session_id, instance_id = await self._ensure_session_and_instance(
                session_id if session_id else None,
                instance_id if instance_id else None,
                agent_id
            )
            
            # Valider le filtre
            valid_filters = ["valid", "invalid", "unknown", "non_monotonic", "all"]
            if filter_status not in valid_filters:
                raise ValueError(f"Filtre invalide: {filter_status}. Utilisez un de: {valid_filters}")
            
            # Appliquer le filtre (convertir 'all' en None pour l'API du service)
            filter_param = None if filter_status == "all" else filter_status
            
            # Interroger les croyances
            result = await self.jtms_service.query_beliefs(
                instance_id=instance_id,
                filter_status=filter_param
            )
            
            # Enrichir le résultat
            result["session_id"] = session_id
            result["instance_id"] = instance_id
            result["agent_id"] = agent_id
            result["operation"] = "query_beliefs"
            result["status"] = "success"
            
            # Ajouter un résumé en langage naturel
            if filter_status == "all":
                summary = f"Système JTMS contenant {result['total_beliefs']} croyances au total."
            else:
                summary = f"Trouvé {result['filtered_count']} croyances avec le statut '{filter_status}' " \
                         f"sur {result['total_beliefs']} croyances totales."
            
            result["natural_language_summary"] = summary
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_result = {
                "operation": "query_beliefs",
                "status": "error",
                "error": str(e),
                "filter_status": filter_status,
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id
            }
            return json.dumps(error_result, indent=2, ensure_ascii=False)
    
    @kernel_function(
        name="get_jtms_state",
        description="Récupère l'état complet du système JTMS avec toutes les croyances et justifications"
    )
    async def get_jtms_state(
        self,
        include_graph: Annotated[str, "Inclure le graphe de justifications: 'true' ou 'false'"] = "true",
        include_statistics: Annotated[str, "Inclure les statistiques détaillées: 'true' ou 'false'"] = "true",
        session_id: Annotated[str, "Identifiant de la session JTMS"] = "",
        instance_id: Annotated[str, "Identifiant de l'instance JTMS"] = "",
        agent_id: Annotated[str, "Identifiant de l'agent demandeur"] = "semantic_kernel"
    ) -> str:
        """
        Fonction SK native : Récupération de l'état complet du système JTMS.
        
        Fournit une vue d'ensemble complète du système incluant :
        - Toutes les croyances et leur statut
        - Graphe complet des justifications
        - Statistiques détaillées
        - Métadonnées de session et instance
        
        Utile pour :
        - Sauvegarde d'état
        - Debugging et analyse
        - Synchronisation entre agents
        - Visualisation du raisonnement
        
        Exemples d'usage :
        - get_jtms_state() -> état complet
        - get_jtms_state("false", "false") -> état minimal
        
        Returns:
            str: JSON avec l'état complet du système JTMS
        """
        try:
            # S'assurer que session et instance existent
            session_id, instance_id = await self._ensure_session_and_instance(
                session_id if session_id else None,
                instance_id if instance_id else None,
                agent_id
            )
            
            # Récupérer l'état complet
            result = await self.jtms_service.get_jtms_state(instance_id=instance_id)
            
            # Enrichir avec les informations de session
            session_info = await self.session_manager.get_session(session_id)
            
            result["session_info"] = {
                "session_id": session_id,
                "agent_id": session_info["agent_id"],
                "session_name": session_info["session_name"],
                "created_at": session_info["created_at"],
                "last_accessed": session_info["last_accessed"],
                "checkpoint_count": session_info.get("checkpoint_count", 0)
            }
            
            result["agent_id"] = agent_id
            result["operation"] = "get_jtms_state"
            result["status"] = "success"
            
            # Filtrer selon les paramètres
            if include_graph.lower() != "true":
                del result["justifications_graph"]
            
            if include_statistics.lower() != "true":
                del result["statistics"]
            
            # Ajouter un résumé en langage naturel
            stats = result.get("statistics", {})
            summary = f"Système JTMS de la session '{session_info['session_name']}' " \
                     f"contenant {stats.get('total_beliefs', 0)} croyances, " \
                     f"dont {stats.get('valid_beliefs', 0)} vraies, " \
                     f"{stats.get('invalid_beliefs', 0)} fausses, " \
                     f"et {stats.get('unknown_beliefs', 0)} indéterminées. " \
                     f"Total de {stats.get('total_justifications', 0)} justifications."
            
            if stats.get('non_monotonic_beliefs', 0) > 0:
                summary += f" Attention: {stats['non_monotonic_beliefs']} croyances non-monotones détectées."
            
            result["natural_language_summary"] = summary
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_result = {
                "operation": "get_jtms_state",
                "status": "error",
                "error": str(e),
                "include_graph": include_graph,
                "include_statistics": include_statistics,
                "session_id": session_id,
                "instance_id": instance_id,
                "agent_id": agent_id
            }
            return json.dumps(error_result, indent=2, ensure_ascii=False)
    
    # Méthodes utilitaires pour la configuration du plugin
    
    def set_default_session(self, session_id: str):
        """Définit la session par défaut pour le plugin."""
        self.default_session_id = session_id
    
    def set_default_instance(self, instance_id: str):
        """Définit l'instance JTMS par défaut pour le plugin."""
        self.default_instance_id = instance_id
    
    def configure_auto_creation(self, auto_session: bool = True, auto_instance: bool = True):
        """Configure la création automatique de sessions et instances."""
        self.auto_create_session = auto_session
        self.auto_create_instance = auto_instance
    
    async def get_plugin_status(self) -> Dict[str, Any]:
        """
        Retourne le statut du plugin et de ses services.
        
        Returns:
            Dict contenant les informations de statut
        """
        return {
            "plugin_name": "JTMSSemanticKernelPlugin",
            "semantic_kernel_available": SK_AVAILABLE,
            "default_session_id": self.default_session_id,
            "default_instance_id": self.default_instance_id,
            "auto_create_session": self.auto_create_session,
            "auto_create_instance": self.auto_create_instance,
            "jtms_service_active": self.jtms_service is not None,
            "session_manager_active": self.session_manager is not None,
            "functions_count": 5,
            "functions": [
                "create_belief",
                "add_justification", 
                "explain_belief",
                "query_beliefs",
                "get_jtms_state"
            ]
        }

# Factory function pour créer une instance configurée du plugin
def create_jtms_plugin(jtms_service: JTMSService = None, 
                      session_manager: JTMSSessionManager = None) -> JTMSSemanticKernelPlugin:
    """
    Factory function pour créer une instance configurée du plugin JTMS.
    
    Args:
        jtms_service: Service JTMS (créé automatiquement si None)
        session_manager: Gestionnaire de sessions (créé automatiquement si None)
        
    Returns:
        JTMSSemanticKernelPlugin: Instance configurée du plugin
    """
    if not jtms_service:
        jtms_service = JTMSService()
    
    if not session_manager:
        session_manager = JTMSSessionManager(jtms_service)
    
    return JTMSSemanticKernelPlugin(jtms_service, session_manager)