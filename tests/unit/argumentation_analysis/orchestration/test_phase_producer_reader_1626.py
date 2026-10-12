"""Guard: a phase producer must have a reader on its OWN voie (#1626 item 4).

The defect this pins, measured once by hand (worker po-2025, R975) and stated
in #1626's body: a phase writes a state field on voie V, the field's only
reader sits on ANOTHER voie, and nothing reports it. ``neural_detect`` writes
``neural_fallacy_scores`` on spectacular; its one content reader,
``narrative_synthesis_plugin.build_narrative`` (l.81), lives on standard/full,
whose capability #1115 removed from spectacular. The report looks complete
while counting fewer fallacies than were detected, and the phase still costs a
model load for a result nothing reads.

Why this shape and not "no reader anywhere". The census that lists phases with
no reader at all is #1605's (8 of 40 phases reach no conclusion); it is a
different defect and it is tracked there. This guard pins the #1626 shape
only: a producer with a reader *elsewhere*. That restriction is not cosmetic —
most field reads on the conclusion path go through TABLES
(``ARTIFACT_FIELDS``, ``act3_conclusion_plugin._iter_formalism_specific``), so
a literal-access census cannot see them and a "no reader anywhere" guard would
be mostly noise. A cross-voie orphan is, by contrast, a measured fact: the
same field is read on this codebase, just not on this voie.

What the census reads (all static, no run):
  - producers: phases of a voie whose capability has a state writer in
    ``CAPABILITY_STATE_WRITERS``; the fields come from the writer's own source
    (``state.<attr> = ...``, ``state.<attr>[k] = ...``, or a ``state.add_<x>()``
    resolved to the ``self.<attr>`` that ``UnifiedAnalysisState.add_<x>``
    mutates — the two classes of ``shared_state.py`` are both walked, since
    ``UnifiedAnalysisState`` extends ``RhetoricalAnalysisState``).
  - readers: fields read inside a capability's invoker body and inside the
    functions that invoker calls by name (bounded to two levels). The
    capability -> invoker mapping is the one ``setup_registry()`` really
    builds — runtime truth, so every registration shape counts (direct
    calls, the row tables, the counter_argument patch); a literal-only read
    resolved 16 of 43 voie capabilities (#3021 review). Attribution
    is per CAPABILITY, never per module: every invoker lives in the single
    file ``invoke_callables.py``, so a module-granular census would attribute
    ``narrative_synthesis``'s read to every voie that touches that file.
  - the Acts are the deliverable and their reader is the restitution renderer,
    not a capability; ``reporting/restitution`` therefore counts as a reader
    for a voie that carries the acts.

The list below is the state of main when this guard landed, each entry
qualified by measurement. It is an equality, not a floor: a NEW cross-voie
orphan reddens (the future phase removal this guard exists for), and so does a
STALE entry — the moment the defect is repaired the entry stops matching, and
the list can only shrink. That is what makes the guard non-vacuous rather than
a snapshot nobody prunes.
"""

import ast
import inspect
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

SHARED_STATE = ROOT / "argumentation_analysis" / "core" / "shared_state.py"
REGISTRY_SETUP = ROOT / "argumentation_analysis" / "orchestration" / "registry_setup.py"
INVOKE_CALLABLES = (
    ROOT / "argumentation_analysis" / "orchestration" / "invoke_callables.py"
)

# The names the state object travels under on these paths — the reader census
# counts an access as a read only when it goes through one of them.
STATE_NAMES = {"state", "unified_state", "_state_object", "analysis_state"}

# Container mutations: `self.X.append(...)`, `self.X[k] = ...` is an Assign
# handled separately.
MUTATORS = {
    "append",
    "extend",
    "update",
    "insert",
    "add",
    "setdefault",
    "pop",
    "remove",
    "clear",
    "discard",
}

# ── The measured allowlist ──────────────────────────────────────────────────
# (voie, phase name) -> (fields, qualification measured on main).
# Each qualification names WHERE the reader is and WHY it is not on this voie.
KNOWN_CROSS_ORPHANS = {
    ("spectacular", "neural_detect"): (
        frozenset({"neural_fallacy_scores"}),
        "read by plugins/narrative_synthesis_plugin.py:81 build_narrative() "
        "on standard/full — the capability #1115 removed from spectacular. "
        "This is #1626's own case.",
    ),
    ("spectacular", "atms"): (
        frozenset({"atms_contexts", "jtms_beliefs"}),
        "atms_contexts read by _invoke_narrative_synthesis (populated-field "
        "diagnostic) on standard/full; no read on spectacular's conclusion "
        "path (deep_synthesis + acts).",
    ),
    ("standard", "aspic_analysis"): (
        frozenset({"aspic_results"}),
        "consumed by reporting/restitution/act3_conclusion_plugin.py:1171 "
        "(Acte III) — spectacular only.",
    ),
    ("full", "aspic_analysis"): (
        frozenset({"aspic_results"}),
        "consumed by reporting/restitution/act3_conclusion_plugin.py:1171 "
        "(Acte III) — spectacular only.",
    ),
    ("standard", "governance"): (
        frozenset({"governance_decisions"}),
        "consumed by reporting/restitution/act2_narrative_plugin.py:842 — "
        "spectacular only.",
    ),
    ("full", "governance"): (
        frozenset({"governance_decisions"}),
        "consumed by reporting/restitution/act2_narrative_plugin.py:842 — "
        "spectacular only.",
    ),
    ("standard", "debate"): (
        frozenset({"debate_transcripts"}),
        "listed in agents/core/synthesis/deep_synthesis_agent.py ARTIFACT_FIELDS "
        "(the spectacular deliverable).",
    ),
    ("full", "debate"): (
        frozenset({"debate_transcripts"}),
        "listed in agents/core/synthesis/deep_synthesis_agent.py ARTIFACT_FIELDS "
        "(the spectacular deliverable).",
    ),
}


def _tree(path):
    # utf-8-sig: several modules carry a BOM and ast.parse rejects U+FEFF.
    return ast.parse(Path(path).read_text(encoding="utf-8-sig"))


def _state_methods():
    """method name -> set of self attributes it mutates, across both classes."""

    def mutated(func_node):
        out = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    t = target
                    if isinstance(t, ast.Subscript):
                        t = t.value
                    if (
                        isinstance(t, ast.Attribute)
                        and isinstance(t.value, ast.Name)
                        and t.value.id == "self"
                    ):
                        out.add(t.attr)
            if isinstance(node, ast.Call):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr in MUTATORS
                    and isinstance(func.value, ast.Attribute)
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "self"
                ):
                    out.add(func.value.attr)
        return out

    methods = {}
    for node in ast.walk(_tree(SHARED_STATE)):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    attrs = mutated(item)
                    if attrs:
                        methods[item.name] = attrs
    return methods


def _writer_fields(writer):
    """Fields a state writer writes. Unresolvable add_ calls are returned so a
    caller can fail loud rather than silently counting the phase as a non-writer.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(writer)))
    methods = _state_methods()
    fields, unresolvable = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                t = target
                if isinstance(t, ast.Subscript):
                    t = t.value
                if (
                    isinstance(t, ast.Attribute)
                    and isinstance(t.value, ast.Name)
                    and t.value.id == "state"
                ):
                    fields.add(t.attr)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "state":
                meth = node.func.attr
                if meth.startswith("add_"):
                    resolved = methods.get(meth)
                    if resolved:
                        fields |= resolved
                    else:
                        unresolvable.add(meth)
    return fields, unresolvable


_INVOKER_CACHE = {}


def _capability_invokers():
    """capability -> invoker name, from the registry setup_registry() builds.

    Runtime truth, not a re-parse of the registration syntax: every
    registration shape lands in the same place — the direct
    ``register_*(capabilities=[...], invoke=...)`` calls, the row tables
    ``for name, caps, desc, invoke_fn in ...`` loops over
    (registry_setup.py:465/499/589/840), and the counter_argument module
    function whose invoke is patched onto the registration afterwards. A
    literal-only census resolved 16 of the 43 capabilities the voies request
    (#3021 review); the registry resolves what production resolves.
    """
    if _INVOKER_CACHE:
        return _INVOKER_CACHE
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    for registration in setup_registry()._registrations.values():
        invoke = getattr(registration, "invoke", None)
        name = getattr(invoke, "__name__", None)
        if name is None:
            continue
        for cap in registration.capabilities:
            _INVOKER_CACHE.setdefault(cap, name)
    return _INVOKER_CACHE


def _file_imports():
    """invoke_callables.py module-level imports: bound name -> dotted module."""
    alias_to_mod = {}
    for node in ast.walk(_tree(INVOKE_CALLABLES)):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("argumentation_analysis"):
                for a in node.names:
                    alias_to_mod[a.asname or a.name] = node.module
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("argumentation_analysis"):
                    alias_to_mod[a.asname or a.name.split(".")[-1]] = a.name
    return alias_to_mod


def _reads_in(node):
    fields = set()
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "getattr"
            and len(sub.args) >= 2
            and isinstance(sub.args[1], ast.Constant)
            and isinstance(sub.args[1].value, str)
        ):
            fields.add(sub.args[1].value)
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            if sub.value.id in STATE_NAMES:
                fields.add(sub.attr)
    return fields


def _module_path(dotted):
    rel = dotted.replace(".", "/")
    for cand in (ROOT / (rel + ".py"), ROOT / rel / "__init__.py"):
        if cand.exists():
            return cand
    return None


def _invoker_node(name):
    for node in ast.walk(_tree(INVOKE_CALLABLES)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def _module_functions():
    """module path -> {function name: node}, cached per call site of the census."""
    cache = {}

    def get(path):
        if path not in cache:
            cache[path] = {
                n.name: n
                for n in ast.walk(_tree(path))
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        return cache[path]

    return get


def _reader_fields_for_capability(cap, invokers, imports, functions):
    """Fields read by a capability: its invoker body + the functions it calls.

    Two levels deep. Nothing is attributed through a module wholesale: the
    invokers all live in one file, so a module-level attribution would credit
    every voie with every read in that file.
    """
    name = invokers.get(cap)
    if not name or name == "_invoke_ai_shield":
        return set()
    node = _invoker_node(name)
    if node is None:
        return set()
    fields = _reads_in(node)

    called_names, called_attrs = set(), {}
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Name):
                called_names.add(sub.func.id)
            elif isinstance(sub.func, ast.Attribute) and isinstance(
                sub.func.value, ast.Name
            ):
                called_attrs.setdefault(sub.func.value.id, set()).add(sub.func.attr)

    by_module = {}
    for alias, dotted in imports.items():
        by_module.setdefault(dotted, set()).add(alias)

    targets = {}
    for dotted, aliases in by_module.items():
        hit = aliases & called_names
        if hit:
            targets.setdefault(dotted, set()).update(hit)
    for bound, attrs in called_attrs.items():
        dotted = imports.get(bound)
        if dotted:
            targets.setdefault(dotted, set()).update(attrs)

    for dotted, names in targets.items():
        path = _module_path(dotted)
        if path is None:
            continue
        table = functions(path)
        for nm in names:
            fn = table.get(nm)
            if fn is None:
                continue
            fields |= _reads_in(fn)
            # level 2: what that function calls in turn
            inner_names, inner_attrs = set(), {}
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        inner_names.add(sub.func.id)
                    elif isinstance(sub.func, ast.Attribute) and isinstance(
                        sub.func.value, ast.Name
                    ):
                        inner_attrs.setdefault(sub.func.value.id, set()).add(
                            sub.func.attr
                        )
            inner_targets = {}
            for d2, aliases2 in by_module.items():
                hit2 = aliases2 & inner_names
                if hit2:
                    inner_targets.setdefault(d2, set()).update(hit2)
            for bound2, attrs2 in inner_attrs.items():
                d2 = imports.get(bound2)
                if d2:
                    inner_targets.setdefault(d2, set()).update(attrs2)
            for d2, names2 in inner_targets.items():
                p2 = _module_path(d2)
                if p2 is None:
                    continue
                t2 = functions(p2)
                for n2 in names2:
                    fn2 = t2.get(n2)
                    if fn2 is not None:
                        fields |= _reads_in(fn2)
    return fields


def _conclusion_path_reads():
    """Fields read anywhere in the restitution package (the Acts' renderer)."""
    fields = set()
    for py in (ROOT / "argumentation_analysis" / "reporting" / "restitution").rglob(
        "*.py"
    ):
        fields |= _reads_in(_tree(py))
    return fields


def census(voies):
    """{voie: [(phase, fields)]} for cross-voie orphan producers.

    A producer is a cross-voie orphan when none of the fields its writer writes
    is read by its own voie, while at least one of them IS read by another.
    """
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    invokers = _capability_invokers()
    imports = _file_imports()
    functions = _module_functions()
    conclusion_read = _conclusion_path_reads()

    read_by_cap = {}
    for wf in voies.values():
        for phase in wf.phases:
            if phase.capability not in read_by_cap:
                read_by_cap[phase.capability] = _reader_fields_for_capability(
                    phase.capability, invokers, imports, functions
                )

    read_by_voie = {}
    for voie, wf in voies.items():
        caps = {p.capability for p in wf.phases}
        read = set()
        for c in caps:
            read |= read_by_cap.get(c, set())
        if any(c.startswith("act") for c in caps) or "deep_synthesis" in caps:
            read |= conclusion_read
        read_by_voie[voie] = read

    report = {}
    unresolvable = set()
    for voie, wf in voies.items():
        own = read_by_voie[voie]
        elsewhere = set()
        for other, read in read_by_voie.items():
            if other != voie:
                elsewhere |= read
        found = []
        for phase in wf.phases:
            writer = CAPABILITY_STATE_WRITERS.get(phase.capability)
            if writer is None:
                continue
            fields, writer_unres = _writer_fields(writer)
            unresolvable |= writer_unres
            if not fields or fields & own:
                continue
            if fields & elsewhere:
                found.append((phase.name, frozenset(fields)))
        report[voie] = found
    assert not unresolvable, (
        "writers whose add_* the census cannot resolve to state fields: "
        f"{sorted(unresolvable)} — everything such a writer writes is "
        "invisible to this census; extend _state_methods or name the exception"
    )
    return report


def _real_voies():
    from argumentation_analysis.orchestration.workflows import (
        build_full_workflow,
        build_spectacular_workflow,
        build_standard_workflow,
    )

    return {
        "spectacular": build_spectacular_workflow(),
        "standard": build_standard_workflow(),
        "full": build_full_workflow(),
    }


def test_cross_voie_orphans_match_the_measured_allowlist():
    """The census equals the measured list — no new orphan, no stale entry.

    A new entry is the future phase removal this guard exists to fail. A
    vanished entry means the defect was repaired and the list must shrink.
    """
    found = {
        (voie, phase): fields
        for voie, entries in census(_real_voies()).items()
        for phase, fields in entries
    }
    expected = {key: fields for key, (fields, _why) in KNOWN_CROSS_ORPHANS.items()}

    new = sorted(set(found) - set(expected))
    stale = sorted(set(expected) - set(found))
    assert not new, (
        "new cross-voie orphan producer(s) — a producer writes a state field "
        "that no reader on its own voie consumes, while a reader exists on "
        "another voie. Either wire a reader on this voie, remove the producer, "
        f"or add a qualified entry here: {new}"
    )
    assert not stale, (
        "stale allowlist entry — this producer is no longer a cross-voie "
        f"orphan; remove it from KNOWN_CROSS_ORPHANS: {stale}"
    )
    for key, fields in found.items():
        assert fields == expected[key], (
            f"{key}: fields written changed to {sorted(fields)} "
            f"(measured {sorted(expected[key])}) — re-qualify the entry"
        )


def test_the_1626_case_is_in_the_list():
    """The issue's own case stays pinned: a guard that lost it proves nothing."""
    key = ("spectacular", "neural_detect")
    assert key in KNOWN_CROSS_ORPHANS
    assert "neural_fallacy_scores" in KNOWN_CROSS_ORPHANS[key][0]


def test_census_fails_a_synthetic_cross_voie_orphan():
    """Born-red by construction: a producer whose only reader is on another voie.

    The probe puts `neural_fallacy_detection` (writer: neural_fallacy_scores,
    read on standard/full) alone on a fresh voie. The census must report it
    cross-voie orphan — that is the property a future removal of a reader
    phase relies on.
    """
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    probe = (
        WorkflowBuilder("probe_1626")
        .add_phase("neural_detect", capability="neural_fallacy_detection")
        .build()
    )
    voies = dict(_real_voies())
    voies["probe_1626"] = probe

    report = census(voies)
    probe_orphans = dict(report["probe_1626"])
    assert "neural_detect" in probe_orphans, (
        "the census failed to flag a producer whose only reader is on another "
        "voie — the guard is vacuous"
    )
    assert "neural_fallacy_scores" in probe_orphans["neural_detect"]


def test_allowlist_entries_are_qualified_by_measurement():
    """Every entry names where its reader is: a list without proof is a shrug."""
    for key, (fields, why) in KNOWN_CROSS_ORPHANS.items():
        assert fields, f"{key} carries no field"
        assert why.strip(), f"{key} carries no qualification"
        assert (
            len(why) > 40
        ), f"{key}: qualification too thin to check — name the reader's site"


INVOKER_UNRESOLVED = frozenset()
"""Voie capabilities allowed to have no resolved invoker. Measured empty on
main `bc55357ef`: the registry setup_registry() builds resolves every one,
whatever its registration shape. A capability that lands here reads as no
read at all — name it only with a measured reason."""


def test_every_voie_capability_has_a_resolved_invoker():
    """A capability the census cannot resolve to an invoker contributes no
    reads — #3021's blind spot, measured at 27 of 43 voie capabilities by
    the review. The registry resolves every one today; this pins it, so a
    registration shape the census stops seeing reddens here instead of
    silently blinding half the voies."""
    invokers = _capability_invokers()
    missing = sorted(
        f"{voie}/{phase.name} ({phase.capability})"
        for voie, wf in _real_voies().items()
        for phase in wf.phases
        if phase.capability not in invokers
        and phase.capability not in INVOKER_UNRESOLVED
    )
    assert not missing, f"voie capabilities with no resolved invoker: {missing}"


def test_a_row_registered_invoker_counts_as_a_reader():
    """Born-red for the registry resolution: a reader registered through a
    row table must count. `fol_reasoning`'s invoker is registered in the
    logic row table, and it reads `identified_arguments`, which
    `fact_extraction` writes. On a voie carrying just those two phases, the
    literal-only census called the producer an orphan; the registry-resolved
    census sees the read (#3021 review's loud direction, made impossible)."""
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    probe = (
        WorkflowBuilder("probe_1626_rows")
        .add_phase("extract", capability="fact_extraction")
        .add_phase("fol", capability="fol_reasoning")
        .build()
    )
    voies = dict(_real_voies())
    voies["probe_1626_rows"] = probe

    report = census(voies)
    orphans = dict(report["probe_1626_rows"])
    assert "extract" not in orphans, (
        "a producer whose own voie carries a reader — registered through a "
        "row table — was still called an orphan: the census is blind to that "
        "registration shape again"
    )


def _voie_without(wf, dropped_phase):
    """Rebuild a workflow minus one phase — the #1115 removal, replayed."""
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    builder = WorkflowBuilder(wf.name + "_minus_" + dropped_phase)
    for phase in wf.phases:
        if phase.name == dropped_phase:
            continue
        builder.add_phase(
            phase.name,
            capability=phase.capability,
            optional=phase.optional,
            depends_on=list(phase.depends_on),
        )
    return builder.build()


def test_removing_a_reader_phase_reddens_a_producer():
    """Born-red: the #1626 DoD, replayed on the voie where it would happen.

    On standard, `neural_detect` has a reader — `narrative_synthesis`, whose
    build_narrative() reads neural_fallacy_scores. Removing that phase is
    exactly the #1115 shape (a capability withdrawn from a voie takes the only
    reader with it). The census must then report neural_detect as a cross-voie
    orphan on standard too, which makes the equality assertion above red.
    """
    voies = _real_voies()
    standard = voies["standard"]
    assert any(
        p.name == "narrative_synthesis" for p in standard.phases
    ), "standard no longer carries narrative_synthesis — re-point this witness"

    before = {phase for phase, _f in census(voies)["standard"]}
    assert "neural_detect" not in before, (
        "neural_detect is already a cross-voie orphan on standard — the witness "
        "must start from the state where its reader is present"
    )

    voies["standard"] = _voie_without(standard, "narrative_synthesis")
    after = {phase for phase, _f in census(voies)["standard"]}
    assert "neural_detect" in after, (
        "removing narrative_synthesis from standard left neural_detect NOT "
        "flagged — the guard does not fail a phase removal that orphans a "
        "producer on its voie, which is the whole point of #1626 item 4"
    )
