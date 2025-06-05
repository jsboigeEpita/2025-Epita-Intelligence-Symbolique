#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service d'analyse complète utilisant le moteur d'analyse argumentative.
"""

import time
import logging
from typing import Dict, List, Any, Optional
import semantic_kernel as sk

# Imports du moteur d'analyse (style b282af4 avec gestion d'erreur)
try:
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent as InformalAgent
    from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
    from argumentation_analysis.core.llm_service import create_llm_service # Ajouté
    from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path # Ajouté
except ImportError as e:
    logging.warning(f"Impossible d'importer les modules d'analyse ou llm_service/taxonomy_loader: {e}")
    # Mode dégradé pour les tests
    InformalAgent = None
    ComplexFallacyAnalyzer = None
    ContextualFallacyAnalyzer = None
    FallacySeverityEvaluator = None
    OperationalManager = None

# Imports des modèles (style HEAD)
from argumentation_analysis.services.web_api.models.request_models import AnalysisRequest
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse, FallacyDetection, ArgumentStructure
)

logger = logging.getLogger("AnalysisService")


class AnalysisService:
    """
    Service pour l'analyse complète de textes argumentatifs.
    
    Ce service utilise le moteur d'analyse existant pour fournir
    une analyse complète incluant la détection de sophismes,
    l'analyse de structure et l'évaluation de cohérence.
    """
    
    def __init__(self):
        """Initialise le service d'analyse."""
        self.logger = logger
        self.is_initialized = False
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialise les composants d'analyse internes du service.

        Tente d'instancier `ComplexFallacyAnalyzer`, `ContextualFallacyAnalyzer`,
        `FallacySeverityEvaluator`, et `InformalAgent`.
        Met à jour `self.is_initialized` en fonction du succès.

        :return: None
        :rtype: None
        """
        try:
            # Initialisation des analyseurs
            if ComplexFallacyAnalyzer:
                self.complex_analyzer = ComplexFallacyAnalyzer()
            else:
                self.complex_analyzer = None
                
            if ContextualFallacyAnalyzer:
                self.contextual_analyzer = ContextualFallacyAnalyzer()
            else:
                self.contextual_analyzer = None
                
            if FallacySeverityEvaluator:
                self.severity_evaluator = FallacySeverityEvaluator()
            else:
                self.severity_evaluator = None
            
            # Configuration des outils pour l'agent informel
            self.tools = {}
            if self.complex_analyzer:
                self.tools['complex_fallacy_analyzer'] = self.complex_analyzer
            if self.contextual_analyzer:
                self.tools['contextual_fallacy_analyzer'] = self.contextual_analyzer
            if self.severity_evaluator:
                self.tools['fallacy_severity_evaluator'] = self.severity_evaluator
            
            # Initialisation de l'agent informel (version b282af4)
            if InformalAgent:
                # Création du kernel et ajout du service LLM
                kernel = sk.Kernel()
                llm_service = None
                if create_llm_service:
                    try:
                        llm_service = create_llm_service(service_id="default_analysis_llm")
                        kernel.add_service(llm_service)
                        self.logger.info("Service LLM créé et ajouté au kernel pour AnalysisService.")
                    except Exception as llm_e:
                        self.logger.error(f"Erreur lors de la création ou de l'ajout du service LLM: {llm_e}")
                else:
                    self.logger.error("create_llm_service non disponible.")

                taxonomy_path = None
                if get_taxonomy_path:
                    try:
                        taxonomy_path = get_taxonomy_path()
                        self.logger.info(f"Chemin de la taxonomie obtenu: {taxonomy_path}")
                    except Exception as tax_e:
                        self.logger.error(f"Erreur lors de l'obtention du chemin de la taxonomie: {tax_e}")
                else:
                    self.logger.error("get_taxonomy_path non disponible.")
                
                if kernel and llm_service: # S'assurer que le kernel et le service LLM sont prêts
                    self.informal_agent = InformalAgent(
                        kernel=kernel,
                        agent_name="web_api_informal_agent", # Utilisation de agent_name
                        taxonomy_file_path=str(taxonomy_path) if taxonomy_path else None # Passer le chemin de la taxonomie
                    )
                    # Configurer les composants de l'agent (plugins, fonctions sémantiques)
                    # L'ID du service LLM est nécessaire ici. create_llm_service devrait le retourner ou le rendre accessible.
                    # Supposons que l'ID est "default_analysis_llm" comme utilisé ci-dessus.
                    try:
                        self.informal_agent.setup_agent_components(llm_service_id="default_analysis_llm")
                        self.logger.info("Composants de InformalAgent configurés.")
                    except Exception as setup_e:
                        self.logger.error(f"Erreur lors de la configuration des composants de InformalAgent: {setup_e}")
                        self.informal_agent = None # Invalider l'agent si la configuration échoue
                else:
                    self.logger.error("Kernel ou LLM Service non initialisé, impossible de créer InformalAgent.")
                    self.informal_agent = None
            else:
                self.informal_agent = None
                self.logger.warning("Classe InformalAgent non disponible.")
            
            self.is_initialized = True # Peut-être conditionner cela au succès de l'init de l'agent
            if self.informal_agent:
                self.logger.info("Service d'analyse initialisé avec succès (avec InformalAgent).")
            else:
                self.logger.warning("Service d'analyse initialisé, mais InformalAgent n'a pas pu être créé/configuré.")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            self.is_initialized = False
    
    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service d'analyse.

        :return: True si le service est initialisé et qu'au moins un composant
                 d'analyse (agent informel ou analyseur spécifique) est disponible,
                 False sinon.
        :rtype: bool
        """
        return self.is_initialized and (
            self.informal_agent is not None or
            any([self.complex_analyzer, self.contextual_analyzer, self.severity_evaluator])
        )
    
    def analyze_text(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Effectue une analyse complète d'un texte argumentatif.

        Orchestre la détection de sophismes, l'analyse de la structure argumentative,
        et le calcul de métriques globales comme la qualité et la cohérence.

        :param request: L'objet `AnalysisRequest` contenant le texte à analyser
                        et les options d'analyse.
        :type request: AnalysisRequest
        :return: Un objet `AnalysisResponse` contenant les résultats de l'analyse.
                 En cas d'échec d'initialisation du service, une réponse de fallback
                 est retournée.
        :rtype: AnalysisResponse
        """
        start_time = time.time()
        
        try:
            # Vérification de l'état du service
            if not self.is_healthy():
                return self._create_fallback_response(request, start_time)
            
            # Analyse des sophismes
            fallacies = self._detect_fallacies(request.text, request.options)
            
            # Analyse de la structure argumentative
            structure = self._analyze_structure(request.text, request.options)
            
            # Calcul des métriques globales
            overall_quality = self._calculate_overall_quality(fallacies, structure)
            coherence_score = self._calculate_coherence_score(structure)
            
            processing_time = time.time() - start_time
            
            return AnalysisResponse(
                success=True,
                text_analyzed=request.text,
                fallacies=fallacies,
                argument_structure=structure,
                overall_quality=overall_quality,
                coherence_score=coherence_score,
                fallacy_count=len(fallacies),
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {}
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {e}")
            processing_time = time.time() - start_time
            
            return AnalysisResponse(
                success=False,
                text_analyzed=request.text,
                fallacies=[],
                argument_structure=None,
                overall_quality=0.0,
                coherence_score=0.0,
                fallacy_count=0,
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {}
            )
    
    def _detect_fallacies(self, text: str, options: Optional[Any]) -> List[FallacyDetection]:
        """Détecte les sophismes dans le texte en utilisant les analyseurs disponibles.

        Utilise `self.informal_agent` si disponible, sinon `self.contextual_analyzer`.
        Filtre les résultats en fonction du `severity_threshold` des options.

        :param text: Le texte à analyser.
        :type text: str
        :param options: Les options d'analyse (par exemple, `AnalysisOptions` ou `FallacyOptions`)
                        pouvant contenir `severity_threshold`.
        :type options: Optional[Any]
        :return: Une liste d'objets `FallacyDetection`.
        :rtype: List[FallacyDetection]
        """
        fallacies = []
        
        try:
            # Utilisation de l'agent informel si disponible
            if self.informal_agent:
                result = self.informal_agent.analyze_text(text) # La signature de analyze_text peut varier
                if result and 'fallacies' in result:
                    for fallacy_data in result['fallacies']:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get('type', 'unknown'),
                            name=fallacy_data.get('name', 'Sophisme non identifié'),
                            description=fallacy_data.get('description', ''),
                            severity=fallacy_data.get('severity', 0.5),
                            confidence=fallacy_data.get('confidence', 0.5),
                            location=fallacy_data.get('location'),
                            context=fallacy_data.get('context'),
                            explanation=fallacy_data.get('explanation')
                        )
                        fallacies.append(fallacy)
            
            # Analyse contextuelle si disponible et si l'agent informel n'a pas été utilisé ou n'a rien retourné
            elif self.contextual_analyzer:
                result = self.contextual_analyzer.analyze_fallacies(text)
                if result:
                    for fallacy_data in result:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get('type', 'contextual'),
                            name=fallacy_data.get('name', 'Sophisme contextuel'),
                            description=fallacy_data.get('description', ''),
                            severity=fallacy_data.get('severity', 0.5),
                            confidence=fallacy_data.get('confidence', 0.5),
                            context=fallacy_data.get('context')
                        )
                        fallacies.append(fallacy)
            
            # Filtrage par seuil de sévérité
            if options and hasattr(options, 'severity_threshold') and options.severity_threshold is not None:
                fallacies = [f for f in fallacies if f.severity >= options.severity_threshold]
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection de sophismes: {e}")
        
        return fallacies
    
    def _analyze_structure(self, text: str, options: Optional[Any]) -> Optional[ArgumentStructure]:
        """Analyse la structure argumentative du texte (implémentation simplifiée).

        Cette méthode fournit une analyse de structure basique en divisant le texte
        en phrases et en utilisant une heuristique simple pour identifier prémisses
        et conclusion.
        NOTE: Un TODO indique une intégration future avec des outils plus avancés.

        :param text: Le texte à analyser.
        :type text: str
        :param options: Options d'analyse (non utilisées actuellement dans cette méthode).
        :type options: Optional[Any]
        :return: Un objet `ArgumentStructure` ou None si une erreur survient.
        :rtype: Optional[ArgumentStructure]
        """
        try:
            # TODO: Future enhancement - Integrate with more advanced structural analysis tools (e.g., discourse parsers) for more accurate conclusion/premise identification.
            
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            
            if len(sentences) < 2:
                return ArgumentStructure(
                    premises=[],
                    conclusion=text,
                    argument_type="simple",
                    strength=0.3, # Faible force si pas de structure claire
                    coherence=0.3 # Faible cohérence
                )
            
            conclusion = sentences[-1]
            premises = sentences[:-1]
            
            strength = min(0.8, len(premises) * 0.2 + 0.4) # Force basée sur le nombre de prémisses
            coherence = 0.7 if len(premises) > 1 else 0.5 # Cohérence basique
            
            return ArgumentStructure(
                premises=premises,
                conclusion=conclusion,
                argument_type="deductive" if len(premises) > 1 else "simple", # Type basé sur le nombre de prémisses
                strength=strength,
                coherence=coherence
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de structure: {e}")
            return None
    
    def _calculate_overall_quality(self, fallacies: List[FallacyDetection], structure: Optional[ArgumentStructure]) -> float:
        """Calcule un score de qualité globale basé sur les sophismes et la structure.

        Combine un score basé sur la pénalité des sophismes et un score basé sur
        la force de la structure argumentative.

        :param fallacies: Liste des sophismes détectés.
        :type fallacies: List[FallacyDetection]
        :param structure: La structure argumentative analysée.
        :type structure: Optional[ArgumentStructure]
        :return: Un score de qualité globale entre 0.0 et 1.0.
        :rtype: float
        """
        try:
            fallacy_penalty = sum(f.severity for f in fallacies) * 0.1
            fallacy_score = max(0.0, 1.0 - fallacy_penalty)
            
            structure_score = structure.strength if structure else 0.3
            
            overall = (fallacy_score * 0.6 + structure_score * 0.4)
            return min(1.0, max(0.0, overall))
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de qualité: {e}")
            return 0.5 # Valeur neutre en cas d'erreur
    
    def _calculate_coherence_score(self, structure: Optional[ArgumentStructure]) -> float:
        """Calcule le score de cohérence basé sur la structure argumentative.

        :param structure: La structure argumentative analysée.
        :type structure: Optional[ArgumentStructure]
        :return: Le score de cohérence de la structure, ou 0.3 par défaut si
                 la structure est None ou si une erreur survient.
        :rtype: float
        """
        try:
            if structure:
                return structure.coherence
            return 0.3 # Cohérence faible par défaut
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de cohérence: {e}")
            return 0.3
    
    def _create_fallback_response(self, request: AnalysisRequest, start_time: float) -> AnalysisResponse:
        """Crée une réponse `AnalysisResponse` de fallback en cas d'échec d'initialisation du service.

        :param request: La requête d'analyse originale.
        :type request: AnalysisRequest
        :param start_time: Le timestamp du début du traitement de la requête.
        :type start_time: float
        :return: Un objet `AnalysisResponse` indiquant un échec avec des valeurs par défaut.
        :rtype: AnalysisResponse
        """
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            success=False,
            text_analyzed=request.text,
            fallacies=[],
            argument_structure=ArgumentStructure( # Fournir une structure par défaut
                premises=[],
                conclusion=request.text, # Au moins retourner le texte comme conclusion
                argument_type="unknown",
                strength=0.0,
                coherence=0.0
            ),
            overall_quality=0.0,
            coherence_score=0.0,
            fallacy_count=0,
            processing_time=processing_time,
            analysis_options=request.options.dict() if request.options else {}
        )