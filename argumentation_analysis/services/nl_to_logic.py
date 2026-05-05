"""
NL-to-Formal-Logic Translation Service.

Translates natural language arguments into formal logic representations
(propositional or first-order logic) using LLM-based translation with
Tweety validation and a retry loop for error correction.

Key insight from QBF soutenance (1.1.5): LLM translation alone is unreliable.
The solution is a translate-validate-retry loop: LLM generates the formula,
Tweety validates its syntax/consistency, and if it fails, the error message
is fed back to the LLM for correction.

Integration: Issue #173.
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Operator mappings ────────────────────────────────────────────────────

# Unicode → ASCII operators (Tweety only accepts ASCII)
UNICODE_TO_ASCII = {
    "\u2200": "forall",  # ∀
    "\u2203": "exists",  # ∃
    "\u2227": "&&",  # ∧
    "\u2228": "||",  # ∨
    "\u2192": "=>",  # →
    "\u00ac": "!",  # ¬
    "\u2194": "<=>",  # ↔
    "\u22a4": "true",  # ⊤
    "\u22a5": "false",  # ⊥
}


def normalize_operators(formula: str) -> str:
    """Replace Unicode logic operators with ASCII equivalents for Tweety."""
    result = formula
    for uni, ascii_op in UNICODE_TO_ASCII.items():
        result = result.replace(uni, ascii_op)
    return result


def _extract_fol_metadata(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Extract FOL metadata (sorts, predicates, constants) from parsed LLM response.

    Handles both old format (constants as flat dict of descriptions) and new
    format (sorts as dict of sort_name -> [constants], predicates as dict of
    pred_name -> [arg_sort_names]).

    Returns a normalized dict with:
        - sorts: Dict[str, List[str]] — sort_name -> list of constant names
        - predicates: Dict[str, List[str]] — pred_name -> list of arg sort names
        - constants_raw: Dict[str, str] — const_name -> description
    """
    sorts = parsed.get("sorts", {})
    predicates_raw = parsed.get("predicates", {})
    constants_raw = parsed.get("constants", {})

    # Normalize predicates: if values are strings (old format), convert to list
    predicates = {}
    for pred_name, pred_info in predicates_raw.items():
        if isinstance(pred_info, list):
            predicates[pred_name] = pred_info
        else:
            # Old format: {"Human": "is a human being"} — cannot infer sorts,
            # will be handled by defensive scanning in _validate_fol_with_signature
            pass

    # If no sorts declared but we have constants, build a default 'Thing' sort
    if not sorts and constants_raw:
        sorts = {"Thing": list(constants_raw.keys())}

    return {
        "sorts": sorts,
        "predicates": predicates,
        "constants_raw": constants_raw,
    }


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class TranslationResult:
    """Result of translating a single NL argument to formal logic."""

    original_text: str
    formula: str
    logic_type: str  # "propositional" or "fol"
    is_valid: bool
    validation_message: str = ""
    attempts: int = 1
    variables: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class TranslationBatchResult:
    """Result of translating multiple arguments."""

    translations: List[TranslationResult] = field(default_factory=list)
    overall_consistency: Optional[bool] = None
    consistency_message: str = ""
    method: str = "llm"  # "llm" or "heuristic"


# ── Prompt templates ─────────────────────────────────────────────────────

PL_SYSTEM_PROMPT = (
    "You are a formal logic expert. Translate natural language arguments "
    "into propositional logic formulas.\n\n"
    "Rules:\n"
    "- Use lowercase variable names (p, q, r, rain, sunny, etc.)\n"
    "- Operators: && (and), || (or), => (implies), ! (not), <=> (iff)\n"
    "- Each proposition should be a simple, atomic variable name\n"
    "- Provide a variable mapping explaining what each variable represents\n\n"
    "Respond with ONLY a JSON object:\n"
    '{"formula": "p && (p => q) => q", '
    '"variables": {"p": "it is raining", "q": "the ground is wet"}, '
    '"confidence": 0.85}'
)

PL_RETRY_PROMPT = (
    "Your previous translation was invalid. The validator returned:\n"
    "Error: {error}\n\n"
    "Please fix the formula. Common issues:\n"
    "- Missing parentheses around implications\n"
    "- Invalid variable names (use simple alphanumeric)\n"
    "- Unmatched parentheses\n"
    "- Wrong operator syntax (use &&, ||, =>, !, <=>)\n\n"
    "Original text: {original}\n"
    "Previous (invalid) formula: {formula}\n\n"
    "Respond with ONLY a corrected JSON object."
)

FOL_SYSTEM_PROMPT = (
    "You are a formal logic expert. Translate natural language arguments "
    "into first-order logic formulas using Tweety syntax.\n\n"
    "Rules:\n"
    "- Predicates: CamelCase (e.g., Mortal, Human, Argues)\n"
    "- Constants: lowercase (e.g., socrates, plato)\n"
    "- Variables: uppercase single letters (e.g., X, Y, Z)\n"
    "- Quantifiers: forall X: (...) and exists X: (...)\n"
    "- Operators: && (and), || (or), => (implies), ! (not), <=> (iff)\n"
    "- Separate multiple formulas with semicolons\n\n"
    "IMPORTANT: You MUST declare all constants with their sorts/types.\n"
    "Group constants by sort (e.g., all people under 'Person', all cities "
    "under 'City'). Every predicate must list the sort names of its arguments.\n"
    "If unsure about the sort, use 'Thing' as a generic sort.\n\n"
    "Respond with ONLY a JSON object:\n"
    '{"formulas": ["forall X: (Human(X) => Mortal(X))", "Human(socrates)"], '
    '"predicates": {"Human": ["Person"], "Mortal": ["Person"]}, '
    '"sorts": {"Person": ["socrates", "plato"]}, '
    '"constants": {"socrates": "the philosopher Socrates", "plato": "the philosopher Plato"}, '
    '"confidence": 0.9}'
)

FOL_RETRY_PROMPT = (
    "Your previous FOL translation was invalid. The validator returned:\n"
    "Error: {error}\n\n"
    "Common issues:\n"
    "- Predicate names must be CamelCase\n"
    "- Constants must be lowercase\n"
    "- Quantifier syntax: forall X: (...) not ∀x.(...)\n"
    "- Missing parentheses around quantifier scope\n\n"
    "Original text: {original}\n"
    "Previous (invalid) formulas: {formulas}\n\n"
    "Respond with ONLY a corrected JSON object."
)


# ── Service class ────────────────────────────────────────────────────────


class NLToLogicTranslator:
    """Translates natural language arguments to formal logic with validation.

    Uses an LLM to generate formal representations, validates them via
    Tweety (or Python fallback), and retries on failure with the error
    message fed back to the LLM.

    Args:
        max_retries: Maximum translation attempts per argument (default: 3).
        logic_type: Default logic type ("propositional" or "fol").
    """

    def __init__(
        self,
        max_retries: int = 3,
        logic_type: str = "propositional",
    ):
        self.max_retries = max_retries
        self.logic_type = logic_type

    async def translate(
        self,
        text: str,
        logic_type: Optional[str] = None,
    ) -> TranslationResult:
        """Translate a single NL argument to formal logic.

        Args:
            text: Natural language argument text.
            logic_type: Override default logic type.

        Returns:
            TranslationResult with formula, validity, and metadata.
        """
        lt = logic_type or self.logic_type

        # Try LLM-based translation with retry loop
        try:
            return await self._translate_with_llm(text, lt)
        except Exception as e:
            logger.warning(f"LLM translation failed, using heuristic: {e}")
            return self._translate_heuristic(text, lt)

    async def translate_batch(
        self,
        arguments: List[str],
        logic_type: Optional[str] = None,
        check_consistency: bool = True,
    ) -> TranslationBatchResult:
        """Translate multiple arguments and optionally check consistency.

        Args:
            arguments: List of NL argument texts.
            logic_type: Logic type for all translations.
            check_consistency: Whether to check KB consistency.

        Returns:
            TranslationBatchResult with all translations and consistency info.
        """
        lt = logic_type or self.logic_type
        translations = []

        for arg_text in arguments[:10]:  # Cap at 10
            if len(arg_text.strip()) < 10:
                continue
            result = await self.translate(arg_text, lt)
            translations.append(result)

        batch = TranslationBatchResult(translations=translations)

        # Check consistency if requested and we have valid formulas
        valid_formulas = [t.formula for t in translations if t.is_valid]
        if check_consistency and valid_formulas:
            is_consistent, msg = await self._check_consistency(valid_formulas, lt)
            batch.overall_consistency = is_consistent
            batch.consistency_message = msg

        # Determine method
        batch.method = (
            "llm" if any(t.attempts > 0 for t in translations) else "heuristic"
        )

        return batch

    # ── LLM translation with retry loop ──────────────────────────────

    async def _translate_with_llm(
        self,
        text: str,
        logic_type: str,
    ) -> TranslationResult:
        """Translate via LLM with validate-retry loop."""
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return self._translate_heuristic(text, logic_type)

        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        system_prompt = (
            PL_SYSTEM_PROMPT if logic_type == "propositional" else FOL_SYSTEM_PROMPT
        )
        retry_template = (
            PL_RETRY_PROMPT if logic_type == "propositional" else FOL_RETRY_PROMPT
        )

        last_error = ""
        last_formula = ""
        variables = {}
        confidence = 0.0

        for attempt in range(1, self.max_retries + 1):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                ]

                if attempt == 1:
                    messages.append({"role": "user", "content": text[:2000]})
                else:
                    retry_msg = retry_template.format(
                        error=last_error,
                        original=text[:1000],
                        formula=last_formula,
                        formulas=last_formula,
                    )
                    messages.append({"role": "user", "content": retry_msg})

                response = await client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                )
                raw = response.choices[0].message.content or ""
                parsed = self._parse_llm_response(raw, logic_type)

                if logic_type == "propositional":
                    formula = parsed.get("formula", "")
                    variables = parsed.get("variables", {})
                    confidence = parsed.get("confidence", 0.7)
                    last_formula = formula
                    fol_metadata = None
                else:
                    formulas = parsed.get("formulas", [])
                    formula = "; ".join(formulas) if formulas else ""
                    variables = {
                        **parsed.get("predicates", {}),
                        **parsed.get("constants", {}),
                    }
                    confidence = parsed.get("confidence", 0.7)
                    last_formula = formula
                    # Extract FOL metadata for Tweety signature building
                    fol_metadata = _extract_fol_metadata(parsed)

                # Validate via Tweety or Python fallback
                is_valid, val_msg = await self._validate_formula(
                    formula, logic_type, fol_metadata=fol_metadata
                )

                if is_valid:
                    return TranslationResult(
                        original_text=text,
                        formula=formula,
                        logic_type=logic_type,
                        is_valid=True,
                        validation_message=val_msg,
                        attempts=attempt,
                        variables=variables,
                        confidence=confidence,
                    )

                last_error = val_msg
                logger.info(
                    f"Translation attempt {attempt}/{self.max_retries} invalid: {val_msg}"
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM call failed on attempt {attempt}: {e}")

        # All retries exhausted — return last attempt as invalid
        return TranslationResult(
            original_text=text,
            formula=last_formula,
            logic_type=logic_type,
            is_valid=False,
            validation_message=f"Failed after {self.max_retries} attempts: {last_error}",
            attempts=self.max_retries,
            variables=variables,
            confidence=0.0,
        )

    def _parse_llm_response(self, raw: str, logic_type: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown fences."""
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        return {}

    # ── Validation ───────────────────────────────────────────────────

    async def _validate_formula(
        self,
        formula: str,
        logic_type: str,
        fol_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Validate formula via Tweety (JVM) or Python fallback.

        Args:
            formula: The formula string to validate.
            logic_type: "propositional" or "fol".
            fol_metadata: Optional FOL metadata with sorts, predicates, and
                constants extracted from the LLM response. Used to build a
                Tweety FolSignature so that constants are pre-declared before
                parsing (required by Tweety's FOL parser).
        """
        if not formula or not formula.strip():
            return False, "Empty formula"

        formula = normalize_operators(formula)

        # Try Tweety validation first
        try:
            return await self._validate_with_tweety(
                formula, logic_type, fol_metadata=fol_metadata
            )
        except Exception as e:
            logger.debug(f"Tweety validation unavailable ({e}), using Python fallback")
            return self._validate_with_python(formula, logic_type)

    async def _validate_with_tweety(
        self,
        formula: str,
        logic_type: str,
        fol_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Validate using TweetyBridge (requires JVM).

        For FOL formulas, builds a Tweety FolSignature from the LLM-provided
        metadata (sorts, constants, predicates) before parsing. This ensures
        that constants like 'socrates' are pre-declared in the signature,
        which Tweety's FOL parser requires.
        """
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge()

        if logic_type == "propositional":
            # Try to parse as PL formula
            result = await asyncio.to_thread(bridge.validate_pl_formula, formula)
            if result:
                return True, "Valid propositional formula (Tweety)"
            else:
                return False, "Invalid propositional formula syntax"
        else:
            # FOL: build signature from metadata and validate all formulas together
            fol_formulas = [f.strip() for f in formula.split(";") if f.strip()]

            if fol_metadata and (
                fol_metadata.get("sorts") or fol_metadata.get("constants_raw")
            ):
                # Use programmatic signature building for robust constant handling
                return await asyncio.to_thread(
                    self._validate_fol_with_signature,
                    bridge,
                    fol_formulas,
                    fol_metadata,
                )
            else:
                # Fallback: try parsing each formula without signature (old behavior)
                errors = []
                for f in fol_formulas:
                    try:
                        await asyncio.to_thread(bridge.fol_handler.parse_fol_formula, f)
                    except (ValueError, Exception) as e:
                        errors.append(f"'{f}': {e}")
                if errors:
                    return False, "; ".join(errors)
                return True, "Valid FOL formulas (Tweety)"

    def _validate_fol_with_signature(
        self,
        bridge: Any,
        fol_formulas: List[str],
        fol_metadata: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Validate FOL formulas by building a Tweety signature with pre-declared constants.

        This is the key fix for the Tweety FOL constant pre-declaration issue:
        Tweety's FolParser requires all constants to be declared in a FolSignature
        before they appear in formulas. Without this, only the first formula
        (which implicitly declares constants) succeeds, and subsequent formulas
        referencing the same constants fail.

        Args:
            bridge: TweetyBridge instance.
            fol_formulas: List of individual FOL formula strings.
            fol_metadata: Dict with 'sorts' (sort_name -> [constants]),
                'predicates' (pred_name -> [arg_sort_names]),
                and 'constants_raw' (const_name -> description).
        """
        import jpype

        sorts_data = fol_metadata.get("sorts", {})
        predicates_data = fol_metadata.get("predicates", {})
        constants_raw = fol_metadata.get("constants_raw", {})

        # If no sorts declared, create a default 'Thing' sort with all constants
        if not sorts_data and constants_raw:
            sorts_data = {"Thing": list(constants_raw.keys())}

        # Also scan formulas for undeclared constants (lowercase identifiers
        # inside predicates that aren't variables — variables are uppercase)
        all_declared_constants = set()
        for consts in sorts_data.values():
            all_declared_constants.update(consts)

        for f in fol_formulas:
            # Find all arguments inside predicates: Pred(arg1, arg2, ...)
            for match in re.finditer(r"[A-Z][a-zA-Z]*\(([^)]+)\)", f):
                args = [a.strip() for a in match.group(1).split(",")]
                for arg in args:
                    # Constants are lowercase identifiers; variables are uppercase single letters
                    if (
                        re.match(r"^[a-z][a-z0-9_]*$", arg)
                        and arg not in all_declared_constants
                        and arg not in ("true", "false")
                    ):
                        logger.debug(
                            f"Found undeclared constant '{arg}' in formula, adding to Thing sort"
                        )
                        if "Thing" not in sorts_data:
                            sorts_data["Thing"] = []
                        sorts_data["Thing"].append(arg)
                        all_declared_constants.add(arg)

        try:
            FolSignature = jpype.JClass(
                "org.tweetyproject.logics.fol.syntax.FolSignature"
            )
            Sort = jpype.JClass("org.tweetyproject.logics.commons.syntax.Sort")
            Constant = jpype.JClass("org.tweetyproject.logics.commons.syntax.Constant")
            Predicate = jpype.JClass(
                "org.tweetyproject.logics.commons.syntax.Predicate"
            )
            FolParser = jpype.JClass("org.tweetyproject.logics.fol.parser.FolParser")
            ArrayList = jpype.JClass("java.util.ArrayList")
            String = jpype.JClass("java.lang.String")

            signature = FolSignature()
            sorts_map = {}

            # Step 1: Create and add all sorts
            for sort_name in sorts_data.keys():
                java_sort = Sort(String(sort_name))
                signature.add(java_sort)
                sorts_map[sort_name] = java_sort

            # Step 2: Create and add constants to their sorts
            for sort_name, constants_list in sorts_data.items():
                parent_sort = sorts_map.get(sort_name)
                if parent_sort:
                    for const_name in constants_list:
                        java_constant = Constant(String(const_name), parent_sort)
                        signature.add(java_constant)

            # Step 3: Create and add predicates with their argument sorts
            # Handle both formats: {"Pred": ["Sort1"]} and {"Pred": "description"}
            for pred_name, arg_info in predicates_data.items():
                if (
                    isinstance(arg_info, list)
                    and arg_info
                    and isinstance(arg_info[0], str)
                ):
                    # New format: list of sort names
                    java_arg_sorts = ArrayList()
                    for arg_sort_name in arg_info:
                        java_sort = sorts_map.get(arg_sort_name)
                        if not java_sort:
                            # Create a fallback sort if referenced but not declared
                            java_sort = Sort(String(arg_sort_name))
                            signature.add(java_sort)
                            sorts_map[arg_sort_name] = java_sort
                        java_arg_sorts.add(java_sort)
                    java_predicate = Predicate(String(pred_name), java_arg_sorts)
                    signature.add(java_predicate)

            # Step 4: Scan formulas for undeclared predicates and add them defensively
            for f in fol_formulas:
                for match in re.finditer(r"([A-Z][a-zA-Z]*)\(([^)]*)\)", f):
                    pred_name = match.group(1)
                    # Check if already in signature by checking predicates_data
                    if pred_name not in predicates_data:
                        args_str = match.group(2)
                        arity = args_str.count(",") + 1 if args_str.strip() else 0
                        # Default to Thing sort for all args
                        if "Thing" not in sorts_map:
                            thing_sort = Sort(String("Thing"))
                            signature.add(thing_sort)
                            sorts_map["Thing"] = thing_sort
                        java_arg_sorts = ArrayList()
                        for _ in range(arity):
                            java_arg_sorts.add(sorts_map["Thing"])
                        java_predicate = Predicate(String(pred_name), java_arg_sorts)
                        signature.add(java_predicate)
                        # Track so we don't re-add
                        predicates_data[pred_name] = ["Thing"] * arity

            # Step 5: Parse all formulas with the pre-configured signature
            parser = FolParser()
            parser.setSignature(signature)

            errors = []
            for f in fol_formulas:
                try:
                    bridge.fol_handler.parse_fol_formula(f, custom_parser=parser)
                except (ValueError, Exception) as e:
                    errors.append(f"'{f}': {e}")

            if errors:
                return False, "; ".join(errors)

            formula_count = len(fol_formulas)
            return (
                True,
                f"Valid FOL formulas ({formula_count} formulas, Tweety with signature)",
            )

        except jpype.JException as e:
            error_msg = str(e.getMessage()) if hasattr(e, "getMessage") else str(e)
            return False, f"Tweety signature building error: {error_msg}"
        except Exception as e:
            return False, f"FOL signature validation error: {e}"

    def _validate_with_python(
        self,
        formula: str,
        logic_type: str,
    ) -> Tuple[bool, str]:
        """Lightweight Python-based syntax validation (no JVM needed)."""
        if logic_type == "propositional":
            return self._validate_pl_python(formula)
        else:
            return self._validate_fol_python(formula)

    def _validate_pl_python(self, formula: str) -> Tuple[bool, str]:
        """Basic propositional logic syntax validation."""
        # Check balanced parentheses
        depth = 0
        for ch in formula:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth < 0:
                return False, "Unmatched closing parenthesis"
        if depth != 0:
            return False, f"Unmatched parentheses (depth {depth})"

        # Check for valid tokens
        # Remove known operators and whitespace
        cleaned = formula
        for op in ["<=>", "=>", "&&", "||", "!"]:
            cleaned = cleaned.replace(op, " ")
        cleaned = cleaned.replace("(", " ").replace(")", " ")
        tokens = cleaned.split()

        # Each token should be a valid identifier
        for token in tokens:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", token):
                return False, f"Invalid token: '{token}'"

        # Check for empty formula (just operators)
        if not tokens:
            return False, "Formula contains no propositions"

        return True, "Valid propositional formula (Python)"

    def _validate_fol_python(self, formula: str) -> Tuple[bool, str]:
        """Basic FOL syntax validation."""
        fol_formulas = [f.strip() for f in formula.split(";") if f.strip()]
        if not fol_formulas:
            return False, "No formulas found"

        for f in fol_formulas:
            # Check balanced parentheses
            depth = 0
            for ch in f:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if depth < 0:
                    return False, f"Unmatched closing parenthesis in '{f}'"
            if depth != 0:
                return False, f"Unmatched parentheses in '{f}'"

            # Check for predicates: at least one CamelCase word followed by (
            if (
                not re.search(r"[A-Z][a-zA-Z]*\(", f)
                and "forall" not in f
                and "exists" not in f
            ):
                return False, f"No predicates found in '{f}'"

        return True, "Valid FOL formulas (Python)"

    # ── Consistency checking ─────────────────────────────────────────

    async def _check_consistency(
        self,
        formulas: List[str],
        logic_type: str,
    ) -> Tuple[bool, str]:
        """Check if a set of formulas is consistent."""
        try:
            from argumentation_analysis.agents.core.logic.tweety_bridge import (
                TweetyBridge,
            )

            bridge = TweetyBridge()
            normalized = [normalize_operators(f) for f in formulas]
            belief_set = "\n".join(normalized)
            lt = "propositional" if logic_type == "propositional" else "first_order"
            is_consistent, msg = await asyncio.to_thread(
                bridge.check_consistency, belief_set, lt
            )
            return bool(is_consistent), msg
        except Exception as e:
            logger.debug(f"Tweety consistency check unavailable: {e}")
            # Python fallback: check for obvious contradictions
            return self._check_consistency_python(formulas, logic_type)

    def _check_consistency_python(
        self,
        formulas: List[str],
        logic_type: str,
    ) -> Tuple[bool, str]:
        """Lightweight contradiction detection (Python fallback)."""
        positives = set()
        negatives = set()
        for f in formulas:
            f = f.strip()
            if f.startswith("!"):
                negatives.add(f[1:].strip())
            else:
                # Only consider simple atoms
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", f):
                    positives.add(f)

        contradictions = positives & negatives
        if contradictions:
            return False, f"Contradictions found: {', '.join(contradictions)}"
        return True, "No obvious contradictions (Python check)"

    # ── Heuristic fallback ───────────────────────────────────────────

    def _translate_heuristic(
        self,
        text: str,
        logic_type: str,
    ) -> TranslationResult:
        """Simple heuristic translation when LLM is unavailable.

        Extracts key terms and creates basic propositional variables.
        """
        # Extract simple propositions from argument markers
        markers = [
            "therefore",
            "because",
            "since",
            "thus",
            "hence",
            "consequently",
            "so",
            "if",
            "then",
            # French markers
            "donc",
            "car",
            "puisque",
            "parce que",
            "si",
            "alors",
        ]

        sentences = re.split(r"[.!?;]", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if logic_type == "propositional":
            variables = {}
            for i, sent in enumerate(sentences[:5]):
                var_name = f"p{i + 1}"
                variables[var_name] = sent[:80]

            if len(variables) >= 2:
                var_names = list(variables.keys())
                # Simple implication chain: p1 => p2 => ... => pN
                implications = [
                    f"{var_names[i]} => {var_names[i+1]}"
                    for i in range(len(var_names) - 1)
                ]
                formula = " && ".join([var_names[0]] + implications)
            elif variables:
                formula = list(variables.keys())[0]
            else:
                formula = "p1"
                variables = {"p1": text[:80]}

            return TranslationResult(
                original_text=text,
                formula=formula,
                logic_type="propositional",
                is_valid=True,
                validation_message="Heuristic translation (no LLM)",
                attempts=0,
                variables=variables,
                confidence=0.3,
            )

        else:  # FOL
            sentences_clean = [
                re.sub(r"[^a-zA-Z0-9\s]", "", s).strip() for s in sentences[:5]
            ]
            formulas = []
            predicates = {}
            for i, sent in enumerate(sentences_clean):
                words = sent.split()
                if len(words) >= 2:
                    pred = words[0].capitalize()
                    const = words[-1].lower()
                    formulas.append(f"{pred}({const})")
                    predicates[pred] = f"relates to {sent[:40]}"

            formula = "; ".join(formulas) if formulas else "Stated(arg1)"
            return TranslationResult(
                original_text=text,
                formula=formula,
                logic_type="fol",
                is_valid=True,
                validation_message="Heuristic FOL translation (no LLM)",
                attempts=0,
                variables=predicates,
                confidence=0.2,
            )
