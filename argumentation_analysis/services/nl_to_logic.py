"""
Natural Language to Formal Logic translation pipeline.

Translates natural language arguments into propositional or first-order
logic formulas, then validates them via Tweety (when available) or
syntactic checks (fallback).

The key insight from student project 1.1.5 (QBF) soutenance is that
LLM translation alone is unreliable. This module implements a
translate-validate-retry loop: LLM generates the formula, validation
checks its syntax/consistency, and failures are fed back for correction.

Usage:
    translator = NLToLogicTranslator()
    result = await translator.translate(
        "If it rains, the ground is wet. It rains. Therefore the ground is wet."
    )
    # result = {
    #     "original_text": "...",
    #     "logic_type": "propositional",
    #     "formulas": ["rain => wet_ground", "rain"],
    #     "conclusion": "wet_ground",
    #     "valid": True,
    #     "validation_method": "tweety" | "syntactic",
    #     "attempts": 1,
    # }
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NLToLogic")

# Tweety availability
_tweety_bridge = None
_tweety_available = None


def _check_tweety() -> bool:
    """Check if TweetyBridge is available."""
    global _tweety_available, _tweety_bridge
    if _tweety_available is not None:
        return _tweety_available
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        _tweety_bridge = TweetyBridge.get_instance()
        _tweety_available = True
        logger.info("TweetyBridge available for formula validation")
    except Exception as e:
        _tweety_available = False
        logger.info(f"TweetyBridge unavailable ({e}), using syntactic validation")
    return _tweety_available


# --- Syntactic validation (fallback when Tweety unavailable) ---

# Valid propositional operators
PL_OPERATORS = {"&&", "||", "=>", "<=>", "!", "(", ")"}
PL_PATTERN = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*"  # variable
    r"(\s*(&&|\|\||=>|<=>)\s*"  # operator
    r"(!?\s*[a-zA-Z_][a-zA-Z0-9_]*))*$"  # more variables
)


def _syntactic_validate_pl(formula: str) -> Tuple[bool, str]:
    """Validate propositional logic formula syntax without Tweety.

    Checks for balanced parentheses and valid operator usage.
    """
    formula = formula.strip()
    if not formula:
        return False, "Empty formula"

    # Check balanced parentheses
    depth = 0
    for ch in formula:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return False, "Unbalanced parentheses: extra closing ')'"
    if depth != 0:
        return False, f"Unbalanced parentheses: {depth} unclosed '('"

    # Strip parens for inner check
    inner = formula.replace("(", " ").replace(")", " ").strip()

    # Check that we have at least one variable-like token
    tokens = inner.split()
    has_var = False
    for t in tokens:
        t_clean = t.strip("!")
        if t_clean and t_clean not in {"&&", "||", "=>", "<=>"}:
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", t_clean):
                has_var = True
            else:
                return False, f"Invalid token: '{t_clean}'"

    if not has_var:
        return False, "No variables found in formula"

    return True, "Syntactically valid"


def _validate_formula(formula: str, logic_type: str = "propositional") -> Tuple[bool, str]:
    """Validate a logic formula using Tweety or syntactic fallback."""
    if _check_tweety() and _tweety_bridge is not None:
        try:
            if logic_type == "propositional":
                valid = _tweety_bridge.validate_pl_formula(formula)
                return valid, "Valid (Tweety)" if valid else "Invalid syntax (Tweety)"
            elif logic_type == "first_order":
                consistent, msg = _tweety_bridge.check_consistency(
                    formula, logic_type="first_order"
                )
                return consistent, msg
        except Exception as e:
            logger.debug(f"Tweety validation failed: {e}, falling back to syntactic")

    # Syntactic fallback
    if logic_type == "propositional":
        return _syntactic_validate_pl(formula)
    return True, "No validation available for this logic type"


def _check_entailment(premises: List[str], conclusion: str) -> Tuple[bool, str]:
    """Check if premises entail the conclusion using Tweety or heuristic."""
    if _check_tweety() and _tweety_bridge is not None:
        try:
            kb = "\n".join(premises)
            result = _tweety_bridge.pl_query(kb, conclusion)
            if result is True:
                return True, "Entailment confirmed (Tweety)"
            elif result is False:
                return False, "Entailment NOT confirmed (Tweety)"
            else:
                return False, "Entailment check inconclusive"
        except Exception as e:
            logger.debug(f"Tweety entailment check failed: {e}")

    # Heuristic: check if conclusion variable appears in premises
    conclusion_vars = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", conclusion))
    premise_vars = set()
    for p in premises:
        premise_vars.update(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", p))

    if conclusion_vars <= premise_vars:
        return True, "Likely valid (all conclusion variables appear in premises)"
    missing = conclusion_vars - premise_vars
    return False, f"Variables {missing} in conclusion not found in premises"


# --- NL-to-PL translation prompts ---

NL_TO_PL_SYSTEM_PROMPT = """You are a formal logic translator. Convert natural language arguments
into propositional logic formulas.

Rules:
- Use lowercase_snake_case for proposition variables (e.g., it_rains, ground_is_wet)
- Use these operators: && (and), || (or), => (implies), <=> (iff), ! (not)
- Parentheses for grouping
- Return ONLY the formulas, one per line
- First lines are premises, last line after "CONCLUSION:" is the conclusion
- Keep variable names short but meaningful

Example input: "If it rains, the ground is wet. It is raining. Therefore the ground is wet."
Example output:
it_rains => ground_is_wet
it_rains
CONCLUSION: ground_is_wet

Example input: "All politicians lie or are corrupt. Smith is a politician. Therefore Smith lies or is corrupt."
Example output:
politician => (lies || corrupt)
smith_is_politician
smith_is_politician => politician
CONCLUSION: lies || corrupt"""

NL_TO_PL_RETRY_PROMPT = """The formula you generated was invalid.
Error: {error}

Please fix the formula and try again. Remember:
- Variables: lowercase_snake_case (letters, digits, underscores)
- Operators: && || => <=> !
- Parentheses must be balanced
- One formula per line
- Last line: CONCLUSION: <formula>

Original text: {text}
Your previous attempt:
{previous}

Please provide corrected formulas:"""


def _parse_llm_output(output: str) -> Tuple[List[str], Optional[str]]:
    """Parse LLM output into premises and conclusion."""
    lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
    premises = []
    conclusion = None

    for line in lines:
        if line.upper().startswith("CONCLUSION:"):
            conclusion = line[len("CONCLUSION:"):].strip()
        elif not line.startswith("#") and not line.startswith("//"):
            # Skip comment lines
            premises.append(line)

    return premises, conclusion


class NLToLogicTranslator:
    """Translates natural language arguments into formal logic with validation.

    Uses LLM for translation and Tweety (or syntactic fallback) for validation.
    Implements a retry loop on validation failure.
    """

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    async def translate(
        self,
        text: str,
        logic_type: str = "propositional",
        llm_service=None,
    ) -> Dict[str, Any]:
        """Translate natural language text to formal logic.

        Args:
            text: Natural language argument to translate
            logic_type: "propositional" or "first_order"
            llm_service: Optional LLM service for translation.
                         If None, uses heuristic extraction.

        Returns:
            Dict with formulas, validation result, and metadata.
        """
        if llm_service is not None:
            return await self._translate_with_llm(text, logic_type, llm_service)
        return self._translate_heuristic(text, logic_type)

    def _translate_heuristic(
        self, text: str, logic_type: str = "propositional"
    ) -> Dict[str, Any]:
        """Heuristic NL-to-logic translation (no LLM needed).

        Extracts simple conditional patterns from text.
        """
        sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if len(s.strip()) > 5]

        premises = []
        conclusion = None
        variables = {}
        var_counter = 0

        def _get_var(phrase: str) -> str:
            nonlocal var_counter
            key = phrase.lower().strip()[:40]
            if key not in variables:
                # Create a clean variable name
                clean = re.sub(r"[^a-z0-9]+", "_", key).strip("_")[:20]
                if not clean or not clean[0].isalpha():
                    clean = f"p{var_counter}"
                variables[key] = clean
                var_counter += 1
            return variables[key]

        for i, sent in enumerate(sentences):
            sent_lower = sent.lower().strip()

            # Pattern: "If X then Y" / "If X, Y" / "Si X alors Y" / "Si X, Y"
            if_match = re.match(
                r"(?:if|si)\s+(.+?)(?:,\s*then\s+|,\s*alors\s+|,\s+then\s+|,\s+alors\s+|,\s+)(.+)",
                sent_lower,
                re.IGNORECASE,
            )
            if if_match:
                antecedent = _get_var(if_match.group(1))
                consequent = _get_var(if_match.group(2))
                premises.append(f"{antecedent} => {consequent}")
                continue

            # Pattern: "Therefore X" / "Donc X"
            therefore_match = re.match(
                r"(?:therefore|donc|thus|par consequent|en conclusion)\s+(.+)",
                sent_lower,
                re.IGNORECASE,
            )
            if therefore_match:
                conclusion = _get_var(therefore_match.group(1))
                continue

            # Simple assertion
            if sent_lower and i < len(sentences) - 1:
                premises.append(_get_var(sent_lower))

        # If no explicit conclusion, use last sentence
        if conclusion is None and sentences:
            conclusion = _get_var(sentences[-1])

        # Validate each formula
        all_valid = True
        validation_errors = []
        for p in premises:
            valid, msg = _validate_formula(p, logic_type)
            if not valid:
                all_valid = False
                validation_errors.append(f"{p}: {msg}")

        if conclusion:
            valid, msg = _validate_formula(conclusion, logic_type)
            if not valid:
                all_valid = False
                validation_errors.append(f"conclusion {conclusion}: {msg}")

        # Check entailment
        entailment_valid = False
        entailment_msg = ""
        if all_valid and premises and conclusion:
            entailment_valid, entailment_msg = _check_entailment(premises, conclusion)

        return {
            "original_text": text[:500],
            "logic_type": logic_type,
            "formulas": premises,
            "conclusion": conclusion,
            "variables": {v: k for k, v in variables.items()},
            "valid_syntax": all_valid,
            "valid_entailment": entailment_valid,
            "entailment_detail": entailment_msg,
            "validation_method": "tweety" if _check_tweety() else "syntactic",
            "validation_errors": validation_errors,
            "attempts": 1,
            "method": "heuristic",
        }

    async def _translate_with_llm(
        self, text: str, logic_type: str, llm_service
    ) -> Dict[str, Any]:
        """LLM-based translation with validation retry loop."""
        previous_output = ""
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt == 1:
                    prompt = f"{NL_TO_PL_SYSTEM_PROMPT}\n\nTranslate this argument:\n{text}"
                else:
                    prompt = NL_TO_PL_RETRY_PROMPT.format(
                        error=last_error,
                        text=text,
                        previous=previous_output,
                    )

                # Call LLM
                response = await llm_service.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.1,
                )
                output = (
                    response.get("content", "")
                    if isinstance(response, dict)
                    else str(response)
                )
                previous_output = output

                # Parse output
                premises, conclusion = _parse_llm_output(output)
                if not premises:
                    last_error = "No formulas found in LLM output"
                    continue

                # Validate each formula
                all_valid = True
                validation_errors = []
                for p in premises:
                    valid, msg = _validate_formula(p, logic_type)
                    if not valid:
                        all_valid = False
                        validation_errors.append(f"{p}: {msg}")
                        last_error = f"Invalid formula: {p} — {msg}"

                if conclusion:
                    valid, msg = _validate_formula(conclusion, logic_type)
                    if not valid:
                        all_valid = False
                        validation_errors.append(f"conclusion: {msg}")
                        last_error = f"Invalid conclusion: {conclusion} — {msg}"

                if not all_valid:
                    logger.info(
                        f"Attempt {attempt}/{self.max_retries}: validation failed, retrying"
                    )
                    continue

                # Check entailment
                entailment_valid = False
                entailment_msg = ""
                if premises and conclusion:
                    entailment_valid, entailment_msg = _check_entailment(
                        premises, conclusion
                    )

                return {
                    "original_text": text[:500],
                    "logic_type": logic_type,
                    "formulas": premises,
                    "conclusion": conclusion,
                    "valid_syntax": True,
                    "valid_entailment": entailment_valid,
                    "entailment_detail": entailment_msg,
                    "validation_method": "tweety" if _check_tweety() else "syntactic",
                    "validation_errors": [],
                    "attempts": attempt,
                    "method": "llm",
                }

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt} error: {e}")

        # All retries exhausted — return best effort
        premises, conclusion = _parse_llm_output(previous_output)
        return {
            "original_text": text[:500],
            "logic_type": logic_type,
            "formulas": premises,
            "conclusion": conclusion,
            "valid_syntax": False,
            "valid_entailment": False,
            "entailment_detail": f"Failed after {self.max_retries} attempts: {last_error}",
            "validation_method": "tweety" if _check_tweety() else "syntactic",
            "validation_errors": [last_error],
            "attempts": self.max_retries,
            "method": "llm",
        }
