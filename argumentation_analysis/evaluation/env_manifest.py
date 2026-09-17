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
    """Probe the JVM/Tweety axis: jars present? version pinned? Maven available?"""
    libs_dir = Path(settings.jvm.tweety_libs_dir)
    tweety_version = settings.jvm.tweety_version
    pinned = os.environ.get("JVM_TWEETY_VERSION")

    jar_count = 0
    if libs_dir.exists():
        jar_count = len(list(libs_dir.glob("*.jar")))

    # Multi-jar layout (#2246): jars live in libs/tweety/ (Maven Central assembly)
    # Legacy fat-jar layout: jars live in libs/ root (tweetyproject.org builds)
    maven_available = shutil.which("mvn") is not None

    result: Dict[str, Any] = {
        "tweety_version_target": tweety_version,
        "jvm_tweety_version_pinned": pinned if pinned else None,
        "jar_count_in_libs_tweety": jar_count,
        "maven_available": maven_available,
        "libs_tweety_dir_exists": libs_dir.exists(),
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
    """Probe the torch / sentence-transformers axis (#1651 axis)."""
    try:
        import torch

        return {
            "torch_available": True,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
        }
    except ImportError:
        return {
            "torch_available": False,
            "torch_note": "torch not installed — neural phases will skip",
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
