# -*- coding: utf-8 -*-
"""#3224 — an absence the act's own speaker detections contradict.

The R1110 render answered the Act I question's causal half in the negative —
« Les unités analysées n'y montrent pas de glissement de causalité ni de faux
dilemme relevé comme procédé » — while ``identified_fallacies`` held a
speaker-attributed detection under the taxonomy branch « Causalité douteuse »
(4.1). #3213 moved such claims from the text to the analysis: the right SCOPE,
still a false claim. The new check reads the sentence against the act's own
record: the analysis as subject with its presence verb negated (or an explicit
« aucun … relevé »), one content word naming a branch or leaf node a SPEAKER
detection sits under.

The rule was measured on the seven stored local renders before being settled:
a loose marker (« aucun » anywhere, ``ne … pas`` across clauses, English
negation) raised 14 flags, all false — so the controls below pin the shapes
that must NOT fire (a quoted « aucun », a node word in a positive sentence, an
absence naming no node, a REPORTED move, a detection with no address).

Synthetic values only; taxonomy names come from the tracked CSV.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)

_R1110_SENTENCE = (
    "Les unités analysées n'y montrent pas de glissement de causalité "
    "ni de faux dilemme relevé comme procédé."
)


def _state(**over: Any) -> SimpleNamespace:
    fallacy: Dict[str, Any] = {
        "type": "Effet cigogne",
        "family": "Erreur de raisonnement",
        "taxonomy_path": "4.1.3",
        "justification": "une corrélation lue comme un lien de cause à effet.",
        "target_argument_id": "arg_1",
    }
    fallacy.update(over)
    return SimpleNamespace(identified_fallacies={"fallacy_1": fallacy})


def _flags(sentence: str, state: SimpleNamespace) -> list:
    return check_reading_license(sentence, state)["flags"]


class TestTheContradictionFires:
    def test_the_r1110_sentence_fires_on_the_branch_it_denies(self):
        """The issue's case 2, on the quoted sentence: the check reads
        « causalité » as naming the branch « Causalité douteuse »."""
        flags = _flags(_R1110_SENTENCE, _state())
        assert [f["kind"] for f in flags] == ["absence_contradicted_by_detection"]
        hit = flags[0]["measured"]["nodes"][0]
        assert hit["node"] == "Causalité douteuse"
        assert hit["taxonomy_path"] == "4.1.3"
        assert hit["shared_tokens"] == ["causalité"]
        assert hit["fallacy_id"] == "fallacy_1"

    def test_the_checked_trace_counts_the_nodes_read(self):
        report = check_reading_license(_R1110_SENTENCE, _state())
        # the branch and the leaf — the root names no category
        assert report["checked"]["speaker_detection_nodes"] == 2


class TestTheRuleStaysOnItsShape:
    def test_a_reported_move_cannot_contradict_the_speakers_claim(self):
        """#3180 — another party's move is not the discourse's; the speaker
        commits nothing, so nothing contradicts the absence."""
        assert _flags(_R1110_SENTENCE, _state(move_author="reported")) == []

    def test_a_detection_with_no_taxonomy_path_names_no_node(self):
        """No address, no guess: the detection cannot be joined to a node."""
        assert _flags(_R1110_SENTENCE, _state(taxonomy_path=None)) == []

    def test_an_absence_that_names_no_node_places_no_flag(self):
        sentence = "Les unités analysées n'y montrent pas de chiffres vérifiables."
        assert _flags(sentence, _state()) == []

    def test_a_node_word_without_an_absence_claim_places_no_flag(self):
        """The measured false-positive class: an ordinary word that happens to
        sit in a node's name, in a POSITIVE sentence."""
        sentence = (
            "Les unités analysées portent un glissement de causalité "
            "relevé comme procédé."
        )
        assert _flags(sentence, _state()) == []

    def test_a_quoted_aucun_is_not_an_absence_claim(self):
        """The measured false-positive class: « aucun » inside a quoted
        fragment, in a sentence that also carries a node word (« effet ») —
        the sentence states no absence, so no marker fires. Under the loose
        marker this test reddens (it fired on the quote alone)."""
        sentence = (
            "La formule « aucun moyen exclu » et l'effet annoncé restent "
            "une prescription."
        )
        assert _flags(sentence, _state()) == []

    def test_a_text_scoped_absence_keeps_its_own_flag(self):
        """#3213 scoping stays distinct: an absence placed on the TEXT is the
        other check's claim, not this one's."""
        sentence = "Le texte ne montre pas de glissement de causalité."
        kinds = [f["kind"] for f in _flags(sentence, _state())]
        assert kinds == ["text_absence_claim"]


_R1110B_SENTENCE = (
    "Un sophisme détecté n'a aucun argument cible identifié, "
    "et je ne lui en prête aucun."
)


class TestAGenericClassWordIsNotACategory:
    """The coordinator's replay on the four stored doc_A states raised one
    more false flag, of a second class: the R1110b sentence matched the node
    « Sophisme psychogénétique » on « sophisme » — the CLASS word itself
    (df 76 over the 1 408 node names), not a category name. The marker was
    right and the token was wrong: a node token now carries a category only
    when its document frequency over the taxonomy's own node names stays at
    or below ``DISTINCTIVE_NODE_DF_MAX`` (measured: 1 535 of 1 573 tokens
    sit at df ≤ 5; the spikes appel 125, effet 86, sophisme 76, biais 58,
    argument 44, erreur 21, question 13 are the file's structural
    vocabulary)."""

    def test_the_r1110b_sentence_stays_silent(self):
        """The sentence says one detection has no target; it denies no
        category. « sophisme » names the class, not a node's category."""
        assert _flags(_R1110B_SENTENCE, _state(taxonomy_path="1.3.2.3.3")) == []

    def test_the_silence_is_the_bar_not_the_marker(self, monkeypatch):
        """Mutation witness: with the bar set to the maximum, the SAME
        sentence flags on « sophisme » — so the silence above is the
        taxonomy-derived distinctiveness bar doing the work, never the
        marker or the attribution filter."""
        import argumentation_analysis.agents.core.synthesis.reading_license as rl

        monkeypatch.setattr(rl, "DISTINCTIVE_NODE_DF_MAX", 10**9)
        flags = _flags(_R1110B_SENTENCE, _state(taxonomy_path="1.3.2.3.3"))
        assert [f["kind"] for f in flags] == ["absence_contradicted_by_detection"]
        hit = flags[0]["measured"]["nodes"][0]
        assert hit["node"] == "Sophisme psychogénétique"
        assert hit["shared_tokens"] == ["sophisme"]

    def test_the_r1110_sentence_still_fires_through_the_bar(self):
        """« causalité » (df 5) sits AT the bar: the true positive survives
        the rule that kills the false one."""
        flags = _flags(_R1110_SENTENCE, _state())
        assert [f["kind"] for f in flags] == ["absence_contradicted_by_detection"]
        assert flags[0]["measured"]["nodes"][0]["shared_tokens"] == ["causalité"]
