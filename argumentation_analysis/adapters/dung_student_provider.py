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


# Adapter-local agent class, built lazily (importing abs_arg_dung at module
# import time would require a running JVM; the module itself stays importable
# JVM-free — see test_dung_student_provider.py).
_LAZY_AGENT_CLS = None


def _lazy_agent_class():
    """Return the adapter-local EnhancedDungAgent subclass (#2921).

    The sanctuary's eager ``_compute_extensions_if_needed`` pays SEVEN
    semantics on the first getter call; this adapter consumes FOUR. Of the
    three unconsumed ones, measured on sparse synthetic AFs (a0..aN-1, no
    attacks; per-semantics timings, po-2025 2026-10-04):

    - ``SimpleIdealReasoner.getModel`` enumerates subsets internally,
      Java-side: 41.7 s at N=15; killed at the 420 s process cap at N=20
      (the dominant term of the issue's 27-minute run);
    - ``SimpleAdmissibleReasoner.getModels`` returns 2^N extensions (1 048
      576 at N=20), each then converted argument-by-argument through the
      JPype bridge by ``_format_extensions``: 362 s total at N=20 (213 s
      Java + 149 s conversion), 4.3 s at N=15.

    The four consumed semantics (grounded/preferred/stable/complete) measure
    <= 9.3 ms each at every N in {5, 10, 15, 20} on sparse AFs. The subclass
    computes exactly those four, formatting each exactly like the sanctuary
    branch it replaces; the EnhancedDungAgent corrections (perfect cycle,
    self-attack) apply unchanged on top of the cache. The sanctuary branch's
    ``print("(Calcul des extensions en cours...)")`` is deliberately not
    reproduced: it is a stdout side-effect, not part of the value contract.

    BOUNDARY — what this repair does NOT bound (#2930). On a DENSE AF the
    remaining cost is the framework's own combinatorics, paid by BOTH engines
    through Tweety's ``Simple*Reasoner``, and therefore not reachable from this
    adapter. Measured on N/2 mutual pairs (2^(N/2) preferred extensions),
    po-2025 2026-10-04, fresh process per row:

    ============  ==================  ===========  ============
    N             preferred exts      tweety       student
    ============  ==================  ===========  ============
    12            64                  0.6 s        1.6 s
    16            256                 2.3 s        2.8 s
    18            512                 2.7 s        2.7 s
    20            1024                78.2 s       46.7 s
    ============  ==================  ===========  ============

    At N=20 the dominant term is ``SimplePreferredReasoner`` alone (34.5 s
    Java, internal 2^N enumeration); ``complete`` returns 59 049 = 3^10
    extensions (the correct count, 2.2 s Java + 1.8 s bridge conversion).
    The student is FASTER than the native engine on this family — the residual
    is the field's arithmetic, not a student defect. ``_compare_dung_backends``
    reports every backend's ``elapsed_ms`` but bounds nothing (a naive
    ``asyncio.wait_for`` would be a false fix: the JPype thread is not
    killable and ``asyncio.run()`` teardown blocks on it) — see #2930.
    """
    global _LAZY_AGENT_CLS
    if _LAZY_AGENT_CLS is None:
        from abs_arg_dung.enhanced_agent import EnhancedDungAgent

        class _LazyFourSemanticsAgent(EnhancedDungAgent):
            """Computes only the 4 semantics the comparison consumes (#2921)."""

            def _compute_extensions_if_needed(self):
                if not self._cache_valid:
                    self._cached_extensions = {
                        "grounded": sorted(
                            [
                                str(arg.getName())
                                for arg in self.grounded_reasoner.getModel(self.af)
                            ]
                        ),
                        "preferred": self._format_extensions(
                            self.preferred_reasoner.getModels(self.af)
                        ),
                        "stable": self._format_extensions(
                            self.stable_reasoner.getModels(self.af)
                        ),
                        "complete": self._format_extensions(
                            self.complete_reasoner.getModels(self.af)
                        ),
                    }
                    self._cache_valid = True

        _LAZY_AGENT_CLS = _LazyFourSemanticsAgent
    return _LAZY_AGENT_CLS


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
        """Lazily create the agent (adapter-local lazy subclass, #2921)."""
        if self._agent is None:
            self._agent = _lazy_agent_class()()
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
        semantics_computed = len([v for v in extensions.values() if "count" in v])

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


# The registry adapter functions (invoke_dung_student,
# register_dung_student_provider) were withdrawn (#2116 A2): 0 production
# callers — the live access path instantiates DungStudentProvider directly
# (orchestration/invoke_callables.py).


# ── Known issues (documented, NOT patched in-place) ──────────────────────
#
# - abs_arg_dung/cli.py uses bare imports (from agent import DungAgent)
#   which break when running as a package. Workaround: import directly
#   from abs_arg_dung.enhanced_agent (which uses correct package imports).
# - abs_arg_dung/agent.py requires matplotlib and networkx at import time.
# - EnhancedDungAgent only supports 4/11 Dung semantics (grounded,
#   preferred, stable, complete) vs native AFHandler's 11.
