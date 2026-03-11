"""
Gestionnaire de Sessions JTMS
Gère le cycle de vie des sessions JTMS avec support de versioning,
checkpoints, rollback et synchronisation multi-agents.
"""

import uuid
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import os

from .jtms_service import JTMSService


class JTMSSessionManager:
    """
    Gestionnaire centralisé pour les sessions JTMS avec support
    de versioning, checkpoints et synchronisation multi-agents.
    """

    def __init__(
        self, jtms_service: JTMSService, storage_path: str = "./logs/sessions"
    ):
        self.jtms_service = jtms_service
        self.jtms_service.session_manager = self  # Injection bidirectionnelle
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        # Sessions actives et métadonnées
        self.sessions: Dict[str, Dict] = {}
        self.checkpoints: Dict[str, List[Dict]] = {}  # session_id -> [checkpoints]
        self.agent_sessions: Dict[str, List[str]] = {}  # agent_id -> [session_ids]

        # Configuration
        self.max_checkpoints_per_session = 10
        self.session_timeout_hours = 24
        self.auto_checkpoint_interval = 300  # 5 minutes

    async def create_session(
        self, agent_id: str, session_name: str = None, metadata: Dict[str, Any] = None
    ) -> str:
        """
        Crée une nouvelle session JTMS pour un agent donné.

        Args:
            agent_id: Identifiant de l'agent (Sherlock/Watson)
            session_name: Nom descriptif de la session
            metadata: Métadonnées additionnelles

        Returns:
            str: Identifiant unique de la session créée
        """
        session_id = f"session_{agent_id}_{uuid.uuid4().hex[:8]}"

        session_data = {
            "session_id": session_id,
            "agent_id": agent_id,
            "session_name": session_name
            or f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "status": "active",
            "metadata": metadata or {},
            "jtms_instances": [],
            "version": 1,
            "checkpoint_count": 0,
        }

        # Stocker la session
        self.sessions[session_id] = session_data
        self.checkpoints[session_id] = []

        # Associer à l'agent
        if agent_id not in self.agent_sessions:
            self.agent_sessions[agent_id] = []
        self.agent_sessions[agent_id].append(session_id)

        # Créer le checkpoint initial
        await self.create_checkpoint(session_id, "session_created", auto_generated=True)

        # Sauvegarder sur disque
        await self._save_session_to_disk(session_id)

        return session_id

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Récupère les détails d'une session spécifique.

        Args:
            session_id: Identifiant de la session

        Returns:
            Dict contenant les détails de la session
        """
        if session_id not in self.sessions:
            # Tentative de chargement depuis le disque
            await self._load_session_from_disk(session_id)

        if session_id not in self.sessions:
            raise ValueError(f"Session non trouvée: {session_id}")

        # Mettre à jour l'accès
        self.sessions[session_id]["last_accessed"] = datetime.now().isoformat()

        # Ajouter les informations sur les instances JTMS
        jtms_instances_info = []
        for instance_id in self.sessions[session_id]["jtms_instances"]:
            if instance_id in self.jtms_service.instances:
                instance_metadata = self.jtms_service.metadata.get(instance_id, {})
                jtms_instances_info.append(
                    {"instance_id": instance_id, "metadata": instance_metadata}
                )

        session_info = self.sessions[session_id].copy()
        session_info["jtms_instances_info"] = jtms_instances_info
        session_info["checkpoint_count"] = len(self.checkpoints.get(session_id, []))

        return session_info

    async def list_sessions(
        self, agent_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Liste les sessions selon les critères spécifiés.

        Args:
            agent_id: Filtrer par agent (optionnel)
            status: Filtrer par statut (optionnel)

        Returns:
            List[Dict]: Liste des sessions correspondantes
        """
        sessions_list = []

        # Charger toutes les sessions depuis le disque si nécessaire
        await self._load_all_sessions()

        for session_id, session_data in self.sessions.items():
            # Appliquer les filtres
            if agent_id and session_data["agent_id"] != agent_id:
                continue
            if status and session_data["status"] != status:
                continue

            # Ajouter les informations enrichies
            session_info = session_data.copy()
            session_info["checkpoint_count"] = len(self.checkpoints.get(session_id, []))
            session_info["jtms_instances_count"] = len(session_data["jtms_instances"])

            sessions_list.append(session_info)

        # Trier par date de création (plus récent en premier)
        sessions_list.sort(key=lambda x: x["created_at"], reverse=True)

        return sessions_list

    async def create_checkpoint(
        self, session_id: str, description: str = None, auto_generated: bool = False
    ) -> str:
        """
        Crée un point de sauvegarde pour une session.

        Args:
            session_id: Identifiant de la session
            description: Description du checkpoint
            auto_generated: Indique si c'est un checkpoint automatique

        Returns:
            str: Identifiant du checkpoint créé
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session non trouvée: {session_id}")

        checkpoint_id = f"cp_{session_id}_{uuid.uuid4().hex[:8]}"

        # Capturer l'état de toutes les instances JTMS de la session
        jtms_states = {}
        for instance_id in self.sessions[session_id]["jtms_instances"]:
            if instance_id in self.jtms_service.instances:
                state = await self.jtms_service.get_jtms_state(instance_id)
                jtms_states[instance_id] = state

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "description": description
            or f"Checkpoint automatique {datetime.now().strftime('%H:%M:%S')}",
            "auto_generated": auto_generated,
            "session_version": self.sessions[session_id]["version"],
            "jtms_states": jtms_states,
            "session_metadata": self.sessions[session_id]["metadata"].copy(),
        }

        # Ajouter le checkpoint
        if session_id not in self.checkpoints:
            self.checkpoints[session_id] = []

        self.checkpoints[session_id].append(checkpoint_data)

        # Limiter le nombre de checkpoints
        if len(self.checkpoints[session_id]) > self.max_checkpoints_per_session:
            # Garder toujours le premier checkpoint (création de session)
            # et supprimer les plus anciens parmi les autres
            non_initial_checkpoints = [
                cp
                for cp in self.checkpoints[session_id]
                if not cp.get("auto_generated")
                or cp["description"] != "session_created"
            ]
            if len(non_initial_checkpoints) > self.max_checkpoints_per_session - 1:
                non_initial_checkpoints.sort(key=lambda x: x["created_at"])
                to_remove = non_initial_checkpoints[
                    : (
                        len(non_initial_checkpoints)
                        - self.max_checkpoints_per_session
                        + 1
                    )
                ]
                for cp_to_remove in to_remove:
                    self.checkpoints[session_id].remove(cp_to_remove)

        # Mettre à jour la session
        self.sessions[session_id]["checkpoint_count"] = len(
            self.checkpoints[session_id]
        )
        self.sessions[session_id]["last_accessed"] = datetime.now().isoformat()

        # Sauvegarder sur disque
        await self._save_checkpoint_to_disk(checkpoint_id, checkpoint_data)
        await self._save_session_to_disk(session_id)

        return checkpoint_id

    async def restore_checkpoint(self, session_id: str, checkpoint_id: str) -> bool:
        """
        Restaure une session à partir d'un checkpoint spécifique.

        Args:
            session_id: Identifiant de la session
            checkpoint_id: Identifiant du checkpoint à restaurer

        Returns:
            bool: True si la restauration a réussi
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session non trouvée: {session_id}")

        if session_id not in self.checkpoints:
            raise ValueError(f"Aucun checkpoint trouvé pour la session: {session_id}")

        # Trouver le checkpoint
        target_checkpoint = None
        for checkpoint in self.checkpoints[session_id]:
            if checkpoint["checkpoint_id"] == checkpoint_id:
                target_checkpoint = checkpoint
                break

        if not target_checkpoint:
            raise ValueError(f"Checkpoint non trouvé: {checkpoint_id}")

        # Nettoyer les instances actuelles
        current_instances = self.sessions[session_id]["jtms_instances"].copy()
        for instance_id in current_instances:
            await self.jtms_service.cleanup_instance(instance_id)

        # Restaurer les instances JTMS depuis le checkpoint
        restored_instances = []
        for old_instance_id, state_data in target_checkpoint["jtms_states"].items():
            # Créer une nouvelle instance avec l'état restauré
            state_json = json.dumps(state_data)
            new_instance_id = await self.jtms_service.import_jtms_state(
                session_id, state_json
            )
            restored_instances.append(new_instance_id)

        # Mettre à jour la session
        self.sessions[session_id]["jtms_instances"] = restored_instances
        self.sessions[session_id]["version"] = target_checkpoint["session_version"]
        self.sessions[session_id]["metadata"] = target_checkpoint[
            "session_metadata"
        ].copy()
        self.sessions[session_id]["last_accessed"] = datetime.now().isoformat()

        # Créer un checkpoint de restauration
        await self.create_checkpoint(
            session_id, f"Restauré depuis {checkpoint_id}", auto_generated=True
        )

        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Supprime définitivement une session et toutes ses données.

        Args:
            session_id: Identifiant de la session à supprimer

        Returns:
            bool: True si la suppression a réussi
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session non trouvée: {session_id}")

        session_data = self.sessions[session_id]
        agent_id = session_data["agent_id"]

        # Nettoyer les instances JTMS
        for instance_id in session_data["jtms_instances"]:
            await self.jtms_service.cleanup_instance(instance_id)

        # Supprimer les checkpoints
        if session_id in self.checkpoints:
            del self.checkpoints[session_id]

        # Retirer de la liste des sessions de l'agent
        if agent_id in self.agent_sessions:
            if session_id in self.agent_sessions[agent_id]:
                self.agent_sessions[agent_id].remove(session_id)
            if not self.agent_sessions[agent_id]:
                del self.agent_sessions[agent_id]

        # Supprimer la session
        del self.sessions[session_id]

        # Supprimer les fichiers sur disque
        await self._delete_session_from_disk(session_id)

        return True

    async def update_session_metadata(
        self, session_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Met à jour les métadonnées d'une session.

        Args:
            session_id: Identifiant de la session
            metadata: Nouvelles métadonnées à fusionner

        Returns:
            bool: True si la mise à jour a réussi
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session non trouvée: {session_id}")

        # Fusionner les métadonnées
        self.sessions[session_id]["metadata"].update(metadata)
        self.sessions[session_id]["last_accessed"] = datetime.now().isoformat()
        self.sessions[session_id]["version"] += 1

        # Sauvegarder sur disque
        await self._save_session_to_disk(session_id)

        return True

    async def add_jtms_instance_to_session(
        self, session_id: str, instance_id: str
    ) -> bool:
        """
        Associe une instance JTMS à une session.

        Args:
            session_id: Identifiant de la session
            instance_id: Identifiant de l'instance JTMS

        Returns:
            bool: True si l'association a réussi
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session non trouvée: {session_id}")

        if instance_id not in self.jtms_service.instances:
            raise ValueError(f"Instance JTMS non trouvée: {instance_id}")

        if instance_id not in self.sessions[session_id]["jtms_instances"]:
            self.sessions[session_id]["jtms_instances"].append(instance_id)
            self.sessions[session_id]["last_accessed"] = datetime.now().isoformat()

            # Sauvegarder sur disque
            await self._save_session_to_disk(session_id)

        return True

    # Méthodes privées pour la persistance

    async def _save_session_to_disk(self, session_id: str):
        """Sauvegarde une session sur disque."""
        session_file = self.storage_path / f"{session_id}.json"
        session_data = self.sessions[session_id].copy()

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    async def _save_checkpoint_to_disk(self, checkpoint_id: str, checkpoint_data: Dict):
        """Sauvegarde un checkpoint sur disque."""
        checkpoint_file = self.storage_path / f"{checkpoint_id}.cp.json"

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

    async def _load_session_from_disk(self, session_id: str):
        """Charge une session depuis le disque."""
        session_file = self.storage_path / f"{session_id}.json"

        if session_file.exists():
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            self.sessions[session_id] = session_data

            # Charger les checkpoints associés
            await self._load_checkpoints_for_session(session_id)

    async def _load_checkpoints_for_session(self, session_id: str):
        """Charge tous les checkpoints d'une session."""
        if session_id not in self.checkpoints:
            self.checkpoints[session_id] = []

        # Rechercher tous les fichiers de checkpoint pour cette session
        checkpoint_files = list(self.storage_path.glob(f"cp_{session_id}_*.cp.json"))

        for checkpoint_file in checkpoint_files:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)

            # Ajouter si pas déjà présent
            if not any(
                cp["checkpoint_id"] == checkpoint_data["checkpoint_id"]
                for cp in self.checkpoints[session_id]
            ):
                self.checkpoints[session_id].append(checkpoint_data)

        # Trier par date de création
        self.checkpoints[session_id].sort(key=lambda x: x["created_at"])

    async def _load_all_sessions(self):
        """Charge toutes les sessions depuis le disque."""
        session_files = list(self.storage_path.glob("session_*.json"))

        for session_file in session_files:
            session_id = session_file.stem
            if session_id not in self.sessions:
                await self._load_session_from_disk(session_id)

    async def _delete_session_from_disk(self, session_id: str):
        """Supprime une session et ses checkpoints du disque."""
        # Supprimer le fichier de session
        session_file = self.storage_path / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # Supprimer tous les checkpoints
        checkpoint_files = list(self.storage_path.glob(f"cp_{session_id}_*.cp.json"))
        for checkpoint_file in checkpoint_files:
            checkpoint_file.unlink()

    async def cleanup_expired_sessions(self):
        """
        Nettoie automatiquement les sessions expirées.

        Returns:
            int: Nombre de sessions nettoyées
        """
        await self._load_all_sessions()

        expired_sessions = []
        cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)

        for session_id, session_data in self.sessions.items():
            last_accessed = datetime.fromisoformat(session_data["last_accessed"])
            if last_accessed < cutoff_time and session_data["status"] != "locked":
                expired_sessions.append(session_id)

        # Supprimer les sessions expirées
        for session_id in expired_sessions:
            await self.delete_session(session_id)

        return len(expired_sessions)
