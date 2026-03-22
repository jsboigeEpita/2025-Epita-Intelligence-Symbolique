"""AI Shield — adversarial protection framework for LLM pipelines.

Modular firewall/filter system that validates inputs before LLM calls
and filters outputs for sensitive information leaks.

Recreated from project 2.5.6 soutenance description (Schweitzer, Ruff, Hantzberg).

Layers:
  1. Heuristic — regex/keyword validation (fast, no LLM cost)
  2. LLM Validator — jailbreak/bias detection via LLM
  3. Output Filter — prevents sensitive information leaks

Usage:
    from argumentation_analysis.services.ai_shield import Shield, load_preset

    shield = load_preset("basic")  # heuristic only
    result = shield.validate_input("some user input")
    if result.blocked:
        print(f"Blocked: {result.reason}")
"""

from argumentation_analysis.services.ai_shield.shield import (
    Shield,
    ShieldResult,
    ShieldLayer,
)
from argumentation_analysis.services.ai_shield.presets import load_preset

__all__ = ["Shield", "ShieldResult", "ShieldLayer", "load_preset"]
