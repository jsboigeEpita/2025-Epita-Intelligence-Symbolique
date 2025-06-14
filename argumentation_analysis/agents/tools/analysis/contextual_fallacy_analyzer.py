#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil d'analyse contextuelle des sophismes.

Ce module fournit des fonctionnalités pour analyser les sophismes dans leur contexte,
en tenant compte des facteurs contextuels qui peuvent influencer l'interprétation
et la gravité des sophismes.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
# current_dir = Path(__file__).parent # Commenté car start_api.py devrait gérer sys.path
# parent_dir = current_dir.parent.parent.parent
# if str(parent_dir) not in sys.path:
#     sys.path.append(str(parent_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ContextualFallacyAnalyzer")


class ContextualFallacyAnalyzer:
    """
    Outil pour l'analyse contextuelle des sophismes.
    
    Cet outil permet d'analyser les sophismes dans leur contexte, en tenant compte
    des facteurs contextuels qui peuvent influencer l'interprétation et la gravité
    des sophismes.
    """
    
    def __init__(self, taxonomy_path: Optional[str] = None):
        """
        Initialise l'analyseur contextuel de sophismes.
        
        Args:
            taxonomy_path: Chemin vers le fichier de taxonomie des sophismes (optionnel)
        """
        self.logger = logger
        self.taxonomy_df = self._load_taxonomy(taxonomy_path)
        self.logger.info("Analyseur contextuel de sophismes initialisé.")
    
    def _load_taxonomy(self, taxonomy_path: Optional[str] = None) -> Any:
        """
        Charge la taxonomie des sophismes.
        
        Args:
            taxonomy_path: Chemin vers le fichier de taxonomie des sophismes (optionnel)
            
        Returns:
            DataFrame contenant la taxonomie des sophismes
        """
        try:
            # Utiliser l'utilitaire de lazy loading pour obtenir le chemin du fichier
            from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path, validate_taxonomy_file
            
            path = taxonomy_path or get_taxonomy_path()
            self.logger.info(f"Chargement de la taxonomie depuis {path}")
            
            # Vérifier que le fichier est valide
            if not validate_taxonomy_file():
                self.logger.error("Le fichier de taxonomie n'est pas valide")
                return None
            
            # Charger le fichier CSV
            import pandas as pd
            df = pd.read_csv(self.taxonomy_path, encoding='utf-8')
            self.logger.info(f"Taxonomie chargée avec succès: {len(df)} sophismes.")
            return df
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la taxonomie: {e}")
            return None
    
    def analyze_context(self, text: str, context: str) -> Dict[str, Any]:
        """
        Analyse le contexte d'un texte pour identifier des sophismes contextuels.
        
        Cette méthode analyse un texte dans son contexte pour identifier des sophismes
        qui dépendent du contexte, comme les appels à l'autorité dans un contexte
        où l'autorité n'est pas pertinente, ou les appels à la tradition dans un
        contexte où la tradition n'est pas un argument valide.
        
        Args:
            text: Texte à analyser
            context: Contexte du texte (ex: type de discours, audience, etc.)
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        self.logger.info(f"Analyse contextuelle du texte (longueur: {len(text)}) dans le contexte: {context}")
        
        # Analyser le type de contexte
        context_type = self._determine_context_type(context)
        self.logger.info(f"Type de contexte déterminé: {context_type}")
        
        # Identifier les sophismes potentiels
        potential_fallacies = self._identify_potential_fallacies(text)
        self.logger.info(f"Sophismes potentiels identifiés: {len(potential_fallacies)}")
        
        # Filtrer les sophismes en fonction du contexte
        contextual_fallacies = self._filter_by_context(potential_fallacies, context_type)
        self.logger.info(f"Sophismes contextuels identifiés: {len(contextual_fallacies)}")
        
        # Préparer les résultats
        results = {
            "context_type": context_type,
            "potential_fallacies_count": len(potential_fallacies),
            "contextual_fallacies_count": len(contextual_fallacies),
            "contextual_fallacies": contextual_fallacies
        }
        
        return results
    
    def _determine_context_type(self, context: str) -> str:
        """
        Détermine le type de contexte à partir de la description du contexte.
        
        Args:
            context: Description du contexte
            
        Returns:
            Type de contexte (ex: politique, scientifique, etc.)
        """
        context_lower = context.lower()
        
        # Déterminer le type de contexte en fonction de mots-clés
        if any(keyword in context_lower for keyword in ["politique", "élection", "gouvernement", "président"]):
            return "politique"
        elif any(keyword in context_lower for keyword in ["scientifique", "recherche", "étude", "expérience"]):
            return "scientifique"
        elif any(keyword in context_lower for keyword in ["commercial", "publicité", "marketing", "produit"]):
            return "commercial"
        elif any(keyword in context_lower for keyword in ["juridique", "légal", "tribunal", "procès"]):
            return "juridique"
        elif any(keyword in context_lower for keyword in ["académique", "universitaire", "éducation"]):
            return "académique"
        else:
            return "général"
    
    def _identify_potential_fallacies(self, text: str) -> List[Dict[str, Any]]:
        """
        Identifie les sophismes potentiels dans un texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des sophismes potentiels identifiés
        """
        # Cette méthode pourrait utiliser des techniques de NLP ou des règles heuristiques
        # pour identifier des sophismes potentiels. Pour l'instant, nous utilisons une
        # approche simplifiée basée sur des mots-clés.
        
        potential_fallacies = []
        
        # Recherche de mots-clés associés à des sophismes courants
        fallacy_keywords = {
            "Appel à l'autorité": ["expert", "autorité", "scientifique", "étude", "recherche", "unanime"],
            "Appel à la popularité": ["tout le monde", "majorité", "populaire", "commun", "consensus"],
            "Appel à la tradition": ["tradition", "toujours", "depuis longtemps", "historiquement", "ancestral"],
            "Appel à la nouveauté": ["nouveau", "moderne", "récent", "innovation", "dernière"],
            "Appel à l'émotion": ["peur", "crainte", "inquiétude", "espoir", "rêve", "cauchemar"],
            "Faux dilemme": ["soit", "ou bien", "alternative", "choix", "uniquement"],
            "Pente glissante": ["mènera à", "conduira à", "finira par", "inévitablement"],
            "Homme de paille": ["prétendre", "caricature", "déformer", "exagérer"],
            "Ad hominem": ["personne", "caractère", "intégrité", "moralité", "crédibilité"]
        }
        
        text_lower = text.lower()
        
        for fallacy_type, keywords in fallacy_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Trouver le contexte autour du mot-clé
                    keyword_index = text_lower.find(keyword.lower())
                    start_index = max(0, keyword_index - 50)
                    end_index = min(len(text), keyword_index + len(keyword) + 50)
                    context_text = text[start_index:end_index]
                    
                    potential_fallacies.append({
                        "fallacy_type": fallacy_type,
                        "keyword": keyword,
                        "context_text": context_text,
                        "confidence": 0.5  # Confiance par défaut
                    })
        
        return potential_fallacies
    
    def _filter_by_context(self, potential_fallacies: List[Dict[str, Any]], context_type: str) -> List[Dict[str, Any]]:
        """
        Filtre les sophismes potentiels en fonction du contexte.
        
        Args:
            potential_fallacies: Liste des sophismes potentiels
            context_type: Type de contexte
            
        Returns:
            Liste des sophismes contextuels
        """
        # Définir les sophismes particulièrement problématiques dans chaque contexte
        context_fallacy_mapping = {
            "politique": ["Appel à l'émotion", "Ad hominem", "Homme de paille", "Faux dilemme"],
            "scientifique": ["Appel à la popularité", "Appel à la tradition", "Appel à l'autorité"],
            "commercial": ["Appel à la nouveauté", "Appel à la popularité", "Faux dilemme"],
            "juridique": ["Pente glissante", "Ad hominem", "Appel à l'émotion"],
            "académique": ["Appel à l'autorité", "Homme de paille", "Ad hominem"],
            "général": []  # Pas de filtre spécifique pour le contexte général
        }
        
        # Si le contexte est général, retourner tous les sophismes potentiels sans modification de confiance
        if context_type == "général" or context_type not in context_fallacy_mapping:
            contextual_fallacies = []
            for fallacy in potential_fallacies:
                fallacy_copy = fallacy.copy()
                fallacy_copy["contextual_relevance"] = "Générale"
                contextual_fallacies.append(fallacy_copy)
            return contextual_fallacies
        
        # Filtrer les sophismes en fonction du contexte
        contextual_fallacies = []
        for fallacy in potential_fallacies:
            # Créer une copie pour éviter de modifier l'original
            fallacy_copy = fallacy.copy()
            if fallacy_copy["fallacy_type"] in context_fallacy_mapping[context_type]:
                # Ajuster la confiance en fonction du contexte
                fallacy_copy["confidence"] = 0.8  # Confiance plus élevée pour les sophismes contextuels
                fallacy_copy["contextual_relevance"] = "Élevée"
                contextual_fallacies.append(fallacy_copy)
            else:
                # Inclure les autres sophismes avec une confiance plus faible
                fallacy_copy["confidence"] = 0.3
                fallacy_copy["contextual_relevance"] = "Faible"
                contextual_fallacies.append(fallacy_copy)
        
        return contextual_fallacies
    
    def identify_contextual_fallacies(self, argument: str, context: str) -> List[Dict[str, Any]]:
        """
        Identifie les sophismes contextuels dans un argument.
        
        Cette méthode est une version simplifiée de analyze_context qui se concentre
        uniquement sur l'identification des sophismes contextuels dans un argument.
        
        Args:
            argument: Argument à analyser
            context: Contexte de l'argument
            
        Returns:
            Liste des sophismes contextuels identifiés
        """
        self.logger.info(f"Identification des sophismes contextuels dans l'argument (longueur: {len(argument)}) dans le contexte: {context}")
        
        # Analyser le contexte
        results = self.analyze_context(argument, context)
        
        # Filtrer les sophismes avec une confiance élevée
        high_confidence_fallacies = [
            fallacy for fallacy in results["contextual_fallacies"]
            if fallacy["confidence"] >= 0.5
        ]
        
        self.logger.info(f"Sophismes contextuels identifiés avec confiance élevée: {len(high_confidence_fallacies)}")
        
        return high_confidence_fallacies
    
    def get_contextual_fallacy_examples(self, fallacy_type: str, context_type: str) -> List[str]:
        """
        Retourne des exemples de sophismes contextuels.
        
        Args:
            fallacy_type: Type de sophisme
            context_type: Type de contexte
            
        Returns:
            Liste d'exemples de sophismes contextuels
        """
        # Exemples de sophismes contextuels
        examples = {
            "Appel à l'autorité": {
                "politique": [
                    "Le Dr. Smith, éminent cardiologue, soutient ma politique fiscale.",
                    "Comme l'a dit Einstein, nous devons augmenter les impôts."
                ],
                "scientifique": [
                    "Le Dr. Jones, célèbre économiste, affirme que cette théorie physique est correcte.",
                    "Cette étude a été publiée dans une revue prestigieuse, donc elle doit être vraie."
                ],
                "commercial": [
                    "9 dentistes sur 10 recommandent ce dentifrice.",
                    "Des experts en nutrition ont conçu ce régime miracle."
                ]
            },
            "Appel à la popularité": {
                "politique": [
                    "80% des Français soutiennent cette mesure, elle doit donc être bonne.",
                    "Tout le monde sait que cette politique est la meilleure."
                ],
                "scientifique": [
                    "La majorité des gens ne croient pas au changement climatique.",
                    "Cette théorie est largement acceptée, elle doit donc être vraie."
                ],
                "commercial": [
                    "C'est le smartphone le plus vendu, il doit donc être le meilleur.",
                    "Des millions de personnes utilisent ce produit, vous devriez l'essayer aussi."
                ]
            }
        }
        
        # Retourner les exemples pour le type de sophisme et le contexte spécifiés
        if fallacy_type in examples and context_type in examples[fallacy_type]:
            return examples[fallacy_type][context_type]
        else:
            return ["Aucun exemple disponible pour ce type de sophisme dans ce contexte."]


# Test de la classe si exécutée directement
if __name__ == "__main__":
    analyzer = ContextualFallacyAnalyzer()
    
    # Exemple d'analyse contextuelle
    text = "Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà."
    context = "Discours commercial pour un produit controversé"
    
    results = analyzer.analyze_context(text, context)
    print(f"Résultats de l'analyse contextuelle: {json.dumps(results, indent=2, ensure_ascii=False)}")
    
    # Exemple d'identification de sophismes contextuels
    fallacies = analyzer.identify_contextual_fallacies(text, context)
    print(f"Sophismes contextuels identifiés: {json.dumps(fallacies, indent=2, ensure_ascii=False)}")