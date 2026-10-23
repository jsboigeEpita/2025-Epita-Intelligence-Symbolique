# -*- coding: utf-8 -*-
"""#3157 — a membership claim is verified against the frame it cites.

The R1107 render wrote « arg_13, arg_17 and arg_100 sit inside the grounded
extension [artifact:dung_frameworks.dung_4] ». That frame's nodes are
arg_1 … arg_40: **arg_100 is not a node of dung_4**, nor of any of the 16
frames — it is the deliberation winner, with its own quality score. The writer
merged a membership claim onto the frame it was citing, and no gate read that
kind of claim: VG-1 counts citations, VG-2 only asks that the cited field is
populated.

``check_reading_license`` now carries ``extension_membership_off_frame``: for a
sentence that cites ``[artifact:dung_frameworks.<id>]``, asserts that a named
unit sits INSIDE an extension, and names a unit that is not a node of that
frame. Frames with no node list (the formalism sidecars the state also holds)
validate nothing and flag nothing.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)

#: The doc_B shape: a frame of 40 nodes, arg_1 … arg_40.
_FRAME_NODES = [f"arg_{i}" for i in range(1, 41)]


def _state(frames=None):
    return SimpleNamespace(
        dung_frameworks=(
            frames
            if frames is not None
            else {
                "dung_4": {
                    "name": "verification_multi",
                    "arguments": list(_FRAME_NODES),
                    "attacks": [["arg_1", "arg_2"]],
                    "extensions": {
                        "count": 1,
                        "all_members": [n for n in _FRAME_NODES if n != "arg_40"],
                    },
                }
            }
        )
    )


def _flags(text, state=None):
    return check_reading_license(text, state if state is not None else _state())[
        "flags"
    ]


def _membership(text, state=None):
    return [
        f for f in _flags(text, state) if f["kind"] == "extension_membership_off_frame"
    ]


class TestTheMeasuredSentenceIsCaught:
    """DoD 1 — the doc_B sentence, fed with the doc_B state."""

    SENTENCE = (
        "arg_13, arg_17 and arg_100 sit inside the grounded extension "
        "[artifact:dung_frameworks.dung_4]."
    )

    def test_the_off_frame_unit_is_flagged(self):
        flags = _membership(self.SENTENCE)
        assert len(flags) == 1
        measured = flags[0]["measured"]
        assert measured["frame"] == "dung_4"
        assert measured["off_frame_units"] == ["arg_100"]
        assert measured["frame_nodes"] == 40

    def test_the_sentence_is_carried_as_produced(self):
        # The reader needs the sentence, not a slice: a cut could only hide
        # the claim (#2850).
        assert _membership(self.SENTENCE)[0]["sentence"] == self.SENTENCE

    def test_the_flag_reads_the_frame_the_sentence_cites(self):
        # Two frames with different nodes: the claim is false against the one
        # cited and true against the other, and only the cited one is read.
        frames = {
            "dung_4": {"arguments": list(_FRAME_NODES)},
            "dung_5": {"arguments": ["arg_100", "arg_13"]},
        }
        text = "arg_100 sits inside the grounded extension [artifact:dung_frameworks.dung_4]."
        assert [f["measured"]["frame"] for f in _membership(text, _state(frames))] == [
            "dung_4"
        ]

    def test_a_french_inside_claim_is_caught(self):
        text = (
            "arg_100 appartient à l'extension préférée "
            "[artifact:dung_frameworks.dung_4]."
        )
        assert [f["measured"]["off_frame_units"] for f in _membership(text)] == [
            ["arg_100"]
        ]


class TestTheControlPasses:
    """DoD 2 — a membership claim the frame supports is not flagged."""

    def test_two_real_nodes_inside_the_cited_extension(self):
        text = (
            "arg_13 and arg_17 sit inside the grounded extension "
            "[artifact:dung_frameworks.dung_4]."
        )
        assert _membership(text) == []

    def test_the_whole_report_has_no_flag_for_a_true_claim(self):
        report = check_reading_license(
            "arg_1 and arg_2 sit inside the grounded extension "
            "[artifact:dung_frameworks.dung_4].",
            _state(),
        )
        assert report["flags"] == []
        assert report["checked"]["dung_frames_with_nodes"] == 1


class TestNoClaimNoFlag:
    """The check reads assertions, never unit ids in passing."""

    def test_an_outside_statement_is_not_a_membership_claim(self):
        text = (
            "arg_100 is not a node of the grounded extension "
            "[artifact:dung_frameworks.dung_4]."
        )
        assert _membership(text) == []

    def test_a_negated_french_claim_is_not_a_membership_claim(self):
        text = (
            "arg_100 n'est pas dans l'extension fondée "
            "[artifact:dung_frameworks.dung_4]."
        )
        assert _membership(text) == []

    def test_a_unit_named_without_a_membership_word_is_not_a_claim(self):
        text = (
            "arg_100 has a quality score of 3.0, unlike the units of "
            "[artifact:dung_frameworks.dung_4]."
        )
        assert _membership(text) == []

    def test_a_sentence_naming_no_unit_is_not_a_claim(self):
        text = "The grounded extension is computed [artifact:dung_frameworks.dung_4]."
        assert _membership(text) == []

    def test_a_frame_absent_from_state_validates_nothing(self):
        text = "arg_100 sits inside the grounded extension [artifact:dung_frameworks.dung_9]."
        assert _membership(text) == []

    def test_a_sidecar_with_no_nodes_validates_nothing(self):
        # The state also holds formalism sidecars (0 arguments): their node
        # set is empty, so they must not read as "this frame holds nothing" —
        # which would flag every unit.
        frames = {"dung_1": {"name": "delp_analysis", "arguments": [], "attacks": []}}
        text = "arg_100 sits inside the grounded extension [artifact:dung_frameworks.dung_1]."
        assert _membership(text, _state(frames)) == []
        report = check_reading_license(text, _state(frames))
        assert report["checked"]["dung_frames_with_nodes"] == 0

    def test_arg_1_does_not_match_inside_arg_100(self):
        # The boundary sits on the digits: a frame of 1..99 nodes must not
        # accept arg_100 through arg_1.
        frames = {"dung_4": {"arguments": [f"arg_{i}" for i in range(1, 100)]}}
        text = "arg_100 sits inside the grounded extension [artifact:dung_frameworks.dung_4]."
        assert [
            f["measured"]["off_frame_units"] for f in _membership(text, _state(frames))
        ] == [["arg_100"]]


#: The extension-half fixture (R1109 remainder): a frame the shared decoder
#: CAN read per semantics — grounded extension arg_1..arg_3, arg_4 attacked by
#: arg_1 (out of the grounded extension, and a node of the frame).
_GROUNDED_FRAMES = {
    "dung_X": {
        "name": "verification_grounded",
        "arguments": ["arg_1", "arg_2", "arg_3", "arg_4"],
        "attacks": [["arg_1", "arg_4"]],
        "extensions": {
            "extensions": [["arg_1", "arg_2", "arg_3"]],
            "count": 1,
            "sizes": [3],
        },
    }
}


def _extension_flags(text, frames=None):
    return check_reading_license(text, _state(frames or _GROUNDED_FRAMES))["flags"]


class TestTheNamedExtensionIsRead:
    """R1109 remainder — a unit said to be inside (or outside) a NAMED
    extension of the cited frame is checked against THAT extension.

    The frame half flags units the frame never held; these witnesses flag
    units the frame holds but the named extension does not (a false inside
    claim), or the extension holds while the sentence puts it outside (a
    false outside claim). Membership alone decides — after #3174 « outside
    the grounded extension » covers ``out`` and ``undec`` alike, so an
    outside claim on an undecided unit is TRUE and never flagged here."""

    def test_an_inside_claim_on_a_unit_out_of_the_extension_is_flagged(self):
        """Witness (DoD): arg_4 is a node of dung_X but out of its grounded
        extension — « arg_4 sits inside the grounded extension » is flagged,
        with a kind naming the extension, not the frame."""
        text = (
            "arg_4 sits inside the grounded extension "
            "[artifact:dung_frameworks.dung_X]."
        )
        flags = [
            f for f in _extension_flags(text) if "extension_membership" in f["kind"]
        ]
        assert len(flags) == 1, flags
        assert flags[0]["kind"] == "extension_membership_off_extension", flags
        measured = flags[0]["measured"]
        assert measured["semantics"] == "grounded"
        assert measured["units_not_in_extension"] == ["arg_4"]

    def test_a_false_outside_claim_on_a_member_is_flagged(self):
        """Witness (DoD): arg_1 IS in the grounded extension — « arg_1 lies
        outside the grounded extension » is flagged."""
        text = (
            "arg_1 lies outside the grounded extension "
            "[artifact:dung_frameworks.dung_X]."
        )
        flags = [
            f for f in _extension_flags(text) if f["kind"].startswith("extension_")
        ]
        assert len(flags) == 1, flags
        assert flags[0]["kind"] == "extension_membership_false_outside", flags
        assert flags[0]["measured"]["units_in_extension"] == ["arg_1"]

    def test_a_true_inside_claim_passes(self):
        text = (
            "arg_1 sits inside the grounded extension "
            "[artifact:dung_frameworks.dung_X]."
        )
        assert _extension_flags(text) == []

    def test_a_true_outside_claim_passes(self):
        """arg_4 is out of the grounded extension (attacked by arg_1): saying
        it lies outside is TRUE — under #3174 that covers out and undec
        alike; only membership decides."""
        text = (
            "arg_4 lies outside the grounded extension "
            "[artifact:dung_frameworks.dung_X]."
        )
        assert _extension_flags(text) == []

    def test_a_sentence_naming_no_semantics_stays_silent(self):
        text = "arg_1 sits inside [artifact:dung_frameworks.dung_X]."
        assert _extension_flags(text) == []

    def test_a_semantics_the_frame_did_not_compute_stays_silent(self):
        text = (
            "arg_4 sits inside the stable extension "
            "[artifact:dung_frameworks.dung_X]."
        )
        assert _extension_flags(text) == []

    def test_a_french_outside_claim_on_a_member_is_flagged(self):
        text = (
            "arg_1 n'est pas dans l'extension grounded "
            "[artifact:dung_frameworks.dung_X]."
        )
        flags = [f for f in _extension_flags(text) if "membership" in f["kind"]]
        assert (
            len(flags) == 1 and flags[0]["kind"] == "extension_membership_false_outside"
        )
