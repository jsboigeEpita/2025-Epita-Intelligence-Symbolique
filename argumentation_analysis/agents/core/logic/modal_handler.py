import jpype
import logging
from typing import Optional, Tuple

from .tweety_initializer import TweetyInitializer
from argumentation_analysis.core.config import settings, ModalSolverChoice

logger = logging.getLogger(__name__)


def _get_spass_path() -> "str | None":
    """Return the detected SPASS binary path, or None if not wired.

    Reads the module-level registry populated by
    ``jvm_setup._configure_external_tools``. Centralised here (mirroring
    ``fol_handler._get_eprover_path``) so the Modal handler does not duplicate
    the detection logic and the wiring is testable in isolation (#1205).

    #1205: the previous ``_get_spass_reasoner`` called ``SPASSMlReasoner()`` with
    no argument — but in Tweety 1.28+/1.29 the only constructors are
    ``SPASSMlReasoner(String)`` and ``SPASSMlReasoner(String, Shell)`` (verified
    via ``javap`` on the bundled jar). The no-arg call raised a Java
    construction error, swallowed by the surrounding ``except`` → SPASS was
    never wired, yet the pipeline reported it as the configured modal solver
    (formal theater, same class as the EProver regression #1196/#1202).
    """
    try:
        from argumentation_analysis.core.jvm_setup import EXTERNAL_TOOL_PATHS

        return EXTERNAL_TOOL_PATHS.get("spass")
    except Exception:  # pragma: no cover - import guard
        return None


class ModalHandler:
    """
    Handles Modal Logic operations using TweetyProject.
    Supports two reasoners:
    - SimpleMlReasoner (default, pure Tweety)
    - SPASSMlReasoner (backed by external SPASS binary, more powerful)
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        """
        Initializes the ModalHandler.
        """
        self._initializer_instance = initializer_instance
        self._modal_parser = initializer_instance.get_modal_parser()
        self._modal_reasoner = initializer_instance.get_modal_reasoner()
        self._spass_reasoner = None  # Lazy-loaded

        if self._modal_parser is None or self._modal_reasoner is None:
            logger.error(
                "Modal Logic components not initialized. Ensure TweetyInitializer is configured for Modal Logic."
            )
            raise RuntimeError(
                "ModalHandler initialized before TweetyInitializer completed Modal Logic setup."
            )

    def _get_spass_reasoner(self):
        """Lazy-load SPASSMlReasoner, wired with the detected binary path.

        #1205 (anti-theater #1019): the previous implementation called
        ``SPASSMlReasoner()`` with no argument — but Tweety 1.28+/1.29 only
        exposes ``SPASSMlReasoner(String)`` / ``SPASSMlReasoner(String, Shell)``
        (verified via ``javap``), so the construction raised and the bare
        ``except`` swallowed it into a generic ``RuntimeError``. The detected
        SPASS path (``EXTERNAL_TOOL_PATHS['spass']``) was never passed to the
        constructor — mirroring the EProver regression #1196/#1202.

        Now reads the registered path and instantiates
        ``SPASSMlReasoner(JString(path))`` (1-arg ctor). If the path is unset
        (binary absent), this raises ``RuntimeError`` **fail-loud** — it does
        NOT silently fall back to ``SimpleMlReasoner``: a missing SPASS binary
        must surface as an honest "could not decide" (``None``/degraded), never
        as a fabricated verdict.
        """
        if self._spass_reasoner is None:
            spass_path = _get_spass_path()
            if spass_path is None:
                raise RuntimeError(
                    "SPASS binary not detected (EXTERNAL_TOOL_PATHS['spass'] "
                    "unset) — modal axis cannot decide via SPASS. Install "
                    "SPASS under ext_tools/spass/ or use a non-SPASS modal "
                    "solver (anti-theater #1019: no silent fallback)."
                )
            try:
                SPASSMlReasoner = jpype.JClass(
                    "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
                )
                JString = jpype.JClass("java.lang.String")
                self._spass_reasoner = SPASSMlReasoner(JString(spass_path))
                logger.info(
                    f"SPASSMlReasoner loaded successfully (binary: {spass_path})."
                )
            except Exception as e:
                logger.warning(f"Failed to load SPASSMlReasoner: {e}")
                raise RuntimeError(f"SPASS reasoner not available: {e}") from e
        return self._spass_reasoner

    def _get_active_reasoner(self):
        """Returns the active reasoner based on configuration."""
        if settings.modal_solver == ModalSolverChoice.SPASS:
            return self._get_spass_reasoner()
        return self._modal_reasoner

    def validate_modal_formula(self, formula_str: str) -> Tuple[bool, str]:
        """
        Validates the syntax of a modal logic formula by attempting to parse it.
        """
        logger.debug(f"Validating modal formula: '{formula_str}'")
        try:
            java_formula_str = jpype.JClass("java.lang.String")(formula_str)
            self._modal_parser.parseFormula(java_formula_str)
            return True, "Formula syntax is valid."
        except jpype.JException as e:
            error_message = f"Invalid modal formula syntax: {e.getMessage()}"
            logger.warning(error_message)
            return False, error_message
        except Exception as e:
            logger.error(
                f"Unexpected error validating modal formula '{formula_str}': {e}",
                exc_info=True,
            )
            return False, "An unexpected error occurred during validation."

    def execute_modal_query(self, belief_set_content: str, query_string: str) -> str:
        """
        Executes a modal logic query against a given belief set.
        Uses the configured reasoner (SimpleMlReasoner or SPASSMlReasoner).
        """
        reasoner = self._get_active_reasoner()
        reasoner_name = (
            type(reasoner).__name__
            if hasattr(reasoner, "__class__")
            else settings.modal_solver.value
        )
        logger.debug(f"Executing modal query '{query_string}' with {reasoner_name}")
        try:
            StringReader = jpype.JClass("java.io.StringReader")

            # Parse belief set
            belief_set_reader = StringReader(belief_set_content)
            belief_set = self._modal_parser.parseBeliefBase(belief_set_reader)

            # Parse query
            query_formula = self._modal_parser.parseFormula(
                jpype.JClass("java.lang.String")(query_string)
            )

            # Execute query
            result = reasoner.query(belief_set, query_formula)

            if bool(result):
                return f"Tweety Result ({reasoner_name}): Modal Query '{query_string}' is ACCEPTED (True)."
            else:
                return f"Tweety Result ({reasoner_name}): Modal Query '{query_string}' is REJECTED (False)."

        except jpype.JException as e:
            error_msg = f"Error executing modal query: {e.getMessage()}"
            logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"
        except Exception as e:
            error_msg = (
                f"An unexpected error occurred during modal query execution: {e}"
            )
            logger.error(error_msg, exc_info=True)
            return f"FUNC_ERROR: {error_msg}"

    def is_modal_kb_consistent(self, belief_set_content: str) -> Tuple[bool, str]:
        """
        Checks if a modal logic knowledge base is consistent.
        Uses the configured reasoner (SimpleMlReasoner or SPASSMlReasoner).
        """
        reasoner = self._get_active_reasoner()
        logger.debug(
            f"Checking modal KB consistency with {settings.modal_solver.value}."
        )
        try:
            StringReader = jpype.JClass("java.io.StringReader")
            belief_set_reader = StringReader(belief_set_content)
            belief_set = self._modal_parser.parseBeliefBase(belief_set_reader)

            is_consistent = reasoner.isConsistent(belief_set)

            message = (
                "Knowledge base is consistent."
                if is_consistent
                else "Knowledge base is inconsistent."
            )
            return bool(is_consistent), message

        except jpype.JException as e:
            if "no method found" in str(e).lower():
                logger.warning(
                    "The 'isConsistent' method is not available on the ModalReasoner. "
                    "Reporting unverified status instead of assuming consistent (#961)."
                )
                return None, "Consistency check unavailable: method not found on reasoner."

            error_msg = f"Error checking modal KB consistency: {e.getMessage()}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during consistency check: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
