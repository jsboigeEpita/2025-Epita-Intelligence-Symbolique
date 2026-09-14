"""
Module principal pour l'analyse d'argumentation.

Ce module définit la classe `ArgumentationAnalyzer`, qui est la façade centrale et le point d'entrée principal
pour toutes les opérations d'analyse d'argumentation. Elle orchestre l'utilisation de pipelines,
de services et d'autres composants pour fournir une analyse complète et unifiée.
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging

# Import des composants existants
from .shared_state import RhetoricalAnalysisState
from argumentation_analysis.pipelines.unified_text_analysis import (
    UnifiedTextAnalysisPipeline,
    UnifiedAnalysisConfig,
)
from argumentation_analysis.services.web_api.services.analysis_service import (
    AnalysisService,
)
from argumentation_analysis.services.web_api.models.request_models import (
    AnalysisRequest,
    AnalysisOptions,
)
from argumentation_analysis.core.llm_service import create_llm_service


class ArgumentationAnalyzer:
    """
    Analyseur d'argumentation principal agissant comme une façade.

    Cette classe orchestre les différents composants d'analyse (pipelines, services)
    pour fournir une interface unifiée et robuste. Elle est conçue pour être le point
    d'entrée unique pour l'analyse de texte et peut être configurée pour utiliser
    différentes stratégies d'analyse.

    Attributs:
        config (Dict[str, Any]): Dictionnaire de configuration.
        logger (logging.Logger): Logger pour les messages de diagnostic.
        analysis_config (UnifiedAnalysisConfig): Configuration pour le pipeline unifié.
        pipeline (UnifiedTextAnalysisPipeline): Pipeline d'analyse de texte.
        analysis_service (AnalysisService): Service d'analyse externe.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'analyseur d'argumentation.

        Le constructeur met en place la configuration, le logger et initialise
        les composants internes comme le pipeline et les services d'analyse.
        En cas d'échec de l'initialisation d'un composant, l'analyseur passe en mode dégradé.

        Args:
            config (Optional[Dict[str, Any]]):
                Un dictionnaire de configuration pour surcharger les paramètres par défaut.
                Exemples de clés : 'enable_fallacy_detection',
                'enable_rhetorical_analysis', 'enable_logic_analysis'
                (mappées sur les modes "informal"/"formal" de UnifiedAnalysisConfig).
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialisation des composants
        self._init_components()

    def _init_components(self):
        """Initialise les composants internes."""
        try:
            # Configuration unifiée — #2097 : les quatre clés enable_* passées
            # ici n'existent pas sur UnifiedAnalysisConfig (TypeError avalée
            # par le except : le mode dégradé tuait aussi le service, sain ou
            # non). Mapping réel : "informal" couvre fallacy + rhetorical,
            # "formal" couvre logic ; "enable_semantic_analysis" n'a pas
            # d'équivalent et n'est plus accepté.
            modes = []
            if self.config.get("enable_fallacy_detection", True) or self.config.get(
                "enable_rhetorical_analysis", True
            ):
                modes.append("informal")
            if self.config.get("enable_logic_analysis", True):
                modes.append("formal")
            self.analysis_config = UnifiedAnalysisConfig(analysis_modes=modes)

            # Pipeline unifié
            self.pipeline = UnifiedTextAnalysisPipeline(self.analysis_config)

            # Service d'analyse — #2097 : le ctor nu `AnalysisService()` levait
            # TypeError (llm_service requis) avalée par le except ci-dessous →
            # mode dégradé silencieux sur tout siège sain. Câblage en miroir de
            # mcp_server/main.py (#1864) : un service LLM par consommateur via
            # la fabrique canonique, pas de défaut `= None` (ça déplacerait la
            # panne du démarrage vers le premier appel réel).
            analysis_llm = create_llm_service(service_id="argumentation_analyzer")
            self.analysis_service = AnalysisService(llm_service=analysis_llm)

            self.logger.info("ArgumentationAnalyzer initialisé avec succès")

        except Exception as e:
            self.logger.warning(f"Erreur lors de l'initialisation des composants : {e}")
            # Initialisation en mode dégradé
            self.pipeline = None
            self.analysis_service = None

    def analyze_text(
        self, text: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyse un texte pour identifier les arguments, sophismes et autres structures rhétoriques.

        Cette méthode est le point d'entrée principal pour l'analyse. Elle utilise les composants
        internes (pipeline, service) pour effectuer une analyse complète. Si les composants
        principaux ne sont pas disponibles, elle se rabat sur une analyse basique.

        Args:
            text (str): Le texte à analyser.
            options (Optional[Dict[str, Any]]):
                Options d'analyse supplémentaires à passer aux services sous-jacents.

        Returns:
            Dict[str, Any]: Un dictionnaire contenant les résultats de l'analyse,
                            structuré comme suit :
                            {
                                'status': 'success' | 'failed' | 'partial',
                                'text': Le texte original,
                                'analysis': {
                                    'unified': (résultats du pipeline),
                                    'service': (résultats du service),
                                    'basic': (résultats de l'analyse de fallback)
                                },
                                'error': (message d'erreur si le statut est 'failed')
                            }
        """
        if not text or not text.strip():
            return {"error": "Texte vide ou invalide", "status": "failed"}

        try:
            results = {"status": "success", "text": text, "analysis": {}}

            # Utilisation du pipeline unifié si disponible — #2097 : le
            # pipeline réel expose ``initialize()`` puis
            # ``analyze_text_unified(text)`` (les deux async) ; l'ancien appel
            # ``analyze_text(text)`` visait une méthode inexistante et tuait
            # toute l'analyse dans le except externe, service compris. Chaque
            # composant se dégrade désormais individuellement.
            if self.pipeline:
                try:

                    async def _run_pipeline() -> Dict[str, Any]:
                        if not self.pipeline.initialized:
                            if not await self.pipeline.initialize():
                                raise RuntimeError(
                                    "initialisation du pipeline unifié échouée"
                                )
                        return await self.pipeline.analyze_text_unified(text)

                    results["analysis"]["unified"] = asyncio.run(_run_pipeline())
                except Exception as e:
                    self.logger.warning(f"Erreur pipeline unifié : {e}")

            # Utilisation du service d'analyse si disponible — #2097 : le
            # service réel expose ``async analyze_text(request: AnalysisRequest)`` ;
            # l'ancien appel ``analyze_text(text, options)`` levait TypeError au
            # premier appel — la panne déplacée du démarrage vers l'usage,
            # exactement ce que #1864 interdit. La façade est synchrone :
            # ``asyncio.run`` est le pont ; depuis un event loop vivant il
            # lève et le service se dégrade proprement (warning + fallback).
            if self.analysis_service:
                try:
                    request = AnalysisRequest(
                        text=text, options=AnalysisOptions(**(options or {}))
                    )
                    response = asyncio.run(self.analysis_service.analyze_text(request))
                    results["analysis"]["service"] = response.model_dump(mode="json")
                except Exception as e:
                    self.logger.warning(f"Erreur service d'analyse : {e}")

            # Analyse basique si les composants ne sont pas disponibles
            if not results["analysis"]:
                results["analysis"]["basic"] = self._basic_analysis(text)

            return results

        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse : {e}")
            return {"error": f"Erreur d'analyse : {str(e)}", "status": "failed"}

    def _basic_analysis(self, text: str) -> Dict[str, Any]:
        """
        Analyse basique en mode dégradé.

        Args:
            text: Le texte à analyser

        Returns:
            Résultats d'analyse basique
        """
        return {
            "text_length": len(text),
            "word_count": len(text.split()),
            "sentences": text.count(".") + text.count("!") + text.count("?"),
            "analysis_type": "basic_fallback",
            "message": "Analyse basique - composants avancés non disponibles",
        }

    def get_available_features(self) -> List[str]:
        """
        Retourne la liste des fonctionnalités d'analyse actuellement disponibles.

        Une fonctionnalité est "disponible" si le composant correspondant a été
        initialisé avec succès.

        Returns:
            List[str]: Une liste de chaînes de caractères identifiant les
                         fonctionnalités disponibles.
                         - 'unified_pipeline': Le pipeline d'analyse complet est actif.
                         - 'analysis_service': Le service d'analyse externe est accessible.
                         - 'basic_analysis': L'analyse de base est toujours disponible en fallback.
        """
        features = []

        if self.pipeline:
            features.append("unified_pipeline")

        if self.analysis_service:
            features.append("analysis_service")

        features.append("basic_analysis")

        return features

    def create_analysis_state(self) -> RhetoricalAnalysisState:
        """
        Crée un nouvel état d'analyse rhétorique.

        Returns:
            Instance de RhetoricalAnalysisState
        """
        return RhetoricalAnalysisState()

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Valide la configuration actuelle de l'analyseur et l'état de ses composants.

        Cette méthode vérifie que les composants essentiels (pipeline, service) sont
        correctement initialisés.

        Returns:
            Dict[str, Any]: Un dictionnaire décrivant l'état de la validation.
                            {
                                'status': 'valid' | 'partial',
                                'components': {
                                    'pipeline': (bool),
                                    'analysis_service': (bool)
                                },
                                'warnings': (List[str])
                            }
        """
        validation = {"status": "valid", "components": {}, "warnings": []}

        validation["components"]["pipeline"] = self.pipeline is not None
        validation["components"]["analysis_service"] = self.analysis_service is not None

        if not self.pipeline:
            validation["warnings"].append("Pipeline unifié non disponible")

        if not self.analysis_service:
            validation["warnings"].append("Service d'analyse non disponible")

        if validation["warnings"]:
            validation["status"] = "partial"

        return validation


# Alias pour compatibilité
Analyzer = ArgumentationAnalyzer
