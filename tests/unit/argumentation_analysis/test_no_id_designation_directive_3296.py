"""FB-34 handed the writer the machine id in four directives — #3296.

FB-34 is a **privacy** rule: it forbids naming the source. Measured on the
R1125a state, four directives did more than that — they *ordered* the opaque
id into the prose (« Désigne chaque argument par son ID opaque (arg_1,
arg_2…) », « an argument is `arg_1` »), while the readability gate (#2980)
counts every printed ``arg_N`` as jargon (WARN at 1, FAIL at 3). The brief
contradicted the gate, and the brief won: 5 of 41 renders carried raw ids.

The arbitration (ai-01, R1126, issue comment 6527131332) removes the
designation clause and **keeps the ban**. This witness pins that half:

* no directive hands the writer an ``arg_N``;
* each one still forbids the real name — removing the order must not remove
  the privacy rule, which would be the pendulum.

Designation moves to a per-act label table with a legend (#2896/#2965); the
end-to-end witness (« no assembler's prompt carries a bare id outside an
anchor ») belongs with the input blocks, the second half of #3296, because it
cannot be green while those blocks still supply the id.

``act1_framing_plugin.py`` is deliberately absent: it speaks in ``Speaker_A``
/ ``era_A`` and never handed out an id (coordinator's table, R1126).
"""

import re

import pytest

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.plugins import narrative_synthesis_plugin as prose
from argumentation_analysis.reporting.restitution import act2_narrative_plugin as act2
from argumentation_analysis.reporting.restitution import act3_conclusion_plugin as act3

_RAW_ID = re.compile(r"\barg_\d+\b")

# Site -> (the directive a writer receives, the phrase proving the ban on real
# names is still stated there). The phrase is the invariant, not decoration:
# a fix that deletes the whole bullet would pass the first test and fail this
# one.
DIRECTIVES = {
    "act2": (act2._OPAQUE_ID_DIRECTIVE, "nom de source"),
    "act3": (act3._OPAQUE_ID_DIRECTIVE, "nom de source"),
    "deep_synthesis": (DeepSynthesisAgent.OPAQUE_ID_DIRECTIVE, "NEVER appear"),
    "prose_rule": (prose._PROSE_OPAQUE_RULE, "never emit a real"),
}


def test_the_four_measured_sites_are_the_four_pinned_here():
    """A void table would make the two tests below vanish instead of fail."""
    assert len(DIRECTIVES) == 4, (
        "R1126 named exactly four sites that ordered the id (Act II, Act III, "
        f"DeepSynthesisAgent, _PROSE_OPAQUE_RULE); this table carries {len(DIRECTIVES)}"
    )
    thin = [name for name, (text, _) in DIRECTIVES.items() if len(text) < 80]
    assert not thin, f"directive(s) read as empty: {thin} — the measurement is void"


@pytest.mark.parametrize("site", sorted(DIRECTIVES))
def test_no_directive_hands_the_writer_an_arg_id(site):
    text, _ = DIRECTIVES[site]
    found = _RAW_ID.findall(text)
    assert not found, (
        f"{site} still orders the opaque id {sorted(set(found))}: the writer is "
        "told to write what the readability gate (#2980) counts as jargon. FB-34 "
        "forbids the source NAME; it does not require the id."
    )


@pytest.mark.parametrize("site", sorted(DIRECTIVES))
def test_every_directive_still_forbids_the_real_name(site):
    text, ban_phrase = DIRECTIVES[site]
    assert ban_phrase in text, (
        f"{site} no longer states the ban on real names ({ban_phrase!r} absent): "
        "removing the designation clause must not remove the privacy rule — that "
        "would be the pendulum (#3296 arbitration)."
    )
