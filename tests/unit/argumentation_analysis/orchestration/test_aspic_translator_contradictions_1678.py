"""#1678 — ASPIC+ translator contradictions/undercuts channel + id validation.

``translate_to_aspic_rules`` previously emitted only positive ``{head, body}``
rules — there was no form in which it could say "argument M contradicts argument
N" or "objection O contests rule R". Every head and body was a positive ``arg_*``
atom, so ASPIC+ could never produce an attack (an attack needs a formula AND its
negation). #1678 adds two channels — ``contradictions`` (→ rebut/undermine,
qualified structurally by the handler) and ``undercuts`` (→ negated rule name) —
with the SAME id validation as the rules channel: any attacker/target/premise
citing an id absent from the inventory is dropped whole (anti-théâtre #1019).

These tests pin the validation contract and the channel→rule mapping. The LLM
call is mocked (no network); inputs are synthetic opaque ids.

Privacy: synthetic atoms only (arg_a, concl_x, d_main) — no corpus content.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import argumentation_analysis.orchestration.structured_arg_translator as tr


def _run(coro):
    import asyncio

    return asyncio.new_event_loop().run_until_complete(coro)


# A 3-argument inventory handed to the translator. The LLM cites arg1/arg2/arg3.
_ARGS = ["the first claim", "the opposing claim", "a side reason"]


def _llm_returning(payload):
    return AsyncMock(return_value=payload)


class TestContradictionsChannel:
    """A contradiction (attacker, target) renders as a negated-head rule."""

    def test_valid_contradiction_becomes_negated_head_rule(self):
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [
                {"attacker": "arg3", "target": "arg2", "rationale": "x"}
            ],
            "undercuts": [],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        rules = out.relations
        # 1 base rule + 1 contradiction rule.
        assert len(rules) == 2
        con = [r for r in rules if r.get("head_negated") is True]
        assert len(con) == 1, f"expected one negated-head rule, got {rules}"
        # The contradiction negates the TARGET's atom (arg2), body = attacker.
        assert con[0]["body"] and len(con[0]["body"]) == 1
        assert out.cause == tr.CAUSE_EVALUATED

    def test_contradiction_with_absent_target_id_is_dropped(self):
        """DoD item 3 — a contradiction citing an absent id is rejected whole."""
        payload = {
            "rules": [],
            "contradictions": [
                {"attacker": "arg3", "target": "arg999_absent", "rationale": "x"}
            ],
            "undercuts": [],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        # Nothing survived → no_genuine_relations, NOT a fabricated rule.
        assert out.relations == []
        assert out.cause == tr.CAUSE_NO_GENUINE_RELATIONS

    def test_contradiction_with_absent_attacker_id_is_dropped(self):
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [
                {"attacker": "ghost", "target": "arg2", "rationale": "x"}
            ],
            "undercuts": [],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        con = [r for r in out.relations if r.get("head_negated") is True]
        assert con == [], "a contradiction citing an absent attacker must be dropped"
        # The base rule survives (it is genuine).
        assert len(out.relations) == 1


class TestUndercutsChannel:
    """An undercut (attacker, target_rule) renders as a negated-rule-name rule."""

    def test_valid_undercut_targets_a_surviving_rule(self):
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [],
            "undercuts": [
                {"attacker": "arg3", "target_rule": "d_main", "rationale": "x"}
            ],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        unc = [r for r in out.relations if r.get("head_negated") is True]
        assert len(unc) == 1
        # The undercut head is the SANITIZED rule name (def_d_main), which the
        # handler will recognize as a rule-name → undercut scope.
        assert unc[0]["head"] == "def_d_main", unc[0]["head"]

    def test_undercut_targeting_an_unknown_rule_is_dropped(self):
        """DoD item 3 — an undercut must target a rule that survived validation."""
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [],
            "undercuts": [
                {"attacker": "arg3", "target_rule": "rule_that_does_not_exist"}
            ],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        unc = [r for r in out.relations if r.get("head_negated") is True]
        assert unc == [], "an undercut to an unknown rule must be dropped"
        assert len(out.relations) == 1  # base rule survives

    def test_undercut_attacker_absent_id_is_dropped(self):
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [],
            "undercuts": [{"attacker": "ghost", "target_rule": "d_main"}],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        unc = [r for r in out.relations if r.get("head_negated") is True]
        assert unc == []


class TestThreeChannelsCoexist:
    """DoD item 2 — rules + contradictions + undercuts survive together."""

    def test_all_three_channels_render_in_one_pass(self):
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [
                {"attacker": "arg3", "target": "arg2", "rationale": "x"}
            ],
            "undercuts": [
                {"attacker": "arg3", "target_rule": "d_main", "rationale": "y"}
            ],
        }
        with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
            out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        negated = [r for r in out.relations if r.get("head_negated") is True]
        # 1 contradiction + 1 undercut = 2 negated-head rules.
        assert len(negated) == 2
        # Rule names are unique (shared namespace).
        names = [r["name"] for r in out.relations]
        assert len(set(names)) == len(names), f"names must be unique, got {names}"


class Test1649DropDiagnostics:
    """#1649 (coord R783): on real corpus the handler emits 0 attack though the
    translator ran. The diagnostic counter distinguishes — without further code
    — whether the LLM emitted contradictions/undercuts that were SILENTLY
    DROPPED at validation (raw>0, kept=0), or emitted NONE (raw=0). A corpus
    run's log answers it; these tests pin the diagnostic contract.
    """

    def test_drop_diagnostic_fires_when_all_contradictions_dropped(self, caplog):
        """raw>0, kept=0 ⇒ a warning logs the drop (the 'emitted-then-dropped'
        hypothesis). This is the case that would explain 0 attack on a live axis.
        """
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [
                {"attacker": "arg3", "target": "arg999_absent", "rationale": "x"},
                {"attacker": "ghost", "target": "arg2", "rationale": "y"},
            ],
            "undercuts": [],
        }
        import logging

        with caplog.at_level(logging.WARNING, logger=tr.logger.name):
            with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
                out = _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        # Both contradictions dropped (absent ids) ⇒ no negated-head rule.
        assert [r for r in out.relations if r.get("head_negated") is True] == []
        diag = [r.message for r in caplog.records if "#1649 diagnostics" in r.message]
        assert len(diag) == 1, f"expected one #1649 diagnostics warning, got {diag}"
        msg = diag[0]
        assert "2 contradiction(s)" in msg
        assert "kept 0" in msg
        assert "dropped 2" in msg

    def test_no_diagnostic_when_llm_emitted_no_contradiction_or_undercut(self, caplog):
        """raw=0 ⇒ NO #1649 diagnostics warning (the 'LLM emitted none'
        hypothesis — silent, distinct from 'dropped'). Pin the negative so a
        corpus log showing no warning reads unambiguously as 'emitted none'.
        """
        payload = {
            "rules": [{"premises": ["arg1"], "conclusion": "arg2", "name": "d_main"}],
            "contradictions": [],
            "undercuts": [],
        }
        import logging

        with caplog.at_level(logging.WARNING, logger=tr.logger.name):
            with patch.object(tr, "_llm_extract_relations", _llm_returning(payload)):
                _run(tr.translate_to_aspic_rules("opaque text", _ARGS))

        diag = [r.message for r in caplog.records if "#1649 diagnostics" in r.message]
        assert diag == [], f"no diagnostic expected when raw=0, got {diag}"
