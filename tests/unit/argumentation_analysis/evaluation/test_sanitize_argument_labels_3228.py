"""#3228 — the four AF containers carry the argument text in a display key.

``argument_labels`` (``{node: label}``) is where the argument TEXT travels
since #3009/#3014 moved the node identity to ``arg_N`` ids: the four
producers (``add_dung_framework``, ``add_ranking_result``, ``add_aspic_result``,
``add_belief_revision_result``) store the label map beside the id list, and
the live render resolves it into prose. The key sat in no sanitize_state
table, so it traversed intact: measured on the stored states, **720/720
labels survive byte-identical and every one equals an
``identified_arguments`` value** — the exact text the scrubber strips one
field away (0 survives there).

Reader census (the issue's decision rule): NO production reader reads
``argument_labels`` from a sanitized export — the five ``.analysis_kb``
consumers never touch it; the only reader (``act3_conclusion_plugin.py``)
resolves labels on the LIVE state during the run. The gesture therefore
follows ``_OPAQUE_DICT_VALUES`` (``source_metadata``): keys are the raw
``arg_N`` join and stay (``native_dung.rejected_by_arg`` reads them — do not
opacify the keys), values are opacified so same-text linkage across the four
containers survives and no verbatim label remains.

This witness is born red on the unrepaired module: the canary label survives,
the keys must not move.
"""

from __future__ import annotations

from typing import Any

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

# Synthetic strings invented for this witness — they appear in no corpus.
_LABEL = "CANARY_3228 le libelle integral de l'unite que le sanitiseur doit opacifier"
_NODES = ("arg_1", "arg_2")


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3228")


def _state_with_all_four_containers() -> UnifiedAnalysisState:
    """Plant the label map through each of the four real producer paths.

    Mirrors the writer sites (``state_writers.py``), never a hand-built
    container dict (the #1664 anti-pattern).
    """
    state = UnifiedAnalysisState("texte synthetique sans valeur de corpus")
    labels = {node: _LABEL for node in _NODES}
    state.add_dung_framework(
        "synthetic frame",
        arguments=list(_NODES),
        attacks=[[_NODES[0], _NODES[1]]],
        argument_labels=labels,
    )
    state.add_ranking_result(
        "synthetic method",
        arguments=list(_NODES),
        comparisons=[{"a": _NODES[0], "b": _NODES[1]}],
        argument_labels=labels,
    )
    state.add_aspic_result(
        "synthetic reasoner",
        extensions=[[_NODES[0]]],
        statistics={"synthetic": 1},
        argument_labels=labels,
    )
    state.add_belief_revision_result(
        "synthetic revision",
        original=[_NODES[0]],
        revised=[_NODES[1]],
        argument_labels=labels,
    )
    return state


def _label_maps(out: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every ``argument_labels`` map in the sanitized output, with its container."""
    found: list[tuple[str, dict[str, Any]]] = []
    for field in (
        "dung_frameworks",
        "ranking_results",
        "aspic_results",
        "belief_revision_results",
    ):
        container = out.get(field) or {}
        entries = container.values() if isinstance(container, dict) else container
        for entry in entries:
            if isinstance(entry, dict) and isinstance(
                entry.get("argument_labels"), dict
            ):
                found.append((field, entry["argument_labels"]))
    return found


class TestArgumentLabelsAreOpacified:
    def test_no_verbatim_label_survives(self) -> None:
        maps = _label_maps(
            sanitize_state(_state_with_all_four_containers().get_state_snapshot())
        )
        assert maps, (
            "no argument_labels map reached the sanitized output — the witness "
            "is vacuous (producer shapes changed?)"
        )
        for field, mapping in maps:
            for node, value in mapping.items():
                assert value != _LABEL, (
                    f"the verbatim label survived in {field}[{node!r}] — the "
                    "text the scrubber strips in identified_arguments one "
                    "field away (#3228)"
                )

    def test_the_node_keys_survive_unchanged(self) -> None:
        """The control: the fix cannot be « drop the map » — ``arg_N`` keys are
        the join #3009 introduced (``native_dung.rejected_by_arg`` reads them)."""
        maps = _label_maps(
            sanitize_state(_state_with_all_four_containers().get_state_snapshot())
        )
        assert len(maps) >= 4, "a container lost its argument_labels map entirely"
        for _field, mapping in maps:
            assert set(mapping) == set(_NODES), (
                "the node keys moved — only the values may change (#3228 "
                "anti-pendulum)"
            )
