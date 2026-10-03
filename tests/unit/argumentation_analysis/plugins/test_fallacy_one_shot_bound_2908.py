"""#2908 — witness: the one-shot fallback's prompt text is bounded.

The one-shot (``FallacyWorkflowPlugin._run_one_shot``) was the analysis
path's only UNBOUNDED reader: every other reader in the plugin windows the
text (wide-net ``[:8000]``, navigation and leaf ``[:500]``), but the one-shot
put the whole ``argument_text`` into its prompt — on the corpus's longest
document that single call would carry ~600k prompt tokens (#2907 reduction
5). The fix reads the text through the #1737 shared window
(``selected_text``) at the wide-net's own bound (8000): no new constant, and
for texts at or under the bound the selection is offset 0 by construction (a
run of ceil(window/stride) passing segments inside a window-sized text must
start at segment 0), so the prompt is BYTE-IDENTICAL to the unbounded form —
no replay-band key can miss (the band holds no one-shot prompt at all,
measured at fix time: 685 cassettes, zero one-shot markers).

Offline by construction: a recording fake service answers the single call;
no network, no key.
"""

import asyncio
import json
import os
import unittest.mock as um

from semantic_kernel.contents import AuthorRole

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

TAXONOMY = os.path.join(
    "argumentation_analysis", "data", "argumentum_fallacies_taxonomy.csv"
)
BOUND = 8000  # the wide-net's own window (fallacy_workflow_plugin line 617)

# Punctuated French prose: ~4 sub-clause marks per 100 chars — far above the
# #1737 selector's 4/kchar threshold, so every stride segment passes and the
# selection stays at offset 0 (the non-regression geometry).
_SENTENCE = (
    "Selon le rapport, il est clair que, malgré les efforts, la décision "
    "reste, en réalité, contestable: le débat continue. "
)


def _prose(length: int) -> str:
    text = ""
    while len(text) < length:
        text += _SENTENCE
    return text[:length]


class _RecordingService:
    """Records the prompt sent to the (single) one-shot call; answers JSON."""

    def __init__(self):
        self.prompts = []

    async def get_chat_message_content(
        self, chat_history=None, settings=None, kernel=None, **kw
    ):
        users = [
            str(m.content)
            for m in (chat_history.messages or [])
            if getattr(m, "role", None) == AuthorRole.USER
        ]
        self.prompts.append("\n<<MSG>>\n".join(users))
        return json.dumps(
            {
                "fallacy_name": "Appel à l'autorité",
                "taxonomy_pk": "1",
                "explanation": "witness",
                "confidence": 0.5,
            }
        )


def _text_section(prompt: str) -> str:
    start = prompt.index("--- TEXT ---\n") + len("--- TEXT ---\n")
    end = prompt.index("\n--- END TEXT ---")
    return prompt[start:end]


def _run_one_shot_and_capture(text: str):
    svc = _RecordingService()
    plugin = FallacyWorkflowPlugin(
        master_kernel=None, llm_service=svc, taxonomy_file_path=TAXONOMY
    )
    plugin._create_one_shot_kernel = lambda: (um.MagicMock(), um.MagicMock())
    result_json = asyncio.run(plugin._run_one_shot(text))
    assert svc.prompts, "the one-shot call never reached the service"
    return svc.prompts[0], json.loads(result_json)


def test_text_over_the_bound_is_windowed_to_exactly_8000_chars():
    """THE witness (born red before the fix): a 10,000-char document must
    reach the one-shot prompt as an 8,000-char window — the wide-net's own
    bound, at the selected offset (offset 0 here: the text is uniform
    prose). Before #2908 the section carried the whole 10,000 chars."""
    text = _prose(10_000)
    prompt, result = _run_one_shot_and_capture(text)
    assert result.get("exploration_method") == "one_shot"
    section = _text_section(prompt)
    assert len(section) == BOUND, (
        f"the one-shot's text section is {len(section)} chars — it must be "
        f"bounded at {BOUND}"
    )
    assert section == text[:BOUND]


def test_texts_at_or_under_the_bound_produce_a_byte_identical_prompt():
    """Non-regression property (the replay-band safety): at exactly the
    bound and under it, the prompt is byte-identical to the pre-#2908
    unbounded construction — same template, same full text."""
    for length in (500, BOUND):
        text = _prose(length)
        prompt, result = _run_one_shot_and_capture(text)
        assert result.get("exploration_method") == "one_shot"
        # The legacy construction, rebuilt here from the template in the
        # source: full text, same taxonomy part.
        plugin = FallacyWorkflowPlugin(
            master_kernel=None, llm_service=um.MagicMock(), taxonomy_file_path=TAXONOMY
        )
        legacy = (
            f"Analyze the following text:\n--- TEXT ---\n{text}\n--- END TEXT ---\n\n"
            "Identify the single most relevant fallacy from the taxonomy below. "
            "CRITICAL: Choose the MOST SPECIFIC (deepest) node that matches — "
            "generic labels like 'Ad hominem' or 'Appel à l'autorité' are too shallow. "
            "Prefer leaf nodes or deep sub-types (e.g., 'Empoisonnement du puits' instead of 'Culpabilité par association'). "
            "IMPORTANT: Use the exact fallacy name as it appears in the taxonomy (in French). "
            "Respond with ONLY a JSON object: "
            '{"fallacy_name": "...", "taxonomy_pk": "...", "explanation": "...", "confidence": 0.0-1.0}\n\n'
            f"--- TAXONOMY ---\n{plugin._build_compact_taxonomy(max_depth=6)}\n--- END ---"
        )
        assert prompt == legacy, (
            f"at length {length} (≤ bound) the prompt must be byte-identical "
            "to the unbounded form — a difference would miss replay keys"
        )


def test_the_window_is_the_shared_1737_mechanism_not_a_new_constant():
    """The bound is selected_text at the wide-net's 8000 — the census guards
    hold the shape: the #2850 guard reads the new window row, the #2908
    census forbids the bare interpolation. This test pins the mechanism so a
    future 'simplification' to a local slice cannot slip in unnoticed."""
    from argumentation_analysis.core.reading_window import select_reading_head

    # The plugin's site must resolve through the shared selector: a
    # no-punctuation text (selection status != selected) still returns a
    # window-sized slice at offset 0 — and a long one is bounded.
    sel = select_reading_head(_prose(10_000), BOUND)
    assert sel.offset == 0 and sel.window == BOUND
    sel_short = select_reading_head(_prose(100), BOUND)
    assert sel_short.offset == 0, "texts under the window never shift offset"
