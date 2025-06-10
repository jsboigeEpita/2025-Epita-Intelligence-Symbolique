"""
Module principal pour l'analyse d'argumentation.

Ce module fournit la classe ArgumentationAnalyzer qui sert de point d'entrée
principal pour toutes les analyses d'argumentation du projet.
"""

from typing import Dict, Any, Optional, List
import logging

# Import des composants existants
from .shared_state import RhetoricalAnalysisState
from ..pipelines.unified_text_analysis import UnifiedTextAnalysisPipeline, UnifiedAnalysisConfig
from ..services.web_api.services.analysis_service import AnalysisService


class ArgumentationAnalyzer:
    """
    Analyseur principal d'argumentation.
    
    Cette classe sert de façade pour tous les services d'analyse d'argumentation
    disponibles dans le projet. Elle coordonne les différents analyseurs
    spécialisés et fournit une interface unifiée.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise l'analyseur d'argumentation.
        
        Args:
            config: Configuration optionnelle pour l'analyseur
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
                enable_fallacy_detection=self.config.get('enable_fallacy_detection', True),
                enable_rhetorical_analysis=self.config.get('enable_rhetorical_analysis', True),
                enable_logic_analysis=self.config.get('enable_logic_analysis', True),
                enable_semantic_analysis=self.config.get('enable_semantic_analysis', True)
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
    
    def analyze_text(self, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyse un texte pour identifier les arguments et sophismes.
        
        Args:
            text: Le texte à analyser
            options: Options d'analyse optionnelles
            
        Returns:
            Dictionnaire contenant les résultats d'analyse
        """
        if not text or not text.strip():
            return {
                'error': 'Texte vide ou invalide',
                'status': 'failed'
            }
        
        try:
            results = {
                'status': 'success',
                'text': text,
                'analysis': {}
            }
            
            # Utilisation du pipeline unifié si disponible
            if self.pipeline:
                pipeline_results = self.pipeline.analyze_text(text)
                results['analysis']['unified'] = pipeline_results
            
            # Utilisation du service d'analyse si disponible
            if self.analysis_service:
                try:
                    service_results = self.analysis_service.analyze_text(text, options or {})
                    results['analysis']['service'] = service_results
                except Exception as e:
                    self.logger.warning(f"Erreur service d'analyse : {e}")
            
            # Analyse basique si les composants ne sont pas disponibles
            if not results['analysis']:
                results['analysis']['basic'] = self._basic_analysis(text)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse : {e}")
            return {
                'error': f'Erreur d\'analyse : {str(e)}',
                'status': 'failed'
            }
    
    def _basic_analysis(self, text: str) -> Dict[str, Any]:
        """
        Analyse basique en mode dégradé.
        
        Args:
            text: Le texte à analyser
            
        Returns:
            Résultats d'analyse basique
        """
        return {
            'text_length': len(text),
            'word_count': len(text.split()),
            'sentences': text.count('.') + text.count('!') + text.count('?'),
            'analysis_type': 'basic_fallback',
            'message': 'Analyse basique - composants avancés non disponibles'
        }
    
    def get_available_features(self) -> List[str]:
        """
        Retourne la liste des fonctionnalités disponibles.
        
        Returns:
            Liste des fonctionnalités disponibles
        """
        features = []
        
        if self.pipeline:
            features.append('unified_pipeline')
        
        if self.analysis_service:
            features.append('analysis_service')
        
        features.append('basic_analysis')
        
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
        Valide la configuration actuelle.
        
        Returns:
            Dictionnaire avec le statut de validation
        """
        validation = {
            'status': 'valid',
            'components': {},
            'warnings': []
        }
        
        validation['components']['pipeline'] = self.pipeline is not None
        validation['components']['analysis_service'] = self.analysis_service is not None
        
        if not self.pipeline:
            validation['warnings'].append('Pipeline unifié non disponible')
        
        if not self.analysis_service:
            validation['warnings'].append('Service d\'analyse non disponible')
        
        if validation['warnings']:
            validation['status'] = 'partial'
        
        return validation


# Alias pour compatibilité
Analyzer = ArgumentationAnalyzer