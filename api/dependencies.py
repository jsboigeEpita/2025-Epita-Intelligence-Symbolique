from fastapi import Depends
from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
from .services import DungAnalysisService
import logging
import time

# Services globaux pour éviter la réinitialisation
_global_service_manager = None
_global_dung_service = None

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
            import json
            service_result = await self.manager.analyze_text(text)
            
            duration = time.time() - start_time
            self.logger.info(f"[API] Analyse terminée en {duration:.2f}s")
            self.logger.debug(f"Résultat brut du ServiceManager: {service_result}")

            # Extraire et parser le résultat du LLM depuis la structure de réponse
            llm_payload = {}
            summary = "Analyse terminée, mais le format du résultat est inattendu."
            fallacies_data = []
            components_used = ['GPT-4o-mini', 'OrchestrationServiceManager']

            try:
                # Naviguer dans la structure pour trouver le résultat JSON string
                specialized_result_str = service_result.get('results', {}).get('specialized', {}).get('result', '{}')
                
                # S'assurer que ce n'est pas None et que c'est bien une string
                if isinstance(specialized_result_str, str):
                    # Parser la string JSON en dictionnaire Python
                    llm_payload = json.loads(specialized_result_str)
                elif isinstance(specialized_result_str, dict): # Au cas où le format changerait
                    llm_payload = specialized_result_str
                else:
                    self.logger.warning(f"Le résultat du LLM n'est ni une string ni un dict: {type(specialized_result_str)}")

                # Extraire les données du payload parsé
                raw_fallacies = llm_payload.get('fallacies', [])
                if isinstance(raw_fallacies, list):
                     fallacies_data = [
                        {
                            "type": f.get("type", "N/A"),
                            "description": f.get("description", "N/A"),
                            "confidence": f.get("confidence", 0.85)
                        }
                        for f in raw_fallacies
                    ]

                summary = llm_payload.get('summary', f"Analyse authentique GPT-4o-mini terminée. {len(fallacies_data)} sophismes détectés.")

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.logger.error(f"Erreur en parsant le résultat du LLM: {e}")
                summary = f"Erreur de formatage dans la réponse du service: {e}"
            
            return {
                'fallacies': fallacies_data,
                'duration': duration,
                'components_used': components_used,
                'summary': summary,
                'overall_quality': llm_payload.get('overall_quality', 0.0),
                'argument_structure': llm_payload.get('argument_structure', "N/A"),
                'suggestions': llm_payload.get('suggestions', []),
                'authentic_gpt4o_used': True,
                'analysis_metadata': {
                    'text_length': len(text),
                    'processing_time': duration,
                    'model_used': 'gpt-4o-mini',
                    'raw_llm_payload': llm_payload # Pour le débogage
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


def get_dung_analysis_service() -> DungAnalysisService:
    """
    Injection de dépendance pour le service d'analyse de Dung.
    Utilise un singleton global pour instancier le service (et la JVM) une seule fois.
    """
    global _global_dung_service
    if _global_dung_service is None:
        logging.info("[API] Initialisation du DungAnalysisService...")
        import jpype
        import jpype.imports
        from argumentation_analysis.core.orchestration.jpype_manager import JPypeManager
        
        if not jpype.isJVMStarted():
            # Instance du manager pour la configuration centralisée
            jpype_manager = JPypeManager()
            
            # Définir le chemin vers les fichiers JAR
            jpype_manager.set_jars_path('libs/java')
            
            # Lancer la JVM avec la configuration du manager
            jpype_manager.start_jvm()

        _global_dung_service = DungAnalysisService()
        logging.info("[API] DungAnalysisService initialisé avec succès.")
    return _global_dung_service