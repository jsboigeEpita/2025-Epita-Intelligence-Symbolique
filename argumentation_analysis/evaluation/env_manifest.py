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

        jvm_started = jpype.isJVMStarted()
        jvm_started_note = "JVM running at probe time" if jvm_started else "JVM not running"
    except ImportError:
        jvm_started = False
        jvm_started_note = "jpype not importable — JVM state unknown, reported not started"

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
    result["self_hosted_endpoint"] = self_hosted_endpoint if self_hosted_endpoint else None
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


def _probe_overrides() -> Dict[str, Any]:
    """Surface any pinned overrides in effect — a pin must be LOUD."""
    overrides: Dict[str, Any] = {}
    for var in [
        "JVM_TWEETY_VERSION",
        "OPENAI_CHAT_MODEL_ID",
        "OPENROUTER_CHAT_MODEL_ID",
        "LLM_DETERMINISTIC_MODE",
        "LLM_TEMPERATURE",
        "LLM_SEED",
    ]:
        val = os.environ.get(var)
        if val is not None:
            overrides[var] = val
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
        lines.append("torch: unavailable — {note}".format(note=torch_axis.get("torch_note", "?")))
    lines.append(
        "overrides: {overrides}".format(
            overrides=", ".join(f"{k}={v}" for k, v in sorted(overrides.items())) or "none"
        )
    )
    lines.append("==== END ENVIRONMENT ====")
    return "\n".join(lines)
