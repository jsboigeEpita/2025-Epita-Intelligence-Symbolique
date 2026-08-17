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

from argumentation_analysis.plugins.kernel_input import parse_kernel_json_object

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TweetyTranslationResult(BaseModel):
    original_text: str = Field(..., description="Source KB text")
    formula: str = Field(..., description="Tweety-compatible formula")
    logic_type: str = Field(..., description="PL, FOL, Modal, Dung, or ASPIC")
    # #1777: tri-state (#1634). None = the label was never evaluated (unknown
    # logic type); True/False = a validator actually parsed the formula.
    is_valid: Optional[bool] = Field(
        None, description="Whether Tweety validation passed"
    )
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
    except ImportError:
        return False
    # CONV-B #1333 / #1773: ``is_jvm_ready()`` lives on TweetyInitializer
    # (``bridge.initializer``), NOT on TweetyBridge. The previous bare
    # ``except Exception`` swallowed the AttributeError, so this probe ALWAYS
    # returned False and the branches below fabricated ``True`` verdicts
    # ("skipped validation"). Only genuine unavailability (module absent,
    # JVM init failed) may return False — a broken probe must raise.
    try:
        return TweetyBridge.get_instance().initializer.is_jvm_ready()
    except RuntimeError:
        return False


def _validate_pl(formula: str) -> Tuple[bool, str]:
    if not _jvm_available():
        # #1773 constat 2: pas de validation => pas de verdict. Rendre True
        # ici fabriquait un is_valid:true sans aucun calcul.
        return False, "JVM unavailable — validation not performed"
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge.get_instance()
        valid = bridge.validate_pl_formula(formula)
        return valid, "Valid" if valid else "Invalid PL syntax"
    except Exception as e:
        return False, str(e)


def _validate_fol(
    formula: str,
    belief_set: str = "",
    signature: Optional[Dict[str, List[str]]] = None,
) -> Tuple[bool, str]:
    if not _jvm_available():
        return False, "JVM unavailable — validation not performed"
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge.get_instance()
        # #1777: is_valid measures parseability (uniform with _validate_pl), not
        # consistency. The old "fol" label never routed (bridge expects
        # "first_order") -> (None, "Unknown logic type") -> 3 retries on a
        # well-formed formula. A well-formed contradictory formula parses.
        #
        # FolParser does NOT auto-declare predicates ("Predicate 'Human' has
        # not been declared", firsthand #1777) — the signature must be built
        # first. create_belief_set_programmatically (fol_handler) constructs
        # the Java FolSignature from the plugin's signature dict and
        # defensively declares predicates used-but-undeclared in the formula,
        # then raises ValueError on unparseable syntax.
        sig = signature or {}
        builder_data = {
            "_sorts": {"thing": list(sig.get("constants") or [])},
            "_predicates": {p: ["thing"] for p in (sig.get("predicates") or [])},
            "_formulas": [belief_set or formula],
        }
        bridge.fol_handler.create_belief_set_programmatically(builder_data)
        return True, "Valid FOL formula"
    except Exception as e:
        return False, str(e)


def _validate_modal(formula: str, belief_set: str = "") -> Tuple[bool, str]:
    if not _jvm_available():
        return False, "JVM unavailable — validation not performed"
    try:
        from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

        bridge = TweetyBridge.get_instance()
        # #1777: same parse-validity semantics; the old "modal_k" label never
        # routed (bridge expects naked codes K/T/S4/S5).
        #
        # MlParser does NOT auto-declare atoms ("Unknown object p", firsthand
        # #1777): propositions are 0-ary predicates declared inline as
        # ``type(p)`` (#1213) — every atom referenced by the formula must be
        # declared first (mirrors _construct_modal_kb_from_json).
        text = belief_set or formula
        atoms = sorted(set(re.findall(r"\b[a-z_][a-z0-9_]*\b", text)))
        declared = "\n".join(f"type({a})" for a in atoms)
        kb_text = f"{declared}\n{text}" if declared else text
        bridge.modal_handler.parse_belief_set(kb_text)
        return True, "Valid modal formula"
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
            valid, msg = _validate_fol(formula, signature=sig)
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
            # #1777: an unknown logic type is neither valid nor invalid — it
            # was never evaluated (tri-state #1634). No fabrication, no retry
            # (the label cannot change between attempts).
            return TweetyTranslationResult(
                original_text=belief_text[:200],
                formula="",
                logic_type=logic_type,
                is_valid=None,
                attempts=1,
                validation_message=(
                    f"Unknown logic type: {logic_type} — not evaluated"
                ),
            )

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
            attempt,
            max_retries,
            belief_text[:50],
            msg,
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["text", "logic_type", "signature"],
            required_keys=["text"],
        )
        if params is None:
            return json.dumps(err)

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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=["beliefs", "logic_type", "signature"],
            required_keys=["beliefs"],
        )
        if params is None:
            return json.dumps(err)

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
        return json.dumps(
            {
                "translations": translations,
                "total": len(translations),
                "valid": valid_count,
                "pass_rate": valid_count / len(translations) if translations else 0.0,
            }
        )

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
        params, err = parse_kernel_json_object(
            input, expected_keys=["arguments", "attacks"]
        )
        if params is None:
            return json.dumps(err)

        arguments = params.get("arguments", [])
        attacks = params.get("attacks", [])

        # Validate attacks reference existing arguments
        arg_set = set(arguments)
        valid_attacks = [
            a
            for a in attacks
            if isinstance(a, (list, tuple))
            and len(a) >= 2
            and a[0] in arg_set
            and a[1] in arg_set
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
        params, err = parse_kernel_json_object(
            input,
            expected_keys=[
                "strict_rules",
                "defeasible_rules",
                "ordinary_premises",
            ],
        )
        if params is None:
            return json.dumps(err)

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

        params, err = parse_kernel_json_object(
            input, expected_keys=["formulas"], required_keys=["formulas"]
        )
        if params is None:
            return json.dumps(err)

        formulas = params.get("formulas", [])
        belief_ids = []

        add_bs = getattr(state, "add_belief_set", None)
        if callable(add_bs):
            for f in formulas:
                formula = f.get("formula", "") if isinstance(f, dict) else str(f)
                logic_type = (
                    f.get("logic_type", "propositional")
                    if isinstance(f, dict)
                    else "propositional"
                )
                if formula:
                    belief_ids.append(add_bs(logic_type, formula))

        return json.dumps(
            {
                "formulas_written": len(belief_ids),
                "belief_ids": belief_ids,
            }
        )
