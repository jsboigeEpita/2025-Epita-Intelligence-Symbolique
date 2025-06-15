"""
Module TraceAnalyzer pour l'analyse et la synthèse des traces d'exécution
du système d'argumentation unifié.

Ce module fournit des outils pour extraire, analyser et synthétiser
les informations contenues dans les logs de conversation et les rapports
générés par le système.
"""

import json
import re
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractMetadata:
    """Métadonnées d'un extrait analysé"""
    source_file: str
    content_length: int
    content_type: str
    complexity_level: str
    analysis_timestamp: str
    encoding_info: Optional[str] = None
    source_origin: Optional[str] = None


@dataclass
class OrchestrationFlow:
    """Flow d'orchestration des agents"""
    agents_called: List[str]
    sequence_order: List[Tuple[str, str]]  # (agent, phase)
    coordination_messages: List[str]
    total_execution_time: float
    success_status: str


@dataclass
class StateEvolution:
    """Évolution des états partagés et belief states"""
    shared_state_changes: List[Dict[str, Any]]
    belief_state_construction: List[Dict[str, Any]]
    progressive_enrichment: List[str]
    state_transitions: List[Tuple[str, str]]  # (from_state, to_state)


@dataclass
class QueryResults:
    """Requêtes et résultats d'inférence"""
    formalizations: List[Dict[str, Any]]
    inference_queries: List[str]
    validation_results: List[Dict[str, Any]]
    logic_types_used: List[str]
    knowledge_base_status: str


@dataclass
class ToolCall:
    """Appel d'outil tracé avec détails enrichis"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    timestamp: float
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    
    def to_compact_string(self) -> str:
        """Conversion en format compact pour les logs."""
        args_str = json.dumps(self.arguments, ensure_ascii=False)[:100] + "..." if len(str(self.arguments)) > 100 else json.dumps(self.arguments, ensure_ascii=False)
        status = "✓" if self.success else "✗"
        return f"{status} {self.tool_name}({args_str}) -> {self.execution_time_ms:.1f}ms"
    
    def to_conversation_format(self, agent_name: str = "Agent") -> str:
        """Conversion en format de conversation agentielle optimisé."""
        # Formatage intelligent des arguments
        args_formatted = self._format_arguments_intelligently()
        
        # Formatage du résultat de manière concise
        result_formatted = self._format_result_concisely()
        
        # Structure de conversation avec indentation (caractères compatibles Windows)
        conversation_block = []
        conversation_block.append(f"[AGENT] {agent_name}")
        conversation_block.append(f"| [TOOL] {self.tool_name}")
        conversation_block.append(f"| [ARGS] {args_formatted}")
        conversation_block.append(f"| [TIME] {self.execution_time_ms:.1f}ms")
        conversation_block.append(f"| [RESULT] {result_formatted}")
        conversation_block.append("|")
        
        return "\n".join(conversation_block)
    
    def _format_arguments_intelligently(self) -> str:
        """Formate les arguments de manière intelligente avec troncature."""
        if not self.arguments:
            return "{}"
        
        formatted_args = []
        for key, value in self.arguments.items():
            if isinstance(value, str) and len(value) > 100:
                # Troncature intelligente pour les longs textes
                preview = value[:100].replace('"', "'")
                formatted_args.append(f'{key}="[{preview}...]"')
            elif isinstance(value, (list, dict)) and len(str(value)) > 150:
                # Résumé pour les structures complexes
                if isinstance(value, list):
                    summary = f"[{len(value)} items: {str(value[:2])[:-1]}...]" if len(value) > 2 else str(value)
                else:
                    summary = f"{{...{len(value)} keys...}}"
                formatted_args.append(f'{key}={summary}')
            else:
                formatted_args.append(f'{key}={json.dumps(value, ensure_ascii=False)}')
        
        args_str = ", ".join(formatted_args)
        if len(args_str) > 150:
            args_str = args_str[:147] + "..."
        
        return args_str
    
    def _format_result_concisely(self) -> str:
        """Formate le résultat de manière concise et informative."""
        if self.result is None:
            return "None"
        
        if isinstance(self.result, str):
            if len(self.result) > 80:
                return f'"{self.result[:77]}..."'
            return f'"{self.result}"'
        
        if isinstance(self.result, (list, tuple)):
            count = len(self.result)
            if count == 0:
                return "[]"
            elif count <= 3:
                return str(self.result)
            else:
                return f"{count} éléments: {str(self.result[:2])[:-1]}...]"
        
        if isinstance(self.result, dict):
            keys_count = len(self.result)
            if keys_count <= 2:
                return str(self.result)
            else:
                first_items = list(self.result.items())[:2]
                return f"{{{', '.join([f'{k}: {v}' for k, v in first_items])}, ...{keys_count-2} more}}"
        
        # Pour les autres types (int, bool, etc.)
        result_str = str(self.result)
        if len(result_str) > 80:
            return result_str[:77] + "..."
        return result_str


@dataclass
class AgentStep:
    """Représentation d'une étape d'agent dans la conversation"""
    agent_name: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "active"  # active, completed, failed
    
    def add_tool_call(self, tool_call: ToolCall):
        """Ajoute un appel d'outil à cette étape d'agent."""
        self.tool_calls.append(tool_call)
    
    def complete(self, status: str = "completed"):
        """Marque l'étape comme terminée."""
        self.end_time = time.time()
        self.status = status
    
    def get_duration_ms(self) -> float:
        """Retourne la durée de l'étape en millisecondes."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    def to_conversation_format(self) -> str:
        """Convertit l'étape d'agent en format de conversation."""
        if not self.tool_calls:
            return f"[AGENT] {self.agent_name}\n| [INFO] Aucun outil utilisé\n|"
        
        conversation_parts = []
        for tool_call in self.tool_calls:
            conversation_parts.append(tool_call.to_conversation_format(self.agent_name))
        
        return "\n".join(conversation_parts)


@dataclass
class ConversationCapture:
    """Capture complète de la conversation avec timing"""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    total_duration_ms: float = 0.0
    
    def add_message(self, role: str, content: str, timestamp: Optional[float] = None):
        """Ajoute un message à la conversation."""
        if timestamp is None:
            timestamp = time.time()
        
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': timestamp,
            'relative_time_ms': (timestamp - self.start_time) * 1000
        })
    
    def add_tool_call(self, tool_call: ToolCall):
        """Ajoute un appel d'outil tracé."""
        self.tool_calls.append(tool_call)
    
    def finalize(self):
        """Finalise la capture et calcule la durée totale."""
        self.total_duration_ms = (time.time() - self.start_time) * 1000
    
    def to_compact_summary(self) -> Dict[str, Any]:
        """Génère un résumé compact de la conversation."""
        return {
            'total_messages': len(self.messages),
            'total_tool_calls': len(self.tool_calls),
            'duration_ms': self.total_duration_ms,
            'tool_summary': [call.to_compact_string() for call in self.tool_calls[-5:]],  # 5 derniers appels
            'conversation_flow': [f"{msg['role']}: {msg['content'][:50]}..." for msg in self.messages[-3:]]  # 3 derniers messages
        }


@dataclass
class InformalExploration:
    """Exploration taxonomique informelle enrichie"""
    taxonomy_path: List[str]  # Chemin général → particulier
    fallacy_detection: List[Dict[str, Any]]
    rhetorical_patterns: List[str]
    severity_analysis: List[Dict[str, Any]]
    # Nouveaux champs pour la taxonomie réelle
    taxonomy_workflow: List[Dict[str, Any]] = field(default_factory=list)
    sophism_keys_detected: List[int] = field(default_factory=list)
    arguments_identified: List[str] = field(default_factory=list)
    detection_method: str = ""


class TraceAnalyzer:
    """
    Analyseur principal des traces d'exécution du système unifié.
    
    Permet d'extraire et synthétiser les informations des logs
    pour générer des rapports détaillés et compréhensibles.
    """
    
    def __init__(self, logs_directory: str = None):
        """
        Initialise l'analyseur de traces enrichi.
        
        Args:
            logs_directory: Répertoire contenant les logs (défaut: ./logs)
        """
        self.logs_directory = logs_directory or "./logs"
        self.conversation_log_file = None
        self.report_json_file = None
        self.raw_conversation_data = None
        self.raw_report_data = None
        
        # Nouvelles fonctionnalités de capture enrichie
        self.conversation_capture = ConversationCapture()
        self.active_tool_calls = []
        self.capture_enabled = True
        self.agent_steps = []  # Liste des étapes d'agents pour la conversation
        self.current_agent_step = None
    
    def start_conversation_capture(self):
        """Démarre la capture de conversation en temps réel."""
        if self.capture_enabled:
            self.conversation_capture = ConversationCapture()
            logger.info("Capture de conversation démarrée")
    
    def start_agent_step(self, agent_name: str) -> AgentStep:
        """Démarre une nouvelle étape d'agent."""
        if self.current_agent_step:
            self.current_agent_step.complete()
        
        self.current_agent_step = AgentStep(agent_name=agent_name)
        self.agent_steps.append(self.current_agent_step)
        return self.current_agent_step
    
    def add_tool_call_to_current_agent(self, tool_call: ToolCall):
        """Ajoute un appel d'outil à l'agent courant."""
        if self.current_agent_step:
            self.current_agent_step.add_tool_call(tool_call)
    
    def capture_message(self, role: str, content: str):
        """Capture un message de conversation."""
        if self.capture_enabled and self.conversation_capture:
            self.conversation_capture.add_message(role, content)
    
    def start_tool_call(self, tool_name: str, **parameters) -> str:
        """Démarre le traçage d'un appel d'outil."""
        if self.capture_enabled:
            tool_call = ToolCall(
                tool_name=tool_name,
                arguments=parameters,
                result=None,
                timestamp=time.time(),
                execution_time_ms=0.0,
                success=True
            )
            call_id = f"tool_{len(self.active_tool_calls)}_{int(time.time())}"
            tool_call.call_id = call_id
            self.active_tool_calls.append(tool_call)
            return call_id
        return ""
    
    def complete_tool_call(self, call_id: str, result: Any = None, success: bool = True, error_message: str = None):
        """Complète le traçage d'un appel d'outil."""
        if self.capture_enabled:
            for tool_call in self.active_tool_calls:
                if getattr(tool_call, 'call_id', None) == call_id:
                    end_time = time.time()
                    tool_call.execution_time_ms = (end_time - tool_call.timestamp) * 1000
                    tool_call.result = result
                    tool_call.success = success
                    tool_call.error_message = error_message
                    
                    if self.conversation_capture:
                        self.conversation_capture.add_tool_call(tool_call)
                    
                    # Ajouter à l'agent courant
                    self.add_tool_call_to_current_agent(tool_call)
                    break
    
    def finalize_conversation_capture(self):
        """Finalise la capture de conversation."""
        if self.capture_enabled and self.conversation_capture:
            self.conversation_capture.finalize()
            if self.current_agent_step:
                self.current_agent_step.complete()
            logger.info(f"Capture finalisée - {len(self.conversation_capture.messages)} messages, {len(self.conversation_capture.tool_calls)} appels d'outils")
    
    def generate_conversation_format_report(self) -> str:
        """Génère un rapport au format de conversation agentielle optimisé."""
        if not self.agent_steps:
            return "Aucune conversation capturée"
        
        conversation_lines = []
        conversation_lines.append("# RAPPORT DE CONVERSATION AGENTIELLE")
        conversation_lines.append("=" * 50)
        conversation_lines.append(f"**Généré le:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        conversation_lines.append("")
        
        for i, agent_step in enumerate(self.agent_steps, 1):
            conversation_lines.append(f"## Étape {i}: {agent_step.agent_name}")
            conversation_lines.append("")
            conversation_lines.append(agent_step.to_conversation_format())
            conversation_lines.append("")
        
        # Ajout du résumé
        total_tools = sum(len(step.tool_calls) for step in self.agent_steps)
        total_duration = sum(step.get_duration_ms() for step in self.agent_steps)
        
        conversation_lines.append("## RÉSUMÉ DE LA CONVERSATION")
        conversation_lines.append("-" * 30)
        conversation_lines.append(f"- **Agents impliqués:** {len(self.agent_steps)}")
        conversation_lines.append(f"- **Total d'outils utilisés:** {total_tools}")
        conversation_lines.append(f"- **Durée totale:** {total_duration:.1f}ms")
        conversation_lines.append("")
        
        return "\n".join(conversation_lines)
        
    def load_traces(self, conversation_log_path: str = None, report_json_path: str = None) -> bool:
        """
        Charge les fichiers de traces pour analyse.
        
        Args:
            conversation_log_path: Chemin vers le log de conversation
            report_json_path: Chemin vers le rapport JSON
            
        Returns:
            True si le chargement réussit, False sinon
        """
        try:
            # Détermination automatique des fichiers si non spécifiés
            if not conversation_log_path or not os.path.exists(conversation_log_path):
                log_files = [f for f in os.listdir(self.logs_directory) if f.endswith('.log')]
                if log_files:
                    conversation_log_path = os.path.join(self.logs_directory, log_files[0])

            if not report_json_path or not os.path.exists(report_json_path):
                json_files = [f for f in os.listdir(self.logs_directory) if f.endswith('.json')]
                if json_files:
                    report_json_path = os.path.join(self.logs_directory, json_files[0])
            
            # Chargement du log de conversation
            if os.path.exists(conversation_log_path):
                with open(conversation_log_path, 'r', encoding='utf-8') as f:
                    self.raw_conversation_data = f.read()
                self.conversation_log_file = conversation_log_path
                logger.info(f"Log de conversation chargé: {conversation_log_path}")
            else:
                logger.warning(f"Fichier log conversation non trouvé: {conversation_log_path}")
                
            # Chargement du rapport JSON
            if os.path.exists(report_json_path):
                with open(report_json_path, 'r', encoding='utf-8') as f:
                    self.raw_report_data = json.load(f)
                self.report_json_file = report_json_path
                logger.info(f"Rapport JSON chargé: {report_json_path}")
            else:
                logger.warning(f"Fichier rapport JSON non trouvé: {report_json_path}")
                
            return (self.raw_conversation_data is not None or 
                   self.raw_report_data is not None)
                   
        except Exception as e:
            logger.error(f"Erreur lors du chargement des traces: {e}")
            return False
    
    def extract_metadata(self) -> ExtractMetadata:
        """
        Extrait les métadonnées de l'extrait analysé.
        
        Returns:
            ExtractMetadata avec les informations sur l'extrait
        """
        metadata = ExtractMetadata(
            source_file="",
            content_length=0,
            content_type="unknown",
            complexity_level="unknown",
            analysis_timestamp=""
        )
        
        try:
            # Extraction depuis le log de conversation
            if self.raw_conversation_data:
                # Recherche du fichier source
                source_match = re.search(
                    r"Fichier source analysé : (.+)", 
                    self.raw_conversation_data
                )
                if source_match:
                    metadata.source_file = source_match.group(1)
                
                # Recherche de la longueur du contenu
                length_match = re.search(
                    r"Longueur du texte: (\d+) caractères", 
                    self.raw_conversation_data
                )
                if length_match:
                    metadata.content_length = int(length_match.group(1).strip())
                
                # Recherche de l'horodatage
                timestamp_match = re.search(
                    r"Horodatage de l'analyse\s*:\s*(.+)",
                    self.raw_conversation_data
                )
                if timestamp_match:
                    metadata.analysis_timestamp = timestamp_match.group(1).strip()
            
            # Extraction depuis le rapport JSON
            if self.raw_report_data:
                if 'statistics' in self.raw_report_data:
                    stats = self.raw_report_data['statistics']
                    if 'text_length' in stats:
                        metadata.content_length = stats['text_length']
                
                if 'metadata' in self.raw_report_data:
                    meta = self.raw_report_data['metadata']
                    metadata.analysis_timestamp = meta.get('timestamp', '')
                    metadata.source_origin = meta.get('source_type', '')
            
            # Déduction du type de complexité
            if metadata.content_length > 0:
                if metadata.content_length < 500:
                    metadata.complexity_level = "simple"
                elif metadata.content_length < 2000:
                    metadata.complexity_level = "medium"
                else:
                    metadata.complexity_level = "complex"
            
            # Type de contenu
            if "fallback" in metadata.source_file.lower():
                metadata.content_type = "fallback_text"
            else:
                metadata.content_type = "encrypted_corpus"
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées: {e}")
        
        return metadata
    
    def analyze_orchestration_flow(self) -> OrchestrationFlow:
        """
        Analyse le flow d'orchestration et la coordination des agents.
        
        Returns:
            OrchestrationFlow avec les détails de l'orchestration
        """
        flow = OrchestrationFlow(
            agents_called=[],
            sequence_order=[],
            coordination_messages=[],
            total_execution_time=0.0,
            success_status="unknown"
        )
        
        try:
            if self.raw_conversation_data:
                # Extraction des agents appelés
                # Extraction des agents appelés de manière plus robuste
                agent_matches = re.findall(
                    r"(?:agent logique:\s*|LogicAgent_)(propositional|first_order|modal)|(SynthesisAgent|ExtractAgent|InformalAgent)",
                    self.raw_conversation_data,
                    re.IGNORECASE
                )
                
                for match in agent_matches:
                    # Le match est un tuple, ex: ('propositional', '') ou ('', 'SynthesisAgent')
                    agent_type = match[0] or match[1]
                    if agent_type:
                        agent_name = ""
                        if agent_type.lower() in ["propositional", "first_order", "modal"]:
                            agent_name = f"LogicAgent_{agent_type.lower()}"
                        else:
                            agent_name = agent_type

                        if agent_name and agent_name not in flow.agents_called:
                            flow.agents_called.append(agent_name)
                
                # Séquence d'orchestration
                orchestration_lines = re.findall(
                    r"\[ETAPE \d+/\d+\] (.+)", 
                    self.raw_conversation_data
                )
                for i, step in enumerate(orchestration_lines):
                    flow.sequence_order.append((f"Step_{i+1}", step))
                
                # Messages de coordination importants
                coordination_patterns = [
                    r"Orchestration des analyses",
                    r"Unification des résultats",
                    r"Synchronisation",
                    r"Coordination"
                ]
                
                for pattern in coordination_patterns:
                    matches = re.findall(
                        f".*{pattern}.*", 
                        self.raw_conversation_data, 
                        re.IGNORECASE
                    )
                    flow.coordination_messages.extend(matches)
                
                # Temps d'exécution
                # Temps d'exécution (prendre la dernière occurrence)
                last_time_found = 0.0
                # Regex assoupli pour accepter des mots entre "terminé" et "en"
                time_pattern = re.compile(r"(?:termin\w*.*en|Temps total:)\s+([\d.]+)\s*ms", re.IGNORECASE)
                for line in self.raw_conversation_data.splitlines():
                    match = time_pattern.search(line)
                    if match:
                        last_time_found = float(match.group(1))
                flow.total_execution_time = last_time_found
                
                # Statut de succès
                # Ordre de priorité : échec > succès > terminé
                if re.search(r"(échec|erreur|failed|error)", self.raw_conversation_data, re.IGNORECASE):
                    flow.success_status = "partial_failure"
                elif re.search(r"analyse terminée avec succès", self.raw_conversation_data, re.IGNORECASE):
                    flow.success_status = "success"
                elif re.search(r"terminé", self.raw_conversation_data, re.IGNORECASE):
                     flow.success_status = "completed"
                else:
                    flow.success_status = "unknown"
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du flow d'orchestration: {e}")
        
        return flow
    
    def track_state_evolution(self) -> StateEvolution:
        """
        Suit l'évolution des états partagés et belief states.
        
        Returns:
            StateEvolution avec les changements d'état détectés
        """
        evolution = StateEvolution(
            shared_state_changes=[],
            belief_state_construction=[],
            progressive_enrichment=[],
            state_transitions=[]
        )
        
        try:
            if self.raw_conversation_data:
                # Recherche des changements d'état partagé
                state_patterns = [
                    r"shared[_\s]*state",
                    r"état[_\s]*partagé",
                    r"belief[_\s]*state"
                ]
                
                for pattern in state_patterns:
                    matches = re.findall(
                        f".*{pattern}.*", 
                        self.raw_conversation_data, 
                        re.IGNORECASE
                    )
                    for match in matches:
                        evolution.shared_state_changes.append({
                            "type": "state_change",
                            "description": match.strip(),
                            "timestamp": "extracted_from_log"
                        })
                
                # Construction progressive des belief states
                belief_indicators = [
                    "construction",
                    "enrichissement", 
                    "mise à jour",
                    "évolution"
                ]
                
                for indicator in belief_indicators:
                    matches = re.findall(
                        f".*{indicator}.*", 
                        self.raw_conversation_data, 
                        re.IGNORECASE
                    )
                    for match in matches:
                        evolution.belief_state_construction.append({
                            "phase": indicator,
                            "details": match.strip()
                        })
                
                # Enrichissement progressif
                enrichment_patterns = [
                    r"Analyse PL simulée",
                    r"Simulation FOL",
                    r"Démarrage de l'analyse modale"
                ]
                
                for pattern in enrichment_patterns:
                    matches = re.findall(pattern, self.raw_conversation_data, re.IGNORECASE)
                    # Aplatir la liste de listes/tuples
                    for match in matches:
                        if isinstance(match, str):
                            evolution.progressive_enrichment.append(match)
                        else: # Tuple de groupes de capture
                            evolution.progressive_enrichment.extend(item for item in match if item)
                
                # Transitions d'état
                transition_patterns = [
                    (r"Début", r"Fin"),
                    (r"Initialisation", r"Configuration"),
                    (r"Chargement", r"Analyse"),
                    (r"Analyse", r"Synthèse"),
                    (r"Démarrage", r"terminée"),
                    (r"construction", r"terminée")
                ]
                
                for start_pattern, end_pattern in transition_patterns:
                    if (re.search(start_pattern, self.raw_conversation_data, re.IGNORECASE) and 
                        re.search(end_pattern, self.raw_conversation_data, re.IGNORECASE)):
                        evolution.state_transitions.append((start_pattern, end_pattern))
                        
        except Exception as e:
            logger.error(f"Erreur lors du suivi de l'évolution d'état: {e}")
        
        return evolution
    
    def extract_query_results(self) -> QueryResults:
        """
        Extrait les requêtes d'inférence et leurs résultats.
        
        Returns:
            QueryResults avec les formalisations et inférences
        """
        results = QueryResults(
            formalizations=[],
            inference_queries=[],
            validation_results=[],
            logic_types_used=[],
            knowledge_base_status=""
        )
        
        try:
            # Depuis le rapport JSON
            if self.raw_report_data:
                if 'formal_analysis' in self.raw_report_data:
                    formal = self.raw_report_data['formal_analysis']
                    
                    # Types de logique utilisés
                    if 'logic_types' in formal:
                        results.logic_types_used = formal['logic_types']
                    
                    # Statut de la base de connaissances
                    if 'knowledge_base' in formal:
                        kb = formal['knowledge_base']
                        results.knowledge_base_status = kb.get('status', 'unknown')
                        
                        # Formalisations
                        if 'formulas' in kb:
                            for formula in kb['formulas']:
                                results.formalizations.append({
                                    'formula': formula,
                                    'type': 'extracted_formula'
                                })
                    
                    # Requêtes d'inférence
                    if 'inference_results' in formal:
                        inference = formal['inference_results']
                        if 'queries' in inference:
                            results.inference_queries = inference['queries']
                        
                        # Résultats de validation
                        if 'results' in inference:
                            for result in inference['results']:
                                results.validation_results.append({
                                    'query': result.get('query', ''),
                                    'result': result.get('result', ''),
                                    'confidence': result.get('confidence', 0.0)
                                })
            
            # Depuis le log de conversation
            if self.raw_conversation_data:
                # Types de logique détectés
                logic_types = re.findall(
                    r"logique (\w+)", 
                    self.raw_conversation_data, 
                    re.IGNORECASE
                )
                for logic_type in logic_types:
                    if logic_type not in results.logic_types_used:
                        results.logic_types_used.append(logic_type)
                
                # Statut KB depuis les logs
                kb_status_match = re.search(
                    r"Création de la KB : (\w+)", 
                    self.raw_conversation_data
                )
                if kb_status_match:
                    results.knowledge_base_status = kb_status_match.group(1)
                
                # Requêtes mentionnées
                query_patterns = [
                    r"requête.{0,50}généré",
                    r"inférence.{0,50}exécuté",
                    r"validation.{0,50}effectué"
                ]
                
                for pattern in query_patterns:
                    matches = re.findall(pattern, self.raw_conversation_data, re.IGNORECASE)
                    results.inference_queries.extend(matches)
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des requêtes: {e}")
        
        return results
    
    def analyze_informal_exploration(self) -> InformalExploration:
        """
        Analyse l'exploration taxonomique informelle (général → particulier).
        
        Returns:
            InformalExploration avec le parcours taxonomique
        """
        exploration = InformalExploration(
            taxonomy_path=[],
            fallacy_detection=[],
            rhetorical_patterns=[],
            severity_analysis=[]
        )
        
        try:
            # Depuis le rapport JSON
            if self.raw_report_data:
                if 'informal_analysis' in self.raw_report_data:
                    informal = self.raw_report_data['informal_analysis']
                    
                    # Détection de sophismes
                    if 'fallacies_detected' in informal:
                        fallacies = informal['fallacies_detected']
                        for fallacy in fallacies:
                            exploration.fallacy_detection.append({
                                'type': fallacy.get('type', ''),
                                'confidence': fallacy.get('confidence', 0.0),
                                'location': fallacy.get('location', ''),
                                'severity': fallacy.get('severity', 'unknown')
                            })
                    
                    # Analyse de sévérité
                    if 'severity_distribution' in informal:
                        severity = informal['severity_distribution']
                        for level, count in severity.items():
                            exploration.severity_analysis.append({
                                'severity_level': level,
                                'count': count
                            })
            
            # Depuis le log de conversation
            if self.raw_conversation_data:
                # Chemin taxonomique (général → particulier)
                taxonomy_indicators = [
                    "Analyse générale",
                    "Catégorisation",
                    "Spécialisation",
                    "Analyse spécifique",
                    "Détection particulière"
                ]
                
                for indicator in taxonomy_indicators:
                    if re.search(indicator, self.raw_conversation_data, re.IGNORECASE):
                        exploration.taxonomy_path.append(indicator)
                
                # Patterns rhétoriques
                rhetorical_patterns = re.findall(
                    r"(structure argumentative|pattern émotionnel)",
                    self.raw_conversation_data,
                    re.IGNORECASE
                )
                exploration.rhetorical_patterns = list(set(rhetorical_patterns))
                
                # Sophismes détectés depuis les logs
                fallacy_match = re.search(
                    r"(\d+)\s+sophismes?\s+détectés?",
                    self.raw_conversation_data,
                    re.IGNORECASE
                )
                if fallacy_match:
                    count = int(fallacy_match.group(1))
                    exploration.fallacy_detection.append({
                        'total_detected': count,
                        'source': 'conversation_log'
                    })
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de l'exploration informelle: {e}")
        
        return exploration
    
    def generate_comprehensive_report(self) -> str:
        """
        Génère un rapport de synthèse complet avec tous les éléments analysés.
        
        Returns:
            Rapport de synthèse formaté en markdown
        """
        try:
            # Extraction de tous les éléments
            metadata = self.extract_metadata()
            orchestration = self.analyze_orchestration_flow()
            state_evolution = self.track_state_evolution()
            query_results = self.extract_query_results()
            informal_exploration = self.analyze_informal_exploration()
            
            # Génération du rapport
            report = []
            report.append("# RAPPORT DE SYNTHÈSE DES TRACES D'EXÉCUTION")
            report.append("=" * 60)
            report.append(f"**Généré le:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"**Analyseur:** TraceAnalyzer v2.0 - Format Conversation Agentielle")
            report.append("")
            
            # 1. Métadonnées de l'extrait
            report.append("## 1. MÉTADONNÉES DE L'EXTRAIT ANALYSÉ")
            report.append("-" * 40)
            report.append(f"- **Fichier source:** {metadata.source_file}")
            report.append(f"- **Longueur du contenu:** {metadata.content_length} caractères")
            report.append(f"- **Type de contenu:** {metadata.content_type}")
            report.append(f"- **Niveau de complexité:** {metadata.complexity_level}")
            report.append(f"- **Horodatage de l'analyse:** {metadata.analysis_timestamp}")
            if metadata.source_origin:
                report.append(f"- **Origine:** {metadata.source_origin}")
            report.append("")
            
            # 2. Flow d'orchestration
            report.append("## 2. FLOW D'ORCHESTRATION")
            report.append("-" * 30)
            report.append(f"- **Statut d'exécution:** {orchestration.success_status}")
            report.append(f"- **Temps d'exécution total:** {orchestration.total_execution_time} ms")
            report.append(f"- **Nombre d'agents appelés:** {len(orchestration.agents_called)}")
            
            if orchestration.agents_called:
                report.append("- **Agents impliqués:**")
                for agent in orchestration.agents_called:
                    report.append(f"  - {agent}")
            
            if orchestration.sequence_order:
                report.append("- **Séquence d'exécution:**")
                for i, (step, description) in enumerate(orchestration.sequence_order, 1):
                    report.append(f"  {i}. {description}")
            
            if orchestration.coordination_messages:
                report.append("- **Messages de coordination clés:**")
                for msg in orchestration.coordination_messages[:5]:  # Limite à 5
                    report.append(f"  - {msg.strip()}")
            report.append("")
            
            # 3. Évolution des états
            report.append("## 3. ÉVOLUTION DES ÉTATS")
            report.append("-" * 25)
            
            if state_evolution.progressive_enrichment:
                report.append("- **Enrichissement progressif:**")
                for enrichment in state_evolution.progressive_enrichment:
                    report.append(f"  - {enrichment}")
            
            if state_evolution.state_transitions:
                report.append("- **Transitions d'état majeures:**")
                for from_state, to_state in state_evolution.state_transitions:
                    report.append(f"  - {from_state} → {to_state}")
            
            if state_evolution.shared_state_changes:
                report.append(f"- **Modifications d'état partagé:** {len(state_evolution.shared_state_changes)} détectées")
            
            if state_evolution.belief_state_construction:
                report.append(f"- **Construction belief state:** {len(state_evolution.belief_state_construction)} phases")
            report.append("")
            
            # 4. Requêtes et résultats
            report.append("## 4. REQUÊTES ET INFÉRENCES")
            report.append("-" * 28)
            report.append(f"- **Types de logique utilisés:** {', '.join(query_results.logic_types_used) if query_results.logic_types_used else 'Aucun'}")
            report.append(f"- **Statut base de connaissances:** {query_results.knowledge_base_status}")
            report.append(f"- **Nombre de formalisations:** {len(query_results.formalizations)}")
            report.append(f"- **Requêtes d'inférence:** {len(query_results.inference_queries)}")
            report.append(f"- **Résultats de validation:** {len(query_results.validation_results)}")
            
            if query_results.validation_results:
                report.append("- **Résultats principaux:**")
                for result in query_results.validation_results[:3]:  # Limite à 3
                    confidence = result.get('confidence', 'N/A')
                    report.append(f"  - Requête: {result.get('query', 'N/A')[:50]}...")
                    report.append(f"    Résultat: {result.get('result', 'N/A')}, Confiance: {confidence}")
            report.append("")
            
            # 5. Exploration taxonomique
            report.append("## 5. EXPLORATION TAXONOMIQUE INFORMELLE")
            report.append("-" * 40)
            
            if informal_exploration.taxonomy_path:
                report.append("- **Parcours taxonomique (général → particulier):**")
                for i, step in enumerate(informal_exploration.taxonomy_path, 1):
                    report.append(f"  {i}. {step}")
            
            if informal_exploration.fallacy_detection:
                report.append("- **Détection de sophismes:**")
                for detection in informal_exploration.fallacy_detection:
                    if 'total_detected' in detection:
                        report.append(f"  - Total détecté: {detection['total_detected']}")
                    else:
                        report.append(f"  - Type: {detection.get('type', 'N/A')}, "
                                    f"Confiance: {detection.get('confidence', 'N/A')}, "
                                    f"Sévérité: {detection.get('severity', 'N/A')}")
            
            if informal_exploration.severity_analysis:
                report.append("- **Analyse de sévérité:**")
                for analysis in informal_exploration.severity_analysis:
                    report.append(f"  - {analysis['severity_level']}: {analysis['count']}")
            
            if informal_exploration.rhetorical_patterns:
                report.append("- **Patterns rhétoriques identifiés:**")
                for pattern in informal_exploration.rhetorical_patterns:
                    report.append(f"  - {pattern}")
            report.append("")
            
            # 6. Synthèse et conclusions
            report.append("## 6. SYNTHÈSE ET CONCLUSIONS")
            report.append("-" * 30)
            
            # Calcul de métriques de synthèse
            total_components = (
                len(orchestration.agents_called) +
                len(state_evolution.progressive_enrichment) +
                len(query_results.logic_types_used) +
                len(informal_exploration.fallacy_detection)
            )
            
            report.append(f"- **Richesse des traces:** {total_components} composants analysés")
            report.append(f"- **Complexité de l'orchestration:** {len(orchestration.sequence_order)} étapes")
            report.append(f"- **Exhaustivité de l'analyse:** "
                        f"Formelle ({len(query_results.logic_types_used)} types) + "
                        f"Informelle ({len(informal_exploration.fallacy_detection)} détections)")
            
            # Évaluation globale
            if orchestration.success_status == "success":
                status_eval = "✅ Excellente"
            elif orchestration.success_status == "completed":
                status_eval = "✅ Satisfaisante"
            else:
                status_eval = "⚠️ Partielle"
            
            report.append(f"- **Évaluation globale:** {status_eval}")
            
            # Recommandations
            report.append("")
            report.append("### Recommandations pour amélioration:")
            
            if not query_results.validation_results:
                report.append("- Améliorer la génération et l'exécution des requêtes d'inférence")
            
            if len(informal_exploration.fallacy_detection) == 0:
                report.append("- Enrichir la détection de sophismes avec des textes plus complexes")
            
            if orchestration.total_execution_time == 0:
                report.append("- Améliorer la mesure des performances temporelles")
            
            if not state_evolution.shared_state_changes:
                report.append("- Renforcer le tracking des changements d'état")
            
            report.append("")
            report.append("=" * 60)
            report.append("*Rapport généré par TraceAnalyzer v2.0 - Système d'Argumentation Unifié*")
            report.append("*Format conversation agentielle optimisé*")
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            return f"Erreur lors de la génération du rapport: {e}"


# Fonctions utilitaires pour usage direct
def analyze_latest_traces(logs_dir: str = "./logs") -> str:
    """
    Analyse les dernières traces disponibles et génère un rapport.
    
    Args:
        logs_dir: Répertoire des logs
        
    Returns:
        Rapport de synthèse complet
    """
    analyzer = TraceAnalyzer(logs_dir)
    
    if analyzer.load_traces():
        return analyzer.generate_comprehensive_report()
    else:
        return "Erreur: Impossible de charger les traces"


def quick_metadata_extract(logs_dir: str = "./logs") -> ExtractMetadata:
    """
    Extraction rapide des métadonnées uniquement.
    
    Args:
        logs_dir: Répertoire des logs
        
    Returns:
        Métadonnées de l'extrait
    """
    analyzer = TraceAnalyzer(logs_dir)
    analyzer.load_traces()
    return analyzer.extract_metadata()


def generate_conversation_report(logs_dir: str = "./logs") -> str:
    """
    Génère un rapport au format conversation agentielle optimisé.
    
    Args:
        logs_dir: Répertoire des logs
        
    Returns:
        Rapport de conversation agentielle
    """
    analyzer = TraceAnalyzer(logs_dir)
    analyzer.load_traces()
    return analyzer.generate_conversation_format_report()


if __name__ == "__main__":
    # Test simple du TraceAnalyzer avec nouveau format
    print("=== Test du TraceAnalyzer v2.0 - Format Conversation ===")
    report = analyze_latest_traces()
    print(report)