"""
French Fallacy Detection Adapter — 3-tier hybrid detection.

Wraps and extends the student 2.3.2-detection-sophismes project.
Provides fallacy detection through 3 tiers with automatic fallback:

  Tier 1: LLM zero-shot (via ServiceDiscovery — Qwen 3.5 / OpenRouter / OpenAI)
  Tier 2: NLI zero-shot (mDeBERTa or similar, auto-downloaded ~600MB)
  Tier 3: Symbolic rules (spaCy Matcher patterns, always available)

Dependencies:
  - Tier 3 (symbolic): spacy + fr_core_news_lg (or sm)
  - Tier 2 (NLI): transformers + torch
  - Tier 1 (LLM): An LLM provider in ServiceDiscovery

All tiers degrade gracefully if their dependencies are missing.

Integration from student project 2.3.2-detection-sophismes (GitHub #44).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

FALLACY_LABELS_FR = [
    "Attaque personnelle (Ad Hominem)",
    "Appel à la popularité (Ad Populum)",
    "Appel à l'émotion (Appeal to Emotion)",
    "Généralisation hâtive (Hasty Generalization)",
    "Fausse causalité (False Cause)",
    "Faux dilemme (False Dilemma)",
    "Raisonnement circulaire (Circular Reasoning)",
    "Pente glissante (Slippery Slope)",
    "Argument d'autorité (Appeal to Authority)",
    "Appel à la tradition (Appeal to Tradition)",
    "Équivoque (Equivocation)",
    "Sophisme de pertinence",
    "Homme de paille (Straw Man)",
]

# Symbolic rules from student project (spaCy Matcher patterns)
_SYMBOLIC_FALLACY_RULES = {
    "AD_HOMINEM_DIRECT": [
        {
            "PATTERN": [
                {"LOWER": {"IN": ["tu", "vous", "il", "elle"]}},
                {"LEMMA": "être"},
                {"POS": "DET", "OP": "*"},
                {"POS": "ADJ"},
                {"LOWER": {"IN": ["donc", "alors", "parce que", "car"]}},
                {"TEXT": {"REGEX": ".*"}},
            ],
            "FALLACY_TYPE": "Attaque personnelle (Ad Hominem)",
        },
        {
            "PATTERN": [
                {"LOWER": "on"},
                {"LOWER": "ne"},
                {"LEMMA": "pouvoir"},
                {"LOWER": "pas"},
                {"LEMMA": "faire"},
                {"LOWER": "confiance"},
                {"LEMMA": "à"},
                {"POS": "DET", "OP": "?"},
                {"POS": "NOUN"},
            ],
            "FALLACY_TYPE": "Attaque personnelle (Ad Hominem)",
        },
    ],
    "PENTE_GLISSANTE": [
        {
            "PATTERN": [
                {"LOWER": "si"},
                {"LOWER": "on"},
                {"LEMMA": "autoriser"},
                {"POS": "NOUN"},
                {"LOWER": "alors"},
                {"TEXT": {"REGEX": ".*"}},
            ],
            "FALLACY_TYPE": "Pente glissante (Slippery Slope)",
        },
        {
            "PATTERN": [
                {"LOWER": "cela"},
                {"LEMMA": "mener"},
                {"LOWER": "inévitablement"},
                {"LEMMA": "à"},
                {"TEXT": {"REGEX": ".*"}},
            ],
            "FALLACY_TYPE": "Pente glissante (Slippery Slope)",
        },
        {
            "PATTERN": [
                {"LOWER": "le"},
                {"LOWER": "premier"},
                {"LOWER": "pas"},
                {"LOWER": "vers"},
                {"TEXT": {"REGEX": ".*"}},
            ],
            "FALLACY_TYPE": "Pente glissante (Slippery Slope)",
        },
    ],
    "GENERALISATION_HATIVE": [
        {
            "PATTERN": [
                {"LOWER": {"IN": ["tous", "toutes", "chaque", "personne"]}},
                {"POS": "NOUN", "OP": "+"},
                {"LEMMA": "être"},
                {"POS": "ADJ"},
            ],
            "FALLACY_TYPE": "Généralisation hâtive (Hasty Generalization)",
        },
    ],
    "APPEL_A_LA_TRADITION": [
        {
            "PATTERN": [
                {"LOWER": "on"},
                {"LOWER": "a"},
                {"LOWER": "toujours"},
                {"LEMMA": "faire"},
                {"LOWER": "comme"},
                {"LOWER": "ça"},
            ],
            "FALLACY_TYPE": "Appel à la tradition (Appeal to Tradition)",
        },
        {
            "PATTERN": [{"LOWER": "depuis"}, {"LOWER": "toujours"}],
            "FALLACY_TYPE": "Appel à la tradition (Appeal to Tradition)",
        },
    ],
    "ARGUMENT_AUTORITE": [
        {
            "PATTERN": [
                {"POS": "NOUN", "OP": "+"},
                {"LEMMA": "dire"},
                {"LOWER": "que"},
                {"TEXT": {"REGEX": ".*"}},
                {"LOWER": {"IN": ["donc", "alors"]}},
                {"TEXT": {"REGEX": ".*"}},
            ],
            "FALLACY_TYPE": "Argument d'autorité (Appeal to Authority)",
        },
        {
            "PATTERN": [
                {"LOWER": "selon"},
                {"POS": "DET"},
                {"POS": "NOUN"},
                {"TEXT": {"REGEX": ".*"}},
            ],
            "FALLACY_TYPE": "Argument d'autorité (Appeal to Authority)",
        },
    ],
}

# Claim/premise mining patterns (from student project)
_CLAIM_PATTERNS = [
    {
        "PATTERN": [
            {"LOWER": {"IN": ["je", "nous"]}},
            {"LEMMA": {"IN": ["penser", "croire", "affirmer"]}},
            {"LOWER": "que"},
            {"OP": "+"},
        ]
    },
    {
        "PATTERN": [
            {"LOWER": {"IN": ["donc", "par", "en"]}},
            {"LOWER": {"IN": ["conséquent", "conclusion"]}},
            {"IS_PUNCT": True, "OP": "?"},
            {"OP": "+"},
        ]
    },
]

_PREMISE_PATTERNS = [
    {
        "PATTERN": [
            {"LOWER": {"IN": ["parce", "car", "étant"]}},
            {"LOWER": {"IN": ["que", "donné"]}},
            {"OP": "+"},
        ]
    },
    {
        "PATTERN": [
            {"LOWER": {"IN": ["selon", "d'après"]}},
            {"POS": "NOUN"},
            {"OP": "+"},
        ]
    },
]


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class FallacyDetection:
    """A single detected fallacy."""

    fallacy_type: str
    confidence: float
    source: str  # "symbolic", "nli", "llm"
    matched_rule: Optional[str] = None
    description: Optional[str] = None


@dataclass
class FallacyAnalysisResult:
    """Full analysis result from the adapter."""

    text: str
    fallacies: List[FallacyDetection] = field(default_factory=list)
    arguments: Optional[Dict[str, List[str]]] = None
    tiers_used: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict matching AbstractFallacyDetector.detect() output."""
        return {
            "text": self.text,
            "detected_fallacies": {
                f.fallacy_type: {
                    "source": f.source,
                    "confidence": f.confidence,
                    "matched_rule": f.matched_rule,
                    "description": f.description,
                }
                for f in self.fallacies
            },
            "arguments": self.arguments or {},
            "tiers_used": self.tiers_used,
            "explanation": self.explanation,
            "total_fallacies": len(self.fallacies),
        }


# ── Tier 3: Symbolic Detection ──────────────────────────────────────────


class SymbolicFallacyDetector:
    """Rule-based fallacy detection using spaCy Matcher patterns."""

    def __init__(self):
        self._nlp = None
        self._available = None

    def is_available(self) -> bool:
        if self._available is None:
            try:
                import spacy

                self._nlp = spacy.load("fr_core_news_lg")
                self._available = True
            except (ImportError, OSError):
                try:
                    import spacy

                    self._nlp = spacy.load("fr_core_news_sm")
                    self._available = True
                    logger.info("Using fr_core_news_sm (lg not available)")
                except (ImportError, OSError):
                    self._available = False
                    logger.warning("spaCy French model not available")
        return self._available

    def mine_arguments(self, text: str) -> Dict[str, List[str]]:
        """Extract claims and premises using spaCy Matcher patterns."""
        if not self.is_available():
            return {"claims": [text], "premises": []}

        from spacy.matcher import Matcher

        doc = self._nlp(text)
        claim_matcher = Matcher(self._nlp.vocab)
        for i, p in enumerate(_CLAIM_PATTERNS):
            claim_matcher.add(f"CLAIM_{i}", [p["PATTERN"]])

        premise_matcher = Matcher(self._nlp.vocab)
        for i, p in enumerate(_PREMISE_PATTERNS):
            premise_matcher.add(f"PREMISE_{i}", [p["PATTERN"]])

        claims, premises = [], []
        for sent in doc.sents:
            if claim_matcher(sent):
                claims.append(sent.text)
            elif premise_matcher(sent):
                premises.append(sent.text)

        if not claims and not premises:
            sents = list(doc.sents)
            if sents:
                claims.append(sents[0].text)
                premises.extend(s.text for s in sents[1:])
            else:
                claims.append(text)

        return {"claims": claims, "premises": premises}

    def detect(self, text: str) -> List[FallacyDetection]:
        """Detect fallacies using symbolic rules."""
        if not self.is_available():
            return []

        from spacy.matcher import Matcher

        doc = self._nlp(text)
        matcher = Matcher(self._nlp.vocab)
        for rule_key, rules in _SYMBOLIC_FALLACY_RULES.items():
            for i, rule in enumerate(rules):
                matcher.add(f"{rule_key}_{i}", [rule["PATTERN"]])

        results = []
        seen_types = set()
        for match_id, start, end in matcher(doc):
            rule_name = self._nlp.vocab.strings[match_id]
            base_key = "_".join(rule_name.split("_")[:-1])  # Remove suffix _0, _1
            span = doc[start:end]

            # Find the FALLACY_TYPE from our rules
            fallacy_type = rule_name
            for rules in _SYMBOLIC_FALLACY_RULES.get(base_key, []):
                fallacy_type = rules.get("FALLACY_TYPE", rule_name)
                break

            if fallacy_type not in seen_types:
                seen_types.add(fallacy_type)
                results.append(
                    FallacyDetection(
                        fallacy_type=fallacy_type,
                        confidence=1.0,
                        source="symbolic",
                        matched_rule=span.text,
                    )
                )

        return results


# ── Tier 2: NLI Zero-Shot Detection ─────────────────────────────────────


class NLIFallacyDetector:
    """Zero-shot fallacy classification via NLI (Natural Language Inference).

    Uses a multilingual NLI model (e.g., mDeBERTa-v3-base-xnli-multilingual)
    to classify text against fallacy labels without fine-tuning.
    Auto-downloads the model on first use (~600MB).
    """

    DEFAULT_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
    CONFIDENCE_THRESHOLD = 0.5

    def __init__(self, model_name: Optional[str] = None, threshold: float = 0.5):
        self._model_name = model_name or self.DEFAULT_MODEL
        self._classifier = None
        self._available = None
        self.threshold = threshold

    def is_available(self) -> bool:
        if self._available is None:
            try:
                from transformers import pipeline

                self._available = True
            except ImportError:
                self._available = False
                logger.warning("transformers not installed — NLI tier unavailable")
        return self._available

    def _get_classifier(self):
        if self._classifier is None:
            from transformers import pipeline

            logger.info(f"Loading NLI model: {self._model_name}")
            self._classifier = pipeline(
                "zero-shot-classification",
                model=self._model_name,
            )
            logger.info("NLI model loaded")
        return self._classifier

    def detect(self, text: str) -> List[FallacyDetection]:
        """Classify text against fallacy labels using NLI zero-shot."""
        if not self.is_available():
            return []

        try:
            classifier = self._get_classifier()
            hypothesis_template = "Ce texte contient un sophisme de type {}."
            result = classifier(
                text,
                candidate_labels=FALLACY_LABELS_FR,
                hypothesis_template=hypothesis_template,
                multi_label=True,
            )

            detections = []
            for label, score in zip(result["labels"], result["scores"]):
                if score >= self.threshold:
                    detections.append(
                        FallacyDetection(
                            fallacy_type=label,
                            confidence=round(score, 3),
                            source="nli",
                            description=f"NLI zero-shot ({self._model_name})",
                        )
                    )
            return detections

        except Exception as e:
            logger.error(f"NLI detection failed: {e}")
            return []


# ── Tier 1: LLM Zero-Shot Detection ─────────────────────────────────────


class LLMFallacyDetector:
    """Zero-shot fallacy detection via LLM prompt.

    Uses ServiceDiscovery to find the best available LLM provider
    and sends a structured prompt for fallacy analysis.
    """

    SYSTEM_PROMPT = """Tu es un expert en logique et argumentation. Analyse le texte fourni
et identifie les sophismes (fallacies) présents. Pour chaque sophisme détecté, donne:
- Le type de sophisme (utilise les noms français standardisés)
- Un score de confiance entre 0 et 1
- Une brève explication

Réponds UNIQUEMENT en JSON valide avec cette structure:
{"fallacies": [{"type": "...", "confidence": 0.XX, "explanation": "..."}]}

Si aucun sophisme n'est détecté, réponds: {"fallacies": []}"""

    def __init__(self, service_discovery=None):
        self._service_discovery = service_discovery
        self._available = None

    def is_available(self) -> bool:
        if self._available is None:
            if self._service_discovery is None:
                self._available = False
            else:
                try:
                    provider = self._service_discovery.get_best_provider("llm")
                    self._available = provider is not None
                except Exception:
                    self._available = False
        return self._available

    async def detect_async(self, text: str) -> List[FallacyDetection]:
        """Detect fallacies via LLM (async)."""
        if not self.is_available():
            return []

        try:
            import json

            provider = self._service_discovery.get_best_provider("llm")
            if provider is None:
                return []

            # Build prompt
            user_prompt = f"Analyse ce texte pour détecter les sophismes:\n\n{text}"

            # The actual LLM call depends on the provider type
            # For now, return empty — real integration needs ServiceDiscovery LLM client
            logger.info(f"LLM fallacy detection via provider: {provider.name}")
            return []

        except Exception as e:
            logger.error(f"LLM detection failed: {e}")
            return []

    def detect(self, text: str) -> List[FallacyDetection]:
        """Synchronous wrapper for detect_async."""
        if not self.is_available():
            return []
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return []  # Can't await in running loop — skip tier
            return loop.run_until_complete(self.detect_async(text))
        except Exception:
            return []


# ── Main Adapter ─────────────────────────────────────────────────────────


class FrenchFallacyAdapter(AbstractFallacyDetector):
    """3-tier French fallacy detection adapter.

    Combines symbolic rules, NLI zero-shot, and LLM zero-shot with
    automatic fallback. Results are merged using an ensemble strategy
    where symbolic matches (confidence=1.0) override neural/LLM scores.

    Register with CapabilityRegistry:
        registry.register_service(
            "french_fallacy_detector",
            FrenchFallacyAdapter,
            capabilities=["fallacy_detection", "neural_fallacy_detection",
                          "symbolic_fallacy_detection"],
        )
    """

    def __init__(
        self,
        enable_symbolic: bool = True,
        enable_nli: bool = True,
        enable_llm: bool = True,
        nli_model: Optional[str] = None,
        nli_threshold: float = 0.5,
        service_discovery=None,
    ):
        self._symbolic = SymbolicFallacyDetector() if enable_symbolic else None
        self._nli = (
            NLIFallacyDetector(model_name=nli_model, threshold=nli_threshold)
            if enable_nli
            else None
        )
        self._llm = (
            LLMFallacyDetector(service_discovery=service_discovery)
            if enable_llm
            else None
        )

    def is_available(self) -> bool:
        """At least one tier must be available."""
        return any(
            t is not None and t.is_available()
            for t in [self._symbolic, self._nli, self._llm]
        )

    def get_available_tiers(self) -> List[str]:
        """Return list of available tier names."""
        tiers = []
        if self._symbolic and self._symbolic.is_available():
            tiers.append("symbolic")
        if self._nli and self._nli.is_available():
            tiers.append("nli")
        if self._llm and self._llm.is_available():
            tiers.append("llm")
        return tiers

    def detect(self, text: str) -> dict:
        """Detect fallacies using all available tiers.

        Returns:
            Dict with keys: detected_fallacies, arguments, tiers_used,
            explanation, total_fallacies
        """
        result = FallacyAnalysisResult(text=text)

        # Mine arguments (symbolic tier provides this)
        if self._symbolic and self._symbolic.is_available():
            result.arguments = self._symbolic.mine_arguments(text)

        # Collect detections from all tiers
        all_detections: List[FallacyDetection] = []

        # Tier 3: Symbolic (fastest, always tried first)
        if self._symbolic and self._symbolic.is_available():
            symbolic_results = self._symbolic.detect(text)
            all_detections.extend(symbolic_results)
            if symbolic_results:
                result.tiers_used.append("symbolic")

        # Tier 2: NLI zero-shot
        if self._nli and self._nli.is_available():
            nli_results = self._nli.detect(text)
            all_detections.extend(nli_results)
            if nli_results:
                result.tiers_used.append("nli")

        # Tier 1: LLM zero-shot
        if self._llm and self._llm.is_available():
            llm_results = self._llm.detect(text)
            all_detections.extend(llm_results)
            if llm_results:
                result.tiers_used.append("llm")

        # Ensemble: merge detections by fallacy type
        merged: Dict[str, FallacyDetection] = {}
        for d in all_detections:
            if d.fallacy_type in merged:
                existing = merged[d.fallacy_type]
                # Symbolic (confidence=1.0) takes priority
                if d.confidence > existing.confidence:
                    d.source = f"{existing.source}+{d.source}"
                    d.matched_rule = d.matched_rule or existing.matched_rule
                    merged[d.fallacy_type] = d
                else:
                    existing.source = f"{existing.source}+{d.source}"
                    existing.matched_rule = existing.matched_rule or d.matched_rule
            else:
                merged[d.fallacy_type] = d

        result.fallacies = list(merged.values())

        # Generate explanation
        if result.fallacies:
            lines = [
                f"Analyse du texte ({len(result.fallacies)} sophisme(s) détecté(s)):"
            ]
            for f in result.fallacies:
                lines.append(
                    f"  - {f.fallacy_type} (confiance: {f.confidence:.2f}, source: {f.source})"
                )
                if f.matched_rule:
                    lines.append(f"    Règle: {f.matched_rule}")
            result.explanation = "\n".join(lines)
        else:
            result.explanation = "Aucun sophisme détecté dans le texte."

        if not result.tiers_used:
            result.tiers_used.append("none")

        return result.to_dict()
