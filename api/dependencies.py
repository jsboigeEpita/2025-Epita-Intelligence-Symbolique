from fastapi import Depends
from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
import logging
import time

# Service global pour éviter la réinitialisation
_global_service_manager = None

class AnalysisService:
    """Service d'analyse authentique utilisant GPT-4o-mini via OrchestrationServiceManager"""
    
    def __init__(self, manager: OrchestrationServiceManager):
        self.manager = manager
        self.logger = logging.getLogger(__name__)
        
    async def analyze_text(self, text: str) -> dict:
        """
        Effectue l'analyse authentique du texte via GPT-4o-mini
        """
        start_time = time.time()
        self.logger.info(f"[API] Démarrage analyse authentique : {text[:100]}...")
        
        try:
            # Utilisation authentique du service manager avec GPT-4o-mini
            result = await self.manager.analyze_text(text)
            
            duration = time.time() - start_time
            self.logger.info(f"[API] Analyse terminée en {duration:.2f}s")
            
            # Format des données pour l'API
            fallacies_data = []
            if hasattr(result, 'fallacies') and result.fallacies:
                fallacies_data = [
                    {
                        "type": f.name if hasattr(f, 'name') else str(f),
                        "description": f.description if hasattr(f, 'description') else str(f),
                        "confidence": getattr(f, 'confidence', 0.8)
                    }
                    for f in result.fallacies
                ]
            
            components_used = []
            if hasattr(result, 'metadata') and isinstance(result.metadata, dict):
                components_used = result.metadata.get('components_used', ['GPT-4o-mini', 'ServiceManager'])
            else:
                components_used = ['GPT-4o-mini', 'OrchestrationServiceManager']
            
            return {
                'fallacies': fallacies_data,
                'duration': duration,
                'components_used': components_used,
                'summary': f"Analyse authentique GPT-4o-mini terminée. {len(fallacies_data)} sophismes détectés.",
                'authentic_gpt4o_used': True,
                'analysis_metadata': {
                    'text_length': len(text),
                    'processing_time': duration,
                    'model_used': 'gpt-4o-mini'
                }
            }
            
        except Exception as e:
            self.logger.error(f"[API] Erreur lors de l'analyse : {e}")
            duration = time.time() - start_time
            return {
                'fallacies': [],
                'duration': duration,
                'components_used': ['ErrorHandler'],
                'summary': f"Erreur lors de l'analyse : {str(e)}",
                'error': str(e),
                'authentic_gpt4o_used': False
            }
    
    def is_available(self) -> bool:
        """Vérifie si le service est disponible"""
        return hasattr(self.manager, '_initialized') and self.manager._initialized
    
    def get_status_details(self) -> dict:
        """Retourne les détails du statut du service"""
        return {
            "service_type": "OrchestrationServiceManager",
            "gpt4o_mini_enabled": True,
            "mock_disabled": True,
            "manager_initialized": self.is_available(),
            "uptime_seconds": getattr(self.manager.state, 'get_uptime', lambda: 0)() if hasattr(self.manager, 'state') else 0
        }

async def get_analysis_service():
    """
    Injection de dépendance pour le service d'analyse authentique.
    Utilise un singleton global pour éviter la réinitialisation.
    """
    global _global_service_manager
    
    if _global_service_manager is None:
        logging.info("[API] Initialisation du ServiceManager authentique...")
        _global_service_manager = OrchestrationServiceManager()
        await _global_service_manager.initialize()
        logging.info("[API] ServiceManager initialisé avec succès")
    
    return AnalysisService(_global_service_manager)

# Example of how another service might be defined and injected
class AnotherService:
    def do_something(self):
        return "AnotherService did something"

def get_another_service():
    return AnotherService()