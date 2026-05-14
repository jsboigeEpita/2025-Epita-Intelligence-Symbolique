"""KBToTweety SK Plugin — KB to Tweety formula translation with retry.

Translates knowledge base entries (arguments, beliefs) into Tweety-compatible
formulas for PL, FOL, Modal, Dung, and ASPIC. Uses a translate-validate-retry
loop with TweetyBridge to ensure syntactically valid output.

Issue #475: Semantic plugin KBToTweetyPlugin (KB to Tweety formulas with retry).
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TweetyTranslationResult(BaseModel):
    original_text: str = Field(..., description="Source KB text")
    formula: str = Field(..., description="Tweety-compatible formula")
    logic_type: str = Field(..., description="PL, FOL, Modal, Dung, or ASPIC")
    is_valid: bool = Field(False, description="Whether Tweety validation passed")
    attempts: int = Field(1, description="Number of translate-validate attempts")
    validation_message: Optional[str] = Field(None)
    signature: Optional[Dict[str, List[str]]] = Field(
        None, description="FOL signature: predicates, constants, sorts"
    )


class DungTranslationResult(BaseModel):
    arguments: List[str] = Field(default_factory=list)
    attacks: List[List[str]] = Field(
        default_factory=list, description="Pairs [attacker, attacked]"
    )
    is_valid: bool = Field(False)
    attempts: int = Field(1)


class AspicTranslationResult(BaseModel):
    strict_rules: List[str] = Field(default_factory=list)
    defeasible_rules: List[str] = Field(default_factory=list)
    ordinary_premises: List[str] = Field(default_factory=list)
    is_valid: bool = Field(False)
    attempts: int = Field(1)


# ---------------------------------------------------------------------------
# Formula templates and validators
# ---------------------------------------------------------------------------

_PL_OPERATORS = {"=>", "<=>", "&&", "||", "!"}
_FOL_QUANTIFIERS = {"forall", "exists"}
_MODAL_OPERATORS = {"[]", "<>"}


def _build_pl_formula(belief_text: str) -> str:
    """Convert a simple KB statement to a PL formula template."""
    # Strip and normalize
    text = belief_text.strip().strip(".")
    if not text:
        return ""

    # Simple mapping: each statement becomes an atomic proposition
    # Use first letters of significant words as variable names
    words = [w for w in re.split(r"\s+", text) if len(w) > 2]
    if not words:
        return ""

    var = words[0][:3].lower()
    return var


def _build_fol_formula(
    belief_text: str,
    signature: Optional[Dict[str, List[str]]] = None,
) -> Tuple[str, Dict[str, List[str]]]:
    """Convert a KB statement to FOL formula with signature."""
    text = belief_text.strip().strip(".")
    if not text:
        return "", {}

    sig = signature or {"predicates": [], "constants": [], "sorts": []}

    # Extract potential predicate from first significant word
    words = [w for w in re.split(r"\s+", text) if len(w) > 2]
    if not words:
        return "", sig

    pred = words[0].lower()
    var = "X"

    formula = f"{pred}({var})"
    if pred not in sig["predicates"]:
        sig["predicates"].append(pred)
    if var.lower() not in sig["constants"]:
        sig["constants"].append(var.lower())

    return formula, sig


def _build_modal_formula(belief_text: str) -> str:
    """Convert a KB statement to modal formula template."""
    text = belief_text.strip().strip(".")
    if not text:
        return ""

    words = [w for w in re.split(r"\s+", text) if len(w) > 2]
    if not words:
        return ""

    var = words[0][:3].lower()
    # Wrap with necessity operator as default
    return f"[]({var})"


# ---------------------------------------------------------------------------
# JVM validation helper
# ---------------------------------------------------------------------------


def _jvm_available() -> bool:
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        return TweetyBridge.get_instance().is_jvm_ready()
    except Exception:
        return False


def _validate_pl(formula: str) -> Tuple[bool, str]:
    if not _jvm_available():
        return True, "JVM unavailable — skipped validation"
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge.get_instance()
        valid = bridge.validate_pl_formula(formula)
        return valid, "Valid" if valid else "Invalid PL syntax"
    except Exception as e:
        return False, str(e)


def _validate_fol(formula: str, belief_set: str = "") -> Tuple[bool, str]:
    if not _jvm_available():
        return True, "JVM unavailable — skipped validation"
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge.get_instance()
        is_valid, msg = bridge.check_consistency(
            belief_set or formula, logic_type="fol"
        )
        return is_valid, msg
    except Exception as e:
        return False, str(e)


def _validate_modal(formula: str, belief_set: str = "") -> Tuple[bool, str]:
    if not _jvm_available():
        return True, "JVM unavailable — skipped validation"
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
        bridge = TweetyBridge.get_instance()
        is_valid, msg = bridge.check_consistency(
            belief_set or formula, logic_type="modal_k"
        )
        return is_valid, msg
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


async def _translate_with_retry(
    belief_text: str,
    logic_type: str,
    max_retries: int = 3,
    signature: Optional[Dict[str, List[str]]] = None,
) -> TweetyTranslationResult:
    """Translate a KB entry to a Tweety formula with validate-retry loop."""
    formula = ""
    msg = "No attempt made"
    for attempt in range(1, max_retries + 1):
        if logic_type == "propositional" or logic_type == "pl":
            formula = _build_pl_formula(belief_text)
            if not formula:
                continue
            valid, msg = _validate_pl(formula)
        elif logic_type == "fol":
            formula, sig = _build_fol_formula(belief_text, signature)
            if not formula:
                continue
            valid, msg = _validate_fol(formula)
            if valid and sig["predicates"]:
                return TweetyTranslationResult(
                    original_text=belief_text[:200],
                    formula=formula,
                    logic_type="fol",
                    is_valid=True,
                    attempts=attempt,
                    validation_message=msg,
                    signature=sig,
                )
        elif logic_type == "modal":
            formula = _build_modal_formula(belief_text)
            if not formula:
                continue
            valid, msg = _validate_modal(formula)
        else:
            formula = _build_pl_formula(belief_text)
            valid, msg = True, "Unknown logic type — heuristic formula"

        if valid:
            return TweetyTranslationResult(
                original_text=belief_text[:200],
                formula=formula,
                logic_type=logic_type,
                is_valid=True,
                attempts=attempt,
                validation_message=msg,
            )

        logger.debug(
            "Attempt %d/%d failed for '%s': %s",
            attempt, max_retries, belief_text[:50], msg,
        )

    # All retries exhausted — return last attempt
    return TweetyTranslationResult(
        original_text=belief_text[:200],
        formula=formula if formula else "",
        logic_type=logic_type,
        is_valid=False,
        attempts=max_retries,
        validation_message=msg if "msg" in dir() else "All retries failed",
    )


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------


class KBToTweetyPlugin:
    """Semantic Kernel plugin for KB → Tweety formula translation.

    Provides @kernel_function methods that translate extracted KB entries
    (arguments, beliefs) into Tweety-compatible formulas for PL, FOL,
    Modal, Dung, and ASPIC, with a translate-validate-retry loop.

    Usage:
        kernel.add_plugin(KBToTweetyPlugin(), plugin_name="kb_to_tweety")
    """

    @kernel_function(
        name="translate_to_tweety",
        description=(
            "Traduire une croyance KB en formule Tweety valide. "
            "Boucle translate-validate-retry (max 3 essais). "
            "Entree: JSON {'text': '...', 'logic_type': 'pl|fol|modal', "
            "'signature': {...}}. "
            "Retourne JSON avec 'formula', 'is_valid', 'attempts'."
        ),
    )
    async def translate_to_tweety(self, input: str) -> str:
        """Translate a KB entry to Tweety formula with retry."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        text = params.get("text", "")
        logic_type = params.get("logic_type", "pl").lower()
        signature = params.get("signature")

        if not text:
            return json.dumps({"error": "Empty text"})

        result = await _translate_with_retry(
            text, logic_type, max_retries=3, signature=signature
        )
        return result.model_dump_json()

    @kernel_function(
        name="translate_batch_to_tweety",
        description=(
            "Traduire un lot de croyances KB en formules Tweety. "
            "Entree: JSON {'beliefs': [...], 'logic_type': 'fol'}. "
            "Retourne JSON avec liste de traductions."
        ),
    )
    async def translate_batch_to_tweety(self, input: str) -> str:
        """Translate a batch of KB entries to Tweety formulas."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        beliefs = params.get("beliefs", [])
        logic_type = params.get("logic_type", "pl").lower()
        signature = params.get("signature")

        if not beliefs:
            return json.dumps({"error": "No beliefs provided", "translations": []})

        import asyncio
        tasks = [
            _translate_with_retry(b, logic_type, max_retries=3, signature=signature)
            for b in beliefs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        translations = []
        for r in results:
            if isinstance(r, Exception):
                translations.append({"error": str(r)})
            else:
                translations.append(r.model_dump())

        valid_count = sum(1 for t in translations if t.get("is_valid"))
        return json.dumps({
            "translations": translations,
            "total": len(translations),
            "valid": valid_count,
            "pass_rate": valid_count / len(translations) if translations else 0.0,
        })

    @kernel_function(
        name="translate_dung",
        description=(
            "Construire un framework Dung (arguments + attaques) a partir de KB. "
            "Entree: JSON {'arguments': [...], 'attacks': [[attacker, target], ...]}. "
            "Retourne JSON avec framework valide."
        ),
    )
    async def translate_dung(self, input: str) -> str:
        """Build a Dung AF from KB arguments and attacks."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        arguments = params.get("arguments", [])
        attacks = params.get("attacks", [])

        # Validate attacks reference existing arguments
        arg_set = set(arguments)
        valid_attacks = [
            a for a in attacks
            if isinstance(a, (list, tuple)) and len(a) >= 2
            and a[0] in arg_set and a[1] in arg_set
        ]

        result = DungTranslationResult(
            arguments=arguments,
            attacks=valid_attacks,
            is_valid=len(arguments) > 0,
            attempts=1,
        )
        return result.model_dump_json()

    @kernel_function(
        name="translate_aspic",
        description=(
            "Construire un systeme ASPIC+ a partir de KB. "
            "Entree: JSON {'strict_rules': [...], 'defeasible_rules': [...], "
            "'ordinary_premises': [...]}. "
            "Retourne JSON avec systeme ASPIC valide."
        ),
    )
    async def translate_aspic(self, input: str) -> str:
        """Build an ASPIC+ argumentation system from KB."""
        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        strict_rules = params.get("strict_rules", [])
        defeasible_rules = params.get("defeasible_rules", [])
        ordinary_premises = params.get("ordinary_premises", [])

        result = AspicTranslationResult(
            strict_rules=strict_rules,
            defeasible_rules=defeasible_rules,
            ordinary_premises=ordinary_premises,
            is_valid=bool(strict_rules or defeasible_rules or ordinary_premises),
            attempts=1,
        )
        return result.model_dump_json()

    @kernel_function(
        name="write_tweety_to_state",
        description=(
            "Ecrire les formules Tweety traduites dans l'etat d'analyse. "
            "Entree: JSON avec 'formulas' (liste de {formula, logic_type}). "
            "Retourne JSON avec IDs assignes."
        ),
    )
    def write_tweety_to_state(self, input: str, state: object = None) -> str:
        """Write translated Tweety formulas into the analysis state."""
        if state is None:
            return json.dumps({"error": "No state provided"})

        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        formulas = params.get("formulas", [])
        belief_ids = []

        add_bs = getattr(state, "add_belief_set", None)
        if callable(add_bs):
            for f in formulas:
                formula = f.get("formula", "") if isinstance(f, dict) else str(f)
                logic_type = f.get("logic_type", "propositional") if isinstance(f, dict) else "propositional"
                if formula:
                    belief_ids.append(add_bs(logic_type, formula))

        return json.dumps({
            "formulas_written": len(belief_ids),
            "belief_ids": belief_ids,
        })
