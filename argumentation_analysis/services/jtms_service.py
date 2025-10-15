"""
Service JTMS Centralisé pour l'intégration avec Semantic Kernel
Implémente une interface de haut niveau pour la manipulation des systèmes JTMS
avec support de sessions, versioning et synchronisation multi-agents.
"""

import uuid
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import sys
import os

# Ajout du path pour importer le module JTMS existant
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "1.4.1-JTMS"))
from jtms import JTMS, Belief, Justification


class JTMSService:
    """
    Service centralisé pour la gestion des systèmes JTMS avec support
    de sessions, versioning et synchronisation multi-agents.
    """

    def __init__(self):
        self.instances: Dict[str, JTMS] = {}
        self.metadata: Dict[str, Dict] = {}
        self.session_manager = None  # Sera injecté par le SessionManager

    async def create_jtms_instance(
        self, session_id: str, strict_mode: bool = False
    ) -> str:
        """
        Crée une nouvelle instance JTMS pour une session donnée.

        Args:
            session_id: Identifiant unique de la session
            strict_mode: Mode strict pour la validation des croyances

        Returns:
            str: Identifiant de l'instance JTMS créée
        """
        instance_id = f"jtms_{session_id}_{uuid.uuid4().hex[:8]}"

        self.instances[instance_id] = JTMS(strict=strict_mode)
        self.metadata[instance_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "strict_mode": strict_mode,
            "beliefs_count": 0,
            "justifications_count": 0,
            "last_updated": datetime.now().isoformat(),
        }

        return instance_id

    async def create_belief(
        self, instance_id: str, belief_name: str, initial_value: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle croyance dans l'instance JTMS spécifiée.

        Args:
            instance_id: Identifiant de l'instance JTMS
            belief_name: Nom de la croyance à créer
            initial_value: Valeur initiale de la croyance (optionnelle)

        Returns:
            Dict contenant les détails de la croyance créée
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        jtms = self.instances[instance_id]

        # Créer la croyance
        jtms.add_belief(belief_name)

        # Définir la valeur initiale si spécifiée
        if initial_value is not None:
            jtms.set_belief_validity(belief_name, initial_value)

        # Mettre à jour les métadonnées
        self.metadata[instance_id]["beliefs_count"] = len(jtms.beliefs)
        self.metadata[instance_id]["last_updated"] = datetime.now().isoformat()

        belief = jtms.beliefs[belief_name]
        return {
            "name": belief.name,
            "valid": belief.valid,
            "non_monotonic": belief.non_monotonic,
            "justifications_count": len(belief.justifications),
            "implications_count": len(belief.implications),
        }

    async def add_justification(
        self,
        instance_id: str,
        in_beliefs: List[str],
        out_beliefs: List[str],
        conclusion: str,
    ) -> Dict[str, Any]:
        """
        Ajoute une justification (règle de déduction) à l'instance JTMS.

        Args:
            instance_id: Identifiant de l'instance JTMS
            in_beliefs: Liste des croyances positives (prémisses)
            out_beliefs: Liste des croyances négatives (contraintes)
            conclusion: Croyance conclusion

        Returns:
            Dict contenant les détails de la justification ajoutée
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        jtms = self.instances[instance_id]

        # Ajouter la justification
        jtms.add_justification(in_beliefs, out_beliefs, conclusion)

        # Mettre à jour les métadonnées
        total_justifications = sum(
            len(belief.justifications) for belief in jtms.beliefs.values()
        )
        self.metadata[instance_id]["justifications_count"] = total_justifications
        self.metadata[instance_id]["last_updated"] = datetime.now().isoformat()

        return {
            "in_beliefs": in_beliefs,
            "out_beliefs": out_beliefs,
            "conclusion": conclusion,
            "conclusion_status": jtms.beliefs[conclusion].valid,
            "non_monotonic": jtms.beliefs[conclusion].non_monotonic,
        }

    async def explain_belief(
        self, instance_id: str, belief_name: str
    ) -> Dict[str, Any]:
        """
        Génère une explication détaillée pour une croyance donnée.

        Args:
            instance_id: Identifiant de l'instance JTMS
            belief_name: Nom de la croyance à expliquer

        Returns:
            Dict contenant l'explication structurée de la croyance
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        if belief_name not in self.instances[instance_id].beliefs:
            raise ValueError(f"Croyance non trouvée: {belief_name}")

        jtms = self.instances[instance_id]
        belief = jtms.beliefs[belief_name]

        justifications_details = []
        for j in belief.justifications:
            in_status = [
                {"name": repr(b), "valid": jtms.beliefs[repr(b)].valid}
                for b in j.in_list
            ]
            out_status = [
                {"name": repr(b), "valid": jtms.beliefs[repr(b)].valid}
                for b in j.out_list
            ]

            is_valid = all(jtms.beliefs[repr(b)].valid for b in j.in_list) and all(
                not jtms.beliefs[repr(b)].valid for b in j.out_list
            )

            justifications_details.append(
                {
                    "in_beliefs": in_status,
                    "out_beliefs": out_status,
                    "is_valid": is_valid,
                    "conclusion": belief_name,
                }
            )

        return {
            "belief_name": belief_name,
            "current_status": belief.valid,
            "non_monotonic": belief.non_monotonic,
            "justifications": justifications_details,
            "explanation_text": jtms.explain_belief(belief_name),
            "implications_count": len(belief.implications),
        }

    async def query_beliefs(
        self, instance_id: str, filter_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interroge et filtre les croyances selon leur statut.

        Args:
            instance_id: Identifiant de l'instance JTMS
            filter_status: Filtre par statut ('valid', 'invalid', 'unknown', 'non_monotonic')

        Returns:
            Dict contenant la liste filtrée des croyances
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        jtms = self.instances[instance_id]
        beliefs_data = []

        for belief in jtms.beliefs.values():
            belief_info = {
                "name": belief.name,
                "valid": belief.valid,
                "non_monotonic": belief.non_monotonic,
                "justifications_count": len(belief.justifications),
                "implications_count": len(belief.implications),
            }

            # Appliquer le filtre si spécifié
            if filter_status:
                if filter_status == "valid" and belief.valid is True:
                    beliefs_data.append(belief_info)
                elif filter_status == "invalid" and belief.valid is False:
                    beliefs_data.append(belief_info)
                elif filter_status == "unknown" and belief.valid is None:
                    beliefs_data.append(belief_info)
                elif filter_status == "non_monotonic" and belief.non_monotonic:
                    beliefs_data.append(belief_info)
            else:
                beliefs_data.append(belief_info)

        return {
            "total_beliefs": len(jtms.beliefs),
            "filtered_count": len(beliefs_data),
            "filter_applied": filter_status,
            "beliefs": beliefs_data,
            "metadata": self.metadata[instance_id],
        }

    async def get_jtms_state(self, instance_id: str) -> Dict[str, Any]:
        """
        Retourne l'état complet de l'instance JTMS.

        Args:
            instance_id: Identifiant de l'instance JTMS

        Returns:
            Dict contenant l'état complet du système
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        jtms = self.instances[instance_id]

        # Construire la représentation complète de l'état
        beliefs_state = {}
        justifications_graph = []

        for belief in jtms.beliefs.values():
            beliefs_state[belief.name] = {
                "valid": belief.valid,
                "non_monotonic": belief.non_monotonic,
                "justifications": [],
            }

            for j in belief.justifications:
                justification_data = {
                    "in_beliefs": [repr(b) for b in j.in_list],
                    "out_beliefs": [repr(b) for b in j.out_list],
                    "conclusion": repr(j.conclusion),
                }
                beliefs_state[belief.name]["justifications"].append(justification_data)
                justifications_graph.append(justification_data)

        return {
            "instance_id": instance_id,
            "metadata": self.metadata[instance_id],
            "beliefs": beliefs_state,
            "justifications_graph": justifications_graph,
            "statistics": {
                "total_beliefs": len(jtms.beliefs),
                "valid_beliefs": len(
                    [b for b in jtms.beliefs.values() if b.valid is True]
                ),
                "invalid_beliefs": len(
                    [b for b in jtms.beliefs.values() if b.valid is False]
                ),
                "unknown_beliefs": len(
                    [b for b in jtms.beliefs.values() if b.valid is None]
                ),
                "non_monotonic_beliefs": len(
                    [b for b in jtms.beliefs.values() if b.non_monotonic]
                ),
                "total_justifications": len(justifications_graph),
            },
        }

    async def set_belief_validity(
        self, instance_id: str, belief_name: str, validity: bool
    ) -> Dict[str, Any]:
        """
        Définit la validité d'une croyance et propage les changements.

        Args:
            instance_id: Identifiant de l'instance JTMS
            belief_name: Nom de la croyance
            validity: Nouvelle valeur de validité

        Returns:
            Dict contenant les détails du changement et de la propagation
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        if belief_name not in self.instances[instance_id].beliefs:
            raise ValueError(f"Croyance non trouvée: {belief_name}")

        jtms = self.instances[instance_id]
        old_value = jtms.beliefs[belief_name].valid

        # Définir la nouvelle valeur
        jtms.set_belief_validity(belief_name, validity)

        # Mettre à jour les métadonnées
        self.metadata[instance_id]["last_updated"] = datetime.now().isoformat()

        return {
            "belief_name": belief_name,
            "old_value": old_value,
            "new_value": validity,
            "propagation_occurred": True,
            "timestamp": datetime.now().isoformat(),
        }

    async def remove_belief(self, instance_id: str, belief_name: str) -> Dict[str, Any]:
        """
        Supprime une croyance de l'instance JTMS.

        Args:
            instance_id: Identifiant de l'instance JTMS
            belief_name: Nom de la croyance à supprimer

        Returns:
            Dict confirmant la suppression
        """
        if instance_id not in self.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        jtms = self.instances[instance_id]

        if belief_name not in jtms.beliefs:
            raise ValueError(f"Croyance non trouvée: {belief_name}")

        # Supprimer la croyance
        jtms.remove_belief(belief_name)

        # Mettre à jour les métadonnées
        self.metadata[instance_id]["beliefs_count"] = len(jtms.beliefs)
        self.metadata[instance_id]["last_updated"] = datetime.now().isoformat()

        return {
            "belief_name": belief_name,
            "removed": True,
            "remaining_beliefs": len(jtms.beliefs),
            "timestamp": datetime.now().isoformat(),
        }

    async def export_jtms_state(self, instance_id: str, format: str = "json") -> str:
        """
        Exporte l'état complet de l'instance JTMS dans un format spécifié.

        Args:
            instance_id: Identifiant de l'instance JTMS
            format: Format d'export ('json', 'graphml', 'dot')

        Returns:
            str: Représentation sérialisée de l'état
        """
        state = await self.get_jtms_state(instance_id)

        if format == "json":
            return json.dumps(state, indent=2, ensure_ascii=False)
        elif format == "graphml":
            # Implémentation future pour GraphML
            raise NotImplementedError("Export GraphML non implémenté")
        elif format == "dot":
            # Implémentation future pour DOT (Graphviz)
            raise NotImplementedError("Export DOT non implémenté")
        else:
            raise ValueError(f"Format non supporté: {format}")

    async def import_jtms_state(
        self, session_id: str, state_data: str, format: str = "json"
    ) -> str:
        """
        Importe un état JTMS depuis une représentation sérialisée.

        Args:
            session_id: Identifiant de la session
            state_data: Données sérialisées de l'état
            format: Format des données ('json')

        Returns:
            str: Identifiant de la nouvelle instance créée
        """
        if format != "json":
            raise ValueError(f"Format d'import non supporté: {format}")

        try:
            state = json.loads(state_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Données JSON invalides: {e}")

        # Créer une nouvelle instance
        instance_id = await self.create_jtms_instance(session_id)
        jtms = self.instances[instance_id]

        # Reconstruire l'état
        beliefs_data = state.get("beliefs", {})

        # Créer toutes les croyances d'abord
        for belief_name in beliefs_data:
            jtms.add_belief(belief_name)

        # Ajouter les justifications
        for belief_name, belief_info in beliefs_data.items():
            for justification in belief_info.get("justifications", []):
                jtms.add_justification(
                    justification["in_beliefs"],
                    justification["out_beliefs"],
                    justification["conclusion"],
                )

        # Restaurer les valeurs de validité
        for belief_name, belief_info in beliefs_data.items():
            if belief_info["valid"] is not None:
                jtms.set_belief_validity(belief_name, belief_info["valid"])

        return instance_id

    async def get_instance_ids(self, session_id: Optional[str] = None) -> List[str]:
        """
        Retourne la liste des identifiants d'instances JTMS.

        Args:
            session_id: Filtrer par session (optionnel)

        Returns:
            List[str]: Liste des identifiants d'instances
        """
        if session_id:
            return [
                instance_id
                for instance_id, metadata in self.metadata.items()
                if metadata["session_id"] == session_id
            ]
        else:
            return list(self.instances.keys())

    async def cleanup_instance(self, instance_id: str) -> bool:
        """
        Nettoie une instance JTMS et ses métadonnées.

        Args:
            instance_id: Identifiant de l'instance à nettoyer

        Returns:
            bool: True si nettoyé avec succès
        """
        if instance_id in self.instances:
            del self.instances[instance_id]

        if instance_id in self.metadata:
            del self.metadata[instance_id]

        return True
