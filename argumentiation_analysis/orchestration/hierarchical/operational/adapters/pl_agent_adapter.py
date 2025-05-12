"""
Module d'adaptation de l'agent de logique propositionnelle pour l'architecture hiérarchique.

Ce module fournit un adaptateur qui permet à l'agent de logique propositionnelle existant
de fonctionner comme un agent opérationnel dans l'architecture hiérarchique.
"""

import os
import re
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.functions.kernel_arguments import KernelArguments

from argumentiation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent
from argumentiation_analysis.orchestration.hierarchical.operational.state import OperationalState

# Import de l'agent PL existant
from argumentiation_analysis.agents.core.pl.pl_definitions import PropositionalLogicPlugin, setup_pl_kernel, PL_AGENT_INSTRUCTIONS
from argumentiation_analysis.core.llm_service import create_llm_service
from argumentiation_analysis.core.jvm_setup import initialize_jvm


class PLAgentAdapter(OperationalAgent):
    """
    Adaptateur pour l'agent de logique propositionnelle.
    
    Cet adaptateur permet à l'agent de logique propositionnelle existant de fonctionner
    comme un agent opérationnel dans l'architecture hiérarchique.
    """
    
    def __init__(self, name: str = "PLAgent", operational_state: Optional[OperationalState] = None):
        """
        Initialise un nouvel adaptateur pour l'agent de logique propositionnelle.
        
        Args:
            name: Nom de l'agent
            operational_state: État opérationnel à utiliser. Si None, un nouvel état est créé.
        """
        super().__init__(name, operational_state)
        self.kernel = None
        self.pl_plugin = None
        self.pl_agent = None
        self.llm_service = None
        self.initialized = False
        self.logger = logging.getLogger(f"PLAgentAdapter.{name}")
    
    async def initialize(self):
        """
        Initialise l'agent de logique propositionnelle.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        if self.initialized:
            return True
        
        try:
            self.logger.info("Initialisation de l'agent de logique propositionnelle...")
            
            # S'assurer que la JVM est démarrée
            jvm_ready = initialize_jvm()
            if not jvm_ready:
                self.logger.error("Échec du démarrage de la JVM.")
                return False
            
            # Créer le service LLM
            self.llm_service = create_llm_service()
            if not self.llm_service:
                self.logger.error("Échec de la création du service LLM.")
                return False
            
            # Créer le kernel
            self.kernel = sk.Kernel()
            self.kernel.add_service(self.llm_service)
            
            # Configurer le kernel pour l'agent PL
            setup_pl_kernel(self.kernel, self.llm_service)
            
            # Récupérer le plugin PL
            if "PLAnalyzer" in self.kernel.plugins:
                self.pl_plugin = self.kernel.plugins["PLAnalyzer"]
                self.logger.info("Plugin PLAnalyzer récupéré avec succès.")
            else:
                self.logger.error("Plugin PLAnalyzer non trouvé dans le kernel.")
                return False
            
            # Créer l'agent PL
            prompt_exec_settings = self.kernel.get_prompt_execution_settings_from_service_id(self.llm_service.service_id)
            self.pl_agent = sk.ChatCompletionAgent(
                kernel=self.kernel,
                service=self.llm_service,
                name="PLAgent",
                instructions=PL_AGENT_INSTRUCTIONS,
                arguments=KernelArguments(settings=prompt_exec_settings)
            )
            
            self.initialized = True
            self.logger.info("Agent de logique propositionnelle initialisé avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de l'agent de logique propositionnelle: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Retourne les capacités de l'agent de logique propositionnelle.
        
        Returns:
            Liste des capacités de l'agent
        """
        return [
            "formal_logic",
            "propositional_logic",
            "validity_checking",
            "consistency_analysis"
        ]
    
    def can_process_task(self, task: Dict[str, Any]) -> bool:
        """
        Vérifie si l'agent peut traiter une tâche donnée.
        
        Args:
            task: La tâche à vérifier
            
        Returns:
            True si l'agent peut traiter la tâche, False sinon
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            return False
        
        # Vérifier si les capacités requises sont fournies par cet agent
        required_capabilities = task.get("required_capabilities", [])
        agent_capabilities = self.get_capabilities()
        
        # Vérifier si au moins une des capacités requises est fournie par l'agent
        return any(cap in agent_capabilities for cap in required_capabilities)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite une tâche opérationnelle.
        
        Args:
            task: La tâche opérationnelle à traiter
            
        Returns:
            Le résultat du traitement de la tâche
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            success = await self.initialize()
            if not success:
                return {
                    "id": f"result-{task.get('id')}",
                    "task_id": task.get("id"),
                    "tactical_task_id": task.get("tactical_task_id"),
                    "status": "failed",
                    "outputs": {},
                    "metrics": {},
                    "issues": [{
                        "type": "initialization_error",
                        "description": "Échec de l'initialisation de l'agent de logique propositionnelle",
                        "severity": "high"
                    }]
                }
        
        # Enregistrer la tâche dans l'état opérationnel
        task_id = self.register_task(task)
        
        # Mettre à jour le statut de la tâche
        self.update_task_status(task_id, "in_progress", {
            "message": "Traitement de la tâche en cours",
            "agent": self.name
        })
        
        # Mesurer le temps d'exécution
        start_time = time.time()
        
        try:
            # Extraire les informations nécessaires de la tâche
            techniques = task.get("techniques", [])
            text_extracts = task.get("text_extracts", [])
            parameters = task.get("parameters", {})
            
            # Vérifier si des extraits de texte sont fournis
            if not text_extracts:
                raise ValueError("Aucun extrait de texte fourni dans la tâche.")
            
            # Préparer les résultats
            results = []
            issues = []
            
            # Traiter chaque technique
            for technique in techniques:
                technique_name = technique.get("name", "")
                technique_params = technique.get("parameters", {})
                
                # Exécuter la technique appropriée
                if technique_name == "propositional_logic_formalization":
                    # Formaliser les arguments en logique propositionnelle
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        belief_set = await self._text_to_belief_set(extract_content, technique_params)
                        
                        if belief_set:
                            results.append({
                                "type": "formal_analyses",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "belief_set": belief_set,
                                "formalism": "propositional_logic",
                                "confidence": 0.8  # Valeur arbitraire pour l'exemple
                            })
                        else:
                            issues.append({
                                "type": "formalization_error",
                                "description": "Échec de la formalisation en logique propositionnelle",
                                "severity": "medium",
                                "extract_id": extract.get("id")
                            })
                
                elif technique_name == "validity_checking":
                    # Vérifier la validité des arguments formalisés
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # D'abord, formaliser le texte en belief set
                        belief_set = await self._text_to_belief_set(extract_content, technique_params)
                        
                        if not belief_set:
                            issues.append({
                                "type": "formalization_error",
                                "description": "Échec de la formalisation en logique propositionnelle",
                                "severity": "medium",
                                "extract_id": extract.get("id")
                            })
                            continue
                        
                        # Ensuite, générer et exécuter des requêtes
                        queries_results = await self._generate_and_execute_queries(extract_content, belief_set, technique_params)
                        
                        if queries_results:
                            results.append({
                                "type": "validity_analysis",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "belief_set": belief_set,
                                "queries": queries_results.get("queries", []),
                                "results": queries_results.get("results", []),
                                "interpretation": queries_results.get("interpretation", ""),
                                "confidence": 0.8  # Valeur arbitraire pour l'exemple
                            })
                        else:
                            issues.append({
                                "type": "validity_checking_error",
                                "description": "Échec de la vérification de validité",
                                "severity": "medium",
                                "extract_id": extract.get("id")
                            })
                
                elif technique_name == "consistency_checking":
                    # Vérifier la cohérence des arguments formalisés
                    for extract in text_extracts:
                        extract_content = extract.get("content", "")
                        if not extract_content:
                            continue
                        
                        # D'abord, formaliser le texte en belief set
                        belief_set = await self._text_to_belief_set(extract_content, technique_params)
                        
                        if not belief_set:
                            issues.append({
                                "type": "formalization_error",
                                "description": "Échec de la formalisation en logique propositionnelle",
                                "severity": "medium",
                                "extract_id": extract.get("id")
                            })
                            continue
                        
                        # Ensuite, vérifier la cohérence
                        consistency_result = await self._check_consistency(belief_set, technique_params)
                        
                        if consistency_result is not None:
                            results.append({
                                "type": "consistency_analysis",
                                "extract_id": extract.get("id"),
                                "source": extract.get("source"),
                                "belief_set": belief_set,
                                "is_consistent": consistency_result.get("is_consistent", False),
                                "explanation": consistency_result.get("explanation", ""),
                                "confidence": 0.8  # Valeur arbitraire pour l'exemple
                            })
                        else:
                            issues.append({
                                "type": "consistency_checking_error",
                                "description": "Échec de la vérification de cohérence",
                                "severity": "medium",
                                "extract_id": extract.get("id")
                            })
                
                else:
                    issues.append({
                        "type": "unsupported_technique",
                        "description": f"Technique non supportée: {technique_name}",
                        "severity": "medium",
                        "details": {
                            "technique": technique_name,
                            "parameters": technique_params
                        }
                    })
            
            # Calculer les métriques
            execution_time = time.time() - start_time
            metrics = {
                "execution_time": execution_time,
                "confidence": 0.8 if results else 0.0,
                "coverage": 1.0 if text_extracts and results else 0.0,
                "resource_usage": 0.7  # Valeur arbitraire pour l'exemple
            }
            
            # Mettre à jour les métriques dans l'état opérationnel
            self.update_metrics(task_id, metrics)
            
            # Déterminer le statut final
            status = "completed"
            if issues:
                status = "completed_with_issues"
            
            # Mettre à jour le statut de la tâche
            self.update_task_status(task_id, status, {
                "message": f"Traitement terminé avec statut: {status}",
                "results_count": len(results),
                "issues_count": len(issues)
            })
            
            # Formater et retourner le résultat
            return self.format_result(task, results, metrics, issues)
        
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la tâche {task_id}: {e}")
            
            # Mettre à jour le statut de la tâche
            self.update_task_status(task_id, "failed", {
                "message": f"Erreur lors du traitement: {str(e)}",
                "exception": str(e)
            })
            
            # Calculer les métriques
            execution_time = time.time() - start_time
            metrics = {
                "execution_time": execution_time,
                "confidence": 0.0,
                "coverage": 0.0,
                "resource_usage": 0.5  # Valeur arbitraire pour l'exemple
            }
            
            # Mettre à jour les métriques dans l'état opérationnel
            self.update_metrics(task_id, metrics)
            
            # Retourner un résultat d'erreur
            return {
                "id": f"result-{task_id}",
                "task_id": task_id,
                "tactical_task_id": task.get("tactical_task_id"),
                "status": "failed",
                "outputs": {},
                "metrics": metrics,
                "issues": [{
                    "type": "execution_error",
                    "description": f"Erreur lors du traitement: {str(e)}",
                    "severity": "high",
                    "details": {
                        "exception": str(e)
                    }
                }]
            }
    
    async def _text_to_belief_set(self, text: str, parameters: Dict[str, Any]) -> Optional[str]:
        """
        Traduit un texte en belief set de logique propositionnelle.
        
        Args:
            text: Le texte à traduire
            parameters: Les paramètres de traduction
            
        Returns:
            Le belief set généré ou None en cas d'erreur
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            await self.initialize()
        
        try:
            # Créer un message de chat pour l'agent
            chat_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"Traduis ce texte en Belief Set de logique propositionnelle (syntaxe Tweety):\n\n{text}"
            )
            
            # Appeler l'agent PL
            response_content = ""
            async for chunk in self.pl_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    response_content = chunk.content
                    break  # Prendre seulement la première réponse complète
            
            # Extraire le belief set de la réponse
            belief_set = None
            
            # Rechercher un bloc de code dans la réponse
            code_match = re.search(r'```(?:pl|tweety)?\s*([\s\S]*?)\s*```', response_content)
            if code_match:
                belief_set = code_match.group(1).strip()
            
            # Si aucun bloc de code n'est trouvé, essayer d'extraire le belief set directement
            if not belief_set:
                # Rechercher un pattern comme "Belief Set:" suivi du contenu
                bs_match = re.search(r'Belief Set:\s*([\s\S]*?)(?:\n\n|\Z)', response_content)
                if bs_match:
                    belief_set = bs_match.group(1).strip()
            
            # Si toujours pas de belief set, utiliser toute la réponse
            if not belief_set:
                belief_set = response_content.strip()
            
            # Vérifier que le belief set est valide
            if belief_set and len(belief_set) > 0:
                return belief_set
            else:
                self.logger.warning("Belief set vide ou invalide généré.")
                return None
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la traduction en belief set: {e}")
            return None
    
    async def _generate_and_execute_queries(self, text: str, belief_set: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Génère et exécute des requêtes sur un belief set.
        
        Args:
            text: Le texte original
            belief_set: Le belief set à interroger
            parameters: Les paramètres d'exécution
            
        Returns:
            Un dictionnaire contenant les requêtes, les résultats et l'interprétation, ou None en cas d'erreur
        """
        # Vérifier si l'agent est initialisé
        if not self.initialized:
            await self.initialize()
        
        try:
            # Générer les requêtes
            queries = await self._generate_queries(text, belief_set, parameters)
            
            if not queries:
                self.logger.warning("Aucune requête générée.")
                return None
            
            # Exécuter les requêtes
            results = []
            for query in queries:
                result = self._execute_query(belief_set, query)
                results.append(result)
            
            # Interpréter les résultats
            interpretation = await self._interpret_results(text, belief_set, queries, results)
            
            return {
                "queries": queries,
                "results": results,
                "interpretation": interpretation
            }
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération et de l'exécution des requêtes: {e}")
            return None
    
    async def _generate_queries(self, text: str, belief_set: str, parameters: Dict[str, Any]) -> List[str]:
        """
        Génère des requêtes pour un belief set.
        
        Args:
            text: Le texte original
            belief_set: Le belief set à interroger
            parameters: Les paramètres de génération
            
        Returns:
            Liste des requêtes générées
        """
        try:
            # Créer un message de chat pour l'agent
            chat_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"Génère des requêtes pertinentes en logique propositionnelle pour ce texte et ce belief set:\n\nTexte:\n{text}\n\nBelief Set:\n{belief_set}"
            )
            
            # Appeler l'agent PL
            response_content = ""
            async for chunk in self.pl_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    response_content = chunk.content
                    break  # Prendre seulement la première réponse complète
            
            # Extraire les requêtes de la réponse
            queries = []
            
            # Rechercher un bloc de code dans la réponse
            code_match = re.search(r'```(?:pl|tweety)?\s*([\s\S]*?)\s*```', response_content)
            if code_match:
                # Diviser le bloc de code en lignes et filtrer les lignes vides
                queries = [q.strip() for q in code_match.group(1).strip().split('\n') if q.strip()]
            
            # Si aucun bloc de code n'est trouvé, essayer d'extraire les requêtes directement
            if not queries:
                # Rechercher des lignes qui ressemblent à des requêtes
                query_matches = re.finditer(r'(?:Requête|Query)\s+\d+:\s*(.*?)(?:\n|$)', response_content)
                queries = [match.group(1).strip() for match in query_matches if match.group(1).strip()]
            
            # Si toujours pas de requêtes, essayer d'extraire toutes les lignes qui contiennent des opérateurs PL
            if not queries:
                # Rechercher des lignes qui contiennent des opérateurs PL (!, ||, =>, <=>, ^^)
                query_lines = [line.strip() for line in response_content.split('\n') 
                              if any(op in line for op in ['!', '||', '=>', '<=>', '^^'])]
                queries = query_lines
            
            return queries
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des requêtes: {e}")
            return []
    
    def _execute_query(self, belief_set: str, query: str) -> Dict[str, Any]:
        """
        Exécute une requête sur un belief set.
        
        Args:
            belief_set: Le belief set à interroger
            query: La requête à exécuter
            
        Returns:
            Le résultat de la requête
        """
        try:
            # Vérifier si le plugin PL est disponible
            if not self.pl_plugin or not hasattr(self.pl_plugin, "execute_pl_query"):
                self.logger.error("Plugin PL non disponible ou méthode execute_pl_query non trouvée.")
                return {
                    "query": query,
                    "status": "error",
                    "message": "Plugin PL non disponible"
                }
            
            # Exécuter la requête
            result_str = self.pl_plugin.execute_pl_query(belief_set, query)
            
            # Analyser le résultat
            if result_str.startswith("FUNC_ERROR:"):
                return {
                    "query": query,
                    "status": "error",
                    "message": result_str[11:].strip()  # Enlever "FUNC_ERROR: "
                }
            elif "ACCEPTED" in result_str:
                return {
                    "query": query,
                    "status": "accepted",
                    "message": result_str
                }
            elif "REJECTED" in result_str:
                return {
                    "query": query,
                    "status": "rejected",
                    "message": result_str
                }
            elif "Unknown" in result_str:
                return {
                    "query": query,
                    "status": "unknown",
                    "message": result_str
                }
            else:
                return {
                    "query": query,
                    "status": "unknown",
                    "message": result_str
                }
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la requête '{query}': {e}")
            return {
                "query": query,
                "status": "error",
                "message": str(e)
            }
    
    async def _interpret_results(self, text: str, belief_set: str, queries: List[str], results: List[Dict[str, Any]]) -> str:
        """
        Interprète les résultats des requêtes.
        
        Args:
            text: Le texte original
            belief_set: Le belief set utilisé
            queries: Les requêtes exécutées
            results: Les résultats des requêtes
            
        Returns:
            L'interprétation des résultats
        """
        try:
            # Formater les requêtes et les résultats pour l'interprétation
            queries_str = "\n".join(queries)
            results_str = "\n".join([f"Query: {r['query']} -> {r['status'].upper()}: {r['message']}" for r in results])
            
            # Créer un message de chat pour l'agent
            chat_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=f"Interprète les résultats de ces requêtes en logique propositionnelle:\n\nTexte original:\n{text}\n\nBelief Set:\n{belief_set}\n\nRequêtes:\n{queries_str}\n\nRésultats:\n{results_str}"
            )
            
            # Appeler l'agent PL
            response_content = ""
            async for chunk in self.pl_agent.invoke([chat_message]):
                if hasattr(chunk, 'content') and chunk.content:
                    response_content = chunk.content
                    break  # Prendre seulement la première réponse complète
            
            return response_content.strip()
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'interprétation des résultats: {e}")
            return f"Erreur lors de l'interprétation des résultats: {e}"
    
    async def _check_consistency(self, belief_set: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Vérifie la cohérence d'un belief set.
        
        Args:
            belief_set: Le belief set à vérifier
            parameters: Les paramètres de vérification
            
        Returns:
            Un dictionnaire contenant le résultat de la vérification, ou None en cas d'erreur
        """
        try:
            # Créer une requête pour vérifier la cohérence
            # En logique propositionnelle, un ensemble est incohérent si et seulement si il implique à la fois une proposition et sa négation
            # Nous pouvons vérifier cela en créant une requête qui vérifie si l'ensemble implique "+" (tautologie)
            # Si l'ensemble est incohérent, il impliquera "+" (car un ensemble incohérent implique tout)
            
            result = self._execute_query(belief_set, "+")
            
            if result["status"] == "error":
                self.logger.warning(f"Erreur lors de la vérification de cohérence: {result['message']}")
                return None
            
            # Interpréter le résultat
            is_consistent = result["status"] != "accepted"
            
            # Générer une explication
            explanation = ""
            if is_consistent:
                explanation = "Le belief set est cohérent car il n'implique pas de contradiction."
            else:
                explanation = "Le belief set est incohérent car il implique une contradiction."
            
            return {
                "is_consistent": is_consistent,
                "explanation": explanation
            }
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de cohérence: {e}")
            return None