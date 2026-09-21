"""#2352 — ONE LLM route resolver in production; the copies CALL it.

The audit measured six resolvers for one route, four diverging. The repair is
**delegation**, not a shared helper pasted into five files: every migrated site
calls :func:`resolve_chat_endpoint` and nothing else re-implements the
OpenRouter toggle.

The audit's census was bounded to ``argumentation_analysis/`` — a positive
census is an absence verdict in disguise, and it missed the **measurement
scripts**, whose defect is worse than a wrong call: they run a pipeline on one
model and stamp the artefact with another name, so no reading of the output can
see it. R1034 therefore adds (a) the four ``scripts/`` sites converted by
delegation, measured **in a subprocess** because those modules load ``.env``,
``chdir`` and (``run_fb32``) ``sys.exit`` at import time, and (b) a census over
every production root, frozen file by file so a new copy reddens anywhere —
including ``argumentation_analysis/``, where the same sweep found five more
files the first audit never walked.

Two divergence classes, both measured on the seat ``.env.example`` prescribes
(only ``OPENAI_CHAT_MODEL_ID`` is set, so ``OPENROUTER_CHAT_MODEL_ID`` is
absent — the normal case for that seat, and the case where the copies broke):

- **A — missing jump**: the two mirrors read ``OPENROUTER_CHAT_MODEL_ID`` and
  fell to a hardcoded literal instead of ``OPENAI_CHAT_MODEL_ID``, so they never
  saw the prescribed seat's model and never applied the #1930 obsolescence
  table (measured: ``gpt-5-mini`` where the canonical resolver renders
  ``gpt-5.6-luna``);
- **B — provider-prefixed literal**: three sites defaulted to
  ``openai/gpt-5.6-luna``, a string no resolver returns — divergent in *every*
  configuration where ``OPENROUTER_CHAT_MODEL_ID`` is absent, obsolescence or
  not.

These tests import **no post-repair symbol at module level**, so the né-rouge
on pre-repair main is a *model value* failure, never an ``ImportError``. They
own every route env var, so no inherited ``.env`` can make a case pass by
accident. The last test measures the file text rather than the call graph: the
delegation tests pin today's wiring, the structural one keeps the next copy
from being born.
"""

import ast
import json
import os
import re
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pytest

from argumentation_analysis.core.llm_service import (
    resolve_active_model_id,
    resolve_chat_endpoint,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Every knob a route resolver could consult. Each test owns all of them, so an
# inherited .env value cannot decide an outcome.
_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
)

# The files that used to re-derive the toggle. `core/llm_service.py` is absent
# on purpose: it is where the route environment is allowed to be read.
_NON_CANONICAL_FILES = (
    "argumentation_analysis/evaluation/fallacy_benchmark.py",
    "argumentation_analysis/orchestration/conversational_orchestrator.py",
    "argumentation_analysis/orchestration/invoke_callables.py",
    "argumentation_analysis/plugins/coordinated_logic_plugin.py",
    "argumentation_analysis/services/nl_to_logic.py",
    "argumentation_analysis/services/ai_shield/layers/llm_validator.py",
)

_ROUTE_ENV_READ = re.compile(
    r"""environ(?:\.get\(\s*|\[\s*)["']"""
    r"""(OPENROUTER_[A-Z_]*|OPENAI_CHAT_MODEL_ID|OPENAI_BASE_URL|OPENAI_API_KEY)["']"""
)


def _seat_without_openrouter_model(monkeypatch: pytest.MonkeyPatch, model: str) -> None:
    """The seat ``.env.example`` prescribes: the OpenRouter pair, no model id.

    ``OPENROUTER_CHAT_MODEL_ID`` absent is what makes the canonical resolver
    jump to ``OPENAI_CHAT_MODEL_ID`` — the jump the two mirrors did not have.
    """
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-synthetic-not-a-real-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", model)


async def _nl_to_logic_model(monkeypatch: pytest.MonkeyPatch) -> str:
    """The model id ``nl_to_logic`` actually sends.

    Recorded on the client that site builds: the stub appends the request kwargs
    and then fails, so the retry loop ends without reaching Tweety validation.
    Nothing leaves the machine — ``openai.AsyncOpenAI`` is replaced.
    """
    from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

    sent: List[Dict[str, Any]] = []

    class _Completions:
        async def create(self, **kwargs: Any) -> Any:
            sent.append(kwargs)
            raise RuntimeError("recording stub — no API call is made")

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _Client:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = _Chat()

    monkeypatch.setattr("openai.AsyncOpenAI", _Client)
    translator = NLToLogicTranslator(max_retries=1)
    await translator._translate_with_llm("Un argument quelconque.", "propositional")

    assert sent, "nl_to_logic never built a chat completion — nothing to measure"
    return sent[0]["model"]


async def _all_site_models(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """The model id each migrated site would send/name, keyed by site."""
    from argumentation_analysis.orchestration.invoke_callables import _resolve_llm_route
    from argumentation_analysis.plugins.coordinated_logic_plugin import (
        _get_openai_client,
    )
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorLayer,
    )

    return {
        "core.resolve_active_model_id": resolve_active_model_id(),
        "invoke_callables._resolve_llm_route": _resolve_llm_route()[2],
        "coordinated_logic_plugin._get_openai_client": _get_openai_client()[1],
        "nl_to_logic._translate_with_llm": await _nl_to_logic_model(monkeypatch),
        "llm_validator.LLMValidatorLayer": LLMValidatorLayer()._model,
    }


async def test_measured_seat_agrees_with_the_canonical_resolver(monkeypatch):
    """THE measured divergence, on the seat the repo prescribes.

    Pre-repair this reddens on **model values**: ``gpt-5-mini`` from the two
    mirrors (class A — no #1930 substitution) and ``openai/gpt-5.6-luna`` from
    the three literals (class B) — never on an ImportError.
    """
    _seat_without_openrouter_model(monkeypatch, model="gpt-5-mini")  # retired (#1930)
    canonical = resolve_chat_endpoint()[2]
    assert canonical == "gpt-5.6-luna", "the canonical resolver must substitute it"

    models = await _all_site_models(monkeypatch)

    divergent = {site: model for site, model in models.items() if model != canonical}
    assert (
        not divergent
    ), f"sites diverging from the canonical model {canonical!r}: {divergent}"


async def test_no_site_names_a_provider_prefixed_literal(monkeypatch):
    """Class B isolated: same seat, a NON-retired ``OPENAI_CHAT_MODEL_ID``.

    The two mirrors agreed pre-repair in this configuration (the model is not
    obsolete, so the missing substitution was invisible) — which is exactly why
    the three ``openai/gpt-5.6-luna`` literals need their own case: they diverge
    by *prefix* whenever ``OPENROUTER_CHAT_MODEL_ID`` is absent.
    """
    _seat_without_openrouter_model(monkeypatch, model="gpt-5.6-luna")

    models = await _all_site_models(monkeypatch)

    assert set(models.values()) == {"gpt-5.6-luna"}, models


async def test_declared_openrouter_model_control_agreed_before_and_after(monkeypatch):
    """Non-vacuity control: this case passed on pre-repair main too.

    With ``OPENROUTER_CHAT_MODEL_ID`` set, all five sites already agreed — so a
    green suite here cannot be read as "the repair fixed what was never broken".
    It pairs with the measured-seat test to show the divergence was
    configuration-dependent, not universal.
    """
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-synthetic-not-a-real-key")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL_ID", "gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-4o")  # never consulted

    models = await _all_site_models(monkeypatch)

    assert set(models.values()) == {"gpt-5.6-luna"}, models


async def test_every_site_calls_the_canonical_resolver(monkeypatch):
    """Delegation, not coincidence: make the canonical resolver return a
    sentinel and check each site follows it.

    A copy that re-derived the toggle from the environment cannot see the
    sentinel, whatever the environment says — so this reddens on any re-inlined
    resolver. On pre-repair main it fails because the delegates do not exist
    (``AttributeError`` on the patch), which is the point: the delegation is
    what is being asserted.
    """
    import argumentation_analysis.core.llm_service as llm_service
    import argumentation_analysis.orchestration.invoke_callables as invoke_callables
    import argumentation_analysis.plugins.coordinated_logic_plugin as coordinated
    import argumentation_analysis.services.ai_shield.layers.llm_validator as validator
    import argumentation_analysis.services.nl_to_logic as nl_to_logic

    sentinel = (
        "sk-sentinel-not-a-real-key",
        "https://sentinel.invalid/v1",
        "sentinel-model",
    )

    def _sentinel_resolver(*_args: Any, **_kwargs: Any):
        return sentinel

    for module in (llm_service, invoke_callables, coordinated, nl_to_logic, validator):
        monkeypatch.setattr(module, "resolve_chat_endpoint", _sentinel_resolver)

    from argumentation_analysis.orchestration.invoke_callables import _resolve_llm_route
    from argumentation_analysis.plugins.coordinated_logic_plugin import (
        _get_openai_client,
    )
    from argumentation_analysis.services.ai_shield.layers.llm_validator import (
        LLMValidatorLayer,
    )

    assert resolve_active_model_id() == "sentinel-model"
    assert _resolve_llm_route() == (
        "sk-sentinel-not-a-real-key",
        "https://sentinel.invalid/v1",
        "sentinel-model",
        "openai",  # classify_route of a non-OpenRouter endpoint
    )
    assert _get_openai_client()[1] == "sentinel-model"
    assert await _nl_to_logic_model(monkeypatch) == "sentinel-model"

    layer = LLMValidatorLayer()
    assert layer._model == "sentinel-model"
    assert layer._base_url == "https://sentinel.invalid/v1"


@pytest.mark.parametrize("relpath", _NON_CANONICAL_FILES)
def test_no_non_canonical_file_reads_the_route_environment(relpath: str) -> None:
    """Structural guard: among the migrated files, the route environment is
    read in ``core/llm_service.py`` and nowhere else.

    The delegation test pins today's call graph; this one pins the file text, so
    a future copy that "just needs the key here" reddens at review time instead
    of at the next silent divergence.
    """
    source = (REPO_ROOT / relpath).read_text(encoding="utf-8")

    found = sorted(set(_ROUTE_ENV_READ.findall(source)))

    assert not found, (
        f"{relpath} reads the route environment ({found}) — it must call "
        "resolve_chat_endpoint instead of re-deriving the toggle (#2352)."
    )


# ---------------------------------------------------------------------------
# R1034 — the measurement scripts, and the census over the roots the first
# audit did not walk
# ---------------------------------------------------------------------------

# The four measurement harnesses the R1034 dispatch named. They are not
# services: they decide the route of a run and stamp the resulting artefact
# with the model's name, so a divergence here is a false provenance.
_MEASUREMENT_SCRIPTS = (
    "scripts/run_capstone_c1.py",
    "scripts/run_fb28_quality_headtohead.py",
    "scripts/run_fb29_agentic_headtohead.py",
    "scripts/run_fb32_decast_variance.py",
)

# `tests/` is deliberately absent: a test owns the route environment to *set* a
# seat, which is not a route decision.
_CENSUS_ROOTS = ("argumentation_analysis", "scripts", "project_core", "api")

_MODEL_VARS = ("OPENAI_CHAT_MODEL_ID", "OPENROUTER_CHAT_MODEL_ID")

# The frozen census (#2352 remainder, tracked by #2370). Every production file
# that READS a model id is named here with what that read feeds: a new copy is
# not a key and reddens; an entry that stopped reading is stale and reddens; a
# file that gained a read reddens on the value tuple. This green claims the
# population is **counted**, never that the route is unified.
_FROZEN_ROUTE_MODEL_READS: Dict[str, Tuple[Tuple[str, ...], str]] = {
    "argumentation_analysis/core/llm_service.py": (
        ("OPENAI_CHAT_MODEL_ID", "OPENROUTER_CHAT_MODEL_ID"),
        "the ONE resolver — the only place the route environment is read on purpose",
    ),
    "argumentation_analysis/evaluation/model_registry.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 B — raw SDK registry, same hardcoded-endpoint default",
    ),
    "argumentation_analysis/evaluation/run_provenance.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 C — a provenance label: a drift here stamps artefacts with a model the run never used",
    ),
    "scripts/apps/sherlock_watson/validation_point1_simple.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A/C — two decisions + one trace label",
    ),
    "scripts/baseline_0shot.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A — builds its client on the raw OpenAI pair, no toggle",
    ),
    "scripts/compare_fallacy_detection_modes.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A — three mode runners each decide their own model",
    ),
    "scripts/maintenance/repair_commit_json.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A — maintenance tool; reads without a fallback and refuses when absent",
    ),
    "scripts/run_fallacy_benchmark.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 C — prints the model it is about to use",
    ),
    "scripts/scda_deepsynthesis_vs_baseline.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A — `gpt-4o-mini` fallback, a literal no resolver renders",
    ),
    "scripts/sherlock_watson/run_einstein_oracle_demo.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A — kernel service built from the env with a `gpt-4o-mini` fallback",
    ),
    "scripts/validation/analyze_random_extract.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 A — logs the model then runs the analysis on it",
    ),
    "scripts/validation/test_environment_simple.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 D — a diagnostic: reading the configuration IS the test",
    ),
    "scripts/validation/validation_environnement_simple.py": (
        ("OPENAI_CHAT_MODEL_ID",),
        "#2370 D — an environment census; delegating here would be wrong",
    ),
}


def _const_str(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _tracked_python_files(root: Path, roots: Sequence[str]) -> List[Path]:
    """``git ls-files``, never a directory walk.

    A local walk counts the ``.py`` a working tree carries and CI does not (and
    vice versa), so the census would differ by machine — the guard has to
    measure the repository, not the checkout.
    """
    listing = subprocess.run(
        ["git", "ls-files", *roots],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [root / line for line in listing.splitlines() if line.endswith(".py")]


def _model_id_read_sites(
    files: Iterable[Path], root: Path
) -> Dict[str, Tuple[str, ...]]:
    """relpath -> the model-id variables that file READS.

    AST, not grep, for three measured reasons: a ``grep`` counts the deliberate
    ``os.environ["OPENROUTER_CHAT_MODEL_ID"] = ...`` **write** in
    ``measure_1629_attack_pairing.py`` as a read; it matches the same string in
    comments and docstrings; and it cannot tell a load from a store. Parsing
    also lets the sweep report the population it walked, so a file that failed
    to parse cannot silently shrink the census.
    """
    found: Dict[str, Tuple[str, ...]] = {}
    for path in files:
        # utf-8-sig: `ast.parse` in strict utf-8 raises on a BOM (#2357).
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        read_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("get", "getenv") and node.args:
                    name = _const_str(node.args[0])
                    if name in _MODEL_VARS:
                        read_vars.add(name)
            elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
                name = _const_str(node.slice)
                if name in _MODEL_VARS:
                    read_vars.add(name)
        if read_vars:
            found[str(path.relative_to(root)).replace("\\", "/")] = tuple(
                sorted(read_vars)
            )
    return found


def test_the_route_model_census_is_complete_and_frozen() -> None:
    """Every production file that reads a model id is named, with its class.

    Three failures, three different defects: an **unexpected** file is a new
    copy of the defect; a **stale** entry is a repair that never updated the
    census; a **drifted** value tuple is a file that grew another read.
    """
    files = _tracked_python_files(REPO_ROOT, _CENSUS_ROOTS)
    assert files, "git ls-files walked no file — this census measured nothing"

    found = _model_id_read_sites(files, REPO_ROOT)

    unexpected = {p: v for p, v in found.items() if p not in _FROZEN_ROUTE_MODEL_READS}
    stale = {p: v for p, v in _FROZEN_ROUTE_MODEL_READS.items() if p not in found}
    drifted = {
        p: (expected[0], v)
        for p, v in found.items()
        if p in _FROZEN_ROUTE_MODEL_READS
        for expected in (_FROZEN_ROUTE_MODEL_READS[p],)
        if v != expected[0]
    }

    assert not unexpected, (
        f"new route-model reader(s) outside the census: {unexpected} — call "
        "resolve_chat_endpoint instead of reading the model id (#2352)."
    )
    assert not stale, (
        f"the census lists file(s) that no longer read a model id: {stale} — "
        "they were converted, drop the entries so the census keeps meaning "
        "something."
    )
    assert not drifted, (
        f"file(s) whose model-id reads changed: {drifted} (expected, found) — "
        "update the census deliberately, or delegate the new read."
    )


def test_the_census_sweep_can_render_non_zero(tmp_path: Path) -> None:
    """Non-vacuity, on a synthetic carrier built at run time.

    The guard above is green; without this control a sweep that silently
    matched nothing would be green for the same reason. It also pins the two
    exclusions that keep the census honest: a **write** of the variable is not a
    read, and a file that delegates is not a reader.
    """
    carrier = tmp_path / "carrier.py"
    carrier.write_text(
        'import os\n\nMODEL = os.environ.get("OPENROUTER_CHAT_MODEL_ID", "openai/gpt-5.6-luna")\n',
        encoding="utf-8",
    )
    subscript = tmp_path / "subscript_reader.py"
    subscript.write_text(
        'import os\n\nMODEL = os.environ["OPENAI_CHAT_MODEL_ID"]\n', encoding="utf-8"
    )
    writer = tmp_path / "writer.py"
    writer.write_text(
        'import os\n\nos.environ["OPENROUTER_CHAT_MODEL_ID"] = "gpt-5.6-luna"\n',
        encoding="utf-8",
    )
    delegating = tmp_path / "delegating.py"
    delegating.write_text(
        "from argumentation_analysis.core.llm_service import resolve_chat_endpoint\n"
        "\n"
        "_KEY, _BASE, MODEL = resolve_chat_endpoint()\n",
        encoding="utf-8",
    )

    found = _model_id_read_sites([carrier, subscript, writer, delegating], tmp_path)

    assert found == {
        "carrier.py": ("OPENROUTER_CHAT_MODEL_ID",),
        "subscript_reader.py": ("OPENAI_CHAT_MODEL_ID",),
    }, found


_SEAT_DRIVER = r'''
"""Measure the model each measurement script would send, in a throwaway process.

Run as ``python -c <this>`` with the ``_SEAT_*`` variables set. A subprocess is
mandatory, not stylistic: these scripts load ``.env``, ``chdir`` to the repo
root, and ``run_fb32`` calls ``sys.exit`` at import time when determinism is
forced — importing them into the pytest process would mutate it.
"""
import asyncio
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

root = Path(os.environ["_SEAT_ROOT"])
sys.path.insert(0, str(root))

import argumentation_analysis.core.llm_service as _llm_service


class _Recorder:
    """Stands in for ``openai.OpenAI``: records construction and call kwargs."""

    constructions = []
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        _Recorder.constructions.append(kwargs)
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        _Recorder.calls.append(kwargs)
        choice = types.SimpleNamespace(
            message=types.SimpleNamespace(content="stub"),
            text=None,
            finish_reason="stop",
        )
        return types.SimpleNamespace(choices=[choice])


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, root / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_SCRIPTS = json.loads(os.environ["_SEAT_SCRIPTS"])
modules = {rel: _load("seat_" + Path(rel).stem, rel) for rel in _SCRIPTS}

# The seat is imposed AFTER the imports: each of these scripts loads .env at
# module level with os.environ.setdefault, which must not decide the case.
seat = json.loads(os.environ["_SEAT"])
for _var in seat["unset"]:
    os.environ.pop(_var, None)
for _var, _value in seat["set"].items():
    os.environ[_var] = _value

# Measured before any patching, so the accord is between the scripts and the
# REAL resolver, in this one process and this one environment.
canonical = _llm_service.resolve_chat_endpoint()

if os.environ.get("_SEAT_SENTINEL") == "1":
    _llm_service.resolve_chat_endpoint = lambda *a, **k: (
        "sk-sentinel-not-a-real-key",
        "https://sentinel.invalid/v1",
        "sentinel-model",
    )

import openai

openai.OpenAI = _Recorder

_SITES = {}


def _snapshot(rel, model, construction):
    _SITES[rel] = {
        "model": model,
        "base_url": construction.get("base_url"),
        "api_key": construction.get("api_key"),
    }


_LEGACY = "scripts/run_capstone_c1.py"
_before_calls = len(_Recorder.calls)
_before_constructions = len(_Recorder.constructions)
asyncio.run(modules[_LEGACY].run_zeroshot_baseline("A", "Texte synthetique."))
assert len(_Recorder.calls) > _before_calls, "run_zeroshot_baseline made no call"
_snapshot(
    _LEGACY,
    _Recorder.calls[_before_calls]["model"],
    _Recorder.constructions[_before_constructions],
)

for _rel in (
    "scripts/run_fb28_quality_headtohead.py",
    "scripts/run_fb29_agentic_headtohead.py",
    "scripts/run_fb32_decast_variance.py",
):
    _before_constructions = len(_Recorder.constructions)
    _client, _model = modules[_rel]._get_llm_client()
    _snapshot(_rel, _model, _Recorder.constructions[_before_constructions])

Path(os.environ["_SEAT_OUT"]).write_text(
    json.dumps(
        {
            "canonical": {"model": canonical[2], "base_url": canonical[1]},
            "sites": _SITES,
        }
    ),
    encoding="utf-8",
)
'''


def _seat(set_vars: Dict[str, str]) -> Dict[str, Any]:
    return {"set": set_vars, "unset": list(_ROUTE_VARS)}


def _measure_the_scripts(
    tmp_path: Path, seat: Dict[str, Any], sentinel: bool = False
) -> Dict[str, Any]:
    """Run the four sites in a subprocess under ``seat``; return what they sent."""
    out = tmp_path / "seat.json"
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in _ROUTE_VARS
        and key != "LLM_DETERMINISTIC_MODE"  # run_fb32 sys.exit()s on it at import
        and not key.startswith("PYTEST_")
    }
    env.update(
        {
            "_SEAT_ROOT": str(REPO_ROOT),
            "_SEAT_OUT": str(out),
            "_SEAT": json.dumps(seat),
            "_SEAT_SCRIPTS": json.dumps(list(_MEASUREMENT_SCRIPTS)),
            "_SEAT_SENTINEL": "1" if sentinel else "0",
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    proc = subprocess.run(
        [sys.executable, "-c", _SEAT_DRIVER],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert out.exists(), (
        f"the seat driver wrote no result (rc={proc.returncode}).\n"
        f"--- stdout ---\n{proc.stdout[-2000:]}\n--- stderr ---\n{proc.stderr[-4000:]}"
    )
    return json.loads(out.read_text(encoding="utf-8"))


def test_measurement_scripts_agree_with_the_resolver_on_the_prescribed_seat(
    tmp_path: Path,
) -> None:
    """THE measured divergence, on the seat ``.env.example`` prescribes.

    Pre-repair the four scripts answered ``openai/gpt-5.6-luna`` — a string no
    resolver renders — while the canonical resolver rendered the configured
    ``OPENAI_CHAT_MODEL_ID``. So the failure is a **model value**, named per
    script, never an ``ImportError``.
    """
    result = _measure_the_scripts(
        tmp_path,
        _seat(
            {
                "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY": "sk-or-synthetic-not-a-real-key",
                "OPENAI_CHAT_MODEL_ID": "openai/gpt-5.6-pro",
            }
        ),
    )

    canonical = result["canonical"]
    assert canonical["model"] == "openai/gpt-5.6-pro", canonical

    divergent = {
        rel: site["model"]
        for rel, site in result["sites"].items()
        if site["model"] != canonical["model"]
    }
    assert not divergent, (
        f"measurement scripts naming a model the run does not use: {divergent} "
        f"(the resolver rendered {canonical['model']!r}) — they must call "
        "resolve_chat_endpoint instead of re-deriving the toggle (#2352)."
    )
    # The endpoint follows too: a model without its route is half a provenance.
    endpoints = {site["base_url"] for site in result["sites"].values()}
    assert endpoints == {canonical["base_url"]}, (endpoints, canonical["base_url"])


def test_measurement_scripts_accord_control_with_a_declared_openrouter_model(
    tmp_path: Path,
) -> None:
    """Non-vacuity: this seat already agreed BEFORE the repair.

    With ``OPENROUTER_CHAT_MODEL_ID`` set, the inline toggle and the resolver
    rendered the same model — so a green here cannot be read as "the repair
    fixed a case that was never broken". It pairs with the measured seat to show
    the divergence was configuration-dependent.
    """
    result = _measure_the_scripts(
        tmp_path,
        _seat(
            {
                "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY": "sk-or-synthetic-not-a-real-key",
                "OPENROUTER_CHAT_MODEL_ID": "gpt-5.6-luna",
                "OPENAI_CHAT_MODEL_ID": "openai/gpt-5.6-pro",  # never consulted
            }
        ),
    )

    assert result["canonical"]["model"] == "gpt-5.6-luna", result["canonical"]
    models = {site["model"] for site in result["sites"].values()}
    assert models == {"gpt-5.6-luna"}, result["sites"]


def test_measurement_scripts_delegate_to_the_canonical_resolver(
    tmp_path: Path,
) -> None:
    """Delegation, not coincidence: the scripts must follow a patched resolver.

    A script that re-derived the toggle from the environment cannot see the
    sentinel, whatever the environment says — so this reddens on any re-inlined
    resolver, and it is the only one of the three that does so in *every*
    configuration.
    """
    result = _measure_the_scripts(
        tmp_path,
        _seat(
            {
                "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY": "sk-or-synthetic-not-a-real-key",
                "OPENAI_CHAT_MODEL_ID": "openai/gpt-5.6-pro",
            }
        ),
        sentinel=True,
    )

    models = {site["model"] for site in result["sites"].values()}
    assert models == {"sentinel-model"}, result["sites"]
    endpoints = {site["base_url"] for site in result["sites"].values()}
    assert endpoints == {"https://sentinel.invalid/v1"}, result["sites"]


# ---------------------------------------------------------------------------
# R1035 — the two production files that close #2352 (#2370 tranche):
# evaluation/fallacy_benchmark.py (class B, raw SDK) and
# orchestration/conversational_orchestrator.py (class A, kernel path)
# ---------------------------------------------------------------------------


async def _fallacy_mode_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> Dict[str, Dict[str, Any]]:
    """The (api_key, base_url, model) each benchmark mode would actually use.

    Recorded on the clients the modes build: ``openai.AsyncOpenAI`` is replaced
    by a recorder (mode C's guided plugin and SK service are stubbed too — the
    plugin would drive its own LLM calls), so nothing leaves the machine.
    """
    from argumentation_analysis.evaluation.fallacy_benchmark import (
        FallacyBenchmarkRunner,
    )

    constructions: List[Dict[str, Any]] = []
    completions: List[Dict[str, Any]] = []
    sk_services: List[Dict[str, Any]] = []

    class _Completions:
        async def create(self, **kwargs: Any) -> Any:
            completions.append(kwargs)
            choice = types.SimpleNamespace(
                message=types.SimpleNamespace(content="stub")
            )
            return types.SimpleNamespace(choices=[choice])

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _Client:
        def __init__(self, **kwargs: Any) -> None:
            constructions.append(kwargs)
            self.chat = _Chat()

    class _StubSKService:
        def __init__(self, **kwargs: Any) -> None:
            sk_services.append(kwargs)

    class _StubPlugin:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def run_guided_analysis(self, argument_text: str) -> str:
            return json.dumps(
                {"fallacies": [{"taxonomy_pk": "1", "fallacy_type": "Ad hominem"}]}
            )

    class _StubKernel:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def add_service(self, _service: Any) -> None:
            pass

    monkeypatch.setattr("openai.AsyncOpenAI", _Client)
    monkeypatch.setattr("semantic_kernel.kernel.Kernel", _StubKernel)
    monkeypatch.setattr(
        "semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion", _StubSKService
    )
    monkeypatch.setattr(
        "argumentation_analysis.plugins.fallacy_workflow_plugin"
        ".FallacyWorkflowPlugin",
        _StubPlugin,
    )

    # __new__: the modes read no taxonomy state beyond `taxonomy_data`/`node_map`
    # (mode A reads neither) — skipping __init__ keeps the measurement off the
    # CSV filesystem dependency.
    runner = FallacyBenchmarkRunner.__new__(FallacyBenchmarkRunner)
    runner.taxonomy_data = []
    runner.node_map = {}

    routes: Dict[str, Dict[str, Any]] = {}
    text = "Un argument quelconque."
    await runner.run_mode_a_free(text)
    routes["mode_a_free"] = {
        "api_key": constructions[-1]["api_key"],
        "base_url": constructions[-1]["base_url"],
        "model": completions[-1]["model"],
    }
    await runner.run_mode_b_one_shot(text)
    routes["mode_b_one_shot"] = {
        "api_key": constructions[-1]["api_key"],
        "base_url": constructions[-1]["base_url"],
        "model": completions[-1]["model"],
    }
    await runner.run_mode_c_constrained(text)
    routes["mode_c_constrained"] = {
        "api_key": constructions[-1]["api_key"],
        "base_url": constructions[-1]["base_url"],
        "model": sk_services[-1]["ai_model_id"],
    }
    return routes


async def test_fallacy_modes_agree_with_the_resolver_on_the_prescribed_seat(
    monkeypatch,
) -> None:
    """THE class-B divergence, on the seat ``.env.example`` prescribes.

    Pre-repair the three modes read the raw OpenAI triple inline, so a set
    OpenRouter toggle was invisible to them: on this seat they sent the
    configured model to **api.openai.com** while the canonical resolver routed
    to OpenRouter — and with a retired model (#1930) they sent it unsubstituted.
    The failure is in **route/model values**, never an ImportError.
    """
    _seat_without_openrouter_model(monkeypatch, model="gpt-5-mini")  # retired
    canonical = resolve_chat_endpoint()
    assert canonical[2] == "gpt-5.6-luna", "the canonical resolver must substitute it"

    routes = await _fallacy_mode_routes(monkeypatch)

    divergent = {
        mode: route
        for mode, route in routes.items()
        if route["model"] != canonical[2] or route["base_url"] != canonical[1]
    }
    assert not divergent, (
        f"fallacy-benchmark modes not on the canonical route: {divergent} "
        f"(the resolver rendered model={canonical[2]!r} "
        f"base_url={canonical[1]!r}) — they must call resolve_chat_endpoint "
        "instead of reading the raw OpenAI triple (#2352/#2370)."
    )


async def test_fallacy_modes_accord_control_official_endpoint(monkeypatch) -> None:
    """Non-vacuity: with NO toggle set, the inline reads already agreed.

    On the official-endpoint seat the pre-repair triple and the resolver
    rendered the same values — so a green here cannot be read as "the repair
    fixed a case that was never broken". It pairs with the prescribed-seat
    test to show the divergence was configuration-dependent.
    """
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-synthetic-not-a-real-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "gpt-5.6-luna")

    canonical = resolve_chat_endpoint()

    routes = await _fallacy_mode_routes(monkeypatch)
    assert routes, "the recorder captured no mode — nothing was measured"
    for mode, route in routes.items():
        assert route == {
            "api_key": canonical[0],
            "base_url": canonical[1],
            "model": canonical[2],
        }, (mode, route)


def test_conversational_kernel_feeds_the_canonical_model_to_the_factory(
    monkeypatch,
) -> None:
    """The class-A site: what `_build_conversational_kernel` hands the factory.

    Pre-repair the model id was read inline with a fallback literal, so the
    OpenRouter jump and the #1930 substitution never reached the kernel path.
    The seam is measured directly — the factory is replaced by a recorder and
    the kernel by a stub, so no service is built and nothing leaves the machine.
    """
    import argumentation_analysis.orchestration.conversational_orchestrator as conversational

    _seat_without_openrouter_model(monkeypatch, model="gpt-5-mini")  # retired
    canonical = resolve_chat_endpoint()[2]
    assert canonical == "gpt-5.6-luna"

    received: Dict[str, Any] = {}

    def _recording_factory(**kwargs: Any) -> Any:
        received.update(kwargs)
        return "stub-llm-service"

    class _StubKernel:
        def __init__(self) -> None:
            self.services: List[Any] = []

        def add_service(self, service: Any) -> None:
            self.services.append(service)

    monkeypatch.setattr(conversational, "sk", types.SimpleNamespace(Kernel=_StubKernel))
    monkeypatch.setattr(conversational, "create_llm_service", _recording_factory)

    kernel = conversational._build_conversational_kernel()

    assert received["model_id"] == canonical, received
    assert received["service_id"] == "conversational_llm", received
    assert received["force_authentic"] is True, received
    assert kernel.services == ["stub-llm-service"]


async def test_fallacy_modes_and_kernel_delegate_to_the_canonical_resolver(
    monkeypatch,
) -> None:
    """Delegation, not coincidence: the new sites must follow a patched resolver.

    A site that re-derived the route from the environment cannot see the
    sentinel, whatever the environment says. Pre-repair this reddens because
    the delegated symbols do not exist (``AttributeError`` on the patch) — the
    delegation is what is being asserted.
    """
    import argumentation_analysis.core.llm_service as llm_service
    import argumentation_analysis.evaluation.fallacy_benchmark as fallacy_benchmark
    import argumentation_analysis.orchestration.conversational_orchestrator as conversational

    sentinel = (
        "sk-sentinel-not-a-real-key",
        "https://sentinel.invalid/v1",
        "sentinel-model",
    )

    def _sentinel_resolver(*_args: Any, **_kwargs: Any):
        return sentinel

    monkeypatch.setattr(fallacy_benchmark, "resolve_chat_endpoint", _sentinel_resolver)
    monkeypatch.setattr(llm_service, "resolve_chat_endpoint", _sentinel_resolver)

    routes = await _fallacy_mode_routes(monkeypatch)
    for mode, route in routes.items():
        assert (
            route["api_key"],
            route["base_url"],
            route["model"],
        ) == sentinel, (mode, route)

    received: Dict[str, Any] = {}

    def _recording_factory(**kwargs: Any) -> Any:
        received.update(kwargs)
        return "stub-llm-service"

    class _StubKernel:
        def __init__(self) -> None:
            self.services: List[Any] = []

        def add_service(self, service: Any) -> None:
            self.services.append(service)

    monkeypatch.setattr(conversational, "sk", types.SimpleNamespace(Kernel=_StubKernel))
    monkeypatch.setattr(conversational, "create_llm_service", _recording_factory)
    conversational._build_conversational_kernel()

    assert received["model_id"] == "sentinel-model", received
