# tests/unit/argumentation_analysis/agents/core/debate/test_protocols.py
"""Tests for Walton-Krabbe dialogue protocols, speech acts, and propositions."""

import pytest
from argumentation_analysis.agents.core.debate.protocols import (
    DialogueType,
    SpeechAct,
    Proposition,
    FormalArgument,
    DialogueMove,
    InquiryProtocol,
    PersuasionProtocol,
)

# ── Enums ──


class TestDialogueType:
    def test_has_six_types(self):
        assert len(DialogueType) == 6

    def test_values(self):
        expected = {
            "information_seeking",
            "inquiry",
            "persuasion",
            "negotiation",
            "deliberation",
            "eristic",
        }
        assert {t.value for t in DialogueType} == expected


class TestSpeechAct:
    def test_has_nine_acts(self):
        assert len(SpeechAct) == 9

    def test_values(self):
        expected = {
            "claim",
            "question",
            "challenge",
            "argue",
            "concede",
            "retract",
            "support",
            "refute",
            "understand",
        }
        assert {a.value for a in SpeechAct} == expected


# ── Proposition ──


class TestProposition:
    def test_init(self):
        p = Proposition(content="The sky is blue")
        assert p.content == "The sky is blue"
        assert p.truth_value is None
        assert p.confidence == 1.0
        assert p.source is None

    def test_init_with_values(self):
        p = Proposition(content="P", truth_value=True, confidence=0.9, source="Alice")
        assert p.truth_value is True
        assert p.confidence == 0.9
        assert p.source == "Alice"

    def test_str(self):
        p = Proposition(content="Rain is expected")
        assert str(p) == "Rain is expected"

    def test_hash_content_based(self):
        p1 = Proposition(content="A")
        p2 = Proposition(content="A", truth_value=True, confidence=0.5)
        assert hash(p1) == hash(p2)

    def test_equality_same_content(self):
        p1 = Proposition(content="A")
        p2 = Proposition(content="A", truth_value=True)
        assert p1 == p2

    def test_equality_different_content(self):
        p1 = Proposition(content="A")
        p2 = Proposition(content="B")
        assert p1 != p2

    def test_equality_non_proposition(self):
        p = Proposition(content="A")
        assert p.__eq__("not a proposition") is NotImplemented

    def test_usable_in_set(self):
        p1 = Proposition(content="A")
        p2 = Proposition(content="A", truth_value=True)
        p3 = Proposition(content="B")
        s = {p1, p2, p3}
        assert len(s) == 2  # p1 and p2 have same content


# ── FormalArgument ──


class TestFormalArgument:
    def test_init(self):
        p1 = Proposition(content="P1")
        p2 = Proposition(content="P2")
        c = Proposition(content="C")
        arg = FormalArgument(premises=[p1, p2], conclusion=c)
        assert len(arg.premises) == 2
        assert arg.conclusion is c
        assert arg.strength == 1.0
        assert arg.scheme is None
        assert arg.id != ""  # auto-generated UUID

    def test_auto_id(self):
        arg = FormalArgument(premises=[], conclusion=Proposition(content="C"))
        assert len(arg.id) > 10  # UUID format

    def test_custom_id(self):
        arg = FormalArgument(
            premises=[], conclusion=Proposition(content="C"), id="custom-1"
        )
        assert arg.id == "custom-1"

    def test_str(self):
        p = Proposition(content="Rain")
        c = Proposition(content="Wet ground")
        arg = FormalArgument(premises=[p], conclusion=c)
        s = str(arg)
        assert "Rain" in s
        assert "Wet ground" in s
        assert "->" in s


# ── DialogueMove ──


class TestDialogueMove:
    def test_init(self):
        p = Proposition(content="test")
        move = DialogueMove(speaker="Alice", act=SpeechAct.CLAIM, content=p)
        assert move.speaker == "Alice"
        assert move.act == SpeechAct.CLAIM
        assert move.content is p
        assert move.target is None
        assert move.id != ""  # auto UUID

    def test_str(self):
        move = DialogueMove(speaker="Bob", act=SpeechAct.QUESTION, content="Why?")
        s = str(move)
        assert "Bob" in s
        assert "question" in s
        assert "Why?" in s

    def test_custom_id(self):
        move = DialogueMove(speaker="A", act=SpeechAct.CLAIM, content="X", id="move-1")
        assert move.id == "move-1"

    def test_with_target(self):
        move = DialogueMove(
            speaker="A", act=SpeechAct.REFUTE, content="No", target="move-1"
        )
        assert move.target == "move-1"


# ── InquiryProtocol ──


class TestInquiryProtocol:
    @pytest.fixture
    def protocol(self):
        return InquiryProtocol()

    def test_type(self, protocol):
        assert protocol.type == DialogueType.INQUIRY

    def test_question_allows_claim(self, protocol):
        assert protocol.is_valid_move(SpeechAct.QUESTION, SpeechAct.CLAIM)

    def test_question_allows_argue(self, protocol):
        assert protocol.is_valid_move(SpeechAct.QUESTION, SpeechAct.ARGUE)

    def test_claim_allows_challenge(self, protocol):
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.CHALLENGE)

    def test_invalid_transition(self, protocol):
        assert not protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.RETRACT)

    def test_get_allowed_responses(self, protocol):
        responses = protocol.get_allowed_responses(SpeechAct.CLAIM)
        assert SpeechAct.SUPPORT in responses
        assert SpeechAct.CHALLENGE in responses

    def test_get_allowed_responses_empty(self, protocol):
        # RETRACT has explicit transitions in inquiry
        responses = protocol.get_allowed_responses(SpeechAct.RETRACT)
        # RETRACT is not in the allowed transitions (only REFUTE and CONCEDE have entries)
        assert responses == []  # RETRACT not in inquiry transitions

    def test_termination_all_concessions(self, protocol):
        """3 consecutive UNDERSTAND/CONCEDE moves → terminal."""
        moves = [
            DialogueMove("A", SpeechAct.UNDERSTAND, "ok"),
            DialogueMove("B", SpeechAct.CONCEDE, "agreed"),
            DialogueMove("A", SpeechAct.UNDERSTAND, "confirmed"),
        ]
        assert protocol.is_terminal_state(moves)

    def test_termination_max_moves(self, protocol):
        """More than 25 moves → terminal."""
        moves = [DialogueMove("A", SpeechAct.CLAIM, f"arg{i}") for i in range(26)]
        assert protocol.is_terminal_state(moves)

    def test_not_terminal_few_moves(self, protocol):
        moves = [
            DialogueMove("A", SpeechAct.CLAIM, "start"),
            DialogueMove("B", SpeechAct.CHALLENGE, "why?"),
        ]
        assert not protocol.is_terminal_state(moves)

    def test_termination_double_understand(self, protocol):
        """Two consecutive UNDERSTAND at end → terminal."""
        moves = [
            DialogueMove("A", SpeechAct.CLAIM, "x"),
            DialogueMove("B", SpeechAct.SUPPORT, "y"),
            DialogueMove("A", SpeechAct.CLAIM, "z"),
            DialogueMove("B", SpeechAct.UNDERSTAND, "ok"),
            DialogueMove("A", SpeechAct.UNDERSTAND, "ok"),
        ]
        assert protocol.is_terminal_state(moves)

    def test_loop_detection(self, protocol):
        """6 moves with repeating act pairs → terminal."""
        moves = [
            DialogueMove("A", SpeechAct.CLAIM, "x"),
            DialogueMove("B", SpeechAct.CHALLENGE, "y"),
            DialogueMove("A", SpeechAct.CLAIM, "x2"),
            DialogueMove("B", SpeechAct.CHALLENGE, "y2"),
            DialogueMove("A", SpeechAct.CLAIM, "x3"),
            DialogueMove("B", SpeechAct.CHALLENGE, "y3"),
        ]
        assert protocol.is_terminal_state(moves)


# ── PersuasionProtocol ──


class TestPersuasionProtocol:
    @pytest.fixture
    def protocol(self):
        return PersuasionProtocol()

    def test_type(self, protocol):
        assert protocol.type == DialogueType.PERSUASION

    def test_claim_allows_challenge(self, protocol):
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.CHALLENGE)

    def test_claim_allows_concede(self, protocol):
        assert protocol.is_valid_move(SpeechAct.CLAIM, SpeechAct.CONCEDE)

    def test_challenge_allows_argue(self, protocol):
        assert protocol.is_valid_move(SpeechAct.CHALLENGE, SpeechAct.ARGUE)

    def test_argue_allows_refute(self, protocol):
        assert protocol.is_valid_move(SpeechAct.ARGUE, SpeechAct.REFUTE)

    def test_termination_on_concede(self, protocol):
        """Last move is CONCEDE → terminal."""
        moves = [
            DialogueMove("A", SpeechAct.CLAIM, "thesis"),
            DialogueMove("B", SpeechAct.CONCEDE, "you win"),
        ]
        assert protocol.is_terminal_state(moves)

    def test_termination_max_moves(self, protocol):
        """More than 30 moves → terminal."""
        moves = [DialogueMove("A", SpeechAct.CLAIM, f"arg{i}") for i in range(31)]
        assert protocol.is_terminal_state(moves)

    def test_termination_double_retract(self, protocol):
        """Two consecutive RETRACT → terminal."""
        moves = [
            DialogueMove("A", SpeechAct.CLAIM, "x"),
            DialogueMove("B", SpeechAct.CLAIM, "y"),
            DialogueMove("A", SpeechAct.RETRACT, "nvm"),
            DialogueMove("B", SpeechAct.RETRACT, "nvm too"),
        ]
        assert protocol.is_terminal_state(moves)

    def test_not_terminal(self, protocol):
        moves = [
            DialogueMove("A", SpeechAct.CLAIM, "thesis"),
            DialogueMove("B", SpeechAct.CHALLENGE, "prove it"),
        ]
        assert not protocol.is_terminal_state(moves)
