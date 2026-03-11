"""
Argument parser and vulnerability analyzer for counter-argument generation.

Provides French-language NLP heuristics for extracting argument structure
(premises, conclusion, type) and identifying logical vulnerabilities.

Adapted from 2.3.3-generation-contre-argument/counter_agent/agent/parser.py.
"""

import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

from .definitions import Argument, Vulnerability, CounterArgumentType

logger = logging.getLogger(__name__)


class ArgumentParser:
    """Parse French argumentative text into structured arguments."""

    def __init__(self):
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
            "abductive": [
                "meilleure explication",
                "probablement",
                "vraisemblablement",
            ],
        }
        self.vulnerability_analyzer = VulnerabilityAnalyzer()

    def parse_argument(self, text: str) -> Argument:
        """Parse text to extract argument structure."""
        premises = self._extract_premises(text)
        conclusion = self._extract_conclusion(text)
        premises, conclusion = self._fix_identical_premise_conclusion(
            premises, conclusion, text
        )
        argument_type = self._determine_argument_type(text)
        confidence = self._calculate_confidence(premises, conclusion)
        return Argument(
            content=text,
            premises=premises,
            conclusion=conclusion,
            argument_type=argument_type,
            confidence=confidence,
        )

    def identify_vulnerabilities(self, argument: Argument) -> List[Vulnerability]:
        """Identify vulnerabilities in an argument, sorted by score."""
        vulnerabilities = self.vulnerability_analyzer.analyze_vulnerabilities(argument)
        vulnerabilities.sort(key=lambda v: v.score, reverse=True)
        return vulnerabilities

    def _extract_premises(self, text: str) -> List[str]:
        """Extract premises from argumentative text."""
        premises = []
        sentences = self._split_into_sentences(text)
        full_text_lower = text.lower()

        for marker in self.premise_markers:
            if marker in full_text_lower:
                parts = full_text_lower.split(marker, 1)
                if len(parts) == 2:
                    premise_part = parts[1].strip()
                    for sentence in sentences:
                        if premise_part in sentence.lower():
                            premises.append(sentence.strip())
                            break

        for marker in self.conclusion_markers:
            if marker in full_text_lower:
                parts = full_text_lower.split(marker, 1)
                if len(parts) == 2:
                    premise_part = parts[0].strip()
                    if not any(premise_part in p.lower() for p in premises):
                        premises.append(premise_part.capitalize())
                    break

        if not premises:
            if len(sentences) > 1:
                if any(
                    marker in sentences[-1].lower()
                    for marker in self.conclusion_markers
                ):
                    premises = [s.strip() for s in sentences[:-1]]
                else:
                    premises = [sentences[0].strip()]
            else:
                premises = [text.strip()]

        return premises

    def _extract_conclusion(self, text: str) -> str:
        """Extract conclusion from argumentative text."""
        sentences = self._split_into_sentences(text)

        for sentence in sentences:
            if any(marker in sentence.lower() for marker in self.conclusion_markers):
                return sentence.strip()

        full_text_lower = text.lower()
        for marker in self.premise_markers:
            if marker in full_text_lower:
                parts = full_text_lower.split(marker, 1)
                if len(parts) == 2:
                    conclusion_part = parts[0].strip()
                    for sentence in sentences:
                        if conclusion_part in sentence.lower():
                            return sentence.strip()

        if sentences:
            return sentences[-1].strip()
        return ""

    def _determine_argument_type(self, text: str) -> str:
        """Determine argument type (deductive, inductive, abductive)."""
        text_lower = text.lower()

        for arg_type, markers in self.argument_types.items():
            if any(marker in text_lower for marker in markers):
                return arg_type

        if any(marker in text_lower for marker in self.conclusion_markers):
            if any(
                term in text_lower
                for term in ["tous", "chaque", "toujours", "jamais", "aucun"]
            ):
                return "deductive"

        if any(
            term in text_lower
            for term in [
                "souvent",
                "généralement",
                "la plupart",
                "plusieurs",
                "statistiques",
                "études",
                "exemple",
            ]
        ):
            return "inductive"

        if any(
            term in text_lower
            for term in [
                "explication",
                "explique",
                "cause",
                "raison",
                "pourquoi",
                "suggère",
                "probable",
            ]
        ):
            return "abductive"

        if "si" in text_lower and any(term in text_lower for term in ["alors", "donc"]):
            return "deductive"

        return "inductive"

    def _calculate_confidence(self, premises: List[str], conclusion: str) -> float:
        """Calculate extraction confidence score."""
        confidence = 0.5
        if len(premises) > 0:
            confidence += 0.2
        if conclusion:
            confidence += 0.2
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
        return min(confidence, 1.0)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    def _fix_identical_premise_conclusion(
        self, premises: List[str], conclusion: str, original_text: str
    ) -> Tuple[List[str], str]:
        """Fix cases where premise and conclusion are identical."""
        if not premises or not conclusion:
            return premises, conclusion

        identical_premises = [p for p in premises if p.lower() == conclusion.lower()]
        if not identical_premises:
            return premises, conclusion

        sentences = self._split_into_sentences(original_text)

        # Try "A car B" pattern
        for marker in self.premise_markers:
            if marker in original_text.lower():
                parts = original_text.lower().split(marker, 1)
                if len(parts) == 2:
                    conclusion_part = parts[0].strip()
                    premise_part = parts[1].strip()
                    new_premises = [
                        s.strip() for s in sentences if premise_part in s.lower()
                    ]
                    new_conclusion = next(
                        (s.strip() for s in sentences if conclusion_part in s.lower()),
                        "",
                    )
                    if new_premises and new_conclusion:
                        return new_premises, new_conclusion

        # Try "B donc A" pattern
        for marker in self.conclusion_markers:
            if marker in original_text.lower():
                parts = original_text.lower().split(marker, 1)
                if len(parts) == 2:
                    premise_part = parts[0].strip()
                    conclusion_part = parts[1].strip()
                    new_premises = [
                        s.strip() for s in sentences if premise_part in s.lower()
                    ]
                    new_conclusion = next(
                        (s.strip() for s in sentences if conclusion_part in s.lower()),
                        "",
                    )
                    if new_premises and new_conclusion:
                        return new_premises, new_conclusion

        # Fallback: split by sentences
        if len(sentences) > 1:
            new_premises = [s.strip() for s in sentences[:-1]]
            new_conclusion = sentences[-1].strip()
            if not any(p.lower() == new_conclusion.lower() for p in new_premises):
                return new_premises, new_conclusion

        # Last resort: split by comma
        if len(sentences) == 1 and len(premises) == 1 and premises[0] == conclusion:
            for separator in [",", ";"]:
                if separator in sentences[0]:
                    parts = sentences[0].split(separator, 1)
                    if len(parts) == 2:
                        return [parts[0].strip()], parts[1].strip()
            return [f"Prémisse implicite: {premises[0]}"], conclusion

        return premises, conclusion


class VulnerabilityAnalyzer:
    """Analyze arguments for logical vulnerabilities."""

    def __init__(self):
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
                "patterns": [
                    "mènera à",
                    "conduira à",
                    "finira par",
                    "inévitablement",
                ],
                "counter_type": CounterArgumentType.REDUCTIO_AD_ABSURDUM,
            },
            "causalite_douteuse": {
                "patterns": ["cause", "provoque", "entraîne", "est dû à"],
                "counter_type": CounterArgumentType.DIRECT_REFUTATION,
            },
        }

    def analyze_vulnerabilities(self, argument: Argument) -> List[Vulnerability]:
        """Analyze argument for vulnerabilities."""
        vulnerabilities = []

        for i, premise in enumerate(argument.premises):
            vuln = self._analyze_text(premise)
            if vuln:
                vuln.target = f"premise_{i}"
                vulnerabilities.append(vuln)

        conclusion_vuln = self._analyze_text(argument.conclusion)
        if conclusion_vuln:
            conclusion_vuln.target = "conclusion"
            vulnerabilities.append(conclusion_vuln)

        structure_vuln = self._analyze_structure(argument)
        if structure_vuln:
            vulnerabilities.append(structure_vuln)

        return vulnerabilities

    def _analyze_text(self, text: str) -> Optional[Vulnerability]:
        """Check text for vulnerability patterns."""
        text_lower = text.lower()
        for vuln_type, info in self.vulnerability_patterns.items():
            for pattern in info["patterns"]:
                if pattern in text_lower:
                    return Vulnerability(
                        type=vuln_type,
                        target="",
                        description=f"Contains '{pattern}', suggesting {vuln_type}",
                        score=0.7,
                        suggested_counter_type=info["counter_type"],
                    )
        return None

    def _analyze_structure(self, argument: Argument) -> Optional[Vulnerability]:
        """Analyze argument structure for vulnerabilities."""
        if not argument.premises:
            return Vulnerability(
                type="manque_de_premisses",
                target="structure",
                description="Argument has no explicit premises",
                score=0.9,
                suggested_counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            )

        if not self._check_coherence(argument):
            return Vulnerability(
                type="incoherence_logique",
                target="structure",
                description="Premises not logically connected to conclusion",
                score=0.8,
                suggested_counter_type=CounterArgumentType.DIRECT_REFUTATION,
            )
        return None

    def _check_coherence(self, argument: Argument) -> bool:
        """Check if premises and conclusion share keywords."""
        premise_words = set()
        for premise in argument.premises:
            premise_words.update(self._extract_key_words(premise))
        conclusion_words = set(self._extract_key_words(argument.conclusion))
        return len(premise_words.intersection(conclusion_words)) > 0

    def _extract_key_words(self, text: str) -> List[str]:
        """Extract non-stopword keywords from text."""
        text = re.sub(r"[^\w\s]", "", text.lower())
        stop_words = {
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
            "est",
            "sont",
            "a",
            "ont",
        }
        return [word for word in text.split() if word not in stop_words]


def parse_llm_response(response: str) -> Dict[str, Any]:
    """Parse LLM response as JSON or structured text."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return parse_structured_text(response)


def parse_structured_text(text: str) -> Dict[str, Any]:
    """Parse key: value structured text into dict."""
    result = {}
    current_key = None
    current_value = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^([^:]+):\s*(.*)$", line)
        if match:
            if current_key:
                result[current_key] = (
                    "\n".join(current_value)
                    if len(current_value) > 1
                    else current_value[0] if current_value else ""
                )
                current_value = []
            current_key = match.group(1).lower()
            value = match.group(2).strip()
            if value:
                current_value.append(value)
        elif current_key:
            current_value.append(line)

    if current_key and current_value:
        result[current_key] = (
            "\n".join(current_value) if len(current_value) > 1 else current_value[0]
        )
    return result
