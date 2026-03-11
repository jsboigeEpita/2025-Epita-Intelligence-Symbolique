import os
from fastapi import Depends
from argumentation_analysis.orchestration.service_manager import (
    OrchestrationServiceManager,
)
from .services import DungAnalysisService
import logging
import time

# Services globaux pour éviter la réinitialisation
_global_service_manager = None
_global_dung_service = None
_global_mock_service = None


class MockAnalysisService:
    """Service d'analyse mock pour les tests ou en cas de fallback."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.force_mock = True

    async def analyze_text(self, text: str) -> dict:
        start_time = time.time()
        self.logger.info("[API-MOCK] Démarrage analyse mock...")

        # Simuler une détection de base pour "ad hominem"
        fallacies = []
        if "idiot" in text or "menteur" in text:
            fallacies.append(
                {
                    "type": "ad_hominem_potentiel",
                    "description": "Attaque personnelle détectée.",
                    "confidence": 0.9,
                }
            )

        duration = time.time() - start_time
        return {
            "fallacies": fallacies,
            "duration": duration,
            "components_used": ["FallbackAnalyzer"],
            "summary": f"Analyse de fallback terminée. {len(fallacies)} sophismes détectés.",
            "overall_quality": 0.1,
            "argument_structure": "Non analysé (fallback)",
            "suggestions": ["Vérifier la connexion à l'API OpenAI."],
            "authentic_gpt4o_used": False,
            "analysis_metadata": {
                "text_length": len(text),
                "processing_time": duration,
                "model_used": "gpt-5-mini-mock",
                "fallback_reason": "Mode mock forcé via FORCE_MOCK_LLM",
            },
        }

    def is_available(self) -> bool:
        return True

    def get_status_details(self) -> dict:
        return {
            "service_type": "MockAnalysisService",
            "llm_enabled": False,
            "mock_disabled": False,
            "manager_initialized": True,
            "uptime_seconds": 0,
        }


class AnalysisService:
    """Service d'analyse authentique via OrchestrationServiceManager"""

    def __init__(self, manager: OrchestrationServiceManager):
        self.manager = manager
        self.logger = logging.getLogger(__name__)

    async def analyze_text(self, text: str) -> dict:
        """
        Effectue l'analyse authentique du texte via LLM
        """
        start_time = time.time()
        self.logger.info(f"[API] Démarrage analyse authentique : {text[:100]}...")

        try:
            # Utilisation authentique du service manager
            import json

            service_result = await self.manager.analyze_text(text)

            duration = time.time() - start_time
            self.logger.info(f"[API] Analyse terminée en {duration:.2f}s")
            self.logger.debug(f"Résultat brut du ServiceManager: {service_result}")

            # Extraire et parser le résultat du LLM depuis la structure de réponse
            llm_payload = {}
            summary = "Analyse terminée, mais le format du résultat est inattendu."
            fallacies_data = []
            components_used = ["LLM", "OrchestrationServiceManager"]

            try:
                # Naviguer dans la structure pour trouver le résultat JSON string
                specialized_result_str = (
                    service_result.get("results", {})
                    .get("specialized", {})
                    .get("result", "{}")
                )

                # S'assurer que ce n'est pas None et que c'est bien une string
                if isinstance(specialized_result_str, str):
                    # Parser la string JSON en dictionnaire Python
                    llm_payload = json.loads(specialized_result_str)
                elif isinstance(
                    specialized_result_str, dict
                ):  # Au cas où le format changerait
                    llm_payload = specialized_result_str
                else:
                    self.logger.warning(
                        f"Le résultat du LLM n'est ni une string ni un dict: {type(specialized_result_str)}"
                    )

                # Extraire les données du payload parsé
                raw_fallacies = llm_payload.get("fallacies", [])
                if isinstance(raw_fallacies, list):
                    fallacies_data = [
                        {
                            "type": f.get("type", "N/A"),
                            "description": f.get("description", "N/A"),
                            "confidence": f.get("confidence", 0.85),
                        }
                        for f in raw_fallacies
                    ]

                summary = llm_payload.get(
                    "summary",
                    f"Analyse authentique terminée. {len(fallacies_data)} sophismes détectés.",
                )

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.logger.error(f"Erreur en parsant le résultat du LLM: {e}")
                summary = f"Erreur de formatage dans la réponse du service: {e}"

            return {
                "fallacies": fallacies_data,
                "duration": duration,
                "components_used": components_used,
                "summary": summary,
                "overall_quality": llm_payload.get("overall_quality", 0.0),
                "argument_structure": llm_payload.get("argument_structure", "N/A"),
                "suggestions": llm_payload.get("suggestions", []),
                "authentic_gpt4o_used": True,
                "analysis_metadata": {
                    "text_length": len(text),
                    "processing_time": duration,
                    "model_used": "gpt-5-mini",
                    "raw_llm_payload": llm_payload,  # Pour le débogage
                },
            }

        except Exception as e:
            self.logger.error(f"[API] Erreur lors de l'analyse : {e}")
            duration = time.time() - start_time
            return {
                "fallacies": [],
                "duration": duration,
                "components_used": ["ErrorHandler"],
                "summary": f"Erreur lors de l'analyse : {str(e)}",
                "error": str(e),
                "authentic_gpt4o_used": False,
            }

    def is_available(self) -> bool:
        """Vérifie si le service est disponible"""
        return hasattr(self.manager, "_initialized") and self.manager._initialized

    def get_status_details(self) -> dict:
        """Retourne les détails du statut du service"""
        return {
            "service_type": "OrchestrationServiceManager",
            "llm_enabled": True,
            "mock_disabled": True,
            "manager_initialized": self.is_available(),
            "uptime_seconds": (
                getattr(self.manager.state, "get_uptime", lambda: 0)()
                if hasattr(self.manager, "state")
                else 0
            ),
        }


async def get_analysis_service():
    """
    Injection de dépendance pour le service d'analyse authentique.
    Initialise et retourne le service utilisant l'OrchestrationServiceManager.
    Lève une RuntimeError si l'initialisation échoue.
    """
    global _global_service_manager

    if _global_service_manager is None:
        try:
            logging.info("[API] Initialisation du ServiceManager authentique...")
            _global_service_manager = OrchestrationServiceManager()
            await _global_service_manager.initialize()
            if not _global_service_manager.is_ready():
                raise RuntimeError(
                    "Le ServiceManager n'est pas prêt après initialisation."
                )
            logging.info("[API] ServiceManager initialisé avec succès")
        except Exception as e:
            logging.critical(
                f"[API] Échec critique de l'initialisation du ServiceManager: {e}",
                exc_info=True,
            )
            # Ne pas passer en mode mock. L'échec doit être visible.
            raise RuntimeError(
                f"Impossible d'initialiser le service d'analyse authentique: {e}"
            ) from e

    return AnalysisService(_global_service_manager)


async def get_mock_analysis_service() -> MockAnalysisService:
    """
    Injection de dépendance pour obtenir explicitement le service d'analyse mock.
    Utilisé pour les tests unitaires.
    """
    global _global_mock_service
    if _global_mock_service is None:
        logging.info("[API] Initialisation du MockAnalysisService pour les tests.")
        _global_mock_service = MockAnalysisService()
    return _global_mock_service


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

        # La gestion de la JVM est maintenant centralisée dans jvm_setup.
        # Il suffit de s'assurer qu'elle est initialisée.
        from argumentation_analysis.core import jvm_setup

        if not jvm_setup.is_jvm_started():
            if not jvm_setup.initialize_jvm():
                # Lever une exception si l'initialisation échoue,
                # pour que l'erreur soit claire dans les logs.
                raise RuntimeError(
                    "Échec critique de l'initialisation de la JVM pour DungAnalysisService."
                )

        _global_dung_service = DungAnalysisService()
        logging.info("[API] DungAnalysisService initialisé avec succès.")
    return _global_dung_service
