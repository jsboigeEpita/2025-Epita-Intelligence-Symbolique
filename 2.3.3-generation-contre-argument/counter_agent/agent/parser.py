"""
Parseurs pour l'analyse d'arguments.

Ce module fournit des fonctions pour analyser et parser la structure des arguments.
"""

import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

from .definitions import Argument, Vulnerability, CounterArgumentType

logger = logging.getLogger(__name__)


class ArgumentParser:
    """Classe pour parser et analyser des arguments."""

    def __init__(self):
        """Initialise le parseur d'arguments."""
        self.premise_markers = [
            "parce que",
            "car",
            "puisque",
            "étant donné que",
            "en raison de",
            "du fait que",
            "comme",
            "considérant que",
        ]
        self.conclusion_markers = [
            "donc",
            "par conséquent",
            "ainsi",
            "en conclusion",
            "il s'ensuit que",
            "on peut conclure que",
            "cela montre que",
            "il en résulte que",
        ]
        self.argument_types = {
            "deductive": ["tous", "chaque", "toujours", "nécessairement"],
            "inductive": ["généralement", "habituellement", "souvent", "la plupart"],
            "abductive": ["meilleure explication", "probablement", "vraisemblablement"],
        }

        # Initialiser l'analyseur de vulnérabilités
        self.vulnerability_analyzer = VulnerabilityAnalyzer()

        logger.debug("ArgumentParser initialisé")

    def parse_argument(self, text: str) -> Argument:
        """
        Parse un texte pour extraire la structure d'un argument.

        Args:
            text: Le texte de l'argument à parser

        Returns:
            Un objet Argument contenant la structure de l'argument
        """
        logger.info(f"Parsing d'un argument: {text[:100]}...")

        # Extraire les prémisses
        premises = self._extract_premises(text)

        # Extraire la conclusion
        conclusion = self._extract_conclusion(text)

        # Vérifier que la prémisse et la conclusion ne sont pas identiques
        premises, conclusion = self._fix_identical_premise_conclusion(
            premises, conclusion, text
        )

        # Déterminer le type d'argument
        argument_type = self._determine_argument_type(text)

        # Calculer un score de confiance
        confidence = self._calculate_confidence(premises, conclusion)

        logger.debug(
            f"Argument parsé: {len(premises)} prémisses, type={argument_type}, confiance={confidence:.2f}"
        )

        return Argument(
            content=text,
            premises=premises,
            conclusion=conclusion,
            argument_type=argument_type,
            confidence=confidence,
        )

    def identify_vulnerabilities(self, argument: Argument) -> List[Vulnerability]:
        """
        Identifie les vulnérabilités dans un argument.

        Args:
            argument: L'argument à analyser

        Returns:
            Une liste de vulnérabilités identifiées
        """
        logger.info(
            f"Identification des vulnérabilités pour l'argument: {argument.content[:100]}..."
        )

        # Utiliser l'analyseur de vulnérabilités
        vulnerabilities = self.vulnerability_analyzer.analyze_vulnerabilities(argument)

        # Trier les vulnérabilités par score décroissant
        vulnerabilities.sort(key=lambda v: v.score, reverse=True)

        logger.debug(f"Vulnérabilités identifiées: {len(vulnerabilities)}")

        return vulnerabilities

    def _extract_premises(self, text: str) -> List[str]:
        """Extrait les prémisses d'un texte argumentatif."""
        premises = []
        sentences = self._split_into_sentences(text)

        # Si l'argument contient "car", "parce que", etc., essayer d'extraire la prémisse principale
        full_text_lower = text.lower()
        for marker in self.premise_markers:
            if marker in full_text_lower:
                parts = full_text_lower.split(marker, 1)
                if len(parts) == 2:
                    # La partie après le marqueur est la prémisse
                    premise_part = parts[1].strip()
                    # Trouver la phrase complète correspondante
                    for sentence in sentences:
                        if premise_part in sentence.lower():
                            premises.append(sentence.strip())
                            break

        # Si des marqueurs de conclusion sont trouvés, extraire tout avant comme prémisses
        for marker in self.conclusion_markers:
            if marker in full_text_lower:
                parts = full_text_lower.split(marker, 1)
                if len(parts) == 2:
                    premise_part = parts[0].strip()
                    # Éviter de dupliquer si déjà trouvé
                    if not any(premise_part in p.lower() for p in premises):
                        premises.append(premise_part.capitalize())
                    break

        # Si aucune prémisse n'a été trouvée avec les marqueurs
        if not premises:
            # Si c'est un argument simple sans marqueurs, essayer de découper
            if len(sentences) > 1:
                # Chercher si la dernière phrase contient une forme de conclusion
                if any(
                    marker in sentences[-1].lower()
                    for marker in self.conclusion_markers
                ):
                    # Toutes les phrases sauf la dernière sont des prémisses
                    premises = [s.strip() for s in sentences[:-1]]
                else:
                    # Sinon, prendre la première phrase comme prémisse
                    premises = [sentences[0].strip()]
            else:
                # Pour un argument d'une seule phrase, essayer de le décomposer
                premises = [text.strip()]

        return premises

    def _extract_conclusion(self, text: str) -> str:
        """Extrait la conclusion d'un texte argumentatif."""
        sentences = self._split_into_sentences(text)

        # Chercher des phrases avec des marqueurs de conclusion
        for sentence in sentences:
            if any(marker in sentence.lower() for marker in self.conclusion_markers):
                return sentence.strip()

        # Chercher des parties après un marqueur de prémisse
        full_text_lower = text.lower()
        for marker in self.premise_markers:
            if marker in full_text_lower:
                parts = full_text_lower.split(marker, 1)
                if len(parts) == 2:
                    # La partie avant le marqueur pourrait être la conclusion
                    conclusion_part = parts[0].strip()
                    # Vérifier que cette partie fait partie d'une phrase
                    for sentence in sentences:
                        if conclusion_part in sentence.lower():
                            return sentence.strip()

        # Si aucune conclusion explicite n'est trouvée, prendre la dernière phrase
        if sentences:
            return sentences[-1].strip()

        return ""

    def _determine_argument_type(self, text: str) -> str:
        """Détermine le type d'argument (déductif, inductif, abductif)."""
        text_lower = text.lower()

        # Chercher des marqueurs spécifiques pour chaque type d'argument
        for arg_type, markers in self.argument_types.items():
            if any(marker in text_lower for marker in markers):
                return arg_type

        # Heuristiques pour déterminer le type en l'absence de marqueurs explicites

        # Déductif: utilise des mots comme "donc", "nécessairement", structure syllogistique
        if any(marker in text_lower for marker in self.conclusion_markers):
            # Chercher des indications de nécessité logique
            if any(
                term in text_lower
                for term in [
                    "tous",
                    "chaque",
                    "toujours",
                    "jamais",
                    "aucun",
                    "nécessairement",
                ]
            ):
                return "deductive"

        # Inductif: généralisation à partir d'exemples, statistiques, probabilités
        if any(
            term in text_lower
            for term in [
                "souvent",
                "généralement",
                "la plupart",
                "plusieurs",
                "nombreux",
                "statistiques",
                "études",
                "observations",
                "exemple",
            ]
        ):
            return "inductive"

        # Abductif: recherche d'explication, inférence à la meilleure explication
        if any(
            term in text_lower
            for term in [
                "explication",
                "explique",
                "cause",
                "raison",
                "pourquoi",
                "comprendre",
                "suggère",
                "probable",
            ]
        ):
            return "abductive"

        # Si le texte contient "si...alors", c'est probablement déductif
        if "si" in text_lower and any(term in text_lower for term in ["alors", "donc"]):
            return "deductive"

        # Par défaut, considérer comme inductif (moins restrictif que déductif)
        return "inductive"

    def _calculate_confidence(self, premises: List[str], conclusion: str) -> float:
        """Calcule un score de confiance pour l'extraction de l'argument."""
        confidence = 0.5  # Score de base

        # Ajuster en fonction du nombre de prémisses trouvées
        if len(premises) > 0:
            confidence += 0.2

        # Ajuster en fonction de la présence d'une conclusion
        if conclusion:
            confidence += 0.2

        # Ajuster en fonction de la présence de marqueurs explicites
        has_premise_markers = any(
            any(marker in p.lower() for marker in self.premise_markers)
            for p in premises
        )
        has_conclusion_markers = any(
            marker in conclusion.lower() for marker in self.conclusion_markers
        )

        if has_premise_markers:
            confidence += 0.1

        if has_conclusion_markers:
            confidence += 0.1

        # Limiter à 1.0
        return min(confidence, 1.0)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Divise un texte en phrases."""
        # Regex simplifiée pour la division en phrases
        return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    def _looks_like_premise(self, text: str) -> bool:
        """Détermine si une phrase ressemble à une prémisse."""
        # Une heuristique simple : les prémisses sont généralement déclaratives
        return not text.endswith("?") and not text.startswith("Si") and len(text) > 10

    def _fix_identical_premise_conclusion(
        self, premises: List[str], conclusion: str, original_text: str
    ) -> Tuple[List[str], str]:
        """
        Vérifie et corrige si la prémisse et la conclusion sont identiques.

        Args:
            premises: Liste des prémisses extraites
            conclusion: Conclusion extraite
            original_text: Texte original de l'argument

        Returns:
            Tuple contenant les prémisses et la conclusion corrigées
        """
        # Si pas de prémisses ou de conclusion, retourner tel quel
        if not premises or not conclusion:
            return premises, conclusion

        # Vérifier si une prémisse et la conclusion sont identiques
        identical_premises = [p for p in premises if p.lower() == conclusion.lower()]

        if identical_premises:
            logger.warning(
                "Prémisse et conclusion identiques détectées, tentative de correction..."
            )

            # Essayer de décomposer l'argument
            sentences = self._split_into_sentences(original_text)

            if "car" in original_text.lower() or "parce que" in original_text.lower():
                # Format "A car B" ou "A parce que B"
                for marker in self.premise_markers:
                    if marker in original_text.lower():
                        parts = original_text.lower().split(marker, 1)
                        if len(parts) == 2:
                            # A = conclusion, B = prémisse
                            conclusion_part = parts[0].strip()
                            premise_part = parts[1].strip()

                            # Trouver les phrases complètes correspondantes
                            new_premises = []
                            for sentence in sentences:
                                if (
                                    premise_part in sentence.lower()
                                    and sentence.lower()
                                    not in [p.lower() for p in new_premises]
                                ):
                                    new_premises.append(sentence.strip())

                            new_conclusion = ""
                            for sentence in sentences:
                                if conclusion_part in sentence.lower():
                                    new_conclusion = sentence.strip()
                                    break

                            if new_premises and new_conclusion:
                                return new_premises, new_conclusion

            # Si l'argument est de la forme "B donc A"
            elif (
                "donc" in original_text.lower()
                or "par conséquent" in original_text.lower()
            ):
                for marker in self.conclusion_markers:
                    if marker in original_text.lower():
                        parts = original_text.lower().split(marker, 1)
                        if len(parts) == 2:
                            # B = prémisse, A = conclusion
                            premise_part = parts[0].strip()
                            conclusion_part = parts[1].strip()

                            # Trouver les phrases complètes
                            new_premises = []
                            for sentence in sentences:
                                if (
                                    premise_part in sentence.lower()
                                    and sentence.lower()
                                    not in [p.lower() for p in new_premises]
                                ):
                                    new_premises.append(sentence.strip())

                            new_conclusion = ""
                            for sentence in sentences:
                                if conclusion_part in sentence.lower():
                                    new_conclusion = sentence.strip()
                                    break

                            if new_premises and new_conclusion:
                                return new_premises, new_conclusion

            # Si aucune des approches ci-dessus ne fonctionne, essayer de diviser l'argument
            if len(sentences) > 1:
                # Prendre toutes les phrases sauf la dernière comme prémisses
                new_premises = [s.strip() for s in sentences[:-1]]
                # Prendre la dernière phrase comme conclusion
                new_conclusion = sentences[-1].strip()

                # Vérifier que les prémisses et la conclusion ne sont pas identiques
                if not any(p.lower() == new_conclusion.lower() for p in new_premises):
                    return new_premises, new_conclusion

            # Si tout échoue et que l'argument est une seule phrase, essayer de le diviser
            if len(sentences) == 1 and len(premises) == 1 and premises[0] == conclusion:
                # Chercher une virgule ou un point-virgule pour diviser
                text = sentences[0]
                for separator in [",", ";"]:
                    if separator in text:
                        parts = text.split(separator, 1)
                        if len(parts) == 2:
                            return [parts[0].strip()], parts[1].strip()

                # Si l'argument reste indivisible, créer une prémisse implicite
                return [f"Prémisse implicite: {premises[0]}"], conclusion

        return premises, conclusion


class VulnerabilityAnalyzer:
    """Classe pour analyser les vulnérabilités dans les arguments."""

    def __init__(self):
        """Initialise l'analyseur de vulnérabilités."""
        self.vulnerability_patterns = {
            "generalisation_abusive": {
                "patterns": ["tous", "chaque", "toujours", "jamais", "sans exception"],
                "counter_type": CounterArgumentType.COUNTER_EXAMPLE,
            },
            "hypothese_non_fondee": {
                "patterns": [
                    "évidemment",
                    "clairement",
                    "bien sûr",
                    "naturellement",
                    "certainement",
                ],
                "counter_type": CounterArgumentType.PREMISE_CHALLENGE,
            },
            "fausse_dichotomie": {
                "patterns": ["soit", "ou bien", "l'un ou l'autre", "deux options"],
                "counter_type": CounterArgumentType.ALTERNATIVE_EXPLANATION,
            },
            "pente_glissante": {
                "patterns": ["mènera à", "conduira à", "finira par", "inévitablement"],
                "counter_type": CounterArgumentType.REDUCTIO_AD_ABSURDUM,
            },
            "causalite_douteuse": {
                "patterns": ["cause", "provoque", "entraîne", "est dû à"],
                "counter_type": CounterArgumentType.DIRECT_REFUTATION,
            },
        }

        logger.debug("VulnerabilityAnalyzer initialisé")

    def analyze_vulnerabilities(self, argument: Argument) -> List[Vulnerability]:
        """
        Analyse les vulnérabilités dans un argument.

        Args:
            argument: L'argument à analyser

        Returns:
            Une liste de vulnérabilités identifiées
        """
        logger.info(f"Analyse des vulnérabilités: {argument.content[:100]}...")

        vulnerabilities = []

        # Analyser les prémisses
        for i, premise in enumerate(argument.premises):
            vuln = self._analyze_premise(premise)
            if vuln:
                vuln.target = f"premise_{i}"
                vulnerabilities.append(vuln)

        # Analyser la conclusion
        conclusion_vuln = self._analyze_premise(argument.conclusion)
        if conclusion_vuln:
            conclusion_vuln.target = "conclusion"
            vulnerabilities.append(conclusion_vuln)

        # Analyser la structure globale de l'argument
        structure_vuln = self._analyze_structure(argument)
        if structure_vuln:
            vulnerabilities.append(structure_vuln)

        logger.debug(f"Vulnérabilités identifiées: {len(vulnerabilities)}")

        return vulnerabilities

    def _analyze_premise(self, text: str) -> Optional[Vulnerability]:
        """Analyse une prémisse pour identifier des vulnérabilités."""
        text_lower = text.lower()

        for vuln_type, info in self.vulnerability_patterns.items():
            for pattern in info["patterns"]:
                if pattern in text_lower:
                    return Vulnerability(
                        type=vuln_type,
                        target="",  # Sera rempli par l'appelant
                        description=f"Contient '{pattern}', suggérant un {vuln_type}",
                        score=0.7,
                        suggested_counter_type=info["counter_type"],
                    )

        return None

    def _analyze_structure(self, argument: Argument) -> Optional[Vulnerability]:
        """Analyse la structure globale de l'argument pour identifier des vulnérabilités."""
        # Vérifier si l'argument a des prémisses
        if not argument.premises:
            return Vulnerability(
                type="manque_de_premisses",
                target="structure",
                description="L'argument ne contient pas de prémisses explicites",
                score=0.9,
                suggested_counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            )

        # Vérifier la cohérence entre les prémisses et la conclusion
        if not self._check_premise_conclusion_coherence(argument):
            return Vulnerability(
                type="incoherence_logique",
                target="structure",
                description="Les prémisses ne semblent pas connectées logiquement à la conclusion",
                score=0.8,
                suggested_counter_type=CounterArgumentType.DIRECT_REFUTATION,
            )

        return None

    def _check_premise_conclusion_coherence(self, argument: Argument) -> bool:
        """Vérifie la cohérence entre les prémisses et la conclusion."""
        # Une heuristique simple : vérifier si des mots clés des prémisses apparaissent dans la conclusion
        premise_words = set()
        for premise in argument.premises:
            premise_words.update(self._extract_key_words(premise))

        conclusion_words = set(self._extract_key_words(argument.conclusion))

        # S'il y a au moins quelques mots en commun, c'est cohérent
        return len(premise_words.intersection(conclusion_words)) > 0

    def _extract_key_words(self, text: str) -> List[str]:
        """Extrait les mots clés d'un texte."""
        # Supprimer la ponctuation et les mots vides
        text = re.sub(r"[^\w\s]", "", text.lower())
        stop_words = [
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "ou",
            "mais",
            "car",
            "donc",
            "si",
            "que",
            "qui",
            "quoi",
            "comment",
            "quand",
            "où",
            "est",
            "sont",
            "a",
            "ont",
            "être",
            "avoir",
        ]

        return [word for word in text.split() if word not in stop_words]


def parse_llm_response(response: str) -> Dict[str, Any]:
    """
    Parse une réponse de LLM qui peut être au format JSON ou texte.

    Args:
        response: La réponse du LLM

    Returns:
        Un dictionnaire avec les informations parsées
    """
    try:
        # Essayer de parser comme JSON
        return json.loads(response)
    except json.JSONDecodeError:
        # Si ce n'est pas du JSON, traiter comme du texte structuré
        return parse_structured_text(response)


def parse_structured_text(text: str) -> Dict[str, Any]:
    """
    Parse un texte structuré en clés-valeurs.

    Args:
        text: Le texte à parser

    Returns:
        Un dictionnaire avec les informations parsées
    """
    result = {}
    current_key = None
    current_value = []

    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Chercher des lignes de type "Clé: Valeur"
        match = re.match(r"^([^:]+):\s*(.*)$", line)
        if match:
            # Si on avait une clé précédente, sauvegarder sa valeur
            if current_key:
                result[current_key] = (
                    "\n".join(current_value)
                    if len(current_value) > 1
                    else current_value[0]
                )
                current_value = []

            # Nouvelle clé et début de nouvelle valeur
            current_key = match.group(1).lower()
            value = match.group(2).strip()
            if value:
                current_value.append(value)
        elif current_key:
            # Continuation de la valeur précédente
            current_value.append(line)

    # Sauvegarder la dernière clé-valeur
    if current_key and current_value:
        result[current_key] = (
            "\n".join(current_value) if len(current_value) > 1 else current_value[0]
        )

    return result
