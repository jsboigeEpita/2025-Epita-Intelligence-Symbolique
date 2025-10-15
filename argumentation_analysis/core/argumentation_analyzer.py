"""
Module principal pour l'analyse d'argumentation.

Ce module définit la classe `ArgumentationAnalyzer`, qui est la façade centrale et le point d'entrée principal
pour toutes les opérations d'analyse d'argumentation. Elle orchestre l'utilisation de pipelines,
de services et d'autres composants pour fournir une analyse complète et unifiée.
"""

from typing import Dict, Any, Optional, List
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
                Exemples de clés : 'enable_fallacy_detection', 'enable_rhetorical_analysis'.
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialisation des composants
        self._init_components()

    def _init_components(self):
        """Initialise les composants internes."""
        try:
            # Configuration unifiée
            self.analysis_config = UnifiedAnalysisConfig(
                enable_fallacy_detection=self.config.get(
                    "enable_fallacy_detection", True
                ),
                enable_rhetorical_analysis=self.config.get(
                    "enable_rhetorical_analysis", True
                ),
                enable_logic_analysis=self.config.get("enable_logic_analysis", True),
                enable_semantic_analysis=self.config.get(
                    "enable_semantic_analysis", True
                ),
            )

            # Pipeline unifié
            self.pipeline = UnifiedTextAnalysisPipeline(self.analysis_config)

            # Service d'analyse
            self.analysis_service = AnalysisService()

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

            # Utilisation du pipeline unifié si disponible
            if self.pipeline:
                pipeline_results = self.pipeline.analyze_text(text)
                results["analysis"]["unified"] = pipeline_results

            # Utilisation du service d'analyse si disponible
            if self.analysis_service:
                try:
                    service_results = self.analysis_service.analyze_text(
                        text, options or {}
                    )
                    results["analysis"]["service"] = service_results
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
