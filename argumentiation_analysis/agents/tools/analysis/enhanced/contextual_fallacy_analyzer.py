#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil d'analyse contextuelle des sophismes amélioré.

Ce module fournit des fonctionnalités avancées pour analyser les sophismes dans leur contexte,
en utilisant des modèles de langage avancés, une analyse contextuelle approfondie et
des mécanismes d'apprentissage continu pour améliorer la précision de l'analyse.
"""

import os
import sys
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer l'analyseur contextuel de base
from argumentiation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer as BaseAnalyzer

# Importations pour les modèles de langage avancés
try:
    import torch
    import transformers
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    from sklearn.metrics.pairwise import cosine_similarity

from argumentiation_analysis.paths import DATA_DIR

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logging.warning("Les bibliothèques transformers et/ou torch ne sont pas installées. "
                   "L'analyseur utilisera des méthodes alternatives.")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("EnhancedContextualFallacyAnalyzer")


class EnhancedContextualFallacyAnalyzer(BaseAnalyzer):
    """
    Outil amélioré pour l'analyse contextuelle des sophismes.
    
    Cette version améliorée intègre des modèles de langage avancés, une analyse
    contextuelle approfondie et des mécanismes d'apprentissage continu pour améliorer
    la précision de l'analyse des sophismes dans leur contexte.
    """
    
    def __init__(self, taxonomy_path: Optional[str] = None, model_name: str = "distilbert-base-uncased"):
        """
        Initialise l'analyseur contextuel de sophismes amélioré.
        
        Args:
            taxonomy_path: Chemin vers le fichier de taxonomie des sophismes (optionnel)
            model_name: Nom du modèle de langage à utiliser (optionnel)
        """
        super().__init__(taxonomy_path)
        self.logger = logger
        self.model_name = model_name
        self.feedback_history = []
        self.context_embeddings_cache = {}
        self.last_analysis_fallacies = {}
        
        # Initialiser les modèles de langage si disponibles
        self.nlp_models = self._initialize_nlp_models()
        
        # Charger les données d'apprentissage précédentes si elles existent
        self.learning_data = self._load_learning_data()
        
        self.logger.info("Analyseur contextuel de sophismes amélioré initialisé.")
    
    def _initialize_nlp_models(self) -> Dict[str, Any]:
        """
        Initialise les modèles de langage avancés.
        
        Returns:
            Dictionnaire contenant les modèles de langage initialisés
        """
        models = {}
        
        if HAS_TRANSFORMERS:
            try:
                # Modèle pour la classification de texte
                self.logger.info(f"Initialisation du modèle de langage {self.model_name}")
                models["tokenizer"] = AutoTokenizer.from_pretrained(self.model_name)
                models["model"] = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                
                # Pipeline pour l'analyse de sentiment (utile pour détecter les appels à l'émotion)
                models["sentiment"] = pipeline("sentiment-analysis")
                
                # Pipeline pour la génération de texte (utile pour l'explication des sophismes)
                models["text_generation"] = pipeline("text-generation", model="gpt2")
                
                # Pipeline pour l'extraction d'entités nommées (utile pour identifier les autorités)
                models["ner"] = pipeline("ner")
                
                self.logger.info("Modèles de langage initialisés avec succès.")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'initialisation des modèles de langage: {e}")
        else:
            self.logger.warning("Fonctionnalités des modèles de langage désactivées.")
        
        return models
    
    def _load_learning_data(self) -> Dict[str, Any]:
        """
        Charge les données d'apprentissage précédentes.
        
        Returns:
            Dictionnaire contenant les données d'apprentissage
        """
        learning_data = {
            "context_patterns": {},
            "fallacy_patterns": {},
            "feedback_history": [],
            "confidence_adjustments": {}
        }
        
        try:
            learning_data_path = Path(current_dir) / DATA_DIR / "learning_data.json"
            if learning_data_path.exists():
                with open(learning_data_path, "r", encoding="utf-8") as f:
                    learning_data = json.load(f)
                self.logger.info(f"Données d'apprentissage chargées: {len(learning_data['feedback_history'])} entrées d'historique")
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des données d'apprentissage: {e}")
        
        return learning_data
    
    def _save_learning_data(self):
        """
        Sauvegarde les données d'apprentissage.
        """
        try:
            learning_data_dir = Path(current_dir) / DATA_DIR
            learning_data_dir.mkdir(exist_ok=True, parents=True)
            
            learning_data_path = learning_data_dir / "learning_data.json"
            with open(learning_data_path, "w", encoding="utf-8") as f:
                json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Données d'apprentissage sauvegardées: {len(self.learning_data['feedback_history'])} entrées d'historique")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des données d'apprentissage: {e}")
    
    def analyze_context(self, text: str, context: str) -> Dict[str, Any]:
        """
        Analyse le contexte d'un texte pour identifier des sophismes contextuels.
        
        Cette méthode améliorée utilise des modèles de langage avancés pour analyser
        un texte dans son contexte et identifier des sophismes qui dépendent du contexte.
        
        Args:
            text: Texte à analyser
            context: Contexte du texte (ex: type de discours, audience, etc.)
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        self.logger.info(f"Analyse contextuelle améliorée du texte (longueur: {len(text)}) dans le contexte: {context}")
        
        # Analyser le type de contexte de manière plus approfondie
        context_analysis = self._analyze_context_deeply(context)
        self.logger.info(f"Analyse contextuelle approfondie: {context_analysis['context_type']} (confiance: {context_analysis['confidence']:.2f})")
        
        # Identifier les sophismes potentiels avec des modèles de langage
        potential_fallacies = self._identify_potential_fallacies_with_nlp(text)
        self.logger.info(f"Sophismes potentiels identifiés avec NLP: {len(potential_fallacies)}")
        
        # Filtrer les sophismes en fonction du contexte avec une analyse sémantique
        contextual_fallacies = self._filter_by_context_semantic(potential_fallacies, context_analysis)
        self.logger.info(f"Sophismes contextuels identifiés après analyse sémantique: {len(contextual_fallacies)}")
        
        # Analyser les relations entre les sophismes
        fallacy_relations = self._analyze_fallacy_relations(contextual_fallacies)
        
        # Stocker les sophismes identifiés pour l'apprentissage
        self.last_analysis_fallacies = {f"fallacy_{i}": fallacy for i, fallacy in enumerate(contextual_fallacies)}
        
        # Préparer les résultats
        results = {
            "context_analysis": context_analysis,
            "potential_fallacies_count": len(potential_fallacies),
            "contextual_fallacies_count": len(contextual_fallacies),
            "contextual_fallacies": contextual_fallacies,
            "fallacy_relations": fallacy_relations,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return results
    
    def _analyze_context_deeply(self, context: str) -> Dict[str, Any]:
        """
        Analyse le contexte de manière approfondie.
        
        Cette méthode utilise des techniques avancées pour analyser le contexte
        et déterminer ses caractéristiques pertinentes pour l'analyse des sophismes.
        
        Args:
            context: Description du contexte
            
        Returns:
            Dictionnaire contenant l'analyse du contexte
        """
        # Vérifier si nous avons déjà analysé ce contexte
        context_key = context.lower()[:100]  # Utiliser une version tronquée comme clé
        if context_key in self.context_embeddings_cache:
            return self.context_embeddings_cache[context_key]
        
        # Déterminer le type de contexte de base
        context_type = self._determine_context_type(context)
        
        # Analyse plus approfondie avec NLP si disponible
        context_subtypes = []
        audience_characteristics = []
        formality_level = "moyen"
        confidence = 0.7  # Confiance par défaut
        
        if HAS_TRANSFORMERS and self.nlp_models:
            try:
                # Analyser le sentiment du contexte
                sentiment_result = self.nlp_models["sentiment"](context)
                sentiment = sentiment_result[0]["label"]
                sentiment_score = sentiment_result[0]["score"]
                
                # Extraire les entités nommées pour identifier l'audience
                ner_results = self.nlp_models["ner"](context)
                entities = [entity for entity in ner_results if entity["entity"].startswith("B-")]
                
                # Déterminer les sous-types de contexte
                if "politique" in context_type:
                    if "élection" in context.lower():
                        context_subtypes.append("électoral")
                    elif "parlement" in context.lower() or "assemblée" in context.lower():
                        context_subtypes.append("parlementaire")
                    elif "international" in context.lower():
                        context_subtypes.append("diplomatique")
                
                # Déterminer les caractéristiques de l'audience
                if "grand public" in context.lower():
                    audience_characteristics.append("généraliste")
                elif "expert" in context.lower() or "spécialiste" in context.lower():
                    audience_characteristics.append("expert")
                elif "étudiant" in context.lower() or "académique" in context.lower():
                    audience_characteristics.append("académique")
                
                # Déterminer le niveau de formalité
                if "formel" in context.lower() or "officiel" in context.lower():
                    formality_level = "élevé"
                elif "informel" in context.lower() or "familier" in context.lower():
                    formality_level = "faible"
                
                # Ajuster la confiance en fonction de la clarté du contexte
                confidence = min(0.9, 0.7 + len(context_subtypes) * 0.05 + len(audience_characteristics) * 0.05)
                
            except Exception as e:
                self.logger.error(f"Erreur lors de l'analyse approfondie du contexte: {e}")
        
        # Préparer les résultats de l'analyse
        context_analysis = {
            "context_type": context_type,
            "context_subtypes": context_subtypes,
            "audience_characteristics": audience_characteristics,
            "formality_level": formality_level,
            "confidence": confidence
        }
        
        # Mettre en cache les résultats
        self.context_embeddings_cache[context_key] = context_analysis
        
        return context_analysis
    
    def _identify_potential_fallacies_with_nlp(self, text: str) -> List[Dict[str, Any]]:
        """
        Identifie les sophismes potentiels dans un texte en utilisant des techniques de NLP.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des sophismes potentiels identifiés
        """
        # Commencer avec l'approche de base
        potential_fallacies = self._identify_potential_fallacies(text)
        
        # Si les modèles de langage sont disponibles, améliorer l'analyse
        if HAS_TRANSFORMERS and self.nlp_models:
            try:
                # Diviser le texte en phrases pour une analyse plus précise
                sentences = text.split(". ")
                
                for i, sentence in enumerate(sentences):
                    if not sentence.strip():
                        continue
                    
                    # Analyser le sentiment pour détecter les appels à l'émotion
                    sentiment_result = self.nlp_models["sentiment"](sentence)
                    sentiment = sentiment_result[0]["label"]
                    sentiment_score = sentiment_result[0]["score"]
                    
                    # Si le sentiment est très positif ou très négatif, vérifier s'il s'agit d'un appel à l'émotion
                    if sentiment_score > 0.8:
                        # Vérifier si ce n'est pas déjà identifié comme un appel à l'émotion
                        if not any(fallacy["fallacy_type"] == "Appel à l'émotion" and sentence in fallacy["context_text"] for fallacy in potential_fallacies):
                            potential_fallacies.append({
                                "fallacy_type": "Appel à l'émotion",
                                "keyword": "sentiment fort",
                                "context_text": sentence,
                                "confidence": sentiment_score * 0.8,  # Ajuster la confiance
                                "detection_method": "sentiment_analysis"
                            })
                    
                    # Extraire les entités nommées pour détecter les appels à l'autorité
                    ner_results = self.nlp_models["ner"](sentence)
                    person_entities = [entity for entity in ner_results if entity["entity"] in ["B-PER", "I-PER"]]
                    
                    if person_entities and ("expert" in sentence.lower() or "autorité" in sentence.lower() or "scientifique" in sentence.lower()):
                        # Vérifier si ce n'est pas déjà identifié comme un appel à l'autorité
                        if not any(fallacy["fallacy_type"] == "Appel à l'autorité" and sentence in fallacy["context_text"] for fallacy in potential_fallacies):
                            potential_fallacies.append({
                                "fallacy_type": "Appel à l'autorité",
                                "keyword": "référence à une autorité",
                                "context_text": sentence,
                                "confidence": 0.7,
                                "detection_method": "named_entity_recognition",
                                "entities": person_entities
                            })
                
                # Appliquer des ajustements de confiance basés sur l'apprentissage
                for fallacy in potential_fallacies:
                    fallacy_type = fallacy["fallacy_type"]
                    if fallacy_type in self.learning_data["confidence_adjustments"]:
                        adjustment = self.learning_data["confidence_adjustments"][fallacy_type]
                        fallacy["confidence"] = min(1.0, max(0.1, fallacy["confidence"] + adjustment))
                        fallacy["confidence_adjusted"] = True
            
            except Exception as e:
                self.logger.error(f"Erreur lors de l'identification des sophismes avec NLP: {e}")
        
        return potential_fallacies
        
    def _filter_by_context_semantic(
        self, 
        potential_fallacies: List[Dict[str, Any]], 
        context_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filtre les sophismes potentiels en fonction du contexte avec une analyse sémantique.
        
        Args:
            potential_fallacies: Liste des sophismes potentiels
            context_analysis: Analyse du contexte
            
        Returns:
            Liste des sophismes contextuels
        """
        context_type = context_analysis["context_type"]
        context_subtypes = context_analysis["context_subtypes"]
        audience = context_analysis["audience_characteristics"]
        formality = context_analysis["formality_level"]
        
        # Définir les sophismes particulièrement problématiques dans chaque contexte
        # avec une analyse plus nuancée
        context_fallacy_mapping = {
            "politique": {
                "Appel à l'émotion": 0.3,
                "Ad hominem": 0.3,
                "Homme de paille": 0.3,
                "Faux dilemme": 0.3,
                "Pente glissante": 0.2
            },
            "scientifique": {
                "Appel à la popularité": 0.4,
                "Appel à la tradition": 0.4,
                "Appel à l'autorité": 0.3,
                "Post hoc ergo propter hoc": 0.3,
                "Généralisation hâtive": 0.3
            },
            "commercial": {
                "Appel à la nouveauté": 0.3,
                "Appel à la popularité": 0.3,
                "Faux dilemme": 0.3,
                "Appel à l'émotion": 0.3,
                "Appel à la peur": 0.3
            },
            "juridique": {
                "Pente glissante": 0.4,
                "Ad hominem": 0.4,
                "Appel à l'émotion": 0.3,
                "Généralisation hâtive": 0.3,
                "Faux dilemme": 0.3
            },
            "académique": {
                "Appel à l'autorité": 0.4,
                "Homme de paille": 0.3,
                "Ad hominem": 0.3,
                "Argument circulaire": 0.4,
                "Appel à l'ignorance": 0.3
            },
            "général": {}  # Pas de filtre spécifique pour le contexte général
        }
        
        # Ajustements basés sur les sous-types de contexte
        subtype_adjustments = {
            "électoral": {
                "Appel à l'émotion": 0.1,
                "Appel à la peur": 0.1
            },
            "parlementaire": {
                "Ad hominem": 0.1,
                "Homme de paille": 0.1
            },
            "diplomatique": {
                "Faux dilemme": 0.1,
                "Pente glissante": 0.1
            }
        }
        
        # Ajustements basés sur l'audience
        audience_adjustments = {
            "généraliste": {
                "Appel à la popularité": 0.1,
                "Appel à l'émotion": 0.1
            },
            "expert": {
                "Appel à l'autorité": 0.1,
                "Argument circulaire": 0.1
            },
            "académique": {
                "Appel à l'autorité": 0.1,
                "Généralisation hâtive": 0.1
            }
        }
        
        # Ajustements basés sur le niveau de formalité
        formality_adjustments = {
            "élevé": {
                "Ad hominem": 0.1,
                "Appel à l'émotion": 0.1
            },
            "faible": {
                "Appel à la popularité": 0.1,
                "Appel à la tradition": 0.1
            }
        }
        
        # Si le contexte est général, retourner tous les sophismes potentiels
        if context_type == "général" or context_type not in context_fallacy_mapping:
            return potential_fallacies
        
        # Filtrer les sophismes en fonction du contexte avec une analyse sémantique
        contextual_fallacies = []
        
        for fallacy in potential_fallacies:
            fallacy_type = fallacy["fallacy_type"]
            base_confidence = fallacy.get("confidence", 0.5)
            
            # Calculer l'ajustement de confiance en fonction du contexte
            context_adjustment = 0.0
            
            # Ajustement basé sur le type de contexte principal
            if fallacy_type in context_fallacy_mapping[context_type]:
                context_adjustment += context_fallacy_mapping[context_type][fallacy_type]
                contextual_relevance = "Élevée"
            else:
                contextual_relevance = "Faible"
            
            # Ajustements supplémentaires basés sur les sous-types, l'audience et la formalité
            for subtype in context_subtypes:
                if subtype in subtype_adjustments and fallacy_type in subtype_adjustments[subtype]:
                    context_adjustment += subtype_adjustments[subtype][fallacy_type]
            
            for aud in audience:
                if aud in audience_adjustments and fallacy_type in audience_adjustments[aud]:
                    context_adjustment += audience_adjustments[aud][fallacy_type]
            
            if formality in formality_adjustments and fallacy_type in formality_adjustments[formality]:
                context_adjustment += formality_adjustments[formality][fallacy_type]
            
            # Calculer la confiance finale
            final_confidence = min(1.0, base_confidence + context_adjustment)
            
            # Ajouter le sophisme avec les informations contextuelles
            fallacy_copy = fallacy.copy()
            fallacy_copy["confidence"] = final_confidence
            fallacy_copy["contextual_relevance"] = contextual_relevance
            fallacy_copy["context_adjustment"] = context_adjustment
            fallacy_copy["context_analysis"] = {
                "type": context_type,
                "subtypes": context_subtypes,
                "audience": audience,
                "formality": formality
            }
            
            contextual_fallacies.append(fallacy_copy)
        
        # Trier les sophismes par confiance décroissante
        contextual_fallacies.sort(key=lambda x: x["confidence"], reverse=True)
        
        return contextual_fallacies
    
    def _analyze_fallacy_relations(self, fallacies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyse les relations entre les sophismes identifiés.
        
        Args:
            fallacies: Liste des sophismes identifiés
            
        Returns:
            Liste des relations entre sophismes
        """
        relations = []
        
        # Si moins de 2 sophismes, pas de relations à analyser
        if len(fallacies) < 2:
            return relations
        
        # Analyser les relations entre paires de sophismes
        for i in range(len(fallacies)):
            for j in range(i + 1, len(fallacies)):
                fallacy1 = fallacies[i]
                fallacy2 = fallacies[j]
                
                # Vérifier si les sophismes sont liés (même contexte textuel)
                if fallacy1["context_text"] == fallacy2["context_text"]:
                    relations.append({
                        "relation_type": "same_context",
                        "fallacy1_type": fallacy1["fallacy_type"],
                        "fallacy2_type": fallacy2["fallacy_type"],
                        "context_text": fallacy1["context_text"],
                        "strength": 0.9
                    })
                
                # Vérifier si les sophismes sont complémentaires
                elif self._are_complementary_fallacies(fallacy1["fallacy_type"], fallacy2["fallacy_type"]):
                    relations.append({
                        "relation_type": "complementary",
                        "fallacy1_type": fallacy1["fallacy_type"],
                        "fallacy2_type": fallacy2["fallacy_type"],
                        "explanation": f"Les sophismes '{fallacy1['fallacy_type']}' et '{fallacy2['fallacy_type']}' se renforcent mutuellement",
                        "strength": 0.7
                    })
        
        return relations
    
    def _are_complementary_fallacies(self, type1: str, type2: str) -> bool:
        """
        Détermine si deux types de sophismes sont complémentaires.
        
        Args:
            type1: Premier type de sophisme
            type2: Deuxième type de sophisme
            
        Returns:
            True si les sophismes sont complémentaires, False sinon
        """
        # Paires de sophismes complémentaires
        complementary_pairs = [
            {"Appel à l'autorité", "Appel à la popularité"},
            {"Faux dilemme", "Appel à l'émotion"},
            {"Pente glissante", "Appel à la peur"},
            {"Homme de paille", "Ad hominem"},
            {"Appel à la tradition", "Appel à l'autorité"}
        ]
        
        return {type1, type2} in complementary_pairs
    
    def identify_contextual_fallacies(self, argument: str, context: str) -> List[Dict[str, Any]]:
        """
        Identifie les sophismes contextuels dans un argument.
        
        Cette méthode améliorée utilise des modèles de langage avancés pour identifier
        des sophismes contextuels dans un argument.
        
        Args:
            argument: Argument à analyser
            context: Contexte de l'argument
            
        Returns:
            Liste des sophismes contextuels identifiés
        """
        self.logger.info(f"Identification améliorée des sophismes contextuels dans l'argument (longueur: {len(argument)}) dans le contexte: {context}")
        
        # Analyser le contexte
        results = self.analyze_context(argument, context)
        
        # Filtrer les sophismes avec une confiance élevée
        high_confidence_fallacies = [
            fallacy for fallacy in results["contextual_fallacies"]
            if fallacy["confidence"] >= 0.5
        ]
        
        self.logger.info(f"Sophismes contextuels identifiés avec confiance élevée: {len(high_confidence_fallacies)}")
        
        return high_confidence_fallacies
    
    def provide_feedback(self, fallacy_id: str, is_correct: bool, feedback_text: Optional[str] = None) -> None:
        """
        Fournit un feedback sur l'identification d'un sophisme pour l'apprentissage continu.
        
        Args:
            fallacy_id: Identifiant du sophisme
            is_correct: Indique si l'identification était correcte
            feedback_text: Texte de feedback optionnel
        """
        self.logger.info(f"Réception de feedback pour le sophisme {fallacy_id}: {'correct' if is_correct else 'incorrect'}")
        
        # Enregistrer le feedback
        feedback_entry = {
            "fallacy_id": fallacy_id,
            "is_correct": is_correct,
            "feedback_text": feedback_text,
            "timestamp": datetime.now().isoformat()
        }
        
        self.feedback_history.append(feedback_entry)
        self.learning_data["feedback_history"].append(feedback_entry)
        
        # Mettre à jour les ajustements de confiance
        if fallacy_id in self.last_analysis_fallacies:
            fallacy = self.last_analysis_fallacies[fallacy_id]
            fallacy_type = fallacy["fallacy_type"]
            
            if fallacy_type not in self.learning_data["confidence_adjustments"]:
                self.learning_data["confidence_adjustments"][fallacy_type] = 0.0
            
            # Ajuster la confiance en fonction du feedback
            if is_correct:
                # Si l'identification était correcte, augmenter légèrement la confiance
                self.learning_data["confidence_adjustments"][fallacy_type] += 0.05
            else:
                # Si l'identification était incorrecte, diminuer la confiance
                self.learning_data["confidence_adjustments"][fallacy_type] -= 0.1
            
            # Limiter l'ajustement
            self.learning_data["confidence_adjustments"][fallacy_type] = max(-0.5, min(0.5, self.learning_data["confidence_adjustments"][fallacy_type]))
            
            self.logger.info(f"Ajustement de confiance pour le type de sophisme '{fallacy_type}': {self.learning_data['confidence_adjustments'][fallacy_type]:.2f}")
        
        # Sauvegarder les données d'apprentissage
        self._save_learning_data()
    
    def get_contextual_fallacy_examples(self, fallacy_type: str, context_type: str) -> List[Dict[str, Any]]:
        """
        Retourne des exemples enrichis de sophismes contextuels.
        
        Cette méthode améliorée fournit des exemples plus riches et contextuels
        de sophismes, avec des explications détaillées et des suggestions de correction.
        
        Args:
            fallacy_type: Type de sophisme
            context_type: Type de contexte
            
        Returns:
            Liste d'exemples enrichis de sophismes contextuels
        """
        # Obtenir les exemples de base
        basic_examples = super().get_contextual_fallacy_examples(fallacy_type, context_type)
        
        # Enrichir les exemples avec des explications et des suggestions
        enriched_examples = []
        
        for example in basic_examples:
            if example == "Aucun exemple disponible pour ce type de sophisme dans ce contexte.":
                enriched_examples.append({
                    "text": "Aucun exemple disponible pour ce type de sophisme dans ce contexte.",
                    "explanation": None,
                    "correction_suggestion": None
                })
                continue
            
            # Générer une explication détaillée
            explanation = self._generate_fallacy_explanation(fallacy_type, context_type, example)
            
            # Générer une suggestion de correction
            correction = self._generate_correction_suggestion(fallacy_type, example)
            
            # Ajouter l'exemple enrichi
            enriched_examples.append({
                "text": example,
                "explanation": explanation,
                "correction_suggestion": correction,
                "context_type": context_type,
                "fallacy_type": fallacy_type
            })
        
        return enriched_examples
    
    def _generate_fallacy_explanation(self, fallacy_type: str, context_type: str, example: str) -> str:
        """
        Génère une explication détaillée d'un sophisme dans un contexte spécifique.
        
        Args:
            fallacy_type: Type de sophisme
            context_type: Type de contexte
            example: Exemple de sophisme
            
        Returns:
            Explication détaillée du sophisme
        """
        # Explications détaillées par type de sophisme et contexte
        explanations = {
            "Appel à l'autorité": {
                "politique": f"Dans cet exemple, l'argument fait appel à une autorité qui n'est pas pertinente dans le domaine politique. Le fait que '{example}' constitue un sophisme car l'expertise citée n'est pas dans le domaine concerné.",
                "scientifique": f"Dans un contexte scientifique, cet exemple constitue un sophisme car il s'appuie sur une autorité sans fournir de preuves empiriques. '{example}' devrait être soutenu par des données et des méthodes scientifiques rigoureuses.",
                "commercial": f"Dans un contexte commercial, '{example}' est un sophisme car il utilise l'autorité pour persuader plutôt que de présenter les mérites réels du produit ou service."
            },
            "Appel à la popularité": {
                "politique": f"Cet exemple, '{example}', est un sophisme dans un contexte politique car il suggère qu'une position est correcte simplement parce qu'elle est populaire, ignorant les questions de fond.",
                "scientifique": f"Dans un contexte scientifique, '{example}' constitue un sophisme car la vérité scientifique ne dépend pas de l'opinion populaire mais de preuves empiriques.",
                "commercial": f"Dans un contexte commercial, '{example}' est un sophisme car la popularité d'un produit n'est pas nécessairement un indicateur de sa qualité ou de son adéquation aux besoins spécifiques."
            }
        }
        
        # Si une explication spécifique existe, la retourner
        if fallacy_type in explanations and context_type in explanations[fallacy_type]:
            return explanations[fallacy_type][context_type]
        
        # Sinon, générer une explication générique
        return f"Cet exemple, '{example}', illustre un sophisme de type '{fallacy_type}' dans un contexte '{context_type}'. Ce type de raisonnement fallacieux peut être particulièrement problématique dans ce contexte car il peut induire en erreur et affecter la prise de décision."
    
    def _generate_correction_suggestion(self, fallacy_type: str, example: str) -> str:
        """
        Génère une suggestion de correction pour un sophisme.
        
        Args:
            fallacy_type: Type de sophisme
            example: Exemple de sophisme
            
        Returns:
            Suggestion de correction
        """
        # Suggestions de correction par type de sophisme
        correction_suggestions = {
            "Appel à l'autorité": f"Au lieu de dire '{example}', il serait préférable de présenter des preuves concrètes ou des données pertinentes qui soutiennent directement l'argument, ou de citer une autorité dont l'expertise est directement liée au sujet.",
            "Appel à la popularité": f"Au lieu de dire '{example}', il serait plus rigoureux de présenter les mérites intrinsèques de l'argument, indépendamment de sa popularité, ou d'expliquer pourquoi cette position est valide sur le fond.",
            "Faux dilemme": f"Au lieu de présenter seulement deux options comme dans '{example}', il serait plus honnête d'explorer le spectre complet des possibilités et de reconnaître la complexité de la situation.",
            "Ad hominem": f"Au lieu d'attaquer la personne comme dans '{example}', il serait plus constructif de se concentrer sur les arguments eux-mêmes et de les réfuter sur le fond.",
            "Pente glissante": f"Au lieu de suggérer une cascade d'événements improbables comme dans '{example}', il serait plus rigoureux d'examiner chaque étape du raisonnement et d'évaluer sa probabilité réelle."
        }
        
        # Si une suggestion spécifique existe, la retourner
        if fallacy_type in correction_suggestions:
            return correction_suggestions[fallacy_type]
        
        # Sinon, générer une suggestion générique
        return f"Pour corriger ce sophisme, il faudrait reformuler l'argument en évitant le raisonnement fallacieux et en se concentrant sur des preuves objectives et des raisonnements logiques valides."


# Test de la classe si exécutée directement
if __name__ == "__main__":
    analyzer = EnhancedContextualFallacyAnalyzer()
    
    # Exemple d'analyse contextuelle
    text = "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
    context = "Discours commercial pour un produit controversé"
    
    results = analyzer.analyze_context(text, context)
    print(f"Résultats de l'analyse contextuelle améliorée: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    # Exemple d'identification de sophismes contextuels
    fallacies = analyzer.identify_contextual_fallacies(text, context)
    print(f"Sophismes contextuels identifiés avec l'analyseur amélioré: {json.dumps(fallacies, indent=2, ensure_ascii=False)}")
    
    # Exemple d'obtention d'exemples enrichis
    examples = analyzer.get_contextual_fallacy_examples("Appel à l'autorité", "commercial")
    print(f"Exemples enrichis de sophismes: {json.dumps(examples, indent=2, ensure_ascii=False)}")