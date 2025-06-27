#!/usr/bin/env python3
"""
Dependencies simplifiées pour l'API FastAPI - GPT-4o-mini authentique
=======================================================================

Version simplifiée qui évite les imports complexes et utilise directement GPT-4o-mini.
"""

import logging
import time
import os
from typing import Dict, Any
import asyncio

# Utilisation directe d'OpenAI pour GPT-4o-mini
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI non disponible, utilisation de mocks")

class SimpleAnalysisService:
    """Service d'analyse simplifié utilisant directement GPT-4o-mini"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.initialized = False
        self.force_mock = os.getenv('FORCE_MOCK_LLM', '0') == '1'
        if self.force_mock:
            self.logger.warning("✅ Mode MOCK forcé par la variable d'environnement FORCE_MOCK_LLM.")

    async def _initialize_openai(self):
        """Initialise le client OpenAI pour GPT-4o-mini de manière asynchrone."""
        if self.initialized:
            return

        # Si le mode mock est forcé, on ne tente même pas d'initialiser OpenAI
        if self.force_mock:
            self.logger.info("Initialisation OpenAI sautée (mode mock forcé).")
            self.client = None
            self.initialized = True
            return
            
        self.logger.info("Initialisation asynchrone du client OpenAI...")
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI non disponible, mode dégradé")
            self.initialized = True
            return

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            self.logger.warning("OPENAI_API_KEY non définie")
            self.initialized = True
            return

        try:
            self.client = OpenAI(api_key=api_key)
            # Valide la clé de manière asynchrone pour ne pas bloquer
            await asyncio.to_thread(self.client.models.list)
            self.logger.info("✅ Client OpenAI GPT-4o-mini initialisé et clé validée.")
        except openai.AuthenticationError as e:
            self.logger.error(f"❌ Erreur d'authentification OpenAI: {e}")
            self.client = None
        except Exception as e:
            self.logger.error(f"❌ Erreur inattendue pendant l'initialisation d'OpenAI: {e}")
            self.client = None
        
        self.initialized = True
    
    async def analyze_text(self, text: str) -> dict:
        """
        Analyse authentique du texte avec GPT-4o-mini
        """
        start_time = time.time()
        self.logger.info(f"[API-SIMPLE] Analyse GPT-4o-mini : {text[:100]}...")
        
        # Initialisation paresseuse et asynchrone
        if not self.initialized:
            await self._initialize_openai()

        if not self.client:
            return self._fallback_analysis(text, start_time)

        try:
            # Appel authentique à GPT-4o-mini
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": """Tu es un expert en analyse argumentative et détection de sophismes. 
                        Analyse le texte fourni et identifie :
                        1. Les sophismes logiques présents
                        2. La structure argumentative
                        3. Les faiblesses de raisonnement
                        
                        Réponds en JSON avec cette structure :
                        {
                            "fallacies": [{"type": "nom_sophisme", "description": "explication", "confidence": 0.8}],
                            "argument_structure": "description de la structure",
                            "summary": "résumé de l'analyse"
                        }"""
                    },
                    {"role": "user", "content": f"Analyse ce texte : {text}"}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            duration = time.time() - start_time
            
            # Parser la réponse JSON de GPT-4o-mini
            gpt_content = response.choices[0].message.content
            
            try:
                import json
                gpt_result = json.loads(gpt_content)
                fallacies = gpt_result.get('fallacies', [])
                summary = gpt_result.get('summary', "Résumé non fourni par l'IA.")
            except (json.JSONDecodeError, AttributeError):
                # Fallback si GPT ne renvoie pas du JSON valide ou si gpt_content n'est pas une string
                fallacies = [{"type": "Analyse_GPT4o_Textuelle", "description": str(gpt_content)[:200], "confidence": 0.9}]
                summary = "Impossible de parser la réponse de l'IA."
            
            self.logger.info(f"✅ Analyse GPT-4o-mini terminée en {duration:.2f}s")
            
            return {
                'fallacies': fallacies,
                'duration': duration,
                'components_used': ['GPT-4o-mini', 'OpenAI-API', 'SimpleAnalysisService'],
                'summary': summary,
                'authentic_gpt4o_used': True,
                'gpt_model_used': response.model,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'analysis_metadata': {
                    'text_length': len(text),
                    'processing_time': duration,
                    'model_confirmed': response.model
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur GPT-4o-mini: {e}")
            return self._fallback_analysis(text, start_time, error=str(e))
    
    def _fallback_analysis(self, text: str, start_time: float, error: str = None) -> dict:
        """Analyse de fallback sans GPT"""
        duration = time.time() - start_time
        
        # Détection basique de sophismes par mots-clés
        fallacies = []
        
        text_lower = text.lower()
        if any(word in text_lower for word in ['tous', 'toujours', 'jamais', 'aucun']):
            fallacies.append({
                "type": "Généralisation_Hâtive_Suspecte",
                "description": "Utilisation de termes absolus pouvant indiquer une généralisation hâtive",
                "confidence": 0.6
            })
        
        if any(word in text_lower for word in ['faux', 'menteur', 'idiot', 'stupide']):
            fallacies.append({
                "type": "Ad_Hominem_Potentiel", 
                "description": "Attaque possible contre la personne plutôt que l'argument",
                "confidence": 0.7
            })
        
        return {
            'fallacies': fallacies,
            'duration': duration,
            'components_used': ['FallbackAnalyzer'],
            'summary': f"Analyse de fallback terminée. {len(fallacies)} sophismes détectés par mots-clés.",
            'authentic_gpt4o_used': False,
            'gpt_model_used': 'fallback_mode',  # Clé ajoutée pour la cohérence
            'fallback_reason': error or 'OpenAI non disponible',
            'analysis_metadata': {
                'text_length': len(text),
                'processing_time': duration,
                'method': 'keyword_fallback'
            }
        }
    
    async def ensure_initialized_and_available(self) -> bool:
        """
        S'assure que le client est initialisé et vérifie sa disponibilité.
        """
        if not self.initialized:
            await self._initialize_openai()
        return self.client is not None

    def get_status_details(self) -> dict:
        """Retourne les détails du statut actuels."""
        return {
            "service_type": "SimpleAnalysisService",
            "gpt4o_mini_enabled": self.client is not None,
            "openai_available": OPENAI_AVAILABLE,
            "mock_disabled": True,
            "service_initialized": self.initialized
        }

# Service global simplifié
_global_simple_service = None

async def get_simple_analysis_service():
    """Injection de dépendance pour le service simplifié"""
    global _global_simple_service
    
    if _global_simple_service is None:
        logging.info("[API-SIMPLE] Initialisation du service d'analyse simplifié...")
        _global_simple_service = SimpleAnalysisService()
        logging.info("[API-SIMPLE] Service initialisé")
    
    return _global_simple_service