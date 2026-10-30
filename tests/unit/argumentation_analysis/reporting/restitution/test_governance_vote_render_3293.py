"""#3293 — the vote's coverage key does NOT move the Act I range sentence.

The coordinator's decision (R1125, comment 6522889451) on po-2023's review
of #3293: option (b) — ``governance_vote`` joins ``stakes`` in the exclusion
tuple of ``coverage_range_sentence``.

The sentence reads « de 6 à 15 unités selon les modules » — it reports what
each module SELECTED. The vote CONSUMES the quality phase's population, so
its k is not a selection; letting it into the range moved the sentence on
every run where governance is derivable (« de 6 à 15 » → « de 3 à 15 »), a
change of rendered text nobody had asked for.

The witness is byte-identity: the sentence computed WITHOUT the vote's key
and the sentence computed WITH it are the same string. The key stays in the
per-key coverage list, named for what it is.

The R1106/R1107 state lives on ai-01 (not on this seat): the witness uses the
same coverage SHAPE — phases at 6..15, a vote at 3 of 12 — which is what the
range sentence reads.

No JVM, no LLM, deterministic.
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    coverage_range_sentence,
)


def _coverage_with_vote() -> dict:
    """The doc_B shape (phases at 6..15) plus the vote's own key."""
    return {
        "debate": {"k": 6, "N": 90},
        "governance": {"k": 6, "N": 90},
        "nl_to_logic": {"k": 6, "N": 90},
        "quality": {"k": 8, "N": 90},
        "atms": {"k": 8, "N": 90},
        "counter": {"k": 10, "N": 90},
        "fallacy": {"k": 10, "N": 90},
        "fol": {"k": 10, "N": 90},
        "pl": {"k": 10, "N": 90},
        "jtms": {"k": 10, "N": 90},
        "synthesis": {"k": 15, "N": 90},
        "stakes": {"k": 30, "N": 90},
        "governance_vote": {"k": 3, "N": 12},
    }


def test_the_vote_key_leaves_the_range_sentence_untouched():
    """Byte-identity: the vote's key does not move the Act I sentence.

    Before the fix the range was computed over the vote's k as well, so the
    sentence read « de 3 à 15 unités » instead of « de 6 à 15 ».
    """
    coverage = _coverage_with_vote()
    without_vote = {k: v for k, v in coverage.items() if k != "governance_vote"}

    before = coverage_range_sentence(without_vote, 6)
    after = coverage_range_sentence(coverage, 6)

    assert after == before, (
        "the vote's coverage key moved the Act I range sentence — it reports "
        "what each module SELECTED, and the vote consumes the quality "
        "population instead of selecting one"
    )
    assert "de 6 à 15" in after
    assert "de 3 à 15" not in after
