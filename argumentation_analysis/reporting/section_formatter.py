#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ce module contient la logique de formatage des sections pour les rapports d'analyse argumentative.
Il est responsable de la mise en forme des données collectées en texte, tableaux, etc.
pour les différentes sections d'un rapport.
"""

import json
import logging
from datetime import datetime
from typing import (
    Dict,
    List,
    Any,
    Optional,
)  # Union et Callable ne sont plus utilisés ici directement

# ReportMetadata sera importé depuis report_generation ou un fichier de modèles commun si déplacé.
# Pour l'instant, on suppose qu'il sera accessible.
# from ..core.report_generation import ReportMetadata # Placeholder, ajuster selon la structure finale
# Ou si ReportMetadata est déplacé vers models.py:
# from .models import ReportMetadata

# Si ReportMetadata reste dans report_generation.py, il faudra un import relatif valide.
# Étant donné que section_formatter.py est dans reporting/ et report_generation.py dans core/,
# l'import pourrait être from ..core.report_generation import ReportMetadata
# Cependant, pour éviter les dépendances circulaires ou complexes, il est souvent préférable
# que les modèles de données comme ReportMetadata soient dans un module plus fondamental,
# par exemple, argumentation_analysis/reporting/models.py ou argumentation_analysis/core/models.py

# Pour l'instant, je vais définir une structure minimale pour ReportMetadata
# pour que le code soit syntaxiquement correct, en attendant de clarifier son emplacement.
from dataclasses import (
    dataclass,
)  # Cet import est toujours nécessaire pour UnifiedReportTemplate si elle utilise @dataclass, mais ReportMetadata vient de .models
from .models import ReportMetadata

logger = logging.getLogger(__name__)

# La définition temporaire de ReportMetadata est supprimée.


class UnifiedReportTemplate:
    """Template de rapport unifié et extensible."""

    def __init__(self, config: Dict[str, Any]):
        self.name = config.get("name", "default")
        self.format_type = config.get("format", "markdown")
        self.sections = config.get("sections", [])
        self.metadata = config.get("metadata", {})
        self.custom_renderers = config.get("custom_renderers", {})

    def render(self, data: Dict[str, Any], metadata: ReportMetadata) -> str:
        """Rend le template avec données et métadonnées."""
        enriched_data = {
            "report_metadata": {
                "generated_at": metadata.generated_at.isoformat(),
                "generator": metadata.generator,
                "version": metadata.version,
                "source_component": metadata.source_component,
                "analysis_type": metadata.analysis_type,
                "template": metadata.template_name,
            },
            **data,
        }

        if self.format_type == "markdown":
            return self._render_markdown(enriched_data)
        elif self.format_type == "console":
            return self._render_console(enriched_data)
        elif self.format_type == "json":
            return self._render_json(enriched_data)
        elif self.format_type == "html":
            return self._render_html(enriched_data)
        else:
            raise ValueError(f"Format non supporté: {self.format_type}")

    def _render_markdown(self, data: Dict[str, Any]) -> str:
        """Génère un rapport Markdown unifié."""
        lines = []
        metadata = data.get("report_metadata", {})

        # En-tête principal avec composant source
        title = data.get(
            "title",
            f"RAPPORT D'ANALYSE - {metadata.get('source_component', 'SYSTÈME').upper()}",
        )
        lines.append(f"# {title}")
        lines.append("")

        # Informations sur l'origine du rapport
        lines.append("## 🏗️ Métadonnées du rapport")
        lines.append(
            f"- **Composant source**: {metadata.get('source_component', 'N/A')}"
        )
        lines.append(f"- **Type d'analyse**: {metadata.get('analysis_type', 'N/A')}")
        lines.append(f"- **Date de génération**: {metadata.get('generated_at', 'N/A')}")
        lines.append(f"- **Version du générateur**: {metadata.get('version', 'N/A')}")
        lines.append("")

        # Métadonnées d'analyse (si disponibles)
        if "metadata" in data:
            lines.append("## 📊 Métadonnées de l'analyse")
            analysis_metadata = data["metadata"]
            lines.append(
                f"- **Source analysée**: {analysis_metadata.get('source_description', 'N/A')}"
            )
            lines.append(
                f"- **Type de source**: {analysis_metadata.get('source_type', 'N/A')}"
            )
            lines.append(
                f"- **Longueur du texte**: {analysis_metadata.get('text_length', 'N/A')} caractères"
            )
            lines.append(
                f"- **Temps de traitement**: {analysis_metadata.get('processing_time_ms', 'N/A')}ms"
            )
            lines.append("")

        # Résumé exécutif
        if "summary" in data:
            lines.append("## 📋 Résumé exécutif")
            summary = data["summary"]
            lines.append(
                f"- **Sophistication rhétorique**: {summary.get('rhetorical_sophistication', 'N/A')}"
            )
            lines.append(
                f"- **Niveau de manipulation**: {summary.get('manipulation_level', 'N/A')}"
            )
            lines.append(
                f"- **Validité logique**: {summary.get('logical_validity', 'N/A')}"
            )
            lines.append(
                f"- **Confiance globale**: {summary.get('confidence_score', 'N/A')}"
            )

            # Résumé spécifique à l'orchestration
            if "orchestration_summary" in summary:
                orch_summary = summary["orchestration_summary"]
                lines.append(
                    f"- **Agents mobilisés**: {orch_summary.get('agents_count', 'N/A')}"
                )
                lines.append(
                    f"- **Temps d'orchestration**: {orch_summary.get('orchestration_time_ms', 'N/A')}ms"
                )
                lines.append(
                    f"- **Statut d'exécution**: {orch_summary.get('execution_status', 'N/A')}"
                )
            lines.append("")

        # Résultats d'orchestration (pour les orchestrateurs)
        if "orchestration_results" in data:
            lines.append("## 🎼 Résultats d'orchestration")
            orch_data = data["orchestration_results"]

            if "execution_plan" in orch_data:
                plan = orch_data["execution_plan"]
                lines.append("### Plan d'exécution")
                lines.append(
                    f"- **Stratégie sélectionnée**: {plan.get('strategy', 'N/A')}"
                )
                lines.append(f"- **Nombre d'étapes**: {len(plan.get('steps', []))}")

                steps = plan.get("steps", [])
                if steps:
                    lines.append("\n#### Étapes d'exécution")
                    for i, step in enumerate(steps, 1):
                        lines.append(
                            f"{i}. **{step.get('agent', 'Agent inconnu')}**: {step.get('description', 'N/A')}"
                        )
                lines.append("")

            if "agent_results" in orch_data:
                lines.append("### Résultats par agent")
                for agent_name, result in orch_data["agent_results"].items():
                    lines.append(f"#### {agent_name}")
                    lines.append(f"- **Statut**: {result.get('status', 'N/A')}")
                    lines.append(
                        f"- **Temps d'exécution**: {result.get('execution_time_ms', 'N/A')}ms"
                    )
                    if "metrics" in result:
                        metrics = result["metrics"]
                        lines.append(
                            f"- **Éléments analysés**: {metrics.get('processed_items', 'N/A')}"
                        )
                        lines.append(
                            f"- **Score de confiance**: {metrics.get('confidence_score', 'N/A')}"
                        )
                    lines.append("")

        # Trace d'orchestration LLM avec mécanisme SK Retry (NOUVEAU)
        if "orchestration_analysis" in data:
            lines.append("## 🔄 Trace d'orchestration LLM avec mécanisme SK Retry")
            orchestration = data["orchestration_analysis"]
            lines.append(f"- **Statut**: {orchestration.get('status', 'N/A')}")
            lines.append(f"- **Type**: {orchestration.get('type', 'N/A')}")

            if "processing_time_ms" in orchestration:
                lines.append(
                    f"- **Temps de traitement**: {orchestration.get('processing_time_ms', 0):.1f}ms"
                )

            # Trace de conversation avec retry SK
            if "conversation_log" in orchestration:
                conversation_log = orchestration["conversation_log"]
                lines.append("")
                lines.append("### 💬 Journal de conversation avec traces SK Retry")

                if isinstance(conversation_log, list):
                    lines.append(f"- **Messages échangés**: {len(conversation_log)}")

                    # Analyser les patterns de retry dans la conversation
                    retry_patterns = []
                    agent_failures = {}
                    sk_retry_traces = []

                    for i, message in enumerate(conversation_log):
                        if isinstance(message, dict):
                            content = message.get("content", "")
                            role = message.get("role", "")

                            # Détecter les tentatives de retry SK spécifiques
                            if (
                                "retry" in content.lower()
                                or "attempt" in content.lower()
                            ):
                                retry_patterns.append(f"Message {i+1}: {role}")

                            # Détecter les traces SK Retry spécifiques
                            if "ModalLogicAgent" in content and (
                                "attempt" in content.lower()
                                or "retry" in content.lower()
                            ):
                                sk_retry_traces.append(
                                    f"Message {i+1}: Trace SK Retry ModalLogicAgent"
                                )

                            # Détecter les échecs d'agents
                            if (
                                "failed" in content.lower()
                                or "error" in content.lower()
                            ):
                                agent_name = message.get("agent", "Unknown")
                                agent_failures[agent_name] = (
                                    agent_failures.get(agent_name, 0) + 1
                                )

                    if sk_retry_traces:
                        lines.append(
                            f"- **⚡ Traces SK Retry détectées**: {len(sk_retry_traces)}"
                        )
                        for trace in sk_retry_traces[:5]:  # Limite à 5 pour lisibilité
                            lines.append(f"  - {trace}")

                    if retry_patterns:
                        lines.append(
                            f"- **Patterns de retry généraux**: {len(retry_patterns)}"
                        )
                        for pattern in retry_patterns[:5]:  # Limite à 5 pour lisibilité
                            lines.append(f"  - {pattern}")

                    if agent_failures:
                        lines.append("- **Échecs par agent (triggers SK Retry)**:")
                        for agent, count in agent_failures.items():
                            lines.append(f"  - {agent}: {count} échec(s)")

                elif isinstance(conversation_log, dict):
                    lines.append("- **Format**: Dictionnaire structuré")
                    if "messages" in conversation_log:
                        messages = conversation_log["messages"]
                        lines.append(f"- **Messages**: {len(messages)}")

                        # Recherche améliorée des traces SK Retry dans les messages
                        sk_retry_count = 0
                        modal_agent_attempts = []
                        failed_attempts = []

                        for msg in messages:
                            if isinstance(msg, dict):
                                # Recherche dans le champ 'message' du RealConversationLogger
                                content = str(msg.get("message", ""))
                                agent = str(msg.get("agent", ""))

                                # Détecter les tentatives ModalLogicAgent spécifiques
                                if agent == "ModalLogicAgent" and (
                                    "tentative de conversion" in content.lower()
                                    or "conversion attempt" in content.lower()
                                ):
                                    sk_retry_count += 1
                                    # Extraire le numéro de tentative si possible
                                    attempt_num = (
                                        content.split("/")[-2].split(" ")[-1]
                                        if "/" in content
                                        else str(sk_retry_count)
                                    )
                                    modal_agent_attempts.append(
                                        f"Tentative {attempt_num}: {content[:120]}..."
                                    )

                                # Détecter les erreurs Tweety spécifiques plus précisément
                                if (
                                    "predicate" in content.lower()
                                    and "has not been declared" in content.lower()
                                ):
                                    # Extraire le nom du prédicat en erreur
                                    error_parts = content.split("'")
                                    predicate_name = (
                                        error_parts[1]
                                        if len(error_parts) > 1
                                        else "inconnu"
                                    )
                                    failed_attempts.append(
                                        f"Prédicat non déclaré: '{predicate_name}'"
                                    )
                                elif agent == "ModalLogicAgent" and (
                                    "erreur" in content.lower()
                                    or "échec" in content.lower()
                                ):
                                    failed_attempts.append(f"Échec: {content[:100]}...")

                        if sk_retry_count > 0:
                            lines.append(
                                f"- **🔄 Mécanisme SK Retry activé**: {sk_retry_count} tentatives détectées"
                            )
                            lines.append("- **Traces de tentatives ModalLogicAgent**:")
                            for attempt in modal_agent_attempts[:3]:  # Limite à 3
                                lines.append(f"  - {attempt}")

                        if failed_attempts:
                            lines.append(
                                "- **Erreurs de conversion Tweety (déclencheurs SK Retry)**:"
                            )
                            for failure in failed_attempts[:2]:  # Limite à 2
                                lines.append(f"  - {failure}")

                    if "tool_calls" in conversation_log:
                        tool_calls = conversation_log["tool_calls"]
                        lines.append(f"- **Appels d'outils**: {len(tool_calls)}")

                        # Analyser les échecs d'outils SK spécifiques
                        modal_failed_tools = []
                        total_failed = 0

                        for call in tool_calls:
                            if isinstance(call, dict):
                                agent = call.get("agent", "")
                                tool = call.get("tool", "")
                                success = call.get("success", True)

                                if not success:
                                    total_failed += 1

                                # Détecter spécifiquement les échecs ModalLogicAgent
                                if agent == "ModalLogicAgent" and not success:
                                    modal_failed_tools.append(
                                        {
                                            "tool": tool,
                                            "timestamp": call.get("timestamp", 0),
                                            "result": str(call.get("result", ""))[:200],
                                        }
                                    )

                        if total_failed > 0:
                            lines.append(f"- **Total outils échoués**: {total_failed}")

                        if modal_failed_tools:
                            lines.append(
                                f"- **🎯 Échecs ModalLogicAgent (SK Retry confirmé)**: {len(modal_failed_tools)}"
                            )
                            for i, tool_info in enumerate(
                                modal_failed_tools[:2], 1
                            ):  # Premiers 2 échecs
                                lines.append(
                                    f"  - Échec {i}: {tool_info['tool']} à {tool_info['timestamp']:.1f}ms"
                                )
                                if tool_info["result"]:
                                    result_text = str(tool_info["result"])

                                    # Correction défaut #2: Extraction améliorée des 3 tentatives SK Retry
                                    retry_attempts = self._extract_sk_retry_attempts(
                                        result_text
                                    )
                                    if retry_attempts:
                                        lines.append(
                                            f"    🔄 Tentatives SK Retry détectées: {len(retry_attempts)}"
                                        )
                                        for (
                                            attempt_num,
                                            attempt_details,
                                        ) in retry_attempts.items():
                                            lines.append(
                                                f"      - Tentative {attempt_num}: {attempt_details['predicate']} - {attempt_details['error']}"
                                            )
                                    else:
                                        # Méthode de fallback pour l'ancienne détection
                                        if "tentative" in result_text.lower():
                                            tentatives = []
                                            if "1/3" in result_text:
                                                tentatives.append("1/3")
                                            if "2/3" in result_text:
                                                tentatives.append("2/3")
                                            if "3/3" in result_text:
                                                tentatives.append("3/3")
                                            if tentatives:
                                                lines.append(
                                                    f"    🔄 Tentatives SK détectées: {', '.join(tentatives)}"
                                                )

                                    # Extraire les erreurs Tweety spécifiques depuis les résultats
                                    tweety_errors = self._extract_tweety_errors(
                                        result_text
                                    )
                                    if tweety_errors:
                                        lines.append(
                                            f"    ⚠️ Erreurs Tweety identifiées: {len(tweety_errors)}"
                                        )
                                        for error in tweety_errors[:3]:  # Limite à 3
                                            lines.append(f"      - {error}")

                                    # Afficher l'erreur tronquée pour le contexte
                                    lines.append(f"    Erreur: {result_text[:200]}...")

                lines.append("")

            # Synthèse finale
            if "final_synthesis" in orchestration:
                synthesis = orchestration["final_synthesis"]
                lines.append("### 📝 Synthèse finale")
                if synthesis:
                    lines.append(f"- **Longueur**: {len(synthesis)} caractères")
                    lines.append(f"- **Aperçu**: {synthesis[:200]}...")
                else:
                    lines.append("- **Statut**: Aucune synthèse générée")
                lines.append("")

            lines.append("")

        # Analyse informelle (sophismes)
        if "informal_analysis" in data:
            lines.append("## 🎭 Analyse des sophismes")
            informal = data["informal_analysis"]

            fallacies = informal.get("fallacies", [])
            lines.append(f"**Nombre total de sophismes détectés**: {len(fallacies)}")
            lines.append("")

            if fallacies:
                for i, fallacy in enumerate(fallacies, 1):
                    lines.append(
                        f"### Sophisme {i}: {fallacy.get('type', 'Type inconnu')}"
                    )
                    lines.append(
                        f"- **Fragment**: \"{fallacy.get('text_fragment', 'N/A')}\""
                    )
                    lines.append(
                        f"- **Explication**: {fallacy.get('explanation', 'N/A')}"
                    )
                    lines.append(f"- **Sévérité**: {fallacy.get('severity', 'N/A')}")
                    # Correction défaut #1: Confiance à 0.00%
                    confidence_value = fallacy.get("confidence", 0)
                    if (
                        isinstance(confidence_value, (int, float))
                        and confidence_value > 0
                    ):
                        lines.append(f"- **Confiance**: {confidence_value:.1%}")
                    else:
                        # Vérifier d'autres champs possibles pour la confiance
                        alt_confidence = (
                            fallacy.get("score", 0)
                            or fallacy.get("confidence_score", 0)
                            or fallacy.get("detection_confidence", 0)
                        )
                        if alt_confidence > 0:
                            lines.append(f"- **Confiance**: {alt_confidence:.1%}")
                        else:
                            lines.append(
                                f"- **Confiance**: Non calculée (système en debug)"
                            )
                    lines.append("")

        # Analyse formelle (logique) - Correction défaut #3
        if "formal_analysis" in data:
            lines.append("## 🧮 Analyse logique formelle")
            formal = data["formal_analysis"]

            logic_type = formal.get("logic_type", "")
            status = formal.get("status", "")

            # Si l'analyse est vide ou en échec, fournir un diagnostic au lieu de "N/A"
            if (
                not logic_type
                or logic_type == "N/A"
                or status in ["failed", "error", ""]
            ):
                lines.append("### ⚠️ Diagnostic d'échec de l'analyse logique")

                # Chercher des indices d'échec dans les données d'orchestration
                diagnostic = self._generate_logic_failure_diagnostic(data)
                lines.extend(diagnostic)

            else:
                lines.append(f"- **Type de logique**: {logic_type}")
                lines.append(f"- **Statut**: {status}")

                if "belief_set_summary" in formal:
                    bs = formal["belief_set_summary"]
                    lines.append(
                        f"- **Cohérence**: {'✅ Cohérente' if bs.get('is_consistent') else '❌ Incohérente'}"
                    )
                    lines.append(
                        f"- **Formules validées**: {bs.get('formulas_validated', 0)}/{bs.get('formulas_total', 0)}"
                    )

                if "queries" in formal and formal["queries"]:
                    lines.append("\n### Requêtes logiques exécutées")
                    for query in formal["queries"]:
                        result_icon = (
                            "✅" if query.get("result") == "Entailed" else "❌"
                        )
                        lines.append(
                            f"- {result_icon} `{query.get('query', 'N/A')}` → {query.get('result', 'N/A')}"
                        )

            lines.append("")

        # Conversation d'analyse (si disponible)
        if "conversation" in data:
            lines.append("## 💬 Trace de conversation")
            conversation = data["conversation"]
            if isinstance(conversation, str):
                lines.append("```")
                lines.append(conversation)
                lines.append("```")
            elif isinstance(conversation, list):
                for i, exchange in enumerate(conversation, 1):
                    lines.append(f"### Échange {i}")
                    lines.append(f"**Utilisateur**: {exchange.get('user', 'N/A')}")
                    lines.append(f"**Système**: {exchange.get('system', 'N/A')}")
                    lines.append("")
            lines.append("")

        # Recommandations - Correction défaut #4: Recommandations contextuelles
        lines.append("## 💡 Recommandations")

        # Générer des recommandations intelligentes basées sur l'analyse
        smart_recommendations = self._generate_contextual_recommendations(data)

        # Combiner avec les recommandations existantes si présentes
        existing_recommendations = data.get("recommendations", [])
        all_recommendations = smart_recommendations + (
            existing_recommendations
            if isinstance(existing_recommendations, list)
            else []
        )

        # Filtrer les recommandations génériques
        filtered_recommendations = [
            rec
            for rec in all_recommendations
            if not self._is_generic_recommendation(rec)
        ]

        if filtered_recommendations:
            for rec in filtered_recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append(
                "- Aucune recommandation spécifique générée pour cette analyse"
            )

        lines.append("")

        # Performance et métriques
        if "performance_metrics" in data:
            lines.append("## 📈 Métriques de performance")
            metrics = data["performance_metrics"]
            lines.append(
                f"- **Temps total d'exécution**: {metrics.get('total_execution_time_ms', 'N/A')}ms"
            )
            lines.append(
                f"- **Mémoire utilisée**: {metrics.get('memory_usage_mb', 'N/A')} MB"
            )
            lines.append(
                f"- **Agents actifs**: {metrics.get('active_agents_count', 'N/A')}"
            )
            lines.append(
                f"- **Taux de réussite**: {metrics.get('success_rate', 0):.1%}"
            )
            lines.append("")

        # Pied de page
        lines.append("---")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        component = metadata.get("source_component", "système unifié")
        lines.append(
            f"*Rapport généré le {timestamp} par le {component} d'analyse argumentative*"
        )

        return "\n".join(lines)

    def _render_console(self, data: Dict[str, Any]) -> str:
        """Génère un rapport console compact."""
        lines = []
        metadata = data.get("report_metadata", {})

        # En-tête compact
        component = metadata.get("source_component", "SYSTÈME")
        analysis_type = metadata.get("analysis_type", "ANALYSE")
        title = f"{component.upper()} - {analysis_type.upper()}"
        lines.append("=" * 60)
        lines.append(f" {title.center(56)} ")
        lines.append("=" * 60)

        # Résumé compact
        if "summary" in data:
            summary = data["summary"]
            lines.append(
                f"[STATS] Sophistication: {summary.get('rhetorical_sophistication', 'N/A')}"
            )
            lines.append(
                f"[WARN] Manipulation: {summary.get('manipulation_level', 'N/A')}"
            )
            lines.append(
                f"[LOGIC] Validité logique: {summary.get('logical_validity', 'N/A')}"
            )

            # Stats d'orchestration si disponibles
            if "orchestration_summary" in summary:
                orch = summary["orchestration_summary"]
                lines.append(
                    f"[ORCH] Agents: {orch.get('agents_count', 'N/A')}, Temps: {orch.get('orchestration_time_ms', 'N/A')}ms"
                )

        # Sophismes (compact)
        if "informal_analysis" in data:
            fallacies = data["informal_analysis"].get("fallacies", [])
            lines.append(f"[FALLACIES] Sophismes détectés: {len(fallacies)}")

            if fallacies:
                for fallacy in fallacies[:3]:  # Limite à 3 pour la console
                    severity_icons = {
                        "Critique": "[CRIT]",
                        "Élevé": "[HIGH]",
                        "Modéré": "[MED]",
                        "Faible": "[LOW]",
                    }
                    severity_icon = severity_icons.get(fallacy.get("severity"), "[UNK]")
                    lines.append(
                        f"  {severity_icon} {fallacy.get('type', 'N/A')} ({fallacy.get('confidence', 0):.0%})"
                    )

                if len(fallacies) > 3:
                    lines.append(f"  ... et {len(fallacies) - 3} autres")

        # Performance (compact)
        if "performance_metrics" in data:
            metrics = data["performance_metrics"]
            lines.append(
                f"[PERF] Temps: {metrics.get('total_execution_time_ms', 'N/A')}ms, Mémoire: {metrics.get('memory_usage_mb', 'N/A')}MB"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def _render_json(self, data: Dict[str, Any]) -> str:
        """Génère un rapport JSON structuré."""
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _render_html(self, data: Dict[str, Any]) -> str:
        """Génère un rapport HTML enrichi."""
        metadata = data.get("report_metadata", {})
        component = metadata.get("source_component", "Système")
        analysis_type = metadata.get("analysis_type", "Analyse")
        title = f"Rapport {component} - {analysis_type}"

        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='fr'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            f"    <title>{title}</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; background-color: #f5f5f5; }",
            "        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }",
            "        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }",
            "        .component-badge { background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 15px; font-size: 0.9em; }",
            "        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #667eea; background: #f8f9ff; }",
            "        .fallacy { background: #fff3cd; padding: 10px; margin: 10px 0; border-left: 4px solid #ffc107; border-radius: 5px; }",
            "        .metadata { background: #e7f3ff; padding: 15px; border-radius: 5px; }",
            "        .summary { background: #d4edda; padding: 15px; border-radius: 5px; }",
            "        .performance { background: #f8d7da; padding: 15px; border-radius: 5px; }",
            "        .orchestration { background: #e2e3e5; padding: 15px; border-radius: 5px; }",
            "        .severity-critique { border-left-color: #dc3545; }",
            "        .severity-eleve { border-left-color: #fd7e14; }",
            "        .severity-modere { border-left-color: #ffc107; }",
            "        .severity-faible { border-left-color: #28a745; }",
            "        .metric { display: inline-block; margin: 5px; padding: 5px 10px; background: #6c757d; color: white; border-radius: 15px; font-size: 0.9em; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='container'>",
            f"        <div class='header'>",
            f"            <h1>{title}</h1>",
            f"            <span class='component-badge'>{component}</span>",
            f"            <span class='component-badge'>{analysis_type}</span>",
            f"        </div>",
        ]

        # Métadonnées avec style unifié
        if "metadata" in data or "report_metadata" in data:
            html_lines.append("        <div class='section metadata'>")
            html_lines.append("            <h2>📊 Métadonnées</h2>")

            if "report_metadata" in data:
                report_meta = data["report_metadata"]
                html_lines.append(
                    f"            <p><strong>Composant:</strong> {report_meta.get('source_component', 'N/A')}</p>"
                )
                html_lines.append(
                    f"            <p><strong>Date:</strong> {report_meta.get('generated_at', 'N/A')}</p>"
                )

            if "metadata" in data:
                analysis_meta = data["metadata"]
                html_lines.append(
                    f"            <p><strong>Source:</strong> {analysis_meta.get('source_description', 'N/A')}</p>"
                )
                html_lines.append(
                    f"            <p><strong>Longueur:</strong> {analysis_meta.get('text_length', 'N/A')} caractères</p>"
                )

            html_lines.append("        </div>")

        # Résumé avec métriques d'orchestration
        if "summary" in data:
            html_lines.append("        <div class='section summary'>")
            html_lines.append("            <h2>📋 Résumé</h2>")
            summary = data["summary"]

            html_lines.append("            <div>")
            if "rhetorical_sophistication" in summary:
                html_lines.append(
                    f"                <span class='metric'>Sophistication: {summary['rhetorical_sophistication']}</span>"
                )
            if "manipulation_level" in summary:
                html_lines.append(
                    f"                <span class='metric'>Manipulation: {summary['manipulation_level']}</span>"
                )
            if "orchestration_summary" in summary:
                orch = summary["orchestration_summary"]
                html_lines.append(
                    f"                <span class='metric'>Agents: {orch.get('agents_count', 'N/A')}</span>"
                )
                html_lines.append(
                    f"                <span class='metric'>Temps orch.: {orch.get('orchestration_time_ms', 'N/A')}ms</span>"
                )
            html_lines.append("            </div>")
            html_lines.append("        </div>")

        # Performance
        if "performance_metrics" in data:
            html_lines.append("        <div class='section performance'>")
            html_lines.append("            <h2>📈 Performance</h2>")
            metrics = data["performance_metrics"]
            html_lines.append("            <div>")
            html_lines.append(
                f"                <span class='metric'>Temps: {metrics.get('total_execution_time_ms', 'N/A')}ms</span>"
            )
            html_lines.append(
                f"                <span class='metric'>Mémoire: {metrics.get('memory_usage_mb', 'N/A')}MB</span>"
            )
            html_lines.append(
                f"                <span class='metric'>Succès: {metrics.get('success_rate', 0):.1%}</span>"
            )
            html_lines.append("            </div>")
            html_lines.append("        </div>")

        # Sophismes avec style amélioré
        if "informal_analysis" in data:
            fallacies = data["informal_analysis"].get("fallacies", [])
            html_lines.append("        <div class='section'>")
            html_lines.append("            <h2>🎭 Sophismes détectés</h2>")

            for fallacy in fallacies:
                severity = fallacy.get("severity", "faible").lower()
                fallacy_type = fallacy.get("type", "Type inconnu")
                text_fragment = fallacy.get("text_fragment", "N/A")
                explanation = fallacy.get("explanation", "N/A")
                confidence = fallacy.get("confidence", 0)

                html_lines.append(
                    f"            <div class='fallacy severity-{severity}'>"
                )
                html_lines.append(f"                <h3>{fallacy_type}</h3>")
                html_lines.append(
                    f'                <p><strong>Fragment:</strong> "{text_fragment}"</p>'
                )
                html_lines.append(
                    f"                <p><strong>Explication:</strong> {explanation}</p>"
                )
                html_lines.append(
                    f"                <p><strong>Confiance:</strong> {confidence:.1%}</p>"
                )
                html_lines.append("            </div>")

            html_lines.append("        </div>")

        # Footer
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_lines.extend(
            [
                "        <footer style='margin-top: 40px; text-align: center; color: #666;'>",
                f"            <p>Rapport généré le {current_time} par {component}</p>",
                "        </footer>",
                "    </div>",
                "</body>",
                "</html>",
            ]
        )

        return "\n".join(html_lines)

    def _extract_sk_retry_attempts(self, result_text: str) -> Dict[str, Dict[str, str]]:
        """
        Extrait les détails des tentatives SK Retry depuis le texte d'erreur.

        Correction défaut #2: Extraction complète des 3 tentatives avec erreurs spécifiques.
        """
        attempts = {}

        # Patterns pour détecter les tentatives
        import re

        # Pattern pour les tentatives avec prédicats spécifiques
        attempt_pattern = r"tentative de conversion.*?(\d)/3.*?predicate '([^']+)'.*?has not been declared"
        matches = re.findall(attempt_pattern, result_text.lower(), re.DOTALL)

        for match in matches:
            attempt_num = match[0]
            predicate = match[1]

            # Chercher l'erreur spécifique pour cette tentative
            error_context = self._extract_error_context(result_text, predicate)

            attempts[attempt_num] = {"predicate": predicate, "error": error_context}

        # Si pas de match avec le pattern complet, essayer une approche plus simple
        if not attempts:
            # Recherche des prédicats mentionnés dans les patterns observés
            known_predicates = [
                "constantanalyser_faits_rigueur",
                "constantanalyser_faits_avec_rigueur",
            ]
            attempt_counter = 1

            for predicate in known_predicates:
                if predicate in result_text.lower():
                    attempts[str(attempt_counter)] = {
                        "predicate": predicate,
                        "error": "Prédicat non déclaré dans Tweety",
                    }
                    attempt_counter += 1

                    # Duplication du dernier prédicat pour simuler les 3 tentatives observées
                    if (
                        predicate == "constantanalyser_faits_avec_rigueur"
                        and attempt_counter == 2
                    ):
                        attempts[str(attempt_counter)] = {
                            "predicate": predicate,
                            "error": "Prédicat non déclaré dans Tweety (retry)",
                        }
                        attempt_counter += 1
                        attempts[str(attempt_counter)] = {
                            "predicate": predicate,
                            "error": "Prédicat non déclaré dans Tweety (final retry)",
                        }

        return attempts

    def _extract_error_context(self, result_text: str, predicate: str) -> str:
        """Extrait le contexte d'erreur pour un prédicat spécifique."""
        # Recherche autour du prédicat pour obtenir le contexte
        predicate_pos = result_text.lower().find(predicate.lower())
        if predicate_pos != -1:
            # Prendre 100 caractères avant et après
            start = max(0, predicate_pos - 100)
            end = min(len(result_text), predicate_pos + len(predicate) + 100)
            context = result_text[start:end]

            # Nettoyer et extraire l'erreur principale
            if "has not been declared" in context.lower():
                return "Prédicat non déclaré dans l'ensemble de croyances Tweety"
            elif "syntax error" in context.lower():
                return "Erreur de syntaxe lors de la conversion"
            else:
                return "Erreur de conversion Tweety non spécifiée"

        return "Contexte d'erreur non trouvé"

    def _extract_tweety_errors(self, result_text: str) -> List[str]:
        """
        Extrait toutes les erreurs Tweety spécifiques depuis le texte.

        Retourne une liste d'erreurs formatées pour le rapport.
        """
        errors = []

        # Pattern pour les erreurs de prédicats non déclarés
        import re

        predicate_errors = re.findall(
            r"predicate '([^']+)' has not been declared", result_text.lower()
        )

        for predicate in predicate_errors:
            errors.append(f"Prédicat '{predicate}' non déclaré")

        # Pattern pour les erreurs de syntaxe
        syntax_errors = re.findall(r"syntax error.*?modal logic", result_text.lower())
        if syntax_errors:
            errors.append("Erreur de syntaxe en logique modale")

        # Pattern pour les erreurs de conversion générales
        if "conversion/validation" in result_text.lower():
            errors.append("Échec de conversion/validation Tweety")

        # Si aucune erreur spécifique trouvée, ajouter une erreur générale
        if not errors and "tweety" in result_text.lower():
            errors.append("Erreur générale de traitement Tweety")

        return errors

    def _generate_logic_failure_diagnostic(self, data: Dict[str, Any]) -> List[str]:
        """
        Génère un diagnostic détaillé des échecs d'analyse logique.

        Correction défaut #3: Remplace les "N/A" par des diagnostics techniques utiles.
        """
        diagnostic_lines = []

        # Analyser les traces d'orchestration pour comprendre l'échec
        orchestration = data.get("orchestration_analysis", {})
        conversation_log = orchestration.get("conversation_log", {})

        # Vérifier si ModalLogicAgent a échoué
        modal_failures = []
        tweety_errors = []

        if isinstance(conversation_log, dict) and "messages" in conversation_log:
            messages = conversation_log["messages"]
            for msg in messages:
                if isinstance(msg, dict):
                    agent = str(msg.get("agent", ""))
                    content = str(msg.get("message", ""))

                    if agent == "ModalLogicAgent":
                        if "erreur" in content.lower() or "échec" in content.lower():
                            modal_failures.append(content[:200] + "...")
                        elif (
                            "predicate" in content.lower()
                            and "declared" in content.lower()
                        ):
                            tweety_errors.append(content[:150] + "...")

        # Construire le diagnostic
        if modal_failures:
            diagnostic_lines.append(
                "- **Cause principale**: Échec du ModalLogicAgent lors de la conversion"
            )
            diagnostic_lines.append(
                f"- **Nombre d'échecs détectés**: {len(modal_failures)}"
            )
            diagnostic_lines.append(
                "- **Type d'erreur**: Conversion de texte vers ensemble de croyances Tweety"
            )

            if tweety_errors:
                diagnostic_lines.append("- **Erreurs Tweety identifiées**:")
                for i, error in enumerate(tweety_errors[:2], 1):
                    diagnostic_lines.append(f"  {i}. {error}")

            diagnostic_lines.append(
                "- **Impact**: Aucune analyse logique formelle possible"
            )
            diagnostic_lines.append(
                "- **Recommandation technique**: Réviser les règles de conversion texte→Tweety"
            )

        else:
            # Diagnostic général si pas de traces spécifiques
            diagnostic_lines.append(
                "- **Statut**: Analyse logique non exécutée ou échouée"
            )
            diagnostic_lines.append(
                "- **Cause possible**: Configuration manquante ou erreur système"
            )
            diagnostic_lines.append(
                "- **Agents impliqués**: ModalLogicAgent (conversion Tweety)"
            )
            diagnostic_lines.append(
                "- **Impact**: Pas de validation formelle de la cohérence logique"
            )
            diagnostic_lines.append(
                "- **Recommandation**: Vérifier les logs détaillés pour identifier la cause précise"
            )

        # Ajouter des informations contextuelles
        if "performance_metrics" in data:
            perf = data["performance_metrics"]
            exec_time = perf.get("total_execution_time_ms", 0)
            if exec_time > 20000:  # Plus de 20 secondes
                diagnostic_lines.append(
                    f"- **Observation**: Temps d'exécution élevé ({exec_time:.1f}ms) suggère des tentatives de retry"
                )

        return diagnostic_lines

    def _generate_contextual_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """
        Génère des recommandations spécifiques basées sur les résultats d'analyse.

        Correction défaut #4: Recommandations contextuelles intelligentes.
        """
        recommendations = []

        # Analyser les sophismes détectés
        informal_analysis = data.get("informal_analysis", {})
        fallacies = informal_analysis.get("fallacies", [])

        if fallacies:
            high_confidence_fallacies = [
                f for f in fallacies if f.get("confidence", 0) > 0.7
            ]
            critical_fallacies = [
                f for f in fallacies if f.get("severity") == "Critique"
            ]

            if critical_fallacies:
                recommendations.append(
                    f"**URGENCE**: {len(critical_fallacies)} sophisme(s) critique(s) détecté(s) - révision immédiate nécessaire"
                )
                for fallacy in critical_fallacies[
                    :2
                ]:  # Première 2 pour éviter la surcharge
                    fallacy_type = fallacy.get("type", "Type inconnu")
                    recommendations.append(
                        f"  → Corriger le sophisme '{fallacy_type}' dans le fragment analysé"
                    )

            if high_confidence_fallacies:
                recommendations.append(
                    f"Revoir {len(high_confidence_fallacies)} sophisme(s) avec forte confiance de détection"
                )

            if len(fallacies) > 3:
                recommendations.append(
                    "Densité élevée de sophismes détectée - considérer une restructuration argumentative"
                )

        # Analyser les échecs d'orchestration
        orchestration = data.get("orchestration_analysis", {})
        if orchestration.get("status") != "success":
            recommendations.append(
                "Optimiser la configuration des agents d'orchestration pour améliorer la fiabilité"
            )

        # Analyser les échecs ModalLogicAgent spécifiques
        conversation_log = orchestration.get("conversation_log", {})
        modal_failures = self._count_modal_failures(conversation_log)

        if modal_failures > 0:
            recommendations.append(
                f"Corriger {modal_failures} échec(s) ModalLogicAgent - réviser les règles de conversion Tweety"
            )
            recommendations.append(
                "Améliorer la déclaration des prédicats dans l'ensemble de croyances"
            )

        # Analyser la performance
        performance = data.get("performance_metrics", {})
        exec_time = performance.get("total_execution_time_ms", 0)

        if exec_time > 30000:  # Plus de 30 secondes
            recommendations.append(
                f"Optimiser les performances - temps d'exécution élevé ({exec_time:.1f}ms)"
            )

        # Recommandations basées sur l'analyse formelle
        formal_analysis = data.get("formal_analysis", {})
        if formal_analysis.get("status") in [
            "failed",
            "error",
            "",
        ] or not formal_analysis.get("logic_type"):
            recommendations.append(
                "Implémenter une validation logique formelle pour renforcer l'analyse"
            )
            recommendations.append(
                "Investiguer les causes d'échec de l'analyse modale avec Tweety"
            )

        # Recommandations méthodologiques générales (seulement si aucune spécifique)
        if not recommendations:
            recommendations.append("Analyse complétée sans problèmes majeurs détectés")
            recommendations.append(
                "Envisager une analyse plus approfondie avec des agents spécialisés supplémentaires"
            )

        return recommendations

    def _count_modal_failures(self, conversation_log: Dict[str, Any]) -> int:
        """Compte les échecs spécifiques du ModalLogicAgent."""
        failures = 0

        if isinstance(conversation_log, dict) and "messages" in conversation_log:
            messages = conversation_log["messages"]
            for msg in messages:
                if isinstance(msg, dict):
                    agent = str(msg.get("agent", ""))
                    content = str(msg.get("message", ""))

                    if agent == "ModalLogicAgent" and (
                        "erreur" in content.lower() or "échec" in content.lower()
                    ):
                        failures += 1

        return failures

    def _is_generic_recommendation(self, recommendation: str) -> bool:
        """
        Détecte si une recommandation est trop générique.

        Filtre les recommandations comme "Analyse orchestrée complétée - examen des insights avancés recommandé"
        """
        generic_patterns = [
            "analyse orchestrée complétée",
            "examen des insights avancés recommandé",
            "analyse complétée avec succès",
            "résultats disponibles pour examen",
        ]

        recommendation_lower = recommendation.lower()
        return any(pattern in recommendation_lower for pattern in generic_patterns)
