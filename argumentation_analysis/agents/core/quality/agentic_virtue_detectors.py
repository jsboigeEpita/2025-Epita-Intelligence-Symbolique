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


# --- FB-38 #1127: the 5 remaining tractable virtues, agentic ---------------
#
# Same multi-step pattern as FB-29 (decompose → verify structure → score, with
# a demonstrated exhibit). The lexical detectors for these 5 virtues are weak
# surface heuristics (Flesch readability, connector counts, sentence count,
# unique-word ratio) — a 0-shot LLM scores them just as well (often better, cf
# FB-28 −1.39). The agentic upgrade's ONLY honest win is to LOCATE structure a
# 0-shot global score does not surface: the specific clarity obstacle, the
# located digression, the reconstructed premise→conclusion chain + its gap, the
# missing coverage dimension, the semantic restatement. Each detector emits that
# located structure as the exhibit.
#
# Negative controls are load-bearing: a planted text where the lexical detector
# gives a FALSE POSITIVE high score (short words but unresolvable anaphora; many
# connectors but a digression; many points but no inferential link; long but
# monodimensional; high lexical diversity but semantic restatement) MUST be
# rejected by the agentic chain. Scoring it high = the theatre #1019 forbids.

# --- clarté (clarity) -------------------------------------------------------
# Lexical = Flesch readability (rewards short words/sentences). Surface: a text
# of short words with an unresolvable anaphora or undefined jargon scores HIGH
# on Flesch but is genuinely unclear. The agentic chain LOCATES the obstacle.

_CLARTE_STEP1_PROMPT = """Tu es un analyste d'argumentation. Identifie si l'argument suivant contient des OBSTACLES À LA CLARTÉ — des éléments qui en rendent le sens difficile à saisir pour un lecteur compétent.

Étape 1 — LOCALISATION DES OBSTACLES :
- Jargon technique non défini (un terme spécialisé utilisé sans explication accessible).
- Anaphore non résolvable (un pronom ou une référence dont l'antécédent est ambigu ou absent).
- Phrase trop emboîtée (subordination excessive brouillant la structure).

Une absence d'obstacle = un texte parfaitement clair.

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_clarity_obstacle": true/false, "obstacles": "<les obstacles localisés, ou chaine vide si aucun>"}}
"""

_CLARTE_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné des obstacles à la clarté identifiés. Détermine s'ils sont GÉNUINEMENT opaques ou résolvables par le contexte.

Obstacles identifiés (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — VÉRIFICATION DE L'OPACITÉ :
- L'obstacle est-il réellement opaque (sens inaccessible), ou résolvable à partir du contexte environnant (le lecteur peut l'inférer) ?
- Un simple mot long ou une phrase dense SANS obstacle sémantique n'est PAS un obstacle opaque.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"obstacle_genuinely_opaque": true/false, "clarity_verdict": "<'opaque_réel' | 'résolvable_contexte' | 'aucun_obstacle'>", "reasoning": "<1 phrase>"}}
"""

_CLARTE_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score la clarté démontrée, sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = clarté pleine : aucun obstacle opaque, le sens est accessible
- 0.5 = clarté partielle : obstacle résolvable par contexte, sens globalement accessible
- 0.2 = clarté faible : obstacle opaque identifié mais sens partiellement reconstructible
- 0.0 = clarté insuffisante : obstacle opaque non résolvable, sens inaccessible

Obstacles identifiés (étape 1) :
{prev_step}

Verdict d'opacité (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : les obstacles localisés + le verdict>"}}
"""


def detect_clarte_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of clarity (FB-38 #1127).

    Chain: locate obstacles → verify opacity → score. Rejects the Flesch false
    positive (short words + unresolvable anaphora/jargon = genuinely unclear).

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    Raises AgenticDetectorError if the chain cannot run (fail-loud).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _CLARTE_STEP1_PROMPT, text)
    if not step1.get("has_clarity_obstacle"):
        return 1.0, "Aucun obstacle à la clarté identifié (step1: localisation)."
    obstacles = str(step1.get("obstacles", ""))[:200]
    step2 = _run_chain_step(
        resolved, _CLARTE_STEP2_PROMPT, text, prev_step=obstacles
    )
    verdict = str(step2.get("clarity_verdict", "aucun_obstacle"))[:60]
    step3 = _run_chain_step(
        resolved,
        _CLARTE_STEP3_PROMPT,
        text,
        prev_step=obstacles,
        prev_step2=verdict,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Clarte chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Clarté (agentic 3-step): obstacles='{obstacles}'; verdict='{verdict}'; "
        f"score={score}. Exhibit: {exhibit}"
    )
    return score, comment


# --- pertinence (relevance) -------------------------------------------------
# Lexical = logical-connector count. Surface: a text with many connectors but a
# clear digression scores HIGH. The agentic chain LOCATES the digression.

_PERTINENCE_STEP1_PROMPT = """Tu es un analyste d'argumentation. Identifie la THÈSE principale de l'argument, puis repère s'il contient des DIGRESSIONS — des propositions qui ne servent pas la thèse (hors-sujet, aparté non pertinent).

Étape 1 — THÈSE + DIGRESSIONS :
- Identifie la thèse principale défendue.
- Repère les propositions qui s'écartent de cette thèse (digressions).

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_thesis": true/false, "thesis": "<thèse principale, ou chaine vide>", "digressions": "<les digressions localisées, ou chaine vide si aucune>"}}
"""

_PERTINENCE_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné une thèse et d'éventuelles digressions. Vérifie si les digressions sont RÉELLES ou si toutes les propositions servent la thèse.

Thèse + digressions identifiées (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — VÉRIFICATION DE LA PERTINENCE :
- Chaque proposition sert-elle la thèse, ou y a-t-il une digression nette (aparté qui ne fait pas avancer l'argument) ?
- La présence de connecteurs logiques NE PRouve PAS la pertinence : un texte peut enchaîner logiquement des propositions hors-sujet.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_digression": true/false, "relevance_verdict": "<'toutes_pertinentes' | 'digression_localisée'>", "located_digression": "<la digression, ou chaine vide>"}}
"""

_PERTINENCE_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score la pertinence démontrée, sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = pertinence pleine : toutes les propositions servent la thèse
- 0.5 = pertinence partielle : une digression mineure, l'ensemble reste centré
- 0.2 = pertinence faible : digressions notables diluant l'argument
- 0.0 = hors-sujet : l'argument ne sert pas (ou trahit) sa thèse annoncée

Thèse + digressions identifiées (étape 1) :
{prev_step}

Verdict de pertinence (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : la thèse + les digressions localisées>"}}
"""


def detect_pertinence_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of relevance (FB-38 #1127).

    Chain: identify thesis → locate digressions → score. Rejects the connector-
    count false positive (many connectors + a digression = low relevance).

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _PERTINENCE_STEP1_PROMPT, text)
    if not step1.get("has_thesis"):
        return 0.0, "Aucune thèse identifiée (step1: pertinence non mesurable)."
    thesis = str(step1.get("thesis", ""))[:150]
    digressions = str(step1.get("digressions", ""))[:200]
    step2 = _run_chain_step(
        resolved,
        _PERTINENCE_STEP2_PROMPT,
        text,
        prev_step=f"thèse='{thesis}'; digressions='{digressions}'",
    )
    verdict = str(step2.get("relevance_verdict", "toutes_pertinentes"))[:60]
    located = str(step2.get("located_digression", ""))[:150]
    step3 = _run_chain_step(
        resolved,
        _PERTINENCE_STEP3_PROMPT,
        text,
        prev_step=f"thèse='{thesis}'; digressions='{digressions}'",
        prev_step2=verdict,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Pertinence chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Pertinence (agentic 3-step): thèse='{thesis}'; verdict='{verdict}'; "
        f"digression='{located}'. Exhibit: {exhibit}"
    )
    return score, comment


# --- structure_logique (logical structure) ----------------------------------
# Lexical = structural-connector count. Surface: a list of points with connectors
# but no actual inferential link scores HIGH. The agentic chain RECONSTRUCTS the
# premise→conclusion chain and LOCATES the gap.

_STRUCTURE_STEP1_PROMPT = """Tu es un analyste d'argumentation. Reconstruis la CHAÎNE ARGUMENTATIVE de l'argument : identifie les PRÉMISSES (les raisons données) et la CONCLUSION (ce qui est conclu).

Étape 1 — EXTRACTION DE LA CHAÎNE :
- Prémisses = les propositions qui servent de raison/de fondement.
- Conclusion = la proposition déduite/défendue.
- Une structure logique EXIGE une relation inférentielle prémisse(s)→conclusion, pas une simple énumération de points.

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_chain": true/false, "premises": "<les prémisses, ou chaine vide>", "conclusion": "<la conclusion, ou chaine vide>"}}
"""

_STRUCTURE_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné une chaîne prémisse→conclusion reconstruite. Vérifie si la relation inférentielle TIENT réellement ou s'il y a un SAUT LOGIQUE.

Chaîne reconstruite (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — VÉRIFICATION DE LA COHÉRENCE :
- La conclusion suit-elle logiquement des prémisses (progression logique), ou s'agit-il d'une énumération de points sans lien inférentiel (énumération_sans_lien) ?
- Y a-t-il un saut logique (la conclusion ne découle pas des prémisses) ?
- La présence de connecteurs (« donc », « ainsi ») NE SUFFIT PAS : un « donc » peut être purement rhétorique sans inférence réelle.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"chain_holds": true/false, "structure_verdict": "<'progression_logique' | 'énumération_sans_lien' | 'saut_logique'>", "reasoning": "<1 phrase>"}}
"""

_STRUCTURE_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score la structure logique démontrée, sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = structure pleine : prémisse(s)→conclusion avec inférence réelle
- 0.5 = structure partielle : inférence présente mais imparfaite/imprécise
- 0.2 = structure faible : énumération de points avec connecteurs rhétoriques mais sans inférence solide
- 0.0 = pas de structure : points non reliés, OU saut logique net (la conclusion ne découle pas des prémisses)

Chaîne reconstruite (étape 1) :
{prev_step}

Verdict de structure (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : la chaîne reconstruite + le verdict>"}}
"""


def detect_structure_logique_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of logical structure (FB-38 #1127).

    Chain: extract premise→conclusion → verify coherence → score. Rejects the
    connector-count false positive (enumeration with rhetorical connectors but
    no inference = weak structure).

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _STRUCTURE_STEP1_PROMPT, text)
    if not step1.get("has_chain"):
        return 0.0, "Aucune chaîne prémisse→conclusion identifiée (step1)."
    chain = (
        f"prémisses='{str(step1.get('premises', ''))[:150]}'; "
        f"conclusion='{str(step1.get('conclusion', ''))[:120]}'"
    )
    step2 = _run_chain_step(
        resolved, _STRUCTURE_STEP2_PROMPT, text, prev_step=chain
    )
    verdict = str(step2.get("structure_verdict", "saut_logique"))[:60]
    step3 = _run_chain_step(
        resolved,
        _STRUCTURE_STEP3_PROMPT,
        text,
        prev_step=chain,
        prev_step2=verdict,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Structure_logique chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Structure logique (agentic 3-step): {chain}; verdict='{verdict}'; "
        f"score={score}. Exhibit: {exhibit}"
    )
    return score, comment


# --- exhaustivité (comprehensiveness) ---------------------------------------
# Lexical = sentence count (rewards length). Surface: a long text covering only
# ONE dimension scores HIGH. The agentic chain IDENTIFIES the expected dimensions
# and LOCATES the missing ones.

_EXHAUST_STEP1_PROMPT = """Tu es un analyste d'argumentation. Identifie le SUJET de l'argument et les DIMENSIONS pertinentes qu'un traitement exhaustif devrait couvrir.

Étape 1 — SUJET + DIMENSIONS ATTENDUES :
- Sujet = la question/l'objet traité.
- Dimensions attendues = les aspects/facettes pertinents qu'un traitement complet du sujet devrait aborder (ex. pour une politique : efficacité, coût, équité, faisabilité).

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"subject": "<sujet>", "expected_dimensions": "<les dimensions qu'un traitement exhaustif couvrirait>"}}
"""

_EXHAUST_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné le sujet et les dimensions attendues. Détermine quelles dimensions sont RÉELLEMENT COUVERTES et lesquelles MANQUENT.

Sujet + dimensions attendues (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — VÉRIFICATION DE LA COUVERTURE :
- Quelles dimensions attendues sont couvertes par l'argument ?
- Quelles dimensions manquent (localise-les) ?
- Un texte long qui martèle UNE seule dimension reste MONODIMENSIONNEL (pas exhaustif) : la longueur ne prouve pas la couverture.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"covered_dimensions": "<dimensions couvertes>", "missing_dimensions": "<dimensions manquantes localisées, ou chaine vide>", "coverage_verdict": "<'couverture_large' | 'couverture_partielle' | 'monodimensionnel_seul'>"}}
"""

_EXHAUST_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score l'exhaustivité démontrée, sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = couverture large : la plupart des dimensions pertinentes du sujet sont traitées
- 0.5 = couverture partielle : plusieurs dimensions couvertes mais des manques notables
- 0.2 = couverture faible : une seule dimension abordée malgré un sujet multidimensionnel
- 0.0 = monodimensionnel : le texte ne couvre qu'une facette, ou est trop court pour juger

Sujet + dimensions (étape 1) :
{prev_step}

Verdict de couverture (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : dimensions couvertes + manquantes>"}}
"""


def detect_exhaustivite_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of comprehensiveness (FB-38 #1127).

    Chain: identify subject + expected dimensions → check coverage → score.
    Rejects the sentence-count false positive (long but monodimensional = low
    exhaustiveness).

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _EXHAUST_STEP1_PROMPT, text)
    subject = str(step1.get("subject", ""))[:120]
    expected = str(step1.get("expected_dimensions", ""))[:200]
    dims = f"sujet='{subject}'; dimensions_attendues='{expected}'"
    step2 = _run_chain_step(
        resolved, _EXHAUST_STEP2_PROMPT, text, prev_step=dims
    )
    verdict = str(step2.get("coverage_verdict", "monodimensionnel_seul"))[:60]
    missing = str(step2.get("missing_dimensions", ""))[:150]
    step3 = _run_chain_step(
        resolved,
        _EXHAUST_STEP3_PROMPT,
        text,
        prev_step=dims,
        prev_step2=verdict,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Exhaustivite chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Exhaustivité (agentic 3-step): {dims}; verdict='{verdict}'; "
        f"manque='{missing}'. Exhibit: {exhibit}"
    )
    return score, comment


# --- redondance_faible (low redundancy) -------------------------------------
# Lexical = unique-word ratio (rewards lexical diversity). Surface: a text that
# restates the SAME point in different words scores HIGH (high lexical diversity
# but semantic redundancy). The agentic chain identifies distinct POINTS and
# LOCATES the semantic restatements.

_REDOND_STEP1_PROMPT = """Tu es un analyste d'argumentation. Identifie les POINTS ARGUMENTATIFS DISTINCTS avancés dans l'argument (chaque idée défendue séparée).

Étape 1 — EXTRACTION DES POINTS :
- Un point argumentatif = une idée/revendication distincte avancée.
- Deux phrases qui disent la même chose (reformulation) = UN seul point.
- Énumère les points réellement distincts.

Argument :
---
{arg_text}
---

Réponds UNIQUEMENT avec un objet JSON valide :
{{"distinct_points": "<les points argumentatifs distincts, numérotés>"}}
"""

_REDOND_STEP2_PROMPT = """Tu es un analyste d'argumentation. On t'a donné les points distincts identifiés. Vérifie s'il existe une REDONDANCE SÉMANTIQUE — des points qui se répètent en substance (même contenu, mots différents), OU si chaque point apporte une progression réelle.

Points distincts identifiés (étape 1) :
{prev_step}

Argument complet :
---
{arg_text}
---

Étape 2 — VÉRIFICATION DE LA REDONDANCE :
- Pour chaque paire de points, le second est-il une PROGRESSION réelle (apport nouveau) ou une REFORMULATION du premier (même idée, mots différents) ?
- Une diversité lexicale élevée NE PRouve PAS l'absence de redondance : on peut répéter la même idée avec un vocabulaire varié.

Réponds UNIQUEMENT avec un objet JSON valide :
{{"has_semantic_redundancy": true/false, "redundancy_verdict": "<'points_distincts' | 'reformulation_utile' | 'redondance_sémantique'>", "located_redundancy": "<les points qui se répètent en substance, ou chaine vide>"}}
"""

_REDOND_STEP3_PROMPT = """Tu es un évaluateur d'arguments. Score la faiblesse de la redondance (1.0 = non redondant, 0.0 = très redondant), sur l'échelle STRICTE {{0.0, 0.2, 0.5, 1.0}} :
- 1.0 = chaque point apporte une idée nouvelle, aucune reprise en substance
- 0.5 = quelques reprises, mais elles clarifient ou font progresser l'argument
- 0.2 = plusieurs points se répètent en substance, couverture effective faible
- 0.0 = l'argument martèle la même idée sous des formulations variées

Points distincts (étape 1) :
{prev_step}

Verdict de redondance (étape 2) :
{prev_step2}

Réponds UNIQUEMENT avec un objet JSON valide :
{{"score": <un de 0.0/0.2/0.5/1.0>, "exhibit": "<résumé de la structure démontrée : points distincts + redondances localisées>"}}
"""


def detect_redondance_faible_agentic(
    text: str, llm: Optional[LLMCallable] = None
) -> Tuple[float, str]:
    """Multi-step agentic detection of low redundancy (FB-38 #1127).

    Chain: extract distinct points → locate semantic restatements → score.
    Rejects the unique-word-ratio false positive (high lexical diversity +
    semantic restatement = low distinctness).

    Returns (score in {0.0, 0.2, 0.5, 1.0}, comment embedding the exhibit).
    """
    resolved = _resolve_llm(llm)
    step1 = _run_chain_step(resolved, _REDOND_STEP1_PROMPT, text)
    points = str(step1.get("distinct_points", ""))[:250]
    step2 = _run_chain_step(
        resolved, _REDOND_STEP2_PROMPT, text, prev_step=points
    )
    verdict = str(step2.get("redundancy_verdict", "redondance_sémantique"))[:60]
    located = str(step2.get("located_redundancy", ""))[:150]
    step3 = _run_chain_step(
        resolved,
        _REDOND_STEP3_PROMPT,
        text,
        prev_step=points,
        prev_step2=verdict,
    )
    score = _snap_to_scale(step3.get("score"))
    if score is None:
        raise AgenticDetectorError(
            f"Redondance_faible chain produced non-scale score: {step3.get('score')!r}"
        )
    exhibit = str(step3.get("exhibit", ""))[:300]
    comment = (
        f"Redondance faible (agentic 3-step): points='{points[:120]}'; "
        f"verdict='{verdict}'; redondance='{located}'. Exhibit: {exhibit}"
    )
    return score, comment


# --- Registry extension -----------------------------------------------------

# Typed Callable[..., ...] (not Callable[[str], ...]) because the agentic
# detectors accept an optional ``llm`` kwarg the lexical detectors do not.
# This lets the evaluator call ``detector(text, llm=agentic_llm)`` type-check
# while the underlying functions remain fully annotated.
#
# FB-29 #1105: 2 joint-zero blindspot virtues (refutation, analogie).
# FB-38 #1127: the 5 remaining tractable virtues (clarte, pertinence,
#   structure_logique, exhaustivite, redondance_faible) — see module docstring.
AGENTIC_DETECTORS: Dict[str, Callable[..., Tuple[float, str]]] = {
    "refutation_constructive": detect_refutation_constructive_agentic,
    "analogie_pertinente": detect_analogie_pertinente_agentic,
    "clarte": detect_clarte_agentic,
    "pertinence": detect_pertinence_agentic,
    "structure_logique": detect_structure_logique_agentic,
    "exhaustivite": detect_exhaustivite_agentic,
    "redondance_faible": detect_redondance_faible_agentic,
}

# Virtues that REMAIN lexical/deterministic (NOT agenticized).
# presence_sources + fiabilite_sources stay lexical (FB-29 #1105, FB-38 #1127):
# the political-corpus arguments plausibly LACK external citations — agenticizing
# them would FABRICATE sources the text does not contain = degraded theatre
# (#1019, #1127 anti-pendule). The lexical detector honestly reports the
# genuine absence (regex citation-pattern / credible-source grep → 0.0). This is
# a deliberate subtraction, not an oversight.
LEXICAL_ONLY_VIRTUES = {"presence_sources", "fiabilite_sources"}
