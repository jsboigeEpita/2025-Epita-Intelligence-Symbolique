"""Coordinated Logic SK Plugin — 2-pass shared-atom/formula extraction.

Exposes the 2-pass coordinated pipeline as @kernel_function methods so that
conversational agents (FormalAgent) can call them during Phase 2.

Pass 1: extract shared symbol inventory from full source text.
Pass 2: generate per-argument formulas using ONLY shared symbols.

Issues #560 (PL), #561 (FOL).
"""

import json
import logging
import os
import re
from typing import List

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


def _parse_json_from_llm(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences and noise."""
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}


def _get_openai_client():
    """Create an AsyncOpenAI client from environment config."""
    from openai import AsyncOpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None, "", ""
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
    return AsyncOpenAI(api_key=api_key, base_url=base_url), model_id, api_key


class CoordinatedLogicPlugin:
    """SK plugin for 2-pass coordinated logic extraction.

    Pass 1 methods extract shared symbol inventories from full text.
    Pass 2 methods generate per-argument formulas using ONLY shared symbols.
    """

    # ── Pass 1: Shared symbol extraction ──

    @kernel_function(
        name="extract_shared_pl_atoms",
        description=(
            "Extract shared atomic propositions from the full source text. "
            "Pass 1 of the 2-pass PL pipeline. Returns JSON with 'shared_atoms' list "
            "of validated proposition names (lowercase snake_case, Tweety-compatible). "
            "Input: full source text. Call this ONCE per source before translating arguments."
        ),
    )
    async def extract_shared_pl_atoms(self, full_text: str) -> str:
        if not full_text or len(full_text) < 100:
            return json.dumps({"shared_atoms": [], "error": "Text too short for atom extraction"})

        client, model_id, _ = _get_openai_client()
        if client is None:
            return json.dumps({"shared_atoms": [], "error": "No API key configured"})

        prompt = (
            "You are an expert in propositional logic. Your task is to identify "
            "atomic propositions (basic facts) in the given text.\n\n"
            "Output a JSON object with a single key 'propositions' mapping to a "
            "list of strings. Each string is an atomic proposition name in "
            "lowercase snake_case (e.g. 'is_mortal', 'foreign_threat').\n\n"
            f"Text:\n{full_text[:4000]}"
        )

        try:
            resp = await client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content or ""
            data = _parse_json_from_llm(raw)
            raw_atoms = data.get("propositions", [])
            valid_atoms = [a for a in raw_atoms if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", a)]

            logger.info(f"PL Pass 1: {len(valid_atoms)} atoms extracted from full text")
            return json.dumps({"shared_atoms": valid_atoms, "count": len(valid_atoms)})
        except Exception as e:
            logger.debug(f"PL atom extraction failed: {e}")
            return json.dumps({"shared_atoms": [], "error": str(e)})

    @kernel_function(
        name="extract_shared_fol_signature",
        description=(
            "Extract a shared FOL signature (sorts, predicates, constants) from full text. "
            "Pass 1 of the 2-pass FOL pipeline. Returns JSON with 'sorts', 'predicates', "
            "'constants'. Call this ONCE per source before translating arguments to FOL."
        ),
    )
    async def extract_shared_fol_signature(self, full_text: str) -> str:
        if not full_text or len(full_text) < 100:
            return json.dumps({"sorts": {}, "predicates": {}, "constants": {}, "error": "Text too short"})

        client, model_id, _ = _get_openai_client()
        if client is None:
            return json.dumps({"sorts": {}, "predicates": {}, "constants": {}, "error": "No API key"})

        prompt = (
            "You are a formal logic expert. Analyze the text and extract a "
            "first-order logic signature.\n\n"
            "Output a JSON object with:\n"
            '- "sorts": dict mapping sort_name -> list of constant names '
            '(e.g. {"Person": ["socrates", "plato"]})\n'
            '- "predicates": dict mapping pred_name -> list of arg sort names '
            '(e.g. {"Mortal": ["Person"], "Human": ["Person"]})\n'
            '- "constants": dict mapping const_name -> description '
            '(e.g. {"socrates": "the philosopher"})\n\n'
            "Rules:\n"
            "- Sorts: group related constants (Person, Country, etc.)\n"
            "- Predicates: CamelCase, list arg sorts\n"
            "- Constants: lowercase\n"
            '- If unsure about sort, use "Thing"\n\n'
            f"Text:\n{full_text[:4000]}"
        )

        try:
            resp = await client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content or ""
            sig_data = _parse_json_from_llm(raw)
            sorts = sig_data.get("sorts", {})
            predicates = sig_data.get("predicates", {})
            constants = sig_data.get("constants", {})

            if not sorts and constants:
                sorts = {"Thing": list(constants.keys())}

            logger.info(
                f"FOL Pass 1: {len(sorts)} sorts, {len(predicates)} predicates, "
                f"{sum(len(v) for v in sorts.values())} constants"
            )
            return json.dumps({"sorts": sorts, "predicates": predicates, "constants": constants})
        except Exception as e:
            logger.debug(f"FOL signature extraction failed: {e}")
            return json.dumps({"sorts": {}, "predicates": {}, "constants": {}, "error": str(e)})

    # ── Pass 2: Per-argument formula generation ──

    @kernel_function(
        name="generate_pl_formulas_with_shared_atoms",
        description=(
            "Generate PL formulas for a single argument using ONLY the provided shared atoms. "
            "Pass 2 of the 2-pass PL pipeline. "
            "Input: 'argument_text' (the argument) and 'shared_atoms' (JSON list of atom names). "
            "Returns JSON with 'formulas' list. Call after extract_shared_pl_atoms."
        ),
    )
    async def generate_pl_formulas_with_shared_atoms(
        self, argument_text: str, shared_atoms: str
    ) -> str:
        client, model_id, _ = _get_openai_client()
        if client is None:
            return json.dumps({"formulas": [], "error": "No API key"})

        try:
            atoms = json.loads(shared_atoms) if isinstance(shared_atoms, str) else shared_atoms
        except json.JSONDecodeError:
            return json.dumps({"formulas": [], "error": "Invalid shared_atoms JSON"})

        if not atoms or not argument_text:
            return json.dumps({"formulas": []})

        atoms_json = json.dumps({"propositions": atoms}, indent=2)
        prompt = (
            "You are an expert in propositional logic. Translate the text "
            "into logical formulas using ONLY the provided atomic propositions.\n\n"
            "Rules:\n"
            "- Use ONLY the propositions from the list below. Do NOT invent new ones.\n"
            "- Operators: ! (not), && (and), || (or), => (implies), <=> (iff)\n"
            "- Output a JSON object with a single key 'formulas' mapping to a "
            "list of formula strings.\n\n"
            f"Text:\n{argument_text[:2000]}\n\n"
            f"Allowed propositions:\n{atoms_json}"
        )

        try:
            resp = await client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content or ""
            data = _parse_json_from_llm(raw)
            formulas = [f for f in data.get("formulas", []) if f]

            logger.info(f"PL Pass 2: {len(formulas)} formulas with {len(atoms)} shared atoms")
            return json.dumps({"formulas": formulas, "used_atoms": atoms})
        except Exception as e:
            logger.debug(f"PL formula generation failed: {e}")
            return json.dumps({"formulas": [], "error": str(e)})

    @kernel_function(
        name="generate_fol_formulas_with_shared_signature",
        description=(
            "Generate FOL formulas for a single argument using ONLY the provided shared signature. "
            "Pass 2 of the 2-pass FOL pipeline. "
            "Input: 'argument_text' and 'shared_signature' (JSON with sorts/predicates/constants). "
            "Returns JSON with 'formulas' list. Call after extract_shared_fol_signature."
        ),
    )
    async def generate_fol_formulas_with_shared_signature(
        self, argument_text: str, shared_signature: str
    ) -> str:
        client, model_id, _ = _get_openai_client()
        if client is None:
            return json.dumps({"formulas": [], "error": "No API key"})

        try:
            sig = json.loads(shared_signature) if isinstance(shared_signature, str) else shared_signature
        except json.JSONDecodeError:
            return json.dumps({"formulas": [], "error": "Invalid shared_signature JSON"})

        if not sig or not argument_text:
            return json.dumps({"formulas": []})

        sig_json = json.dumps(sig, indent=2)
        prompt = (
            "You are a formal logic expert. Translate the text "
            "into first-order logic formulas using ONLY the "
            "provided signature.\n\n"
            "Rules:\n"
            "- Use ONLY the predicates and constants from the signature\n"
            "- Predicates: CamelCase, constants: lowercase\n"
            "- Quantifiers: forall X: (...), exists X: (...)\n"
            "- Operators: ! (not), && (and), || (or), => (implies)\n"
            "- Output JSON with key 'formulas' (list of formula strings)\n\n"
            f"Text:\n{argument_text[:2000]}\n\n"
            f"Signature:\n{sig_json}"
        )

        try:
            resp = await client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content or ""
            data = _parse_json_from_llm(raw)
            formulas = [f.strip() for f in data.get("formulas", []) if f and f.strip()]

            logger.info(f"FOL Pass 2: {len(formulas)} formulas with shared signature")
            return json.dumps({"formulas": formulas})
        except Exception as e:
            logger.debug(f"FOL formula generation failed: {e}")
            return json.dumps({"formulas": [], "error": str(e)})
