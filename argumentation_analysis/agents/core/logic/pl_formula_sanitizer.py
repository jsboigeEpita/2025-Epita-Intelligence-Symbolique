"""PL Formula Sanitizer for Tweety-compatible syntax (#537).

Sits between LLM output and TweetyBridge.parse_pl_formula(). Handles:
- Normalisation of illegal tokens (accents/punctuation/spaces) into
  snake_case atoms that **preserve the LLM-chosen meaning**.
- Syntax validation against Tweety PL grammar before JPype submission
- Graceful fallback: log warning and skip invalid formulas instead of raising
- Symbol mapping storage for round-trip interpretation

Epic #1258 Track 2 (#1260): the sanitizer used to collapse ANY atom longer
than 30 chars (or NL-like) into opaque ``p, q, r`` — destroying the readable
names the LLM produced. The collapse is now **subtracted**: a readable,
parser-legal atom (``renewable_essential``) survives untouched regardless of
length. Only tokens that would fail the Tweety grammar (accents, punctuation,
embedded spaces) are normalised into a meaning-preserving snake_case atom;
``symbol_mapping`` records those renames so Track 3 can opacify at export.
The LLM names — this never generates a name.

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

# Tweety PL operators (after normalization). NB (#1132): Tweety's PlParser
# accepts the DOUBLE-form "&&"/"||" and rejects single-form "&"/"|".
_TWEETY_OPERATORS = frozenset({"=>", "<=>", "&&", "||", "!"})
_PARENS = frozenset({"(", ")"})
_SPECIAL_TOKENS = frozenset({"=>", "<=>", "&&", "||", "!", "(", ")", ""})

# Valid proposition name: starts with letter/underscore, followed by alphanumeric/underscore
_PROP_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Atomic formula: single valid proposition
_ATOMIC_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]+$")

# Pattern to detect NL-like tokens (too long, spaces, special chars, mixed language)
_NL_TOKEN_RE = re.compile(
    r"["
    r"\s"  # whitespace
    r"'\"`"  # quotes
    r",;:!?"  # punctuation (inside tokens)
    r"(){}[\]"  # brackets (inside tokens)
    r"@#$%^*=+"  # math/special
    r"<>/"  # angle brackets, slash
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
            print(f)  # "rain && (rain => wet)" — readable atoms survive (#1260)
        print(result.symbol_mapping)  # {"verbose_nl_claim": "verbose NL claim"}
    """

    def __init__(self, max_prop_length: int = 30):
        # #1260: ``max_prop_length`` is retained for backward-compat but no
        # longer caps readable atoms into ``p,q,r``. It is *not* read in the
        # hot path — see ``_needs_normalization``. Kept (not deleted) only so
        # existing call-sites passing it keep working.
        self._max_prop_length = max_prop_length
        self._symbol_counter = 0
        self._label_to_symbol: Dict[str, str] = {}

    def _next_symbol(self) -> str:
        """Generate the next atomic symbol: p, q, r, s, t, u, v, w, x, y, z, p2, q2, ...

        Retained for any future opt-in opaque-symbolisation, but #1260 stops
        calling it for readable atoms — see ``_normalize_atom``.
        """
        idx = self._symbol_counter
        # 11 letters: p(0), q(1), r(2), s(3), t(4), u(5), v(6), w(7), x(8), y(9), z(10)
        base = idx % 11
        round_num = idx // 11
        letter = chr(ord("p") + base)
        symbol = f"{letter}{round_num + 1}" if round_num > 0 else letter
        self._symbol_counter += 1
        return symbol

    def _needs_normalization(self, token: str) -> bool:
        """Return True only if ``token`` would FAIL the Tweety proposition grammar.

        #1260 (anti-pendule): previously an atom longer than 30 chars *or*
        containing any NL marker was collapsed to ``p,q,r``. That destroyed
        readable LLM-chosen atoms (``renewable_essential`` is perfectly legal
        yet was >30c-readable). The cap is **subtracted**: a token needs
        normalisation iff it is NOT already a valid ``PROPOSITION``. A long
        but legal atom survives untouched.
        """
        return not _PROP_RE.match(token)

    def _is_nl_like(self, token: str) -> bool:
        """Backward-compatible alias for :meth:`_needs_normalization`.

        #1260: the name is kept (callers + tests reference it) but the
        semantics narrowed to "illegal for Tweety", not "looks like prose".
        A readable long atom is no longer "NL-like" in the collapse sense.
        """
        return self._needs_normalization(token)

    def _normalize_atom(self, atom: str) -> str:
        """Normalise an illegal atom into a meaning-preserving snake_case atom.

        #1260: replaces the old ``_map_label`` collapse to ``p,q,r``. The
        transformation is lossy only in the syntactic sense (accents dropped,
        non-alnum → ``_``) — the semantic stem of the LLM-chosen name is
        preserved (``l``é``conomie_est_forte`` → ``l_e_conomie_est_forte``),
        never replaced by an opaque letter. First alnum chars retained
        (truncated to keep atoms reasonable); a short hash disambiguates
        distinct inputs collapsing to the same stem. Deterministic.
        """
        if not atom:
            return "x"
        import hashlib as _hashlib

        # Collapse runs of non-alnum to a single underscore, lowercase.
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", atom).strip("_").lower()[:24]
        if not cleaned:
            cleaned = "x"
        digest = _hashlib.md5(atom.encode("utf-8")).hexdigest()[:6]
        return f"{cleaned}_{digest}"

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
        """Map an illegal proposition label to a meaning-preserving atom.

        #1260: previously produced opaque ``p,q,r``. Now normalises the label
        into a readable snake_case atom (:meth:`_normalize_atom`) and records
        the mapping in ``symbol_mapping`` (readable_atom → original NL) so
        Track 3 can opacify at export. Reuses existing mappings for stability.
        """
        label_lower = label.lower()
        if label_lower in self._label_to_symbol:
            return self._label_to_symbol[label_lower]
        symbol = self._normalize_atom(label)
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
        # Canonicalise conjunction/disjunction to the Tweety DOUBLE-form (&&, ||)
        # — single-form &/| is rejected by Tweety (#1132).
        f = re.sub(r"\s*&+\s*", " && ", f)
        f = re.sub(r"\s*\|+\s*", " || ", f)
        f = f.replace("<->", " <=> ").replace("->", " => ")
        f = f.replace(" NOT ", " ! ").replace(" Not ", " ! ")
        f = re.sub(r"\s*(<=>|=>|!|\(|\))\s*", r" \1 ", f)
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
            bad = [
                t
                for t in f.split()
                if t not in _SPECIAL_TOKENS and not _PROP_RE.match(t)
            ]
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
            logger.debug(
                f"Formula failed validation after sanitization: '{formula}' → '{normalized}' ({reason})"
            )
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
