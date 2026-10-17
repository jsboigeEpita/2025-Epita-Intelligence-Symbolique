import itertools
import jpype
import logging
from typing import List, Dict, Any, Set, Optional, Tuple

from .tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)


# Mapping from semantics name to Tweety reasoner class path.
# #1215 (FP-12): ``cf2`` removed — ``CF2Reasoner`` is NOT shipped in the vendored
# Tweety build (introspected firsthand: the FQN raises ClassNotFoundException in
# both 1.28 and 1.29; no SimpleCF2Reasoner / prover.* variant exists either).
# Advertising it as supported while the class is absent was a false promise;
# honest gate-out instead of a silent {"error": ...} dressed as a result.
SEMANTICS_REASONERS = {
    "preferred": "org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner",
    "grounded": "org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner",
    "stable": "org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner",
    "complete": "org.tweetyproject.arg.dung.reasoner.SimpleCompleteReasoner",
    "admissible": "org.tweetyproject.arg.dung.reasoner.SimpleAdmissibleReasoner",
    "conflict_free": "org.tweetyproject.arg.dung.reasoner.SimpleConflictFreeReasoner",
    "semi_stable": "org.tweetyproject.arg.dung.reasoner.SimpleSemiStableReasoner",
    "stage": "org.tweetyproject.arg.dung.reasoner.SimpleStageReasoner",
    "ideal": "org.tweetyproject.arg.dung.reasoner.SimpleIdealReasoner",
    "naive": "org.tweetyproject.arg.dung.reasoner.SimpleNaiveReasoner",
}


# --- #3050: sized enumeration over weakly-connected components -------------
#
# Since #3017 the AF-family callables hand these reasoners frames drawn from
# the merged population (budget-capped at 40 nodes). On the standing
# one-document pass that frame is SPARSE (40 nodes, 1 attack): preferred,
# grounded, stable and complete return instantly, but the semantics that
# materialize their whole search space (admissible, conflict_free — and
# semi_stable/stage/ideal, which walk the same families) enumerate 2^N-scale
# collections until the JVM heap dies. Measured on base `f385fa662`
# (2026-10-17, real JVM, offline witness): admissible on a 40/1 frame
# exhausted the 2 GB heap after 223 s, and the executor thread kept running
# past its phase deadline (the #2080 shape). Tweety's ``Simple*`` are
# reference implementations: no bound, no refusal.
#
# The repair decomposes the frame into weakly-connected components. Dung
# semantics compose over disconnected components — every extension of the
# whole frame is the union of one extension per component — so each component
# is solved on its own (small) theory and the global models are the product:
#
# - every component within ``_DUNG_COMPONENT_MAX_NODES``: exact per-component
#   models through the SAME Simple* reasoners (each call bounded — the only
#   JVM work submitted, so no thread can outlive its phase enumerating);
# - product of the per-component counts over ``_DUNG_ENUMERATION_CEILING``:
#   the count stays exact and is reported, the enumeration is refused BY NAME
#   (never a silent ``{"error": ...}``);
# - any component over ``_DUNG_COMPONENT_MAX_NODES``: refused BEFORE any JVM
#   call, naming the component size.
#
# ``grounded`` keeps the direct single-theory call: its characteristic
# function iteration is polynomial (measured instant at 40 nodes) and
# decomposing it would change nothing.

#: A component up to this size is brute-forced by the Simple* reasoners
#: (2**16 subsets worst case — sub-second); larger ones are refused.
_DUNG_COMPONENT_MAX_NODES = 16

#: Aligned with the #2930 measured knee (512 -> 2.7 s, 1024 -> 46.7 s
#: student / 78.2 s tweety, po-2025 2026-10-04): past this many models the
#: enumeration is reported by count and refused.
_DUNG_ENUMERATION_CEILING = 1024

#: Semantics that materialize their search space; ``grounded`` is polynomial.
_ENUMERATING_SEMANTICS = frozenset(
    name for name in SEMANTICS_REASONERS if name != "grounded"
)


def weak_components(
    arguments: List[str], attacks: List[List[str]]
) -> List[Tuple[List[str], List[List[str]]]]:
    """Split a frame into weakly-connected components (#3050).

    Returns one ``(component_arguments, component_attacks)`` pair per
    component, in first-appearance order (deterministic). An attack naming an
    unknown endpoint is skipped exactly like ``AFHandler._build_framework``
    skips it, so the components always match the theory actually built.
    Isolated nodes form singleton components — that is where sparse frames
    get their 2^N product from.
    """
    index = {name: i for i, name in enumerate(arguments)}
    parent = list(range(len(arguments)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    kept: List[List[str]] = []
    for source, target in attacks:
        src, dst = index.get(source), index.get(target)
        if src is None or dst is None:
            continue
        kept.append([source, target])
        union(src, dst)

    members: Dict[int, List[str]] = {}
    for name in arguments:
        members.setdefault(find(index[name]), []).append(name)

    components: List[Tuple[List[str], List[List[str]]]] = []
    for comp_args in members.values():
        comp = set(comp_args)
        comp_attacks = [e for e in kept if e[0] in comp and e[1] in comp]
        components.append((comp_args, comp_attacks))
    return components


class AFHandler:
    """
    Handles Abstract Argumentation Framework (AF) operations using TweetyProject.
    Supports multiple Dung semantics: preferred, grounded, stable, complete,
    admissible, conflict-free, semi-stable, stage, ideal, naive.
    (CF2 is NOT shipped in the vendored Tweety build — see SEMANTICS_REASONERS.)
    """

    def __init__(self, initializer_instance: TweetyInitializer):
        self._initializer_instance = initializer_instance
        if not self._initializer_instance.is_jvm_ready():
            raise RuntimeError("AFHandler instantiated before JVM is ready.")

        # Core Java classes
        self.DungTheory = jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
        self.Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
        self.Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
        self.Extension = jpype.JClass("org.tweetyproject.arg.dung.semantics.Extension")

        # Legacy alias
        self.SimplePreferredReasoner = jpype.JClass(
            "org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner"
        )

        # Reasoner cache
        self._reasoner_cache: Dict[str, Any] = {}

    @staticmethod
    def supported_semantics() -> List[str]:
        """Returns list of supported semantics names."""
        return list(SEMANTICS_REASONERS.keys())

    def _get_reasoner(self, semantics: str):
        """
        Gets or creates a reasoner instance for the given semantics.
        Caches reasoner instances for reuse.
        """
        semantics_key = semantics.lower().replace("-", "_")
        if semantics_key not in SEMANTICS_REASONERS:
            raise ValueError(
                f"Unsupported semantics: '{semantics}'. "
                f"Supported: {', '.join(SEMANTICS_REASONERS.keys())}"
            )

        if semantics_key not in self._reasoner_cache:
            class_path = SEMANTICS_REASONERS[semantics_key]
            try:
                reasoner_cls = jpype.JClass(class_path)
                self._reasoner_cache[semantics_key] = reasoner_cls()
                logger.debug(f"Loaded reasoner for '{semantics_key}': {class_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load reasoner for '{semantics_key}' ({class_path}): {e}"
                )
                raise RuntimeError(
                    f"Reasoner for '{semantics}' not available: {e}"
                ) from e

        return self._reasoner_cache[semantics_key]

    def _build_framework(self, arguments: List[str], attacks: List[List[str]]) -> tuple:
        """
        Builds a DungTheory from argument names and attack pairs.
        Returns (dung_theory, arg_map).
        """
        dung_theory = self.DungTheory()
        arg_map = {arg_name: self.Argument(arg_name) for arg_name in arguments}
        for arg_obj in arg_map.values():
            dung_theory.add(arg_obj)

        for source_name, target_name in attacks:
            if source_name in arg_map and target_name in arg_map:
                attack = self.Attack(arg_map[source_name], arg_map[target_name])
                dung_theory.add(attack)
            else:
                logger.warning(
                    f"Skipping invalid attack from '{source_name}' to '{target_name}'."
                )

        return dung_theory, arg_map

    def _extensions_to_python(self, extensions_java) -> List[List[str]]:
        """Converts Java Extension collection to sorted Python list of lists."""
        result = []
        for ext_java in extensions_java:
            extension_args = [str(arg.getName()) for arg in ext_java]
            result.append(sorted(extension_args))
        return sorted(result)

    def _sized_models(
        self, semantics_key: str, arguments: List[str], attacks: List[List[str]]
    ) -> Any:
        """(#3050) Exact models for an enumerating semantics, size-gated.

        Returns the enumerated extensions (``List[List[str]]``, sorted, same
        contract as :meth:`_extensions_to_python`) or a REFUSAL dict —
        ``{"error": <named reason>, "refused": True, ...}`` carrying the exact
        count when it is known — never a silent ``{"error": ...}``. See the
        module-level ``#3050`` block for the decomposition argument.
        """
        components = weak_components(arguments, attacks)
        largest = max((len(comp_args) for comp_args, _ in components), default=0)
        if largest > _DUNG_COMPONENT_MAX_NODES:
            return {
                "error": (
                    f"enumeration refused (#3050): the largest "
                    f"weakly-connected component holds {largest} nodes, over "
                    f"the {_DUNG_COMPONENT_MAX_NODES}-node enumerable bound — "
                    f"the {semantics_key} reasoner would walk its search "
                    f"space unbounded"
                ),
                "refused": True,
                "largest_component_nodes": largest,
            }

        reasoner = self._get_reasoner(semantics_key)
        per_component: List[List[List[str]]] = []
        for comp_args, comp_attacks in components:
            theory, _ = self._build_framework(comp_args, comp_attacks)
            per_component.append(self._extensions_to_python(reasoner.getModels(theory)))

        total = 1
        for models in per_component:
            total *= len(models)
        if total == 0:
            # A component with no model (e.g. stable on an even cycle) leaves
            # the whole frame without one — that IS the verdict, not a refusal.
            return []
        if total > _DUNG_ENUMERATION_CEILING:
            return {
                "error": (
                    f"enumeration refused (#3050): the frame admits exactly "
                    f"{total} {semantics_key} extensions (product over "
                    f"{len(per_component)} components), over the "
                    f"{_DUNG_ENUMERATION_CEILING}-model ceiling — the count "
                    f"is exact, the extensions are not materialized"
                ),
                "refused": True,
                "extensions_count": total,
                "per_component_counts": [len(m) for m in per_component],
            }

        combined = [
            sorted(arg for combo in combos for arg in combo)
            for combos in itertools.product(*per_component)
        ]
        return sorted(combined)

    def analyze_dung_framework(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        semantics: str = "preferred",
    ) -> Dict[str, Any]:
        """
        Analyzes a Dung-style abstract argumentation framework.

        Args:
            arguments: A list of argument names.
            attacks: A list of attacks [source, target].
            semantics: The semantics to use. Supported: preferred, grounded, stable,
                      complete, admissible, conflict_free, semi_stable, stage,
                      ideal, naive. (cf2 is NOT available in the vendored build.)

        Returns:
            Dict with keys: semantics, extensions, statistics. Enumerating
            semantics run through the #3050 sized path (component
            decomposition; over-ceiling counts are reported with a named
            refusal instead of being materialized).
        """
        semantics_key = semantics.lower().replace("-", "_")
        logger.info(
            f"Analyzing Dung framework with {len(arguments)} arguments and "
            f"{len(attacks)} attacks for '{semantics_key}' semantics."
        )

        try:
            dung_theory, arg_map = self._build_framework(arguments, attacks)

            # #3050: enumerating semantics go through the sized, decomposed
            # path; grounded stays on the direct (polynomial) call.
            if semantics_key in _ENUMERATING_SEMANTICS:
                extensions = self._sized_models(semantics_key, arguments, attacks)
            else:
                reasoner = self._get_reasoner(semantics_key)
                extensions = self._extensions_to_python(reasoner.getModels(dung_theory))

            if isinstance(extensions, dict):
                extensions_count: Optional[int] = extensions.get("extensions_count")
            else:
                extensions_count = len(extensions)

            result = {
                "semantics": semantics_key,
                "extensions": {semantics_key: extensions},
                "statistics": {
                    "arguments_count": len(arguments),
                    "attacks_count": len(attacks),
                    "extensions_count": extensions_count,
                },
            }
            logger.info(
                f"Analysis successful. Found {len(extensions)} {semantics_key} extensions."
            )
            return result

        except jpype.JException as e:
            logger.error(
                f"Java exception during Dung framework analysis: {e.stacktrace()}",
                exc_info=True,
            )
            raise RuntimeError(f"Error during framework analysis: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise

    def analyze_multi_semantics(
        self,
        arguments: List[str],
        attacks: List[List[str]],
        semantics_list: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes a framework under multiple semantics at once.

        Args:
            arguments: Argument names.
            attacks: Attack pairs.
            semantics_list: List of semantics to compute. Defaults to
                           ["grounded", "preferred", "stable", "complete"].

        Returns:
            Dict with all requested semantics results. Enumerating semantics
            run through the #3050 sized path (component decomposition;
            over-ceiling counts are reported with a named refusal instead of
            being materialized).
        """
        if semantics_list is None:
            semantics_list = ["grounded", "preferred", "stable", "complete"]

        try:
            dung_theory, arg_map = self._build_framework(arguments, attacks)
            all_extensions = {}
            statistics = {
                "arguments_count": len(arguments),
                "attacks_count": len(attacks),
            }

            for sem in semantics_list:
                sem_key = sem.lower().replace("-", "_")
                try:
                    # #3050: enumerating semantics go through the sized,
                    # decomposed path; grounded stays on the direct
                    # (polynomial) call over the whole theory.
                    if sem_key in _ENUMERATING_SEMANTICS:
                        extensions = self._sized_models(sem_key, arguments, attacks)
                    else:
                        reasoner = self._get_reasoner(sem_key)
                        extensions = self._extensions_to_python(
                            reasoner.getModels(dung_theory)
                        )
                    all_extensions[sem_key] = extensions
                    statistics[f"{sem_key}_count"] = (
                        len(extensions)
                        if isinstance(extensions, list)
                        else extensions.get("extensions_count")
                    )
                except Exception as e:
                    logger.warning(f"Failed to compute {sem_key} semantics: {e}")
                    all_extensions[sem_key] = {"error": str(e)}

            return {
                "semantics": semantics_list,
                "extensions": all_extensions,
                "statistics": statistics,
            }

        except jpype.JException as e:
            raise RuntimeError(f"Error building framework: {e}") from e

    def get_grounded_extension(
        self, arguments: List[str], attacks: List[List[str]]
    ) -> List[str]:
        """
        Convenience method: returns the unique grounded extension.
        The grounded extension is always unique (skeptical semantics).
        """
        result = self.analyze_dung_framework(arguments, attacks, "grounded")
        extensions = result["extensions"].get("grounded", [])
        return extensions[0] if extensions else []
