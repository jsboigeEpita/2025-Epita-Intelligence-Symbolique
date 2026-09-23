# -*- coding: utf-8 -*-
"""#2506: Prover9's verdict is read from its proof count and its exit reason.

The endings below are the last lines of the bundled binary's output, recorded
on myia-ai-01 (Prover9 2009-11A). ``SEARCH FAILED`` is printed on every exit
short of ``max_proofs``: after a proof when ``auto_denials`` asked for two,
after an exhausted search, and on a resource limit.
"""

import pytest

from argumentation_analysis.agents.core.logic.fol_handler import _prover9_proved

_END_OF_SEARCH = (
    "============================== end of search =========================\n\n"
)

ENDINGS = {
    "a proof, max_proofs reached": (
        "THEOREM PROVED\n\nExiting with 1 proof.\n\n"
        "Process 1303 exit (max_proofs) Wed Sep 23 21:10:43 2026\n",
        True,
    ),
    "a proof, then the search for a second one runs out": (
        "SEARCH FAILED\n\nExiting with 1 proof.\n\n"
        "Process 1556 exit (sos_empty) Wed Sep 23 21:10:43 2026\n",
        True,
    ),
    "no proof, the search runs out": (
        "SEARCH FAILED\n\nExiting with failure.\n\n"
        "Process 258 exit (sos_empty) Wed Sep 23 21:10:43 2026\n",
        False,
    ),
    "no proof, a resource limit": (
        "SEARCH FAILED\n\nExiting with failure.\n\n"
        "Process 814 exit (max_given) Wed Sep 23 21:10:44 2026\n",
        None,
    ),
    "no ending at all": ("", None),
}


@pytest.mark.parametrize("label", list(ENDINGS))
def test_the_verdict_is_read_from_the_count_and_the_exit(label):
    ending, expected = ENDINGS[label]

    assert _prover9_proved(_END_OF_SEARCH + ending) is expected
