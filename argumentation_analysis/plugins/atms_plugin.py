"""
ATMS Semantic Kernel Plugin.

Wraps argumentation_analysis.services.jtms.atms_core.ATMS into 4 @kernel_function
methods for assumption-based reasoning within the Semantic Kernel agent framework.

Unlike the JTMS plugin, this is synchronous and stateless-per-instance — the ATMS
core is pure Python with no JVM dependency.
"""

import json
import logging
from typing import Annotated, Optional

try:
    from semantic_kernel.functions import kernel_function

    SK_AVAILABLE = True
except ImportError:

    def kernel_function(name=None, description=None):
        def decorator(func):
            func._sk_function_name = name or func.__name__
            func._sk_function_description = description or func.__doc__
            return func

        return decorator

    SK_AVAILABLE = False

from argumentation_analysis.services.jtms.atms_core import ATMS

logger = logging.getLogger(__name__)


class ATMSPlugin:
    """Semantic Kernel plugin exposing ATMS assumption-based reasoning.

    Provides 4 kernel functions:
        - atms_create_assumption  — declare an assumption node
        - atms_add_justification  — add a derivation rule (antecedents → consequent)
        - atms_check_environment  — check which beliefs hold under given assumptions
        - atms_enumerate_labels   — list minimal assumption sets supporting a belief
    """

    def __init__(self):
        self._atms_instances: dict[str, ATMS] = {}
        self._default_key = "__default__"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, instance_id: Optional[str] = None) -> tuple[ATMS, str]:
        key = instance_id or self._default_key
        if key not in self._atms_instances:
            self._atms_instances[key] = ATMS()
            logger.debug("Created ATMS instance '%s'", key)
        return self._atms_instances[key], key

    @staticmethod
    def _json_result(success: bool, data: dict = None, error: str = None) -> str:
        return json.dumps(
            {"success": success, **(data or {}), **({"error": error} if error else {})}
        )

    # ------------------------------------------------------------------
    # Kernel functions
    # ------------------------------------------------------------------

    @kernel_function(
        name="atms_create_assumption",
        description="Declare an assumption node in the ATMS. Assumptions are the "
        "atomic premises whose combinations form environments.",
    )
    def atms_create_assumption(
        self,
        name: Annotated[str, "Unique name for the assumption node"],
        description: Annotated[
            str, "Human-readable description of what this assumption represents"
        ] = "",
        instance_id: Annotated[
            Optional[str], "ATMS instance to use (default: shared instance)"
        ] = None,
    ) -> str:
        try:
            atms, _ = self._get_or_create(instance_id)
            node = atms.add_assumption(name)
            return self._json_result(
                True,
                {
                    "node": name,
                    "is_assumption": True,
                    "description": description,
                    "environments": [sorted(e) for e in node.label],
                },
            )
        except Exception as exc:
            logger.exception("atms_create_assumption failed")
            return self._json_result(False, error=str(exc))

    @kernel_function(
        name="atms_add_justification",
        description="Add a derivation rule: if all *antecedents* are derivable "
        "then *consequent* is derivable. The ATMS propagates assumption "
        "environments automatically.",
    )
    def atms_add_justification(
        self,
        consequent: Annotated[str, "Name of the conclusion node"],
        antecedents: Annotated[
            str,
            "Comma-separated list of in-node names (premises). "
            "Use empty string for an unconditional derivation.",
        ],
        out_nodes: Annotated[
            str,
            "Comma-separated list of out-node names (blocking conditions). "
            "Defaults to empty.",
        ] = "",
        instance_id: Annotated[
            Optional[str], "ATMS instance to use (default: shared instance)"
        ] = None,
    ) -> str:
        try:
            atms, _ = self._get_or_create(instance_id)
            in_names = [n.strip() for n in antecedents.split(",") if n.strip()]
            out_names = [n.strip() for n in out_nodes.split(",") if n.strip()]

            # Ensure all referenced nodes exist
            for n in in_names + out_names:
                if n not in atms.nodes:
                    atms.add_node(n)
            if consequent not in atms.nodes:
                atms.add_node(consequent)

            atms.add_justification(in_names, out_names, consequent)

            conclusion = atms.nodes[consequent]
            return self._json_result(
                True,
                {
                    "consequent": consequent,
                    "antecedents": in_names,
                    "out_nodes": out_names,
                    "resulting_environments": [sorted(e) for e in conclusion.label],
                },
            )
        except Exception as exc:
            logger.exception("atms_add_justification failed")
            return self._json_result(False, error=str(exc))

    @kernel_function(
        name="atms_check_environment",
        description="Given a set of assumptions, check which non-assumption "
        "beliefs are derivable (i.e. which nodes have an environment that is "
        "a subset of the provided assumptions).",
    )
    def atms_check_environment(
        self,
        assumptions: Annotated[
            str, "Comma-separated list of assumption names to check"
        ],
        instance_id: Annotated[
            Optional[str], "ATMS instance to use (default: shared instance)"
        ] = None,
    ) -> str:
        try:
            atms, _ = self._get_or_create(instance_id)
            assumption_set = frozenset(
                n.strip() for n in assumptions.split(",") if n.strip()
            )
            derivable = []
            for name, node in atms.nodes.items():
                if node.is_assumption or name == "\u22a5":
                    continue
                for env in node.label:
                    if env.issubset(assumption_set):
                        derivable.append(
                            {"belief": name, "supporting_environment": sorted(env)}
                        )
                        break  # one matching env is enough
            return self._json_result(
                True,
                {
                    "assumptions_checked": sorted(assumption_set),
                    "derivable_beliefs": derivable,
                    "is_consistent": atms.is_consistent(assumption_set),
                },
            )
        except Exception as exc:
            logger.exception("atms_check_environment failed")
            return self._json_result(False, error=str(exc))

    @kernel_function(
        name="atms_enumerate_labels",
        description="List all minimal assumption environments under which a "
        "given belief can be derived. Each environment is a frozenset of "
        "assumption names.",
    )
    def atms_enumerate_labels(
        self,
        belief: Annotated[str, "Name of the node to query"],
        instance_id: Annotated[
            Optional[str], "ATMS instance to use (default: shared instance)"
        ] = None,
    ) -> str:
        try:
            atms, _ = self._get_or_create(instance_id)
            explanation = atms.explain_node(belief)
            return self._json_result(
                True,
                {
                    "belief": belief,
                    "is_assumption": explanation["is_assumption"],
                    "minimal_environments": explanation["environments"],
                    "justifications": explanation["justifications"],
                },
            )
        except KeyError:
            return self._json_result(False, error=f"Node '{belief}' not found in ATMS")
        except Exception as exc:
            logger.exception("atms_enumerate_labels failed")
            return self._json_result(False, error=str(exc))
