"""#2346, section "Naming / sémantique": a name or a field promises what the
code does not do.

- The argument map printed a stance for every argument, but no producer
  computes one. ``_infer_stance`` voted on keywords of the argument's
  description, which is the narration verb ("He claims …" gave ``pro``,
  "The claim is false" too), and ``neutral`` meant "no keyword", not "takes
  no side". Measured on 601 arguments from 9 local analysis states: 521
  ``neutral`` (87 %), the other 80 decided by the verb or by transcript
  markup. The field goes, as ``attacks`` did in #2134: the map carries what
  the state holds.
- ``strategic_bridge._scrub_dict`` deleted keys from the dict it was given.
  Both callers were safe (one deep-copies first, the other builds a fresh
  dict of strings); the next one would have scrubbed the analysis state
  itself. It now returns a scrubbed copy and reaches dicts at any depth of
  nested lists.
"""

import copy
from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    ArgumentMapEntry,
    DeepSynthesisReport,
)
from argumentation_analysis.core.strategic_bridge import _scrub_dict

# Descriptions whose only "stance" cue is a narration verb or a negation.
_ARGS = {
    "arg_1": "The speaker's claim is false",
    "arg_2": "They argue against the reform",
    "arg_3": "He claims the plan worked",
}


def _state():
    return SimpleNamespace(
        identified_arguments=dict(_ARGS),
        identified_fallacies={},
        counter_arguments=[],
    )


class TestArgumentMapAssertsNoStance:
    def test_entries_carry_no_stance(self):
        amap = DeepSynthesisAgent._build_argument_map(_state())
        assert [e.arg_id for e in amap] == list(_ARGS)
        for entry in amap:
            assert set(vars(entry)) == {"arg_id", "description", "attacked_by"}

    def test_rendered_map_has_no_stance_column(self):
        report = DeepSynthesisReport()
        report.argument_map = DeepSynthesisAgent._build_argument_map(_state())
        md = DeepSynthesisAgent.render_markdown(report)
        section = md.split("## 2. Argument Map", 1)[1].split("## 3.", 1)[0]
        assert "| ID | Description | Attacked by |" in section
        assert "Stance" not in section
        # One data row per argument, three cells each.
        rows = [r for r in section.splitlines() if r.startswith("| `arg_")]
        assert len(rows) == 3
        for row in rows:
            assert row.count("|") == 4
            assert "| pro |" not in row and "| con |" not in row

    def test_exported_map_has_no_stance_key(self):
        report = DeepSynthesisReport()
        report.argument_map = DeepSynthesisAgent._build_argument_map(_state())
        exported = report.to_dict()["argument_map"]
        assert len(exported) == 3
        assert all("stance" not in e for e in exported)

    def test_keyword_vote_is_gone(self):
        assert not hasattr(DeepSynthesisAgent, "_infer_stance")

    def test_description_and_attacks_still_mapped(self):
        """Control: the rest of the map is untouched."""
        state = _state()
        state.identified_fallacies = {"f1": {"target_argument_id": "arg_2"}}
        amap = {e.arg_id: e for e in DeepSynthesisAgent._build_argument_map(state)}
        assert amap["arg_2"].description == _ARGS["arg_2"]
        assert amap["arg_2"].attacked_by == ["fallacy_f1"]
        assert amap["arg_1"].attacked_by == []
        assert isinstance(amap["arg_1"], ArgumentMapEntry)


class TestScrubDictLeavesItsInputAlone:
    def _payload(self):
        return {
            "id": "obj-1",
            "source_name": "SECRET_SOURCE",
            "nested": {"author": "SECRET_AUTHOR", "keep": 1},
            "items": [{"raw_text": "SECRET_TEXT", "keep": 2}, "plain"],
            "deep": [[{"full_text": "SECRET_FULL", "keep": 3}]],
        }

    def test_input_is_not_mutated(self):
        payload = self._payload()
        before = copy.deepcopy(payload)
        _scrub_dict(payload)
        assert payload == before

    def test_privacy_keys_removed_at_every_depth(self):
        out = _scrub_dict(self._payload())
        assert "SECRET" not in repr(out)
        assert out == {
            "id": "obj-1",
            "nested": {"keep": 1},
            "items": [{"keep": 2}, "plain"],
            "deep": [[{"keep": 3}]],
        }

    def test_non_privacy_content_kept(self):
        """Control: keys outside the strip list and non-dict values survive."""
        out = _scrub_dict({"a": 1, "b": [1, "x"], "c": {"d": None}})
        assert out == {"a": 1, "b": [1, "x"], "c": {"d": None}}
