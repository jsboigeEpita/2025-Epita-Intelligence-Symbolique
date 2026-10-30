"""Run-level environment manifest — probes each optional-dependency axis.

A run that renders on a dead JVM (or a silent LLM endpoint) must say so next
to its signature, not discover it 48 documents later (#2276, #2282).

Every probe is honest: it reads the real environment of the real run. No
mocking, no heuristic guessing — either the axis is measured as started or it
is marked not_started with the reason the probe found.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from argumentation_analysis.config.settings import settings


def _probe_jvm() -> Dict[str, Any]:
    """Probe the JVM/Tweety axis: jars present? version pinned? Maven available?

    ``jvm_started`` reflects the JVM state AT PROBE TIME — call the manifest
    at run end and it says whether the JVM actually started during the run
    (#2282 DoD: the stamp must be run-level, not a phase rollup).
    """
    libs_dir = Path(settings.jvm.tweety_libs_dir)
    tweety_version = settings.jvm.tweety_version
    pinned = os.environ.get("JVM_TWEETY_VERSION")

    jar_count = 0
    if libs_dir.exists():
        jar_count = len(list(libs_dir.glob("*.jar")))

    # Multi-jar layout (#2246): jars live in libs/tweety/ (Maven Central assembly)
    # Legacy fat-jar layout: jars live in libs/ root (tweetyproject.org builds)
    maven_available = shutil.which("mvn") is not None

    try:
        import jpype

        # bool() coercion: jpype.isJVMStarted() is a bool on real jpype, but
        # conftest's --disable-jvm-session replaces jpype with a MagicMock
        # whose return is truthy non-bool — the stamp must stay a bool either way.
        jvm_started = bool(jpype.isJVMStarted())
        jvm_started_note = (
            "JVM running at probe time" if jvm_started else "JVM not running"
        )
    except ImportError:
        jvm_started = False
        jvm_started_note = (
            "jpype not importable — JVM state unknown, reported not started"
        )

    result: Dict[str, Any] = {
        "tweety_version_target": tweety_version,
        "jvm_tweety_version_pinned": pinned if pinned else None,
        "jar_count_in_libs_tweety": jar_count,
        "maven_available": maven_available,
        "libs_tweety_dir_exists": libs_dir.exists(),
        "jvm_started": jvm_started,
        "jvm_started_note": jvm_started_note,
    }

    if jar_count > 0:
        result["jars_resolvable"] = True
        result["jars_note"] = f"{jar_count} jars in {libs_dir}"
    elif maven_available:
        result["jars_resolvable"] = True
        result["jars_note"] = "no local jars, but Maven can provision"
    else:
        result["jars_resolvable"] = False
        result["jars_note"] = (
            f"0 jars in {libs_dir} and no Maven — provisioning impossible. "
            "A JVM-facing run will fail on every formal phase (#2276)."
        )

    return result


def _probe_llm_endpoints() -> Dict[str, Any]:
    """Probe the LLM endpoint axes: OpenAI / OpenRouter / self-hosted."""
    result: Dict[str, Any] = {}

    openai_key = os.environ.get("OPENAI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_url = os.environ.get("OPENROUTER_BASE_URL")

    result["openai_configured"] = bool(openai_key)
    result["openrouter_configured"] = bool(openrouter_key and openrouter_url)
    result["openrouter_base_url"] = openrouter_url if openrouter_url else None

    # Self-hosted LLM (#2130 axis)
    self_hosted_key = os.environ.get("SELF_HOSTED_LLM_API_KEY")
    self_hosted_endpoint = os.environ.get("SELF_HOSTED_LLM_ENDPOINT")
    self_hosted_mini_key = os.environ.get("SELF_HOSTED_LLM_MINI_API_KEY")
    self_hosted_mini_endpoint = os.environ.get("SELF_HOSTED_LLM_MINI_ENDPOINT")

    result["self_hosted_configured"] = bool(self_hosted_key and self_hosted_endpoint)
    result["self_hosted_mini_configured"] = bool(
        self_hosted_mini_key and self_hosted_mini_endpoint
    )
    result["self_hosted_endpoint"] = (
        self_hosted_endpoint if self_hosted_endpoint else None
    )
    result["self_hosted_mini_endpoint"] = (
        self_hosted_mini_endpoint if self_hosted_mini_endpoint else None
    )

    return result


def _probe_torch() -> Dict[str, Any]:
    """Probe the torch / sentence-transformers axis (#1651 axis).

    Catches every import-time failure, not just ImportError: a torch whose
    DLL fails to load (CI winerror 182) or a stub module left in sys.modules
    raises AttributeError on attribute access — the probe must report that
    environment as torch_available=False with the reason, never propagate.
    """
    try:
        import torch

        return {
            "torch_available": True,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
        }
    except Exception as e:  # noqa: BLE001 — a probe reports, never raises
        return {
            "torch_available": False,
            "torch_note": f"torch unusable: {type(e).__name__}: {e}",
        }


def _anthropic_route_in_env() -> bool:
    """Whether this run's LLM calls land on Anthropic's route (#3096).

    Asked of the ONE resolver, never re-derived here. The manifest used to
    answer from the environment directly — ``ANTHROPIC_CHAT_MODEL_ID`` set,
    ``OPENAI_CHAT_MODEL_ID`` starting with ``claude-``, or ``OPENAI_BASE_URL``
    naming Anthropic — and that answer was a second route resolver, which is
    the defect #2352 counts (the census reddened on the ``OPENAI_CHAT_MODEL_ID``
    read). It also diverged from the layer it describes: ``llm_cache`` applies
    the effort and the thinking knob on ``anthropic_route(model_id)``, so a
    non-``claude-*`` named id or a bare Anthropic base URL made the manifest
    stamp "measured inert" over a knob the run would actually have applied.

    A probe reports, never raises: a declared named route without its key
    raises at resolution by design (#3096 item 6), and the startup factory
    refuses the run long before a manifest is written — no call is made, so
    no Anthropic route is in effect.
    """
    from argumentation_analysis.core.llm_service import resolve_chat_endpoint
    from argumentation_analysis.services.llm_cache import anthropic_route

    try:
        _api_key, _base_url, model_id = resolve_chat_endpoint()
    except Exception:  # noqa: BLE001 — a probe reports, never raises
        return False
    return anthropic_route(model_id)


def _probe_overrides() -> Dict[str, Any]:
    """Surface any pinned overrides in effect — a pin must be LOUD."""
    overrides: Dict[str, Any] = {}
    for var in [
        "JVM_TWEETY_VERSION",
        "OPENAI_CHAT_MODEL_ID",
        "OPENROUTER_CHAT_MODEL_ID",
        # #3096 item 6 — the named route's rung is a pin like the others.
        "ANTHROPIC_CHAT_MODEL_ID",
        "LLM_DETERMINISTIC_MODE",
        "LLM_TEMPERATURE",
        "LLM_SEED",
        # #3096 item 5 — the effort a run explicitly set is part of its record.
        "LLM_REASONING_EFFORT",
        # #3096 item 5 (R1126) — the thinking control a run explicitly set is
        # part of its record, exactly like the effort.
        "LLM_ANTHROPIC_THINKING",
    ]:
        val = os.environ.get(var)
        if val is not None:
            overrides[var] = val
    # #3096 item 5 (R1126) — a recorded control with no effect is the defect
    # this repairs, so the manifest never presents one as bare fact. On the
    # Anthropic route ``LLM_REASONING_EFFORT`` is measured INERT (comment
    # 6527232924); off that route ``LLM_ANTHROPIC_THINKING`` commands a road
    # the run is not on. Both carry their verdict instead of a bare value.
    if "LLM_REASONING_EFFORT" in overrides and _anthropic_route_in_env():
        overrides["LLM_REASONING_EFFORT"] = {
            "value": overrides["LLM_REASONING_EFFORT"],
            "verdict": (
                "measured inert on the Anthropic route (#3096 comment "
                "6527232924) — not applied; LLM_ANTHROPIC_THINKING is the "
                "control that acts there"
            ),
        }
    if "LLM_ANTHROPIC_THINKING" in overrides and not _anthropic_route_in_env():
        overrides["LLM_ANTHROPIC_THINKING"] = {
            "value": overrides["LLM_ANTHROPIC_THINKING"],
            "verdict": (
                "set but no Anthropic route resolved — not applied to any "
                "call (#3096 item 5)"
            ),
        }
    return {"pinned_overrides": overrides}


def environment_manifest() -> Dict[str, Any]:
    """Build the run-level environment manifest (#2282).

    Returns a dict with one key per optional-dependency axis, each carrying
    started/not_started + reason. This is stamped next to every run signature
    so a campaign that rendered on a dead JVM is named as such, not read as
    "ok" (#2276).

    The manifest is probed, not declared — it reads the real environment of
    the real run, never a cached or assumed state.
    """
    return {
        "jvm": _probe_jvm(),
        "llm_endpoints": _probe_llm_endpoints(),
        "torch": _probe_torch(),
        "overrides": _probe_overrides(),
    }


def _render_override(value: Any) -> str:
    """A pin's value — a bare value, or ``value (verdict)`` when the probe
    attached one (#3096 item 5, R1126)."""
    if isinstance(value, dict):
        return "{value} ({verdict})".format(
            value=value.get("value"), verdict=value.get("verdict")
        )
    return str(value)


def render_environment_stamp(env: Dict[str, Any]) -> str:
    """Render the run-level environment stamp as plain text for stdout (#2282).

    stdout is the run-visible surface (#1874/#1903): the stamp must appear in
    the campaign summary, not in a log line to go fish for. ``not_started``
    states render with their reason — a dead axis is LOUD, a live axis says
    what it is running on.
    """
    jvm = env.get("jvm", {})
    llm = env.get("llm_endpoints", {})
    torch_axis = env.get("torch", {})
    overrides = env.get("overrides", {}).get("pinned_overrides", {})

    lines = ["==== ENVIRONMENT (run-level, #2282) ===="]
    if jvm.get("jvm_started"):
        lines.append(
            "jvm: started ({note}; {jars} jars, target={target})".format(
                note=jvm.get("jvm_started_note", ""),
                jars=jvm.get("jar_count_in_libs_tweety", 0),
                target=jvm.get("tweety_version_target", "?"),
            )
        )
    else:
        lines.append(
            "jvm: not_started — {note}; resolvable={resolvable} ({res_note})".format(
                note=jvm.get("jvm_started_note", "unknown"),
                resolvable=jvm.get("jars_resolvable", False),
                res_note=jvm.get("jars_note", ""),
            )
        )
    providers = [
        name
        for name, key in (
            ("openai", "openai_configured"),
            ("openrouter", "openrouter_configured"),
            ("self_hosted", "self_hosted_configured"),
        )
        if llm.get(key)
    ]
    lines.append(
        "llm: configured=[{providers}]{self_hosted}".format(
            providers=", ".join(providers) if providers else "none",
            self_hosted=(
                " endpoint={}".format(llm["self_hosted_endpoint"])
                if llm.get("self_hosted_endpoint")
                else ""
            ),
        )
    )
    if torch_axis.get("torch_available"):
        lines.append(
            "torch: available ({version}, cuda={cuda})".format(
                version=torch_axis.get("torch_version", "?"),
                cuda=torch_axis.get("cuda_available"),
            )
        )
    else:
        lines.append(
            "torch: unavailable — {note}".format(note=torch_axis.get("torch_note", "?"))
        )
    lines.append(
        "overrides: {overrides}".format(
            # #3096 item 5 (R1126): a control measured inert on the resolved
            # route carries its verdict — ``k=v (verdict)``, never a bare
            # value that reads as effective.
            overrides=", ".join(
                f"{k}={_render_override(v)}" for k, v in sorted(overrides.items())
            )
            or "none",
        )
    )
    lines.append("==== END ENVIRONMENT ====")
    return "\n".join(lines)
