"""#3453 — a descent that confirms one measured and one unmeasured fallacy.

Since #3029 ``IdentifiedFallacy.confidence`` is ``Optional[float]``: ``None``
is a reply that measured nothing. #3029 made the dedup comparators None-safe
(``confidence_outranks``) but left the final ordering of
``run_guided_analysis`` as ``identified.sort(key=lambda f: f.confidence)`` —
two confirmations, one measured and one not, raised ``TypeError`` there, and
the method's ``except`` returned ``{"error": ..., "fallacies": []}``: every
confirmation of the descent dropped after its calls were paid. Measured on the
panel pipeline logs: 6 occurrences on cycle 2, 9 on cycle 3.

Born red on ``a0acb7e94``: ``confidence_sort_key`` does not exist, and the
real ``run_guided_analysis`` returns an empty list with the error.
"""

import ast
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, create_autospec

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)
from argumentation_analysis.plugins.identification_models import IdentifiedFallacy

ROOT = Path(__file__).resolve().parents[4]
PLUGINS_DIR = ROOT / "argumentation_analysis" / "plugins"


def _taxonomy():
    def node(pk, name):
        return {
            "PK": pk,
            "path": pk,
            "depth": "1",
            "text_fr": name,
            "text_en": name,
            "desc_fr": name,
            "desc_en": name,
            "Famille": "test",
            "Sous-Famille": name,
            "nom_vulgarisé": name,
            "example_fr": "",
            "example_en": "",
        }

    return [node("9", "Appel à la peur"), node("10", "Faux dilemme")]


def _confirmed(pk, name, confidence):
    return IdentifiedFallacy(
        fallacy_type=pk,
        taxonomy_pk=pk,
        taxonomy_path=pk,
        explanation=f"{name} confirmed",
        problematic_quote="",
        confidence=confidence,
        navigation_trace=[pk],
    )


def _plugin_with_two_branches(first_confidence, second_confidence):
    """The real plugin; only the two branch descents are scripted.

    Wide net names both roots; each branch descent returns one confirmed
    fallacy. Everything after the gather — dedup, ordering, result building —
    is the production code path.
    """
    plugin = FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=MagicMock(),
        taxonomy_data=_taxonomy(),
    )
    plugin._wide_net_candidates = AsyncMock(return_value=["9", "10"])
    plugin._create_slave_kernel = create_autospec(
        plugin._create_slave_kernel,
        return_value=(
            create_autospec(Kernel, instance=True),
            create_autospec(OpenAIPromptExecutionSettings, instance=True),
        ),
    )
    plugin._explore_single_branch = AsyncMock(
        side_effect=[
            _confirmed("9", "Appel à la peur", first_confidence),
            _confirmed("10", "Faux dilemme", second_confidence),
        ]
    )
    return plugin


async def _run(plugin):
    return json.loads(
        await plugin.run_guided_analysis("Ou bien vous nous suivez, ou bien le chaos.")
    )


class TestTheDescentKeepsItsConfirmations:
    async def test_measured_and_unmeasured_both_survive_measured_first(self):
        parsed = await _run(_plugin_with_two_branches(None, 0.8))
        assert (
            "error" not in parsed
        ), f"#3453: the ordering raised: {parsed.get('error')}"
        pks = [f["taxonomy_pk"] for f in parsed["fallacies"]]
        assert pks == ["10", "9"], pks
        assert parsed["fallacies"][0]["confidence"] == 0.8
        assert parsed["fallacies"][1]["confidence"] is None

    async def test_two_measured_still_sort_descending(self):
        parsed = await _run(_plugin_with_two_branches(0.4, 0.9))
        assert [f["confidence"] for f in parsed["fallacies"]] == [0.9, 0.4]

    async def test_two_unmeasured_keep_their_order(self):
        parsed = await _run(_plugin_with_two_branches(None, None))
        assert [f["taxonomy_pk"] for f in parsed["fallacies"]] == ["9", "10"]


class TestTheKey:
    def test_the_key_ranks_measured_above_unmeasured(self):
        from argumentation_analysis.plugins.identification_models import (
            confidence_sort_key,
        )

        values = [None, 0.2, 0.9, None, 0.5]
        ordered = sorted(values, key=confidence_sort_key, reverse=True)
        assert ordered == [0.9, 0.5, 0.2, None, None]


class TestTheCensus:
    def test_no_plugin_sort_keys_on_a_bare_confidence_attribute(self):
        """A ``sort``/``sorted`` whose key reads ``<x>.confidence`` (AST nodes).

        The attribute form is the Optional model field; a dict ``["confidence"]``
        is another producer's contract and is out of scope here.
        """
        offenders = []
        for path in sorted(PLUGINS_DIR.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for call in ast.walk(tree):
                if not isinstance(call, ast.Call):
                    continue
                func = call.func
                name = getattr(func, "attr", None) or getattr(func, "id", None)
                if name not in ("sort", "sorted"):
                    continue
                for kw in call.keywords:
                    if kw.arg != "key" or not isinstance(kw.value, ast.Lambda):
                        continue
                    body = kw.value.body
                    if isinstance(body, ast.Attribute) and body.attr == "confidence":
                        offenders.append(f"{path.relative_to(ROOT)}:{call.lineno}")
        assert offenders == [], offenders
