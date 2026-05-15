"""PL Formula Sanitizer for Tweety-compatible syntax (#537).

Sits between LLM output and TweetyBridge.parse_pl_formula(). Handles:
- Verbose proposition names (NL fragments) → atomic symbols (p, q, r, ...)
- Syntax validation against Tweety PL grammar before JPype submission
- Graceful fallback: log warning and skip invalid formulas instead of raising
- Symbol mapping storage for round-trip interpretation

Tweety PL BNF (simplified):
    FORMULA ::= PROPOSITION | "(" FORMULA ")" | FORMULA "=>" FORMULA
              | FORMULA "||" FORMULA | FORMULA "&&" FORMULA
              | FORMULA "<=>" FORMULA | "!" FORMULA
    PROPOSITION ::= [a-zA-Z_][a-zA-Z0-9_]*
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Tweety PL operators (after normalization)
_TWEETY_OPERATORS = frozenset({"=>", "<=>", "&", "|", "!"})
_PARENS = frozenset({"(", ")"})
_SPECIAL_TOKENS = frozenset({"=>", "<=>", "&", "|", "!", "(", ")", ""})

# Valid proposition name: starts with letter/underscore, followed by alphanumeric/underscore
_PROP_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Atomic formula: single valid proposition
_ATOMIC_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+$")

# Pattern to detect NL-like tokens (too long, spaces, special chars, mixed language)
_NL_TOKEN_RE = re.compile(
    r"["
    r"\s"          # whitespace
    r"'\"`"        # quotes
    r",;:!?"       # punctuation (inside tokens)
    r"(){}[\]"     # brackets (inside tokens)
    r"@#$%^*=+"    # math/special
    r"<>/"         # angle brackets, slash
    r"\\"
    r"]"
)


@dataclass
class SanitizationResult:
    """Result of sanitizing a batch of PL formulas."""

    sanitized_formulas: List[str] = field(default_factory=list)
    symbol_mapping: Dict[str, str] = field(default_factory=dict)
    skipped_formulas: List[Tuple[str, str]] = field(default_factory=list)
    total_input: int = 0
    total_sanitized: int = 0


class PLFormulaSanitizer:
    """Sanitizes PL formulas for Tweety compatibility.

    Usage:
        sanitizer = PLFormulaSanitizer()
        result = sanitizer.sanitize_batch(["rain && (rain => wet)", "verbose NL claim"])
        for f in result.sanitized_formulas:
            print(f)  # "p && (p => q)"
        print(result.symbol_mapping)  # {"p": "rain", "q": "wet"}
    """

    def __init__(self, max_prop_length: int = 30):
        self._max_prop_length = max_prop_length
        self._symbol_counter = 0
        self._label_to_symbol: Dict[str, str] = {}

    def _next_symbol(self) -> str:
        """Generate the next atomic symbol: p, q, r, s, t, u, v, w, x, y, z, p2, q2, ..."""
        idx = self._symbol_counter
        # 11 letters: p(0), q(1), r(2), s(3), t(4), u(5), v(6), w(7), x(8), y(9), z(10)
        base = idx % 11
        round_num = idx // 11
        letter = chr(ord("p") + base)
        symbol = f"{letter}{round_num + 1}" if round_num > 0 else letter
        self._symbol_counter += 1
        return symbol

    def _is_nl_like(self, token: str) -> bool:
        """Check if a token looks like NL text rather than a proposition name."""
        if len(token) > self._max_prop_length:
            return True
        if _NL_TOKEN_RE.search(token):
            return True
        # Mixed language with accented chars
        if re.search(r"[àâäéèêëïîôùûüÿçœæÀÂÄÉÈÊËÏÎÔÙÛÜŸÇŒÆ]", token):
            return True
        return False

    def _extract_propositions(self, formula: str) -> List[str]:
        """Extract proposition tokens from a normalized formula string."""
        tokens = formula.split()
        props = []
        for t in tokens:
            if t in _SPECIAL_TOKENS:
                continue
            # Strip surrounding parens from grouped props (rare but possible)
            clean = t.strip("()")
            if clean and clean not in _SPECIAL_TOKENS:
                props.append(clean)
        return props

    def _map_label(self, label: str) -> str:
        """Map a proposition label to an atomic symbol. Reuses existing mappings."""
        label_lower = label.lower()
        if label_lower in self._label_to_symbol:
            return self._label_to_symbol[label_lower]
        symbol = self._next_symbol()
        self._label_to_symbol[label_lower] = symbol
        return symbol

    def _replace_props_in_formula(self, formula: str, mapping: Dict[str, str]) -> str:
        """Replace proposition names in formula using the provided mapping."""
        tokens = formula.split()
        result = []
        for t in tokens:
            if t in _SPECIAL_TOKENS:
                result.append(t)
            elif t.lower() in mapping:
                result.append(mapping[t.lower()])
            else:
                result.append(t)
        return " ".join(result)

    @staticmethod
    def _check_balanced_parens(formula: str) -> bool:
        """Check that parentheses are balanced."""
        depth = 0
        for ch in formula:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth < 0:
                return False
        return depth == 0

    @staticmethod
    def _check_valid_tokens(formula: str) -> bool:
        """Check that all tokens are valid proposition names or operators."""
        tokens = formula.split()
        for t in tokens:
            if t in _SPECIAL_TOKENS:
                continue
            if not _PROP_RE.match(t):
                return False
        return True

    @staticmethod
    def _check_not_empty(formula: str) -> bool:
        """Check that formula contains at least one proposition."""
        tokens = formula.split()
        return any(t not in _SPECIAL_TOKENS for t in tokens)

    def _has_nl_props(self, formula: str) -> bool:
        """Check if any proposition in the formula looks like NL text."""
        props = self._extract_propositions(formula)
        return any(self._is_nl_like(p) for p in props)

    def _normalize_operators(self, formula: str) -> str:
        """Normalize operator variants to Tweety-compatible forms."""
        f = formula
        f = f.replace("&&", " & ")
        f = f.replace("||", " | ")
        f = f.replace("<->", " <=> ")
        f = f.replace("->", " => ")
        f = f.replace(" NOT ", " ! ").replace(" Not ", " ! ")
        f = re.sub(r"\s*(=>|<=>|&|\||!|\(|\))\s*", r" \1 ", f)
        # Sanitize proposition names
        tokens = f.split(" ")
        sanitized = []
        for t in tokens:
            if t in _SPECIAL_TOKENS:
                sanitized.append(t)
            else:
                sanitized.append(re.sub(r"[^a-zA-Z0-9_]", "_", t))
        return " ".join(sanitized).strip()

    def validate_formula(self, formula: str) -> Tuple[bool, str]:
        """Validate a single formula against Tweety PL grammar rules.

        Returns:
            (is_valid, reason) tuple.
        """
        if not formula or not formula.strip():
            return False, "empty formula"

        f = formula.strip()

        if not self._check_balanced_parens(f):
            return False, "unbalanced parentheses"

        if not self._check_not_empty(f):
            return False, "no propositions"

        if not self._check_valid_tokens(f):
            bad = [t for t in f.split() if t not in _SPECIAL_TOKENS and not _PROP_RE.match(t)]
            return False, f"invalid tokens: {bad}"

        return True, "valid"

    def sanitize_formula(self, formula: str) -> Optional[str]:
        """Sanitize a single formula: normalize, map NL props, validate.

        Returns:
            Sanitized formula string, or None if the formula is irrecoverable.
        """
        if not formula or not isinstance(formula, str):
            return None

        f = formula.strip()

        # Strip markdown artifacts
        if f.startswith("```") or f.endswith("```") or "```" in f:
            return None

        # Normalize operators and sanitize prop names
        normalized = self._normalize_operators(f)

        # Map NL-like proposition names to atomic symbols
        if self._has_nl_props(normalized):
            props = self._extract_propositions(normalized)
            local_mapping: Dict[str, str] = {}
            for p in props:
                if self._is_nl_like(p):
                    local_mapping[p.lower()] = self._map_label(p)
            if local_mapping:
                normalized = self._replace_props_in_formula(normalized, local_mapping)

        # Validate
        is_valid, reason = self.validate_formula(normalized)
        if not is_valid:
            logger.debug(f"Formula failed validation after sanitization: '{formula}' → '{normalized}' ({reason})")
            return None

        return normalized

    def sanitize_batch(
        self,
        formulas: List[str],
        source_labels: Optional[Dict[str, str]] = None,
    ) -> SanitizationResult:
        """Sanitize a batch of formulas.

        Args:
            formulas: List of raw formula strings (possibly from LLM).
            source_labels: Optional mapping of proposition labels to NL meanings
                (used to populate symbol_mapping even for valid formulas).

        Returns:
            SanitizationResult with sanitized formulas, symbol mapping, and skipped items.
        """
        result = SanitizationResult(total_input=len(formulas))

        for f in formulas:
            sanitized = self.sanitize_formula(f)
            if sanitized is not None:
                result.sanitized_formulas.append(sanitized)
            else:
                reason = "failed sanitization/validation"
                result.skipped_formulas.append((f, reason))
                logger.warning(f"Skipped formula: '{f[:80]}' ({reason})")

        result.total_sanitized = len(result.sanitized_formulas)
        result.symbol_mapping = dict(self._label_to_symbol)

        logger.info(
            f"PLFormulaSanitizer: {result.total_sanitized}/{result.total_input} "
            f"formulas sanitized, {len(result.skipped_formulas)} skipped"
        )
        return result

    def get_symbol_mapping(self) -> Dict[str, str]:
        """Get the current label→symbol mapping."""
        return dict(self._label_to_symbol)

    def reverse_mapping(self) -> Dict[str, str]:
        """Get symbol→label mapping for result interpretation."""
        return {v: k for k, v in self._label_to_symbol.items()}
