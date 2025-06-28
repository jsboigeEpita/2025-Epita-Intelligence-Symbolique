"""
Intégration avec les LLMs pour la génération de contre-arguments.

Ce module permet de générer des contre-arguments en utilisant des grands modèles
de langage (LLMs) via des API comme OpenAI.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional

import openai
from openai import OpenAI, AsyncOpenAI

# Ajouter dotenv pour charger les variables d'environnement depuis .env
from dotenv import load_dotenv

from ..agent.definitions import (
    Argument, 
    CounterArgument, 
    CounterArgumentType,
    ArgumentStrength,
    RhetoricalStrategy,
    Vulnerability
)
from .prompts import (
    ARGUMENT_ANALYSIS_PROMPT,
    VULNERABILITY_IDENTIFICATION_PROMPT,
    COUNTER_ARGUMENT_GENERATION_PROMPT,
    COUNTER_ARGUMENT_EVALUATION_PROMPT,
    format_prompt
)

logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class LLMGenerator:
    """
    Classe pour générer des contre-arguments en utilisant des LLMs.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialise le générateur LLM.
        
        Args:
            api_key: Clé API pour le service LLM (OpenAI par défaut)
            model: Modèle LLM à utiliser
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        
        # Initialiser le client OpenAI
        openai.api_key = self.api_key
        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        
        logger.info(f"LLMGenerator initialisé avec le modèle {self.model}")
    
    def analyze_argument(self, argument_text: str) -> Dict[str, Any]:
        """
        Analyse un argument en utilisant un LLM.
        
        Args:
            argument_text: Le texte de l'argument à analyser
            
        Returns:
            Un dictionnaire contenant l'analyse de l'argument
        """
        prompt = format_prompt(ARGUMENT_ANALYSIS_PROMPT, argument_text=argument_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en analyse d'arguments. Votre tâche est d'analyser la structure d'un argument."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Réponse LLM pour l'analyse d'argument: {content[:100]}...")
            
            # Parser la réponse
            return self._parse_argument_analysis(content)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse d'argument avec LLM: {e}")
            return {
                "premises": [],
                "conclusion": "",
                "argument_type": "unknown",
                "explanation": "Erreur lors de l'analyse"
            }
    
    def identify_vulnerabilities(self, argument: Argument) -> List[Dict[str, Any]]:
        """
        Identifie les vulnérabilités d'un argument en utilisant un LLM.
        
        Args:
            argument: L'argument à analyser
            
        Returns:
            Une liste de vulnérabilités identifiées
        """
        premises_str = "\n".join([f"- {p}" for p in argument.premises])
        prompt = format_prompt(
            VULNERABILITY_IDENTIFICATION_PROMPT,
            argument_text=argument.content,
            premises=premises_str,
            conclusion=argument.conclusion,
            argument_type=argument.argument_type
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en analyse d'arguments. Votre tâche est d'identifier les vulnérabilités dans un argument."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Réponse LLM pour l'identification des vulnérabilités: {content[:100]}...")
            
            # Parser la réponse JSON
            try:
                data = json.loads(content)
                return data.get("vulnerabilities", [])
            except json.JSONDecodeError:
                logger.error(f"Erreur de décodage JSON: {content}")
                return []
            
        except Exception as e:
            logger.error(f"Erreur lors de l'identification des vulnérabilités avec LLM: {e}")
            return []
    
    def generate_counter_argument(
        self,
        argument: Argument,
        counter_type: CounterArgumentType,
        vulnerabilities: List[Vulnerability] = None,
        rhetorical_strategy: RhetoricalStrategy = None
    ) -> Dict[str, Any]:
        """
        Génère un contre-argument en utilisant un LLM.
        
        Args:
            argument: L'argument original
            counter_type: Le type de contre-argument à générer
            vulnerabilities: Liste des vulnérabilités identifiées (optionnel)
            rhetorical_strategy: Stratégie rhétorique à utiliser (optionnel)
            
        Returns:
            Un dictionnaire contenant le contre-argument généré
        """
        premises_str = "\n".join([f"- {p}" for p in argument.premises])
        
        # Formater les vulnérabilités
        if vulnerabilities:
            vulns_str = "\n".join([
                f"- Type: {v.type}, Cible: {v.target}, Score: {v.score:.2f}, "
                f"Description: {v.description}"
                for v in vulnerabilities
            ])
        else:
            vulns_str = "Aucune vulnérabilité spécifique identifiée."
        
        # Préparer la stratégie rhétorique
        strat_str = rhetorical_strategy.value if rhetorical_strategy else "au choix"
        
        prompt = format_prompt(
            COUNTER_ARGUMENT_GENERATION_PROMPT,
            argument_text=argument.content,
            premises=premises_str,
            conclusion=argument.conclusion,
            argument_type=argument.argument_type,
            vulnerabilities=vulns_str,
            counter_type=counter_type.value,
            rhetorical_strategy=strat_str
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en argumentation. Votre tâche est de générer un contre-argument pertinent."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Réponse LLM pour la génération de contre-argument: {content[:100]}...")
            
            # Parser la réponse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Erreur de décodage JSON: {content}")
                return {
                    "counter_argument": "Erreur lors de la génération du contre-argument.",
                    "target_component": "unknown",
                    "strength": "weak",
                    "confidence": 0.5,
                    "supporting_evidence": [],
                    "explanation": "Erreur de format dans la réponse du LLM."
                }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de contre-argument avec LLM: {e}")
            return {
                "counter_argument": f"Erreur lors de la génération: {str(e)}",
                "target_component": "error",
                "strength": "weak",
                "confidence": 0.1,
                "supporting_evidence": [],
                "explanation": f"Exception: {str(e)}"
            }
    
    def evaluate_counter_argument(
        self,
        original_argument: Argument,
        counter_argument: CounterArgument
    ) -> Dict[str, Any]:
        """
        Évalue la qualité d'un contre-argument en utilisant un LLM.
        
        Args:
            original_argument: L'argument original
            counter_argument: Le contre-argument à évaluer
            
        Returns:
            Un dictionnaire contenant l'évaluation du contre-argument
        """
        prompt = format_prompt(
            COUNTER_ARGUMENT_EVALUATION_PROMPT,
            original_argument=original_argument.content,
            counter_argument=counter_argument.counter_content,
            counter_type=counter_argument.counter_type.value,
            rhetorical_strategy=counter_argument.rhetorical_strategy
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en évaluation d'arguments. Votre tâche est d'évaluer la qualité d'un contre-argument."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Réponse LLM pour l'évaluation de contre-argument: {content[:100]}...")
            
            # Parser la réponse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Erreur de décodage JSON: {content}")
                return {
                    "scores": {
                        "relevance": 0.5,
                        "logical_strength": 0.5,
                        "persuasiveness": 0.5,
                        "originality": 0.5,
                        "clarity": 0.5
                    },
                    "overall_score": 0.5,
                    "recommendations": ["Erreur de format dans la réponse du LLM."],
                    "explanation": "Erreur de décodage JSON dans la réponse du LLM."
                }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation de contre-argument avec LLM: {e}")
            return {
                "scores": {
                    "relevance": 0.3,
                    "logical_strength": 0.3,
                    "persuasiveness": 0.3,
                    "originality": 0.3,
                    "clarity": 0.3
                },
                "overall_score": 0.3,
                "recommendations": [f"Erreur: {str(e)}"],
                "explanation": f"Exception lors de l'évaluation: {str(e)}"
            }
    
    async def analyze_argument_async(self, argument_text: str) -> Dict[str, Any]:
        """
        Analyse un argument en utilisant un LLM de manière asynchrone.
        
        Args:
            argument_text: Le texte de l'argument à analyser
            
        Returns:
            Un dictionnaire contenant l'analyse de l'argument
        """
        prompt = format_prompt(ARGUMENT_ANALYSIS_PROMPT, argument_text=argument_text)
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en analyse d'arguments. Votre tâche est d'analyser la structure d'un argument."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Réponse LLM pour l'analyse d'argument (async): {content[:100]}...")
            
            # Parser la réponse
            return self._parse_argument_analysis(content)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse d'argument avec LLM (async): {e}")
            return {
                "premises": [],
                "conclusion": "",
                "argument_type": "unknown",
                "explanation": f"Erreur lors de l'analyse: {str(e)}"
            }
    
    async def generate_counter_argument_async(
        self,
        argument: Argument,
        counter_type: CounterArgumentType,
        vulnerabilities: List[Vulnerability] = None,
        rhetorical_strategy: RhetoricalStrategy = None
    ) -> Dict[str, Any]:
        """
        Génère un contre-argument en utilisant un LLM de manière asynchrone.
        
        Args:
            argument: L'argument original
            counter_type: Le type de contre-argument à générer
            vulnerabilities: Liste des vulnérabilités identifiées (optionnel)
            rhetorical_strategy: Stratégie rhétorique à utiliser (optionnel)
            
        Returns:
            Un dictionnaire contenant le contre-argument généré
        """
        premises_str = "\n".join([f"- {p}" for p in argument.premises])
        
        # Formater les vulnérabilités
        if vulnerabilities:
            vulns_str = "\n".join([
                f"- Type: {v.type}, Cible: {v.target}, Score: {v.score:.2f}, "
                f"Description: {v.description}"
                for v in vulnerabilities
            ])
        else:
            vulns_str = "Aucune vulnérabilité spécifique identifiée."
        
        # Préparer la stratégie rhétorique
        strat_str = rhetorical_strategy.value if rhetorical_strategy else "au choix"
        
        prompt = format_prompt(
            COUNTER_ARGUMENT_GENERATION_PROMPT,
            argument_text=argument.content,
            premises=premises_str,
            conclusion=argument.conclusion,
            argument_type=argument.argument_type,
            vulnerabilities=vulns_str,
            counter_type=counter_type.value,
            rhetorical_strategy=strat_str
        )
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en argumentation. Votre tâche est de générer un contre-argument pertinent."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Réponse LLM pour la génération de contre-argument (async): {content[:100]}...")
            
            # Parser la réponse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Erreur de décodage JSON (async): {content}")
                return {
                    "counter_argument": "Erreur lors de la génération du contre-argument.",
                    "target_component": "unknown",
                    "strength": "weak",
                    "confidence": 0.5,
                    "supporting_evidence": [],
                    "explanation": "Erreur de format dans la réponse du LLM."
                }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de contre-argument avec LLM (async): {e}")
            return {
                "counter_argument": f"Erreur lors de la génération: {str(e)}",
                "target_component": "error",
                "strength": "weak",
                "confidence": 0.1,
                "supporting_evidence": [],
                "explanation": f"Exception: {str(e)}"
            }
    
    def _parse_argument_analysis(self, text: str) -> Dict[str, Any]:
        """
        Parse la réponse du LLM pour l'analyse d'argument.
        
        Args:
            text: La réponse du LLM
            
        Returns:
            Un dictionnaire avec l'analyse structurée
        """
        result = {
            "premises": [],
            "conclusion": "",
            "argument_type": "",
            "explanation": ""
        }
        
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("- Prémisses:"):
                current_section = "premises"
                # Extraire les prémisses s'il y en a sur la même ligne
                content = line.replace("- Prémisses:", "").strip()
                if content and content != "[Liste des prémisses]":
                    result["premises"].append(content)
            elif line.startswith("- Conclusion:"):
                current_section = "conclusion"
                result["conclusion"] = line.replace("- Conclusion:", "").strip()
            elif line.startswith("- Type d'argument:"):
                current_section = "type"
                arg_type = line.replace("- Type d'argument:", "").strip()
                if arg_type != "[déductif/inductif/abductif]":
                    result["argument_type"] = arg_type
            elif line.startswith("- Explication:"):
                current_section = "explanation"
                result["explanation"] = line.replace("- Explication:", "").strip()
            elif current_section == "premises" and line.startswith("-"):
                # Ajouter une prémisse
                premise = line.replace("-", "", 1).strip()
                if premise and premise != "[Liste des prémisses]":
                    result["premises"].append(premise)
            elif current_section == "explanation":
                # Concaténer l'explication
                result["explanation"] += " " + line
        
        return result 