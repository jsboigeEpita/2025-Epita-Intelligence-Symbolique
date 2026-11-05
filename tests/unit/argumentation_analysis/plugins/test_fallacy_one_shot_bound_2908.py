"""#2908 — witness: the one-shot fallback's prompt text is bounded.

The one-shot (``FallacyWorkflowPlugin._run_one_shot``) was the analysis
path's only UNBOUNDED reader: every other reader in the plugin windows the
text (wide-net ``[:8000]``, navigation and leaf ``[:500]``), but the one-shot
put the whole ``argument_text`` into its prompt — on the corpus's longest
document that single call would carry ~600k prompt tokens (#2907 reduction
5). The fix reads the text through the #1737 shared window
(``selected_text``) at the wide-net's own bound — ONE named constant,
shared by both readers (R1058 review: two literals with the same value
could drift apart; #2915 moved the constant from this plugin to the shared
``reading_window`` module as ``WIDE_NET_WINDOW`` because five off-pipeline
readers meant the same bound), and
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

from argumentation_analysis.core.reading_window import (
    WHOLE_TEXT_CALL_CAPACITY,
    WIDE_NET_WINDOW,
)
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)

TAXONOMY = os.path.join(
    "argumentation_analysis", "data", "argumentum_fallacies_taxonomy.csv"
)
BOUND = WIDE_NET_WINDOW  # the wide-net's window, shared since #2915

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
    return svc.prompts, json.loads(result_json)


def test_text_over_the_bound_is_read_whole_in_calls_of_one_capacity():
    """#2850 lot 10 — supersedes the #2908 wide-net-sized window. The witness
    flips in the direction the dispatch asks: a 10,000-char document no longer
    loses its last 2,000 chars. It is read in k = 2 contiguous chunks of one
    call's capacity, each prompt's text section stays under that capacity, and
    the union of the sections IS the document (offset 0: uniform prose). Each
    chunk answers, so the pooled result carries both detections."""
    text = _prose(10_000)
    prompts, result = _run_one_shot_and_capture(text)
    assert result.get("exploration_method") == "one_shot"
    assert len(prompts) == 2
    sections = [_text_section(prompt) for prompt in prompts]
    assert all(len(section) <= WHOLE_TEXT_CALL_CAPACITY for section in sections), (
        f"each call carries at most one capacity "
        f"({WHOLE_TEXT_CALL_CAPACITY} chars), got {[len(s) for s in sections]}"
    )
    assert "".join(sections) == text, "the chunks must tile the whole document"
    assert len(result.get("fallacies") or []) == 2, (
        "each chunk's detection is pooled — a chunk is not a throwaway"
    )


def test_texts_at_or_under_the_bound_produce_a_byte_identical_prompt():
    """Non-regression property (the replay-band safety): at exactly the
    bound and under it, the prompt is byte-identical to the pre-#2908
    unbounded construction — same template, same full text."""
    for length in (500, BOUND):
        text = _prose(length)
        prompts, result = _run_one_shot_and_capture(text)
        prompt = prompts[0]
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
            # #3180 — the template also asks WHOSE move it is (speaker or a
            # reported party); the JSON contract gained the two fields. The
            # re-pin keeps the property this test exists for: the template is
            # a single constant, byte-identical between runs.
            'Also say WHOSE move it is: "move_author" is "speaker" when the '
            'text\'s own speaker commits the fallacy, or "reported" when the '
            "text reports/denounces a move made by another party — then "
            '"move_author_label" names that party as the text names it '
            '(e.g. "opponent"). Omit both when the text does not let you tell.\n'
            # #3391 — the template also carries the register test and the
            # self-correction reading, and the JSON contract gained
            # "register_test". Same re-pin as #3180 above: the property is the
            # single constant template, not a frozen vintage of it.
            "When the fallacy you chose is an appeal to emotion, loyalty, the "
            "flag, pride, pity or fear, apply that node's own conditions as a "
            'proportionality test and say the result in "register_test": '
            '"disproportionate" when the appeal drives past what the text '
            'itself states (its facts and its stakes), "proportionate" when it '
            "stays within them — then it is legitimate in its register and "
            "NOT a fallacy. The cap is the same for every side: a "
            "disproportionate appeal stays flagged, whoever the speaker.\n"
            "When the text revises or restricts its own preceding wording, "
            "that revision is not a false implication of the wording it "
            "corrects: do not flag it.\n"
            "Respond with ONLY a JSON object: "
            '{"fallacy_name": "...", "taxonomy_pk": "...", "explanation": "...", '
            '"confidence": 0.0-1.0, "move_author": "speaker|reported", '
            '"move_author_label": "...", '
            '"register_test": "proportionate|disproportionate"}\n\n'
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


def test_the_bound_is_one_named_constant_shared_with_the_wide_net():
    """R1058 review: the one-shot window must cite ONE named constant rather
    than a literal that could drift. #2915 moved the constant to the shared
    ``reading_window`` module; the plugin must IMPORT it, never redefine it.

    #2850 lot 10 changed the shape of the sharing, not its point: the wide
    net no longer slices ``[:WIDE_NET_WINDOW]`` — it reads the whole document
    in k calls chunked at ``WHOLE_TEXT_CALL_CAPACITY`` (same constant family,
    derived from lot 9's one-call capacity). ``WIDE_NET_WINDOW`` therefore
    backs exactly ONE read now (the one-shot), and the wide net must go
    through the shared capacity constant, never a new literal."""
    import ast as _ast
    import importlib as _importlib
    from pathlib import Path as _Path

    mod = _importlib.import_module(
        "argumentation_analysis.plugins.fallacy_workflow_plugin"
    )
    tree = _ast.parse(_Path(mod.__file__).read_text(encoding="utf-8-sig"))
    defs = [
        n.targets[0].id
        for n in tree.body
        if isinstance(n, _ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], _ast.Name)
        and isinstance(n.value, _ast.Constant)
        and n.value.value == BOUND
    ]
    assert defs == [], (
        f"the plugin must not define its own {BOUND} constant — the shared "
        f"WIDE_NET_WINDOW lives in core/reading_window.py (#2915); found "
        f"module-level definitions {defs}"
    )
    uses = [
        n.lineno
        for n in _ast.walk(tree)
        if isinstance(n, _ast.Name) and n.id == "WIDE_NET_WINDOW"
    ]
    one_shot = [
        n
        for n in _ast.walk(tree)
        if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef))
        and n.name == "_run_one_shot"
    ]
    assert one_shot, "the one-shot entry point moved; update this pin"
    lo, hi = one_shot[0].lineno, one_shot[0].end_lineno
    stray = [line for line in uses if not (lo <= line <= hi)]
    assert uses and not stray, (
        f"WIDE_NET_WINDOW must back only the one-shot window (in "
        f"_run_one_shot, lines {lo}-{hi}; the wide net chunks at "
        f"WHOLE_TEXT_CALL_CAPACITY since #2850 lot 10) — uses at {uses}, "
        f"stray at {stray}"
    )
    capacity_uses = [
        n.lineno
        for n in _ast.walk(tree)
        if isinstance(n, _ast.Name) and n.id == "WHOLE_TEXT_CALL_CAPACITY"
    ]
    assert capacity_uses, (
        "the wide net must chunk through the shared WHOLE_TEXT_CALL_CAPACITY "
        "(#2850 lot 10), never a local literal"
    )
