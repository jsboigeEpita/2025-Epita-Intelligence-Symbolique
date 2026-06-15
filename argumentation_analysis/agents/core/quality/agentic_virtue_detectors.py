"""Agentic multi-step virtue detectors (FB-29 #1105, Epic #947).

The deterministic detectors in ``quality_evaluator.py`` are *lexical* — they
grep for a fixed marker list (``marqueurs_refutation``, ``patterns_analogies``).
FB-28 (#1103) proved these score 0.0 on dense political-corpus arguments even
when the structure is arguably present: the markers do not appear verbatim, so
the detector fires nothing. Worse, a 0-shot LLM baseline scores the SAME args
on the SAME rubric and *also* largely returns 0.0 on these two virtues — a
joint blindspot, not a pipeline win (FB-28 §4).

The *only honest route* to quality→DECIDES (#1105 DoD) is to make the pipeline
detect structure a single 0-shot call cannot surface: a **multi-step reasoning
chain** where each step consumes the previous step's output. A 0-shot baseline
emits one score per virtue; these detectors emit a *demonstrated structure*
(located rebuttal-target / domain-mapping) that can be exhibited as evidence.

Design constraints (anti-théâtre #1019, anti-pendule):
- **Higher numbers ≠ better.** The deliverable is *demonstrated structure*, not
  inflated scores. A detector that returns 1.0 without locating the structure
  it claims is theatre.
- **Negative control is load-bearing.** A planted pseudo-refutation (strawman)
  or surface ``comme X`` non-analogy MUST be rejected. The detector proves it
  discriminates by refusing, not by scoring.
- **No synthetic zeros.** If the LLM dependency is unavailable, the detector
  raises — it never returns ``0.0`` "as if measured". That is the exact
  degraded theatre #1019 forbids.
- **LLM dependency is injectable.** Tests patch the callable, not the detector
  internals — the detector logic is what is under test.

Multi-step structure (what a 0-shot call cannot replicate):

  refutation_constructive:
    step 1 — DECOMPOSE: split into claims; locate an opposing/counter claim.
    step 2 — VERIFY ENGAGEMENT: does the rebuttal address THAT claim's actual
             thesis, or a strawman / non-sequitur?
    step 3 — SCORE: on demonstrated engagement (0.0–1.0), with the located
             target + verdict as exhibit.

  analogie_pertinente:
    step 1 — DOMAINS: identify source domain + target domain of the analogy.
    step 2 — MAPPING: map the structural correspondence between domains.
    step 3 — SCORE: on mapping quality (reject surface "comme X" with no
             structural mapping), with domains + mapping as exhibit.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional, Protocol, Tuple

logger = logging.getLogger("AgenticVirtueDetectors")

# Reusable LLM callable contract: takes a prompt string, returns a string.
# Injected so tests patch the dependency, not the detector (FB-29 DoD).
LLMCallable = Callable[[str], str]


class AgenticDetectorError(RuntimeError):
    """Raised when an agentic detector cannot run (env/LLM unavailable).

    Fail-loud per #1019: the caller MUST see the failure rather than receive
    synthetic ``0.0`` scores "as if measured".
    """


# --- LLM callable resolution ------------------------------------------------

_DEFAULT_LLM: Optional[LLMCallable] = None


def set_default_llm_callable(llm: Optional[LLMCallable]) -> None:
    """Register the process-wide default LLM callable for agentic detectors.

    Production wires the OpenRouter-toggle-aware client here (see
    ``invoke_callables._get_quality_llm`` / FB-21 toggle). Tests pass a stub
    via the detector constructor and leave this unset.
    """
    global _DEFAULT_LLM
    _DEFAULT_LLM = llm


def _resolve_llm(explicit: Optional[LLMCallable]) -> LLMCallable:
    """Return the LLM callable to use, or raise AgenticDetectorError."""
    llm = explicit or _DEFAULT_LLM
    if llm is None:
        raise AgenticDetectorError(
            "Agentic virtue detector has no LLM callable. Wire one via "
            "set_default_llm_callable() (production) or pass llm= to the "
            "detector (tests). Fail-loud per #1019 — not returning synthetic "
            "zeros as if measured."
        )
    return llm


# --- Prompt templates (multi-step chains) -----------------------------------

# Each prompt asks for STRICT JSON only (parse-or-reject), so the chain is
# deterministic-ish in shape even though the LLM is stochastic. The prompts use
# {arg_text} / {prev_step} as plain placeholders replaced via str.replace (NOT
# str.format) because the rubric contains literal braces {0.0, 0.2, 0.5, 1.0}
# — the same FB-28 .format() bug that broke positional args.

_REFUT_STEP1_PROMPT = """Tu es un analyste d'argumentation. Décompose l'argument suivant et identifie s'il contient une RÉFUTATION CONSTRUCTIVE — c'est-à-dire s'il adresse une position adverse (une thèse opposée qu'il cherche à contredire).

Étape 1 — DÉCOMPOSITION :
- Identifie la thèse principale défendue.
- Identifie la position adverse référencée (la thèse que l'auteur cherche à réfuter), si elle est présente. Une réfutation constructive EXIGE une position adverse explicite ou clairement implicite.

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_opposing_claim": true/false, "opposing_claim": "<la position adverse identifiée, ou chaine vide si aucune>", "main_thesis": "<thèse principale>"}}
"""

_REFUT_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné une position adverse identifiée dans un argument. Détermine si la réfutation l'engage RÉELLEMENT ou si c'est un homme de paille / non-sequitur.

Position adverse identifiée (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — VÉRIFICATION DE L'ENGAGEMENT :
- La réfutation adresse-t-elle la position adverse RÉELLE, ou une version déformée (homme de paille) ?
- Y a-t-il un lien logique entre la réfutation et la position adverse, ou est-ce un hors-sujet (non-sequitur) ?

Réponds UNIQUEMENT avec un objet JSON valide :
{{"engages_real_claim": true/false, "engagement_verdict": "<'engagement_réel' | 'homme_de_paille' | 'non_sequitur' | 'pas_de_refutation'>", "reasoning": "<1 phrase>"}}
"""

_REFUT_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score la qualité de la réfutation constructive démontrée, sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = réfutation constructive pleinement démontrée : position adverse identifiée + engagement réel sur la thèse adverse
- 0.5 = réfutation partielle : position adverse présente mais engagement partiel/imprécis
- 0.2 = trace de réfutation : position adverse évoquée mais non réellement adressée
- 0.0 = aucune réfutation constructive : pas de position adverse, OU homme de paille, OU non-sequitur

Position adverse identifiée (étape 1) :
{prev_step}

Verdict d'engagement (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : la position adverse + le verdict d'engagement>"}}
"""

_ANALOGY_STEP1_PROMPT = """Tu es un analyste d'argumentation. Identifie si l'argument suivant contient une ANALOGIE — un rapprochement entre deux domaines (un domaine source et un domaine cible) pour éclairer ce dernier.

Étape 1 — IDENTIFICATION DES DOMAINES :
- Domaine source = le domaine utilisé comme comparant (le plus concret/connu).
- Domaine cible = le domaine à expliquer/étayer (le sujet de l'argument).
- Une analogie EXIGE deux domaines distincts reliés par un opérateur de comparaison (comme, tel, à l'image de) OU une métaphore étendue.

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_analogy": true/false, "source_domain": "<domaine source, ou chaine vide>", "target_domain": "<domaine cible, ou chaine vide>"}}
"""

_ANALOGY_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné une analogie identifiée. Établis la correspondance STRUCTURELLE entre les deux domaines (au-delà d'une simple comparaison de surface).

Analogie identifiée (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — MAPPING STRUCTUREL :
- Quels éléments/relations du domaine source correspondent à quels éléments/relations du domaine cible ?
- Une analogie de surface ("c'est comme X" sans correspondance structurelle) NE COMPTE PAS — rejette-la.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_structural_mapping": true/false, "mapping": "<la correspondance structurelle identifiée, ou 'surface_seule' si c'est une comparaison sans profondeur>", "reasoning": "<1 phrase>"}}
"""

_ANALOGY_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score la pertinence de l'analogie démontrée, sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = analogie pertinente pleinement démontrée : deux domaines + correspondance structurelle identifiée
- 0.5 = analogie partielle : deux domaines mais mapping structurel partiel/imprécis
- 0.2 = trace d'analogie : domaine source évoqué mais mapping surface-seule
- 0.0 = aucune analogie pertinente : pas d'analogie, OU surface "comme X" sans correspondance structurelle

Analogie identifiée (étape 1) :
{prev_step}

Verdict de mapping (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : les domaines + le mapping>"}}
"""


# --- JSON parsing (loose, code-fence tolerant) ------------------------------

def _parse_json_strict(text: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON object from LLM output, tolerating code fences/prose.

    Returns None on failure (caller decides fail-loud vs default). Mirrors the
    FB-28 harness parser so behaviour is consistent across the quality path.
    """
    import re

    cleaned = re.sub(r"```(?:json)?\s*", "", text or "")
    cleaned = cleaned.replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _snap_to_scale(val: Any) -> Optional[float]:
    """Snap a value to {0.0, 0.2, 0.5, 1.0}; None if not coercible."""
    scale = [0.0, 0.2, 0.5, 1.0]
    if isinstance(val, bool):  # bool is an int subclass — reject explicitly
        return None
    if isinstance(val, (int, float)):
        clamped = max(0.0, min(1.0, float(val)))
        return min(scale, key=lambda s: abs(s - clamped))
    return None


# --- Chain step runner -------------------------------------------------------

def _run_chain_step(
    llm: LLMCallable,
    prompt: str,
    arg_text: str,
    prev_step: str = "",
    prev_step2: str = "",
) -> Dict[str, Any]:
    """Run one chain step: substitute placeholders, call LLM, parse JSON.

    Raises AgenticDetectorError if the LLM output is unparseable — fail-loud
    rather than fabricating a step result that would poison the chain.
    """
    filled = prompt.replace("{arg_text}", arg_text[:4000])
    filled = filled.replace("{prev_step}", str(prev_step)[:2000])
    filled = filled.replace("{prev_step2}", str(prev_step2)[:2000])
    try:
        raw = llm(filled)
    except Exception as exc:  # LLM transport failure — fail loud, no fallback.
        raise AgenticDetectorError(
            f"LLM callable raised during agentic chain step: {exc}"
        ) from exc
    parsed = _parse_json_strict(raw)
    if parsed is None:
        raise AgenticDetectorError(
            "Agentic chain step returned unparseable LLM output — refusing to "
            "fabricate a step result (fail-loud per #1019)."
        )
    return parsed


# --- Public detectors -------------------------------------------------------

def detect_refutation_constructive_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of constructive refutation (FB-29 #1105).

    Chain: decompose → verify engagement → score. The exhibit (located
    opposing claim + engagement verdict) is what a 0-shot call does not
    surface — that demonstrated structure is the content-separation claim.

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    Raises AgenticDetectorError if the chain cannot run (fail-loud).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _REFUT_STEP1_PROMPT, text)
    if not step1.get("has_opposing_claim"):
        # Genuine absence — located nothing, scored 0.0 with the (empty)
        # exhibit. This is a measured zero, not a synthetic fallback.
        return 0.0, "Aucune position adverse identifiée (step1: décomposition)."
    opposing = str(step1.get("opposing_claim", ""))[:200]
    step2 = _run_chain_step(
        resolved, _REFUT_STEP2_PROMPT, text, prev_step=opposing
    )
    verdict = str(step2.get("engagement_verdict", "pas_de_refutation"))[:60]
    step3 = _run_chain_step(
        resolved,
        _REFUT_STEP3_PROMPT,
        text,
        prev_step=opposing,
        prev_step2=verdict,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Refutation chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Réfutation constructive (agentic 3-step): position adverse='{opposing}'; "
        f"verdict='{verdict}'; score={score}. Exhibit: {exhibit}"
    )
    return score, comment


def detect_analogie_pertinente_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of pertinent analogy (FB-29 #1105).

    Chain: identify domains → map structural correspondence → score. Rejects
    surface ``comme X`` without structural mapping (the FB-28 §4 blindspot).

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    Raises AgenticDetectorError if the chain cannot run (fail-loud).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _ANALOGY_STEP1_PROMPT, text)
    if not step1.get("has_analogy"):
        return 0.0, "Aucune analogie identifiée (step1: domaines)."
    domains = (
        f"source='{str(step1.get('source_domain', ''))[:80]}'; "
        f"target='{str(step1.get('target_domain', ''))[:80]}'"
    )
    step2 = _run_chain_step(
        resolved, _ANALOGY_STEP2_PROMPT, text, prev_step=domains
    )
    mapping = str(step2.get("mapping", "surface_seule"))[:120]
    step3 = _run_chain_step(
        resolved,
        _ANALOGY_STEP3_PROMPT,
        text,
        prev_step=domains,
        prev_step2=mapping,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Analogy chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Analogie pertinente (agentic 3-step): {domains}; mapping='{mapping}'; "
        f"score={score}. Exhibit: {exhibit}"
    )
    return score, comment


# --- Registry extension -----------------------------------------------------

# Typed Callable[..., ...] (not Callable[[str], ...]) because the agentic
# detectors accept an optional ``llm`` kwarg the lexical detectors do not.
# This lets the evaluator call ``detector(text, llm=agentic_llm)`` type-check
# while the underlying functions remain fully annotated.
AGENTIC_DETECTORS: Dict[str, Callable[..., Tuple[float, str]]] = {
    "refutation_constructive": detect_refutation_constructive_agentic,
    "analogie_pertinente": detect_analogie_pertinente_agentic,
}

# Virtues that REMAIN lexical/deterministic (not upgraded to agentic in FB-29).
# Source-virtues (presence_sources, fiabilite_sources) stay lexical: the corpus
# plausibly lacks external citations, and #1105 DoD forbids fabricating them.
LEXICAL_ONLY_VIRTUES = {"clarte", "pertinence", "structure_logique", "exhaustivite", "redondance_faible", "presence_sources", "fiabilite_sources"}
