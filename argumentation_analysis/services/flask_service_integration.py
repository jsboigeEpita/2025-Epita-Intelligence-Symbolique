#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'intégration des services Flask pour l'analyse argumentative.

Ce module fournit une interface unifiée pour intégrer tous les services
critiques dans l'application Flask avec gestion d'erreurs robuste.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import Flask

# Import des services
from .logic_service import LogicService
from ..orchestration.group_chat import GroupChatOrchestration


class FlaskServiceIntegrator:
    """
    Intégrateur de services Flask avec gestion d'erreurs et healthchecks.
    
    Cette classe centralise l'initialisation et la gestion de tous les services
    critiques pour l'application Flask.
    """
    
    def __init__(self, app: Optional[Flask] = None):
        """
        Initialise l'intégrateur de services.
        
        Args:
            app: Instance Flask (optionnelle)
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.services = {}
        self.health_status = {}
        self.initialization_errors = []
        
    def init_app(self, app: Flask) -> bool:
        """
        Initialise tous les services dans l'application Flask.
        
        Args:
            app: Instance Flask
            
        Returns:
            True si l'initialisation réussit
        """
        self.app = app
        self.logger.info("Initialisation des services Flask...")
        
        try:
            # Initialiser LogicService
            if self._init_logic_service():
                self.logger.info("LogicService initialisé avec succès")
            else:
                self.logger.error("Échec de l'initialisation du LogicService")
                
            # Initialiser GroupChatOrchestration
            if self._init_group_chat_orchestration():
                self.logger.info("GroupChatOrchestration initialisé avec succès")
            else:
                self.logger.error("Échec de l'initialisation du GroupChatOrchestration")
                
            # Ajouter les services à l'app Flask
            self._register_services_to_app()
            
            # Ajouter les routes de monitoring
            self._register_health_routes()
            
            # Effectuer le healthcheck initial
            self._perform_initial_healthcheck()
            
            success_count = len([s for s in self.health_status.values() if s.get('status') == 'healthy'])
            total_count = len(self.services)
            
            self.logger.info(f"Services initialisés: {success_count}/{total_count}")
            return success_count == total_count
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'initialisation des services: {e}")
            self.initialization_errors.append(str(e))
            return False
    
    def _init_logic_service(self) -> bool:
        """Initialise le service de logique."""
        try:
            logic_service = LogicService()
            
            # Configuration et initialisation
            if logic_service.initialize_logic_agents():
                self.services['logic_service'] = logic_service
                self.health_status['logic_service'] = {
                    'status': 'healthy',
                    'last_check': datetime.now().isoformat(),
                    'service_type': 'LogicService'
                }
                return True
            else:
                self.health_status['logic_service'] = {
                    'status': 'unhealthy',
                    'last_check': datetime.now().isoformat(),
                    'error': 'Échec de l\'initialisation des agents logiques'
                }
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du LogicService: {e}")
            self.health_status['logic_service'] = {
                'status': 'error',
                'last_check': datetime.now().isoformat(),
                'error': str(e)
            }
            return False
    
    def _init_group_chat_orchestration(self) -> bool:
        """Initialise le service d'orchestration de groupe chat."""
        try:
            orchestration_service = GroupChatOrchestration()
            
            # Test de fonctionnement
            test_session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if orchestration_service.initialize_session(test_session_id, {}):
                # Nettoyage du test
                orchestration_service.cleanup_session()
                
                self.services['group_chat_orchestration'] = orchestration_service
                self.health_status['group_chat_orchestration'] = {
                    'status': 'healthy',
                    'last_check': datetime.now().isoformat(),
                    'service_type': 'GroupChatOrchestration'
                }
                return True
            else:
                self.health_status['group_chat_orchestration'] = {
                    'status': 'unhealthy',
                    'last_check': datetime.now().isoformat(),
                    'error': 'Échec de l\'initialisation de session test'
                }
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du GroupChatOrchestration: {e}")
            self.health_status['group_chat_orchestration'] = {
                'status': 'error',
                'last_check': datetime.now().isoformat(),
                'error': str(e)
            }
            return False
    
    def _register_services_to_app(self):
        """Enregistre les services dans l'app Flask."""
        if not self.app:
            raise ValueError("App Flask non initialisée")
            
        # Enregistrer LogicService
        if 'logic_service' in self.services:
            self.app.logic_service = self.services['logic_service']
            
        # Enregistrer GroupChatOrchestration
        if 'group_chat_orchestration' in self.services:
            self.app.group_chat_orchestration = self.services['group_chat_orchestration']
            
        # Enregistrer l'intégrateur lui-même pour le monitoring
        self.app.service_integrator = self
        
        self.logger.info("Services enregistrés dans l'app Flask")
    
    def _register_health_routes(self):
        """Enregistre les routes de monitoring de santé."""
        if not self.app:
            return
            
        @self.app.route('/health')
        def health_check():
            """Route de vérification de santé globale."""
            return self.get_health_status()
            
        @self.app.route('/health/services')
        def services_health():
            """Route de vérification détaillée des services."""
            return self.get_detailed_health_status()
            
        @self.app.route('/health/services/<service_name>')
        def service_health(service_name):
            """Route de vérification d'un service spécifique."""
            return self.get_service_health(service_name)
    
    def _perform_initial_healthcheck(self):
        """Effectue un healthcheck initial de tous les services."""
        self.logger.info("Exécution du healthcheck initial...")
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'get_service_status'):
                    status = service.get_service_status()
                    self.health_status[service_name].update({
                        'detailed_status': status,
                        'last_healthcheck': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                self.logger.error(f"Erreur lors du healthcheck de {service_name}: {e}")
                self.health_status[service_name]['status'] = 'error'
                self.health_status[service_name]['error'] = str(e)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Retourne le statut de santé global.
        
        Returns:
            Dictionnaire du statut de santé
        """
        healthy_services = [
            name for name, status in self.health_status.items() 
            if status.get('status') == 'healthy'
        ]
        
        total_services = len(self.health_status)
        is_healthy = len(healthy_services) == total_services
        
        return {
            'status': 'healthy' if is_healthy else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'services_count': {
                'total': total_services,
                'healthy': len(healthy_services),
                'unhealthy': total_services - len(healthy_services)
            },
            'services': list(self.health_status.keys()),
            'initialization_errors': self.initialization_errors
        }
    
    def get_detailed_health_status(self) -> Dict[str, Any]:
        """
        Retourne le statut de santé détaillé de tous les services.
        
        Returns:
            Dictionnaire détaillé du statut
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'services': self.health_status.copy(),
            'initialization_errors': self.initialization_errors
        }
    
    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """
        Retourne le statut de santé d'un service spécifique.
        
        Args:
            service_name: Nom du service
            
        Returns:
            Statut du service ou erreur 404
        """
        if service_name not in self.health_status:
            return {
                'error': f'Service {service_name} non trouvé',
                'available_services': list(self.health_status.keys())
            }
            
        return {
            'service_name': service_name,
            'timestamp': datetime.now().isoformat(),
            **self.health_status[service_name]
        }
    
    def refresh_health_status(self) -> Dict[str, Any]:
        """
        Rafraîchit et retourne le statut de santé de tous les services.
        
        Returns:
            Statut de santé rafraîchi
        """
        self._perform_initial_healthcheck()
        return self.get_health_status()
    
    def get_service(self, service_name: str) -> Any:
        """
        Retourne une instance de service.
        
        Args:
            service_name: Nom du service
            
        Returns:
            Instance du service ou None
        """
        return self.services.get(service_name)
    
    def is_service_healthy(self, service_name: str) -> bool:
        """
        Vérifie si un service est en bonne santé.
        
        Args:
            service_name: Nom du service
            
        Returns:
            True si le service est sain
        """
        status = self.health_status.get(service_name, {})
        return status.get('status') == 'healthy'


# Instance globale pour l'intégration
service_integrator = FlaskServiceIntegrator()


def init_flask_services(app: Flask) -> bool:
    """
    Fonction utilitaire pour initialiser tous les services Flask.
    
    Args:
        app: Instance Flask
        
    Returns:
        True si l'initialisation réussit
    """
    return service_integrator.init_app(app)


def get_flask_service(service_name: str) -> Any:
    """
    Fonction utilitaire pour récupérer un service.
    
    Args:
        service_name: Nom du service
        
    Returns:
        Instance du service
    """
    return service_integrator.get_service(service_name)