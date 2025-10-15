#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestionnaire Singleton pour les modèles NLP de Hugging Face.

Ce module crucial fournit la classe `NLPModelManager`, un Singleton responsable
du chargement et de la distribution des modèles NLP (de la bibliothèque `transformers`)
à travers toute l'application.

Son rôle est de :
- Assurer que chaque modèle NLP n'est chargé en mémoire qu'une seule fois.
- Centraliser la configuration des noms de modèles utilisés.
- Fournir une interface thread-safe pour le chargement et l'accès aux modèles.
- Gérer gracieusement l'absence de la bibliothèque `transformers`.
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
    Singleton qui gère le cycle de vie des modèles NLP.

    Cette classe utilise le design pattern Singleton pour garantir une seule instance
    à travers l'application. Le chargement des modèles est une opération coûteuse,
    ce pattern évite donc le gaspillage de ressources.

    Le cycle de vie est le suivant :
    1. L'instance est créée (ex: `nlp_model_manager = NLPModelManager()`).
       Le constructeur est non-bloquant.
    2. Le chargement réel est déclenché par l'appel à `load_models_sync()`.
       Cette méthode est bloquante et doit être gérée avec soin.
    3. Les modèles sont ensuite accessibles via `get_model(model_name)`.
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
        Charge tous les modèles NLP de manière synchrone et thread-safe.

        Cette méthode est le point d'entrée pour le chargement des modèles. Elle est
        conçue pour être appelée une seule fois au démarrage de l'application.

        Caractéristiques :
        - **Bloquante :** L'appelant attendra que tous les modèles soient chargés.
          À utiliser dans un thread de démarrage pour ne pas geler une IHM.
        - **Thread-safe :** Utilise un verrou pour empêcher les chargements multiples
          si la méthode est appelée par plusieurs threads simultanément.
        - **Idempotente :** Si les modèles sont déjà chargés, la méthode retourne
          immédiatement sans rien faire.
        """
        if self._models_loaded or not HAS_TRANSFORMERS:
            if self._models_loaded:
                logger.info("Modèles déjà chargés (appel synchrone).")
            else:
                logger.warning(
                    "Impossible de charger les modèles car 'transformers' n'est pas disponible."
                )
            return

        with self._lock:
            if self._models_loaded:
                return

            logger.info("Début du chargement SYNC des modèles NLP...")
            try:
                logger.info(
                    f"Chargement du modèle de classification: {TEXT_CLASSIFICATION_MODEL}"
                )
                self._models["sentiment"] = pipeline(
                    "sentiment-analysis", model=TEXT_CLASSIFICATION_MODEL
                )

                logger.info(f"Chargement du modèle NER: {NER_MODEL}")
                self._models["ner"] = pipeline("ner", model=NER_MODEL)

                self._models_loaded = True
                logger.info(
                    "Tous les modèles NLP ont été chargés et sont prêts (mode synchrone)."
                )

            except Exception as e:
                logger.error(
                    f"Erreur critique lors du chargement synchrone des modèles NLP : {e}",
                    exc_info=True,
                )
                self._models_loaded = False

    def get_model(self, model_name: str):
        """
        Récupère un pipeline de modèle NLP pré-chargé.

        Args:
            model_name (str): Le nom du modèle à récupérer (ex: 'sentiment', 'ner').

        Returns:
            Le pipeline Hugging Face si le modèle est chargé et trouvé, sinon None.
        """
        if not self._models_loaded:
            logger.warning(
                f"Tentative d'accès au modèle '{model_name}' avant la fin du chargement."
            )
            return None
        return self._models.get(model_name)

    def are_models_loaded(self) -> bool:
        """Vérifie si les modèles sont chargés."""
        return self._models_loaded


# L'instance sera maintenant gérée par l'application principale
nlp_model_manager = NLPModelManager()
