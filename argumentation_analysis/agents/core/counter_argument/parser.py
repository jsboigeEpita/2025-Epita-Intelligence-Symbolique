"""
Argument parser and vulnerability analyzer for counter-argument generation.

Provides French-language NLP heuristics for extracting argument structure
(premises, conclusion, type) and identifying logical vulnerabilities.

Adapted from 2.3.3-generation-contre-argument/counter_agent/agent/parser.py.
"""

import re
import logging
from typing import List, Tuple, Optional

from .definitions import Argument, Vulnerability, CounterArgumentType

logger = logging.getLogger(__name__)

# #2671: "car" coordinates, it never opens a preposed clause the way
# "puisque"/"comme"/"parce que" do ("Puisque X, Y"). A sentence opening on
# "Car X, Y" states one premise, not a premise and its conclusion.
_COORDINATING_PREMISE_MARKERS = {"car"}

# #2678: why ``parse_prose`` finds nothing to reconstruct. The route words its
# refusal from the reason, so each message stays true of the text it refuses.
NO_MARKER = "no_marker"
PREMISE_MARKER_ALONE = "premise_marker_alone"
CONCLUSION_MARKER_ALONE = "conclusion_marker_alone"

# #2682: a marker word opening a fixed phrase is not a marker. "Comme prévu"
# says "as expected", not "because"; "ainsi que" says "as well as", not
# "therefore". Each entry lists the words that make the phrase fixed.
_FIXED_PHRASE_FOLLOWERS = {
    "comme": (
        "prévu",
        "convenu",
        "annoncé",
        "attendu",
        "indiqué",
        "mentionné",
        "si",
        "toujours",
    ),
    "ainsi": ("que",),
}


def _find_marker(text: str, markers: List[str]) -> Optional[Tuple[int, int]]:
    """Earliest standalone-word occurrence of any marker (case-insensitive).

    #2562: a plain substring test misfires — ``car`` matches ``carte``,
    ``comme`` matches ``commencer``. A marker only counts when flanked by
    non-word characters (``\\w`` already covers accented French letters).

    #2682: an occurrence opening a fixed phrase (``_FIXED_PHRASE_FOLLOWERS``)
    is skipped, and a later occurrence of the same marker still counts.
    """
    best: Optional[Tuple[int, int]] = None
    for marker in markers:
        followers = _FIXED_PHRASE_FOLLOWERS.get(marker, ())
        fixed = re.compile(
            r"\s+(?:" + "|".join(re.escape(f) for f in followers) + r")(?!\w)",
            re.IGNORECASE,
        )
        for match in re.finditer(
            rf"(?<!\w){re.escape(marker)}(?!\w)", text, re.IGNORECASE
        ):
            if followers and fixed.match(text, match.end()):
                continue
            if best is None or match.start() < best[0]:
                best = (match.start(), match.end())
            break
    return best


class ArgumentParser:
    """Parse French argumentative text into structured arguments."""

    def __init__(self) -> None:
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
            "conclusion",
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

    def parse_prose(self, text: str) -> Optional[Argument]:
        """Parse prose into an argument, or None when nothing is identifiable.

        #2562 route contract: a text carrying no argumentative marker (no
        conclusion marker, no premise marker) has nothing reconstructible in
        it — the caller must say so instead of presenting an empty or
        fabricated structure as a success. ``parse_argument`` keeps its
        always-returns-something contract for the agent's own calls.
        ``unparseable_reason`` decides, and says why (#2678).
        """
        if self.unparseable_reason(text) is not None:
            return None
        return self.parse_argument(text)

    def unparseable_reason(self, text: str) -> Optional[str]:
        """Why ``parse_prose`` returns None for ``text``; None when it parses.

        A text parses when its markers give a reading with both sides
        (``_marker_reading``). A text whose two sides say the same thing is
        read, not refused: "Il pleut car il pleut." is circular, and says so.

        ``NO_MARKER`` (#2562): no conclusion marker and no premise marker.

        ``CONCLUSION_MARKER_ALONE`` (#2682): a conclusion marker leaves a side
        empty and no neighbouring sentence fills it. "Donc il faut partir."
        states a conclusion and no premise, "Il pleut donc." a premise and no
        conclusion.

        ``PREMISE_MARKER_ALONE`` (#2678): the same for a premise marker. "Car
        il pleut." states a premise and no claim, "Il faut partir car." a
        claim and no premise. "Car" never opens a preposed clause (#2671), so
        "Car il pleut, il faut partir." is one premise with no claim (#2682).
        """
        if self._marker_reading(text) is not None:
            return None
        if _find_marker(text, self.conclusion_markers) is not None:
            return CONCLUSION_MARKER_ALONE
        if _find_marker(text, self.premise_markers) is not None:
            return PREMISE_MARKER_ALONE
        return NO_MARKER

    def _marker_reading(self, text: str) -> Optional[Tuple[List[str], str]]:
        """The reading the markers give, ``(premises, conclusion)``, or None.

        #2682: the conclusion marker's reading when both of its sides are
        filled, otherwise the premise marker's when both of its sides are:
        "Donc il faut partir car il pleut." has nothing before "donc", and
        "car" supplies the premise. None when no marker fills both sides.
        """
        sentences = self._split_into_sentences(text)
        by_conclusion = self._split_at_conclusion_marker(text, sentences)
        if by_conclusion is not None and by_conclusion[0] and by_conclusion[1]:
            return by_conclusion
        by_premise = self._split_at_premise_marker(text, sentences)
        if by_premise is not None and by_premise[0] and by_premise[1]:
            return [by_premise[1]], by_premise[0]
        return None

    def _sentence_spans(self, text: str, sentences: List[str]) -> List[Tuple[int, int]]:
        """Where each of ``sentences`` sits in ``text``, in order."""
        spans: List[Tuple[int, int]] = []
        cursor = 0
        for sentence in sentences:
            start = text.find(sentence, cursor)
            if start < 0:
                continue
            spans.append((start, start + len(sentence)))
            cursor = start + len(sentence)
        return spans

    def _sentence_at(
        self, text: str, sentences: List[str], offset: int
    ) -> Optional[str]:
        """The sentence (original case) containing ``offset``."""
        for start, end in self._sentence_spans(text, sentences):
            if start <= offset < end:
                return text[start:end]
        return None

    def _split_at_conclusion_marker(
        self, text: str, sentences: List[str]
    ) -> Optional[Tuple[List[str], str]]:
        """Split around the earliest conclusion marker: ``(premises, conclusion)``.

        #2682: the premises are the sentences before the marker's sentence,
        plus the part of that sentence before the marker; the conclusion runs
        from the marker to the end of its sentence. "Il pleut, donc il faut
        partir." used to come back with the whole sentence as its conclusion,
        premise included. A marker ending its sentence ("Il pleut donc. Il
        faut partir.") concludes on the next sentence, as a premise marker
        does. A side the text does not fill comes back empty.
        """
        marker = _find_marker(text, self.conclusion_markers)
        if marker is None:
            return None
        marker_start, marker_end = marker
        spans = self._sentence_spans(text, sentences)
        for index, (sentence_start, sentence_end) in enumerate(spans):
            if not sentence_start <= marker_start < sentence_end:
                continue
            premises = [text[start:end].strip() for start, end in spans[:index]]
            before = text[sentence_start:marker_start].strip(" \t,;:")
            if before:
                premises.append(before)
            if text[marker_end:sentence_end].strip(" \t,;:"):
                return premises, text[marker_start:sentence_end].strip()
            if index + 1 < len(spans):
                start, end = spans[index + 1]
                return premises, text[start:end].strip()
            return premises, ""
        return None

    def _split_at_premise_marker(
        self, text: str, sentences: List[str]
    ) -> Optional[Tuple[str, str]]:
        """Split around the earliest premise marker: ``(conclusion, premise)``.

        #2600: "X car Y" states its premise AFTER the marker and its
        conclusion BEFORE it. Returning the whole sentence for both made the
        argument read as circular. Both parts come back with the marker and
        the punctuation around it left out.

        #2671: a sentence OPENING on its marker has nothing before it inside
        the sentence. When a clause follows ("Puisque X, Y") the sentence
        carries its own reading: the marker's clause is the premise, marker
        included, and the next clause the conclusion (the #2600 review's
        pinned form; never for "car", which cannot open such a clause).
        Otherwise the claim the premise supports is another
        sentence: the one before it, or the one after when it opens the text.

        #2682: a sentence ENDING on its marker ("Il faut partir car. Il
        pleut.") announces its premise, and the premise is the next sentence.
        A side the text does not fill comes back empty.
        """
        marker = _find_marker(text, self.premise_markers)
        if marker is None:
            return None
        marker_start, marker_end = marker
        spans = self._sentence_spans(text, sentences)

        for index, (sentence_start, sentence_end) in enumerate(spans):
            if not sentence_start <= marker_start < sentence_end:
                continue
            before = text[sentence_start:marker_start].strip(" \t,;:")
            after = text[marker_end:sentence_end].strip(" \t,;:")
            if before and not after and index + 1 < len(spans):
                start, end = spans[index + 1]
                return before, text[start:end].strip()
            if before or not after:
                return before, after
            sentence = text[sentence_start:sentence_end]
            preposes = (
                text[marker_start:marker_end].lower()
                not in _COORDINATING_PREMISE_MARKERS
            )
            for separator in (",", ";"):
                if preposes and separator in sentence:
                    premise, claim = sentence.split(separator, 1)
                    return claim.strip(" \t,;:"), premise.strip()
            neighbour = index - 1 if index > 0 else index + 1
            if neighbour < len(spans):
                start, end = spans[neighbour]
                return text[start:end].strip(), after
            return before, after
        return None

    def _extract_premises(self, text: str) -> List[str]:
        """Extract premises from argumentative text.

        #2562: premises come out as one sentence per list element, in the
        original case (the former implementation lowercased the text and
        returned everything before a conclusion marker as ONE merged,
        re-capitalized string).
        """
        # #2600/#2682: the premises of the reading the markers give. A text
        # whose markers leave a side empty ("Car il pleut.") has none;
        # ``parse_prose`` refuses it (``unparseable_reason``), and
        # ``parse_argument``, which always returns, falls back below.
        reading = self._marker_reading(text)
        if reading is not None:
            return reading[0]

        sentences = self._split_into_sentences(text)

        conclusion_marker = _find_marker(text, self.conclusion_markers)
        if conclusion_marker is not None:
            premises = self._split_into_sentences(text[: conclusion_marker[0]])
            if premises:
                return premises

        premise_marker = _find_marker(text, self.premise_markers)
        if premise_marker is not None:
            sentence = self._sentence_at(text, sentences, premise_marker[0])
            if sentence is not None:
                return [sentence]

        if len(sentences) > 1:
            return [sentences[0]]
        return [text.strip()] if text.strip() else []

    def _extract_conclusion(self, text: str) -> str:
        """Extract conclusion from argumentative text."""
        # #2600/#2682: symmetric to the premise side.
        reading = self._marker_reading(text)
        if reading is not None:
            return reading[1]

        sentences = self._split_into_sentences(text)

        conclusion_marker = _find_marker(text, self.conclusion_markers)
        if conclusion_marker is not None:
            sentence = self._sentence_at(text, sentences, conclusion_marker[0])
            if sentence is not None:
                return sentence

        premise_marker = _find_marker(text, self.premise_markers)
        if premise_marker is not None:
            sentence = self._sentence_at(text, sentences, premise_marker[0])
            if sentence is not None:
                return sentence

        if sentences:
            return sentences[-1]
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


# parse_llm_response / parse_structured_text were withdrawn (#2137): zero
# callers in the repo (the nl_to_logic homonyms are distinct private methods) —
# relics of the student project's raw LLM-response parsing, made useless by
# the Semantic Kernel migration.
