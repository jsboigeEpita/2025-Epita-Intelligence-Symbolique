"""
RA-2 #1047 — Value-gates for summer-2025 3-way deep-descent validation.

These gates codify the finding that guided progressive descent reaches
taxonomy nodes that neither 0-shot instinct nor unguided function-calling
can reach. The reference cases come from the EPITA validation demo
(examples/03_demos_overflow/validation/validation_complete_epita.py).

Reference cases (depth 4-5):
- PK 179 "Question piège" (depth 5)
- PK 677 "Pente glissante" (depth 5)
- PK 61 "Argument par le scénario" (depth 4)
- PK 168 "Homme de paille" (depth 5)

Gates:
- VG-RA2-1: Guided workflow reaches depth >= 4 on reference cases
- VG-RA2-2: Guided workflow finds the expected PK or a descendant
- VG-RA2-3: Taxonomy infrastructure loads deep nodes (depth >= 5)

Markers: requires_api (LLM calls), llm_light (single-case smoke)
"""

import pytest

from pathlib import Path

# Auto-skip if API keys unavailable
pytestmark = [
    pytest.mark.requires_api,
    pytest.mark.llm_light,
]

# Reference cases from EPITA validation
REFERENCE_CASES = [
    {
        "test_name": "Question Piège",
        "dialogue": "As-tu arrêté de manipuler les chiffres ?",
        "expected_pk": 179,
        "expected_name": "Question piège",
        "min_depth": 4,
    },
    {
        "test_name": "Pente Glissante",
        "dialogue": "Si on autorise les trottinettes, demain ce sera les motos.",
        "expected_pk": 677,
        "expected_name": "Pente glissante",
        "min_depth": 4,
    },
    {
        "test_name": "Argument par le Scénario",
        "dialogue": "Il a acheté une pelle. Son voisin a disparu. C'est évident.",
        "expected_pk": 61,
        "expected_name": "Argument par le scénario",
        "min_depth": 4,
    },
    {
        "test_name": "Homme de Paille",
        "dialogue": "Les écolos veulent nous faire revenir à l'âge de pierre.",
        "expected_pk": 168,
        "expected_name": "Homme de paille",
        "min_depth": 4,
    },
]


class TestTaxonomyInfrastructure:
    """VG-RA2-3: Taxonomy loads deep nodes correctly."""

    def test_taxonomy_full_has_deep_nodes(self):
        """taxonomy_full.csv must contain nodes at depth >= 5."""
        import csv
        from pathlib import Path

        taxonomy_path = (
            Path(__file__).parent.parent.parent.parent
            / "argumentation_analysis"
            / "data"
            / "taxonomy_full.csv"
        )

        if not taxonomy_path.exists():
            pytest.skip("taxonomy_full.csv not found")

        max_depth = 0
        reference_pks = {case["expected_pk"] for case in REFERENCE_CASES}
        found_pks = set()

        with open(taxonomy_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=",")
            for row in reader:
                try:
                    depth = int(row.get("depth", 0))
                    max_depth = max(max_depth, depth)
                    pk = int(row.get("PK", 0))
                    if pk in reference_pks:
                        found_pks.add(pk)
                except (ValueError, TypeError):
                    continue

        assert max_depth >= 5, f"Taxonomy max depth is {max_depth}, expected >= 5"

    def test_reference_pks_exist_in_taxonomy(self):
        """All reference case PKs must exist in taxonomy_full.csv."""
        import csv
        from pathlib import Path

        taxonomy_path = (
            Path(__file__).parent.parent.parent.parent
            / "argumentation_analysis"
            / "data"
            / "taxonomy_full.csv"
        )

        if not taxonomy_path.exists():
            pytest.skip("taxonomy_full.csv not found")

        all_pks = set()
        with open(taxonomy_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=",")
            for row in reader:
                try:
                    all_pks.add(int(row.get("PK", 0)))
                except (ValueError, TypeError):
                    continue

        for case in REFERENCE_CASES:
            assert (
                case["expected_pk"] in all_pks
            ), f"PK {case['expected_pk']} ({case['expected_name']}) not found in taxonomy"

    def test_reference_pks_at_expected_depth(self):
        """Reference PKs must be at depth >= 4."""
        import csv
        from pathlib import Path

        taxonomy_path = (
            Path(__file__).parent.parent.parent.parent
            / "argumentation_analysis"
            / "data"
            / "taxonomy_full.csv"
        )

        if not taxonomy_path.exists():
            pytest.skip("taxonomy_full.csv not found")

        pk_depths = {}
        with open(taxonomy_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=",")
            for row in reader:
                try:
                    pk_depths[int(row.get("PK", 0))] = int(row.get("depth", 0))
                except (ValueError, TypeError):
                    continue

        for case in REFERENCE_CASES:
            pk = case["expected_pk"]
            assert pk in pk_depths, f"PK {pk} not found in taxonomy"
            assert pk_depths[pk] >= case["min_depth"], (
                f"PK {pk} ({case['expected_name']}) at depth {pk_depths[pk]}, "
                f"expected >= {case['min_depth']}"
            )


class TestExploreHierarchyPrimitive:
    """Verify _internal_explore_hierarchy can reach deep nodes."""

    def test_explore_hierarchy_reaches_depth_5(self):
        """_internal_explore_hierarchy should navigate to depth >= 5 iteratively.

        #2401: this guard imported ``InformalFallacyDefinitions`` (a name that
        never existed) and read ``taxonomy_df`` (no such attribute), turning
        the ImportError into a skip — it skipped on every run since #1055.
        Pointed at the real class, it measured depth 0: the root had no
        children. A missing primitive now fails here instead of vanishing.
        """
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            InformalAnalysisPlugin,
        )

        plugin = InformalAnalysisPlugin()
        df = plugin._get_taxonomy_dataframe()
        assert df is not None and not df.empty, "the taxonomy CSV must load"

        current_pk = 0  # root
        max_depth_reached = 0

        for _ in range(10):  # max 10 levels of descent
            result = plugin._internal_explore_hierarchy(current_pk, df)
            assert not result.get("error"), result.get("error")

            max_depth_reached = max(max_depth_reached, result["current_node"]["depth"])

            children = result.get("children", [])
            if not children:
                break
            current_pk = int(children[0]["pk"])

        assert max_depth_reached >= 5, (
            f"Hierarchy exploration only reached depth {max_depth_reached}, "
            f"expected >= 5 (capability to descend iteratively)"
        )


class TestGuidedDescentDepthGate:
    """
    VG-RA2-1: Guided workflow reaches depth >= 4 on reference cases.

    These tests require LLM access. They verify that the guided descent
    workflow (when properly conducted) reaches deeper taxonomy nodes than
    flat classification.

    NOTE: These are value-gates, not unit tests. They may fail if the
    LLM is unavailable or if the descent prompt has been degraded.
    A failure here is a REGRESSION SIGNAL for prompt/tier changes.
    """

    @pytest.fixture
    def fallacy_workflow(self):
        # #2290: this fixture called FallacyWorkflowPlugin() with no arguments
        # while the constructor has required master_kernel/llm_service since
        # #675 — every one of the 8 production call sites passes them. The
        # drift survived because this band (requires_api) ran in no lane: the
        # per-push gate deselects it and nobody ran it by hand. The scheduled
        # lane (#2286) caught it on its first fire.
        #
        # NOT mocked: these are value-gates on real descent behaviour. A mock
        # here would make them pass while measuring nothing — the false green
        # this lane exists to end.
        #
        # #2391: the client comes from the single constructor, like every
        # production client. This fixture used to copy fallacy_benchmark's
        # bare ``AsyncOpenAI(...)`` and called that "production" — but the
        # bare client skipped ReasoningEffortTransport (#2387), so on the
        # default route every descent call got a 400 and the gate stayed red
        # while the pipeline itself was repaired (run 35783217532).
        import os

        try:
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

            from argumentation_analysis.core.utils.network_utils import (
                build_async_openai_client,
            )
            from argumentation_analysis.plugins.fallacy_workflow_plugin import (
                FallacyWorkflowPlugin,
            )
        except ImportError as exc:
            pytest.skip(f"FallacyWorkflowPlugin stack not importable: {exc}")

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            pytest.skip("OPENAI_API_KEY unset — value-gates need a real LLM")

        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")

        llm_service = OpenAIChatCompletion(
            ai_model_id=model_id,
            async_client=build_async_openai_client(api_key=api_key, base_url=base_url),
        )
        kernel = Kernel()
        kernel.add_service(llm_service)

        # #2290: every production call site passes a taxonomy source; without
        # one the navigator is empty ("taxonomy_state=none"), the wide-net
        # resolves 0 PKs and the plugin falls back to one-shot — depth 1 by
        # construction. The fixture used to omit it, so the gate measured the
        # fallback, not the descent it claims to gate.
        taxonomy_path = (
            Path(__file__).parent.parent.parent.parent
            / "argumentation_analysis"
            / "data"
            / "taxonomy_full.csv"
        )
        if not taxonomy_path.exists():
            pytest.skip("taxonomy_full.csv not found")

        plugin = FallacyWorkflowPlugin(
            master_kernel=kernel,
            llm_service=llm_service,
            taxonomy_file_path=str(taxonomy_path),
        )
        assert plugin.taxonomy_state == "loaded", (
            f"Fixture regression: taxonomy_state={plugin.taxonomy_state!r} — "
            "the gate would measure the one-shot fallback, not the descent"
        )
        return plugin

    async def test_smoke_single_reference_case(self, fallacy_workflow):
        """
        Smoke test: verify guided analysis can be invoked on a reference case.
        This is a lightweight gate — it just checks the workflow runs,
        not that it reaches the exact expected PK.
        """
        case = REFERENCE_CASES[0]  # Question Piège
        try:
            result = await fallacy_workflow.run_guided_analysis(
                argument_text=case["dialogue"],
            )
        except Exception as e:
            # If LLM unavailable, this is expected — not a regression
            if "api" in str(e).lower() or "key" in str(e).lower():
                pytest.skip(f"LLM API unavailable: {e}")
            raise

        # #2290: `run_guided_analysis` is async. Called without `await` (as it
        # was), it returns a coroutine — never None, never executed, no LLM
        # call. `assert result is not None` then passed on an unrun workflow in
        # 1.7s. Assert the declared return type instead: a non-empty JSON str.
        assert isinstance(result, str) and result.strip(), (
            f"run_guided_analysis should return a non-empty JSON string, got "
            f"{type(result).__name__}: {result!r}"
        )

    async def test_guided_reaches_deeper_than_flat(self, fallacy_workflow):
        """
        VG-RA2-1: On reference text, guided analysis should reach
        taxonomy depth >= 2 (deeper than flat depth-1 families).

        #2290: the xfail is REMOVED. The old 3-pass/2-flake signature was not
        descent instability — it was the fixture's empty navigator forcing
        one-shot (depth 1 by construction) while the gate's
        `if isinstance(result, dict)` branch silently skipped the assertion
        whenever the one-shot LLM returned non-JSON (a vacuous PASS). With the
        taxonomy source in the fixture and `depth` serialized on
        IdentifiedFallacy, this gate measures the real funnel and fails loud
        on every degenerate shape.
        """
        case = REFERENCE_CASES[0]  # Question Piège
        try:
            result = await fallacy_workflow.run_guided_analysis(
                argument_text=case["dialogue"],
            )
        except Exception as e:
            if "api" in str(e).lower() or "key" in str(e).lower():
                pytest.skip(f"LLM API unavailable: {e}")
            raise

        if isinstance(result, str):
            import json

            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                pytest.fail(f"run_guided_analysis returned non-JSON: {result[:200]!r}")

        if not isinstance(result, dict):
            pytest.fail(
                f"run_guided_analysis returned {type(result).__name__}, expected "
                "a dict after JSON parse — the vacuous-pass hole is closed"
            )

        fallacies = result.get("fallacies", [])
        assert fallacies, (
            f"Guided analysis identified no fallacy "
            f"(exploration_method={result.get('exploration_method', '?')!r})"
        )

        depths = [
            f["depth"]
            for f in fallacies
            if isinstance(f, dict) and isinstance(f.get("depth"), int)
        ]
        assert depths, (
            "No identified fallacy carries an int `depth` — the descent "
            "confirmed no taxonomy node "
            f"(exploration_method={result.get('exploration_method', '?')!r}); "
            "the gate refuses to score the one-shot fallback as a descent"
        )

        max_depth = max(depths)
        assert max_depth >= 2, (
            f"Guided descent only reached depth {max_depth}, "
            f"expected >= 2 (deeper than flat depth-1)"
        )

    def test_identified_fallacy_serializes_depth(self):
        """#2290 kill-set: the depth field exists, serializes, and defaults
        to None (not a fabricated 1) — the structural precondition for the
        depth gate above to measure anything at all."""
        import json

        from argumentation_analysis.plugins.identification_models import (
            IdentifiedFallacy,
        )

        confirmed = IdentifiedFallacy(
            fallacy_type="Question piège",
            taxonomy_pk="179",
            explanation="opaque synthetic",
            depth=4,
        )
        assert confirmed.depth == 4
        assert json.loads(confirmed.model_dump_json())["depth"] == 4

        bare = IdentifiedFallacy(
            fallacy_type="x", taxonomy_pk="1", explanation="opaque synthetic"
        )
        assert bare.depth is None, (
            "one-shot identifications must carry depth=None, never a "
            "fabricated 1 — None is the honest 'not measured' signal"
        )


class TestCompareDetectionModes:
    """
    VG-RA2-2: Verify the 3-way comparison infrastructure.

    The comparison script (scripts/compare_fallacy_detection_modes.py)
    runs fallacy detection in 3 modes:
    - A: 0-shot raw (no taxonomy)
    - B: 0-shot + taxonomy function-calling
    - C: Guided workflow (progressive descent)

    The gate asserts: depth(C) > depth(A) and depth(C) > depth(B)
    """

    def test_compare_script_exists_and_importable(self):
        """The 3-way comparison script must exist and be importable."""
        from pathlib import Path

        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts"
            / "compare_fallacy_detection_modes.py"
        )
        assert (
            script_path.exists()
        ), "3-way comparison script not found at scripts/compare_fallacy_detection_modes.py"

    def test_comparison_modes_defined(self):
        """The script must define the 3 comparison modes."""
        from pathlib import Path

        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts"
            / "compare_fallacy_detection_modes.py"
        )
        content = script_path.read_text(encoding="utf-8")

        # Check that the script mentions the 3 modes
        assert (
            "0-shot" in content or "zero_shot" in content
        ), "Script must reference 0-shot mode"
        assert (
            "taxonomy" in content.lower()
        ), "Script must reference taxonomy-based mode"
        assert (
            "guided" in content.lower() or "workflow" in content.lower()
        ), "Script must reference guided/workflow mode"
