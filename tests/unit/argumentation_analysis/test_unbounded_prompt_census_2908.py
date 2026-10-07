"""#2908 — census guard: no unbounded document-text interpolation into prompts.

The #2850 census guard reads ``[:N]`` head slices and ``selected_text`` calls
— a reader with NO slice is invisible to it. #2907's audit found exactly one
such reader on the analysis path (the fallacy one-shot fallback, which put
the whole ``argument_text`` into its prompt), and #2908 bounds it. This guard
is the instrument half of the DoD: on the AST (never grep — the #1842
pattern), every f-string / ``.format`` interpolation of a document-text-
bearing name with no bound must appear in ``ALLOWED`` below with a triage —
what the site reads and why it is a row (named debt) instead of a fix.

Census boundary, stated rather than hidden: an interpolation counts when the
expression is a bare Name/Attribute (or an unbounded-upper Subscript —
``text[start:]``) whose name is one of ``_DOC_TEXT_NAMES``. Bare names are
resolved through single-assignment aliases of the enclosing function —
whatever the alias is called (``windowed = argument_text`` then ``f"{windowed}"`` reads as
``argument_text`` — R1058); a name assigned more than once, or aliased from
a non-document source, is NOT tracked — both limits are held by the
alias-control test below, so they are documented limits, not unknown ones.
Sliced (``[:N]``) and derived (``selected_text(...)``, ``.lower()``)
expressions are bounded by construction and are NOT this census's
population; short labels, ids, counts and pks (``fallacy_type``, ``arg_id``,
…) are outside the name set — the boundary is held by the negative-control
test below, so it is a documented limit, not an unknown one.

Keys are semantic — ``(relpath, kind, name, ordinal)`` in ``ast.walk`` order
(the #2850 pattern) — so a moved line stays green while a renamed variable, a
new site or a deleted one reddens. Line numbers ride along as comments for
readability; the triage note is the row's content.
"""

import ast
import re
from pathlib import Path

from tests.support.tree_walk import iter_tracked_files

ROOT = Path(__file__).resolve().parents[3]

# Names that can carry DOCUMENT or UNIT text (the material a prompt could
# read the whole document through). Ids, labels, counts, pks and formula
# fragments are deliberately outside — see the negative control.
_DOC_TEXT_NAMES = frozenset(
    {
        "text",
        "argument_text",
        "input_text",
        "text_to_analyze",
        "raw_text",
        "extracted_text",
        "extract_text",
        "claim_text",
        "problematic_text",
        "current_chunk",
        "taxonomy_text",
        "contextual_frame",
        "context_block",
        "arguments_block",
        "textual_span",
        "full_text",
        "target_text",
        "highlighted_text",
        "html_text",
        "full_text_preview",
        "matched_text",
        "status_text",
        "args_text",
        "short_text",
    }
)

_TEXT_TOKEN = re.compile(
    r"arg|claim|fallac|sophism|counter|sentence|segment|chunk|premise|text",
    re.IGNORECASE,
)


def _name_of(node: ast.expr):
    """The bare name an expression reads — ``x``, ``self.x``; None otherwise.

    Calls return None (``selected_text(...)``, ``.lower()`` — derived, out of
    the population); Subscripts are handled separately.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _unbounded_upper_subscript(node: ast.expr):
    """``text[start:]`` / ``text[:]`` — a Subscript whose slice has NO upper."""
    if not isinstance(node, ast.Subscript):
        return None
    sl = node.slice
    if not isinstance(sl, ast.Slice) or sl.upper is not None:
        return None
    base = _name_of(node.value)
    if base and _TEXT_TOKEN.search(base):
        return f"{base}[…:]"
    return None


def _bare_text_expr(node: ast.expr):
    """A bare Name/Attribute carrying a text token — no slice, no call."""
    name = _name_of(node)
    if name and _TEXT_TOKEN.search(name):
        return name
    return None


def _single_assign_aliases(fn: ast.AST) -> dict:
    """alias name -> root doc-text name, for aliases assigned exactly once
    in ``fn``'s subtree (R1058: ``windowed = argument_text`` then
    ``f"{windowed}"`` must not slip past the census).

    A name assigned more than once is NOT tracked — its later value may not
    be the document; a source outside ``_DOC_TEXT_NAMES`` is not a document
    read. Chains (``a = argument_text; b = a``) resolve to the root, with a
    cycle guard (``a = b; b = a`` is two single assignments and would loop).
    """
    assigns: dict = {}
    for node in ast.walk(fn):
        pairs = []
        if isinstance(node, ast.Assign):
            pairs = [
                (t.id, _name_of(node.value))
                for t in node.targets
                if isinstance(t, ast.Name)
            ]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            src = _name_of(node.value) if node.value is not None else None
            pairs = [(node.target.id, src)]
        for target, src in pairs:
            assigns.setdefault(target, []).append(src)
    # every single-assignment name-to-name binding (the chain's middle links
    # have a non-document source and must enter the map to be walkable)
    singles = {
        t: srcs[0]
        for t, srcs in assigns.items()
        if len(srcs) == 1 and srcs[0] is not None
    }
    # walk each chain to its root; keep the name only if the root is a
    # document-text name (cycle-guarded: ``a = b; b = a`` is two single
    # assignments and would loop)
    aliases = {}
    for t in singles:
        root, seen, hop = singles[t], {t}, 0
        while root in singles and root not in seen and hop < 32:
            seen.add(root)
            root = singles[root]
            hop += 1
        if root in _DOC_TEXT_NAMES and root != t:
            aliases[t] = root
    return aliases


def _parent_map(tree: ast.Module) -> dict:
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing_function(node: ast.AST, parents: dict):
    """The innermost FunctionDef/AsyncFunctionDef above ``node`` (None at
    module level) — the scope whose aliases govern the site."""
    n = node
    while n in parents:
        n = parents[n]
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return n
    return None


def _sites_in_tree(tree: ast.Module):
    """(kind, name, lineno) for every unbounded text-bearing interpolation,
    in ``ast.walk`` order (the ordinal scheme below depends on it).

    A bare Name is resolved through the single-assignment aliases of its
    innermost enclosing function BEFORE the text-token check — the alias can
    be called anything (``x = argument_text`` reads as ``argument_text``) —
    and the ROOT name is the census key: an aliased read lands on the root's
    ordinal series, so introducing an alias reddens the census instead of
    hiding behind a local name.
    """
    parents = _parent_map(tree)
    alias_maps: dict = {}

    def _text_name_of(expr: ast.expr, site: ast.AST):
        if isinstance(expr, ast.Name):
            fn = _enclosing_function(site, parents)
            if fn is not None:
                if fn not in alias_maps:
                    alias_maps[fn] = _single_assign_aliases(fn)
                root = alias_maps[fn].get(expr.id)
                if root is not None:
                    return root
        return _bare_text_expr(expr)

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for fv in node.values:
                if not isinstance(fv, ast.FormattedValue):
                    continue
                sub = _unbounded_upper_subscript(fv.value)
                if sub:
                    found.append(("fstring", sub, fv.value.lineno))
                    continue
                bare = _text_name_of(fv.value, fv)
                if bare:
                    found.append(("fstring", bare, fv.value.lineno))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
        ):
            for a in node.args:
                sub = _unbounded_upper_subscript(a)
                if sub:
                    found.append(("format-arg", sub, a.lineno))
                    continue
                bare = _text_name_of(a, a)
                if bare:
                    found.append(("format-arg", bare, a.lineno))
            for kw in node.keywords:
                sub = _unbounded_upper_subscript(kw.value)
                if sub:
                    found.append(("format-kwarg", sub, kw.value.lineno))
                    continue
                bare = _text_name_of(kw.value, kw)
                if bare:
                    found.append(("format-kwarg", bare, kw.value.lineno))
    return found


def census():
    """(relpath, kind, name, ordinal) -> lineno for every site in the tracked
    ``argumentation_analysis`` tree. Ordinals count the occurrences sharing
    the same first three fields, in ``ast.walk`` order."""
    rows = {}
    for path in iter_tracked_files(ROOT):
        rel = path.relative_to(ROOT).as_posix()
        if not rel.startswith("argumentation_analysis/"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            raise RuntimeError(f"census cannot parse {rel}: {exc!r} (#2908)") from exc
        ordinal_of = {}
        for kind, name, lineno in _sites_in_tree(tree):
            if name.replace("[…:]", "") not in _DOC_TEXT_NAMES:
                continue
            key3 = (kind, name)
            ordinal_of[key3] = ordinal_of.get(key3, 0) + 1
            rows[(rel, kind, name, ordinal_of[key3])] = lineno
    return rows


# (relpath, kind, name, ordinal) -> triage: what the site reads, and why it
# is a row (named debt / bounded upstream / not a prompt) instead of a fix.
# Generated from the census at guard birth (post-#2908 fix: the one-shot row
# is gone — it now reads selected_text(argument_text, 8000, ...) and is
# censused by the #2850 guard as a window). Post-#2912: the seven named-debt
# rows are gone too — every one of them now interpolates a selected_text(...)
# call (the wide-net's 8000, or the file's own 3000 for the self-hosted
# tier), so the #2850 guard holds them as window rows and this census holds
# none.
ALLOWED = {
    # --- bounded upstream: the interpolated value is already a slice/unit ---
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "fstring",
        "input_text",
        1,
    ): (
        "line 7908 — FOL directives prepend; the LLM window reads "
        "selected_text(_doc_text_fol, …) downstream — bounded"
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "fstring",
        "input_text",
        2,
    ): (
        "line 3331 — effective text fed to run_guided_analysis; every plugin "
        "reader is windowed (the one-shot's window is #2908's fix)"
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "fstring",
        "input_text",
        3,
    ): (
        "line 6255 — same run_guided_analysis feed as ordinal 2 (cam "
        "variant) — every plugin reader is windowed"
    ),
    (
        "argumentation_analysis/orchestration/invoke_callables.py",
        "fstring",
        "text",
        1,
    ): ("line 1605 — scored argument UNIT texts in the target list"),
    (
        "argumentation_analysis/orchestration/state_writers.py",
        "fstring",
        "text",
        1,
    ): ("line 1216 — argument unit text + quote[:100]"),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "fstring",
        "argument_text",
        1,
    ): (
        "line 207 — accumulated context = k stratified unit texts (#2850 "
        "selector) joined"
    ),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "fstring",
        "text",
        1,
    ): ("line 169 — unit text from the stratified selection"),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "fstring",
        "text",
        2,
    ): ("line 173 — unit text from the arguments[:8] fallback"),
    (
        "argumentation_analysis/orchestration/collaborative_debate.py",
        "fstring",
        "text",
        3,
    ): ("line 177 — unit text from the claims[:8] fallback"),
    (
        "argumentation_analysis/agents/core/political/stakes_extractor.py",
        "format-kwarg",
        "arguments_block",
        1,
    ): (
        "line 137 — per-item 200-char excerpts over ≤30 args — registered "
        "#2850 debt (the stakes site)"
    ),
    (
        "argumentation_analysis/plugins/text_to_kb_plugin.py",
        "fstring",
        "current_chunk",
        1,
    ): ("line 88 — chunker accumulator, bounded by max_chars per chunk"),
    (
        "argumentation_analysis/reporting/restitution/act3_conclusion_plugin.py",
        "fstring",
        "text",
        1,
    ): (
        "line 2418 — claim excerpts in the Acte III claims block (#2965); "
        "bounded upstream: each text was capped at CITED_UNIT_TEXT_CAP where "
        "claim_excerpts is built (line 2144) and the loop stops at "
        "_MAX_CLAIM_EXCERPTS (5) lines"
    ),
    # --- not a prompt: logs, cache keys, renders, UI ---
    (
        "argumentation_analysis/agents/core/logic/tweety_bridge_sk.py",
        "fstring",
        "problematic_text",
        1,
    ): ("line 398 — log line"),
    (
        "argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py",
        "fstring",
        "text",
        1,
    ): ("line 95 — log line (hypothesis text)"),
    (
        "argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py",
        "fstring",
        "text",
        2,
    ): ("line 104 — return message (hypothesis text)"),
    (
        "argumentation_analysis/orchestration/cluedo_extended_orchestrator.py",
        "fstring",
        "input_text",
        1,
    ): ("line 52 — fallback message string (display)"),
    (
        "argumentation_analysis/orchestration/pipeline_utils.py",
        "fstring",
        "text",
        1,
    ): ("line 85 — cache-key material (md5), not a prompt"),
    (
        "argumentation_analysis/plugin_framework/core/plugins/standard/external_verification/plugin.py",
        "fstring",
        "claim_text",
        1,
    ): ("line 282 — search-query string in a simulated plugin, not an LLM " "prompt"),
    (
        "argumentation_analysis/plugins/semantic_kernel/jtms_plugin.py",
        "fstring",
        "status_text",
        1,
    ): ("line 357 — natural-language status summary (render)"),
    (
        "argumentation_analysis/plugins/tweety_result_interpretation_plugin.py",
        "fstring",
        "args_text",
        1,
    ): ("line 69 — display sentence"),
    (
        "argumentation_analysis/reporting/restitution/appendix.py",
        "fstring",
        "text",
        1,
    ): ("line 653 — fabrication-note string in report render"),
    (
        "argumentation_analysis/reporting/summary_generator.py",
        "fstring",
        "extract_text",
        1,
    ): ("line 232 — markdown report render (display)"),
    (
        "argumentation_analysis/services/logic_service.py",
        "fstring",
        "text",
        1,
    ): ("line 272 — md5 id material, not a prompt"),
    (
        "argumentation_analysis/services/web_api/services/fallacy_service.py",
        "fstring",
        "text",
        1,
    ): ("line 501 — DEBUG print (display)"),
    (
        "argumentation_analysis/services/web_api/services/fallacy_service.py",
        "fstring",
        "text",
        2,
    ): ("line 574 — DEBUG print (display)"),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "fstring",
        "html_text",
        1,
    ): ("line 566 — UI render"),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "fstring",
        "highlighted_text",
        1,
    ): ("line 321 — UI render"),
    (
        "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
        "fstring",
        "highlighted_text",
        2,
    ): ("line 385 — UI render"),
    (
        "argumentation_analysis/utils/debug_utils.py",
        "fstring",
        "full_text_preview",
        1,
    ): ("line 135 — debug log preview"),
    (
        "argumentation_analysis/utils/dev_tools/format_utils.py",
        "fstring",
        "matched_text",
        1,
    ): ("line 193 — dev-tool output line"),
    (
        "argumentation_analysis/utils/dev_tools/format_utils.py",
        "fstring",
        "matched_text",
        2,
    ): ("line 184 — dev-tool output line"),
    (
        "argumentation_analysis/utils/dev_tools/format_utils.py",
        "fstring",
        "matched_text",
        3,
    ): ("line 236 — dev-tool output line"),
    (
        "argumentation_analysis/utils/dev_tools/format_utils.py",
        "fstring",
        "matched_text",
        4,
    ): ("line 216 — dev-tool output line"),
    # --- not document text: formulas, metadata frames, spans, counts ---
    (
        "argumentation_analysis/agents/core/logic/fol_handler.py",
        "format-arg",
        "text",
        1,
    ): ("line 436 — formula fragment recursion, not document text"),
    (
        "argumentation_analysis/agents/core/logic/fol_handler.py",
        "fstring",
        "text",
        1,
    ): ("line 420 — formula fragment recursion, not document text"),
    (
        "argumentation_analysis/agents/core/synthesis/deep_synthesis_agent.py",
        "fstring",
        "contextual_frame",
        1,
    ): ("line 1711 — source metadata frame into the synthesis prompt"),
    (
        "argumentation_analysis/agents/core/synthesis/deep_synthesis_agent.py",
        "fstring",
        "context_block",
        1,
    ): ("line 1712 — SECTION-1 state-data block (bounded state fields)"),
    (
        "argumentation_analysis/agents/core/synthesis/deep_synthesis_agent.py",
        "fstring",
        "contextual_frame",
        2,
    ): ("line 774 — report render line (metadata frame)"),
    (
        "argumentation_analysis/agents/core/synthesis/deep_synthesis_agent.py",
        "fstring",
        "contextual_frame",
        3,
    ): ("line 1547 — prompt block line (metadata frame)"),
    (
        "argumentation_analysis/agents/core/synthesis/deep_synthesis_agent.py",
        "fstring",
        "textual_span",
        1,
    ): ("line 796 — fallacy span quote (unit-level) in report render"),
    (
        "argumentation_analysis/plugins/kb_to_tweety_plugin.py",
        "fstring",
        "text",
        1,
    ): ("line 217 — formula/belief-set string"),
    # --- scaffolding / harness ---
    (
        "argumentation_analysis/agents/templates/student_template/agent.py",
        "format-kwarg",
        "text",
        1,
    ): ("line 70 — student template scaffold, not wired on the analysis path"),
    (
        "argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py",
        "fstring",
        "short_text",
        1,
    ): ("line 83 — display row (already-truncated preview)"),
    (
        "argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py",
        "fstring",
        "short_text",
        2,
    ): ("line 203 — display row (already-truncated preview)"),
    (
        "argumentation_analysis/evaluation/fallacy_benchmark.py",
        "fstring",
        "taxonomy_text",
        1,
    ): (
        "line 636 — evaluation-harness prompt; carries the fixed taxonomy "
        "listing, not document text"
    ),
}


def test_every_unbounded_doc_text_interpolation_is_registered():
    """The gate: census keys == ALLOWED keys, both directions.

    A site the census reads and ALLOWED lacks is NEW UNREGISTERED UNBOUNDED
    TEXT — bound it (selected_text, #1737) or name it here with a triage. An
    ALLOWED row without a site is STALE — the site was bounded, renamed or
    deleted; delete the row, do not keep dead debt.
    """
    found = census()
    missing = sorted(set(found) - set(ALLOWED))
    stale = sorted(set(ALLOWED) - set(found))
    lines = []
    if missing:
        shown = [
            f"  {rel}:{found[(rel, kind, name, o)]} {kind} {name} #{o}"
            for rel, kind, name, o in missing[:20]
        ]
        lines.append(
            "NEW unbounded document-text interpolation(s) not in ALLOWED — "
            "bound them (selected_text, #1737) or register a triage row:\n"
            + "\n".join(shown)
            + (f"\n  … and {len(missing) - 20} more" if len(missing) > 20 else "")
        )
    if stale:
        shown = [f"  {rel} {kind} {name} #{o}" for rel, kind, name, o in stale[:20]]
        lines.append(
            "STALE ALLOWED row(s) — no such site in the census (bounded, "
            "renamed or deleted); delete the row:\n"
            + "\n".join(shown)
            + (f"\n  … and {len(stale) - 20} more" if len(stale) > 20 else "")
        )
    assert not lines, "\n\n".join(lines)


def test_the_one_shot_no_longer_reads_the_text_unbounded():
    """#2908's own fix, as a named mutation guard: the fallacy one-shot must
    interpolate a BOUNDED window (selected_text, censused as a window by the
    #2850 guard), never the bare ``argument_text``. Reverting the bound makes
    the gate above fail with this file's row — this test says it in words."""
    found = census()
    one_shot = [
        key
        for key in found
        if key[0] == "argumentation_analysis/plugins/fallacy_workflow_plugin.py"
        and key[2] == "argument_text"
    ]
    assert not one_shot, (
        "the one-shot (or a sibling in fallacy_workflow_plugin) interpolates "
        f"argument_text with no bound again: {one_shot} — bound it through "
        "selected_text (see #2908)"
    )


def test_positive_control_a_planted_interpolation_is_found():
    """The instrument is a measurement — mutation-proof it on a synthetic
    module: the planted unbounded interpolation is found with its exact key
    material, and every bounded or out-of-boundary form is NOT counted."""
    snippet = (
        "from x import selected_text\n"
        "def f(argument_text, text, start, fallacy_id):\n"
        "    a = f'prompt {argument_text}'\n"  # planted: the #2908 defect
        "    b = f'prompt {text[:800]}'\n"  # bounded head slice
        "    c = f'prompt {selected_text(text, 100, \"s\")}'\n"  # the shared window
        "    d = f'prompt {text.lower()}'\n"  # derived (call)
        "    e = f'prompt {text[start:]}'\n"  # unbounded UPPER: counted
        "    g = f'label {fallacy_id}'\n"  # outside the name set (boundary)
        "    h = 'prompt {}'.format(text)\n"  # .format arg
        "    return a, b, c, d, e, g, h\n"
    )
    ordinal_of = {}
    keys = set()
    for kind, name, lineno in _sites_in_tree(ast.parse(snippet)):
        if name.replace("[…:]", "") not in _DOC_TEXT_NAMES:
            continue
        key3 = (kind, name)
        ordinal_of[key3] = ordinal_of.get(key3, 0) + 1
        keys.add(("synthetic", kind, name, ordinal_of[key3], lineno))
    assert ("synthetic", "fstring", "argument_text", 1, 3) in keys, (
        "the planted unbounded interpolation was not found — the census "
        "instrument is blind"
    )
    assert (
        "synthetic",
        "fstring",
        "text[…:]",
        1,
        7,
    ) in keys, "text[start:] carries no upper bound — it must be censused"
    assert (
        "synthetic",
        "format-arg",
        "text",
        1,
        9,
    ) in keys, ".format arguments are part of the population"
    assert {k for k in keys if k[2] == "text"} == {
        ("synthetic", "format-arg", "text", 1, 9)
    }, (
        "text[:800] (line 4), selected_text (line 5) and .lower() (line 6) "
        "must not count as bare names — only the .format arg may"
    )
    assert not any(k[2] == "fallacy_id" for k in keys), (
        "a non-doc-text name entered the census — update the boundary "
        "docstring and _DOC_TEXT_NAMES"
    )


def test_alias_control_single_assignment_is_followed():
    """R1058: a single-assignment alias does not hide a document read — the
    census keys it by the ROOT name, so the read lands on the root's ordinal
    series. The two limits are asserted, not silent: a name assigned more
    than once is not an alias (its later value may not be the document), and
    an alias of a non-document name is not a document read."""
    snippet = (
        "def f(argument_text, other):\n"
        "    windowed_text = argument_text\n"
        "    a = f'prompt {windowed_text}'\n"  # alias — the R1058 measured blindness
        "    snippet_text = argument_text\n"
        "    snippet_text = other\n"
        "    b = f'prompt {snippet_text}'\n"  # assigned twice — NOT an alias
        "    label = other\n"
        "    c = f'prompt {label}'\n"  # non-doc source — not a document read
        "    chained = argument_text\n"
        "    second = chained\n"
        "    d = f'prompt {second}'\n"  # alias chain — resolves to the root
        "    return a, b, c, d\n"
    )
    ordinal_of = {}
    keys = set()
    for kind, name, lineno in _sites_in_tree(ast.parse(snippet)):
        if name.replace("[…:]", "") not in _DOC_TEXT_NAMES:
            continue
        key3 = (kind, name)
        ordinal_of[key3] = ordinal_of.get(key3, 0) + 1
        keys.add(("synthetic", kind, name, ordinal_of[key3], lineno))
    assert keys == {
        ("synthetic", "fstring", "argument_text", 1, 3),
        ("synthetic", "fstring", "argument_text", 2, 11),
    }, (
        "the census must see through windowed_text (line 3) and the chain "
        "second/chained (line 11) as argument_text — and ONLY those: the "
        "twice-assigned snippet_text (line 6) and the non-doc label (line 8) "
        "stay outside"
    )
