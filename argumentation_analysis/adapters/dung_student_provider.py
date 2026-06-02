"""Adapter for abs_arg_dung as an alternative Dung extensions provider.

Registers the student Dung library (abs_arg_dung) as a selectable provider
in ServiceDiscovery for the ``dung_extensions`` capability, alongside the
native AFHandler engine.  The student library is treated as a **sanctuary**
(never modified); this adapter wraps its public API from the outside.

Architecture:
- ``DungStudentProvider`` wraps ``EnhancedDungAgent`` via ``asyncio.to_thread``
  (the agent is synchronous JPype-based).
- Shape normalisation: converts the agent's output to the same dict format
  as the native ``_invoke_dung_extensions`` callable.
- Graceful fallback if JVM is not started or the student library is missing.

Sanctuary rule: ``abs_arg_dung/`` source is NEVER modified.  All adaptation
happens in this file.  Known issues (e.g. ``cli.py`` bare imports) are
documented but NOT patched in-place.

Issue: #893
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Semantics supported by EnhancedDungAgent (subset of the 11 in af_handler)
SUPPORTED_SEMANTICS = [
    "grounded",
    "preferred",
    "stable",
    "complete",
]


class DungStudentProvider:
    """Wraps abs_arg_dung.EnhancedDungAgent as a selectable Dung provider.

    The student library is synchronous and requires a running JVM.
    This provider wraps calls via ``asyncio.to_thread`` for async compatibility.
    """

    def __init__(self):
        self._agent = None
        self._available: Optional[bool] = None

    @property
    def provider_name(self) -> str:
        return "abs_arg_dung_student"

    @property
    def quality_score(self) -> float:
        """Quality score for ServiceDiscovery ranking.

        Lower than native AFHandler (0.8) since the student lib only
        supports 4 semantics vs 11 in the native engine.
        """
        return 0.6

    @property
    def capabilities(self) -> List[str]:
        return ["dung_extensions"]

    def is_available(self) -> bool:
        """Check if the student library is importable and JVM is running."""
        if self._available is not None:
            return self._available

        try:
            import jpype

            if not jpype.isJVMStarted():
                logger.info("DungStudentProvider: JVM not started, unavailable")
                self._available = False
                return False

            from abs_arg_dung.enhanced_agent import EnhancedDungAgent

            self._available = True
            logger.info("DungStudentProvider: available (EnhancedDungAgent importable)")
            return True
        except ImportError as e:
            logger.info(f"DungStudentProvider: import failed ({e})")
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"DungStudentProvider: unexpected error ({e})")
            self._available = False
            return False

    def _get_agent(self):
        """Lazily create the EnhancedDungAgent."""
        if self._agent is None:
            from abs_arg_dung.enhanced_agent import EnhancedDungAgent

            self._agent = EnhancedDungAgent()
        return self._agent

    def _build_framework(
        self, arguments: List[str], attacks: List[Tuple[str, str]]
    ) -> None:
        """Build the AF on the agent from arguments and attack relations.

        Clears any existing framework first (the agent reuses its internal AF).
        """
        agent = self._get_agent()

        # Clear existing framework by creating a new DungTheory
        agent.af = agent.DungTheory()

        # Add arguments
        for arg_name in arguments:
            arg = agent.Argument(arg_name)
            agent.af.add(arg)

        # Add attacks
        for attacker, attacked in attacks:
            attacker_arg = agent.Argument(attacker)
            attacked_arg = agent.Argument(attacked)
            attack = agent.Attack(attacker_arg, attacked_arg)
            agent.af.add(attack)

    def _compute_extensions_sync(
        self, arguments: List[str], attacks: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Synchronous computation — runs in thread via asyncio.to_thread."""
        self._build_framework(arguments, attacks)

        agent = self._get_agent()
        extensions = {}

        # Compute each supported semantics
        try:
            grounded = agent.get_grounded_extension()
            extensions["grounded"] = {
                "extensions": [sorted(grounded)] if grounded else [[]],
                "count": 1,
                "sizes": [len(grounded)] if grounded else [0],
                "all_members": sorted(grounded) if grounded else [],
            }
        except Exception as e:
            extensions["grounded"] = {"error": str(e)[:200]}

        try:
            preferred = agent.get_preferred_extensions()
            extensions["preferred"] = {
                "extensions": [sorted(ext) for ext in preferred],
                "count": len(preferred),
                "sizes": [len(ext) for ext in preferred],
                "all_members": sorted({a for ext in preferred for a in ext}),
            }
        except Exception as e:
            extensions["preferred"] = {"error": str(e)[:200]}

        try:
            stable = agent.get_stable_extensions()
            extensions["stable"] = {
                "extensions": [sorted(ext) for ext in stable],
                "count": len(stable),
                "sizes": [len(ext) for ext in stable],
                "all_members": sorted({a for ext in stable for a in ext}),
            }
        except Exception as e:
            extensions["stable"] = {"error": str(e)[:200]}

        try:
            complete = agent.get_complete_extensions()
            extensions["complete"] = {
                "extensions": [sorted(ext) for ext in complete],
                "count": len(complete),
                "sizes": [len(ext) for ext in complete],
                "all_members": sorted({a for ext in complete for a in ext}),
            }
        except Exception as e:
            extensions["complete"] = {"error": str(e)[:200]}

        # Statistics
        semantics_computed = len(
            [v for v in extensions.values() if "count" in v]
        )

        return {
            "provider": self.provider_name,
            "semantics": "multi",
            "extensions": extensions.get("preferred", extensions.get("grounded", {})),
            "all_extensions": extensions,
            "arguments": arguments,
            "attacks": list(attacks),
            "statistics": {
                "arguments_count": len(arguments),
                "attacks_count": len(attacks),
                "semantics_computed": semantics_computed,
                "semantics_supported": SUPPORTED_SEMANTICS,
            },
        }

    async def compute_extensions(
        self, arguments: List[str], attacks: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Async entry point for the adapter callable."""
        if not self.is_available():
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "error": "JVM not started or abs_arg_dung not importable",
            }

        return await asyncio.to_thread(
            self._compute_extensions_sync, arguments, attacks
        )


# ── Adapter callable for CapabilityRegistry ──────────────────────────────


async def invoke_dung_student(
    input_text: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Adapter callable matching the _invoke_* signature.

    Extracts arguments and attacks from context (same pattern as
    _invoke_dung_extensions in invoke_callables.py), then delegates
    to DungStudentProvider.
    """
    # Reuse the extraction helpers from invoke_callables
    from argumentation_analysis.orchestration.invoke_callables import (
        _extract_arguments_from_context,
        _generate_attacks_from_args,
    )

    arguments = _extract_arguments_from_context(input_text, context)
    attacks = _generate_attacks_from_args(arguments, context)

    provider = DungStudentProvider()
    return await provider.compute_extensions(arguments, attacks)


def register_dung_student_provider(registry) -> None:
    """Register the student Dung provider in a CapabilityRegistry.

    Usage::

        from argumentation_analysis.adapters.dung_student_provider import (
            register_dung_student_provider,
        )
        register_dung_student_provider(registry)
    """
    provider = DungStudentProvider()

    if not provider.is_available():
        logger.info(
            "DungStudentProvider not registered (JVM or library unavailable)"
        )
        return

    registry.register_service(
        name="dung_extensions_student",
        capabilities=["dung_extensions"],
        description="Dung AF extensions via abs_arg_dung student library (4 semantics)",
        callable=invoke_dung_student,
        metadata={
            "provider": "abs_arg_dung_student",
            "quality_score": provider.quality_score,
            "semantics_supported": SUPPORTED_SEMANTICS,
            "sanctuary": True,  # Never modifies abs_arg_dung/ source
        },
    )
    logger.info("DungStudentProvider registered in CapabilityRegistry")


# ── Known issues (documented, NOT patched in-place) ──────────────────────
#
# - abs_arg_dung/cli.py uses bare imports (from agent import DungAgent)
#   which break when running as a package. Workaround: import directly
#   from abs_arg_dung.enhanced_agent (which uses correct package imports).
# - abs_arg_dung/agent.py requires matplotlib and networkx at import time.
# - EnhancedDungAgent only supports 4/11 Dung semantics (grounded,
#   preferred, stable, complete) vs native AFHandler's 11.
