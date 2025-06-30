# -*- coding: utf-8 -*-
"""
Extracteur d'affirmations factuelles pour l'intégration du fact-checking.

Ce module implémente l'extraction automatique d'affirmations vérifiables
dans un texte pour alimenter le système de fact-checking.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import spacy
from datetime import datetime

logger = logging.getLogger(__name__)


class ClaimType(Enum):
    """Types d'affirmations factuelles."""
    
    STATISTICAL = "statistical"
    HISTORICAL = "historical"
    SCIENTIFIC = "scientific"
    GEOGRAPHICAL = "geographical"
    BIOGRAPHICAL = "biographical"
    NUMERICAL = "numerical"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    DEFINITIONAL = "definitional"
    QUOTE = "quote"


class ClaimVerifiability(Enum):
    """Niveaux de vérifiabilité des affirmations."""
    
    HIGHLY_VERIFIABLE = "highly_verifiable"
    MODERATELY_VERIFIABLE = "moderately_verifiable"
    PARTIALLY_VERIFIABLE = "partially_verifiable"
    SUBJECTIVE = "subjective"
    OPINION = "opinion"


@dataclass
class FactualClaim:
    """Représentation d'une affirmation factuelle extraite."""
    
    claim_text: str
    claim_type: ClaimType
    verifiability: ClaimVerifiability
    confidence: float
    context: str
    start_pos: int
    end_pos: int
    entities: List[Dict[str, Any]]
    keywords: List[str]
    temporal_references: List[str]
    numerical_values: List[Dict[str, Any]]
    sources_mentioned: List[str]
    extraction_method: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'affirmation en dictionnaire."""
        return {
            "claim_text": self.claim_text,
            "claim_type": self.claim_type.value,
            "verifiability": self.verifiability.value,
            "confidence": self.confidence,
            "context": self.context,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "entities": self.entities,
            "keywords": self.keywords,
            "temporal_references": self.temporal_references,
            "numerical_values": self.numerical_values,
            "sources_mentioned": self.sources_mentioned,
            "extraction_method": self.extraction_method
        }


class FactClaimExtractor:
    """
    Extracteur d'affirmations factuelles pour le fact-checking.
    
    Cette classe identifie et extrait les affirmations vérifiables
    dans un texte selon différents critères et patterns.
    """
    
    def __init__(self, language: str = "fr"):
        """
        Initialise l'extracteur d'affirmations factuelles.
        
        :param language: Langue du texte à analyser
        """
        self.logger = logging.getLogger("FactClaimExtractor")
        self.language = language
        
        # Tentative de chargement du modèle spaCy
        try:
            if language == "fr":
                self.nlp = spacy.load("fr_core_news_sm")
            else:
                self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.logger.warning(f"Modèle spaCy {language} non trouvé, utilisation du modèle de base")
            self.nlp = None
        
        # Patterns de détection d'affirmations
        self._initialize_patterns()
        
        self.logger.info(f"FactClaimExtractor initialisé pour la langue: {language}")
    
    def _initialize_patterns(self):
        """Initialise les patterns de détection d'affirmations."""
        
        # Patterns pour différents types d'affirmations
        self.claim_patterns = {
            ClaimType.STATISTICAL: [
                r'\b\d+(?:\.\d+)?%\s+(?:des?|de\s+(?:la|les))\s+\w+',
                r'\b(?:une|la)\s+(?:majorité|minorité)\s+(?:des?|de)',
                r'\b\d+\s+(?:fois\s+)?(?:plus|moins)\s+(?:que|de)',
                r'\bstatistiquement\s+(?:parlant|significatif)',
                r'\ben\s+moyenne\s+\d+',
                r'\b(?:taux|niveau)\s+de\s+\d+(?:\.\d+)?%'
            ],
            
            ClaimType.HISTORICAL: [
                r'\ben\s+\d{4}\b',
                r'\bau\s+(?:XVIe?|XVIIIe?|XIXe?|XXe?|XXIe?)\s+siècle',
                r'\b(?:pendant|durant|lors\s+de)\s+(?:la|le|les)\s+\w+',
                r'\b(?:avant|après)\s+(?:J\.?-?C\.?|\d{4})',
                r'\bhistoriquement\s+(?:parlant|connu)',
                r'\bil\s+y\s+a\s+\d+\s+(?:ans?|siècles?)'
            ],
            
            ClaimType.SCIENTIFIC: [
                r'\b(?:une|des?)\s+(?:étude|recherche)s?\s+(?:montre|prouve|démontre)',
                r'\bselon\s+(?:une|des?)\s+(?:étude|recherche)s?',
                r'\bscientifiquement\s+(?:prouvé|établi|démontré)',
                r'\b(?:des?|les)\s+(?:scientifiques?|chercheurs?)\s+(?:ont|affirment)',
                r'\bpublié\s+dans\s+(?:une|la)\s+revue',
                r'\b(?:expérience|expérimentation)\s+(?:montre|prouve)'
            ],
            
            ClaimType.GEOGRAPHICAL: [
                r'\b(?:à|dans|en)\s+[A-Z][a-zA-ZÀ-ÿ]+(?:\s+[A-Z][a-zA-ZÀ-ÿ]+)*',
                r'\b(?:pays|ville|région|continent)\s+(?:des?|de)',
                r'\bsitué\s+(?:à|en|dans)',
                r'\b\d+\s+(?:km|kilomètres?|mètres?)\s+(?:de|du)',
                r'\b(?:nord|sud|est|ouest)\s+(?:de|du)',
                r'\bcapitale\s+(?:de|du)'
            ],
            
            ClaimType.NUMERICAL: [
                r'\b\d+(?:\s+\d{3})*(?:\.\d+)?\s+(?:millions?|milliards?|milliers?)',
                r'\b\d+(?:\.\d+)?\s+(?:euros?|dollars?|€|\$)',
                r'\b\d+\s+(?:personnes?|habitants?|individus?)',
                r'\b(?:coûte|vaut|représente)\s+\d+',
                r'\b\d+\s+(?:fois|multiplié\s+par)',
                r'\bplus\s+de\s+\d+'
            ],
            
            ClaimType.TEMPORAL: [
                r"\b(?:hier|aujourd'hui|demain|maintenant)",
                r'\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)',
                r'\ben\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)',
                r'\bce\s+(?:matin|soir|week-end|mois|année)',
                r'\bdepuis\s+\d+\s+(?:jours?|mois|années?)',
                r'\bdans\s+\d+\s+(?:jours?|mois|années?)'
            ],
            
            ClaimType.CAUSAL: [
                r'\b(?:cause|provoque|entraîne|résulte)\s+(?:de|en)',
                r'\bà\s+cause\s+de',
                r'\bgrâce\s+à',
                r'\bpar\s+conséquent',
                r'\bdonc\s+(?:nous|on|il)',
                r'\bcela\s+(?:implique|signifie|veut\s+dire)'
            ],
            
            ClaimType.QUOTE: [
                r'\"[^\"]{20,}\"',
                r'«[^»]{20,}»',
                r'\ba\s+(?:dit|déclaré|affirmé|soutenu)',
                r'\bselon\s+[A-Z][a-zA-ZÀ-ÿ]+',
                r"d'après\s+[A-Z][a-zA-ZÀ-ÿ]+",
                r"comme l'a dit",
            ]
        }
        
        # Mots-clés d'opinion vs. fait
        self.opinion_keywords = {
            "je pense", "je crois", "à mon avis", "il me semble",
            "probablement", "peut-être", "possiblement", "sans doute",
            "j'ai l'impression", "il est possible", "on dirait"
        }
        
        self.fact_keywords = {
            "il est prouvé", "il est établi", "c'est un fait",
            "la réalité est", "concrètement", "objectivement",
            "de manière factuelle", "les données montrent"
        }
        
        # Indicateurs de sources
        self.source_indicators = [
            r'\bselon\s+(?:le|la|les)\s+\w+',
            r"d'après\s+(?:le|la|les)\s+\w+",
            r'\bcomme\s+(?:le|la)\s+(?:dit|rapporte|précise)',
            r'\b(?:une|la)\s+(?:étude|enquête|recherche)\s+(?:de|du)',
            r'\b(?:le|la)\s+(?:journal|magazine|site)\s+\w+',
            r"\b(?:l'|le|la)\s+(?:organisation|institut|agence)\s+\w+"
        ]
    
    def extract_factual_claims(self, text: str, max_claims: int = 20) -> List[FactualClaim]:
        """
        Extrait les affirmations factuelles d'un texte.
        
        :param text: Texte à analyser
        :param max_claims: Nombre maximum d'affirmations à extraire
        :return: Liste des affirmations factuelles extraites
        """
        try:
            self.logger.info(f"Extraction d'affirmations factuelles dans un texte de {len(text)} caractères")
            
            claims = []
            
            # 1. Segmentation en phrases
            sentences = self._segment_sentences(text)
            
            # 2. Extraction par patterns
            for sentence_data in sentences:
                sentence = sentence_data['text']
                start_pos = sentence_data['start']
                
                # Analyser chaque type d'affirmation
                for claim_type, patterns in self.claim_patterns.items():
                    sentence_claims = self._extract_claims_by_pattern(
                        sentence, claim_type, patterns, start_pos
                    )
                    claims.extend(sentence_claims)
            
            # 3. Traitement NLP si disponible
            if self.nlp:
                nlp_claims = self._extract_claims_with_nlp(text)
                claims.extend(nlp_claims)
            
            # 4. Déduplication et classement
            claims = self._deduplicate_claims(claims)
            claims = self._rank_claims(claims)
            
            # 5. Limitation du nombre de résultats
            claims = claims[:max_claims]
            
            self.logger.info(f"Extraction terminée: {len(claims)} affirmations factuelles trouvées")
            return claims
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction d'affirmations: {e}")
            return []
    
    def _segment_sentences(self, text: str) -> List[Dict[str, Any]]:
        """Segmente le texte en phrases avec positions."""
        
        # Pattern simple de segmentation
        sentence_pattern = r'[.!?]+\s+'
        sentences = []
        
        current_pos = 0
        parts = re.split(sentence_pattern, text)
        
        for i, part in enumerate(parts):
            if part.strip():
                start = current_pos
                end = start + len(part)
                
                sentences.append({
                    'text': part.strip(),
                    'start': start,
                    'end': end,
                    'index': i
                })
                
                current_pos = end + 1  # +1 pour le séparateur
        
        return sentences
    
    def _extract_claims_by_pattern(self, sentence: str, claim_type: ClaimType, 
                                 patterns: List[str], start_pos: int) -> List[FactualClaim]:
        """Extrait les affirmations d'une phrase basée sur les patterns."""
        
        claims = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, sentence, re.IGNORECASE)
            
            for match in matches:
                claim_text = match.group()
                
                # Étendre le contexte
                context_start = max(0, match.start() - 50)
                context_end = min(len(sentence), match.end() + 50)
                context = sentence[context_start:context_end]
                
                # Calculer la vérifiabilité
                verifiability = self._assess_verifiability(sentence, claim_text)
                
                # Calculer la confiance
                confidence = self._calculate_confidence(sentence, claim_type, match)
                
                # Extraire les entités et métadonnées
                entities = self._extract_entities(context)
                keywords = self._extract_keywords(context, claim_type)
                temporal_refs = self._extract_temporal_references(context)
                numerical_values = self._extract_numerical_values(context)
                sources = self._extract_source_mentions(context)
                
                claim = FactualClaim(
                    claim_text=claim_text,
                    claim_type=claim_type,
                    verifiability=verifiability,
                    confidence=confidence,
                    context=context,
                    start_pos=start_pos + match.start(),
                    end_pos=start_pos + match.end(),
                    entities=entities,
                    keywords=keywords,
                    temporal_references=temporal_refs,
                    numerical_values=numerical_values,
                    sources_mentioned=sources,
                    extraction_method="pattern_based"
                )
                
                claims.append(claim)
        
        return claims
    
    def _extract_claims_with_nlp(self, text: str) -> List[FactualClaim]:
        """Extrait les affirmations avec analyse NLP."""
        
        if not self.nlp:
            return []
        
        claims = []
        
        try:
            doc = self.nlp(text)
            
            # Analyser les entités nommées
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "MONEY", "PERCENT"]:
                    # Créer une affirmation basée sur l'entité
                    claim_type = self._map_entity_to_claim_type(ent.label_)
                    
                    if claim_type:
                        # Étendre le contexte autour de l'entité
                        sent = ent.sent
                        
                        claim = FactualClaim(
                            claim_text=ent.text,
                            claim_type=claim_type,
                            verifiability=ClaimVerifiability.MODERATELY_VERIFIABLE,
                            confidence=0.6,
                            context=sent.text,
                            start_pos=ent.start_char,
                            end_pos=ent.end_char,
                            entities=[{"text": ent.text, "label": ent.label_}],
                            keywords=[],
                            temporal_references=[],
                            numerical_values=[],
                            sources_mentioned=[],
                            extraction_method="nlp_entities"
                        )
                        
                        claims.append(claim)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse NLP: {e}")
        
        return claims
    
    def _assess_verifiability(self, sentence: str, claim: str) -> ClaimVerifiability:
        """Évalue la vérifiabilité d'une affirmation."""
        
        sentence_lower = sentence.lower()
        
        # Vérifier les indicateurs d'opinion
        opinion_score = sum(1 for keyword in self.opinion_keywords 
                          if keyword in sentence_lower)
        
        # Vérifier les indicateurs de fait
        fact_score = sum(1 for keyword in self.fact_keywords 
                        if keyword in sentence_lower)
        
        # Vérifier la présence de sources
        source_score = sum(1 for pattern in self.source_indicators 
                           if re.search(pattern, sentence_lower))
        
        # Vérifier la présence de données quantifiables
        numerical_score = len(re.findall(r'\d+(?:\.\d+)?', claim))
        
        # Calculer le score de vérifiabilité
        total_score = fact_score + source_score + numerical_score - opinion_score
        
        if total_score >= 3:
            return ClaimVerifiability.HIGHLY_VERIFIABLE
        elif total_score >= 1:
            return ClaimVerifiability.MODERATELY_VERIFIABLE
        elif total_score >= 0:
            return ClaimVerifiability.PARTIALLY_VERIFIABLE
        elif opinion_score > 0:
            return ClaimVerifiability.OPINION
        else:
            return ClaimVerifiability.SUBJECTIVE
    
    def _calculate_confidence(self, sentence: str, claim_type: ClaimType, match) -> float:
        """Calcule la confiance dans l'extraction."""
        
        base_confidence = 0.5
        
        # Bonus basé sur le type d'affirmation
        type_bonuses = {
            ClaimType.STATISTICAL: 0.3,
            ClaimType.NUMERICAL: 0.3,
            ClaimType.HISTORICAL: 0.2,
            ClaimType.SCIENTIFIC: 0.2,
            ClaimType.GEOGRAPHICAL: 0.1,
            ClaimType.QUOTE: 0.2,
            ClaimType.TEMPORAL: 0.1,
            ClaimType.CAUSAL: 0.1,
            ClaimType.BIOGRAPHICAL: 0.1,
            ClaimType.DEFINITIONAL: 0.1
        }
        
        confidence = base_confidence + type_bonuses.get(claim_type, 0.0)
        
        # Bonus pour la longueur du match
        if len(match.group()) > 20:
            confidence += 0.1
        
        # Bonus pour la présence de nombres
        if re.search(r'\d+', match.group()):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extrait les entités du texte."""
        
        entities = []
        
        if self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char
                    })
            except Exception as e:
                self.logger.debug(f"Erreur extraction entités: {e}")
        
        return entities
    
    def _extract_keywords(self, text: str, claim_type: ClaimType) -> List[str]:
        """Extrait les mots-clés pertinents."""
        
        # Mots-clés spécifiques par type
        type_keywords = {
            ClaimType.STATISTICAL: ["statistique", "pourcentage", "données", "taux"],
            ClaimType.SCIENTIFIC: ["étude", "recherche", "scientifique", "expérience"],
            ClaimType.HISTORICAL: ["histoire", "historique", "siècle", "époque"],
            ClaimType.GEOGRAPHICAL: ["lieu", "géographie", "région", "pays"],
            ClaimType.NUMERICAL: ["nombre", "chiffre", "quantité", "total"]
        }
        
        keywords = []
        text_lower = text.lower()
        
        for keyword in type_keywords.get(claim_type, []):
            if keyword in text_lower:
                keywords.append(keyword)
        
        return keywords
    
    def _extract_temporal_references(self, text: str) -> List[str]:
        """Extrait les références temporelles."""
        
        temporal_patterns = [
            r'\b\d{4}\b',  # Années
            r'\b(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b',
            r'\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b',
            r"\b(?:hier|aujourd'hui|demain)\b"
        ]
        
        temporal_refs = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            temporal_refs.extend(matches)
        
        return list(set(temporal_refs))  # Dédupliquer
    
    def _extract_numerical_values(self, text: str) -> List[Dict[str, Any]]:
        """Extrait les valeurs numériques."""
        
        numerical_values = []
        
        # Pattern pour les nombres avec unités
        number_pattern = r'\b(\d+(?:\.\d+)?)\s*([a-zA-ZÀ-ÿ%€$]+)?\b'
        matches = re.finditer(number_pattern, text)
        
        for match in matches:
            value = match.group(1)
            unit = match.group(2) if match.group(2) else ""
            
            numerical_values.append({
                "value": float(value),
                "unit": unit,
                "text": match.group(),
                "start": match.start(),
                "end": match.end()
            })
        
        return numerical_values
    
    def _extract_source_mentions(self, text: str) -> List[str]:
        """Extrait les mentions de sources."""
        
        sources = []
        
        for pattern in self.source_indicators:
            matches = re.findall(pattern, text, re.IGNORECASE)
            sources.extend(matches)
        
        return list(set(sources))  # Dédupliquer
    
    def _map_entity_to_claim_type(self, entity_label: str) -> Optional[ClaimType]:
        """Mappe un label d'entité NLP vers un type d'affirmation."""
        
        mapping = {
            "PERSON": ClaimType.BIOGRAPHICAL,
            "ORG": ClaimType.DEFINITIONAL,
            "GPE": ClaimType.GEOGRAPHICAL,
            "DATE": ClaimType.TEMPORAL,
            "MONEY": ClaimType.NUMERICAL,
            "PERCENT": ClaimType.STATISTICAL
        }
        
        return mapping.get(entity_label)
    
    def _deduplicate_claims(self, claims: List[FactualClaim]) -> List[FactualClaim]:
        """Déduplique les affirmations similaires."""
        
        unique_claims = []
        seen_texts = set()
        
        for claim in claims:
            # Normaliser le texte pour la comparaison
            normalized_text = claim.claim_text.lower().strip()
            
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_claims.append(claim)
        
        return unique_claims
    
    def _rank_claims(self, claims: List[FactualClaim]) -> List[FactualClaim]:
        """Classe les affirmations par pertinence."""
        
        def claim_score(claim: FactualClaim) -> float:
            score = claim.confidence
            
            # Bonus pour la vérifiabilité élevée
            if claim.verifiability == ClaimVerifiability.HIGHLY_VERIFIABLE:
                score += 0.3
            elif claim.verifiability == ClaimVerifiability.MODERATELY_VERIFIABLE:
                score += 0.2
            
            # Bonus pour la présence d'entités
            score += len(claim.entities) * 0.05
            
            # Bonus pour les valeurs numériques
            score += len(claim.numerical_values) * 0.1
            
            # Bonus pour les sources mentionnées
            score += len(claim.sources_mentioned) * 0.15
            
            return score
        
        return sorted(claims, key=claim_score, reverse=True)