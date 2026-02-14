"""
Agent de Synthèse qui orchestre les analyses et unifie les résultats.

Ce module définit le `SynthesisAgent`, un agent de haut niveau dont le rôle
est de coordonner les analyses logiques (formelles) et rhétoriques (informelles)
d'un texte donné. Il invoque les agents spécialisés, recueille leurs
résultats, et les consolide dans un `UnifiedReport` unique et cohérent.

L'agent est conçu avec une architecture progressive (par "phases") pour
permettre des améliorations futures (gestion des conflits, etc.). La version
actuelle représente la Phase 1 : coordination et rapport.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple, List

from semantic_kernel import Kernel
from pydantic import PrivateAttr

from ..abc.agent_bases import BaseAgent
from .data_models import LogicAnalysisResult, InformalAnalysisResult, UnifiedReport


class SynthesisAgent(BaseAgent):
    """
    Orchestre les analyses formelles et informelles pour produire un rapport unifié.

    En tant qu'agent de haut niveau, il ne réalise pas d'analyse primaire lui-même.
    Son rôle est de :
    1.  Invoquer les agents d'analyse spécialisés (logique, informel).
    2.  Exécuter leurs analyses en parallèle pour plus d'efficacité.
    3.  Agréger les résultats structurés (`LogicAnalysisResult`, `InformalAnalysisResult`).
    4.  Générer une synthèse, évaluer la cohérence et produire un `UnifiedReport`.

    Attributes:
        _enable_advanced_features (bool): Drapeau pour activer les fonctionnalités
            des phases futures (non implémentées en Phase 1).
        _logic_agents_cache (Dict[str, Any]): Cache pour les instances des agents logiques.
        _informal_agent (Optional[Any]): Instance de l'agent d'analyse informelle.
        _llm_service_id (str): ID du service LLM utilisé pour les fonctions sémantiques.
    """
    
    # Déclaration des attributs Pydantic pour compatibilité avec BaseAgent
    _enable_advanced_features: bool = PrivateAttr(default=False)
    _logic_agents_cache: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _informal_agent: Optional[Any] = PrivateAttr(default=None)
    _llm_service_id: Optional[str] = PrivateAttr(default=None)
    # Modules avancés (Phase 2+) - déclarés comme PrivateAttr pour Pydantic V2
    _fusion_manager: Optional[Any] = PrivateAttr(default=None)
    _conflict_manager: Optional[Any] = PrivateAttr(default=None)
    _evidence_manager: Optional[Any] = PrivateAttr(default=None)
    _quality_manager: Optional[Any] = PrivateAttr(default=None)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "SynthesisAgent",
        enable_advanced_features: bool = False,
        service_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialise le SynthesisAgent.

        Args:
            kernel (Kernel): L'instance du kernel Semantic Kernel.
            agent_name (str): Le nom de l'agent.
            enable_advanced_features (bool): Si `True`, tentera d'utiliser des
                fonctionnalités avancées (non disponibles en Phase 1).
            service_id (Optional[str]): L'ID du service LLM à utiliser.
        """
        system_prompt = self._get_synthesis_system_prompt()
        super().__init__(kernel, agent_name, system_prompt, **kwargs)

        self._enable_advanced_features = enable_advanced_features
        self._logic_agents_cache = {}
        self._informal_agent = None
        self._llm_service_id = service_id

        # Modules avancés (Phase 2+) - désactivés en Phase 1
        self._fusion_manager = None
        self._conflict_manager = None
        self._evidence_manager = None
        self._quality_manager = None

        self.logger.info(
            f"SynthesisAgent initialisé (mode avancé: {enable_advanced_features})"
        )

    # ==================== BACKWARD COMPATIBILITY PROPERTIES ====================

    @property
    def fusion_manager(self):
        return self._fusion_manager

    @fusion_manager.setter
    def fusion_manager(self, value):
        self._fusion_manager = value

    @property
    def conflict_manager(self):
        return self._conflict_manager

    @conflict_manager.setter
    def conflict_manager(self, value):
        self._conflict_manager = value

    @property
    def evidence_manager(self):
        return self._evidence_manager

    @evidence_manager.setter
    def evidence_manager(self, value):
        self._evidence_manager = value

    @property
    def quality_manager(self):
        return self._quality_manager

    @quality_manager.setter
    def quality_manager(self, value):
        self._quality_manager = value

    @property
    def enable_advanced_features(self):
        return self._enable_advanced_features

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit les capacités de l'agent de synthèse."""
        capabilities = {
            "synthesis_coordination": True,
            "formal_analysis_orchestration": True,
            "informal_analysis_orchestration": True,
            "unified_reporting": True,
            "logic_types_supported": ["propositional", "first_order", "modal"],
            "phase": 1,
            "advanced_features_enabled": self._enable_advanced_features,
        }

        if self._enable_advanced_features:
            capabilities.update(
                {
                    "fusion_management": False,  # À implémenter en Phase 2
                    "conflict_resolution": False,  # À implémenter en Phase 3
                    "evidence_assessment": False,  # À implémenter en Phase 3
                    "quality_metrics": False,  # À implémenter en Phase 3
                }
            )

        return capabilities

    async def synthesize_analysis(self, text: str) -> UnifiedReport:
        """
        Point d'entrée principal pour lancer une analyse complète et une synthèse.

        Cette méthode exécute l'ensemble du pipeline d'analyse :
        - Orchestration des analyses parallèles.
        - Synthèse des résultats.
        - Calcul du temps total de traitement.

        Args:
            text (str): Le texte source à analyser.

        Returns:
            UnifiedReport: L'objet `UnifiedReport` complet contenant tous les
                résultats et la synthèse.
        """
        self.logger.info(
            f"Début de la synthèse d'analyse (texte: {len(text)} caractères)"
        )
        start_time = time.time()

        try:
            if self._enable_advanced_features and self._fusion_manager is not None:
                # Mode avancé (Phase 2+) - à implémenter
                result = await self._advanced_synthesis(text)
            else:
                # Mode simple (Phase 1)
                result = await self._simple_synthesis(text)

            end_time = time.time()
            result.total_processing_time_ms = (end_time - start_time) * 1000

            self.logger.info(
                f"Synthèse terminée en {result.total_processing_time_ms:.2f}ms"
            )
            return result

        except Exception as e:
            self.logger.error(f"Erreur lors de la synthèse: {str(e)}", exc_info=True)
            raise

    async def orchestrate_analysis(
        self, text: str
    ) -> Tuple[LogicAnalysisResult, InformalAnalysisResult]:
        """
        Lance et coordonne les analyses formelles et informelles en parallèle.

        Utilise `asyncio.gather` pour exécuter simultanément les analyses logiques
        et informelles, optimisant ainsi le temps d'exécution.

        Args:
            text (str): Le texte à analyser.

        Returns:
            A tuple containing the `LogicAnalysisResult` and `InformalAnalysisResult`.
            En cas d'erreur dans une des analyses, un objet de résultat vide
            est retourné pour cette analyse.
        """
        self.logger.info("Orchestration des analyses formelles et informelles")

        # Lancement des analyses en parallèle pour optimiser les performances
        formal_task = self._run_formal_analysis(text)
        informal_task = self._run_informal_analysis(text)

        # Attente des résultats
        formal_results, informal_results = await asyncio.gather(
            formal_task, informal_task, return_exceptions=True
        )

        # Gestion des erreurs
        if isinstance(formal_results, Exception):
            self.logger.error(f"Erreur analyse formelle: {formal_results}")
            formal_results = LogicAnalysisResult()  # Résultat vide par défaut

        if isinstance(informal_results, Exception):
            self.logger.error(f"Erreur analyse informelle: {informal_results}")
            informal_results = InformalAnalysisResult()  # Résultat vide par défaut

        return formal_results, informal_results

    async def unify_results(
        self,
        logic_result: LogicAnalysisResult,
        informal_result: InformalAnalysisResult,
        original_text: str,
    ) -> UnifiedReport:
        """
        Combine les résultats bruts en un rapport unifié et synthétisé.

        Cette méthode prend les résultats des analyses logiques et informelles
        et les utilise pour peupler un `UnifiedReport`. Elle génère également
        des métriques et des synthèses de plus haut niveau.

        Args:
            logic_result (LogicAnalysisResult): Les résultats de l'analyse formelle.
            informal_result (InformalAnalysisResult): Les résultats de l'analyse informelle.
            original_text (str): Le texte original pour référence dans le rapport.

        Returns:
            UnifiedReport: Le rapport unifié, prêt à être formaté ou utilisé.
        """
        self.logger.info("Unification des résultats d'analyses")

        # Création du rapport de base
        unified_report = UnifiedReport(
            original_text=original_text,
            logic_analysis=logic_result,
            informal_analysis=informal_result,
        )

        # Génération de la synthèse basique (Phase 1)
        unified_report.executive_summary = await self._generate_simple_summary(
            logic_result, informal_result
        )

        # Évaluations basiques
        unified_report.overall_validity = self._assess_overall_validity(
            logic_result, informal_result
        )

        unified_report.confidence_level = self._calculate_confidence_level(
            logic_result, informal_result
        )

        # Détection de contradictions simples
        unified_report.contradictions_identified = self._identify_basic_contradictions(
            logic_result, informal_result
        )

        # Recommandations de base
        unified_report.recommendations = self._generate_basic_recommendations(
            logic_result, informal_result
        )

        return unified_report

    async def generate_report(self, unified_report: UnifiedReport) -> str:
        """
        Formate un objet `UnifiedReport` en un rapport textuel lisible (Markdown).

        Args:
            unified_report (UnifiedReport): L'objet rapport structuré.

        Returns:
            str: Une chaîne de caractères formatée en Markdown représentant le rapport.
        """
        self.logger.info("Génération du rapport textuel")

        report_sections = []

        # En-tête
        report_sections.append("# RAPPORT DE SYNTHÈSE UNIFIÉ")
        report_sections.append(f"Généré le: {unified_report.synthesis_timestamp}")
        report_sections.append(f"Version: {unified_report.synthesis_version}")
        report_sections.append("")

        # Texte Original Analysé
        report_sections.append("## TEXTE ORIGINAL ANALYSÉ")
        # Utilisation d'un bloc de citation pour une meilleure lisibilité
        report_sections.append(f"> {unified_report.original_text}")
        report_sections.append("")

        # Résumé exécutif
        report_sections.append("## RÉSUMÉ EXÉCUTIF")
        report_sections.append(unified_report.executive_summary)
        report_sections.append("")

        # Statistiques
        stats = unified_report.get_summary_statistics()
        report_sections.append("## STATISTIQUES")
        report_sections.append(
            f"- Longueur du texte: {stats['text_length']} caractères"
        )
        report_sections.append(
            f"- Formules logiques extraites: {stats['formulas_count']}"
        )
        report_sections.append(f"- Sophismes détectés: {stats['fallacies_count']}")
        report_sections.append(
            f"- Contradictions identifiées: {stats['contradictions_count']}"
        )
        report_sections.append("")

        # Évaluation globale
        report_sections.append("## ÉVALUATION GLOBALE")
        report_sections.append(f"- Validité globale: {unified_report.overall_validity}")
        report_sections.append(
            f"- Niveau de confiance: {unified_report.confidence_level}"
        )
        report_sections.append("")

        # Contradictions
        if unified_report.contradictions_identified:
            report_sections.append("## CONTRADICTIONS IDENTIFIÉES")
            for contradiction in unified_report.contradictions_identified:
                report_sections.append(f"- {contradiction}")
            report_sections.append("")

        # Recommandations
        if unified_report.recommendations:
            report_sections.append("## RECOMMANDATIONS")
            for recommendation in unified_report.recommendations:
                report_sections.append(f"- {recommendation}")
            report_sections.append("")

        # Détails techniques
        report_sections.append("## DÉTAILS DES ANALYSES")
        report_sections.append("### Analyse Logique")
        if unified_report.logic_analysis.propositional_result:
            report_sections.append(
                f"**Logique propositionnelle:** {unified_report.logic_analysis.propositional_result}"
            )
        if unified_report.logic_analysis.first_order_result:
            report_sections.append(
                f"**Logique de premier ordre:** {unified_report.logic_analysis.first_order_result}"
            )
        if unified_report.logic_analysis.modal_result:
            report_sections.append(
                f"**Logique modale:** {unified_report.logic_analysis.modal_result}"
            )

        report_sections.append("")
        report_sections.append("### Analyse Informelle")
        if unified_report.informal_analysis.arguments_structure:
            report_sections.append(
                f"**Structure argumentative:** {unified_report.informal_analysis.arguments_structure}"
            )
        if unified_report.informal_analysis.fallacies_detected:
            report_sections.append(
                f"**Sophismes:** {len(unified_report.informal_analysis.fallacies_detected)} détectés"
            )

        return "\n".join(report_sections)

    # =====================================
    # Méthodes privées d'implémentation
    # =====================================

    async def _simple_synthesis(self, text: str) -> UnifiedReport:
        """Synthèse simple sans modules avancés (Phase 1)."""
        self.logger.info("Exécution de la synthèse simple (Phase 1)")

        # Orchestration des analyses
        logic_result, informal_result = await self.orchestrate_analysis(text)

        # Unification des résultats
        unified_report = await self.unify_results(logic_result, informal_result, text)

        return unified_report

    async def _advanced_synthesis(self, text: str) -> UnifiedReport:
        """Synthèse avancée avec modules optionnels (Phase 2+)."""
        # À implémenter dans les phases futures
        raise NotImplementedError("Synthèse avancée non encore implémentée (Phase 2+)")

    async def _run_formal_analysis(self, text: str) -> LogicAnalysisResult:
        """Exécute les analyses logiques formelles."""
        self.logger.info("Démarrage des analyses logiques formelles")
        start_time = time.time()

        result = LogicAnalysisResult()

        try:
            # Création des agents logiques via la factory
            logic_types = ["propositional", "first_order", "modal"]
            tasks = []

            for logic_type in logic_types:
                agent = self._get_logic_agent(logic_type)
                if agent:
                    task = self._analyze_with_logic_agent(agent, text, logic_type)
                    tasks.append(task)

            # Exécution en parallèle
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Traitement des résultats
                for i, logic_type in enumerate(logic_types):
                    if i < len(results) and not isinstance(results[i], Exception):
                        analysis_result = results[i]
                        if logic_type == "propositional":
                            result.propositional_result = analysis_result
                        elif logic_type == "first_order":
                            result.first_order_result = analysis_result
                        elif logic_type == "modal":
                            result.modal_result = analysis_result

            end_time = time.time()
            result.processing_time_ms = (end_time - start_time) * 1000

        except Exception as e:
            self.logger.error(f"Erreur dans l'analyse formelle: {str(e)}")
            result.propositional_result = f"Erreur: {str(e)}"

        return result

    async def _run_informal_analysis(self, text: str) -> InformalAnalysisResult:
        """Exécute l'analyse informelle."""
        self.logger.info("Démarrage de l'analyse informelle")
        start_time = time.time()

        result = InformalAnalysisResult()

        try:
            # Utilisation de l'agent informel existant
            informal_agent = self._get_informal_agent()
            if informal_agent:
                # Adaptation selon l'interface de InformalAgent
                # Cette partie pourrait nécessiter un ajustement selon l'API réelle
                analysis_result = await self._analyze_with_informal_agent(
                    informal_agent, text
                )

                # Parsing des résultats (à adapter selon le format de retour)
                if isinstance(analysis_result, str):
                    result.arguments_structure = analysis_result
                elif isinstance(analysis_result, dict):
                    result.fallacies_detected = analysis_result.get("fallacies", [])
                    result.arguments_structure = analysis_result.get("structure", "")
                    result.rhetorical_devices = analysis_result.get("devices", [])

            end_time = time.time()
            result.processing_time_ms = (end_time - start_time) * 1000

        except Exception as e:
            self.logger.error(f"Erreur dans l'analyse informelle: {str(e)}")
            result.arguments_structure = f"Erreur: {str(e)}"

        return result

    def _get_logic_agent(self, logic_type: str):
        """Récupère ou crée un agent logique du type spécifié (simulation Phase 1)."""
        # Pour la Phase 1, on simule les agents logiques
        self.logger.info(f"Simulation agent logique: {logic_type}")
        if logic_type not in self._logic_agents_cache:
            # MOCK ÉLIMINÉ PHASE 3 - FORCER ERREUR RÉELLE
            raise NotImplementedError(
                f"MockLogicAgent éliminé - implémenter agent authentique {logic_type}"
            )

        return self._logic_agents_cache.get(logic_type)

    def _get_informal_agent(self):
        """Récupère ou crée l'agent d'analyse informelle (simulation Phase 1)."""
        if self._informal_agent is None:
            # MOCK ÉLIMINÉ PHASE 3 - FORCER ERREUR RÉELLE
            self.logger.error("MockInformalAgent éliminé")
            raise NotImplementedError(
                "MockInformalAgent éliminé - implémenter agent authentique"
            )

        return self._informal_agent

    async def _analyze_with_logic_agent(self, agent, text: str, logic_type: str) -> str:
        """Analyse un texte avec un agent logique spécifique."""
        try:
            # Adaptation selon l'interface des agents logiques
            # Cette méthode devra être ajustée selon l'API réelle des agents
            if hasattr(agent, "analyze_text"):
                result = await agent.analyze_text(text)
            elif hasattr(agent, "process_text"):
                result = await agent.process_text(text)
            else:
                result = f"Agent {logic_type} disponible mais interface non reconnue"

            return str(result) if result else f"Analyse {logic_type} sans résultat"

        except Exception as e:
            self.logger.error(f"Erreur agent {logic_type}: {str(e)}")
            return f"Erreur analyse {logic_type}: {str(e)}"

    async def _analyze_with_informal_agent(self, agent, text: str):
        """Analyse un texte avec l'agent informel."""
        try:
            # Adaptation selon l'interface de InformalAgent
            if hasattr(agent, "analyze_text"):
                result = await agent.analyze_text(text)
            elif hasattr(agent, "process_text"):
                result = await agent.process_text(text)
            else:
                result = "Agent informel disponible mais interface non reconnue"

            return result

        except Exception as e:
            self.logger.error(f"Erreur agent informel: {str(e)}")
            return f"Erreur analyse informelle: {str(e)}"

    async def _generate_simple_summary(
        self, logic_result: LogicAnalysisResult, informal_result: InformalAnalysisResult
    ) -> str:
        """Génère un résumé simple des analyses."""
        summary_parts = []

        # Analyse des résultats logiques
        logic_summary = []
        if logic_result.propositional_result:
            logic_summary.append("logique propositionnelle")
        if logic_result.first_order_result:
            logic_summary.append("logique de premier ordre")
        if logic_result.modal_result:
            logic_summary.append("logique modale")

        if logic_summary:
            summary_parts.append(
                f"Analyse formelle réalisée avec: {', '.join(logic_summary)}."
            )

        # Analyse des résultats informels
        fallacies_count = len(informal_result.fallacies_detected)
        if fallacies_count > 0:
            summary_parts.append(
                f"Analyse informelle: {fallacies_count} sophisme(s) détecté(s)."
            )
        else:
            summary_parts.append("Analyse informelle: aucun sophisme majeur détecté.")

        # Synthèse générale
        if logic_result.logical_validity is not None:
            validity_text = "valide" if logic_result.logical_validity else "invalide"
            summary_parts.append(f"Validité logique: {validity_text}.")

        return (
            " ".join(summary_parts)
            if summary_parts
            else "Synthèse des analyses réalisée."
        )

    def _assess_overall_validity(
        self, logic_result: LogicAnalysisResult, informal_result: InformalAnalysisResult
    ) -> Optional[bool]:
        """Évalue la validité globale basée sur les deux analyses."""
        # Logique simple pour Phase 1
        logic_valid = logic_result.logical_validity
        informal_issues = len(informal_result.fallacies_detected) == 0

        if logic_valid is None:
            return informal_issues

        return logic_valid and informal_issues

    def _calculate_confidence_level(
        self, logic_result: LogicAnalysisResult, informal_result: InformalAnalysisResult
    ) -> Optional[float]:
        """Calcule un niveau de confiance basique."""
        confidence = 0.5  # Base neutre

        # Ajustements basés sur la disponibilité des résultats
        if logic_result.propositional_result:
            confidence += 0.1
        if logic_result.first_order_result:
            confidence += 0.1
        if logic_result.modal_result:
            confidence += 0.1

        if informal_result.arguments_structure:
            confidence += 0.15

        # Pénalités pour les problèmes détectés
        fallacies_penalty = min(len(informal_result.fallacies_detected) * 0.05, 0.2)
        confidence -= fallacies_penalty

        return min(max(confidence, 0.0), 1.0)

    def _identify_basic_contradictions(
        self, logic_result: LogicAnalysisResult, informal_result: InformalAnalysisResult
    ) -> List[str]:
        """Identifie des contradictions basiques entre les analyses."""
        contradictions = []

        # Contradiction entre validité logique et sophismes
        if (
            logic_result.logical_validity == True
            and len(informal_result.fallacies_detected) > 0
        ):
            contradictions.append(
                "Contradiction: argument logiquement valide mais contenant des sophismes"
            )

        # Contradiction entre cohérence et validité
        if (
            logic_result.consistency_check == False
            and logic_result.logical_validity == True
        ):
            contradictions.append(
                "Contradiction: argument valide mais ensemble de prémisses incohérent"
            )

        return contradictions

    def _generate_basic_recommendations(
        self, logic_result: LogicAnalysisResult, informal_result: InformalAnalysisResult
    ) -> List[str]:
        """Génère des recommandations basiques."""
        recommendations = []

        # Recommandations basées sur l'analyse logique
        if logic_result.logical_validity == False:
            recommendations.append("Revoir la structure logique de l'argument")

        if logic_result.consistency_check == False:
            recommendations.append("Vérifier la cohérence des prémisses")

        # Recommandations basées sur l'analyse informelle
        fallacies_count = len(informal_result.fallacies_detected)
        if fallacies_count > 0:
            recommendations.append(
                f"Corriger les {fallacies_count} sophisme(s) identifié(s)"
            )

        if not informal_result.arguments_structure:
            recommendations.append("Clarifier la structure argumentative")

        # Recommandation générale
        if not recommendations:
            recommendations.append(
                "L'analyse est satisfaisante, aucune correction majeure nécessaire"
            )

        return recommendations

    def _get_synthesis_system_prompt(self) -> str:
        """Retourne le prompt système pour l'agent de synthèse."""
        return """Vous êtes un Agent de Synthèse Unifié spécialisé dans l'analyse 
        et la coordination d'évaluations logiques formelles et informelles de textes argumentatifs.

        Votre rôle est de:
        1. Orchestrer les analyses logiques (propositionnelle, premier ordre, modale)
        2. Coordonner l'analyse rhétorique et de détection de sophismes
        3. Unifier les résultats en une synthèse cohérente
        4. Identifier les contradictions entre analyses formelles et informelles
        5. Fournir des recommandations d'amélioration

        Vous travaillez de manière systématique et objective, en préservant 
        la spécificité de chaque type d'analyse tout en créant une vue d'ensemble cohérente."""

    # Méthodes abstraites de BaseAgent
    async def invoke_single(self, text: str, **kwargs) -> UnifiedReport:
        """
        Exécute la logique principale de l'agent (synthèse) et retourne une réponse unique.
        Implémentation de la méthode abstraite de BaseAgent.
        """
        self.logger.debug(f"invoking SynthesisAgent with text: {text[:80]}...")
        return await self.synthesize_analysis(text)

    async def get_response(self, *args, **kwargs):
        """Implémentation de la méthode abstraite get_response."""
        if args and isinstance(args[0], str):
            report = await self.invoke_single(args[0])
            return await self.generate_report(report)
        return "Usage: fournir un texte à analyser"


# =====================================
# MOCKS ÉLIMINÉS PHASE 3 - ZÉRO TOLÉRANCE
# =====================================
# Classes Mock supprimées brutalement selon consignes élimination
# Utiliser agents authentiques au lieu de masquer avec mocks
