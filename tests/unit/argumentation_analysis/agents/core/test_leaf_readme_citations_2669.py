"""#2669: the leaf READMEs of ``agents/core/`` cite code by name, and the names resolve.

The READMEs used to cite ``file.py:N`` and ```Symbol` :N``. Measured on
``main`` ``255f5fefd``: 637 such citations (265 ``path:N``, 275 ``symbol :N``,
about 97 bare ``:N``). Of the 332 whose symbol and file could be paired, 203
no longer landed on their symbol: up to +89 lines off in ``quality/``, and 0
of 20 in ``synthesis/`` still landed. A line number drifts with every
insertion above it, and prose gives a reader no way to notice. #2669 removed
them: a citation names its file and its symbol.

Three checks keep it that way:

* no line-number citation comes back (``path.py:N``, ```:N```, a bare
  ``:N``, ``l. N``, a bold ``**N-M**`` range, a ``#LN`` anchor);
* every cited path is a tracked file or directory: a backticked ``*.py`` /
  ``*.json`` / ... is matched as a path suffix, and a relative link must
  resolve from the README's own directory;
* every backticked code name (snake_case, CamelCase, dotted, or called with
  ``()``) occurs in the tracked production source, is defined (``def``,
  ``class``, assignment) in a tracked test, or is Python's own. A mere mention
  under ``tests/``, ``docs/`` or an archive does not count, so a name that
  survives only as a test's failure string (as ``FirstOrderLogicAgent`` did)
  does not resolve.

Run on the rewritten READMEs, the checks found five citations that no
line-number drift explains: the relative links to ``abc/`` in
``counter_argument`` and ``logic`` climbed one directory too many, ``logic``
linked ``FirstOrderLogicAgent`` in ``first_order_logic_agent.py`` (the class
is ``FOLLogicAgent`` in ``fol_logic_agent.py``), and ``abc`` gave the retired
``synthesis/synthesis_agent.py`` as an importer of ``BaseAgent``.

The name check is a presence check, not a location check: a name that still
exists elsewhere in the tree passes even if it left the file the README pairs
it with. The path check has the same limit for a homonym file.

A README may name what is gone on purpose: a retired module, an attribute
stated absent, a hypothetical subclass. Those names live in
``ABSENT_BY_DESIGN`` with their reason. Each entry must really be absent and
really be cited, so the map cannot shelter a live name or outlive its
citation.
"""

import builtins
import keyword
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
README = re.compile(r"argumentation_analysis/agents/core/(?:\w+/)?README\.md")
# 14 leaf READMEs on 2026-09-26; far fewer means the census missed them.
MIN_READMES = 10

LINE_REFERENCES = {
    "path:N": re.compile(r"\.(?:py|json|md|ya?ml|ipynb|toml|ini):\d"),
    "`:N`": re.compile(r"`:\d"),
    "bare :N": re.compile(r"(?:^|[\s(/])(?:ex-)?:\d{1,5}\b"),
    "l. N": re.compile(r"(?<![\w.])l\. ?\d"),
    "**N-M**": re.compile(r"\*\*\d{2,5}-\d{2,5}\*\*"),
    "#LN": re.compile(r"#L\d"),
}
EXTENSIONS = r"(?:py|json|md|ya?ml|ipynb|toml|ini)"
PATH_TOKEN = re.compile(r"[\w./{},-]+\." + EXTENSIONS)
SPAN = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\]\(([^)\s]+)\)")
CODE_NAME = re.compile(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(\(\))?")
SOURCE = re.compile(r"\.(?:py|json|ya?ml|toml|ini|cfg)$")
NOT_SOURCE = re.compile(r"(?:tests|docs)/|.*_archive")
TEST_DEFINITION = re.compile(
    r"^\s*(?:(?:async\s+)?def|class)\s+(\w+)|^\s*(\w+)\s*(?::[^=\n]+)?=(?!=)",
    re.MULTILINE,
)

ABSENT_BY_DESIGN = {
    # paths, as cited
    "core/plugin_loader.py": "retired by #2145 with the abc plugin ABC",
    "agents/core/plugin_loader.py": "retired by #2145 with the abc plugin ABC",
    "abc/plugin.py": "retired by #2145",
    "hypothesis_tracker.py": "retired by #2137",
    "oracle/hypothesis_tracker.py": "retired by #2137",
    "tests/unit/argumentation_analysis/test_sherlock_atms_branching.py": (
        "retired by #2137 with the tracker it imported"
    ),
    "test_governance_simulation.py": "retired by #2137 with simulation.py",
    "tests/.../test_governance_simulation.py": "retired by #2137 with simulation.py",
    "synthesis_agent.py": "retired by #2140",
    "orchestration/operational/direct_executor.py": "retired by #2140",
    ".cache/_g8_smoke.py": "a gitignored local scratch, never tracked",
    # code names
    "ParameterSpec": "retired by #2145 with the abc plugin ABC",
    "_get_quality_llm": "the README records this former docstring citation as gone",
    "_DEFAULT_LLM": "retired by #2137 with set_default_llm_callable",
    "data_models": "retired by #2140 with SynthesisAgent",
    "UnifiedReport": "retired by #2140 with data_models",
    "LogicAnalysisResult": "retired by #2140 with data_models",
    "InformalAnalysisResult": "retired by #2140 with data_models",
    "agent_logger": "stated absent: the logger is the private _agent_logger",
    # retired by #2699 with the scripted PM stack (its runner went in #2638/#2704).
    # "ProjectManagerAgent" needs no entry: the name still occurs in the live
    # designation vocabulary of other agents' prompts; "prompts.py" neither: it
    # is a tracked suffix elsewhere. Only these are wholly gone:
    "core/pm/pm_agent.py": "retired by #2699",
    "pm_definitions.py": "retired by #2699",
    # retired by #1649 with the Walton-Krabbe relations channel (the README
    # records which import used to live in dung_arbitration_stage.py).
    "WALTON_KRABBE_ATTACKING_ACTS": "retired by #1649 with the WK channel",
}


@lru_cache(maxsize=1)
def _tracked():
    listed = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return tuple(listed)


@lru_cache(maxsize=1)
def _tracked_dirs():
    return frozenset(
        str(parent).replace(os.sep, "/")
        for path in _tracked()
        for parent in Path(path).parents
    )


@lru_cache(maxsize=1)
def _source_words():
    """Identifiers of the production source, of test definitions, and Python's."""
    words = set(dir(builtins)) | set(dir(type)) | set(keyword.kwlist)
    for path in _tracked():
        file = REPO / path
        if not SOURCE.search(path) or not file.is_file():
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        if not NOT_SOURCE.match(path):
            words.update(re.findall(r"[A-Za-z_]\w*", text))
        elif path.startswith("tests/") and path.endswith(".py"):
            words.update(filter(None, sum(TEST_DEFINITION.findall(text), ())))
    return frozenset(words)


def _readmes():
    return [path for path in _tracked() if README.fullmatch(path)]


def _text(readme):
    return (REPO / readme).read_text(encoding="utf-8")


def _line_references(text):
    """``(line number, form, line)`` for every line-number citation."""
    return [
        (number, form, line.strip())
        for number, line in enumerate(text.splitlines(), 1)
        for form, pattern in LINE_REFERENCES.items()
        if pattern.search(line)
    ]


def _expand(token):
    """``workflows/{a,b}.py`` -> ``workflows/a.py``, ``workflows/b.py``."""
    brace = re.search(r"\{([^{}]*)\}", token)
    if not brace:
        return [token]
    return [
        expanded
        for alternative in brace.group(1).split(",")
        for expanded in _expand(
            token[: brace.start()] + alternative.strip() + token[brace.end() :]
        )
    ]


def _cited_paths(text):
    """``(kind, token)`` for every relative link and every backticked path."""
    cited = []
    for match in LINK.finditer(text):
        target = match.group(1).split("#")[0]
        if target and not re.match(r"[a-z]+:", target):
            cited.append(("link", target))
    for match in SPAN.finditer(text):
        words = match.group(1).split()
        if words and PATH_TOKEN.fullmatch(words[0]):
            cited.extend(("span", token) for token in _expand(words[0]))
    return cited


def _suffix_resolves(token):
    token = token[2:] if token.startswith("./") else token
    pattern = re.compile(
        r"(?:^|/)" + re.escape(token).replace(re.escape("..."), ".*") + r"$"
    )
    return any(pattern.search(path) for path in _tracked())


def _resolves(kind, token, base):
    local = os.path.normpath(os.path.join(base, token)).replace(os.sep, "/")
    if local in _tracked() or local.rstrip("/") in _tracked_dirs():
        return True
    return kind == "span" and _suffix_resolves(token)


def _unresolved_paths(text, base):
    return sorted(
        token
        for kind, token in _cited_paths(text)
        if token not in ABSENT_BY_DESIGN and not _resolves(kind, token, base)
    )


def _looks_like_code(name, called):
    return called or bool(re.search(r"_|\.|[a-z][A-Z]|[A-Z]{2,}[a-z]", name))


def _code_names(text):
    names = []
    for match in SPAN.finditer(text):
        if PATH_TOKEN.fullmatch(match.group(1).strip()):
            continue
        name = CODE_NAME.fullmatch(match.group(1).strip())
        if name and _looks_like_code(name.group(1), bool(name.group(2))):
            names.append(name.group(1))
    return names


def _missing_names(text, words):
    return sorted(
        name
        for name in _code_names(text)
        if name not in ABSENT_BY_DESIGN
        and not all(segment in words for segment in name.split("."))
    )


def test_the_census_reads_the_leaf_readmes():
    readmes = _readmes()
    print(f"{len(readmes)} leaf READMEs: {readmes}")
    assert len(readmes) >= MIN_READMES, readmes


def test_no_line_number_citation():
    found = [
        f"{readme}:{number} [{form}] {line[:120]}"
        for readme in _readmes()
        for number, form, line in _line_references(_text(readme))
    ]
    assert found == [], "\n".join(found)


def test_every_cited_path_resolves():
    found = [
        f"{readme}: {token}"
        for readme in _readmes()
        for token in _unresolved_paths(_text(readme), str(Path(readme).parent))
    ]
    assert found == [], "\n".join(found)


def test_every_cited_code_name_exists_in_production_source():
    words = _source_words()
    found = [
        f"{readme}: {name}"
        for readme in _readmes()
        for name in _missing_names(_text(readme), words)
    ]
    assert found == [], "\n".join(found)


def test_absent_by_design_entries_are_absent_and_cited():
    texts = [_text(readme) for readme in _readmes()]
    cited = {token for text in texts for _, token in _cited_paths(text)}
    cited |= {name for text in texts for name in _code_names(text)}
    words = _source_words()
    stale = [entry for entry in ABSENT_BY_DESIGN if entry not in cited]
    alive = [
        entry
        for entry in ABSENT_BY_DESIGN
        if (_suffix_resolves(entry) if PATH_TOKEN.fullmatch(entry) else entry in words)
    ]
    assert stale == [], f"no README cites these any more: {stale}"
    assert alive == [], f"these exist again, revisit their README: {alive}"


LINE_REFERENCE_WITNESSES = {
    "path:N": "`quality_evaluator.py:263` `VERTUES`",
    "`:N`": "`evaluate` (`:630`)",
    "bare :N": "the whole-text fallback :570/:572",
    "l. N": "truncated l. 160",
    "**N-M**": "in `build_spectacular_workflow()` (**683-1066**)",
    "#LN": "[link](quality_evaluator.py#L12)",
}


def test_each_line_number_form_is_detected():
    # One literal witness per form, checked on its own line: a form dropped
    # from LINE_REFERENCES leaves its witness undetected.
    for form, line in LINE_REFERENCE_WITNESSES.items():
        assert form in {found for _, found, _ in _line_references(line)}, line
    assert set(LINE_REFERENCES) == set(LINE_REFERENCE_WITNESSES)


def test_a_missing_path_and_a_missing_name_are_detected():
    text = "`no/such/module_2669.py` and [gone](missing_2669.py)\n" + (
        "`NoSuchClass2669` and `no_such_function_2669()`"
    )
    assert _unresolved_paths(text, "argumentation_analysis/agents/core/quality") == [
        "missing_2669.py",
        "no/such/module_2669.py",
    ]
    assert _missing_names(text, _source_words()) == [
        "NoSuchClass2669",
        "no_such_function_2669",
    ]


def test_the_checks_let_real_citations_through():
    text = (
        "`quality_evaluator.py` `ArgumentQualityEvaluator`, `evaluate()`,"
        " `orchestration/workflows.py`, `workflows/{democratech,belief_dynamics}.py`,"
        " [plugin](../../../plugins/quality_scoring_plugin.py), [up](../README.md),"
        ' a mapping `{"k": 1}` and a slice `text[:5]` at 21:00'
    )
    assert _line_references(text) == []
    assert _unresolved_paths(text, "argumentation_analysis/agents/core/quality") == []
    assert _missing_names(text, _source_words()) == []


def test_a_test_mention_is_not_a_definition():
    # The two real cases: ``FirstOrderLogicAgent`` survives in ``tests/`` only
    # as an expected failure string; ``IN_SCOPE_COMPONENTS`` is a constant
    # the #1842 guard defines, and the political README cites it.
    words = _source_words()
    assert "FirstOrderLogicAgent" not in words
    assert "IN_SCOPE_COMPONENTS" in words
    assert _missing_names("`FirstOrderLogicAgent`", words) == ["FirstOrderLogicAgent"]
