"""
Gestionnaire centralisé des ports pour l'application d'analyse argumentative.
Remplace la configuration dispersée des ports dans tout le projet.
"""

import json
import os
import socket
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union


class PortManager:
    """
    Gestionnaire centralisé des ports avec support pour:
    - Configuration JSON centralisée
    - Détection automatique de ports libres
    - Variables d'environnement dynamiques
    - Fallback intelligent
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialise le gestionnaire de ports.

        Args:
            config_path: Chemin vers le fichier de configuration JSON.
                        Par défaut: config/ports.json
        """
        if config_path is None:
            # Trouver le répertoire racine du projet
            current_dir = Path(__file__).parent
            project_root = (
                current_dir.parent.parent
            )  # project_core/config -> project_core -> racine
            config_path = project_root / "config" / "ports.json"

        self.config_path = Path(config_path)
        self.lock_file_path = self.config_path.parent / ".port_lock"
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Charge la configuration depuis le fichier JSON."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration des ports non trouvée: {self.config_path}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Configuration JSON invalide: {e}")

    def get_port(self, service: str, use_fallback: bool = True) -> int:
        """
        Récupère le port pour un service donné.

        Args:
            service: Nom du service (backend, frontend, test.backend, etc.)
            use_fallback: Si True, utilise les ports de fallback si le principal est occupé

        Returns:
            Port disponible

        Raises:
            ValueError: Si le service n'existe pas
            RuntimeError: Si aucun port n'est disponible
        """
        # Navigation dans la configuration avec support pour les sous-clés
        config_parts = service.split(".")
        port_config = self.config["ports"]

        for part in config_parts:
            if part not in port_config:
                raise ValueError(
                    f"Service '{service}' non trouvé dans la configuration"
                )
            port_config = port_config[part]

        # Récupération du port principal
        if isinstance(port_config, dict):
            primary_port = port_config.get("primary")
            fallback_ports = port_config.get("fallback", [])
        else:
            # Configuration simple (juste un numéro)
            primary_port = port_config
            fallback_ports = []

        if primary_port is None:
            raise ValueError(f"Port principal non défini pour le service '{service}'")

        # Test du port principal
        if self.is_port_available(primary_port):
            return primary_port

        # Test des ports de fallback si demandé
        if use_fallback:
            for fallback_port in fallback_ports:
                if self.is_port_available(fallback_port):
                    return fallback_port

        raise RuntimeError(f"Aucun port disponible pour le service '{service}'")

    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """
        Vérifie si un port est disponible.

        Args:
            port: Numéro de port à tester
            host: Hôte à tester (par défaut: localhost)

        Returns:
            True si le port est libre, False sinon
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # 0 = connexion réussie = port occupé
        except Exception:
            return False

    def get_url(self, service: str, endpoint: str = "") -> str:
        """
        Génère une URL complète pour un service.

        Args:
            service: Nom du service (backend, frontend)
            endpoint: Endpoint optionnel à ajouter

        Returns:
            URL complète
        """
        port = self.get_port(service)
        base_url = f"http://localhost:{port}"

        if endpoint:
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint
            base_url += endpoint

        return base_url

    def get_api_base_url(self) -> str:
        """Récupère l'URL de base de l'API."""
        port = self.get_port("backend")
        return f"http://localhost:{port}/api"

    def get_environment_variables(self) -> Dict[str, str]:
        """
        Génère les variables d'environnement basées sur la configuration actuelle.

        Returns:
            Dictionnaire des variables d'environnement
        """
        env_vars = {}
        env_template = self.config.get("environment_variables", {})

        for var_name, template in env_template.items():
            # Remplacement des templates {{service.port}}
            if "{{backend.primary}}" in template:
                backend_port = self.get_port("backend")
                value = template.replace("{{backend.primary}}", str(backend_port))
            elif "{{frontend.primary}}" in template:
                frontend_port = self.get_port("frontend")
                value = template.replace("{{frontend.primary}}", str(frontend_port))
            else:
                value = template

            env_vars[var_name] = value

        return env_vars

    def set_environment_variables(self):
        """
        Configure les variables d'environnement du processus actuel.
        """
        env_vars = self.get_environment_variables()
        for var_name, value in env_vars.items():
            os.environ[var_name] = value

    def find_available_port_range(self, start_port: int, count: int = 1) -> List[int]:
        """
        Trouve une plage de ports consécutifs disponibles.

        Args:
            start_port: Port de départ
            count: Nombre de ports consécutifs requis

        Returns:
            Liste des ports disponibles
        """
        available_ports = []
        current_port = start_port

        while len(available_ports) < count and current_port < 65535:
            if self.is_port_available(current_port):
                available_ports.append(current_port)
            else:
                # Reset si on trouve un port occupé
                available_ports = []
            current_port += 1

        if len(available_ports) < count:
            raise RuntimeError(
                f"Impossible de trouver {count} ports consécutifs à partir de {start_port}"
            )

        return available_ports

    def get_service_info(self, service: str) -> Dict:
        """
        Récupère les informations complètes d'un service.

        Args:
            service: Nom du service

        Returns:
            Dictionnaire avec port, URL, description, etc.
        """
        port = self.get_port(service)

        return {
            "service": service,
            "port": port,
            "url": f"http://localhost:{port}",
            "api_url": f"http://localhost:{port}/api" if service == "backend" else None,
            "available": self.is_port_available(port),
            "description": self._get_service_description(service),
        }

    def _get_service_description(self, service: str) -> str:
        """Récupère la description d'un service."""
        config_parts = service.split(".")
        port_config = self.config["ports"]

        for part in config_parts:
            if part in port_config:
                port_config = port_config[part]

        if isinstance(port_config, dict):
            return port_config.get("description", "Service sans description")
        return "Service simple"

    def list_all_services(self) -> Dict[str, Dict]:
        """
        Liste tous les services configurés avec leurs informations.

        Returns:
            Dictionnaire des services et leurs infos
        """
        services = {}

        def _extract_services(config_dict: Dict, prefix: str = ""):
            for key, value in config_dict.items():
                current_path = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    if "primary" in value or isinstance(value, int):
                        # C'est un service
                        try:
                            services[current_path] = self.get_service_info(current_path)
                        except Exception as e:
                            services[current_path] = {"error": str(e)}
                    else:
                        # Continuer la récursion
                        _extract_services(value, current_path)
                elif isinstance(value, int):
                    # Service simple avec juste un numéro de port
                    try:
                        services[current_path] = self.get_service_info(current_path)
                    except Exception as e:
                        services[current_path] = {"error": str(e)}

        _extract_services(self.config["ports"])
        return services

    def lock_port(self, service: str) -> Optional[int]:
        """Trouve un port disponible, le verrouille dans .port_lock et le retourne."""
        try:
            port = self.get_port(service)
            lock_data = {"service": service, "port": port}
            with open(self.lock_file_path, "w", encoding="utf-8") as f:
                json.dump(lock_data, f)
            return port
        except (RuntimeError, ValueError):
            return None

    def get_locked_info(self) -> Optional[Dict]:
        """Lit les informations de port depuis le fichier .port_lock."""
        if not self.lock_file_path.exists():
            return None
        try:
            with open(self.lock_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def unlock_port(self):
        """Supprime le fichier de verrouillage."""
        if self.lock_file_path.exists():
            self.lock_file_path.unlink()


# Instance globale pour utilisation simple
_port_manager = None


def get_port_manager() -> PortManager:
    """Récupère l'instance globale du gestionnaire de ports."""
    global _port_manager
    if _port_manager is None:
        _port_manager = PortManager()
    return _port_manager


# Fonctions de convenance
def get_backend_port() -> int:
    """Récupère le port du backend."""
    return get_port_manager().get_port("backend")


def get_frontend_port() -> int:
    """Récupère le port du frontend."""
    return get_port_manager().get_port("frontend")


def get_api_base_url() -> str:
    """Récupère l'URL de base de l'API."""
    return get_port_manager().get_api_base_url()


def set_environment_variables():
    """Configure les variables d'environnement avec les ports corrects."""
    get_port_manager().set_environment_variables()


def is_port_available(port: int) -> bool:
    """Vérifie si un port est disponible."""
    return get_port_manager().is_port_available(port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Port Manager CLI")
    parser.add_argument(
        "--export-env",
        action="store_true",
        help="Affiche les variables d'environnement au format KEY=VALUE. Utilise .port_lock si présent.",
    )
    parser.add_argument(
        "--lock-service",
        type=str,
        help="Trouve, verrouille et affiche le port pour le service spécifié.",
    )
    parser.add_argument(
        "--unlock",
        action="store_true",
        help="Supprime le fichier de verrouillage .port_lock.",
    )
    args = parser.parse_args()

    manager = PortManager()

    if args.lock_service:
        port = manager.lock_port(args.lock_service)
        if port:
            print(port)
        else:
            sys.exit(1)

    elif args.unlock:
        manager.unlock_port()
        print("Port unlocked.", file=sys.stdout)

    elif args.export_env:
        env_vars = {}
        locked_info = manager.get_locked_info()

        if locked_info and locked_info.get("service") == "backend":
            # Utilise le port verrouillé pour générer les variables
            locked_port = locked_info["port"]
            env_template = manager.config.get("environment_variables", {})
            for var_name, template in env_template.items():
                value = template.replace("{{backend.primary}}", str(locked_port))
                if "{{frontend.primary}}" in value:
                    # Si le frontend est nécessaire, il faut quand même le chercher
                    frontend_port = manager.get_port("frontend")
                    value = value.replace("{{frontend.primary}}", str(frontend_port))
                env_vars[var_name] = value
        else:
            # Comportement par défaut
            env_vars = manager.get_environment_variables()

        for var, value in env_vars.items():
            print(f"{var}={value}")

    else:
        # Sortie de débogage pour exécution manuelle
        locked_info = manager.get_locked_info()
        if locked_info:
            print(
                f"=== Port Verrouillé: {locked_info['service']} sur le port {locked_info['port']} ==="
            )

        print("\n=== Configuration des Ports (actuellement disponible) ===")
        for service, info in manager.list_all_services().items():
            print(f"{service}: {info}")

        print("\n=== Variables d'environnement (si générées maintenant) ===")
        for var, value in manager.get_environment_variables().items():
            print(f"{var}={value}")

        print(f"\n=== URLs (basées sur les ports disponibles) ===")
        print(f"Backend: {manager.get_url('backend')}")
        print(f"Frontend: {manager.get_url('frontend')}")
        print(f"API: {manager.get_api_base_url()}")
