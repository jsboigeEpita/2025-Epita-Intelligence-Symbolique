"""
French Fallacy Detection Adapter — 3-tier hybrid detection.

Wraps and extends the student 2.3.2-detection-sophismes project.
Provides fallacy detection through 3 tiers with automatic fallback:

  Tier 1: LLM zero-shot (via OpenAI-compatible API — primary detector)
  Tier 2: NLI zero-shot (mDeBERTa or similar, auto-downloaded ~600MB)
  Tier 3: Symbolic rules (spaCy Matcher patterns, always available)

Dependencies:
  - Tier 3 (symbolic): spacy + fr_core_news_lg (or sm)
  - Tier 2 (NLI): transformers + torch
  - Tier 1 (LLM): OPENAI_API_KEY env var + openai package

CamemBERT Tier 2.5 was deprecated in #297 (model never deployed).
All tiers degrade gracefully if their dependencies are missing.

Integration from student project 2.3.2-detection-sophismes (GitHub #44).
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from argumentation_analysis.core.interfaces.fallacy_detector import (
    AbstractFallacyDetector,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

# Legacy 13-label list kept as absolute fallback
_FALLACY_LABELS_LEGACY = [
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

_TAXONOMY_CSV = Path(__file__).resolve().parent.parent / "data" / "taxonomy_medium.csv"
_TAXONOMY_FULL_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "taxonomy_full.csv"
)

# Maps taxonomy text_fr label → PK for downstream hierarchical descent
_TAXONOMY_LABEL_TO_PK: Dict[str, int] = {}

# Hierarchical taxonomy structure loaded from taxonomy_full.csv
# Each node: {"pk": int, "label": str, "depth": int, "children": [...]}
_TAXONOMY_HIERARCHY: Dict[str, Any] = {}

# Maps PK → node dict for quick lookup
_TAXONOMY_PK_TO_NODE: Dict[int, Dict[str, Any]] = {}


def _load_taxonomy_labels() -> List[str]:
    """Load fallacy labels from taxonomy_medium.csv (depth 1+2).

    Returns 28 labels covering 7 families and 21 sub-families instead of
    the original 13 hardcoded labels. Falls back to legacy list if the
    CSV is missing or unreadable.
    """
    try:
        with open(_TAXONOMY_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            labels = []
            for row in reader:
                depth = int(row.get("depth", 0))
                if depth < 1:
                    continue  # skip root
                text_fr = row.get("text_fr", "").strip()
                famille = row.get("Famille", "").strip()
                pk = int(row.get("PK", 0))
                if text_fr:
                    # Include family context for depth-2 sub-families
                    if depth == 2 and famille and famille != text_fr:
                        label = f"{text_fr} ({famille})"
                    else:
                        label = text_fr
                    labels.append(label)
                    _TAXONOMY_LABEL_TO_PK[label] = pk
            if labels:
                logger.info(
                    f"Loaded {len(labels)} fallacy labels from taxonomy_medium.csv"
                )
                return labels
    except Exception as e:
        logger.warning(f"Could not load taxonomy_medium.csv: {e}")

    logger.info("Using legacy 13-label fallacy list as fallback")
    return list(_FALLACY_LABELS_LEGACY)


def _load_taxonomy_hierarchy() -> Dict[str, Any]:
    """Load hierarchical taxonomy from taxonomy_full.csv.

    Builds a tree structure using the ``path`` column (e.g. "1.1.3")
    to determine parent-child relationships.  Only the tree structure
    is kept in memory -- the flat 28-label list used by default NLI
    classification is NOT affected.

    Returns the root node dict, or an empty dict on failure.
    Also populates ``_TAXONOMY_PK_TO_NODE`` for quick PK lookups.
    """
    if _TAXONOMY_HIERARCHY:
        return _TAXONOMY_HIERARCHY

    try:
        with open(_TAXONOMY_FULL_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Collect all rows, keyed by their path
            nodes_by_path: Dict[str, Dict[str, Any]] = {}
            for row in reader:
                pk = int(row.get("PK", 0))
                depth = int(row.get("depth", 0))
                text_fr = row.get("text_fr", "").strip()
                path = row.get("path", "").strip()
                if not text_fr or not path:
                    continue
                node = {
                    "pk": pk,
                    "label": text_fr,
                    "depth": depth,
                    "path": path,
                    "children": [],
                }
                nodes_by_path[path] = node
                _TAXONOMY_PK_TO_NODE[pk] = node

            # Build parent-child links using path hierarchy
            # Path "1.1.3" is a child of "1.1"; path "1" is child of "0"
            for path, node in nodes_by_path.items():
                if path == "0":
                    continue  # root has no parent
                if "." in path:
                    parent_path = path.rsplit(".", 1)[0]
                else:
                    # Depth-1 nodes (path "1", "2", ...) are children of root
                    parent_path = "0"
                parent = nodes_by_path.get(parent_path)
                if parent is not None:
                    parent["children"].append(node)

            root = nodes_by_path.get("0")
            if root:
                _TAXONOMY_HIERARCHY.update(root)
                family_count = len(root.get("children", []))
                total = len(nodes_by_path)
                logger.info(
                    f"Loaded taxonomy hierarchy: {total} nodes, "
                    f"{family_count} families from taxonomy_full.csv"
                )
                return _TAXONOMY_HIERARCHY

    except Exception as e:
        logger.warning(f"Could not load taxonomy_full.csv hierarchy: {e}")

    return {}


FALLACY_LABELS_FR = _load_taxonomy_labels()

# Lazy-load hierarchy on first use (not at import time to keep startup fast)
# Call _load_taxonomy_hierarchy() when needed.

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
    taxonomy_pk: Optional[int] = None  # PK in taxonomy CSV for hierarchical descent


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
                    "taxonomy_pk": f.taxonomy_pk,
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

    def detect(
        self, text: str, *, hierarchical: bool = False
    ) -> List[FallacyDetection]:
        """Classify text against fallacy labels using NLI zero-shot.

        Args:
            text: Text to analyse.
            hierarchical: When *True*, use 2-stage hierarchical
                classification (family then sub-family) instead of
                flat 28-label matching.  Requires taxonomy_full.csv.
        """
        if not self.is_available():
            return []

        if hierarchical:
            return self._nli_hierarchical_classify(text)

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
                    taxonomy_pk = _TAXONOMY_LABEL_TO_PK.get(label)
                    desc = f"NLI zero-shot ({self._model_name})"
                    if taxonomy_pk is not None:
                        desc += f" [taxonomy PK={taxonomy_pk}]"
                    detections.append(
                        FallacyDetection(
                            fallacy_type=label,
                            confidence=round(score, 3),
                            source="nli",
                            description=desc,
                            taxonomy_pk=taxonomy_pk,
                        )
                    )
            return detections

        except Exception as e:
            logger.error(f"NLI detection failed: {e}")
            return []

    # ── Hierarchical 2-stage NLI classification ────────────────────────

    # Threshold for Stage 1: minimum confidence on a family to drill down
    HIERARCHICAL_STAGE1_THRESHOLD = 0.3

    def _nli_hierarchical_classify(self, text: str) -> List[FallacyDetection]:
        """2-stage hierarchical NLI classification.

        Stage 1: classify against the 7 depth-1 families.
        Stage 2: for each family above *HIERARCHICAL_STAGE1_THRESHOLD*,
                 classify against its depth-2 (and optionally depth-3)
                 children to get the most specific match.

        Falls back to flat classification if hierarchy is unavailable.
        """
        hierarchy = _load_taxonomy_hierarchy()
        if not hierarchy or not hierarchy.get("children"):
            logger.info(
                "Taxonomy hierarchy not available — "
                "falling back to flat NLI classification"
            )
            return self.detect(text, hierarchical=False)

        try:
            classifier = self._get_classifier()
            hypothesis_template = "Ce texte contient un sophisme de type {}."

            # ── Stage 1: classify against depth-1 families ────────────
            families = hierarchy["children"]
            family_labels = [f["label"] for f in families]

            stage1_result = classifier(
                text,
                candidate_labels=family_labels,
                hypothesis_template=hypothesis_template,
                multi_label=True,
            )

            detections: List[FallacyDetection] = []

            for label, score in zip(stage1_result["labels"], stage1_result["scores"]):
                if score < self.HIERARCHICAL_STAGE1_THRESHOLD:
                    continue

                # Find the family node
                family_node = None
                for f in families:
                    if f["label"] == label:
                        family_node = f
                        break

                if family_node is None or not family_node.get("children"):
                    # No children to drill into — report the family itself
                    detections.append(
                        FallacyDetection(
                            fallacy_type=label,
                            confidence=round(score, 3),
                            source="nli_hierarchical",
                            description=(
                                f"NLI hierarchical stage-1 " f"({self._model_name})"
                            ),
                            taxonomy_pk=family_node["pk"] if family_node else None,
                        )
                    )
                    continue

                # ── Stage 2: classify against children ────────────────
                # Collect depth-2 children, and optionally depth-3
                child_labels_map: Dict[str, Dict[str, Any]] = {}
                for child in family_node["children"]:
                    child_labels_map[child["label"]] = child
                    # Also include depth-3 grandchildren for finer grain
                    for grandchild in child.get("children", []):
                        child_labels_map[grandchild["label"]] = grandchild

                if not child_labels_map:
                    detections.append(
                        FallacyDetection(
                            fallacy_type=label,
                            confidence=round(score, 3),
                            source="nli_hierarchical",
                            description=(
                                f"NLI hierarchical stage-1 only "
                                f"({self._model_name})"
                            ),
                            taxonomy_pk=family_node["pk"],
                        )
                    )
                    continue

                child_labels = list(child_labels_map.keys())
                stage2_result = classifier(
                    text,
                    candidate_labels=child_labels,
                    hypothesis_template=hypothesis_template,
                    multi_label=False,
                )

                best_child_label = stage2_result["labels"][0]
                best_child_score = stage2_result["scores"][0]
                best_child_node = child_labels_map[best_child_label]

                # Use the finer result if confident enough; else keep family
                if best_child_score >= self.threshold:
                    # Combined confidence: family_score * child_score
                    combined = round(score * best_child_score, 3)
                    detections.append(
                        FallacyDetection(
                            fallacy_type=best_child_label,
                            confidence=combined,
                            source="nli_hierarchical",
                            description=(
                                f"NLI hierarchical stage-2: "
                                f"{label} → {best_child_label} "
                                f"(s1={score:.3f}, s2={best_child_score:.3f}) "
                                f"({self._model_name})"
                            ),
                            taxonomy_pk=best_child_node["pk"],
                        )
                    )
                else:
                    # Stage 2 not confident — report family level
                    detections.append(
                        FallacyDetection(
                            fallacy_type=label,
                            confidence=round(score, 3),
                            source="nli_hierarchical",
                            description=(
                                f"NLI hierarchical stage-1 only "
                                f"(stage-2 best={best_child_score:.3f} "
                                f"< threshold={self.threshold}) "
                                f"({self._model_name})"
                            ),
                            taxonomy_pk=family_node["pk"],
                        )
                    )

            return detections

        except Exception as e:
            logger.error(f"NLI hierarchical detection failed: {e}")
            return []


# ── Tier 2.5: CamemBERT Fine-Tuned Detection (#169) ─────────────────────

# Maps CamemBERT's 13 output labels → standardized French labels
_CAMEMBERT_LABEL_MAPPING = {
    0: "Attaque personnelle (Ad Hominem)",
    1: "Appel à la popularité (Ad Populum)",
    2: "Appel à l'émotion (Appeal to Emotion)",
    3: "Fallacy de crédibilité",
    4: "Fallacy d'extension",
    5: "Fallacy de logique",
    6: "Généralisation hâtive (Hasty Generalization)",
    7: "Fausse causalité (False Cause)",
    8: "Faux dilemme (False Dilemma)",
    9: "Intentionnel",
    10: "Raisonnement circulaire (Circular Reasoning)",
    11: "Sophisme de pertinence",
    12: "Équivoque (Equivocation)",
}


class CamemBERTFallacyDetector:
    """Fine-tuned CamemBERT for 13-category French fallacy classification.

    Uses the model trained by student project 2.3.2 (Hamard) on a French
    fallacy dataset. Gracefully degrades if the model or dependencies are
    not available.

    The model can be loaded from:
    - A local directory (fine_tuned_camembert/)
    - The student project directory (2.3.2-detection-sophismes/fine_tuned_camembert/)

    Integration: Issue #169.
    """

    # Default model search paths (relative to project root)
    _MODEL_SEARCH_PATHS = [
        "fine_tuned_camembert",
        "2.3.2-detection-sophismes/fine_tuned_camembert",
        "models/camembert_fallacy",
    ]

    def __init__(
        self,
        model_path: Optional[str] = None,
        threshold: float = 0.3,
        max_length: int = 128,
    ):
        self._model_path = model_path
        self._threshold = threshold
        self._max_length = max_length
        self._tokenizer = None
        self._model = None
        self._available = None

    def _find_model_path(self) -> Optional[str]:
        """Search for the fine-tuned model in known locations."""
        if self._model_path:
            p = Path(self._model_path)
            if p.exists() and (p / "config.json").exists():
                return str(p)
            return None

        # Search in known locations relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        for rel_path in self._MODEL_SEARCH_PATHS:
            candidate = project_root / rel_path
            if candidate.exists() and (candidate / "config.json").exists():
                logger.info(f"Found CamemBERT model at: {candidate}")
                return str(candidate)
        return None

    def is_available(self) -> bool:
        """Check if fine-tuned model exists and dependencies are installed."""
        if self._available is not None:
            return self._available

        try:
            import torch  # noqa: F401
            from transformers import (  # noqa: F401
                CamembertTokenizer,
                CamembertForSequenceClassification,
            )
        except ImportError:
            logger.debug("CamemBERT dependencies not available (torch/transformers)")
            self._available = False
            return False

        model_path = self._find_model_path()
        if model_path is None:
            logger.info(
                "CamemBERT fine-tuned model not found. "
                "Tier 2.5 will be skipped. "
                "To enable: place model in fine_tuned_camembert/ or "
                "2.3.2-detection-sophismes/fine_tuned_camembert/"
            )
            self._available = False
            return False

        try:
            from transformers import (
                CamembertTokenizer,
                CamembertForSequenceClassification,
            )

            self._tokenizer = CamembertTokenizer.from_pretrained(model_path)
            self._model = CamembertForSequenceClassification.from_pretrained(model_path)
            self._model.eval()
            self._available = True
            logger.info(f"CamemBERT fallacy detector loaded from {model_path}")
        except Exception as e:
            logger.warning(f"Failed to load CamemBERT model: {e}")
            self._available = False

        return self._available

    def detect(self, text: str) -> List[FallacyDetection]:
        """Classify text using fine-tuned CamemBERT.

        Returns at most one detection (the highest-confidence class).
        """
        if not self.is_available():
            return []

        try:
            import torch

            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self._max_length,
                padding=True,
            )

            with torch.no_grad():
                outputs = self._model(**inputs)

            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
            predicted_class_id = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][predicted_class_id].item()

            if confidence < self._threshold:
                return []

            fallacy_type = _CAMEMBERT_LABEL_MAPPING.get(
                predicted_class_id, f"unknown_class_{predicted_class_id}"
            )
            taxonomy_pk = _TAXONOMY_LABEL_TO_PK.get(fallacy_type)

            return [
                FallacyDetection(
                    fallacy_type=fallacy_type,
                    confidence=round(confidence, 3),
                    source="camembert",
                    description=(
                        f"CamemBERT fine-tuned classifier "
                        f"[class={predicted_class_id}, conf={confidence:.3f}]"
                    ),
                    taxonomy_pk=taxonomy_pk,
                )
            ]

        except Exception as e:
            logger.error(f"CamemBERT detection failed: {e}")
            return []

    def get_status_details(self) -> Dict[str, Any]:
        """Return detector status details."""
        return {
            "detector_type": "CamemBERTFallacyDetector",
            "available": self.is_available(),
            "model_path": self._find_model_path(),
            "threshold": self._threshold,
            "num_labels": len(_CAMEMBERT_LABEL_MAPPING),
        }


# ── Tier 1.5: Self-Hosted LLM Fallacy Detection (#297) ───────────────────


class SelfHostedLLMFallacyDetector:
    """Fallacy detection via self-hosted LLM with function calling.

    Uses an OpenAI-compatible endpoint (text-generation-webui / vLLM)
    to perform structured fallacy classification. Replaces CamemBERT
    (Tier 2.5, dead) and NLI (Tier 2, DLL crash on Windows).

    Requires: SELF_HOSTED_LLM_ENDPOINT, SELF_HOSTED_LLM_API_KEY,
              SELF_HOSTED_LLM_MODEL env vars.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        import os

        self._endpoint = endpoint or os.environ.get("SELF_HOSTED_LLM_ENDPOINT", "")
        self._api_key = api_key or os.environ.get(
            "SELF_HOSTED_LLM_API_KEY", "not-needed"
        )
        self._model = model or os.environ.get("SELF_HOSTED_LLM_MODEL", "")
        self._timeout = timeout
        self._available = None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = bool(self._endpoint and self._model)
        return self._available

    async def detect_async(self, text: str) -> List[FallacyDetection]:
        """Detect fallacies via self-hosted LLM with structured output."""
        if not self.is_available():
            return []

        import json
        import httpx

        prompt = (
            "Tu es un expert en logique et argumentation. "
            "Analyse le texte suivant et identifie les sophismes.\n\n"
            "Pour chaque sophisme détecté, donne le type exact parmi:\n"
            + "\n".join(f"- {label}" for label in FALLACY_LABELS_FR[:15])
            + "\n\nRéponds UNIQUEMENT en JSON:\n"
            '{"fallacies": [{"type": "...", "confidence": 0.XX, "explanation": "..."}]}\n'
            'Si aucun sophisme: {"fallacies": []}\n\n'
            f"Texte à analyser:\n{text}"
        )

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "Tu es un expert en logique et argumentation. Réponds en JSON uniquement.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._endpoint}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            start = content.find("{")
            end = content.rfind("}") + 1
            if start < 0 or end <= start:
                return []

            parsed = json.loads(content[start:end])
            fallacies = parsed.get("fallacies", [])

            detections = []
            for f in fallacies:
                if not isinstance(f, dict):
                    continue
                ftype = f.get("type", "")
                conf = float(f.get("confidence", 0.5))
                explanation = f.get("explanation", "")
                taxonomy_pk = _TAXONOMY_LABEL_TO_PK.get(ftype)
                detections.append(
                    FallacyDetection(
                        fallacy_type=ftype,
                        confidence=conf,
                        source="self_hosted_llm",
                        description=explanation,
                        taxonomy_pk=taxonomy_pk,
                    )
                )
            return detections

        except Exception as e:
            logger.warning("Self-hosted LLM fallacy detection failed: %s", e)
            return []

    def detect(self, text: str) -> List[FallacyDetection]:
        """Synchronous wrapper for detect_async."""
        if not self.is_available():
            return []
        try:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.detect_async(text))
                    return future.result(timeout=self._timeout)
            else:
                return asyncio.run(self.detect_async(text))
        except Exception as e:
            logger.warning("Self-hosted LLM sync detect failed: %s", e)
            return []


# ── Tier 1: LLM Zero-Shot Detection ─────────────────────────────────────


class LLMFallacyDetector:
    """Zero-shot fallacy detection via LLM (OpenAI-compatible API).

    Calls the same OpenAI-compatible endpoint used by the pipeline
    (via OPENAI_API_KEY / OPENAI_BASE_URL env vars, or self-hosted vLLM).
    Returns structured JSON with detected fallacies.

    Replaces the defunct CamemBERT Tier 2.5 and the heavy NLI Tier 2
    with a single, more capable inference path (#297).
    """

    SYSTEM_PROMPT = (
        "Tu es un expert en logique et argumentation. Analyse le texte fourni "
        "et identifie les sophismes (fallacies) presents. Pour chaque sophisme "
        "detecte, donne:\n"
        "- Le type de sophisme (utilise les noms francais standardises)\n"
        "- Un score de confiance entre 0 et 1\n"
        "- Une breve explication\n"
        "- Le passage du texte concerne\n\n"
        "Reponds UNIQUEMENT en JSON valide avec cette structure:\n"
        '{"fallacies": [{"type": "...", "confidence": 0.XX, '
        '"explanation": "...", "target_text": "..."}]}\n\n'
        'Si aucun sophisme n\'est detecte, reponds: {"fallacies": []}\n\n'
        "Types de sophismes connus:\n"
        "- Attaque personnelle (Ad Hominem)\n"
        "- Appel a la popularite (Ad Populum)\n"
        "- Appel a l'emotion (Appeal to Emotion)\n"
        "- Generalisation hative (Hasty Generalization)\n"
        "- Fausse causalite (False Cause)\n"
        "- Faux dilemme (False Dilemma)\n"
        "- Raisonnement circulaire (Circular Reasoning)\n"
        "- Pente glissante (Slippery Slope)\n"
        "- Argument d'autorite (Appeal to Authority)\n"
        "- Appel a la tradition (Appeal to Tradition)\n"
        "- Equivoque (Equivocation)\n"
        "- Homme de paille (Straw Man)\n"
        "- Sophisme de pertinence"
    )

    def __init__(self, service_discovery=None, confidence_threshold: float = 0.4):
        self._service_discovery = service_discovery
        self._available = None
        self._threshold = confidence_threshold

    def _get_openai_client(self):
        """Get OpenAI-compatible client and model, same as unified_pipeline."""
        import os

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None, None
        try:
            from openai import AsyncOpenAI

            base_url = os.environ.get("OPENAI_BASE_URL")
            client = AsyncOpenAI(
                api_key=api_key,
                **({"base_url": base_url} if base_url else {}),
            )
            model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")
            return client, model
        except ImportError:
            return None, None

    def is_available(self) -> bool:
        if self._available is None:
            client, _ = self._get_openai_client()
            self._available = client is not None
        return self._available

    async def detect_async(self, text: str) -> List[FallacyDetection]:
        """Detect fallacies via LLM (async)."""
        client, model = self._get_openai_client()
        if client is None:
            return []

        try:
            import json as _json

            user_prompt = (
                f"Analyse ce texte pour detecter les sophismes:\n\n{text[:3000]}"
            )

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1024,
            )

            raw = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(l for l in lines if not l.startswith("```"))

            data = _json.loads(raw)
            fallacies_data = data.get("fallacies", [])

            detections = []
            for f in fallacies_data:
                if not isinstance(f, dict):
                    continue
                ftype = f.get("type", "unknown")
                conf = float(f.get("confidence", 0.5))
                if conf < self._threshold:
                    continue
                explanation = f.get("explanation", "")
                target = f.get("target_text", "")
                taxonomy_pk = _TAXONOMY_LABEL_TO_PK.get(ftype)
                detections.append(
                    FallacyDetection(
                        fallacy_type=ftype,
                        confidence=round(conf, 3),
                        source="llm",
                        description=explanation,
                        matched_rule=target[:200] if target else None,
                        taxonomy_pk=taxonomy_pk,
                    )
                )

            logger.info(
                f"LLM fallacy detection: {len(detections)} fallacies "
                f"from {len(fallacies_data)} candidates (model={model})"
            )
            return detections

        except Exception as e:
            logger.error(f"LLM detection failed: {e}")
            return []

    def detect(self, text: str) -> List[FallacyDetection]:
        """Synchronous wrapper for detect_async."""
        if not self.is_available():
            return []
        try:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                # Already in async context — can't nest; skip
                return []
            except RuntimeError:
                pass
            return asyncio.run(self.detect_async(text))
        except Exception:
            return []


# ── Main Adapter ─────────────────────────────────────────────────────────


class FrenchFallacyAdapter(AbstractFallacyDetector):
    """Multi-tier French fallacy detection adapter.

    Combines symbolic rules, self-hosted LLM, and remote LLM with
    automatic fallback. Deprecated tiers (CamemBERT, NLI) are kept for
    backwards compat but shadowed when self-hosted LLM is enabled.

    Tier hierarchy (fastest → most capable):
      Tier 3:   Symbolic (spaCy Matcher, always available)
      Tier 2:   NLI zero-shot (deprecated, shadowed by self-hosted LLM)
      Tier 1.5: Self-hosted LLM (vLLM/text-generation-webui, #297)
      Tier 1:   Remote LLM (OpenAI via ServiceDiscovery)
      Tier 0.5: CamemBERT fine-tuned (deprecated, model never deployed)

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
        enable_camembert: bool = False,  # Deprecated (#297): model never deployed
        enable_nli: bool = True,
        enable_llm: bool = True,
        enable_self_hosted_llm: bool = True,
        camembert_model_path: Optional[str] = None,
        camembert_threshold: float = 0.3,
        nli_model: Optional[str] = None,
        nli_threshold: float = 0.5,
        self_hosted_endpoint: Optional[str] = None,
        self_hosted_api_key: Optional[str] = None,
        self_hosted_model: Optional[str] = None,
        service_discovery=None,
        llm_confidence_threshold: float = 0.4,
        nli_hierarchical: bool = False,
    ):
        self._symbolic = SymbolicFallacyDetector() if enable_symbolic else None
        # Self-hosted LLM replaces CamemBERT + NLI (#297)
        self._self_hosted_llm = (
            SelfHostedLLMFallacyDetector(
                endpoint=self_hosted_endpoint,
                api_key=self_hosted_api_key,
                model=self_hosted_model,
            )
            if enable_self_hosted_llm
            else None
        )
        # Deprecated tiers — kept for backwards compat but not enabled by default
        self._camembert = (
            CamemBERTFallacyDetector(
                model_path=camembert_model_path,
                threshold=camembert_threshold,
            )
            if enable_camembert and not enable_self_hosted_llm
            else None
        )
        self._nli = (
            NLIFallacyDetector(model_name=nli_model, threshold=nli_threshold)
            if enable_nli and not enable_self_hosted_llm
            else None
        )
        self._llm = (
            LLMFallacyDetector(
                service_discovery=service_discovery,
                confidence_threshold=llm_confidence_threshold,
            )
            if enable_llm
            else None
        )
        self._nli_hierarchical = nli_hierarchical

    def is_available(self) -> bool:
        """At least one tier must be available."""
        return any(
            t is not None and t.is_available()
            for t in [
                self._symbolic,
                self._self_hosted_llm,
                self._camembert,
                self._nli,
                self._llm,
            ]
        )

    def get_available_tiers(self) -> List[str]:
        """Return list of available tier names."""
        tiers = []
        if self._symbolic and self._symbolic.is_available():
            tiers.append("symbolic")
        if self._self_hosted_llm and self._self_hosted_llm.is_available():
            tiers.append("self_hosted_llm")
        if self._camembert and self._camembert.is_available():
            tiers.append("camembert")
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

        # Tier 2: Symbolic (fastest, always tried first)
        if self._symbolic and self._symbolic.is_available():
            symbolic_results = self._symbolic.detect(text)
            all_detections.extend(symbolic_results)
            if symbolic_results:
                result.tiers_used.append("symbolic")

        # Tier 1: Self-hosted LLM (#297)
        if self._self_hosted_llm and self._self_hosted_llm.is_available():
            self_hosted_results = self._self_hosted_llm.detect(text)
            all_detections.extend(self_hosted_results)
            if self_hosted_results:
                result.tiers_used.append("self_hosted_llm")

        # Tier 1.5: CamemBERT fine-tuned (#169, deprecated)
        if self._camembert and self._camembert.is_available():
            camembert_results = self._camembert.detect(text)
            all_detections.extend(camembert_results)
            if camembert_results:
                result.tiers_used.append("camembert")

        # Tier 2: NLI zero-shot (deprecated, shadowed by self-hosted LLM)
        if self._nli and self._nli.is_available():
            nli_results = self._nli.detect(text, hierarchical=self._nli_hierarchical)
            all_detections.extend(nli_results)
            if nli_results:
                tier_name = "nli_hierarchical" if self._nli_hierarchical else "nli"
                result.tiers_used.append(tier_name)

        # Tier 0: Remote LLM zero-shot
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
