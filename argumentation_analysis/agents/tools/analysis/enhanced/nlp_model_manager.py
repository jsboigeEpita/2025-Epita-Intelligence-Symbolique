#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestionnaire de modèles NLP pour l'analyse rhétorique.

Ce module fournit un singleton pour charger et gérer les modèles NLP de Hugging Face
de manière centralisée, afin d'éviter les rechargements multiples et de
standardiser les modèles utilisés à travers l'application.
"""

import logging
import asyncio
from threading import Lock

# Configuration du logging
logger = logging.getLogger(__name__)

# Variable pour suivre l'état de l'importation de transformers
HAS_TRANSFORMERS = False
pipeline = None

try:
    from transformers import pipeline as hf_pipeline
    pipeline = hf_pipeline
    HAS_TRANSFORMERS = True
    logger.info("Bibliothèque Transformers chargée avec succès.")
except (ImportError, OSError):
    logger.warning(
        "Bibliothèque 'transformers' non trouvée. "
        "Les fonctionnalités NLP avancées seront désactivées."
    )

# --- Modèles standardisés pour l'application ---
TEXT_CLASSIFICATION_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
NER_MODEL = "dbmdz/bert-large-cased-finetuned-conll03-english"
TEXT_GENERATION_MODEL = "gpt2"


class NLPModelManager:
    """
    Singleton pour gérer le chargement et l'accès aux modèles NLP de manière asynchrone.
    """
    _instance = None
    _lock = Lock()
    _models = {}
    _models_loaded = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(NLPModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialise le gestionnaire. Le chargement des modèles est différé.
        """
        # Le constructeur est maintenant non bloquant.
        pass

    def load_models_sync(self):
        """
        Charge tous les modèles NLP requis de manière synchrone.
        Cette méthode est bloquante et doit être exécutée dans un thread séparé
        pour ne pas geler l'application principale.
        """
        if self._models_loaded or not HAS_TRANSFORMERS:
            if self._models_loaded:
                logger.info("Modèles déjà chargés (appel synchrone).")
            else:
                logger.warning("Impossible de charger les modèles car 'transformers' n'est pas disponible.")
            return

        with self._lock:
            if self._models_loaded:
                return
                
            logger.info("Début du chargement SYNC des modèles NLP...")
            try:
                logger.info(f"Chargement du modèle de classification: {TEXT_CLASSIFICATION_MODEL}")
                self._models['sentiment'] = pipeline("sentiment-analysis", model=TEXT_CLASSIFICATION_MODEL)
                
                logger.info(f"Chargement du modèle NER: {NER_MODEL}")
                self._models['ner'] = pipeline("ner", model=NER_MODEL)
                
                self._models_loaded = True
                logger.info("Tous les modèles NLP ont été chargés et sont prêts (mode synchrone).")

            except Exception as e:
                logger.error(f"Erreur critique lors du chargement synchrone des modèles NLP : {e}", exc_info=True)
                self._models_loaded = False

    def get_model(self, model_name: str):
        """
        Récupère un modèle pré-chargé. Attention : vérifier si les modèles sont chargés.
        """
        if not self._models_loaded:
            logger.warning(f"Tentative d'accès au modèle '{model_name}' avant la fin du chargement.")
            return None
        return self._models.get(model_name)

    def are_models_loaded(self) -> bool:
        """Vérifie si les modèles sont chargés."""
        return self._models_loaded

# L'instance sera maintenant gérée par l'application principale
nlp_model_manager = NLPModelManager()